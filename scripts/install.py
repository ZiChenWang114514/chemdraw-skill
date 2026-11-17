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
AGENT_ALIASES = {
    'codex': ('.agents/skills', '.agents/skills'),
    'antigravity': ('.gemini/antigravity/skills', '.agent/skills'),
    'windsurf': ('.codeium/windsurf/skills', '.windsurf/skills'),
    'cline': ('.cline/skills', '.cline/skills'),
    'roo': ('.roo/skills', '.roo/skills'),
    'goose': ('.config/goose/skills', '.goose/skills'),
    'trae': ('.trae/skills', '.trae/skills'),
    'kiro': ('.kiro/skills', '.kiro/skills'),
    'aider': ('.aider/skills', '.aider/skills'),
    'amp': ('.config/agents/skills', '.agents/skills'),
    'qwen': ('.qwen/skills', '.qwen/skills'),
    'continue': ('.continue/skills', '.continue/skills'),
    'zed': ('.zed/skills', '.zed/skills'),
    'openhands': ('.openhands/skills', '.openhands/skills'),
    'zcode': ('.zcode/skills', '.zcode/skills'),
    'dsh': ('.dsh/skills', '.dsh/skills'),
    'qoder': ('.qoder/skills', '.qoder/skills'),
    'codebuddy': ('.codebuddy/skills', '.codebuddy/skills'),
    'lingma': ('.lingma/skills', '.lingma/skills'),
    'comate': ('.comate/skills', '.comate/skills'),
    'bailian': ('.bailian/skills', '.bailian/skills'),
    'codegeex': ('.codegeex/skills', '.codegeex/skills'),
}
ALL_AGENTS = {**AGENTS, **AGENT_ALIASES}
EXTRA_AGENT_DIRS = {
    'codex': ('.codex',),
    'kimi': ('.kimi', '.kimi-code'),
    'windsurf': ('.windsurf', '.Windsurf'),
    'pi': ('.pi',),
    'opencode': ('.config/opencode', '.opencode'),
    'amp': ('.config/amp', '.amp'),
    'zed': ('.config/zed',),
    'zcode': ('.zcode',),
    'dsh': ('.dsh',),
    'qoder': ('.qoder', '.qoder-cn', '.qoder-cli'),
    'codebuddy': ('.codebuddy', '.workbuddy'),
    'trae': ('.trae', '.trae-cn'),
    'lingma': ('.lingma',),
    'comate': ('.comate',),
    'bailian': ('.bailian',),
    'codegeex': ('.codegeex',),
}
LEGACY_SKILL_DIRS = ('.codex/skills', '.kimi/skills', '.windsurf/skills')
# Never copied into an installation; runtime.local.json is written per installation.
IGNORED = ('__pycache__', '.pytest_cache', '.mypy_cache', '.ruff_cache', '*.pyc', '*.pyo',
           'manifest.json', 'runtime.local.json', 'tests')
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
    hashes = {k: v for k, v in check_installation.file_hashes(root).items()
              if k != 'runtime.local.json' and not k.startswith('tests/')}
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


def detect_agents(base, scope=0):
    """Detect existing agent parent folders under `base`, falling back to ['claude', 'agents']."""
    base = Path(base)
    found = []
    for agent, folders in ALL_AGENTS.items():
        candidates = [base / Path(folders[scope]).parent]
        candidates.extend(base / rel for rel in EXTRA_AGENT_DIRS.get(agent, ()))
        if any(p.is_dir() for p in candidates):
            found.append(agent)
    return found or ['claude', 'agents']


def resolve_agents(agents, base, scope=0):
    out = []
    for agent in agents:
        expanded = detect_agents(base, scope) if agent == 'auto' else [agent]
        for item in expanded:
            if item not in out:
                out.append(item)
    return out


def _is_link_to_source(target, source_resolved=None):
    """True when `target` is a distinct path (symlink/junction) that resolves to `SOURCE`."""
    source_resolved = source_resolved or SOURCE.resolve()
    lexical = Path(os.path.abspath(target))
    try:
        return lexical != source_resolved and target.exists() and target.resolve() == source_resolved
    except OSError:
        return False


