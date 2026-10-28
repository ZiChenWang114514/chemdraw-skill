#!/usr/bin/env python3
"""Single command-line entry point for the ChemDraw skill.

    python3 <skill>/scripts/cdx.py <command> ...     (Windows: python or py)

Any Python 3.9+ can start it: when the current interpreter lacks
cdxml-toolkit, cdx.py re-launches itself in the toolkit runtime (see
runtime_candidates for the search order). Every tool call goes through the toolkit's
isolated worker, so the native ChemDraw lock, worker timeouts and the JSON
envelope are preserved.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time

SKILL_ROOT = Path(__file__).resolve().parents[1]
REFERENCES = SKILL_ROOT / 'references'
SIGNATURES = REFERENCES / 'mcp-signatures.md'
# Inventory shards that regen-catalog owns; the curated shards beside them are never touched.
CATALOG_SHARDS = ('chemscript-', 'com-', 'cdxml-attributes-')
BASELINE = SKILL_ROOT / 'runtime.json'
SUMMARY_LIMIT = 6000
REEXEC_FLAG = 'CHEMDRAW_CDX_REEXEC'
# Written by the installer when the runtime lives somewhere cdx.py would not look.
LOCAL_CONFIG = SKILL_ROOT / 'runtime.local.json'


def extras_for(platform):
    """Modules each toolkit extra needs; ChemDraw is driven by COM/.NET on Windows, AppleScript on macOS."""
    windows = platform == 'win32'
    return {'publication': ['openpyxl'], 'scientific': ['numpy', 'scipy', 'matplotlib', 'nmrglue'],
            'office': (['win32com.client'] if windows else []) + ['docx', 'pptx', 'olefile'],
            'analysis': ['pdfplumber', 'fitz'], 'image': ['cv2', 'pytesseract'],
            # macOS answers ChemScript calls with ChemDraw and OPSIN instead of the .NET SDK.
            'chemscript': ['clr'] if windows else ['py2opsin']}


EXTRAS = extras_for(sys.platform)


# ------------------------------------------------------------- runtime bootstrap
def _runs(python, code, timeout):
    """True when `python -c code` exits 0. A venv whose base interpreter was removed or is
    blocked fails here (its launcher exits without running Python), so it is skipped instead
    of producing an opaque launcher error later."""
    try:
        probe = subprocess.run([str(python), '-c', code], capture_output=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired):
        return False
    return probe.returncode == 0


def _has_toolkit(python):
    """True when `python` starts and its environment contains cdxml_toolkit.mcp_runtime."""
    root = Path(python).resolve().parent
    if root.name.lower() in ('scripts', 'bin'):
        root = root.parent
    patterns = ('Lib/site-packages/cdxml_toolkit/mcp_runtime', 'lib/python3*/site-packages/cdxml_toolkit/mcp_runtime')
    if any(glob.glob(str(root / pattern)) for pattern in patterns):
        return _runs(python, 'import sys', 30)
    # Editable (pip -e) installs live outside site-packages: ask the interpreter.
    return _runs(python, 'import cdxml_toolkit.mcp_runtime', 60)


def _interpreter(env_root):
    for name in ('Scripts/python.exe', 'python.exe', 'bin/python3', 'bin/python'):
        if (env_root / name).is_file():
            return env_root / name
    return None


def default_runtime_dir():
    """Shared runtime venv used by every agent's copy of the skill."""
    if os.name == 'nt':
        base = os.environ.get('LOCALAPPDATA') or str(Path.home() / 'AppData' / 'Local')
    else:
        base = os.environ.get('XDG_DATA_HOME') or str(Path.home() / '.local' / 'share')
    return Path(base) / 'chemdraw-skill' / 'venv'


def runtime_candidates():
    """Ordered runtime interpreters: CHEMDRAW_MCP_PYTHON, runtime.local.json,
    a `chemdraw-venv` beside the skill folder, the shared venv, conda env `cdxml`."""
    found = []
    explicit = os.environ.get('CHEMDRAW_MCP_PYTHON')
    if explicit:
        found.append(('CHEMDRAW_MCP_PYTHON', Path(explicit)))
    try:
        local = json.loads(LOCAL_CONFIG.read_text(encoding='utf-8')).get('runtime_python')
        if local:
            found.append(('runtime.local.json', Path(local)))
    except (OSError, ValueError, AttributeError):
        pass
    for source, env_root in (('chemdraw-venv', SKILL_ROOT.parent / 'chemdraw-venv'),
                             ('shared venv', default_runtime_dir())):
        python = _interpreter(env_root)
        if python:
            found.append((source, python))
    registry = Path.home() / '.conda' / 'environments.txt'
    if registry.is_file():
        for line in registry.read_text(encoding='utf-8', errors='ignore').splitlines():
            env_root = Path(line.strip())
            if env_root.name.lower() == 'cdxml' and _interpreter(env_root):
                found.append(('conda cdxml', _interpreter(env_root)))
    return found


