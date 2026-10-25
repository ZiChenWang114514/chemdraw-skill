import json

import pytest
from rdkit import Chem

from cdxml_toolkit.mcp_runtime import official_overrides as api
from cdxml_toolkit.mcp_runtime.report_tools import map_reaction_atoms
from cdxml_toolkit.mcp_runtime.tool_registry import build_registry


def maps(smiles_side):
    """{map number: element} of one side of a mapped reaction SMILES."""
    out = {}
    for part in filter(None, smiles_side.split('.')):
        for atom in Chem.MolFromSmiles(part).GetAtoms():
            if atom.GetAtomMapNum():
                assert atom.GetAtomMapNum() not in out, 'a map number is used twice'
                out[atom.GetAtomMapNum()] = atom.GetSymbol()
    return out


def sides(result):
    left, _, right = result['mapped_reaction'].split('>')
    return maps(left), maps(right)


def kinds(result):
    return sorted((c['type'], c['elements']) for c in result['bond_changes'])


def test_amide_formation_maps_every_product_atom_and_names_the_leaving_group():
    result = map_reaction_atoms('CC(=O)Cl.CCN>>CC(=O)NCC')
    assert result['ok'] and result['status'] == 'complete' and result['ambiguous'] == []
    left, right = sides(result)
    assert set(right) <= set(left) and all(left[n] == right[n] for n in right) and len(right) == 6
    assert kinds(result) == [('broken', 'C-Cl'), ('formed', 'C-N')]
    assert result['unmapped_reactant_atoms'] == [{'species': 'CC(=O)Cl', 'atoms': ['Cl'], 'formula': 'Cl'}]
    assert result['product_coverage'] == [{'species': 'CC(=O)NCC', 'mapped': 6, 'atoms': 6}]


def test_suzuki_coupling_is_not_ambiguous_because_the_rings_are_equivalent():
    result = map_reaction_atoms('Brc1ccccc1.OB(O)c1ccccc1>>c1ccc(-c2ccccc2)cc1')
    assert result['status'] == 'complete' and result['ambiguous'] == []
    assert kinds(result) == [('broken', 'B-C'), ('broken', 'Br-C'), ('formed', 'C-C')]
    assert sorted(a for u in result['unmapped_reactant_atoms'] for a in u['atoms']) == ['B', 'Br', 'O', 'O']


def test_cycloaddition_changes_bond_orders_without_breaking_bonds():
    result = map_reaction_atoms('C=CC=C.C=C>>C1=CCCCC1')
    assert result['status'] == 'complete'
    assert [k for k in kinds(result) if k[0] == 'formed'] == [('formed', 'C-C'), ('formed', 'C-C')]
    assert {c['type'] for c in result['bond_changes']} <= {'formed', 'order_changed'}


def test_esterification_leaves_the_oxygen_that_cannot_be_decided_unmapped():
    result = map_reaction_atoms('CC(=O)O.OCC>>CC(=O)OCC')
    assert result['status'] == 'ambiguous'
    group = result['ambiguous'][0]
    assert group['product_atom'] == 'O' and len(group['candidates']) == 2
    assert {c['species'] for c in group['candidates']} == {'CC(=O)O', 'OCC'}
    _, right = sides(result)
    assert len(right) == 5 and result['product_coverage'] == [{'species': 'CC(=O)OCC', 'mapped': 5, 'atoms': 6}]
    forced = map_reaction_atoms('CC(=O)O.OCC>>CC(=O)OCC', {'resolve_ambiguity': True})
    assert forced['status'] == 'complete' and forced['ambiguous'] == [] and len(sides(forced)[1]) == 6
    assert any('resolve_ambiguity' in w for w in forced['warnings'])


def test_the_same_input_always_gives_the_same_mapping():
    first = map_reaction_atoms('CC(=O)O.OCC>>CC(=O)OCC', {'resolve_ambiguity': True})['mapped_reaction']
    second = map_reaction_atoms('CC(=O)O.OCC>>CC(=O)OCC', {'resolve_ambiguity': True})['mapped_reaction']
    assert first == second


def test_product_atoms_without_a_source_are_reported_and_agents_can_supply_them():
    result = map_reaction_atoms('CCO>CC(=O)Cl>CCOC(C)=O')
    assert result['status'] == 'incomplete'
    assert any('no source' in w for w in result['warnings'])
    with_agents = map_reaction_atoms('CCO>CC(=O)Cl>CCOC(C)=O', {'include_agents': True})
    assert with_agents['status'] == 'complete'
    assert with_agents['product_coverage'] == [{'species': 'CCOC(C)=O', 'mapped': 6, 'atoms': 6}]
    assert result['product_coverage'] == [{'species': 'CCOC(C)=O', 'mapped': 3, 'atoms': 6}]


def test_records_and_drawn_schemes_are_accepted(tmp_path):
    records = {'reactants': [{'smiles': 'CC(=O)Cl'}, {'smiles': 'CCN'}], 'products': [{'smiles': 'CC(=O)NCC'}]}
    assert map_reaction_atoms(records)['status'] == 'complete'
    scheme = tmp_path / 's.cdxml'
    api.render_scheme(yaml_text="""layout: linear
structures:
  S1: {smiles: "CC(=O)Cl"}
  S2: {smiles: "CCN"}
  S3: {smiles: "CC(=O)NCC"}
steps:
  - substrates: [S1, S2]
    products: [S3]
""", output_path=str(scheme))
    assert map_reaction_atoms({'cdxml': str(scheme)})['status'] == 'complete'


def test_files_for_the_mapping_and_its_picture(tmp_path):
    out = map_reaction_atoms('CC(=O)Cl.CCN>>CC(=O)NCC', output_path=str(tmp_path / 'map.json'))
    assert json.loads((tmp_path / 'map.json').read_text(encoding='utf-8'))['status'] == 'complete'
    assert out['output_path'].endswith('map.json')
    map_reaction_atoms('CC(=O)Cl.CCN>>CC(=O)NCC', output_path=str(tmp_path / 'map.smi'))
    assert (tmp_path / 'map.smi').read_text(encoding='utf-8').strip() == out['mapped_reaction']
    map_reaction_atoms('CC(=O)Cl.CCN>>CC(=O)NCC', output_path=str(tmp_path / 'map.svg'))
    assert (tmp_path / 'map.svg').read_text(encoding='utf-8').lstrip().startswith(('<?xml', '<svg'))
    with pytest.raises(Exception):
        map_reaction_atoms('CC(=O)Cl.CCN>>CC(=O)NCC', output_path=str(tmp_path / 'map.json'))
    with pytest.raises(ValueError, match='output_path'):
        map_reaction_atoms('CC(=O)Cl.CCN>>CC(=O)NCC', output_path=str(tmp_path / 'map.txt'))


def test_refusals():
    with pytest.raises(ValueError, match='generic'):
        map_reaction_atoms({'reactants': [{'smiles': 'C[*]'}], 'products': [{'smiles': 'CC'}]})
    with pytest.raises(ValueError, match='Unknown option'):
        map_reaction_atoms('CC>>CC', {'speed': 1})
    big = 'C' * 130
    with pytest.raises(ValueError, match='at most'):
        map_reaction_atoms(f'{big}>>{big}')


def test_tool_is_registered():
    assert 'map_reaction_atoms' in build_registry('full')
