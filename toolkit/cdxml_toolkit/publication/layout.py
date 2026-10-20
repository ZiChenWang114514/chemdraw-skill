"""Measured page layout and native editable compound groups."""
from collections import Counter
from copy import deepcopy
from pathlib import Path
import math
from xml.etree import ElementTree as ET
from PIL import ImageFont
from rdkit import Chem
from rdkit.Chem import rdDepictor, rdFMCS
from ..chemistry_semantics import read_molecules, semantic_key, document_inventory
from ..mcp_runtime.figure_tools import compose_chemical_figure, _move
from .data import field_text, write_json


def style_settings(spec):
    style = {'width_mm':180, 'height_mm':240, 'font_size':8, 'bond_length':14.4,
             'font':'Arial', **spec.get('style',{})}
    if not 60 <= float(style['width_mm']) <= 400 or not 60 <= float(style['height_mm']) <= 500:
        raise ValueError('Figure width/height must be 60..400 / 60..500 mm')
    if not 7 <= float(style['font_size']) <= 24 or not 10 <= float(style['bond_length']) <= 40:
        raise ValueError('Use 7..24 pt text and 10..40 pt bonds')
    return style


def font_for(style, size=None):
    size = size or style['font_size']
    name = style.get('font','Arial')
    for candidate in (name+'.ttf', name.lower()+'.ttf', 'DejaVuSans.ttf'):
        try:
            return ImageFont.truetype(candidate, round(float(size)*8))
        except OSError:
            pass
    return ImageFont.load_default()


def text_width(value, style, size=None):
    font = font_for(style,size)
    return max((font.getlength(line)/8 for line in str(value).splitlines()), default=0)


def wrap(value, width, style):
    lines=[]
    for paragraph in str(value).split('\n'):
        line=''
        for char in paragraph:
            if line and text_width(line+char,style)>width:
                lines.append(line.rstrip()); line=''
            line+=char
        lines.append(line)
    return '\n'.join(lines)


def fragment_mol(fragment):
    molecules=read_molecules('<CDXML><page>'+ET.tostring(fragment,encoding='unicode')+'</page></CDXML>')
    mol=molecules[0]
    for other in molecules[1:]: mol=Chem.CombineMols(mol,other)
    return mol


def node_text(node):
    return ''.join(s.text or '' for s in node.iter('s')) if node is not None else ''


def molecule_coordinates(mol, bond_length, reference=None):
    mol=Chem.Mol(mol)
    warning=None
    if reference is not None:
        mcs=rdFMCS.FindMCS([reference,mol],timeout=3,ringMatchesRingOnly=True,completeRingsOnly=True)
        if mcs.canceled or mcs.numAtoms<3:
            rdDepictor.Compute2DCoords(mol)
            warning='No usable common core; independently depicted'
        else:
            query=Chem.MolFromSmarts(mcs.smartsString)
            pairs=list(zip(reference.GetSubstructMatch(query),mol.GetSubstructMatch(query)))
            rdDepictor.GenerateDepictionMatching2DStructure(mol,reference,atomMap=pairs)
    else:
        rdDepictor.Compute2DCoords(mol)
    scale=float(bond_length)/1.5
    conf=mol.GetConformer()
    xy=[(conf.GetAtomPosition(i).x*scale,-conf.GetAtomPosition(i).y*scale) for i in range(mol.GetNumAtoms())]
    return mol,xy,warning


def prepare(records,spec):
    style=style_settings(spec); size=style['font_size']
    usable=style['width_mm']*72/25.4-32
    refs={}; prepared=[]; warnings=[]
    by_id={r['compound_id']:r for r in records}
    for record in records:
        group=record['group']; ref_id=spec.get('core_by_group',{}).get(group)
        if group not in refs and ref_id:
            if ref_id not in by_id: raise ValueError(f'Unknown reference compound: {ref_id}')
            ref=Chem.MolFromSmiles(by_id[ref_id]['smiles']); rdDepictor.Compute2DCoords(ref); refs[group]=ref
        mol,xy,warning=molecule_coordinates(Chem.MolFromSmiles(record['smiles']),style['bond_length'],refs.get(group))
        refs.setdefault(group,mol)
        if warning: warnings.append({'compound_id':record['compound_id'],'message':warning})
        xs,ys=zip(*xy); molecule_width=max(xs)-min(xs)+size*4
        if molecule_width>usable:
            raise ValueError(f"Structure {record['compound_id']} exceeds figure width at requested bond length")
        texts={'label':record['label'],**{f['column']:field_text(record,f) for f in spec.get('fields',[])}}
        width=max(100,molecule_width,min(usable,max(text_width(v,style)+16 for v in texts.values())))
        width=min(width,usable)
        texts={k:wrap(v,width-12,style) for k,v in texts.items()}
        height=max(ys)-min(ys)+size*4+sum((v.count('\n')+1)*size*1.45+4 for v in texts.values())+8
        coords=[[x-min(xs)+size*2,y-min(ys)+size*2] for x,y in xy]
        prepared.append({'input':record,'coords':coords,'texts':texts,'width':width,'height':height,
                         'molecule_bottom':max(y for x,y in coords)})
    return prepared,warnings


