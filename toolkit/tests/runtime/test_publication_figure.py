"""Publication workflows use the grounded structures from existing figure tests."""
import csv
import json
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

STEREO = 'N[C@@H]1CC[C@H](O)C1'
OTHER = 'CC[C@H](F)[C@H](C)O |&1:2,4|'


def request(tmp_path, rows=None, **options):
    rows = rows or [['a', '1', STEREO, '82%', 'amine'], ['b', '2', OTHER, '<10 nM', 'alcohol']]
    table = tmp_path/'data.csv'
    with table.open('w', newline='', encoding='utf-8') as stream:
        writer = csv.writer(stream)
        writer.writerow(['compound_id','label','smiles','value','group'])
        writer.writerows(rows)
    spec = {'table': str(table), 'mode':'scope', 'fields':[{'column':'value','label':'Result'}],
            'group_column':'group', 'native_render':False, **options}
    path = tmp_path/'spec.json'; path.write_text(json.dumps(spec))
    return path


def execute(spec, output, operation='create'):
    from cdxml_toolkit.mcp_runtime.publication_figure import publication_figure
    return publication_figure(operation, str(spec), str(output))


def test_create_binding_pagination_and_reproducibility(tmp_path):
    rows = [[f'id{i}', str(i), STEREO if i % 2 else OTHER,
             '' if i == 2 else f'>{i} nM', 'Series'] for i in range(48)]
    spec = request(tmp_path, rows, mode='sar')
    a,b=tmp_path/'a',tmp_path/'b'
    assert execute(spec,a)['ok']
    assert execute(spec,b)['ok']
    project=json.loads((a/'project.json').read_text())
    assert len(project['compounds']) == 48
    assert len(project['pages']) > 1
    assert project['compounds']['id2']['input']['values']['value'] == ''
    for page in project['pages']:
        assert (a/page['file']).read_bytes() == (b/page['file']).read_bytes()
    assert json.loads((a/'checks.json').read_text())['data_binding']['status']=='passed'
    assert not json.loads((a/'checks.json').read_text())['layout']['issues']


@pytest.mark.parametrize('rows', [
    [['a','1',STEREO,'1',''],['a','2',OTHER,'2','']],
    [['a','1','not a structure','1','']],
])
def test_invalid_data_never_published(tmp_path,rows):
    with pytest.raises(ValueError, match='row'):
        execute(request(tmp_path,rows),tmp_path/'out')
    assert not (tmp_path/'out').exists()


def test_metric_update_preserves_manual_layout_and_annotation(tmp_path):
    spec=request(tmp_path)
    base=tmp_path/'base'; execute(spec,base)
    project=json.loads((base/'project.json').read_text()); record=project['compounds']['a']
    page=record['page']; tree=ET.parse(base/project['pages'][page]['file'])
    group=tree.find(f".//group[@id='{record['objects']['group']}']")
    from cdxml_toolkit.mcp_runtime.figure_tools import _move
    _move(group,5,7)
    label=group.find(f"t[@id='{record['objects']['label']}']")
    label.find('s').set('face','1')
    ET.SubElement(tree.find('page'),'t',{'id':'99001','p':'30 25'}).append(ET.Element('s',{'font':'3','size':'8'}))
    tree.find(".//t[@id='99001']/s").text='Keep this annotation'
    edited=tmp_path/'edited.cdxml';tree.write(edited)
    before=ET.tostring(group.find('fragment'))
    spec=request(tmp_path,[['b','2',OTHER,'<10 nM','alcohol'],['a','1',STEREO,'91%','amine']],
                 project_path=str(base/'project.json'),edited_pages={str(page):str(edited)})
    out=tmp_path/'updated'; result=execute(spec,out,'update'); assert result['ok']
    after=ET.parse(out/project['pages'][page]['file'])
    assert ET.tostring(after.find(f".//group[@id='{record['objects']['group']}']/fragment"))==before
    assert '91%' in ''.join(after.getroot().itertext())
    assert 'Keep this annotation' in ''.join(after.getroot().itertext())
    assert after.find(f".//t[@id='{record['objects']['label']}']/s").get('face')=='1'


