from __future__ import annotations

import xml.etree.ElementTree as ET

import pytest

from cdxml_toolkit.render import renderer
from cdxml_toolkit.render.parser import parse_yaml
from cdxml_toolkit.text_formatting import normalize_condition_text


@pytest.mark.parametrize("raw, expected", [
    ("80 C", "80 °C"),
    ("105C", "105 °C"),
    ("80°C", "80 °C"),
    ("-78 °C", "-78 °C"),
    ("0 to 25 C", "0 to 25 °C"),
    ("80 deg C", "80 °C"),
    ("RT", "rt"),
    ("r.t.", "rt"),
    ("room temperature", "rt"),
    ("12 hr", "12 h"),
    ("12 hrs", "12 h"),
    ("12 hours", "12 h"),
    ("30 mins", "30 min"),
    ("30 minutes", "30 min"),
    ("DMF, 80 C, 12 hr", "DMF, 80 °C, 12 h"),
])
def test_common_notation_is_normalised(raw, expected):
    assert normalize_condition_text(raw) == expected


@pytest.mark.parametrize("text", [
    "Pd(PPh3)4 (5 mol %)",
    "K2CO3, dioxane/H2O",
    "1.2 equiv",
    "overnight",
    "reflux",
    "C10H21Br",
    "rt, 12 h",
])
def test_text_that_is_already_fine_is_unchanged(text):
    assert normalize_condition_text(text) == text


def test_normalising_twice_changes_nothing():
    once = normalize_condition_text("THF, 80 C, 12 hrs, RT")
    assert normalize_condition_text(once) == once


SCHEME = """
layout: linear
structures:
  A: {smiles: "c1ccccc1C(=O)O", label: "1"}
  B: {smiles: "c1ccccc1C(=O)OC", label: "2"}
steps:
  - substrates: [A]
    products: [B]
    above_arrow: {text: ["MeOH, H2SO4"]}
    below_arrow: {text: ["80 C, 12 hrs", "RT"]}
"""


def test_renderer_normalises_condition_lines(tmp_path):
    source = tmp_path / "scheme.yaml"
    source.write_text(SCHEME, encoding="utf-8")
    cdxml = renderer.render(parse_yaml(str(source)))
    text = "".join(ET.fromstring(cdxml[cdxml.index("<CDXML"):]).itertext())

    assert "80 °C, 12 h" in text
    assert "hrs" not in text
