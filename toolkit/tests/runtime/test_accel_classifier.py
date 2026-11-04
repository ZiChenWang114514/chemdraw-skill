"""Tests for the adaptive task-complexity classifier and resident engine daemon pool."""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import pytest

from cdxml_toolkit.engines import accel


def test_single_cold_call_classified_as_simple_oneshot(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv('CHEMDRAW_ACCEL', raising=False)
    monkeypatch.delenv('CHEMDRAW_TASK_HINT', raising=False)

    decision = accel.classify_task(
        'magnet',
        'predict',
        {'smiles': 'Cn1cnc2c1c(=O)n(C)c(=O)n2C', 'nucleus': '1H'},
        engine_home=tmp_path,
    )
    assert decision.tier == 'simple'
    assert decision.accelerate is False
    assert decision.use_daemon is False
    assert decision.primary_reason == 'single_item_cold_call'


@pytest.mark.parametrize(
    'hint',
    [
        '这是一个简单任务，只测这一个分子',
        '只看一张结构图，不用提速',
        'Just one quick check on aspirin',
        'simple task, single molecule only',
        'one-off NMR check',
    ],
)
def test_explicit_user_simple_intent_overrides_batch_and_burst(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, hint: str):
    monkeypatch.delenv('CHEMDRAW_ACCEL', raising=False)
    monkeypatch.delenv('CHEMDRAW_TASK_HINT', raising=False)
    # Even if recent burst calls exist AND batch items are passed, user's explicit simple intent wins!
    accel.record_call(tmp_path, 'molscribe', now=1000.0)
    accel.record_call(tmp_path, 'molscribe', now=1010.0)

    decision = accel.classify_task(
        'molscribe',
        'predict',
        {'images': ['a.png', 'b.png', 'c.png']},
        task_hint=hint,
        engine_home=tmp_path,
        now=1015.0,
    )
    assert decision.tier == 'simple'
    assert decision.accelerate is False
    assert decision.use_daemon is False
    assert decision.primary_reason == 'user_indicated_simple_task'


@pytest.mark.parametrize(
    'hint',
    [
        '批量提取整篇文献PDF里的所有分子并对比多个引擎',
        '96孔板高通量筛选结果核对',
        'Run a multi-step substrate scope batch evaluation',
        'whole paper extraction benchmark',
    ],
)
def test_explicit_complex_hint_activates_acceleration(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, hint: str):
    monkeypatch.delenv('CHEMDRAW_ACCEL', raising=False)
    decision = accel.classify_task(
        'molscribe',
        'predict',
        {'images': ['crop1.png']},
        task_hint=hint,
        engine_home=tmp_path,
    )
    assert decision.tier == 'complex'
    assert decision.accelerate is True
    assert decision.use_daemon is True
    assert decision.primary_reason == 'user_indicated_complex_task'


def test_batch_payload_and_multi_step_classify_as_complex(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv('CHEMDRAW_ACCEL', raising=False)
    batch_dec = accel.classify_task(
        'decimer-local',
        'predict',
        {'images': ['1.png', '2.png', '3.png']},
        engine_home=tmp_path,
    )
    assert batch_dec.tier == 'complex'
    assert batch_dec.accelerate is True
    assert batch_dec.use_daemon is True
    assert 'batch_items_3' in batch_dec.reasons

    retro_dec = accel.classify_task(
        'aizynthfinder',
        'predict',
        {'smiles': 'CC(=O)Oc1ccccc1C(=O)O', 'steps': 'multi'},
        engine_home=tmp_path,
    )
    assert retro_dec.tier == 'complex'
    assert retro_dec.accelerate is True
    assert retro_dec.use_daemon is True
    assert 'multi_step_search' in retro_dec.reasons


def test_temporal_burst_promotes_second_call_to_complex(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv('CHEMDRAW_ACCEL', raising=False)
    t0 = 5000.0
    first = accel.classify_task('magnet', 'predict', {'smiles': 'CCO'}, engine_home=tmp_path, now=t0)
    assert first.tier == 'simple'
    accel.record_call(tmp_path, 'magnet', now=t0)

    second = accel.classify_task('magnet', 'predict', {'smiles': 'CCCO'}, engine_home=tmp_path, now=t0 + 20.0)
    assert second.tier == 'complex'
    assert second.accelerate is True
    assert second.use_daemon is True
    assert any(r.startswith('burst_session_') for r in second.reasons)

    # After the burst window expires (>180s), a single call returns to simple mode.
    later = accel.classify_task('magnet', 'predict', {'smiles': 'CCCCO'}, engine_home=tmp_path, now=t0 + 300.0)
    assert later.tier == 'simple'
    assert later.accelerate is False


def test_heavy_memory_engine_disables_resident_daemon_even_when_complex(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv('CHEMDRAW_ACCEL', raising=False)
    decision = accel.classify_task(
        'retrochimera',
        'predict',
        {'smiles': 'CC(=O)Nc1ccc(O)cc1', 'steps': 'multi'},
        engine_home=tmp_path,
    )
    assert decision.tier == 'complex'
    assert decision.accelerate is True
    assert decision.use_daemon is False


def test_env_mode_overrides(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv('CHEMDRAW_ACCEL', 'off')
    off_dec = accel.classify_task('molscribe', 'predict', {'images': ['1.png', '2.png']}, engine_home=tmp_path)
    assert off_dec.tier == 'simple'
    assert off_dec.accelerate is False
    assert off_dec.primary_reason == 'explicit_simple_mode'

    monkeypatch.setenv('CHEMDRAW_ACCEL', 'on')
    on_dec = accel.classify_task('molscribe', 'predict', {'images': ['1.png']}, engine_home=tmp_path)
    assert on_dec.tier == 'complex'
    assert on_dec.accelerate is True
    assert on_dec.use_daemon is True
    assert on_dec.primary_reason == 'explicit_complex_mode'


def test_resident_daemon_lifecycle_warm_hit_lru_and_stop(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Spawn a tiny mock worker supporting --daemon to test warm start, cache hit, LRU cap, and shutdown."""
    mock_worker = tmp_path / 'mock_worker.py'
    mock_worker.write_text(
        """import argparse, json, os, socket, time
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument('--daemon', action='store_true')
p.add_argument('--state-file', required=True)
p.add_argument('--idle-seconds', type=int, default=30)
p.add_argument('--engine-name', required=True)
ns = p.parse_args()
token = os.environ['CHEMDRAW_DAEMON_TOKEN']

srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
srv.bind(('127.0.0.1', 0))
srv.listen(8)
port = srv.getsockname()[1]
srv.settimeout(float(ns.idle_seconds))

sf = Path(ns.state_file)
sf.parent.mkdir(parents=True, exist_ok=True)
now = round(time.time(), 3)
sf.write_text(json.dumps({'engine': ns.engine_name, 'device': 'cpu', 'pid': os.getpid(), 'port': port, 'token': token, 'started_at': now, 'last_used_at': now}), encoding='utf-8')

calls = 0
try:
    while True:
        try:
            conn, _ = srv.accept()
        except socket.timeout:
            break
        with conn:
            msg = json.loads(conn.makefile('r', encoding='utf-8').readline())
            if msg.get('token') != token:
                conn.sendall((json.dumps({'ok': False, 'error': 'unauthorized'}) + '\\n').encode('utf-8'))
                continue
            cmd = msg.get('cmd')
            if cmd == 'ping':
                conn.sendall((json.dumps({'ok': True, 'pid': os.getpid()}) + '\\n').encode('utf-8'))
            elif cmd == 'shutdown':
                conn.sendall((json.dumps({'ok': True}) + '\\n').encode('utf-8'))
                break
            elif cmd == 'run':
                calls += 1
                req = msg['request']
                conn.sendall((json.dumps({'ok': True, 'engine': req['engine'], 'device': 'cpu', 'result': {'calls': calls, 'pid': os.getpid()}}) + '\\n').encode('utf-8'))
finally:
    sf.unlink(missing_ok=True)
    srv.close()
""",
        encoding='utf-8',
    )

    monkeypatch.setenv('CHEMDRAW_ACCEL_IDLE', '20')
    py = Path(sys.executable)
    env_vars = dict(os.environ)

    res1 = accel.call_via_daemon(
        engine='molscribe',
        python=py,
        worker_script=mock_worker,
        request={'engine': 'molscribe', 'action': 'predict', 'params': {}},
        env_vars=env_vars,
        engine_home=tmp_path,
        device_key='cpu',
        timeout=10,
    )
    assert res1 is not None
    payload1, mode1 = res1
    assert mode1 == 'daemon_warm'
    assert payload1['result']['calls'] == 1
    pid1 = payload1['result']['pid']

    # Second call reuses the exact same warm daemon process!
    res2 = accel.call_via_daemon(
        engine='molscribe',
        python=py,
        worker_script=mock_worker,
        request={'engine': 'molscribe', 'action': 'predict', 'params': {}},
        env_vars=env_vars,
        engine_home=tmp_path,
        device_key='cpu',
        timeout=10,
    )
    assert res2 is not None
    payload2, mode2 = res2
    assert mode2 == 'daemon_hit'
    assert payload2['result']['calls'] == 2
    assert payload2['result']['pid'] == pid1

    # Spawning two more distinct engines triggers LRU eviction of the oldest ('molscribe') at MAX_RESIDENT_DAEMONS=2.
    time.sleep(0.05)
    accel.call_via_daemon(
        engine='magnet', python=py, worker_script=mock_worker,
        request={'engine': 'magnet', 'action': 'predict', 'params': {}},
        env_vars=env_vars, engine_home=tmp_path, device_key='cpu', timeout=10,
    )
    time.sleep(0.05)
    accel.call_via_daemon(
        engine='reactiont5-forward', python=py, worker_script=mock_worker,
        request={'engine': 'reactiont5-forward', 'action': 'predict', 'params': {}},
        env_vars=env_vars, engine_home=tmp_path, device_key='cpu', timeout=10,
    )

    live_engines = {d['engine'] for d in accel.active_daemons(tmp_path)}
    assert live_engines == {'magnet', 'reactiont5-forward'}

    stopped = accel.stop_all_daemons(tmp_path)
    assert len(stopped) == 2
    assert accel.active_daemons(tmp_path) == []


def test_env_call_records_accel_meta_and_cli_stop_daemons(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys):
    from cdxml_toolkit.engines import __main__ as cli
    from cdxml_toolkit.engines import env
    import subprocess

    monkeypatch.setenv('CHEMDRAW_ENGINE_HOME', str(tmp_path))
    eng_dir = tmp_path / 'molscribe'
    py_dir = eng_dir / 'bin'
    py_dir.mkdir(parents=True)
    (py_dir / 'python3').write_text('', encoding='utf-8')
    (eng_dir / 'pyvenv.cfg').write_text('home = /usr/bin\n', encoding='utf-8')
    (eng_dir / env.RECEIPT).write_text(json.dumps({'device': 'cuda'}), encoding='utf-8')

    monkeypatch.setattr(
        env,
        '_run',
        lambda cmd, **kw: subprocess.CompletedProcess(
            cmd, 0, env.MARKER + json.dumps({'ok': True, 'engine': 'molscribe', 'device': 'cuda', 'result': [{'smiles': 'CCO'}]}), ''
        ),
    )

    monkeypatch.setenv('CHEMDRAW_TASK_HINT', '这是一个简单任务')
    env.call('molscribe', 'predict', {'images': ['a.png', 'b.png', 'c.png']})
    assert env.last_call_meta('molscribe') == {'device': 'cuda', 'device_fallback': False}
    meta_simple = env.last_accel_meta('molscribe')
    assert meta_simple is not None
    assert meta_simple['tier'] == 'simple'
    assert meta_simple['reason'] == 'user_indicated_simple_task'
    assert meta_simple['mode'] == 'oneshot'

    monkeypatch.setenv('CHEMDRAW_TASK_HINT', '批量识别整篇PDF')
    env.call('molscribe', 'predict', {'images': ['a.png', 'b.png', 'c.png']})
    meta_complex = env.last_accel_meta('molscribe')
    assert meta_complex is not None
    assert meta_complex['tier'] == 'complex'
    assert meta_complex['accelerate'] is True

    assert cli.main(['--stop-daemons']) == 0
    out = json.loads(capsys.readouterr().out)
    assert out['stopped_daemons'] == []
