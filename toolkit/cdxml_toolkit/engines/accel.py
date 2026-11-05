"""Resident worker pool for prediction engines: reuse a warm model across calls.

``CHEMDRAW_ACCEL`` (``cdx.py ... --accel``) is ``auto`` (default), ``on`` or ``off``.

- ``off``: every call is a clean one-shot subprocess; nothing stays resident.
- ``auto``: a batch of items, a multi-step search or a both-nuclei NMR run reuses a loopback-only,
  token-authenticated resident worker with an idle TTL and an LRU cap (``MAX_RESIDENT_DAEMONS``);
  every other call is a one-shot.
- ``on``: use the resident worker for every call of an engine that can run in one.

A worker handles one request at a time. A caller that finds it busy runs its own one-shot instead and never
touches the worker's state file; the state file is removed only when the worker is gone.
"""

from __future__ import annotations

import json
import os
import secrets
import signal
import socket
import subprocess
import time
from pathlib import Path
from typing import Any

DEFAULT_IDLE_SECONDS = 180
MAX_RESIDENT_DAEMONS = 2
PING_TIMEOUT_SECONDS = 1.5

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

_OFF = frozenset({'0', 'off', 'false', 'no'})
_ON = frozenset({'1', 'on', 'true', 'yes'})


def accel_mode(mode: str | None = None) -> str:
    """``'auto'``, ``'on'`` or ``'off'`` from ``mode`` or ``CHEMDRAW_ACCEL``."""
    raw = (mode if mode is not None else os.environ.get('CHEMDRAW_ACCEL', '')).strip().lower()
    return 'off' if raw in _OFF else 'on' if raw in _ON else 'auto'


def _batch_item_count(params: dict[str, Any]) -> int:
    for key in ('images', 'inputs', 'smiles_list', 'reactions', 'targets'):
        val = params.get(key)
        if isinstance(val, (list, tuple)):
            return len(val)
    return 1


def wants_daemon(engine: str, action: str = 'predict', params: dict[str, Any] | None = None,
                 *, mode: str | None = None) -> bool:
    """True when this engine call should run on a resident worker."""
    if action != 'predict' or engine not in DAEMON_CAPABLE_ENGINES:
        return False
    chosen = accel_mode(mode)
    if chosen != 'auto':
        return chosen == 'on'
    params = params if isinstance(params, dict) else {}
    return _batch_item_count(params) >= 2 or params.get('steps') == 'multi' or params.get('nucleus') == 'both'


def _daemons_dir(engine_home: Path) -> Path:
    return engine_home / '.locks' / 'daemons'


def daemon_state_path(engine_home: Path, engine: str, device: str) -> Path:
    """The state file of the resident worker for ``engine`` on ``device`` (``'cpu'`` or any other device)."""
    safe_dev = 'cpu' if device == 'cpu' else 'default'
    return _daemons_dir(engine_home) / f'{engine}.{safe_dev}.json'


def idle_timeout_seconds() -> int:
    raw = os.environ.get('CHEMDRAW_ACCEL_IDLE', '').strip()
    if raw:
        try:
            return max(5, min(3600, int(raw)))
        except ValueError:
            pass
    return DEFAULT_IDLE_SECONDS


class DaemonTimeout(TimeoutError):
    """A resident worker accepted a request and did not answer within the caller's timeout."""


def _rpc(port: int, payload: dict[str, Any], timeout: float) -> dict[str, Any] | None:
    """One JSON line to the worker on ``port``; its reply, or None when nothing sensible answers (refused,
    reset, empty or malformed reply). A worker that does not answer in time is busy, not gone: that raises
    ``TimeoutError``."""
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
        return json.loads(raw.splitlines()[-1]) if raw else None
    except TimeoutError:
        raise
    except (OSError, ValueError):
        return None


def _pid_alive(pid: Any) -> bool:
    try:
        pid = int(pid)
    except (TypeError, ValueError):
        return False
    if pid <= 0:
        return False
    if os.name == 'nt':
        import ctypes
        kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
        handle = kernel32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
        if not handle:
            return ctypes.get_last_error() == 5  # access denied: the process exists
        code = ctypes.c_ulong()
        ok = kernel32.GetExitCodeProcess(handle, ctypes.byref(code))
        kernel32.CloseHandle(handle)
        return bool(ok) and code.value == 259  # STILL_ACTIVE
    try:
        os.kill(pid, 0)
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def _read_state(state_file: Path) -> dict[str, Any] | None:
    try:
        info = json.loads(state_file.read_text(encoding='utf-8'))
        int(info['port'])
        str(info['token'])
        return info
    except (OSError, ValueError, KeyError, TypeError):
        return None


