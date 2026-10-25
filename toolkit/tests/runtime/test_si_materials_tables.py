import csv
import io
import json

import pytest

from cdxml_toolkit.mcp_runtime import official_overrides as api
from cdxml_toolkit.mcp_runtime.report_tools import si_materials_tables
from cdxml_toolkit.mcp_runtime.tool_registry import build_registry

ACETYLATION = {'reactants': [{'smiles': 'OCc1ccccc1', 'mass_mg': 108.14}, {'smiles': 'CC(=O)Cl', 'equiv': 1.2}],
               'agents': [{'smiles': 'CCN(CC)CC', 'equiv': 1.5}, {'smiles': 'ClCCl'}],
               'products': [{'smiles': 'CC(=O)OCc1ccccc1', 'name': 'benzyl acetate', 'isolated_mg': 120}]}
SECOND = 'OCc1ccccc1.O=C(Cl)c1ccccc1>CCN(CC)CC.ClCCl>O=C(OCc1ccccc1)c1ccccc1'


def two_step_scheme(path):
    api.render_scheme(yaml_text="""layout: linear
structures:
  S1: {smiles: "OCc1ccccc1"}
  S2: {smiles: "CC(=O)Cl"}
  S3: {smiles: "CC(=O)OCc1ccccc1"}
  S4: {smiles: "CCN"}
  S5: {smiles: "CC(=O)NCC"}
steps:
  - substrates: [S1, S2]
    products: [S3]
  - substrates: [S4, S2]
    products: [S5]
""", output_path=str(path))


def test_a_batch_gives_one_table_per_reaction_with_product_line_and_hrms(tmp_path):
    result = si_materials_tables([{'label': '3a', 'reaction': ACETYLATION, 'options': {'title': 'Acetylation'}},
                                  {'label': '3b', 'reaction': SECOND}],
                                 {'scale_mmol': 1.0, 'molarity': 0.1})
    assert result['ok'] and result['count'] == 2
    first, second = result['reactions']
    assert (first['label'], second['label']) == ('3a', '3b')
    by_name = {r['name']: r for r in first['rows']}
    assert by_name['benzyl alcohol']['mmol'] == pytest.approx(1.0, abs=1e-3)       # 108.14 mg fixes the scale
    assert by_name['dichloromethane']['volume_ml'] == pytest.approx(10.0, abs=0.01)  # 0.1 M of 1 mmol
    assert first['product']['hrms'] == 'HRMS (ESI) m/z calcd for C9H11O2 [M+H]+ 151.0754'
    assert first['product']['yield_percent'] == pytest.approx(120 / 150.177 * 100, abs=0.2)
    assert second['product']['formula'] == 'C14H12O2'
    md = result['markdown']
    assert md.index('### 3a') < md.index('### 3b')
    assert '| Material | Role | MW | equiv | mmol | mass (mg) | volume (mL) |' in md
    assert 'benzyl acetate' in md and 'HRMS (ESI) m/z calcd for C9H11O2 [M+H]+ 151.0754' in md
    assert any(w.startswith('3b:') and 'assumed' in w for w in result['warnings'])


def test_each_reaction_has_a_procedure_sentence():
    result = si_materials_tables([{'label': '3a', 'reaction': ACETYLATION}])
    text = result['reactions'][0]['procedure']
    assert text.startswith('To a solution of benzyl alcohol (0.104 mL, 1 mmol, 1 equiv) in dichloromethane (5 mL, 0.2 M) was added')
    assert 'acetyl chloride' in text and 'triethylamine' in text and 'Isolated benzyl acetate: 120 mg' in text


def test_a_drawn_file_expands_to_one_reaction_per_step(tmp_path):
    scheme = tmp_path / 'two.cdxml'
    two_step_scheme(scheme)
    result = si_materials_tables([{'cdxml': str(scheme)}])
    assert result['count'] == 2
    assert [r['label'] for r in result['reactions']] == ['two, step 1', 'two, step 2']
    assert {row['name'] for row in result['reactions'][1]['rows'] if row['role'] != 'solvent'} >= {'C2H7N'}


def test_a_reaction_that_cannot_be_read_is_reported_and_the_rest_continue():
    result = si_materials_tables([{'label': 'bad', 'reaction': 'not>a>reaction'}, {'label': 'ok', 'reaction': SECOND}])
    bad, good = result['reactions']
    assert bad['ok'] is False and bad['error'] and good['ok'] is True
    assert any(w.startswith('bad:') for w in result['warnings']) and result['count'] == 2
    with pytest.raises(ValueError, match='at least one'):
        si_materials_tables([])
    with pytest.raises(ValueError, match='At most'):
        si_materials_tables([SECOND] * 101)


def test_files_in_each_format_and_no_overwrite(tmp_path):
    reactions = [{'label': '3a', 'reaction': ACETYLATION}, {'label': '3b', 'reaction': SECOND}]
    csv_path = tmp_path / 'materials.csv'
    si_materials_tables(reactions, output_path=str(csv_path))
    rows = list(csv.DictReader(io.StringIO(csv_path.read_text(encoding='utf-8'))))
    assert {r['reaction'] for r in rows} == {'3a', '3b'}
    assert {'reaction', 'material', 'role', 'mw', 'equiv', 'mmol', 'mass_mg', 'volume_ml', 'density_g_ml'} <= set(rows[0])
    md_path = tmp_path / 'materials.md'
    si_materials_tables(reactions, output_path=str(md_path))
    assert md_path.read_text(encoding='utf-8').startswith('### 3a')
    html_path = tmp_path / 'materials.html'
    si_materials_tables([{'label': '<b>x</b>', 'reaction': SECOND}], output_path=str(html_path))
    html = html_path.read_text(encoding='utf-8')
    assert '<table' in html and '&lt;b&gt;x&lt;/b&gt;' in html and '<b>x</b>' not in html and 'http' not in html
    json_path = tmp_path / 'materials.json'
    si_materials_tables(reactions, output_path=str(json_path))
    assert json.loads(json_path.read_text(encoding='utf-8'))['reactions'][0]['label'] == '3a'
    with pytest.raises(Exception):
        si_materials_tables(reactions, output_path=str(csv_path))
    with pytest.raises(ValueError, match='output_path'):
        si_materials_tables(reactions, output_path=str(tmp_path / 'm.docx'))


def test_hrms_can_be_turned_off_or_changed():
    plain = si_materials_tables([SECOND], {'hrms': False})['reactions'][0]['product']
    assert 'hrms' not in plain
    sodium = si_materials_tables([SECOND], {'adduct': '[M+Na]+', 'ionization': 'ESI-TOF'})['reactions'][0]['product']
    assert sodium['hrms'].startswith('HRMS (ESI-TOF) m/z calcd for C14H12O2Na [M+Na]+ ')


def test_tool_is_registered():
    assert 'si_materials_tables' in build_registry('full')
