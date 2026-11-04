"""Engine installs and runs that fail half way: restore, verify, retry, lock, kill, and say what went wrong."""
import json
import os
import re
import subprocess
import sys
import time

import pytest

from cdxml_toolkit.engines import env
from cdxml_toolkit.engines.registry import ENGINES


@pytest.fixture
def home(tmp_path, monkeypatch):
    monkeypatch.setenv('CHEMDRAW_ENGINE_HOME', str(tmp_path))
    monkeypatch.delenv('CHEMDRAW_ENGINE_DEVICE', raising=False)
    monkeypatch.setattr(env, '_nvidia_gpu', lambda: None)
    return tmp_path


def _ready(home, name):
    python = home / name / 'bin' / 'python3'
    python.parent.mkdir(parents=True, exist_ok=True)
    python.write_text('')
    (home / name / 'pyvenv.cfg').write_text('home = /usr/bin\n')
    return python


def _failure(status=1, tail='boom'):
    return subprocess.CalledProcessError(status, ['pip'], stderr=tail)


# --- a CUDA swap that fails leaves the CPU stack, a successful one is verified ---------------------

def _cuda_install(home, monkeypatch, pip, probe, name='magnet'):
    _ready(home, name)
    calls = []

    def fake_pip(python, reqs, log, find_links=None, no_build_isolation=False, index_url=None):
        calls.append({'reqs': list(reqs), 'find_links': find_links, 'index': index_url})
        pip(calls)

    monkeypatch.setattr(env, '_pip', fake_pip)
    monkeypatch.setattr(env, '_nvidia_gpu', lambda: 'RTX')
    monkeypatch.setattr(env, '_has_package', lambda python, package: False)
    monkeypatch.setattr(env, '_torch_probe', probe)
    monkeypatch.setattr(env, 'call', lambda *a, **k: {})
    return env.install(name), calls


def test_a_cuda_step_that_fails_after_the_torch_swap_restores_the_cpu_stack(home, monkeypatch):
    cuda = ENGINES['magnet']['cuda']

    def pip(calls):  # the torch swap works, the compiled extensions for it do not
        if calls[-1]['find_links'] == cuda['find_links']:
            raise _failure()

    report, calls = _cuda_install(home, monkeypatch, pip, lambda python: ('2.5.0', False))
    spec = ENGINES['magnet']
    restore = calls[-2:]
    assert restore[0]['reqs'] == spec['requirements'] and restore[1]['reqs'] == spec['extra_requirements']
    assert all(c['find_links'] == spec['find_links'] and c['index'] is None for c in restore)
    assert report['ok'] and report['device'] == 'cpu' and 'CUDA' in report['gpu_error']
    receipt = json.loads((home / 'magnet' / env.RECEIPT).read_text())
    assert receipt['device'] == 'cpu'


def test_the_install_fails_when_the_cpu_stack_cannot_be_restored_either(home, monkeypatch):
    cuda = ENGINES['magnet']['cuda']
    state = {'swapped': False}

    def pip(calls):
        if calls[-1]['index'] == cuda['index']:
            state['swapped'] = True
        elif state['swapped']:
            raise _failure(tail='no route to host')

    report, _ = _cuda_install(home, monkeypatch, pip, lambda python: ('2.5.0', False))
    assert report['ok'] is False and 'no route to host' in report['error']
    assert not (home / 'magnet' / env.RECEIPT).exists()


def test_the_device_is_what_torch_reports_after_the_swap(home, monkeypatch):
    report, _ = _cuda_install(home, monkeypatch, lambda calls: None, lambda python: ('2.10.0+cu128', False))
    assert report['ok'] and report['device'] == 'cpu' and 'is_available' in report['gpu_error']
    assert json.loads((home / 'magnet' / env.RECEIPT).read_text())['device'] == 'cpu'
    (home / 'magnet' / env.RECEIPT).unlink()
    report, _ = _cuda_install(home, monkeypatch, lambda calls: None, lambda python: ('2.10.0+cu128', True))
    assert report['device'] == 'cuda'


