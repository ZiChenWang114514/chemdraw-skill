"""Tests for cdxml_toolkit.scheme_reader — CDXML scheme comprehension."""

import json
import os
import pytest
import tempfile

from cdxml_toolkit.perception.scheme_reader import (
    read_scheme,
    SchemeDescription,
    SpeciesRecord,
    StepRecord,
    _detect_topology,
    _get_text_content,
)


# ---------------------------------------------------------------------------
# Skip marker: ChemScript-only (SMILES→name, aligned naming)
# ---------------------------------------------------------------------------

def _chemscript_available():
    try:
        from cdxml_toolkit.chemdraw.chemscript_bridge import ChemScriptBridge
        ChemScriptBridge()
        return True
    except Exception:
        return False

needs_chemscript = pytest.mark.skipif(
    not _chemscript_available(),
    reason="ChemScript required (SMILES-to-name not available via OPSIN)",
)


# ---------------------------------------------------------------------------
# Test data paths
# ---------------------------------------------------------------------------

SHOWCASE_DIR = os.path.join(
    os.path.dirname(__file__), "..", "experiments", "scheme_dsl", "showcase"
)


def _showcase(name: str) -> str:
    """Return full path to a showcase CDXML file."""
    path = os.path.join(SHOWCASE_DIR, name)
    if not os.path.isfile(path):
        pytest.skip(f"Showcase file not found: {path}")
    return path


# ---------------------------------------------------------------------------
# Single-step schemes
# ---------------------------------------------------------------------------

class TestSingleStep:
    """Tests on single-step reaction schemes."""

    def test_buchwald_step_count(self):
        desc = read_scheme(_showcase("01_buchwald_linear.cdxml"),
                           use_network=False)
        assert desc.num_steps == 1

    def test_buchwald_topology(self):
        desc = read_scheme(_showcase("01_buchwald_linear.cdxml"),
                           use_network=False)
        assert desc.topology == "linear"

    def test_buchwald_has_species(self):
        desc = read_scheme(_showcase("01_buchwald_linear.cdxml"),
                           use_network=False)
        # Should have at least reactant, product, and morpholine
        assert len(desc.species) >= 3

    def test_buchwald_reactant_smiles(self):
        """Reactant aryl bromide SMILES should match the YAML source."""
        desc = read_scheme(_showcase("01_buchwald_linear.cdxml"),
                           use_network=False)
        step = desc.steps[0]
        reactant = desc.species[step.reactant_ids[0]]
        assert reactant.smiles == "Brc1ccc2ccccc2n1"

    def test_buchwald_product_smiles(self):
        desc = read_scheme(_showcase("01_buchwald_linear.cdxml"),
                           use_network=False)
        step = desc.steps[0]
        product = desc.species[step.product_ids[0]]
        assert product.smiles == "c1ccc2nc(N3CCOCC3)ccc2c1"

    def test_buchwald_labels(self):
        """Compound labels should be detected from nearby text."""
        desc = read_scheme(_showcase("01_buchwald_linear.cdxml"),
                           use_network=False)
        step = desc.steps[0]
        reactant = desc.species[step.reactant_ids[0]]
        product = desc.species[step.product_ids[0]]
        assert reactant.label == "1"
        assert product.label == "2"

    def test_buchwald_conditions(self):
        desc = read_scheme(_showcase("01_buchwald_linear.cdxml"),
                           use_network=False)
        conds = desc.steps[0].conditions
        # Should extract temperature/time from "reflux, 24 h"
        assert any("reflux" in c.lower() for c in conds)
        assert any("24" in c and "h" in c for c in conds)

    def test_buchwald_arrow_style(self):
        desc = read_scheme(_showcase("01_buchwald_linear.cdxml"),
                           use_network=False)
        assert desc.steps[0].arrow_style == "solid"

    def test_morpholine_name_resolved(self):
        """Fragment species should get names from reagent_db."""
        desc = read_scheme(_showcase("01_buchwald_linear.cdxml"),
                           use_network=False)
        names = [sp.name for sp in desc.species.values() if sp.name]
        assert any("morpholine" in n.lower() for n in names)

    def test_suzuki(self):
        desc = read_scheme(_showcase("02_suzuki_linear.cdxml"),
                           use_network=False)
        assert desc.num_steps == 1
        assert desc.topology == "linear"

    def test_snar(self):
        desc = read_scheme(_showcase("03_snar_linear.cdxml"),
                           use_network=False)
        assert desc.num_steps == 1

    def test_amide_coupling(self):
        desc = read_scheme(_showcase("04_amide_coupling_linear.cdxml"),
                           use_network=False)
        assert desc.num_steps == 1

    def test_boc_deprotection(self):
        desc = read_scheme(_showcase("05_boc_deprotection_linear.cdxml"),
                           use_network=False)
        assert desc.num_steps == 1


