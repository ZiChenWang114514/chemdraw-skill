from pathlib import Path
from unittest import mock
import json
import pytest
from rdkit import Chem
from cdxml_toolkit.mcp_runtime import figure_validation as fv, native_io
from cdxml_toolkit.mcp_runtime.official_overrides import draw_molecule


@pytest.mark.parametrize('filename,field', [
    ('reconstruction.cdxml', 'cdxml_sha256'), ('native.png', 'png_sha256'),
])
def test_published_case_matches_verified_bytes(filename, field):
    import hashlib
    case = Path(__file__).resolve().parents[2] / 'assets/readme/stereo-reconstruction'
    evidence = json.loads((case / 'verification.json').read_text(encoding='utf-8'))
    assert hashlib.sha256((case / filename).read_bytes()).hexdigest() == evidence[field]


@pytest.mark.parametrize('smiles,hydrogens,radicals', [
    ('CCN', 7, 0), ('CC[NH]', 6, 1), ('CC(=O)O', 4, 0),
    ('CC(=O)[O]', 3, 1), ('[2H]O[H]', 2, 0), ('[NH4+]', 4, 0),
])
def test_inventory_exposes_hydrogen_and_radical_changes(tmp_path, smiles, hydrogens, radicals):
    source = tmp_path / 'input.cdxml'
    source.write_text('<CDXML/>')
    molecule = Chem.MolFromSmiles(smiles)
    # Isolate inventory accounting from version-dependent CDXML parsing.
    with mock.patch.object(fv, 'read_molecules', return_value=[molecule]):
        observed = fv.inspect_document(source)['molecules'][0]
    assert observed['hydrogen_count'] == hydrogens
    assert observed['radical_electrons'] == radicals


def test_native_hydrogen_loss_cannot_be_accepted(tmp_path):
    source = tmp_path / 'input.cdxml'
    source.write_text('<CDXML/>')
    with mock.patch.object(fv, 'read_molecules', return_value=[Chem.MolFromSmiles('CCN')]):
        before = fv.inspect_document(source)
    with mock.patch.object(fv, 'read_molecules', return_value=[Chem.MolFromSmiles('CC[NH]')]):
        after = fv.inspect_document(source)
    result = fv.compare_inventories(before, after)
    assert result['status'] == 'changed'
    assert not result['composition_preserved']


@pytest.mark.parametrize('bom',[b'',b'\xef\xbb\xbf'])
def test_alias_normalized_only_in_staging(tmp_path,bom):
    source=tmp_path/'input.cdxml'
    source.write_bytes(bom+b'<?xml version="1.0" encoding="utf8"?><CDXML/>')
    original=source.read_bytes()
    with native_io.ascii_inputs([source]) as paths:
        assert b'encoding="UTF-8"' in paths[0].read_bytes()
    assert source.read_bytes()==original


def test_validation_report_with_no_native(tmp_path):
    source=tmp_path/'input.cdxml'
    draw_molecule({'smiles':'CCO'},str(source))
    fv.validate_figure(str(source),str(tmp_path/'check'))
    report=json.loads((tmp_path/'check/report.json').read_text())
    assert report['basic']['molecule_count']==1
    assert report['native']['status']=='not_run'
    assert report['source_unchanged']
    with pytest.raises(ValueError):fv.validate_figure(str(source),str(tmp_path/'check'))


def test_native_implicit_ligand_zero_is_not_dangling(tmp_path):
    source=tmp_path/'implicit.cdxml'
    source.write_text('<CDXML><page id="1"><fragment id="2"><n id="3" p="0 0" BondOrdering="0 4"/><n id="4" p="20 0"/><b id="5" B="3" E="4"/></fragment></page></CDXML>')
    assert fv.inspect_document(source)['molecule_count']==1


def test_native_failure_is_not_pass(tmp_path):
    source=tmp_path/'input.cdxml'
    draw_molecule({'smiles':'CCO'},str(source))
    with mock.patch.object(fv,'_worker',return_value={'ok':False,'error':{'code':'native_missing'}}):
        fv.validate_figure(str(source),str(tmp_path/'check'),native=True,cross_reader=True)
    report=json.loads((tmp_path/'check/report.json').read_text())
    assert report['native']['status']=='failed'
    assert report['cross_reader']['status']=='not_run'


def test_added_stereo_assignment_is_reported(tmp_path):
    a=tmp_path/'a.cdxml';b=tmp_path/'b.cdxml'
    draw_molecule({'smiles':'FC(Cl)Br'},str(a))
    draw_molecule({'smiles':'F[C@H](Cl)Br'},str(b))
    diff=fv.compare_inventories(fv.inspect_document(a),fv.inspect_document(b))
    assert diff['connectivity_preserved']
    assert not diff['semantic_inventory_preserved']
    assert diff['molecules'][0]['comparison']['stereo_changes'][0]['kind']=='added_assignment'


def test_cross_reader_compares_canonical_structures_not_smiles_text(tmp_path):
    source=tmp_path/'input.cdxml';draw_molecule({'smiles':'CCO'},str(source))
    with mock.patch.object(fv,'_worker',return_value={'ok':True,'result':{'outputs':{'molecule_a':{'canonical_smiles':'OCC'}}}}):
        result=fv._cross_reader(source,tmp_path)
    assert result['status']=='consistent'


def test_native_invalid_saved_xml_retains_failed_report(tmp_path):
    source=tmp_path/'input.cdxml';draw_molecule({'smiles':'CCO'},str(source))
    def broken(name,args):
        Path(args['output_path']).write_text('<broken')
        return {'ok':True}
    with mock.patch.object(fv,'_worker',side_effect=broken):
        fv.validate_figure(str(source),str(tmp_path/'check'),native=True)
    report=json.loads((tmp_path/'check/report.json').read_text())
    assert report['native']['status']=='failed'


def test_stereo_display_change_cannot_pass_as_layout(tmp_path):
    import xml.etree.ElementTree as ET
    from cdxml_toolkit.mcp_runtime.figure_tools import compose_chemical_figure
    source=tmp_path/'input.cdxml';draw_molecule({'smiles':'F[C@H](Cl)Br'},str(source))
    b=next(b for b in ET.parse(source).iter('b') if 'Wedge' in b.get('Display',''))
    manifest=tmp_path/'manifest.json'
    manifest.write_text(json.dumps({'template_path':str(source),'edits':[{'id':b.get('id'),'display':'None'}]}))
    with pytest.raises(ValueError):compose_chemical_figure(str(manifest),str(tmp_path/'changed.cdxml'))
    assert not (tmp_path/'changed.cdxml').exists()