def test_a_torch_that_already_is_the_cuda_build_is_not_downloaded_again(home, monkeypatch):
    cuda = ENGINES['magnet']['cuda']
    target = f'{cuda["torch"]}+{cuda["tag"]}'
    report, calls = _cuda_install(home, monkeypatch, lambda calls: None, lambda python: (target, True))
    assert all(c['index'] != cuda['index'] for c in calls) and report['device'] == 'cuda'
    assert calls[-1]['reqs'] == cuda['requirements']  # the extensions are still checked
    report, calls = _cuda_install(home, monkeypatch, lambda calls: None, lambda python: ('2.5.0', False))
    assert any(c['index'] == cuda['index'] for c in calls)  # a CPU torch is swapped


# --- a GPU that fails at run time gets one retry on the CPU -----------------------------------------

def _engine_with_receipt(home, name='molscribe'):
    _ready(home, name)
    (home / name / env.RECEIPT).write_text('{}')


@pytest.mark.parametrize('message', ['CUDA error: an illegal memory access', 'no kernel image is available',
                                     'CUDA out of memory. Tried to allocate 2 GiB'])
def test_a_cuda_failure_is_retried_once_on_the_cpu(home, monkeypatch, message):
    _engine_with_receipt(home)
    devices = []
    cuda_visible = []

    def run(command, **kwargs):
        devices.append(kwargs['env'].get('CHEMDRAW_ENGINE_DEVICE'))
        cuda_visible.append(kwargs['env'].get('CUDA_VISIBLE_DEVICES'))
        ok = devices[-1] == 'cpu'
        payload = {'ok': True, 'engine': 'molscribe', 'device': 'cpu', 'result': [1]} if ok else {'ok': False, 'error': message}
        return subprocess.CompletedProcess(command, 0, env.MARKER + json.dumps(payload), '')

    monkeypatch.setenv('CUDA_VISIBLE_DEVICES', '0')
    monkeypatch.setattr(env, '_run', run)
    assert env.call('molscribe', 'predict', {}) == [1]
    assert devices == [None, 'cpu']
    assert cuda_visible == ['0', '']
    assert env.last_call_meta('molscribe') == {'device': 'cpu', 'device_fallback': True}


def test_cpu_calls_hide_cuda_visible_devices_in_child_env(home, monkeypatch):
    _engine_with_receipt(home)
    (home / 'molscribe' / env.RECEIPT).write_text(json.dumps({'device': 'cuda'}))
    seen = []

    def run(command, **kwargs):
        seen.append(dict(kwargs['env']))
        dev = 'cpu' if kwargs['env'].get('CUDA_VISIBLE_DEVICES') == '' else 'cuda'
        payload = {'ok': True, 'engine': 'molscribe', 'device': dev, 'result': {'ok': True}}
        return subprocess.CompletedProcess(command, 0, env.MARKER + json.dumps(payload), '')

    monkeypatch.setenv('CUDA_VISIBLE_DEVICES', '0')
    monkeypatch.setattr(env, '_run', run)

    env._call('molscribe', 'predict', {}, timeout=30, device='cpu')
    assert seen[-1]['CHEMDRAW_ENGINE_DEVICE'] == 'cpu' and seen[-1]['CUDA_VISIBLE_DEVICES'] == ''
    assert env.last_call_meta('molscribe') == {'device': 'cpu', 'device_fallback': False}

    monkeypatch.setenv('CHEMDRAW_ENGINE_DEVICE', 'cpu')
    env.call('molscribe', 'predict', {})
    assert seen[-1]['CUDA_VISIBLE_DEVICES'] == ''
    assert env.last_call_meta('molscribe') == {'device': 'cpu', 'device_fallback': False}

    monkeypatch.delenv('CHEMDRAW_ENGINE_DEVICE')
    env.call('molscribe', 'predict', {})
    assert seen[-1]['CUDA_VISIBLE_DEVICES'] == '0'
    assert env.last_call_meta('molscribe') == {'device': 'cuda', 'device_fallback': False}
    assert env.last_call_meta('aizynthfinder') == {'device': 'cpu', 'device_fallback': False}


