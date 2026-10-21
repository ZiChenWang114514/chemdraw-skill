"""Unit tests for text_formatting.py — chemical text formatting for CDXML."""

import pytest

from cdxml_toolkit.text_formatting import (
    ITALIC_PREFIXES,
    SUBSCRIPT_RE,
    build_formatted_s_xml,
    needs_subscript,
    split_italic_prefix,
)


# =========================================================================
# needs_subscript
# =========================================================================

class TestNeedsSubscript:
    def test_ch3oh_needs_subscript(self):
        assert needs_subscript("CH3OH") is True

    def test_et3n_needs_subscript(self):
        assert needs_subscript("Et3N") is True

    def test_cs2co3_needs_subscript(self):
        assert needs_subscript("Cs2CO3") is True

    def test_pd2dba3_needs_subscript(self):
        assert needs_subscript("Pd2(dba)3") is True

    def test_dmf_no_subscript(self):
        assert needs_subscript("DMF") is False

    def test_rt_no_subscript(self):
        assert needs_subscript("rt") is False

    def test_temperature_no_subscript(self):
        assert needs_subscript("80 °C") is False

    def test_duration_no_subscript(self):
        assert needs_subscript("2 h") is False

    def test_percentage_no_subscript(self):
        assert needs_subscript("95%") is False

    def test_plain_text_no_subscript(self):
        assert needs_subscript("reflux") is False


# =========================================================================
# split_italic_prefix
# =========================================================================

class TestSplitItalicPrefix:
    def test_n_buli(self):
        assert split_italic_prefix("n-BuLi") == ("n-", "BuLi")

    def test_tert_butanol(self):
        assert split_italic_prefix("tert-butanol") == ("tert-", "butanol")

    def test_tert_buoh(self):
        assert split_italic_prefix("tert-BuOH") == ("tert-", "BuOH")

    def test_n_boc(self):
        assert split_italic_prefix("N-Boc") == ("N-", "Boc")

    def test_sec_buli(self):
        assert split_italic_prefix("sec-BuLi") == ("sec-", "BuLi")

    def test_no_prefix(self):
        assert split_italic_prefix("Cs2CO3") == ("", "Cs2CO3")

    def test_no_prefix_plain(self):
        assert split_italic_prefix("DMF") == ("", "DMF")


# =========================================================================
# build_formatted_s_xml
# =========================================================================

class TestBuildFormattedSXml:
    def test_et3n_has_subscript(self):
        xml = build_formatted_s_xml("Et3N")
        assert "<s " in xml
        # face="32" is subscript
        assert 'face="32"' in xml

    def test_et3n_has_formula_face(self):
        xml = build_formatted_s_xml("Et3N")
        assert 'face="96"' in xml

    def test_dmf_no_subscript(self):
        xml = build_formatted_s_xml("DMF")
        assert 'face="32"' not in xml

    def test_dmf_has_formula_face(self):
        xml = build_formatted_s_xml("DMF")
        assert 'face="96"' in xml

    def test_n_buli_has_italic(self):
        xml = build_formatted_s_xml("n-BuLi")
        # face="2" is italic
        assert 'face="2"' in xml
        assert "n-</s>" in xml

    def test_xml_escape(self):
        # Ampersand in text should be escaped
        xml = build_formatted_s_xml("A&B")
        assert "&amp;" in xml
        assert "A&B" not in xml  # raw & should not appear

    def test_custom_font_params(self):
        xml = build_formatted_s_xml("CH3", font="5", size="12", color="2")
        assert 'font="5"' in xml
        assert 'size="12"' in xml
        assert 'color="2"' in xml

    def test_returns_string(self):
        result = build_formatted_s_xml("Et3N")
        assert isinstance(result, str)

    def test_empty_string(self):
        result = build_formatted_s_xml("")
        assert isinstance(result, str)


# =========================================================================
# Module-level constants sanity
# =========================================================================

class TestModuleConstants:
    def test_subscript_re_matches_formula_digits(self):
        m = SUBSCRIPT_RE.search("CH3OH")
        assert m is not None
        assert m.group(2) == "3"

    def test_italic_prefixes_is_list(self):
        assert isinstance(ITALIC_PREFIXES, list)
        assert len(ITALIC_PREFIXES) >= 10

    def test_italic_prefixes_all_end_with_dash(self):
        for prefix in ITALIC_PREFIXES:
            assert prefix.endswith("-"), f"prefix {prefix!r} missing trailing dash"
