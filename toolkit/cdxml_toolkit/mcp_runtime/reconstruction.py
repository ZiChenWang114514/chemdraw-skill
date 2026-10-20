"""Incremental, evidence-bound reconstruction. CLI only; no automatic stereo guessing."""
from collections import Counter
from copy import deepcopy
import argparse
import hashlib
import json
import math
from pathlib import Path
import shutil
import tempfile
import time
import xml.etree.ElementTree as ET

from rdkit import Chem, rdBase
from ..chemistry_semantics import semantic_key, read_molecules
from . import artifact_safety as safety
from .figure_validation import inspect_document, validate_figure, _worker


def _json(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=True, allow_nan=False)


def _hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _key(value):
    return hashlib.sha256(_json(value).encode()).hexdigest()


def _read(value):
    return json.loads(Path(value).read_text(encoding='utf-8-sig')) if isinstance(value, (str, Path)) else value


def _write(path, value):
    target = safety.resolve_destination(source=None, output_path=path, tag='record', suffix='.json')
    with safety.staging_file(target) as stage:
        stage.write_text(json.dumps(value, indent=2, ensure_ascii=True, allow_nan=False), encoding='utf-8')
        safety.publish_file(stage, target)


def _capture(cdxml, source_image, transform=None, context=None, versions=None):
    """Link raw native objects to chemistry without re-layout or inferred atom mapping."""
    path, image = Path(cdxml).resolve(), Path(source_image).resolve()
    root = ET.parse(path).getroot()
    if root.tag != 'CDXML':
        raise ValueError('Extract/convert native sources to CDXML first')
    if transform is not None:
        if set(transform) != {'scale', 'offset'} or any(len(transform[k]) != 2 for k in transform):
            raise ValueError('transform requires scale=[sx,sy], offset=[x,y]')
        values = transform['scale'] + transform['offset']
        if any(type(x) not in (int, float) or not math.isfinite(x) for x in values) or min(transform['scale']) <= 0:
            raise ValueError('Invalid source coordinate transform')
    scene, atoms, bonds, fragments = {}, {}, {}, []
    def visit(node, address, owner=None, parent=None):
        identity = 'id:' + node.get('id') if node.get('id') else 'path:' + address
        if identity in scene:
            raise ValueError('Duplicate native object ID')
        if node.tag == 'fragment' and owner is None:
            owner = node.get('id')
            if not owner:
                raise ValueError('Top-level fragments need stable IDs')
            fragments.append(owner)
        attributes = {k: v if len(v) <= 1024 else {'sha256': _key(v), 'length': len(v)}
                      for k, v in node.attrib.items()}
        record = dict(tag=node.tag, attributes=attributes, text=node.text or '', owner=owner, parent=parent)
        # Child order can affect reader behavior; retain it as evidence.
        record['children'] = [c.get('id', f'@{i}:{c.tag}') for i, c in enumerate(node)]
        if node.get('p') and transform:
            xy = list(map(float, node.get('p').split()))
            if len(xy) == 2:
                record['source_point'] = [xy[i]*transform['scale'][i]+transform['offset'][i] for i in (0, 1)]
        scene[identity] = record
        if node.tag in ('n', 'b'):
            fields = {'Element','NodeType','Charge','Isotope','NumHydrogens','AS','Geometry',
                      'BondOrdering','ExternalConnectionType','B','E','Order','BS','Display','Display2'}
            destination = atoms if node.tag == 'n' else bonds
            destination[identity] = dict(owner=owner, attributes={k:v for k,v in node.attrib.items() if k in fields})
        for i, child in enumerate(node):
            visit(child, address + '/' + str(i), owner, identity)
    visit(root, '0')
    try:
        inventory = inspect_document(path)
    except Exception as exc:
        inventory = {'status': 'failed', 'error_type': type(exc).__name__, 'reason': str(exc)}
    return dict(version=1, native_path=str(path), native_sha256=_hash(path),
                source_image=str(image), source_sha256=_hash(image), transform=transform,
                context=context or {}, versions=dict(versions or {}, rdkit=rdBase.rdkitVersion),
                fragments=fragments, scene=scene, chemistry={'atoms':atoms, 'bonds':bonds, 'inventory':inventory},
                acceptance='not_evaluated', mapping_scope='native_IDs_within_document_lineage_not_cross_reader_indices')


