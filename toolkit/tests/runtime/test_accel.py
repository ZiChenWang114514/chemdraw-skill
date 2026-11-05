"""Tests for the optional resident engine daemons: when they are used, and how they stay alive."""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

from cdxml_toolkit.engines import accel, env, worker

MOCK_WORKER = '''import argparse, json, os, socket, time
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
        try:
            with conn:
                msg = json.loads(conn.makefile('r', encoding='utf-8').readline())
                if msg.get('token') != token:
                    conn.sendall((json.dumps({'ok': False, 'error': 'unauthorized'}) + chr(10)).encode('utf-8'))
                    continue
                cmd = msg.get('cmd')
                if cmd == 'ping':
                    conn.sendall((json.dumps({'ok': True, 'pid': os.getpid()}) + chr(10)).encode('utf-8'))
                elif cmd == 'shutdown':
                    conn.sendall((json.dumps({'ok': True}) + chr(10)).encode('utf-8'))
                    break
                elif cmd == 'run':
                    calls += 1
                    req = msg['request']
                    time.sleep(float((req.get('params') or {}).get('sleep', 0)))
                    conn.sendall((json.dumps({'ok': True, 'engine': req['engine'], 'device': 'cpu', 'result': {'calls': calls, 'pid': os.getpid()}}) + chr(10)).encode('utf-8'))
        except OSError:
            pass
finally:
    sf.unlink(missing_ok=True)
    srv.close()
'''


