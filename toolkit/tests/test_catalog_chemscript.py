from __future__ import annotations

import json
import os
from importlib import resources

import pytest

from cdxml_toolkit.catalog import chemscript

NS = "CambridgeSoft.ChemScript."

XML = """<?xml version="1.0"?>
<doc><assembly><name>CambridgeSoft.ChemScript</name></assembly><members>
<member name="T:CambridgeSoft.ChemScript.Atom">
  <summary><para>class of Atom</para><para>Users cannot create Atom objects directly.</para></summary>
</member>
<member name="M:CambridgeSoft.ChemScript.Atom.SetCartesian(System.Double,System.Double,System.Double)">
  <summary><para>Sets the Cartesian coordinates for the atom</para></summary>
</member>
<member name="M:CambridgeSoft.ChemScript.Atom.GetCartesian">
  <summary>Get the Cartesian coordinates of the atom.</summary>
</member>
<member name="P:CambridgeSoft.ChemScript.Atom.Name"><summary>The element name.</summary></member>
<member name="M:CambridgeSoft.ChemScript.StructureData.#ctor">
  <summary>Creates an empty structure.</summary>
</member>
<member name="M:CambridgeSoft.ChemScript.StructureData.#ctor(System.String)">
  <summary>Creates a structure from a string.</summary>
</member>
</members></doc>
"""


def _member(type_name, kind, name, *, params=0, classification="sdk_api", static=False):
    return {
        "type": NS + type_name,
        "kind": kind,
        "name": name,
        "signature": f"Void {name}()",
        "parameters": [{"name": f"p{i}"} for i in range(params)],
        "static": static,
        "classification": classification,
        "execution_op": "call",
        "reason": None if classification == "sdk_api" else "Native SWIG pointer or handle plumbing",
    }


REFLECTION = {
    "assembly": "CambridgeSoft.ChemScript, Version=22.0.0.0, Culture=neutral, PublicKeyToken=65bb58ea6feffb0a",
    "types": [
        {"name": NS + "Atom", "kind": "class"},
        {"name": NS + "StructureData", "kind": "class"},
        {"name": NS + "AtomList", "kind": "class"},
        {"name": NS + "ChemScriptPINVOKE", "kind": "class"},
    ],
    "members": [
        _member("Atom", "method", "SetCartesian", params=3),
        _member("Atom", "method", "GetCartesian"),
        _member("Atom", "method", "Frobnicate"),
        _member("Atom", "property", "Name"),
        _member("Atom", "method", "getCPtr", classification="interop_infrastructure", static=True),
        _member("StructureData", "constructor", ".ctor"),
        _member("StructureData", "constructor", ".ctor", params=1),
        _member("StructureData", "method", "CleanupStructure", static=False),
        _member("AtomList", "method", "Add", params=1),
        _member("AtomList", "method", "Clear"),
        _member("ChemScriptPINVOKE", "method", "delete_Atom", classification="interop_infrastructure"),
    ],
}


@pytest.fixture()
def xml_path(tmp_path):
    path = tmp_path / "docs.xml"
    path.write_text(XML, encoding="utf-8")
    return path


def test_xml_docs_become_one_line_summaries(xml_path):
    docs = chemscript.parse_xml_docs(xml_path)

    assert docs["T:" + NS + "Atom"] == "class of Atom Users cannot create Atom objects directly."
    assert docs["P:" + NS + "Atom.Name"] == "The element name."


def test_types_are_sorted_into_api_collection_and_interop_roles(xml_path):
    catalog = chemscript.build_catalog(
        REFLECTION, chemscript.parse_xml_docs(xml_path), verified_on="22.2.0/win"
    )

    roles = {t["name"]: t["role"] for t in catalog["types"]}
    assert roles == {
        "Atom": "api",
        "AtomList": "collection",
        "ChemScriptPINVOKE": "interop",
        "StructureData": "api",
    }


def test_only_api_members_are_listed_and_the_rest_are_counted(xml_path):
    catalog = chemscript.build_catalog(
        REFLECTION, chemscript.parse_xml_docs(xml_path), verified_on="22.2.0/win"
    )

    atom = next(t for t in catalog["types"] if t["name"] == "Atom")
    assert [m["name"] for m in atom["members"]] == ["Frobnicate", "GetCartesian", "Name", "SetCartesian"]
    assert atom["interop_members"] == 1
    collection = next(t for t in catalog["types"] if t["name"] == "AtomList")
    assert "members" not in collection and collection["member_count"] == 2
    assert catalog["counts"]["members_listed"] == 7
    assert catalog["counts"]["members_total"] == 11


