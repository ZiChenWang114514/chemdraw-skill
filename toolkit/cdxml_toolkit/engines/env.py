"""Environments, installation and the JSON pipe for the optional engines. Standard library only.

One environment per engine under ``home()``, so PyTorch 1.x, TensorFlow 2.14 and the numpy 1.x/2.x
stacks never meet. ``call`` starts ``worker.py`` with the engine's own interpreter; Java engines run
as a jar. ``CHEMDRAW_ENGINE_HOME`` moves the whole tree (the tests point it at an empty folder).
"""

from __future__ import annotations

import collections
import contextlib
import contextvars
import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from . import accel
from .registry import BUNDLES, CUDA_TORCH, ENGINES, GUIDE, RECOMMEND, RECOMMEND_ALIASES, disk_mb

WORKER = Path(__file__).with_name('worker.py')
RUN_TIMEOUT = 900  # the first import of PyTorch can take a minute on a cold disk
VENV_TIMEOUT = 600
FETCH_TIMEOUT = 6 * 3600  # large model files on a slow link; every download resumes, so a retry loses nothing
RECEIPT = '.engine.json'
MARKER = '@@ENGINE-RESULT@@'  # worker.py prefixes its one JSON line with this
DEVICE_ERRORS = re.compile(r'CUDA error|no kernel image|CUDA out of memory', re.I)  # the GPU, not the input, failed
ERROR_LINES = 15  # how much of a failing install step's stderr the error shows
_LAST_CALL_META: contextvars.ContextVar[dict | None] = contextvars.ContextVar('_LAST_CALL_META', default=None)


class EngineError(RuntimeError):
    """An engine is missing, could not run, or returned something unusable."""


class EngineMissing(EngineError):
    """The engine is not installed. ``hint`` says what installing it would cost, for the user to decide."""

    def __init__(self, name: str, message: str):
        super().__init__(message)
        self.hint = hint(name)


def hint(name: str) -> dict:
    """What to tell the user when ``name`` is needed but absent: use, size, licence and the command."""
    spec = ENGINES[name]
    guide = GUIDE.get(name, {})
    return {'engine': name, 'title': spec['title'], 'use_when': guide.get('use_when'),
            'size_mb': guide.get('disk_mb'), 'license': spec.get('license'), 'needs': guide.get('needs', []),
            'command': f'cdx.py install-engines {name}', 'home': str(home()), 'asks_the_network': True}


def _offline() -> bool:
    return os.environ.get('CHEMDRAW_OFFLINE', '').strip().lower() in ('1', 'true', 'yes', 'on')


def home() -> Path:
    explicit = os.environ.get('CHEMDRAW_ENGINE_HOME')
    if explicit:
        return Path(explicit).expanduser()
    if os.name == 'nt':
        base = os.environ.get('LOCALAPPDATA') or str(Path.home() / 'AppData' / 'Local')
    else:
        base = os.environ.get('XDG_DATA_HOME') or str(Path.home() / '.local' / 'share')
    return Path(base) / 'chemdraw-skill' / 'engines'


def environment(name: str) -> Path:
    return home() / name


def interpreter(env: Path) -> Path | None:
    for relative in ('Scripts/python.exe', 'bin/python3', 'bin/python'):
        if (env / relative).is_file():
            return env / relative
    return None


def data_dir(name: str) -> Path:
    """Where an engine's downloaded weights or data live (inside its own folder)."""
    return environment(name) / 'data'


def java() -> str | None:
    from ..resolve.jre_manager import get_java
    return get_java(download=False)


def receipt(name: str) -> dict | None:
    path = environment(name) / RECEIPT
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None


def jar_path(name: str) -> Path | None:
    spec = ENGINES[name]
    path = environment(name) / spec['jar']['name']
    return path if path.is_file() else None


def python_for(name: str) -> Path | None:
    """The interpreter that runs engine ``name``, or None when it is not installed."""
    if ENGINES[name]['kind'] != 'local':
        return None
    own = interpreter(environment(name))
    return own if own and receipt(name) is not None else None


def _has_cuda_torch_dist(env_dir: Path) -> bool:
    """True when ``env_dir`` has a ``+cu...`` wheel of torch installed (for legacy receipts without ``device``)."""
    if sys.platform == 'darwin':
        return False
    candidates = [env_dir / 'Lib' / 'site-packages', *env_dir.glob('lib/python*/site-packages')]
    return any('+cu' in dist.name for site in candidates if site.is_dir() for dist in site.glob('torch-*.dist-info'))


