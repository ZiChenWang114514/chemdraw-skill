from __future__ import annotations

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
    assert markush_validate(str(EXAMPLE)) == {'ok': True, 'errors': []}
    assert markush_enumerate(str(EXAMPLE), count=2)['ok']
    assert not markush_enumerate(str(EXAMPLE), count=0)['ok']


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
