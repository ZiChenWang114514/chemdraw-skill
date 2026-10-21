"""Complete-file validation, with optional isolated native save-cycle checks."""
from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

from rdkit import Chem
from rdkit.Chem import rdMolDescriptors
from ..chemistry_semantics import read_molecules, semantic_key
from ..chemistry_diff import structural_diff
from . import artifact_safety


def inspect_document(path):
    path = Path(path)
    root = ET.parse(path).getroot()
    if root.tag != 'CDXML': raise ValueError('Expected CDXML root')
    ids = {}
    for n in root.iter():
        if n.get('id'):
            if n.get('id') in ids: raise ValueError('Duplicate object ID')
            ids[n.get('id')] = n
    for n in root.iter():
        for attr in ('B','E','CrossingBonds','BondOrdering','object'):
            for ref in n.get(attr,'').split():
                if attr == 'BondOrdering' and ref == '0': continue  # implicit ligand
                if ref not in ids: raise ValueError(f'Dangling {attr} reference: {ref}')
        if n.tag == 'b':
            if any(ids.get(n.get(k)) is None or ids[n.get(k)].tag != 'n' for k in ('B','E')):
                raise ValueError('Bond reference must target an atom')
    molecules = []
    for m in read_molecules(path):
        molecules.append(dict(smiles=Chem.MolToSmiles(m), cxsmiles=Chem.MolToCXSmiles(m),
            connectivity=Chem.MolToSmiles(m,isomericSmiles=False),
            semantic_key=semantic_key(m), formula=rdMolDescriptors.CalcMolFormula(m),
            formal_charge=Chem.GetFormalCharge(m),
            # H vertices (including isotopes) plus implicit/bracket H counts.
            # includeNeighbors=False avoids counting explicit H vertices twice.
            hydrogen_count=sum(int(a.GetAtomicNum()==1)+a.GetTotalNumHs(includeNeighbors=False)
                               for a in m.GetAtoms()),
            radical_electrons=sum(a.GetNumRadicalElectrons() for a in m.GetAtoms()),
            assigned_centers=sum(c!='?' for _,c in Chem.FindMolChiralCenters(m,includeUnassigned=True))))
    return dict(status='passed', sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                object_count=len(ids), molecule_count=len(molecules), molecules=molecules)


def compare_inventories(a,b):
    old,new = a['molecules'],b['molecules']
    connectivity = Counter(x['connectivity'] for x in old)==Counter(x['connectivity'] for x in new)
    semantic = Counter(x['semantic_key'] for x in old)==Counter(x['semantic_key'] for x in new)
    composition = Counter((x['formula'],x['formal_charge']) for x in old)==Counter(
        (x['formula'],x['formal_charge']) for x in new)
    pairs=[];available=list(new)
    for x in old:
        matches=[y for y in available if y['connectivity']==x['connectivity']]
        if not matches: continue
        exact=next((y for y in matches if y['semantic_key']==x['semantic_key']),None)
        if exact is None and len(matches)>1:
            pairs.append({'status':'partial','reason':'ambiguous_species_pairing'});continue
        y=exact or matches[0];available.remove(y)
        diff=structural_diff(x['smiles'],y['smiles'])
        pairs.append({'before_smiles':x['smiles'],'after_smiles':y['smiles'],
            'assigned_center_count_delta':y['assigned_centers']-x['assigned_centers'],'comparison':diff})
    return dict(status='preserved' if semantic else 'changed',
                connectivity_preserved=connectivity, semantic_inventory_preserved=semantic,
                composition_preserved=composition,
                molecules=pairs, scope='reader_consistency_not_source_identity')


def _worker(name,kwargs):
    # Reuse the registered process boundary, timeouts, and native resource lock.
    from .mcp_server import _run_worker
    return _run_worker(name, [], kwargs)


