"""Drive the calculator page in a headless browser: type into fields and read the table back."""
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from cdxml_toolkit.mcp_runtime.report_tools import reaction_calculator

CANDIDATES = (
    r'C:\Program Files\Google\Chrome\Application\chrome.exe',
    r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    '/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge',
)


def browser():
    for name in ('google-chrome', 'chromium', 'chromium-browser', 'chrome', 'msedge'):
        found = shutil.which(name)
        if found:
            return found
    return next((path for path in CANDIDATES if Path(path).exists()), None)


pytestmark = pytest.mark.skipif(
    browser() is None or (os.environ.get('CI') and not os.environ.get('CDXML_BROWSER_TESTS')),
    reason='needs Chrome or Edge (set CDXML_BROWSER_TESTS=1 to run in CI)')

REACTION = {'reactants': [{'smiles': 'OCc1ccccc1', 'mass_mg': 108.14}, {'smiles': 'CC(=O)Cl', 'equiv': 1.2}],
            'agents': [{'smiles': 'CCN(CC)CC', 'equiv': 1.5}, {'smiles': 'ClCCl'}],
            'products': [{'smiles': 'CC(=O)OCc1ccccc1', 'name': 'benzyl acetate'}]}

DRIVER = r"""
(function () {
  var out = {};
  function input(id, field) { return document.querySelector('input[data-id="' + id + '"][data-field="' + field + '"]'); }
  function val(id, field) { return Number(input(id, field).value); }
  function type(id, field, text) { var i = input(id, field); i.value = text; i.dispatchEvent(new Event('change', { bubbles: true })); }
  function click(selector) { document.querySelector(selector).click(); }
  function status() { return document.getElementById('status').textContent; }
  try {
    out.start = { mass: val('r1', 'mass'), mmol: val('r1', 'mmol'), acetyl: val('r2', 'mass'), solvent: val('a2', 'volume') };
    out.limitingEquivDisabled = input('r1', 'equiv').disabled;
    type('r1', 'mass', '216.28');
    out.doubled = { mmol: val('r1', 'mmol'), acetyl: val('r2', 'mass'), solvent: val('a2', 'volume'), fixed: input('r1', 'mass').classList.contains('fixed') };
    type('r2', 'mmol', '3');
    out.acetylFixed = { equiv: val('r2', 'equiv'), fixed: input('r2', 'mmol').classList.contains('fixed'), equivFixed: input('r2', 'equiv').classList.contains('fixed') };
    type('a1', 'volume', '1');
    out.tea = { mmol: val('a1', 'mmol'), mass: val('a1', 'mass') };
    type('a2', 'conc', '0.5');
    out.conc = { volume: val('a2', 'volume') };
    click('tr[data-row="r2"] input[type=radio]');
    out.rebased = { acetylEquiv: val('r2', 'equiv'), alcoholEquiv: val('r1', 'equiv'), alcoholMass: val('r1', 'mass'), solventVolume: val('a2', 'volume'), status: status() };
    type('p1', 'yield', '90');
    out.product = { actual: val('p1', 'actual'), theory: val('p1', 'theory_mg') };
    type('p1', 'actual', '500');
    out.productOver = { yield: val('p1', 'yield'), warning: document.getElementById('warnings').textContent };
    type('a1', 'density', '');
    out.needsDensity = { status: status(), density: val('a1', 'density') };
    click('#undo');
    out.undone = { yield: val('p1', 'yield') };
    document.getElementById('add-role').value = 'solvent';
    document.getElementById('add-name').value = 'THF';
    click('#add');
    out.thf = { rows: document.querySelectorAll('#rows tr[data-row]').length, last: document.querySelector('#rows tr[data-row]:last-child input.txt').value };
    document.getElementById('add-role').value = 'catalyst';
    document.getElementById('add-name').value = 'Pd(PPh3)4';
    click('#add');
    var pd = Array.prototype.filter.call(document.querySelectorAll('#rows tr[data-row]'), function (tr) { return tr.querySelector('input.txt').value === 'Pd(PPh3)4'; })[0];
    out.pd = { name: pd.querySelector('input.txt').value, mw: pd.querySelector('input[data-field=mw]').value, equiv: pd.querySelector('input[data-field=equiv]').value };
    document.getElementById('add-role').value = 'reagent';
    document.getElementById('add-name').value = 'mystery stuff';
    var before = document.querySelectorAll('#rows tr[data-row]').length;
    click('#add');
    out.unknown = { added: document.querySelectorAll('#rows tr[data-row]').length - before, status: status() };
    document.getElementById('add-mw').value = '250';
    click('#add');
    out.custom = { added: document.querySelectorAll('#rows tr[data-row]').length - before };
    out.procedure = document.getElementById('procedure').textContent;
    out.draw = document.getElementById('draw').disabled;
    out.stats = document.getElementById('stats').textContent;
  } catch (e) { out.error = String(e && e.stack || e); }
  var pre = document.createElement('pre');
  pre.id = 'testout';
  pre.textContent = JSON.stringify(out);
  document.body.appendChild(pre);
})();
"""


