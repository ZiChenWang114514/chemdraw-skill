import json

import pytest
from rdkit import Chem

from cdxml_toolkit import atom_mapping, mapping_backends
from cdxml_toolkit.mcp_runtime.report_tools import map_reaction_atoms, si_materials_tables

ESTER = 'CC(=O)O.OCC>>CC(=O)OCC'
AMIDE = 'CC(=O)Cl.CCN>>CC(=O)NCC'
MAPPED = {
    'OCC': '[OH:5][CH2:6][CH3:7].[CH3:1][C:2](=[O:3])[OH:4]>>[CH3:7][CH2:6][O:5][C:2](=[O:3])[CH3:1]',
    'Cl': '[CH3:1][C:2](=[O:3])[Cl:4].[CH3:5][CH2:6][NH2:7]>>[CH3:1][C:2](=[O:3])[NH:7][CH2:6][CH3:5]',
}


def answer(name, text):
    item = {'mapped_rxn': MAPPED['Cl' if 'Cl' in text else 'OCC']}
    item.update({'confidence': 0.97} if name == 'rxnmapper' else {'confident': True})
    return item


@pytest.fixture
def fake(monkeypatch):
    """Both learned backends installed; ``calls`` records every backend call with the reactions it carried."""
    calls = []

    def run(name, reactions, timeout=0):
        calls.append((name, list(reactions)))
        return [answer(name, text) for text in reactions]

    monkeypatch.setattr(mapping_backends, 'available', lambda: {'rxnmapper': True, 'localmapper': True})
    monkeypatch.setattr(mapping_backends, 'run', run)
    return calls


def test_many_reactions_reach_the_learned_mapper_in_one_call(fake):
    result = map_reaction_atoms([ESTER, AMIDE])
    assert result['ok'] and result['count'] == 2
    assert len(fake) == 1 and fake[0][0] == 'localmapper' and len(fake[0][1]) == 2
    first, second = result['reactions']
    assert first['method'] == second['method'] == 'localmapper'
    assert first['status'] == second['status'] == 'complete'
    assert sorted(c['elements'] for c in second['bond_changes']) == ['C-Cl', 'C-N']
    assert Chem.MolFromSmiles(second['mapped_reaction'].split('>')[-1]).GetNumAtoms() == 6


def test_labels_and_one_record_per_cdxml_step_are_kept(fake):
    result = map_reaction_atoms([{'label': '3a', 'reaction': ESTER}, {'label': '3b', 'reaction': AMIDE}])
    assert [r['label'] for r in result['reactions']] == ['3a', '3b'] and len(fake) == 1


def test_a_reaction_the_mapper_fails_on_falls_back_alone(fake, monkeypatch):
    def run(name, reactions, timeout=0):
        fake.append((name, list(reactions)))
        if name == 'localmapper':
            return [{'error': 'ValueError: too long'}, answer(name, reactions[1])]
        return [answer(name, text) for text in reactions]
    monkeypatch.setattr(mapping_backends, 'run', run)
    result = map_reaction_atoms([ESTER, AMIDE])
    first, second = result['reactions']
    assert first['method'] == 'rxnmapper'
    assert any('too long' in w for w in first['warnings'])
    assert second['method'] == 'localmapper'
    assert fake[0][0] == 'localmapper' and len(fake[0][1]) == 2
    assert all(len(reactions) == 1 for name, reactions in fake[1:])  # only the failed one is retried


def test_explicit_method_failures_are_reported_per_reaction(fake, monkeypatch):
    monkeypatch.setattr(mapping_backends, 'run', lambda name, reactions, timeout=0: [
        {'error': 'ValueError: too long'}, answer(name, reactions[1])])
    result = map_reaction_atoms([ESTER, AMIDE], {'method': 'localmapper'})
    first, second = result['reactions']
    assert first['ok'] is False and 'too long' in first['error']
    assert second['ok'] is True and second['method'] == 'localmapper'
    assert any('too long' in w for w in result['warnings'])