def test_concurrent_value_edit_is_conflict_draft(tmp_path):
    spec=request(tmp_path);base=tmp_path/'base';execute(spec,base)
    p=json.loads((base/'project.json').read_text());r=p['compounds']['a']
    tree=ET.parse(base/p['pages'][r['page']]['file'])
    tree.find(f".//t[@id='{r['objects']['fields']['value']}']/s").text='Result: 77%'
    edited=tmp_path/'edited.cdxml';tree.write(edited)
    spec=request(tmp_path,[['a','1',STEREO,'91%','amine'],['b','2',OTHER,'<10 nM','alcohol']],
                 project_path=str(base/'project.json'),edited_pages={str(r['page']):str(edited)})
    out=tmp_path/'update'; result=execute(spec,out,'update')
    assert not result['ok'] and result['status']=='conflict'
    assert (out/'conflicts.json').is_file()
    assert not (out/'project.json').exists()
    assert list((out/'draft').glob('*.cdxml'))


def test_renumbered_native_ids_use_unique_identity_and_label(tmp_path):
    spec=request(tmp_path);base=tmp_path/'base';execute(spec,base)
    p=json.loads((base/'project.json').read_text()); tree=ET.parse(base/p['pages'][0]['file'])
    mapping={n.get('id'):str(int(n.get('id'))+100000) for n in tree.iter() if n.get('id')}
    for node in tree.iter():
        if node.get('id'):node.set('id',mapping[node.get('id')])
        for attr in ('B','E','BondOrdering'):
            if node.get(attr):node.set(attr,' '.join(mapping.get(v,v) for v in node.get(attr).split()))
    path=tmp_path/'renumbered.cdxml';tree.write(path)
    spec=request(tmp_path,project_path=str(base/'project.json'),edited_pages={'0':str(path)})
    assert execute(spec,tmp_path/'updated','update')['ok']


def test_missing_group_and_ambiguous_duplicate_are_conflicts(tmp_path):
    from copy import deepcopy
    spec=request(tmp_path,[['a','1',STEREO,'1',''],['b','1',STEREO,'1','']])
    base=tmp_path/'base';execute(spec,base);p=json.loads((base/'project.json').read_text())
    tree=ET.parse(base/p['pages'][0]['file']);page=tree.find('page')
    for group in page.findall('group'):group.set('id',str(int(group.get('id'))+9000))
    edited=tmp_path/'edited.cdxml';tree.write(edited)
    spec=request(tmp_path,[['a','1',STEREO,'1',''],['b','1',STEREO,'1','']],project_path=str(base/'project.json'),edited_pages={'0':str(edited)})
    assert not execute(spec,tmp_path/'conflict','update')['ok']


def test_new_and_deleted_compounds_keep_existing_pages(tmp_path):
    spec=request(tmp_path);base=tmp_path/'base';execute(spec,base)
    p=json.loads((base/'project.json').read_text())
    spec=request(tmp_path,[['a','1',STEREO,'82%','amine'],['c','3',OTHER,'33%','alcohol']],project_path=str(base/'project.json'))
    out=tmp_path/'updated';assert execute(spec,out,'update')['ok']
    q=json.loads((out/'project.json').read_text())
    assert set(q['compounds'])=={'a','c'}
    assert q['compounds']['a']['page']==p['compounds']['a']['page']
    assert q['compounds']['c']['page']>=len(p['pages'])


def test_mol_and_sdf_identity_binding(tmp_path):
    from rdkit import Chem
    mol=Chem.MolFromSmiles(STEREO)
    Chem.MolToMolFile(mol,str(tmp_path/'a.mol'))
    spec=request(tmp_path,[['a','1','a.mol','82%','']],structure={'format':'mol','column':'smiles'})
    assert execute(spec,tmp_path/'mol')['ok']
    writer=Chem.SDWriter(str(tmp_path/'library.sdf'));mol.SetProp('compound_id','a');writer.write(mol);writer.close()
    spec=request(tmp_path,[['a','1','','82%','']],structure={'format':'sdf','file':'library.sdf'})
    assert execute(spec,tmp_path/'sdf')['ok']


def test_structure_replacement_has_explicit_core_map(tmp_path):
    # Existing aspirin fixture and its resolved salicylic-acid substructure.
    old='CC(=O)Oc1ccccc1C(=O)O'
    new='O=C(O)c1ccccc1O'
    from rdkit import Chem
    a,b=Chem.MolFromSmiles(old),Chem.MolFromSmiles(new)
    match=a.GetSubstructMatch(b)
    spec=request(tmp_path,[['a','1',old,'82%','']]);base=tmp_path/'base';execute(spec,base)
    spec=request(tmp_path,[['a','1',new,'82%','']],project_path=str(base/'project.json'),atom_maps={'a':[[i,j] for j,i in enumerate(match)]})
    out=tmp_path/'updated';result=execute(spec,out,'update')
    assert result['ok'], (out/'conflicts.json').read_text() if (out/'conflicts.json').exists() else result
    q=json.loads((out/'project.json').read_text())
    from cdxml_toolkit.chemistry_semantics import semantic_key
    assert q['compounds']['a']['displayed_identity']==semantic_key(b)