def test_documentation_is_joined_by_name_and_parameter_count(xml_path):
    catalog = chemscript.build_catalog(
        REFLECTION, chemscript.parse_xml_docs(xml_path), verified_on="22.2.0/win"
    )

    atom = {m["name"]: m for m in next(t for t in catalog["types"] if t["name"] == "Atom")["members"]}
    assert atom["SetCartesian"]["doc"] == "Sets the Cartesian coordinates for the atom"
    assert atom["Name"]["doc"] == "The element name."
    assert "doc" not in atom["Frobnicate"]
    ctors = [m for m in next(t for t in catalog["types"] if t["name"] == "StructureData")["members"]
             if m["kind"] == "constructor"]
    assert [m.get("doc") for m in ctors] == ["Creates an empty structure.", "Creates a structure from a string."]
    assert catalog["counts"]["api_members_undocumented"] == 2


def test_the_catalog_records_where_it_came_from_and_is_deterministic(xml_path):
    docs = chemscript.parse_xml_docs(xml_path)
    first = chemscript.build_catalog(REFLECTION, docs, verified_on="22.2.0/win")
    second = chemscript.build_catalog(json.loads(json.dumps(REFLECTION)), docs, verified_on="22.2.0/win")

    assert first == second
    assert first["layer"] == "chemscript"
    assert first["assembly_version"] == "22.0.0.0"
    assert first["verified_on"] == "22.2.0/win"
    assert first["sources"] == ["reflection", "xml_docs"]


def test_base_types_are_recorded_so_inherited_members_can_be_found(xml_path):
    docs = chemscript.parse_xml_docs(xml_path)

    catalog = chemscript.build_catalog(
        REFLECTION, docs, verified_on="22.2.0/win", bases={NS + "StructureData": NS + "Atom", NS + "Atom": "System.Object"}
    )

    by_name = {t["name"]: t for t in catalog["types"]}
    assert by_name["StructureData"]["base"] == "Atom"
    assert "base" not in by_name["Atom"]


def test_a_missing_documentation_file_is_reported_not_hidden():
    catalog = chemscript.build_catalog(REFLECTION, {}, verified_on="22.2.0/win")

    assert catalog["sources"] == ["reflection"]
    assert catalog["counts"]["api_members_documented"] == 0


COMMITTED = resources.files("cdxml_toolkit.catalog").joinpath("data", "chemscript_22_2.json")


def test_committed_catalog_matches_its_own_counts():
    catalog = json.loads(COMMITTED.read_text(encoding="utf-8"))

    listed = sum(len(t.get("members", [])) for t in catalog["types"])
    assert catalog["counts"]["members_listed"] == listed
    assert catalog["counts"]["types"] == len(catalog["types"]) >= 80
    assert catalog["counts"]["api_members_documented"] + catalog["counts"]["api_members_undocumented"] == listed
    assert all(t["role"] in {"api", "collection", "interop"} for t in catalog["types"])
    assert [t["name"] for t in catalog["types"]] == sorted(t["name"] for t in catalog["types"])
    structure = next(t for t in catalog["types"] if t["name"] == "StructureData")
    assert any(m["name"] == "CleanupStructure" for m in structure["members"])
    # WriteData is declared once on the base class and inherited by structures and reactions.
    assert structure["base"] == "ChemicalData"
    assert next(t for t in catalog["types"] if t["name"] == "ReactionData")["base"] == "ChemicalData"
    chemical = next(t for t in catalog["types"] if t["name"] == "ChemicalData")
    assert any(m["name"] == "WriteData" for m in chemical["members"])


@pytest.mark.skipif(os.environ.get("CDX_LIVE") != "1", reason="set CDX_LIVE=1 to re-read the installed SDK")
def test_live_extraction_matches_the_committed_catalog(tmp_path):
    live = chemscript.extract_live(tmp_path / "reflection.json")
    committed = json.loads(COMMITTED.read_text(encoding="utf-8"))

    assert live["counts"]["types"] == committed["counts"]["types"]
    assert live["counts"]["members_total"] == committed["counts"]["members_total"]
