"""Environments, installation and the JSON pipe for the optional engines. Standard library only.

One environment per engine under ``home()``, so PyTorch 1.x, TensorFlow 2.14 and the numpy 1.x/2.x
stacks never meet. ``call`` starts ``worker.py`` with the engine's own interpreter; Java engines run
as a jar. ``CHEMDRAW_ENGINE_HOME`` moves the whole tree (the tests point it at an empty folder).
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from .registry import ENGINES

WORKER = Path(__file__).with_name('worker.py')
RUN_TIMEOUT = 900  # the first import of PyTorch can take a minute on a cold disk
VENV_TIMEOUT = 600
RECEIPT = '.engine.json'
MARKER = '@@ENGINE-RESULT@@'  # worker.py prefixes its one JSON line with this


class EngineError(RuntimeError):
    """An engine is missing, could not run, or returned something unusable."""


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
    return shutil.which('java')


def _find_spec(module: str) -> bool:
    try:
        return importlib.util.find_spec(module) is not None
    except (ImportError, ValueError):
        return False


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


def _decimer_weights() -> bool:
    """The local DECIMER models are on disk (the engine must never start a download while it runs)."""
    root = Path(os.environ.get('DECIMER_MODEL_DIR') or Path.home() / '.data' / 'DECIMER-V2').expanduser()
    return (root / 'DECIMER_model' / 'saved_model.pb').is_file()


def python_for(name: str) -> Path | None:
    """The interpreter that runs engine ``name``, or None when it is not installed."""
    spec = ENGINES[name]
    kind = spec['kind']
    if kind == 'runtime':
        return Path(sys.executable) if _find_spec(spec['module']) and _decimer_weights() else None
    if kind != 'local':
        return None
    own = interpreter(environment(name))
    return own if own and receipt(name) is not None else None


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


def call(name: str, action: str, params: dict, timeout: int = RUN_TIMEOUT) -> dict:
    """Run ``action`` of engine ``name`` in its environment and return the worker's ``result``."""
    python = python_for(name)
    title = ENGINES[name]['title']
    if python is None:
        raise EngineError(f'{title} is not installed: run `cdx.py install-engines {name}`')
    request = {'engine': name, 'action': action, 'params': params,
               'data_dir': str(data_dir(name)), 'spec': {k: ENGINES[name].get(k) for k in ('weights', 'data', 'family', 'download', 'sha256')}}
    env = dict(os.environ, TOKENIZERS_PARALLELISM='false', PYTHONIOENCODING='utf-8', PYTHONUNBUFFERED='1')
    if ENGINES[name]['kind'] == 'local':  # libraries that cache models with pystow keep them inside the engine
        env['PYSTOW_HOME'] = str(data_dir(name))
    env.update(HF_HUB_OFFLINE='0' if action == 'fetch' else '1', TRANSFORMERS_OFFLINE='0' if action == 'fetch' else '1')
    try:
        done = subprocess.run([str(python), '-W', 'ignore', str(WORKER)], input=json.dumps(request),
                              capture_output=True, text=True, encoding='utf-8', timeout=timeout, env=env)
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
        raise EngineError(f'{title} failed to start: {tail[0][:300] if tail else "no output"}')
    if not payload.get('ok'):
        raise EngineError(f'{title}: {payload.get("error")}')
    return payload['result']


def run_jar(name: str, args: list, timeout: int = 300) -> subprocess.CompletedProcess:
    jar = jar_path(name)
    if jar is None or not java():
        raise EngineError(f'{ENGINES[name]["title"]} is not installed (it needs Java and its jar): '
                          f'run `cdx.py install-engines {name}`')
    try:
        return subprocess.run([java(), '-Djava.awt.headless=true', '-cp', str(jar), *args], capture_output=True,
                              text=True, encoding='utf-8', errors='replace', timeout=timeout)
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


