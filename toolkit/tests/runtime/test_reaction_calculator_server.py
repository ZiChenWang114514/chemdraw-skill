import http.client
import json
import re
from pathlib import Path
import threading
import time
from urllib.parse import urlparse

import pytest

from cdxml_toolkit.mcp_runtime.report_tools import _side
from cdxml_toolkit.reaction_calculator import build_state, server
from cdxml_toolkit.reaction_calculator.__main__ import load_state

REACTION = {'reactants': [{'smiles': 'OCc1ccccc1', 'mass_mg': 108.14}, {'smiles': 'CC(=O)Cl', 'equiv': 1.2}],
            'agents': [{'smiles': 'CCN(CC)CC', 'equiv': 1.5}, {'smiles': 'ClCCl'}],
            'products': [{'smiles': 'CC(=O)OCc1ccccc1', 'name': 'benzyl acetate'}]}


def state_of(reaction=REACTION):
    return build_state({role: _side(reaction.get(role) or [], role[:-1])
                        for role in ('reactants', 'agents', 'products')})


# --- resolving what the user types -------------------------------------------

def test_resolve_prefers_the_library_then_smiles_then_the_reagent_database():
    thf = server.resolve('THF', offline=True)
    assert (thf['name'], thf['smiles'], thf['density'], thf['source']) == ('tetrahydrofuran', 'C1CCOC1', 0.889, 'library')
    ethanol = server.resolve('CCO', offline=True)
    assert ethanol['source'] == 'smiles' and ethanol['name'] == 'ethanol' and ethanol['mw'] == pytest.approx(46.069, abs=1e-3)
    boronic = server.resolve('PhB(OH)2', offline=True)
    assert boronic['ok'] and boronic['formula'] == 'C6H7BO2' and boronic['svg'].startswith('<svg')
    assert server.resolve('C1CCCCC1C(=O)O', offline=True)['name'] == 'C7H12O2'  # no library name: the formula


def test_resolve_refuses_nonsense_and_generic_atoms():
    assert server.resolve('', offline=True)['ok'] is False
    assert server.resolve('zzzqqq', offline=True)['ok'] is False
    assert 'specific structure' in server.resolve('C[*]', offline=True)['error']


# --- the ChemDraw canvas -------------------------------------------------------

def test_a_drawn_canvas_comes_back_with_the_amounts_already_entered(tmp_path):
    opened = []
    app = server.CalculatorApp(state_of(), workdir=tmp_path, opener=lambda path: opened.append(path) or True)
    first = app.open_canvas(app.state)
    assert first['ok'] and opened == [app.canvas] and app.canvas.read_text(encoding='utf-8').count('<step') == 1
    again = app.open_canvas(app.state)  # same reaction: the file the user may be drawing in is reused
    assert again['path'] == first['path']
    loaded = app.load_canvas(app.state)
    assert loaded['ok'] and loaded['summary'] == '2 reactant(s), 1 agent(s), 1 product(s)'
    rows = {r['name']: r for r in loaded['state']['rows']}
    assert (rows['benzyl alcohol']['basis'], rows['benzyl alcohol']['value']) == ('mass', 108.14)
    assert (rows['acetyl chloride']['basis'], rows['acetyl chloride']['value']) == ('equiv', 1.2)
    assert rows['triethylamine']['value'] == 1.5
    assert rows['dichloromethane']['role'] == 'solvent'  # written under the arrow, so it is kept, not drawn
    assert loaded['state']['limiting'] == rows['benzyl alcohol']['id']


