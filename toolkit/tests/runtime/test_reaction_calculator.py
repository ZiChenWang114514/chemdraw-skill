import json
import shutil
import subprocess
from pathlib import Path

import pytest
from rdkit import Chem
from rdkit.Chem import Descriptors

from cdxml_toolkit.mcp_runtime import official_overrides as api
from cdxml_toolkit.mcp_runtime.report_tools import reaction_calculator
from cdxml_toolkit.mcp_runtime.tool_registry import build_registry
from cdxml_toolkit.reaction_calculator import compute, rebase, render_page
from cdxml_toolkit.reaction_calculator import library

ENGINE_JS = Path(__file__).resolve().parents[2] / 'cdxml_toolkit' / 'reaction_calculator' / 'engine.js'


def row(id, role, basis, value, mw=100.0, **extra):
    return {'id': id, 'role': role, 'name': id, 'mw': mw, 'basis': basis, 'value': value, 'coefficient': 1,
            'density': None, 'solution_m': None, 'purity': 1.0, **extra}


def esterification():
    return {'limiting': 'a', 'rows': [
        row('a', 'reactant', 'mass', 200.0, mw=100.0),
        row('b', 'reagent', 'equiv', 1.5, mw=50.0),
        row('c', 'reagent', 'volume', 0.5, mw=100.0, density=0.8),
        row('s', 'solvent', 'conc', 0.2, mw=84.9, density=1.325),
        row('p', 'product', 'mass', 240.0, mw=150.0),
    ]}


def by_id(result):
    return {r['id']: r for r in result['rows']}


# --- engine ---------------------------------------------------------------

def test_amounts_follow_the_limiting_reagent_and_the_fixed_quantities():
    result = compute(esterification())
    rows = by_id(result)
    assert rows['a']['mmol'] == pytest.approx(2.0)
    assert rows['b']['mmol'] == pytest.approx(3.0) and rows['b']['mass_mg'] == pytest.approx(150.0)
    # 0.5 mL x 0.8 g/mL = 400 mg of M 100 = 4 mmol = 2 equiv
    assert rows['c']['mass_mg'] == pytest.approx(400.0)
    assert rows['c']['mmol'] == pytest.approx(4.0) and rows['c']['equiv'] == pytest.approx(2.0)
    assert rows['s']['volume_ml'] == pytest.approx(10.0)  # 2 mmol at 0.2 M
    assert result['totals']['concentration_m'] == pytest.approx(0.2)
    assert rows['p']['theory_mg'] == pytest.approx(300.0)
    assert rows['p']['yield_percent'] == pytest.approx(80.0)
    assert result['totals']['atom_economy_percent'] == pytest.approx(150.0 / 100.0 * 100.0)


def test_purity_and_stock_solutions():
    state = {'limiting': 'a', 'rows': [
        row('a', 'reactant', 'mass', 100.0, purity=0.8),
        row('b', 'reagent', 'volume', 0.4, solution_m=2.5),
    ]}
    rows = by_id(compute(state))
    assert rows['a']['mmol'] == pytest.approx(0.8)          # 100 mg of 80 % material
    assert rows['a']['mass_mg'] == pytest.approx(100.0)
    assert rows['b']['mmol'] == pytest.approx(1.0)           # 0.4 mL x 2.5 M
    assert rows['b']['equiv'] == pytest.approx(1.25)
    assert rows['b']['volume_ml'] == pytest.approx(0.4)


def test_coefficients_scale_the_theoretical_yield():
    state = esterification()
    state['rows'][-1]['coefficient'] = 2
    assert by_id(compute(state))['p']['theory_mmol'] == pytest.approx(4.0)


def test_changing_the_limiting_reagent_keeps_every_amount():
    before = compute(esterification())
    after = compute(rebase(esterification(), 'b'))
    assert after['limiting'] == 'b'
    for key, old in by_id(before).items():
        new = by_id(after)[key]
        for field in ('mmol', 'mass_mg', 'volume_ml'):
            assert new.get(field) == pytest.approx(old.get(field)), (key, field)
    assert by_id(after)['b']['equiv'] == pytest.approx(1.0)
    assert by_id(after)['a']['equiv'] == pytest.approx(2.0 / 3.0)


