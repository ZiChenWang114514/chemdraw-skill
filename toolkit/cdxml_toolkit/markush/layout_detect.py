"""Parse a clean line drawing of a generic structure into an image graph.

Patent Markush figures are black-on-white line art, so geometry is found by
code, not by a model: text boxes, straight bonds (with double-bond partners),
variable-ring circles and the free end of a variable-position bond.  The
result keeps image pixel coordinates; a model only has to read the text in
each numbered label box.
"""
from __future__ import annotations

import math
from pathlib import Path

import cv2
import numpy as np


def _thin(mask: np.ndarray) -> np.ndarray:
    """Zhang-Suen thinning on a boolean image."""
    img = np.pad(mask.astype(np.uint8), 1)
    while True:
        changed = False
        for step in (0, 1):
            p2, p3, p4 = img[:-2, 1:-1], img[:-2, 2:], img[1:-1, 2:]
            p5, p6, p7 = img[2:, 2:], img[2:, 1:-1], img[2:, :-2]
            p8, p9 = img[1:-1, :-2], img[:-2, :-2]
            seq = [p2, p3, p4, p5, p6, p7, p8, p9, p2]
            b = sum(seq[:8])
            a = sum(((seq[i] == 0) & (seq[i + 1] == 1)).astype(np.uint8) for i in range(8))
            if step == 0:
                c1, c2 = p2 * p4 * p6, p4 * p6 * p8
            else:
                c1, c2 = p2 * p4 * p8, p2 * p6 * p8
            core = img[1:-1, 1:-1]
            drop = (core == 1) & (b >= 2) & (b <= 6) & (a == 1) & (c1 == 0) & (c2 == 0)
            if drop.any():
                core[drop] = 0
                changed = True
        if not changed:
            return img[1:-1, 1:-1].astype(bool)


_NB = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]


def _trace(skel: np.ndarray):
    """Pixel paths between end/junction pixels (and closed loops)."""
    ys, xs = np.nonzero(skel)
    pix = set(zip(ys.tolist(), xs.tolist()))
    def nbrs(p):
        return [(p[0] + dy, p[1] + dx) for dy, dx in _NB if (p[0] + dy, p[1] + dx) in pix]
    deg = {p: len(nbrs(p)) for p in pix}
    nodes = {p for p, d in deg.items() if d != 2}
    seen_edges = set()
    paths = []
    for n in nodes:
        for first in nbrs(n):
            key = frozenset((n, first))
            if key in seen_edges:
                continue
            path, prev, cur = [n], n, first
            seen_edges.add(key)
            while True:
                path.append(cur)
                if cur in nodes:
                    break
                nxt = [q for q in nbrs(cur) if q != prev and frozenset((cur, q)) not in seen_edges]
                if not nxt:
                    break
                seen_edges.add(frozenset((cur, nxt[0])))
                prev, cur = cur, nxt[0]
            paths.append(path)
    visited = {p for path in paths for p in path}
    for p in pix - visited:  # closed loops without junctions
        if p in visited:
            continue
        loop, prev, cur = [p], None, p
        while True:
            nxt = [q for q in nbrs(cur) if q != prev and q not in loop[1:]]
            visited.add(cur)
            if not nxt or (nxt[0] == p and len(loop) > 2):
                break
            prev, cur = cur, nxt[0]
            if cur == p:
                break
            loop.append(cur)
        loop.append(p)
        if len(loop) > 4:
            paths.append(loop)
    return paths


def _pca(points):
    pts = np.asarray(points, dtype=float)
    c = pts.mean(axis=0)
    if len(pts) < 3:
        return c, 0.0, 0.0
    w, v = np.linalg.eigh(np.cov((pts - c).T))
    return c, math.sqrt(max(w[1], 0)), math.sqrt(max(w[0], 0))


def _seg_dist(p, a, b):
    p, a, b = map(np.asarray, (p, a, b))
    ab = b - a
    t = 0.0 if not ab.any() else float(np.clip(np.dot(p - a, ab) / np.dot(ab, ab), 0, 1))
    return float(np.linalg.norm(p - (a + t * ab)))


def _box_dist(p, box):
    x0, y0, x1, y1 = box
    dx = max(x0 - p[0], 0, p[0] - x1)
    dy = max(y0 - p[1], 0, p[1] - y1)
    return math.hypot(dx, dy)


