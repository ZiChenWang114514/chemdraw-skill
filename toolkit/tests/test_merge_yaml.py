"""Unit tests for multi-reaction merge logic in scheme_yaml_writer.py."""

import json
import os
import tempfile

import pytest

try:
    from rdkit import Chem  # noqa: F401
    _HAS_RDKIT = True
except ImportError:
    _HAS_RDKIT = False

pytestmark = pytest.mark.skipif(not _HAS_RDKIT, reason="RDKit not available")

from cdxml_toolkit.render.scheme_yaml_writer import (
    _canonicalize,
    _classify_pair,
    _build_merge_plan,
    _diff_reagents,
    _equiv_range,
    _extract_reaction_summary,
    _merge_eln_labels,
    _namespace_species_id,
    build_merged_scheme_yaml_dict,
    build_scheme_yaml_dict,
    write_scheme_yaml,
    ReactionSummary,
)
from cdxml_toolkit.render.schema import RunArrowEntry
from cdxml_toolkit.render.parser import parse_yaml


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_json(tmp_path, filename, species, conditions=None, eln_data=None):
    """Write a minimal reaction JSON file and return its path."""
    data = {
        "version": "1.3",
        "experiment": os.path.splitext(filename)[0],
        "input_files": {},
        "species": species,
        "conditions": conditions or [],
        "eln_data": eln_data or {},
    }
    path = os.path.join(str(tmp_path), filename)
    with open(path, "w") as f:
        json.dump(data, f)
    return path


def _buchwald_species(sm_smi="Brc1ccccc1", dp_smi="c1ccc(-n2cccc2)cc1",
                      catalyst="Pd2(dba)3", base="Cs2CO3",
                      cat_equiv="0.05", base_equiv="2.0",
                      solvent="THF"):
    """Build a typical Buchwald coupling species list."""
    return [
        {"id": "sp_0", "smiles": sm_smi, "name": "SM",
         "role": "atom_contributing", "is_sm": True, "is_dp": False,
         "source": "fragment"},
        {"id": "sp_1", "smiles": "C1CCNC1", "name": "pyrrole",
         "role": "atom_contributing", "is_sm": False, "is_dp": False,
         "is_substrate": False, "source": "fragment",
         "csv_equiv": "1.2"},
        {"id": "sp_2", "smiles": dp_smi, "name": "DP",
         "role": "product", "is_sm": False, "is_dp": True,
         "source": "fragment"},
        {"id": "sp_3", "smiles": "", "name": catalyst,
         "role": "non_contributing", "role_detail": "catalyst",
         "is_sm": False, "is_dp": False, "is_solvent": False,
         "source": "text_label", "csv_equiv": cat_equiv},
        {"id": "sp_4", "smiles": "O=C([O-])[O-].[Cs+].[Cs+]", "name": base,
         "role": "non_contributing", "role_detail": "base",
         "is_sm": False, "is_dp": False, "is_solvent": False,
         "source": "text_label", "csv_equiv": base_equiv},
        {"id": "sp_5", "smiles": "C1CCOC1", "name": solvent,
         "role": "non_contributing", "role_detail": "solvent",
         "is_sm": False, "is_dp": False, "is_solvent": True,
         "source": "text_label"},
    ]


# ---------------------------------------------------------------------------
# _canonicalize
# ---------------------------------------------------------------------------

def test_canonicalize_basic():
    assert _canonicalize("c1ccccc1") == "c1ccccc1"
    assert _canonicalize("C1=CC=CC=C1") == "c1ccccc1"


def test_canonicalize_empty():
    assert _canonicalize("") == ""
    assert _canonicalize("not_a_smiles") == "not_a_smiles"


# ---------------------------------------------------------------------------
# _namespace_species_id
# ---------------------------------------------------------------------------

def test_namespace_species_id():
    assert _namespace_species_id(0, "sp_0") == "rxn0_sp_0"
    assert _namespace_species_id(3, "sp_12") == "rxn3_sp_12"


# ---------------------------------------------------------------------------
# _extract_reaction_summary
# ---------------------------------------------------------------------------

