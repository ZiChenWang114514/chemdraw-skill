from __future__ import annotations

import sys

import pytest
from rdkit import Chem

from cdxml_toolkit.mcp_runtime import official_overrides as api
from cdxml_toolkit.mcp_runtime import report_tools
from cdxml_toolkit.mcp_runtime.report_tools import structure_to_name
from cdxml_toolkit.mcp_runtime.tool_registry import build_registry

ASPIRIN = 'CC(=O)Oc1ccccc1C(=O)O'
ALANINE = 'C[C@H](N)C(=O)O'


class FakeBridge:
    """Stands in for ChemScript: names come from a table, name parsing from another."""

    def __init__(self, names, parse=None, fail_on=()):
        canonical = lambda smiles: Chem.MolToSmiles(Chem.MolFromSmiles(smiles))
        self.names = {canonical(key): value for key, value in names.items()}
        self.parse = parse if parse is not None else {}
        self.fail_on = {canonical(key) for key in fail_on}
        self.closed = False

    def get_info(self, source):
        if source in self.fail_on:
            raise RuntimeError('ChemScript could not name this structure')
        mol = Chem.MolFromSmiles(source)
        return {'ok': True, 'name': self.names[source], 'formula': 'X', 'smiles': source,
                'inchi': Chem.MolToInchi(mol)}

    def name_to_cdxml(self, name, output=None):
        smiles = self.parse.get(name)
        if smiles is None:
            raise RuntimeError(f'Name resolution failed: {name}')
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / 'name.cdxml'
            api.draw_molecule({'smiles': smiles}, str(target))
            return target.read_text(encoding='utf-8')

    def close(self):
        self.closed = True


@pytest.fixture
def fake(monkeypatch):
    def install(bridge):
        monkeypatch.setattr(report_tools, '_bridge_factory', lambda: bridge)
        return bridge
    return install


def test_name_is_reported_with_a_passing_round_trip(fake):
    bridge = fake(FakeBridge({ASPIRIN: '2-acetoxybenzoic acid'}, {'2-acetoxybenzoic acid': ASPIRIN}))
    result = structure_to_name([{'smiles': ASPIRIN, 'label': 'aspirin'}])
    row = result['results'][0]
    assert result['ok'] and result['operation'] == 'structure_to_name'
    assert (row['label'], row['name']) == ('aspirin', '2-acetoxybenzoic acid')
    assert row['roundtrip']['status'] == 'same'
    assert row['roundtrip']['inchikey_input'] == row['roundtrip']['inchikey_from_name']
    assert 'BSYNRYMUTXBXSQ' in row['roundtrip']['inchikey_input']
    assert bridge.closed


def test_a_name_that_parses_to_another_structure_is_flagged(fake):
    fake(FakeBridge({ASPIRIN: 'wrong name'}, {'wrong name': 'CC(=O)O'}))
    result = structure_to_name([{'smiles': ASPIRIN}])
    row = result['results'][0]
    assert row['roundtrip']['status'] == 'different'
    assert any('does not parse back' in w for w in result['warnings'])


def test_lost_stereo_is_distinguished_from_a_different_structure(fake):
    fake(FakeBridge({ALANINE: 'alanine'}, {'alanine': 'CC(N)C(=O)O'}))
    row = structure_to_name([{'smiles': ALANINE}])['results'][0]
    assert row['roundtrip']['status'] == 'same_connectivity'
    assert 'stereo' in row['roundtrip']['note']


def test_an_unparseable_name_and_verify_false(fake):
    fake(FakeBridge({ASPIRIN: 'unparseable'}))
    assert structure_to_name([{'smiles': ASPIRIN}])['results'][0]['roundtrip']['status'] == 'unparseable'
    skipped = structure_to_name([{'smiles': ASPIRIN}], options={'verify': False})['results'][0]
    assert skipped['name'] == 'unparseable' and skipped['roundtrip']['status'] == 'skipped'


def test_salts_are_compared_component_by_component(fake):
    salt = '[Na+].CC(=O)[O-]'
    fake(FakeBridge({salt: 'sodium acetate'}, {'sodium acetate': salt}))
    assert structure_to_name([{'smiles': salt}])['results'][0]['roundtrip']['status'] == 'same'


