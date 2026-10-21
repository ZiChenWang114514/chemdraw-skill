"""Unit tests for reaction_parser.py — the unified reaction semantic layer."""

import json
import os
import tempfile

import pytest

# ---------------------------------------------------------------------------
# Import the module under test
# ---------------------------------------------------------------------------
from cdxml_toolkit.perception.reaction_parser import (
    SpeciesDescriptor,
    ReactionDescriptor,
    reaction_summary,
    split_condition_text,
    _is_condition_token,
    _resolve_text_label,
    _build_reaction_smiles,
    _deduplicate_species,
)

# Check RDKit availability
try:
    from rdkit import Chem
    HAS_RDKIT = True
except ImportError:
    HAS_RDKIT = False


# ===================================================================
# SpeciesDescriptor tests
# ===================================================================

class TestSpeciesDescriptor:
    """Tests for the SpeciesDescriptor dataclass."""

    def test_to_dict_roundtrip(self):
        sp = SpeciesDescriptor(
            id="sp_0", smiles="CCO", name="ethanol",
            role="non_contributing", role_detail="solvent",
            is_sm=False, is_dp=False,
            exact_mass=46.0, exact_mass_full=46.0, mw=46.07,
            source="text_label",
        )
        d = sp.to_dict()
        assert d["id"] == "sp_0"
        assert d["smiles"] == "CCO"
        assert d["name"] == "ethanol"
        assert d["role"] == "non_contributing"
        # None values should be filtered out
        assert "rxn_insight_role" not in d
        assert "source_id" not in d

    def test_defaults(self):
        sp = SpeciesDescriptor()
        assert sp.id == ""
        assert sp.smiles is None
        assert sp.is_sm is False
        assert sp.is_dp is False
        assert sp.exact_mass == 0.0
        assert sp.adducts == {}

    def test_salt_dual_smiles(self):
        sp = SpeciesDescriptor(
            smiles="[Na+].[Cl-]",
            smiles_neutral="[Na+]",
        )
        assert "." in sp.smiles
        assert "." not in sp.smiles_neutral

    def test_adducts_dict(self):
        sp = SpeciesDescriptor(
            adducts={"[M+H]+": 100.0, "[M-H]-": 98.0}
        )
        assert sp.adducts["[M+H]+"] == 100.0
        assert len(sp.adducts) == 2


# ===================================================================
# ReactionDescriptor tests
# ===================================================================