def configured_device(name: str) -> str:
    """The device ``name`` is configured to run on ('cuda', 'cpu', or 'remote')."""
    spec = ENGINES[name]
    if spec['kind'] == 'remote':
        return 'remote'
    if os.environ.get('CHEMDRAW_ENGINE_DEVICE', '').strip().lower() == 'cpu' or spec['kind'] == 'jar' or not spec.get('gpu'):
        return 'cpu'
    recorded = (receipt(name) or {}).get('device')
    if recorded in ('cuda', 'cpu'):
        return recorded
    return 'cuda' if _has_cuda_torch_dist(environment(name)) else 'cpu'


def last_call_meta(name: str | None = None) -> dict:
    """Device metadata from the most recent ``call`` on this context, or configured defaults."""
    meta = _LAST_CALL_META.get()
    if isinstance(meta, dict) and (name is None or meta.get('engine') == name):
        return {'device': meta['device'], 'device_fallback': bool(meta.get('device_fallback'))}
    return {'device': configured_device(name) if name else 'cpu', 'device_fallback': False}


def _cuda_failure(error) -> bool:
    return bool(DEVICE_ERRORS.search(str(error)))


def available() -> dict:
    """Which engines can run now. Remote engines count as available; the network policy decides later."""
    out = {}
    for name, spec in ENGINES.items():
        if spec['kind'] == 'remote':
            out[name] = True
        elif spec['kind'] == 'jar':
            out[name] = bool(jar_path(name) and java())
        else:
            out[name] = python_for(name) is not None
    return out


def _kill_tree(process: subprocess.Popen) -> None:
    """Stop ``process`` and everything it started (an engine's own workers keep running after the parent dies)."""
    try:
        if os.name == 'nt':
            subprocess.run(['taskkill', '/F', '/T', '/PID', str(process.pid)], capture_output=True, timeout=30)
        else:
            os.killpg(process.pid, signal.SIGKILL)  # the process leads its own group (start_new_session)
    except (OSError, subprocess.TimeoutExpired):
        pass
    try:
        process.kill()
    except OSError:
        pass


