"""Draw a compiled Markush graph as native-style CDXML.

The CDXML is the display layer.  Readers (RDKit included) turn generic
labels into carbon and ignore multi-attachment nodes, so chemistry is taken
from the spec/CXSMILES, never from reading this file back.

Layout (points, x right, y down)::

    {"coords": {"ind:C2": [x, y], ...},
     "circles": {"ringC": {"center": [x, y], "radius": r}},
     "groups": {"RB": {"anchor": [x, y], "label": [x, y]}},
     "h_labels": {"nh": [x, y]},          # centre of a drawn H next to N/O

     "style": {"bond_length": 15, "font_size": 11, "line_width": 0.9}}

Missing coordinates are filled by RDKit coordinate generation.
"""
from __future__ import annotations

import math
from xml.sax.saxutils import escape

from rdkit import Chem
from rdkit.Chem import rdDepictor

from .compile import Graph, cx_label
from .spec import label_runs

FACE = {'normal': 0, 'sup': 64, 'sub': 32}
SYMBOL = {6: 'C', 7: 'N', 8: 'O', 16: 'S', 15: 'P', 9: 'F', 17: 'Cl', 35: 'Br', 53: 'I', 5: 'B', 14: 'Si'}
# Arial advance widths in em, enough to centre the attachment character
_WIDE = set('MW')
_NARROW = set('il.,;:!|')


def _char_w(ch: str, size: float) -> float:
    if ch in '()[]':
        return 0.333 * size
    if ch in _WIDE:
        return 0.85 * size
    if ch in _NARROW:
        return 0.25 * size
    if ch.isupper():
        return 0.68 * size
    return 0.55 * size


def _runs_width(runs, size):
    return sum(_char_w(c, size * (1 if kind == 'normal' else 0.75)) for text, kind in runs for c in text)


def _label_node_x(x, runs, size, display, toward):
    """Node x that puts the label's first letter at ``x`` after ChemDraw places it.

    Measured on native renders of one-bond labels: a bond within about 45 degrees
    of horizontal makes ChemDraw centre the first (Left) or last (Right)
    character on the node and ignore the stored text position; steeper bonds,
    and labels with several bonds, keep the text where it is put.
    """
    vx, vy = toward
    angle = math.degrees(math.atan2(abs(vy), abs(vx)))
    chars = [(c, size * (1 if kind == 'normal' else 0.75)) for text, kind in runs for c in text]
    if display == 'Right' and angle < 25:
        width = sum(_char_w(c, s) for c, s in chars)
        return x - _anchor_offset(runs, size) + width - _char_w(*chars[-1]) / 2
    if display != 'Right' and angle < 45 and not chars[0][0].isalnum():
        return x - _anchor_offset(runs, size) + _char_w(*chars[0]) / 2
    return x


def _anchor_offset(runs, size):
    """x distance from text start to the centre of the first letter (skips '(')."""
    x = 0.0
    for text, kind in runs:
        s = size * (1 if kind == 'normal' else 0.75)
        for c in text:
            if c.isalnum():
                return x + _char_w(c, s) / 2
            x += _char_w(c, s)
    return x / 2


def default_style(style=None):
    out = {'bond_length': 15.0, 'font_size': 11.0, 'line_width': 0.9, 'bond_spacing': 18.0}
    out.update({k: v for k, v in (style or {}).items() if v is not None})
    return out


