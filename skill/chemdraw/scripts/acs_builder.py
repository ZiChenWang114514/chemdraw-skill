"""ACS Document 1996 CDXML writer for exam, lecture and paper figures.

Fixed style: Arial 10 pt, bond 14.4 pt, line 0.6, bold 2.0, hash spacing 2.5,
margin 1.6. RDKit supplies 2D coordinates; this module adds what plain
draw_molecule does not: abbreviation nodes (C10H21, OMe...) with correct
subscripts and label direction, rich-text markup ({i:}{b:}{bi:}{sub:}{sup:}),
Chinese text (SimSun font 5), arrows, boxes and bold compound codes.

Library use:  fig = Fig(); fig.mol('[*:1]CC(=O)O', at=(100, 80), labels={1: 'C10H21'}); fig.write('a.cdxml')
CLI use:      cdx.py build spec.json out.cdxml --render   (spec format: build_from_spec)
"""
import json
import math
import re
from pathlib import Path

from rdkit import Chem
from rdkit.Chem import rdDepictor, AllChem
rdDepictor.SetPreferCoordGen(True)

BL = 14.4
SYM_WIDE = {'Si', 'Cl', 'Br', 'Mg', 'Na', 'Li'}
ELEM = {'H': 1, 'C': 6, 'N': 7, 'O': 8, 'F': 9, 'Si': 14, 'P': 15, 'S': 16, 'Cl': 17, 'Br': 35, 'I': 53}
TOK = re.compile(r'\{(i|b|bi|sub|sup):([^{}]*)\}')
FACE = {'': 0, 'b': 1, 'i': 2, 'bi': 3, 'sub': 32, 'sup': 64}


def _is_cjk(ch):
    """CJK ideographs, CJK punctuation and full-width forms need the SimSun font entry."""
    return ('\u3000' <= ch <= '\u303f' or '\u3400' <= ch <= '\u9fff' or '\uff00' <= ch <= '\uffef')


CJK_CLASS = r'[\u3000-\u303f\u3400-\u9fff\uff00-\uffef]'
NON_CJK_CLASS = r'[^\u3000-\u303f\u3400-\u9fff\uff00-\uffef]'


def runs(markup, font=3, size=10, base=0):
    out, pos = [], 0
    for m in TOK.finditer(markup):
        if m.start() > pos:
            out.append((markup[pos:m.start()], base))
        out.append((m.group(2), FACE[m.group(1)] | base))
        pos = m.end()
    if pos < len(markup):
        out.append((markup[pos:], base))
    s = ''
    for t, f in out:
        # Only CJK characters use SimSun (font 5); Latin text, digits and symbols stay in `font`.
        for piece in re.findall(r'(?:%s)+|(?:%s)+' % (CJK_CLASS, NON_CJK_CLASS), t):
            fnt = 5 if _is_cjk(piece[0]) else font
            piece = piece.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            s += f'<s font="{fnt}" size="{size}" face="{f}">{piece}</s>'
    return s


def formula_markup(label):
    """C10H21 -> C{sub:10}H{sub:21}; leaves already-marked text alone"""
    if '{' in label:
        return label
    return re.sub(r'(?<=[A-Za-z\)])(\d+)', r'{sub:\1}', label)


