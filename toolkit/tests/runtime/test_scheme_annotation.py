import re
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

from cdxml_toolkit.mcp_runtime import official_overrides as api
from cdxml_toolkit.mcp_runtime.report_tools import reaction_calculator
from cdxml_toolkit.reaction_calculator import annotate, compute

REACTION = {'reactants': [{'smiles': 'OCc1ccccc1', 'mass_mg': 108.14}, {'smiles': 'CC(=O)Cl', 'equiv': 1.2}],
            'agents': [{'smiles': 'CCN(CC)CC', 'equiv': 1.5}, {'smiles': 'ClCCl'}],
            'products': [{'smiles': 'CC(=O)OCc1ccccc1', 'name': 'benzyl acetate', 'isolated_mg': 120}]}


def texts(path):
    root = ET.parse(path).getroot()
    page = root.find('page')
    return {t.get('id'): [s.text for s in t.findall('s')] for t in page.findall('t')}


def fragment_boxes(path):
    page = ET.parse(path).getroot().find('page')
    return [tuple(float(v) for v in f.get('BoundingBox').split()) for f in page.findall('fragment')]


def test_amounts_are_written_under_each_matched_structure(tmp_path):
    out = tmp_path / 'amounts.cdxml'
    result = reaction_calculator(REACTION, options={'scheme_output': str(out)}, output_path=str(tmp_path / 'c.html'))
    assert result['scheme_path'] == str(out) and result['scheme_unplaced'] == []
    assert 'dichloromethane (5.00 mL, 0.20 M)' in out.read_text(encoding='utf-8')
    labels = [' '.join(parts) for parts in texts(out).values()]
    assert any('1.00 mmol' in l and '108 mg' in l and '1.0 equiv' in l for l in labels)       # limiting reagent
    assert any('1.2 equiv' in l and '1.20 mmol' in l for l in labels)                           # acetyl chloride
    assert any('1.5 equiv' in l and 'mL' in l for l in labels)                                  # triethylamine, liquid
    assert any('120 mg' in l and '%' in l for l in labels)                                      # isolated product
    text = out.read_text(encoding='utf-8')
    assert text.startswith('<?xml') and '<!DOCTYPE CDXML' in text and text.count('<scheme') == 1


def test_labels_sit_below_reactants_and_above_agents_without_touching_the_structure(tmp_path):
    out = tmp_path / 'amounts.cdxml'
    reaction_calculator(REACTION, options={'scheme_output': str(out)}, output_path=str(tmp_path / 'c.html'))
    page = ET.parse(out).getroot().find('page')
    boxes = {f.get('id'): [float(v) for v in f.get('BoundingBox').split()] for f in page.findall('fragment')}
    steps = page.find('scheme').find('step')
    above = set(steps.get('ReactionStepObjectsAboveArrow').split())
    added = [t for t in page.findall('t') if len(t.findall('s')) > 0 and any(
        w in ''.join(s.text or '' for s in t.findall('s')) for w in ('mmol', 'mg'))]
    assert len(added) >= 4
    for label in added:
        lx0, ly0, lx1, ly1 = (float(v) for v in label.get('BoundingBox').split())
        for ident, (x0, y0, x1, y1) in boxes.items():
            overlap_x = lx0 < x1 and lx1 > x0
            assert not (overlap_x and ly0 < y1 and ly1 > y0), f'label overlaps fragment {ident}'
    # every label of an agent is above it, every other one below
    for ident in above:
        top = boxes[ident][1]
        assert any(float(t.get('BoundingBox').split()[3]) <= top for t in added)


def test_a_drawn_file_is_annotated_by_structure_and_the_source_is_kept(tmp_path):
    source = tmp_path / 'drawn.cdxml'
    api.render_scheme(yaml_text="""layout: linear
structures:
  S1: {smiles: "OCc1ccccc1"}
  S2: {smiles: "CC(=O)Cl"}
  S3: {smiles: "CC(=O)OCc1ccccc1"}
steps:
  - substrates: [S1, S2]
    products: [S3]
""", output_path=str(source))
    before = source.read_text(encoding='utf-8')
    out = tmp_path / 'amounts.cdxml'
    result = reaction_calculator({'cdxml': str(source)}, options={'scale_mmol': 2, 'scheme_output': str(out)},
                                 output_path=str(tmp_path / 'c.html'))
    assert source.read_text(encoding='utf-8') == before and out.exists()
    labels = [' '.join(parts) for parts in texts(out).values()]
    assert any('2.00 mmol' in l and '216 mg' in l for l in labels)
    assert result['scheme_unplaced'] == []


def test_amounts_start_below_the_compound_number_drawn_under_a_structure(tmp_path):
    source = tmp_path / 'labelled.cdxml'
    api.render_scheme(yaml_text="""layout: linear
structures:
  S1: {smiles: "OCc1ccccc1", label: "1"}
  S2: {smiles: "CC(=O)Cl", label: "2"}
  S3: {smiles: "CC(=O)OCc1ccccc1", label: "3"}
steps:
  - substrates: [S1, S2]
    products: [S3]
""", output_path=str(source))
    out = tmp_path / 'amounts.cdxml'
    reaction_calculator({'cdxml': str(source)}, options={'scheme_output': str(out)}, output_path=str(tmp_path / 'c.html'))
    page = ET.parse(source).getroot().find('page')
    numbers = [tuple(float(v) for v in t.get('BoundingBox').split()) for t in page.findall('t')
               if [s.text for s in t.findall('s')] in (['1'], ['2'], ['3'])]
    assert len(numbers) == 3
    added = [t for t in ET.parse(out).getroot().find('page').findall('t') if t.get('id') not in {x.get('id') for x in page.findall('t')}]
    assert len(added) >= 2
    for note in added:
        box = tuple(float(v) for v in note.get('BoundingBox').split())
        for number in numbers:
            overlap_x = box[0] < number[2] and number[0] < box[2]
            overlap_y = box[1] < number[3] and number[1] < box[3]
            assert not (overlap_x and overlap_y), 'an amount block sits on top of a compound number'


def test_an_existing_output_is_never_replaced(tmp_path):
    out = tmp_path / 'amounts.cdxml'
    out.write_text('keep', encoding='utf-8')
    with pytest.raises(Exception):
        reaction_calculator(REACTION, options={'scheme_output': str(out)}, output_path=str(tmp_path / 'c.html'))
    assert out.read_text(encoding='utf-8') == 'keep'


def test_choice_of_quantities_and_ids_stay_unique(tmp_path):
    source = tmp_path / 'amounts.cdxml'
    reaction_calculator(REACTION, options={'scheme_output': str(source), 'scheme_show': ['equiv']},
                        output_path=str(tmp_path / 'c.html'))
    text = source.read_text(encoding='utf-8')
    assert 'mmol' not in text and ' mg' not in text.replace('mg"', '') and '1.2 equiv' in text
    ids = re.findall(r'<(?:fragment|t|arrow|step|scheme|page)\b[^>]*?\bid="(\d+)"', text)
    assert len(ids) == len(set(ids))
    with pytest.raises(ValueError, match='scheme_show'):
        reaction_calculator(REACTION, options={'scheme_output': str(tmp_path / 'x.cdxml'), 'scheme_show': ['moles']},
                            output_path=str(tmp_path / 'd.html'))
