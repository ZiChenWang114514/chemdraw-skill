import copy
import json

import pytest

from cdxml_toolkit import spectral_text
from cdxml_toolkit.mcp_runtime.report_tools import characterization_text

BENZYL_ACETATE = {
    'label': '3a', 'smiles': 'CC(=O)OCc1ccccc1', 'appearance': 'colorless oil',
    'nmr': {'1H': {'frequency': 400, 'solvent': 'CDCl3', 'text': '7.40-7.30 (m, 5H), 5.11 (s, 2H), 2.10 (s, 3H)'},
            '13C': {'frequency': 101, 'solvent': 'CDCl3', 'peaks': ['171.0', '136.0', '128.6', '128.3', '128.2', '66.4', '21.1']}},
    'ir': {'medium': 'neat', 'values': [3034, 1738, 1229]},
    'adduct': '[M+Na]+', 'found_mz': 173.0572,
}


def run(record, options=None, **kwargs):
    return characterization_text([record], options, **kwargs)


def test_a_full_record_reads_as_an_acs_paragraph_in_the_usual_order():
    result = run(BENZYL_ACETATE)
    assert result['ok'] and result['count'] == 1 and result['warnings'] == []
    assert result['compounds'][0]['paragraph'] == (
        'colorless oil; IR (neat) 3034, 1738, 1229 cm-1; '
        '1H NMR (400 MHz, CDCl3) \u03b4 7.40\u20137.30 (m, 5H), 5.11 (s, 2H), 2.10 (s, 3H); '
        '13C NMR (101 MHz, CDCl3) \u03b4 171.0, 136.0, 128.6, 128.3, 128.2, 66.4, 21.1; '
        'HRMS (ESI) m/z calcd for C9H10O2Na [M+Na]+ 173.0573, found 173.0572.')
    assert result['text'] == '3a: ' + result['compounds'][0]['paragraph'] + '\n'
    assert result['compounds'][0]['checks'] == {
        '1H': {'integral': 10, 'formula_h': 10}, '13C': {'signals': 7, 'distinct_carbons': 7}}


def test_physical_data_come_before_the_spectra_and_each_one_is_optional():
    record = {'label': '5', 'smiles': 'OC[C@H](C)c1ccccc1', 'appearance': 'white solid', 'rf': {'value': 0.4, 'eluent': 'hexanes/EtOAc 4:1'},
              'mp': '112-114', 'optical_rotation': {'value': -12.3, 'c': 1.0, 'solvent': 'CHCl3', 'temperature': 20},
              'hrms': False}
    paragraph = run(record)['compounds'][0]['paragraph']
    assert paragraph == ('white solid; Rf = 0.4 (hexanes/EtOAc 4:1); mp 112\u2013114 \u00b0C; '
                         '[\u03b1]20D -12.3 (c 1.0, CHCl3).')
    assert run({'label': 'x', 'smiles': 'CCO', 'mp': 98.5, 'hrms': False})['compounds'][0]['paragraph'] == 'mp 98.5 \u00b0C.'
    assert run({'label': 'x', 'smiles': 'CCO', 'optical_rotation': {'value': 3.2, 'c': 0.5, 'solvent': 'MeOH'},
                'hrms': False})['compounds'][0]['paragraph'] == '[\u03b1]D +3.2 (c 0.5, MeOH).'


def test_proton_peaks_can_be_given_as_text_or_as_numbers_and_come_out_alike():
    structured = [{'range': [7.40, 7.30], 'mult': 'm', 'n': 5}, {'shift': 5.11, 'mult': 's', 'n': 2},
                  {'shift': 2.10, 'mult': 's', 'n': 3}]
    record = {**BENZYL_ACETATE, 'nmr': {**BENZYL_ACETATE['nmr'], '1H': {**BENZYL_ACETATE['nmr']['1H'], 'peaks': structured}}}
    del record['nmr']['1H']['text']
    assert run(record)['compounds'][0]['paragraph'] == run(BENZYL_ACETATE)['compounds'][0]['paragraph']


def test_coupling_constants_and_broad_signals_are_written_the_acs_way():
    text = '8.10 (d, J = 8.0 Hz, 1H), 7.55 (dd, J = 8.0, 2.0 Hz, 1H), 6.90 (br s, 1H), 1.25 (t, J=7.1 Hz, 3H)'
    peaks = spectral_text.parse_peaks(text)
    assert [p['mult'] for p in peaks] == ['d', 'dd', 'br s', 't']
    assert peaks[1]['J'] == ['8.0', '2.0'] and peaks[3]['J'] == ['7.1'] and peaks[0]['n'] == 1
    assert spectral_text.format_peaks(peaks) == ('8.10 (d, J = 8.0 Hz, 1H), 7.55 (dd, J = 8.0, 2.0 Hz, 1H), '
                                                '6.90 (br s, 1H), 1.25 (t, J = 7.1 Hz, 3H)')


def test_carbon_signals_may_carry_fluorine_coupling():
    peaks = spectral_text.parse_peaks('163.2 (d, J = 245.0 Hz), 129.1, 115.6 (d, J = 21.5 Hz)')
    assert spectral_text.format_peaks(peaks) == '163.2 (d, J = 245.0 Hz), 129.1, 115.6 (d, J = 21.5 Hz)'


def test_an_unreadable_peak_is_an_error_that_names_it():
    with pytest.raises(ValueError, match='7.26 \\(q'):
        spectral_text.parse_peaks('7.30 (m, 2H), 7.26 (q, J = , 2H)')


