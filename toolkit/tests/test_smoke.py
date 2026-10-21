"""Smoke tests — run each CLI tool with real test data, verify basic output.

Focus: structural correctness (exit code, output exists, valid XML/text).
Chemical correctness is validated separately by the chemist.

Tools requiring ChemDraw COM are skipped:
  scheme_polisher.py, cdx_converter.py, cdxml_to_image.py,
  eln_cdx_cleanup.py, ole_embedder.py, chemscript_bridge.py

Pipeline-specific tools (lcms_analyzer, multi_lcms_analyzer, procedure_writer,
etc.) are tested in the private chem-pipeline repo.
"""

import glob
import json
import os
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

import pytest

# Paths -------------------------------------------------------------------
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PYTHON = sys.executable  # use the same interpreter running pytest
TEST_DATA = os.environ.get(
    "CHEM_TEST_DATA",
    os.path.join(os.path.dirname(PROJECT_ROOT), "chem-test-data"),
)


def _run(args, **kwargs):
    """Run a subprocess, return CompletedProcess."""
    return subprocess.run(
        args,
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
        timeout=120,
        **kwargs,
    )


def _assert_valid_cdxml(path):
    """Assert file exists, is non-empty, and parses as valid XML with a CDXML root."""
    assert os.path.isfile(path), f"output file missing: {path}"
    assert os.path.getsize(path) > 0, f"output file is empty: {path}"
    tree = ET.parse(path)
    root = tree.getroot()
    assert root.tag == "CDXML", f"unexpected root tag: {root.tag}"


# =========================================================================
# reaction_cleanup.py — pure-Python reaction layout
# =========================================================================

class TestReactionCleanup:
    """Smoke tests for reaction_cleanup.py."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        self.tmp = tmp_path
        # Use a CDXML that has a reaction scheme
        candidates = glob.glob(os.path.join(TEST_DATA, "*.cdxml"))
        if not candidates:
            pytest.skip("No .cdxml files found in test_data/")
        self.cdxml = candidates[0]

    def test_default_approach_runs(self):
        out = os.path.join(self.tmp, "cleaned.cdxml")
        r = _run([PYTHON, "-m", "cdxml_toolkit.layout.reaction_cleanup", self.cdxml, "--output", out])
        assert r.returncode == 0, f"stderr: {r.stderr}"
        _assert_valid_cdxml(out)

    def test_all_approaches_run(self):
        # Copy input into tmp_path so --all output stays in tmp_path
        import shutil
        tmp_cdxml = os.path.join(self.tmp, "input.cdxml")
        shutil.copy2(self.cdxml, tmp_cdxml)
        r = _run([PYTHON, "-m", "cdxml_toolkit.layout.reaction_cleanup", tmp_cdxml, "--all"])
        assert r.returncode == 0, f"stderr: {r.stderr}"
        # --all produces one file per approach next to the input
        outputs = glob.glob(os.path.join(self.tmp, "*cleanup*.cdxml"))
        assert len(outputs) >= 1

    def test_json_output(self):
        r = _run([PYTHON, "-m", "cdxml_toolkit.layout.reaction_cleanup", self.cdxml, "--json"])
        assert r.returncode == 0, f"stderr: {r.stderr}"
        data = json.loads(r.stdout)
        assert isinstance(data, dict)


# =========================================================================
# coord_normalizer.py — coordinate normalization
# =========================================================================

class TestCoordNormalizer:
    """Smoke tests for coord_normalizer.py."""

    def test_normalizes_json_input(self, tmp_path):
        # Create a minimal molecule JSON (two-atom ethane fragment)
        mol = {
            "atoms": [
                {"index": 0, "symbol": "C", "x": 0.0, "y": 0.0},
                {"index": 1, "symbol": "C", "x": 1.54, "y": 0.0},
            ],
            "bonds": [
                {"index": 0, "order": 1, "atom1": 0, "atom2": 1},
            ],
        }
        inp = os.path.join(tmp_path, "mol_in.json")
        out = os.path.join(tmp_path, "mol_out.json")
        with open(inp, "w") as f:
            json.dump(mol, f)

        r = _run([PYTHON, "-m", "cdxml_toolkit.coord_normalizer", inp, "--output", out])
        assert r.returncode == 0, f"stderr: {r.stderr}"
        assert os.path.isfile(out)

        with open(out) as f:
            result = json.load(f)
        assert "atoms" in result
        assert len(result["atoms"]) == 2


# =========================================================================
# rdf_parser.py — SciFinder RDF parsing
# =========================================================================

class TestRdfParser:
    """Smoke tests for rdf_parser.py."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.rdf = os.path.join(TEST_DATA, "Reaction_20260217_1738.rdf")
        if not os.path.isfile(self.rdf):
            pytest.skip("RDF test file not found")

    def test_parses_rdf_to_json(self, tmp_path):
        out = os.path.join(tmp_path, "parsed.json")
        r = _run([PYTHON, "-m", "cdxml_toolkit.perception.rdf_parser", self.rdf, "--output", out, "--pretty"])
        assert r.returncode == 0, f"stderr: {r.stderr}"
        assert os.path.isfile(out)

        with open(out) as f:
            data = json.load(f)
        # RDF parser outputs a reaction dict with reactants/products
        assert "reactants" in data or "reactions" in data

    def test_stdout_output(self):
        r = _run([PYTHON, "-m", "cdxml_toolkit.perception.rdf_parser", self.rdf])
        assert r.returncode == 0, f"stderr: {r.stderr}"
        data = json.loads(r.stdout)
        assert "reactants" in data or "reactions" in data


