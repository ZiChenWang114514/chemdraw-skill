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
    assert engine['params'] == {'smiles': 'CCO', 'solvent': 'chloroform', 'nuclei': ['1H']}  # NMR solvent names are understood
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


def test_two_engines_are_compared_peak_by_peak_and_never_averaged(monkeypatch):
    seen = []
    shifted = ethanol_atoms()
    shifted['atoms'][1]['shift'] = 64.5  # the second engine puts the CH2 carbon 6.5 ppm away

    def call(name, action, params, timeout=0):
        seen.append(name)
        return ethanol_atoms() if name == 'magnet' else shifted

    monkeypatch.setattr(env, 'call', call)
    answer = predict_nmr('CCO', 'both', engine='magnet,nmrnet-pp')
    assert seen == ['magnet', 'nmrnet-pp'] and answer['engine'] == 'magnet,nmrnet-pp'
    assert [e['engine'] for e in answer['engines']] == ['magnet', 'nmrnet-pp']
    rows = {tuple(r['atoms']): r for r in answer['comparison']['peaks']['13C']}
    assert rows[(1,)]['shift_ppm'] == {'magnet': 58.0, 'nmrnet-pp': 64.5} and rows[(1,)]['spread_ppm'] == 6.5
    assert rows[(1,)]['needs_review'] is True and rows[(0,)]['needs_review'] is False
    assert answer['comparison']['needs_review'] is True and answer['predicted'] is True
    assert answer['provenance'] == 'model_prediction'


def test_every_named_engine_must_support_the_elements(monkeypatch):
    monkeypatch.setattr(env, 'call', lambda *a, **k: pytest.fail('engine must not start'))
    with pytest.raises(ValueError, match='MagNET supports'):
        predict_nmr('CBr', engine='nmrnet-pp,magnet')
    with pytest.raises(ValueError, match='each engine once'):
        predict_nmr('CCO', engine='magnet,magnet')


def test_simulated_lines_keep_their_height_wherever_they_fall_on_the_grid():
    from cdxml_toolkit.engines import nmr

    for nucleus in ('1H', '13C'):
        for frequency in (300.0, 400.0, 1200.0):
            for shift in (1.2, 1.2037, 7.2613, 10.019):
                peak = {'shift_ppm': shift, 'count': 1}
                top = max(y for _, y in nmr.simulate([peak], nucleus, frequency, points=16384))
                assert 0.9 <= top <= 1.0001, (nucleus, frequency, shift, top)


def test_a_shift_beyond_the_usual_range_stays_on_the_spectrum():
    from cdxml_toolkit.engines import nmr

    for nucleus, shift in (('1H', 13.2), ('1H', -2.5), ('13C', 245.0), ('13C', -20.0)):
        rows = nmr.simulate([{'shift_ppm': shift, 'count': 1}], nucleus, 400.0)
        top = max(rows, key=lambda row: row[1])
        assert top[1] > 0.9 and abs(top[0] - shift) < 0.05, (nucleus, shift)
        assert rows[0][0] > rows[-1][0]


def test_one_missing_engine_does_not_throw_away_the_finished_answer(monkeypatch):
    def call(name, action, params, timeout=0):
        if name == 'nmrnet-pp':
            raise env.EngineMissing(name, 'NMRNet++ is not installed: run `cdx.py install-engines nmrnet-pp`')
        return ethanol_atoms()

    monkeypatch.setattr(env, 'call', call)
    answer = predict_nmr('CCO', 'both', engine='magnet,nmrnet-pp')
    assert answer['ok'] is True and answer['engine'] == 'magnet' and answer['peaks']['13C'][0]['shift_ppm'] == 58.0
    assert 'comparison' not in answer and any('nmrnet-pp' in w and 'compare' in w for w in answer['warnings'])
    failed = answer['failed_engines'][0]
    assert failed['engine'] == 'nmrnet-pp' and failed['install_hint']['command'] == 'cdx.py install-engines nmrnet-pp'


def test_when_every_engine_fails_each_install_hint_is_kept():
    answer = predict_nmr('CCO', engine='magnet,nmrnet-pp')
    assert answer['ok'] is False and answer['engine'] == 'magnet'
    assert [f['engine'] for f in answer['failed_engines']] == ['magnet', 'nmrnet-pp']
    assert all(f['install_hint'] for f in answer['failed_engines'])


def test_an_existing_output_file_is_refused_before_the_engine_runs(tmp_path, monkeypatch):
    monkeypatch.setattr(env, 'call', lambda *a, **k: pytest.fail('engine must not start'))
    (tmp_path / 'spectrum-13C.csv').write_text('keep')
    with pytest.raises(ValueError, match='exists'):
        predict_nmr('CCO', 'both', output_path=str(tmp_path / 'spectrum.csv'))
    assert (tmp_path / 'spectrum-13C.csv').read_text() == 'keep'


def test_experimental_peaks_turn_a_prediction_into_a_peak_assignment(engine):
    answer = predict_nmr('CCO', '1H', 'CDCl3', experimental_1h=[3.69, 2.35, 1.25], experimental_13c=[58.4, 18.2])
    assert set(answer['peaks']) == {'1H', '13C'}  # the nuclei with experimental peaks are predicted, whatever `nucleus` says
    comparison = answer['experimental_comparison']
    assert comparison['kind'] == 'model_assisted_candidate_assignment'
    assert comparison['prediction_source'] == 'supplied'  # the prediction made by this very call
    pairs = {(m['predicted_shift'], m['experimental_shift']) for m in comparison['matches_1h']}
    assert pairs == {(3.72, 3.69), (2.4, 2.35), (1.2, 1.25)}
    assert comparison['mae_1h'] == pytest.approx(0.0433, abs=1e-4)
    assert comparison['mae_13c'] == pytest.approx(0.3, abs=1e-4)
    assert comparison['outliers'] == []
    assert answer['provenance'] == 'model_prediction'  # still a prediction, never measured data


def test_a_wrong_peak_is_flagged_as_an_outlier_and_the_engine_is_asked_for_the_experimental_nuclei(engine):
    answer = predict_nmr('CCO', experimental_13c=[58.4, 30.0])
    assert engine['params']['nuclei'] == ['13C']
    assert [m['atoms'] for m in answer['experimental_comparison']['outliers']] and \
        answer['experimental_comparison']['outliers'][0]['experimental_shift'] == 30.0


def test_comparison_needs_one_engine_and_no_experimental_peaks_means_no_comparison(engine):
    with pytest.raises(ValueError, match='one engine'):
        predict_nmr('CCO', engine='magnet,nmrnet-pp', experimental_1h=[1.2])
    assert 'experimental_comparison' not in predict_nmr('CCO')
