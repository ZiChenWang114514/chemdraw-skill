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
        ET.SubElement(ET.SubElement(self.root,'fonttable'),'font',{'id':'3','charset':'utf-8','name':'Arial'})
        self.colortable=ET.SubElement(self.root,'colortable')
        ET.SubElement(self.colortable,'color',{'r':'1','g':'1','b':'1'})
        ET.SubElement(self.colortable,'color',{'r':'0','g':'0','b':'0'})
        self._color_map: dict[tuple[int, int, int], str] = {}
        self.page=ET.SubElement(self.root,'page',{'id':'1','BoundingBox':f'0 0 {width} {height}',
            'Width':str(width),'Height':str(height),'HeaderPosition':'0','FooterPosition':'0'})
        self.counter=100

    def color(self, rgb_hex: str) -> str:
        text = str(rgb_hex).strip()
        if text.isdigit():
            return text
        if text.startswith('#'):
            text = text[1:]
        if len(text) == 3:
            text = ''.join(ch * 2 for ch in text)
        if len(text) != 6:
            raise ValueError(f'Invalid RGB hex color: {rgb_hex!r}')
        try:
            rgb = (int(text[0:2], 16), int(text[2:4], 16), int(text[4:6], 16))
        except ValueError as exc:
            raise ValueError(f'Invalid RGB hex color: {rgb_hex!r}') from exc
        if rgb in self._color_map:
            return self._color_map[rgb]
        colortable = self.root.find('colortable')
        if colortable is None:
            colortable = ET.SubElement(self.root, 'colortable')
        idx = str(len(colortable) + 2)
        def _fmt(c: int) -> str:
            if c <= 0:
                return '0'
            if c >= 255:
                return '1'
            return f'{c / 255.0:.4f}'.rstrip('0').rstrip('.')
        ET.SubElement(colortable, 'color', {'r': _fmt(rgb[0]), 'g': _fmt(rgb[1]), 'b': _fmt(rgb[2])})
        self._color_map[rgb] = idx
        return idx

    def _resolve_color(self, color: str | None) -> str | None:
        if color is None:
            return None
        text = str(color).strip()
        if not text:
            return None
        return text if text.isdigit() else self.color(text)

    def add(self, kind, attrs, parent=None):
        node=ET.SubElement(self.page if parent is None else parent,kind,{'id':str(self.counter),'Z':str(self.counter),**{k:str(v) for k,v in attrs.items()}})
        self.counter+=1
        return node

    def text(self, xy, value, size=10, parent=None, color: str | None = None):
        x,y=point(xy)
        t_attrs = {'p':f'{x} {y}','Justification':'Left'}
        s_attrs = {'font':'3','size':str(size),'face':'0'}
        c_idx = self._resolve_color(color)
        if c_idx is not None:
            t_attrs['color'] = c_idx
            s_attrs['color'] = c_idx
        node=self.add('t',t_attrs,parent)
        ET.SubElement(node,'s',s_attrs).text=str(value)
        return node

    def line(self, a, b, parent=None, color: str | None = None, dashed: bool = False):
        a,b=point(a),point(b)
        attrs = {'GraphicType':'Line','BoundingBox':' '.join(map(str,(*a,*b)))}
        c_idx = self._resolve_color(color)
        if c_idx is not None:
            attrs['color'] = c_idx
        if dashed:
            attrs['LineType'] = 'Dashed'
        return self.add('graphic',attrs,parent)

    def curve(self, points, parent=None, closed=False, filled=False, color: str | None = None, dashed: bool = False):
        pts=[point(p) for p in points]
        if len(pts)<2:raise ValueError('A curve needs at least two points')
        # Degenerate cubic handles produce an editable polyline.
        native=[q for p in pts for q in (p,p,p)]
        attrs = {
            'CurvePoints':' '.join(str(c) for p in native for c in p),
            'Closed':'yes' if closed else 'no',
            'FillType':'Solid' if filled else 'None',
            'CurveType':(1 if closed else 0)+(128 if filled else 0),
        }
        c_idx = self._resolve_color(color)
        if c_idx is not None:
            attrs['color'] = c_idx
        if dashed:
            attrs['LineType'] = 'Dashed'
        return self.add('curve',attrs,parent)

    def filled_rect(
        self,
        x1,
        y1,
        x2,
        y2,
        *,
        fill_color: str,
        border_color: str | None = None,
        parent=None,
    ) -> ET.Element:
        px1, py1 = point((x1, y1))
        px2, py2 = point((x2, y2))
        pts = [(px1, py1), (px2, py1), (px2, py2), (px1, py2)]
        native = [q for p in pts for q in (p, p, p)]
        fill_idx = self._resolve_color(fill_color)
        attrs = {
            'CurvePoints': ' '.join(str(c) for p in native for c in p),
            'Closed': 'yes',
            'FillType': 'Solid',
            'LineType': 'Solid',
            'CurveType': 129,
            'BoundingBox': f'{min(px1, px2)} {min(py1, py2)} {max(px1, px2)} {max(py1, py2)}',
        }
        if fill_idx is not None:
            attrs['color'] = fill_idx
        if border_color is not None:
            border_idx = self._resolve_color(border_color)
            if border_idx is not None:
                attrs['fgcolor'] = border_idx
        return self.add('curve', attrs, parent)

    def save(self, output):
        target=artifact_safety.resolve_destination(source=None,output_path=str(output),tag='scientific',suffix='.cdxml')
        with artifact_safety.staging_file(target) as stage:
            ET.ElementTree(self.root).write(stage,encoding='utf-8',xml_declaration=True)
            artifact_safety.publish_file(stage,target)
        return str(target)