def probe_daemon(state_file: Path) -> tuple[str, dict[str, Any] | None]:
    """``('live', info)``, ``('busy', info)`` (the worker is serving a request) or ``('gone', None)``.

    The state file is removed only for a worker that is gone: unreadable state, a refused or reset connection,
    or a reply that is not ours. A busy worker keeps its state file."""
    info = _read_state(state_file)
    if info is None:
        # a worker that is still writing its state file has just started: leave a fresh file alone
        try:
            fresh = time.time() - state_file.stat().st_mtime < 5.0
        except OSError:
            fresh = False
        if not fresh:
            state_file.unlink(missing_ok=True)
        return 'gone', None
    try:
        reply = _rpc(int(info['port']), {'token': str(info['token']), 'cmd': 'ping'}, timeout=PING_TIMEOUT_SECONDS)
    except TimeoutError:  # no answer in time: busy if the process lives (Windows is slow to refuse a dead port)
        if info.get('pid') is None or _pid_alive(info['pid']):
            return 'busy', info
        state_file.unlink(missing_ok=True)
        return 'gone', None
    if not reply or not reply.get('ok'):
        state_file.unlink(missing_ok=True)
        return 'gone', None
    return 'live', info


def _terminate(pid: Any) -> None:
    try:
        os.kill(int(pid), signal.SIGTERM)  # TerminateProcess on Windows
    except (OSError, ValueError, TypeError):
        pass


def stop_daemon_file(state_file: Path) -> bool:
    existed = state_file.exists()
    rpc_ok = False
    info = _read_state(state_file)
    if info is not None:
        try:
            reply = _rpc(int(info['port']), {'token': str(info['token']), 'cmd': 'shutdown'}, timeout=2.0)
            rpc_ok = bool(reply and reply.get('ok'))
        except TimeoutError:  # busy or hung: an explicit stop ends it
            _terminate(info.get('pid'))
            rpc_ok = True
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
    """Resident daemons that are running, idle or busy (stale state files are pruned)."""
    folder = _daemons_dir(engine_home)
    if not folder.is_dir():
        return []
    live: list[dict[str, Any]] = []
    for state_file in sorted(folder.glob('*.json')):
        status, info = probe_daemon(state_file)
        if info is not None:
            live.append({
                'engine': info.get('engine'),
                'device': info.get('device'),
                'pid': info.get('pid'),
                'started_at': info.get('started_at'),
                'last_used_at': info.get('last_used_at'),
                'busy': status == 'busy',
                'state_file': state_file,
            })
    return live


def _enforce_lru_cap(engine_home: Path, keep_state: Path) -> None:
    live = [d for d in active_daemons(engine_home) if d['state_file'] != keep_state]
    if len(live) < MAX_RESIDENT_DAEMONS:
        return
    live.sort(key=lambda d: (d['busy'], float(d.get('last_used_at') or d.get('started_at') or 0.0)))
    while len(live) >= MAX_RESIDENT_DAEMONS:
        oldest = live.pop(0)
        if oldest['busy']:  # never end a worker that is in the middle of someone's request
            break
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

    Returns ``(payload, 'daemon_hit' | 'daemon_warm')`` when handled by the daemon, or ``None`` if the
    daemon could not start, or is busy with another request, so the caller can fall back to a one-shot
    subprocess. A busy worker's state file is left alone. Raises ``DaemonTimeout`` when the worker took the
    request and did not answer within ``timeout`` seconds (its state file is kept: the worker may still be
    computing; ``stop-daemons`` ends it).
    """
    folder = _daemons_dir(engine_home)
    try:
        folder.mkdir(parents=True, exist_ok=True)
    except OSError:
        return None

    state_file = daemon_state_path(engine_home, engine, device_key)
    status, info = probe_daemon(state_file)
    if status == 'busy':
        return None
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
                status, info = probe_daemon(state_file)
                if status != 'gone':
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

    try:
        reply = _rpc(
            int(info['port']),
            {'token': str(info['token']), 'cmd': 'run', 'request': request},
            timeout=float(timeout),
        )
    except TimeoutError as exc:
        raise DaemonTimeout(f'the resident {engine} worker did not answer within {timeout} s') from exc
    if reply is None:  # the connection broke: the worker died mid-request
        probe_daemon(state_file)  # removes the state file when the worker is gone
        return None
    try:
        info['last_used_at'] = round(time.time(), 3)
        state_file.write_text(json.dumps(info), encoding='utf-8')
    except OSError:
        pass
    return reply, mode
