"""Unit tests for cdxml_utils.py — CDXML geometry and IO utilities."""

import xml.etree.ElementTree as ET

import pytest

from cdxml_toolkit.cdxml_utils import (
    build_id_map,
    fragment_bbox,
    fragment_bbox_with_label_extension,
    fragment_bottom_has_hanging_label,
    fragment_centroid,
    recompute_text_bbox,
)
from cdxml_toolkit.constants import LAYOUT_HANGING_LABEL_GAP


# =========================================================================
# Shared test fragments
# =========================================================================

def _make_simple_fragment():
    """Two-carbon fragment: atom1 at (100,200), atom2 at (114.4,200)."""
    xml = """\
    <fragment id="100">
      <n id="1" p="100 200" Element="6"/>
      <n id="2" p="114.4 200" Element="6"/>
      <b id="10" B="1" E="2"/>
    </fragment>"""
    return ET.fromstring(xml)


def _make_three_atom_fragment():
    """Three atoms: C(100,200), N(120,180), C(140,200). Two bonds."""
    xml = """\
    <fragment id="100">
      <n id="1" p="100 200" Element="6" />
      <n id="2" p="120 180" Element="7" NumHydrogens="1" />
      <n id="3" p="140 200" />
      <b id="10" B="1" E="2" />
      <b id="11" B="2" E="3" />
    </fragment>"""
    return ET.fromstring(xml)


# =========================================================================
# fragment_bbox
# =========================================================================

class TestFragmentBbox:
    def test_simple_two_atom(self):
        frag = _make_simple_fragment()
        bbox = fragment_bbox(frag)
        assert bbox is not None
        assert bbox == (100.0, 200.0, 114.4, 200.0)

    def test_three_atom(self):
        frag = _make_three_atom_fragment()
        bbox = fragment_bbox(frag)
        assert bbox is not None
        assert bbox == (100.0, 180.0, 140.0, 200.0)

    def test_empty_fragment_returns_none(self):
        frag = ET.fromstring('<fragment id="1" />')
        assert fragment_bbox(frag) is None

    def test_fallback_to_xml_boundingbox(self):
        xml = '<fragment id="1" BoundingBox="10 20 30 40" />'
        frag = ET.fromstring(xml)
        bbox = fragment_bbox(frag)
        assert bbox == (10.0, 20.0, 30.0, 40.0)


# =========================================================================
# fragment_centroid
# =========================================================================

class TestFragmentCentroid:
    def test_simple_two_atom(self):
        frag = _make_simple_fragment()
        c = fragment_centroid(frag)
        assert c is not None
        assert abs(c[0] - 107.2) < 0.01
        assert abs(c[1] - 200.0) < 0.01

    def test_three_atom(self):
        frag = _make_three_atom_fragment()
        c = fragment_centroid(frag)
        assert c is not None
        assert abs(c[0] - 120.0) < 0.01
        assert abs(c[1] - 190.0) < 0.01

    def test_empty_fragment_returns_none(self):
        frag = ET.fromstring('<fragment id="1" />')
        assert fragment_centroid(frag) is None


# =========================================================================
# fragment_bottom_has_hanging_label
# =========================================================================

class TestHangingLabel:
    def test_n_not_at_bottom_no_hang(self):
        """N at y=180 is above C at y=200 — no hanging label."""
        frag = _make_three_atom_fragment()
        assert fragment_bottom_has_hanging_label(frag) is False

    def test_n_at_bottom_hangs(self):
        """N at y=200 (bottom) with 1 bond — hanging label."""
        xml = """\
        <fragment id="200">
          <n id="1" p="100 180" Element="6" />
          <n id="2" p="120 200" Element="7" />
          <b id="10" B="1" E="2" />
        </fragment>"""
        frag = ET.fromstring(xml)
        assert fragment_bottom_has_hanging_label(frag) is True

    def test_p_at_bottom_hangs(self):
        """P (Element=15) at bottom with 2 bonds — hanging label."""
        xml = """\
        <fragment id="300">
          <n id="1" p="100 180" Element="6" />
          <n id="2" p="120 200" Element="15" />
          <n id="3" p="140 180" Element="6" />
          <b id="10" B="1" E="2" />
          <b id="11" B="2" E="3" />
        </fragment>"""
        frag = ET.fromstring(xml)
        assert fragment_bottom_has_hanging_label(frag) is True

    def test_carbon_at_bottom_no_hang(self):
        """Carbon (Element=6) at bottom — no hanging label."""
        xml = """\
        <fragment id="400">
          <n id="1" p="100 180" Element="7" />
          <n id="2" p="120 200" Element="6" />
          <b id="10" B="1" E="2" />
        </fragment>"""
        frag = ET.fromstring(xml)
        assert fragment_bottom_has_hanging_label(frag) is False

    def test_empty_fragment(self):
        frag = ET.fromstring('<fragment id="1" />')
        assert fragment_bottom_has_hanging_label(frag) is False