def destinations(ns):
    if ns.destination:
        return [Path(os.path.abspath(Path(d).expanduser())) for d in ns.destination]
    base = (Path(ns.project).expanduser() if ns.project else Path.home()).resolve()
    scope = 1 if ns.project else 0
    seen, out = set(), []
    for agent in resolve_agents(ns.agent, base, scope):
        rels = [ALL_AGENTS[agent][scope]]
        if scope == 0:
            if agent == 'qoder' and (base / '.qoder-cn').is_dir():
                rels.append('.qoder-cn/skills')
            elif agent == 'trae' and (base / '.trae-cn').is_dir():
                rels.append('.trae-cn/skills')
            elif agent == 'codebuddy' and (base / '.workbuddy').is_dir():
                rels.append('.workbuddy/connectors/skills')
        for rel in rels:
            target = Path(os.path.abspath(base / rel / SKILL_NAME))
            if target not in seen:
                seen.add(target)
                out.append(target)
    return out


def legacy_shadow_warnings(base, targets, source_print):
    """Warn when an older legacy user-scope Skill copy (e.g. ~/.codex/skills/chemdraw) may shadow targets."""
    base = Path(base)
    target_set = {Path(os.path.abspath(t)) for t in targets}
    source_resolved = SOURCE.resolve()
    warnings = []
    for rel in LEGACY_SKILL_DIRS:
        folder = Path(os.path.abspath(base / rel / SKILL_NAME))
        if folder in target_set or not (folder / 'SKILL.md').is_file():
            continue
        try:
            if folder.resolve() == source_resolved:
                continue
            other_print = fingerprint(folder)
        except OSError:
            other_print = 'unreadable'
        if other_print != source_print:
            warnings.append(
                f'Legacy Skill copy at {folder} differs from current source and may shadow newer '
                f'agent Skill folders; update it with '
                f'`python scripts/install.py --destination "{folder}" --apply` or remove it.'
            )
    return warnings


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


def probe_candidates(requested):
    """Return (first supported 64-bit Python 3.10-3.13 command, rejected [(command, info), ...])."""
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
    rejected = []
    seen = set()
    for command in commands:
        info = probe_python(command)
        if supported(info):
            return command, rejected
        if info is not None:
            key = (command[0], info)
            if key not in seen:
                seen.add(key)
                rejected.append((command, info))
    return None, rejected


def base_python(requested):
    """First command that runs a 64-bit Python 3.10-3.13 (the toolkit's supported range)."""
    return probe_candidates(requested)[0]


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
        base, rejected = probe_candidates(ns.python)
        if base is None:
            detail = ', '.join(
                f'Python {maj}.{mn} ({bits}-bit) at {" ".join(cmd)}'
                for cmd, (maj, mn, bits) in rejected[:3]
            )
            found_clause = f'Found unsupported {detail}; ' if detail else ''
            raise SystemExit(
                'The runtime needs a 64-bit Python 3.10-3.13 and none was found. '
                f'{found_clause}Python 3.14 and newer are not supported by the toolkit yet. '
                'Install Python 3.12 — e.g. `uv python install 3.12` (then `--python "<interpreter>"`) '
                'or the python.org 64-bit 3.12 installer (Windows: `py -3.12`) — and re-run.'
            )
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
    """True when cdx.py's default search (a `chemdraw-venv` beside the Skill, then the shared venv) would not
    reach `python` first."""
    python = Path(python).resolve()
    beside = venv_python(skill.parent / 'chemdraw-venv')
    if python == beside.resolve():
        return False
    return python != venv_python(cdx.default_runtime_dir()).resolve() or beside.is_file()


