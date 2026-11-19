"""Symmetric cores: all equally valid atom mappings are compared, not one picked."""
from __future__ import annotations

import xml.etree.ElementTree as ET

import pytest

from cdxml_toolkit.cdxml_builder import mol_to_cdxml
from cdxml_toolkit.chemistry_diff import structural_diff
from cdxml_toolkit.publication.update import replacement_fragment


@pytest.mark.parametrize("before, after", [
    ("c1ccccc1O", "c1ccccc1OC"),
    ("Oc1ccc(O)cc1", "COc1ccc(O)cc1"),
    ("c1ccccc1", "Cc1ccccc1"),
    ("Oc1ccccc1", "Oc1ccccc1C"),
])
def test_mappings_that_agree_give_a_completed_diff(before, after):
    result = structural_diff(before, after)
    assert result["status"] == "completed", result
    assert result["atom_mappings_considered"] >= 1
    assert len([c for c in result["bond_changes"] if c["kind"] == "added"]) == 1


@pytest.mark.parametrize("before, after", [("CO", "COCCO"), ("CCO", "CCOCC(C)O")])
def test_mappings_that_disagree_are_reported_as_ambiguous(before, after):
    result = structural_diff(before, after)
    assert (result["status"], result["reason"]) == ("partial", "ambiguous_atom_mapping")
    assert result["atom_mapping"] is None


def _fragment(smiles):
    text = mol_to_cdxml(smiles)
    root = ET.fromstring(text[text.index("<CDXML"):])
    return root, root.find(".//fragment")


def test_publication_update_accepts_a_symmetric_core_with_one_picture(tmp_path):
    root, fragment = _fragment("Cc1ccccc1")
    replacement_fragment(fragment, "CCc1ccccc1", None, str(tmp_path), root, "c1")


def test_publication_update_refuses_a_core_with_two_pictures(tmp_path):
    root, fragment = _fragment("Oc1ccccc1")
    with pytest.raises(ValueError, match="Symmetric core mapping"):
        replacement_fragment(fragment, "Oc1ccccc1C", None, str(tmp_path), root, "c1")
