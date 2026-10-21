"""Unit tests for scheme_maker.py — experimental CDXML builder from reaction JSON.

Tests the internal logic of scheme_maker without needing ChemDraw COM.
Requires RDKit for SMILES → 2D coordinate generation.
"""

import json
import os
import sys
import textwrap
import tempfile

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Skip all tests if RDKit is not available
try:
    from rdkit import Chem  # noqa: F401
    _HAS_RDKIT = True
except ImportError:
    _HAS_RDKIT = False

pytestmark = pytest.mark.skipif(not _HAS_RDKIT, reason="RDKit not available")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _minimal_json(tmp_path, species=None, conditions=None, eln_data=None,
                  version="1.1"):
    """Create a minimal reaction JSON for testing."""
    if species is None:
        species = [
            {
                "id": "sp_0",
                "smiles": "BrC1=CC=CC=C1",
                "name": "SM",
                "role": "atom_contributing",
                "is_sm": True,
                "is_dp": False,
                                "source": "fragment",
                "display_text": "SM",
            },
            {
                "id": "sp_1",
                "smiles": "C1CCNCC1",
                "name": "DP",
                "role": "product",
                "is_sm": False,
                "is_dp": True,
                                "source": "fragment",
                "display_text": "DP",
            },
        ]
    data = {
        "version": version,
        "experiment": "TEST-001",
        "input_files": {},
        "species": species,
        "warnings": [],
        "metadata": {"parser_version": "1.1"},
        "conditions": conditions or [],
        "eln_data": eln_data,
    }
    path = os.path.join(str(tmp_path), "test.json")
    with open(path, "w") as f:
        json.dump(data, f)
    return path


# ---------------------------------------------------------------------------
# Tests: build_scheme
# ---------------------------------------------------------------------------

class TestBuildScheme:
    """Tests for the main build_scheme() function."""

    def test_basic_build(self, tmp_path):
        """Simplest case: one reactant + one product."""
        from cdxml_toolkit.render.scheme_maker import build_scheme

        json_path = _minimal_json(tmp_path)
        out = os.path.join(str(tmp_path), "out.cdxml")
        result = build_scheme(json_path, output=out, align_mode="none")
        assert os.path.isfile(result)
        assert os.path.getsize(result) > 0

        # Parse and verify structure
        import xml.etree.ElementTree as ET
        tree = ET.parse(result)
        root = tree.getroot()
        assert root.tag == "CDXML"
        frags = tree.findall(".//fragment")
        assert len(frags) >= 2  # at least reactant + product

    def test_conditions_in_output(self, tmp_path):
        """Conditions should appear in the output CDXML."""
        from cdxml_toolkit.render.scheme_maker import build_scheme
        import xml.etree.ElementTree as ET

        json_path = _minimal_json(tmp_path, conditions=["80 °C", "24 h"])
        out = os.path.join(str(tmp_path), "out.cdxml")
        build_scheme(json_path, output=out, align_mode="none")

        tree = ET.parse(out)
        page = tree.find(".//page")
        assert page is not None
        # Find standalone <t> elements (conditions text)
        texts = [el for el in page if el.tag == "t"]
        # Should have at least one text block with conditions
        all_text = ""
        for t in texts:
            for s in t.findall("s"):
                all_text += (s.text or "")
        assert "80" in all_text or "24" in all_text

    def test_no_product_exits(self, tmp_path):
        """JSON without any product should exit with error."""
        from cdxml_toolkit.render.scheme_maker import build_scheme

        species = [
            {
                "id": "sp_0",
                "smiles": "BrC1=CC=CC=C1",
                "name": "SM",
                "role": "atom_contributing",
                                "source": "fragment",
            },
        ]
        json_path = _minimal_json(tmp_path, species=species)
        with pytest.raises(SystemExit):
            build_scheme(json_path, align_mode="none")

    def test_eln_data_run_arrow(self, tmp_path):
        """ELN data should produce a run arrow."""
        from cdxml_toolkit.render.scheme_maker import build_scheme
        import xml.etree.ElementTree as ET

        eln = {"sm_mass": "100 mg", "product_obtained": "80 mg",
               "product_yield": "80 %"}
        json_path = _minimal_json(tmp_path, eln_data=eln)
        out = os.path.join(str(tmp_path), "out.cdxml")
        build_scheme(json_path, output=out, align_mode="none",
                     run_arrow=True)

        tree = ET.parse(out)
        arrows = tree.findall(".//arrow")
        # Should have at least 2 arrows (reaction + run)
        assert len(arrows) >= 2

    def test_no_run_arrow(self, tmp_path):
        """run_arrow=False should skip run arrow even with ELN data."""
        from cdxml_toolkit.render.scheme_maker import build_scheme
        import xml.etree.ElementTree as ET

        eln = {"sm_mass": "100 mg", "product_obtained": "80 mg"}
        json_path = _minimal_json(tmp_path, eln_data=eln)
        out = os.path.join(str(tmp_path), "out.cdxml")
        build_scheme(json_path, output=out, align_mode="none",
                     run_arrow=False)

        tree = ET.parse(out)
        arrows = tree.findall(".//arrow")
        assert len(arrows) == 1  # only reaction arrow

    def test_default_output_path(self, tmp_path):
        """Without output path, should create {stem}-scheme.cdxml."""
        from cdxml_toolkit.render.scheme_maker import build_scheme

        json_path = _minimal_json(tmp_path)
        result = build_scheme(json_path, align_mode="none")
        expected = os.path.join(str(tmp_path), "test-scheme.cdxml")
        assert result == expected
        assert os.path.isfile(expected)

    def test_v10_json_compatibility(self, tmp_path):
        """v1.0 JSON (minimal fields) should still work."""
        from cdxml_toolkit.render.scheme_maker import build_scheme

        species = [
            {
                "id": "sp_0",
                "smiles": "BrC1=CC=CC=C1",
                "name": "SM",
                "role": "atom_contributing",
                "is_sm": True,
                "source": "fragment",
            },
            {
                "id": "sp_1",
                "smiles": "C1CCNCC1",
                "name": "DP",
                "role": "product",
                "is_dp": True,
                "source": "fragment",
            },
        ]
        json_path = _minimal_json(tmp_path, species=species, version="1.0")
        out = os.path.join(str(tmp_path), "out.cdxml")
        result = build_scheme(json_path, output=out, align_mode="none")
        assert os.path.isfile(result)


