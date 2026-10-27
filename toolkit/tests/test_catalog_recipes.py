from __future__ import annotations

import json
import os
from importlib import resources

import pytest

from cdxml_toolkit.catalog import recipes

RESULTS = [
    {"step": 0, "op": "call_static", "value": {"$ref": "mol", "$type": "CambridgeSoft.ChemScript.StructureData"}},
    {"step": 1, "op": "call", "value": "C6H6O"},
    {"step": 2, "op": "get", "value": 94.1131},
    {"step": 3, "op": "call", "value": "<CDXML id=\"1\"></CDXML>"},
]


def test_check_accepts_matching_results():
    recipe = {"expect": [
        {"step": 0, "type": "StructureData"},
        {"step": 1, "equals": "C6H6O"},
        {"step": 2, "approx": 94.113, "tolerance": 0.01},
        {"step": 3, "contains": "<CDXML"},
    ]}

    assert recipes.check(recipe, RESULTS) == []


def test_check_names_each_mismatch():
    recipe = {"expect": [
        {"step": 1, "equals": "C6H6"},
        {"step": 2, "approx": 95.0, "tolerance": 0.01},
        {"step": 3, "contains": "<cdxml"},
        {"step": 9, "equals": 1},
    ]}

    failures = recipes.check(recipe, RESULTS)

    assert len(failures) == 4
    assert "step 1" in failures[0] and "C6H6" in failures[0]
    assert "step 9" in failures[3] and "missing" in failures[3]


COMMITTED = resources.files("cdxml_toolkit.catalog").joinpath("data", "recipes.json")


def test_committed_recipes_are_well_formed_and_cover_real_symbols():
    document = json.loads(COMMITTED.read_text(encoding="utf-8"))
    chemscript = json.loads(
        resources.files("cdxml_toolkit.catalog").joinpath("data", "chemscript_22_2.json").read_text(encoding="utf-8")
    )
    types = {t["name"]: t for t in chemscript["types"]}

    ids = [r["id"] for r in document["recipes"]]
    assert len(ids) == len(set(ids)) >= 5
    for recipe in document["recipes"]:
        assert recipe["tool"] == "execute_chemscript_sdk"
        assert recipe["platforms"] == ["win"]
        assert recipe["verified_on"].startswith("22.")
        assert all("op" in step for step in recipe["program"])
        assert recipe["expect"], recipe["id"]
        assert all(0 <= item["step"] < len(recipe["program"]) for item in recipe["expect"]), recipe["id"]
        for symbol in recipe["members"]:
            type_name, member = symbol.split(".")
            assert recipes.declaring_type(chemscript, type_name, member) is not None, symbol
            assert type_name in types


def test_declaring_type_follows_the_base_chain():
    catalog = {"types": [
        {"name": "ChemicalData", "role": "api", "members": [{"kind": "method", "name": "WriteData"}]},
        {"name": "StructureData", "role": "api", "base": "ChemicalData", "members": [{"kind": "method", "name": "Clone"}]},
    ]}

    assert recipes.declaring_type(catalog, "StructureData", "Clone") == "StructureData"
    assert recipes.declaring_type(catalog, "StructureData", "WriteData") == "ChemicalData"
    assert recipes.declaring_type(catalog, "StructureData", "Nope") is None


@pytest.mark.skipif(os.environ.get("CDX_LIVE") != "1", reason="set CDX_LIVE=1 to run the recipes against the installed SDK")
def test_every_recipe_still_passes_on_the_installed_sdk():
    failures = {r["id"]: recipes.run(r) for r in recipes.load()}

    assert {key: value for key, value in failures.items() if value} == {}
