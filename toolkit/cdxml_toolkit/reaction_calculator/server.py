"""The calculator as a small local web app: draw in ChemDraw, load the drawing, look names up.

Everything is served from 127.0.0.1 on a random port behind a per-run token, and the only file
the page can make this process touch is the canvas it asked for in a private working folder.
Name lookups can reach PubChem (through ``resolve_compound``); ``offline=True`` keeps them local.
"""

from __future__ import annotations

import json
import os
import secrets
import subprocess
import sys
import tempfile
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from rdkit import Chem
from rdkit.Chem import Descriptors, rdMolDescriptors

from . import library
from .engine import compute
from .page import render_page
from .state import build_state, depiction

MAX_BODY = 4 * 1024 * 1024


# --- structures -----------------------------------------------------------------------

def canonical(smiles: str) -> str | None:
    mol = Chem.MolFromSmiles(smiles) if smiles else None
    return Chem.MolToSmiles(mol) if mol is not None else None


def resolve(query: str, *, offline: bool = False) -> dict:
    """A name, abbreviation, SMILES or formula as {ok, name, smiles, formula, mw, density, svg, source}."""
    query = query.strip()
    if not query or len(query) > 300:
        return {'ok': False, 'error': 'Type a name, SMILES or formula.'}
    smiles, name, source = None, None, None
    known = library.by_name(query)
    if known:
        smiles, source = known['smiles'], 'library'
    elif canonical(query):
        smiles, source = canonical(query), 'smiles'
    else:
        try:
            from cdxml_toolkit.naming.mol_builder import resolve_compound
            found = resolve_compound(query, use_network=not offline)
        except Exception as exc:  # a lookup service failing is not a calculator failure
            return {'ok': False, 'error': f'Lookup failed: {exc}'}
        if not found.get('ok') or not found.get('smiles'):
            return {'ok': False, 'error': found.get('error') or f'Could not resolve {query!r}.'}
        smiles, source, name = found['smiles'], found.get('source') or 'lookup', query
    mol = Chem.MolFromSmiles(smiles)
    if mol is None or any(a.GetAtomicNum() == 0 for a in mol.GetAtoms()):
        return {'ok': False, 'error': f'{query!r} did not give a specific structure.'}
    formula = rdMolDescriptors.CalcMolFormula(mol)
    entry = library.by_smiles(smiles)
    return {'ok': True, 'name': entry['name'] if entry else (name or formula), 'smiles': Chem.MolToSmiles(mol),
            'formula': formula, 'mw': round(Descriptors.MolWt(mol), 4), 'density': entry['density'] if entry else None,
            'svg': depiction(smiles), 'source': source}


# --- the ChemDraw canvas --------------------------------------------------------------

def blank_canvas() -> str:
    from cdxml_toolkit.cdxml_builder import _PAGE_OPEN, _header
    from cdxml_toolkit.constants import CDXML_FOOTER
    return _header('0 0 0 0') + _PAGE_OPEN.format(page_id=1) + '</page>' + CDXML_FOOTER


def scheme_yaml(state: dict) -> str | None:
    """A scheme of the state's reactants and products, with agents as structures above the arrow."""
    rows = state.get('rows', [])
    structures, ids = {}, {}
    for row in rows:
        if row.get('smiles') and row['role'] != 'solvent':
            key = f"S{len(structures) + 1}"
            structures[key], ids[row['id']] = {'smiles': row['smiles']}, key
    reactants = [ids[r['id']] for r in rows if r['role'] == 'reactant' and r['id'] in ids]
    products = [ids[r['id']] for r in rows if r['role'] == 'product' and r['id'] in ids]
    if not reactants or not products:
        return None
    agents = [ids[r['id']] for r in rows if r['role'] in ('reagent', 'catalyst') and r['id'] in ids]
    below = ', '.join(r['name'] for r in rows if r['role'] == 'solvent')
    lines = ['layout: linear', 'structures:']
    for key, value in structures.items():
        lines += [f'  {key}:', f"    smiles: {json.dumps(value['smiles'])}"]
    lines += ['steps:', f"  - substrates: [{', '.join(reactants)}]", f"    products: [{', '.join(products)}]"]
    if agents:
        lines += ['    above_arrow:', f"      structures: [{', '.join(agents)}]"]
    if below:
        lines += ['    below_arrow:', f'      text: [{json.dumps(below)}]']
    return '\n'.join(lines) + '\n'


def open_in_chemdraw(path: Path) -> bool:
    """Show a file in ChemDraw (the user asked to draw, so a window is expected)."""
    if sys.platform == 'darwin':
        return subprocess.run(['open', '-a', 'ChemDraw', str(path)], capture_output=True).returncode == 0
    if sys.platform == 'win32':
        os.startfile(str(path))  # noqa: S606 - ChemDraw is the .cdxml handler
        return True
    return False