def _segments(skel: np.ndarray, ink: np.ndarray, char_h):
    """Straight segments from the skeleton, with collinear pieces merged and spurs dropped.

    Probabilistic Hough on the one-pixel skeleton keeps a line straight through a
    crossing; pieces split by a crossing line are joined when the gap is inked.
    """
    lines = cv2.HoughLinesP(skel.astype(np.uint8) * 255, 1, np.pi / 360, threshold=max(5, int(0.3 * char_h)),
                            minLineLength=max(4, int(0.35 * char_h)), maxLineGap=max(2, int(0.3 * char_h)))
    if lines is None:
        return []
    segs = [[np.array(l[:2], float), np.array(l[2:], float)] for l in np.asarray(lines).reshape(-1, 4)]
    changed = True
    while changed:
        changed = False
        for i in range(len(segs)):
            for j in range(i + 1, len(segs)):
                m = _merge_collinear(segs[i], segs[j], char_h, ink, segs)
                if m is not None:
                    segs[i] = m
                    segs.pop(j)
                    changed = True
                    break
            if changed:
                break
    return [s for s in segs if np.linalg.norm(s[1] - s[0]) >= 0.35 * char_h]


def _inked(ink, a, b) -> float:
    n = max(2, int(math.dist(a, b)))
    hits = 0
    for t in np.linspace(0, 1, n):
        x, y = (int(round(v)) for v in (a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])))
        if 0 <= y < ink.shape[0] and 0 <= x < ink.shape[1] and ink[max(0, y - 1):y + 2, max(0, x - 1):x + 2].any():
            hits += 1
    return hits / n


def _crossed(mid, u, segs, char_h) -> bool:
    for s in segs:
        d = s[1] - s[0]
        n = np.linalg.norm(d)
        if n < 1e-6 or abs(float(np.dot(d / n, u))) > math.cos(math.radians(25)):
            continue
        if _seg_dist(mid, s[0], s[1]) <= 0.25 * char_h:
            return True
    return False


def _merge_collinear(s1, s2, char_h, ink=None, segs=()):
    d1, d2 = s1[1] - s1[0], s2[1] - s2[0]
    l1, l2 = np.linalg.norm(d1), np.linalg.norm(d2)
    if l1 < 1e-6 or l2 < 1e-6:
        return None
    if abs(float(np.dot(d1, d2))) / (l1 * l2) < math.cos(math.radians(7)):
        return None
    u = d1 / l1
    def perp(p):
        v = p - s1[0]
        return abs(v[0] * u[1] - v[1] * u[0])
    if max(perp(s2[0]), perp(s2[1])) > max(2.0, 0.08 * char_h):
        return None
    t = [0.0, l1, float(np.dot(s2[0] - s1[0], u)), float(np.dot(s2[1] - s1[0], u))]
    gap = max(min(t[2], t[3]) - l1, -max(t[2], t[3]))
    if gap > 0.25 * char_h:
        # a line crossing this one leaves a gap (often a deliberate white break)
        if ink is None or gap > 0.8 * char_h:
            return None
        if min(t[2], t[3]) > l1:
            a, b = s1[0] + u * l1, s1[0] + u * min(t[2], t[3])
        else:
            a, b = s1[0] + u * max(t[2], t[3]), s1[0]
        if _inked(ink, a, b) < 0.95 and not _crossed((a + b) / 2, u, segs, char_h):
            return None
    lo, hi = min(t), max(t)
    return [s1[0] + u * lo, s1[0] + u * hi]