# ---------------------------------------------------------------------------
# Tests: species partitioning
# ---------------------------------------------------------------------------

class TestSpeciesPartitioning:
    """Tests for how species are partitioned into layout groups."""

    def test_non_contributing_goes_to_text(self, tmp_path):
        """Non-contributing species (base/catalyst) → text, not structure."""
        from cdxml_toolkit.render.scheme_maker import build_scheme
        import xml.etree.ElementTree as ET

        species = [
            {
                "id": "sp_0", "smiles": "BrC1=CC=CC=C1", "name": "SM",
                "role": "atom_contributing",                 "source": "fragment", "is_sm": True,
            },
            {
                "id": "sp_1", "smiles": "O=C([O-])[O-].[Cs+].[Cs+]",
                "name": "Cs2CO3", "role": "non_contributing",
                "source": "fragment",
                "display_text": "Cs2CO3 (2 eq.)",
            },
            {
                "id": "sp_2", "smiles": "C1CCNCC1", "name": "DP",
                "role": "product",                 "source": "fragment", "is_dp": True,
            },
        ]
        json_path = _minimal_json(tmp_path, species=species)
        out = os.path.join(str(tmp_path), "out.cdxml")
        build_scheme(json_path, output=out, align_mode="none")

        tree = ET.parse(out)
        page = tree.find(".//page")
        texts = [el for el in page if el.tag == "t"]
        all_text = ""
        for t in texts:
            for s in t.findall("s"):
                all_text += (s.text or "")
        # Cs2CO3 should appear as text, not as a drawn structure
        assert "Cs" in all_text or "2 eq" in all_text

    def test_atom_contributing_above_arrow_is_structure(self, tmp_path):
        """Atom-contributing species repositioned above arrow → drawn structure."""
        from cdxml_toolkit.render.scheme_maker import build_scheme
        import xml.etree.ElementTree as ET

        species = [
            {
                "id": "sp_0", "smiles": "BrC1=CC=CC=C1", "name": "SM",
                "role": "atom_contributing",                 "source": "fragment", "is_sm": True, "is_substrate": True,
            },
            {
                "id": "sp_1", "smiles": "C1CCNCC1",
                "name": "morpholine", "role": "atom_contributing",
                "source": "fragment",
            },
            {
                "id": "sp_2", "smiles": "C1=CC=C(N2CCCCC2)C=C1",
                "name": "DP", "role": "product",                 "source": "fragment", "is_dp": True,
            },
        ]
        json_path = _minimal_json(tmp_path, species=species)
        out = os.path.join(str(tmp_path), "out.cdxml")
        build_scheme(json_path, output=out, align_mode="none")

        tree = ET.parse(out)
        frags = tree.findall(".//fragment")
        # Should have 3 fragments: SM, morpholine above arrow, product
        assert len(frags) >= 3


