"""Regression checks for scientific drawing and numerical analysis contracts."""
import json
from pathlib import Path
import xml.etree.ElementTree as ET
import numpy as np
import pytest
from cdxml_toolkit.scientific.tlc import draw_tlc, measure_rf
from cdxml_toolkit.scientific.spectra import analyze_spectrum
from cdxml_toolkit.scientific.apparatus import draw_apparatus


def test_variable_substituent_uses_native_generic_node():
    from rdkit import Chem
    from rdkit.Chem import rdDepictor
    from cdxml_toolkit.image.structure_from_image import _rdkit_mol_to_atom_bond_dicts
    from cdxml_toolkit.render.renderer import _build_fragment, _IDGen
    from cdxml_toolkit.chemistry_semantics import validate_fragment
    mol=Chem.MolFromSmiles('*NCC');rdDepictor.Compute2DCoords(mol)
    atoms,bonds=_rdkit_mol_to_atom_bond_dicts(mol)
    xml,_,_=_build_fragment(atoms,bonds,_IDGen())
    root=ET.fromstring(xml)
    generic=root.find("n[@NodeType='GenericNickname']")
    assert generic is not None and generic.get('GenericNickname')=='R'
    assert not any(n.get('Element')=='0' for n in root.iter('n'))
    assert validate_fragment('*NCC',xml)['status']=='preserved'

def test_rf_geometry_and_invalid_calibration():
    assert measure_rf([0,100],[0,0],[2,75]) == pytest.approx(.25)
    assert measure_rf([0,0],[100,0],[75,3]) == pytest.approx(.75)
    with pytest.raises(ValueError):measure_rf([0,0],[0,0],[1,2])
    with pytest.raises(ValueError):measure_rf([0,100],[0,0],[0,-20])

def test_native_tlc_retains_lane_and_rf(tmp_path):
    p=tmp_path/'tlc.cdxml'
    draw_tlc({'lanes':[{'label':'Starting material','spots':[{'rf':.2}]},{'label':'Product','spots':[{'rf':.7}]}]},p)
    r=ET.parse(p).getroot()
    assert len(r.findall('.//tlclane'))==2
    assert [float(n.get('Rf')) for n in r.findall('.//tlcspot')]==[.2,.7]
    with pytest.raises(ValueError, match="overwrite"):draw_tlc({'lanes':[{'spots':[]}]},p)

def test_tlc_rejects_unphysical_rf_and_nan(tmp_path):
    for rf in [-.1,1.1,float('nan')]:
        with pytest.raises(ValueError):draw_tlc({'lanes':[{'spots':[{'rf':rf}]}]},tmp_path/'bad.cdxml')
    assert not (tmp_path/'bad.cdxml').exists()

def test_spectrum_integral_independent_of_ppm_direction(tmp_path):
    x=np.linspace(0,10,10001); y=1/(1+((x-3)/.03)**2)+2/(1+((x-7)/.03)**2)
    results=[]
    for descending in [False,True]:
        p=tmp_path/f'{descending}.csv';np.savetxt(p,np.c_[x[::-1],y[::-1]] if descending else np.c_[x,y],delimiter=',',header='ppm,intensity',comments='')
        results.append(analyze_spectrum(p,{'prominence':.2,'integration_regions':[[2,4],[6,8]],'normalization_region':0,'normalization_value':1}))
    assert results[0]['integrals'][1]['normalized']==pytest.approx(2,rel=.002)
    assert results[0]['integrals']==results[1]['integrals']
    assert len(results[0]['peaks'])==2
    assert results[0]['assignments']=='not_performed'

def test_spectrum_rejects_duplicate_axis(tmp_path):
    p=tmp_path/'bad.csv';p.write_text('ppm,intensity\n1,2\n1,3\n2,4\n')
    with pytest.raises(ValueError):analyze_spectrum(p,{})


@pytest.mark.parametrize('options',[
    {'baseline_windows':[[0,2]],'baseline_degree':1.5},
    {'baseline_windows':[[float('nan'),2]]},
    {'baseline_windows':[[-1,2]]},
    {'baseline_windows':[[0,1,2]]},
    {'integration_regions':[[0,1]],'normalization_region':True},
    {'prominance':0.5},
])
def test_spectrum_rejects_ambiguous_processing_options(tmp_path,options):
    p=tmp_path/'s.csv';np.savetxt(p,np.c_[np.linspace(0,2,100),np.ones(100)],delimiter=',',header='ppm,intensity',comments='')
    with pytest.raises(ValueError):analyze_spectrum(p,options)


def test_spectrum_records_normalization_provenance(tmp_path):
    p=tmp_path/'s.csv';np.savetxt(p,np.c_[np.linspace(0,2,100),np.ones(100)],delimiter=',',header='ppm,intensity',comments='')
    result=analyze_spectrum(p,{'integration_regions':[[0,1]],'normalization_region':0,'normalization_value':3})
    assert result['processing']['normalization']=={'region':0,'value':3.0,'denominator_area':1.0}

