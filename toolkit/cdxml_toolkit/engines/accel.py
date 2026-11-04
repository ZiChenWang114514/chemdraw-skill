"""Adaptive task-complexity classifier and idle-timeout resident worker pool for prediction engines.

Design goals:
- Simple one-off tasks (or explicit user hints such as "简单任务" / "只跑一个" / "simple" /
  ``CHEMDRAW_ACCEL=off|simple``) run as clean one-shot subprocesses and leave zero background
  processes or resident GPU allocations behind.
- Complex tasks (batch inputs, multi-step route searches, iterative multi-call sessions within a
  short burst window, or explicit complex-task hints) automatically warm and reuse a loopback-only,
  token-authenticated resident worker with a strict idle TTL and LRU cap (`MAX_RESIDENT_DAEMONS = 2`).
"""

from __future__ import annotations

import dataclasses
import json
import os
import re
import secrets
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

DEFAULT_IDLE_SECONDS = 180
BURST_WINDOW_SECONDS = 180
MAX_RESIDENT_DAEMONS = 2
COMPLEXITY_THRESHOLD = 2

# Engines whose models load cleanly in-process inside worker.py without huge (>10 GB) CPU stock tables
# or nested external CLI entrypoints.
DAEMON_CAPABLE_ENGINES = frozenset({
    'molscribe',
    'molnextr',
    'molparser',
    'decimer-local',
    'decimer-segmentation',
    'aizynthfinder',
    'reactiont5-forward',
    'reactiont5-retro',
    'magnet',
})

_SIMPLE_MODES = frozenset({'0', 'off', 'false', 'no', 'simple', 'oneshot', 'single'})
_COMPLEX_MODES = frozenset({'1', 'on', 'true', 'yes', 'complex', 'force', 'accel', 'daemon'})

# Bilingual intent patterns for explicit user instructions.
_SIMPLE_HINT_RE = re.compile(
    r'(?:'
    r'简单任务|简单测|只跑一个|只看一张|只测一个|仅这一个|单次|单个分子|不用提速|不提速|不要常驻|轻量模式'
    r'|\bsimple\s+task\b|\bone[- ]off\b|\bsingle\s+(?:check|molecule|image|run|call)\b'
    r'|\bjust\s+one\b|\bonly\s+one\b|\bquick\s+check\b|\bno\s+accel(?:eration)?\b'
    r')',
    re.IGNORECASE,
)

_COMPLEX_HINT_RE = re.compile(
    r'(?:'
    r'复杂任务|批量|整篇|全套|多步|底物拓展|构效|孔板|96\s*孔|对比多个|多分子|路线规划|高通量|加速模式'
    r'|\bbatch\b|\bcomplex\s+task\b|\bmulti[- ]step\b|\bwhole\s+(?:paper|pdf|document)\b'
    r'|\bbenchmark\b|\blibrary\b|\bplate\b|\bsubstrate\s+scope\b|\bseries\b'
    r')',
    re.IGNORECASE,
)


@dataclasses.dataclass(frozen=True)
class AccelDecision:
    """Result of evaluating whether an engine invocation warrants acceleration."""

    tier: str          # 'simple' | 'complex'
    accelerate: bool   # True when complex-task acceleration is active
    use_daemon: bool   # True when an in-process resident worker should be used/warmed
    score: int         # heuristic score (>= COMPLEXITY_THRESHOLD => complex)
    reasons: tuple[str, ...]

    @property
    def primary_reason(self) -> str:
        return self.reasons[0] if self.reasons else 'default_oneshot'

    def to_dict(self, execution_mode: str = 'oneshot') -> dict[str, Any]:
        return {
            'tier': self.tier,
            'accelerate': self.accelerate,
            'use_daemon': self.use_daemon,
            'mode': execution_mode,
            'score': self.score,
            'reason': self.primary_reason,
            'reasons': list(self.reasons),
        }


def _history_path(engine_home: Path) -> Path:
    return engine_home / '.locks' / 'recent_calls.json'


