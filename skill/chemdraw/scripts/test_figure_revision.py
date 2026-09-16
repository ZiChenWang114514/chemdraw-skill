import json
from unittest import mock
import xml.etree.ElementTree as ET

import pytest

from cdxml_toolkit.mcp_runtime import capabilities, figure_tools, tool_registry


def test_real_diagnostics_envelope_and_summary():
    diagnostic = {'ok': True, 'outputs': {'capabilities': {'python': {'status': 'available'}}},
                  'warnings': ['optional native unavailable']}
    with mock.patch('cdxml_toolkit.mcp_runtime.runtime_diagnostics.diagnose_runtime', return_value=diagnostic):
        full = capabilities.get_toolkit_capabilities()
        summary = capabilities.get_toolkit_capabilities(detail='summary')
    assert full['outputs']['capabilities'] == diagnostic['outputs']['capabilities']
    assert summary['warnings'] == diagnostic['warnings']
    assert 'tools' not in summary['outputs']
    assert summary['outputs']['tool_schema_sha256'] == full['outputs']['tool_schema_sha256']


def test_crossings_and_solid_display_preserve_graph(tmp_path):
    source = tmp_path / 'input.cdxml'
    source.write_text('''<CDXML><page id="1"><fragment id="2">
      <n id="3" p="0 0"/><n id="4" p="30 30"/>
      <n id="5" p="0 30"/><n id="6" p="30 0" Element="7"/>
      <b id="7" B="3" E="4" Order="1"/>
      <b id="8" B="5" E="6" Order="1" Display="Dash"/>
      </fragment></page></CDXML>''')
    manifest = tmp_path / 'scene.json'
    manifest.write_text(json.dumps({'template_path': str(source),
        'edits': [{'id': '8', 'display': 'None'}], 'crossings': [{'front': '7', 'back': '8'}]}))
    output = tmp_path / 'output.cdxml'
    figure_tools.compose_chemical_figure(str(manifest), str(output))
    bonds = ET.parse(output).findall('.//b')
    assert [b.get('id') for b in bonds] == ['8', '7']
    assert bonds[0].get('Display') is None
    assert bonds[0].get('CrossingBonds') == '7'
    assert bonds[1].get('CrossingBonds') == '8'
    assert all(b.get('Order') == '1' for b in bonds)
    assert float(bonds[0].get('Z')) < float(bonds[1].get('Z'))


def test_crossing_cycle_rejected(tmp_path):
    from cdxml_toolkit.mcp_runtime.figure_editing import apply_crossings
    root = ET.fromstring('<page><fragment><b id="1" B="a" E="b"/><b id="2" B="c" E="d"/></fragment></page>')
    with pytest.raises(ValueError, match='cycle'):
        apply_crossings(root, [{'front':'1','back':'2'}, {'front':'2','back':'1'}])


def test_diff_timeout_is_not_empty_success():
    from cdxml_toolkit.chemistry_diff import structural_diff
    with mock.patch('rdkit.Chem.rdFMCS.FindMCS', return_value=mock.Mock(canceled=True)):
        result = structural_diff('CCO', 'CCN')
    assert result['status'] == 'not_completed'
    assert result['reason'] == 'mcs_timeout'
    assert result['atom_mapping'] is None


def test_diff_identical_and_symmetric():
    from cdxml_toolkit.chemistry_diff import structural_diff
    assert structural_diff('CCO', 'OCC')['status'] == 'completed'
    result = structural_diff('c1ccccc1', 'Cc1ccccc1')
    assert result['status'] == 'partial'
    assert result['reason'] == 'ambiguous_atom_mapping'


@pytest.mark.parametrize('failure,reason', [(RuntimeError('failed'), 'comparison_exception'),
    (mock.Mock(canceled=False, numAtoms=0), 'no_common_substructure')])
def test_diff_incomplete_reasons(failure, reason):
    from cdxml_toolkit.chemistry_diff import structural_diff
    options = {'side_effect':failure} if isinstance(failure,Exception) else {'return_value':failure}
    with mock.patch('rdkit.Chem.rdFMCS.FindMCS', **options):
        result=structural_diff('CCO','CCN')
    assert result['status']=='not_completed' and result['reason']==reason
    assert result['bond_changes'] is None


def test_double_bond_configuration_change_is_reported():
    from cdxml_toolkit.chemistry_diff import structural_diff
    result=structural_diff('F/C=C/Cl','F/C=C\\Cl')
    assert result['status']=='completed'
    assert any(change['kind']=='bond_stereo_changed' for change in result['stereo_changes'])


def test_unmapped_enhanced_stereo_is_not_empty_success():
    from cdxml_toolkit.chemistry_diff import structural_diff
    result=structural_diff('F[C@H](Cl)Br |&1:1|','F[C@H](Cl)Br |o1:1|')
    assert result['status']=='partial'
    assert result['reason']=='unclassified_semantic_difference'


def test_validation_dangling_reference(tmp_path):
    from cdxml_toolkit.mcp_runtime.figure_validation import inspect_document
    source = tmp_path / 'bad.cdxml'
    source.write_text('<CDXML><page id="1"><fragment id="2"><n id="3"/><b id="4" B="3" E="99"/></fragment></page></CDXML>')
    with pytest.raises(ValueError, match='reference'):
        inspect_document(source)
