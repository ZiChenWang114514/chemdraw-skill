"""ACS Document 1996 CDXML writer for exam, lecture and paper figures.

Fixed style: Arial 10 pt, bond 14.4 pt, line 0.6, bold 2.0, hash spacing 2.5,
margin 1.6. RDKit supplies 2D coordinates; this module adds what plain
draw_molecule does not: abbreviation nodes (C10H21, OMe...) with correct
subscripts and label direction, rich-text markup ({i:}{b:}{bi:}{sub:}{sup:}),
Chinese text (SimSun font 5), arrows, boxes, bold compound codes, JACS/Angew
pastel ring fills, atom halos, multi-center organometallic attachments,
transition-state brackets, orbital lobes, non-covalent interactions and
3D conformer/projection templates.

Library use:  fig = Fig(); fig.mol('[*:1]CC(=O)O', at=(100, 80), labels={1: 'C10H21'}); fig.write('a.cdxml')
CLI use:      cdx.py build spec.json out.cdxml --render   (spec format: build_from_spec)
"""
from collections.abc import Mapping
import json
import math
import re
import sys
from pathlib import Path

from rdkit import Chem
from rdkit.Chem import rdDepictor, AllChem

BL = 14.4
SYM_WIDE = {'Si', 'Cl', 'Br', 'Mg', 'Na', 'Li'}
ELEM = {
    'H': 1, 'Li': 3, 'B': 5, 'C': 6, 'N': 7, 'O': 8, 'F': 9, 'Na': 11, 'Mg': 12,
    'Al': 13, 'Si': 14, 'P': 15, 'S': 16, 'Cl': 17, 'K': 19, 'Ca': 20, 'Ti': 22,
    'Cr': 24, 'Mn': 25, 'Fe': 26, 'Co': 27, 'Ni': 28, 'Cu': 29, 'Zn': 30, 'Se': 34,
    'Br': 35, 'Ru': 44, 'Rh': 45, 'Pd': 46, 'Ag': 47, 'Sn': 50, 'I': 53, 'Ir': 77,
    'Pt': 78, 'Au': 79, 'Hg': 80,
}
TOK = re.compile(r'\{(i|b|bi|sub|sup):([^{}]*)\}')
FACE = {'': 0, 'b': 1, 'i': 2, 'bi': 3, 'sub': 32, 'sup': 64}

JACS_PALETTE = {
    "pastel_blue": "#D6EAF8",
    "pastel_red": "#FADBD8",
    "pastel_green": "#D5F5E3",
    "pastel_yellow": "#FCF3CF",
    "pastel_purple": "#E8DAEF",
    "pastel_orange": "#FDEBD0",
    "pastel_teal": "#D1F2EB",
    "jacs_blue": "#005AB5",
    "jacs_red": "#DC3220",
    "jacs_green": "#008060",
    "jacs_purple": "#6A3D9A",
}

_EXTRA_NAMED_COLORS = {
    "white": "#FFFFFF",
    "black": "#000000",
    "red": "#DC3220",
    "blue": "#005AB5",
    "green": "#008060",
    "purple": "#6A3D9A",
    "yellow": "#FCF3CF",
    "orange": "#FDEBD0",
    "teal": "#D1F2EB",
    "gray": "#808080",
    "grey": "#808080",
}


def _is_cjk(ch):
    """CJK ideographs, CJK punctuation and full-width forms need the SimSun font entry."""
    return ('\u3000' <= ch <= '\u303f' or '\u3400' <= ch <= '\u9fff' or '\uff00' <= ch <= '\uffef')


CJK_CLASS = r'[\u3000-\u303f\u3400-\u9fff\uff00-\uffef]'
NON_CJK_CLASS = r'[^\u3000-\u303f\u3400-\u9fff\uff00-\uffef]'


def runs(markup, font=3, size=10, base=0, color=None):
    out, pos = [], 0
    for m in TOK.finditer(markup):
        if m.start() > pos:
            out.append((markup[pos:m.start()], base))
        out.append((m.group(2), FACE[m.group(1)] | base))
        pos = m.end()
    if pos < len(markup):
        out.append((markup[pos:], base))
    s = ''
    color_attr = f' color="{color}"' if color is not None else ''
    for t, f in out:
        # Only CJK characters use SimSun (font 5); Latin text, digits and symbols stay in `font`.
        for piece in re.findall(r'(?:%s)+|(?:%s)+' % (CJK_CLASS, NON_CJK_CLASS), t):
            fnt = 5 if _is_cjk(piece[0]) else font
            piece = piece.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            s += f'<s font="{fnt}" size="{size}" face="{f}"{color_attr}>{piece}</s>'
    return s