# ---------------------------------------------------------------------------
# Multi-step sequential schemes
# ---------------------------------------------------------------------------

class TestMultiStep:
    """Tests on multi-step sequential reaction schemes."""

    def test_two_step_count(self):
        desc = read_scheme(_showcase("06_two_step_sequential.cdxml"),
                           use_network=False)
        assert desc.num_steps == 2

    def test_two_step_topology(self):
        desc = read_scheme(_showcase("06_two_step_sequential.cdxml"),
                           use_network=False)
        assert desc.topology == "linear"

    def test_two_step_shared_intermediate(self):
        """Product of step 1 should be reactant of step 2."""
        desc = read_scheme(_showcase("06_two_step_sequential.cdxml"),
                           use_network=False)
        step1_products = set(desc.steps[0].product_ids)
        step2_reactants = set(desc.steps[1].reactant_ids)
        assert step1_products & step2_reactants, \
            "No shared intermediate between step 1 and step 2"

    def test_three_step_count(self):
        desc = read_scheme(_showcase("07_three_step_sequential.cdxml"),
                           use_network=False)
        assert desc.num_steps == 3

    def test_three_step_topology(self):
        desc = read_scheme(_showcase("07_three_step_sequential.cdxml"),
                           use_network=False)
        assert desc.topology == "linear"

    def test_three_step_chain(self):
        """Each step should feed the next."""
        desc = read_scheme(_showcase("07_three_step_sequential.cdxml"),
                           use_network=False)
        for i in range(len(desc.steps) - 1):
            products_i = set(desc.steps[i].product_ids)
            reactants_next = set(desc.steps[i + 1].reactant_ids)
            assert products_i & reactants_next, \
                f"No link between step {i} and step {i + 1}"

    def test_three_step_smiles(self):
        """Verify SMILES match the YAML source."""
        desc = read_scheme(_showcase("07_three_step_sequential.cdxml"),
                           use_network=False)
        # Reactant of step 0 should be aryl bromide
        sm = desc.species[desc.steps[0].reactant_ids[0]]
        assert sm.smiles == "Brc1ccc2ccccc2n1"
        # Final product
        fp = desc.species[desc.steps[2].product_ids[0]]
        assert fp.smiles == "c1ccc(-c2cc3ccccc3nc2N2CCOCC2)cc1"


# ---------------------------------------------------------------------------
# Wrap-repeat and serpentine
# ---------------------------------------------------------------------------

class TestWrapLayouts:
    """Tests for wrapped multi-step layouts."""

    def test_wrap_repeat_4step(self):
        desc = read_scheme(_showcase("08_wrap_repeat_4step.cdxml"),
                           use_network=False)
        assert desc.num_steps == 4
        assert desc.topology == "linear"

    def test_wrap_repeat_5step(self):
        desc = read_scheme(_showcase("09_wrap_repeat_5step.cdxml"),
                           use_network=False)
        assert desc.num_steps == 5
        assert desc.topology == "linear"

    def test_serpentine_5step(self):
        desc = read_scheme(_showcase("12_serpentine_5step.cdxml"),
                           use_network=False)
        assert desc.num_steps >= 3  # At least 3 steps visible


# ---------------------------------------------------------------------------
# Divergent schemes
# ---------------------------------------------------------------------------

