import json
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest
from rdkit import Chem
from PIL import Image

from cdxml_toolkit.chemistry_semantics import semantic_key, read_molecules, validate_document_preserved
from cdxml_toolkit.mcp_runtime import official_overrides as api
from cdxml_toolkit.mcp_runtime.figure_tools import compose_chemical_figure, rdkit_workbench, compare_figure_images
from cdxml_toolkit.mcp_runtime.structure_fidelity import repair_and_validate_drawn_cdxml, StructureFidelityError

# Grounded fixtures: existing runtime tests and RDKit Book enhanced stereo examples.
STEREO='N[C@@H]1CC[C@H](O)C1'
AND='CC[C@H](F)[C@H](C)O |&1:2,4|'

@pytest.mark.parametrize('damage', ['missing', 'duplicate', 'mirror'])
def test_final_serialized_inventory_rejects_damage(tmp_path, monkeypatch, damage):
    from copy import deepcopy
    original = ET.ElementTree.write
    def damaged_write(tree, *args, **kwargs):
        if tree.getroot().tag != 'CDXML' or not isinstance(args[0], Path):
            return original(tree, *args, **kwargs)
        page = tree.find('page')
        fragment = page.find('fragment')
        if damage == 'missing':
            page.remove(fragment)
        elif damage == 'duplicate':
            page.append(deepcopy(fragment))
        else:
            for node in fragment.iter('n'):
                x, y = map(float, node.get('p').split())
                node.set('p', f'{-x} {y}')
        return original(tree, *args, **kwargs)
    monkeypatch.setattr(ET.ElementTree, 'write', damaged_write)
    with pytest.raises(ValueError):
        compose(tmp_path, {'objects':[{'type':'molecule','smiles':STEREO}]})
    assert not (tmp_path/'figure.cdxml').exists()

def test_document_receipt_counts_duplicate_species(tmp_path):
    import hashlib
    _, source = compose(tmp_path, {'objects':[{'type':'molecule','smiles':STEREO}]}, 'source')
    result, output = compose(tmp_path, {'template_path':str(source),
        'objects':[{'type':'molecule','smiles':STEREO,'position':[300,100]}]})
    receipt = result['metadata']['document_chemistry_validation']
    assert receipt['molecules'] == 2
    assert receipt['sha256'] == hashlib.sha256(output.read_bytes()).hexdigest()
    assert receipt['scope'] == 'rdkit_readback_consistency'

@pytest.mark.parametrize('group',['&1','o1','a'])
def test_enhanced_stereo_roundtrip(tmp_path,group):
    source=f'CC[C@H](F)[C@H](C)O |{group}:2,4|'
    output=tmp_path/'group.cdxml'
    api.draw_molecule({'smiles':source},str(output))
    assert semantic_key(read_molecules(output)[0])==semantic_key(Chem.MolFromSmiles(source))

def test_mirror_fails_even_when_wedge_count_matches(tmp_path):
    output=tmp_path/'source.cdxml'
    api.draw_molecule({'smiles':STEREO},str(output))
    tree=ET.parse(output)
    for node in tree.iter('n'):
        x,y=map(float,node.get('p').split()); node.set('p',f'{-x} {y}')
    tree.write(output)
    with pytest.raises(StructureFidelityError):
        repair_and_validate_drawn_cdxml(STEREO,output,repair_stereo=False)

def test_atom_order_does_not_change_validation(tmp_path):
    output=tmp_path/'source.cdxml'
    api.draw_molecule({'smiles':STEREO},str(output))
    tree=ET.parse(output); fragment=tree.find('.//fragment')
    fragment[:]=list(reversed(list(fragment)))
    tree.write(output)
    assert repair_and_validate_drawn_cdxml(STEREO,output,repair_stereo=False)['status']=='preserved'