# ---------------------------------------------------------------------------
# Tests: deduplication
# ---------------------------------------------------------------------------

class TestDeduplication:
    """Tests for above-arrow text deduplication."""

    def test_duplicate_text_removed(self, tmp_path):
        """Duplicate above-arrow text labels should be deduplicated."""
        from cdxml_toolkit.render.scheme_maker import build_scheme
        import xml.etree.ElementTree as ET

        species = [
            {
                "id": "sp_0", "smiles": "BrC1=CC=CC=C1", "name": "SM",
                "role": "atom_contributing",                 "source": "fragment", "is_sm": True,
            },
            {
                "id": "sp_1", "name": "THF",
                "role": "non_contributing",                 "source": "text_label", "is_solvent": True,
                "display_text": "THF",
            },
            {
                "id": "sp_2", "name": "THF",
                "role": "non_contributing",                 "source": "csv_only", "is_solvent": True,
                "display_text": "THF",
            },
            {
                "id": "sp_3", "smiles": "C1CCNCC1", "name": "DP",
                "role": "product",                 "source": "fragment", "is_dp": True,
            },
        ]
        json_path = _minimal_json(tmp_path, species=species)
        out = os.path.join(str(tmp_path), "out.cdxml")
        build_scheme(json_path, output=out, align_mode="none")

        tree = ET.parse(out)
        page = tree.find(".//page")
        texts = [el for el in page if el.tag == "t"]
        all_text = ""
        for t in texts:
            for s in t.findall("s"):
                all_text += (s.text or "")
        # THF should appear only once (not twice)
        count = all_text.count("THF")
        assert count == 1, f"THF appears {count} times, expected 1"


# ---------------------------------------------------------------------------
# Tests: text formatting
# ---------------------------------------------------------------------------

class TestTextFormatting:
    """Tests for _apply_text_formatting behavior."""

    def test_condition_tokens_not_subscripted(self, tmp_path):
        """Temperature and time should NOT get subscripted digits."""
        from cdxml_toolkit.render.scheme_maker import build_scheme
        import xml.etree.ElementTree as ET

        json_path = _minimal_json(tmp_path, conditions=["105 °C", "24 h"])
        out = os.path.join(str(tmp_path), "out.cdxml")
        build_scheme(json_path, output=out, align_mode="none")

        tree = ET.parse(out)
        page = tree.find(".//page")
        # Find all <s> elements in standalone <t> elements
        for t in page:
            if t.tag != "t":
                continue
            for s in t.findall("s"):
                text = s.text or ""
                face = s.get("face", "0")
                # If text contains "105" or "24", face should NOT have
                # subscript bit (face & 32 == 0 in ChemDraw's bitmask)
                if "105" in text or "24 h" in text:
                    face_int = int(face) if face.isdigit() else 0
                    assert face_int & 32 == 0, (
                        f"Condition text '{text}' has subscript face={face}"
                    )


# ---------------------------------------------------------------------------
# Tests: CLI argument parsing
# ---------------------------------------------------------------------------

class TestCLI:
    """Tests for CLI argument handling."""

    def test_json_errors_flag(self, tmp_path):
        """--json-errors should produce JSON on stderr for failures."""
        import subprocess
        r = subprocess.run(
            [sys.executable, "-m", "cdxml_toolkit.render.scheme_maker", "nonexistent.json",
             "--json-errors"],
            capture_output=True, text=True, cwd=PROJECT_ROOT, timeout=30,
        )
        assert r.returncode != 0
        err = json.loads(r.stderr.strip())
        assert "error" in err

    def test_verbose_flag(self, tmp_path):
        """--verbose should produce diagnostic output on stderr."""
        json_path = _minimal_json(tmp_path)
        out = os.path.join(str(tmp_path), "out.cdxml")
        import subprocess
        r = subprocess.run(
            [sys.executable, "-m", "cdxml_toolkit.render.scheme_maker", json_path,
             "-o", out, "--align-mode", "none", "-v"],
            capture_output=True, text=True, cwd=PROJECT_ROOT, timeout=60,
        )
        assert r.returncode == 0, f"stderr: {r.stderr}"
        assert "Loaded JSON" in r.stderr
        assert "Layout" in r.stderr or "layout" in r.stderr
