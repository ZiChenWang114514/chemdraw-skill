"""Transactional publication figure projects and their CLI."""
from copy import deepcopy
from pathlib import Path
import argparse
import json
import shutil
import tempfile
import time
from xml.etree import ElementTree as ET

from . import artifact_safety
from ..publication.data import load_records, local_path, sha256, write_json
from ..publication.layout import create_pages, check_pages
from ..publication.update import update_pages


def _native_previews(stage, pages):
    from .mcp_server import _run_worker
    results=[]
    for fmt in ('png','svg'):
        result=_run_worker('render_cdxml_files',(),{
            'input_paths':[str(stage/p['file']) for p in pages],
            'output_dir':str(stage/fmt),'format':fmt,'dpi':144},timeout_seconds=180)
        if not result['ok']:
            return {'status':'unavailable','format':fmt,'error':result.get('error'),
                    'completed_formats':results}
        results.append(fmt)
    return {'status':'rendered_pending_visual_review','formats':results,'dpi':144,
            'renderer':'native_chemdraw_isolated_worker'}


def publication_figure(operation: str, spec_path: str, output_dir: str) -> dict:
    """Create, update, or check editable substrate-scope and SAR figure projects.

    operation is create, update, or check. spec_path is a local JSON file naming
    the CSV/XLSX table, structure source, fields and style. Updates/checks name a
    project_path and optionally edited_pages (zero-based page index to CDXML).
    Output is a new directory. Conflicts produce only a draft and conflict report,
    never a new accepted project. Native PNG/SVG rendering defaults on, through
    isolated locked workers; native failure is reported as pending validation.
    This checks reader consistency and data binding, not experimental chemistry.
    """
    if operation not in {'create','update','check'}:
        raise ValueError('operation must be create, update, or check')
    started=time.monotonic()
    spec_file=Path(spec_path).expanduser().resolve()
    requested=json.loads(spec_file.read_text(encoding='utf-8-sig'))
    if not isinstance(requested,dict):raise ValueError('Specification must be an object')
    target=Path(output_dir).expanduser().resolve()
    if target.exists():raise ValueError('Refusing to overwrite output directory')
    project=None;base_dir=None
    if operation!='create':
        project_file=local_path(spec_file.parent,requested['project_path'])
        project=json.loads(project_file.read_text(encoding='utf-8'))
        if project.get('version')!=1:raise ValueError('Unsupported project version')
        base_dir=project_file.parent
        settings=deepcopy(project['settings'])
        settings.update(requested)
        if 'style' in requested:settings['style']={**project['settings'].get('style',{}),**requested['style']}
        # Altering figure-wide policies during a locked update needs a new create.
        for field in ('fields','mode','style','conditions','footnotes','title'):
            if operation=='update' and field in requested and settings.get(field)!=project['settings'].get(field):
                raise ValueError(f'Changing {field} requires creating a new layout')
        spec=settings
        for page in project['pages']:
            if sha256(base_dir/page['file'])!=page['sha256']:
                raise ValueError('Baseline page was modified; preserve the baseline and supply edited_pages separately')
    else:spec=requested
    if spec.get('mode','scope') not in {'scope','sar'}:raise ValueError('mode must be scope or sar')
    if any(f.get('column')=='label' for f in spec.get('fields',[])):
        raise ValueError('label is reserved for compound labels; select other measurement columns')
    sources={str(spec_file):sha256(spec_file)}
    records=[]
    if operation!='check':
        records,inputs=load_records(spec,spec_file.parent);sources.update(inputs)
    target.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.publication-',dir=target.parent) as temporary:
        stage=Path(temporary)/'result';stage.mkdir()
        conflicts=[];changes=[]
        if operation=='create':
            pages,compounds,warnings=create_pages(records,spec,stage)
            project={'version':1,'mode':spec.get('mode','scope'),'pages':pages,'compounds':compounds,
                     'warnings':warnings,'revision':1}
            roots=[ET.parse(stage/p['file']).getroot() for p in pages]
        elif operation=='update':
            project,roots,conflicts,changes,edited=update_pages(project,base_dir,records,spec,spec_file.parent,stage)
            sources.update(edited);project['revision']+=1
        else:
            roots=[]
            for i,page in enumerate(project['pages']):
                path=local_path(spec_file.parent,spec['edited_pages'][str(i)]) if str(i) in spec.get('edited_pages',{}) else base_dir/page['file']
                sources[str(path)]=sha256(path);roots.append(ET.parse(path).getroot())
                shutil.copy2(path,stage/page['file'])
        checks=check_pages(project,roots,spec)
        if checks['data_binding']['errors']:
            conflicts.extend(checks['data_binding']['errors'])
        # Known scientific disagreements cannot disappear into an ordinary pass.
        checks['chemistry']['unresolved']=spec.get('unresolved_chemistry',project.get('unresolved_chemistry',[]))
        if checks['chemistry']['unresolved']:checks['chemistry']['status']='unresolved'
        if conflicts:
            draft=stage/'draft';draft.mkdir()
            for path in stage.glob('page-*.cdxml'):shutil.move(str(path),str(draft/path.name))
            write_json(stage/'conflicts.json',conflicts)
            checks['native_preview']=_native_previews(draft,project['pages']) if spec.get('native_render',True) else {'status':'not_run'}
            write_json(stage/'checks.json',checks)
            write_json(stage/'changes.json',changes)
            artifact_safety.publish_directory(stage,target)
            return {'ok':False,'status':'conflict','output_dir':str(target),'conflicts':len(conflicts)}
        if spec.get('native_render',True):checks['native_preview']=_native_previews(stage,project['pages'])
        settings={k:v for k,v in spec.items() if k not in {'project_path','edited_pages','atom_maps'}}
        if operation!='check':
            settings['table']=str(local_path(spec_file.parent,spec['table']))
            if settings.get('structure',{}).get('file'):
                settings['structure']=dict(settings['structure'])
                settings['structure']['file']=str(local_path(spec_file.parent,settings['structure']['file']))
        project['settings']=settings
        project['unresolved_chemistry']=checks['chemistry']['unresolved']
        snapshots=stage/'inputs';snapshots.mkdir()
        provenance=[]
        for index,(source,digest) in enumerate(sources.items()):
            if sha256(source)!=digest:raise ValueError('Input changed during generation: '+source)
            dest=snapshots/f'{index:03d}-{Path(source).name}';shutil.copy2(source,dest)
            provenance.append({'source':source,'sha256':digest,'snapshot':str(dest.relative_to(stage))})
        project['inputs']=provenance
        for page in project['pages']:page['sha256']=sha256(stage/page['file'])
        write_json(stage/'project.json',project)
        write_json(stage/'data.json',records if operation!='check' else [r['input'] for r in project['compounds'].values()])
        write_json(stage/'checks.json',checks);write_json(stage/'changes.json',changes)
        elapsed=round(time.monotonic()-started,3)
        write_json(stage/'summary.json',{'operation':operation,'compounds':len(project['compounds']),
                   'pages':len(project['pages']),'duration_seconds':elapsed,'manual_adjustments':None,
                   'note':'Manual adjustment count must be recorded by the reviewer, not inferred.',
                   'native_preview':checks['native_preview']['status']})
        artifact_safety.publish_directory(stage,target)
    status='review_required' if checks['layout']['issues'] or checks['chemistry']['status']=='unresolved' else 'ready_for_visual_review'
    if checks['native_preview']['status'] in {'unavailable','not_run'}:status='pending_native_validation'
    return {'ok':True,'status':status,'output_dir':str(target),'project_path':str(target/'project.json'),
            'pages':len(project['pages']),'compounds':len(project['compounds']),
            'checks':checks,'duration_seconds':round(time.monotonic()-started,3)}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation',choices=('create','update','check'))
    parser.add_argument('--spec',required=True)
    parser.add_argument('--output',required=True)
    args=parser.parse_args(argv)
    result=publication_figure(args.operation,args.spec,args.output)
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return 0 if result['ok'] else 2


if __name__=='__main__':raise SystemExit(main())