def _create(name: str, env: Path, log) -> Path:
    low, high = ENGINES[name]['python']
    env.parent.mkdir(parents=True, exist_ok=True)
    if _uv():  # uv fetches a matching Python itself
        subprocess.run([_uv(), 'venv', '--python', f'3.{high}', str(env)], check=True, stdout=log, timeout=VENV_TIMEOUT)
    else:
        for minor in range(high, low - 1, -1):
            base = shutil.which(f'python3.{minor}')
            if base:
                subprocess.run([base, '-m', 'venv', str(env)], check=True, stdout=log, timeout=VENV_TIMEOUT)
                break
        else:
            raise RuntimeError(f'no Python 3.{low} to 3.{high} found: install one or `pip install uv`')
    return interpreter(env)


def _pip(python, requirements, log, find_links=None):
    links = ['--find-links', find_links] if find_links else []
    if _uv():
        subprocess.run([_uv(), 'pip', 'install', '--python', str(python), *links, *requirements], check=True,
                       stdout=log, env={**os.environ, 'UV_HTTP_TIMEOUT': '300'})
    else:
        subprocess.run([str(python), '-m', 'pip', 'install', '--default-timeout', '120', '--retries', '8',
                        *links, *requirements], check=True, stdout=log)


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
    """Create the environment (or fetch the jar), install the pinned requirements and the weights."""
    spec = ENGINES[name]
    env = environment(name)
    report = {'engine': name, 'environment': str(env), 'license': spec.get('license'), 'size': spec.get('size'),
              'requirements': spec.get('requirements') or ([spec['jar']['url']] if 'jar' in spec else [])}
    if spec['kind'] in ('remote', 'runtime'):
        report.update(ok=available()[name], note=spec.get('note') or 'nothing to install here')
        return report
    if dry_run:
        report['python_needed'] = f'3.{spec["python"][0]} to 3.{spec["python"][1]}' if 'python' in spec else 'Java'
        return report
    log = log or sys.stderr
    try:
        if spec['kind'] == 'jar':
            if not java():
                raise RuntimeError('Java was not found on PATH')
            _fetch_jar(name)
            env.mkdir(parents=True, exist_ok=True)
            (env / RECEIPT).write_text(json.dumps({'engine': name, 'sha256': spec['jar']['sha256']}), encoding='utf-8')
            report.update(ok=True)
            return report
        python = interpreter(env) or _create(name, env, log)
        _pip(python, spec['requirements'], log, spec.get('find_links'))
        if spec.get('extra_requirements'):
            _pip(python, spec['extra_requirements'], log, spec.get('find_links'))
        (env / RECEIPT).write_text(json.dumps({'engine': name, 'installing': True}), encoding='utf-8')
        fetched = call(name, 'fetch', {}, timeout=3 * RUN_TIMEOUT) if (spec.get('weights') or spec.get('data')) else {}
        (env / RECEIPT).write_text(json.dumps({'engine': name, 'requirements': spec['requirements'], **fetched}),
                                   encoding='utf-8')
        report.update(ok=True, python=str(python), fetched=fetched)
    except subprocess.CalledProcessError as exc:
        _drop_receipt(env)
        report.update(ok=False, error=f'installation failed: a step exited with status {exc.returncode} (see the '
                                      'messages above); run the same command again, finished downloads are cached')
    except subprocess.TimeoutExpired as exc:
        _drop_receipt(env)
        report.update(ok=False, error=f'installation failed: a step timed out after {exc.timeout} s; run it again')
    except (OSError, RuntimeError, EngineError) as exc:
        _drop_receipt(env)
        report.update(ok=False, error=f'installation failed: {exc}')
    return report


def _drop_receipt(env: Path):
    try:
        (env / RECEIPT).unlink()
    except OSError:
        pass


def status() -> dict:
    found = available()
    return {'home': str(home()), 'engines': {name: {
        'title': spec['title'], 'task': spec['task'], 'kind': spec['kind'], 'available': found[name],
        'license': spec.get('license'), 'size': spec.get('size')} for name, spec in ENGINES.items()}}