def test_no_retry_when_the_device_was_chosen_or_the_error_is_something_else(home, monkeypatch):
    _engine_with_receipt(home)
    devices = []

    def run(command, **kwargs):
        devices.append(kwargs['env'].get('CHEMDRAW_ENGINE_DEVICE'))
        return subprocess.CompletedProcess(command, 0, env.MARKER + json.dumps({'ok': False, 'error': 'CUDA error'}), '')

    monkeypatch.setattr(env, '_run', run)
    monkeypatch.setenv('CHEMDRAW_ENGINE_DEVICE', 'cuda')
    with pytest.raises(env.EngineError, match='CUDA error'):
        env.call('molscribe', 'predict', {})
    assert devices == ['cuda']
    monkeypatch.delenv('CHEMDRAW_ENGINE_DEVICE')
    devices.clear()
    monkeypatch.setattr(env, '_run', lambda command, **kw: devices.append(1) or subprocess.CompletedProcess(
        command, 0, env.MARKER + json.dumps({'ok': False, 'error': 'invalid SMILES'}), ''))
    with pytest.raises(env.EngineError, match='invalid SMILES'):
        env.call('molscribe', 'predict', {})
    assert devices == [1]


# --- status is read from the receipt ---------------------------------------------------------------

def test_status_reads_the_size_from_the_receipt_and_walks_only_old_installs(home, monkeypatch):
    for name in ('molscribe', 'molnextr'):
        _ready(home, name)
    (home / 'molscribe' / env.RECEIPT).write_text(json.dumps({'disk_mb': 1234.5}))
    (home / 'molnextr' / env.RECEIPT).write_text('{}')  # installed before the size was recorded
    (home / 'molnextr' / 'weights.bin').write_bytes(b'x' * 2_000_000)
    walked = []
    real = env.disk_usage
    monkeypatch.setattr(env, 'disk_usage', lambda name: walked.append(name) or real(name))
    engines = env.status()['engines']
    assert engines['molscribe']['disk_used_mb'] == 1234.5 and 'molscribe' not in walked
    assert engines['molnextr']['disk_used_mb'] >= 2.0 and 'molnextr' in walked
    assert json.loads((home / 'molnextr' / env.RECEIPT).read_text())['disk_mb'] >= 2.0  # measured once
    walked.clear()
    env.status()
    assert 'molnextr' not in walked
    env.status(sizes=True)
    assert 'molscribe' in walked  # sizes=True measures again


def test_an_install_records_its_size_in_the_receipt(home, monkeypatch):
    _ready(home, 'molscribe')
    (home / 'molscribe' / 'weights.bin').write_bytes(b'x' * 3_000_000)
    monkeypatch.setattr(env, '_pip', lambda *a, **k: None)
    monkeypatch.setattr(env, 'call', lambda *a, **k: {})
    assert env.install('molscribe')['ok']
    assert json.loads((home / 'molscribe' / env.RECEIPT).read_text())['disk_mb'] >= 3.0


def test_the_mcp_listing_does_not_measure_folders(home, monkeypatch):
    from cdxml_toolkit.mcp_runtime import engine_tools
    _ready(home, 'molscribe')
    (home / 'molscribe' / env.RECEIPT).write_text(json.dumps({'disk_mb': 700.0}))
    monkeypatch.setattr(env, 'disk_usage', lambda name: pytest.fail('walked the folder'))
    listing = engine_tools.list_engines()
    assert listing['ok'] is True and listing['engines']['molscribe']['disk_used_mb'] == 700.0


# --- no stale receipt after an interrupted install --------------------------------------------------

@pytest.mark.parametrize('error', [KeyboardInterrupt(), _failure(), RuntimeError('x')])
def test_an_install_that_stops_for_any_reason_leaves_no_receipt(home, monkeypatch, error):
    _ready(home, 'magnet')
    (home / 'magnet' / env.RECEIPT).write_text('{}')

    def pip(*a, **k):
        assert not (home / 'magnet' / env.RECEIPT).exists()  # withdrawn before the first step
        raise error

    monkeypatch.setattr(env, '_pip', pip)
    try:
        env.install('magnet')
    except KeyboardInterrupt:
        assert isinstance(error, KeyboardInterrupt)
    assert not (home / 'magnet' / env.RECEIPT).exists() and env.available()['magnet'] is False


# --- a timeout takes the whole process tree ---------------------------------------------------------