def test_an_edited_drawing_changes_the_rows_and_keeps_what_still_matches(tmp_path):
    app = server.CalculatorApp(state_of(), workdir=tmp_path, opener=lambda path: True)
    app.open_canvas(app.state)
    swapped = {**REACTION, 'reactants': [REACTION['reactants'][0], {'smiles': 'O=C(Cl)c1ccccc1'}],
               'products': [{'smiles': 'O=C(OCc1ccccc1)c1ccccc1'}]}
    other = server.CalculatorApp(state_of(swapped), workdir=tmp_path / 'b', opener=lambda path: True)
    other.open_canvas(other.state)
    app.canvas = other.canvas  # as if the user had redrawn the reaction and saved
    loaded = app.load_canvas(app.state)['state']
    names = [r['name'] for r in loaded['rows'] if r['role'] == 'reactant']
    assert names == ['benzyl alcohol', 'benzoyl chloride']
    kept = next(r for r in loaded['rows'] if r['name'] == 'benzyl alcohol')
    assert (kept['basis'], kept['value']) == ('mass', 108.14)
    new = next(r for r in loaded['rows'] if r['name'] == 'benzoyl chloride')
    assert new['assumed'] is True and new['basis'] == 'equiv'


def test_a_drawing_without_stored_reaction_steps_is_read_by_arrow_position(tmp_path):
    app = server.CalculatorApp(state_of(), workdir=tmp_path, opener=lambda path: True)
    app.open_canvas(app.state)
    plain = tmp_path / 'no-steps.cdxml'
    plain.write_text(re.sub(r'<scheme.*?</scheme>', '', app.canvas.read_text(encoding='utf-8'), flags=re.S),
                     encoding='utf-8')
    state, summary = server.load_drawing(plain, None)
    assert summary.startswith('2 reactant(s)')
    assert [r['role'] for r in state['rows']].count('product') == 1


def test_load_before_drawing_and_a_blank_drawing_give_actionable_errors(tmp_path):
    app = server.CalculatorApp(state_of(), workdir=tmp_path, opener=lambda path: True)
    assert 'Draw in ChemDraw first' in app.load_canvas(None)['error']
    app.open_canvas({'rows': []})  # nothing known yet: a blank ACS-style canvas
    assert '<CDXML' in app.canvas.read_text(encoding='utf-8') and '<fragment' not in app.canvas.read_text(encoding='utf-8')
    assert 'Save the drawing in ChemDraw' in app.load_canvas(None)['error']
    refused = server.CalculatorApp(state_of(), workdir=tmp_path / 'x', opener=lambda path: False)
    assert refused.open_canvas(refused.state)['ok'] is False


def test_amounts_are_written_into_a_copy_of_the_drawing_and_the_canvas_is_left_alone(tmp_path):
    opened = []
    app = server.CalculatorApp(state_of(), workdir=tmp_path, opener=lambda path: opened.append(path) or True)
    assert app.write_scheme({'rows': []})['ok'] is False
    fresh = app.write_scheme(app.state)                      # no drawing yet: the scheme is drawn from the state
    assert fresh['ok'] and fresh['unplaced'] == [] and 'dichloromethane (5.00 mL' in open(fresh['path'], encoding='utf-8').read()
    app.open_canvas(app.state)
    before = app.canvas.read_text(encoding='utf-8')
    again = app.write_scheme(app.state)                      # a drawing exists: its copy is annotated
    assert again['ok'] and again['path'] != fresh['path'] and again['unplaced'] == ['dichloromethane']
    assert app.canvas.read_text(encoding='utf-8') == before
    assert '108 mg' in open(again['path'], encoding='utf-8').read() and str(opened[-1]) == again['path']
    refused = server.CalculatorApp(state_of(), workdir=tmp_path / 'z', opener=lambda path: False)
    assert refused.write_scheme(refused.state)['ok'] is False


def test_command_line_inputs_become_the_starting_state(tmp_path):
    assert load_state(None, 1.0, None)['rows'] == []
    from_string = load_state('OCc1ccccc1.CC(=O)Cl>CCN(CC)CC.ClCCl>CC(=O)OCc1ccccc1', 5.0, 0.1)
    assert next(r for r in from_string['rows'] if r['role'] == 'reactant')['value'] == 5.0
    assert next(r for r in from_string['rows'] if r['role'] == 'solvent')['value'] == 0.1
    record = tmp_path / 'r.json'
    record.write_text(json.dumps(REACTION), encoding='utf-8')
    assert load_state(str(record), 1.0, None)['limiting'] == 'r1'