def _daemons_dir(engine_home: Path) -> Path:
    return engine_home / '.locks' / 'daemons'


def _daemon_state_path(engine_home: Path, engine: str, device: str) -> Path:
    safe_dev = 'cpu' if device == 'cpu' else 'default'
    return _daemons_dir(engine_home) / f'{engine}.{safe_dev}.json'


def recent_call_count(engine_home: Path | None, *, window_seconds: float = BURST_WINDOW_SECONDS,
                      now: float | None = None) -> int:
    """Count recent engine calls within ``window_seconds`` (stores timestamps and engine names only)."""
    if engine_home is None:
        return 0
    path = _history_path(engine_home)
    if not path.is_file():
        return 0
    current = time.time() if now is None else now
    try:
        entries = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return 0
    if not isinstance(entries, list):
        return 0
    cutoff = current - window_seconds
    return sum(1 for item in entries if isinstance(item, dict) and float(item.get('ts', 0.0)) >= cutoff)


def record_call(engine_home: Path | None, engine: str, *, now: float | None = None) -> None:
    """Append a lightweight timestamp entry (never molecular content) to the burst ring buffer."""
    if engine_home is None:
        return
    current = time.time() if now is None else now
    path = _history_path(engine_home)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        existing = []
        if path.is_file():
            try:
                loaded = json.loads(path.read_text(encoding='utf-8'))
                if isinstance(loaded, list):
                    existing = [x for x in loaded if isinstance(x, dict) and current - float(x.get('ts', 0.0)) <= 600]
            except (OSError, ValueError):
                existing = []
        existing.append({'ts': round(current, 3), 'engine': engine})
        existing = existing[-16:]
        path.write_text(json.dumps(existing), encoding='utf-8')
    except OSError:
        pass


def _batch_item_count(params: dict[str, Any] | None) -> int:
    if not isinstance(params, dict):
        return 1
    for key in ('images', 'inputs', 'smiles_list', 'reactions', 'targets'):
        val = params.get(key)
        if isinstance(val, (list, tuple)):
            return len(val)
    return 1


def classify_task(
    engine: str,
    action: str = 'predict',
    params: dict[str, Any] | None = None,
    *,
    mode: str | None = None,
    task_hint: str | None = None,
    engine_home: Path | None = None,
    now: float | None = None,
) -> AccelDecision:
    """Classify an engine invocation as ``simple`` (stateless one-shot) or ``complex`` (accelerated).

    Precedence:
    1. Non-prediction actions (``fetch``) always stay one-shot.
    2. Explicit mode override (``mode`` argument or ``CHEMDRAW_ACCEL``).
    3. Explicit user simple-task intent in ``task_hint`` or ``CHEMDRAW_TASK_HINT`` always wins and
       forces stateless ``simple`` execution (zero resident background processes).
    4. Heuristic feature scoring across user complex-task hints, batch size, multi-step search,
       multi-nucleus workloads, and temporal burst session history.
    """
    if action != 'predict':
        return AccelDecision('simple', False, False, 0, ('non_predict_action',))

    raw_mode = (mode if mode is not None else os.environ.get('CHEMDRAW_ACCEL', '')).strip().lower()
    if raw_mode in _SIMPLE_MODES:
        return AccelDecision('simple', False, False, 0, ('explicit_simple_mode',))

    hint_parts = [
        task_hint or '',
        str((params or {}).get('task_hint') or ''),
        os.environ.get('CHEMDRAW_TASK_HINT', ''),
    ]
    combined_hint = ' '.join(part.strip() for part in hint_parts if part and part.strip())

    # User explicitly stating this is a simple / single one-off task strictly disables acceleration
    # unless raw_mode explicitly forced acceleration ('on' / 'force').
    if combined_hint and _SIMPLE_HINT_RE.search(combined_hint) and raw_mode not in _COMPLEX_MODES:
        return AccelDecision('simple', False, False, 0, ('user_indicated_simple_task',))

    if raw_mode in _COMPLEX_MODES:
        can_daemon = engine in DAEMON_CAPABLE_ENGINES
        return AccelDecision('complex', True, can_daemon, 10, ('explicit_complex_mode',))

    score = 0
    reasons: list[str] = []

    if combined_hint and _COMPLEX_HINT_RE.search(combined_hint):
        score += 4
        reasons.append('user_indicated_complex_task')

    n_items = _batch_item_count(params)
    if n_items >= 2:
        score += 3 if n_items < 8 else 5
        reasons.append(f'batch_items_{n_items}')

    if isinstance(params, dict):
        if params.get('steps') == 'multi':
            score += 2
            reasons.append('multi_step_search')
        if params.get('nucleus') == 'both':
            score += 1
            reasons.append('dual_nucleus_nmr')
        engines_arg = params.get('engines') or ''
        if isinstance(engines_arg, str) and (',' in engines_arg or engines_arg.strip() == 'all'):
            score += 2
            reasons.append('multi_engine_comparison')

    recent = recent_call_count(engine_home, now=now)
    if recent >= 1:
        score += 3
        reasons.append(f'burst_session_{recent}_recent_calls')

    if score >= COMPLEXITY_THRESHOLD:
        can_daemon = engine in DAEMON_CAPABLE_ENGINES
        return AccelDecision('complex', True, can_daemon, score, tuple(reasons or ('score_threshold',)))

    return AccelDecision('simple', False, False, score, tuple(reasons or ('single_item_cold_call',)))