def auto_layout(graph: Graph, style=None) -> dict:
    """RDKit CoordGen coordinates for atoms the layout does not place."""
    style = default_style(style)
    skip = {g['star'] for g in graph.groups} | {g['label_atom'] for g in graph.groups}
    mol = Chem.RWMol(graph.mol)
    for idx in sorted(skip, reverse=True):
        mol.RemoveAtom(idx)
    keep = [i for i in range(graph.mol.GetNumAtoms()) if i not in skip]
    previous = rdDepictor.GetPreferCoordGen()  # process-wide setting; restore it
    rdDepictor.SetPreferCoordGen(True)
    try:
        rdDepictor.Compute2DCoords(mol)
    finally:
        rdDepictor.SetPreferCoordGen(previous)
    conf = mol.GetConformer()
    lengths = [(conf.GetAtomPosition(b.GetBeginAtomIdx()) - conf.GetAtomPosition(b.GetEndAtomIdx())).Length()
               for b in mol.GetBonds()]
    scale = style['bond_length'] / (sorted(lengths)[len(lengths) // 2] if lengths else 1.0)
    coords = {}
    for new, old in enumerate(keep):
        p = conf.GetAtomPosition(new)
        coords[graph.atoms[old]['ref']] = [p.x * scale, -p.y * scale]
    xs = [c[0] for c in coords.values()]
    ys = [c[1] for c in coords.values()]
    dx, dy = 40 - min(xs), 40 - min(ys)
    return {'coords': {k: [x + dx, y + dy] for k, (x, y) in coords.items()}, 'style': style}


def _circumcircle(a, b, c):
    (ax, ay), (bx, by), (cx, cy) = a, b, c
    d = 2 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
    if abs(d) < 1e-9:
        return None
    ux = ((ax**2 + ay**2) * (by - cy) + (bx**2 + by**2) * (cy - ay) + (cx**2 + cy**2) * (ay - by)) / d
    uy = ((ax**2 + ay**2) * (cx - bx) + (bx**2 + by**2) * (ax - cx) + (cx**2 + cy**2) * (bx - ax)) / d
    return (ux, uy), math.hypot(ax - ux, ay - uy)


def _angle(center, p):
    return math.atan2(p[1] - center[1], p[0] - center[0])


def _arc_points(center, r, a0, a1):
    """Cubic Bezier anchors/handles in ChemDraw CurvePoints order, angle a0 -> a1 (y down)."""
    sweep = a1 - a0
    n = max(1, math.ceil(abs(sweep) / (math.pi / 4)))
    step = sweep / n
    k = 4 / 3 * math.tan(step / 4) * r
    pts = []
    for i in range(n + 1):
        a = a0 + i * step
        x, y = center[0] + r * math.cos(a), center[1] + r * math.sin(a)
        tx, ty = -math.sin(a), math.cos(a)
        pts += [(x - k * tx, y - k * ty), (x, y), (x + k * tx, y + k * ty)]
    return pts


def _sweep_avoiding(center, a_from, a_to, avoid):
    """Signed sweep from a_from to a_to that does not pass the angles in ``avoid``."""
    def norm(a):
        return a % (2 * math.pi)
    ccw = norm(a_to - a_from)
    hits = [norm(a - a_from) for a in avoid]
    if all(not (0 < h < ccw) for h in hits):
        return ccw
    return ccw - 2 * math.pi


class _Doc:
    def __init__(self, style):
        self.style = style
        self.next_id = 100
        self.nodes, self.bonds, self.extras = [], [], []

    def nid(self):
        self.next_id += 1
        return self.next_id

    def runs_xml(self, runs, size):
        return ''.join(f'<s font="3" size="{size:g}" face="{FACE[k]}">{escape(t)}</s>' for t, k in runs)

    def label_t(self, x, y, runs):
        size = self.style['font_size']
        tx = x - _anchor_offset(runs, size)
        ty = y + 0.36 * size
        return (f'<t p="{tx:.2f} {ty:.2f}" LabelJustification="Left" LabelAlignment="Left" '
                f'InterpretChemically="no">{self.runs_xml(runs, size)}</t>')

    def node(self, x, y, element=None, runs=None, generic=None, extra='', display=None, toward=None):
        i = self.nid()
        tx, ty = x, y
        if runs and display and toward is not None:
            x = _label_node_x(x, runs, self.style['font_size'], display, toward)
        attrs = f'id="{i}" p="{x:.2f} {y:.2f}"'
        if element and element != 6:
            attrs += f' Element="{element}"'
        if generic is not None:
            attrs += f' NodeType="GenericNickname" GenericNickname="{escape(generic)}"'
        if extra:
            attrs += ' ' + extra
        if display:
            # Left: first character on the node; Right: last character.  Without it ChemDraw
            # reverses multi-part labels ("q(R^B)") when the bond arrives from the right.
            attrs += f' LabelDisplay="{display}"'
        body = self.label_t(tx, ty, runs) if runs else ''
        self.nodes.append(f'<n {attrs}>{body}</n>')
        return i

    def bond(self, a, b, order=1):
        o = f' Order="{order}"' if order != 1 else ''
        self.bonds.append(f'<b id="{self.nid()}" B="{a}" E="{b}"{o}/>')

    def text(self, x, y, runs, center=True):
        size = self.style['font_size']
        tx = x - (_runs_width(runs, size) / 2 if center else 0)
        self.extras.append(f'<t id="{self.nid()}" p="{tx:.2f} {y + 0.36 * size:.2f}" '
                           f'InterpretChemically="no">{self.runs_xml(runs, size)}</t>')

    def circle(self, c, r):
        cx, cy = c
        self.extras.append(
            f'<graphic id="{self.nid()}" GraphicType="Oval" OvalType="Circle" '
            f'BoundingBox="{cx - r:.2f} {cy - r:.2f} {cx + r:.2f} {cy + r:.2f}" '
            f'Center3D="{cx:.2f} {cy:.2f} 0" MajorAxisEnd3D="{cx + r:.2f} {cy:.2f} 0" '
            f'MinorAxisEnd3D="{cx:.2f} {cy + r:.2f} 0"/>')

    def arc(self, c, r, a0, sweep):
        pts = _arc_points(c, r, a0, a0 + sweep)
        flat = ' '.join(f'{x:.2f} {y:.2f}' for x, y in pts)
        self.extras.append(f'<curve id="{self.nid()}" CurvePoints="{flat}" FillType="None" '
                           f'LineWidth="{self.style["line_width"]}"/>')


def to_points(layout: dict | None) -> dict:
    """Convert a ``"units": "px"`` layout (image pixels) to points with ``scale``/``offset``."""
    layout = dict(layout or {})
    if layout.get('units') != 'px':
        return layout
    s = float(layout.get('scale', 0.45))
    ox, oy = layout.get('offset', [20, 10])
    P = lambda p: [p[0] * s + ox, p[1] * s + oy]
    out = {'style': layout.get('style'), 'coords': {k: P(v) for k, v in (layout.get('coords') or {}).items()}}
    out['circles'] = {k: {'center': P(v['center']), 'radius': v['radius'] * s}
                      for k, v in (layout.get('circles') or {}).items()}
    out['groups'] = {k: {kk: P(vv) for kk, vv in v.items()} for k, v in (layout.get('groups') or {}).items()}
    out['h_labels'] = {k: P(v) for k, v in (layout.get('h_labels') or {}).items()}
    return out


def write_cdxml(graph: Graph, layout: dict | None = None) -> str:
    layout = to_points(layout)
    style = default_style(layout.get('style'))
    auto = auto_layout(graph, style)
    coords = {**auto['coords'], **{k: list(v) for k, v in (layout.get('coords') or {}).items()}}
    doc = _Doc(style)
    bl = style['bond_length']
    ring_refs = {r['ref']: r for r in graph.rings}
    group_refs = {g['group'] for g in graph.groups} | {f"{g['group']}:attach" for g in graph.groups}
    node_of: dict[str, int] = {}
    # ring geometry
    circles = {}
    for ring in graph.rings:
        given = (layout.get('circles') or {}).get(ring['ref'])
        if given:
            circles[ring['ref']] = (tuple(given['center']), float(given['radius']))
        elif ring['members']:
            pts = [coords[m] for m in ring['members']]
            three = pts if len(pts) >= 3 else [pts[0], coords[ring['ref']], pts[-1]]
            cc = _circumcircle(*three[:3]) or (tuple(coords[ring['ref']]), 0.8 * bl)
            circles[ring['ref']] = cc
        else:
            circles[ring['ref']] = (tuple(coords[ring['ref']]), 0.8 * bl)
    def display_for(i, x, y, extra_points=()):
        pts = list(extra_points)
        for nbr in graph.mol.GetAtomWithIdx(i).GetNeighbors():
            ref = graph.atoms[nbr.GetIdx()]['ref']
            if ref in ring_refs:
                pts.append(circles[ref][0])
            elif ref in coords:
                pts.append(coords[ref])
        if not pts:
            return 'Left', None
        vx = sum(p[0] - x for p in pts) / len(pts)
        vy = sum(p[1] - y for p in pts) / len(pts)
        return ('Right' if vx > 0.8 * math.hypot(vx, vy) else 'Left'), (vx, vy)

    # atoms
    for i, info in enumerate(graph.atoms):
        ref = info['ref']
        if ref in ring_refs or ref in group_refs:
            continue
        x, y = coords[ref]
        atom = graph.mol.GetAtomWithIdx(i)
        if info.get('kind') == 'generic':
            display, toward = display_for(i, x, y)
            if graph.mol.GetAtomWithIdx(i).GetDegree() != 1:
                toward = None
            node_of[ref] = doc.node(x, y, runs=label_runs(info['label']), generic=cx_label(info),
                                    display=display, toward=toward)
        elif atom.GetAtomicNum() != 6:
            sym = SYMBOL.get(atom.GetAtomicNum(), atom.GetSymbol())
            node_of[ref] = doc.node(x, y, element=atom.GetAtomicNum(), runs=[(sym, 'normal')],
                                    extra=f'NumHydrogens="{atom.GetTotalNumHs()}"')
        else:
            node_of[ref] = doc.node(x, y)
    # explicit H captions: ChemDraw would put H on the side without bonds, which is wrong next to
    # a ring arc, so the H is drawn as a caption opposite the drawn neighbours.
    for i, info in enumerate(graph.atoms):
        atom = graph.mol.GetAtomWithIdx(i)
        if info['ref'] not in node_of or atom.GetAtomicNum() in (0, 6) or not atom.GetTotalNumHs():
            continue
        x, y = coords[info['ref']]
        vx = vy = 0.0
        for nbr in atom.GetNeighbors():
            ref = graph.atoms[nbr.GetIdx()]['ref']
            if ref in ring_refs:
                c, _ = circles[ref]
                p = c
            else:
                p = coords[ref]
            d = math.hypot(p[0] - x, p[1] - y) or 1
            vx += (p[0] - x) / d
            vy += (p[1] - y) / d
        d = math.hypot(vx, vy) or 1
        h = 'H' if atom.GetTotalNumHs() == 1 else f'H{atom.GetTotalNumHs()}'
        hx, hy = (layout.get('h_labels') or {}).get(info['ref']) or             (x - vx / d * 0.95 * style['font_size'], y - vy / d * 0.95 * style['font_size'])
        doc.text(hx, hy, [(h, 'normal')])
    # bonds
    perimeter = {}

    def on_ring(ring_ref, toward):
        c, r = circles[ring_ref]
        a = _angle(c, toward)
        px, py = c[0] + r * math.cos(a), c[1] + r * math.sin(a)
        return doc.node(px, py)

    arc_bonds = []
    for bond in graph.bonds:
        a, b = bond['a'], bond['b']
        if a in ring_refs or b in ring_refs:
            ring, other = (a, b) if a in ring_refs else (b, a)
            if other in ring_refs[ring]['members']:
                continue  # ring closure: drawn as the arc
            node = on_ring(ring, coords[other])
            perimeter[(ring, other)] = node
            doc.bond(node_of[other], node, bond['order'])
            continue
        if bond.get('display') == 'arc':
            arc_bonds.append(bond)
            continue
        doc.bond(node_of[a], node_of[b], bond['order'])
    # ring graphics
    for ring in graph.rings:
        c, r = circles[ring['ref']]
        members = ring['members']
        if not members:
            doc.circle(c, r)
        else:
            ang = {m: _angle(c, coords[m]) for m in members}
            # closure arc from last member to first member, away from the other members
            others = [ang[m] for m in members[1:-1]]
            doc.arc(c, r, ang[members[-1]], _sweep_avoiding(c, ang[members[-1]], ang[members[0]], others))
            for bond in arc_bonds:
                if bond['a'] in ang and bond['b'] in ang:
                    rest = [ang[m] for m in members if m not in (bond['a'], bond['b'])]
                    doc.arc(c, r, ang[bond['a']], _sweep_avoiding(c, ang[bond['a']], ang[bond['b']], rest))
        doc.text(c[0], c[1], label_runs(ring['label']))
    # variable-position groups
    centre = (sum(v[0] for v in coords.values()) / len(coords), sum(v[1] for v in coords.values()) / len(coords))
    for g in graph.groups:
        given = (layout.get('groups') or {}).get(g['group']) or {}
        runs = label_runs(g['label'])
        on_rings = [r for r in g['on'] if r in ring_refs]
        if on_rings:
            ring = on_rings[0]
            c, r = circles[ring]
            if given.get('label'):
                lx, ly = given['label']
            else:
                d = math.hypot(c[0] - centre[0], c[1] - centre[1]) or 1
                lx, ly = c[0] + (c[0] - centre[0]) / d * (r + 1.3 * bl), c[1] + (c[1] - centre[1]) / d * (r + 1.3 * bl)
            node = on_ring(ring, (lx, ly))
            lab = doc.node(lx, ly, runs=runs, generic=g['group'], toward=(c[0] - lx, c[1] - ly),
                           display='Right' if c[0] - lx > 0.8 * math.hypot(c[0] - lx, c[1] - ly) else 'Left')
            doc.bond(node, lab)
            continue
        pts = [coords[r] for r in g['on']]
        ax_, ay_ = given.get('anchor') or (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))
        if given.get('label'):
            lx, ly = given['label']
        else:
            frag = g['on'][0].split(':')[0]
            ring_pts = [v for k, v in coords.items() if k.startswith(frag + ':')]
            fc = (sum(p[0] for p in ring_pts) / len(ring_pts), sum(p[1] for p in ring_pts) / len(ring_pts))
            d = math.hypot(ax_ - fc[0], ay_ - fc[1]) or 1
            lx, ly = ax_ + (ax_ - fc[0]) / d * 1.6 * bl, ay_ + (ay_ - fc[1]) / d * 1.6 * bl
        ma = doc.nid()
        ids = ' '.join(str(node_of[r]) for r in g['on'])
        doc.nodes.append(f'<n id="{ma}" p="{ax_:.2f} {ay_:.2f}" NodeType="MultiAttachment" Attachments="{ids}"/>')
        lab = doc.node(lx, ly, runs=runs, generic=g['group'], toward=(ax_ - lx, ay_ - ly),
                       display='Right' if ax_ - lx > 0.8 * math.hypot(ax_ - lx, ay_ - ly) else 'Left')
        doc.bond(ma, lab)
    fs = style['font_size']
    frag = f'<fragment id="{doc.nid()}">' + ''.join(doc.nodes) + ''.join(doc.bonds) + '</fragment>'
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<!DOCTYPE CDXML SYSTEM "http://www.cambridgesoft.com/xml/cdxml.dtd">\n'
        f'<CDXML BondLength="{bl:.2f}" LineWidth="{style["line_width"]}" BoldWidth="{style["line_width"] * 2.6:.2f}" '
        f'MarginWidth="{style["line_width"] * 2:.2f}" BondSpacing="{style["bond_spacing"]}" '
        f'HashSpacing="2.7" LabelFont="3" CaptionFont="3" LabelSize="{fs:g}" CaptionSize="{fs:g}" LabelFace="96">'
        '<fonttable><font id="3" charset="iso-8859-1" name="Arial"/></fonttable>'
        '<colortable><color r="1" g="1" b="1"/><color r="0" g="0" b="0"/></colortable>'
        f'<page id="{doc.nid()}">{frag}{"".join(doc.extras)}</page></CDXML>\n')