def test_extract_reaction_summary(tmp_path):
    species = _buchwald_species()
    path = _write_json(tmp_path, "rxn1.json", species,
                       conditions=["100 °C", "24 h"])
    summary = _extract_reaction_summary(0, path)

    assert summary.sm_smiles == _canonicalize("Brc1ccccc1")
    assert summary.dp_smiles == _canonicalize("c1ccc(-n2cccc2)cc1")
    # Solvent should be excluded from reagent set
    assert "sp_5" not in summary.reagent_smiles
    # Non-solvent reagents should be present
    assert "sp_1" in summary.reagent_smiles  # pyrrole
    assert "sp_4" in summary.reagent_smiles  # Cs2CO3


def test_extract_excludes_solvents(tmp_path):
    """Solvents should not appear in the reagent comparison set."""
    species = _buchwald_species(solvent="DMF")
    species[5]["smiles"] = "CN(C)C=O"  # DMF SMILES
    path = _write_json(tmp_path, "rxn.json", species)
    s = _extract_reaction_summary(0, path)
    # DMF should not be in reagent_smiles
    reagent_smi_values = set(s.reagent_smiles.values())
    assert _canonicalize("CN(C)C=O") not in reagent_smi_values


# ---------------------------------------------------------------------------
# _classify_pair
# ---------------------------------------------------------------------------

def test_classify_parallel(tmp_path):
    """Same SM + DP + shared reagent → parallel."""
    sp_a = _buchwald_species(cat_equiv="0.05", base_equiv="2.0")
    sp_b = _buchwald_species(cat_equiv="0.05", base_equiv="1.5")
    path_a = _write_json(tmp_path, "a.json", sp_a)
    path_b = _write_json(tmp_path, "b.json", sp_b)
    sa = _extract_reaction_summary(0, path_a)
    sb = _extract_reaction_summary(1, path_b)
    assert _classify_pair(sa, sb) == "parallel"


def test_classify_sequential(tmp_path):
    """A's DP = B's SM → sequential_ab."""
    intermediate = "c1ccc(-n2cccc2)cc1"
    sp_a = _buchwald_species(dp_smi=intermediate)
    sp_b = _buchwald_species(sm_smi=intermediate, dp_smi="c1ccc(-n2cccc2)c(Br)c1")
    path_a = _write_json(tmp_path, "a.json", sp_a)
    path_b = _write_json(tmp_path, "b.json", sp_b)
    sa = _extract_reaction_summary(0, path_a)
    sb = _extract_reaction_summary(1, path_b)
    assert _classify_pair(sa, sb) == "sequential_ab"


def test_classify_unrelated(tmp_path):
    """Completely different reactions → unrelated."""
    sp_a = _buchwald_species(sm_smi="Brc1ccccc1", dp_smi="c1ccc(-n2cccc2)cc1")
    sp_b = _buchwald_species(sm_smi="ClC1=CC=CC=C1F", dp_smi="FC1=CC=CC(O)=C1")
    path_a = _write_json(tmp_path, "a.json", sp_a)
    path_b = _write_json(tmp_path, "b.json", sp_b)
    sa = _extract_reaction_summary(0, path_a)
    sb = _extract_reaction_summary(1, path_b)
    assert _classify_pair(sa, sb) == "unrelated"


def test_classify_same_endpoints_no_shared_reagent(tmp_path):
    """Same SM + DP but completely different reagents → unrelated."""
    sp_a = _buchwald_species()
    # Use completely different reagents for sp_b
    sp_b = [
        {"id": "sp_0", "smiles": "Brc1ccccc1", "name": "SM",
         "role": "atom_contributing", "is_sm": True, "is_dp": False,
         "source": "fragment"},
        {"id": "sp_1", "smiles": "C1CCOC1", "name": "morpholine",
         "role": "atom_contributing", "is_sm": False, "is_dp": False,
         "source": "fragment", "csv_equiv": "1.5"},
        {"id": "sp_2", "smiles": "c1ccc(-n2cccc2)cc1", "name": "DP",
         "role": "product", "is_sm": False, "is_dp": True,
         "source": "fragment"},
        {"id": "sp_3", "smiles": "[Cu+].[I-]", "name": "CuI",
         "role": "non_contributing", "role_detail": "catalyst",
         "is_sm": False, "is_dp": False, "source": "text_label"},
        {"id": "sp_4", "smiles": "O=C([O-])[O-].[K+].[K+]", "name": "K2CO3",
         "role": "non_contributing", "role_detail": "base",
         "is_sm": False, "is_dp": False, "source": "text_label"},
    ]
    path_a = _write_json(tmp_path, "a.json", sp_a)
    path_b = _write_json(tmp_path, "b.json", sp_b)
    sa = _extract_reaction_summary(0, path_a)
    sb = _extract_reaction_summary(1, path_b)
    assert _classify_pair(sa, sb) == "unrelated"