def idle_timeout_seconds() -> int:
    raw = os.environ.get('CHEMDRAW_ACCEL_IDLE', '').strip()
    if raw:
        try:
            return max(5, min(3600, int(raw)))
        except ValueError:
            pass
    return DEFAULT_IDLE_SECONDS


def _rpc(port: int, payload: dict[str, Any], timeout: float) -> dict[str, Any] | None:
    data = (json.dumps(payload) + '\n').encode('utf-8')
    try:
        with socket.create_connection(('127.0.0.1', port), timeout=min(timeout, 5.0)) as sock:
            sock.settimeout(timeout)
            sock.sendall(data)
            chunks: list[bytes] = []
            while True:
                chunk = sock.recv(65536)
                if not chunk:
                    break
                chunks.append(chunk)
                if b'\n' in chunk:
                    break
        raw = b''.join(chunks).decode('utf-8', errors='replace').strip()
        if not raw:
            return None
        return json.loads(raw.splitlines()[-1])
    except (OSError, ValueError):
        return None


def _ping_daemon(state_file: Path) -> dict[str, Any] | None:
    try:
        info = json.loads(state_file.read_text(encoding='utf-8'))
        port = int(info['port'])
        token = str(info['token'])
    except (OSError, ValueError, KeyError, TypeError):
        state_file.unlink(missing_ok=True)
        return None
    reply = _rpc(port, {'token': token, 'cmd': 'ping'}, timeout=1.5)
    if not reply or not reply.get('ok'):
        state_file.unlink(missing_ok=True)
        return None
    return info


def stop_daemon_file(state_file: Path) -> bool:
    existed = state_file.exists()
    rpc_ok = False
    try:
        info = json.loads(state_file.read_text(encoding='utf-8'))
        reply = _rpc(int(info['port']), {'token': str(info['token']), 'cmd': 'shutdown'}, timeout=2.0)
        rpc_ok = bool(reply and reply.get('ok'))
    except (OSError, ValueError, KeyError, TypeError):
        pass
    for _ in range(5):
        try:
            state_file.unlink(missing_ok=True)
            return existed or rpc_ok
        except OSError:
            time.sleep(0.03)
    return rpc_ok or not state_file.exists()


