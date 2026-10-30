from __future__ import annotations

from types import SimpleNamespace

import pytest

from cdxml_toolkit.mcp_runtime import chemscript_sdk, report_tools
from cdxml_toolkit.mcp_runtime.report_tools import chemdraw_chemical_properties
from cdxml_toolkit.mcp_runtime.tool_registry import build_registry

ASPIRIN = 'CC(=O)Oc1ccccc1C(=O)O'
ETHANOL = 'CCO'
VALUES = {
    ASPIRIN: {'Formula': 'C9H8O4', 'Weight': 180.159, 'ExactMass': 180.0423,
              'ElementalAnalysis': 'C, 60.00; H, 4.48; O, 35.52', 'PartitionCoefficient': 1.0235,
              'Refractivity': 4.4576},
    ETHANOL: {'Formula': 'C2H6O', 'Weight': 46.069, 'ExactMass': 46.0419,
              'ElementalAnalysis': 'C, 52.14; H, 13.13; O, 34.73', 'PartitionCoefficient': -0.235,
              'Refractivity': 1.2},
}


class FakeSdk:
    """Executes the declarative programs the tool sends against a table of values."""

    def __init__(self, broken=()):
        self.calls = []
        self.broken = set(broken)  # (smiles, member) pairs that raise

    def __call__(self, program, **options):
        self.calls.append(program)
        loaded = {}
        results = []
        for index, step in enumerate(program):
            if step['op'] == 'call_static':
                assert (step['type'], step['member']) == ('StructureData', 'LoadData')
                loaded[step['as']] = step['args'][0]
                results.append({'step': index, 'op': step['op'], 'value': {'$ref': step['as']}})
                continue
            smiles = loaded[step['target']]
            if (smiles, step['member']) in self.broken:
                raise RuntimeError(f"{step['member']} failed")
            results.append({'step': index, 'op': step['op'], 'value': VALUES[smiles][step['member']]})
        return {'ok': True, 'outputs': {'assembly': 'CambridgeSoft.ChemScript, Version=22.2.0.3300', 'results': results},
                'warnings': [], 'metadata': {}}


@pytest.fixture
def sdk(monkeypatch):
    # The Windows ChemScript answers every property; the macOS test sets its own platform.
    monkeypatch.setattr(report_tools, 'sys', SimpleNamespace(platform='win32'))

    def install(fake):
        monkeypatch.setattr(chemscript_sdk, 'execute_chemscript_sdk', fake)
        return fake
    return install


def test_values_are_chemdraws_own_and_carry_their_provenance(sdk):
    fake = sdk(FakeSdk())

    result = chemdraw_chemical_properties([{'smiles': ASPIRIN, 'label': 'aspirin'}, ETHANOL])

    assert result['ok'] and result['operation'] == 'chemdraw_chemical_properties' and result['count'] == 2
    assert result['provenance']['engine'] == 'ChemDraw ChemScript'
    assert '22.2.0.3300' in result['provenance']['assembly']
    row = result['results'][0]
    assert row['label'] == 'aspirin'
    assert (row['formula'], row['average_mass'], row['exact_mass']) == ('C9H8O4', 180.159, 180.0423)
    assert row['elemental_analysis'] == 'C, 60.00; H, 4.48; O, 35.52'
    assert (row['log_p'], row['molar_refractivity']) == (1.0235, 4.4576)
    assert result['results'][1]['log_p'] == -0.235
    assert len(fake.calls) == 1  # both structures in one ChemDraw session
    assert not result['warnings']


def test_one_failing_property_is_reported_and_the_others_are_kept(sdk):
    fake = sdk(FakeSdk(broken={(ASPIRIN, 'PartitionCoefficient')}))

    result = chemdraw_chemical_properties([ASPIRIN, ETHANOL])

    first, second = result['results']
    assert first['log_p'] is None and 'PartitionCoefficient' in first['errors']['log_p']
    assert first['formula'] == 'C9H8O4' and first['molar_refractivity'] == 4.4576
    assert second['log_p'] == -0.235 and 'errors' not in second
    assert any('aspirin' in w or ASPIRIN in w or '#1' in w for w in result['warnings'])
    assert len(fake.calls) > 1  # the failing batch was split to isolate the property


def test_generic_atoms_are_refused_instead_of_estimated(sdk):
    sdk(FakeSdk())

    with pytest.raises(ValueError, match='generic atoms'):
        chemdraw_chemical_properties(['*CC(=O)O'])


def test_large_batches_are_split_to_stay_within_the_program_limit(sdk):
    fake = sdk(FakeSdk())

    chemdraw_chemical_properties([ETHANOL] * 70)

    assert len(fake.calls) == 3
    assert all(len(program) <= 256 for program in fake.calls)


def test_missing_chemscript_is_an_error_not_a_substitute(sdk):
    def unavailable(program, **options):
        raise chemscript_sdk.ChemScriptSdkUnavailable('ChemScript needs Windows or macOS')

    sdk(unavailable)

    with pytest.raises(chemscript_sdk.ChemScriptSdkUnavailable):
        chemdraw_chemical_properties([ETHANOL])


def test_output_file_is_written_once_and_never_replaced(sdk, tmp_path):
    sdk(FakeSdk())
    target = tmp_path / 'props.csv'

    result = chemdraw_chemical_properties([ETHANOL], output_path=str(target))

    text = target.read_text(encoding='utf-8')
    assert text.splitlines()[0].startswith('label,smiles,formula,average_mass')
    assert result['output_path'] == str(target)
    with pytest.raises(Exception):
        chemdraw_chemical_properties([ETHANOL], output_path=str(target))


def test_tool_is_registered_with_the_chemscript_tools():
    from cdxml_toolkit.mcp_runtime import tool_registry

    assert 'chemdraw_chemical_properties' in build_registry()
    assert 'chemdraw_chemical_properties' in build_registry('chemscript')
    assert 'chemdraw_chemical_properties' not in build_registry('core')
    assert tool_registry._resource_class('chemdraw_chemical_properties', 'darwin') == 'chemdraw_com'


def test_macos_skips_what_chemdraw_for_macos_cannot_give(sdk, monkeypatch):
    fake = sdk(FakeSdk())
    monkeypatch.setattr(report_tools, 'sys', SimpleNamespace(platform='darwin'))

    result = chemdraw_chemical_properties([ETHANOL])

    asked = {step['member'] for step in fake.calls[0] if step['op'] != 'call_static'}
    assert asked == {'Formula', 'Weight', 'ExactMass', 'ElementalAnalysis'} and len(fake.calls) == 1
    row = result['results'][0]
    assert row['average_mass'] == 46.069 and row['elemental_analysis'] == 'C, 52.14; H, 13.13; O, 34.73'
    assert row['log_p'] is None and row['molar_refractivity'] is None and 'errors' not in row
    assert result['warnings'] == ['ChemDraw for macOS cannot give log_p, molar_refractivity; '
                                  'they are null in every row.']
