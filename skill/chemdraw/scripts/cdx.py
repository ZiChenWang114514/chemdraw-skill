"""Single command-line entry point for the ChemDraw skill.

    python <skill>/scripts/cdx.py <command> ...

Any Python 3.9+ can start it: when the current interpreter lacks
cdxml-toolkit, cdx.py re-launches itself in the toolkit runtime
(CHEMDRAW_MCP_PYTHON, a `chemdraw-venv` beside the skill folder, or a conda
environment named `cdxml`). Every tool call goes through the toolkit's
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
import subprocess
import sys
import tempfile
import time

SKILL_ROOT = Path(__file__).resolve().parents[1]
SIGNATURES = SKILL_ROOT / 'references' / 'mcp-signatures.md'
SUMMARY_LIMIT = 6000
REEXEC_FLAG = 'CHEMDRAW_CDX_REEXEC'
EXTRAS = {'publication': ['openpyxl'], 'scientific': ['numpy', 'scipy', 'matplotlib', 'nmrglue'],
          'office': ['win32com.client', 'docx', 'pptx', 'olefile'], 'analysis': ['pdfplumber', 'fitz'],
          'image': ['cv2', 'pytesseract'], 'chemscript': ['clr']}


# ------------------------------------------------------------- runtime bootstrap
def _has_toolkit(python):
    """True when `python` belongs to an environment containing cdxml_toolkit.mcp_runtime."""
    root = Path(python).resolve().parent
    if root.name.lower() in ('scripts', 'bin'):
        root = root.parent
    patterns = ('Lib/site-packages/cdxml_toolkit/mcp_runtime', 'lib/python3*/site-packages/cdxml_toolkit/mcp_runtime')
    if any(glob.glob(str(root / pattern)) for pattern in patterns):
        return True
    # Editable (pip -e) installs live outside site-packages: ask the interpreter.
    try:
        probe = subprocess.run([str(python), '-c', 'import cdxml_toolkit.mcp_runtime'],
                               capture_output=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return False
    return probe.returncode == 0


def _interpreter(env_root):
    for name in ('Scripts/python.exe', 'python.exe', 'bin/python3', 'bin/python'):
        if (env_root / name).is_file():
            return env_root / name
    return None


def runtime_candidates():
    """Ordered runtime interpreters: explicit variable, sibling venv, conda `cdxml`."""
    found = []
    explicit = os.environ.get('CHEMDRAW_MCP_PYTHON')
    if explicit:
        found.append(('CHEMDRAW_MCP_PYTHON', Path(explicit)))
    sibling = _interpreter(SKILL_ROOT.parent / 'chemdraw-venv')
    if sibling:
        found.append(('chemdraw-venv', sibling))
    registry = Path.home() / '.conda' / 'environments.txt'
    if registry.is_file():
        for line in registry.read_text(encoding='utf-8', errors='ignore').splitlines():
            env_root = Path(line.strip())
            if env_root.name.lower() == 'cdxml' and _interpreter(env_root):
                found.append(('conda cdxml', _interpreter(env_root)))
    return found


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
    sys.stderr.write(
        'cdx.py: no cdxml-toolkit runtime found.\n'
        f'Looked for: CHEMDRAW_MCP_PYTHON, {SKILL_ROOT.parent / "chemdraw-venv"}, conda env "cdxml".\n'
        'Install one with the repository installer (install.ps1 -Runtime) or set CHEMDRAW_MCP_PYTHON.\n')
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
        raise SystemExit(f'Unknown tool {tool!r}; run `cdx.py tools`.')
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
    if ns.args:
        value = json.loads(Path(ns.args).read_text(encoding='utf-8-sig'))
    else:
        value = json.loads(ns.json or '{}')
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
        print(f'{name:42s} timeout={spec.timeout_seconds}s{native}')
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


def cmd_render(ns):
    status = 0
    for src in ns.files:
        source = Path(src).resolve()
        out_dir = Path(ns.out_dir).resolve() if ns.out_dir else source.parent
        out_dir.mkdir(parents=True, exist_ok=True)
        png = out_dir / (source.stem + '.png')
        # The renderer refuses existing outputs: render to a fresh name, then
        # replace, so a failed render never destroys the previous PNG.
        staged = out_dir / f'.{source.stem}.{os.getpid()}.rendering.png'
        staged.unlink(missing_ok=True)
        result = _worker('render_to_png', {'output_path': str(staged)}, [str(source)])
        ok = _summary('render_to_png', result)['ok'] and staged.is_file()
        if ok:
            os.replace(staged, png)
        else:
            staged.unlink(missing_ok=True)
        status |= 0 if ok else 1
        print(json.dumps({'source': str(source), 'png': str(png) if ok else None, 'ok': ok,
                          **({} if ok else {'error': _summary('render_to_png', result).get('error')})},
                         ensure_ascii=False))
    return status


def cmd_build(ns):
    sys.path.insert(0, str(Path(__file__).parent))
    import acs_builder
    out = acs_builder.build_from_spec(ns.spec, ns.output)
    print(json.dumps({'cdxml': str(out), 'ok': True}))
    if ns.render:
        return cmd_render(argparse.Namespace(files=[str(out)], out_dir=None))
    return 0


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
    from cdxml_toolkit.mcp_runtime import official_overrides, resource_lock
    base = os.environ.get('LOCALAPPDATA') or os.environ.get('TEMP') or str(Path.home())
    logs = sorted(glob.glob(os.path.join(base, '*', 'chemdraw-mcp', 'logs')))
    return {'python': sys.executable, 'skill_root': str(SKILL_ROOT),
            'worker_logs': logs or f'{base}\\<runtime>\\chemdraw-mcp\\logs (created on first worker failure)',
            'native_mutex': resource_lock.CHEMDRAW_COM_MUTEX,
            'native_temp': os.environ.get('CHEMDRAW_NATIVE_TEMP') or str(official_overrides._TEMP_OUTPUT),
            'chemscript_pythonpath': _chemscript_env().get('PYTHONPATH')}


def _signatures_current():
    from cdxml_toolkit.mcp_runtime import generate_reference
    return normalize_signatures(generate_reference.render_reference()) == \
        normalize_signatures(SIGNATURES.read_text(encoding='utf-8'))


def normalize_signatures(text):
    text = re.sub(r'^(Distribution|Profile): .*\n', '', text, flags=re.M)
    return '\n'.join(line.strip() for line in text.splitlines() if line.strip())


def write_signatures():
    from cdxml_toolkit.mcp_runtime import generate_reference
    text = generate_reference.render_reference()
    text = re.sub(r'^Profile: .*$', 'Profile: `full (default)`', text, count=1, flags=re.M)
    SIGNATURES.write_bytes(text.encode('utf-8').replace(b'\r\n', b'\n'))


def cmd_doctor(ns):
    import importlib.metadata as md
    import importlib.util
    report = {'toolkit': md.version('cdxml-toolkit-community'), 'python': sys.version.split()[0],
              'runtime': sys.executable}
    report['extras'] = {k: [m for m in v if importlib.util.find_spec(m.split('.')[0]) is None] or 'ok'
                        for k, v in EXTRAS.items()}
    if ns.paths:
        report['paths'] = runtime_paths()
    report['signatures_current'] = _signatures_current()
    sys.path.insert(0, str(Path(__file__).parent))
    import check_installation
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
    healthy = report['signatures_current'] and not isinstance(report['installation'], dict)
    return 0 if healthy else 1


def cmd_py(ns):
    """Run the toolkit runtime's interpreter, e.g. `cdx.py py -m cdxml_toolkit.scientific ...`."""
    return subprocess.call([sys.executable, *ns.rest], env=_chemscript_env())