class TestDivergent:
    """Tests for divergent (SAR) reaction schemes."""

    def test_divergent_topology(self):
        desc = read_scheme(_showcase("17_divergent_buchwald_sar.cdxml"),
                           use_network=False)
        assert desc.topology == "divergent"

    def test_divergent_shared_reactant(self):
        """All steps should share the same reactant."""
        desc = read_scheme(_showcase("17_divergent_buchwald_sar.cdxml"),
                           use_network=False)
        reactant_sets = [set(s.reactant_ids) for s in desc.steps]
        common = reactant_sets[0]
        for rs in reactant_sets[1:]:
            common &= rs
        assert common, "No common reactant across divergent steps"

    def test_divergent_different_products(self):
        """Each step should have a different product."""
        desc = read_scheme(_showcase("17_divergent_buchwald_sar.cdxml"),
                           use_network=False)
        product_ids = [s.product_ids[0] for s in desc.steps]
        assert len(set(product_ids)) == len(product_ids)

    def test_divergent_labels(self):
        """Products should have labels 2a, 2b, 2c."""
        desc = read_scheme(_showcase("17_divergent_buchwald_sar.cdxml"),
                           use_network=False)
        labels = set()
        for step in desc.steps:
            for pid in step.product_ids:
                sp = desc.species[pid]
                if sp.label:
                    labels.add(sp.label)
        assert "2a" in labels
        assert "2b" in labels
        assert "2c" in labels

    def test_4_product_divergent(self):
        desc = read_scheme(_showcase("18_divergent_4products.cdxml"),
                           use_network=False)
        assert desc.topology == "divergent"
        assert desc.num_steps == 4


# ---------------------------------------------------------------------------
# Arrow styles
# ---------------------------------------------------------------------------

class TestArrowStyles:
    """Tests for arrow style detection."""

    def test_failed_arrow(self):
        desc = read_scheme(_showcase("16_failed_arrow.cdxml"),
                           use_network=False)
        assert desc.steps[0].arrow_style in ("failed", "dashed")

    def test_divergent_with_failed(self):
        """Showcase 26 has one success and one failure."""
        desc = read_scheme(_showcase("26_divergent_success_vs_failure.cdxml"),
                           use_network=False)
        styles = [s.arrow_style for s in desc.steps]
        assert "solid" in styles
        assert "failed" in styles


# ---------------------------------------------------------------------------
# Parallel / stacked-rows
# ---------------------------------------------------------------------------

class TestParallel:
    """Tests for parallel (stacked-rows) schemes."""

    def test_stacked_rows_topology(self):
        desc = read_scheme(_showcase("19_stacked_rows_comparison.cdxml"),
                           use_network=False)
        assert desc.topology == "parallel"

    def test_stacked_rows_step_count(self):
        desc = read_scheme(_showcase("19_stacked_rows_comparison.cdxml"),
                           use_network=False)
        assert desc.num_steps == 3

    def test_stacked_different_routes(self):
        desc = read_scheme(_showcase("20_stacked_rows_different_routes.cdxml"),
                           use_network=False)
        assert desc.topology == "parallel"


# ---------------------------------------------------------------------------
# Yield extraction
# ---------------------------------------------------------------------------

class TestYield:
    """Tests for yield extraction from text."""

    def test_yield_from_conditions(self):
        desc = read_scheme(_showcase("17_divergent_buchwald_sar.cdxml"),
                           use_network=False)
        # Step 1 should have yield "72%"
        assert desc.steps[0].yield_text == "72%"

    def test_stacked_rows_yields(self):
        desc = read_scheme(_showcase("19_stacked_rows_comparison.cdxml"),
                           use_network=False)
        yields = [s.yield_text for s in desc.steps if s.yield_text]
        assert len(yields) >= 2  # At least 2 of 3 should have yields


# ---------------------------------------------------------------------------
# Topology detection (unit tests)
# ---------------------------------------------------------------------------

class TestTopologyDetection:
    """Unit tests for _detect_topology with synthetic data."""

    def test_single_step(self):
        steps = [StepRecord(step_index=0, reactant_ids=["a"],
                            product_ids=["b"])]
        assert _detect_topology(steps) == "linear"

    def test_linear_chain(self):
        steps = [
            StepRecord(step_index=0, reactant_ids=["a"], product_ids=["b"]),
            StepRecord(step_index=1, reactant_ids=["b"], product_ids=["c"]),
            StepRecord(step_index=2, reactant_ids=["c"], product_ids=["d"]),
        ]
        assert _detect_topology(steps) == "linear"

    def test_divergent(self):
        steps = [
            StepRecord(step_index=0, reactant_ids=["a"], product_ids=["b"]),
            StepRecord(step_index=1, reactant_ids=["a"], product_ids=["c"]),
            StepRecord(step_index=2, reactant_ids=["a"], product_ids=["d"]),
        ]
        assert _detect_topology(steps) == "divergent"

    def test_parallel_disconnected(self):
        steps = [
            StepRecord(step_index=0, reactant_ids=["a"], product_ids=["b"]),
            StepRecord(step_index=1, reactant_ids=["c"], product_ids=["d"]),
        ]
        assert _detect_topology(steps) == "parallel"

    def test_convergent(self):
        steps = [
            StepRecord(step_index=0, reactant_ids=["a"], product_ids=["c"]),
            StepRecord(step_index=1, reactant_ids=["b"], product_ids=["c"]),
        ]
        assert _detect_topology(steps) == "convergent"

    def test_empty(self):
        assert _detect_topology([]) == "linear"