# ---------------------------------------------------------------------------
# _build_merge_plan
# ---------------------------------------------------------------------------

def test_merge_plan_parallel(tmp_path):
    """Three parallel reactions → single group with 3 members."""
    species = _buchwald_species()
    paths = [_write_json(tmp_path, f"r{i}.json", species) for i in range(3)]
    summaries = [_extract_reaction_summary(i, p) for i, p in enumerate(paths)]
    plan = _build_merge_plan(summaries)
    assert len(plan.parallel_groups) == 1
    assert sorted(plan.parallel_groups[0]) == [0, 1, 2]


def test_merge_plan_sequential(tmp_path):
    """Two sequential reactions → one chain of 2 groups."""
    intermediate = "c1ccc(-n2cccc2)cc1"
    sp_a = _buchwald_species(dp_smi=intermediate)
    sp_b = _buchwald_species(sm_smi=intermediate, dp_smi="c1cc(-n2cccc2)cc(Br)c1")
    path_a = _write_json(tmp_path, "a.json", sp_a)
    path_b = _write_json(tmp_path, "b.json", sp_b)
    summaries = [_extract_reaction_summary(0, path_a),
                 _extract_reaction_summary(1, path_b)]
    plan = _build_merge_plan(summaries)
    assert len(plan.chains) == 1
    assert len(plan.chains[0]) == 2
    assert len(plan.unrelated_groups) == 0


def test_merge_plan_independent_chains(tmp_path):
    """Two independent 2-step chains → two chains, no unrelated."""
    # Chain 1: A → B
    int1 = "c1ccc(-n2cccc2)cc1"
    sp_a = _buchwald_species(sm_smi="Brc1ccccc1", dp_smi=int1)
    sp_b = _buchwald_species(sm_smi=int1, dp_smi="c1cc(-n2cccc2)cc(Br)c1")
    # Chain 2: C → D (completely different molecules)
    int2 = "c1ccc(O)cc1"
    sp_c = _buchwald_species(sm_smi="Clc1ccc(F)cc1", dp_smi=int2)
    sp_d = _buchwald_species(sm_smi=int2, dp_smi="c1ccc(OC)cc1")
    paths = [
        _write_json(tmp_path, "a.json", sp_a),
        _write_json(tmp_path, "b.json", sp_b),
        _write_json(tmp_path, "c.json", sp_c),
        _write_json(tmp_path, "d.json", sp_d),
    ]
    summaries = [_extract_reaction_summary(i, p) for i, p in enumerate(paths)]
    plan = _build_merge_plan(summaries)
    assert len(plan.chains) == 2
    assert all(len(c) == 2 for c in plan.chains)
    assert len(plan.unrelated_groups) == 0


# ---------------------------------------------------------------------------
# _diff_reagents
# ---------------------------------------------------------------------------

def test_diff_reagents_identical(tmp_path):
    """Identical reagents → all_identical=True."""
    species = _buchwald_species()
    paths = [_write_json(tmp_path, f"r{i}.json", species) for i in range(2)]
    summaries = [_extract_reaction_summary(i, p) for i, p in enumerate(paths)]
    all_identical, notes = _diff_reagents(summaries, [0, 1])
    assert all_identical is True
    assert notes == {}


def test_diff_reagents_different_equivs_only(tmp_path):
    """Different equivs but same reagent set → all_identical=True.

    Equiv differences are handled by range notation on the main arrow,
    not by run arrow notes.
    """
    sp_a = _buchwald_species(base_equiv="2.0")
    sp_b = _buchwald_species(base_equiv="1.5")
    path_a = _write_json(tmp_path, "a.json", sp_a)
    path_b = _write_json(tmp_path, "b.json", sp_b)
    summaries = [_extract_reaction_summary(0, path_a),
                 _extract_reaction_summary(1, path_b)]
    all_identical, notes = _diff_reagents(summaries, [0, 1])
    assert all_identical is True
    assert notes == {}