@pytest.fixture
def mock_worker(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    script = tmp_path / 'mock_worker.py'
    script.write_text(MOCK_WORKER, encoding='utf-8')
    monkeypatch.setenv('CHEMDRAW_ACCEL_IDLE', '20')
    return script


def _call(engine_home: Path, script: Path, engine: str = 'molscribe', timeout: int = 10, **params):
    return accel.call_via_daemon(
        engine=engine, python=Path(sys.executable), worker_script=script,
        request={'engine': engine, 'action': 'predict', 'params': params},
        env_vars=dict(os.environ), engine_home=engine_home, device_key='cpu', timeout=timeout,
    )


@pytest.mark.parametrize(
    ('engine', 'params', 'mode', 'expected'),
    [
        ('magnet', {'smiles': 'CCO', 'nucleus': '1H'}, None, False),                    # one cold call
        ('molscribe', {'images': ['1.png']}, None, False),
        ('decimer-local', {'images': ['1.png', '2.png', '3.png']}, None, True),         # batch
        ('aizynthfinder', {'smiles': 'CCO', 'steps': 'multi'}, None, True),             # multi-step search
        ('magnet', {'smiles': 'CCO', 'nucleus': 'both'}, None, True),                   # two spectra, one model
        ('retrochimera', {'smiles': 'CCO', 'steps': 'multi'}, None, False),             # too heavy to keep resident
        ('molscribe', {'images': ['1.png', '2.png']}, 'off', False),
        ('molscribe', {'images': ['1.png']}, 'on', True),
        ('retrochimera', {'smiles': 'CCO'}, 'on', False),
    ],
)
def test_wants_daemon_for_batches_multistep_and_explicit_mode(engine, params, mode, expected, monkeypatch):
    monkeypatch.delenv('CHEMDRAW_ACCEL', raising=False)
    assert accel.wants_daemon(engine, 'predict', params, mode=mode) is expected


def test_fetch_never_uses_a_daemon_and_env_var_selects_the_mode(monkeypatch):
    monkeypatch.setenv('CHEMDRAW_ACCEL', 'on')
    assert accel.wants_daemon('molscribe', 'fetch', {}) is False
    assert accel.wants_daemon('molscribe', 'predict', {}) is True
    monkeypatch.setenv('CHEMDRAW_ACCEL', 'off')
    assert accel.wants_daemon('molscribe', 'predict', {'images': ['a', 'b']}) is False
    assert not hasattr(accel, 'classify_task')


def test_resident_daemon_lifecycle_warm_hit_lru_and_stop(tmp_path: Path, mock_worker: Path):
    payload1, mode1 = _call(tmp_path, mock_worker)
    assert mode1 == 'daemon_warm'
    assert payload1['result']['calls'] == 1
    payload2, mode2 = _call(tmp_path, mock_worker)
    assert mode2 == 'daemon_hit'
    assert payload2['result'] == {'calls': 2, 'pid': payload1['result']['pid']}

    # A third and fourth engine evict the least recently used worker (MAX_RESIDENT_DAEMONS = 2).
    time.sleep(0.05)
    _call(tmp_path, mock_worker, engine='magnet')
    time.sleep(0.05)
    _call(tmp_path, mock_worker, engine='reactiont5-forward')
    assert {d['engine'] for d in accel.active_daemons(tmp_path)} == {'magnet', 'reactiont5-forward'}

    assert len(accel.stop_all_daemons(tmp_path)) == 2
    assert accel.active_daemons(tmp_path) == []


def test_busy_daemon_is_neither_deleted_nor_duplicated(tmp_path: Path, mock_worker: Path, monkeypatch):
    monkeypatch.setattr(accel, 'PING_TIMEOUT_SECONDS', 0.3)
    first, _ = _call(tmp_path, mock_worker)
    state = accel.daemon_state_path(tmp_path, 'molscribe', 'cpu')
    before = state.read_text(encoding='utf-8')

    slow: dict = {}
    thread = threading.Thread(target=lambda: slow.update(r=_call(tmp_path, mock_worker, sleep=2.0)))
    thread.start()
    time.sleep(0.5)  # the worker is inside its 2 s request: single-threaded, so it cannot answer a ping

    assert _call(tmp_path, mock_worker) is None            # the caller falls back to a one-shot
    assert state.is_file() and json.loads(before)['pid'] == json.loads(state.read_text(encoding='utf-8'))['pid']
    assert [d['busy'] for d in accel.active_daemons(tmp_path)] == [True]
    assert len(list(state.parent.glob('*.json'))) == 1       # no second worker was spawned

    thread.join()
    assert slow['r'][1] == 'daemon_hit'
    again, mode = _call(tmp_path, mock_worker)
    assert mode == 'daemon_hit' and again['result']['pid'] == first['result']['pid']
    accel.stop_all_daemons(tmp_path)


def test_run_timeout_keeps_the_worker_and_raises(tmp_path: Path, mock_worker: Path):
    first, _ = _call(tmp_path, mock_worker)
    state = accel.daemon_state_path(tmp_path, 'molscribe', 'cpu')
    with pytest.raises(accel.DaemonTimeout):
        _call(tmp_path, mock_worker, timeout=1, sleep=3.0)
    assert state.is_file()
    time.sleep(2.5)
    again, mode = _call(tmp_path, mock_worker)
    assert mode == 'daemon_hit' and again['result']['pid'] == first['result']['pid']
    accel.stop_all_daemons(tmp_path)


def _dead_pid() -> int:
    process = subprocess.Popen([sys.executable, '-c', 'pass'])
    process.wait()
    return process.pid


def test_dead_daemon_state_is_removed_and_replaced(tmp_path: Path, mock_worker: Path):
    state = accel.daemon_state_path(tmp_path, 'molscribe', 'cpu')
    state.parent.mkdir(parents=True)
    with socket.socket() as probe:  # a port nobody listens on
        probe.bind(('127.0.0.1', 0))
        dead_port = probe.getsockname()[1]
    state.write_text(json.dumps({'engine': 'molscribe', 'port': dead_port, 'token': 'x', 'pid': 1}), encoding='utf-8')
    assert accel.probe_daemon(state) == ('gone', None)
    assert not state.exists()

    state.write_text(json.dumps({'engine': 'molscribe', 'port': dead_port, 'token': 'x', 'pid': 1}), encoding='utf-8')
    payload, mode = _call(tmp_path, mock_worker)
    assert mode == 'daemon_warm' and payload['ok']
    accel.stop_all_daemons(tmp_path)


def test_real_worker_survives_silent_and_vanished_clients(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """The worker's accepted sockets time out, and a client that gave up cannot crash its loop."""
    monkeypatch.setattr(worker, 'CONN_IO_TIMEOUT', 0.3)
    monkeypatch.setattr(sys, 'stdout', sys.stdout)  # _serve_daemon rebinds stdout; monkeypatch restores it
    monkeypatch.setenv('CHEMDRAW_DAEMON_TOKEN', 'tok')
    state = tmp_path / 'd.json'
    thread = threading.Thread(target=worker._serve_daemon, args=([
        '--daemon', '--state-file', str(state), '--idle-seconds', '5', '--engine-name', 'aizynthfinder'],), daemon=True)
    thread.start()
    deadline = time.time() + 5
    while not state.is_file() and time.time() < deadline:
        time.sleep(0.02)
    port = json.loads(state.read_text(encoding='utf-8'))['port']

    silent = socket.create_connection(('127.0.0.1', port))  # connects, never sends
    started = time.time()
    assert accel._rpc(port, {'token': 'tok', 'cmd': 'ping'}, timeout=5.0)['ok'] is True
    assert time.time() - started < 3.0                      # not stuck behind the silent client for the idle period
    silent.close()

    gone = socket.create_connection(('127.0.0.1', port))    # sends a ping and leaves before the reply
    gone.sendall(b'{"token": "tok", "cmd": "ping"}\n')
    gone.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, b'\x01\x00\x00\x00\x00\x00\x00\x00')  # reset on close
    gone.close()
    assert accel._rpc(port, {'token': 'tok', 'cmd': 'ping'}, timeout=5.0)['ok'] is True
    assert thread.is_alive()
    assert accel._rpc(port, {'token': 'tok', 'cmd': 'shutdown'}, timeout=5.0)['ok'] is True
    thread.join(5)
    assert not thread.is_alive() and not state.exists()


def _fake_engine_install(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('CHEMDRAW_ENGINE_HOME', str(tmp_path))
    eng_dir = tmp_path / 'molscribe'
    py_dir = eng_dir / 'bin'
    py_dir.mkdir(parents=True)
    (py_dir / 'python3').write_text('', encoding='utf-8')
    (eng_dir / 'pyvenv.cfg').write_text('home = /usr/bin\n', encoding='utf-8')
    (eng_dir / env.RECEIPT).write_text(json.dumps({'device': 'cuda'}), encoding='utf-8')
    monkeypatch.setattr(env, '_run', lambda cmd, **kw: subprocess.CompletedProcess(
        cmd, 0, env.MARKER + json.dumps({'ok': True, 'engine': 'molscribe', 'device': 'cuda',
                                         'result': [{'smiles': 'CCO'}]}), ''))


def test_env_call_reports_only_the_device_and_uses_a_daemon_when_asked(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    from cdxml_toolkit.engines import __main__ as cli

    _fake_engine_install(tmp_path, monkeypatch)
    used: list = []
    monkeypatch.setattr(accel, 'call_via_daemon', lambda **kw: used.append(kw['engine']) or (
        {'ok': True, 'device': 'cuda', 'result': [{'smiles': 'CCO'}]}, 'daemon_hit'))

    monkeypatch.setenv('CHEMDRAW_ACCEL', 'off')
    env.call('molscribe', 'predict', {'images': ['a.png', 'b.png', 'c.png']})
    assert used == []                                         # off wins over a batch
    assert env.last_call_meta('molscribe') == {'device': 'cuda', 'device_fallback': False}

    monkeypatch.setenv('CHEMDRAW_ACCEL', 'auto')
    env.call('molscribe', 'predict', {'images': ['a.png']})
    assert used == []                                         # one cold call stays one-shot
    assert env.call('molscribe', 'predict', {'images': ['a.png', 'b.png']}) == [{'smiles': 'CCO'}]
    assert used == ['molscribe']                              # a batch reuses a resident worker
    assert env.last_call_meta('molscribe') == {'device': 'cuda', 'device_fallback': False}
    assert not hasattr(env, 'last_accel_meta')

    assert cli.main(['--stop-daemons']) == 0


def test_busy_daemon_falls_back_to_a_one_shot_call(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    _fake_engine_install(tmp_path, monkeypatch)
    monkeypatch.setenv('CHEMDRAW_ACCEL', 'on')
    monkeypatch.setattr(accel, 'call_via_daemon', lambda **kw: None)
    assert env.call('molscribe', 'predict', {'images': ['a.png']}) == [{'smiles': 'CCO'}]

    def timed_out(**kw):
        raise accel.DaemonTimeout('slow')
    monkeypatch.setattr(accel, 'call_via_daemon', timed_out)
    with pytest.raises(env.EngineError, match='did not finish within'):
        env.call('molscribe', 'predict', {'images': ['a.png']}, timeout=7)
