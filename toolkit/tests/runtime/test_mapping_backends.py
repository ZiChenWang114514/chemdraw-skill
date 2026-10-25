import json
import sys
import textwrap

import pytest
from rdkit import Chem

from cdxml_toolkit import atom_mapping, mapping_backends
from cdxml_toolkit.mcp_runtime.report_tools import map_reaction_atoms

ESTER = 'CC(=O)O.OCC>>CC(=O)OCC'
# Fragments in the opposite order and with their own atom order, as a learned mapper may return them.
ESTER_MAPPED = '[OH:5][CH2:6][CH3:7].[CH3:1][C:2](=[O:3])[OH:4]>>[CH3:7][CH2:6][O:5][C:2](=[O:3])[CH3:1]'


def ester_sources(result):
    """Species of the reactant atom that became the ester oxygen (the single-bonded O of the product)."""
    return [m['reactant']['species'] for m in result['map'] if m['element'] == 'O' and m['product']['atom_index'] == 3]


@pytest.fixture
def fake(monkeypatch):
    """Pretend both learned backends are installed; ``calls`` records the reactions they were sent."""
    calls = []

    def run(name, reactions, timeout=0):
        calls.append((name, list(reactions)))
        item = {'mapped_rxn': ESTER_MAPPED}
        item.update({'confidence': 0.97} if name == 'rxnmapper' else {'confident': True})
        return [item]

    monkeypatch.setattr(mapping_backends, 'available', lambda: {'rxnmapper': True, 'localmapper': True})
    monkeypatch.setattr(mapping_backends, 'run', run)
    return calls


def test_without_backends_auto_uses_the_builtin_method(monkeypatch):
    monkeypatch.setattr(mapping_backends, 'available', lambda: {'rxnmapper': False, 'localmapper': False})
    result = map_reaction_atoms(ESTER)
    assert result['method'] == 'mcs' and result['available_methods'] == ['mcs']
    assert result['status'] == 'ambiguous'  # the built-in method refuses to guess the ester oxygen


def test_explicit_learned_method_that_is_not_installed_names_the_install_command(monkeypatch):
    monkeypatch.setattr(mapping_backends, 'available', lambda: {'rxnmapper': False, 'localmapper': False})
    with pytest.raises(ValueError, match='install-mappers localmapper'):
        map_reaction_atoms(ESTER, {'method': 'localmapper'})
    with pytest.raises(ValueError, match='Unknown method'):
        map_reaction_atoms(ESTER, {'method': 'magic'})


def test_auto_prefers_localmapper_and_translates_its_map_onto_our_atoms(fake):
    result = map_reaction_atoms(ESTER)
    assert result['method'] == 'localmapper' and result['confident'] is True
    assert result['available_methods'] == ['mcs', 'localmapper', 'rxnmapper']
    assert result['status'] == 'complete' and result['ambiguous'] == []
    assert fake == [('localmapper', ['CC(=O)O.CCO>>CCOC(C)=O'])]
    assert ester_sources(result) == ['OCC']  # the alcohol oxygen, which the built-in method leaves open
    assert sorted((c['type'], c['elements']) for c in result['bond_changes']) == [('broken', 'C-O'), ('formed', 'C-O')]
    right = result['mapped_reaction'].split('>')[-1]
    assert Chem.MolFromSmiles(right).GetNumAtoms() == 6


def test_explicit_rxnmapper_reports_confidence_and_warns_when_low(fake, monkeypatch):
    result = map_reaction_atoms(ESTER, {'method': 'rxnmapper'})
    assert result['method'] == 'rxnmapper' and result['confidence'] == 0.97 and result['warnings'] == []
    monkeypatch.setattr(mapping_backends, 'run', lambda name, reactions, timeout=0: [
        {'mapped_rxn': ESTER_MAPPED, 'confidence': 0.41}])
    result = map_reaction_atoms(ESTER, {'method': 'rxnmapper'})
    assert any('confidence' in w and '0.41' in w for w in result['warnings'])


def test_auto_falls_back_with_a_warning_when_the_learned_backend_fails(fake, monkeypatch):
    def broken(name, reactions, timeout=0):
        raise mapping_backends.BackendError('LocalMapper failed to start: boom')
    monkeypatch.setattr(mapping_backends, 'run', broken)
    result = map_reaction_atoms(ESTER)
    assert result['method'] == 'mcs' and any('failed' in w and 'boom' in w for w in result['warnings'])
    with pytest.raises(ValueError, match='boom'):
        map_reaction_atoms(ESTER, {'method': 'localmapper'})


