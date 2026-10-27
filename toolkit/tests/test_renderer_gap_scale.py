from __future__ import annotations

import xml.etree.ElementTree as ET

import pytest

from cdxml_toolkit.render import renderer
from cdxml_toolkit.render.parser import SchemeParseError, parse_yaml

SCHEME = """
layout: sequential
{extra}
structures:
  A: {{smiles: "c1ccccc1C(=O)O", label: "1"}}
  B: {{smiles: "c1ccccc1C(=O)OC", label: "2"}}
  C: {{smiles: "c1ccccc1C(=O)N", label: "3"}}
steps:
  - {{substrates: [A], products: [B], above_arrow: {{text: ["MeOH, H2SO4"]}}}}
  - {{substrates: [B], products: [C], above_arrow: {{text: ["NH3, MeOH"]}}}}
"""


def _width(tmp_path, extra=""):
    source = tmp_path / "scheme.yaml"
    source.write_text(SCHEME.format(extra=extra), encoding="utf-8")
    cdxml = renderer.render(parse_yaml(str(source)))
    root = ET.fromstring(cdxml[cdxml.index("<CDXML"):])
    xs = [float(n.get("p").split()[0]) for n in root.iter("n")]
    return max(xs) - min(xs)


def test_default_spacing_is_unchanged(tmp_path):
    assert _width(tmp_path) == _width(tmp_path, extra="gap_scale: 1")


def test_a_larger_gap_scale_spreads_the_row(tmp_path):
    assert _width(tmp_path, extra="gap_scale: 1.6") > _width(tmp_path) + 20


def test_gap_scale_must_be_positive(tmp_path):
    source = tmp_path / "scheme.yaml"
    source.write_text(SCHEME.format(extra="gap_scale: 0"), encoding="utf-8")

    with pytest.raises(SchemeParseError):
        parse_yaml(str(source))