def _sides_from_descriptor(path: Path) -> dict:
    """Fallback for a drawing without stored reaction steps: classify the structures by their arrow position."""
    from cdxml_toolkit.mcp_runtime import official_overrides as api
    with tempfile.TemporaryDirectory(prefix='cdx-calc-parse-') as folder:
        parsed = api.parse_reaction(cdxml=str(path), output_path=str(Path(folder) / 'reaction.json'))
        descriptor = json.loads(Path(parsed['output_path']).read_text(encoding='utf-8'))
    sides = {'reactants': [], 'agents': [], 'products': []}
    for species in descriptor.get('species', []):
        smiles = species.get('smiles') or species.get('smiles_neutral')
        if not smiles or canonical(smiles) is None:
            continue  # a label or abbreviation the parser could not turn into a structure
        record = {'smiles': smiles}
        key = 'products' if species.get('is_dp') else 'reactants' if species.get('role') == 'atom_contributing' else 'agents'
        sides[key].append(record)
    if not sides['reactants'] or not sides['products']:
        raise ValueError('The drawing has no reactant and product the arrow connects')
    return sides


def load_drawing(path: Path, previous: dict | None, options: dict | None = None) -> tuple[dict, str]:
    """Calculator state for the reaction in a saved CDXML file, keeping the amounts already entered."""
    from cdxml_toolkit.mcp_runtime.report_tools import _reaction_sources, _side
    try:
        sources = _reaction_sources({'cdxml': str(path)})
        sides = {role: _side(sources[0][role], role[:-1]) for role in ('reactants', 'agents', 'products')}
    except ValueError as exc:
        if 'No reaction step' not in str(exc) and 'has no drawn' not in str(exc):
            raise
        raw = _sides_from_descriptor(path)
        sides = {role: _side(raw[role], role[:-1]) for role in ('reactants', 'agents', 'products')}
    state = build_state(sides, options)
    summary = f"{len(sides['reactants'])} reactant(s), {len(sides['agents'])} agent(s), {len(sides['products'])} product(s)"
    return (merge_states(previous, state) if previous and previous.get('rows') else state), summary


_CLASS = {'reactant': 'amount', 'reagent': 'amount', 'catalyst': 'amount', 'solvent': 'solvent', 'product': 'product'}


def merge_states(old: dict, new: dict) -> dict:
    """The new rows, with the amounts, names and properties of rows whose structure was already there."""
    previous = {}
    for row in old['rows']:
        key = canonical(row.get('smiles'))
        if key:
            previous.setdefault(key, row)
    try:
        old_scale = compute(old)['totals']['limiting_mmol']
    except ValueError:
        old_scale = 1.0
    old_limiting = next((r for r in old['rows'] if r['id'] == old.get('limiting')), None)
    merged = {'title': new.get('title'), 'limiting': new['limiting'], 'rows': []}
    seen = set()
    for row in new['rows']:
        key = canonical(row.get('smiles'))
        seen.add(key)
        match = previous.get(key)
        if match:
            for field in ('density', 'solution_m', 'purity', 'coefficient'):
                row[field] = match.get(field, row.get(field))
            if match['name'] != match.get('formula'):
                row['name'] = match['name']
            if _CLASS[match['role']] == _CLASS[row['role']] and match.get('basis') is not None:
                row['basis'], row['value'], row['assumed'] = match['basis'], match['value'], match.get('assumed', False)
            if old_limiting is not None and match['id'] == old_limiting['id'] and row['role'] == 'reactant':
                merged['limiting'] = row['id']
        merged['rows'].append(row)
    for row in old['rows']:  # solvents are written under the arrow, not drawn, so they stay
        if row['role'] == 'solvent' and canonical(row.get('smiles')) not in seen:
            merged['rows'].append({**row, 'id': f"s{len(merged['rows']) + 1}"})
    limiting = next(r for r in merged['rows'] if r['id'] == merged['limiting'])
    if limiting['basis'] == 'equiv':
        limiting['basis'], limiting['value'] = 'mmol', old_scale
    compute(merged)
    return merged


# --- HTTP -------------------------------------------------------------------------------