def record_runtime(skills, python):
    """Point every Skill folder at `python`: write runtime.local.json where cdx.py would not find it by default,
    and remove a runtime.local.json that would otherwise keep cdx.py on an older interpreter.

    The repository checkout (SOURCE) is included so `cdx.py` works from the checkout too; the
    file is ignored by Git and never copied into installations."""
    written, removed = [], []
    for skill in skills:
        config = skill / 'runtime.local.json'
        if needs_local_config(skill, python):
            config.write_text(json.dumps({'runtime_python': str(python)}, indent=2) + '\n', encoding='utf-8')
            written.append(config)
        elif config.is_file():
            config.unlink()
            removed.append(config)
    return {'written': written, 'removed': removed}


def parse(argv):
    p = argparse.ArgumentParser(description=__doc__.split('\n\n')[0],
                                formatter_class=argparse.RawDescriptionHelpFormatter,
                                epilog='Agents: ' + ', '.join(f'{k} (~/{u}, <project>/{q})'
                                                             for k, (u, q) in ALL_AGENTS.items()))
    p.add_argument('--agent', nargs='+', choices=sorted([*ALL_AGENTS, 'auto']), default=['claude'],
                   help='agent Skill folder(s) to install into, or auto to detect existing agent folders (default: claude)')
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
    p.add_argument('--mcp', action='store_true',
                   help='register the cdxml-toolkit MCP server config for targeted agents')
    p.add_argument('--toolkit-path', help='toolkit source folder to build the runtime from (default: toolkit/ of this checkout)')
    p.add_argument('--backup-root', help=f'where replaced installations go (default: {data_dir() / "backups"})')
    p.add_argument('--apply', action='store_true', help='install; without it only the proposal is printed')
    ns = p.parse_args(argv)
    for extra in ns.extras or ():
        if not re.fullmatch(r'[a-z][a-z0-9_-]*', extra):
            p.error(f'invalid extra: {extra}')
    return ns


def _strip_jsonc(text):
    out = []
    i = 0
    in_str = False
    escape = False
    n = len(text)
    while i < n:
        ch = text[i]
        if in_str:
            out.append(ch)
            if escape:
                escape = False
            elif ch == '\\':
                escape = True
            elif ch == '"':
                in_str = False
            i += 1
            continue
        if ch == '"':
            in_str = True
            out.append(ch)
            i += 1
        elif ch == '/' and i + 1 < n and text[i + 1] == '/':
            while i < n and text[i] not in '\r\n':
                i += 1
        elif ch == '/' and i + 1 < n and text[i + 1] == '*':
            i += 2
            while i + 1 < n and not (text[i] == '*' and text[i + 1] == '/'):
                i += 1
            i += 2
        else:
            out.append(ch)
            i += 1
    cleaned = re.sub(r',(\s*[}\]])', r'\1', ''.join(out))
    return cleaned


def _appdata_base(home):
    home = Path(home).resolve()
    real_home = Path(os.environ.get('USERPROFILE') or os.environ.get('HOME') or Path.home()).resolve()
    if os.name == 'nt':
        if home == real_home and os.environ.get('APPDATA'):
            return Path(os.environ['APPDATA']).resolve()
        return (home / 'AppData' / 'Roaming').resolve()
    if sys.platform == 'darwin':
        return (home / 'Library' / 'Application Support').resolve()
    if home == real_home and os.environ.get('XDG_CONFIG_HOME'):
        return Path(os.environ['XDG_CONFIG_HOME']).resolve()
    return (home / '.config').resolve()


