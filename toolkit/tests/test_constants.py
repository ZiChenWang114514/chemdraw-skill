"""Unit tests for constants.py — centralized project constants."""

import pytest

from cdxml_toolkit.constants import (
    ACS_BOND_LENGTH,
    ACS_BOND_LENGTH_STR,
    ACS_BOLD_WIDTH,
    ACS_CAPTION_SIZE,
    ACS_CHAIN_ANGLE,
    ACS_CHAIN_ANGLE_STR,
    ACS_HASH_SPACING,
    ACS_LABEL_FACE,
    ACS_LABEL_FONT,
    ACS_LABEL_SIZE,
    ACS_LINE_WIDTH,
    ACS_MARGIN_WIDTH,
    ACS_STYLE,
    CDXML_FOOTER,
    CDXML_HEADER,
    CDXML_MINIMAL_HEADER,
    EXPAND_SCALE_BOND,
    LAYOUT_ABOVE_GAP,
    LAYOUT_BELOW_GAP,
    LAYOUT_FRAG_GAP_BONDS,
    LAYOUT_HANGING_LABEL_GAP,
    LAYOUT_INTER_FRAGMENT_GAP,
    LAYOUT_INTER_GAP_BONDS,
    LCMS_COLUMN_BOUNDARY,
    LCMS_MIN_SUMMARY_AREA,
    LCMS_MS_AXIS_TICKS,
    LCMS_MZ_TOLERANCE,
    LCMS_RT_TOLERANCE,
    LCMS_TREND_THRESHOLD,
    LCMS_UV_AXIS_TICKS,
    LCMS_UV_WAVELENGTH_MAX,
    LCMS_UV_WAVELENGTH_MIN,
    MASS_TOLERANCE,
    MIN_REPORT_AREA_PCT,
    MW_MATCH_TOLERANCE,
)


# =========================================================================
# ACS Document 1996 style constants
# =========================================================================

class TestACSConstants:
    def test_bond_length_value(self):
        assert ACS_BOND_LENGTH == 14.40

    def test_bond_length_is_float(self):
        assert isinstance(ACS_BOND_LENGTH, float)

    def test_bond_length_str(self):
        assert ACS_BOND_LENGTH_STR == "14.40"

    def test_chain_angle_value(self):
        assert ACS_CHAIN_ANGLE == 120

    def test_chain_angle_str(self):
        assert ACS_CHAIN_ANGLE_STR == "120"

    def test_label_font_is_arial(self):
        assert ACS_LABEL_FONT == "3"

    def test_label_size(self):
        assert ACS_LABEL_SIZE == "10"

    def test_label_face(self):
        assert ACS_LABEL_FACE == "96"

    def test_caption_size(self):
        assert ACS_CAPTION_SIZE == "10"

    def test_line_width(self):
        assert ACS_LINE_WIDTH == "0.60"

    def test_bold_width(self):
        assert ACS_BOLD_WIDTH == "2"

    def test_hash_spacing(self):
        assert ACS_HASH_SPACING == "2.50"

    def test_margin_width(self):
        assert ACS_MARGIN_WIDTH == "1.60"


# =========================================================================
# ACS_STYLE dict
# =========================================================================

class TestACSStyle:
    def test_is_dict(self):
        assert isinstance(ACS_STYLE, dict)

    def test_has_bond_length(self):
        assert ACS_STYLE["BondLength"] == ACS_BOND_LENGTH_STR

    def test_has_chain_angle(self):
        assert ACS_STYLE["ChainAngle"] == ACS_CHAIN_ANGLE_STR

    def test_all_values_are_strings(self):
        for k, v in ACS_STYLE.items():
            assert isinstance(v, str), f"ACS_STYLE[{k!r}] is {type(v)}, expected str"


# =========================================================================
# LCMS constants
# =========================================================================

class TestLCMSConstants:
    def test_rt_tolerance_positive(self):
        assert LCMS_RT_TOLERANCE > 0

    def test_mz_tolerance_positive(self):
        assert LCMS_MZ_TOLERANCE > 0

    def test_trend_threshold_positive(self):
        assert LCMS_TREND_THRESHOLD > 0

    def test_min_summary_area_positive(self):
        assert LCMS_MIN_SUMMARY_AREA > 0

    def test_column_boundary_positive(self):
        assert LCMS_COLUMN_BOUNDARY > 0

    def test_uv_wavelength_range(self):
        assert LCMS_UV_WAVELENGTH_MIN < LCMS_UV_WAVELENGTH_MAX
        assert LCMS_UV_WAVELENGTH_MIN > 0

    def test_ms_axis_ticks_is_set(self):
        assert isinstance(LCMS_MS_AXIS_TICKS, set)
        assert len(LCMS_MS_AXIS_TICKS) > 0

    def test_uv_axis_ticks_is_set(self):
        assert isinstance(LCMS_UV_AXIS_TICKS, set)
        assert len(LCMS_UV_AXIS_TICKS) > 0

    def test_all_lcms_numbers_positive(self):
        for val in [LCMS_RT_TOLERANCE, LCMS_MZ_TOLERANCE, LCMS_TREND_THRESHOLD,
                     LCMS_MIN_SUMMARY_AREA, LCMS_COLUMN_BOUNDARY,
                     LCMS_UV_WAVELENGTH_MIN, LCMS_UV_WAVELENGTH_MAX]:
            assert isinstance(val, (int, float))
            assert val > 0


# =========================================================================
# Mass matching constants
# =========================================================================

class TestMassConstants:
    def test_mw_match_tolerance_positive(self):
        assert MW_MATCH_TOLERANCE > 0

    def test_mass_tolerance_positive(self):
        assert MASS_TOLERANCE > 0

    def test_min_report_area_positive(self):
        assert MIN_REPORT_AREA_PCT > 0


# =========================================================================
# Layout constants
# =========================================================================

class TestLayoutConstants:
    def test_above_gap_positive(self):
        assert LAYOUT_ABOVE_GAP > 0

    def test_below_gap_positive(self):
        assert LAYOUT_BELOW_GAP > 0

    def test_hanging_label_gap_larger_than_above(self):
        assert LAYOUT_HANGING_LABEL_GAP > LAYOUT_ABOVE_GAP

    def test_inter_fragment_gap_positive(self):
        assert LAYOUT_INTER_FRAGMENT_GAP > 0

    def test_frag_gap_bonds_positive(self):
        assert LAYOUT_FRAG_GAP_BONDS > 0

    def test_inter_gap_bonds_positive(self):
        assert LAYOUT_INTER_GAP_BONDS > 0


# =========================================================================
# CDXML templates
# =========================================================================

class TestCDXMLTemplates:
    def test_header_has_bbox_placeholder(self):
        assert "{bbox}" in CDXML_HEADER

    def test_header_has_xml_declaration(self):
        assert "<?xml" in CDXML_HEADER

    def test_header_has_doctype(self):
        assert "<!DOCTYPE CDXML" in CDXML_HEADER

    def test_minimal_header_has_bond_length(self):
        assert ACS_BOND_LENGTH_STR in CDXML_MINIMAL_HEADER

    def test_footer_closes_cdxml(self):
        assert CDXML_FOOTER == "</CDXML>"

    def test_expand_scale_bond_positive(self):
        assert EXPAND_SCALE_BOND > 0