class TestReactionDescriptor:
    """Tests for the ReactionDescriptor dataclass."""

    def test_empty_descriptor(self):
        rd = ReactionDescriptor()
        assert rd.version == "1.3"
        assert rd.species == []
        assert rd.warnings == []
        assert rd.conditions == []
        assert rd.eln_data is None
    def test_to_dict_structure(self):
        rd = ReactionDescriptor(experiment="KL-7001-004")
        d = rd.to_dict()
        assert d["version"] == "1.3"
        assert d["experiment"] == "KL-7001-004"
        assert isinstance(d["species"], list)

    def test_to_json_from_json_roundtrip(self):
        sp = SpeciesDescriptor(
            id="sp_0", smiles="CCO", name="ethanol",
            role="non_contributing", is_sm=False, is_dp=False,
            exact_mass=46.0, exact_mass_full=46.0, mw=46.07,
        )
        rd = ReactionDescriptor(
            experiment="test",
            species=[sp],
            warnings=["test warning"],
        )
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False,
                                         mode="w") as f:
            path = f.name
        try:
            rd.to_json(path)
            rd2 = ReactionDescriptor.from_json(path)
            assert rd2.experiment == "test"
            assert len(rd2.species) == 1
            assert rd2.species[0].smiles == "CCO"
            assert rd2.species[0].name == "ethanol"
            assert rd2.warnings == ["test warning"]
        finally:
            os.unlink(path)

    def test_from_dict(self):
        d = {
            "version": "1.0",
            "experiment": "test",
            "species": [
                {"id": "sp_0", "smiles": "C", "name": "methane",
                 "is_sm": True, "is_dp": False, "role": "atom_contributing"}
            ],
        }
        rd = ReactionDescriptor.from_dict(d)
        assert rd.species[0].is_sm is True
        assert rd.species[0].name == "methane"

    def test_get_sm(self):
        rd = ReactionDescriptor(species=[
            SpeciesDescriptor(id="sp_0", name="SM", is_sm=True),
            SpeciesDescriptor(id="sp_1", name="DP", is_dp=True),
            SpeciesDescriptor(id="sp_2", name="reagent"),
        ])
        sm = rd.get_sm()
        assert sm is not None
        assert sm.name == "SM"

    def test_get_dp(self):
        rd = ReactionDescriptor(species=[
            SpeciesDescriptor(id="sp_0", name="SM", is_sm=True),
            SpeciesDescriptor(id="sp_1", name="DP", is_dp=True),
        ])
        dp = rd.get_dp()
        assert dp is not None
        assert dp.name == "DP"

    def test_get_sm_none(self):
        rd = ReactionDescriptor(species=[
            SpeciesDescriptor(id="sp_0", name="DP", is_dp=True),
        ])
        assert rd.get_sm() is None

    def test_get_expected_species(self):
        rd = ReactionDescriptor(species=[
            SpeciesDescriptor(
                id="sp_0", smiles="CCO", name="SM",
                exact_mass=46.0, adducts={"[M+H]+": 47.0},
                is_sm=True, role="atom_contributing",
            ),
            SpeciesDescriptor(
                id="sp_1", name="unknown",
                exact_mass=0.0,
            ),
        ])
        expected = rd.get_expected_species()
        assert len(expected) == 1
        assert expected[0]["name"] == "SM"
        assert expected[0]["role"] == "substrate"

    def test_version_field(self):
        rd = ReactionDescriptor()
        assert rd.version == "1.3"

    def test_csv_volume_supplier_fields(self):
        sp = SpeciesDescriptor(
            id="sp_0", csv_volume="1.5 mL", csv_supplier="Sigma-Aldrich",
        )
        d = sp.to_dict()
        assert d["csv_volume"] == "1.5 mL"
        assert d["csv_supplier"] == "Sigma-Aldrich"


# ===================================================================
# split_condition_text tests
# ===================================================================

class TestSplitConditionText:
    """Tests for the condition text splitting function."""

    def test_single_reagent(self):
        tokens = split_condition_text("Cs2CO3")
        assert tokens == ["Cs2CO3"]

    def test_newline_separated(self):
        tokens = split_condition_text("DEAD\nPPh3")
        assert "DEAD" in tokens
        assert "PPh3" in tokens
        assert len(tokens) == 2

    def test_comma_separated(self):
        tokens = split_condition_text("THF, DMF")
        assert "THF" in tokens
        assert "DMF" in tokens

    def test_filter_temperature(self):
        tokens = split_condition_text("80 C")
        assert tokens == []

    def test_filter_rt(self):
        tokens = split_condition_text("rt")
        assert tokens == []

    def test_filter_time(self):
        tokens = split_condition_text("16 h")
        assert tokens == []

    def test_filter_overnight(self):
        tokens = split_condition_text("overnight")
        assert tokens == []

    def test_mixed_reagents_and_conditions(self):
        tokens = split_condition_text("DEAD\nPPh3\nTHF, rt, 16 h")
        assert "DEAD" in tokens
        assert "PPh3" in tokens
        assert "THF" in tokens
        assert "rt" not in tokens
        assert "16 h" not in tokens
        assert len(tokens) == 3

    def test_multiline_merged_block(self):
        tokens = split_condition_text(
            "Cs2CO3\nBINAP\nPd2dba3\ndioxane, 105 C, 24 h"
        )
        assert "Cs2CO3" in tokens
        assert "BINAP" in tokens
        assert "Pd2dba3" in tokens
        # dioxane is known in reagent_db
        assert any("dioxane" in t.lower() for t in tokens)
        # conditions should be filtered
        assert not any("105" in t for t in tokens)
        assert not any("24 h" in t for t in tokens)

    def test_empty_string(self):
        assert split_condition_text("") == []

    def test_strip_equiv_annotation(self):
        tokens = split_condition_text("Cs2CO3 (2 eq.)")
        assert tokens == ["Cs2CO3"]

    def test_preserves_known_names_with_commas(self):
        """1,4-dioxane should not be split on the comma."""
        tokens = split_condition_text("1,4-dioxane")
        # Should be recognized as a single reagent (in reagent_db)
        assert len(tokens) == 1

    def test_mol_percent_filtered(self):
        tokens = split_condition_text("5 mol%")
        assert tokens == []

    def test_reflux_filtered(self):
        tokens = split_condition_text("reflux")
        assert tokens == []


