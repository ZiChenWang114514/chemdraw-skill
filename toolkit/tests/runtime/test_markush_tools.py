from __future__ import annotations

import json
from pathlib import Path
import pytest

from cdxml_toolkit.markush.cdxml_writer import _label_node_x
from cdxml_toolkit.mcp_runtime import artifact_safety
from cdxml_toolkit.mcp_runtime.markush_tools import (markush_compile, markush_detect, markush_enumerate,
                                                     markush_validate)
from cdxml_toolkit.mcp_runtime.tool_registry import build_registry

from .markush_synthetic import benzene_with_groups

EXAMPLE = Path(__file__).resolve().parents[2] / 'examples' / 'markush' / 'indole-macrocycle.json'
MARKUSH = {'markush_validate', 'markush_compile', 'markush_enumerate', 'markush_detect'}


def test_registry_lists_the_markush_tools():
    assert MARKUSH <= set(build_registry())


def test_compile_writes_the_three_formats_and_refuses_an_existing_folder(tmp_path):
    out = tmp_path / 'out'
    result = markush_compile(str(EXAMPLE), str(out), render=False)
    assert result['ok'] and result['native_render'] == 'not_run'
    assert {p.name for p in out.iterdir()} == {'markush.cxsmiles', 'markush.mol', 'markush.cdxml'}
    with pytest.raises(artifact_safety.OutputExistsError):
        markush_compile(str(EXAMPLE), str(out), render=False)


def test_validate_and_enumerate(tmp_path):
    assert markush_validate(str(EXAMPLE)) == {'ok': True, 'errors': [], 'warnings': []}
    assert markush_enumerate(str(EXAMPLE), count=2)['ok']
    assert not markush_enumerate(str(EXAMPLE), count=0)['ok']


def _overloaded_carbonyl(tmp_path, min_count=1):
    """A carbonyl carbon with one free valence that two groups must both occupy."""
    spec = {
        'version': 1, 'title': 'over-substituted carbonyl carbon',
        'atoms': [{'id': 'c1', 'element': 'C', 'h': 3}, {'id': 'cc', 'element': 'C'}, {'id': 'co', 'element': 'O'}],
        'bonds': [['c1', 'cc'], ['cc', 'co', 2]],
        'variable_position': [{'group': 'RA', 'label': 'R^A', 'on': ['cc']},
                              {'group': 'RB', 'label': 'R^B', 'on': ['cc']}],
        'definitions': {'RA': {'text': 'hydroxy', 'values': ['[*:1]O']},
                        'RB': {'text': 'amino', 'values': ['[*:1]N'], 'count_range': [min_count, 1]}},
    }
    path = tmp_path / 'spec.json'
    path.write_text(json.dumps(spec), encoding='utf-8')
    return str(path)


def test_enumerate_fails_when_no_member_can_be_built(tmp_path):
    result = markush_enumerate(_overloaded_carbonyl(tmp_path), count=5)
    assert result['ok'] is False
    assert result['error']['code'] == 'no_member_built'
    assert result['members'] == []
    # The failure names the spec atom and the groups placed on it, not an RDKit atom index.
    assert "'cc'" in result['failures'][0] and 'atom #' not in result['failures'][0]
    assert result['failed_groups'] == ['RA', 'RB'] and result['not_enumerated'] == ['RA', 'RB']
    assert result['failed_attempts'] == 20


def test_enumerate_warns_when_only_some_members_fail(tmp_path):
    result = markush_enumerate(_overloaded_carbonyl(tmp_path, min_count=0), count=2)
    assert result['ok'] is True
    assert result['members'] == ['CC(=O)O']
    assert result['failed_attempts'] > 0 and result['failed_groups'] == ['RA', 'RB']
    assert result['not_enumerated'] == []
    assert any('could not be built' in warning for warning in result['warnings'])


def test_validate_warns_when_groups_need_more_room_than_an_atom_has(tmp_path):
    result = markush_validate(_overloaded_carbonyl(tmp_path))
    # The spec still draws, so this is a warning: the carbonyl carbon has room for one group, two are required.
    assert result['ok'] is True and result['errors'] == []
    assert len(result['warnings']) == 1
    warning = result['warnings'][0]
    assert "'cc'" in warning and 'RA' in warning and 'RB' in warning and 'count_range' in warning


def test_validate_is_quiet_when_an_optional_group_makes_room(tmp_path):
    assert markush_validate(_overloaded_carbonyl(tmp_path, min_count=0))['warnings'] == []


def test_validate_warns_when_a_group_has_no_open_site(tmp_path):
    spec = {
        'version': 1,
        'atoms': [{'id': 'c1', 'element': 'C', 'h': 3}, {'id': 'cq', 'element': 'C'},
                  {'id': 'c2', 'element': 'C', 'h': 3}, {'id': 'c3', 'element': 'C', 'h': 3},
                  {'id': 'c4', 'element': 'C', 'h': 3}],
        'bonds': [['c1', 'cq'], ['cq', 'c2'], ['cq', 'c3'], ['cq', 'c4']],
        'variable_position': [{'group': 'RA', 'label': 'R^A', 'on': ['cq']}],
        'definitions': {'RA': {'text': 'hydroxy', 'values': ['[*:1]O']}},
    }
    path = tmp_path / 'quaternary.json'
    path.write_text(json.dumps(spec), encoding='utf-8')
    warning = markush_validate(str(path))['warnings'][0]
    assert "'cq'" in warning and 'RA' in warning


def test_detect_writes_marks_and_label_sheet(tmp_path):
    benzene_with_groups(tmp_path / 'figure.png')
    result = markush_detect(str(tmp_path / 'figure.png'), str(tmp_path / 'det'))
    assert result['labels'] == 3 and result['circles'] == 1
    assert {p.name for p in (tmp_path / 'det').iterdir()} == {'graph.json', 'marks.png', 'labels.png'}


def test_label_node_follows_chemdraw_placement():
    runs = [('(R', 'normal'), ('C', 'sup'), (')', 'normal'), ('p', 'sub')]
    # steep bond: ChemDraw keeps the stored text position, node stays on the anchor letter
    assert _label_node_x(100.0, runs, 10, 'Left', (0.1, 1.0)) == 100.0
    # near-horizontal bond: ChemDraw centres "(" on the node, so the node moves left
    assert _label_node_x(100.0, runs, 10, 'Left', (1.0, 0.1)) < 100.0
    # a label starting with a letter needs no shift
    assert _label_node_x(100.0, [('Z', 'normal')], 10, 'Left', (1.0, 0.0)) == 100.0
    # right display on a horizontal bond centres the last character on the node
    assert _label_node_x(100.0, runs, 10, 'Right', (-1.0, 0.0)) > 100.0