# ---------------------------------------------------------------------------
# Narrative generation
# ---------------------------------------------------------------------------

class TestNarrative:
    """Tests for narrative content."""

    def test_narrative_step_count(self):
        desc = read_scheme(_showcase("07_three_step_sequential.cdxml"),
                           use_network=False)
        assert "3-step" in desc.narrative

    def test_narrative_topology(self):
        desc = read_scheme(_showcase("17_divergent_buchwald_sar.cdxml"),
                           use_network=False)
        assert "divergent" in desc.narrative

    @needs_chemscript
    def test_narrative_contains_aligned_names(self):
        desc = read_scheme(_showcase("01_buchwald_linear.cdxml"),
                           use_network=False)
        # Aligned IUPAC names should appear instead of raw SMILES
        assert "bromoquinoline" in desc.narrative.lower()
        assert "morpholin" in desc.narrative.lower()
        # Molecular diff should be in the narrative
        assert "bromo" in desc.narrative.lower()
        # SMILES should NOT appear in the narrative when names are available
        assert "SMILES:" not in desc.narrative

    def test_narrative_mentions_failed(self):
        desc = read_scheme(_showcase("26_divergent_success_vs_failure.cdxml"),
                           use_network=False)
        assert "FAILED" in desc.narrative

    def test_narrative_step_labels(self):
        desc = read_scheme(_showcase("07_three_step_sequential.cdxml"),
                           use_network=False)
        assert "Step 1:" in desc.narrative
        assert "Step 2:" in desc.narrative
        assert "Step 3:" in desc.narrative

    def test_narrative_includes_molecular_diff(self):
        desc = read_scheme(_showcase("01_buchwald_linear.cdxml"),
                           use_network=False)
        # Molecular diff should appear in brackets
        assert "[" in desc.narrative and "]" in desc.narrative


# ---------------------------------------------------------------------------
# Aligned naming
# ---------------------------------------------------------------------------

class TestAlignedNaming:
    """Tests for aligned IUPAC name enrichment."""

    @needs_chemscript
    def test_aligned_iupac_populated(self):
        desc = read_scheme(_showcase("01_buchwald_linear.cdxml"),
                           use_network=False)
        # Find species with aligned names
        named = [sp for sp in desc.species.values()
                 if sp.aligned_iupac is not None]
        assert len(named) >= 2, "Expected SM and product to have aligned names"

    def test_molecular_diff_on_step(self):
        desc = read_scheme(_showcase("01_buchwald_linear.cdxml"),
                           use_network=False)
        assert desc.steps[0].molecular_diff_text is not None
        assert len(desc.steps[0].molecular_diff_text) > 0

    @needs_chemscript
    def test_aligned_names_in_json(self):
        desc = read_scheme(_showcase("01_buchwald_linear.cdxml"),
                           use_network=False)
        d = desc.to_dict()
        # Check at least one species has aligned_iupac in the dict
        has_aligned = any("aligned_iupac" in sp_d
                          for sp_d in d["species"].values())
        assert has_aligned, "aligned_iupac missing from JSON output"
        # Check molecular_diff_text in steps
        has_diff = any("molecular_diff_text" in s
                       for s in d["steps"])
        assert has_diff, "molecular_diff_text missing from JSON output"

    def test_multistep_aligned_names(self):
        desc = read_scheme(_showcase("07_three_step_sequential.cdxml"),
                           use_network=False)
        # Each step should have a molecular diff
        for step in desc.steps:
            assert step.molecular_diff_text is not None, \
                f"Step {step.step_index} missing molecular_diff_text"


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------