def run_page(html, tmp_path, driver=DRIVER):
    page = tmp_path / 'page.html'
    page.write_text(html.replace('</body>', f'<script>{driver}</script></body>'), encoding='utf-8')
    profile = tmp_path / 'profile'
    done = subprocess.run(
        [browser(), '--headless=new', '--disable-gpu', '--no-sandbox', f'--user-data-dir={profile}',
         '--virtual-time-budget=4000', '--dump-dom', page.as_uri()],
        capture_output=True, text=True, timeout=120, encoding='utf-8')
    match = re.search(r'<pre id="testout">(.*?)</pre>', done.stdout, re.S)
    assert match, done.stderr[-500:] + done.stdout[-500:]
    import html as htmllib
    return json.loads(htmllib.unescape(match.group(1)))


def test_typing_into_the_table_recomputes_every_other_quantity(tmp_path):
    result = reaction_calculator(REACTION, options={'molarity': 0.2}, output_path=str(tmp_path / 'calc.html'))
    assert result['ok']
    out = run_page(Path(result['output_path']).read_text(encoding='utf-8'), tmp_path)
    assert 'error' not in out, out.get('error') + json.dumps(out)
    assert out['start']['mmol'] == pytest.approx(1.0, abs=1e-3) and out['start']['solvent'] == pytest.approx(5.0, abs=0.01)
    assert out['limitingEquivDisabled'] is True
    # doubling the limiting mass doubles every amount that follows it and the solvent volume at fixed molarity
    assert out['doubled']['mmol'] == pytest.approx(2.0, abs=1e-2)
    assert out['doubled']['acetyl'] == pytest.approx(2 * out['start']['acetyl'], rel=1e-2)
    assert out['doubled']['solvent'] == pytest.approx(10.0, abs=0.05) and out['doubled']['fixed'] is True
    # fixing the second reactant by mmol turns its equivalents into a result
    assert out['acetylFixed'] == {'equiv': pytest.approx(1.5, abs=1e-2), 'fixed': True, 'equivFixed': False}
    assert out['tea']['mmol'] == pytest.approx(1.0 * 0.726 * 1000 / 101.193, rel=1e-2)
    assert out['conc']['volume'] == pytest.approx(4.0, abs=0.05)
    # switching the limiting reagent changes no amount, only the equivalents
    assert out['rebased']['acetylEquiv'] == pytest.approx(1.0) and out['rebased']['alcoholEquiv'] == pytest.approx(2 / 3, abs=1e-3)
    assert out['rebased']['alcoholMass'] == pytest.approx(216.3, abs=0.1)
    assert out['rebased']['solventVolume'] == pytest.approx(4.0, abs=0.05)
    assert out['product']['actual'] == pytest.approx(0.9 * out['product']['theory'], rel=1e-2)
    assert out['productOver']['yield'] > 100 and 'above 100%' in out['productOver']['warning']
    assert 'density' in out['needsDensity']['status'] and out['needsDensity']['density'] == pytest.approx(0.726)
    assert out['undone']['yield'] == pytest.approx(90.0, abs=0.1)
    assert out['thf']['rows'] == 5 and out['thf']['last'] == 'tetrahydrofuran'
    assert out['pd']['name'] == 'Pd(PPh3)4' and float(out['pd']['mw']) == pytest.approx(1155.6, abs=0.6)
    assert float(out['pd']['equiv']) == pytest.approx(0.05)
    assert out['unknown']['added'] == 0 and 'molecular weight' in out['unknown']['status']
    assert out['custom']['added'] == 1
    assert out['procedure'].startswith('To a solution of') and 'equiv' in out['procedure']
    assert out['draw'] is True  # a standalone page cannot open ChemDraw