def _alive(pid):
    if os.name == 'nt':
        out = subprocess.run(['tasklist', '/FI', f'PID eq {pid}', '/NH'], capture_output=True).stdout
        return str(pid).encode() in out
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def test_a_timeout_kills_the_children_of_the_engine_too(tmp_path):
    pid_file = tmp_path / 'child.pid'
    code = ('import subprocess, sys, time\n'
            "child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(120)'])\n"
            f"open({str(pid_file)!r}, 'w').write(str(child.pid))\n"
            'time.sleep(120)\n')
    with pytest.raises(subprocess.TimeoutExpired):
        env._run([sys.executable, '-c', code], timeout=4)
    pid = int(pid_file.read_text())
    for _ in range(50):
        if not _alive(pid):
            break
        time.sleep(0.1)
    assert not _alive(pid)


def test_run_returns_what_the_process_printed(tmp_path):
    done = env._run([sys.executable, '-c', 'import sys; print(sys.stdin.read()); print("e", file=sys.stderr)'],
                    input='hi', timeout=60)
    assert done.returncode == 0 and done.stdout.strip() == 'hi' and done.stderr.strip() == 'e'


# --- one install of an engine at a time -------------------------------------------------------------

def test_a_second_install_of_the_same_engine_fails_fast(home, monkeypatch):
    held = env._acquire('magnet')
    try:
        monkeypatch.setattr(env, '_pip', lambda *a, **k: pytest.fail('ran while locked'))
        report = env.install('magnet')
        assert report['ok'] is False and 'another install of magnet is running' in report['error']
        _ready(home, 'magnet')
        (home / 'magnet' / env.RECEIPT).write_text('{}')
        assert 'another install of magnet is running' in env.remove('magnet', dry_run=False)['error']
        assert (home / 'magnet').exists()
        with pytest.raises(env.EngineError, match='another install of magnet is running'):
            env.call('magnet', 'fetch', {})
        env._release(held)
        held = None
        monkeypatch.setattr(env, '_pip', lambda *a, **k: None)
        monkeypatch.setattr(env, 'call', lambda *a, **k: {})
        assert env.install('magnet')['ok']  # the lock is gone once released
        assert env.remove('magnet', dry_run=False)['removed']
    finally:
        if held:
            env._release(held)


def test_another_engine_is_not_blocked(home, monkeypatch):
    held = env._acquire('magnet')
    try:
        _ready(home, 'molscribe')
        monkeypatch.setattr(env, '_pip', lambda *a, **k: None)
        monkeypatch.setattr(env, 'call', lambda *a, **k: {})
        assert env.install('molscribe')['ok']
    finally:
        env._release(held)


# --- the pip error is shown -------------------------------------------------------------------------

def test_a_failed_step_shows_the_last_lines_of_its_error(home, monkeypatch):
    _ready(home, 'magnet')
    tail = '\n'.join(f'line {i}' for i in range(30)) + '\nERROR: Could not find a version that satisfies torch'

    def pip(*a, **k):
        raise _failure(tail=tail)

    monkeypatch.setattr(env, '_pip', pip)
    error = env.install('magnet')['error']
    assert 'Could not find a version that satisfies torch' in error and 'line 20' in error and 'line 5\n' not in error
    assert 'check the network or proxy' in error


def test_pip_keeps_the_last_stderr_lines_of_a_failing_step(monkeypatch, tmp_path):
    monkeypatch.setenv('CHEMDRAW_ENGINE_HOME', str(tmp_path))
    monkeypatch.setattr(env, '_uv', lambda: None)
    code = 'import sys\n' + ''.join(f'print("e{i}", file=sys.stderr)\n' for i in range(40)) + 'sys.exit(3)\n'
    script = tmp_path / 'fake_pip.py'
    script.write_text(code)
    with pytest.raises(subprocess.CalledProcessError) as caught:
        env._step([sys.executable, str(script)], None, os.environ)
    assert caught.value.returncode == 3 and caught.value.stderr.splitlines() == [f'e{i}' for i in range(25, 40)]


# --- a Python on Windows without uv -----------------------------------------------------------------