# ===================================================================
# _is_condition_token tests
# ===================================================================

class TestIsConditionToken:
    """Tests for condition token detection."""

    def test_temperature_celsius(self):
        assert _is_condition_token("80 C") is True
        assert _is_condition_token("105 C") is True

    def test_rt(self):
        assert _is_condition_token("rt") is True
        assert _is_condition_token("r.t.") is True

    def test_time(self):
        assert _is_condition_token("16 h") is True
        assert _is_condition_token("30 min") is True
        assert _is_condition_token("2 d") is True

    def test_overnight(self):
        assert _is_condition_token("overnight") is True

    def test_reflux(self):
        assert _is_condition_token("reflux") is True

    def test_mol_percent(self):
        assert _is_condition_token("5 mol%") is True

    def test_reagent_not_condition(self):
        assert _is_condition_token("DEAD") is False
        assert _is_condition_token("PPh3") is False
        assert _is_condition_token("THF") is False
        assert _is_condition_token("Cs2CO3") is False

    def test_pressure(self):
        assert _is_condition_token("1 bar") is True

    def test_atmosphere(self):
        assert _is_condition_token("N2") is True
        assert _is_condition_token("Ar") is True


# ===================================================================
# Text label resolution tests
# ===================================================================

class TestTextLabelResolution:
    """Tests for text label → SMILES resolution."""

    def test_known_reagent_db_name(self):
        """reagent_db should resolve Cs2CO3 to SMILES."""
        smi = _resolve_text_label("Cs2CO3", use_network=False)
        assert smi is not None
        assert "Cs" in smi or "[Cs" in smi

    def test_known_reagent_thf(self):
        smi = _resolve_text_label("THF", use_network=False)
        assert smi is not None

    def test_unknown_returns_none(self):
        smi = _resolve_text_label("xyzzy_unknown_compound_12345",
                                  use_network=False)
        assert smi is None

    def test_strip_equiv_annotation(self):
        smi = _resolve_text_label("Et3N (2 eq.)", use_network=False)
        assert smi is not None
        assert "N" in smi  # triethylamine has N

    def test_case_insensitive(self):
        smi1 = _resolve_text_label("cs2co3", use_network=False)
        smi2 = _resolve_text_label("Cs2CO3", use_network=False)
        # Both should resolve (reagent_db is case-insensitive)
        assert smi1 is not None
        assert smi2 is not None


# ===================================================================
# Display name precedence tests
# ===================================================================