def test_too_few_or_too_many_protons_are_flagged_not_fixed():
    record = copy.deepcopy(BENZYL_ACETATE)
    record['nmr']['1H']['text'] = '7.40-7.30 (m, 5H), 5.11 (s, 2H)'
    result = run(record)
    assert result['compounds'][0]['checks']['1H'] == {'integral': 7, 'formula_h': 10}
    assert any('7 of 10 H' in w and 'exchangeable' in w for w in result['warnings'])
    assert '2.10' not in result['compounds'][0]['paragraph']  # nothing was added
    record['nmr']['1H']['text'] = '7.40-7.30 (m, 5H), 5.11 (s, 2H), 2.10 (s, 3H), 1.00 (s, 3H)'
    assert any('13 H' in w and 'more' in w for w in run(record)['warnings'])


def test_carbon_signal_count_is_compared_with_the_symmetry_distinct_carbons():
    record = copy.deepcopy(BENZYL_ACETATE)
    record['nmr']['13C']['peaks'] = ['171.0', '136.0', '128.6', '66.4', '21.1']
    result = run(record)
    assert result['compounds'][0]['checks']['13C'] == {'signals': 5, 'distinct_carbons': 7}
    assert any('5 signals' in w and '7' in w and 'overlap' in w for w in result['warnings'])
    record['nmr']['13C']['peaks'] = ['171.0', '136.0', '128.6', '128.3', '128.2', '127.0', '66.4', '21.1']
    assert any('8 signals' in w and 'coupling' in w for w in run(record)['warnings'])


def test_the_solvent_signal_in_a_carbon_list_is_pointed_out():
    record = copy.deepcopy(BENZYL_ACETATE)
    record['nmr']['13C']['peaks'] = ['171.0', '136.0', '128.6', '128.3', '128.2', '77.2', '66.4', '21.1']
    assert any('77.2' in w and 'CDCl3' in w and 'solvent' in w for w in run(record)['warnings'])


def test_an_unusual_multiplicity_is_flagged():
    record = copy.deepcopy(BENZYL_ACETATE)
    record['nmr']['1H']['text'] = '7.40-7.30 (x, 5H), 5.11 (s, 2H), 2.10 (s, 3H)'
    assert any("'x'" in w and 'multiplicity' in w for w in run(record)['warnings'])


def test_a_found_mass_far_from_the_calculated_one_is_flagged_and_a_missing_one_is_noted():
    off = {**BENZYL_ACETATE, 'found_mz': 173.0700}
    assert any('ppm' in w for w in run(off)['warnings'])
    calc_only = {k: v for k, v in BENZYL_ACETATE.items() if k != 'found_mz'}
    result = run(calc_only)
    assert any('no found' in w.lower() for w in result['warnings'])
    assert result['compounds'][0]['paragraph'].endswith('HRMS (ESI) m/z calcd for C9H10O2Na [M+Na]+ 173.0573.')


def test_missing_instrument_details_are_left_out_not_invented():
    record = {'label': 'x', 'smiles': 'CCO', 'hrms': False, 'nmr': {'1H': {'text': '3.70 (q, J = 7.0 Hz, 2H), 1.25 (t, J = 7.0 Hz, 3H)'}}}
    paragraph = run(record)['compounds'][0]['paragraph']
    assert paragraph == '1H NMR \u03b4 3.70 (q, J = 7.0 Hz, 2H), 1.25 (t, J = 7.0 Hz, 3H).'


def test_other_nuclei_are_listed_after_carbon_without_a_count_check():
    record = {'label': 'x', 'smiles': 'FC(F)(F)c1ccccc1', 'hrms': False,
              'nmr': {'19F': {'frequency': 376, 'solvent': 'CDCl3', 'peaks': ['-62.8']}}}
    result = run(record)
    assert result['compounds'][0]['paragraph'] == '19F NMR (376 MHz, CDCl3) \u03b4 -62.8.'
    assert result['warnings'] == []


def test_the_input_is_never_changed_and_every_record_needs_a_real_structure():
    before = copy.deepcopy(BENZYL_ACETATE)
    run(BENZYL_ACETATE)
    assert BENZYL_ACETATE == before
    with pytest.raises(ValueError):
        characterization_text([{'label': 'x'}])
    with pytest.raises(ValueError, match='Unknown option'):
        run(BENZYL_ACETATE, {'colour': 'red'})
    with pytest.raises(ValueError, match='nuclei|nucleus'):
        run({'label': 'x', 'smiles': 'CCO', 'hrms': False, 'nmr': {'2X': {'peaks': ['1.0']}}})


def test_several_compounds_give_one_line_each_and_files_are_written_once(tmp_path):
    second = {**BENZYL_ACETATE, 'label': '3b'}
    result = characterization_text([BENZYL_ACETATE, second], output_path=str(tmp_path / 'si.txt'))
    assert result['count'] == 2 and result['text'].count('\n') == 2
    assert (tmp_path / 'si.txt').read_text(encoding='utf-8') == result['text']
    with pytest.raises(Exception):
        characterization_text([BENZYL_ACETATE], output_path=str(tmp_path / 'si.txt'))
    characterization_text([BENZYL_ACETATE], output_path=str(tmp_path / 'si.json'))
    assert json.loads((tmp_path / 'si.json').read_text(encoding='utf-8'))['compounds'][0]['label'] == '3a'
    characterization_text([BENZYL_ACETATE], output_path=str(tmp_path / 'si.md'))
    assert (tmp_path / 'si.md').read_text(encoding='utf-8').startswith('**3a**')
