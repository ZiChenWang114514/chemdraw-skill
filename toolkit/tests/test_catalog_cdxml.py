from __future__ import annotations

import json
import os
from importlib import resources

import pytest

from cdxml_toolkit.catalog import cdxml

DOC_A = """<?xml version="1.0" encoding="UTF-8" ?>
<!DOCTYPE CDXML SYSTEM "http://www.cambridgesoft.com/xml/cdxml.dtd" >
<CDXML BoundingBox="1 2 3 4" LineWidth="0.6">
<page id="1" Width="540" HeightPages="1"><fragment id="2"><n id="3" p="10 20" Element="8"/>
<n id="4" p="30 20"/><b id="5" B="3" E="4" Order="2" Display="Bold"/></fragment></page></CDXML>
"""
DOC_B = """<CDXML BoundingBox="5 6 7 8"><page id="1"><fragment id="2"><n id="3" p="1 2" Element="7"/>
<b id="4" B="3" E="3" Display="Wavy"/><mystery id="9" Odd="x"/></fragment></page></CDXML>
"""


@pytest.fixture
def documents(tmp_path):
    first = tmp_path / "a.cdxml"
    second = tmp_path / "b.cdxml"
    broken = tmp_path / "c.cdxml"
    first.write_text(DOC_A, encoding="utf-8")
    second.write_text(DOC_B, encoding="utf-8")
    broken.write_text("<CDXML><page>", encoding="utf-8")
    return [first, second, broken]


def test_scan_counts_elements_attributes_and_nesting(documents):
    observed = cdxml.scan_documents(documents)

    assert observed["documents"] == 2
    assert observed["unparsable"] == 1
    n = observed["elements"]["n"]
    assert n["count"] == 3 and n["documents"] == 2
    assert n["attributes"]["Element"]["count"] == 2
    assert n["attributes"]["p"]["kind"] == "numbers"
    assert n["parents"] == ["fragment"]
    assert observed["elements"]["fragment"]["children"] == ["b", "mystery", "n"]
    bond = observed["elements"]["b"]["attributes"]
    assert bond["Display"]["kind"] == "enum"
    assert bond["Display"]["values"] == ["Bold", "Wavy"]
    assert bond["Order"]["kind"] == "integer"


def test_scan_never_keeps_free_text_values(documents):
    observed = cdxml.scan_documents(documents)

    odd = observed["elements"]["mystery"]["attributes"]["Odd"]
    assert odd["kind"] == "enum" and odd["values"] == ["x"]
    big = cdxml.summarise_values({str(i) for i in range(60)} | {"a1"})
    assert big["kind"] == "string" and "values" not in big


def test_catalog_marks_unobserved_candidates_by_binary_evidence(documents, tmp_path):
    binary = tmp_path / "engine.bin"
    binary.write_bytes(b"\x00bioshape\x00altgroup\x00unrelated\x00")
    observed = cdxml.scan_documents(documents)

    catalog = cdxml.build_catalog(
        observed,
        binary_names=cdxml.binary_names([binary], ["bioshape", "altgroup", "fragment", "tlcplate"]),
        candidates=["bioshape", "altgroup", "fragment", "tlcplate"],
        fixtures=[{"name": "make_altgroup", "status": "ok"}],
        verified_on="22.2.0/win",
    )

    by_name = {item["name"]: item for item in catalog["elements"]}
    assert by_name["fragment"]["evidence"] == ["observed"]
    assert by_name["altgroup"]["evidence"] == ["binary"]
    assert by_name["tlcplate"]["evidence"] == []
    assert "attributes" not in by_name["altgroup"]
    assert catalog["counts"]["elements_observed"] == 6
    assert catalog["counts"]["elements"] == 9
    assert catalog["counts"]["elements_binary_only"] == 2
    assert catalog["counts"]["elements_unconfirmed"] == 1


COMMITTED = resources.files("cdxml_toolkit.catalog").joinpath("data", "cdxml_model_22_2.json")


def test_committed_catalog_covers_the_structural_elements_and_their_attributes():
    catalog = json.loads(COMMITTED.read_text(encoding="utf-8"))

    assert catalog["layer"] == "cdxml"
    assert catalog["verified_on"].startswith("22.")
    by_name = {item["name"]: item for item in catalog["elements"]}
    for name in ("CDXML", "page", "fragment", "n", "b", "t", "s", "arrow", "graphic", "curve", "bioshape",
                 "plasmidmap", "table", "group", "objecttag", "chemicalproperty", "annotation", "embeddedobject"):
        assert "observed" in by_name[name]["evidence"], name
    attributes = {a["name"] for a in by_name["b"]["attributes"]}
    assert {"B", "E", "Order", "Display"} <= attributes
    counts = catalog["counts"]
    assert counts["elements"] == len(catalog["elements"])
    assert counts["attributes"] == sum(len(item.get("attributes", [])) for item in catalog["elements"])
    assert [item["name"] for item in catalog["elements"]] == sorted(item["name"] for item in catalog["elements"])


@pytest.mark.skipif(os.environ.get("CDX_LIVE") != "1", reason="set CDX_LIVE=1 to rescan the installed ChemDraw files")
def test_live_extraction_matches_the_committed_catalog(tmp_path):
    live = cdxml.extract_live(tmp_path, verified_on="22.2.0/win")
    committed = json.loads(COMMITTED.read_text(encoding="utf-8"))

    assert live["counts"] == committed["counts"]