def test_the_windows_launcher_is_tried_when_no_versioned_python_is_on_the_path(tmp_path, monkeypatch):
    low, high = ENGINES['molscribe']['python']
    assert low == high  # one version: the launcher is asked for exactly that one
    monkeypatch.setattr(env, '_uv', lambda: None)
    monkeypatch.setattr(env.os, 'name', 'nt')
    monkeypatch.setattr(env.shutil, 'which', lambda command: 'py-launcher' if command == 'py' else None)
    ran = []
    monkeypatch.setattr(env.subprocess, 'run', lambda command, **kw: ran.append(command) or subprocess.CompletedProcess(command, 0))
    monkeypatch.setattr(env, 'interpreter', lambda path: path / 'Scripts' / 'python.exe')
    env._create('molscribe', tmp_path / 'molscribe', None)
    assert ran[-1] == ['py-launcher', f'-3.{high}', '-m', 'venv', str(tmp_path / 'molscribe')]


def test_no_python_anywhere_says_what_to_install(tmp_path, monkeypatch):
    monkeypatch.setattr(env, '_uv', lambda: None)
    monkeypatch.setattr(env.shutil, 'which', lambda command: None)
    with pytest.raises(RuntimeError, match='no Python 3.10 to 3.10 found'):
        env._create('molscribe', tmp_path / 'molscribe', None)


def test_allow_runtime_changes_flag_is_gone_from_cli(capsys):
    from cdxml_toolkit.engines import __main__ as cli
    with pytest.raises(SystemExit) as stopped:
        cli.main(['--allow-runtime-changes', 'molscribe'])
    assert stopped.value.code == 2
    assert 'unrecognized arguments: --allow-runtime-changes' in capsys.readouterr().err


# --- device & fallback metadata propagate through every engine wrapper ------------------------------

def test_device_and_fallback_propagate_through_ocsr_and_document(home, tmp_path, monkeypatch):
    from PIL import Image
    from cdxml_toolkit.engines import document, ocsr
    from cdxml_toolkit.mcp_runtime import decimer_api

    img = tmp_path / 'mol.png'
    Image.new('RGB', (40, 40), 'white').save(img)

    # Mixed GPU + CPU jar, plus remote
    def fake_call_mixed(name, action, params, timeout=0):
        if name == 'decimer-segmentation':
            seg = tmp_path / 'seg1.png'
            Image.new('RGB', (40, 40), 'white').save(seg)
            env._LAST_CALL_META.set({'engine': name, 'device': 'cpu', 'device_fallback': False})
            return [{'source': params['images'][0], 'segments': [str(seg)], 'bboxes': [[0, 0, 40, 40]]}]
        env._LAST_CALL_META.set({'engine': name, 'device': 'cuda', 'device_fallback': False})
        return [{'smiles': 'CCO', 'score': 0.95}]

    molvec_mol = (
        '\n  Molvec\n\n  3  2  0  0  0  0  0  0  0  0999 V2000\n'
        '    0.0000    0.0000    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0\n'
        '    1.0000    0.5000    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0\n'
        '    2.0000    0.0000    0.0000 O   0  0  0  0  0  0  0  0  0  0  0  0\n'
        '  1  2  1  0  0  0  0\n  2  3  1  0  0  0  0\nM  END\n'
    )
    monkeypatch.setattr(env, 'call', fake_call_mixed)
    monkeypatch.setattr(env, 'run_jar', lambda *a, **k: subprocess.CompletedProcess(a, 0, molvec_mol, ''))
    monkeypatch.setattr(decimer_api, 'recognize_image',
                        lambda *a, **k: {'structures': [{'smiles': 'CCO'}], 'warnings': []})

    mixed = ocsr.recognize(str(img), 'molscribe,molvec')
    assert mixed['device'] == 'mixed' and 'device_fallback' not in mixed
    assert [e['device'] for e in mixed['engines']] == ['cuda', 'cpu']

    remote = ocsr.recognize(str(img), 'decimer-api', confirm_upload=True)
    assert remote['device'] == 'remote' and remote['engines'][0]['device'] == 'remote'

    # Document extraction reports segmenter_device='cpu' and per-segment device
    monkeypatch.setattr(env, 'available', lambda: {n: n in {'decimer-segmentation', 'molscribe', 'molvec'} for n in ENGINES})
    extracted = document.extract(str(img), str(tmp_path / 'out_doc'), engines='molscribe', segmenter='decimer-segmentation')
    assert extracted['segmenter'] == 'decimer-segmentation' and extracted['segmenter_device'] == 'cpu'
    assert extracted['segments'][0]['device'] == 'cuda'
    assert extracted['segments'][0]['engines'][0]['device'] == 'cuda'

    # Fallback warning & flag in OCSR
    def fake_call_fallback(name, action, params, timeout=0):
        env._LAST_CALL_META.set({'engine': name, 'device': 'cpu', 'device_fallback': True})
        return [{'smiles': 'CCO', 'score': 0.9}]

    monkeypatch.setattr(env, 'call', fake_call_fallback)
    fell_back = ocsr.recognize(str(img), 'molscribe')
    assert fell_back['device'] == 'cpu' and fell_back['device_fallback'] is True
    assert fell_back['engines'][0]['device'] == 'cpu' and fell_back['engines'][0]['device_fallback'] is True
    assert any('molscribe: CUDA failed at runtime; fell back to CPU.' in w for w in fell_back['warnings'])
    assert any('molscribe: CUDA failed at runtime; fell back to CPU.' in w for w in fell_back['engines'][0]['warnings'])