def _pair_multiple_bonds(segs, char_h):
    """Drop the extra line(s) of double/triple bonds; returns segments and their orders."""
    order = [1] * len(segs)
    gone = set()
    idx = sorted(range(len(segs)), key=lambda k: -np.linalg.norm(segs[k][1] - segs[k][0]))
    for i in idx:
        if i in gone:
            continue
        a2, b2 = segs[i]
        d2 = b2 - a2
        l2 = np.linalg.norm(d2)
        for j in idx:
            if j == i or j in gone:
                continue
            a1, b1 = segs[j]
            d1 = b1 - a1
            l1 = np.linalg.norm(d1)
            if l1 > l2 + 1e-6:
                continue
            if abs(float(np.dot(d1, d2))) / (l1 * l2) < math.cos(math.radians(10)):
                continue
            mid = (a1 + b1) / 2
            t = float(np.dot(mid - a2, d2) / (l2 * l2))
            perp = abs(float(d2[0] * (mid - a2)[1] - d2[1] * (mid - a2)[0])) / l2
            if not (0.0 < t < 1.0 and 0.06 * l2 <= perp <= min(max(0.45 * l2, 0.4 * char_h), 0.9 * char_h)):
                continue
            overlap = (min(max(np.dot(a1 - a2, d2), np.dot(b1 - a2, d2)), l2 * l2) -
                       max(min(np.dot(a1 - a2, d2), np.dot(b1 - a2, d2)), 0)) / l2
            if overlap < 0.5 * l1:
                continue
            gone.add(j)
            order[i] += 1
            if l1 > 0.85 * l2:  # centred double bond: use the midline
                if np.linalg.norm(a1 - a2) > np.linalg.norm(a1 - b2):
                    a1, b1 = b1, a1
                segs[i] = [(a1 + a2) / 2, (b1 + b2) / 2]
                a2, b2 = segs[i]
                d2 = b2 - a2
                l2 = np.linalg.norm(d2)
    keep = [k for k in range(len(segs)) if k not in gone]
    return [segs[k] for k in keep], [min(order[k], 3) for k in keep]


