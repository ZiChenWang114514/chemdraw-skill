#!/usr/bin/env python3
"""Install the ChemDraw Skill for one or more coding agents, and optionally its runtime.

Without --apply this prints the proposal only (JSON on stdout). With --apply each
Skill copy is staged, verified and swapped into place; an existing installation
is moved to a backup outside every Skill discovery directory and restored on
failure.

--runtime creates (or reuses) one toolkit venv shared by all installed copies
and installs the bundled toolkit from this checkout's toolkit/ folder. scripts/cdx.py
finds that venv on its own, so any Python can launch the Skill's CLI. When the
venv lives somewhere cdx.py would not look, runtime.local.json is written into
every installed copy and into this repository checkout (ignored by Git).

--opsin downloads the OPSIN command-line JAR (pinned version, SHA-256 verified) into
the shared data folder beside the venv, where the runtime diagnostics find it.

--mapping adds the optional machine-learning atom-mapping backends (RXNMapper, LocalMapper;
PyTorch based). Each gets its own environment beside the runtime so their pinned numeric
stacks cannot disturb it. Nothing needs them: map_reaction_atoms falls back to its built-in
substructure method. `scripts/cdx.py install-mappers` does the same for an existing runtime.

Examples:
    python3 scripts/install.py                                   # proposal for --agent claude
    python3 scripts/install.py --agent claude agents --runtime --apply
    python3 scripts/install.py --runtime --opsin --apply           # also fetch OPSIN
    python3 scripts/install.py --runtime-only --apply              # runtime for this checkout only
    python3 scripts/install.py --runtime --mapping --apply         # also RXNMapper + LocalMapper
    python3 scripts/install.py --agent copilot --project ~/src/app --apply
    python3 scripts/install.py --destination /opt/skills/chemdraw --apply
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import urllib.request
import uuid

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'skill' / 'chemdraw'
TOOLKIT = ROOT / 'toolkit'  # the bundled cdxml-toolkit source the runtime is built from
SKILL_NAME = 'chemdraw'

# Skill folders per agent: (user scope relative to the home folder, project scope).
# `agents` is the shared Agent Skills folder that most agents read in addition to their own.
AGENTS = {
    'claude': ('.claude/skills', '.claude/skills'),
    'agents': ('.agents/skills', '.agents/skills'),
    'gemini': ('.gemini/skills', '.gemini/skills'),
    'copilot': ('.copilot/skills', '.github/skills'),
    'cursor': ('.cursor/skills', '.cursor/skills'),
    'opencode': ('.config/opencode/skills', '.opencode/skills'),
    'kimi': ('.kimi-code/skills', '.kimi-code/skills'),
    'pi': ('.pi/agent/skills', '.pi/skills'),
}
# Never copied into an installation; runtime.local.json is written per installation.
IGNORED = ('__pycache__', '.pytest_cache', '.mypy_cache', '.ruff_cache', '*.pyc', '*.pyo',
           'manifest.json', 'runtime.local.json')
# Extras that drive a local ChemDraw (COM/.NET on Windows, AppleScript on macOS).
CHEMDRAW_EXTRAS = ('office', 'chemscript')
ALL_EXTRAS = ('publication', 'scientific', 'office', 'analysis', 'image', 'chemscript')
# OPSIN command-line JAR for --opsin; the digest is the one GitHub publishes for the release asset.
OPSIN_VERSION = '2.9.0'
OPSIN_JAR_NAME = f'opsin-cli-{OPSIN_VERSION}-jar-with-dependencies.jar'
OPSIN_URL = f'https://github.com/dan2097/opsin/releases/download/{OPSIN_VERSION}/{OPSIN_JAR_NAME}'
OPSIN_SHA256 = 'c2e29326c281f87b59a05d934d8589adac6e9d17b95b984931b3e739111b360f'


def default_extras(platform=sys.platform):
    chemdraw = platform in ('win32', 'darwin')
    return [e for e in ALL_EXTRAS if chemdraw or e not in CHEMDRAW_EXTRAS]


def mapping_backends(ns):
    """Backends named by --mapping: [] when absent, both when given without names or with `all`."""
    if ns.mapping is None:
        return []
    return list(dict.fromkeys(ns.mapping)) if ns.mapping and 'all' not in ns.mapping else ['rxnmapper', 'localmapper']


def install_mappers(python, backends):
    """Install the optional atom-mapping backends, each in its own environment, via the Skill's cdx.py."""
    command = [str(python), str(SOURCE / 'scripts' / 'cdx.py'), 'install-mappers', *backends]
    return subprocess.run(command, stdout=sys.stderr).returncode


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# The Skill's own modules are the single source for hashing and runtime locations.
check_installation = _load('chemdraw_check_installation', SOURCE / 'scripts' / 'check_installation.py')
cdx = _load('chemdraw_cdx', SOURCE / 'scripts' / 'cdx.py')


