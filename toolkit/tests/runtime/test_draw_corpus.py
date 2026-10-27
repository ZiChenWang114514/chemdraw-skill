"""Regression corpus for ``draw_figure``: a request sentence, the brief an agent
would write for it, and what the report must say. Everything runs without ChemDraw."""
from __future__ import annotations

import copy
import glob
import json
import os
import xml.etree.ElementTree as ET

import pytest

from cdxml_toolkit.mcp_runtime.figure_draw import draw_figure

CORPUS = os.path.join(os.path.dirname(__file__), "draw_corpus")
CASES = [
    json.load(open(path, encoding="utf-8"))
    for path in sorted(glob.glob(os.path.join(CORPUS, "*.json")))
]


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.setenv("CHEMDRAW_OFFLINE", "1")


def _target(case, tmp_path):
    name = case["id"] if case["brief"].get("kind") == "scope" else case["id"] + ".cdxml"
    return str(tmp_path / name)


def _cdxml_files(report):
    if "pages" in report:
        return [page["path"] for page in report["pages"]]
    return [report["output_path"]]


def _root(path):
    text = open(path, encoding="utf-8").read()
    return ET.fromstring(text[text.index("<CDXML"):])


def test_the_corpus_is_not_empty_and_ids_are_unique():
    ids = [case["id"] for case in CASES]
    assert len(ids) >= 20
    assert len(ids) == len(set(ids))
    assert all(case["sentence"] for case in CASES)


@pytest.mark.parametrize("case", CASES, ids=[case["id"] for case in CASES])
def test_each_brief_reports_what_the_corpus_expects(case, tmp_path):
    expect = case["expect"]
    brief = copy.deepcopy(case["brief"])

    report = draw_figure(copy.deepcopy(brief), output_path=_target(case, tmp_path), render=False)

    assert report["ok"] is expect["ok"], report.get("errors")
    for fragment in expect.get("errors_contain", []):
        assert any(fragment in error for error in report["errors"]), report["errors"]
    if not expect["ok"]:
        assert list(tmp_path.iterdir()) == []
        return

    assert report["checks_passed"] is True
    assert report["readback"]["status"] == "matched"
    assert report["lint"]["issues"] == []
    assert report["native"]["status"] == "not_run"
    assert len(report["species"]) == expect["species"]
    if "layout" in expect:
        assert report["layout"] == expect["layout"]
    if "kind" in expect:
        assert report["kind"] == expect["kind"]
    if "pages" in expect:
        assert len(report["pages"]) == expect["pages"]
    if "arrows" in expect:
        assert report["arrows"]["count"] == expect["arrows"]
        assert report["arrows"]["crossings"] == []
    if "balanced" in expect:
        assert [step["balanced"] for step in report["steps"]] == expect["balanced"]
    for fragment in expect.get("warnings_contain", []):
        assert any(fragment in warning for warning in report["warnings"]), report["warnings"]
    for fragment in expect.get("notes_contain", []):
        assert any(fragment in note for note in report["notes"]), report["notes"]
    if not expect.get("warnings_contain"):
        assert not [w for w in report["warnings"] if "does not balance" not in w]
    if expect.get("no_too_wide"):
        assert not [i for i in report["lint"]["issues"] if i["kind"] == "too_wide"]
    if "arrow_attr" in expect:
        (arrow,) = _root(_cdxml_files(report)[0]).iter("arrow")
        assert expect["arrow_attr"] in (arrow.get("ArrowheadHead"), arrow.get("ArrowheadTail"))
    for name in expect.get("curated", []):
        species = next(s for s in report["species"] if s["id"] == name)
        assert species["source"] != "user"
        assert species["smiles"]

    for path in _cdxml_files(report):
        assert os.path.isfile(path)
    # The brief is the agent's input: drawing must never rewrite it.
    assert brief == case["brief"]

