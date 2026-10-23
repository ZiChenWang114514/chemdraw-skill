from __future__ import annotations

import json
import shutil

import pytest

from cdxml_toolkit.markush import text_defs, workflow

from .markush_synthetic import benzene_with_groups

CLAIMS = """1. A compound of formula (I), wherein
Ring A is phenyl or pyridyl;
R is methyl or ethyl;
each X is independently fluoro or chloro; n is 0, 1 or 2.
"""


def _fake_renderer(source, png):
    """Stands in for native ChemDraw: copies the source figure as the 'rendering'."""
    shutil.copyfile(_fake_renderer.image, png)
    return True


@pytest.fixture
def run(tmp_path):
    image = tmp_path / 'figure.png'
    benzene_with_groups(image)
    claims = tmp_path / 'claims.txt'
    claims.write_text(CLAIMS, encoding='utf-8')
    _fake_renderer.image = image
    work = tmp_path / 'work'
    workflow.init(work, image, text=claims)
    return work


def _texts(work):
    graph = json.loads((work / 'graph.json').read_text(encoding='utf-8'))
    out = {}
    for lab in graph['labels']:
        wide = lab['box'][2] - lab['box'][0] > 2 * graph['char_px']
        out[lab['id']] = 'A' if lab['in_circle'] is not None else ('(X)_{n}' if wide else 'R')
    return out


def test_full_run_with_scripted_answers(run):
    answers = {'labels': _texts(run), 'labels_check': {'wrong': {}, 'unboxed': []},
               'review:1': {'missing_bonds': [], 'extra_bonds': [], 'bond_orders': [], 'text': {}},
               'definitions:A': {'text': 'phenyl or pyridyl', 'values': ['[*:1]c1ccccc1']},
               'definitions:R': {'text': 'methyl or ethyl', 'values': ['[*:1]C', '[*:1]CC']},
               'definitions:X': {'text': 'F or Cl', 'values': ['[*:1]F', '[*:1]Cl'], 'count_range': [0, 2]}}
    seen = []
    for _ in range(20):
        task = workflow.next_task(run, renderer=_fake_renderer)
        if task['task'] is None:
            break
        seen.append(task['task'])
        assert task['question'] and 'answer_shape' in task
        assert workflow.submit(run, task['task'], answers[task['task']])['accepted']
    assert seen == list(answers)
    final = run / 'final'
    for name in ('markush.json', 'markush.cxsmiles', 'markush.mol', 'markush.cdxml', 'report.json'):
        assert (final / name).is_file()
    report = json.loads((final / 'report.json').read_text(encoding='utf-8'))
    assert report['needs_review'] == [] and report['undefined'] == []
    assert report['fidelity']['match'] > 0.5


def test_invalid_answers_explain_and_then_go_to_review(run):
    task = workflow.next_task(run)
    assert task['task'] == 'labels'
    first = workflow.submit(run, 'labels', {'T1': 'R'})
    assert not first['accepted'] and any('missing' in e for e in first['errors'])
    again = workflow.next_task(run)
    assert again['attempt'] == 2 and again['fix_these']
    workflow.submit(run, 'labels', {'T1': 'R'})
    workflow.submit(run, 'labels', {'T1': 'R'})
    assert workflow.status(run)['needs_review'] == ['labels']


def test_review_edits_must_use_marks(run):
    workflow.next_task(run)
    workflow.submit(run, 'labels', _texts(run))
    workflow.next_task(run)
    workflow.submit(run, 'labels_check', {'wrong': {}, 'unboxed': []})
    task = workflow.next_task(run, renderer=_fake_renderer)
    assert task['task'] == 'review:1'
    bad = workflow.submit(run, 'review:1', {'missing_bonds': [['T1', 'Q7']]})
    assert not bad['accepted'] and 'Q7 is not a mark' in bad['errors'][0]
    ok = workflow.submit(run, 'review:1', {'missing_bonds': [['T1', 'T3']]})
    assert ok['accepted']
    assert workflow.next_task(run, renderer=_fake_renderer)['task'] == 'review:2'


def test_definition_values_need_the_right_attachment_points(run):
    for answer in (_texts(run), {'wrong': {}, 'unboxed': []}, {}):
        task = workflow.next_task(run, renderer=_fake_renderer)['task']
        workflow.submit(run, task, answer)
    task = workflow.next_task(run, renderer=_fake_renderer)
    assert task['task'] == 'definitions:A' and 'phenyl' in task['text']
    bad = workflow.submit(run, 'definitions:A', {'text': 'phenyl', 'values': ['c1ccccc1']})
    assert not bad['accepted'] and '[*:1]' in bad['errors'][0]
    # an empty count_range means "no repeat count", not an error
    assert workflow.submit(run, 'definitions:A', {'text': 'phenyl', 'values': [], 'count_range': []})['accepted']


def test_answers_are_reused_when_the_input_is_unchanged(run, tmp_path):
    workflow.next_task(run)
    workflow.submit(run, 'labels', _texts(run))
    second = tmp_path / 'again'
    workflow.init(second, _fake_renderer.image, reuse=run)
    assert workflow.next_task(second)['task'] == 'labels_check'


def test_parse_answer_accepts_fenced_json():
    assert workflow.parse_answer('Here:\n```json\n{"T1": "R"}\n```') == {'T1': 'R'}
    assert workflow.parse_answer('answer {"a": [1]} done') == {'a': [1]}


def test_locate_definition_clauses():
    found = text_defs.locate(CLAIMS, ['A', 'R', 'X'], counts={'X': 'n'}, rings={'A'})
    assert found['A'].startswith('Ring A is phenyl')
    assert 'fluoro' in found['X'] and 'n is 0, 1 or 2' in found['X']
    assert found['R'] == 'R is methyl or ethyl;'
