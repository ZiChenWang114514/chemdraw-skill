import pytest

from cdxml_toolkit.engines import env
from cdxml_toolkit.mcp_runtime.engine_tools import predict_nmr


def ethanol_atoms():
    """CH3-CH2-OH with explicit hydrogens, as the worker reports them."""
    return {'geometry': 'test', 'atoms': [
        {'index': 0, 'element': 'C', 'shift': 18.0, 'class': 1, 'neighbors': [1, 3, 4, 5]},
        {'index': 1, 'element': 'C', 'shift': 58.0, 'class': 2, 'neighbors': [0, 2, 6, 7]},
        {'index': 2, 'element': 'O', 'shift': None, 'class': 3, 'neighbors': [1, 8]},
        {'index': 3, 'element': 'H', 'shift': 1.20, 'class': 4, 'neighbors': [0]},
        {'index': 4, 'element': 'H', 'shift': 1.22, 'class': 4, 'neighbors': [0]},
        {'index': 5, 'element': 'H', 'shift': 1.18, 'class': 4, 'neighbors': [0]},
        {'index': 6, 'element': 'H', 'shift': 3.70, 'class': 5, 'neighbors': [1]},
        {'index': 7, 'element': 'H', 'shift': 3.74, 'class': 5, 'neighbors': [1]},
        {'index': 8, 'element': 'H', 'shift': 2.40, 'class': 6, 'neighbors': [2]}]}


@pytest.fixture
def engine(monkeypatch):
    seen = {}

    def call(name, action, params, timeout=0):
        seen.update(params=params)
        return ethanol_atoms()

    monkeypatch.setattr(env, 'call', call)
    return seen


def test_equivalent_protons_become_one_peak_and_everything_is_marked_predicted(engine):
    answer = predict_nmr('CCO', '1H', 'CDCl3')
    assert engine['params'] == {'smiles': 'CCO', 'solvent': 'chloroform'}  # NMR solvent names are understood
    peaks = answer['peaks']['1H']
    assert [(p['shift_ppm'], p['count']) for p in peaks] == [(3.72, 2), (2.4, 1), (1.2, 3)]
    assert all(p['predicted'] for p in peaks) and answer['predicted'] is True
    assert answer['provenance'] == 'model_prediction'
    assert [p['exchangeable'] for p in peaks] == [False, True, False]
    assert any('not measured data' in w for w in answer['warnings']) and any('OH/NH' in w for w in answer['warnings'])


def test_carbon_peaks_and_both_nuclei(engine):
    answer = predict_nmr('CCO', 'both')
    assert [p['shift_ppm'] for p in answer['peaks']['13C']] == [58.0, 18.0]
    assert set(answer['peaks']) == {'1H', '13C'}


def test_a_simulated_spectrum_is_a_new_csv_with_the_peaks_where_predicted(engine, tmp_path):
    target = tmp_path / 'ethanol.csv'
    answer = predict_nmr('CCO', '1H', output_path=str(target))
    rows = [line.split(',') for line in target.read_text().splitlines()[1:]]
    assert target.read_text().startswith('ppm,intensity\n') and float(rows[0][0]) > float(rows[-1][0])
    top = max(rows, key=lambda r: float(r[1]))
    assert abs(float(top[0]) - 1.2) < 0.05  # the three-proton methyl is the tallest line
    assert answer['simulated_spectra'] == {'1H': str(target)}
    with pytest.raises(ValueError, match='exists'):
        predict_nmr('CCO', '1H', output_path=str(target))


def test_inputs_are_checked_before_the_engine_starts(monkeypatch):
    monkeypatch.setattr(env, 'call', lambda *a, **k: pytest.fail('engine must not start'))
    with pytest.raises(ValueError, match='supports H, C, N, O, F, Cl, S only; found Br'):
        predict_nmr('CBr')
    with pytest.raises(ValueError, match='one molecule'):
        predict_nmr('CC(=O)[O-].[Na+]')
    with pytest.raises(ValueError, match='unknown solvent'):
        predict_nmr('CCO', solvent='lava')
    with pytest.raises(ValueError, match='nucleus'):
        predict_nmr('CCO', nucleus='31P')
    with pytest.raises(ValueError, match='not valid'):
        predict_nmr('C(C)(C)(C)(C)C')


def test_a_missing_engine_is_reported_with_the_install_command():
    answer = predict_nmr('CCO')
    assert answer['ok'] is False and 'install-engines magnet' in answer['error']