def _plan(before, after):
    before, after = _read(before), _read(after)
    if before['version'] != 1 or after['version'] != 1:
        raise ValueError('Unsupported snapshot version')
    full = any(before[k] != after[k] for k in ('source_sha256','transform','context','versions'))
    a, b = before['scene'], after['scene']
    changed = sorted(k for k in set(a)|set(b) if a.get(k) != b.get(k))
    chemical = set(after['fragments']) if full else set()
    # Only explicitly understood presentation fields may bypass local chemistry.
    visual_attributes = {'size','font','face','color','Justification','LabelJustification'}
    visual_root = {'LabelSize','CaptionSize','LabelFont','CaptionFont','LabelFace','CaptionFace'}
    for key in changed:
        old, new = a.get(key), b.get(key)
        nodes = [n for n in (old,new) if n]
        owners = {n['owner'] for n in nodes if n['owner']}
        simple = False
        if old and new and all(old.get(k) == new.get(k) for k in ('tag','text','children','owner','parent')):
            delta = {k for k in set(old['attributes'])|set(new['attributes'])
                     if old['attributes'].get(k) != new['attributes'].get(k)}
            simple = (new['tag'] in ('s','t') and delta <= visual_attributes) or (new['tag']=='CDXML' and delta <= visual_root)
        if owners and not simple:
            chemical.update(owners)
        elif not owners and not simple and any(n['tag'] not in ('arrow','curve','font','fonttable','colortable','color') for n in nodes):
            chemical.update(after['fragments'])
    return dict(before_sha256=before['native_sha256'], after_sha256=after['native_sha256'],
                visual_objects=sorted(after['scene']) if full else changed,
                chemical_fragments=sorted(chemical), full_invalidation=full,
                removed_fragments=sorted(set(before['fragments'])-set(after['fragments'])),
                final_full_validation_required=True, acceptance='not_evaluated')


def _cache(action, root, spec, artifact=None, kind='recognition'):
    if kind not in ('recognition','intermediate') or action not in ('store','load'):
        raise ValueError('Cache only recognition/intermediate artifacts, never acceptance')
    required = {'source_image','crop','definitions','parameters','versions','transform'}
    if set(spec) != required or not spec['versions']:
        raise ValueError('Cache needs source, crop, definitions, parameters, versions and transform')
    dependency = dict(spec, source_image=_hash(spec['source_image']), crop=_hash(spec['crop']), kind=kind)
    key = _key(dependency); folder = Path(root).resolve() / key
    if action == 'load':
        try:
            metadata = _read(folder/'record.json')
            path = folder/'artifact'
            if metadata['dependencies'] != dependency or metadata['sha256'] != _hash(path):
                return {'hit':False, 'key':key, 'reason':'integrity_mismatch'}
            return dict(hit=True, key=key, artifact=str(path), acceptance='not_reusable')
        except (OSError, ValueError, KeyError):
            return {'hit':False, 'key':key, 'reason':'missing_or_invalid'}
    if artifact is None:
        raise ValueError('Cache store requires artifact')
    if folder.exists():
        existing = _cache('load', root, spec, kind=kind)
        if existing['hit'] and _hash(existing['artifact']) == _hash(artifact):
            return existing
        raise ValueError('Cache conflict: preserve old evidence and use revised dependencies')
    destination = safety.resolve_directory_destination(source=artifact, output_dir=folder, tag='cache')
    with safety.staging_directory(destination) as stage:
        shutil.copyfile(artifact, stage/'artifact')
        (stage/'record.json').write_text(_json({'dependencies':dependency,'sha256':_hash(stage/'artifact')}),encoding='utf-8')
        safety.publish_directory(stage, destination)
    return dict(hit=False, stored=True, key=key, artifact=str(destination/'artifact'), acceptance='not_reusable')


