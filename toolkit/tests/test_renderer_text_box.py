from __future__ import annotations

import xml.etree.ElementTree as ET

from cdxml_toolkit.render import renderer


def _box(justification):
    xml, _ = renderer._build_text_element(["MeOH, H2SO4"], 100.0, 200.0, renderer._IDGen(), justification=justification)
    t = ET.fromstring(xml)
    return [float(v) for v in t.get("BoundingBox").split()]


def test_a_left_justified_text_box_starts_at_the_anchor():
    x1, _, x2, _ = _box("Left")

    assert x1 == 100.0
    assert x2 > 100.0


def test_a_right_justified_text_box_ends_at_the_anchor():
    x1, _, x2, _ = _box("Right")

    assert x2 == 100.0
    assert x1 < 100.0


def test_a_centred_text_box_is_centred_on_the_anchor():
    x1, _, x2, _ = _box("Center")

    assert abs((x1 + x2) / 2.0 - 100.0) < 0.01


def test_a_vertical_arrow_condition_does_not_overlap_its_shaft():
    from cdxml_toolkit.mcp_runtime import figure_lint

    ids = renderer._IDGen()
    xml, _ = renderer._build_vertical_arrow(
        100.0, 300.0, 380.0, ids, condition_lines=["SOCl2; NH3"], condition_side="right"
    )
    cdxml = f'<CDXML><page id="1">{xml}</page></CDXML>'

    assert figure_lint.lint_cdxml(cdxml) == []