def test_reaction_wedges_are_semantic_and_multisubstrate_has_plus(tmp_path):
    import yaml
    manifest={'structures':{'A':{'smiles':STEREO},'B':{'smiles':AND}},
        'steps':[{'substrates':['A','B'],'products':['A'],'above_arrow':{'text':['test']}}]}
    output=tmp_path/'reaction.cdxml'
    result=api.render_scheme(yaml_text=yaml.safe_dump(manifest),output_path=str(output))
    assert result['ok']
    expected=[semantic_key(Chem.MolFromSmiles(s)) for s in [STEREO,AND,STEREO]]
    assert [semantic_key(m) for m in read_molecules(output)]==expected
    assert '+' in ''.join(ET.parse(output).getroot().itertext())

def compose(tmp_path,manifest,name='figure'):
    path=tmp_path/(name+'.json'); path.write_text(json.dumps(manifest))
    output=tmp_path/(name+'.cdxml')
    return compose_chemical_figure(str(path),str(output)),output


def test_native_electron_symbols_preserve_molecule_graph(tmp_path):
    _, output=compose(tmp_path,{'objects':[
        {'type':'molecule','smiles':'[Cl-]','position':[50,50]},
        {'type':'symbol','symbol':'LonePair','start':[46,35],'end':[52,37]},
        {'type':'symbol','symbol':'CirclePlus','start':[75,25],'end':[81,31]}]})
    root=ET.parse(output).getroot()
    assert root.find(".//graphic[@SymbolType='LonePair']").get('GraphicType')=='Symbol'
    assert root.find(".//graphic[@SymbolType='CirclePlus']") is not None
    assert semantic_key(read_molecules(output)[0])==semantic_key(Chem.MolFromSmiles('[Cl-]'))
    with pytest.raises(ValueError,match='Unsupported native symbol'):
        compose(tmp_path,{'objects':[{'type':'symbol','symbol':'Unknown','start':[0,0],'end':[5,5]}]},'invalid-symbol')

def test_fixed_figure_roundtrip_unique_ids_and_rich_labels(tmp_path):
    result,output=compose(tmp_path,{'objects':[
        {'id':'A','type':'molecule','smiles':AND,'position':[100,100],'cip_labels':True,'atom_numbers':True},
        {'id':'B','type':'molecule','smiles':STEREO,'position':[300,100],'rotation':180,'highlight_atoms':[0]},
        {'id':'arrow','type':'arrow','start':[170,100],'end':[240,100]},
        {'type':'text','position':[180,75],'runs':[{'text':'H'},{'text':'2','subscript':True},{'text':'O'}]}],
        'steps':[{'reactants':['A'],'products':['B'],'arrows':['arrow']}]})
    assert len(read_molecules(output))==2
    root=ET.parse(output).getroot(); ids=[n.get('id') for n in root.iter() if n.get('id')]
    assert len(set(ids))==len(ids)
    assert root.find(".//s[@face='32']").text=='2'
    assert all(v['status']=='preserved' for v in result['metadata']['chemistry_validation'])

def test_fixed_coordinate_reflection_rewedges_to_preserve_identity(tmp_path):
    mol=Chem.MolFromSmiles(STEREO)
    from rdkit.Chem import rdDepictor
    rdDepictor.Compute2DCoords(mol)
    coords=[
        [-mol.GetConformer().GetAtomPosition(i).x*15,mol.GetConformer().GetAtomPosition(i).y*15] for i in range(mol.GetNumAtoms())]
    _,output=compose(tmp_path,{'objects':[{'type':'molecule','smiles':STEREO,'coordinates':coords}]})
    assert semantic_key(read_molecules(output)[0])==semantic_key(mol)

def test_template_translation_keeps_unknown_native_objects(tmp_path):
    _,source=compose(tmp_path,{'objects':[{'id':'A','type':'molecule','smiles':STEREO}]},'source')
    tree=ET.parse(source); fragment=tree.find('.//fragment')
    ET.SubElement(tree.find('page'),'graphic',{'id':'99999','GraphicType':'Oval','BoundingBox':'1 1 9 9'})
    tree.write(source)
    _,output=compose(tmp_path,{'template_path':str(source),'edits':[{'id':fragment.get('id'),'translate':[40,20]}]},'copy')
    validate_document_preserved(source,output)
    assert ET.parse(output).find(".//graphic[@id='99999']") is not None