def log(message):
    print(message, file=sys.stderr, flush=True)


def fingerprint(root):
    hashes = check_installation.file_hashes(root)
    hashes.pop('runtime.local.json', None)
    return hashlib.sha256(json.dumps(hashes, sort_keys=True).encode('utf-8')).hexdigest()


def data_dir():
    return cdx.default_runtime_dir().parent


def opsin_plan(ns):
    if not ns.opsin:
        return {'action': 'skip'}
    jar = data_dir() / 'opsin' / OPSIN_JAR_NAME
    return {'action': 'present' if jar.is_file() else 'download', 'path': str(jar),
            'url': OPSIN_URL, 'sha256': OPSIN_SHA256}


def install_opsin(folder, *, url=OPSIN_URL, sha256=OPSIN_SHA256, opener=urllib.request.urlopen):
    """Download the OPSIN JAR into `folder`, keeping it only when its SHA-256 matches."""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    jar = folder / OPSIN_JAR_NAME
    partial = folder / f'.{OPSIN_JAR_NAME}.{uuid.uuid4().hex}.part'
    digest = hashlib.sha256()
    try:
        with opener(url, timeout=120) as response, partial.open('wb') as out:
            for block in iter(lambda: response.read(1 << 20), b''):
                digest.update(block)
                out.write(block)
        if digest.hexdigest() != sha256:
            raise OSError(f'OPSIN download failed its SHA-256 check: {digest.hexdigest()} != {sha256}')
        os.replace(partial, jar)
    finally:
        partial.unlink(missing_ok=True)
    return jar


def destinations(ns):
    if ns.destination:
        return [Path(d).expanduser().resolve() for d in ns.destination]
    base = Path(ns.project).expanduser().resolve() if ns.project else Path.home()
    scope = 1 if ns.project else 0
    seen, out = set(), []
    for agent in ns.agent:
        target = (base / AGENTS[agent][scope] / SKILL_NAME).resolve()
        if target not in seen:
            seen.add(target)
            out.append(target)
    return out


def venv_python(venv):
    return venv / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')


