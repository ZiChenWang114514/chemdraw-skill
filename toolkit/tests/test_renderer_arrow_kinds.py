from __future__ import annotations

import xml.etree.ElementTree as ET

import pytest

from cdxml_toolkit.render import renderer
from cdxml_toolkit.render.compact_parser import parse_compact
from cdxml_toolkit.render.parser import SchemeParseError, parse_yaml

YAML = """
layout: linear
structures:
  A: {{smiles: "CC(C)=O", label: "1"}}
  B: {{smiles: "C=C(C)O", label: "2"}}
steps:
  - {{substrates: [A], products: [B], arrow_style: {style}, above_arrow: {{text: ["H+"]}}}}
"""

COMPACT = 'A{{CC(=O)CC}} {arrow} B{{CC(O)=CC}}'


def _arrows(cdxml):
    return list(ET.fromstring(cdxml[cdxml.index("<CDXML"):]).iter("arrow"))


def _render_yaml(tmp_path, style):
    source = tmp_path / "scheme.yaml"
    source.write_text(YAML.format(style=style), encoding="utf-8")
    return renderer.render(parse_yaml(str(source)))


def test_a_reversible_arrow_is_a_native_equilibrium_arrow(tmp_path):
    (arrow,) = _arrows(_render_yaml(tmp_path, "reversible"))

    assert arrow.get("ArrowheadHead") == "HalfLeft"
    assert arrow.get("ArrowheadTail") == "HalfLeft"
    assert arrow.get("ArrowShaftSpacing")


def test_a_resonance_arrow_has_a_full_head_at_both_ends(tmp_path):
    (arrow,) = _arrows(_render_yaml(tmp_path, "resonance"))

    assert arrow.get("ArrowheadHead") == "Full"
    assert arrow.get("ArrowheadTail") == "Full"
    assert arrow.get("ArrowShaftSpacing") is None


def test_the_default_arrow_is_unchanged(tmp_path):
    (arrow,) = _arrows(_render_yaml(tmp_path, "solid"))

    assert arrow.get("ArrowheadHead") == "Full"
    assert arrow.get("ArrowheadTail") is None


def test_an_unknown_arrow_style_is_still_rejected(tmp_path):
    with pytest.raises(SchemeParseError):
        _render_yaml(tmp_path, "wavy")


@pytest.mark.parametrize("token, style", [("<=>", "reversible"), ("<->", "resonance"),
                                          ("-->", "solid"), ("..>", "dashed")])
def test_compact_text_has_a_token_for_each_arrow(token, style):
    scheme = parse_compact(COMPACT.format(arrow=token))

    assert [s.arrow_style for s in scheme.steps] == [style]


def test_the_reversible_arrow_keeps_its_condition_text_clear_of_the_shafts(tmp_path):
    cdxml = _render_yaml(tmp_path, "reversible")
    page = ET.fromstring(cdxml[cdxml.index("<CDXML"):]).find("page")
    arrow = page.find("arrow")
    top = float(arrow.get("BoundingBox").split()[1])
    condition = next(t for t in page.findall("t") if "H" in "".join(t.itertext()))

    assert float(condition.get("BoundingBox").split()[3]) <= top
