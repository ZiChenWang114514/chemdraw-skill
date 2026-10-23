"""Turn a detected image graph plus label transcriptions into a spec and layout.

The model only reads text: ``{"T1": "(R^{A})_{n}", "T5": "N", ...}``.  Every
connection, ring membership, attachment set and coordinate comes from the
image graph of :mod:`layout_detect`, so the draft keeps the source geometry.

Rules
- ``N``, ``NH``, ``O``, ``Cl`` ... are atoms with that element and H count;
  any other text is a generic label (``R^{1}``, ``L``, ``G^{2}``).
- A circle with a letter at its centre is a variable ring.  When text atoms
  sit on the circle, they and the bonded unlabelled points on the circle are
  drawn members, ordered around the circle; the widest gap is the open part
  of the ring.  Otherwise points on the circle are attachments to the ring.
- ``(X)_{n}`` is a variable-position group.  A line from it to a circle puts
  it on that ring; a line ending inside a drawn ring lets it sit on any ring
  atom of that ring that has no other substituent.
"""
from __future__ import annotations

import math
import re

import cv2
import numpy as np
from rdkit import Chem

from .spec import ELEMENTS, plain_label

_ELEMENT_RE = re.compile(r'^(?:(Cl|Br|Si|[BCNOSPFI])(?:H_?\{?(\d?)\}?)?|H_?\{?(\d?)\}?(Cl|Br|Si|[BCNOSPFI]))$')
_GROUP_RE = re.compile(r'^\((.+)\)_\{?([A-Za-z0-9]+)\}?$')


def classify(text: str):
    """('element', symbol, h) | ('group', inner, count) | ('generic', label)."""
    t = text.strip().replace(' ', '')
    m = _ELEMENT_RE.match(t)
    if m:
        sym = m.group(1) or m.group(4)
        hs = m.group(2) if m.group(1) else m.group(3)
        has_h = 'H' in t.replace(sym, '', 1) if sym != 'H' else False
        if sym in ELEMENTS:
            return ('element', sym, (int(hs) if hs else 1) if has_h else 0)
    m = _GROUP_RE.match(t)
    if m:
        return ('group', m.group(1), m.group(2))
    return ('generic', t)


def _ink(image_path, upscale):
    gray = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
    if upscale > 1:
        gray = cv2.resize(gray, None, fx=upscale, fy=upscale, interpolation=cv2.INTER_CUBIC)
    _, bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    return bw > 0


def _chord_drawn(ink, a_box, b_box, a, b, pad) -> bool:
    """Is there a straight line between two labels (outside both boxes)?"""
    pts = [(a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])) for t in np.linspace(0, 1, 80)]
    def inside(p, box):
        return box[0] - pad <= p[0] <= box[2] + pad and box[1] - pad <= p[1] <= box[3] + pad
    free = [p for p in pts if not inside(p, a_box) and not inside(p, b_box)]
    if len(free) < 4:
        return False
    hits = sum(1 for x, y in free if 0 <= int(y) < ink.shape[0] and 0 <= int(x) < ink.shape[1]
               and ink[max(0, int(y) - 1):int(y) + 2, max(0, int(x) - 1):int(x) + 2].any())
    return hits / len(free) >= 0.85