def _baseline():
    try:
        value = json.loads(BASELINE.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {}
    return value if isinstance(value, dict) else {}


def install_help():
    """How to get a runtime, from a repository checkout or from the Skill folder alone."""
    python = 'Scripts\\python.exe' if os.name == 'nt' else 'bin/python'
    venv = default_runtime_dir()
    return [
        'Repository checkout: python scripts/install.py --runtime --apply '
        '(add --agent/--destination to choose where the Skill is installed).',
        f'Skill folder only: python -m venv "{venv}", then '
        f'"{venv / python}" "{Path(__file__).resolve().parent / "install_runtime.py"}" '
        '--extras publication scientific office analysis image chemscript',
        f'Repository: {_baseline().get("repository", "see runtime.json")}',
        'Or point CHEMDRAW_MCP_PYTHON at an interpreter that has the toolkit installed.',
    ]


def _ensure_runtime(argv):
    try:
        import cdxml_toolkit.mcp_runtime  # noqa: F401
        # Do not leak the loop guard into child processes (nested cdx.py calls must re-launch normally).
        os.environ.pop(REEXEC_FLAG, None)
        return
    except ImportError:
        pass
    if os.environ.get(REEXEC_FLAG):
        raise SystemExit(f'cdx.py: the selected runtime {sys.executable} cannot import cdxml_toolkit.')
    for source, python in runtime_candidates():
        if python.is_file() and _has_toolkit(python):
            env = dict(os.environ, **{REEXEC_FLAG: '1'})
            raise SystemExit(subprocess.call([str(python), str(Path(__file__).resolve()), *argv], env=env))
    searched = ['CHEMDRAW_MCP_PYTHON', str(LOCAL_CONFIG), str(SKILL_ROOT.parent / 'chemdraw-venv'),
                str(default_runtime_dir()), 'conda env "cdxml"']
    if argv[:1] == ['doctor']:
        print(json.dumps({'runtime': 'missing', 'python': sys.version.split()[0], 'searched': searched,
                          'install': install_help(),
                          'note': 'The runtime needs a 64-bit Python 3.10-3.13; cdx.py itself runs on 3.9+.'},
                         ensure_ascii=False, indent=2))
        raise SystemExit(2)
    sys.stderr.write(
        'cdx.py: no working cdxml-toolkit runtime found.\n'
        f'Looked for: {", ".join(searched)} (candidates whose interpreter does not start are skipped).\n'
        + ''.join(f'- {line}\n' for line in install_help()))
    raise SystemExit(2)


def _chemscript_lib():
    """ChemScript's Python folder from a standard ChemOffice install, if any."""
    roots = {os.environ.get(k) for k in ('ProgramFiles', 'ProgramW6432', 'ProgramFiles(x86)')}
    roots |= {rf'{d}:\Program Files' for d in 'CDE'}
    for root in sorted(r for r in roots if r):
        hits = sorted(glob.glob(os.path.join(root, '*', 'ChemOffice*', 'ChemScript', 'Lib')))
        if hits:
            return hits[-1]
    return None


def _chemscript_env(env=None):
    """Environment for the ChemScript bridge subprocess, without a global PYTHONPATH."""
    env = dict(os.environ if env is None else env)
    parts = [p for p in env.get('PYTHONPATH', '').split(os.pathsep) if p]
    if not any('ChemScript' in p for p in parts):
        found = _chemscript_lib()
        if found:
            parts.append(found)
    if parts:
        env['PYTHONPATH'] = os.pathsep.join(parts)
    return env


def _worker(tool, kwargs, args=()):
    from cdxml_toolkit.mcp_runtime.mcp_server import _run_worker
    from cdxml_toolkit.mcp_runtime.tool_registry import build_registry
    spec = build_registry().get(tool)
    if spec is None:
        raise SystemExit(f'Unknown tool {tool!r}; run `cdx.py tools`. If the Skill documents it, the runtime '
                         'may be older than the Skill: `cdx.py doctor` reports runtime_matches_skill.')
    return _run_worker(tool, list(args), kwargs, timeout_seconds=spec.timeout_seconds)


def _layers(result):
    out, cur = [], result
    for _ in range(8):
        if isinstance(cur, str):
            try:
                cur = json.loads(cur)
            except ValueError:
                break
        if not isinstance(cur, dict):
            break
        out.append(cur)
        cur = cur.get('result')
    return out


def _error_id(result):
    """{'error_id': ...} when the worker logged the failure (read worker-<id>.log, see `doctor --paths`)."""
    for layer in _layers(result):
        error, meta = layer.get('error'), layer.get('metadata')
        found = (error.get('id') if isinstance(error, dict) else None) or \
            (meta.get('error_id') if isinstance(meta, dict) else None)
        if found:
            return {'error_id': found}
    return {}


def _summary(tool, result, path=None):
    layers = _layers(result)
    failed = any(x.get('ok') is False or x.get('error') for x in layers)
    errors = [x.get('error') for x in layers if x.get('error')]
    warnings = sum(len(x['warnings']) if isinstance(x.get('warnings'), list) else int(bool(x.get('warnings')))
                   for x in layers)
    out = {'ok': bool(layers) and layers[0].get('ok') is True and not failed, 'tool': tool,
           'warning_count': warnings}
    if errors:
        out['error'] = errors[-1]
    out.update(_error_id(result))
    if path:
        out['evidence'] = str(path)
    return out


def _emit(tool, result, out_path=None):
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if out_path is None and len(text) <= SUMMARY_LIMIT:
        print(text)
        return 0 if _summary(tool, result)['ok'] else 1
    if out_path is None:
        root = Path(tempfile.gettempdir()) / 'chemdraw-cdx'
        root.mkdir(exist_ok=True)
        out_path = root / f'{tool}-{time.strftime("%Y%m%d-%H%M%S")}-{os.getpid()}.json'
    target = Path(out_path).resolve()
    if target.exists():
        raise SystemExit(f'Refusing to overwrite existing evidence file {target}')
    target.write_text(text, encoding='utf-8')
    summary = _summary(tool, result, target)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary['ok'] else 1


def _load_args(ns):
    if ns.json and ns.args:
        raise SystemExit('Use either --json or --args, not both')
    # Either flag takes inline JSON or a JSON file; agents mix them up and the intent is never unclear.
    given = (ns.args or ns.json or '{}').strip()
    if given.startswith(('{', '[')):
        text = given
    elif Path(given).is_file():
        text = Path(given).read_text(encoding='utf-8-sig')
    else:
        raise SystemExit(f"{given!r} is neither a JSON object nor an existing file; "
                         "pass inline JSON with --json '{...}' or a file with --args FILE")
    value = json.loads(text)
    if not isinstance(value, dict):
        raise SystemExit('Tool arguments must be a JSON object')
    return value


# ---------------------------------------------------------------- commands
def cmd_tools(ns):
    from cdxml_toolkit.mcp_runtime.tool_registry import build_registry
    reg = build_registry()
    if ns.detail == 'summary':
        print(f'{len(reg)} tools: ' + ', '.join(sorted(reg)))
        return 0
    for name in sorted(reg):
        spec = reg[name]
        native = ' [native lock]' if getattr(spec, 'resource_class', None) else ''
        timeout = f'{spec.timeout_seconds}s' if spec.timeout_seconds else 'default'
        print(f'{name:42s} timeout={timeout}{native}')
    print(f'-- {len(reg)} tools; `cdx.py sig <tool>` prints a signature')
    return 0


def cmd_sig(ns):
    text = SIGNATURES.read_text(encoding='utf-8')
    m = re.search(rf'^### `{re.escape(ns.tool)}\(.*?(?=^### |^## |\Z)', text, re.S | re.M)
    if not m:
        raise SystemExit(f'No signature for {ns.tool!r}; run `cdx.py tools`.')
    print(m.group(0).rstrip())
    return 0


def cmd_call(ns):
    return _emit(ns.tool, _worker(ns.tool, _load_args(ns)), ns.out)


def render_log_path():
    """PNGs written by `cdx.py render` and their SHA-256; only these may be replaced without --replace."""
    return default_runtime_dir().parent / 'render-log.json'


def _render_log():
    try:
        value = json.loads(render_log_path().read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {}
    return value if isinstance(value, dict) else {}


def _record_render(png):
    log = _render_log()
    log.pop(str(png), None)
    log[str(png)] = _sha256(png)
    path = render_log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    staged = path.with_name(f'.{path.name}.{os.getpid()}')
    staged.write_text(json.dumps(dict(list(log.items())[-5000:]), indent=0), encoding='utf-8')
    os.replace(staged, path)


def cmd_render(ns):
    jobs = []
    for src in ns.files:
        source = Path(src).resolve()
        out_dir = Path(ns.out_dir).resolve() if ns.out_dir else source.parent
        jobs.append((source, out_dir, out_dir / (source.stem + '.png')))
    targets = [png for _, _, png in jobs]
    clashes = sorted({str(png) for png in targets if targets.count(png) > 1})
    if clashes:
        raise SystemExit(f'Several inputs would render to the same file: {", ".join(clashes)}; render them separately')
    status = 0
    for source, out_dir, png in jobs:
        # Replace only a PNG this command wrote and nobody changed since: next to a
        # reconstructed CDXML, the same name is often the user's source image.
        if png.exists() and not ns.replace and _render_log().get(str(png)) != _sha256(png):
            status = 1
            print(json.dumps({'source': str(source), 'png': None, 'ok': False,
                              'error': f'{png} exists and was not written by cdx.py render (it may be the source '
                                       'image); choose another folder with --out-dir, or pass --replace if it '
                                       'is safe to overwrite'}, ensure_ascii=False))
            continue
        out_dir.mkdir(parents=True, exist_ok=True)
        # The renderer refuses existing outputs: render to a fresh name, then
        # replace, so a failed render never destroys the previous PNG.
        staged = out_dir / f'.{source.stem}.{os.getpid()}.rendering.png'
        staged.unlink(missing_ok=True)
        result = _worker('render_to_png', {'output_path': str(staged)}, [str(source)])
        summary = _summary('render_to_png', result)
        ok = summary['ok'] and staged.is_file()
        if ok:
            os.replace(staged, png)
            _record_render(png)
        else:
            staged.unlink(missing_ok=True)
        status |= 0 if ok else 1
        print(json.dumps({'source': str(source), 'png': str(png) if ok else None, 'ok': ok,
                          **({} if ok else {k: summary[k] for k in ('error', 'error_id') if k in summary})},
                         ensure_ascii=False))
    return status


def cmd_build(ns):
    sys.path.insert(0, str(Path(__file__).parent))
    import acs_builder
    if Path(ns.output).exists():
        raise SystemExit(f'Refusing to overwrite existing {Path(ns.output).resolve()}; choose a new output name')
    out = acs_builder.build_from_spec(ns.spec, ns.output)
    print(json.dumps({'cdxml': str(out), 'ok': True}))
    if ns.render:
        return cmd_render(argparse.Namespace(files=[str(out)], out_dir=None, replace=False))
    return 0


def cmd_draw(ns):
    """Brief (JSON file or '-' for stdin) -> checked CDXML through the draw_figure tool."""
    text = sys.stdin.read() if ns.brief == '-' else Path(ns.brief).read_text(encoding='utf-8')
    try:
        brief = json.loads(text)
    except ValueError as exc:
        raise SystemExit(f'The brief is not valid JSON: {exc}')
    kwargs = {'brief': brief, 'render': ns.render}
    if ns.output:
        kwargs['output_path'] = ns.output
    return _emit('draw_figure', _worker('draw_figure', kwargs), ns.out)


def _markush_render(source, png):
    """Native render for the Markush driver, through the worker (native lock, timeout)."""
    result = _worker('render_to_png', {'output_path': str(png)}, [str(source)])
    return _summary('render_to_png', result)['ok'] and Path(png).is_file()


def cmd_markush(ns):
    from cdxml_toolkit.markush import workflow
    if ns.action == 'init':
        if not ns.image:
            raise SystemExit('init needs --image')
        crop = [int(v) for v in ns.crop] if ns.crop else None
        out = workflow.init(ns.workdir, ns.image, text=ns.text, crop=crop, reuse=ns.reuse)
    elif ns.action == 'next':
        out = workflow.next_task(ns.workdir, renderer=_markush_render)
    elif ns.action == 'submit':
        if not (ns.task and ns.answer):
            raise SystemExit('submit needs TASK and ANSWER.json')
        out = workflow.submit(ns.workdir, ns.task, ns.answer, renderer=_markush_render)
    else:
        out = workflow.status(ns.workdir)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if out.get('accepted', True) else 1


def cmd_chemscript_info(ns):
    from cdxml_toolkit.mcp_runtime.resource_lock import native_resource_lock
    with native_resource_lock('chemdraw_com', ns.timeout):
        proc = subprocess.run([sys.executable, '-m', 'cdxml_toolkit.chemdraw.chemscript_bridge', 'info', ns.source],
                              capture_output=True, text=True, timeout=ns.timeout, env=_chemscript_env())
    sys.stdout.write(proc.stdout)
    sys.stderr.write(proc.stderr)
    return proc.returncode


def cmd_decimer(ns):
    kwargs = {'image_path': str(Path(ns.image).resolve()), 'hand_drawn': ns.hand_drawn,
              'confirm_upload': not ns.preflight, 'timeout_seconds': ns.timeout}
    if ns.out:
        kwargs['output_path'] = str(Path(ns.out).resolve())
    result = _worker('extract_structures_via_decimer_api', kwargs)
    if ns.preflight:
        pre = next((x['preflight'] for x in _layers(result) if isinstance(x.get('preflight'), dict)), None)
        print(json.dumps(pre or result, ensure_ascii=False, indent=2))
        return 0 if pre else 1
    inner = next((x for x in _layers(result) if 'structures' in x), None)
    if inner is None:
        return _emit('extract_structures_via_decimer_api', result)
    print(json.dumps({'ok': inner.get('ok'), 'output_path': inner.get('output_path'),
                      'structures': [{k: s.get(k) for k in ('index', 'smiles', 'valid', 'formula')}
                                     for s in inner['structures']],
                      'warnings': inner.get('warnings', [])}, ensure_ascii=False, indent=2))
    return 0 if inner.get('ok') else 1


def runtime_paths():
    from cdxml_toolkit.mcp_runtime import official_overrides, resource_lock, tool_worker
    base = os.environ.get('LOCALAPPDATA') or os.environ.get('TEMP') or str(Path.home())
    # The runtime names its folder (~/Library/Logs/chemdraw-skill on macOS); runtimes before
    # that used <base>/chemdraw-skill/logs, older ones <base>/<client>/chemdraw-mcp/logs.
    current = str(tool_worker.worker_log_dir()) if hasattr(tool_worker, 'worker_log_dir') \
        else os.path.join(base, 'chemdraw-skill', 'logs')
    logs = sorted({*glob.glob(current), *glob.glob(os.path.join(base, 'chemdraw-skill', 'logs')),
                   *glob.glob(os.path.join(base, '*', 'chemdraw-mcp', 'logs'))})
    native_lock = resource_lock.CHEMDRAW_COM_MUTEX if os.name == 'nt' else str(resource_lock.CHEMDRAW_LOCK_FILE)
    return {'python': sys.executable, 'skill_root': str(SKILL_ROOT),
            'worker_logs': logs or current + ' (created on first worker failure)',
            'native_lock': native_lock,
            'native_temp': os.environ.get('CHEMDRAW_NATIVE_TEMP') or str(official_overrides._TEMP_OUTPUT),
            'chemscript_pythonpath': _chemscript_env().get('PYTHONPATH')}


def _check_installation():
    sys.path.insert(0, str(Path(__file__).parent))
    import check_installation
    return check_installation


def checkout_toolkit():
    """`<repo>/toolkit/cdxml_toolkit` when this Skill is the skill/chemdraw folder of a checkout."""
    package = SKILL_ROOT.parent.parent / 'toolkit' / 'cdxml_toolkit'
    return package if SKILL_ROOT.parent.name == 'skill' and package.is_dir() else None


def expected_fingerprint():
    """Toolkit this Skill documents: the checkout's toolkit/ source, else the one pinned in runtime.json."""
    package = checkout_toolkit()
    if package:
        return _check_installation().toolkit_fingerprint(package)
    return _baseline().get('toolkit_fingerprint')


def runtime_fingerprint():
    import cdxml_toolkit
    return _check_installation().toolkit_fingerprint(Path(cdxml_toolkit.__file__).resolve().parent)


def runtime_hint():
    return ('The runtime was built from another toolkit revision than this Skill documents, so tools may be '
            'missing or behave differently. Rebuild it: ' + ' | '.join(install_help()[:2]))


def _signatures_current():
    from cdxml_toolkit.mcp_runtime import generate_reference
    return normalize_signatures(generate_reference.render_reference()) == \
        normalize_signatures(SIGNATURES.read_text(encoding='utf-8'))


def normalize_signatures(text):
    text = re.sub(r'^(Distribution|Profile): .*\n', '', text, flags=re.M)
    return '\n'.join(line.strip() for line in text.splitlines() if line.strip())


def cmd_regen_signatures(ns):
    # Regenerating from a stale runtime would roll the committed reference back to its tool set.
    if runtime_fingerprint() != expected_fingerprint():
        raise SystemExit('cdx.py: refusing to regenerate signatures. ' + runtime_hint())
    write_signatures()
    print(SIGNATURES)
    package = checkout_toolkit()
    if package:  # keep runtime.json's fingerprint in step with the toolkit source it pins
        baseline = _baseline()
        baseline['toolkit_fingerprint'] = expected_fingerprint()
        BASELINE.write_bytes((json.dumps(baseline, indent=2) + '\n').encode('utf-8'))
        print(BASELINE)
    return 0


def write_signatures():
    from cdxml_toolkit.mcp_runtime import generate_reference
    text = generate_reference.render_reference()
    text = re.sub(r'^Profile: .*$', 'Profile: `full (default)`', text, count=1, flags=re.M)
    SIGNATURES.write_bytes(text.encode('utf-8').replace(b'\r\n', b'\n'))


def _catalog_pages():
    from cdxml_toolkit.catalog import render
    return render.render_all()


def _generated_shards():
    inventory = REFERENCES / 'inventory'
    if not inventory.is_dir():
        return []
    return sorted(f'inventory/{path.name}' for path in inventory.glob('*.md') if path.name.startswith(CATALOG_SHARDS))


def catalog_stale():
    """Names of generated interface pages that differ from the catalogs, are missing, or are left over."""
    pages = _catalog_pages()
    stale = []
    for name, text in pages.items():
        path = REFERENCES / name
        if not path.is_file() or path.read_bytes().decode('utf-8').replace('\r\n', '\n') != text:
            stale.append(name)
    stale += [name for name in _generated_shards() if name not in pages]
    return stale


def write_catalog():
    """Write the generated interface pages (LF) and drop shards the catalogs no longer produce."""
    pages = _catalog_pages()
    for name in _generated_shards():
        if name not in pages:
            (REFERENCES / name).unlink()
    for name, text in pages.items():
        path = REFERENCES / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(text.encode('utf-8'))
    return list(pages)


def cmd_regen_catalog(ns):
    # Same guard as regen-signatures: a stale runtime would write pages for another toolkit revision.
    if runtime_fingerprint() != expected_fingerprint():
        raise SystemExit('cdx.py: refusing to regenerate the interface catalog. ' + runtime_hint())
    if ns.check:
        stale = catalog_stale()
        print(json.dumps({'catalog_current': not stale, 'stale': stale}, indent=2))
        return 1 if stale else 0
    for name in write_catalog():
        print(REFERENCES / name)
    return 0


def cmd_doctor(ns):
    import importlib.metadata as md
    import importlib.util
    baseline = _baseline()
    # The Skill and its toolkit are released together under one version tag.
    report = {'skill_version': baseline.get('toolkit_version'), 'toolkit': md.version('cdxml-toolkit-community'),
              'runtime_source': baseline.get('ref') or (baseline.get('commit') or '')[:12] or None,
              'python': sys.version.split()[0], 'runtime': sys.executable}
    report['extras'] = {k: [m for m in v if importlib.util.find_spec(m.split('.')[0]) is None] or 'ok'
                        for k, v in EXTRAS.items()}
    if ns.paths:
        report['paths'] = runtime_paths()
    expected = expected_fingerprint()
    report['runtime_matches_skill'] = None if expected is None else runtime_fingerprint() == expected
    if report['runtime_matches_skill'] is False:
        report['runtime_hint'] = runtime_hint()
    report['signatures_current'] = _signatures_current()
    report['catalog_current'] = not catalog_stale()
    check_installation = _check_installation()
    if (SKILL_ROOT / check_installation.MANIFEST).is_file():
        inst = check_installation.check_manifest(SKILL_ROOT)
        report['installation'] = 'ok' if inst['ok'] else {k: inst[k] for k in ('missing', 'modified', 'extra')}
    else:
        report['installation'] = 'no manifest (source checkout, or installed without the installer)'
    diag = _worker('diagnose_runtime', {'run_native_probe': ns.native, 'run_office_probe': ns.office,
                                        'run_chemscript_probe': ns.chemscript})
    layers = _layers(diag)
    inner = layers[-1] if layers else {}
    caps = (inner.get('outputs') or {}).get('capabilities') or {}
    report['capabilities'] = {k: (v.get('status') if isinstance(v, dict) else v) for k, v in caps.items()}
    report['warnings'] = inner.get('warnings') or []
    if ns.full:
        report['diagnose_runtime'] = inner
    print(json.dumps(report, ensure_ascii=False, indent=2))
    healthy = report['signatures_current'] and report['catalog_current'] \
        and not isinstance(report['installation'], dict) \
        and report['runtime_matches_skill'] is not False
    return 0 if healthy else 1


def _sha256(path):
    import hashlib
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _open_in_chemdraw(path):
    """Show one file to the user in ChemDraw (they asked to edit it, so a window is expected)."""
    if sys.platform == 'darwin':
        return subprocess.run(['open', '-a', 'ChemDraw', str(path)], capture_output=True).returncode == 0
    if sys.platform == 'win32':
        os.startfile(str(path))  # noqa: S606 - ChemDraw is the .cdxml handler
        return True
    return False


def _office_edit_start(ns):
    document = Path(ns.target).resolve()
    workdir = Path(ns.workdir or document.with_name(document.stem + '_chemdraw_edit')).resolve()
    if workdir.exists():
        raise SystemExit(f'Refusing to reuse existing edit folder {workdir}; pass --workdir')
    # Inspect into a scratch folder: the edit folder is made only once an object is chosen,
    # so listing the objects or a wrong --object leaves nothing that blocks the rerun.
    with tempfile.TemporaryDirectory(prefix='cdx-office-edit-') as scratch:
        inspection = Path(scratch) / 'inspection'
        result = _worker('inspect_chemdraw_objects_in_office',
                         {'input_path': str(document), 'output_dir': str(inspection), 'render_previews': False})
        if not _summary('inspect_chemdraw_objects_in_office', result)['ok']:
            return _emit('inspect_chemdraw_objects_in_office', result)
        manifest = json.loads((inspection / 'manifest.json').read_text(encoding='utf-8'))
        objects = manifest['objects']
        listing = [{'object': item['ordinal'], 'host': item['host'], 'shape': item.get('shape_name')}
                   for item in objects]
        if ns.object is None and len(objects) > 1:
            print(json.dumps({'ok': False, 'error': 'choose one object with --object N', 'objects': listing},
                             ensure_ascii=False, indent=2))
            return 2
        number = 1 if ns.object is None else ns.object
        chosen = next((item for item in objects if item['ordinal'] == number), None)
        if chosen is None:
            raise SystemExit(f'No ChemDraw object {number}; the document has {len(objects)} (numbered from 1)')
        workdir.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(inspection, workdir / 'inspection')
    cdxml = workdir / f'object_{number:03d}.cdxml'
    cdxml.write_bytes((workdir / 'inspection' / chosen['cdxml']).read_bytes())
    (workdir / 'replacements.json').write_text(json.dumps({
        'schema_version': 1, 'source_sha256': manifest['source_sha256'],
        'replacements': [{'object_id': chosen['object_id'], 'replacement_cdxml': cdxml.name}],
    }, indent=2), encoding='utf-8')
    (workdir / 'session.json').write_text(json.dumps({
        'document': str(document), 'object': number, 'object_id': chosen['object_id'],
        'cdxml': cdxml.name, 'cdxml_sha256': _sha256(cdxml),
    }, indent=2), encoding='utf-8')
    opened = False if ns.no_open else _open_in_chemdraw(cdxml)
    print(json.dumps({'ok': True, 'workdir': str(workdir), 'cdxml': str(cdxml), 'object': number,
                      'opened_in_chemdraw': opened,
                      'next': f'edit and save {cdxml.name} in ChemDraw, then: cdx.py office-edit --finish "{workdir}"'},
                     ensure_ascii=False, indent=2))
    return 0


def _office_edit_finish(ns):
    target = Path(ns.target).resolve()
    if target.is_dir():
        workdir = Path(ns.workdir).resolve() if ns.workdir else target
    else:  # the document: its edit folder is --workdir or the default one
        workdir = Path(ns.workdir or target.with_name(target.stem + '_chemdraw_edit')).resolve()
    if not (workdir / 'session.json').is_file():
        print(json.dumps({'ok': False, 'error': f'No office-edit session in {workdir}; start one with '
                          f'cdx.py office-edit DOCUMENT, or pass its folder with --workdir'},
                         ensure_ascii=False, indent=2))
        return 2
    session = json.loads((workdir / 'session.json').read_text(encoding='utf-8'))
    cdxml = workdir / session['cdxml']
    deadline = time.monotonic() + max(0, ns.wait)
    while True:
        try:
            saved = _sha256(cdxml) != session['cdxml_sha256']
            age = time.time() - cdxml.stat().st_mtime
        except OSError:  # ChemDraw replaces the file while saving
            saved, age = False, 0
        if saved and age >= 2:
            break
        if saved:  # a save just landed: let it settle, whatever --wait says
            deadline = max(deadline, time.monotonic() + 2 - age)
        if time.monotonic() >= deadline:
            print(json.dumps({'ok': False, 'error': f'{cdxml.name} has not been saved since the edit started',
                              'cdxml': str(cdxml)}, ensure_ascii=False, indent=2))
            return 1
        time.sleep(1)
    args = {'input_path': session['document'], 'replacements_manifest': str(workdir / 'replacements.json'),
            'render_pdf_preview': ns.pdf, 'resize_frames': True}
    if ns.output:
        args['output_path'] = str(Path(ns.output).resolve())
    return _emit('replace_chemdraw_objects_in_office', _worker('replace_chemdraw_objects_in_office', args))


def cmd_office_edit(ns):
    """Edit one ChemDraw object of a PPTX/DOCX in ChemDraw and write it back to a new copy.

    Stands in for double-click editing, which Office for macOS does not offer for
    ChemDraw objects: the frame grows or shrinks with the drawing, the source is kept.
    """
    return _office_edit_finish(ns) if ns.finish else _office_edit_start(ns)


def cmd_py(ns):
    """Run the toolkit runtime's interpreter, e.g. `cdx.py py -m cdxml_toolkit.scientific ...`."""
    return subprocess.call([sys.executable, *ns.rest], env=_chemscript_env())


def cmd_calc(ns):
    """Serve the reaction calculator page (draw in ChemDraw, enter amounts, read every quantity).

    Runs until the page is closed, so an agent starts it in the background and reports the
    address printed on the first line.
    """
    return subprocess.call([sys.executable, '-m', 'cdxml_toolkit.reaction_calculator', *ns.rest],
                           env=_chemscript_env())


def cmd_install_mappers(ns):
    """Install RXNMapper / LocalMapper, each in its own environment beside the runtime (several hundred MB).

    map_reaction_atoms works without them (built-in substructure method); with them, method auto
    prefers the learned mappers. The weights ship inside the packages, so mapping stays local.
    """
    return subprocess.call([sys.executable, '-m', 'cdxml_toolkit.mapping_backends', *ns.rest], env=_chemscript_env())


def main(argv=None):
    argv = sys.argv[1:] if argv is None else list(argv)
    # `sig` reads a generated reference and help is static: both work before a runtime exists.
    if argv[:1] not in (['sig'], ['-h'], ['--help'], []):
        _ensure_runtime(argv)
    if argv[:1] == ['py']:  # pass everything through untouched (argparse would eat -m/-c)
        return cmd_py(argparse.Namespace(rest=argv[1:]))
    if argv[:1] == ['calc']:  # the page's own parser handles every flag, including -h
        return cmd_calc(argparse.Namespace(rest=argv[1:]))
    if argv[:1] == ['install-mappers']:  # likewise: `--status` or `--dry-run` may come first
        return cmd_install_mappers(argparse.Namespace(rest=argv[1:]))
    p = argparse.ArgumentParser(prog='cdx.py', description=__doc__.split('\n')[0])
    sub = p.add_subparsers(dest='cmd', required=True)
    s = sub.add_parser('tools', help='list registered tools')
    s.add_argument('--detail', choices=['full', 'summary'], default='full')
    s.set_defaults(fn=cmd_tools)
    s = sub.add_parser('sig', help='print one tool signature')
    s.add_argument('tool')
    s.set_defaults(fn=cmd_sig)
    s = sub.add_parser('call', help='run any tool through the isolated worker')
    s.add_argument('tool')
    s.add_argument('--json', help='keyword arguments as a JSON object string')
    s.add_argument('--args', help='keyword arguments in a JSON file')
    s.add_argument('--out', help='new evidence file for the full result')
    s.set_defaults(fn=cmd_call)
    s = sub.add_parser('render', help='native 300 dpi PNG next to each CDXML (replaces only its own earlier render)')
    s.add_argument('files', nargs='+')
    s.add_argument('--out-dir')
    s.add_argument('--replace', action='store_true', help='also replace a same-named PNG this command did not write')
    s.set_defaults(fn=cmd_render)
    s = sub.add_parser('build', help='ACS Document 1996 CDXML from a JSON spec (acs_builder)')
    s.add_argument('spec')
    s.add_argument('output')
    s.add_argument('--render', action='store_true')
    s.set_defaults(fn=cmd_build)
    s = sub.add_parser('draw', help='checked reaction scheme, scope panel or mechanism from a brief (JSON file or -): '
                                    'cdx.py draw BRIEF [OUTPUT] [--render]')
    s.add_argument('brief')
    s.add_argument('output', nargs='?', help='new .cdxml path, or a new folder for kind "scope" '
                                              '(default: a fresh name in the temp folder)')
    s.add_argument('--render', action='store_true', help='also render a native PNG')
    s.add_argument('--out', help='new evidence file for the full report')
    s.set_defaults(fn=cmd_draw)
    s = sub.add_parser('chemscript-info', help='ChemScript reading of a saved file, under the native lock')
    s.add_argument('source')
    s.add_argument('--timeout', type=int, default=120)
    s.set_defaults(fn=cmd_chemscript_info)
    s = sub.add_parser('decimer', help='recognize one image with the built-in DECIMER endpoint')
    s.add_argument('image')
    s.add_argument('--hand-drawn', action='store_true')
    s.add_argument('--preflight', action='store_true', help='no upload; print size/sha256/origin only')
    s.add_argument('--timeout', type=int, default=120)
    s.add_argument('--out', help='new JSON file for the raw recognition result')
    s.set_defaults(fn=cmd_decimer)
    s = sub.add_parser('markush', help='Markush workflow from an image: init, next task, submit an answer, status')
    s.add_argument('action', choices=['init', 'next', 'submit', 'status'])
    s.add_argument('workdir')
    s.add_argument('task', nargs='?', help='submit: the task id printed by next')
    s.add_argument('answer', nargs='?', help='submit: JSON answer file')
    s.add_argument('--image', help='init: the structure image (crop of the figure)')
    s.add_argument('--text', help='init: claim text (.txt or .pdf) with the variable definitions')
    s.add_argument('--crop', nargs=4, metavar=('X0', 'Y0', 'X1', 'Y1'), help='init: crop box in image pixels')
    s.add_argument('--reuse', help='init: earlier workdir whose answers are reused when the task input is unchanged')
    s.set_defaults(fn=cmd_markush)
    s = sub.add_parser('doctor', help='runtime, extras, signatures, installation and capability report')
    s.add_argument('--paths', action='store_true', help='also print log, lock and temp locations')
    s.add_argument('--native', action='store_true', help='run the native ChemDraw render probe')
    s.add_argument('--office', action='store_true', help='run the Word/PowerPoint OLE probes')
    s.add_argument('--chemscript', action='store_true', help='run the ChemScript bridge ping')
    s.add_argument('--full', action='store_true', help='include the complete diagnose_runtime result')
    s.set_defaults(fn=cmd_doctor)
    s = sub.add_parser('office-edit', help='edit one ChemDraw object of a PPTX/DOCX in ChemDraw, then --finish')
    s.add_argument('target', help='the PPTX/DOCX, or with --finish the edit folder')
    s.add_argument('--object', type=int, help='object number from the listing (needed when there are several)')
    s.add_argument('--workdir', help='new edit folder (default: <document>_chemdraw_edit beside it)')
    s.add_argument('--no-open', action='store_true', help='do not open the drawing in ChemDraw')
    s.add_argument('--finish', action='store_true', help='write the saved drawing back to a new copy')
    s.add_argument('--output', help='with --finish: new Office file (default: <document>_replaced beside it)')
    s.add_argument('--wait', type=int, default=0, help='with --finish: seconds to wait for the save')
    s.add_argument('--pdf', action='store_true', help='with --finish: also export a PDF preview through Office')
    s.set_defaults(fn=cmd_office_edit)
    s = sub.add_parser('py', help='run the runtime Python: cdx.py py SCRIPT_OR_-m ... (helper scripts, examples)')
    s.add_argument('rest', nargs=argparse.REMAINDER)
    s.set_defaults(fn=cmd_py)
    s = sub.add_parser('calc', help='reaction calculator page: cdx.py calc [REACTION] [--scale MMOL] [--molarity M] '
                                    '[--offline] [--no-open] (runs until the page is closed; start it in the background)')
    s.add_argument('rest', nargs=argparse.REMAINDER)
    s.set_defaults(fn=cmd_calc)
    s = sub.add_parser('install-mappers', help='one-click install of the optional RXNMapper / LocalMapper atom-mapping '
                                               'backends beside the runtime: cdx.py install-mappers [rxnmapper] [localmapper] '
                                               '[--dry-run] [--status] (map_reaction_atoms works without them)')
    s.add_argument('rest', nargs=argparse.REMAINDER)
    s.set_defaults(fn=cmd_install_mappers)
    s = sub.add_parser('regen-signatures', help='rewrite references/mcp-signatures.md from the live registry '
                                                '(and, in a checkout, the toolkit fingerprint in runtime.json)')
    s.set_defaults(fn=cmd_regen_signatures)
    s = sub.add_parser('regen-catalog', help='rewrite the generated interface pages (interface-chemscript/com/cdxml-model/menu, '
                                             'recipes-chemdraw, their inventory shards) from the catalogs; --check only reports')
    s.add_argument('--check', action='store_true', help='report stale pages and exit 1 instead of writing')
    s.set_defaults(fn=cmd_regen_catalog)
    ns = p.parse_args(argv)
    return ns.fn(ns)


if __name__ == '__main__':
    raise SystemExit(main())