class TestDisplayNamePrecedence:
    """Tests for display name precedence rules."""

    def test_sm_uses_normal_name_resolution(self):
        """SM species follow normal name precedence (reagent DB > CSV > formula).
        The is_sm flag is preserved for downstream tools but doesn't override name."""
        from cdxml_toolkit.perception.reaction_parser import _apply_display_names
        species = [
            SpeciesDescriptor(id="sp_0", smiles="CCO", name="ethanol",
                              is_sm=True, csv_name="Ethanol"),
        ]
        _apply_display_names(species)
        # EtOH is in reagent_db — uses reagent DB display name
        assert species[0].name == "EtOH"
        assert species[0].is_sm is True  # flag preserved

    def test_dp_uses_normal_name_resolution(self):
        """DP species follow normal name precedence (reagent DB > CSV > formula).
        The is_dp flag is preserved for downstream tools but doesn't override name."""
        from cdxml_toolkit.perception.reaction_parser import _apply_display_names
        species = [
            SpeciesDescriptor(id="sp_0", smiles="CCO", name="product",
                              is_dp=True, csv_name="Product-1"),
        ]
        _apply_display_names(species)
        # EtOH is in reagent_db — uses reagent DB display name
        assert species[0].name == "EtOH"
        assert species[0].is_dp is True  # flag preserved

    def test_reagent_db_display(self):
        from cdxml_toolkit.perception.reaction_parser import _apply_display_names
        species = [
            SpeciesDescriptor(id="sp_0", smiles="CCN(CC)CC", name="",
                              is_sm=False, is_dp=False),
        ]
        _apply_display_names(species)
        # Et3N is in reagent_db with display "Et3N"
        assert species[0].name == "Et3N"

    def test_csv_name_fallback(self):
        from cdxml_toolkit.perception.reaction_parser import _apply_display_names
        species = [
            SpeciesDescriptor(
                id="sp_0", smiles=None, name="",
                is_sm=False, is_dp=False,
                csv_name="weird reagent from supplier"),
        ]
        _apply_display_names(species)
        assert species[0].name == "weird reagent from supplier"

    def test_formula_fallback(self):
        from cdxml_toolkit.perception.reaction_parser import _apply_display_names
        species = [
            SpeciesDescriptor(
                id="sp_0", smiles=None, name="",
                is_sm=False, is_dp=False,
                formula="C6H5Br"),
        ]
        _apply_display_names(species)
        assert species[0].name == "C6H5Br"

    def test_smiles_last_resort(self):
        from cdxml_toolkit.perception.reaction_parser import _apply_display_names
        species = [
            SpeciesDescriptor(
                id="sp_0", smiles="c1ccccc1",
                name="",
                is_sm=False, is_dp=False),
        ]
        _apply_display_names(species)
        # Should get either a reagent_db name or SMILES
        assert species[0].name != ""


# ===================================================================
# SM/DP identification tests
# ===================================================================

class TestSmDpIdentification:
    """Tests for SM/DP identification logic."""

    def test_csv_substrate_flag(self):
        from cdxml_toolkit.perception.reaction_parser import _identify_sm_dp
        species = [
            SpeciesDescriptor(id="sp_0", mw=200.0, role="atom_contributing",
                              is_sm=True),  # CSV substrate
            SpeciesDescriptor(id="sp_1", mw=300.0, role="atom_contributing"),
            SpeciesDescriptor(id="sp_2", mw=400.0, role="product"),
        ]
        _identify_sm_dp(species)
        assert species[0].is_sm is True
        assert species[2].is_dp is True

    def test_largest_reactant_fallback(self):
        from cdxml_toolkit.perception.reaction_parser import _identify_sm_dp
        species = [
            SpeciesDescriptor(id="sp_0", mw=100.0, role="atom_contributing"),
            SpeciesDescriptor(id="sp_1", mw=300.0, role="atom_contributing"),
            SpeciesDescriptor(id="sp_2", mw=400.0, role="product"),
        ]
        _identify_sm_dp(species)
        # sp_1 has larger MW → should be SM
        assert species[1].is_sm is True
        assert species[2].is_dp is True

    def test_single_product_is_dp(self):
        from cdxml_toolkit.perception.reaction_parser import _identify_sm_dp
        species = [
            SpeciesDescriptor(id="sp_0", mw=200.0, role="product"),
        ]
        _identify_sm_dp(species)
        assert species[0].is_dp is True


# ===================================================================
# Deduplication tests
# ===================================================================

class TestDeduplication:
    """Tests for species deduplication."""

    def test_no_duplicates(self):
        species = [
            SpeciesDescriptor(id="sp_0", smiles="CCO"),
            SpeciesDescriptor(id="sp_1", smiles="C"),
        ]
        result = _deduplicate_species(species)
        assert len(result) == 2

    def test_duplicate_merged(self):
        species = [
            SpeciesDescriptor(id="sp_0", smiles="CCO", name="ethanol",
                              source="fragment"),
            SpeciesDescriptor(id="sp_1", smiles="CCO", csv_name="EtOH",
                              source="text_label"),
        ]
        result = _deduplicate_species(species)
        assert len(result) == 1
        assert result[0].csv_name == "EtOH"  # merged from duplicate

    def test_none_smiles_not_deduped(self):
        species = [
            SpeciesDescriptor(id="sp_0", smiles=None, name="unknown1"),
            SpeciesDescriptor(id="sp_1", smiles=None, name="unknown2"),
        ]
        result = _deduplicate_species(species)
        assert len(result) == 2