def test_diff_reagents_qualitative_difference(tmp_path):
    """Different reagent set (one has extra SMILES reagent) → notes.

    Notes are template-relative: only runs that differ from the template
    (first reaction) get notes showing what THEY used that's different.
    """
    sp_a = _buchwald_species(catalyst="Pd2(dba)3", cat_equiv="0.05")
    # Give both catalysts actual SMILES
    sp_a[3]["smiles"] = "O=C(/C=C/c1ccccc1)/C=C/c1ccccc1"  # dba
    sp_b = _buchwald_species(catalyst="CuI", cat_equiv="0.1")
    sp_b[3]["smiles"] = "[Cu+].[I-]"  # CuI SMILES
    path_a = _write_json(tmp_path, "a.json", sp_a)
    path_b = _write_json(tmp_path, "b.json", sp_b)
    summaries = [_extract_reaction_summary(0, path_a),
                 _extract_reaction_summary(1, path_b)]
    all_identical, notes = _diff_reagents(summaries, [0, 1])
    assert all_identical is False
    # Template (reaction 0) matches itself → no note
    assert notes.get(0) is None
    # Reaction 1 uses CuI (not in template) → note
    assert notes.get(1) is not None  # "CuI"


# ---------------------------------------------------------------------------
# _equiv_range
# ---------------------------------------------------------------------------

def test_equiv_range():
    """Equivs 1.1 and 1.5 → "1.1–1.5" (en-dash)."""
    s0 = ReactionSummary(
        index=0, json_path="", experiment="",
        sm_smiles="", dp_smiles="",
        reagent_smiles={"sp_1": "CCO"},
        reagent_names={"sp_1": "EtOH"},
        reagent_equivs={"sp_1": "1.1"},
        all_smiles=set(), species=[], conditions=[], eln_data={},
    )
    s1 = ReactionSummary(
        index=1, json_path="", experiment="",
        sm_smiles="", dp_smiles="",
        reagent_smiles={"sp_1": "CCO"},
        reagent_names={"sp_1": "EtOH"},
        reagent_equivs={"sp_1": "1.5"},
        all_smiles=set(), species=[], conditions=[], eln_data={},
    )
    result = _equiv_range([s0, s1], [0, 1], "CCO")
    assert "\u2013" in result  # en-dash
    assert "1.1" in result
    assert "1.5" in result


def test_equiv_range_same():
    """Same equivs → single value, no range."""
    s0 = ReactionSummary(
        index=0, json_path="", experiment="",
        sm_smiles="", dp_smiles="",
        reagent_smiles={"sp_1": "CCO"},
        reagent_names={}, reagent_equivs={"sp_1": "2.0"},
        all_smiles=set(), species=[], conditions=[], eln_data={},
    )
    s1 = ReactionSummary(
        index=1, json_path="", experiment="",
        sm_smiles="", dp_smiles="",
        reagent_smiles={"sp_1": "CCO"},
        reagent_names={}, reagent_equivs={"sp_1": "2.0"},
        all_smiles=set(), species=[], conditions=[], eln_data={},
    )
    result = _equiv_range([s0, s1], [0, 1], "CCO")
    assert "\u2013" not in result
    assert "2" in result


# ---------------------------------------------------------------------------
# RunArrowEntry.note
# ---------------------------------------------------------------------------

def test_run_arrow_entry_note():
    """RunArrowEntry should accept a note field."""
    entry = RunArrowEntry(
        input_label="50 mg", output_label="32 mg, 62%",
        note="T3P (1.5 eq)",
    )
    assert entry.note == "T3P (1.5 eq)"


def test_run_arrow_entry_note_default():
    entry = RunArrowEntry(input_label="50 mg", output_label="32 mg")
    assert entry.note is None