def formula_markup(label):
    """C10H21 -> C{sub:10}H{sub:21}; leaves already-marked text alone"""
    if '{' in label:
        return label
    return re.sub(r'(?<=[A-Za-z\)])(\d+)', r'{sub:\1}', label)


def _fmt_rgb_component(val_255: int) -> str:
    if val_255 <= 0:
        return '0'
    if val_255 >= 255:
        return '1'
    return f'{val_255 / 255.0:.4f}'.rstrip('0').rstrip('.')


def _load_conformers_module():
    try:
        from cdxml_toolkit.templates import conformers
        return conformers
    except ImportError:
        toolkit_dir = Path(__file__).resolve().parents[3] / 'toolkit'
        if toolkit_dir.is_dir() and str(toolkit_dir) not in sys.path:
            sys.path.insert(0, str(toolkit_dir))
        from cdxml_toolkit.templates import conformers
        return conformers


def _curve_points_for_ring(ring_pts, style='polygon', inset=0.0):
    if not ring_pts:
        return ''
    n = len(ring_pts)
    rcx = sum(p[0] for p in ring_pts) / n
    rcy = sum(p[1] for p in ring_pts) / n
    adjusted = []
    for px, py in ring_pts:
        dx, dy = rcx - px, rcy - py
        dist = math.hypot(dx, dy)
        if inset and dist > 1e-6:
            step = min(float(inset), dist * 0.45)
            px += (dx / dist) * step
            py += (dy / dist) * step
        adjusted.append((px, py))

    if style == 'spline' and n >= 3:
        # Catmull-Rom to cubic Bezier control points around closed ring
        ctrl_pts = []
        for i in range(n):
            p_prev = adjusted[(i - 1) % n]
            p_curr = adjusted[i]
            p_next = adjusted[(i + 1) % n]
            tx = (p_next[0] - p_prev[0]) * 0.16
            ty = (p_next[1] - p_prev[1]) * 0.16
            c_in = (p_curr[0] - tx, p_curr[1] - ty)
            c_out = (p_curr[0] + tx, p_curr[1] + ty)
            ctrl_pts.extend([c_in, p_curr, c_out])
        return ' '.join(f'{x:.2f} {y:.2f}' for x, y in ctrl_pts)

    # Polygon: degenerate cubic handles (p, p, p) per vertex
    poly_pts = [q for p in adjusted for q in (p, p, p)]
    return ' '.join(f'{x:.2f} {y:.2f}' for x, y in poly_pts)