def _mcp_specs(agents, home, python_cmd):
    """Build native MCP / Skill configuration descriptors for selected harnesses."""
    home = Path(home)
    appdata = _appdata_base(home)
    specs = []
    seen_paths = set()

    def add(agent, path, fmt, **extra):
        resolved = Path(os.path.abspath(path))
        if resolved in seen_paths:
            return
        seen_paths.add(resolved)
        specs.append({'agent': agent, 'path': str(resolved), 'format': fmt, **extra})

    for agent in agents:
        if agent == 'codex':
            add(agent, home / '.codex' / 'config.toml', 'codex_toml')
        elif agent == 'claude':
            add(agent, home / '.claude.json', 'json_key', root_key='mcpServers', entry_key='cdxml-toolkit',
                value={'command': python_cmd, 'args': ['-m', 'cdxml_toolkit.mcp_runtime']})
        elif agent == 'cursor':
            add(agent, home / '.cursor' / 'mcp.json', 'json_key', root_key='mcpServers', entry_key='cdxml-toolkit',
                value={'command': python_cmd, 'args': ['-m', 'cdxml_toolkit.mcp_runtime']})
        elif agent == 'windsurf':
            add(agent, home / '.codeium' / 'windsurf' / 'mcp_config.json', 'json_key', root_key='mcpServers',
                entry_key='cdxml-toolkit', value={'command': python_cmd, 'args': ['-m', 'cdxml_toolkit.mcp_runtime']})
        elif agent == 'gemini':
            add(agent, home / '.gemini' / 'settings.json', 'json_key', root_key='mcpServers', entry_key='cdxml-toolkit',
                value={'command': python_cmd, 'args': ['-m', 'cdxml_toolkit.mcp_runtime']})
        elif agent == 'copilot':
            add(agent, home / '.copilot' / 'mcp-config.json', 'json_key', root_key='mcpServers', entry_key='cdxml-toolkit',
                value={'type': 'local', 'command': python_cmd, 'args': ['-m', 'cdxml_toolkit.mcp_runtime'], 'tools': ['*']})
            vsc_mcp = appdata / 'Code' / 'User' / 'mcp.json'
            if vsc_mcp.parent.is_dir():
                add(agent, vsc_mcp, 'json_key', root_key='servers', entry_key='cdxml-toolkit',
                    value={'type': 'stdio', 'command': python_cmd, 'args': ['-m', 'cdxml_toolkit.mcp_runtime']})
        elif agent == 'opencode':
            oc_dir = home / '.config' / 'opencode'
            target = oc_dir / 'opencode.jsonc' if (oc_dir / 'opencode.jsonc').is_file() else oc_dir / 'opencode.json'
            add(agent, target, 'opencode_json')
        elif agent == 'antigravity':
            add(agent, home / '.gemini' / 'antigravity' / 'mcp_config.json', 'json_key', root_key='mcpServers',
                entry_key='cdxml-toolkit', value={'command': python_cmd, 'args': ['-m', 'cdxml_toolkit.mcp_runtime']})
        elif agent == 'kimi':
            add(agent, home / '.kimi-code' / 'mcp.json', 'json_key', root_key='mcpServers', entry_key='cdxml-toolkit',
                value={'command': python_cmd, 'args': ['-m', 'cdxml_toolkit.mcp_runtime']})
            add(agent, home / '.kimi' / 'mcp.json', 'json_key', root_key='mcpServers', entry_key='cdxml-toolkit',
                value={'command': python_cmd, 'args': ['-m', 'cdxml_toolkit.mcp_runtime']})
        elif agent == 'zcode':
            add(agent, home / '.zcode' / 'cli' / 'config.json', 'zcode_json')
        elif agent == 'dsh':
            add(agent, home / '.dsh' / 'cordis.patch.yml', 'dsh_cordis_yaml')
        elif agent == 'qoder':
            add(agent, home / '.qoder' / 'mcp.json', 'json_key', root_key='mcpServers', entry_key='cdxml-toolkit',
                value={'command': python_cmd, 'args': ['-m', 'cdxml_toolkit.mcp_runtime']})
            if (home / '.qoder-cn').is_dir():
                add(agent, home / '.qoder-cn' / 'mcp.json', 'json_key', root_key='mcpServers', entry_key='cdxml-toolkit',
                    value={'command': python_cmd, 'args': ['-m', 'cdxml_toolkit.mcp_runtime']})
        elif agent == 'codebuddy':
            add(agent, home / '.codebuddy' / 'mcp.json', 'json_key', root_key='mcpServers', entry_key='cdxml-toolkit',
                value={'command': python_cmd, 'args': ['-m', 'cdxml_toolkit.mcp_runtime']})
            if (home / '.workbuddy').is_dir():
                add(agent, home / '.workbuddy' / 'mcp.json', 'json_key', root_key='mcpServers', entry_key='cdxml-toolkit',
                    value={'command': python_cmd, 'args': ['-m', 'cdxml_toolkit.mcp_runtime']})
        elif agent == 'lingma':
            add(agent, home / '.lingma' / 'mcp.json', 'json_key', root_key='mcpServers', entry_key='cdxml-toolkit',
                value={'command': python_cmd, 'args': ['-m', 'cdxml_toolkit.mcp_runtime']})
        elif agent == 'comate':
            add(agent, home / '.comate' / 'mcp.json', 'json_key', root_key='mcpServers', entry_key='cdxml-toolkit',
                value={'command': python_cmd, 'args': ['-m', 'cdxml_toolkit.mcp_runtime']})
        elif agent == 'codegeex':
            add(agent, home / '.codegeex' / 'mcp.json', 'json_key', root_key='mcpServers', entry_key='cdxml-toolkit',
                value={'command': python_cmd, 'args': ['-m', 'cdxml_toolkit.mcp_runtime']})
        elif agent == 'cline':
            add(agent, home / '.cline' / 'data' / 'settings' / 'cline_mcp_settings.json', 'json_key',
                root_key='mcpServers', entry_key='cdxml-toolkit',
                value={'command': python_cmd, 'args': ['-m', 'cdxml_toolkit.mcp_runtime'], 'disabled': False})
            vsc = appdata / 'Code' / 'User' / 'globalStorage' / 'saoudrizwan.claude-dev' / 'settings' / 'cline_mcp_settings.json'
            if vsc.parent.parent.is_dir():
                add(agent, vsc, 'json_key', root_key='mcpServers', entry_key='cdxml-toolkit',
                    value={'command': python_cmd, 'args': ['-m', 'cdxml_toolkit.mcp_runtime'], 'disabled': False})
        elif agent == 'roo':
            vsc = appdata / 'Code' / 'User' / 'globalStorage' / 'rooveterinaryinc.roo-cline' / 'settings' / 'mcp_settings.json'
            target = vsc if vsc.parent.parent.is_dir() else (home / '.roo' / 'mcp.json')
            add(agent, target, 'json_key', root_key='mcpServers', entry_key='cdxml-toolkit',
                value={'command': python_cmd, 'args': ['-m', 'cdxml_toolkit.mcp_runtime'], 'disabled': False})
        elif agent == 'goose':
            add(agent, home / '.config' / 'goose' / 'config.yaml', 'goose_yaml')
        elif agent == 'trae':
            add(agent, appdata / 'Trae' / 'User' / 'mcp.json', 'json_key', root_key='mcpServers',
                entry_key='cdxml-toolkit', value={'command': python_cmd, 'args': ['-m', 'cdxml_toolkit.mcp_runtime']})
            for cn_variant in ('TRAE SOLO', 'Trae CN'):
                cn_mcp = appdata / cn_variant / 'User' / 'mcp.json'
                if cn_mcp.parent.parent.is_dir():
                    add(agent, cn_mcp, 'json_key', root_key='mcpServers', entry_key='cdxml-toolkit',
                        value={'command': python_cmd, 'args': ['-m', 'cdxml_toolkit.mcp_runtime']})
        elif agent == 'kiro':
            add(agent, home / '.kiro' / 'settings' / 'mcp.json', 'json_key', root_key='mcpServers',
                entry_key='cdxml-toolkit', value={'command': python_cmd, 'args': ['-m', 'cdxml_toolkit.mcp_runtime']})
        elif agent == 'qwen':
            add(agent, home / '.qwen' / 'settings.json', 'json_key', root_key='mcpServers',
                entry_key='cdxml-toolkit', value={'command': python_cmd, 'args': ['-m', 'cdxml_toolkit.mcp_runtime']})
        elif agent == 'amp':
            add(agent, home / '.config' / 'amp' / 'settings.json', 'json_key', root_key='amp.mcpServers',
                entry_key='cdxml-toolkit', value={'command': python_cmd, 'args': ['-m', 'cdxml_toolkit.mcp_runtime']})
        elif agent == 'continue':
            add(agent, home / '.continue' / 'mcpServers' / 'cdxml-toolkit.yaml', 'continue_yaml')
        elif agent == 'zed':
            zed_dir = appdata / 'Zed' if os.name == 'nt' else home / '.config' / 'zed'
            add(agent, zed_dir / 'settings.json', 'json_key', root_key='context_servers',
                entry_key='cdxml-toolkit', value={'command': python_cmd, 'args': ['-m', 'cdxml_toolkit.mcp_runtime']})
        elif agent == 'aider':
            add(agent, home / '.aider.conf.yml', 'aider_yaml')
    return specs