# ===================================================================
# Build reaction SMILES tests
# ===================================================================

class TestBuildReactionSmiles:
    """Tests for reaction SMILES assembly."""

    def test_simple_reaction(self):
        species = [
            SpeciesDescriptor(smiles="BrC1=CC=CC=C1", role="atom_contributing"),
            SpeciesDescriptor(smiles="C1CCNCC1", role="atom_contributing"),
            SpeciesDescriptor(smiles="c1ccc(N2CCCCC2)cc1", role="product"),
        ]
        rxn = _build_reaction_smiles(species)
        assert ">>" in rxn
        assert "BrC1=CC=CC=C1" in rxn.split(">>")[0]
        assert "C1CCNCC1" in rxn.split(">>")[0]

    def test_no_product_returns_none(self):
        species = [
            SpeciesDescriptor(smiles="CCO", role="atom_contributing"),
        ]
        assert _build_reaction_smiles(species) is None

    def test_no_reactant_returns_none(self):
        species = [
            SpeciesDescriptor(smiles="CCO", role="product"),
        ]
        assert _build_reaction_smiles(species) is None

    def test_includes_non_contributing(self):
        """Non-contributing reagents should be on the LHS too."""
        species = [
            SpeciesDescriptor(smiles="CCO", role="atom_contributing"),
            SpeciesDescriptor(smiles="CCN(CC)CC", role="non_contributing"),
            SpeciesDescriptor(smiles="C", role="product"),
        ]
        rxn = _build_reaction_smiles(species)
        lhs = rxn.split(">>")[0]
        assert "CCN(CC)CC" in lhs


# ===================================================================
# Mass computation tests
# ===================================================================

@pytest.mark.skipif(not HAS_RDKIT, reason="RDKit required")
class TestMassComputation:
    """Tests for mass computation."""

    def test_simple_molecule(self):
        from cdxml_toolkit.perception.reaction_parser import _compute_all_masses
        species = [
            SpeciesDescriptor(id="sp_0", smiles="C1COCCN1"),  # morpholine
        ]
        _compute_all_masses(species)
        sp = species[0]
        assert sp.exact_mass > 85 and sp.exact_mass < 89
        assert sp.mw > 85 and sp.mw < 89
        assert sp.formula == "C4H9NO"
        assert sp.smiles_neutral == sp.smiles  # no salt
        assert "[M+H]+" in sp.adducts

    def test_salt_splitting(self):
        from cdxml_toolkit.perception.reaction_parser import _compute_all_masses
        species = [
            SpeciesDescriptor(id="sp_0",
                              smiles="O=C([O-])[O-].[Cs+].[Cs+]"),  # Cs2CO3
        ]
        _compute_all_masses(species)
        sp = species[0]
        assert sp.smiles_neutral != sp.smiles  # neutral is carbonate only
        assert sp.exact_mass < sp.exact_mass_full  # neutral < full
        assert "[Cs" not in (sp.smiles_neutral or "")

    def test_adducts_correct(self):
        from cdxml_toolkit.perception.reaction_parser import _compute_all_masses
        species = [
            SpeciesDescriptor(id="sp_0", smiles="C1COCCN1"),
        ]
        _compute_all_masses(species)
        sp = species[0]
        # [M+H]+ should be exact_mass + ~1.007
        mh = sp.adducts["[M+H]+"]
        assert abs(mh - sp.exact_mass - 1.00728) < 0.001


# ===================================================================
# v1.1 feature tests — scheme position, conditions, ELN data
# ===================================================================

