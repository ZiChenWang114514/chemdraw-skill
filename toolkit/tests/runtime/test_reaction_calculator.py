"""The stoichiometry engine behind the materials tables and route summaries."""

import pytest

from cdxml_toolkit.reaction_calculator import compute
from cdxml_toolkit.reaction_calculator import library


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


def test_process_mass_intensity_counts_every_input_and_solvent_over_the_isolated_product():
    totals = compute(esterification())['totals']
    # inputs 200 + 150 + 400 mg, 10 mL of solvent at 1.325 g/mL, 240 mg isolated
    assert totals['solvent_mg'] == pytest.approx(13250.0)
    assert totals['solvents_without_mass'] == 0
    assert totals['pmi'] == pytest.approx((750.0 + 13250.0) / 240.0)
    assert totals['e_factor'] == pytest.approx(totals['pmi'] - 1.0)
    assert totals['pmi_no_solvent'] == pytest.approx(750.0 / 240.0)


def test_no_isolated_mass_means_no_pmi_and_a_solvent_without_density_is_counted_as_missing():
    state = esterification()
    state['rows'][-1].update(basis=None, value=None)
    assert 'pmi' not in compute(state)['totals']
    state = esterification()
    state['rows'][3]['density'] = None
    totals = compute(state)['totals']
    assert totals['solvents_without_mass'] == 1 and totals['solvent_mg'] is None
    assert totals['pmi'] == pytest.approx(750.0 / 240.0)


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


def test_library_recognises_common_reagents_by_structure_and_name():
    assert library.by_smiles('C1CCOC1')['name'] == 'tetrahydrofuran'
    assert library.by_smiles('CCN(CC)CC')['density'] == pytest.approx(0.726)
    assert library.by_name('  DIPEA ')['name'] == 'N,N-diisopropylethylamine'
    assert library.by_smiles('OC[C@H](O)CO') is None and library.by_smiles('not a smiles') is None
    smiles = [e['smiles'] for e in library.entries()]
    assert len(smiles) == len(set(smiles)) >= 50
