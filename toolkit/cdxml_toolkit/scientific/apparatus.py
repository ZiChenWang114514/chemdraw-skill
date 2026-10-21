"""Assemble installed ChemDraw apparatus templates without redrawing their artwork."""
from copy import deepcopy
import hashlib
from pathlib import Path
from xml.etree import ElementTree as ET
from .common import Drawing, number, point


def template_catalog(path):
    path=Path(path).resolve();root=ET.parse(path).getroot()
    if root.tag!='CDXML':raise ValueError('A native CDXML template document is required')
    pages=[]
    for index,page in enumerate(root.findall('page')):
        boxes=[list(map(float,n.get('BoundingBox').split())) for n in page if n.get('BoundingBox')]
        bounds=[min(b[0] for b in boxes),min(b[1] for b in boxes),max(b[2] for b in boxes),max(b[3] for b in boxes)] if boxes else None
        pages.append({'index':index,'bounds':bounds,'objects':len(list(page))})
    return {'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'pages':pages}


def draw_apparatus(spec, output):
    files=spec.get('template_files',{})
    if not files:raise ValueError('Provide native template_files converted from the installed ChemDraw CTP files')
    components=spec.get('components',[])
    if not 1<=len(components)<=100:raise ValueError('Provide 1..100 native template components')
    d=Drawing(number(spec.get('width',600),'width',100,3000),number(spec.get('height',600),'height',100,3000))
    d.text([25,25],spec.get('title','Experimental apparatus'))
    templates={};catalogs={};color_maps={};font_maps={}
    for key,path in files.items():
        catalogs[key]=template_catalog(path);templates[key]=ET.parse(path).getroot()
        color_maps[key]={0:0,1:1}
        for index,color in enumerate(templates[key].findall('./colortable/color')):
            dest=d.root.find('colortable');color_maps[key][index+2]=len(dest)+2;dest.append(deepcopy(color))
        font_maps[key]={}
        for font in templates[key].findall('./fonttable/font'):
            copy=deepcopy(font);font_maps[key][font.get('id')]=str(d.counter);copy.set('id',str(d.counter));d.counter+=1
            d.root.find('fonttable').append(copy)
    ports={};used=set();receipts=[]
    for component in components:
        ident=str(component['id']);key=component.get('template')
        if ident in used or '.' in ident:raise ValueError('Component IDs must be unique and contain no dots')
        if key not in templates:raise ValueError('Unknown template library')
        used.add(ident);index=component['page'];pages=templates[key].findall('page')
        if not isinstance(index,int) or not 0<=index<len(pages):raise ValueError('Invalid template page index')
        bounds=catalogs[key]['pages'][index]['bounds']
        if not bounds:raise ValueError('The selected native template page is empty')
        x0,y0,x1,y1=bounds;scale=number(component.get('scale',1),'scale',.05,10)
        local_ports={name:point(value) for name,value in component.get('ports',{}).items()}
        if any(not 0<=v<=1 for xy in local_ports.values() for v in xy):raise ValueError('Ports use normalized template bounds')
        if component.get('attach'):
            attachment=component['attach'];target=ports.get(attachment['to']);local=local_ports.get(attachment['port'])
            if target is None or local is None:raise ValueError('Attachment requires an existing target port and a local port')
            tx=target[0]-local[0]*(x1-x0)*scale;ty=target[1]-local[1]*(y1-y0)*scale
        else:tx,ty=point(component.get('position',[50,50]))
        elements=[deepcopy(n) for n in pages[index] if n.tag not in ('annotation',)]
        if any(n.tag in ('n','b','fragment','embeddedobject') for e in elements for n in e.iter()):
            raise ValueError('Apparatus templates must contain editable graphics, not molecule graphs or embedded images')
        id_map={}
        for element in elements:
            for node in element.iter():
                if node.get('id') is not None:id_map[node.get('id')]=str(d.counter);d.counter+=1
        wrapper=d.add('group',{'Integral':'yes'})
        for element in elements:
            for node in element.iter():
                if node.get('id') is not None:node.set('id',id_map[node.get('id')])
                for attr in ('SupersededBy','BasisObjects','AttachedObjects'):
                    if attr in node.attrib:
                        refs=node.get(attr).split()
                        if any(ref not in id_map for ref in refs):raise ValueError('Template references an object outside its page')
                        node.set(attr,' '.join(id_map[ref] for ref in refs))
                for attr in ('p','BoundingBox','Head3D','Tail3D','Center3D','MajorAxisEnd3D','MinorAxisEnd3D','CurvePoints'):
                    if attr not in node.attrib:continue
                    values=list(map(float,node.get(attr).split()));stride=3 if attr.endswith('3D') else 2
                    if len(values)%stride:raise ValueError('Invalid native coordinates')
                    for i in range(0,len(values),stride):values[i]=(values[i]-x0)*scale+tx;values[i+1]=(values[i+1]-y0)*scale+ty
                    node.set(attr,' '.join(f'{v:.5f}' for v in values))
                for attr in ('LineWidth','BoldWidth'):
                    if attr in node.attrib:node.set(attr,str(float(node.get(attr))*scale))
                for attr in ('color','bgcolor'):
                    if attr in node.attrib:node.set(attr,str(color_maps[key][int(node.get(attr))]))
                if node.get('font') in font_maps[key]:node.set('font',font_maps[key][node.get('font')])
            wrapper.append(element)
        for name,(u,v) in local_ports.items():ports[f'{ident}.{name}']=[tx+u*(x1-x0)*scale,ty+v*(y1-y0)*scale]
        if component.get('label'):
            dx,dy=point(component.get('label_offset',[(x1-x0)*scale+15,20]))
            d.text([tx+dx,ty+dy],component['label'],10)
        receipts.append({'component':ident,'template':key,'page':index,'source_sha256':catalogs[key]['sha256'],'source_objects':len(id_map)})
    for connection in spec.get('connections',[]):
        a=ports.get(connection['from']);b=ports.get(connection['to'])
        if a is None or b is None:raise ValueError('Unknown connection port')
        via=[point(p) for p in connection.get('via',[])]
        if a!=b or via:d.curve([a,*via,b])
    return {'output_path':d.save(output),'ports':ports,'native_templates':receipts,
        'scope':'Native ChemDraw template assembly; connection ports describe drawing geometry'}