def test_device_and_fallback_propagate_through_reactions_and_synplanner(home, tmp_path, monkeypatch):
    from cdxml_toolkit.engines import reactions, worker
    from cdxml_toolkit.mcp_runtime import report_tools

    real_call = env.call

    def fake_call_with_meta(device, fallback, result):
        def _call(name, action, params, timeout=0):
            env._LAST_CALL_META.set({'engine': name, 'device': device, 'device_fallback': fallback})
            return result
        return _call

    # Products (normal GPU + fallback)
    monkeypatch.setattr(env, 'call', fake_call_with_meta('cuda', False, [[{'smiles': 'CC(=O)OCC', 'score': -0.1}]]))
    prod = reactions.products('CC(=O)O.CCO')
    assert prod['device'] == 'cuda' and 'device_fallback' not in prod

    monkeypatch.setattr(env, 'call', fake_call_with_meta('cpu', True, [[{'smiles': 'CC(=O)OCC', 'score': -0.1}]]))
    prod_fb = reactions.products('CC(=O)O.CCO')
    assert prod_fb['device'] == 'cpu' and prod_fb['device_fallback'] is True
    assert any('reactiont5-forward: CUDA failed at runtime; fell back to CPU.' in w for w in prod_fb['warnings'])

    # Retrosynthesis: aizynthfinder (CPU)
    monkeypatch.setattr(env, 'call', fake_call_with_meta('cpu', False, {
        'steps': 'single', 'target': 'CC(=O)OCC',
        'options': [{'reactants': [['CC(=O)O', 'CCO']], 'probability': 0.8, 'template': 't'}],
    }))
    retro_ai = reactions.retrosynthesis('CC(=O)OCC', engine='aizynthfinder', steps='single')
    assert retro_ai['device'] == 'cpu' and 'device_fallback' not in retro_ai

    # SynPlanner: CPU override sets CUDA_VISIBLE_DEVICES="", and CUDA failure retries once on CPU
    monkeypatch.setattr(env, 'call', real_call)
    _engine_with_receipt(home, 'synplanner')
    (home / 'synplanner' / env.RECEIPT).write_text(json.dumps({'device': 'cuda'}))
    synplan_envs = []

    def fake_worker_synplan_run(cmd, **kwargs):
        synplan_envs.append(kwargs.get('env'))
        res_dir = cmd[cmd.index('--results_dir') + 1]
        os.makedirs(res_dir, exist_ok=True)
        with open(os.path.join(res_dir, 'tree_search_stats.csv'), 'w', encoding='utf-8') as fh:
            fh.write('solved,target_in_stock,num_routes,best_route_score\nTrue,False,1,0.75\n')
        with open(os.path.join(res_dir, 'extracted_routes.json'), 'w', encoding='utf-8') as fh:
            json.dump([[{'type': 'mol', 'smiles': 'CC(=O)OCC', 'in_stock': True, 'children': []}]], fh)
        return subprocess.CompletedProcess(cmd, 0, '', '')

    monkeypatch.setenv('CHEMDRAW_ENGINE_DEVICE', 'cpu')
    monkeypatch.setattr(worker.subprocess, 'run', fake_worker_synplan_run)
    syn_out = worker._synplanner({'smiles': 'CC(=O)OCC'}, str(tmp_path), {})
    assert syn_out['solved'] is True and synplan_envs[-1]['CUDA_VISIBLE_DEVICES'] == ''

    monkeypatch.delenv('CHEMDRAW_ENGINE_DEVICE')
    attempts = []

    def fake_env_run(command, **kwargs):
        attempts.append((kwargs['env'].get('CHEMDRAW_ENGINE_DEVICE'), kwargs['env'].get('CUDA_VISIBLE_DEVICES')))
        if len(attempts) == 1:
            payload = {'ok': False, 'error': 'RuntimeError: synplan planning failed: CUDA out of memory'}
        else:
            payload = {'ok': True, 'engine': 'synplanner', 'device': 'cpu',
                       'result': {'steps': 'multi', 'target': 'CC(=O)OCC', 'solved': True,
                                  'top_score': 0.8, 'routes': []}}
        return subprocess.CompletedProcess(command, 0, env.MARKER + json.dumps(payload), '')

    monkeypatch.setattr(env, '_run', fake_env_run)
    retro_syn = reactions.retrosynthesis('CC(=O)OCC', engine='synplanner', steps='multi')
    assert attempts == [(None, None), ('cpu', '')]
    assert retro_syn['device'] == 'cpu' and retro_syn['device_fallback'] is True
    assert any('synplanner: CUDA failed at runtime; fell back to CPU.' in w for w in retro_syn['warnings'])

    # Conditions (GPU and fallback)
    monkeypatch.setattr(report_tools, 'map_reaction_atoms',
                        lambda rxn: {'status': 'complete', 'mapped_reaction': '[CH3:1][OH:2]>>[CH3:1][OH:2]', 'method': 'rxnmapper'})
    monkeypatch.setattr(env, 'call', fake_call_with_meta('cpu', True, {
        'template_level': 'r1', 'candidates': [{'catalyst': None, 'solvents': ['THF'], 'reagents': [], 'score': 0.5}],
    }))
    cond = reactions.conditions('CO', 'CO')
    assert cond['device'] == 'cpu' and cond['device_fallback'] is True
    assert any('reacon: CUDA failed at runtime; fell back to CPU.' in w for w in cond['warnings'])