class CalculatorApp:
    def __init__(self, state: dict, *, offline: bool = False, idle_seconds: float = 180.0,
                 max_seconds: float = 4 * 3600, workdir: Path | None = None, opener=open_in_chemdraw):
        self.state, self.offline, self.opener = state, offline, opener
        self.token = secrets.token_urlsafe(16)
        self.workdir = Path(workdir) if workdir else Path(tempfile.mkdtemp(prefix='cdx-calc-'))
        self.workdir.mkdir(parents=True, exist_ok=True)
        self.canvas: Path | None = None
        self.canvas_key: str | None = None
        self.idle_seconds, self.max_seconds = idle_seconds, max_seconds
        self.started = self.last_seen = time.monotonic()
        self.httpd: ThreadingHTTPServer | None = None
        self.lock = threading.Lock()

    # -- canvas
    def open_canvas(self, state: dict) -> dict:
        yaml_text = scheme_yaml(state) if state.get('rows') else None
        key = json.dumps([[r['smiles'], r['role']] for r in state.get('rows', [])], sort_keys=True)
        with self.lock:
            if self.canvas is None or self.canvas_key != key or not self.canvas.exists():
                target = self.workdir / (f'reaction-{len(list(self.workdir.glob("reaction*.cdxml"))) + 1}.cdxml')
                if yaml_text:
                    from cdxml_toolkit.mcp_runtime import official_overrides as api
                    api.render_scheme(yaml_text=yaml_text, output_path=str(target))
                else:
                    target.write_text(blank_canvas(), encoding='utf-8')
                self.canvas, self.canvas_key = target, key
            canvas = self.canvas
        if not self.opener(canvas):
            return {'ok': False, 'error': f'ChemDraw could not be opened on this system. Open {canvas} yourself, '
                                          'draw there, save, then press Load drawing.'}
        return {'ok': True, 'path': str(canvas)}

    def load_canvas(self, previous: dict | None) -> dict:
        if self.canvas is None or not self.canvas.exists():
            return {'ok': False, 'error': 'No drawing yet: press Draw in ChemDraw first.'}
        try:
            state, summary = load_drawing(self.canvas, previous)
        except ValueError as exc:
            return {'ok': False, 'error': f'{exc}. Save the drawing in ChemDraw (Ctrl+S) with the arrow between '
                                          'the reactants and the products, then press Load drawing again.'}
        return {'ok': True, 'state': state, 'summary': summary}

    # -- serving
    def handler(self):
        app = self

        class Handler(BaseHTTPRequestHandler):
            server_version = 'cdx-calc'

            def log_message(self, *args):
                pass

            def _host_ok(self):
                port = app.httpd.server_address[1]
                return self.headers.get('Host') in (f'127.0.0.1:{port}', f'localhost:{port}')

            def _send(self, code, body, kind='application/json'):
                data = body if isinstance(body, bytes) else body.encode('utf-8')
                self.send_response(code)
                self.send_header('Content-Type', f'{kind}; charset=utf-8')
                self.send_header('Content-Length', str(len(data)))
                self.send_header('Cache-Control', 'no-store')
                self.send_header('X-Content-Type-Options', 'nosniff')
                self.send_header('Content-Security-Policy',
                                 "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; "
                                 "connect-src 'self'; img-src data:; form-action 'none'; base-uri 'none'")
                self.end_headers()
                self.wfile.write(data)

            def do_GET(self):
                if not self._host_ok():
                    return self._send(403, '{"error":"bad host"}')
                if self.path.rstrip('/') == f'/{app.token}':
                    app.last_seen = time.monotonic()
                    return self._send(200, render_page(app.state, token=app.token), 'text/html')
                self._send(404, '{"error":"not found"}')

            def do_POST(self):
                if not self._host_ok() or not secrets.compare_digest(self.headers.get('X-Token', ''), app.token):
                    return self._send(403, '{"ok":false,"error":"forbidden"}')
                length = int(self.headers.get('Content-Length') or 0)
                if length > MAX_BODY:
                    return self._send(413, '{"ok":false,"error":"too large"}')
                try:
                    body = json.loads(self.rfile.read(length) or b'{}')
                    app.last_seen = time.monotonic()
                    reply = app.route(self.path, body)
                except (ValueError, KeyError, TypeError) as exc:
                    reply = {'ok': False, 'error': str(exc)}
                except Exception as exc:  # keep the server alive; the page shows the message
                    reply = {'ok': False, 'error': f'{type(exc).__name__}: {exc}'}
                self._send(200, json.dumps(reply, ensure_ascii=False))

        return Handler

    def route(self, path: str, body: dict) -> dict:
        if path == '/api/ping':
            return {'ok': True}
        if path == '/api/resolve':
            return resolve(str(body.get('query', '')), offline=self.offline)
        if path == '/api/canvas':
            return self.open_canvas(body.get('state') or {'rows': []})
        if path == '/api/canvas/load':
            return self.load_canvas(body.get('state'))
        return {'ok': False, 'error': 'unknown endpoint'}

    def serve(self, *, port: int = 0, open_browser: bool = True, announce=print) -> None:
        self.httpd = ThreadingHTTPServer(('127.0.0.1', port), self.handler())
        url = f'http://127.0.0.1:{self.httpd.server_address[1]}/{self.token}'
        announce(json.dumps({'ok': True, 'url': url, 'workdir': str(self.workdir), 'offline': self.offline,
                             'pid': os.getpid(), 'idle_seconds': self.idle_seconds}), flush=True)

        def watch():
            while True:
                time.sleep(1.0)
                now = time.monotonic()
                if now - self.last_seen > self.idle_seconds or now - self.started > self.max_seconds:
                    self.httpd.shutdown()
                    return
        threading.Thread(target=watch, daemon=True).start()
        if open_browser:
            webbrowser.open(url)
        try:
            self.httpd.serve_forever(poll_interval=0.25)
        finally:
            self.httpd.server_close()