def _attempt(previous, issue_id, passed, difference, artifact_sha256):
    state = deepcopy(_read(previous)) if previous else {'issues':{}}
    if not issue_id or type(passed) is not bool or not difference or not artifact_sha256:
        raise ValueError('Attempt needs issue, boolean result, concrete difference and artifact hash')
    item = state['issues'].setdefault(issue_id, {'attempts':[], 'status':'pending'})
    if item['status'] in ('needs_review','resolved'):
        raise ValueError('Issue is closed to automatic retries; preserve it and obtain a reviewed correction')
    item['attempts'].append({'passed':passed,'difference':difference,'artifact_sha256':artifact_sha256})
    item['status'] = 'resolved' if passed else ('needs_review' if len(item['attempts']) >= 2 else 'retry_local')
    return state


def _compile(template, output_path, edits):
    from .figure_tools import compose_chemical_figure
    with tempfile.TemporaryDirectory(prefix='cdxml-replay-') as folder:
        manifest = Path(folder)/'manifest.json'
        manifest.write_text(_json({'template_path':str(Path(template).resolve()),'edits':edits}),encoding='utf-8')
        return compose_chemical_figure(str(manifest), output_path)


def _map_reuse(reference, candidate):
    """Require unique full-graph correspondence; never transfer coordinates or stereo."""
    left,right=read_molecules(Path(reference)),read_molecules(Path(candidate))
    if len(left)!=1 or len(right)!=1: raise ValueError('Map one complete molecule at a time')
    a,b=left[0],right[0]
    if a.GetNumAtoms()!=b.GetNumAtoms() or a.GetNumBonds()!=b.GetNumBonds():
        return {'status':'needs_review','reason':'partial_graph_reuse_not_automatic'}
    aa,bb=Chem.Mol(a),Chem.Mol(b)
    Chem.RemoveStereochemistry(aa);Chem.RemoveStereochemistry(bb)
    if Chem.MolToSmiles(aa)!=Chem.MolToSmiles(bb):
        return {'status':'needs_review','reason':'different_graph_or_atom_properties'}
    matches=bb.GetSubstructMatches(aa,uniquify=False,useChirality=False,maxMatches=257)
    if len(matches)!=1:
        return {'status':'needs_review','reason':'no_unique_full_graph_mapping','mapping_count_bounded':len(matches)}
    changes=[]
    for i,j in enumerate(matches[0]):
        x,y=a.GetAtomWithIdx(i),b.GetAtomWithIdx(j)
        before=x.GetProp('_CIPCode') if x.HasProp('_CIPCode') else None
        after=y.GetProp('_CIPCode') if y.HasProp('_CIPCode') else None
        if before!=after: changes.append({'reference_index':i,'candidate_index':j,'before':before,'after':after})
    return dict(status='mapped_requires_difference_review',atom_mapping=list(enumerate(matches[0])),
                stereo_changes=changes,reference_sha256=_hash(reference),candidate_sha256=_hash(candidate),
                coordinates_transferred=False,source_identity='not_evaluated')


