import json
from pathlib import Path
import xml.etree.ElementTree as ET

import pytest
from PIL import Image

from cdxml_toolkit.mcp_runtime import reconstruction as r


@pytest.fixture
def drawing(tmp_path):
    image = tmp_path / 'source.png'
    Image.new('RGB', (100, 100), 'white').save(image)
    doc = tmp_path / 'source.cdxml'
    doc.write_text('<CDXML><page id="1"><fragment id="2"><n id="3" p="10 10"/>'
                   '<n id="4" p="20 10"/><b id="5" B="3" E="4"/></fragment>'
                   '<t id="6" p="30 30"><s size="10">conditions</s></t></page></CDXML>')
    return image, doc


def capture(drawing, **kwargs):
    image, doc = drawing
    return r._capture(str(doc), str(image), transform={'scale': [2, 2], 'offset': [0, 0]}, **kwargs)


def test_linked_records_preserve_ids_and_source_location(drawing):
    record = capture(drawing)
    assert record['scene']['id:3']['source_point'] == [20, 20]
    assert record['chemistry']['atoms']['id:3']['owner'] == '2'
    assert record['chemistry']['bonds']['id:5']['attributes']['B'] == '3'
    assert record['acceptance'] == 'not_evaluated'


@pytest.mark.parametrize('attribute,value', [('p', '11 10'), ('NumHydrogens', '0'),
    ('Charge', '1'), ('AS', 'R'), ('LabelDisplay', 'Left')])
def test_atom_changes_require_chemical_readback(drawing, attribute, value):
    before = capture(drawing)
    tree = ET.parse(drawing[1]); tree.find('.//n').set(attribute, value); tree.write(drawing[1])
    plan = r._plan(before, capture(drawing))
    assert plan['chemical_fragments'] == ['2']
    assert plan['final_full_validation_required']


def test_font_only_change_stays_local(drawing):
    before = capture(drawing)
    tree = ET.parse(drawing[1]); tree.find('.//s').set('size', '11'); tree.write(drawing[1])
    plan = r._plan(before, capture(drawing))
    assert not plan['chemical_fragments']
    assert plan['visual_objects']


def test_shared_definition_text_triggers_review(drawing):
    before=capture(drawing)
    tree=ET.parse(drawing[1]);tree.find('.//s').text='R = Et';tree.write(drawing[1])
    assert r._plan(before,capture(drawing))['chemical_fragments']==['2']


def test_symmetric_reuse_is_not_an_arbitrary_atom_mapping(drawing):
    assert r._map_reuse(str(drawing[1]),str(drawing[1]))['status']=='needs_review'


def test_source_changed_invalidates_local_plan(drawing,tmp_path):
    snapshot=capture(drawing);plan=r._plan(snapshot,snapshot)
    drawing[0].write_bytes(b'changed')
    with pytest.raises(ValueError,match='Source changed'):
        r._local(snapshot,plan,str(tmp_path/'local'))


def test_reversed_wedge_is_not_a_matching_target():
    target=r._target([{'label':'A','smiles':'F[C@H](Cl)Br'}],'reviewed fixture',True)
    report={'cross_reader':{'fragments':[{'rdkit_smiles':'F[C@@H](Cl)Br',
            'chemscript_smiles':'F[C@@H](Cl)Br'}]}}
    assert not r._against_target(report,target)['rdkit_matches_target']


def test_local_visual_plan_does_not_call_native(drawing,tmp_path,monkeypatch):
    before=capture(drawing)
    tree=ET.parse(drawing[1]);tree.find('.//s').set('size','12');tree.write(drawing[1])
    after=capture(drawing);plan=r._plan(before,after)
    def forbidden(*args,**kwargs): raise AssertionError('Unnecessary native chemical call')
    monkeypatch.setattr(r,'validate_figure',forbidden)
    result=r._local(after,plan,str(tmp_path/'local'))
    assert result['checked_fragments']==0


def test_local_report_source_survives_publication_and_directory_move(drawing, tmp_path):
    before = capture(drawing)
    tree = ET.parse(drawing[1]); tree.find('.//n').set('p', '11 10'); tree.write(drawing[1])
    after = capture(drawing)
    folder = tmp_path / 'local'
    r._local(after, r._plan(before, after), str(folder), native=False, cross_reader=False)
    moved = tmp_path / 'moved'
    folder.rename(moved)
    report_path = moved / 'check-0/report.json'
    report = json.loads(report_path.read_text())
    assert not Path(report['source']).is_absolute()
    source = (report_path.parent / report['source']).resolve()
    assert source == moved / 'fragment-0.cdxml'
    assert source.is_file()
    assert r._hash(source) == report['basic']['sha256']


