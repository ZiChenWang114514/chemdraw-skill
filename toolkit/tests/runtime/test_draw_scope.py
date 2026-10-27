from __future__ import annotations

import copy
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from cdxml_toolkit.mcp_runtime import figure_scope
from cdxml_toolkit.mcp_runtime.figure_draw import draw_figure

SCOPE = {
    "kind": "scope",
    "title": "Substrate scope",
    "conditions": "Conditions as reported by the user.",
    "footnotes": ["a Isolated yield."],
    "species": [
        {"id": "3a", "smiles": "Cc1ccccc1", "label": "3a", "values": {"yield": "85%", "ee": "92%"}},
        {"id": "3b", "smiles": "COc1ccccc1", "label": "3b", "values": {"yield": "78%", "ee": "90%"}},
        {"id": "3c", "smiles": "Clc1ccccc1", "label": "3c", "values": {"yield": "81%"}},
        {"id": "3d", "smiles": "Fc1ccccc1", "label": "3d", "values": {"yield": "74%", "ee": "88%"}},
    ],
}


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.setenv("CHEMDRAW_OFFLINE", "1")


def _brief(**changes):
    brief = copy.deepcopy(SCOPE)
    brief.update(changes)
    return brief


def _pages(report):
    return [ET.parse(page["path"]).getroot() for page in report["pages"]]


def _texts(report):
    return [" ".join("".join(t.itertext()).split()) for root in _pages(report) for t in root.iter("t")]


def test_a_scope_brief_is_drawn_into_a_folder_of_editable_pages(tmp_path):
    out = tmp_path / "scope"

    report = draw_figure(SCOPE, output_path=str(out))

    assert report["ok"] is True
    assert report["kind"] == "scope"
    assert report["output_dir"] == str(out)
    assert (out / "page-001.cdxml").is_file()
    assert [Path(p["path"]).name for p in report["pages"]] == ["page-001.cdxml"]
    assert len(report["species"]) == 4
    assert {s["source"] for s in report["species"]} == {"user"}
    assert report["readback"]["status"] == "matched"
    assert report["checks_passed"] is True


def test_labels_and_values_stay_with_their_structures(tmp_path):
    report = draw_figure(SCOPE, output_path=str(tmp_path / "scope"))
    texts = _texts(report)

    for expected in ("3a", "yield: 85%", "ee: 92%", "Substrate scope", "Conditions as reported by the user."):
        assert expected in texts


def test_a_missing_value_is_shown_as_a_dash_and_named_in_the_notes(tmp_path):
    report = draw_figure(SCOPE, output_path=str(tmp_path / "scope"))

    assert "ee: —" in _texts(report)
    assert any("3c" in note and "ee" in note for note in report["notes"])


def test_the_columns_follow_the_fields_the_brief_names(tmp_path):
    brief = _brief(fields=[{"key": "ee", "label": "ee", "unit": "%"}, "yield"])
    for entry in brief["species"]:
        entry["values"] = {k: v.rstrip("%") for k, v in entry["values"].items()}

    report = draw_figure(brief, output_path=str(tmp_path / "scope"))
    texts = _texts(report)

    assert [f["key"] for f in report["fields"]] == ["ee", "yield"]
    assert "ee: 92 %" in texts
    assert "yield: 85" in texts


def test_groups_become_headings_in_first_seen_order(tmp_path):
    brief = _brief()
    for entry, group in zip(brief["species"], ("para", "ortho", "para", "ortho")):
        entry["group"] = group

    report = draw_figure(brief, output_path=str(tmp_path / "scope"))
    texts = _texts(report)

    assert texts.index("para") < texts.index("ortho")


def test_many_compounds_continue_on_further_pages(tmp_path):
    brief = _brief(width_mm=90, height_mm=90)
    brief["species"] = [
        {"id": f"c{i}", "smiles": "c1ccccc1" + "C" * (i % 5), "label": str(i), "values": {"yield": f"{50 + i}%"}}
        for i in range(1, 25)
    ]

    report = draw_figure(brief, output_path=str(tmp_path / "scope"))

    assert report["ok"] is True
    assert len(report["pages"]) > 1
    assert report["readback"]["status"] == "matched"
    assert sum(p["compounds"] for p in report["pages"]) == 24


