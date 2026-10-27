from __future__ import annotations

import json
import os
from importlib import resources

import pytest

from cdxml_toolkit.catalog import menu

RAW = [
    {"menu": "&Structure", "items": [
        {"caption": "Clean Up Structure", "command_id": 356},
        {"caption": "", "command_id": 0},
        {"caption": "Enhanced Stereochemistry", "command_id": 0},
        {"caption": "Predict ¹H-NMR Shifts", "command_id": 370},
    ]},
    {"menu": "&Add-ins", "items": []},
]


def test_build_catalog_strips_accelerators_and_classifies_items():
    catalog = menu.build_catalog(RAW, verified_on="22.2.0/win")

    assert catalog["layer"] == "menu"
    assert catalog["verified_on"] == "22.2.0/win"
    structure = catalog["menus"][0]
    assert structure["caption"] == "Structure"
    assert structure["items"] == [
        {"caption": "Clean Up Structure", "command_id": 356},
        {"caption": "Enhanced Stereochemistry", "popup": True},
        {"caption": "Predict ¹H-NMR Shifts", "command_id": 370},
    ]
    assert catalog["counts"] == {"menus": 2, "items": 3, "commands": 2, "popups": 1, "separators": 1}


def test_a_command_can_be_found_by_caption_and_id():
    catalog = menu.build_catalog(RAW, verified_on="x")

    assert menu.find_command(catalog, "clean up structure") == ("Structure", 356)
    assert menu.find_command(catalog, "No such item") is None


COMMITTED = resources.files("cdxml_toolkit.catalog").joinpath("data", "menu_22_2.json")


def test_committed_catalog_lists_the_analysis_commands():
    catalog = json.loads(COMMITTED.read_text(encoding="utf-8"))

    assert catalog["layer"] == "menu"
    captions = {item["caption"] for m in catalog["menus"] for item in m["items"]}
    for caption in ("Clean Up Structure", "Check Structure", "Analyze Stoichiometry", "Map Reaction Atoms"):
        assert caption in captions, caption
    assert any("NMR" in caption for caption in captions)
    ids = [item["command_id"] for m in catalog["menus"] for item in m["items"] if "command_id" in item]
    assert all(isinstance(value, int) and value > 0 for value in ids)
    counts = catalog["counts"]
    assert counts["items"] == sum(len(m["items"]) for m in catalog["menus"])
    assert counts["commands"] + counts["popups"] == counts["items"]


@pytest.mark.skipif(os.environ.get("CDX_LIVE") != "1", reason="set CDX_LIVE=1 to read the menus of the installed ChemDraw")
def test_live_extraction_matches_the_committed_catalog():
    live = menu.extract_live()
    committed = json.loads(COMMITTED.read_text(encoding="utf-8"))

    assert live["counts"] == committed["counts"]