def main(argv=None):
    argv = sys.argv[1:] if argv is None else list(argv)
    _ensure_runtime(argv)
    if argv[:1] == ['py']:  # pass everything through untouched (argparse would eat -m/-c)
        return cmd_py(argparse.Namespace(rest=argv[1:]))
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
    s = sub.add_parser('render', help='native 300 dpi PNG next to each CDXML (replaces an old PNG)')
    s.add_argument('files', nargs='+')
    s.add_argument('--out-dir')
    s.set_defaults(fn=cmd_render)
    s = sub.add_parser('build', help='ACS Document 1996 CDXML from a JSON spec (acs_builder)')
    s.add_argument('spec')
    s.add_argument('output')
    s.add_argument('--render', action='store_true')
    s.set_defaults(fn=cmd_build)
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
    s = sub.add_parser('doctor', help='runtime, extras, signatures, installation and capability report')
    s.add_argument('--paths', action='store_true', help='also print log, lock and temp locations')
    s.add_argument('--native', action='store_true', help='run the native ChemDraw render probe')
    s.add_argument('--office', action='store_true', help='run the Word/PowerPoint OLE probes')
    s.add_argument('--chemscript', action='store_true', help='run the ChemScript bridge ping')
    s.add_argument('--full', action='store_true', help='include the complete diagnose_runtime result')
    s.set_defaults(fn=cmd_doctor)
    s = sub.add_parser('py', help='run the runtime Python: cdx.py py SCRIPT_OR_-m ... (helper scripts, examples)')
    s.add_argument('rest', nargs=argparse.REMAINDER)
    s.set_defaults(fn=cmd_py)
    s = sub.add_parser('regen-signatures', help='rewrite references/mcp-signatures.md from the live registry')
    s.set_defaults(fn=lambda ns: (write_signatures(), print(SIGNATURES))[0] or 0)
    ns = p.parse_args(argv)
    return ns.fn(ns)


if __name__ == '__main__':
    raise SystemExit(main())
