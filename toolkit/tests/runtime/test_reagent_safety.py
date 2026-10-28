from rdkit import Chem

from cdxml_toolkit.mcp_runtime.report_tools import si_materials_tables
from cdxml_toolkit.reaction_calculator import hazards, library

ACETYLATION = 'OCc1ccccc1.CC(=O)Cl>CCN(CC)CC.ClCCl>CC(=O)OCc1ccccc1'
FLAMMABLE = {'H220', 'H222', 'H224', 'H225', 'H226', 'H228', 'H242', 'H260'}
TOXIC = {'H300', 'H301', 'H310', 'H311', 'H330', 'H331'}
HEALTH = {'H304', 'H340', 'H350', 'H351', 'H360D', 'H361d', 'H361f', 'H370', 'H372', 'H373'}


def test_a_listed_reagent_has_codes_pictograms_and_physical_data():
    thf = hazards.lookup('C1CCOC1')
    assert thf['signal'] == 'Danger' and thf['bp_c'] == 66 and thf['flash_c'] == -14
    assert 'GHS02' in thf['ghs'] and 'H225' in thf['h'] and 'peroxide' in thf['note'].lower()
    assert hazards.lookup('O1CCCC1') == thf  # any SMILES spelling of the same structure


def test_unknown_and_unreadable_structures_are_not_listed():
    assert hazards.lookup('CC(C)(C)c1ccc(cc1)C(C)(C)C') is None
    assert hazards.lookup('not a smiles') is None


def test_water_and_dmso_are_listed_without_a_classification():
    for smiles in ('O', 'CS(C)=O'):
        entry = hazards.lookup(smiles)
        assert entry is not None and entry['h'] == [] and entry['signal'] is None and entry['ghs'] == []


def test_every_common_solvent_of_the_library_is_covered():
    missing = [e['name'] for e in library.entries() if e['role'] == 'solvent' and hazards.lookup(e['smiles']) is None]
    assert missing == []


def test_the_table_is_internally_consistent():
    assert len(hazards.entries()) >= 40
    for entry in hazards.entries():
        assert Chem.MolFromSmiles(entry['smiles']) is not None, entry['smiles']
        codes = set(entry['h'])
        assert len(codes) == len(entry['h']), entry['name']
        for code in codes:
            assert hazards.H_TEXT.get(code), f"{entry['name']}: no text for {code}"
        for code in entry['ghs']:
            assert code in hazards.GHS_NAME, code
        if codes & FLAMMABLE - {'H242'}:
            assert 'GHS02' in entry['ghs'], entry['name']
        if codes & TOXIC:
            assert 'GHS06' in entry['ghs'], entry['name']
        if codes & {'H314', 'H318'}:
            assert 'GHS05' in entry['ghs'], entry['name']
        if codes & HEALTH:
            assert 'GHS08' in entry['ghs'], entry['name']
        if codes & {'H400', 'H410', 'H411'}:
            assert 'GHS09' in entry['ghs'], entry['name']
        if entry['signal'] is None:
            assert not codes, entry['name']
        assert entry['signal'] in (None, 'Danger', 'Warning')
        if codes & {'H224', 'H225', 'H300', 'H301', 'H310', 'H311', 'H330', 'H331', 'H314', 'H318', 'H350', 'H340'}:
            assert entry['signal'] == 'Danger', entry['name']


def test_summary_is_one_line_with_the_numbers_a_chemist_checks_first():
    line = hazards.summary(hazards.lookup('C1CCOC1'))
    assert line.startswith('Danger; GHS02 GHS07 GHS08; H225') and 'bp 66 °C' in line and 'flash point -14 °C' in line
    assert 'peroxide' in line
    assert hazards.summary(hazards.lookup('O')) == 'no GHS classification; bp 100 °C'


def test_materials_tables_list_safety_only_when_asked():
    plain = si_materials_tables([ACETYLATION])
    assert 'safety' not in plain['reactions'][0] and 'Safety' not in plain['markdown']
    result = si_materials_tables([ACETYLATION], {'reagent_safety': True})
    safety = {item['name']: item for item in result['reactions'][0]['safety']}
    assert {'benzyl alcohol', 'acetyl chloride', 'triethylamine', 'dichloromethane'} <= set(safety)
    assert all(item['role'] != 'product' for item in safety.values())
    assert safety['acetyl chloride']['signal'] == 'Danger' and 'H314' in safety['acetyl chloride']['h']
    assert safety['acetyl chloride']['listed'] is True
    assert 'Safety reminders' in result['markdown'] and 'supplier SDS' in result['markdown']
    assert 'acetyl chloride' in result['markdown'].split('Safety reminders')[1]


def test_a_species_that_is_not_in_the_table_says_so_instead_of_guessing():
    odd = 'CC(C)(C)c1ccc(cc1)C(C)(C)C.CC(=O)Cl>>CC(=O)c1ccc(cc1C(C)(C)C)C(C)(C)C'
    result = si_materials_tables([odd], {'reagent_safety': True})
    items = result['reactions'][0]['safety']
    unlisted = [item for item in items if not item['listed']]
    assert unlisted and all(set(item) == {'id', 'name', 'role', 'listed'} for item in unlisted)
    assert 'not listed' in result['markdown'] and 'check the supplier SDS' in result['markdown']


def test_materials_csv_and_html_carry_the_safety_summary(tmp_path):
    si_materials_tables([ACETYLATION], {'reagent_safety': True}, output_path=str(tmp_path / 'm.csv'))
    csv_text = (tmp_path / 'm.csv').read_text(encoding='utf-8')
    header, *rows = csv_text.splitlines()
    assert 'hazards' in header.split(',')
    assert any('H314' in row for row in rows)
    si_materials_tables([ACETYLATION], {'reagent_safety': True}, output_path=str(tmp_path / 'm.html'))
    assert 'Safety reminders' in (tmp_path / 'm.html').read_text(encoding='utf-8')


def test_a_misspelled_safety_option_is_reported_not_ignored():
    result = si_materials_tables([ACETYLATION], {'reagent_safty': True})
    assert result['reactions'][0]['ok'] is False
    assert 'reagent_safty' in result['reactions'][0]['error']
