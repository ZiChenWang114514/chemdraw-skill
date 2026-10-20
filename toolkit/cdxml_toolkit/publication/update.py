"""Three-way updates preserving native objects; ambiguous edits become conflicts."""
from copy import deepcopy
from pathlib import Path
import math
import statistics
import tempfile
from xml.etree import ElementTree as ET
from rdkit import Chem
from rdkit.Chem import rdDepictor, rdFMCS
from ..chemistry_semantics import semantic_key
from ..mcp_runtime.figure_tools import compose_chemical_figure
from .data import field_text, local_path, write_json
from .layout import fragment_mol, node_text, bounds, wrap, style_settings, create_pages


def matching_group(root, record):
    ids=record['objects']; candidates=list(root.iter('group'))
    direct=[g for g in candidates if g.get('id')==ids['group']]
    def identity(group):
        fragments=group.findall('fragment')
        if len(fragments)!=1: return None
        try: return semantic_key(fragment_mol(fragments[0]))
        except ValueError: return None
    if len(direct)==1:
        group=direct[0]
        # IDs alone are insufficient: native saves may renumber or recycle them.
        label=group.find(f"t[@id='{ids['label']}']")
        same_identity=identity(group)==record['displayed_identity']
        unique_identity=same_identity and sum(identity(g)==record['displayed_identity'] for g in candidates)==1
        if unique_identity or node_text(label)==record['display']['label']:
            return group
    matches=[g for g in candidates if identity(g)==record['displayed_identity']
             and any(node_text(t)==record['display']['label'] for t in g.findall('t'))]
    return matches[0] if len(matches)==1 else None


def match_objects(group, record):
    ids=record['objects']; result={'group':group.get('id'),'fields':{}}
    fragments=group.findall('fragment')
    if len(fragments)!=1: raise ValueError('compound group must contain exactly one chemical fragment')
    result['fragment']=fragments[0].get('id')
    used=set()
    for field,oid in {'label':ids['label'],**ids['fields']}.items():
        matches=[t for t in group.findall('t') if t.get('id')==oid]
        # With renumbered groups do not trust old child IDs.
        if group.get('id')!=ids['group'] or len(matches)!=1:
            matches=[t for t in group.findall('t') if node_text(t)==record['display'][field]]
        if len(matches)!=1 or matches[0].get('id') in used:
            raise ValueError(f'Cannot uniquely match field {field}')
        found=matches[0].get('id');used.add(found)
        if field=='label':result['label']=found
        else:result['fields'][field]=found
    return result


def replace_text(node, old, new):
    """Preserve unchanged rich runs; single-run labels retain all their style."""
    runs=list(node.findall('s'))
    if not runs: raise ValueError('Text object has no editable runs')
    if len(runs)==1:
        runs[0].text=new; return
    # Preserve the common prefix and suffix across styled runs. Style the changed
    # span with its original first run; do not flatten unrelated styled text.
    prefix=0
    while prefix<min(len(old),len(new)) and old[prefix]==new[prefix]:prefix+=1
    suffix=0
    while suffix<min(len(old)-prefix,len(new)-prefix) and old[-suffix-1]==new[-suffix-1]:suffix+=1
    end=len(old)-suffix; chunks=[]; offset=0; inserted=False
    for run in runs:
        value=run.text or ''; stop=offset+len(value)
        if offset<prefix:
            copy=deepcopy(run);copy.text=value[:max(0,min(len(value),prefix-offset))]
            if copy.text:chunks.append(copy)
        if not inserted and stop>=prefix:
            copy=deepcopy(run);copy.text=new[prefix:len(new)-suffix if suffix else len(new)]
            if copy.text:chunks.append(copy)
            inserted=True
        if stop>end:
            copy=deepcopy(run);copy.text=value[max(0,end-offset):]
            if copy.text:chunks.append(copy)
        offset=stop
    for run in runs:node.remove(run)
    for run in chunks:node.append(run)


