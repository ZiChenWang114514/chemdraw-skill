"""A multi-component recognition result never loses components silently."""

import pytest

pytest.importorskip("rdkit")

from cdxml_toolkit.image import reaction_from_image, structure_from_image
from cdxml_toolkit.image.components import split_components


def test_salt_lists_counter_ion():
    split = split_components("[Cl-].C[NH3+]")
    assert split["main"] == "C[NH3+]" or split["main"] == "[Cl-]"
    assert split["main"] == "C[NH3+]"
    assert split["dropped_components"] == ["[Cl-]"]
    assert split["smiles"] == "[Cl-].C[NH3+]"
    assert split["warning"]


def test_heavy_atoms_counted_by_rdkit():
    # "Cl" and "Br" are one heavy atom each, not two upper-case letters.
    split = split_components("ClCBr.CCCC")
    assert split["main"] == "CCCC"
    assert split["dropped_components"] == ["ClCBr"]


def test_single_component_untouched():
    split = split_components("c1ccccc1")
    assert split == {"smiles": "c1ccccc1", "main": "c1ccccc1", "dropped_components": [], "warning": None}


def test_structure_results_record_dropped_components():
    smiles = "CC(=O)[O-].[Na+]"
    entry = {"smiles": smiles,
             "atoms": [{"index": 1, "symbol": "C", "x": 0.0, "y": 0.0}], "bonds": []}
    structure_from_image.results_to_cdxml([entry])
    assert entry["smiles"] == smiles
    assert entry["dropped_components"] == ["[Na+]"]
    assert any("[Na+]" in w for w in entry["warnings"])


def test_no_private_component_pickers_left():
    assert not hasattr(structure_from_image, "_best_smiles_component")
    assert not hasattr(reaction_from_image, "_best_smiles_component")