def test_device_and_fallback_propagate_through_nmr_single_and_dual_engine(home, monkeypatch):
    from cdxml_toolkit.engines import nmr

    atoms = [
        {'index': 0, 'element': 'C', 'shift': 58.0, 'class': 0, 'neighbors': [2]},
        {'index': 1, 'element': 'C', 'shift': 18.0, 'class': 1, 'neighbors': [0]},
        {'index': 2, 'element': 'O', 'shift': None, 'class': 2, 'neighbors': [0, 3]},
        {'index': 3, 'element': 'H', 'shift': 2.5, 'class': 3, 'neighbors': [2]},
    ]

    def fake_call(name, action, params, timeout=0):
        if name == 'magnet':
            env._LAST_CALL_META.set({'engine': name, 'device': 'cuda', 'device_fallback': False})
        else:
            env._LAST_CALL_META.set({'engine': name, 'device': 'cpu', 'device_fallback': True})
        return {'atoms': atoms, 'geometry': 'RDKit'}

    monkeypatch.setattr(env, 'call', fake_call)
    single = nmr.predict('CCO', nucleus='13C', engine='magnet')
    assert single['device'] == 'cuda' and 'device_fallback' not in single

    single_fb = nmr.predict('CCO', nucleus='13C', engine='nmrnet-pp')
    assert single_fb['device'] == 'cpu' and single_fb['device_fallback'] is True
    assert any('nmrnet-pp: CUDA failed at runtime; fell back to CPU.' in w for w in single_fb['warnings'])

    dual = nmr.predict('CCO', nucleus='13C', engine='magnet,nmrnet-pp')
    assert dual['device'] == 'mixed' and dual['device_fallback'] is True
    assert [(e['engine'], e['device'], e.get('device_fallback', False)) for e in dual['engines']] == [
        ('magnet', 'cuda', False),
        ('nmrnet-pp', 'cpu', True),
    ]
    assert any('nmrnet-pp: CUDA failed at runtime; fell back to CPU.' in w for w in dual['warnings'])


# --- RetroChimera stops early when the model cannot fit ---------------------------------------------

def _worker():
    from cdxml_toolkit.engines import worker
    return worker