def test_a_map_that_does_not_fit_the_reaction_is_rejected(fake, monkeypatch):
    monkeypatch.setattr(mapping_backends, 'run', lambda name, reactions, timeout=0: [
        {'mapped_rxn': '[CH3:1][NH2:2]>>[CH3:1][NH2:2]', 'confident': True}])
    with pytest.raises(ValueError, match='not in the reaction'):
        map_reaction_atoms(ESTER, {'method': 'localmapper'})
    monkeypatch.setattr(mapping_backends, 'run', lambda name, reactions, timeout=0: [
        {'mapped_rxn': '[CH3:1][CH2:2][OH:3]>>[CH3:1][CH2:2][OH:3]', 'confident': True}])
    with pytest.raises(ValueError, match='dropped'):
        map_reaction_atoms(ESTER, {'method': 'localmapper'})
    monkeypatch.setattr(mapping_backends, 'run', lambda name, reactions, timeout=0: [{'error': 'ValueError: too big'}])
    with pytest.raises(ValueError, match='too big'):
        map_reaction_atoms(ESTER, {'method': 'localmapper'})


def test_compare_runs_every_method_and_lists_the_atoms_they_disagree_on(fake):
    result = map_reaction_atoms(ESTER, {'compare': True})
    comparison = result['comparison']
    assert set(comparison['methods']) == {'localmapper', 'rxnmapper', 'mcs'} and comparison['failed'] == {}
    assert comparison['methods']['mcs']['status'] == 'ambiguous'
    oxygen = [d for d in comparison['disagreements'] if d['product_atom'] == 'O']
    assert len(oxygen) == 1 and oxygen[0]['source']['mcs'] is None
    assert oxygen[0]['source']['localmapper']['species'] == 'OCC'
    assert result['method'] == 'localmapper'


def test_stub_backend_runs_through_the_json_worker(tmp_path, monkeypatch):
    (tmp_path / 'rxnmapper.py').write_text(textwrap.dedent('''
        class RXNMapper:
            def get_attention_guided_atom_maps(self, reactions):
                print("progress line that must not reach the answer")
                return [{"mapped_rxn": "[CH3:1][OH:2]>>[CH3:1][OH:2]", "confidence": 0.5} for _ in reactions]
        '''))
    monkeypatch.setenv('CHEMDRAW_MAPPER_HOME', str(tmp_path / 'none'))
    monkeypatch.setenv('PYTHONPATH', str(tmp_path))
    monkeypatch.syspath_prepend(str(tmp_path))
    assert mapping_backends.available()['rxnmapper'] is True
    assert mapping_backends.run('rxnmapper', ['CO>>CO']) == [{'mapped_rxn': '[CH3:1][OH:2]>>[CH3:1][OH:2]', 'confidence': 0.5}]


def test_worker_reports_one_bad_reaction_without_losing_the_others(tmp_path, monkeypatch):
    (tmp_path / 'rxnmapper.py').write_text(textwrap.dedent('''
        class RXNMapper:
            def get_attention_guided_atom_maps(self, reactions):
                if reactions[0] == "bad":
                    raise ValueError("too long")
                return [{"mapped_rxn": reactions[0], "confidence": 1.0}]
        '''))
    monkeypatch.setenv('CHEMDRAW_MAPPER_HOME', str(tmp_path / 'none'))
    monkeypatch.setenv('PYTHONPATH', str(tmp_path))
    monkeypatch.syspath_prepend(str(tmp_path))
    first, second = mapping_backends.run('rxnmapper', ['bad', 'CO>>CO'])
    assert first == {'error': 'ValueError: too long'} and second['mapped_rxn'] == 'CO>>CO'


def test_environment_layout_and_install_plan(tmp_path, monkeypatch):
    monkeypatch.setenv('CHEMDRAW_MAPPER_HOME', str(tmp_path))
    assert mapping_backends.home() == tmp_path
    assert mapping_backends.environment('localmapper') == tmp_path / 'localmapper'
    monkeypatch.setattr(mapping_backends.importlib.util, 'find_spec', lambda name: None)
    assert mapping_backends.available() == {'rxnmapper': False, 'localmapper': False}
    bin_dir = tmp_path / 'rxnmapper' / ('Scripts' if sys.platform == 'win32' else 'bin')
    bin_dir.mkdir(parents=True)
    (bin_dir / ('python.exe' if sys.platform == 'win32' else 'python3')).write_text('')
    assert mapping_backends.available()['rxnmapper'] is True
    with pytest.raises(mapping_backends.BackendError, match='install-mappers localmapper'):
        mapping_backends.run('localmapper', ['CO>>CO'])
    plan = mapping_backends.install('localmapper', dry_run=True)
    assert plan['environment'] == str(tmp_path / 'localmapper') and 'torch==2.3.0' in plan['requirements']
    assert 'ok' not in plan and not (tmp_path / 'localmapper').exists()