def create_pages(records,spec,stage,start_index=0):
    style=style_settings(spec); prepared,warnings=prepare(records,spec)
    width=style['width_mm']*72/25.4; height=style['height_mm']*72/25.4
    margin=16; gap=12; size=style['font_size']; pages=[]; compounds={}
    # Keep first-occurrence group order, and preserve row order within each group.
    groups=list(dict.fromkeys(p['input']['group'] for p in prepared))
    arranged=[p for group in groups for p in prepared if p['input']['group']==group]
    manifests=[]; current=None; x=y=row_height=0; last_group=None
    footer='\n'.join(spec.get('footnotes',[]))
    footer=wrap(footer,width-2*margin,style) if footer else ''
    bottom=height-margin-((footer.count('\n')+1)*size*1.5+8 if footer else 0)
    def new_page():
        index=start_index+len(manifests)
        title=spec.get('title', 'Substrate scope' if spec.get('mode','scope')=='scope' else 'Structure–activity relationships')
        title=wrap(title,width-2*margin,style)
        conditions=wrap(spec.get('conditions',''),width-2*margin,style)
        objects=[{'type':'text','id':'title','text':title,'position':[margin,margin+size],'size':size}]
        top=margin+(title.count('\n')+1)*size*1.5+8
        if conditions:
            objects.append({'type':'text','id':'conditions','text':conditions,'position':[margin,top+size],'size':size})
            top+=(conditions.count('\n')+1)*size*1.5+8
        if footer: objects.append({'type':'text','id':'footnotes','text':footer,'position':[margin,bottom+size+8],'size':size})
        current={'index':index,'objects':objects,'entries':[],'top':top}
        manifests.append(current)
        return current,margin,top,0
    for p in arranged:
        group=p['input']['group']
        if current is None: current,x,y,row_height=new_page()
        if group!=last_group:
            if x!=margin: y+=row_height+gap
            x=margin; row_height=0
            if y+p['height']+size*2>bottom: current,x,y,row_height=new_page()
            if group:
                heading=wrap(group,width-2*margin,style)
                current['objects'].append({'type':'text','text':heading,'position':[margin,y+size],'size':size})
                y+=(heading.count('\n')+1)*size*1.5+8
            last_group=group
        if x+p['width']>width-margin:
            x=margin; y+=row_height+gap; row_height=0
        if y+p['height']>bottom:
            current,x,y,row_height=new_page()
            if group:
                heading=wrap(group+' (continued)',width-2*margin,style)
                current['objects'].append({'type':'text','text':heading,'position':[margin,y+size],'size':size})
                y+=(heading.count('\n')+1)*size*1.5+8
        if y+p['height']>bottom: raise ValueError(f"Compound {p['input']['compound_id']} exceeds page height")
        key=f'c{len(compounds)}'; cid=p['input']['compound_id']
        objects=[{'type':'molecule','id':key+'_mol','smiles':p['input']['smiles'],
                  'coordinates':[[a+x,b+y] for a,b in p['coords']]}]
        ty=y+p['molecule_bottom']+size*2.6
        for field,value in p['texts'].items():
            objects.append({'type':'text','id':key+'_'+field,'text':value,'position':[x+6,ty],'size':size})
            ty+=(value.count('\n')+1)*size*1.45+4
        current['objects'].extend(objects)
        entry={'key':key,'cid':cid,'bbox':[x,y,x+p['width'],y+p['height']]}
        current['entries'].append(entry)
        compounds[cid]={'input':p['input'],'page':current['index'],'bbox':entry['bbox'],
                        'display':p['texts'],'locked':False}
        x+=p['width']+gap; row_height=max(row_height,p['height'])
    stage=Path(stage)
    for page in manifests:
        name=f"page-{page['index']+1:03d}.cdxml"
        manifest=stage/f"page-{page['index']+1:03d}.manifest.json"
        write_json(manifest,{'style':{k:style[k] for k in ('font','font_size','bond_length')},'objects':page['objects']})
        result=compose_chemical_figure(str(manifest),str(stage/name))
        tree=ET.parse(stage/name); root=tree.getroot(); native_page=root.find('page')
        root.set('BoundingBox',f'0 0 {width:g} {height:g}')
        native_page.set('BoundingBox',f'0 0 {width:g} {height:g}')
        native_page.set('WidthPages','1');native_page.set('HeightPages','1')
        ids=result['metadata']['object_ids']
        next_id=max(int(n.get('id','0')) for n in root.iter())+1
        for entry in page['entries']:
            record=compounds[entry['cid']]; key=entry['key']
            group=ET.SubElement(native_page,'group',{'id':str(next_id)});next_id+=1
            object_ids={'group':group.get('id'),'fragment':ids[key+'_mol'],'label':ids[key+'_label'],
                        'fields':{f['column']:ids[key+'_'+f['column']] for f in spec.get('fields',[])}}
            for oid in [object_ids['fragment'],object_ids['label'],*object_ids['fields'].values()]:
                node=next(n for n in native_page if n.get('id')==oid)
                native_page.remove(node);group.append(node)
            record['objects']=object_ids
            record['displayed_identity']=semantic_key(fragment_mol(group.find('fragment')))
        tree.write(stage/name,encoding='utf-8',xml_declaration=True)
        pages.append({'file':name,'width_pt':width,'height_pt':height})
    return pages,compounds,warnings