def test_retrochimera_refuses_to_start_when_free_memory_is_below_the_model(monkeypatch):
    worker = _worker()
    monkeypatch.delenv('CHEMDRAW_ENGINE_PROCESSES', raising=False)
    monkeypatch.setattr(worker, '_available_gb', lambda: 9.4)
    with pytest.raises(RuntimeError) as caught:
        worker._check_model_memory()
    assert str(caught.value) == ('RetroChimera needs about 14 GB free memory, only 9.4 GB: close programs, or set '
                                 'CHEMDRAW_ENGINE_PROCESSES=1 to try anyway')
    monkeypatch.setattr(worker, '_available_gb', lambda: 20.0)
    worker._check_model_memory()
    monkeypatch.setattr(worker, '_available_gb', lambda: None)  # unknown memory is not a reason to refuse
    worker._check_model_memory()


def test_setting_the_process_count_skips_the_memory_guard(monkeypatch):
    worker = _worker()
    monkeypatch.setattr(worker, '_available_gb', lambda: 2.0)
    monkeypatch.setenv('CHEMDRAW_ENGINE_PROCESSES', '1')
    worker._check_model_memory()


def test_retrochimera_checks_memory_before_loading_the_model(monkeypatch):
    worker = _worker()
    monkeypatch.delenv('CHEMDRAW_ENGINE_PROCESSES', raising=False)
    monkeypatch.setattr(worker, '_available_gb', lambda: 3.0)
    import types
    for module in ('syntheseus', 'syntheseus.interface', 'syntheseus.interface.molecule'):
        monkeypatch.setitem(sys.modules, module, types.ModuleType(module))
    sys.modules['syntheseus.interface.molecule'].Molecule = str
    with pytest.raises(RuntimeError, match='needs about 14 GB free memory'):
        worker._retrochimera({'smiles': 'CCO', 'steps': 'single'}, 'nowhere', {})


# --- a broken archive is not kept ------------------------------------------------------------------

def test_a_corrupt_archive_is_deleted_so_the_next_try_starts_clean(tmp_path, monkeypatch):
    worker = _worker()

    def download(url, partial, **kw):
        with open(partial, 'wb') as out:
            out.write(b'this is not a zip file')

    monkeypatch.setattr(worker, '_download', download)
    source = {'url': 'http://host/z', 'members': [{'name': 'a', 'path': 'a.bin', 'sha256': '0' * 64}]}
    with pytest.raises(Exception, match='[Ee]rror|zip'):
        worker._fetch_archive_members(str(tmp_path), source)
    assert not (tmp_path / '_archive.zip.part').exists()


def test_an_archive_whose_member_fails_its_hash_is_deleted(tmp_path, monkeypatch):
    import zipfile
    worker = _worker()

    def download(url, partial, **kw):
        with zipfile.ZipFile(partial, 'w') as bundle:
            bundle.writestr('a', b'content')

    monkeypatch.setattr(worker, '_download', download)
    source = {'url': 'http://host/z', 'members': [{'name': 'a', 'path': 'a.bin', 'sha256': '0' * 64}]}
    with pytest.raises(RuntimeError, match='does not match the pinned sha256'):
        worker._fetch_archive_members(str(tmp_path), source)
    assert not (tmp_path / '_archive.zip.part').exists() and not (tmp_path / 'a.bin.tmp').exists()


# --- errors say where the engines live ---------------------------------------------------------------

def test_a_missing_engine_names_the_folder_that_was_searched(home):
    with pytest.raises(env.EngineMissing) as caught:
        env.call('molscribe', 'predict', {})
    assert str(home) in str(caught.value) and caught.value.hint['home'] == str(home)
    with pytest.raises(env.EngineMissing, match=re.escape(str(home))):
        env.run_jar('molvec', [])


def test_diagnostics_and_segmentation_name_the_engine_home_too(home):
    from cdxml_toolkit.engines import document
    from cdxml_toolkit.mcp_runtime.runtime_diagnostics import _engine_capabilities
    detail = _engine_capabilities()['engine_molscribe']['detail']
    assert str(home) in detail and 'install-engines molscribe' in detail
    with pytest.raises(ValueError, match=re.escape(str(home))):
        document._segment([], home, 'decimer-segmentation', [])