class Fig:
    def __init__(self):
        self.items = []
        self.nid = 1000
        self.bbox = [1e9, 1e9, -1e9, -1e9]

    def _id(self):
        self.nid += 1
        return self.nid

    def _bb(self, x, y, pad=8):
        b = self.bbox
        b[0] = min(b[0], x - pad); b[1] = min(b[1], y - pad); b[2] = max(b[2], x + pad); b[3] = max(b[3], y + pad)

    # ------------------------------------------------------------------ molecule
    def mol(self, smiles, at=(100, 100), labels=None, coords=None, rotate=0.0, flip=False, scale=BL,
            displays=None, radicals=(), wedge=True, explicitH=None, center=True, hide_charge_label=False,
            lone_pairs=(), double_pos=None, label_text=None):
        """smiles may contain [*:n] dummy atoms; labels maps n -> label text (e.g. 'C10H21').
        coords: optional list of (x,y) in drawing units (y down) per atom index (overrides layout).
        displays: dict bond_idx -> CDXML Display (WedgeBegin etc., B = bond begin atom).
        label_text: dict atom_idx -> explicit label markup."""
        labels = labels or {}
        if isinstance(smiles, str):
            ps = Chem.SmilesParserParams(); ps.removeHs = False
            m = Chem.MolFromSmiles(smiles, ps)
        else:
            m = smiles
        Chem.Kekulize(m, clearAromaticFlags=True)
        if coords is None:
            rdDepictor.Compute2DCoords(m)
            conf = m.GetConformer()
            pts = [(conf.GetAtomPosition(i).x, -conf.GetAtomPosition(i).y) for i in range(m.GetNumAtoms())]
            ds = [math.dist(pts[b.GetBeginAtomIdx()], pts[b.GetEndAtomIdx()]) for b in m.GetBonds()]
            ds.sort(); med = ds[len(ds) // 2] if ds else 1
            pts = [(x / med * scale, y / med * scale) for x, y in pts]
            if flip:
                pts = [(-x, y) for x, y in pts]
            if rotate:
                c, s = math.cos(math.radians(rotate)), math.sin(math.radians(rotate))
                pts = [(x * c + y * s, -x * s + y * c) for x, y in pts]
            if wedge and displays is None:
                for i, (x, y) in enumerate(pts):
                    conf.SetAtomPosition(i, (x, -y, 0))
                Chem.WedgeMolBonds(m, conf)
        else:
            pts = list(coords)
        if center:
            cx = (min(p[0] for p in pts) + max(p[0] for p in pts)) / 2
            cy = (min(p[1] for p in pts) + max(p[1] for p in pts)) / 2
        else:
            cx = cy = 0
        pts = [(x - cx + at[0], y - cy + at[1]) for x, y in pts]
        ids = [self._id() for _ in pts]
        nb = {i: [] for i in range(len(pts))}
        for b in m.GetBonds():
            nb[b.GetBeginAtomIdx()].append(b.GetEndAtomIdx()); nb[b.GetEndAtomIdx()].append(b.GetBeginAtomIdx())
        ring = m.GetRingInfo()
        xml = [f'<fragment id="{self._id()}">']
        for i, a in enumerate(m.GetAtoms()):
            x, y = pts[i]; self._bb(x, y)
            sym = a.GetSymbol()
            attrs = f'id="{ids[i]}" p="{x:.2f} {y:.2f}"'
            # direction of neighbours: label H on the side away from bonds
            dx = sum(pts[j][0] - x for j in nb[i])
            right = dx > 0.5  # bonds mostly to the right -> label text to the left
            text = None
            if a.GetAtomicNum() == 0:
                lab = labels.get(a.GetAtomMapNum(), 'R')
                attrs += f' NodeType="GenericNickname" GenericNickname="{lab}"'
                text = formula_markup(lab)
                if right and re.match(r'C\d', lab):  # reverse formula when bond on the right
                    parts = re.findall(r'[A-Z][a-z]?\d*', lab)
                    text = formula_markup(''.join(reversed(parts)))
                # reversed text "H21C10": the attachment must be the last element
            else:
                chg = a.GetFormalCharge()
                nh = a.GetTotalNumHs()
                if sym != 'C' or chg or (label_text and i in label_text):
                    attrs += f' Element="{ELEM.get(sym, a.GetAtomicNum())}" NumHydrogens="{nh}"'
                    if chg:
                        attrs += f' Charge="{chg}"'
                    if i in radicals:
                        attrs += ' Radical="Doublet"'
                    if label_text and i in label_text:
                        text = label_text[i]
                    elif sym != 'C' or chg:
                        hpart = '' if nh == 0 else ('H' if nh == 1 else 'H{sub:%d}' % nh)
                        cs = '' if not chg or hide_charge_label else ('{sup:+}' if chg == 1 else '{sup:−}' if chg == -1 else '{sup:%d%s}' % (abs(chg), '+' if chg > 0 else '−'))
                        if sym == 'C' and chg:
                            text = sym + hpart + cs if nh else sym + cs
                        else:
                            text = (hpart + sym + cs) if (right and hpart) else (sym + hpart + cs)
            if text is not None:
                just = 'Right' if right and (a.GetAtomicNum() == 0 or text.startswith('H')) else 'Left'
                xml.append(f'<n {attrs}><t p="{x:.2f} {y + 3.5:.2f}" LabelJustification="{just}" LabelAlignment="{just}">{runs(text)}</t></n>')
            else:
                xml.append(f'<n {attrs}/>')
        for b in m.GetBonds():
            i, j = b.GetBeginAtomIdx(), b.GetEndAtomIdx()
            attrs = f'id="{self._id()}" B="{ids[i]}" E="{ids[j]}"'
            bt = b.GetBondType()
            if bt == Chem.BondType.DOUBLE:
                attrs += ' Order="2"'
                pos = None
                if double_pos and b.GetIdx() in double_pos:
                    pos = double_pos[b.GetIdx()]
                elif ring.NumBondRings(b.GetIdx()):
                    # put second line toward ring centre (smallest ring)
                    rr = min((r for r in ring.BondRings() if b.GetIdx() in r), key=len)
                    atoms = set()
                    for bi in rr:
                        bb = m.GetBondWithIdx(bi); atoms |= {bb.GetBeginAtomIdx(), bb.GetEndAtomIdx()}
                    rx = sum(pts[k][0] for k in atoms) / len(atoms); ry = sum(pts[k][1] for k in atoms) / len(atoms)
                    pos = self._side(pts[i], pts[j], (rx, ry))
                else:
                    others = [k for k in nb[i] if k != j] + [k for k in nb[j] if k != i]
                    if len(nb[i]) == 1 or len(nb[j]) == 1 or not others:
                        pos = 'Center' if (len(nb[i]) == 1 or len(nb[j]) == 1) else None
                    else:
                        sx = sum(pts[k][0] for k in others) / len(others); sy = sum(pts[k][1] for k in others) / len(others)
                        pos = self._side(pts[i], pts[j], (sx, sy))
                if pos:
                    attrs += f' DoublePosition="{pos}"'
            elif bt == Chem.BondType.TRIPLE:
                attrs += ' Order="3"'
            disp = None
            if displays and b.GetIdx() in displays:
                disp = displays[b.GetIdx()]
            elif wedge:
                d = b.GetBondDir()
                if d == Chem.BondDir.BEGINWEDGE:
                    disp = 'WedgeBegin'
                elif d == Chem.BondDir.BEGINDASH:
                    disp = 'WedgedHashBegin'
            if disp:
                attrs += f' Display="{disp}"'
            xml.append(f'<b {attrs}/>')
        xml.append('</fragment>')
        for i in radicals:
            x, y = pts[i]
            ox, oy = self._free_dir(pts, nb, i)
            self.text(x + ox * 6 - 1.8, y + oy * 6 + 3.5, '•', size=10, align='Left')
        for (i, side) in lone_pairs:
            x, y = pts[i]
            dx = {'right': 11, 'left': -14, 'up': -1.5, 'down': -1.5}[side]
            self.text(x + dx, y + 3.2, '{b::}', size=10, align='Left')
        self.items.append('\n'.join(xml))
        self.last_pts = pts
        return pts

    @staticmethod
    def _free_dir(pts, nb, i):
        x, y = pts[i]
        vx = -sum(pts[j][0] - x for j in nb[i]); vy = -sum(pts[j][1] - y for j in nb[i])
        n = math.hypot(vx, vy) or 1
        return vx / n, vy / n

    @staticmethod
    def _side(p, q, s):
        # CDXML y down; cross product sign tells which side of B->E the point s lies
        cr = (q[0] - p[0]) * (s[1] - p[1]) - (q[1] - p[1]) * (s[0] - p[0])
        return 'Left' if cr > 0 else 'Right'

    # ------------------------------------------------------------------ annotations
    def text(self, x, y, markup, size=10, align='Center', bold=False, font=3):
        self._bb(x, y)
        base = 1 if bold else 0
        j = f' Justification="{align}" CaptionJustification="{align}"' if align != 'Left' else ''
        self.items.append(f'<t id="{self._id()}" p="{x:.2f} {y:.2f}"{j}>{runs(markup, font, size, base)}</t>')

    def arrow(self, x1, y1, x2, y2, kind='forward'):
        self._bb(x1, y1); self._bb(x2, y2)
        tail = ' ArrowheadTail="Full"' if kind == 'resonance' else ''
        self.items.append(f'<arrow id="{self._id()}" FillType="None" ArrowheadHead="Full"{tail} ArrowheadType="Solid" '
                          f'HeadSize="1000" ArrowheadCenterSize="875" ArrowheadWidth="250" '
                          f'Head3D="{x2:.2f} {y2:.2f} 0" Tail3D="{x1:.2f} {y1:.2f} 0"/>')

    def box(self, x1, y1, x2, y2, round_=True):
        self._bb(x1, y1, 2); self._bb(x2, y2, 2)
        rt = ' RectangleType="RoundEdge"' if round_ else ''
        self.items.append(f'<graphic id="{self._id()}" BoundingBox="{x2:.2f} {y2:.2f} {x1:.2f} {y1:.2f}" GraphicType="Rectangle"{rt}/>')

    def label_box(self, x, y, markup, w=None):
        """bold Arial code in a rounded box centred at (x,y)"""
        n = len(re.sub(r'\{[a-z]+:|\}', '', markup))
        w = w or max(16, 7.5 * n + 8)
        self.box(x - w / 2, y - 9, x + w / 2, y + 7)
        if n == 1:
            self.text(x - 3.6, y + 3.5, markup, bold=True, align='Left')
        else:
            self.text(x, y + 3.5, markup, bold=True)

    def write(self, path):
        b = self.bbox
        head = ('<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE CDXML SYSTEM "http://www.cambridgesoft.com/xml/cdxml.dtd">\n'
                f'<CDXML BondLength="14.4" LabelFont="3" LabelSize="10" LabelFace="96" CaptionFont="3" CaptionSize="10" '
                'LineWidth="0.6" BoldWidth="2" HashSpacing="2.5" MarginWidth="1.6" BondSpacing="18" ChainAngle="120" '
                'LabelJustification="Auto" CaptionJustification="Left" color="0" bgcolor="1">'
                '<colortable><color r="1" g="1" b="1"/><color r="0" g="0" b="0"/></colortable>'
                '<fonttable><font id="3" charset="iso-8859-1" name="Arial"/><font id="5" charset="Unicode" name="SimSun"/></fonttable>'
                '<page id="1">\n')
        Path(path).write_text(head + '\n'.join(self.items) + '\n</page></CDXML>\n', encoding='utf-8')
        return Path(path)


def build_from_spec(spec_path, output_path):
    """Build a CDXML from a JSON spec; coordinates are points, x right, y down.

    {"objects": [
      {"type": "molecule", "smiles": "[*:1]CC(=O)O", "at": [100, 80], "labels": {"1": "C10H21"},
       "rotate": 0, "flip": false, "displays": {"0": "WedgeBegin"}, "radicals": [], "lone_pairs": [[2, "right"]]},
      {"type": "text", "at": [100, 130], "text": "{b:A} (note)", "size": 10, "align": "Center", "bold": false},
      {"type": "arrow", "from": [150, 80], "to": [200, 80], "kind": "forward"},
      {"type": "box", "from": [10, 10], "to": [60, 40], "round": true},
      {"type": "label_box", "at": [100, 150], "text": "B"}
    ]}
    """
    spec = json.loads(Path(spec_path).read_text(encoding='utf-8-sig'))
    fig = Fig()
    for o in spec['objects']:
        kind = o['type']
        if kind == 'molecule':
            fig.mol(o['smiles'], at=tuple(o.get('at', (100, 100))),
                    labels={int(k): v for k, v in (o.get('labels') or {}).items()},
                    rotate=o.get('rotate', 0.0), flip=o.get('flip', False),
                    displays={int(k): v for k, v in o['displays'].items()} if 'displays' in o else None,
                    radicals=tuple(o.get('radicals', ())), lone_pairs=[tuple(x) for x in o.get('lone_pairs', ())],
                    hide_charge_label=o.get('hide_charge_label', False))
        elif kind == 'text':
            fig.text(*o['at'], o['text'], size=o.get('size', 10), align=o.get('align', 'Center'),
                     bold=o.get('bold', False))
        elif kind == 'arrow':
            fig.arrow(*o['from'], *o['to'], kind=o.get('kind', 'forward'))
        elif kind == 'box':
            fig.box(*o['from'], *o['to'], round_=o.get('round', True))
        elif kind == 'label_box':
            fig.label_box(*o['at'], o['text'], w=o.get('width'))
        else:
            raise ValueError(f'Unknown object type {kind!r}')
    return fig.write(output_path)