def test_invalid_states_are_refused_with_the_reason():
    state = esterification()
    state['rows'][0]['basis'] = 'equiv'
    with pytest.raises(ValueError, match='sets the scale'):
        compute(state)
    state = esterification()
    state['rows'][1].update(basis='volume', value=1.0)
    with pytest.raises(ValueError, match='density or a solution molarity'):
        compute(state)
    state = esterification()
    state['limiting'] = 'p'
    with pytest.raises(ValueError, match='limiting must name'):
        compute(state)
    state = esterification()
    state['rows'][0]['mw'] = 0
    with pytest.raises(ValueError, match='mw must be a positive'):
        compute(state)
    state = esterification()
    state['rows'][4]['value'] = 400.0
    assert compute(state)['warnings'] and 'above 100%' in compute(state)['warnings'][0]


# --- the page runs the same rules -------------------------------------------

CASES = {
    'esterification': esterification(),
    'rebased': rebase(esterification(), 'c'),
    'stock': {'limiting': 'a', 'rows': [row('a', 'reactant', 'mass', 100.0, purity=0.8),
                                        row('b', 'reagent', 'volume', 0.4, solution_m=2.5),
                                        row('p', 'product', 'yield', 75.0, mw=250.0, coefficient=2)]},
}


@pytest.mark.skipif(shutil.which('node') is None, reason='node is not installed')
def test_javascript_engine_matches_the_python_engine(tmp_path):
    script = tmp_path / 'run.js'
    script.write_text(
        "const E = require(process.argv[2]);\n"
        "const cases = JSON.parse(require('fs').readFileSync(0, 'utf8'));\n"
        "const out = {};\n"
        "for (const [k, v] of Object.entries(cases)) out[k] = E.compute(v);\n"
        "out.rebase = E.rebase(cases.esterification, 'b');\n"
        "out.weights = ['C6H12O6', 'NaCl', 'Pd(PPh3)4', 'CuSO4.5H2O', 'Et3N', 'xx', 'C6H12O6)'].map(f => E.formulaWeight(f));\n"
        "process.stdout.write(JSON.stringify(out));\n", encoding='utf-8')
    done = subprocess.run(['node', str(script), str(ENGINE_JS)], input=json.dumps(CASES), capture_output=True,
                          text=True, timeout=60, check=True)
    js = json.loads(done.stdout)
    for name, state in CASES.items():
        expected, got = compute(state), js[name]
        assert got['limiting'] == expected['limiting']
        for e, g in zip(expected['rows'], got['rows']):
            for key in ('mmol', 'equiv', 'mass_mg', 'volume_ml', 'theory_mmol', 'theory_mg', 'actual_mg',
                        'yield_percent'):
                assert g.get(key) == pytest.approx(e.get(key), rel=1e-12), (name, e['id'], key)
        for key, value in expected['totals'].items():
            assert got['totals'][key] == pytest.approx(value, rel=1e-12), (name, key)
    assert js['rebase']['limiting'] == 'b'
    mw = js['weights']
    assert mw[0] == pytest.approx(Descriptors.MolWt(Chem.MolFromSmiles('OCC(O)C(O)C(O)C(O)C=O')), abs=0.01)
    assert mw[1] == pytest.approx(58.44, abs=0.01)
    assert mw[2] == pytest.approx(1155.6, abs=0.1)
    assert mw[3] == pytest.approx(249.68, abs=0.01)
    assert mw[4] == pytest.approx(Descriptors.MolWt(Chem.MolFromSmiles('CCN(CC)CC')), abs=0.01)
    assert mw[5] is None and mw[6] is None


# --- library, state and the tool --------------------------------------------

def test_library_recognises_common_reagents_by_structure_and_name():
    assert library.by_smiles('C1CCOC1')['name'] == 'tetrahydrofuran'
    assert library.by_smiles('CCN(CC)CC')['density'] == pytest.approx(0.726)
    assert library.by_name('  DIPEA ')['name'] == 'N,N-diisopropylethylamine'
    assert library.by_smiles('OC[C@H](O)CO') is None and library.by_smiles('not a smiles') is None
    smiles = [e['smiles'] for e in library.entries()]
    assert len(smiles) == len(set(smiles)) >= 50


REACTION = {'reactants': [{'smiles': 'OCc1ccccc1', 'mass_mg': 108.14}, {'smiles': 'CC(=O)Cl', 'equiv': 1.2}],
            'agents': [{'smiles': 'CCN(CC)CC', 'equiv': 1.5}, {'smiles': 'ClCCl'}, {'smiles': '[Pd]', 'name': 'Pd'}],
            'products': [{'smiles': 'CC(=O)OCc1ccccc1', 'name': 'benzyl acetate', 'isolated_mg': 130}]}


