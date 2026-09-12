"""Rebuild the two reference layouts from editable native components.
Chemical acceptance remains provisional; see the README and provenance files.
"""
from pathlib import Path
from copy import deepcopy
from collections import Counter
import json,sys
from lxml import etree as E
from cdxml_toolkit.chemistry_semantics import document_inventory
b=Path(__file__).resolve().parent
out=Path(sys.argv[1]).resolve();out.mkdir(parents=True,exist_ok=False)
cases=json.loads((b/'cases.json').read_text())
reference_attrs=('B','E','CrossingBonds','SupersededBy','AttachedObjects','BasisObjects','BondOrdering','object','BondCircularOrdering')
records={}
for name,files,size in [(key,value['files'],value['size']) for key,value in cases.items()]:
 root=E.Element('CDXML',BondLength='20',LineWidth='0.6',BoldWidth='2',HashSpacing='2.5',MarginWidth='1.5',BondSpacing='18',LabelFont='1000',CaptionFont='1000',LabelSize='13',CaptionSize='13',LabelFace='96',BoundingBox=f'0 0 {size[0]/2} {size[1]/2}')
 fonts=E.SubElement(root,'fonttable');colors=E.SubElement(root,'colortable');page=E.SubElement(root,'page',id='1',BoundingBox=root.get('BoundingBox'),WidthPages='2',HeightPages='1')
 font_lookup={};color_lookup={};counter=100;expected=Counter();entries=[]
 for key,relative in files.items():
  path=b/relative;source=E.parse(str(path)).getroot()
  if key!='conditions':expected.update(document_inventory(path))
  else:assert not source.findall('.//fragment')
  fmap={};cmap={}
  for font in source.findall('fonttable/font'):
   identity=(font.get('name'),font.get('charset'))
   if identity not in font_lookup:
    fid=str(1000+len(font_lookup));font_lookup[identity]=fid;copy=deepcopy(font);copy.set('id',fid);fonts.append(copy)
   fmap[font.get('id')]=font_lookup[identity]
  for i,color in enumerate(source.findall('colortable/color'),2):
   identity=tuple(sorted(color.attrib.items()))
   if identity not in color_lookup:color_lookup[identity]=str(2+len(color_lookup));colors.append(deepcopy(color))
   cmap[str(i)]=color_lookup[identity]
  items=[deepcopy(item) for p in source.findall('page') for item in p];ids={}
  for item in items:
   for node in item.iter():
    if node.get('id') is not None:ids[node.get('id')]=str(counter);counter+=1
  dx,dy=(13,-136) if name=='113-122' and key=='112' else (0,0)
  for item in items:
   for node in item.iter():
    if node.get('id') is not None:node.set('id',ids[node.get('id')])
    for attr in reference_attrs:
     if node.get(attr):node.set(attr,' '.join(ids.get(v,v) for v in node.get(attr).split()))
    for attr in ('font','LabelFont','CaptionFont'):
     if node.get(attr) in fmap:node.set(attr,fmap[node.get(attr)])
    for attr in ('color','bgcolor'):
     if node.get(attr) in cmap:node.set(attr,cmap[node.get(attr)])
    if dx or dy:
     for attr in ('p','BoundingBox','CurvePoints','Head3D','Tail3D','Center3D','MajorAxisEnd3D','MinorAxisEnd3D'):
      if not node.get(attr):continue
      vals=list(map(float,node.get(attr).split()));stride=3 if attr.endswith('3D') else 2
      for i in range(0,len(vals),stride):vals[i]+=dx;vals[i+1]+=dy
      node.set(attr,' '.join(f'{v:g}' for v in vals))
   page.append(item)
  entries.append({'id':key,'file':relative,'translation_points':[dx,dy]})
 target=out/f'synthesis-{name}.cdxml';E.ElementTree(root).write(str(target),encoding='UTF-8',xml_declaration=True)
 observed=document_inventory(target);assert observed==expected,(name,'assembly changed inventory')
 records[name]={'file':target.name,'components':entries,'molecular_species':sum(expected.values()),'component_inventory_preserved':True,'full_stereo_acceptance':False,'pixel_identical':False}
(out/'assembly.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
print(json.dumps({k:{'file':v['file'],'species':v['molecular_species']} for k,v in records.items()}))
