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

    def run(command, **kwargs):
        devices.append(kwargs['env'].get('CHEMDRAW_ENGINE_DEVICE'))
        ok = devices[-1] == 'cpu'
        payload = {'ok': True, 'result': [1]} if ok else {'ok': False, 'error': message}
        return subprocess.CompletedProcess(command, 0, env.MARKER + json.dumps(payload), '')

    monkeypatch.setattr(env, '_run', run)
    assert env.call('molscribe', 'predict', {}) == [1]
    assert devices == [None, 'cpu']


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


# --- the shared runtime is not changed under the user -----------------------------------------------

def test_decimer_local_refuses_an_install_that_would_change_installed_packages(home, monkeypatch):
    import importlib.metadata
    monkeypatch.setattr(importlib.metadata, 'requires', lambda dist: ['decimer>=2.6; extra == "decimer"'])
    monkeypatch.setattr(importlib.metadata, 'version', lambda dist: '1.26.4')
    monkeypatch.setattr(env, '_dry_run_changes', lambda requirements: [('protobuf', '5.29.0', '4.25.3'), ('keras', '3.1', '2.14')])
    monkeypatch.setattr(env, '_pip', lambda *a, **k: pytest.fail('installed anyway'))
    report = env.install('decimer-local')
    assert report['ok'] is False and 'protobuf 5.29.0 -> 4.25.3' in report['error'] and 'keras 3.1 -> 2.14' in report['error']


def test_the_uv_dry_run_listing_names_the_packages_it_would_replace_or_remove():
    text = ('Resolved 9 packages in 12ms\nWould download 2 packages\nWould uninstall 2 packages\nWould install 3 packages\n'
            ' - keras==3.1.0\n - protobuf==5.29.0\n + keras==2.14.0\n + protobuf==4.25.3\n + decimer==2.6.0\n')
    assert env._parse_uv_dry_run(text) == [('keras', '3.1.0', '2.14.0'), ('protobuf', '5.29.0', '4.25.3')]
    assert env._parse_uv_dry_run(' + decimer==2.6.0\n') == []
    assert env._parse_uv_dry_run(' - gone==1.0\n') == [('gone', '1.0', None)]


def test_the_pip_dry_run_report_names_changed_installed_packages(monkeypatch):
    import importlib.metadata
    versions = {'protobuf': '5.29.0', 'numpy': '1.26.4'}

    def version(name):
        if name not in versions:
            raise importlib.metadata.PackageNotFoundError(name)
        return versions[name]

    monkeypatch.setattr(importlib.metadata, 'version', version)
    report = {'install': [{'metadata': {'name': 'protobuf', 'version': '4.25.3'}},
                          {'metadata': {'name': 'numpy', 'version': '1.26.4'}},
                          {'metadata': {'name': 'decimer', 'version': '2.6.0'}}]}
    assert env._parse_pip_report(report) == [('protobuf', '5.29.0', '4.25.3')]


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
