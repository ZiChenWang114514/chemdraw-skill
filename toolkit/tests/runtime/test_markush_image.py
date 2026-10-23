from __future__ import annotations

import math

from cdxml_toolkit.markush import draft_spec, fidelity, layout_detect
from cdxml_toolkit.markush.compile import build_graph, to_cxsmiles

from .markush_synthetic import benzene_with_groups


def _detect(tmp_path):
    truth = benzene_with_groups(tmp_path / 'figure.png')
    return truth, layout_detect.detect(tmp_path / 'figure.png')


def test_detects_ring_bonds_labels_and_circle(tmp_path):
    truth, graph = _detect(tmp_path)
    up = graph['upscale']
    assert len(graph['circles']) == 1
    (cx, cy), r = truth['circle']
    circle = graph['circles'][0]
    assert math.dist(circle['center'], (cx * up, cy * up)) < 6 and abs(circle['radius'] - r * up) < 6
    assert len(graph['labels']) == 3
    assert sum(1 for l in graph['labels'] if l['in_circle'] == 0) == 1
    ring_edges = [e for e in graph['edges'] if e['a'].startswith('v') and e['b'].startswith('v')]
    assert sum(e['order'] == 2 for e in ring_edges) == 3
    # every drawn ring atom is found once, within a few pixels
    for p in truth['ring']:
        assert min(math.dist(v['p'], (p[0] * up, p[1] * up)) for v in graph['vertices']) < 10


def test_a_line_crossing_a_ring_bond_does_not_add_an_atom(tmp_path):
    _, graph = _detect(tmp_path)
    degree = {}
    for e in graph['edges']:
        for k in (e['a'], e['b']):
            degree[k] = degree.get(k, 0) + 1
    assert max(degree.values()) <= 3
    assert len([v for v in graph['vertices'] if v['on_circle'] is None]) == 7  # 6 ring atoms + 1 free end


def test_draft_turns_transcriptions_into_a_spec(tmp_path):
    _, graph = _detect(tmp_path)
    ids = {l['in_circle'] is not None and 'ring' or ('group' if l['box'][2] - l['box'][0] > 2 * graph['char_px']
                                                     else 'R'): l['id'] for l in graph['labels']}
    texts = {ids['ring']: 'A', ids['group']: '(X)_{n}', ids['R']: 'R'}
    out = draft_spec.draft(graph, texts)
    assert out['notes'] == [] and out['missing'] == []
    spec = out['spec']
    group = spec['variable_position'][0]
    assert group['group'] == 'X' and group['count'] == 'n'
    assert len(group['on']) == 4  # the ring atoms without another substituent
    ring = next(a for a in spec['atoms'] if a.get('kind') == 'variable_ring')
    assert ring['label'] == 'A' and 'members' not in ring
    cx = to_cxsmiles(build_graph(spec))
    assert '$' in cx and 'm:' in cx
    assert out['layout']['units'] == 'px' and out['layout']['circles']


def test_draft_asks_for_every_label(tmp_path):
    _, graph = _detect(tmp_path)
    out = draft_spec.draft(graph, {})
    assert out['spec'] is None and len(out['missing']) == 3


def test_classify_labels():
    assert draft_spec.classify('NH') == ('element', 'N', 1)
    assert draft_spec.classify('O') == ('element', 'O', 0)
    assert draft_spec.classify('NH_{2}') == ('element', 'N', 2)
    assert draft_spec.classify('(R^{B})_{q}') == ('group', 'R^{B}', 'q')
    assert draft_spec.classify('L^{1}')[0] == 'generic'


def test_fidelity_of_an_image_with_itself_is_perfect(tmp_path):
    benzene_with_groups(tmp_path / 'a.png')
    result = fidelity.compare(tmp_path / 'a.png', tmp_path / 'a.png', tmp_path / 'diff.png')
    assert result['match'] > 0.99 and (tmp_path / 'diff.png').is_file()


def test_label_sheet_hides_bond_ends_inside_a_label_box(tmp_path):
    import cv2
    import numpy as np
    img = np.full((60, 120), 255, np.uint8)
    img[20:40, 20:30] = 0          # the glyph
    img[10:22, 50:53] = 0          # a bond end that falls inside the label box
    cv2.imwrite(str(tmp_path / 'l.png'), img)
    graph = {'upscale': 1, 'labels': [{'id': 'T1', 'box': [18, 8, 56, 42], 'parts': [[20, 20, 30, 40]]}]}
    layout_detect.label_sheet(tmp_path / 'l.png', graph, tmp_path / 'sheet.png', pad=0)
    sheet = cv2.imread(str(tmp_path / 'sheet.png'), cv2.IMREAD_GRAYSCALE)
    crop = sheet[5:75, 100:]
    k = 70 / 34
    assert crop[:, int(32 * k):int(38 * k)].min() > 200   # bond end gone
    assert crop[:, int(2 * k):int(12 * k)].min() < 60     # glyph kept
