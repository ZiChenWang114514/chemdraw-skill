"""Small native drawing and artifact helpers shared by scientific workflows."""
import math
from pathlib import Path
from xml.etree import ElementTree as ET
from ..mcp_runtime import artifact_safety


def number(value, name, low=None, high=None):
    if isinstance(value, bool):
        raise ValueError(f'{name} must be numeric')
    value = float(value)
    if not math.isfinite(value) or (low is not None and value < low) or (high is not None and value > high):
        raise ValueError(f'{name} is outside the supported range')
    return value


def point(value):
    if len(value) != 2:
        raise ValueError('A point needs two coordinates')
    return tuple(number(v, 'coordinate', -10000, 10000) for v in value)


class Drawing:
    def __init__(self, width=600, height=400):
        self.root = ET.Element('CDXML', {'BondLength':'14.4', 'LineWidth':'0.6', 'BoldWidth':'2',
            'LabelFont':'3', 'CaptionFont':'3', 'LabelSize':'10', 'CaptionSize':'10',
            'PrintMargins':'0 0 0 0', 'BoundingBox':f'0 0 {width} {height}'})
        ET.SubElement(ET.SubElement(self.root,'fonttable'),'font',{'id':'3','charset':'iso-8859-1','name':'Arial'})
        colors=ET.SubElement(self.root,'colortable')
        ET.SubElement(colors,'color',{'r':'1','g':'1','b':'1'})
        ET.SubElement(colors,'color',{'r':'0','g':'0','b':'0'})
        self.page=ET.SubElement(self.root,'page',{'id':'1','BoundingBox':f'0 0 {width} {height}',
            'Width':str(width),'Height':str(height),'HeaderPosition':'0','FooterPosition':'0'})
        self.counter=100

    def add(self, kind, attrs, parent=None):
        node=ET.SubElement(self.page if parent is None else parent,kind,{'id':str(self.counter),**{k:str(v) for k,v in attrs.items()}})
        self.counter+=1
        return node

    def text(self, xy, value, size=10, parent=None):
        x,y=point(xy)
        node=self.add('t',{'p':f'{x} {y}','Justification':'Left'},parent)
        ET.SubElement(node,'s',{'font':'3','size':str(size),'face':'0'}).text=str(value)
        return node

    def line(self, a, b, parent=None):
        a,b=point(a),point(b)
        return self.add('graphic',{'GraphicType':'Line','BoundingBox':' '.join(map(str,(*a,*b)))},parent)

    def curve(self, points, parent=None, closed=False, filled=False):
        pts=[point(p) for p in points]
        if len(pts)<2:raise ValueError('A curve needs at least two points')
        # Degenerate cubic handles produce an editable polyline.
        native=[q for p in pts for q in (p,p,p)]
        return self.add('curve',{'CurvePoints':' '.join(str(c) for p in native for c in p),
            'Closed':'yes' if closed else 'no','FillType':'Solid' if filled else 'None',
            'CurveType':(1 if closed else 0)+(128 if filled else 0)},parent)

    def save(self, output):
        target=artifact_safety.resolve_destination(source=None,output_path=str(output),tag='scientific',suffix='.cdxml')
        with artifact_safety.staging_file(target) as stage:
            ET.ElementTree(self.root).write(stage,encoding='utf-8',xml_declaration=True)
            artifact_safety.publish_file(stage,target)
        return str(target)
