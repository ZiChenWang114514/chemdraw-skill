from __future__ import annotations

import pytest

from cdxml_toolkit.catalog import classify, recipes

CHEMSCRIPT = {"layer": "chemscript", "types": [
    {"name": "ChemicalData", "kind": "class", "role": "api", "members": [
        {"kind": "method", "name": "WriteData", "signature": "String WriteData(String)", "doc": "Writes."},
        {"kind": "method", "name": "WriteData", "signature": "String WriteData(String, Boolean)"},
        {"kind": "method", "name": "Mystery", "signature": "Void Mystery()"},
    ]},
    {"name": "StructureData", "kind": "class", "role": "api", "base": "ChemicalData", "members": [
        {"kind": "method", "name": "Clone", "signature": "StructureData Clone()"},
    ]},
    {"name": "AtomList", "kind": "class", "role": "collection", "member_count": 12},
    {"name": "ChemScriptPINVOKE", "kind": "class", "role": "interop", "member_count": 400},
]}
COM = {"layer": "com", "object_library": {"types": [
    {"name": "IChemDrawDocument", "kind": "dispatch", "members": [
        {"kind": "method", "name": "SaveAs", "returns": "void", "parameters": []},
        {"kind": "property", "name": "Width", "type": "double", "access": ["get", "put"]},
    ]},
    {"name": "CDOrbitalType", "kind": "enum", "members": [{"kind": "constant", "name": "kCDOrbitalTypeS", "value": 0}]},
    {"name": "ChemDrawDocument", "kind": "coclass", "implements": ["IChemDrawDocument"]},
]}, "control_library": {"types": [
    {"name": "IChemDrawDocument", "kind": "dispatch", "members": []},
    {"name": "ICtlOnly", "kind": "dispatch", "members": [{"kind": "method", "name": "Go", "returns": "void", "parameters": []}]},
]}}
MENU = {"layer": "menu", "menus": [{"caption": "Structure", "items": [
    {"caption": "Clean Up Structure", "command_id": 356}, {"caption": "Enhanced Stereochemistry", "popup": True}]}]}
CDXML = {"layer": "cdxml", "elements": [
    {"name": "fragment", "evidence": ["observed"]}, {"name": "bioshape", "evidence": ["observed"]},
    {"name": "geometry", "evidence": ["binary"]}, {"name": "splitter", "evidence": []}]}
RECIPES = [
    {"id": "r1", "tool": "execute_chemscript_sdk", "members": ["StructureData.WriteData"]},
    {"id": "c1", "tool": "chemdraw_com_call", "layer": "com", "members": ["IChemDrawDocument.Width", "IChemDrawDocument.SaveAs"]},
]
CLASSIFICATION = {
    "reasons": {
        "chemscript.interop": "plumbing", "chemscript.collection": "wrapper",
        "chemscript.unverified": "no recipe yet", "com.default": "type entry", "com.unverified": "no recipe yet", "com.blocked": "refused", "com.control": "control only",
        "com.enum": "enum values", "com.coclass": "class id", "menu.default": "no menu tool",
        "cdxml.default": "never observed", "cdxml.unconfirmed": "no evidence",
        "cdxml.object": "edited by the object tool",
    },
    "overrides": [
        {"layer": "com", "symbol": "IChemDrawDocument.SaveAs", "tier": "T1", "tool": "convert_cdx_cdxml", "reason": "used"},
        {"layer": "cdxml", "symbol": "fragment", "tier": "T1", "tool": "draw_molecule", "reason": "written"},
    ],
}


def rows():
    return classify.classify(
        {"chemscript": CHEMSCRIPT, "com": COM, "menu": MENU, "cdxml": CDXML}, RECIPES, CLASSIFICATION
    )


def by_id():
    return {row["id"]: row for row in rows()}


def test_chemscript_members_are_tiered_by_recipe_and_inherit_through_the_base_chain():
    found = by_id()

    verified = found["chemscript:ChemicalData.WriteData"]
    assert verified["tier"] == "T2" and verified["recipe"] == "r1" and verified["tool"] == "execute_chemscript_sdk"
    assert verified["overloads"] == 2 and verified["doc"] == "Writes."
    assert found["chemscript:ChemicalData.Mystery"]["tier"] == "T3"
    assert found["chemscript:ChemicalData.Mystery"]["reason"] == "no recipe yet"
    assert found["chemscript:StructureData.Clone"]["tier"] == "T3"
    assert found["chemscript:AtomList"]["reason"] == "wrapper"
    assert found["chemscript:ChemScriptPINVOKE"]["reason"] == "plumbing"