def test_a_backend_that_cannot_start_sends_every_reaction_to_the_next_method(fake, monkeypatch):
    def broken(name, reactions, timeout=0):
        fake.append((name, list(reactions)))
        raise mapping_backends.BackendError(f'{name} failed to start: boom')
    monkeypatch.setattr(mapping_backends, 'run', broken)
    result = map_reaction_atoms([ESTER, AMIDE])
    assert [r['method'] for r in result['reactions']] == ['mcs', 'mcs']
    assert [name for name, _ in fake] == ['localmapper', 'rxnmapper']  # one attempt per backend, not per reaction


def test_compare_costs_one_call_per_installed_backend(fake):
    result = map_reaction_atoms([ESTER, AMIDE], {'compare': True})
    assert [name for name, _ in fake] == ['localmapper', 'rxnmapper']
    assert all(len(reactions) == 2 for _, reactions in fake)
    assert all('comparison' in r for r in result['reactions'])


def test_one_oversized_reaction_does_not_stop_the_others(fake):
    huge = '.'.join(['CCCCCCCCCCCCCCCCCCCC'] * 7) + '>>' + '.'.join(['CCCCCCCCCCCCCCCCCCCC'] * 7)
    result = map_reaction_atoms([huge, AMIDE])
    first, second = result['reactions']
    assert first['ok'] is False and '120' in first['error'] and second['ok'] is True
    assert len(fake) == 1 and len(fake[0][1]) == 1


def test_batch_outputs_are_json_or_smiles_lines_and_never_a_picture(fake, tmp_path):
    out = tmp_path / 'maps.smi'
    result = map_reaction_atoms([ESTER, AMIDE], output_path=str(out))
    lines = out.read_text(encoding='utf-8').splitlines()
    assert len(lines) == 2 and lines[0] == result['reactions'][0]['mapped_reaction']
    data = tmp_path / 'maps.json'
    map_reaction_atoms([ESTER, AMIDE], output_path=str(data))
    assert len(json.loads(data.read_text(encoding='utf-8'))['reactions']) == 2
    with pytest.raises(ValueError, match='one reaction at a time'):
        map_reaction_atoms([ESTER, AMIDE], output_path=str(tmp_path / 'maps.svg'))


def test_a_single_reaction_keeps_its_old_shape(fake):
    result = map_reaction_atoms(ESTER)
    assert 'reactions' not in result and result['method'] == 'localmapper' and 'mapped_reaction' in result


def test_materials_tables_can_add_the_bond_changes_with_one_backend_call(fake):
    result = si_materials_tables([{'label': '3a', 'reaction': ESTER}, {'label': '3b', 'reaction': AMIDE}],
                                 {'map_atoms': True})
    assert len(fake) == 1 and len(fake[0][1]) == 2
    first, second = result['reactions']
    assert first['mapping']['method'] == 'localmapper' and second['mapping']['status'] == 'complete'
    assert 'formed C-N' in second['mapping']['summary'] and 'broken C-Cl' in second['mapping']['summary']
    assert 'Bond changes (LocalMapper): ' in result['markdown']


def test_materials_tables_without_the_option_never_start_a_mapper(fake):
    result = si_materials_tables([ESTER, AMIDE])
    assert fake == [] and all('mapping' not in r for r in result['reactions'])


def test_materials_tables_keep_going_when_mapping_is_unavailable(monkeypatch):
    monkeypatch.setattr(mapping_backends, 'available', lambda: {'rxnmapper': False, 'localmapper': False})
    result = si_materials_tables([AMIDE], {'map_atoms': True, 'map_method': 'localmapper'})
    entry = result['reactions'][0]
    assert entry['ok'] is True and 'mapping' not in entry
    assert any('localmapper' in w and 'install-mappers' in w for w in result['warnings'])


def test_map_atoms_many_returns_one_entry_per_reaction(fake):
    def species(text):
        return [(s, Chem.MolFromSmiles(s)) for s in text.split('.')]
    pairs = [(species(a.split('>>')[0]), species(a.split('>>')[1])) for a in (ESTER, AMIDE)]
    out = atom_mapping.map_atoms_many(pairs, method='localmapper')
    assert len(out) == 2 and all(o['method'] == 'localmapper' for o in out) and len(fake) == 1
    one = atom_mapping.map_atoms(*pairs[0], method='localmapper')
    assert one['map'] == out[0]['map']
    assert atom_mapping.map_atoms_many([], method='mcs') == []