def _upsert_codex_toml(path, python_cmd):
    existing = path.read_text(encoding='utf-8') if path.is_file() else ''
    escaped = python_cmd.replace('\\', '\\\\')
    block = (
        '[mcp_servers.cdxml-toolkit]\n'
        f'command = "{escaped}"\n'
        'args = ["-m", "cdxml_toolkit.mcp_runtime"]\n'
    )
    pattern = re.compile(r'(?ms)^\[mcp_servers\.cdxml-toolkit\]\r?\n.*?(?=^\[|\Z)')
    if pattern.search(existing):
        updated = pattern.sub(lambda _match: block + '\n', existing, count=1)
    else:
        sep = '' if not existing or existing.endswith('\n') else '\n'
        updated = existing + (sep + '\n' if existing else '') + block
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(updated, encoding='utf-8')


def _upsert_goose_yaml(path, python_cmd):
    existing = path.read_text(encoding='utf-8') if path.is_file() else ''
    quoted = json.dumps(python_cmd)
    entry = (
        '  cdxml-toolkit:\n'
        '    enabled: true\n'
        '    type: stdio\n'
        '    name: cdxml-toolkit\n'
        f'    cmd: {quoted}\n'
        '    args:\n'
        '    - -m\n'
        '    - cdxml_toolkit.mcp_runtime\n'
        '    timeout: 600\n'
        '    description: ChemDraw CDXML and 3D Mol* / 2D Studio chemistry toolkit\n'
    )
    entry_re = re.compile(r'(?ms)^  cdxml-toolkit:\r?\n(?:    .*\r?\n)*')
    if entry_re.search(existing):
        updated = entry_re.sub(lambda _match: entry, existing, count=1)
    elif re.search(r'(?m)^extensions:\s*$', existing):
        updated = re.sub(r'(?m)^extensions:\s*$', lambda _match: 'extensions:\n' + entry.rstrip('\n'), existing, count=1)
    else:
        sep = '' if not existing or existing.endswith('\n') else '\n'
        updated = existing + (sep if existing else '') + 'extensions:\n' + entry
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(updated, encoding='utf-8')