def test_note_parsed_from_yaml(tmp_path):
    """Parse a YAML with note key → RunArrowEntry.note populated."""
    yaml_content = """
structures:
  sm:
    smiles: "Brc1ccccc1"
    label: "1"
  prod:
    smiles: "c1ccccc1"
    label: "2"
steps:
  - substrates: [sm]
    products: [prod]
    below_arrow:
      text: ["conditions"]
layout: linear
run_arrows:
  - step: 1
    runs:
      - input: "50 mg"
        output: "32 mg, 62%"
        note: "T3P (1.5 eq)"
      - input: "100 mg"
        output: "75 mg, 70%"
"""
    yaml_path = os.path.join(str(tmp_path), "test.yaml")
    with open(yaml_path, "w") as f:
        f.write(yaml_content)

    scheme = parse_yaml(yaml_path)
    assert len(scheme.run_arrows) == 1
    runs = scheme.run_arrows[0].runs
    assert len(runs) == 2
    assert runs[0].note == "T3P (1.5 eq)"
    assert runs[1].note is None


# ---------------------------------------------------------------------------
# build_merged_scheme_yaml_dict
# ---------------------------------------------------------------------------

def test_merged_parallel(tmp_path):
    """Two parallel reactions → single step, two run entries."""
    sp_a = _buchwald_species()
    sp_b = _buchwald_species(base_equiv="1.5")
    eln_a = {"sm_mass": "50 mg", "product_obtained": "32 mg",
             "product_yield": "62"}
    eln_b = {"sm_mass": "100 mg", "product_obtained": "75 mg",
             "product_yield": "70"}
    path_a = _write_json(tmp_path, "a.json", sp_a, eln_data=eln_a)
    path_b = _write_json(tmp_path, "b.json", sp_b, eln_data=eln_b)

    result = build_merged_scheme_yaml_dict([path_a, path_b])

    assert "steps" in result
    assert len(result["steps"]) == 1
    assert "run_arrows" in result
    runs = result["run_arrows"][0]["runs"]
    assert len(runs) == 2
    assert runs[0]["input"] == "50 mg"
    assert runs[1]["input"] == "100 mg"


def test_merged_sequential(tmp_path):
    """Two sequential reactions → two steps, sequential layout."""
    intermediate = "c1ccc(-n2cccc2)cc1"
    sp_a = _buchwald_species(dp_smi=intermediate)
    sp_b = _buchwald_species(sm_smi=intermediate,
                             dp_smi="c1cc(-n2cccc2)cc(Br)c1")
    path_a = _write_json(tmp_path, "a.json", sp_a)
    path_b = _write_json(tmp_path, "b.json", sp_b)

    result = build_merged_scheme_yaml_dict([path_a, path_b])

    assert result["layout"] == "sequential"
    assert len(result["steps"]) == 2


def test_single_json_backward_compat(tmp_path):
    """Single JSON → same behavior as write_scheme_yaml."""
    species = _buchwald_species()
    path = _write_json(tmp_path, "single.json", species)

    # Via write_scheme_yaml
    out_single = os.path.join(str(tmp_path), "single-scheme.yaml")
    write_scheme_yaml(path, out_single)

    # Via build_merged_scheme_yaml_dict with single input
    result = build_merged_scheme_yaml_dict([path])

    # Both should produce a linear single-step layout
    assert result["layout"] == "linear"
    assert len(result.get("steps", [])) == 1


# ---------------------------------------------------------------------------
# _merge_eln_labels
# ---------------------------------------------------------------------------

def test_merge_eln_labels_single():
    assert _merge_eln_labels(["KL-7001-004"]) == "KL-7001-004"


def test_merge_eln_labels_shared_prefix():
    result = _merge_eln_labels(["KL-7001-001", "KL-7001-003", "KL-7001-004"])
    assert result == "KL-7001-001/003/004"


def test_merge_eln_labels_different_prefix():
    result = _merge_eln_labels(["KL-7001-001", "KL-CC-002"])
    assert result == "KL-7001-001, KL-CC-002"


# ---------------------------------------------------------------------------
# ELN labels — single reaction
# ---------------------------------------------------------------------------