def bounds(node, style):
    if node.tag=='t':
        coords=list(map(float,node.get('p','0 0').split()))
        size=max([float(s.get('size',style['font_size'])) for s in node.findall('s')]+[style['font_size']])
        text=node_text(node); width=text_width(text,style,size)
        left=coords[0]
        if node.get('Justification')=='Center': left-=width/2
        elif node.get('Justification')=='Right':left-=width
        return [left,coords[1]-size,left+width,coords[1]+max(0,text.count('\n'))*size*1.5+size*.3]
    points=[]
    for n in node.iter('n'):
        if n.get('p'): points.append(list(map(float,n.get('p').split()))[:2])
    if not points: return None
    pad=style['font_size']*1.2
    return [min(p[0] for p in points)-pad,min(p[1] for p in points)-pad,
            max(p[0] for p in points)+pad,max(p[1] for p in points)+pad]


def overlap(a,b):
    return min(a[2],b[2])-max(a[0],b[0])>1 and min(a[3],b[3])-max(a[1],b[1])>1


def check_pages(project, roots, spec):
    style=style_settings(spec); issues=[]; errors=[]
    expected=[Counter() for _ in roots]; boxes=[[] for _ in roots]
    for cid,record in project['compounds'].items():
        index=record['page']; root=roots[index]; ids=record['objects']
        group=root.find(f".//group[@id='{ids['group']}']")
        if group is None:
            errors.append({'page':index+1,'compound_id':cid,'error':'missing_group'});continue
        fragment=group.find(f"fragment[@id='{ids['fragment']}']")
        if fragment is None:
            errors.append({'page':index+1,'compound_id':cid,'error':'missing_structure'});continue
        mol=fragment_mol(fragment)
        if semantic_key(mol)!=record['displayed_identity']:
            errors.append({'page':index+1,'compound_id':cid,'error':'structure_changed'})
        expected[index].update(semantic_key(m) for m in Chem.GetMolFrags(Chem.MolFromSmiles(record['displayed_identity']),asMols=True))
        for field,oid in {'label':ids['label'],**ids['fields']}.items():
            node=group.find(f"t[@id='{oid}']")
            if node is None or node_text(node)!=record['display'][field]:
                errors.append({'page':index+1,'compound_id':cid,'error':'label_binding_changed','field':field})
        elements=[fragment,*group.findall('t')]
        for element in elements:
            box=bounds(element,style)
            if box:
                boxes[index].append((cid,element.get('id'),box))
        for run in group.iter('s'):
            if float(run.get('size',style['font_size']))<7:
                issues.append({'page':index+1,'compound_id':cid,'issue':'text_below_7pt'})
    for index,root in enumerate(roots):
        managed={oid for cid,oid,box in boxes[index]}
        parents={child:parent for parent in root.iter() for child in parent}
        for node in root.iter('t'):
            if node.get('id') in managed:continue
            parent=parents.get(node)
            in_structure=False
            while parent is not None:
                if parent.tag in {'fragment','n'}:in_structure=True;break
                parent=parents.get(parent)
            if in_structure:continue
            box=bounds(node,style)
            if box:boxes[index].append(('annotation',node.get('id'),box))
            if any(float(run.get('size',style['font_size']))<7 for run in node.findall('s')):
                issues.append({'page':index+1,'object_id':node.get('id'),'issue':'text_below_7pt'})
        actual=Counter(semantic_key(m) for m in read_molecules(ET.tostring(root,encoding='unicode'))) if root.find('.//fragment') is not None else Counter()
        if actual!=expected[index]: errors.append({'page':index+1,'error':'document_inventory_changed'})
        page=project['pages'][index]
        for cid,oid,box in boxes[index]:
            if box[0]<0 or box[1]<0 or box[2]>page['width_pt'] or box[3]>page['height_pt']:
                issues.append({'page':index+1,'compound_id':cid,'object_id':oid,'issue':'outside_page'})
        for i,(cid,oid,box) in enumerate(boxes[index]):
            for other,oid2,box2 in boxes[index][i+1:]:
                if overlap(box,box2): issues.append({'page':index+1,'compound_id':cid,'other_compound_id':other,
                                                   'objects':[oid,oid2],'issue':'overlap'})
    return {'data_binding':{'status':'failed' if errors else 'passed','errors':errors},
            'chemistry':{'status':'failed' if errors else 'passed','scope':'rdkit_readback_consistency'},
            'layout':{'status':'review_required' if issues else 'passed','issues':issues,
                      'measurement':'font_metrics_and_structure_bounds; confirm native pixels'},
            'native_preview':{'status':'not_run'}}