def _run(command, *, timeout, input=None, env=None, capture=True) -> subprocess.CompletedProcess:
    """``subprocess.run`` that ends the whole process tree on a timeout or an interrupt. stdout is always captured;
    stderr too unless ``capture`` is false (then it stays on the terminal, to show a download's progress)."""
    options = {'creationflags': subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == 'nt' else {'start_new_session': True}
    process = subprocess.Popen(command, stdin=subprocess.PIPE if input is not None else None, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE if capture else None, text=True, encoding='utf-8',
                               errors='replace', env=env, **options)
    try:
        out, err = process.communicate(input, timeout=timeout)
    except subprocess.TimeoutExpired:
        _kill_tree(process)
        process.communicate()
        raise
    except BaseException:  # KeyboardInterrupt included
        _kill_tree(process)
        raise
    return subprocess.CompletedProcess(command, process.returncode, out, err)



def _missing(name: str, detail: str = '') -> EngineMissing:
    return EngineMissing(name, f'{ENGINES[name]["title"]} is not installed{detail} (looked in {home()}): '
                               f'run `cdx.py install-engines {name}`')


def call(name: str, action: str, params: dict, timeout: int = RUN_TIMEOUT) -> dict:
    """Run ``action`` of engine ``name`` in its environment and return the worker's ``result``.

    ``fetch`` is part of installing, so it runs before the engine counts as installed, under the engine's lock.
    When the GPU fails (a CUDA error, no kernels for it, out of memory) and the device was not chosen with
    ``CHEMDRAW_ENGINE_DEVICE``, the call is repeated once on the CPU.
    """
    _LAST_CALL_META.set(None)
    if action == 'fetch':
        with _lock(name):
            return _call(name, action, params, timeout)
    try:
        return _call(name, action, params, timeout)
    except RuntimeError as exc:
        if os.environ.get('CHEMDRAW_ENGINE_DEVICE', '').strip() or not _cuda_failure(exc):
            raise
        print(f'{ENGINES[name]["title"]}: the GPU failed ({str(exc)[:160]}); trying once on the CPU', file=sys.stderr)
        result = _call(name, action, params, timeout, device='cpu')
        _LAST_CALL_META.set({'engine': name, 'device': 'cpu', 'device_fallback': True})
        return result


def _call(name: str, action: str, params: dict, timeout: int, device: str | None = None) -> dict:
    _LAST_CALL_META.set(None)
    python = interpreter(environment(name)) if action == 'fetch' else python_for(name)
    title = ENGINES[name]['title']
    if python is None:
        raise _missing(name)
    request = {'engine': name, 'action': action, 'params': params,
               'data_dir': str(data_dir(name)), 'spec': {k: ENGINES[name].get(k) for k in ('weights', 'data', 'family', 'download', 'downloads', 'zip_members',
                                                                           'archive_members', 'stock', 'sha256')}}
    env = dict(os.environ, TOKENIZERS_PARALLELISM='false', PYTHONIOENCODING='utf-8', PYTHONUNBUFFERED='1')
    if device:
        env['CHEMDRAW_ENGINE_DEVICE'] = device
    force_cpu = device == 'cpu' or os.environ.get('CHEMDRAW_ENGINE_DEVICE', '').strip().lower() == 'cpu'
    if force_cpu:
        env['CUDA_VISIBLE_DEVICES'] = ''
    if ENGINES[name]['kind'] == 'local':  # libraries that cache models with pystow keep them inside the engine
        env['PYSTOW_HOME'] = str(data_dir(name))
    env.update(HF_HUB_OFFLINE='0' if action == 'fetch' else '1', TRANSFORMERS_OFFLINE='0' if action == 'fetch' else '1')

    effective_device = 'cpu' if force_cpu else (device or configured_device(name))

    if accel.wants_daemon(name, action, params):
        try:
            daemon_out = accel.call_via_daemon(
                engine=name,
                python=python,
                worker_script=WORKER,
                request=request,
                env_vars=env,
                engine_home=home(),
                device_key=effective_device,
                timeout=timeout,
            )
        except accel.DaemonTimeout as exc:
            raise EngineError(f'{title} did not finish within {timeout} s') from exc
        if daemon_out is not None:
            payload, _ = daemon_out
            if not payload.get('ok'):
                if _cuda_failure(payload.get('error', '')):
                    accel.stop_daemon_file(accel.daemon_state_path(home(), name, effective_device))
                raise EngineError(f'{title}: {payload.get("error")}')
            _LAST_CALL_META.set({'engine': name, 'device': payload.get('device') or effective_device,
                                 'device_fallback': False})
            return payload['result']

    # A download shows its progress lines on the terminal; a prediction's output stays captured.
    try:
        done = _run([str(python), '-W', 'ignore', str(WORKER)], input=json.dumps(request), capture=action != 'fetch',
                    timeout=timeout, env=env)
    except subprocess.TimeoutExpired as exc:
        raise EngineError(f'{title} did not finish within {timeout} s') from exc
    except OSError as exc:
        raise EngineError(f'{title} could not start: {exc}') from exc
    payload = None
    for line in reversed((done.stdout or '').splitlines()):  # engines may print to stdout; only our marked line counts
        if line.startswith(MARKER):
            try:
                payload = json.loads(line[len(MARKER):])
            except ValueError:
                pass
            break
    if payload is None:
        tail = (done.stderr or done.stdout or '').strip().splitlines()[-1:]
        raise EngineError(f'{title} failed to start: {tail[0][:300] if tail else "see the messages above"}')
    if not payload.get('ok'):
        raise EngineError(f'{title}: {payload.get("error")}')
    _LAST_CALL_META.set({'engine': name, 'device': payload.get('device') or effective_device, 'device_fallback': False})
    return payload['result']


def run_jar(name: str, args: list, timeout: int = 300) -> subprocess.CompletedProcess:
    jar = jar_path(name)
    if jar is None or not java():
        raise _missing(name, ' (it needs Java and its jar)')
    try:
        return _run([java(), '-Djava.awt.headless=true', '-cp', str(jar), *args], timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        raise EngineError(f'{ENGINES[name]["title"]} did not finish within {timeout} s') from exc


def sha256_of(path) -> str:
    digest = hashlib.sha256()
    with open(path, 'rb') as handle:
        for block in iter(lambda: handle.read(1 << 20), b''):
            digest.update(block)
    return digest.hexdigest()


def _uv() -> str | None:
    return shutil.which('uv')


_HELD: set[str] = set()  # engines this process holds the lock of: install calls fetch, which asks again


def _acquire(name: str):
    """Take the lock of engine ``name`` (a file under ``home()/.locks``), or say that another install holds it."""
    folder = home() / '.locks'
    folder.mkdir(parents=True, exist_ok=True)
    handle = open(folder / name, 'a+b')
    try:
        if os.name == 'nt':
            import msvcrt
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        handle.close()
        raise EngineError(f'another install of {name} is running (lock {folder / name}); wait for it to finish') from None
    return handle


def _release(handle) -> None:
    try:
        if os.name == 'nt':
            import msvcrt
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            fcntl.flock(handle, fcntl.LOCK_UN)
    except OSError:
        pass
    handle.close()


@contextlib.contextmanager
def _lock(name: str):
    """One install, removal or download of an engine at a time; a second one fails at once instead of corrupting it."""
    if name in _HELD:
        yield
        return
    handle = _acquire(name)
    _HELD.add(name)
    try:
        yield
    finally:
        _HELD.discard(name)
        _release(handle)


def _python_for_version(minor: int) -> list[str] | None:
    """The command that starts Python 3.``minor``: ``python3.N`` on the PATH, or on Windows the ``py -3.N`` launcher."""
    found = shutil.which(f'python3.{minor}')
    if found:
        return [found]
    launcher = shutil.which('py') if os.name == 'nt' else None
    if launcher and subprocess.run([launcher, f'-3.{minor}', '-c', 'import sys'], capture_output=True,
                                   timeout=60).returncode == 0:
        return [launcher, f'-3.{minor}']
    return None


def _create(name: str, env: Path, log) -> Path:
    low, high = ENGINES[name]['python']
    env.parent.mkdir(parents=True, exist_ok=True)
    if _uv():  # uv fetches a matching Python itself
        subprocess.run([_uv(), 'venv', '--allow-existing', '--python', f'3.{high}', str(env)], check=True, stdout=log,
                       timeout=VENV_TIMEOUT)
    else:
        for minor in range(high, low - 1, -1):
            base = _python_for_version(minor)
            if base:
                subprocess.run([*base, '-m', 'venv', str(env)], check=True, stdout=log, timeout=VENV_TIMEOUT)
                break
        else:
            raise RuntimeError(f'no Python 3.{low} to 3.{high} found: install one or `pip install uv`')
    return interpreter(env)


def _step(command, log, environment) -> None:
    """Run one install step. Its stderr is shown as it comes and its last lines are kept: a failure raises
    ``CalledProcessError`` carrying them, so the error can say what pip or uv said."""
    process = subprocess.Popen(command, stdout=log, stderr=subprocess.PIPE, text=True, encoding='utf-8',
                               errors='replace', env=environment)
    tail = collections.deque(maxlen=ERROR_LINES)
    try:
        for line in process.stderr:
            sys.stderr.write(line)
            tail.append(line.rstrip('\r\n'))
        process.wait()
    except BaseException:
        process.kill()
        raise
    if process.returncode:
        raise subprocess.CalledProcessError(process.returncode, command, stderr='\n'.join(tail))


def _pip(python, requirements, log, find_links=None, no_build_isolation=False, index_url=None, no_deps=False):
    links = ['--find-links', find_links] if find_links else []
    links += ['--no-deps'] if no_deps else []  # put exact versions back without resolving anything else
    links += ['--no-build-isolation'] if no_build_isolation else []  # packages whose setup.py imports torch
    if index_url:  # the CUDA wheels: torch from this index, everything else still from PyPI
        links += ['--index-url', index_url, '--extra-index-url', 'https://pypi.org/simple']
    # Package downloads (several GB for PyTorch) are cached beside the engines, on the disk the user chose for them
    cache = home() / '.cache'
    environment = {'UV_HTTP_TIMEOUT': '300', 'UV_CACHE_DIR': str(cache / 'uv'), 'PIP_CACHE_DIR': str(cache / 'pip'),
                   **os.environ}
    if _uv():
        strategy = ['--index-strategy', 'unsafe-best-match'] if index_url else []
        _step([_uv(), 'pip', 'install', '--python', str(python), *links, *strategy, *requirements], log, environment)
    else:
        _step([str(python), '-m', 'pip', 'install', '--default-timeout', '120', '--retries', '8',
               *links, *requirements], log, environment)


def _nvidia_gpu() -> str | None:
    """The name of an NVIDIA GPU that a CUDA build of torch can use, or None (also when CPU use is forced)."""
    if os.environ.get('CHEMDRAW_ENGINE_DEVICE', '').strip().lower() == 'cpu' or sys.platform == 'darwin':
        return None
    smi = shutil.which('nvidia-smi')
    if not smi:
        return None
    try:
        done = subprocess.run([smi, '--query-gpu=name', '--format=csv,noheader'], capture_output=True, text=True,
                              timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return None
    name = done.stdout.strip().splitlines()[0].strip() if done.returncode == 0 and done.stdout.strip() else ''
    return name or None


def _has_package(python, package: str) -> bool:
    code = f'import importlib.util, sys; sys.exit(0 if importlib.util.find_spec({package!r}) else 1)'
    return subprocess.run([str(python), '-c', code], capture_output=True, timeout=120).returncode == 0


def _torch_probe(python) -> tuple[str, bool] | None:
    """(torch version, ``torch.cuda.is_available()``) as the engine's own interpreter sees them, or None."""
    try:
        done = subprocess.run([str(python), '-c', 'import torch;print(torch.__version__);print(torch.cuda.is_available())'],
                              capture_output=True, text=True, timeout=300)
    except (OSError, subprocess.TimeoutExpired):
        return None
    words = done.stdout.split()
    return (words[-2], words[-1] == 'True') if done.returncode == 0 and len(words) >= 2 else None


def _cpu_stack(spec: dict, python, log) -> None:
    """The pinned requirements the engine runs on without CUDA (also what is put back after a failed CUDA swap)."""
    _pip(python, spec['requirements'], log, spec.get('find_links'))
    if spec.get('extra_requirements'):
        _pip(python, spec['extra_requirements'], log, spec.get('find_links'))


def _cuda_torch(name: str, python, log) -> dict:
    """Swap the engine's torch for the CUDA build when it can use one and an NVIDIA GPU is here.

    A swap that fails half way (torch replaced, its compiled extensions not) puts the CPU stack back; if that fails
    too the error goes up and the install fails. The ``device`` is what torch reports afterwards, not what was hoped.
    """
    spec = ENGINES[name]
    gpu = _nvidia_gpu() if spec.get('gpu') else None
    if not gpu:
        return {'device': 'cpu'}
    build = spec.get('cuda') or CUDA_TORCH
    tag = build['tag']
    target = f'{build["torch"]}+{tag}'
    requirements = [f'torch=={target}']
    if build.get('torchvision') and _has_package(python, 'torchvision'):
        requirements.append(f'torchvision=={build["torchvision"]}+{tag}')
    try:
        probe = _torch_probe(python)
        if not (probe and probe[0] == target):  # a re-install keeps the CUDA build it already has
            _pip(python, requirements, log, index_url=build['index'])
        if build.get('requirements'):  # compiled torch extensions built for this torch
            _pip(python, build['requirements'], log, build.get('find_links'))
    except subprocess.CalledProcessError as exc:  # back to the CPU stack, which works
        _cpu_stack(spec, python, log)
        return {'device': 'cpu', 'gpu': gpu, 'gpu_error': f'the CUDA build of torch did not install (status '
                                                          f'{exc.returncode}); the engine runs on the CPU'}
    probe = _torch_probe(python)
    if probe and probe[1]:
        return {'device': 'cuda', 'gpu': gpu, 'torch': target}
    return {'device': 'cpu', 'gpu': gpu, 'torch': target,
            'gpu_error': 'the CUDA build of torch is installed but torch.cuda.is_available() is False '
                         '(driver or GPU); the engine runs on the CPU'}


def _fetch_jar(name: str):
    jar = ENGINES[name]['jar']
    target = environment(name) / jar['name']
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_suffix('.part')
    for attempt in range(4):  # model and package hosts sometimes drop a TLS connection mid-handshake
        try:
            with urllib.request.urlopen(jar['url'], timeout=120) as response, open(partial, 'wb') as out:  # noqa: S310
                shutil.copyfileobj(response, out)
            break
        except OSError:
            if attempt == 3:
                raise
            time.sleep(2 * (attempt + 1))
    if sha256_of(partial) != jar['sha256']:
        partial.unlink()
        raise EngineError(f'{jar["name"]} does not match the pinned sha256; nothing was installed')
    os.replace(partial, target)
    return target


def install(name: str, *, dry_run: bool = False, log=None) -> dict:
    """Create the environment (or fetch the jar), install the pinned requirements and the weights.

    The old receipt is withdrawn before the first step and written again only when every step has finished, so an
    install that is interrupted (even by Ctrl-C) leaves an engine that does not count as installed. One install of
    an engine runs at a time.
    """
    spec = ENGINES[name]
    env = environment(name)
    report = {'engine': name, 'environment': str(env), 'license': spec.get('license'), 'size': spec.get('size'),
              'requirements': spec.get('requirements') or ([spec['jar']['url']] if 'jar' in spec else [])}
    if spec['kind'] == 'remote':
        report.update(ok=available()[name], note=spec.get('note') or 'nothing to install here')
        return report
    report['disk_mb'] = GUIDE.get(name, {}).get('disk_mb')
    if not dry_run and _offline():
        report.update(ok=False, error='CHEMDRAW_OFFLINE is set: installing downloads packages and weights, so nothing '
                                      'was installed')
        return report
    if dry_run:
        report['python_needed'] = f'3.{spec["python"][0]} to 3.{spec["python"][1]}' if 'python' in spec else 'Java'
        return report
    log = log or sys.stderr
    try:
        with _lock(name):
            _drop_receipt(env)
            report.update(_install_steps(name, spec, env, log))
    except subprocess.CalledProcessError as exc:
        tail = '\n'.join(exc.stderr.strip().splitlines()[-ERROR_LINES:]) if isinstance(exc.stderr, str) else ''
        report.update(ok=False, error=f'installation failed: a step exited with status {exc.returncode}'
                                      + (f':\n{tail}\n' if tail else ' (see the messages above); ')
                                      + 'check the network or proxy, then run the same command again, finished '
                                        'downloads are cached.')
    except subprocess.TimeoutExpired as exc:
        report.update(ok=False, error=f'installation failed: a step timed out after {exc.timeout} s; run it again')
    except (OSError, RuntimeError, EngineError) as exc:
        report.update(ok=False, error=f'installation failed: {exc}')
    return report


def _install_steps(name: str, spec: dict, env: Path, log) -> dict:
    """What ``install`` adds to its report; raises when a step fails."""
    if spec['kind'] == 'jar':
        if not java():
            raise RuntimeError('Java was not found on PATH')
        _fetch_jar(name)
        env.mkdir(parents=True, exist_ok=True)
        _write_receipt(name, {'engine': name, 'sha256': spec['jar']['sha256']})
        return {'ok': True}
    # Without pyvenv.cfg the launcher falls back to the base Python, so the folder is made a venv again
    python = (interpreter(env) if (env / 'pyvenv.cfg').is_file() else None) or _create(name, env, log)
    _cpu_stack(spec, python, log)
    if spec.get('late_requirements'):  # built against what is already installed
        _pip(python, spec['late_requirements'], log, spec.get('find_links'), no_build_isolation=True)
    device = _cuda_torch(name, python, log)
    fetched = call(name, 'fetch', {}, timeout=FETCH_TIMEOUT) if (spec.get('weights') or spec.get('data')) else {}
    _write_receipt(name, {'engine': name, 'requirements': spec['requirements'], **fetched, 'device': device['device']})
    return {'ok': True, 'python': str(python), 'fetched': fetched, **device}


def _write_receipt(name: str, data: dict) -> None:
    """The receipt says the install finished; it also keeps the folder's size so that listing engines need not walk it."""
    (environment(name) / RECEIPT).write_text(json.dumps({**data, 'disk_mb': round(disk_usage(name) / 1e6, 1)}),
                                             encoding='utf-8')


def _drop_receipt(env: Path):
    try:
        (env / RECEIPT).unlink()
    except OSError:
        pass


def disk_usage(name: str) -> int:
    """Bytes used by the engine's own folder (0 when it has none). Symbolic links are not followed."""
    root = environment(name)
    if not root.is_dir() or root.is_symlink():
        return 0
    total = 0
    for base, _dirs, files in os.walk(root, followlinks=False):
        for file in files:
            try:
                total += os.lstat(os.path.join(base, file)).st_size
            except OSError:
                pass
    return total


def _used_mb(name: str, sizes: bool) -> float:
    """The engine's disk use in MB: the size its receipt recorded, or (an install from before sizes were recorded,
    or ``sizes=True``) a walk of the folder, whose result is then written into the receipt."""
    if not environment(name).is_dir():
        return 0.0
    recorded = (receipt(name) or {}).get('disk_mb')
    if isinstance(recorded, (int, float)) and not sizes:
        return recorded
    measured = round(disk_usage(name) / 1e6, 1)
    stored = receipt(name)
    if stored is not None:
        try:
            (environment(name) / RECEIPT).write_text(json.dumps({**stored, 'disk_mb': measured}), encoding='utf-8')
        except OSError:
            pass
    return measured


def status(sizes: bool = False) -> dict:
    """Which engines are available and their disk use. Sizes come from the receipts; ``sizes=True`` measures again."""
    found = available()
    engines, total = {}, 0
    for name, spec in ENGINES.items():
        used = _used_mb(name, sizes) if spec['kind'] in ('local', 'jar') else 0
        total += used
        if spec['kind'] == 'remote':
            device = 'remote'
        elif not found[name]:
            device = None
        else:
            device = configured_device(name)
        engines[name] = {'title': spec['title'], 'task': spec['task'], 'kind': spec['kind'], 'available': found[name],
                         'device': device, 'license': spec.get('license'), 'size': spec.get('size'),
                         'disk_used_mb': round(used, 1), 'use_when': GUIDE.get(name, {}).get('use_when')}
    daemons = [{'engine': d['engine'], 'device': d['device'], 'pid': d['pid']} for d in accel.active_daemons(home())]
    return {'home': str(home()), 'disk_used_mb': round(total, 1), 'active_daemons': daemons, 'engines': engines}


def recommend(task: str) -> dict:
    """The smallest set of engines that serves ``task`` (a need in ``RECOMMEND`` or an engine task name), with what
    each costs. Reads only; nothing is downloaded."""
    need = RECOMMEND_ALIASES.get(task, task)
    if need not in RECOMMEND:
        raise ValueError(f'unknown need {task!r} (choose from {", ".join([*RECOMMEND, *RECOMMEND_ALIASES])})')
    found = available()
    options = []
    for bundle in RECOMMEND[need]:
        names = BUNDLES[bundle]['engines']
        missing = [n for n in names if not found[n]]
        options.append({
            'bundle': bundle, 'about': BUNDLES[bundle]['about'], 'engines': names, 'missing': missing,
            'download_mb': disk_mb(missing),
            'details': [{'engine': n, 'installed': found[n], 'license': ENGINES[n].get('license'),
                         'size_mb': GUIDE[n]['disk_mb'], 'use_when': GUIDE[n]['use_when'],
                         'skip_when': GUIDE[n]['skip_when'], 'needs': GUIDE[n].get('needs', [])} for n in names],
            'command': f'cdx.py install-engines --bundle {bundle}' if missing else None})
    return {'ok': True, 'task': task, 'need': need, 'suggested': options[0]['bundle'], 'already_installed': not options[0]['missing'],
            'options': options, 'offline': _offline(),
            'note': 'Installing downloads packages and weights; it never uploads anything.'}


def remove(name: str, *, dry_run: bool = True) -> dict:
    """Delete one engine's folder. Only a direct child of ``home()`` that looks like an engine is removed."""
    spec = ENGINES[name]
    root = environment(name)
    report = {'engine': name, 'path': str(root), 'disk_mb': round(disk_usage(name) / 1e6, 1)}
    if spec['kind'] not in ('local', 'jar'):
        return {**report, 'ok': False, 'error': 'nothing to remove: this engine has no folder of its own'}
    if not root.exists() and not root.is_symlink():
        return {**report, 'ok': True, 'removed': False, 'note': 'not installed'}
    looks_like_engine = (root / RECEIPT).is_file() or (root / 'pyvenv.cfg').is_file()
    if root.is_symlink() or not root.is_dir() or root.resolve().parent != home().resolve() or not looks_like_engine:
        return {**report, 'ok': False, 'error': 'refused: this folder is not an engine installation made by '
                                                 'install-engines (nothing was deleted)'}
    if dry_run:
        return {**report, 'ok': True, 'removed': False, 'dry_run': True}
    try:
        with _lock(name):
            for dev in ('default', 'cpu'):
                accel.stop_daemon_file(accel.daemon_state_path(home(), name, dev))
            shutil.rmtree(root)
    except EngineError as exc:  # an install of this engine is running
        return {**report, 'ok': False, 'error': str(exc)}
    return {**report, 'ok': True, 'removed': True}