class TestSerialization:
    """Tests for JSON serialization and deserialization."""

    def test_to_dict_roundtrip(self):
        desc = read_scheme(_showcase("07_three_step_sequential.cdxml"),
                           use_network=False)
        d = desc.to_dict()
        desc2 = SchemeDescription.from_dict(d)
        assert desc2.num_steps == desc.num_steps
        assert desc2.topology == desc.topology
        assert len(desc2.species) == len(desc.species)

    def test_to_json_file(self):
        desc = read_scheme(_showcase("01_buchwald_linear.cdxml"),
                           use_network=False)
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json",
                                         delete=False) as f:
            tmp_path = f.name
        try:
            desc.to_json(tmp_path)
            desc2 = SchemeDescription.from_json(tmp_path)
            assert desc2.num_steps == 1
            assert desc2.topology == "linear"
        finally:
            os.unlink(tmp_path)


# ---------------------------------------------------------------------------
# SchemeDescriptor bridge (round-trip)
# ---------------------------------------------------------------------------

class TestRoundTrip:
    """Tests for to_scheme_descriptor() bridge."""

    def test_bridge_step_count(self):
        desc = read_scheme(_showcase("06_two_step_sequential.cdxml"),
                           use_network=False)
        sd = desc.to_scheme_descriptor()
        assert len(sd.steps) == 2

    def test_bridge_layout(self):
        desc = read_scheme(_showcase("06_two_step_sequential.cdxml"),
                           use_network=False)
        sd = desc.to_scheme_descriptor()
        assert sd.layout == "sequential"

    def test_bridge_divergent_layout(self):
        desc = read_scheme(_showcase("17_divergent_buchwald_sar.cdxml"),
                           use_network=False)
        sd = desc.to_scheme_descriptor()
        assert sd.layout == "divergent"

    def test_bridge_has_structures(self):
        desc = read_scheme(_showcase("01_buchwald_linear.cdxml"),
                           use_network=False)
        sd = desc.to_scheme_descriptor()
        # Should have structure refs for species with SMILES
        smiles_species = [s for s in desc.species.values() if s.smiles]
        assert len(sd.structures) >= len(smiles_species)


# ---------------------------------------------------------------------------
# All showcase files parse without error
# ---------------------------------------------------------------------------

class TestAllShowcase:
    """Ensure all 30 showcase files parse without exceptions."""

    @pytest.fixture(params=[f for f in sorted(os.listdir(SHOWCASE_DIR))
                            if f.endswith(".cdxml")]
                    if os.path.isdir(SHOWCASE_DIR) else [])
    def showcase_cdxml(self, request):
        return os.path.join(SHOWCASE_DIR, request.param)

    def test_no_parse_error(self, showcase_cdxml):
        desc = read_scheme(showcase_cdxml, use_network=False)
        assert desc.num_steps >= 1
        assert len(desc.species) >= 1
        assert desc.narrative  # non-empty narrative
        assert desc.topology in ("linear", "divergent", "convergent",
                                 "parallel", "mixed")


# ---------------------------------------------------------------------------
# Segmenter
# ---------------------------------------------------------------------------

EXTRACTED_DOCX_DIR = os.path.join(
    os.environ.get("CHEM_TEST_DATA", os.path.join(
        os.path.dirname(__file__), "..", "..", "chem-test-data")),
    "extracted_docx",
)


def _oleobj(name: str) -> str:
    path = os.path.join(EXTRACTED_DOCX_DIR, name)
    if not os.path.isfile(path):
        pytest.skip(f"oleObject not found: {path}")
    return path