def test_com_rows_cover_members_enums_coclasses_and_control_only_types():
    found = by_id()

    assert found["com:IChemDrawDocument.SaveAs"]["tier"] == "T1"
    assert found["com:IChemDrawDocument.SaveAs"]["tool"] == "convert_cdx_cdxml"
    assert found["com:IChemDrawDocument.Width"]["tier"] == "T2"
    assert found["com:IChemDrawDocument.Width"]["tool"] == "chemdraw_com_call"
    assert found["com:IChemDrawDocument.Width"]["recipe"] == "c1"
    assert found["com:CDOrbitalType"]["reason"] == "enum values"
    assert found["com:ChemDrawDocument"]["reason"] == "class id"
    assert found["com:ICtlOnly.Go"]["tier"] == "T3"
    assert "com:IChemDrawDocument.SaveAs" in found and len([r for r in rows() if r["symbol"] == "IChemDrawDocument"]) == 0


def test_menu_and_cdxml_rows():
    found = by_id()

    assert found["menu:Structure/Clean Up Structure"]["symbol"] == "Structure/Clean Up Structure"
    assert found["menu:Structure/Clean Up Structure"]["command_id"] == 356
    assert found["menu:Structure/Enhanced Stereochemistry"]["kind"] == "popup"
    assert found["cdxml:fragment"]["tier"] == "T1" and found["cdxml:fragment"]["tool"] == "draw_molecule"
    assert found["cdxml:bioshape"]["tier"] == "T1" and found["cdxml:bioshape"]["tool"] == "chemdraw_object"
    assert found["cdxml:geometry"]["tier"] == "T3" and found["cdxml:geometry"]["via"] == "chemdraw_object"
    assert found["cdxml:geometry"]["reason"] == "never observed"
    assert found["cdxml:splitter"]["reason"] == "no evidence"


def test_unknown_override_symbols_are_rejected():
    bad = {**CLASSIFICATION, "overrides": [{"layer": "com", "symbol": "Nope.Nothing", "tier": "T1", "tool": "x", "reason": "r"}]}

    with pytest.raises(ValueError, match="Nope.Nothing"):
        classify.classify({"chemscript": CHEMSCRIPT, "com": COM, "menu": MENU, "cdxml": CDXML}, RECIPES, bad)


def test_every_tier_one_or_two_row_names_a_tool():
    for row in rows():
        if row["tier"] in ("T1", "T2"):
            assert row["tool"], row["id"]
        else:
            assert row["reason"], row["id"]


def test_summary_counts_rows_per_layer_and_tier():
    summary = classify.summarize(rows())

    assert summary["chemscript"] == {"T1": 0, "T2": 1, "T3": 4}
    assert summary["cdxml"] == {"T1": 2, "T2": 0, "T3": 2}


def test_committed_classification_is_consistent_with_the_committed_catalogs_and_the_registry():
    from cdxml_toolkit.mcp_runtime import tool_registry

    catalogs = {layer: classify.load_catalog(layer) for layer in ("chemscript", "com", "menu", "cdxml")}
    classification = classify.load_classification()
    result = classify.classify(catalogs, recipes.load(), classification)
    registry = set(tool_registry.build_registry())

    assert len({row["id"] for row in result}) == len(result)
    for row in result:
        assert row["tier"] in ("T1", "T2", "T3"), row["id"]
        if row["tier"] in ("T1", "T2"):
            assert row["tool"] in registry, row["id"]
        else:
            assert row.get("reason"), row["id"]
    summary = classify.summarize(result)
    assert summary["chemscript"]["T2"] >= 8
    assert summary["com"]["T1"] >= 3
    assert summary["com"]["T2"] >= 15
    assert summary["menu"] == {"T1": 1, "T2": 0, "T3": 158}
    found = {row["id"]: row for row in result}
    assert found["menu:Structure/Analyze Stoichiometry"]["tool"] == "stoichiometry_grid"
    assert sum(summary[layer][tier] for layer in summary for tier in summary[layer]) == len(result)


def test_the_macos_emulation_only_offers_members_the_windows_sdk_has():
    from cdxml_toolkit.mcp_runtime import chemscript_sdk_mac

    catalog = classify.load_catalog("chemscript")
    # Emulation-only helper types stand in for .NET containers and have no SDK class of that name.
    known = {t["name"] for t in catalog["types"]}
    missing = []
    for owner, kind, name, *_ in chemscript_sdk_mac._MEMBERS:
        if kind == "constructor" or owner not in known:
            continue
        if recipes.declaring_type(catalog, owner, name) is None:
            missing.append(f"{owner}.{name}")
    assert missing == []


def test_property_members_are_tier_one_through_the_property_tool():
    found = {row["id"]: row for row in classify.all_rows()}

    for symbol in ("ChemicalData.Formula", "StructureData.Weight", "StructureData.ExactMass",
                   "StructureData.ElementalAnalysis", "StructureData.PartitionCoefficient",
                   "StructureData.Refractivity"):
        row = found[f"chemscript:{symbol}"]
        assert (row["tier"], row["tool"]) == ("T1", "chemdraw_chemical_properties"), symbol
    assert found["chemscript:StructureData.ChemicalName"]["tool"] == "structure_to_name"

