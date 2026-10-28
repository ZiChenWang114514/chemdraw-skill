"""Optional learned atom-mapping backends (RXNMapper, LocalMapper), each in its own environment.

Both depend on PyTorch and, for LocalMapper, on an old numeric stack (numpy 1.x, torch 2.3 and a
matching DGL), so they are installed beside the runtime instead of into it and are driven by
``atom_mapping_worker.py`` through a JSON pipe. A backend is also found when the runtime itself
imports it. Nothing here is needed by the built-in substructure method.

Run ``python -m cdxml_toolkit.mapping_backends`` (``cdx.py install-mappers``) to install them.

Standard library only.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

WORKER = Path(__file__).with_name('atom_mapping_worker.py')
RUN_TIMEOUT = 900  # the first import of PyTorch can take a minute on a cold disk
SELF_TEST = 'CC(=O)Cl.CCN>>CC(=O)NCC'

# Versions verified together on Windows with Python 3.12. DGL 2.2.1 ships graphbolt libraries
# for PyTorch 2.1 to 2.3 only, which forces the old numpy/scipy/pandas stack below.
BACKENDS = {
    'rxnmapper': {
        'title': 'RXNMapper',
        'module': 'rxnmapper',
        'requirements': ['rxnmapper>=0.4.3', 'rdkit', 'setuptools<81'],
        'python': 'Python 3.10 to 3.13',
        'minor': (10, 13),
    },
    'localmapper': {
        'title': 'LocalMapper',
        'module': 'localmapper',
        'requirements': ['localmapper==0.1.5', 'dgl==2.2.1', 'dgllife==0.3.2', 'torch==2.3.0', 'torchdata==0.7.1',
                         'numpy<2', 'scipy<1.14', 'pandas<2.3', 'scikit-learn<1.6', 'matplotlib<3.10',
                         'setuptools<81', 'pyyaml', 'pydantic', 'rdkit'],
        'python': 'Python 3.10 to 3.12 (PyTorch 2.3 has no wheel for newer versions)',
        'minor': (10, 12),
    },
}


def home() -> Path:
    """Folder that holds one environment per backend (CHEMDRAW_MAPPER_HOME overrides it)."""
    explicit = os.environ.get('CHEMDRAW_MAPPER_HOME')
    if explicit:
        return Path(explicit).expanduser()
    if os.name == 'nt':
        base = os.environ.get('LOCALAPPDATA') or str(Path.home() / 'AppData' / 'Local')
    else:
        base = os.environ.get('XDG_DATA_HOME') or str(Path.home() / '.local' / 'share')
    return Path(base) / 'chemdraw-skill' / 'mappers'


def environment(name: str) -> Path:
    return home() / name


def interpreter(env: Path) -> Path | None:
    for relative in ('Scripts/python.exe', 'bin/python3', 'bin/python'):
        if (env / relative).is_file():
            return env / relative
    return None


def python_for(name: str) -> Path | None:
    """Interpreter that can run backend ``name``: its own environment, else this one if it imports."""
    own = interpreter(environment(name))
    if own:
        return own
    try:
        found = importlib.util.find_spec(BACKENDS[name]['module']) is not None
    except (ImportError, ValueError):
        found = False
    return Path(sys.executable) if found else None


def available() -> dict:
    return {name: python_for(name) is not None for name in BACKENDS}


class BackendError(RuntimeError):
    """A backend could not run or returned something unusable."""


def run(name: str, reactions: list, timeout: int = RUN_TIMEOUT) -> list:
    """Map reaction SMILES with backend ``name``; one dict per reaction (mapped_rxn plus a score)."""
    python = python_for(name)
    if python is None:
        raise BackendError(f'{BACKENDS[name]["title"]} is not installed: run `cdx.py install-mappers {name}`')
    env = dict(os.environ, TOKENIZERS_PARALLELISM='false', HF_HUB_OFFLINE='1', PYTHONIOENCODING='utf-8')
    try:
        done = subprocess.run([str(python), '-W', 'ignore', str(WORKER)], input=json.dumps(
            {'method': name, 'reactions': list(reactions)}), capture_output=True, text=True, encoding='utf-8',
            timeout=timeout, env=env)
    except subprocess.TimeoutExpired as exc:
        raise BackendError(f'{BACKENDS[name]["title"]} did not finish within {timeout} s') from exc
    except OSError as exc:
        raise BackendError(f'{BACKENDS[name]["title"]} could not start: {exc}') from exc
    try:
        payload = json.loads(done.stdout)
    except ValueError:
        tail = (done.stderr or done.stdout or '').strip().splitlines()[-1:]
        raise BackendError(f'{BACKENDS[name]["title"]} failed to start: {tail[0] if tail else "no output"}') from None
    if not payload.get('ok'):
        raise BackendError(f'{BACKENDS[name]["title"]}: {payload.get("error")}')
    return payload['results']


def _minor(python) -> int | None:
    """Minor version of a Python 3 interpreter, or None when it cannot be asked."""
    try:
        done = subprocess.run([str(python), '-c', 'import sys; print(sys.version_info[0] * 100 + sys.version_info[1])'],
                              capture_output=True, text=True, timeout=30)
        value = int(done.stdout.strip())
    except (OSError, ValueError, subprocess.SubprocessError):
        return None
    return value - 300 if value // 100 == 3 else None


def find_base(name: str) -> str | None:
    """A Python that can host backend ``name``: this one, else python3.N on PATH, else the Windows launcher."""
    low, high = BACKENDS[name]['minor']
    candidates = [sys.executable] + [shutil.which(f'python3.{m}') for m in range(high, low - 1, -1)]
    if os.name == 'nt' and shutil.which('py'):
        for m in range(high, low - 1, -1):
            try:
                done = subprocess.run(['py', f'-3.{m}', '-c', 'import sys; print(sys.executable)'],
                                      capture_output=True, text=True, timeout=30)
            except (OSError, subprocess.SubprocessError):
                continue
            if done.returncode == 0 and done.stdout.strip():
                candidates.append(done.stdout.strip())
    for candidate in candidates:
        if not candidate:
            continue
        minor = _minor(candidate)
        if minor is not None and low <= minor <= high:
            return candidate
    return None


# Creating a venv or asking pip for its version takes seconds; past these limits the step is stuck.
VENV_TIMEOUT = 600
PROBE_TIMEOUT = 60


def _create(name: str, env: Path, log) -> Path:
    """Create the environment for backend ``name`` and return its interpreter."""
    env.parent.mkdir(parents=True, exist_ok=True)
    base = find_base(name)
    if base:
        subprocess.run([base, '-m', 'venv', str(env)], check=True, stdout=log, timeout=VENV_TIMEOUT)
    elif shutil.which('uv'):  # uv fetches a matching Python itself
        subprocess.run(['uv', 'venv', '--python', f'3.{BACKENDS[name]["minor"][1]}', str(env)], check=True, stdout=log,
                       timeout=VENV_TIMEOUT)
    else:
        raise RuntimeError(f'no {BACKENDS[name]["python"]} found: install one (python.org, or `pip install uv`) and retry')
    return interpreter(env)


def _pip(python, requirements, log):
    """Install into ``python``'s environment; PyTorch wheels are large, so a slow link gets time and retries."""
    pip = subprocess.run([str(python), '-m', 'pip', '--version'], capture_output=True,
                         timeout=PROBE_TIMEOUT).returncode == 0
    if not pip and shutil.which('uv'):  # environments made by uv carry no pip
        subprocess.run(['uv', 'pip', 'install', '--python', str(python), *requirements], check=True, stdout=log,
                       env={**os.environ, 'UV_HTTP_TIMEOUT': '300'})
    else:
        subprocess.run([str(python), '-m', 'pip', 'install', '--default-timeout', '120', '--retries', '8',
                        *requirements], check=True, stdout=log)