def test_native_apparatus_preserves_objects_and_remaps_references(tmp_path):
    template=tmp_path/'source.cdxml'
    template.write_text('<CDXML><page id="1"><group id="2" BoundingBox="10 10 30 50"><graphic id="3" GraphicType="Line" SupersededBy="4" BoundingBox="10 10 30 50"/><arrow id="4" Tail3D="10 10 0" Head3D="30 50 0"/></group></page></CDXML>')
    spec={'template_files':{'native':str(template)},'components':[{'id':'a','template':'native','page':0,'position':[100,100],'ports':{'out':[.5,1]}},{'id':'b','template':'native','page':0,'attach':{'port':'in','to':'a.out'},'ports':{'in':[.5,0]}}]}
    result=draw_apparatus(spec,tmp_path/'setup.cdxml')
    assert result['ports']['a.out']==result['ports']['b.in']
    root=ET.parse(tmp_path/'setup.cdxml').getroot()
    ids=[n.get('id') for n in root.iter() if n.get('id')]
    assert len(ids)==len(set(ids))
    assert len(root.findall('.//arrow'))==2
    for n in root.findall('.//graphic'):assert n.get('SupersededBy') in ids
    with pytest.raises(ValueError):draw_apparatus({'components':[{'id':'x','kind':'flask'}]},tmp_path/'bad.cdxml')


def test_mechanism_anchor_tracks_bond_midpoint_and_validates_indices():
    from cdxml_toolkit.scientific.mechanism import compile_mechanism
    spec={'objects':[{'type':'molecule','id':'m','smiles':'CBr','coordinates':[[10,10],[30,10]]}],
          'electron_arrows':[{'source':{'molecule':'m','bond':[0,1]},'target':{'molecule':'m','atom':1},'controls':[[15,30],[30,30]],'electrons':2}]}
    out=compile_mechanism(spec)
    assert out['objects'][-1]['points'][0]==[20,10]
    spec['objects'][0]['coordinates']=[[20,20],[40,20]]
    assert compile_mechanism(spec)['objects'][-1]['points'][0]==[30,20]
    spec['electron_arrows'][0]['target']['atom']=5
    with pytest.raises(ValueError):compile_mechanism(spec)


def test_complete_mechanism_step_checks_atoms_charge_and_isotopes():
    from cdxml_toolkit.scientific.mechanism import validate_mechanism_steps
    from rdkit import Chem
    molecules={k:Chem.MolFromSmiles(s) for k,s in {'a':'[Cl-]','b':'CBr','c':'CCl','d':'[Br-]','neutral':'[Br]','heavy':'[37Cl-]'}.items()}
    step={'reactants':['a','b'],'products':['c','d'],'complete':True}
    assert validate_mechanism_steps([step],molecules)[0]['status']=='balanced'
    with pytest.raises(ValueError,match='not balanced'):
        validate_mechanism_steps([{**step,'products':['c']}],molecules)
    with pytest.raises(ValueError,match='not balanced'):
        validate_mechanism_steps([{**step,'products':['c','neutral']}],molecules)
    with pytest.raises(ValueError,match='not balanced'):
        validate_mechanism_steps([{**step,'reactants':['heavy','b']}],molecules)
    assert validate_mechanism_steps([{**step,'complete':False,'products':['c']}],molecules)[0]['status']=='not_checked_incomplete_step'

def test_plot_envelope_keeps_narrow_peaks():
    from cdxml_toolkit.scientific.plots import envelope_indices
    y=np.zeros(10000);y[7777]=9
    indices=envelope_indices(y,1000)
    assert 7777 in indices
    assert indices[0]==0 and indices[-1]==len(y)-1
    assert len(indices)<=1000

def test_rendered_ion_label_includes_visible_charge_and_isotope():
    from cdxml_toolkit.render.renderer import _build_fragment, _IDGen
    atoms=[{'index':0,'x':0,'y':0,'symbol':'Cl','atomic_number':17,'num_hydrogens':0,'charge':-1,'isotope':37}]
    xml,_,_=_build_fragment(atoms,[],_IDGen())
    root=ET.fromstring(xml)
    runs=root.findall('.//s')
    assert ''.join(s.text or '' for s in runs)=='37Cl-'
    assert runs[0].get('face')=='64' and runs[-1].get('face')=='64'

def test_tlc_native_dimensions_are_fixed_point(tmp_path):
    p=tmp_path/'plate.cdxml';draw_tlc({'lanes':[{'spots':[{'rf':.5,'width':8,'height':5,'tail':2}]}]},p)
    spot=ET.parse(p).find('.//tlcspot')
    assert int(spot.get('Width'))==8*65536
    assert int(spot.get('Height'))==5*65536
    assert int(spot.get('Tail'))==2*65536
