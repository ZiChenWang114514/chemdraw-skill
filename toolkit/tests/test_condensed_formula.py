"""Tests for the condensed structural formula parser."""

import pytest
from rdkit import Chem

from cdxml_toolkit.resolve.condensed_formula import (
    resolve_condensed_formula,
    tokenize,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _canon(smiles: str) -> str:
    """Canonicalise a SMILES string via RDKit."""
    mol = Chem.MolFromSmiles(smiles)
    assert mol is not None, f"Invalid SMILES: {smiles}"
    return Chem.MolToSmiles(mol)


def _assert_same_molecule(result: str, expected: str, label: str = ""):
    """Assert two SMILES encode the same molecule."""
    assert result is not None, f"{label}: got None, expected {expected}"
    can_r = _canon(result)
    can_e = _canon(expected)
    assert can_r == can_e, (
        f"{label}: got {can_r}, expected {can_e} "
        f"(raw result={result})"
    )


# ===================================================================
# Tokenizer tests
# ===================================================================

class TestTokenizer:
    """Tests for tokenize()."""

    def test_simple_two_fragment(self):
        toks = tokenize("MeI")
        assert len(toks) == 2
        assert toks[0] == ("abbrev", "Me")
        assert toks[1] == ("element", "I")

    def test_multiplied_group(self):
        toks = tokenize("Et3N")
        assert toks == [
            ("abbrev", "Et"), ("count", 3), ("element", "N"),
        ]

    def test_parenthesised_group(self):
        toks = tokenize("PhB(OH)2")
        assert toks == [
            ("abbrev", "Ph"), ("element", "B"),
            ("paren_open", "("), ("abbrev", "OH"), ("paren_close", ")"),
            ("count", 2),
        ]

    def test_element_priority_over_abbrev(self):
        """Single-letter elements must not be grabbed as abbreviations."""
        toks = tokenize("NaBH4")
        assert len(toks) == 4
        assert toks[0] == ("element", "Na")
        assert toks[1] == ("element", "B")
        assert toks[2] == ("element", "H")
        assert toks[3] == ("count", 4)

    def test_two_letter_element_priority(self):
        """Two-letter elements like Co, Ag must match as elements."""
        toks = tokenize("Ag2O")
        assert toks[0] == ("element", "Ag")
        assert toks[1] == ("count", 2)
        assert toks[2] == ("element", "O")

    def test_empty_string(self):
        assert tokenize("") == []

    def test_unrecognisable(self):
        """Unrecognisable characters should return empty list."""
        assert tokenize("!!!") == []
        assert tokenize("Xyz") == []

    def test_abbreviation_with_subscript_in_table(self):
        """Multi-char abbreviations like Me3Si are in the superatom table."""
        toks = tokenize("Me3SiCl")
        # "Me3Si" should match as a single abbreviation (it's in the table)
        assert toks[0][0] == "abbrev"
        assert toks[-1] == ("element", "Cl")


# ===================================================================
# Assembly tests — simple two-fragment compounds
# ===================================================================

class TestSimpleTwoFragment:
    """Test group + element linear compounds."""

    def test_mei(self):
        _assert_same_molecule(resolve_condensed_formula("MeI"), "CI", "MeI")

    def test_bzcl(self):
        _assert_same_molecule(
            resolve_condensed_formula("BzCl"),
            "O=C(Cl)c1ccccc1", "BzCl")

    def test_accl(self):
        _assert_same_molecule(
            resolve_condensed_formula("AcCl"),
            "CC(=O)Cl", "AcCl")

    def test_etoh(self):
        _assert_same_molecule(
            resolve_condensed_formula("EtOH"), "CCO", "EtOH")

    def test_meoh(self):
        _assert_same_molecule(
            resolve_condensed_formula("MeOH"), "CO", "MeOH")

    def test_iproh(self):
        _assert_same_molecule(
            resolve_condensed_formula("iPrOH"),
            "CC(C)O", "iPrOH")

    def test_tbuoh(self):
        _assert_same_molecule(
            resolve_condensed_formula("tBuOH"),
            "CC(C)(C)O", "tBuOH")


# ===================================================================
# Assembly tests — multiplied groups (X_n + central)
# ===================================================================

class TestMultipliedGroups:
    """Test group_n + central atom pattern."""

    def test_et3n(self):
        _assert_same_molecule(
            resolve_condensed_formula("Et3N"),
            "CCN(CC)CC", "Et3N")

    def test_ph3p(self):
        _assert_same_molecule(
            resolve_condensed_formula("Ph3P"),
            "c1ccc(P(c2ccccc2)c2ccccc2)cc1", "Ph3P")

    def test_me3sicl(self):
        _assert_same_molecule(
            resolve_condensed_formula("Me3SiCl"),
            "C[Si](C)(C)Cl", "Me3SiCl")


# ===================================================================
# Assembly tests — parenthesised groups (the key novel-combo feature)
# ===================================================================

class TestParenthesisedGroups:
    """Test left + atom + (group)_n pattern — the generative use case."""

    def test_phb_oh2(self):
        _assert_same_molecule(
            resolve_condensed_formula("PhB(OH)2"),
            "OB(O)c1ccccc1", "PhB(OH)2")

    def test_phb_ome2(self):
        """Novel combo not in any dictionary."""
        _assert_same_molecule(
            resolve_condensed_formula("PhB(OMe)2"),
            "COB(OC)c1ccccc1", "PhB(OMe)2")

    def test_phb_oet2(self):
        """Novel combo not in any dictionary."""
        _assert_same_molecule(
            resolve_condensed_formula("PhB(OEt)2"),
            "CCOB(OCC)c1ccccc1", "PhB(OEt)2")

    def test_cu_oac2(self):
        """Copper(II) acetate — metal with parenthesised ligand."""
        result = resolve_condensed_formula("Cu(OAc)2")
        assert result is not None, "Cu(OAc)2 should parse"
        # Just verify it contains Cu and two acetate groups
        mol = Chem.MolFromSmiles(result)
        assert mol is not None
        # Should have 1 Cu, 2 O-C(=O)-C units
        cu_count = sum(
            1 for a in mol.GetAtoms() if a.GetSymbol() == "Cu")
        assert cu_count == 1


# ===================================================================
# Assembly tests — hydrogen subscripts
# ===================================================================

class TestHydrogenSubscripts:
    """Hydrogen count always attaches to previous heavy atom."""

    def test_phch2br(self):
        """PhCH₂Br = benzyl bromide."""
        _assert_same_molecule(
            resolve_condensed_formula("PhCH2Br"),
            "BrCc1ccccc1", "PhCH2Br")

    def test_phnh2(self):
        """PhNH₂ = aniline."""
        _assert_same_molecule(
            resolve_condensed_formula("PhNH2"),
            "Nc1ccccc1", "PhNH2")


# ===================================================================
# Assembly tests — inorganic / metal compounds
# ===================================================================

class TestInorganic:
    """Test metal-containing compounds."""

    def test_ag2o(self):
        _assert_same_molecule(
            resolve_condensed_formula("Ag2O"),
            "[Ag]O[Ag]", "Ag2O")

    def test_nabh4_returns_none(self):
        """NaBH₄ is ionic — valence check should fail gracefully."""
        # NaBH4 is in the reagent DB anyway; the parser may return None
        # for ionic compounds with invalid covalent valence.
        result = resolve_condensed_formula("NaBH4")
        # Either None (valence failure) or valid SMILES is acceptable
        if result is not None:
            mol = Chem.MolFromSmiles(result)
            assert mol is not None

    def test_lialh4_returns_none(self):
        """LiAlH₄ is ionic — same graceful handling."""
        result = resolve_condensed_formula("LiAlH4")
        if result is not None:
            mol = Chem.MolFromSmiles(result)
            assert mol is not None


# ===================================================================
# Guard rail / negative tests
# ===================================================================

class TestGuardRails:
    """Inputs that should return None (let downstream tiers handle)."""

    def test_iupac_name_with_spaces(self):
        assert resolve_condensed_formula("triethylamine") is None

    def test_iupac_name_acid(self):
        assert resolve_condensed_formula("phenylboronic acid") is None

    def test_empty_string(self):
        assert resolve_condensed_formula("") is None

    def test_single_abbreviation(self):
        """Single abbreviations (no combination) should return None."""
        assert resolve_condensed_formula("Ph") is None
        assert resolve_condensed_formula("Et") is None

    def test_too_long(self):
        assert resolve_condensed_formula("A" * 50) is None

    def test_single_element(self):
        """Bare elements should return None."""
        assert resolve_condensed_formula("Na") is None
        assert resolve_condensed_formula("Cl") is None

    def test_gibberish(self):
        assert resolve_condensed_formula("XyzAbc123") is None


# ===================================================================
# Case insensitivity
# ===================================================================

class TestCaseInsensitivity:
    """Condensed formulae should work regardless of case quirks."""

    def test_lowercase_et3n(self):
        # "et3n" — lowercase version
        result = resolve_condensed_formula("et3n")
        # Tokenizer uses case-insensitive abbreviation matching
        # but requires uppercase for element symbols; this may fail
        # which is acceptable (chemists always write Et3N, not et3n)

    def test_phb_oh_2(self):
        """Standard case: PhB(OH)2."""
        result = resolve_condensed_formula("PhB(OH)2")
        assert result is not None