def probe_python(command):
    """(major, minor, bits) for a runnable interpreter command, else None."""
    code = 'import struct,sys;print(sys.version_info[0],sys.version_info[1],struct.calcsize("P")*8)'
    try:
        out = subprocess.run([*command, '-c', code], capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return None
    parts = out.stdout.split()
    if out.returncode != 0 or len(parts) != 3:
        return None
    return tuple(int(x) for x in parts)


def supported(info):
    return bool(info) and info[2] == 64 and (3, 10) <= info[:2] <= (3, 13)


def base_python(requested):
    """First command that runs a 64-bit Python 3.10-3.13 (the toolkit's supported range)."""
    if requested:
        found = shutil.which(requested) or (requested if Path(requested).is_file() else None)
        if not found:
            raise SystemExit(f'Python not found: {requested}')
        commands = [[found, f'-{v}'] for v in ('3.12', '3.13', '3.11', '3.10')] \
            if Path(found).stem.lower() == 'py' else [[found]]
    else:
        commands = [[sys.executable]]
        launcher = shutil.which('py') if os.name == 'nt' else None
        if launcher:
            commands += [[launcher, f'-{v}'] for v in ('3.12', '3.13', '3.11', '3.10')]
        for name in ('python3.12', 'python3.13', 'python3.11', 'python3.10', 'python3', 'python'):
            if shutil.which(name):
                commands.append([shutil.which(name)])
    for command in commands:
        if supported(probe_python(command)):
            return command
    return None


def runtime_plan(ns, targets):
    if not ns.runtime:
        return {'action': 'skip'}
    venv = Path(ns.runtime_dir).expanduser().resolve() if ns.runtime_dir else None
    if venv is None:
        # Reuse a venv that an older installation placed beside the Skill.
        legacy = [t.parent / 'chemdraw-venv' for t in targets if venv_python(t.parent / 'chemdraw-venv').is_file()]
        venv = legacy[0] if legacy else cdx.default_runtime_dir()
    action = 'reuse' if venv_python(venv).is_file() else 'create'
    base = None
    if action == 'create':
        base = base_python(ns.python)
        if base is None:
            raise SystemExit('The runtime needs a 64-bit Python 3.10-3.13 and none was found '
                             '(Python 3.14 and newer are not supported by the toolkit yet). '
                             'Install one, e.g. `uv python install 3.12` or the python.org 3.12 '
                             'installer, then pass --python <interpreter> if it is still not found.')
    extras = ns.extras if ns.extras is not None else default_extras()
    # base_python stays a command list: interpreter paths may contain spaces ("Program Files").
    return {'action': action, 'venv': str(venv), 'python': str(venv_python(venv)),
            'base_python': list(base) if base else None, 'extras': extras,
            # Always build from this checkout's toolkit/ so the runtime matches the Skill exactly.
            'toolkit_path': str(Path(ns.toolkit_path).expanduser().resolve()) if ns.toolkit_path
            else str(TOOLKIT)}


def backup_root(ns):
    return Path(ns.backup_root).expanduser().resolve() if ns.backup_root else data_dir() / 'backups'


def install_one(target, source_print, backups):
    """Stage, verify and swap one Skill copy. Returns the backup folder (or None)."""
    target.parent.mkdir(parents=True, exist_ok=True)
    staging = target.parent / f'.chemdraw-install-{uuid.uuid4().hex}'
    backup, published = None, False
    try:
        shutil.copytree(SOURCE, staging, ignore=shutil.ignore_patterns(*IGNORED))
        if fingerprint(staging) != source_print:
            raise RuntimeError('staged Skill does not match the repository source')
        if target.exists():
            backups.mkdir(parents=True, exist_ok=True)
            backup = backups / f'{time.strftime("%Y%m%d-%H%M%S")}-{uuid.uuid4().hex[:8]}'
            shutil.move(str(target), str(backup))
            (backup / 'BACKUP_ORIGIN.txt').write_text(f'{target}\n', encoding='utf-8')
        os.replace(staging, target)
        published = True
        if fingerprint(target) != source_print:
            raise RuntimeError('installed Skill does not match the repository source')
    except BaseException:
        if published and target.exists():
            shutil.rmtree(target)
        if backup and backup.exists():
            (backup / 'BACKUP_ORIGIN.txt').unlink(missing_ok=True)
            shutil.move(str(backup), str(target))
        raise
    finally:
        if staging.exists():
            shutil.rmtree(staging, ignore_errors=True)
    return backup


def install_runtime(plan, skill):
    """Create or reuse the venv and install the pinned toolkit; progress goes to stderr."""
    venv, python = Path(plan['venv']), Path(plan['python'])
    if plan['action'] == 'create':
        venv.parent.mkdir(parents=True, exist_ok=True)
        # Creating a venv takes seconds; past this limit the step is stuck, not slow.
        subprocess.run([*plan['base_python'], '-m', 'venv', str(venv)], check=True,
                       stdout=sys.stderr, timeout=600)
    command = [str(python), str(skill / 'scripts' / 'install_runtime.py'), '--extras', *plan['extras']]
    if plan['toolkit_path']:
        command += ['--toolkit-path', plan['toolkit_path']]
    subprocess.run(command, check=True, stdout=sys.stderr)


def needs_local_config(skill, python):
    """True when cdx.py would not find `python` by its default search order."""
    return Path(python).resolve() not in {
        venv_python(skill.parent / 'chemdraw-venv').resolve(), venv_python(cdx.default_runtime_dir()).resolve()}


def record_runtime(skills, python):
    """Write runtime.local.json into every Skill folder that could not find `python` otherwise.

    The repository checkout (SOURCE) is included so `cdx.py` works from the checkout too; the
    file is ignored by Git and never copied into installations."""
    written = []
    for skill in skills:
        if needs_local_config(skill, python):
            (skill / 'runtime.local.json').write_text(
                json.dumps({'runtime_python': str(python)}, indent=2) + '\n', encoding='utf-8')
            written.append(skill / 'runtime.local.json')
    return written


def parse(argv):
    p = argparse.ArgumentParser(description=__doc__.split('\n\n')[0],
                                formatter_class=argparse.RawDescriptionHelpFormatter,
                                epilog='Agents: ' + ', '.join(f'{k} (~/{u}, <project>/{q})'
                                                             for k, (u, q) in AGENTS.items()))
    p.add_argument('--agent', nargs='+', choices=sorted(AGENTS), default=['claude'],
                   help='agent Skill folder(s) to install into (default: claude)')
    p.add_argument('--project', help='install into this project instead of the home folder')
    p.add_argument('--destination', nargs='+', help='explicit Skill folder(s); overrides --agent/--project')
    p.add_argument('--runtime', action='store_true', help='create or reuse the shared toolkit venv')
    p.add_argument('--runtime-only', action='store_true',
                   help='only build the runtime for this checkout; installed Skill copies are left alone')
    p.add_argument('--runtime-dir', help=f'venv location (default: {cdx.default_runtime_dir()})')
    p.add_argument('--python', help='base interpreter for a new venv (64-bit Python 3.10-3.13)')
    p.add_argument('--extras', nargs='*', help='toolkit extras (default: all that apply to this OS)')
    p.add_argument('--mapping', nargs='*', choices=['rxnmapper', 'localmapper', 'all'], metavar='BACKEND',
                   help='also install the optional machine-learning atom-mapping backends, each in its own '
                        'environment (rxnmapper, localmapper, or all; no name means all; several hundred MB '
                        'with PyTorch). Without them map_reaction_atoms uses its built-in substructure method')
    p.add_argument('--opsin', action='store_true',
                   help=f'download the OPSIN {OPSIN_VERSION} JAR (SHA-256 verified) next to the shared venv')
    p.add_argument('--toolkit-path', help='toolkit source folder to build the runtime from (default: toolkit/ of this checkout)')
    p.add_argument('--backup-root', help=f'where replaced installations go (default: {data_dir() / "backups"})')
    p.add_argument('--apply', action='store_true', help='install; without it only the proposal is printed')
    ns = p.parse_args(argv)
    for extra in ns.extras or ():
        if not re.fullmatch(r'[a-z][a-z0-9_-]*', extra):
            p.error(f'invalid extra: {extra}')
    return ns


def main(argv=None):
    ns = parse(argv)
    if not (SOURCE / 'SKILL.md').is_file():
        raise SystemExit(f'Deployable Skill not found: {SOURCE}')
    if ns.runtime_only or ns.mapping is not None:
        ns.runtime = True
    targets = [] if ns.runtime_only else destinations(ns)
    backups = backup_root(ns)
    for target in targets:
        if target == SOURCE.resolve() or SOURCE.resolve() in target.parents:
            raise SystemExit(f'Destination must lie outside the repository Skill source: {target}')
        if target in backups.parents or backups == target:
            raise SystemExit('The backup folder must not be inside an installed Skill.')
    source_print = fingerprint(SOURCE)
    record = {
        'apply': ns.apply, 'source': str(SOURCE), 'source_fingerprint': source_print,
        'backup_root': str(backups),
        'installations': [{'destination': str(t), 'existing': t.exists()} for t in targets],
        'runtime': runtime_plan(ns, targets),
        'opsin': opsin_plan(ns),
        'mapping': {'backends': mapping_backends(ns)},
        'status': 'proposal',
    }
    if not ns.apply:
        print(json.dumps(record, indent=2))
        return 0

    for item, target in zip(record['installations'], targets):
        backup = install_one(target, source_print, backups)
        item.update(backup=str(backup) if backup else None, installed_fingerprint=fingerprint(target))
    record['status'] = 'installed'

    # A failed runtime install leaves usable Skill copies (docs, diagnostics) and is reported.
    code = 0
    runtime = record['runtime']
    if ns.runtime:
        try:
            install_runtime(runtime, targets[0] if targets else SOURCE)
            runtime['status'] = 'installed'
        except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
            runtime.update(status='failed', error=str(exc))
            record['status'] = 'installed_runtime_failed'
            code = 1
    if ns.runtime and runtime.get('status') == 'installed':
        runtime['local_config'] = [str(p) for p in record_runtime([*targets, SOURCE], runtime['python'])]
    mapping = record['mapping']
    if mapping['backends']:
        if runtime.get('status') == 'installed':
            mapping['status'] = 'installed' if install_mappers(runtime['python'], mapping['backends']) == 0 else 'failed'
        else:
            mapping['status'] = 'skipped: the runtime was not installed'
        if mapping['status'] != 'installed':
            code = 1
    opsin = record['opsin']
    if opsin['action'] == 'download':
        try:
            install_opsin(Path(opsin['path']).parent)
            opsin['status'] = 'installed'
        except OSError as exc:
            opsin.update(status='failed', error=str(exc))
            code = 1
    for target in targets:
        # Record the installed state so check_installation.py / cdx.py doctor detect later drift.
        check_installation.write_manifest(target)
    print(json.dumps(record, indent=2))
    return code


if __name__ == '__main__':
    raise SystemExit(main())