def _upsert_aider_yaml(path, skill_md_path):
    existing = path.read_text(encoding='utf-8') if path.is_file() else ''
    line = f'read:\n  - {json.dumps(str(skill_md_path))}\n'
    if str(skill_md_path) in existing:
        return
    if re.search(r'(?m)^read:\s*$', existing):
        updated = re.sub(r'(?m)^read:\s*$', lambda _match: f'read:\n  - {json.dumps(str(skill_md_path))}', existing, count=1)
    else:
        sep = '' if not existing or existing.endswith('\n') else '\n'
        updated = existing + (sep if existing else '') + line
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(updated, encoding='utf-8')


def _upsert_dsh_cordis_yaml(path, python_cmd):
    existing = path.read_text(encoding='utf-8') if path.is_file() else ''
    quoted = json.dumps(python_cmd)
    block = (
        '# BEGIN chemdraw-skill mcp\n'
        '- insert:\n'
        '    - id: mcp-cdxml-toolkit\n'
        '      name: "@deepseek-ai/dsh-mcp-client"\n'
        '      config:\n'
        '        transport: stdio\n'
        '        serverName: cdxml_toolkit\n'
        f'        command: {quoted}\n'
        '        args:\n'
        '          - "-m"\n'
        '          - "cdxml_toolkit.mcp_runtime"\n'
        '# END chemdraw-skill mcp\n'
    )
    marker_re = re.compile(r'(?ms)^# BEGIN chemdraw-skill mcp\r?\n.*?^# END chemdraw-skill mcp\r?\n?')
    if marker_re.search(existing):
        updated = marker_re.sub(lambda _match: block, existing, count=1)
    elif existing.strip() in ('', '[]'):
        updated = block
    else:
        sep = '' if existing.endswith('\n') else '\n'
        updated = existing + sep + block
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(updated, encoding='utf-8')


