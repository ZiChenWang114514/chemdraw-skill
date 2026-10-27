from __future__ import annotations

import json
import os
import sys
from importlib import resources

import pytest

from cdxml_toolkit.catalog import com


class FakeInfo:
    def GetRefTypeInfo(self, href):
        names = {7: "IChemDrawObject"}

        class Ref:
            def GetDocumentation(self, memid):
                return (names[href], "")

        return Ref()


def test_type_names_follow_pythoncom_typedescs():
    info = FakeInfo()

    assert com.type_name(8, info) == "string"
    assert com.type_name((26, 3), info) == "long*"
    assert com.type_name((26, (29, 7)), info) == "IChemDrawObject*"
    assert com.type_name((27, 12), info) == "variant[]"
    assert com.type_name(99, info) == "vt99"


def test_property_accessors_merge_into_one_member():
    members = [
        {"kind": "property_get", "name": "Visible", "returns": "bool", "parameters": [], "doc": "Shown."},
        {"kind": "property_put", "name": "Visible", "returns": "void",
         "parameters": [{"name": "rhs", "type": "bool"}]},
        {"kind": "method", "name": "Quit", "returns": "void", "parameters": []},
        {"kind": "property_get", "name": "Item", "returns": "IChemDrawObject*",
         "parameters": [{"name": "index", "type": "long"}]},
    ]

    merged = com.merge_properties(members)

    assert merged == [
        {"kind": "property", "name": "Visible", "type": "bool", "access": ["get", "put"], "doc": "Shown."},
        {"kind": "method", "name": "Quit", "returns": "void", "parameters": []},
        {"kind": "property", "name": "Item", "type": "IChemDrawObject*", "access": ["get"],
         "parameters": [{"name": "index", "type": "long"}]},
    ]


@pytest.mark.skipif(sys.platform != "win32", reason="type libraries are read through pythoncom on Windows")
def test_the_walker_reads_a_system_type_library():
    path = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32", "stdole2.tlb")
    if not os.path.isfile(path):
        pytest.skip("stdole2.tlb not present")

    library = com.read_typelib(path)

    assert library["library"] == "stdole"
    names = {t["name"] for t in library["types"]}
    assert {"IFont", "Font", "IPicture", "StdFont"} <= names
    for type_name in ("IFont", "Font"):  # an interface and a dispinterface
        font = next(t for t in library["types"] if t["name"] == type_name)
        name = next(m for m in font["members"] if m["name"] == "Name")
        assert name["kind"] == "property" and "get" in name["access"], type_name
        assert not any(m["name"] in com.INHERITED for m in font["members"])
    assert next(t for t in library["types"] if t["name"] == "StdFont")["implements"]


COMMITTED = resources.files("cdxml_toolkit.catalog").joinpath("data", "com_22_2.json")


def test_committed_catalog_describes_the_application_document_and_objects():
    catalog = json.loads(COMMITTED.read_text(encoding="utf-8"))

    assert catalog["layer"] == "com"
    assert catalog["verified_on"].startswith("22.")
    objects = {t["name"]: t for t in catalog["object_library"]["types"]}
    for name in ("IChemDrawApplication", "IChemDrawDocument", "IChemDrawObjects", "IChemDrawPlasmidMap",
                 "IChemDrawTable", "IChemOfficeMenuItem"):
        assert name in objects, name
    application = {m["name"] for m in objects["IChemDrawApplication"]["members"]}
    assert {"ActiveDocument", "Documents", "Quit", "MenuBars"} <= application
    document = {m["name"]: m for m in objects["IChemDrawDocument"]["members"]}
    assert document["SaveAs"]["kind"] == "method"
    assert document["Visible" if "Visible" in document else "Saved"]["kind"] == "property"
    counts = catalog["counts"]
    assert counts["object_library_types"] == len(catalog["object_library"]["types"])
    assert counts["object_library_members"] == sum(
        len(t.get("members", [])) for t in catalog["object_library"]["types"]
    )
    assert [t["name"] for t in catalog["object_library"]["types"]] == sorted(
        t["name"] for t in catalog["object_library"]["types"]
    )


@pytest.mark.skipif(os.environ.get("CDX_LIVE") != "1", reason="set CDX_LIVE=1 to re-read the installed type libraries")
def test_live_extraction_matches_the_committed_catalog():
    live = com.extract_live()
    committed = json.loads(COMMITTED.read_text(encoding="utf-8"))

    assert live["counts"] == committed["counts"]