class TestExtractConditionsFromText:
    """Tests for extract_conditions_from_text()."""

    def test_temperature(self):
        from cdxml_toolkit.perception.reaction_parser import extract_conditions_from_text
        result = extract_conditions_from_text("80 °C")
        assert "80 °C" in result

    def test_time(self):
        from cdxml_toolkit.perception.reaction_parser import extract_conditions_from_text
        result = extract_conditions_from_text("24 h")
        assert "24 h" in result

    def test_mixed_text(self):
        from cdxml_toolkit.perception.reaction_parser import extract_conditions_from_text
        result = extract_conditions_from_text("Cs2CO3\n80 °C, 24 h\nTHF")
        # Should extract "80 °C" and "24 h" but NOT "Cs2CO3" or "THF"
        assert any("80" in c for c in result)
        assert any("24" in c for c in result)
        # Chemical names should not be in conditions
        assert not any("Cs" in c for c in result)

    def test_empty(self):
        from cdxml_toolkit.perception.reaction_parser import extract_conditions_from_text
        result = extract_conditions_from_text("")
        assert result == []

    def test_rt(self):
        from cdxml_toolkit.perception.reaction_parser import extract_conditions_from_text
        result = extract_conditions_from_text("rt")
        assert "rt" in result

    def test_overnight(self):
        from cdxml_toolkit.perception.reaction_parser import extract_conditions_from_text
        result = extract_conditions_from_text("overnight")
        assert "overnight" in result


class TestDisplayText:
    """Tests for _build_display_texts()."""

    def test_reagent_with_equiv(self):
        from cdxml_toolkit.perception.reaction_parser import _build_display_texts
        species = [
            SpeciesDescriptor(id="sp_0", name="Cs2CO3",
                              csv_equiv="2.0"),
        ]
        _build_display_texts(species)
        assert species[0].display_text == "Cs2CO3 (2 eq.)"

    def test_substrate_no_equiv(self):
        from cdxml_toolkit.perception.reaction_parser import _build_display_texts
        species = [
            SpeciesDescriptor(id="sp_0", name="ArBr",
                              is_substrate=True,
                              csv_equiv="1.0"),
        ]
        _build_display_texts(species)
        assert species[0].display_text == "ArBr"

    def test_solvent_no_equiv(self):
        from cdxml_toolkit.perception.reaction_parser import _build_display_texts
        species = [
            SpeciesDescriptor(id="sp_0", name="DMF",
                              is_solvent=True, csv_equiv=""),
        ]
        _build_display_texts(species)
        assert species[0].display_text == "DMF"

    def test_equiv_one_not_shown(self):
        from cdxml_toolkit.perception.reaction_parser import _build_display_texts
        species = [
            SpeciesDescriptor(id="sp_0", name="NaH",
                              csv_equiv="1"),
        ]
        _build_display_texts(species)
        assert species[0].display_text == "NaH"

    def test_no_name_gives_none(self):
        from cdxml_toolkit.perception.reaction_parser import _build_display_texts
        species = [
            SpeciesDescriptor(id="sp_0", name=""),
        ]
        _build_display_texts(species)
        assert species[0].display_text is None


class TestFormatEquiv:
    """Tests for _format_equiv()."""

    def test_integer_equiv(self):
        from cdxml_toolkit.perception.reaction_parser import _format_equiv
        assert _format_equiv("2.0") == "2"
        assert _format_equiv("3.0") == "3"

    def test_decimal_equiv(self):
        from cdxml_toolkit.perception.reaction_parser import _format_equiv
        assert _format_equiv("0.05") == "0.05"
        assert _format_equiv("1.5") == "1.5"

    def test_empty_equiv(self):
        from cdxml_toolkit.perception.reaction_parser import _format_equiv
        assert _format_equiv("") == ""
        assert _format_equiv(None) == ""


class TestElnData:
    """Tests for _populate_eln_data()."""

    def test_no_exp_data(self):
        from cdxml_toolkit.perception.reaction_parser import _populate_eln_data
        desc = ReactionDescriptor()
        _populate_eln_data(desc, None)
        assert desc.eln_data is None

    def test_with_product_data(self):
        """Test with a mock exp_data containing product info."""
        from cdxml_toolkit.perception.reaction_parser import _populate_eln_data
        from types import SimpleNamespace
        product = SimpleNamespace(
            obtained_mass="1.6 g", yield_pct="72%", name="product")
        exp = SimpleNamespace(
            product=product,
            procedure_html="Add SM to flask.",
            solvents=[SimpleNamespace(name="DMF")],
        )
        desc = ReactionDescriptor(species=[
            SpeciesDescriptor(id="sp_0", is_sm=True, csv_mass="2.15 g"),
        ])
        _populate_eln_data(desc, exp)
        assert desc.eln_data is not None
        assert desc.eln_data["sm_mass"] == "2.15 g"
        assert desc.eln_data["product_obtained"] == "1.6 g"
        assert desc.eln_data["product_yield"] == "72%"
        assert desc.eln_data["solvents"] == ["DMF"]