def validate_figure(input_path: str, output_dir: str, native: bool = False,
                    cross_reader: bool = False) -> dict:
    """Write a diagnostic directory without changing the source. CLI-only operation.

    native performs CDXML -> CDX -> CDXML through registered isolated workers.
    cross_reader additionally reads saved native fragments directly with ChemScript.
    A completed report can contain failed/unavailable checks; inspect its statuses.
    """
    if cross_reader and not native: raise ValueError('cross_reader requires native=True')
    source=artifact_safety.validate_input_file(input_path,suffixes=('.cdxml',))
    target=artifact_safety.resolve_directory_destination(source=source,output_dir=output_dir,tag='figure-validation')
    initial=inspect_document(source)
    report=dict(source=str(source),basic=initial,source_identity='not_evaluated',
                native={'status':'not_run'},cross_reader={'status':'not_run'},visual_review='not_run')
    with artifact_safety.staging_directory(target) as stage:
        if native:
            cdx=stage/'native.cdx';saved=stage/'native.cdxml'
            first=_worker('convert_cdx_cdxml',{'input_path':str(source),'output_path':str(cdx)})
            second=_worker('convert_cdx_cdxml',{'input_path':str(cdx),'output_path':str(saved)}) if first.get('ok') else None
            if second and second.get('ok'):
                try:
                    observed=inspect_document(saved)
                    report['native']=dict(status='completed',saved=observed,
                                          comparison=compare_inventories(initial,observed))
                except Exception as exc:
                    report['native']={'status':'failed','reason':'saved_file_validation_failed',
                                      'error_type':type(exc).__name__,'validation':'not_completed'}
                if cross_reader and report['native']['status']=='completed':
                    try:
                        report['cross_reader']=_cross_reader(saved,stage)
                    except Exception as exc:
                        report['cross_reader']={'status':'unavailable','error_type':type(exc).__name__}
                elif cross_reader:
                    report['cross_reader']={'status':'not_run','reason':'saved_file_validation_failed'}
            else:
                failed=second or first
                report['native']={'status':'failed','error':failed.get('error',{}),
                                  'validation':'not_completed'}
                if cross_reader: report['cross_reader']={'status':'not_run','reason':'native_save_failed'}
        report['source_unchanged']=hashlib.sha256(source.read_bytes()).hexdigest()==initial['sha256']
        if not report['source_unchanged']: raise ValueError('Source changed during validation')
        (stage/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
        artifact_safety.publish_directory(stage,target)
    return artifact_safety.with_artifacts({'ok':True,'output_dir':str(target),
        'report':str(target/'report.json'),'validation_status':report['native']['status']},[target/'report.json'])


def _cross_reader(saved,stage):
    from .resource_lock import native_resource_lock
    root=ET.parse(saved).getroot();parents={c:p for p in root.iter() for c in p}
    fragments=[n for n in root.iter('fragment') if parents[n].tag!='n']
    results=[]
    for i,fragment in enumerate(fragments):
        doc=ET.Element('CDXML',root.attrib)
        for tag in ('fonttable','colortable'):
            if root.find(tag) is not None: doc.append(deepcopy(root.find(tag)))
        page=ET.SubElement(doc,'page');page.append(deepcopy(fragment))
        path=stage/f'fragment-{i}.cdxml';ET.ElementTree(doc).write(path,encoding='UTF-8',xml_declaration=True)
        original=inspect_document(path)
        with native_resource_lock('chemdraw_com', timeout_seconds=120):
            result=_worker('compare_molecules',{'molecule_a':str(path),'molecule_b':str(path)})
        if not result.get('ok'):
            results.append({'fragment_id':fragment.get('id'),'status':'unavailable','error':result.get('error')});continue
        value=result.get('result',{}).get('outputs',{})
        smiles=value.get('molecule_a',{}).get('canonical_smiles')
        if not smiles or len(original['molecules'])!=1:
            results.append({'fragment_id':fragment.get('id'),'status':'unresolved'});continue
        before=original['molecules'][0]['smiles'];diff=structural_diff(before,smiles)
        identical=diff['status']=='completed' and diff['method']=='canonical_identity'
        results.append({'fragment_id':fragment.get('id'),'status':'consistent' if identical else 'different',
                        'rdkit_smiles':before,'chemscript_smiles':smiles,'comparison':diff})
    return {'status':'consistent' if results and all(x['status']=='consistent' for x in results) else 'unresolved',
            'method':'direct_saved_CDXML_fragments_no_MOL_intermediate','fragments':results}