def _local(snapshot, plan, output_dir, native=True, cross_reader=True):
    snapshot, plan = _read(snapshot), _read(plan)
    path = Path(snapshot['native_path'])
    if _hash(path) != snapshot['native_sha256'] or plan['after_sha256'] != snapshot['native_sha256']:
        raise ValueError('Stale snapshot/plan')
    if _hash(snapshot['source_image']) != snapshot['source_sha256']:
        raise ValueError('Source changed')
    root = ET.parse(path).getroot()
    target = safety.resolve_directory_destination(source=path, output_dir=output_dir, tag='local-check')
    results = []
    with safety.staging_directory(target) as stage:
        for i, fid in enumerate(plan['chemical_fragments']):
            matches = [n for n in root.iter('fragment') if n.get('id') == fid]
            if not matches:
                results.append({'fragment_id':fid,'status':'removed_requires_full_inventory'}); continue
            doc = ET.Element('CDXML',root.attrib)
            for tag in ('fonttable','colortable'):
                if root.find(tag) is not None: doc.append(deepcopy(root.find(tag)))
            ET.SubElement(doc,'page').append(deepcopy(matches[0]))
            fragment_path = stage/f'fragment-{i}.cdxml'
            ET.ElementTree(doc).write(fragment_path,encoding='UTF-8',xml_declaration=True)
            validate_figure(str(fragment_path),str(stage/f'check-{i}'),native=native,cross_reader=cross_reader)
            check = _read(stage/f'check-{i}/report.json')
            # The fragment is part of the published bundle, not an external source.
            # Resolve this reference from report.json, including after a directory move.
            check['source'] = f'../fragment-{i}.cdxml'
            check['source_reference_base'] = 'report_directory'
            (stage/f'check-{i}/report.json').write_text(_json(check), encoding='utf-8')
            results.append({'fragment_id':fid,'report':f'check-{i}/report.json',
                            'native':check['native'].get('status'),'cross_reader':check['cross_reader'].get('status')})
        result = {'results':results,'checked_fragments':len(results),'final_full_validation_required':True}
        (stage/'local.json').write_text(_json(result),encoding='utf-8')
        safety.publish_directory(stage,target)
    return dict(result, output_dir=str(target))


def _overlay(source, candidate, output_dir, offset):
    from PIL import Image, ImageOps
    import numpy as np
    if len(offset) != 2 or any(type(x) is not int for x in offset):
        raise ValueError('Offset must be two integer pixels')
    def load(path):
        with Image.open(path) as raw:
            rgba = ImageOps.exif_transpose(raw).convert('RGBA')
            return Image.alpha_composite(Image.new('RGBA',rgba.size,'white'),rgba).convert('RGB')
    a, b = load(source), load(candidate); x, y = offset
    if x < 0 or y < 0 or x+b.width > a.width or y+b.height > a.height:
        raise ValueError('Alignment would clip pixels; resizing is not allowed')
    canvas = Image.new('RGB',a.size,'white'); canvas.paste(b,(x,y))
    aa, bb = np.asarray(a), np.asarray(canvas)
    ia, ib = aa.min(axis=2)<240, bb.min(axis=2)<240
    rgb = np.full_like(aa,255)
    rgb[ia & ib] = (40,40,40); rgb[ia & ~ib] = (230,40,130); rgb[ib & ~ia] = (0,150,210)
    result = dict(source_sha256=_hash(source), candidate_sha256=_hash(candidate), offset=offset,
                  scale=1, exact_pixels=bool(np.array_equal(aa,bb)),
                  ink_iou=float((ia & ib).sum()/max(1,(ia | ib).sum())),
                  normalized_mae=float(np.abs(aa.astype(float)-bb).mean()/255),
                  legend={'shared':'dark','source_only':'magenta','candidate_only':'cyan'},
                  chemical_acceptance='not_evaluated', visual_review='pending')
    target=safety.resolve_directory_destination(source=source,output_dir=output_dir,tag='overlay')
    with safety.staging_directory(target) as stage:
        Image.fromarray(rgb).save(stage/'overlay.png')
        (stage/'comparison.json').write_text(_json(result),encoding='utf-8')
        safety.publish_directory(stage,target)
    return result


def _target(molecules, provenance, reviewed):
    if reviewed is not True or not str(provenance).strip() or not molecules:
        raise ValueError('A target requires explicit source review and provenance')
    rows=[]; labels=set()
    for item in molecules:
        if not item.get('label') or item['label'] in labels:
            raise ValueError('Target labels must be unique')
        labels.add(item['label']); mol=Chem.MolFromSmiles(item['smiles'])
        if mol is None: raise ValueError('Invalid target molecule')
        rows.append(dict(label=item['label'],smiles=item['smiles'],semantic_key=semantic_key(mol)))
    return dict(version=1,molecules=rows,provenance=provenance,reviewed=True,
                scope='declared_source_review_not_independent_experimental_confirmation')