def apply_mcp_configs(specs, python_cmd, skill_md_path):
    results = []
    for spec in specs:
        path = Path(spec['path'])
        fmt = spec['format']
        try:
            if fmt == 'codex_toml':
                _upsert_codex_toml(path, python_cmd)
            elif fmt == 'goose_yaml':
                _upsert_goose_yaml(path, python_cmd)
            elif fmt == 'dsh_cordis_yaml':
                _upsert_dsh_cordis_yaml(path, python_cmd)
            elif fmt == 'zcode_json':
                raw = path.read_text(encoding='utf-8') if path.is_file() else '{}'
                data = json.loads(_strip_jsonc(raw) or '{}')
                if not isinstance(data, dict):
                    data = {}
                mcp_obj = data.get('mcp')
                if not isinstance(mcp_obj, dict):
                    mcp_obj = {}
                servers = mcp_obj.get('servers')
                if not isinstance(servers, dict):
                    servers = {}
                servers['cdxml-toolkit'] = {
                    'command': python_cmd,
                    'args': ['-m', 'cdxml_toolkit.mcp_runtime'],
                }
                mcp_obj['servers'] = servers
                data['mcp'] = mcp_obj
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
            elif fmt == 'continue_yaml':
                content = (
                    'name: ChemDraw Toolkit MCP\n'
                    'version: 1.0.0\n'
                    'schema: v1\n'
                    'mcpServers:\n'
                    '  - name: cdxml-toolkit\n'
                    f'    command: {json.dumps(python_cmd)}\n'
                    '    args:\n'
                    '      - -m\n'
                    '      - cdxml_toolkit.mcp_runtime\n'
                )
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding='utf-8')
            elif fmt == 'aider_yaml':
                _upsert_aider_yaml(path, skill_md_path)
            elif fmt == 'opencode_json':
                raw = path.read_text(encoding='utf-8') if path.is_file() else '{}'
                data = json.loads(_strip_jsonc(raw) or '{}')
                if not isinstance(data, dict):
                    data = {}
                mcp_map = data.get('mcp')
                if not isinstance(mcp_map, dict):
                    mcp_map = {}
                # Repair stale legacy chemdraw entry if pointing to removed scripts/mcp_server.py
                legacy = mcp_map.get('chemdraw')
                if isinstance(legacy, dict) and any('mcp_server.py' in str(c) for c in (legacy.get('command') or [])):
                    mcp_map.pop('chemdraw', None)
                mcp_map['cdxml-toolkit'] = {
                    'type': 'local',
                    'command': [python_cmd, '-m', 'cdxml_toolkit.mcp_runtime'],
                    'enabled': True,
                }
                data['mcp'] = mcp_map
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
            elif fmt == 'json_key':
                raw = path.read_text(encoding='utf-8') if path.is_file() else '{}'
                data = json.loads(_strip_jsonc(raw) or '{}')
                if not isinstance(data, dict):
                    data = {}
                section = data.get(spec['root_key'])
                if not isinstance(section, dict):
                    section = {}
                section[spec['entry_key']] = spec['value']
                data[spec['root_key']] = section
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
            results.append({**spec, 'status': 'configured'})
        except Exception as exc:
            results.append({**spec, 'status': 'failed', 'error': str(exc)})
    return results