def stop_all_daemons(engine_home: Path) -> list[str]:
    """Shut down all warm resident engine daemons under ``engine_home`` and return their names."""
    folder = _daemons_dir(engine_home)
    if not folder.is_dir():
        return []
    stopped: list[str] = []
    for state_file in sorted(folder.glob('*.json')):
        name = state_file.stem
        if stop_daemon_file(state_file):
            stopped.append(name)
    return stopped


def active_daemons(engine_home: Path) -> list[dict[str, Any]]:
    """Return metadata of currently live resident daemons (pruning stale state files)."""
    folder = _daemons_dir(engine_home)
    if not folder.is_dir():
        return []
    live: list[dict[str, Any]] = []
    for state_file in sorted(folder.glob('*.json')):
        info = _ping_daemon(state_file)
        if info is not None:
            live.append({
                'engine': info.get('engine'),
                'device': info.get('device'),
                'pid': info.get('pid'),
                'started_at': info.get('started_at'),
                'last_used_at': info.get('last_used_at'),
                'state_file': state_file,
            })
    return live


def _enforce_lru_cap(engine_home: Path, keep_state: Path) -> None:
    live = [d for d in active_daemons(engine_home) if d['state_file'] != keep_state]
    if len(live) < MAX_RESIDENT_DAEMONS:
        return
    live.sort(key=lambda d: float(d.get('last_used_at') or d.get('started_at') or 0.0))
    while len(live) >= MAX_RESIDENT_DAEMONS:
        oldest = live.pop(0)
        stop_daemon_file(oldest['state_file'])


def call_via_daemon(
    *,
    engine: str,
    python: Path,
    worker_script: Path,
    request: dict[str, Any],
    env_vars: dict[str, str],
    engine_home: Path,
    device_key: str,
    timeout: int,
) -> tuple[dict[str, Any], str] | None:
    """Execute ``request`` on a warm resident worker, spawning one if needed.

    Returns ``(payload, 'daemon_hit' | 'daemon_warm')`` when handled by the daemon, or ``None`` if
    the daemon could not start/respond so the caller can fall back to one-shot subprocess execution.
    """
    folder = _daemons_dir(engine_home)
    try:
        folder.mkdir(parents=True, exist_ok=True)
    except OSError:
        return None

    state_file = _daemon_state_path(engine_home, engine, device_key)
    info = _ping_daemon(state_file)
    mode = 'daemon_hit'

    if info is None:
        mode = 'daemon_warm'
        _enforce_lru_cap(engine_home, state_file)
        token = secrets.token_hex(32)
        idle = idle_timeout_seconds()
        cmd = [
            str(python), '-W', 'ignore', str(worker_script),
            '--daemon',
            '--state-file', str(state_file),
            '--idle-seconds', str(idle),
            '--engine-name', engine,
        ]
        daemon_env = dict(env_vars, CHEMDRAW_DAEMON_TOKEN=token)
        creationflags = 0
        if os.name == 'nt':
            creationflags = getattr(subprocess, 'CREATE_NO_WINDOW', 0) | getattr(subprocess, 'CREATE_NEW_PROCESS_GROUP', 0)
        try:
            proc = subprocess.Popen(
                cmd,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                env=daemon_env,
                start_new_session=(os.name != 'nt'),
                creationflags=creationflags,
            )
        except OSError:
            return None

        deadline = time.time() + 25.0
        while time.time() < deadline:
            if state_file.is_file():
                info = _ping_daemon(state_file)
                if info is not None:
                    break
            if proc.poll() is not None:
                return None
            time.sleep(0.05)
        if info is None:
            try:
                proc.kill()
            except OSError:
                pass
            state_file.unlink(missing_ok=True)
            return None

    reply = _rpc(
        int(info['port']),
        {'token': str(info['token']), 'cmd': 'run', 'request': request},
        timeout=float(timeout),
    )
    if reply is None:
        state_file.unlink(missing_ok=True)
        return None
    try:
        info['last_used_at'] = round(time.time(), 3)
        state_file.write_text(json.dumps(info), encoding='utf-8')
    except OSError:
        pass
    return reply, mode