def _against_target(report, target):
    report, target = _read(report), _read(target)
    validated=_target(target['molecules'],target['provenance'],target['reviewed'])
    expected=Counter(x['semantic_key'] for x in validated['molecules'])
    result={}
    for reader in ('rdkit','chemscript'):
        actual=[]
        for row in report['cross_reader'].get('fragments',[]):
            mol=Chem.MolFromSmiles(row.get(reader+'_smiles',''))
            if mol is not None and mol.GetNumAtoms(): actual.append(semantic_key(mol))
        result[reader+'_matches_target']=Counter(actual)==expected
    return result


def _verify_variants(source_cdxml, compatible_cdxml, target_record, output_dir):
    """Fresh full native validation of both variants against a frozen reviewed target."""
    target_record=_read(target_record)
    _target(target_record['molecules'],target_record['provenance'],target_record['reviewed'])
    destination=safety.resolve_directory_destination(source=source_cdxml,output_dir=output_dir,tag='dual')
    # Use the final location: worker receipts must not retain a moved staging path.
    destination.mkdir()
    started=time.perf_counter(); results={}
    (destination/'target.json').write_text(_json(target_record),encoding='utf-8')
    for variant, path in [('source',source_cdxml),('compatible',compatible_cdxml)]:
        copy=destination/(variant+'.cdxml'); shutil.copyfile(path,copy)
        validate_figure(str(copy),str(destination/(variant+'-validation')),native=True,cross_reader=True)
        report=_read(destination/(variant+'-validation')/'report.json')
        matches=_against_target(report,target_record)
        native=report['native'].get('comparison',{}).get('semantic_inventory_preserved',False)
        required=matches['chemscript_matches_target'] and (variant=='source' or matches['rdkit_matches_target'])
        # A source-oriented depiction can have explicitly disclosed reader differences.
        render=_worker('render_cdxml_files',{'input_paths':[str(copy)],'output_dir':str(destination/(variant+'-render')),'format':'png','dpi':144})
        (destination/(variant+'-render-receipt.json')).write_text(_json(render),encoding='utf-8')
        results[variant]=dict(matches,native_preserved=native,sha256=_hash(copy),
                             validation_sha256=_hash(destination/(variant+'-validation')/'report.json'),
                             render_receipt_sha256=_hash(destination/(variant+'-render-receipt.json')),
                             cross_reader_status=report['cross_reader']['status'],
                             chemistry_gate=bool(native and required and report['source_unchanged']),
                             render_ok=render.get('ok',False),visual_review='pending')
    ready=all(row['chemistry_gate'] and row['render_ok'] for row in results.values())
    result=dict(variants=results,target_sha256=_hash(destination/'target.json'),
                elapsed_seconds=time.perf_counter()-started,
                acceptance='pending_visual_review' if ready else 'blocked_chemistry_or_native',
                output_dir=str(destination),source_identity='requires_source_review')
    (destination/'verification.json').write_text(_json(result),encoding='utf-8')
    return result