def test_tool_tabulates_amounts_and_reports_what_it_assumed(tmp_path):
    out = tmp_path / 'calc.html'
    result = reaction_calculator(REACTION, options={'molarity': 0.1}, output_path=str(out))
    assert result['ok'] and result['operation'] == 'reaction_calculator'
    rows = {r['name']: r for r in result['rows']}
    assert rows['benzyl alcohol']['mmol'] == pytest.approx(1.0, abs=1e-3)
    assert rows['acetyl chloride']['mass_mg'] == pytest.approx(1.2 * 78.498, abs=0.05)
    assert rows['triethylamine']['volume_ml'] == pytest.approx(1.5 * 101.193 / 726.0, abs=2e-3)
    assert rows['dichloromethane']['volume_ml'] == pytest.approx(10.0, abs=0.01)
    assert rows['benzyl acetate']['yield_percent'] == pytest.approx(130 / 150.177 / 1.0 * 100, abs=0.2)
    assert result['totals']['concentration_m'] == pytest.approx(0.1)
    # the metal is taken as a 5 mol % catalyst, the solvent as a 0.1 M choice; both are said to be assumed
    assert rows['Pd']['fixed'] == {'basis': 'equiv', 'value': 0.05, 'assumed': True}
    assert set(result['assumed']) == {'dichloromethane', 'Pd'}
    page = out.read_text(encoding='utf-8')
    assert page.startswith('<!doctype html>')
    assert '<script src' not in page and '<link' not in page and 'xmlns' not in page and 'END OF HEADER' not in page
    with pytest.raises(Exception):
        reaction_calculator(REACTION, output_path=str(out))


def test_tool_accepts_a_reaction_string_and_a_drawn_scheme(tmp_path):
    result = reaction_calculator('OCc1ccccc1.CC(=O)Cl>CCN(CC)CC.ClCCl>CC(=O)OCc1ccccc1',
                                 options={'scale_mmol': 5}, output_path=str(tmp_path / 'a.html'))
    assert result['totals']['limiting_mmol'] == pytest.approx(5.0)
    scheme = tmp_path / 'ester.cdxml'
    api.render_scheme(yaml_text=('layout: linear\nstructures:\n  A: {smiles: "CCO"}\n  B: {smiles: "CC(=O)Cl"}\n'
                                 '  P: {smiles: "CCOC(C)=O"}\nsteps:\n  - substrates: [A, B]\n    products: [P]\n'),
                       output_path=str(scheme))
    drawn = reaction_calculator({'cdxml': str(scheme)}, options={'scale_mmol': 2}, output_path=str(tmp_path / 'b.html'))
    assert [r['role'] for r in drawn['rows']].count('reactant') == 2
    assert drawn['totals']['limiting_mmol'] == pytest.approx(2.0)


def test_tool_refuses_conflicting_or_unknown_input(tmp_path):
    bad = {**REACTION, 'reactants': [{'smiles': 'OCc1ccccc1', 'mass_mg': 100, 'mmol': 1}, REACTION['reactants'][1]]}
    with pytest.raises(ValueError, match='give only one'):
        reaction_calculator(bad, output_path=str(tmp_path / 'x.html'))
    with pytest.raises(ValueError, match='Unknown options'):
        reaction_calculator(REACTION, options={'html': 1}, output_path=str(tmp_path / 'y.html'))
    with pytest.raises(ValueError, match='sets the scale'):
        reaction_calculator({**REACTION, 'reactants': [{'smiles': 'OCc1ccccc1', 'equiv': 1}, REACTION['reactants'][1]]},
                            output_path=str(tmp_path / 'z.html'))
    with pytest.raises(ValueError, match='output_path must end'):
        reaction_calculator(REACTION, output_path=str(tmp_path / 'w.txt'))
    assert 'reaction_calculator' in build_registry()


def test_page_embeds_state_safely():
    state = {'title': '</script><b>x', 'limiting': 'a', 'rows': [row('a', 'reactant', 'mmol', 1.0, name='<img src=x onerror=1>')]}
    page = render_page(state)
    assert page.count('</script>') == 3  # the payload, the engine and the page script
    assert '<img src=x' not in page