def test_bond_display_and_crossing_changes_are_chemical(drawing):
    before = capture(drawing)
    tree = ET.parse(drawing[1]); tree.find('.//b').set('Display', 'WedgeBegin'); tree.write(drawing[1])
    assert r._plan(before, capture(drawing))['chemical_fragments'] == ['2']


def test_context_change_invalidates_same_pixels(drawing):
    a = capture(drawing, context={'R': 'Me'})
    b = capture(drawing, context={'R': 'Et'})
    assert r._plan(a, b)['full_invalidation']


def test_unknown_root_change_is_conservative(drawing):
    before = capture(drawing)
    tree = ET.parse(drawing[1]); tree.getroot().set('UnknownStereoOption', 'yes'); tree.write(drawing[1])
    assert r._plan(before, capture(drawing))['chemical_fragments'] == ['2']


def test_cache_checks_dependencies_and_bytes(drawing, tmp_path):
    image, doc = drawing
    spec = dict(source_image=str(image), crop=str(image), definitions={'R': 'Me'},
                parameters={}, versions={'recognizer': 'test'}, transform={'scale': 1})
    put = r._cache('store', str(tmp_path / 'cache'), spec, str(doc))
    assert r._cache('load', str(tmp_path / 'cache'), spec)['hit']
    other = dict(spec, definitions={'R': 'Et'})
    assert not r._cache('load', str(tmp_path / 'cache'), other)['hit']
    other = dict(spec, versions={'recognizer': 'other'})
    assert not r._cache('load', str(tmp_path / 'cache'), other)['hit']
    Path(put['artifact']).write_text('corrupt')
    assert not r._cache('load', str(tmp_path / 'cache'), spec)['hit']
    with pytest.raises(ValueError):
        r._cache('store', str(tmp_path / 'cache'), spec, str(doc), kind='acceptance')


def test_two_failed_repairs_require_review():
    a = r._attempt(None, 'bridge', False, 'missing center', 'hash1')
    b = r._attempt(a, 'bridge', False, 'opposite center', 'hash2')
    assert b['issues']['bridge']['status'] == 'needs_review'
    with pytest.raises(ValueError):
        r._attempt(b, 'bridge', True, 'try again', 'hash3')


def test_overlay_does_not_resize_or_clip(drawing, tmp_path):
    out = tmp_path / 'overlay'
    result = r._overlay(str(drawing[0]), str(drawing[0]), str(out), [0, 0])
    assert result['exact_pixels']
    assert Image.open(out / 'overlay.png').size == (100, 100)
    with pytest.raises(ValueError):
        r._overlay(str(drawing[0]), str(drawing[0]), str(tmp_path / 'bad'), [1, 0])


def test_verified_target_is_not_reader_agreement():
    target = r._target([{'label': 'A', 'smiles': 'CCO'}], 'reviewed reference', True)
    report = {'cross_reader': {'fragments': [{'status': 'consistent',
               'rdkit_smiles': 'CCN', 'chemscript_smiles': 'CCN'}]}}
    check = r._against_target(report, target)
    assert not check['rdkit_matches_target']
    assert not check['chemscript_matches_target']


def test_target_requires_explicit_review():
    with pytest.raises(ValueError):
        r._target([{'label': 'A', 'smiles': 'CCO'}], '', False)


def test_exact_replay_preserves_native_objects(drawing, tmp_path):
    out = tmp_path / 'copy.cdxml'
    result = r._compile(str(drawing[1]), str(out), [])
    assert out.read_bytes() == drawing[1].read_bytes()
    assert result['metadata']['native_objects'] == 'byte_identical'


def test_benchmark_refuses_unmatched_conditions():
    base = {'fixture_sha256': 'a', 'model': 'm', 'versions': {'v': '1'},
            'acceptance_contract': 'dual', 'accepted': True, 'elapsed_seconds': 10}
    assert r._benchmark(base, dict(base, elapsed_seconds=5))['speedup'] == 2
    assert r._benchmark(base, dict(base, model='other'))['speedup'] is None


def test_crossing_wrong_connectivity_cannot_match_target():
    target=r._target([{'label':'A','smiles':'CCCC'}],'reviewed open chain',True)
    report={'cross_reader':{'fragments':[{'rdkit_smiles':'C1CCC1','chemscript_smiles':'C1CCC1'}]}}
    assert not r._against_target(report,target)['chemscript_matches_target']


def test_abbreviation_hydrogen_loss_cannot_match_target():
    target=r._target([{'label':'A','smiles':'CCN'}],'reviewed NH2 group',True)
    report={'cross_reader':{'fragments':[{'rdkit_smiles':'CC[NH]','chemscript_smiles':'CC[NH]'}]}}
    assert not r._against_target(report,target)['rdkit_matches_target']