def _finalize(package_dir, review_record):
    """Bind explicit visual/source review to the exact fresh verification artifacts."""
    folder=Path(package_dir).resolve(); review=_read(review_record)
    verification=_read(folder/'verification.json')
    if review.get('verification_sha256')!=_hash(folder/'verification.json') or not review.get('reviewer'):
        raise ValueError('Review must name a reviewer and bind the current verification hash')
    if _hash(review['source_image'])!=review.get('source_sha256'):
        raise ValueError('Source image changed since review')
    if _hash(folder/'target.json')!=verification['target_sha256']:
        raise ValueError('Target changed after validation')
    files=[]
    for variant in ('source','compatible'):
        result=verification['variants'][variant]; visual=review.get('variants',{}).get(variant,{})
        if not result['chemistry_gate'] or not result['render_ok']:
            raise ValueError('Chemical/native gates not passed: '+variant)
        if any(visual.get(k) is not True for k in ('graph_checked','stereo_checked','text_checked','whole_figure_checked')):
            raise ValueError('Source/visual review incomplete: '+variant)
        if visual.get('status') not in ('reviewed','reviewed_with_differences') or not isinstance(visual.get('differences'),list):
            raise ValueError('Explicit visual status and differences required')
        if visual['status']=='reviewed' and visual['differences']:
            raise ValueError('Visual differences must be disclosed in status')
        for name, key in [(variant+'.cdxml','sha256'),(variant+'-validation/report.json','validation_sha256'),
                          (variant+'-render-receipt.json','render_receipt_sha256')]:
            if _hash(folder/name)!=result[key]: raise ValueError('Validated artifact changed: '+name)
            files.append({'path':name,'sha256':result[key]})
        receipt=_read(folder/(variant+'-render-receipt.json'))
        receipt=receipt.get('result',receipt)
        if receipt.get('metadata',{}).get('renderer')!='ChemDraw COM':
            raise ValueError('Native renderer receipt missing')
        rendered=receipt.get('outputs',{}).get('rendered',[])
        evidence={str(Path(a['path']).resolve()):a['sha256'] for a in receipt.get('metadata',{}).get('artifacts',[])}
        if len(rendered)!=1 or _hash(rendered[0])!=visual.get('preview_sha256') or evidence.get(str(Path(rendered[0]).resolve()))!=visual['preview_sha256']:
            raise ValueError('Preview does not match native receipt and review')
        files.append({'path':str(Path(rendered[0]).resolve().relative_to(folder)),'sha256':visual['preview_sha256']})
    return dict(status='accepted_with_declared_limits',variants=verification['variants'],review=review,files=files,
                scope='reviewed_source_and_saved_reader_consistency_not_experimental_confirmation',
                pixel_exact_claim=False)


def _benchmark(baseline, candidate):
    baseline,candidate=_read(baseline),_read(candidate)
    required=('fixture_sha256','model','versions','acceptance_contract')
    comparable=all(baseline.get(k) and baseline.get(k)==candidate.get(k) for k in required)
    comparable=comparable and baseline.get('accepted') is True and candidate.get('accepted') is True
    times=[baseline.get('elapsed_seconds'),candidate.get('elapsed_seconds')]
    valid=all(type(x) in (int,float) and math.isfinite(x) and x>0 for x in times)
    return dict(comparable=bool(comparable and valid),speedup=times[0]/times[1] if comparable and valid else None,
                baseline=baseline,candidate=candidate,
                scope='matched_replay_only_not_unseen_image_accuracy',
                missing_usage_is_unknown=True)


def main():
    """Execute one file-based reconstruction operation; print a compact evidence pointer."""
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--arguments',required=True)
    args=parser.parse_args(); values=_read(args.arguments)
    operation=values.pop('operation'); result_path=values.pop('result_path',None)
    handlers={'capture':_capture,'plan':_plan,'cache':_cache,'attempt':_attempt,'compile':_compile,
              'local':_local,'overlay':_overlay,'target':_target,'verify_variants':_verify_variants,
              'benchmark':_benchmark,'map_reuse':_map_reuse,'finalize':_finalize}
    if operation not in handlers: raise ValueError('Unknown operation')
    # Preflight the report destination before any operation with side effects.
    if result_path and Path(result_path).exists(): raise ValueError('Refusing existing result_path')
    if not result_path and operation in ('capture','plan','target','attempt','benchmark','map_reuse','finalize'):
        raise ValueError('This operation requires result_path for its full record')
    result=handlers[operation](**values)
    if result_path: _write(result_path,result)
    print(_json({'operation':operation,'result_path':result_path,
                 'output_dir':result.get('output_dir'),'status':'produced_not_accepted'}))


if __name__=='__main__':
    main()
