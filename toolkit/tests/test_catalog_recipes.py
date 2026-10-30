from __future__ import annotations

import json
import os
import sys
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

def test_check_matches_com_object_references_bounds_and_kinds():
    results = [
        {"step": 0, "op": "get", "value": {"object": "IChemDrawDocument"}},
        {"step": 1, "op": "get", "value": 3},
        {"step": 2, "op": "get", "value": False},
        {"step": 3, "op": "call", "value": None},
    ]
    recipe = {"expect": [
        {"step": 0, "object": "IChemDrawDocument"},
        {"step": 1, "at_least": 2},
        {"step": 2, "kind": "bool"},
        {"step": 3, "equals": None},
    ]}

    assert recipes.check(recipe, results) == []

    failures = recipes.check({"expect": [
        {"step": 0, "object": "IChemDrawObjects"},
        {"step": 1, "at_least": 4},
        {"step": 2, "kind": "int"},
    ]}, results)
    assert len(failures) == 3


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
        if recipe["tool"] == "chemdraw_com_call":
            continue
        assert recipe["tool"] == "execute_chemscript_sdk"
        assert recipe["platforms"] in (["win"], ["win", "mac"])
        assert recipe["verified_on"].startswith("22.")
        assert all("op" in step for step in recipe["program"])
        assert recipe["expect"], recipe["id"]
        assert all(0 <= item["step"] < len(recipe["program"]) for item in recipe["expect"]), recipe["id"]
        for symbol in recipe["members"]:
            type_name, member = symbol.split(".")
            assert recipes.declaring_type(chemscript, type_name, member) is not None, symbol
            assert type_name in types


def test_committed_com_recipes_name_real_members_and_pass_the_static_program_check():
    from cdxml_toolkit.mcp_runtime import com_call

    com = [r for r in recipes.load() if r["tool"] == "chemdraw_com_call"]
    assert len(com) >= 3
    types = com_call._catalog()["types"]
    for recipe in com:
        assert recipe["layer"] == "com" and recipe["platforms"] == ["win"] and recipe["verified_on"].startswith("22.")
        assert recipe["fixture"].lstrip().startswith("<?xml"), recipe["id"]
        for symbol in recipe["members"]:
            type_name, member = symbol.split(".")
            assert member in types[type_name]["members"], symbol
        program = recipes.fill_program(recipe["program"], fixture="C:/x/fixture.cdxml", out="C:/x/out")
        steps = com_call.validate_program(program, allow_file_io=True)
        assert all(0 <= item["step"] < len(steps) for item in recipe["expect"]), recipe["id"]
        used = {(step["owner_type"], step["member"]) for step in steps if "member" in step}
        used |= {(step["element_type"], name) for step in steps if step["op"] == "iterate" for name in step.get("members", [])}
        assert {tuple(symbol.split(".")) for symbol in recipe["members"]} <= used, recipe["id"]


def test_fill_program_substitutes_paths_everywhere():
    program = [{"op": "call", "args": ["{fixture}", {"nested": ["{out}/a.png"]}]}, {"op": "get", "member": "x"}]

    filled = recipes.fill_program(program, fixture="F", out="O")

    assert filled[0]["args"] == ["F", {"nested": ["O/a.png"]}]
    assert program[0]["args"][0] == "{fixture}"


def test_declaring_type_follows_the_base_chain():
    catalog = {"types": [
        {"name": "ChemicalData", "role": "api", "members": [{"kind": "method", "name": "WriteData"}]},
        {"name": "StructureData", "role": "api", "base": "ChemicalData", "members": [{"kind": "method", "name": "Clone"}]},
    ]}

    assert recipes.declaring_type(catalog, "StructureData", "Clone") == "StructureData"
    assert recipes.declaring_type(catalog, "StructureData", "WriteData") == "ChemicalData"
    assert recipes.declaring_type(catalog, "StructureData", "Nope") is None


@pytest.mark.skipif(os.environ.get("CDX_LIVE") != "1", reason="set CDX_LIVE=1 to run the recipes against the installed ChemDraw")
def test_every_recipe_still_passes_on_the_installed_sdk():
    failures = {r["id"]: recipes.run(r) for r in recipes.load()}

    assert {key: value for key, value in failures.items() if value} == {}


def _mac_recipes():
    return [r for r in recipes.load() if "mac" in r["platforms"]]


def test_recipes_marked_for_macos_use_only_emulated_members():
    from cdxml_toolkit.mcp_runtime import chemscript_sdk_mac

    emulated = {(owner, name) for owner, name, _operation in chemscript_sdk_mac._ALLOWED}
    assert _mac_recipes()
    for recipe in _mac_recipes():
        for symbol in recipe["members"]:
            assert tuple(symbol.split(".")) in emulated, (recipe["id"], symbol)


@pytest.mark.skipif(not (sys.platform == "darwin" and os.environ.get("CDXML_LIVE_CHEMDRAW") == "1"),
                    reason="drives ChemDraw for macOS; set CDXML_LIVE_CHEMDRAW=1 on a Mac")
def test_recipes_marked_for_macos_pass_on_chemdraw_for_macos():
    failures = {r["id"]: recipes.run(r) for r in _mac_recipes()}

    assert {key: value for key, value in failures.items() if value} == {}