def test_one_failing_structure_does_not_hide_the_others(fake):
    fake(FakeBridge({ASPIRIN: '2-acetoxybenzoic acid'}, {'2-acetoxybenzoic acid': ASPIRIN}, fail_on={'CCO'}))
    result = structure_to_name([{'smiles': 'CCO', 'label': 'ethanol'}, {'smiles': ASPIRIN}])
    failed, ok = result['results']
    assert failed['name'] is None and 'could not name' in failed['error']
    assert ok['name'] == '2-acetoxybenzoic acid'
    assert any('ethanol' in w for w in result['warnings'])


def test_each_structure_of_a_cdxml_file_is_named(fake, tmp_path):
    scheme = tmp_path / 'ester.cdxml'
    api.render_scheme(yaml_text=('layout: linear\nstructures:\n  A: {smiles: "CCO"}\n  P: {smiles: "CC(=O)OCC"}\n'
                                 'steps:\n  - substrates: [A]\n    products: [P]\n'), output_path=str(scheme))
    fake(FakeBridge({'CCO': 'ethanol', 'CCOC(C)=O': 'ethyl acetate'},
                    {'ethanol': 'CCO', 'ethyl acetate': 'CCOC(C)=O'}))
    result = structure_to_name([{'file': str(scheme), 'all_fragments': True}])
    assert [r['name'] for r in result['results']] == ['ethanol', 'ethyl acetate']
    assert all(r['source']['fragment_id'] for r in result['results'])


def test_enhanced_stereo_and_generic_atoms_are_called_out(fake):
    fake(FakeBridge({'CC[C@H](F)[C@H](C)O': 'x'}, {'x': 'CC[C@H](F)[C@H](C)O'}))
    result = structure_to_name([{'smiles': 'CC[C@H](F)[C@H](C)O |&1:2,4|', 'label': 'mixture'}])
    assert any('stereo group' in w for w in result['warnings'])
    with pytest.raises(ValueError, match='generic'):
        structure_to_name([{'smiles': 'C[*]'}])
    with pytest.raises(ValueError):
        structure_to_name([])
    with pytest.raises(ValueError, match='Unknown options'):
        structure_to_name([{'smiles': ASPIRIN}], options={'html': True})


def test_output_file_and_registration(fake, tmp_path):
    fake(FakeBridge({ASPIRIN: '2-acetoxybenzoic acid'}, {'2-acetoxybenzoic acid': ASPIRIN}))
    out = tmp_path / 'names.csv'
    structure_to_name([{'smiles': ASPIRIN, 'label': 'aspirin'}], output_path=str(out))
    assert 'aspirin' in out.read_text(encoding='utf-8') and '2-acetoxybenzoic acid' in out.read_text(encoding='utf-8')
    with pytest.raises(Exception):
        structure_to_name([{'smiles': ASPIRIN}], output_path=str(out))
    assert 'structure_to_name' in build_registry('chemscript')
    assert 'structure_to_name' not in build_registry('core')
    assert 'structure_to_name' in build_registry()


def test_no_chemscript_gives_an_actionable_error(monkeypatch):
    def unavailable():
        raise RuntimeError('Could not find Python for ChemScript.')
    monkeypatch.setattr(report_tools, '_bridge_factory', unavailable)
    with pytest.raises(RuntimeError, match='ChemScript'):
        structure_to_name([{'smiles': ASPIRIN}])


@pytest.mark.skipif(sys.platform != 'win32', reason='live ChemScript check runs on Windows only')
def test_live_chemscript_names_and_round_trips():
    try:
        from cdxml_toolkit.mcp_runtime.chemistry_compare import _bridge_factory
        _bridge_factory().close()
    except Exception as exc:  # no ChemScript on this host
        pytest.skip(f'ChemScript unavailable: {exc}')
    result = structure_to_name([{'smiles': ASPIRIN}, {'smiles': ALANINE}, {'smiles': 'C/C=C/C(=O)O'}])
    names = [r['name'] for r in result['results']]
    assert names == ['2-acetoxybenzoic acid', 'L-alanine', '(E)-but-2-enoic acid']
    assert [r['roundtrip']['status'] for r in result['results']] == ['same', 'same', 'same']