class TestBackwardCompatV10:
    """Test that v1.0 JSONs (without new fields) load correctly."""

    def test_v10_json_loads(self):
        """A v1.0 JSON without conditions/eln_data loads fine."""
        d = {
            "version": "1.0",
            "experiment": "old-test",
            "species": [
                {"id": "sp_0", "smiles": "CCO", "name": "ethanol",
                 "role": "non_contributing"},
            ],
            "warnings": [],
            "metadata": {},
        }
        rd = ReactionDescriptor.from_dict(d)
        assert rd.version == "1.0"
        assert rd.conditions == []
        assert rd.eln_data is None
        assert rd.species[0].is_substrate is False
        assert rd.species[0].is_solvent is False
        assert rd.species[0].display_text is None


# ===================================================================
# ReactionDescriptor.summary() and reaction_summary() tests
# ===================================================================

def _make_test_descriptor():
    """Build a ReactionDescriptor with enough fields to exercise summary()."""
    sp0 = SpeciesDescriptor(
        id="sp_0", smiles="Brc1ncnc2sccc12", name="ArBr",
        role="atom_contributing", role_detail=None,
        classification_method="schneider_fp",
        is_sm=True, is_dp=False, is_substrate=True, is_solvent=False,
        exact_mass=213.92, exact_mass_full=213.92, mw=215.07,
        formula="C6H3BrN2S",
        adducts={"[M+H]+": 214.93, "[M-H]-": 212.91},
        source="fragment", source_id="23",
        csv_equiv="1.0", csv_mass="2.15 g", csv_name="ArBr",
        display_text="ArBr",
        original_geometry={"atoms": [{"id": 2, "x": 0, "y": 0, "symbol": "C"}],
                           "bonds": [], "bond_length": 14.4},
    )
    sp1 = SpeciesDescriptor(
        id="sp_1", smiles="C1COCCN1", name="morpholine",
        role="atom_contributing",
        is_sm=False, is_dp=False, is_substrate=False, is_solvent=False,
        exact_mass=87.07, exact_mass_full=87.07, mw=87.12,
        formula="C4H9NO",
        adducts={"[M+H]+": 88.08},
        source="fragment", source_id="62",
        csv_equiv="1.2", csv_mass="1.06 g",
        display_text="morpholine (1.2 eq.)",
    )
    sp2 = SpeciesDescriptor(
        id="sp_2", smiles="c1nc(N2CCOCC2)c2ccsc2n1", name="product",
        role="product",
        is_sm=False, is_dp=True, is_substrate=False, is_solvent=False,
        exact_mass=221.06, exact_mass_full=221.06, mw=221.28,
        formula="C10H11N3OS",
        adducts={"[M+H]+": 222.07},
        source="fragment", source_id="97",
        display_text="product",
    )
    return ReactionDescriptor(
        experiment="TEST-001",
        species=[sp0, sp1, sp2],
        conditions=["105 °C", "24 h"],
        eln_data={
            "sm_mass": "2.15 g",
            "product_obtained": "1.60 g",
            "product_yield": "72 %",
            "reaction_type": "Buchwald coupling",
            "procedure_plain": "SM was dissolved in dioxane...",
            "labbook_name": "Draft",
            "solvents": ["Dioxane"],
        },
    )