# --- the local web server ---------------------------------------------------------

class Running:
    def __init__(self, tmp_path, idle=60.0):
        lines = []
        self.app = server.CalculatorApp(state_of(), workdir=tmp_path, idle_seconds=idle, offline=True,
                                        opener=lambda path: True)
        self.thread = threading.Thread(target=lambda: self.app.serve(open_browser=False, announce=lambda *a, **k: lines.append(a[0])),
                                       daemon=True)
        self.thread.start()
        for _ in range(100):
            if lines:
                break
            time.sleep(0.05)
        info = json.loads(lines[0])
        parsed = urlparse(info['url'])
        self.port, self.path, self.info = parsed.port, parsed.path, info

    def request(self, method, path, body=None, headers=None, host=None):
        connection = http.client.HTTPConnection('127.0.0.1', self.port, timeout=10)
        merged = {'Host': host or f'127.0.0.1:{self.port}', **(headers or {})}
        connection.request(method, path, body=json.dumps(body) if body is not None else None, headers=merged)
        response = connection.getresponse()
        data = response.read().decode('utf-8')
        connection.close()
        return response.status, data

    def post(self, path, body=None):
        return self.request('POST', path, body or {}, {'X-Token': self.app.token, 'Content-Type': 'application/json'})

    def stop(self):
        self.app.httpd.shutdown()
        self.thread.join(5)


def test_server_starts_without_a_reverse_dns_lookup(tmp_path, monkeypatch):
    # http.server resolves the host name of the bound address, and that lookup can stall for
    # seconds (seen on macOS). The page is only ever served on 127.0.0.1, so no lookup is needed.
    import socket

    def no_lookup(*args, **kwargs):
        raise AssertionError('reverse DNS lookup while starting the calculator server')
    monkeypatch.setattr(socket, 'getfqdn', no_lookup)
    run = Running(tmp_path)
    assert run.request('GET', run.path)[0] == 200


def test_server_serves_the_page_and_guards_every_call(tmp_path):
    run = Running(tmp_path)
    try:
        assert run.info['offline'] is True and run.path == f'/{run.app.token}'
        status, page = run.request('GET', run.path)
        assert status == 200 and run.app.token in page and 'Reaction calculator' in page
        assert run.request('GET', '/')[0] == 404
        assert run.request('GET', run.path, host='evil.example:80')[0] == 403          # DNS rebinding
        assert run.request('POST', '/api/ping', {})[0] == 403                           # no token
        assert run.request('POST', '/api/ping', {}, {'X-Token': 'wrong'})[0] == 403
        status, body = run.post('/api/ping')
        assert status == 200 and json.loads(body) == {'ok': True}
        reply = json.loads(run.post('/api/resolve', {'query': 'DIPEA'})[1])
        assert reply['ok'] and reply['smiles'] == 'CCN(C(C)C)C(C)C'
        assert json.loads(run.post('/api/resolve', {'query': 'zzzqqq'})[1])['ok'] is False
        assert json.loads(run.post('/api/nothing')[1])['ok'] is False
        opened = json.loads(run.post('/api/canvas', {'state': run.app.state})[1])
        assert opened['ok'] and opened['path'].startswith(str(tmp_path))
        loaded = json.loads(run.post('/api/canvas/load', {'state': run.app.state})[1])
        assert loaded['ok'] and loaded['state']['limiting'] == 'r1'
        assert run.request('POST', '/api/ping', None, {'X-Token': run.app.token, 'Content-Length': '99999999'})[0] == 413
    finally:
        run.stop()


def test_server_stops_when_the_page_goes_away(tmp_path):
    run = Running(tmp_path, idle=1.2)
    run.thread.join(8)
    assert not run.thread.is_alive()