class Fig:
    def __init__(self):
        self.items = []
        self.page = self.items
        self.nid = 1000
        self.bbox = [1e9, 1e9, -1e9, -1e9]
        self._colortable = [('1', '1', '1'), ('0', '0', '0')]
        self._color_map = {(255, 255, 255): '2', (0, 0, 0): '3'}

    def _id(self):
        self.nid += 1
        return self.nid

    def _bb(self, x, y, pad=8):
        b = self.bbox
        b[0] = min(b[0], x - pad); b[1] = min(b[1], y - pad); b[2] = max(b[2], x + pad); b[3] = max(b[3], y + pad)

    def resolve_color(self, color):
        """Resolve a JACS_PALETTE name, #RRGGBB hex string, or integer index into a CDXML colortable index."""
        if color is None:
            return None
        if isinstance(color, int):
            return str(color)
        text = str(color).strip()
        if not text:
            return None
        if text.isdigit():
            return text
        lower = text.lower()
        if lower in JACS_PALETTE:
            text = JACS_PALETTE[lower]
        elif lower in _EXTRA_NAMED_COLORS:
            text = _EXTRA_NAMED_COLORS[lower]
        if text.startswith('#'):
            text = text[1:]
        if len(text) == 3:
            text = ''.join(ch * 2 for ch in text)
        if len(text) != 6:
            raise ValueError(f'Unknown or invalid color specification: {color!r}')
        rgb = (int(text[0:2], 16), int(text[2:4], 16), int(text[4:6], 16))
        if rgb in self._color_map:
            return self._color_map[rgb]
        idx = str(len(self._colortable) + 2)
        self._colortable.append((
            _fmt_rgb_component(rgb[0]),
            _fmt_rgb_component(rgb[1]),
            _fmt_rgb_component(rgb[2]),
        ))
        self._color_map[rgb] = idx
        return idx

    color = resolve_color

    # ------------------------------------------------------------------ molecule
    def mol(self, smiles, at=(100, 100), labels=None, coords=None, rotate=0.0, flip=False, scale=BL,
            displays=None, radicals=(), wedge=True, explicitH=None, center=True, hide_charge_label=False,
            lone_pairs=(), double_pos=None, label_text=None, ring_fills=None, atom_halos=None,
            multi_attachments=None):
        """smiles may contain [*:n] dummy atoms; labels maps n -> label text (e.g. 'C10H21').
        coords: optional list of (x,y) in drawing units (y down) per atom index (overrides layout).
        displays: dict bond_idx -> CDXML Display (WedgeBegin etc., B = bond begin atom).
        label_text: dict atom_idx -> explicit label markup.
        ring_fills: optional list of {'ring_index': 0, 'color': 'pastel_blue', 'style': 'polygon'|'spline', 'inset': 1.0}.
        atom_halos: optional list of {'atoms': [0, 1], 'color': 'pastel_yellow', 'radius': 8.0}.
        multi_attachments: optional list of {'metal_atom': 0, 'ligand_atoms': [1..5], 'bond_display': 'Dash', 'bond_order': 'dative'}."""
        labels = labels or {}
        if isinstance(smiles, str):
            ps = Chem.SmilesParserParams(); ps.removeHs = False
            m = Chem.MolFromSmiles(smiles, ps)
            if m is None:
                raise ValueError(f'Invalid SMILES: {smiles!r}')
        else:
            m = smiles
        try:
            Chem.Kekulize(m, clearAromaticFlags=True)
        except Exception:
            pass
        if coords is None:
            rdDepictor.SetPreferCoordGen(True)
            try:
                rdDepictor.Compute2DCoords(m)
            finally:
                rdDepictor.SetPreferCoordGen(False)
            conf = m.GetConformer()
            pts = [(conf.GetAtomPosition(i).x, -conf.GetAtomPosition(i).y) for i in range(m.GetNumAtoms())]
            ds = [math.dist(pts[b.GetBeginAtomIdx()], pts[b.GetEndAtomIdx()]) for b in m.GetBonds()]
            ds.sort(); med = ds[len(ds) // 2] if ds else 1.0
            if med < 1e-6:
                med = 1.0
            pts = [(x / med * scale, y / med * scale) for x, y in pts]
            if flip:
                pts = [(-x, y) for x, y in pts]
            if rotate:
                c, s = math.cos(math.radians(rotate)), math.sin(math.radians(rotate))
                pts = [(x * c + y * s, -x * s + y * c) for x, y in pts]
            if wedge and displays is None:
                for i, (x, y) in enumerate(pts):
                    conf.SetAtomPosition(i, (x, -y, 0))
                try:
                    Chem.WedgeMolBonds(m, conf)
                except Exception:
                    pass
        else:
            pts = list(coords)
        if center and pts:
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

        # Background decorations (inserted into <page> BEFORE <fragment> so black bonds stay crisp on top)
        bg_elements = []
        if ring_fills:
            atom_rings = list(ring.AtomRings())
            for rf in ring_fills:
                if 'atoms' in rf:
                    r_atoms = [int(idx) for idx in rf['atoms']]
                else:
                    r_idx = int(rf.get('ring_index', 0))
                    if 0 <= r_idx < len(atom_rings):
                        r_atoms = list(atom_rings[r_idx])
                    else:
                        continue
                if len(r_atoms) < 3:
                    continue
                r_pts = [pts[idx] for idx in r_atoms]
                style = str(rf.get('style', 'polygon')).lower()
                inset = float(rf.get('inset', 0.0))
                c_idx = self.resolve_color(rf.get('color', 'pastel_blue'))
                curve_pts_str = _curve_points_for_ring(r_pts, style=style, inset=inset)
                rx1 = min(p[0] for p in r_pts)
                ry1 = min(p[1] for p in r_pts)
                rx2 = max(p[0] for p in r_pts)
                ry2 = max(p[1] for p in r_pts)
                bg_z = len(bg_elements) + 1
                bg_elements.append(
                    f'<curve id="{self._id()}" Closed="yes" FillType="Solid" LineType="None" '
                    f'color="{c_idx}" Z="{bg_z}" BoundingBox="{rx1:.2f} {ry1:.2f} {rx2:.2f} {ry2:.2f}" '
                    f'CurvePoints="{curve_pts_str}"/>'
                )

        if atom_halos:
            for halo in atom_halos:
                h_atoms = halo.get('atoms')
                if h_atoms is None and 'atom' in halo:
                    h_atoms = [halo['atom']]
                if not h_atoms:
                    continue
                r = float(halo.get('radius', 8.0))
                c_idx = self.resolve_color(halo.get('color', 'pastel_yellow'))
                for a_idx in h_atoms:
                    ax, ay = pts[int(a_idx)]
                    self._bb(ax, ay, r + 2)
                    bg_z = len(bg_elements) + 1
                    bg_elements.append(
                        f'<graphic id="{self._id()}" GraphicType="Oval" OvalType="Circle Filled" '
                        f'color="{c_idx}" Z="{bg_z}" '
                        f'BoundingBox="{ax - r:.2f} {ay - r:.2f} {ax + r:.2f} {ay + r:.2f}" '
                        f'Center3D="{ax:.2f} {ay:.2f} 0" '
                        f'MajorAxisEnd3D="{ax + r:.2f} {ay:.2f} 0" '
                        f'MinorAxisEnd3D="{ax:.2f} {ay + r:.2f} 0"/>'
                    )

        for bg_el in reversed(bg_elements):
            self.page.insert(0, bg_el)

        frag_id = self._id()
        xml = [f'<fragment id="{frag_id}" Z="{self._id()}">']
        for i, a in enumerate(m.GetAtoms()):
            x, y = pts[i]; self._bb(x, y)
            sym = a.GetSymbol()
            attrs = f'id="{ids[i]}" Z="{self._id()}" p="{x:.2f} {y:.2f}"'
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
                        cs = '' if not chg or hide_charge_label else ('{sup:+}' if chg == 1 else '{sup:\u2212}' if chg == -1 else '{sup:%d%s}' % (abs(chg), '+' if chg > 0 else '\u2212'))
                        if sym == 'C' and chg:
                            text = sym + hpart + cs if nh else sym + cs
                        else:
                            text = (hpart + sym + cs) if (right and hpart) else (sym + hpart + cs)
            if text is not None:
                just = 'Right' if right and (a.GetAtomicNum() == 0 or text.startswith('H')) else 'Left'
                xml.append(f'<n {attrs}><t p="{x:.2f} {y + 3.5:.2f}" LabelJustification="{just}" LabelAlignment="{just}">{runs(text)}</t></n>')
            else:
                xml.append(f'<n {attrs}/>')

        ma_bonds_xml = []
        if multi_attachments:
            for ma in multi_attachments:
                metal_idx = int(ma['metal_atom'])
                ligand_indices = [int(k) for k in ma['ligand_atoms']]
                if not ligand_indices:
                    continue
                mcx = sum(pts[k][0] for k in ligand_indices) / len(ligand_indices)
                mcy = sum(pts[k][1] for k in ligand_indices) / len(ligand_indices)
                ma_id = self._id()
                att_str = ' '.join(str(ids[k]) for k in ligand_indices)
                xml.append(
                    f'<n id="{ma_id}" Z="{self._id()}" p="{mcx:.2f} {mcy:.2f}" '
                    f'NodeType="MultiAttachment" Attachments="{att_str}"/>'
                )
                b_disp = ma.get('bond_display', 'Dash')
                b_order = ma.get('bond_order', 'dative')
                b_attrs = f'id="{self._id()}" Z="{self._id()}" B="{ids[metal_idx]}" E="{ma_id}"'
                if b_disp:
                    b_attrs += f' Display="{b_disp}"'
                if b_order:
                    b_attrs += f' Order="{b_order}"'
                ma_bonds_xml.append(f'<b {b_attrs}/>')

        for b in m.GetBonds():
            i, j = b.GetBeginAtomIdx(), b.GetEndAtomIdx()
            attrs = f'id="{self._id()}" Z="{self._id()}" B="{ids[i]}" E="{ids[j]}"'
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
        xml.extend(ma_bonds_xml)
        xml.append('</fragment>')
        for i in radicals:
            x, y = pts[i]
            ox, oy = self._free_dir(pts, nb, i)
            self.text(x + ox * 6 - 1.8, y + oy * 6 + 3.5, '\u2022', size=10, align='Left')
        for (i, side) in lone_pairs:
            x, y = pts[i]
            dx = {'right': 11, 'left': -14, 'up': -1.5, 'down': -1.5}[side]
            self.text(x + dx, y + 3.2, '{b::}', size=10, align='Left')
        self.items.append('\n'.join(xml))
        self.last_pts = pts
        self.last_fragment_id = frag_id
        return pts

    add_smiles = mol

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

    # ------------------------------------------------------------------ annotations & power-user primitives
    def text(self, x, y, markup, size=10, align='Center', bold=False, font=3, color=None):
        self._bb(x, y)
        base = 1 if bold else 0
        j = f' Justification="{align}" CaptionJustification="{align}"' if align != 'Left' else ''
        c_idx = self.resolve_color(color)
        c_attr = f' color="{c_idx}"' if c_idx is not None else ''
        # Captions are annotations; without this ChemDraw reads codes such as "B" as atoms on CDX conversion.
        self.items.append(f'<t id="{self._id()}" p="{x:.2f} {y:.2f}"{j}{c_attr} InterpretChemically="no">'
                          f'{runs(markup, font, size, base, color=c_idx)}</t>')

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

    def add_ts_bracket(self, box, superscript='\u2021', bracket_type='Square', lip_size=5.0, object_ids=None):
        """Emit left and right Square bracket graphics, <bracketedgroup>, and top-right superscript (e.g. double dagger)."""
        x1, y1, x2, y2 = float(box[0]), float(box[1]), float(box[2]), float(box[3])
        bx1, bx2 = min(x1, x2), max(x1, x2)
        by1, by2 = min(y1, y2), max(y1, y2)
        lip = float(lip_size)
        self._bb(bx1, by1, 6); self._bb(bx2 + 8, by2, 6)

        left_id = self._id()
        right_id = self._id()
        bg_id = self._id()
        att1_id = self._id()
        att2_id = self._id()

        self.items.append(
            f'<graphic id="{left_id}" BoundingBox="{bx1:.2f} {by1:.2f} {bx1 + lip:.2f} {by2:.2f}" '
            f'GraphicType="Bracket" BracketType="{bracket_type}" LipSize="{lip:g}"/>'
        )
        self.items.append(
            f'<graphic id="{right_id}" BoundingBox="{bx2:.2f} {by1:.2f} {bx2 - lip:.2f} {by2:.2f}" '
            f'GraphicType="Bracket" BracketType="{bracket_type}" LipSize="{lip:g}"/>'
        )
        obj_attr = f' BracketedObjectIDs="{" ".join(str(i) for i in object_ids)}"' if object_ids else ''
        self.items.append(
            f'<bracketedgroup id="{bg_id}"{obj_attr} BracketType="{bracket_type}">'
            f'<bracketattachment id="{att1_id}" GraphicID="{left_id}"/>'
            f'<bracketattachment id="{att2_id}" GraphicID="{right_id}"/>'
            f'</bracketedgroup>'
        )
        if superscript:
            self.text(bx2 + 3.5, by1 + 4.0, str(superscript), size=10, align='Left')
        return bg_id

    def add_orbital(self, cx, cy, orbital_type='pShaded', angle_deg=-90.0, length=18.0, width=7.5, color='jacs_blue'):
        """Emit a native CDXML <graphic GraphicType="Orbital"> lobe at (cx, cy)."""
        cx, cy = float(cx), float(cy)
        length, width = float(length), float(width)
        rad = math.radians(float(angle_deg))
        tip_x = cx + length * math.cos(rad)
        tip_y = cy + length * math.sin(rad)
        perp_rad = rad + math.pi / 2.0
        side_x = cx + width * math.cos(perp_rad)
        side_y = cy + width * math.sin(perp_rad)
        self._bb(cx, cy, max(length, width) + 2)
        self._bb(tip_x, tip_y, width + 2)
        c_idx = self.resolve_color(color)
        c_attr = f' color="{c_idx}"' if c_idx is not None else ''
        oid = self._id()
        self.items.append(
            f'<graphic id="{oid}" GraphicType="Orbital" OrbitalType="{orbital_type}" '
            f'BoundingBox="{cx:.2f} {cy:.2f} {tip_x:.2f} {tip_y:.2f}" '
            f'Center3D="{cx:.2f} {cy:.2f} 0" '
            f'MajorAxisEnd3D="{tip_x:.2f} {tip_y:.2f} 0" '
            f'MinorAxisEnd3D="{side_x:.2f} {side_y:.2f} 0"{c_attr}/>'
        )
        return oid

    def add_interaction(self, p1, p2, style='dashed', color='jacs_blue', label=None, clip_margin=3.5):
        """Draw an endpoint-clipped dashed line for H-bonds, pi-stacking, or TS partial bonds."""
        x1, y1 = float(p1[0]), float(p1[1])
        x2, y2 = float(p2[0]), float(p2[1])
        dist = math.hypot(x2 - x1, y2 - y1)
        if dist > 1e-6:
            ux, uy = (x2 - x1) / dist, (y2 - y1) / dist
            clip = min(float(clip_margin), dist * 0.4)
        else:
            ux, uy, clip = 1.0, 0.0, 0.0
        cx1, cy1 = x1 + ux * clip, y1 + uy * clip
        cx2, cy2 = x2 - ux * clip, y2 - uy * clip
        self._bb(cx1, cy1, 4); self._bb(cx2, cy2, 4)

        c_idx = self.resolve_color(color)
        c_attr = f' color="{c_idx}"' if c_idx is not None else ''
        line_type = 'Solid' if str(style).lower() == 'solid' else 'Dashed'
        gid = self._id()
        self.items.append(
            f'<graphic id="{gid}" GraphicType="Line" LineType="{line_type}" '
            f'BoundingBox="{min(cx1, cx2):.2f} {min(cy1, cy2):.2f} {max(cx1, cx2):.2f} {max(cy1, cy2):.2f}" '
            f'Head3D="{cx2:.2f} {cy2:.2f} 0" Tail3D="{cx1:.2f} {cy1:.2f} 0"{c_attr}/>'
        )
        if label:
            mx = (cx1 + cx2) / 2.0 - uy * 6.0
            my = (cy1 + cy2) / 2.0 + ux * 6.0 + 3.0
            self.text(mx, my, str(label), size=9, align='Center', color=color)
        return gid

    def add_conformer(self, spec_or_template, **kwargs):
        """Insert a 3D conformer or projection template from cdxml_toolkit.templates.conformers."""
        conformers = _load_conformers_module()
        if isinstance(spec_or_template, Mapping):
            conf_spec = dict(spec_or_template)
            conf_spec.update(kwargs)
        else:
            conf_spec = {'template': str(spec_or_template), **kwargs}

        tmpl = str(conf_spec.get('template') or conf_spec.get('scaffold') or 'chair').strip().lower()
        at = conf_spec.get('at') or conf_spec.get('center')
        cx = float(at[0] if isinstance(at, (list, tuple)) and len(at) >= 2 else conf_spec.get('cx', 180.0))
        cy = float(at[1] if isinstance(at, (list, tuple)) and len(at) >= 2 else conf_spec.get('cy', 160.0))

        if tmpl in ('chair', 'chair_cyclohexane'):
            res = conformers.chair_cyclohexane(
                flip=bool(conf_spec.get('flip', False)),
                substituents=conf_spec.get('substituents'),
                cx=cx, cy=cy,
                bond_length=float(conf_spec.get('bond_length', BL)),
            )
        elif tmpl in ('newman', 'newman_projection'):
            res = conformers.newman_projection(
                conformation=str(conf_spec.get('conformation', 'staggered')),
                dihedral_offset=(float(conf_spec['dihedral_offset']) if conf_spec.get('dihedral_offset') is not None else None),
                front=tuple(conf_spec.get('front', ('Me', 'H', 'H'))),
                rear=tuple(conf_spec.get('rear', ('Br', 'H', 'Me'))),
                cx=cx, cy=cy,
                bond_length=float(conf_spec.get('bond_length', 24.0)),
            )
        elif tmpl in ('haworth', 'haworth_pyranose'):
            res = conformers.haworth_pyranose(
                anomer=str(conf_spec.get('anomer', 'beta')),
                substituents=conf_spec.get('substituents'),
                cx=cx, cy=cy,
                bond_length=float(conf_spec.get('bond_length', 18.0)),
            )
        elif tmpl in ('fischer', 'fischer_projection'):
            res = conformers.fischer_projection(
                centers=tuple(conf_spec.get('centers', ({'left': 'H', 'right': 'OH'},))),
                top=str(conf_spec.get('top', 'CHO')),
                bottom=str(conf_spec.get('bottom', 'CH2OH')),
                cx=cx,
                cy=float(at[1] if isinstance(at, (list, tuple)) and len(at) >= 2 else conf_spec.get('cy', 120.0)),
                bond_length=float(conf_spec.get('bond_length', 18.0)),
            )
        elif tmpl in ('norbornane', 'bicyclo_222', 'adamantane', 'bicyclic_cage', 'cage'):
            scaffold_name = str(conf_spec.get('scaffold', 'norbornane' if tmpl in ('bicyclic_cage', 'cage') else tmpl))
            res = conformers.bicyclic_cage(
                scaffold=scaffold_name,
                substituents=conf_spec.get('substituents'),
                cx=cx, cy=cy,
                bond_length=float(conf_spec.get('bond_length', 16.0)),
            )
        else:
            raise ValueError(f'Unknown conformer template {tmpl!r}')

        for a in res.get('atoms', ()):
            self._bb(float(a['x']), float(a['y']), 12)
        for g_xml in reversed(res.get('graphics_xml', ())):
            self.page.insert(0, g_xml)
        self.items.append(res['fragment_xml'])
        return res

    def to_cdxml(self):
        b = self.bbox
        # Root BoundingBox: ChemDraw writes one, and Office embedding sizes the OLE object from it.
        box = f' BoundingBox="{b[0]:.2f} {b[1]:.2f} {b[2]:.2f} {b[3]:.2f}"' if b[0] < b[2] and b[1] < b[3] else ''
        colors_xml = ''.join(f'<color r="{r}" g="{g}" b="{bl}"/>' for r, g, bl in self._colortable)
        head = ('<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE CDXML SYSTEM "http://www.cambridgesoft.com/xml/cdxml.dtd">\n'
                f'<CDXML{box} BondLength="14.4" LabelFont="3" LabelSize="10" LabelFace="96" CaptionFont="3" CaptionSize="10" '
                'LineWidth="0.6" BoldWidth="2" HashSpacing="2.5" MarginWidth="1.6" BondSpacing="18" ChainAngle="120" '
                'LabelJustification="Auto" CaptionJustification="Left" color="0" bgcolor="1">'
                f'<colortable>{colors_xml}</colortable>'
                '<fonttable><font id="3" charset="iso-8859-1" name="Arial"/><font id="5" charset="Unicode" name="SimSun"/></fonttable>'
                '<page id="1">\n')
        return head + '\n'.join(self.items) + '\n</page></CDXML>\n'

    def write(self, path):
        Path(path).write_text(self.to_cdxml(), encoding='utf-8')
        return Path(path)


Doc = Fig


def build_from_spec(spec_path, output_path=None):
    """Build a CDXML from a JSON spec (or dict); coordinates are points, x right, y down.

    {"objects": [
      {"type": "molecule", "smiles": "[*:1]CC(=O)O", "at": [100, 80], "labels": {"1": "C10H21"},
       "rotate": 0, "flip": false, "displays": {"0": "WedgeBegin"}, "radicals": [], "lone_pairs": [[2, "right"]],
       "ring_fills": [{"ring_index": 0, "color": "pastel_blue", "style": "polygon", "inset": 1.0}],
       "atom_halos": [{"atoms": [0, 1], "color": "pastel_yellow", "radius": 8.0}],
       "multi_attachments": [{"metal_atom": 0, "ligand_atoms": [1, 2, 3, 4, 5], "bond_display": "Dash", "bond_order": "dative"}]},
      {"type": "ts_bracket", "box": [60, 40, 140, 120], "superscript": "\u2021"},
      {"type": "orbital", "cx": 100, "cy": 80, "orbital_type": "pShaded", "angle_deg": -90, "color": "jacs_blue"},
      {"type": "interaction", "from": [120, 80], "to": [170, 80], "style": "dashed", "color": "jacs_blue", "label": "2.1 A"},
      {"type": "conformer", "template": "chair", "flip": false, "at": [180, 160]},
      {"type": "text", "at": [100, 130], "text": "{b:A} (note)", "size": 10, "align": "Center", "bold": false},
      {"type": "arrow", "from": [150, 80], "to": [200, 80], "kind": "forward"},
      {"type": "box", "from": [10, 10], "to": [60, 40], "round": true},
      {"type": "label_box", "at": [100, 150], "text": "B"}
    ]}
    """
    if isinstance(spec_path, Mapping):
        spec = dict(spec_path)
    else:
        spec = json.loads(Path(spec_path).read_text(encoding='utf-8-sig'))
    if not isinstance(spec, dict) or not isinstance(spec.get('objects'), list):
        raise ValueError('a spec is a JSON object with an "objects" list')
    fig = Fig()
    for o in spec['objects']:
        kind = o['type']
        if kind == 'molecule':
            fig.mol(o['smiles'], at=tuple(o.get('at', (100, 100))),
                    labels={int(k): v for k, v in (o.get('labels') or {}).items()},
                    coords=[tuple(pt) for pt in o['coords']] if 'coords' in o else None,
                    rotate=o.get('rotate', 0.0), flip=o.get('flip', False),
                    displays={int(k): v for k, v in o['displays'].items()} if 'displays' in o else None,
                    radicals=tuple(o.get('radicals', ())), lone_pairs=[tuple(x) for x in o.get('lone_pairs', ())],
                    hide_charge_label=o.get('hide_charge_label', False),
                    ring_fills=o.get('ring_fills'),
                    atom_halos=o.get('atom_halos'),
                    multi_attachments=o.get('multi_attachments'))
        elif kind == 'text':
            fig.text(*o['at'], o['text'], size=o.get('size', 10), align=o.get('align', 'Center'),
                     bold=o.get('bold', False), color=o.get('color'))
        elif kind == 'arrow':
            fig.arrow(*o['from'], *o['to'], kind=o.get('kind', 'forward'))
        elif kind == 'box':
            fig.box(*o['from'], *o['to'], round_=o.get('round', True))
        elif kind == 'label_box':
            fig.label_box(*o['at'], o['text'], w=o.get('width'))
        elif kind == 'ts_bracket':
            box = o.get('box') or (*o['from'], *o['to'])
            fig.add_ts_bracket(
                box,
                superscript=o.get('superscript', '\u2021'),
                bracket_type=o.get('bracket_type', 'Square'),
                lip_size=o.get('lip_size', 5.0),
                object_ids=o.get('object_ids'),
            )
        elif kind == 'orbital':
            at = o.get('at', (o.get('cx', 100.0), o.get('cy', 100.0)))
            fig.add_orbital(
                at[0], at[1],
                orbital_type=o.get('orbital_type', 'pShaded'),
                angle_deg=o.get('angle_deg', -90.0),
                length=o.get('length', 18.0),
                width=o.get('width', 7.5),
                color=o.get('color', 'jacs_blue'),
            )
        elif kind == 'interaction':
            p1 = o.get('from') or o['p1']
            p2 = o.get('to') or o['p2']
            fig.add_interaction(
                p1, p2,
                style=o.get('style', 'dashed'),
                color=o.get('color', 'jacs_blue'),
                label=o.get('label'),
                clip_margin=o.get('clip_margin', 3.5),
            )
        elif kind in ('conformer', 'chair', 'newman', 'haworth', 'fischer', 'norbornane', 'bicyclo_222', 'adamantane'):
            conf_spec = dict(o)
            if kind != 'conformer' and 'template' not in conf_spec:
                conf_spec['template'] = kind
            fig.add_conformer(conf_spec)
        else:
            raise ValueError(f'Unknown object type {kind!r}')
    if output_path is not None:
        return fig.write(output_path)
    return fig.to_cdxml()
