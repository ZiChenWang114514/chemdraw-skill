"""Unit tests for superatom_table.py — abbreviation label → SMILES lookup."""

import xml.etree.ElementTree as ET

import pytest

try:
    from rdkit import Chem
    from rdkit.Chem import Descriptors
    HAS_RDKIT = True
except ImportError:
    HAS_RDKIT = False

needs_rdkit = pytest.mark.skipif(not HAS_RDKIT, reason="RDKit not installed")


# =========================================================================
# Table building and lookup
# =========================================================================

class TestGetSuperatomTable:
    def test_returns_dict(self):
        from cdxml_toolkit.resolve.superatom_table import get_superatom_table
        table = get_superatom_table()
        assert isinstance(table, dict)

    def test_has_common_entries(self):
        from cdxml_toolkit.resolve.superatom_table import get_superatom_table
        table = get_superatom_table()
        # Spot-check common abbreviations
        assert "boc" in table
        assert "tbu" in table
        assert "ome" in table
        assert "ph" in table
        assert "tms" in table
        assert "ac" in table
        assert "bn" in table
        assert "cbz" in table

    def test_case_insensitive(self):
        from cdxml_toolkit.resolve.superatom_table import lookup_smiles
        # Same result regardless of case
        assert lookup_smiles("Boc") == lookup_smiles("boc") == lookup_smiles("BOC")
        assert lookup_smiles("TMS") == lookup_smiles("tms")
        assert lookup_smiles("OMe") == lookup_smiles("ome")

    def test_left_and_right_forms_indexed(self):
        from cdxml_toolkit.resolve.superatom_table import lookup_smiles
        # CO2Et (left) and EtO2C (right) should both resolve
        smi_left = lookup_smiles("CO2Et")
        smi_right = lookup_smiles("EtO2C")
        assert smi_left is not None
        assert smi_right is not None
        assert smi_left == smi_right

    def test_unknown_returns_none(self):
        from cdxml_toolkit.resolve.superatom_table import lookup_smiles
        assert lookup_smiles("NotARealGroup") is None
        assert lookup_smiles("") is None

    def test_singleton_behavior(self):
        from cdxml_toolkit.resolve.superatom_table import get_superatom_table
        t1 = get_superatom_table()
        t2 = get_superatom_table()
        assert t1 is t2

    def test_minimum_size(self):
        """Table should have at least 2000 entries (ChemScanner JSON)."""
        from cdxml_toolkit.resolve.superatom_table import get_superatom_table
        table = get_superatom_table()
        assert len(table) >= 2000

    def test_chemscanner_exclusive_entry(self):
        """An abbreviation only in ChemScanner superatom.txt should resolve."""
        from cdxml_toolkit.resolve.superatom_table import lookup_smiles
        # DMF is in ChemScanner superatom.txt but was not in old OpenBabel list
        assert lookup_smiles("DMF") is not None
        # py (pyridine) is at the end of ChemScanner superatom.txt
        assert lookup_smiles("py") is not None


# =========================================================================
# MW lookup
# =========================================================================

@needs_rdkit
class TestLookupMw:
    def test_tbu_mw(self):
        from cdxml_toolkit.resolve.superatom_table import lookup_mw
        mw = lookup_mw("tBu")
        assert mw is not None
        # tBu standalone = C(C)(C)C = isobutane = C4H10 = 58.12
        assert abs(mw - 58.12) < 0.1

    def test_boc_mw(self):
        from cdxml_toolkit.resolve.superatom_table import lookup_mw
        mw = lookup_mw("Boc")
        assert mw is not None
        # Boc = C(=O)OC(C)(C)C = C5H10O2 standalone = 102.13
        assert abs(mw - 102.13) < 0.1

    def test_ots_mw(self):
        from cdxml_toolkit.resolve.superatom_table import lookup_mw
        mw = lookup_mw("OTs")
        assert mw is not None
        # OTs = OS(=O)(=O)c1ccc(C)cc1 = C7H8O3S = 172.20
        assert abs(mw - 172.20) < 0.2

    def test_ph_mw(self):
        from cdxml_toolkit.resolve.superatom_table import lookup_mw
        mw = lookup_mw("Ph")
        assert mw is not None
        # Ph standalone = c1ccccc1 = benzene = C6H6 = 78.11
        assert abs(mw - 78.11) < 0.1

    def test_unknown_returns_none(self):
        from cdxml_toolkit.resolve.superatom_table import lookup_mw
        assert lookup_mw("NotARealGroup") is None

    def test_me_mw(self):
        from cdxml_toolkit.resolve.superatom_table import lookup_mw
        mw = lookup_mw("Me")
        assert mw is not None
        # Me standalone = C = CH4 = 16.04
        assert abs(mw - 16.04) < 0.1

    def test_cf3_mw(self):
        from cdxml_toolkit.resolve.superatom_table import lookup_mw
        mw = lookup_mw("CF3")
        assert mw is not None
        # CF3 standalone = C(F)(F)F = CHF3 = 70.01
        assert abs(mw - 70.01) < 0.1


# =========================================================================
# Label extraction from CDXML nodes
# =========================================================================

class TestGetAbbrevLabel:
    def test_simple_label(self):
        from cdxml_toolkit.resolve.superatom_table import get_abbrev_label
        xml = '<n NodeType="Fragment"><t><s>OTs</s></t></n>'
        node = ET.fromstring(xml)
        assert get_abbrev_label(node) == "OTs"

    def test_multi_s_label(self):
        """Labels can have multiple <s> elements (different formatting)."""
        from cdxml_toolkit.resolve.superatom_table import get_abbrev_label
        xml = '<n NodeType="Fragment"><t><s>CO</s><s>2</s><s>Et</s></t></n>'
        node = ET.fromstring(xml)
        assert get_abbrev_label(node) == "CO2Et"

    def test_no_label_returns_none(self):
        from cdxml_toolkit.resolve.superatom_table import get_abbrev_label
        xml = '<n NodeType="Fragment"></n>'
        node = ET.fromstring(xml)
        assert get_abbrev_label(node) is None

    def test_ignores_inner_fragment_text(self):
        """Should read <t> on the <n>, not inside the inner <fragment>."""
        from cdxml_toolkit.resolve.superatom_table import get_abbrev_label
        xml = """\
        <n NodeType="Fragment">
          <fragment>
            <n><t><s>O</s></t></n>
          </fragment>
          <t><s>OTs</s></t>
        </n>"""
        node = ET.fromstring(xml)
        assert get_abbrev_label(node) == "OTs"


# =========================================================================
# SMILES validity
# =========================================================================

@needs_rdkit
class TestSmilesValidity:
    def test_all_smiles_parseable(self):
        """Every SMILES in the table should be parseable by RDKit."""
        from cdxml_toolkit.resolve.superatom_table import get_superatom_table
        table = get_superatom_table()
        failures = []
        seen_smiles = set()
        for label, smiles in table.items():
            if smiles in seen_smiles:
                continue
            seen_smiles.add(smiles)
            mol = Chem.MolFromSmiles(smiles)
            if mol is None:
                # Try as SMARTS (RDKit abbreviations use SMARTS notation)
                mol = Chem.MolFromSmarts(smiles)
            if mol is None:
                failures.append((label, smiles))
        assert not failures, f"Unparseable SMILES: {failures}"