def draft(graph: dict, texts: dict[str, str], bond_length_pt: float = 14.4) -> dict:
    """Return ``{"spec": ..., "layout": ..., "notes": [...], "missing": [...]}``."""
    labels = {l['id']: l for l in graph['labels']}
    missing = sorted((set(labels) - set(texts)), key=lambda s: int(s[1:]))
    if missing:
        return {'spec': None, 'layout': None, 'missing': missing,
                'notes': [f'Transcribe every label box first; missing {", ".join(missing)}.']}
    notes = []
    pos = {v['id']: v['p'] for v in graph['vertices']}
    pos.update({l['id']: l['anchor'] for l in graph['labels']})
    on_circle = {v['id']: v['on_circle'] for v in graph['vertices']}
    on_circle.update({l['id']: l['on_circle'] for l in graph['labels']})
    edges = [dict(e) for e in graph['edges']]
    nbrs: dict[str, list] = {}
    for e in edges:
        nbrs.setdefault(e['a'], []).append(e['b'])
        nbrs.setdefault(e['b'], []).append(e['a'])
    kind = {tid: classify(texts[tid]) for tid in labels}
    circles = graph['circles']
    char = graph['char_px']

    # ring letters
    ring_of_circle = {}
    for tid, lab in labels.items():
        ci = lab.get('in_circle')
        if ci is not None and ci not in ring_of_circle:
            ring_of_circle[ci] = tid
    for ci in range(len(circles)):
        if ci not in ring_of_circle:
            notes.append(f'circle {ci} has no letter inside; it was ignored.')
    ring_ids = {ci: f'ring{plain_label(texts[t])}' for ci, t in ring_of_circle.items()}
    dropped: set[str] = set(ring_of_circle.values())
    drop_edges: set[frozenset] = set()

    def inside(p, ci):
        return math.dist(p, circles[ci]['center']) < circles[ci]['radius'] - 0.4 * char

    # line ends that poke into a ring circle (decoration of a ring substituent)
    for v in graph['vertices']:
        vid = v['id']
        if len(nbrs.get(vid, [])) == 1 and v['on_circle'] is None:
            for ci in ring_ids:
                other = nbrs[vid][0]
                if inside(v['p'], ci) and on_circle.get(other) == ci:
                    dropped.add(vid)
                    drop_edges.add(frozenset((vid, other)))

    def live(x):
        return [n for n in nbrs.get(x, []) if n not in dropped and frozenset((x, n)) not in drop_edges]

    groups_tid = [t for t in labels if kind[t][0] == 'group']
    atoms, bonds, vp, layout_groups = [], [], [], {}
    ring_members = {ci: [] for ci in ring_ids}
    ring_attach = {}  # perimeter vertex -> ring circle
    for ci in ring_ids:
        texts_on = [t for t, l in labels.items() if l.get('on_circle') == ci and kind[t][0] != 'group'
                    and t not in dropped]
        verts_on = [v['id'] for v in graph['vertices'] if v['on_circle'] == ci and v['id'] not in dropped]
        if texts_on:
            ring_members[ci] = list(texts_on)
            for vid in verts_on:
                if any(n not in groups_tid for n in live(vid)):
                    ring_members[ci].append(vid)
                else:
                    ring_attach[vid] = ci
        else:
            for vid in verts_on:
                ring_attach[vid] = ci

    # variable-position groups
    ring_atoms = _drawn_rings(graph, edges, dropped, set(groups_tid))
    for gid in groups_tid:
        inner, count = kind[gid][1], kind[gid][2]
        name = plain_label(inner)
        ends = live(gid)
        dropped.add(gid)
        if len(ends) != 1:
            notes.append(f'{gid} {texts[gid]!r}: expected one line to the group, found {len(ends)}.')
            continue
        end = ends[0]
        entry = {'group': name, 'label': texts[gid], 'count': count}
        ci = on_circle.get(end)
        if end in ring_attach or (ci is not None and ci in ring_ids and end not in sum(ring_members.values(), [])):
            ci = ring_attach.pop(end, ci)
            entry['on'] = [ring_ids[ci]]
            dropped.add(end)
            layout_groups[name] = {'label': pos[gid]}
        elif not live(end):  # free end inside a drawn ring
            ring = next((r for r in ring_atoms if cv2.pointPolygonTest(
                np.array([pos[a] for a in r], np.float32).reshape(-1, 1, 2), tuple(map(float, pos[end])), False) > 0),
                None)
            if ring is None:
                notes.append(f'{gid} {texts[gid]!r}: the line from the group does not end inside a ring.')
                continue
            free = [a for a in ring if a not in labels and
                    len([n for n in live(a) if n != end]) == 2]
            entry['on'] = free
            dropped.add(end)
            layout_groups[name] = {'anchor': pos[end], 'label': pos[gid]}
        else:
            notes.append(f'{gid} {texts[gid]!r} is bonded like an ordinary substituent; drawn as a plain label.')
            kind[gid] = ('generic', texts[gid])
            dropped.discard(gid)
            continue
        vp.append(entry)

    coords, h_labels = {}, {}
    for v in graph['vertices']:
        if v['id'] in dropped or v['id'] in ring_attach:
            continue
        atoms.append({'id': v['id'], 'element': 'C'})
        coords[v['id']] = v['p']
    for tid, lab in labels.items():
        if tid in dropped:
            continue
        k = kind[tid]
        if k[0] == 'element':
            atom = {'id': tid, 'element': k[1]}
            if k[2] or k[1] != 'C':
                atom['h'] = k[2]
            atoms.append(atom)
            others = [q for q in lab.get('parts') or [] if not (q[0] <= lab['anchor'][0] <= q[2]
                                                                and q[1] <= lab['anchor'][1] <= q[3])]
            if k[2] and others:  # where the image puts the H (below, left or right of the atom)
                hb = others[0] if len(others) == 1 else [min(q[0] for q in others), min(q[1] for q in others),
                                                         max(q[2] for q in others), max(q[3] for q in others)]
                h_labels[tid] = [(hb[0] + hb[2]) / 2, (hb[1] + hb[3]) / 2]
        else:
            atoms.append({'id': tid, 'label': texts[tid].strip()})
        coords[tid] = lab['anchor']

    def ref(x):
        return ring_ids[ring_attach[x]] if x in ring_attach else x

    seen = set()
    for e in edges:
        a, b = e['a'], e['b']
        if frozenset((a, b)) in drop_edges or a in dropped or b in dropped:
            continue
        ra, rb = ref(a), ref(b)
        if ra == rb or frozenset((ra, rb)) in seen:
            continue
        seen.add(frozenset((ra, rb)))
        bonds.append([ra, rb] + ([e['order']] if e['order'] > 1 else []))

    ink = None
    circles_layout = {}
    for ci, rid in ring_ids.items():
        c = circles[ci]
        circles_layout[rid] = {'center': c['center'], 'radius': c['radius']}
        ring_atom = {'id': rid, 'label': texts[ring_of_circle[ci]].strip(), 'kind': 'variable_ring'}
        members = ring_members[ci]
        if members:
            ang = {m: math.atan2(pos[m][1] - c['center'][1], pos[m][0] - c['center'][0]) % (2 * math.pi)
                   for m in members}
            order = sorted(members, key=ang.get)
            gaps = [((ang[order[(i + 1) % len(order)]] - ang[order[i]]) % (2 * math.pi), i) for i in range(len(order))]
            widest = max(gaps)[1]
            order = order[widest + 1:] + order[:widest + 1]
            ring_atom['members'] = order
            for a, b in zip(order, order[1:]):
                if frozenset((a, b)) in seen:
                    continue
                straight = False
                if a in labels and b in labels:
                    ink = ink if ink is not None else _ink(graph['image'], graph['upscale'])
                    straight = _chord_drawn(ink, labels[a]['box'], labels[b]['box'], pos[a], pos[b], 0.15 * char)
                seen.add(frozenset((a, b)))
                bonds.append([a, b] if straight else {'a': a, 'b': b, 'display': 'arc'})
        atoms.append(ring_atom)

    scale = bond_length_pt / graph['bond_px']
    style = {'bond_length': round(bond_length_pt, 2),
             'font_size': round(max(7.0, graph['char_px'] * scale / 0.72), 1),
             'line_width': round(max(0.5, graph['stroke_px'] * scale), 2)}
    xs = [p[0] for p in pos.values()] + [c['center'][0] - c['radius'] for c in circles]
    ys = [p[1] for p in pos.values()] + [c['center'][1] - c['radius'] for c in circles]
    offset = [round(20 - min(xs) * scale, 2), round(20 - min(ys) * scale, 2)]
    spec = {'version': 1, 'title': 'Drafted from image', 'atoms': atoms, 'bonds': bonds}
    if vp:
        spec['variable_position'] = vp
    layout = {'units': 'px', 'scale': round(scale, 5), 'offset': offset, 'coords': coords,
              'circles': circles_layout, 'groups': layout_groups, 'h_labels': h_labels, 'style': style}
    return {'spec': spec, 'layout': layout, 'notes': notes, 'missing': []}


def _drawn_rings(graph, edges, dropped, skip):
    """Smallest drawn rings (SSSR) of the image graph, as lists of node ids."""
    ids = [v['id'] for v in graph['vertices']] + [l['id'] for l in graph['labels']]
    ids = [i for i in ids if i not in skip]
    index = {i: k for k, i in enumerate(ids)}
    mol = Chem.RWMol()
    for _ in ids:
        mol.AddAtom(Chem.Atom(6))
    for e in edges:
        if e['a'] in index and e['b'] in index and mol.GetBondBetweenAtoms(index[e['a']], index[e['b']]) is None:
            mol.AddBond(index[e['a']], index[e['b']], Chem.BondType.SINGLE)
    Chem.FastFindRings(mol)
    rings = [[ids[k] for k in r] for r in Chem.GetSymmSSSR(mol)]
    return sorted(rings, key=len)