def test_install_builds_a_separate_environment_installs_pinned_requirements_and_self_tests(tmp_path, monkeypatch):
    monkeypatch.setenv('CHEMDRAW_MAPPER_HOME', str(tmp_path))
    commands = []
    bin_dir = 'Scripts' if sys.platform == 'win32' else 'bin'
    exe = 'python.exe' if sys.platform == 'win32' else 'python3'

    def fake_run(command, **kwargs):
        commands.append(command)
        if command[1:3] == ['-m', 'venv']:
            (tmp_path / 'localmapper' / bin_dir).mkdir(parents=True)
            (tmp_path / 'localmapper' / bin_dir / exe).write_text('')
        return mapping_backends.subprocess.CompletedProcess(command, 0, '', '')

    monkeypatch.setattr(mapping_backends, 'find_base', lambda name: '/usr/bin/python3.12')
    monkeypatch.setattr(mapping_backends.subprocess, 'run', fake_run)
    monkeypatch.setattr(mapping_backends, 'run', lambda name, reactions, timeout=0: [{'mapped_rxn': 'C>>C'}])
    report = mapping_backends.install('localmapper', log=mapping_backends.subprocess.DEVNULL)
    assert report['ok'] is True and report['self_test'] == 'C>>C'
    assert commands[0] == ['/usr/bin/python3.12', '-m', 'venv', str(tmp_path / 'localmapper')]
    pip = [c for c in commands if c[1:4] == ['-m', 'pip', 'install']][0]
    assert 'torch==2.3.0' in pip and 'localmapper==0.1.5' in pip
    assert pip[0].startswith(str(tmp_path / 'localmapper'))  # never the runtime's own interpreter


def test_install_reports_a_missing_python_instead_of_raising(tmp_path, monkeypatch):
    monkeypatch.setenv('CHEMDRAW_MAPPER_HOME', str(tmp_path))
    monkeypatch.setattr(mapping_backends, 'find_base', lambda name: None)
    monkeypatch.setattr(mapping_backends.shutil, 'which', lambda name: None)
    report = mapping_backends.install('localmapper')
    assert report['ok'] is False and 'Python 3.10 to 3.12' in report['error']


def test_find_base_accepts_only_a_supported_python_minor_version(monkeypatch):
    versions = {sys.executable: 14, '/py/3.12': 12}
    monkeypatch.setattr(mapping_backends, '_minor', lambda python: versions.get(str(python)))
    monkeypatch.setattr(mapping_backends.shutil, 'which', lambda name: '/py/3.12' if name == 'python3.12' else None)
    assert mapping_backends.find_base('localmapper') == '/py/3.12'
    versions[sys.executable] = 11
    assert mapping_backends.find_base('localmapper') == sys.executable
    versions.update({sys.executable: 14, '/py/3.12': 14})
    assert mapping_backends.find_base('localmapper') is None


def test_status_command_lists_each_backend(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv('CHEMDRAW_MAPPER_HOME', str(tmp_path))
    monkeypatch.setattr(mapping_backends, 'available', lambda: {'rxnmapper': True, 'localmapper': False})
    assert mapping_backends.main(['--status']) == 0
    status = json.loads(capsys.readouterr().out)
    assert status['backends']['rxnmapper']['available'] is True and status['backends']['localmapper']['available'] is False


def test_map_atoms_validates_method_before_searching():
    with pytest.raises(ValueError, match='Unknown method'):
        atom_mapping.map_atoms([('a', Chem.MolFromSmiles('CO'))], [('b', Chem.MolFromSmiles('CO'))], method='x')


def test_compare_ignores_swaps_between_symmetry_equivalent_product_atoms(monkeypatch):
    suzuki = 'Brc1ccccc1.OB(O)c1ccccc1>>c1ccc(-c2ccccc2)cc1'
    # the boronic acid ring is placed on the other ring of the symmetric biphenyl than the built-in method does
    mapped = ('Br[c:5]1[cH:6][cH:7][cH:8][cH:9][cH:10]1.OB(O)[c:4]1[cH:3][cH:2][cH:1][cH:12][cH:11]1>>'
              '[cH:1]1[cH:2][cH:3][c:4](-[c:5]2[cH:6][cH:7][cH:8][cH:9][cH:10]2)[cH:11][cH:12]1')
    monkeypatch.setattr(mapping_backends, 'available', lambda: {'rxnmapper': False, 'localmapper': True})
    monkeypatch.setattr(mapping_backends, 'run', lambda name, reactions, timeout=0: [
        {'mapped_rxn': mapped, 'confident': True}])
    comparison = map_reaction_atoms(suzuki, {'compare': True})['comparison']
    assert set(comparison['methods']) == {'localmapper', 'mcs'} and comparison['disagreements'] == []
    assert comparison['agree'] is True