class TestReactionSummary:
    """Tests for ReactionDescriptor.summary() and reaction_summary()."""

    def test_default_summary_species_fields(self):
        desc = _make_test_descriptor()
        s = desc.summary()
        sp = s["species"][0]
        # Default fields present
        for key in ["id", "name", "role", "smiles", "display_text",
                     "formula", "mw"]:
            assert key in sp, f"missing default field: {key}"
        # Heavy fields absent
        for key in ["original_geometry", "adducts", "exact_mass",
                     "source_id", "csv_mass", "classification_method"]:
            assert key not in sp, f"should not be in default: {key}"

    def test_default_summary_top_level(self):
        desc = _make_test_descriptor()
        s = desc.summary()
        assert s["experiment"] == "TEST-001"
        assert s["conditions"] == ["105 °C", "24 h"]
        # Non-default top-level fields absent
        assert "version" not in s
        assert "reaction_smiles" not in s
        assert "warnings" not in s
        assert "metadata" not in s

    def test_default_summary_eln(self):
        desc = _make_test_descriptor()
        s = desc.summary()
        assert s["eln_data"]["product_yield"] == "72 %"
        assert s["eln_data"]["reaction_type"] == "Buchwald coupling"
        # Non-default eln fields absent
        assert "procedure_plain" not in s["eln_data"]
        assert "sm_mass" not in s["eln_data"]

    def test_custom_species_fields(self):
        desc = _make_test_descriptor()
        s = desc.summary(species_fields=["id", "smiles", "exact_mass", "adducts"])
        sp = s["species"][0]
        assert sp["exact_mass"] == 213.92
        assert "[M+H]+" in sp["adducts"]
        assert "name" not in sp

    def test_custom_top_fields(self):
        desc = _make_test_descriptor()
        s = desc.summary(top_fields=["experiment", "version"])
        assert s["experiment"] == "TEST-001"
        assert s["version"] == "1.3"
        assert "conditions" not in s

    def test_custom_eln_fields(self):
        desc = _make_test_descriptor()
        s = desc.summary(eln_fields=["procedure_plain", "sm_mass"])
        assert s["eln_data"]["procedure_plain"].startswith("SM was")
        assert s["eln_data"]["sm_mass"] == "2.15 g"
        assert "product_yield" not in s["eln_data"]

    def test_empty_eln_fields_omits_eln_data(self):
        desc = _make_test_descriptor()
        s = desc.summary(eln_fields=[])
        assert "eln_data" not in s

    def test_star_species_fields(self):
        desc = _make_test_descriptor()
        s = desc.summary(species_fields=["*"])
        sp = s["species"][0]
        assert "original_geometry" in sp
        assert "adducts" in sp
        assert "csv_mass" in sp

    def test_star_top_fields(self):
        desc = _make_test_descriptor()
        s = desc.summary(top_fields=["*"])
        assert "version" in s
        assert "experiment" in s
        assert "conditions" in s

    def test_star_eln_fields(self):
        desc = _make_test_descriptor()
        s = desc.summary(eln_fields=["*"])
        assert "procedure_plain" in s["eln_data"]
        assert "product_yield" in s["eln_data"]
        assert "sm_mass" in s["eln_data"]

    def test_no_eln_data(self):
        desc = _make_test_descriptor()
        desc.eln_data = None
        s = desc.summary()
        assert "eln_data" not in s

    def test_role_detail_included_when_present(self):
        desc = _make_test_descriptor()
        desc.species[0].role_detail = "ligand"
        s = desc.summary()
        assert s["species"][0]["role_detail"] == "ligand"

    def test_role_detail_absent_when_none(self):
        desc = _make_test_descriptor()
        s = desc.summary()
        # sp_0 has role_detail=None → to_dict() strips it → not in summary
        assert "role_detail" not in s["species"][0]

    def test_species_count_preserved(self):
        desc = _make_test_descriptor()
        s = desc.summary()
        assert len(s["species"]) == 3

    def test_reaction_summary_from_file(self):
        """Test the standalone reaction_summary() convenience function."""
        desc = _make_test_descriptor()
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            json.dump(desc.to_dict(), f, indent=2)
            path = f.name
        try:
            s = reaction_summary(path)
            assert s["experiment"] == "TEST-001"
            assert len(s["species"]) == 3
            assert "original_geometry" not in s["species"][0]
        finally:
            os.unlink(path)

    def test_reaction_summary_custom_fields_from_file(self):
        """Test custom field selection via the file-based function."""
        desc = _make_test_descriptor()
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            json.dump(desc.to_dict(), f, indent=2)
            path = f.name
        try:
            s = reaction_summary(
                path,
                species_fields=["id", "exact_mass", "adducts"],
                eln_fields=["procedure_plain"],
            )
            assert s["species"][0]["exact_mass"] == 213.92
            assert "name" not in s["species"][0]
            assert "procedure_plain" in s["eln_data"]
        finally:
            os.unlink(path)