def _clean_graph(verts, edges, char_h):
    """Collapse too-short edges, merge near-duplicate vertices and undo straight crossings."""
    alias = {}
    def r(v):
        while v in alias:
            v = alias[v]
        return v
    def merge(u, v):
        u, v = r(u), r(v)
        if u != v:
            verts[v]['p'] = list((np.array(verts[u]['p']) + np.array(verts[v]['p'])) / 2)
            alias[u] = v
    lengths = sorted(math.dist(verts[e['a']]['p'], verts[e['b']]['p']) for e in edges)
    bond = lengths[len(lengths) // 2] if lengths else 2 * char_h
    deg = {}
    for e in edges:
        for v in (e['a'], e['b']):
            deg[v] = deg.get(v, 0) + 1
    for e in edges:  # junction debris between two real bonds; a short free stub is kept
        if min(deg[e['a']], deg[e['b']]) >= 2 and math.dist(verts[r(e['a'])]['p'], verts[r(e['b'])]['p']) < 0.4 * bond:
            merge(e['a'], e['b'])
    live = sorted({r(v) for e in edges for v in (e['a'], e['b'])})
    linked = {frozenset((r(e['a']), r(e['b']))) for e in edges}
    for i, u in enumerate(live):
        for v in live[i + 1:]:
            if r(u) != r(v) and frozenset((r(u), r(v))) not in linked and                     math.dist(verts[r(u)]['p'], verts[r(v)]['p']) < 0.65 * char_h:
                merge(u, v)
    out = {}
    for e in edges:
        a, b = r(e['a']), r(e['b'])
        if a != b:
            key = frozenset((a, b))
            out[key] = {'a': a, 'b': b, 'order': max(e['order'], out.get(key, {}).get('order', 1))}
    edges = list(out.values())
    # a crossing (two straight lines through one point) is not an atom
    changed = True
    while changed:
        changed = False
        nb = {}
        for e in edges:
            nb.setdefault(e['a'], []).append(e)
            nb.setdefault(e['b'], []).append(e)
        for v, es in nb.items():
            if len(es) != 4:
                continue
            p = np.array(verts[v]['p'])
            others = [(e, e['b'] if e['a'] == v else e['a']) for e in es]
            dirs = [(np.array(verts[o]['p']) - p) / (np.linalg.norm(np.array(verts[o]['p']) - p) or 1) for _, o in others]
            pairs = [(i, j) for i in range(4) for j in range(i + 1, 4) if float(np.dot(dirs[i], dirs[j])) < -0.97]
            if len(pairs) == 2 and not set(pairs[0]) & set(pairs[1]):
                for i, j in pairs:
                    edges.append({'a': others[i][1], 'b': others[j][1], 'order': 1})
                for e in es:
                    edges.remove(e)
                changed = True
                break
    return verts, edges


def _vertices(segs, orders, char_h):
    tol = 0.45 * char_h
    verts = []
    ends = []
    for s in segs:
        ids = []
        for p in s:
            for k, v in enumerate(verts):
                if k not in ids and math.dist(p, v['p']) <= tol:  # a short stub keeps both ends
                    v['members'].append(p)
                    v['p'] = list(np.mean(v['members'], axis=0))
                    ids.append(k)
                    break
            else:
                verts.append({'p': list(map(float, p)), 'members': [p]})
                ids.append(len(verts) - 1)
        ends.append(ids)
    edges = {}
    for (va, vb), o in zip(ends, orders):
        if va != vb:
            key = frozenset((va, vb))
            edges[key] = {'a': va, 'b': vb, 'order': max(o, edges.get(key, {}).get('order', 1))}
    return verts, list(edges.values())


def _components(bw, stroke):
    n, labels, stats, _ = cv2.connectedComponentsWithStats(bw, connectivity=8)
    comps = []
    for i in range(1, n):
        x, y, w, h, area = stats[i]
        if area < 3:
            continue
        ys, xs = np.nonzero(labels[y:y + h, x:x + w] == i)
        c, major, minor = _pca(np.column_stack([xs + x, ys + y]))
        comps.append({'id': i, 'box': [int(x), int(y), int(x + w), int(y + h)], 'w': int(w), 'h': int(h),
                      'area': int(area), 'center': [float(c[0]), float(c[1])], 'major': major, 'minor': minor,
                      'ys': ys + y, 'xs': xs + x,
                      'straight': minor <= 0.45 * stroke and max(w, h) >= 2.5 * stroke})
    return comps


def _char_height(comps, height):
    hs = [c['h'] for c in comps if not c['straight'] and 4 <= c['h'] <= height / 6
          and c['w'] <= 1.6 * c['h'] and c['area'] / max(1, c['w'] * c['h']) > 0.12]
    if not hs:
        raise ValueError('No text-sized marks found; is this a structure drawing?')
    hist = np.bincount(np.round(np.asarray(hs) / 2).astype(int))
    return float(np.argmax(hist) * 2) or float(np.median(hs))


def _classify_text(comps, char_h):
    for c in comps:
        small = max(c['w'], c['h']) <= 1.7 * char_h and c['h'] <= 1.5 * char_h
        c['speck'] = max(c['w'], c['h']) < 0.25 * char_h and not c['straight']  # dust, erase residue
        c['text'] = small and not c['straight'] and not c['speck']
    for c in comps:  # thin tall glyphs (l, 1, I, parentheses) count as text next to other text
        if c['straight'] and 0.6 * char_h <= c['h'] <= 1.3 * char_h and c['w'] <= 0.6 * char_h:
            for o in comps:
                if o is c or not o['text']:
                    continue
                gap = max(o['box'][0] - c['box'][2], c['box'][0] - o['box'][2])
                overlap = min(c['box'][3], o['box'][3]) - max(c['box'][1], o['box'][1])
                if gap <= 0.45 * char_h and overlap > 0:
                    c['text'] = True
                    break


def _find_circles(bw, comps, char_h, stroke):
    blur = cv2.GaussianBlur(bw, (5, 5), 1.5)
    found = cv2.HoughCircles(blur, cv2.HOUGH_GRADIENT, dp=1, minDist=2 * char_h, param1=120, param2=25,
                             minRadius=int(0.9 * char_h), maxRadius=int(4.5 * char_h))
    tol = max(2.0, 0.6 * stroke)
    letters = [c for c in comps if c['text']]
    circles = []
    if found is None:
        return circles
    for cx, cy, r in found[0]:
        if not any(math.dist(l['center'], (cx, cy)) <= 0.35 * r and l['h'] <= 1.3 * char_h for l in letters):
            continue
        angles = np.linspace(0, 2 * np.pi, 240, endpoint=False)
        hits = 0
        for a in angles:
            for dr in np.linspace(-tol, tol, 5):
                px, py = int(round(cx + (r + dr) * math.cos(a))), int(round(cy + (r + dr) * math.sin(a)))
                if 0 <= py < bw.shape[0] and 0 <= px < bw.shape[1] and bw[py, px]:
                    hits += 1
                    break
        coverage = hits / len(angles)
        if coverage >= 0.6 and not any(math.dist((cx, cy), c['center']) < r for c in circles):
            circles.append({'center': [float(cx), float(cy)], 'radius': float(r), 'coverage': round(coverage, 2)})
    return circles


def detect(image_path, upscale: int | None = None) -> dict:
    gray = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
    if gray is None:
        raise ValueError(f'Cannot read image {image_path}')
    up = upscale or (2 if max(gray.shape) < 900 else 1)
    if up > 1:
        gray = cv2.resize(gray, None, fx=up, fy=up, interpolation=cv2.INTER_CUBIC)
    _, bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    ink = bw > 0
    dist = cv2.distanceTransform(bw, cv2.DIST_L2, 3)
    skel_all = _thin(ink)
    stroke = max(1.5, 2 * float(np.median(dist[skel_all])) if skel_all.any() else 2.0)
    comps = _components(bw, stroke)
    char_h = _char_height(comps, gray.shape[0])
    _classify_text(comps, char_h)
    # variable-ring circles: a Markush ring circle always has its ring letter at the centre
    circles = _find_circles(bw, comps, char_h, stroke)
    tol = max(2.0, 0.6 * stroke)
    if circles:  # letters touching a circle only separate once the circle is erased
        band = np.zeros_like(bw)
        for c in circles:
            cv2.circle(band, (int(round(c['center'][0])), int(round(c['center'][1]))), int(round(c['radius'])), 255,
                       thickness=int(math.ceil(stroke + 2 * tol)))
        bw_text = bw.copy()
        bw_text[band > 0] = 0
        comps = _components(bw_text, stroke)
        _classify_text(comps, char_h)
        near = cv2.dilate(band, np.ones((3, 3), np.uint8), iterations=int(math.ceil(stroke)))
        for c in comps:  # circle residue: small marks lying entirely along the erased band
            if c['text'] and max(c['w'], c['h']) < 0.5 * char_h and near[c['ys'], c['xs']].all():
                c['text'], c['speck'] = False, True
    band_half = math.ceil(stroke + 2 * tol) / 2 if circles else 0

    text = [c for c in comps if c['text']]
    parent = list(range(len(text)))
    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    for i, a in enumerate(text):
        for j in range(i + 1, len(text)):
            b = text[j]
            gap_x = max(b['box'][0] - a['box'][2], a['box'][0] - b['box'][2])
            ov_y = min(a['box'][3], b['box'][3]) - max(a['box'][1], b['box'][1])
            gap_y = max(b['box'][1] - a['box'][3], a['box'][1] - b['box'][3])
            ov_x = min(a['box'][2], b['box'][2]) - max(a['box'][0], b['box'][0])
            side = gap_x <= 0.45 * char_h and ov_y > 0
            stack = gap_y <= 0.4 * char_h and ov_x >= 0.5 * min(a['w'], b['w'])
            if side or stack:
                parent[find(i)] = find(j)
    groups: dict[int, list] = {}
    for i, c in enumerate(text):
        groups.setdefault(find(i), []).append(c)
    label_boxes = []
    for members in groups.values():
        box = [min(m['box'][0] for m in members), min(m['box'][1] for m in members),
               max(m['box'][2] for m in members), max(m['box'][3] for m in members)]
        label_boxes.append({'box': box, 'parts': [{'center': m['center'], 'box': m['box']}
                                                  for m in sorted(members, key=lambda m: (m['box'][0], m['box'][1]))]})
    label_boxes.sort(key=lambda l: (l['box'][1], l['box'][0]))
    for k, lab in enumerate(label_boxes, 1):
        lab['id'] = f'T{k}'
    # line image
    text_mask = np.zeros_like(bw)
    for c in comps:  # text and specks never become bonds
        if c['text'] or c['speck']:
            text_mask[c['ys'], c['xs']] = 255
    text_mask = cv2.dilate(text_mask, np.ones((3, 3), np.uint8), iterations=max(1, int(stroke / 2)))
    lines = (bw > 0) & (text_mask == 0)
    erase = lines.astype(np.uint8)
    for c in circles:
        cv2.circle(erase, (int(round(c['center'][0])), int(round(c['center'][1]))), int(round(c['radius'])), 0,
                   thickness=int(math.ceil(stroke + 2 * tol)))
    skel = _thin(erase > 0)
    segs = _segments(skel, erase > 0, char_h)
    segs, orders = _pair_multiple_bonds(segs, char_h)
    verts, edges = _vertices(segs, orders, char_h)
    verts, edges = _clean_graph(verts, edges, char_h)
    used = {v for e in edges for v in (e['a'], e['b'])}
    degree = {v: sum(v in (e['a'], e['b']) for e in edges) for v in used}
    ring_letters = {lab['id'] for lab in label_boxes for c in circles
                    if math.dist(((lab['box'][0] + lab['box'][2]) / 2, (lab['box'][1] + lab['box'][3]) / 2), c['center'])
                    <= 0.35 * c['radius']}
    # attach line ends to labels: a free end near a label, or a junction inside the label box
    vertices = []
    remap = {}
    for k in sorted(used):
        v = verts[k]
        near = None
        reach = 0.9 * char_h if degree[k] == 1 else 0.3 * char_h
        for lab in label_boxes:
            if lab['id'] in ring_letters:  # nothing bonds to the letter naming a ring
                continue
            if _box_dist(v['p'], lab['box']) <= reach:
                if near is None or _box_dist(v['p'], lab['box']) < _box_dist(v['p'], near['box']):
                    near = lab
        on = None
        for ci, c in enumerate(circles):
            if abs(math.dist(v['p'], c['center']) - c['radius']) <= band_half + 0.4 * char_h:
                on = ci
        remap[k] = ('label', near['id']) if near else ('v', k)
        if not near:
            vertices.append({'id': f'v{len(vertices) + 1}', 'p': [round(float(v['p'][0]), 1), round(float(v['p'][1]), 1)],
                             'on_circle': on, 'key': k})
    vmap = {v['key']: v['id'] for v in vertices}
    final_edges = {}
    for e in edges:
        ends = []
        for k in (e['a'], e['b']):
            kind, ident = remap[k]
            ends.append(ident if kind == 'label' else vmap[k])
        if ends[0] != ends[1]:
            key = frozenset(ends)
            final_edges[key] = {'a': ends[0], 'b': ends[1], 'order': max(e['order'], final_edges.get(key, {}).get('order', 1))}
    # label anchor = the text part closest to its bonds
    for lab in label_boxes:
        ends = []
        for e in edges:
            for k in (e['a'], e['b']):
                if remap[k] == ('label', lab['id']):
                    ends.append(verts[k]['p'])
        # the anchor is a full-size glyph (not a parenthesis, digit-sized script or stacked H)
        wide = [q for q in lab['parts'] if q['box'][2] - q['box'][0] >= 0.4 * char_h] or lab['parts']
        tallest = max(q['box'][3] - q['box'][1] for q in wide)
        main = [q for q in wide if q['box'][3] - q['box'][1] >= 0.8 * tallest]
        if ends:
            target = np.mean(ends, axis=0)
            lab['anchor'] = min(main, key=lambda q: math.dist(q['center'], target))['center']
        else:
            lab['anchor'] = min(main, key=lambda q: (q['box'][1], q['box'][0]))['center']
        lab['anchor'] = [round(float(lab['anchor'][0]), 1), round(float(lab['anchor'][1]), 1)]
        lab['on_circle'] = None
        lab['in_circle'] = None
        for ci, c in enumerate(circles):
            d = math.dist(lab['anchor'], c['center'])
            if d <= 0.5 * c['radius']:
                lab['in_circle'] = ci
            elif _box_dist(c['center'], lab['box']) <= c['radius'] + 0.3 * char_h and \
                    max(math.dist(c['center'], q) for q in [(lab['box'][0], lab['box'][1]), (lab['box'][2], lab['box'][3]),
                                                            (lab['box'][0], lab['box'][3]), (lab['box'][2], lab['box'][1])]) >= c['radius'] - 0.3 * char_h:
                lab['on_circle'] = ci
        lab['box'] = [int(x) for x in lab['box']]
        lab['parts'] = [[int(x) for x in q['box']] for q in lab['parts']]
    lengths = [math.dist(verts[e['a']]['p'], verts[e['b']]['p']) for e in edges
               if remap[e['a']][0] == 'v' and remap[e['b']][0] == 'v']
    bond_px = float(np.median(lengths)) if lengths else 1.7 * char_h
    return {
        'image': str(Path(image_path)), 'upscale': up, 'size': [int(gray.shape[1]), int(gray.shape[0])],
        'stroke_px': round(stroke, 2), 'char_px': round(char_h, 2), 'bond_px': round(bond_px, 2),
        'labels': label_boxes, 'vertices': [{k: v for k, v in x.items() if k != 'key'} for x in vertices],
        'edges': list(final_edges.values()),
        'circles': [{**c, 'center': [round(c['center'][0], 1), round(c['center'][1], 1)], 'radius': round(c['radius'], 1)}
                    for c in circles],
    }


def overlay(image_path, graph: dict, out_path, labels_only: bool = False) -> str:
    """Numbered marks for label boxes (T#) and vertices (v#) on the upscaled image."""
    img = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
    up = graph['upscale']
    if up > 1:
        img = cv2.resize(img, None, fx=up, fy=up, interpolation=cv2.INTER_CUBIC)
    fs = max(0.4, graph['char_px'] / 45)
    for lab in graph['labels']:
        x0, y0, x1, y1 = lab['box']
        cv2.rectangle(img, (x0 - 2, y0 - 2), (x1 + 2, y1 + 2), (0, 140, 255), 1)
        cv2.putText(img, lab['id'], (x0, max(10, y0 - 4)), cv2.FONT_HERSHEY_SIMPLEX, fs, (0, 100, 230), 1, cv2.LINE_AA)
    if not labels_only:
        for v in graph['vertices']:
            x, y = map(int, v['p'])
            cv2.circle(img, (x, y), 3, (220, 40, 40), -1)
            cv2.putText(img, v['id'][1:], (x + 4, y - 4), cv2.FONT_HERSHEY_SIMPLEX, fs * 0.8, (200, 30, 30), 1, cv2.LINE_AA)
        for c in graph['circles']:
            cv2.circle(img, tuple(int(t) for t in c['center']), int(c['radius']), (40, 170, 40), 1)
        where = {v['id']: v['p'] for v in graph['vertices']}
        where.update({l['id']: l['anchor'] for l in graph['labels']})
        for e in graph['edges']:
            a, b = (tuple(int(t) for t in where[e[k]]) for k in ('a', 'b'))
            cv2.line(img, a, b, (200, 0, 200) if e['order'] == 1 else (0, 160, 0), 1, cv2.LINE_AA)
    cv2.imwrite(str(out_path), img)
    return str(out_path)


def label_sheet(image_path, graph: dict, out_path, ids=None, pad: int = 6) -> str:
    """One enlarged crop per label box, captioned with its id, stacked vertically."""
    gray = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
    up = graph['upscale']
    if up > 1:
        gray = cv2.resize(gray, None, fx=up, fy=up, interpolation=cv2.INTER_CUBIC)
    rows = []
    target_h = 70
    for lab in graph['labels']:
        if ids and lab['id'] not in ids:
            continue
        x0, y0, x1, y1 = lab['box']
        # show only the label's own glyphs: a bond end inside the box reads as a prime or a dash
        keep = np.zeros_like(gray, bool)
        for px0, py0, px1, py1 in lab.get('parts') or [lab['box']]:
            keep[max(0, py0 - 2):py1 + 3, max(0, px0 - 2):px1 + 3] = True
        glyphs = np.where(keep, gray, 255).astype(np.uint8)
        crop = glyphs[max(0, y0 - pad):y1 + pad, max(0, x0 - pad):x1 + pad]
        k = target_h / max(1, crop.shape[0])
        crop = cv2.resize(crop, None, fx=k, fy=k, interpolation=cv2.INTER_CUBIC)
        cap = np.full((target_h, 90), 255, np.uint8)
        cv2.putText(cap, lab['id'], (6, 45), cv2.FONT_HERSHEY_SIMPLEX, 0.9, 0, 2, cv2.LINE_AA)
        rows.append((cap, crop))
    if not rows:
        raise ValueError('No label boxes to show')
    width = max(c.shape[1] for _, c in rows) + 100
    sheet = []
    for cap, crop in rows:
        row = np.full((target_h + 10, width), 255, np.uint8)
        row[5:5 + target_h, :90] = cap
        row[5:5 + crop.shape[0], 100:100 + crop.shape[1]] = crop
        cv2.line(row, (0, target_h + 9), (width, target_h + 9), 200, 1)
        sheet.append(row)
    cv2.imwrite(str(out_path), np.vstack(sheet))
    return str(out_path)
