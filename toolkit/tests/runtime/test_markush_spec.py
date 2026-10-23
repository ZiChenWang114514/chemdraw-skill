from __future__ import annotations

import json
from pathlib import Path

import pytest
from rdkit import Chem

from cdxml_toolkit.markush import templates
from cdxml_toolkit.markush.cdxml_writer import write_cdxml
from cdxml_toolkit.markush.compile import (SpecError, build_graph, check_cxsmiles, compile_spec,
                                           enumerate_members, to_cxsmiles)
from cdxml_toolkit.markush.spec import label_runs, plain_label, validate_spec

EXAMPLE = Path(__file__).resolve().parents[2] / 'examples' / 'markush' / 'indole-macrocycle.json'


def _example():
    return json.loads(EXAMPLE.read_text(encoding='utf-8'))


@pytest.mark.parametrize('name', templates.template_names())
def test_every_template_has_one_locant_per_atom(name):
    mol = templates.template_mol(name)
    locs = [a.GetProp('locant') for a in mol.GetAtoms()]
    assert len(locs) == len(set(locs)) == mol.GetNumAtoms()


def test_label_markup():
    assert label_runs('(R^{B})_{q}') == [('(R', 'normal'), ('B', 'sup'), (')', 'normal'), ('q', 'sub')]
    assert plain_label('R^{2}') == 'R2'
    assert plain_label('(R^{A})_{n}') == 'RAn'


def test_worked_example_compiles_to_cxsmiles_with_variable_attachments():
    result = compile_spec(_example())
    cx = result['cxsmiles']
    assert result['checks'] == []
    assert ',m:' in cx and cx.count(':') >= 3
    params = Chem.SmilesParserParams()
    params.sanitize = False
    mol = Chem.MolFromSmiles(cx, params)
    labels = sorted(a.GetProp('atomLabel') for a in mol.GetAtoms() if a.HasProp('atomLabel'))
    assert {'RA', 'RB', 'RC', 'Z', 'Y', 'L1', 'L2', 'G', 'G1', 'G2', 'A', 'C'} <= set(labels)
    assert 'ENDPTS' in result['molblock']


def test_multicenter_group_lists_its_ring_atoms():
    graph = build_graph(_example())
    rb = next(g for g in graph.groups if g['group'] == 'RB')
    assert rb['on'] == ['ind:C4', 'ind:C6', 'ind:C7']
    assert check_cxsmiles(graph, to_cxsmiles(graph)) == []


def test_validator_names_the_valid_locants():
    spec = _example()
    spec['bonds'].append(['ind:C9', 'Z'])
    errors = validate_spec(spec)
    assert any("unknown atom 'ind:C9'" in e and 'C3a' in e for e in errors)
    with pytest.raises(SpecError):
        build_graph(spec)


def test_validator_rejects_atom_with_both_element_and_label():
    spec = _example()
    spec['atoms'][0]['element'] = 'C'
    assert any('exactly one of "element"' in e for e in validate_spec(spec))


def test_enumeration_uses_definition_values():
    out = enumerate_members(_example(), n=3, seed=1)
    assert out['members'] and not out['failures']
    for smi in out['members']:
        assert Chem.MolFromSmiles(smi) is not None
    assert set(out['not_enumerated']) == {'RA', 'RC'}


def test_cdxml_uses_generic_nicknames_and_multi_attachment():
    graph = build_graph(_example())
    xml = write_cdxml(graph)
    assert 'NodeType="MultiAttachment"' in xml
    assert 'GenericNickname="RB"' in xml
    assert 'GraphicType="Oval"' in xml
    assert '<curve' in xml  # drawn-member ring A is an arc


def test_auto_layout_leaves_the_rdkit_depictor_setting_alone():
    from rdkit.Chem import rdDepictor
    from cdxml_toolkit.markush.cdxml_writer import auto_layout
    before = rdDepictor.GetPreferCoordGen()
    auto_layout(build_graph(_example()))
    assert rdDepictor.GetPreferCoordGen() == before