def install(name: str, *, dry_run: bool = False, log=None) -> dict:
    """Create ``environment(name)``, install its pinned requirements and check it with a real mapping.

    Never touches the runtime's own packages. Returns a report; ``ok`` is true only when the
    self-test mapped a reaction.
    """
    spec = BACKENDS[name]
    env = environment(name)
    report = {'backend': name, 'environment': str(env), 'requirements': spec['requirements'],
              'python_needed': spec['python']}
    if dry_run:
        report['python_found'] = find_base(name)
        return report
    log = log or sys.stderr
    try:
        python = interpreter(env) or _create(name, env, log)
        _pip(python, spec['requirements'], log)
    except subprocess.CalledProcessError as exc:
        report.update(ok=False, error=f'installation failed: a step exited with status {exc.returncode} (see the '
                                      'messages above), usually a download that timed out; run the same command '
                                      'again (finished downloads are cached)')
        return report
    except subprocess.TimeoutExpired as exc:
        report.update(ok=False, error=f'installation failed: a step timed out after {exc.timeout} s; '
                                      'run the same command again')
        return report
    except (OSError, RuntimeError) as exc:
        report.update(ok=False, error=f'installation failed: {exc}')
        return report
    try:
        mapped = run(name, [SELF_TEST], timeout=RUN_TIMEOUT)[0].get('mapped_rxn')
    except BackendError as exc:
        report.update(ok=False, error=f'installed but the self-test failed: {exc}')
        return report
    report.update(ok=bool(mapped), python=str(python), self_test=mapped)
    return report


def status() -> dict:
    found = available()
    return {'home': str(home()), 'backends': {name: {
        'available': found[name], 'environment': str(environment(name)), 'python_needed': BACKENDS[name]['python']}
        for name in BACKENDS}}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog='cdx.py install-mappers', description=(
        'Install the optional learned atom-mapping backends, each in its own environment under '
        f'{home()} (several hundred MB with PyTorch). map_reaction_atoms works without them.'))
    parser.add_argument('backends', nargs='*', metavar='BACKEND', help=f'{" or ".join(sorted(BACKENDS))}; default: both')
    parser.add_argument('--dry-run', action='store_true', help='print what would be installed')
    parser.add_argument('--status', action='store_true', help='print which backends are available; install nothing')
    ns = parser.parse_args(argv)
    unknown = [name for name in ns.backends if name not in BACKENDS]
    if unknown:  # not argparse `choices`: Python 3.10 and 3.11 check the empty default against them
        parser.error(f'unknown backend {unknown[0]!r} (choose from {", ".join(sorted(BACKENDS))})')
    names = ns.backends or sorted(BACKENDS)
    if ns.status:
        print(json.dumps(status(), indent=2))
        return 0
    reports = [install(name, dry_run=ns.dry_run) for name in names]
    print(json.dumps({'home': str(home()), 'reports': reports,
                      'note': 'map_reaction_atoms uses these with method auto, rxnmapper or localmapper; '
                              'method mcs (the fallback) needs nothing extra. Nothing is uploaded.'}, indent=2))
    return 0 if ns.dry_run or all(r.get('ok') for r in reports) else 1


if __name__ == '__main__':
    sys.exit(main())
