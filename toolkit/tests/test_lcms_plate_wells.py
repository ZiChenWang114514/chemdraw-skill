"""Regression tests for LCMS plate well parsing and missing-data handling."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from types import SimpleNamespace

import pytest

from cdxml_toolkit.scientific.plots import (
    _detect_plate_dimensions,
    _normalize_well_id,
    _reports_to_well_records,
    build_lcms_plate_cdxml,
)


def test_rack_prefix_is_split_before_matching_well():
    assert _normalize_well_id("Plate1:A5", 0) == "A5"
    assert _normalize_well_id("B:3", 0) == "B3"
    assert _normalize_well_id("A01", 0) == "A1"
    with pytest.raises(ValueError):
        _normalize_well_id("Plate1A5x", 0)


def test_numeric_position_uses_plate_row_count_and_rejects_overflow():
    assert _normalize_well_id("24", 0, n_cols=6, n_rows=4) == "D6"
    assert _normalize_well_id("1:7", 0, n_cols=6, n_rows=4) == "B1"
    with pytest.raises(ValueError, match="outside"):
        _normalize_well_id("25", 0, n_cols=6, n_rows=4)
    assert _normalize_well_id("25", 0) == "C1"


def test_out_of_plate_well_raises_instead_of_being_counted():
    wells = [{"well": "A1", "purity": 80}, {"well": "E1", "purity": 50}]
    with pytest.raises(ValueError, match="E1"):
        build_lcms_plate_cdxml(wells, plate_format=24)


def test_duplicate_well_raises_naming_the_well():
    wells = [{"well": "A1", "purity": 80}, {"well": "a01", "purity": 5}]
    with pytest.raises(ValueError, match="Duplicate well A1"):
        build_lcms_plate_cdxml(wells, plate_format=24)


def test_missing_purity_is_no_data_not_zero():
    wells = [
        {"well": "A1", "purity": 80},
        {"well": "B2"},
        {"well": "C3", "purity": 0.0},
    ]
    res = build_lcms_plate_cdxml(wells, plate_format=24)
    by_id = {w["well"]: w for w in res["wells"]}
    assert by_id["B2"]["purity"] is None and by_id["B2"]["tier"] == "no_data"
    assert by_id["C3"]["purity"] == 0.0 and by_id["C3"]["tier"] == "none"
    assert by_id["B2"]["color"] != by_id["C3"]["color"]
    assert res["best_wells"] == ["A1"]
    assert res["well_count"] == 3
    assert res["tier_counts"]["no_data"] == 1
    texts = ["".join(t.itertext()) for t in ET.fromstring(res["cdxml"]).iter("t")]
    assert "n/d" in texts and "0%" in texts and "-" in texts


def test_numeric_ids_detect_plate_once():
    assert len(_detect_plate_dimensions(["1", "24"], None)[0]) == 4
    assert len(_detect_plate_dimensions(["1", "25"], None)[0]) == 8
    res = build_lcms_plate_cdxml([{"well": "7", "purity": 50}])
    assert res["plate_format"] == "24-well"
    assert res["wells"][0]["well"] == "B1"


def test_sample_index_zero_is_kept():
    rep = SimpleNamespace(well="", sample_id="", sample_name="", filename="", sample_index=0, peaks=[])
    assert _reports_to_well_records([rep])[0]["well"] == 0