def replacement_fragment(old_fragment,new_smiles,atom_map,stage,root,cid):
    old=fragment_mol(old_fragment);new=Chem.MolFromSmiles(new_smiles)
    mcs=rdFMCS.FindMCS([old,new],timeout=5,ringMatchesRingOnly=True,completeRingsOnly=True)
    if mcs.canceled or mcs.numAtoms<3: raise ValueError('No usable core; supply a new layout explicitly')
    query=Chem.MolFromSmarts(mcs.smartsString)
    if atom_map is None:
        a=old.GetSubstructMatches(query,uniquify=False,maxMatches=128)
        b=new.GetSubstructMatches(query,uniquify=False,maxMatches=128)
        mappings={tuple(zip(i,j)) for i in a for j in b}
        if len(mappings)!=1:
            raise ValueError('Symmetric core mapping; supply atom_maps[compound_id] as old/new zero-based pairs')
        pairs=list(next(iter(mappings)))
    else:
        pairs=[tuple(map(int,p)) for p in atom_map]
        if len(pairs)<3 or len({a for a,b in pairs})!=len(pairs) or len({b for a,b in pairs})!=len(pairs):
            raise ValueError('atom_map must contain at least three unique pairs')
        for a,b in pairs:
            if a<0 or a>=old.GetNumAtoms() or b<0 or b>=new.GetNumAtoms() or old.GetAtomWithIdx(a).GetAtomicNum()!=new.GetAtomWithIdx(b).GetAtomicNum():
                raise ValueError('atom_map has invalid indices or element mismatch')
        for a,b in pairs:
            for c,d in pairs:
                left,right=old.GetBondBetweenAtoms(a,c),new.GetBondBetweenAtoms(b,d)
                if (left is None)!=(right is None) or (left and left.GetBondType()!=right.GetBondType()):
                    raise ValueError('atom_map does not preserve core bonds')
    # RDKit's CDXML reader can expose fixed-point rather than point units.
    # Recover a uniform transform and validate EVERY coordinate against the file.
    native=[list(map(float,n.get('p').split()))[:2] for n in old_fragment.iter('n') if n.get('p')]
    conf=old.GetConformer()
    parsed=[(conf.GetAtomPosition(i).x,-conf.GetAtomPosition(i).y) for i in range(old.GetNumAtoms())]
    spans=[max(p[i] for p in parsed)-min(p[i] for p in parsed) for i in (0,1)]
    axis=spans.index(max(spans))
    if spans[axis]<1e-8:raise ValueError('Degenerate core coordinates')
    scale=(max(p[axis] for p in native)-min(p[axis] for p in native))/spans[axis]
    offset=[min(p[i] for p in native)-scale*min(p[i] for p in parsed) for i in (0,1)]
    points=[[scale*p[i]+offset[i] for i in (0,1)] for p in parsed]
    if any(not any(math.dist(p,n)<.03 for n in native) for p in points):
        raise ValueError('Cannot verify CDXML coordinate transform for this structure')
    lengths=[math.dist(points[b.GetBeginAtomIdx()],points[b.GetEndAtomIdx()]) for b in old.GetBonds()]
    bond_scale=statistics.median(lengths)/1.5
    if bond_scale<1e-6:raise ValueError('Degenerate bond lengths')
    for i,(x,y) in enumerate(points):conf.SetAtomPosition(i,(x/bond_scale,-y/bond_scale,0))
    rdDepictor.GenerateDepictionMatching2DStructure(new,old,atomMap=pairs)
    conf=new.GetConformer()
    coords=[[conf.GetAtomPosition(i).x*bond_scale,-conf.GetAtomPosition(i).y*bond_scale] for i in range(new.GetNumAtoms())]
    manifest=Path(stage)/'replacement.json'; target=Path(stage)/'replacement.cdxml'
    # The temporary workspace is private; remove previous intermediate only.
    if target.exists(): target.unlink()
    write_json(manifest,{'objects':[{'type':'molecule','smiles':new_smiles,'coordinates':coords}]})
    compose_chemical_figure(str(manifest),str(target))
    fragment=ET.parse(target).find('.//fragment')
    next_id=max([int(n.get('id','0')) for n in root.iter() if n.get('id','0').isdigit()]+[1000])+1
    mapping={n.get('id'):str(next_id+i) for i,n in enumerate(fragment.iter()) if n.get('id')}
    for node in fragment.iter():
        if node.get('id'):node.set('id',mapping[node.get('id')])
        for attr in ('B','E','BondOrdering','CrossingBonds'):
            if node.get(attr):node.set(attr,' '.join(mapping.get(v,v) for v in node.get(attr).split()))
    # Reuse existing font table and native atom-label style.
    old_run=old_fragment.find('.//s')
    if old_run is not None:
        for run in fragment.iter('s'):
            for attr in ('font','size','face','color'):
                if old_run.get(attr):run.set(attr,old_run.get(attr))
    return fragment, {'atom_map':pairs,'old_identity':semantic_key(old),'new_identity':semantic_key(new)}