def test_eln_labels_single_reaction(tmp_path):
    """use_eln_labels=True → product labelled with experiment name."""
    species = _buchwald_species()
    data = {
        "version": "1.3",
        "experiment": "KL-7001-004",
        "input_files": {},
        "species": species,
        "conditions": [],
        "eln_data": {},
    }
    path = os.path.join(str(tmp_path), "rxn.json")
    with open(path, "w") as f:
        json.dump(data, f)

    result = build_scheme_yaml_dict(path, use_eln_labels=True)
    structs = result["structures"]

    # Product (sp_2) should have the experiment name as label
    dp_labels = [v["label"] for v in structs.values()
                 if v.get("label") == "KL-7001-004"]
    assert len(dp_labels) == 1

    # Substrate (sp_0) should NOT have a label
    sm_entry = structs.get("sp_0", {})
    assert "label" not in sm_entry


def test_eln_labels_default_off(tmp_path):
    """Default (no eln labels) → sequential numbers."""
    species = _buchwald_species()
    path = _write_json(tmp_path, "rxn.json", species)
    result = build_scheme_yaml_dict(path)
    labels = [v.get("label") for v in result["structures"].values()
              if v.get("label")]
    assert "1" in labels
    assert "2" in labels


# ---------------------------------------------------------------------------
# ELN labels — merged scheme
# ---------------------------------------------------------------------------

def test_eln_labels_merged_parallel(tmp_path):
    """Parallel merge with ELN labels → merged experiment names."""
    sp_a = _buchwald_species()
    sp_b = _buchwald_species(base_equiv="1.5")
    path_a = _write_json(tmp_path, "KL-7001-001.json", sp_a)
    path_b = _write_json(tmp_path, "KL-7001-003.json", sp_b)

    result = build_merged_scheme_yaml_dict(
        [path_a, path_b], use_eln_labels=True)

    # Find the product label
    labels = [v.get("label") for v in result["structures"].values()
              if v.get("label")]
    # Should contain merged ELN label
    assert any("KL-7001-001" in l and "003" in l for l in labels)


# ---------------------------------------------------------------------------
# Unrelated reactions as stacked rows
# ---------------------------------------------------------------------------

def test_unrelated_reactions_included(tmp_path):
    """Unrelated reactions should appear as their own stacked rows."""
    # Reaction 1: typical Buchwald
    sp_a = _buchwald_species(sm_smi="Brc1ccccc1", dp_smi="c1ccc(-n2cccc2)cc1")
    # Reaction 2: completely different (unrelated)
    sp_b = _buchwald_species(sm_smi="ClC1=CC=CC=C1F", dp_smi="FC1=CC=CC(O)=C1")
    path_a = _write_json(tmp_path, "a.json", sp_a)
    path_b = _write_json(tmp_path, "b.json", sp_b)

    result = build_merged_scheme_yaml_dict([path_a, path_b])

    # Should have sections (stacked-rows), not flat steps
    assert result["layout"] == "stacked-rows"
    assert "sections" in result
    assert len(result["sections"]) == 2


# ---------------------------------------------------------------------------
# Solvent-flagged species not used as SM
# ---------------------------------------------------------------------------

def test_solvent_not_overwrite_sm(tmp_path):
    """A species with is_sm=True but role_detail='solvent' should not
    overwrite the real SM SMILES."""
    species = [
        {"id": "sp_0", "smiles": "O=C1CCC(N2C(=O)c3cccc(O)c3C2=O)C(=O)N1",
         "name": "SM", "role": "product", "is_sm": True, "is_dp": True,
         "is_substrate": True, "source": "fragment"},
        {"id": "sp_1", "smiles": "C1CCOC1", "name": "SM",
         "role": "non_contributing", "role_detail": "solvent",
         "is_sm": True, "is_dp": False, "source": "text_label"},
    ]
    path = _write_json(tmp_path, "degenerate.json", species)
    s = _extract_reaction_summary(0, path)

    # SM should be the glutarimide, not THF
    assert s.sm_smiles == _canonicalize(
        "O=C1CCC(N2C(=O)c3cccc(O)c3C2=O)C(=O)N1")
    assert s.sm_smiles != _canonicalize("C1CCOC1")
    # DP should also be set (same molecule in this degenerate case)
    assert s.dp_smiles == s.sm_smiles