def test_duplicate_species_multiplicity_is_checked():
    target=r._target([{'label':'A','smiles':'CCO'},{'label':'B','smiles':'CCO'}],'two source structures',True)
    report={'cross_reader':{'fragments':[{'rdkit_smiles':'CCO','chemscript_smiles':'CCO'}]}}
    assert not r._against_target(report,target)['rdkit_matches_target']


def test_cli_capture_is_compact_and_refuses_existing_result(drawing,tmp_path):
    import subprocess,sys
    args=tmp_path/'args.json';out=tmp_path/'snapshot.json'
    args.write_text(json.dumps({'operation':'capture','cdxml':str(drawing[1]),
        'source_image':str(drawing[0]),'result_path':str(out)}))
    command=[sys.executable,'-m','cdxml_toolkit.mcp_runtime.reconstruction','--arguments',str(args)]
    result=subprocess.run(command,capture_output=True,text=True)
    assert result.returncode==0,result.stderr
    assert len(result.stdout)<1024
    original=out.read_bytes()
    assert subprocess.run(command,capture_output=True).returncode!=0
    assert out.read_bytes()==original


def test_finalization_requires_bound_review(tmp_path):
    (tmp_path/'verification.json').write_text('{}')
    with pytest.raises(ValueError,match='bind'):
        r._finalize(str(tmp_path),{'reviewer':'tester','verification_sha256':'old'})


@pytest.mark.parametrize('name,key',[('source-oriented.cdxml','source_variant'),('reconstruction.cdxml','compatible_variant')])
def test_published_dual_variant_bytes(name,key):
    case=Path(__file__).resolve().parents[2]/'assets/readme/stereo-reconstruction'
    evidence=r._read(case/'incremental-verification.json')
    assert r._hash(case/name)==evidence[key]['sha256']


def test_variant_gate_does_not_treat_report_creation_as_acceptance(drawing,tmp_path,monkeypatch):
    target=r._target([{'label':'A','smiles':'CC'}],'reviewed synthetic ethane',True)
    def failed_native(path,output_dir,**kwargs):
        folder=Path(output_dir);folder.mkdir()
        (folder/'report.json').write_text(json.dumps({'native':{'status':'failed'},'source_unchanged':True,
            'cross_reader':{'status':'unavailable','fragments':[]}}))
    monkeypatch.setattr(r,'validate_figure',failed_native)
    monkeypatch.setattr(r,'_worker',lambda *args,**kwargs:{'ok':True})
    result=r._verify_variants(str(drawing[1]),str(drawing[1]),target,str(tmp_path/'dual'))
    assert result['acceptance']=='blocked_chemistry_or_native'


def test_finalization_rechecks_artifacts_and_requires_both_profiles(drawing,tmp_path):
    package=tmp_path/'package';package.mkdir()
    (package/'target.json').write_text('{}')
    verification={'target_sha256':r._hash(package/'target.json'),'variants':{}}
    review={'reviewer':'test fixture','source_image':str(drawing[0]),'source_sha256':r._hash(drawing[0]),'variants':{}}
    for variant in ('source','compatible'):
        document=package/(variant+'.cdxml');document.write_bytes(drawing[1].read_bytes())
        validation=package/(variant+'-validation');validation.mkdir();(validation/'report.json').write_text('{}')
        preview=package/(variant+'.png');preview.write_bytes(drawing[0].read_bytes())
        receipt=package/(variant+'-render-receipt.json')
        receipt.write_text(json.dumps({'metadata':{'renderer':'ChemDraw COM','artifacts':[{'path':str(preview),'sha256':r._hash(preview)}]},'outputs':{'rendered':[str(preview)]}}))
        verification['variants'][variant]={'chemistry_gate':True,'render_ok':True,'sha256':r._hash(document),
            'validation_sha256':r._hash(validation/'report.json'),'render_receipt_sha256':r._hash(receipt)}
        review['variants'][variant]={'graph_checked':True,'stereo_checked':True,'text_checked':True,
            'whole_figure_checked':True,'status':'reviewed','differences':[],'preview_sha256':r._hash(preview)}
    (package/'verification.json').write_text(json.dumps(verification))
    review['verification_sha256']=r._hash(package/'verification.json')
    assert r._finalize(str(package),review)['status']=='accepted_with_declared_limits'
    (package/'source.cdxml').write_text('modified')
    with pytest.raises(ValueError,match='artifact changed'):
        r._finalize(str(package),review)
    (package/'source.cdxml').write_bytes(drawing[1].read_bytes())
    verification['variants']['source']['chemistry_gate']=False
    (package/'verification.json').write_text(json.dumps(verification))
    review['verification_sha256']=r._hash(package/'verification.json')
    with pytest.raises(ValueError,match='gates not passed'):
        r._finalize(str(package),review)