def main(argv=None):
    ns = parse(argv)
    if not (SOURCE / 'SKILL.md').is_file():
        raise SystemExit(f'Deployable Skill not found: {SOURCE}')
    if ns.runtime_only or ns.mapping is not None:
        ns.runtime = True
    targets = [] if ns.runtime_only else destinations(ns)
    backups = backup_root(ns)
    source_resolved = SOURCE.resolve()
    for target in targets:
        resolved_target = target.resolve() if target.exists() else None
        if target == source_resolved or source_resolved in target.parents or (
            resolved_target is not None and source_resolved in resolved_target.parents
        ):
            raise SystemExit(f'Destination must lie outside the repository Skill source: {target}')
        if target in backups.parents or backups == target:
            raise SystemExit('The backup folder must not be inside an installed Skill.')
    source_print = fingerprint(SOURCE)
    installations = [
        {
            'destination': str(t),
            'existing': t.exists(),
            **({'linked_to_source': True} if _is_link_to_source(t, source_resolved) else {}),
        }
        for t in targets
    ]
    warnings = [] if (ns.project or ns.destination or ns.runtime_only) else legacy_shadow_warnings(
        Path.home().resolve(), targets, source_print
    )
    record = {
        'apply': ns.apply, 'source': str(SOURCE), 'source_fingerprint': source_print,
        'backup_root': str(backups),
        'installations': installations,
        'runtime': runtime_plan(ns, targets),
        'opsin': opsin_plan(ns),
        'mapping': {'backends': mapping_backends(ns)},
        **({'warnings': warnings} if warnings else {}),
        'status': 'proposal',
    }
    home_dir = Path.home().resolve()
    mcp_python = (
        record['runtime'].get('python')
        if record['runtime'].get('action') in ('create', 'reuse')
        else str(venv_python(Path(ns.runtime_dir).expanduser().resolve() if ns.runtime_dir else cdx.default_runtime_dir()))
    )
    resolved_agents = [] if (ns.project or ns.destination or ns.runtime_only) else resolve_agents(
        ns.agent, home_dir, 0
    )
    mcp_specs = _mcp_specs(resolved_agents, home_dir, mcp_python) if ns.mcp else []
    if ns.mcp:
        record['mcp'] = mcp_specs
    if not ns.apply:
        base_root = Path(ns.project).expanduser().resolve() if ns.project else Path.home()
        detected = detect_agents(base_root, 1 if ns.project else 0)
        record['detected_agents'] = detected
        if not ns.runtime_only and not ns.destination and ns.agent == ['claude'] and not ns.runtime:
            hint = ('Dry-run proposal only (nothing written). Add --apply to install, '
                    'or run: python scripts/install.py --agent auto --runtime --apply')
        else:
            hint = 'Dry-run proposal only (nothing written). Re-run with --apply to perform this installation.'
        record['apply_hint'] = hint
        if sys.stderr.isatty():
            log(hint)
        print(json.dumps(record, indent=2))
        return 0

    for item, target in zip(record['installations'], targets):
        if _is_link_to_source(target, source_resolved):
            item.update(backup=None, installed_fingerprint=source_print)
        else:
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
        non_linked = [t for t in targets if not _is_link_to_source(t, source_resolved)]
        recorded = record_runtime([*non_linked, SOURCE], runtime['python'])
        runtime['local_config'] = [str(p) for p in recorded['written']]
        runtime['local_config_removed'] = [str(p) for p in recorded['removed']]
        explicit = os.environ.get('CHEMDRAW_MCP_PYTHON')
        if explicit and Path(explicit).resolve() != Path(runtime['python']).resolve():
            runtime['overridden_by'] = f'CHEMDRAW_MCP_PYTHON={explicit} (cdx.py uses it before this runtime)'
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
        if _is_link_to_source(target, source_resolved):
            continue
        # Record the installed state so check_installation.py / cdx.py doctor detect later drift.
        check_installation.write_manifest(target)
    if ns.mcp and mcp_specs:
        skill_ref = (targets[0] if targets else SOURCE) / 'SKILL.md'
        record['mcp'] = apply_mcp_configs(mcp_specs, mcp_python, skill_ref)
        if any(item.get('status') == 'failed' for item in record['mcp']):
            code = 1
    print(json.dumps(record, indent=2))
    return code


if __name__ == '__main__':
    raise SystemExit(main())