class TestSegmenter:
    """Tests for scheme_segmenter module."""

    def test_import(self):
        from cdxml_toolkit.perception.scheme_segmenter import (
            segment_scheme, classify_scheme_complexity, SchemeSegment,
        )

    def test_oleobject12_segments_into_5(self):
        from cdxml_toolkit.perception.scheme_segmenter import segment_scheme
        r = segment_scheme(_oleobj("oleObject12.cdxml"))
        assert r.num_segments == 5
        assert r.is_multi_panel
        assert not r.wrap_repeat_detected

    def test_oleobject12_segments_are_disjoint(self):
        from cdxml_toolkit.perception.scheme_segmenter import segment_scheme
        r = segment_scheme(_oleobj("oleObject12.cdxml"))
        all_species = []
        for seg in r.segments:
            all_species.extend(seg.species_ids)
        # No duplicates = disjoint
        assert len(all_species) == len(set(all_species))

    def test_wrap_repeat_not_segmented(self):
        from cdxml_toolkit.perception.scheme_segmenter import segment_scheme
        r = segment_scheme(_showcase("08_wrap_repeat_4step.cdxml"))
        assert r.num_segments == 1
        assert not r.is_multi_panel
        assert r.wrap_repeat_detected

    def test_single_scheme_not_segmented(self):
        from cdxml_toolkit.perception.scheme_segmenter import segment_scheme
        r = segment_scheme(_showcase("01_buchwald_linear.cdxml"))
        assert r.num_segments == 1
        assert not r.is_multi_panel

    def test_classify_simple(self):
        from cdxml_toolkit.perception.scheme_segmenter import classify_scheme_complexity
        tier = classify_scheme_complexity(
            _showcase("01_buchwald_linear.cdxml"))
        assert tier == "simple"

    def test_classify_complex(self):
        from cdxml_toolkit.perception.scheme_segmenter import classify_scheme_complexity
        tier = classify_scheme_complexity(_oleobj("oleObject12.cdxml"))
        assert tier == "complex"


# ---------------------------------------------------------------------------
# Segmented read_scheme
# ---------------------------------------------------------------------------

class TestSegmentedReadScheme:
    """Tests for read_scheme(segment=True)."""

    def test_oleobject12_composite(self):
        desc = read_scheme(_oleobj("oleObject12.cdxml"),
                           use_network=False, segment=True)
        assert desc.content_type == "composite"
        assert desc.topology == "parallel"
        assert len(desc.sub_schemes) == 5

    def test_oleobject12_sub_schemes_have_steps(self):
        desc = read_scheme(_oleobj("oleObject12.cdxml"),
                           use_network=False, segment=True)
        total = sum(s.num_steps for s in desc.sub_schemes)
        assert total == desc.num_steps
        for sub in desc.sub_schemes:
            assert sub.num_steps >= 1
            assert len(sub.species) >= 2

    def test_wrap_repeat_stays_connected(self):
        desc = read_scheme(_showcase("08_wrap_repeat_4step.cdxml"),
                           use_network=False, segment=True)
        assert len(desc.sub_schemes) == 0
        assert desc.num_steps == 4
        assert desc.topology == "linear"

    def test_segment_false_backward_compatible(self):
        desc = read_scheme(_oleobj("oleObject12.cdxml"),
                           use_network=False, segment=False)
        assert len(desc.sub_schemes) == 0
        assert desc.num_steps == 8  # merged flat list

    def test_sub_schemes_serialization(self):
        desc = read_scheme(_oleobj("oleObject12.cdxml"),
                           use_network=False, segment=True)
        d = desc.to_dict()
        assert "sub_schemes" in d
        assert len(d["sub_schemes"]) == 5
        # Round-trip
        desc2 = SchemeDescription.from_dict(d)
        assert len(desc2.sub_schemes) == 5
        assert desc2.sub_schemes[0].num_steps == desc.sub_schemes[0].num_steps

    def test_composite_narrative(self):
        desc = read_scheme(_oleobj("oleObject12.cdxml"),
                           use_network=False, segment=True)
        assert "5 independent" in desc.narrative
        assert "Sub-scheme 1" in desc.narrative


# ---------------------------------------------------------------------------
# Name decomposer — recursive decomposition
# ---------------------------------------------------------------------------

@needs_chemscript
class TestNameDecomposerRecursion:
    """Test recursive sub-fragment decomposition in decompose_name."""

    def test_compound6_quinoline_rooted(self):
        """Compound 6: (2-morpholino-4-phenylquinolin-3-yl)(phenyl)methanol.

        Recursive decomposition should produce quinoline-rooted alternatives,
        not just morpholine-rooted ones.
        """
        from cdxml_toolkit.naming.name_decomposer import decompose_name

        smiles = "OC(c1ccccc1)c1c(N2CCOCC2)nc3ccccc3c1-c1ccccc1"
        result = decompose_name(smiles, max_depth=1)

        valid_names = [a.name for a in result.alternatives if a.valid]

        # At least one valid alternative should be quinoline-rooted
        has_quinoline_parent = any(
            name.endswith("quinoline") for name in valid_names
        )
        assert has_quinoline_parent, (
            f"No quinoline-rooted alternative found. "
            f"Valid names: {valid_names}"
        )
