import pytest
from rdkit import Chem

from cdxml_toolkit import characterization
from cdxml_toolkit.mcp_runtime.report_tools import hrms_line, molecule_report
from cdxml_toolkit.mcp_runtime.tool_registry import build_registry

BENZYL_ACETATE = 'CC(=O)OCc1ccccc1'   # C9H10O2, 150.0681
ASPIRIN = 'CC(=O)Oc1ccccc1C(=O)O'


def mol(smiles):
    return Chem.MolFromSmiles(smiles)


def test_sodium_adduct_matches_the_hand_calculation_with_electron_mass():
    entry = characterization.hrms_entry(mol(BENZYL_ACETATE), '[M+Na]+')
    assert entry['ion_formula'] == 'C9H10O2Na'
    assert entry['calcd_mz'] == pytest.approx(173.0573, abs=5e-5)
    assert entry['line'] == 'HRMS (ESI) m/z calcd for C9H10O2Na [M+Na]+ 173.0573'
    ignoring = characterization.hrms_entry(mol(BENZYL_ACETATE), '[M+Na]+', electron_mass=False)
    assert ignoring['calcd_mz'] == pytest.approx(173.0578, abs=1e-4)


def test_found_value_adds_the_measurement_and_the_error_in_ppm():
    entry = characterization.hrms_entry(mol(BENZYL_ACETATE), '[M+Na]+', found=173.0570)
    assert entry['line'].endswith('173.0573, found 173.0570')
    assert entry['error_ppm'] == pytest.approx(-1.7, abs=0.05)


@pytest.mark.parametrize('adduct, formula, mz', [
    ('[M+H]+', 'C9H11O2', 151.0754),
    ('[M+NH4]+', 'C9H14NO2', 168.1019),
    ('[M+K]+', 'C9H10O2K', 189.0312),
    ('[M-H]-', 'C9H9O2', 149.0608),
    ('[M+Cl]-', 'C9H10O2Cl', 185.0375),
    ('[M+HCOO]-', 'C10H11O4', 195.0663),
])
def test_ion_formulas_and_masses_for_common_adducts(adduct, formula, mz):
    entry = characterization.hrms_entry(mol(BENZYL_ACETATE), adduct)
    assert entry['ion_formula'] == formula
    assert entry['calcd_mz'] == pytest.approx(mz, abs=1e-4)


def test_adduct_masses_agree_with_molecule_report():
    report = molecule_report([{'smiles': ASPIRIN}])['results'][0]['adducts']
    for item in report:
        if item['name'] in ('[M+H]+', '[M+Na]+', '[M-H]-', '[M+NH4]+'):
            assert characterization.hrms_entry(mol(ASPIRIN), item['name'])['calcd_mz'] == pytest.approx(item['mz'], abs=1e-4)


def test_doubly_charged_and_electron_impact_ions():
    two = characterization.hrms_entry(mol('CN(C)CCN(C)C'), '[M+2H]2+')
    assert two['ion_formula'] == 'C6H18N2' and two['calcd_mz'] == pytest.approx(59.0730, abs=1e-4)
    ei = characterization.hrms_entry(mol(BENZYL_ACETATE), 'M+.', ionization='EI')
    assert ei['calcd_mz'] == pytest.approx(150.0675, abs=1e-4) and ei['line'].startswith('HRMS (EI) m/z calcd for C9H10O2 ')


def test_a_cation_is_reported_as_the_intact_ion():
    entry = characterization.hrms_entry(mol('C[N+](C)(C)C'), None)
    assert (entry['adduct'], entry['ion_formula']) == ('[M]+', 'C4H12N')
    assert entry['calcd_mz'] == pytest.approx(74.0964, abs=1e-4)
    with pytest.raises(ValueError, match='charged'):
        characterization.hrms_entry(mol('C[N+](C)(C)C'), '[M+Na]+')


def test_unknown_or_impossible_adducts_are_refused():
    with pytest.raises(ValueError, match='Supported adducts'):
        characterization.hrms_entry(mol(BENZYL_ACETATE), '[M+Zz]+')
    with pytest.raises(ValueError, match='more hydrogen'):
        characterization.hrms_entry(mol('O=C=O'), '[M-H]-')


def test_the_tool_formats_a_line_per_molecule_and_adduct(tmp_path):
    result = hrms_line([{'smiles': BENZYL_ACETATE, 'label': 'benzyl acetate', 'found_mz': {'[M+Na]+': 173.0570}},
                        {'smiles': ASPIRIN, 'label': 'aspirin'}],
                       {'adducts': ['[M+H]+', '[M+Na]+'], 'ionization': 'ESI-TOF'},
                       output_path=str(tmp_path / 'hrms.txt'))
    assert result['ok'] and result['count'] == 2
    first = result['results'][0]
    assert [e['adduct'] for e in first['entries']] == ['[M+H]+', '[M+Na]+']
    assert 'found 173.0570' in first['entries'][1]['line'] and 'found' not in first['entries'][0]['line']
    assert result['results'][1]['entries'][0]['line'] == 'HRMS (ESI-TOF) m/z calcd for C9H9O4 [M+H]+ 181.0495'
    text = (tmp_path / 'hrms.txt').read_text(encoding='utf-8')
    assert 'benzyl acetate' in text and 'HRMS (ESI-TOF) m/z calcd for C9H11O2 [M+H]+ 151.0754' in text
    with pytest.raises(ValueError, match='ionization'):
        hrms_line([{'smiles': ASPIRIN}], {'ionization': 'x' * 50})


def test_default_adduct_follows_the_mode_and_a_large_error_is_flagged():
    positive = hrms_line([{'smiles': ASPIRIN}])['results'][0]['entries'][0]
    negative = hrms_line([{'smiles': ASPIRIN}], {'mode': 'negative'})['results'][0]['entries'][0]
    assert (positive['adduct'], negative['adduct']) == ('[M+H]+', '[M-H]-')
    off = hrms_line([{'smiles': ASPIRIN, 'found_mz': 181.0600}])
    assert any('ppm' in w for w in off['warnings'])


def test_tool_is_registered_in_the_full_profile():
    assert 'hrms_line' in build_registry('full')


def test_a_charged_molecule_report_uses_one_electron_correction():
    adduct = molecule_report([{'smiles': 'C[N+](C)(C)C'}])['results'][0]['adducts'][0]
    assert adduct['name'] == '[M]+' and adduct['mz'] == pytest.approx(74.0964, abs=1e-4)