def test_check_rejects_tampered_measurement(tmp_path):
    spec=request(tmp_path);base=tmp_path/'base';execute(spec,base)
    p=json.loads((base/'project.json').read_text());r=p['compounds']['a']
    tree=ET.parse(base/p['pages'][0]['file']);tree.find(f".//t[@id='{r['objects']['fields']['value']}']/s").text='wrong'
    edited=tmp_path/'edited.cdxml';tree.write(edited)
    spec=request(tmp_path,project_path=str(base/'project.json'),edited_pages={'0':str(edited)})
    assert not execute(spec,tmp_path/'checked','check')['ok']


def test_xlsx_cached_formula_and_missing_cache(tmp_path):
    # Minimal OOXML fixture: explicitly control the formula cache without Excel.
    import zipfile
    from xml.sax.saxutils import escape
    from cdxml_toolkit.publication.data import table_rows
    path=tmp_path/'data.xlsx'
    def workbook(cached):
        with zipfile.ZipFile(path,'w') as z:
            z.writestr('[Content_Types].xml','<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/></Types>')
            z.writestr('_rels/.rels','<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>')
            z.writestr('xl/workbook.xml','<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Data" sheetId="1" r:id="rId1"/></sheets></workbook>')
            z.writestr('xl/_rels/workbook.xml.rels','<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/></Relationships>')
            z.writestr('xl/worksheets/sheet1.xml','<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData><row r="1"><c r="A1" t="inlineStr"><is><t>value</t></is></c></row><row r="2"><c r="A2"><f>1+1</f>'+('<v>2</v>' if cached else '')+'</c></row></sheetData></worksheet>')
    pytest.importorskip('openpyxl')
    workbook(False)
    with pytest.raises(ValueError,match='Data!A2'):table_rows(path)
    workbook(True)
    assert table_rows(path)[1][0][1]['value']=='2'


def test_unresolved_chemistry_persists_and_existing_output_is_protected(tmp_path):
    spec=request(tmp_path,unresolved_chemistry=['reader disagreement for compound a'])
    base=tmp_path/'base';execute(spec,base)
    before=(base/'project.json').read_bytes()
    with pytest.raises(ValueError,match='overwrite'):execute(spec,base)
    assert (base/'project.json').read_bytes()==before
    spec=request(tmp_path,project_path=str(base/'project.json'))
    out=tmp_path/'updated';execute(spec,out,'update')
    assert json.loads((out/'checks.json').read_text())['chemistry']['status']=='unresolved'


def test_locked_overflow_is_reported_without_moving(tmp_path):
    spec=request(tmp_path);base=tmp_path/'base';execute(spec,base)
    p=json.loads((base/'project.json').read_text());tree=ET.parse(base/p['pages'][0]['file'])
    from cdxml_toolkit.mcp_runtime.figure_tools import _move
    _move(tree.find('page/group'),1000,0)
    edited=tmp_path/'edited.cdxml';tree.write(edited)
    spec=request(tmp_path,project_path=str(base/'project.json'),edited_pages={'0':str(edited)})
    out=tmp_path/'updated';result=execute(spec,out,'update')
    assert any(i['issue']=='outside_page' for i in result['checks']['layout']['issues'])


def test_coordinate_bearing_cxsmiles_does_not_reuse_old_wedges(tmp_path):
    from rdkit import Chem
    from cdxml_toolkit.chemistry_semantics import read_molecules
    source=Path(__file__).resolve().parents[2]/'samples/publication-figures/stereo-reaction.cdxml'
    mol=read_molecules(source)[0]
    spec=request(tmp_path,[['a','1',Chem.MolToCXSmiles(mol),'82%','']])
    assert execute(spec,tmp_path/'out')['ok']


def test_xlsx_preserves_decimal_percent_and_explicit_units(tmp_path):
    xl=pytest.importorskip('openpyxl')
    from cdxml_toolkit.publication.data import table_rows
    w=xl.Workbook();s=w.active;s.append(['percent','activity','missing'])
    s.append([0.397,12.3,None]);s['A2'].number_format='0.0%'
    s['B2'].number_format='0.00 "µM"'
    p=tmp_path/'units.xlsx';w.save(p)
    row=table_rows(p)[1][0][1]
    assert row=={'percent':'39.7%','activity':'12.30 µM','missing':''}