# =========================================================================
# build_id_map
# =========================================================================

class TestBuildIdMap:
    def test_simple_fragment(self):
        frag = _make_simple_fragment()
        m = build_id_map(frag)
        # fragment id="100", two atoms id="1","2", one bond id="10"
        assert "100" in m
        assert "1" in m
        assert "2" in m
        assert "10" in m

    def test_nested_elements(self):
        xml = '<page><n id="1"><n id="2"><n id="3" /></n></n></page>'
        page = ET.fromstring(xml)
        m = build_id_map(page)
        assert "1" in m
        assert "2" in m
        assert "3" in m

    def test_empty_element(self):
        el = ET.fromstring('<page />')
        m = build_id_map(el)
        assert len(m) == 0  # no id attribute on <page>


# =========================================================================
# recompute_text_bbox
# =========================================================================

class TestRecomputeTextBbox:
    def test_sets_boundingbox(self):
        t = ET.fromstring('<t id="1" p="100 200"><s>Hello</s></t>')
        recompute_text_bbox(t)
        bb = t.get("BoundingBox")
        assert bb is not None
        vals = [float(v) for v in bb.split()]
        assert len(vals) == 4

    def test_left_justified_starts_at_anchor(self):
        t = ET.fromstring('<t id="1" p="100 200"><s>Test</s></t>')
        recompute_text_bbox(t)
        vals = [float(v) for v in t.get("BoundingBox").split()]
        # Left-justified: x1 should be at anchor x (100)
        assert abs(vals[0] - 100.0) < 0.01

    def test_no_p_attribute_does_nothing(self):
        t = ET.fromstring('<t id="1"><s>Test</s></t>')
        recompute_text_bbox(t)
        assert t.get("BoundingBox") is None

    def test_multiline_text(self):
        t = ET.fromstring('<t id="1" p="100 200"><s>Line1\nLine2</s></t>')
        recompute_text_bbox(t)
        bb = t.get("BoundingBox")
        assert bb is not None
        vals = [float(v) for v in bb.split()]
        # Two lines: y2 should be larger than for single line
        assert vals[3] > vals[1]


# =========================================================================
# fragment_bbox_with_label_extension
# =========================================================================

class TestFragmentBboxWithLabelExtension:
    def test_no_hanging_label_matches_plain_bbox(self):
        """Fragment without hanging label — should equal fragment_bbox."""
        frag = _make_simple_fragment()
        bbox = fragment_bbox_with_label_extension(frag)
        assert bbox == fragment_bbox(frag)

    def test_hanging_label_extends_max_y(self):
        """N at bottom with 1 bond — max_y extended by LAYOUT_HANGING_LABEL_GAP."""
        xml = """\
        <fragment id="200">
          <n id="1" p="100 180" Element="6" />
          <n id="2" p="120 200" Element="7" />
          <b id="10" B="1" E="2" />
        </fragment>"""
        frag = ET.fromstring(xml)
        bbox = fragment_bbox_with_label_extension(frag)
        base = fragment_bbox(frag)
        assert bbox is not None and base is not None
        assert bbox[0] == base[0]  # min_x unchanged
        assert bbox[1] == base[1]  # min_y unchanged
        assert bbox[2] == base[2]  # max_x unchanged
        assert bbox[3] == base[3] + LAYOUT_HANGING_LABEL_GAP  # max_y extended

    def test_empty_fragment_returns_none(self):
        frag = ET.fromstring('<fragment id="1" />')
        assert fragment_bbox_with_label_extension(frag) is None

    def test_three_atom_n_not_at_bottom(self):
        """N at y=180 is above C at y=200 — no extension."""
        frag = _make_three_atom_fragment()
        bbox = fragment_bbox_with_label_extension(frag)
        assert bbox == fragment_bbox(frag)