# =========================================================================
# cdxml_builder.py — CDXML from JSON
# =========================================================================

class TestCdxmlBuilder:
    """Smoke tests for cdxml_builder.py."""

    def test_builds_molecule_from_json(self, tmp_path):
        # Minimal benzene-like input (just two atoms + bond for smoke test)
        mol = {
            "atoms": [
                {"index": 0, "symbol": "C", "x": 200.0, "y": 300.0},
                {"index": 1, "symbol": "C", "x": 214.4, "y": 300.0},
            ],
            "bonds": [
                {"index": 0, "order": 1, "atom1": 0, "atom2": 1},
            ],
        }
        inp = os.path.join(tmp_path, "mol.json")
        out = os.path.join(tmp_path, "mol.cdxml")
        with open(inp, "w") as f:
            json.dump(mol, f)

        r = _run([
            PYTHON, "-m", "cdxml_toolkit.cdxml_builder",
            "--input", inp,
            "--output", out,
            "--mode", "molecule",
        ])
        assert r.returncode == 0, f"stderr: {r.stderr}"
        _assert_valid_cdxml(out)

    def test_builds_reaction_from_json(self, tmp_path):
        rxn = {
            "reactants": [
                {
                    "atoms": [
                        {"index": 0, "symbol": "C", "x": 100.0, "y": 300.0},
                        {"index": 1, "symbol": "C", "x": 114.4, "y": 300.0},
                    ],
                    "bonds": [
                        {"index": 0, "order": 1, "atom1": 0, "atom2": 1},
                    ],
                }
            ],
            "products": [
                {
                    "atoms": [
                        {"index": 0, "symbol": "C", "x": 300.0, "y": 300.0},
                        {"index": 1, "symbol": "O", "x": 314.4, "y": 300.0},
                    ],
                    "bonds": [
                        {"index": 0, "order": 1, "atom1": 0, "atom2": 1},
                    ],
                }
            ],
            "conditions": {
                "above": ["Pd(OAc)2"],
                "below": ["DMF, 80 °C"],
            },
        }
        inp = os.path.join(tmp_path, "rxn.json")
        out = os.path.join(tmp_path, "rxn.cdxml")
        with open(inp, "w") as f:
            json.dump(rxn, f)

        r = _run([
            PYTHON, "-m", "cdxml_toolkit.cdxml_builder",
            "--input", inp,
            "--output", out,
            "--mode", "reaction",
        ])
        assert r.returncode == 0, f"stderr: {r.stderr}"
        _assert_valid_cdxml(out)

        # Verify reaction elements exist in the CDXML
        tree = ET.parse(out)
        root = tree.getroot()
        arrows = root.findall(".//arrow")
        assert len(arrows) >= 1, "reaction CDXML should contain an arrow"


# =========================================================================
# reagent_db.py — import and basic load test
# =========================================================================

class TestReagentDbSmoke:
    """Smoke test: reagent_db loads without error."""

    def test_import_and_load(self):
        from cdxml_toolkit.resolve.reagent_db import get_reagent_db

        db = get_reagent_db()
        assert db is not None
        # Verify it has data
        result = db.display_for_name("cs2co3")
        assert result is not None