def update_pages(base_project,base_dir,records,spec,spec_dir,stage):
    project=deepcopy(base_project);style=style_settings(spec)
    roots=[];sources={};conflicts=[];changes=[]
    from .data import sha256
    for index,page in enumerate(project['pages']):
        supplied=spec.get('edited_pages',{}).get(str(index))
        path=local_path(spec_dir,supplied) if supplied else Path(base_dir)/page['file']
        sources[str(path)]=sha256(path);roots.append(ET.parse(path).getroot())
    incoming={r['compound_id']:r for r in records}; consumed=set(); matched=set()
    for cid,record in list(project['compounds'].items()):
        root=roots[record['page']]; group=matching_group(root,record); new=incoming.get(cid)
        if group is None:
            if new is None:
                del project['compounds'][cid];changes.append({'compound_id':cid,'change':'deleted'});continue
            conflicts.append({'compound_id':cid,'page':record['page']+1,'reason':'missing_or_ambiguous_group'});continue
        native_key=(record['page'],group.get('id'))
        if native_key in matched:
            conflicts.append({'compound_id':cid,'reason':'group_matched_more_than_once'});continue
        matched.add(native_key)
        try: ids=match_objects(group,record)
        except ValueError as exc:
            conflicts.append({'compound_id':cid,'reason':str(exc)});continue
        old_input=record['input']; fragment=group.find(f"fragment[@id='{ids['fragment']}']")
        identity=semantic_key(fragment_mol(fragment))
        current={field:node_text(group.find(f"t[@id='{oid}']")) for field,oid in {'label':ids['label'],**ids['fields']}.items()}
        manual=identity!=record['displayed_identity'] or current!=record['display']
        if new is None:
            if manual:
                conflicts.append({'compound_id':cid,'reason':'delete_conflicts_with_manual_content_edit'});continue
            parent=next(p for p in root.iter() if group in list(p));parent.remove(group)
            del project['compounds'][cid];changes.append({'compound_id':cid,'change':'deleted'});continue
        consumed.add(cid)
        if new['group']!=old_input['group']:
            conflicts.append({'compound_id':cid,'reason':'group_change_requires_explicit_relayout'});continue
        record['objects']=ids;record['locked']=True
        # Each side is compared to its own baseline (input vs displayed text).
        desired={'label':new['label'],**{f['column']:field_text(new,f) for f in spec.get('fields',[])}}
        for field,oid in {'label':ids['label'],**ids['fields']}.items():
            upstream_changed=(new['label']!=old_input['label']) if field=='label' else new['values'][field]!=old_input['values'][field]
            node=group.find(f"t[@id='{oid}']")
            if upstream_changed:
                value=wrap(desired[field],max(40,record['bbox'][2]-record['bbox'][0]-12),style)
                if current[field]!=record['display'][field] and current[field]!=value:
                    conflicts.append({'compound_id':cid,'field':field,'reason':'both_sides_changed',
                                      'baseline':record['display'][field],'manual':current[field],'incoming':value});continue
                replace_text(node,current[field],value)
                changes.append({'compound_id':cid,'field':field,'change':'data_updated'})
            elif current[field]!=record['display'][field]:
                changes.append({'compound_id':cid,'field':field,'change':'manual_text_preserved'})
            record['display'][field]=node_text(node)
        if new['identity']!=old_input['identity']:
            if identity!=record['displayed_identity'] and identity!=new['identity']:
                conflicts.append({'compound_id':cid,'reason':'both_sides_changed_structure'});continue
            if identity!=new['identity']:
                try:
                    with tempfile.TemporaryDirectory(prefix='.replacement-',dir=stage) as work:
                        replacement,diff=replacement_fragment(fragment,new['smiles'],spec.get('atom_maps',{}).get(cid),work,root,cid)
                except ValueError as exc:
                    conflicts.append({'compound_id':cid,'reason':str(exc)});continue
                index=list(group).index(fragment);group.remove(fragment);group.insert(index,replacement)
                record['objects']['fragment']=replacement.get('id');identity=new['identity']
                changes.append({'compound_id':cid,'change':'structure_replaced','diff':diff})
        elif identity!=record['displayed_identity']:
            changes.append({'compound_id':cid,'change':'manual_structure_preserved'})
        record['displayed_identity']=identity; record['input']=new
        all_bounds=[bounds(n,style) for n in group if n.tag in {'t','fragment'}]
        all_bounds=[b for b in all_bounds if b]
        if all_bounds:record['bbox']=[min(b[0] for b in all_bounds),min(b[1] for b in all_bounds),max(b[2] for b in all_bounds),max(b[3] for b in all_bounds)]
    additions=[r for r in records if r['compound_id'] not in base_project['compounds']]
    if additions:
        pages,compounds,warnings=create_pages(additions,spec,stage,start_index=len(roots))
        project['pages'].extend(pages);project['compounds'].update(compounds)
        roots.extend(ET.parse(Path(stage)/p['file']).getroot() for p in pages)
        changes.extend({'compound_id':r['compound_id'],'change':'added_on_new_page'} for r in additions)
    for index,root in enumerate(roots):
        ET.ElementTree(root).write(Path(stage)/project['pages'][index]['file'],encoding='utf-8',xml_declaration=True)
    return project,roots,conflicts,changes,sources