@pytest.mark.parametrize('operation,mols',[
    ('inspect',[STEREO]),('stereoisomers',['NC1CCC(O)C1']),
    ('tautomers',['CC(=O)Oc1ccccc1C(=O)O']),('mcs',[STEREO,STEREO]),
    ('r_groups',[STEREO,STEREO])])
def test_workbench_operations(tmp_path,operation,mols):
    output=tmp_path/(operation+'.json')
    result=rdkit_workbench([{'smiles':s} for s in mols],operation,{'max_results':2},str(output))
    data=json.loads(output.read_text()); assert result['ok'] and data['results']
    if operation=='stereoisomers': assert len(data['results'][0]['candidates'])<=2

def test_reference_compare_never_hides_dimension_changes(tmp_path):
    a=tmp_path/'a.png'; b=tmp_path/'b.png'
    Image.new('RGB',(20,20),'white').save(a)
    Image.new('RGB',(20,21),'white').save(b)
    output=tmp_path/'compare.json'
    compare_figure_images(str(a),str(b),str(output))
    result=json.loads(output.read_text())['results'][0]
    assert not result['same_dimensions'] and 'exact_pixels' not in result

def test_publish_rejects_overwrite(tmp_path):
    manifest={'objects':[{'type':'molecule','smiles':STEREO}]}
    _,output=compose(tmp_path,manifest)
    before=output.read_bytes()
    with pytest.raises(Exception): compose(tmp_path,manifest)
    assert output.read_bytes()==before

def test_explicit_cip_edit_has_achieved_configuration_and_diff(tmp_path):
    output=tmp_path/'edited.json'
    rdkit_workbench([{'smiles':STEREO}],'set_stereo',{'configurations':{'1':'R'}},str(output))
    result=json.loads(output.read_text())['results'][0]
    assert result['atoms'][1]['cip']=='R'
    assert result['connectivity_preserved'] and result['diff'][0]['after']=='R'

def test_grid_and_mcs_alignment_preserve_stereo(tmp_path):
    _,output=compose(tmp_path,{'grid':{'columns':2},'objects':[
        {'type':'molecule','smiles':STEREO,'align_to':{'smiles':STEREO},'alignment_mode':'mcs'},
        {'type':'molecule','smiles':AND}]})
    assert [semantic_key(m) for m in read_molecules(output)]==[semantic_key(Chem.MolFromSmiles(s)) for s in [STEREO,AND]]

def test_noop_template_copy_is_byte_identical(tmp_path):
    _,source=compose(tmp_path,{'objects':[{'type':'molecule','smiles':STEREO}]},'source')
    _,copy=compose(tmp_path,{'template_path':str(source)},'copy')
    assert source.read_bytes()==copy.read_bytes()


def test_explicit_cip_rejects_symmetric_atom(tmp_path):
    with pytest.raises(ValueError, match='potential tetrahedral'):
        rdkit_workbench([{'smiles':'CC(O)C'}],'set_stereo',
                        {'configurations':{'1':'R'}},str(tmp_path/'invalid.json'))


@pytest.mark.parametrize('arguments', [{}, {'molecules':[{'smiles':'INVALID'}]},
                                      {'molecules':[], 'unknown':True}])
def test_cli_errors_are_json(tmp_path, capsys, arguments):
    from cdxml_toolkit.mcp_runtime.figure_tools import main
    path=tmp_path/'args.json'
    path.write_text(json.dumps(arguments))
    assert main(['rdkit_workbench','--arguments',str(path)])==1
    result=json.loads(capsys.readouterr().out)
    assert result['ok'] is False and result['error']['type']