def test_native_rendering_is_not_claimed_when_it_did_not_run(tmp_path):
    report = draw_figure(SCOPE, output_path=str(tmp_path / "scope"))

    assert report["native"]["status"] == "not_run"
    assert any("not been rendered" in n for n in report["notes"])


def test_a_native_render_lists_the_pngs(tmp_path, monkeypatch):
    def fake(stage, pages):
        (stage / "png").mkdir()
        for page in pages:
            (stage / "png" / page["file"].replace(".cdxml", ".png")).write_bytes(b"png")
        return {"status": "rendered_pending_visual_review", "formats": ["png", "svg"]}

    monkeypatch.setattr("cdxml_toolkit.mcp_runtime.publication_figure._native_previews", fake)

    report = draw_figure(SCOPE, output_path=str(tmp_path / "scope"), render=True)

    assert report["native"]["status"] == "rendered"
    assert [Path(p).name for p in report["native"]["png_paths"]] == ["page-001.png"]


def test_without_an_output_path_a_fresh_folder_is_made(tmp_path, monkeypatch):
    monkeypatch.setattr("tempfile.tempdir", str(tmp_path))

    first = draw_figure(SCOPE)
    second = draw_figure(SCOPE)

    assert first["output_dir"] != second["output_dir"]
    assert Path(first["output_dir"]).is_dir() and Path(second["output_dir"]).is_dir()


def test_an_existing_folder_is_never_overwritten(tmp_path):
    out = tmp_path / "scope"
    out.mkdir()
    (out / "keep.txt").write_text("mine", encoding="utf-8")

    report = draw_figure(SCOPE, output_path=str(out))

    assert report["ok"] is False
    assert (out / "keep.txt").read_text(encoding="utf-8") == "mine"
    assert not (out / "page-001.cdxml").exists()


def test_a_name_that_cannot_be_resolved_stops_the_run(tmp_path):
    brief = _brief()
    brief["species"][0] = {"id": "3a", "name": "no-such-compound-zzz", "values": {"yield": "85%"}}

    report = draw_figure(brief, output_path=str(tmp_path / "scope"))

    assert report["ok"] is False
    assert "no-such-compound-zzz" in " ".join(report["errors"])
    assert not (tmp_path / "scope").exists()


@pytest.mark.parametrize(
    "change, message",
    [
        ({"steps": [{}]}, "steps"),
        ({"surprise": 1}, "Unknown brief keys"),
        ({"fields": [{"label": "x"}]}, "key"),
        ({"fields": ["yield", "yield"]}, "duplicate"),
        ({"footnotes": "a single string"}, "footnotes"),
        ({"width_mm": 5}, "width_mm"),
    ],
)
def test_a_malformed_scope_brief_is_refused_with_a_reason(tmp_path, change, message):
    report = draw_figure(_brief(**change), output_path=str(tmp_path / "scope"))

    assert report["ok"] is False
    assert message in " ".join(report["errors"])


def test_a_value_for_an_unlisted_field_is_refused(tmp_path):
    brief = _brief(fields=["yield"])

    report = draw_figure(brief, output_path=str(tmp_path / "scope"))

    assert report["ok"] is False
    assert "ee" in " ".join(report["errors"])


def test_duplicate_ids_are_refused(tmp_path):
    brief = _brief()
    brief["species"][1]["id"] = "3a"

    report = draw_figure(brief, output_path=str(tmp_path / "scope"))

    assert report["ok"] is False
    assert "duplicate" in " ".join(report["errors"])


def test_the_scope_checks_are_the_publication_checks(tmp_path):
    report = draw_figure(SCOPE, output_path=str(tmp_path / "scope"))

    assert report["checks"]["data_binding"]["status"] == "passed"
    assert report["lint"]["issues"] == []


def test_the_brief_validator_names_the_scope_keys():
    assert {"fields", "conditions", "footnotes", "width_mm", "height_mm"} <= figure_scope.SCOPE_KEYS
