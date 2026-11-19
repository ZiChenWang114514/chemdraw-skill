"""build_reaction_cdxml: condition text placement and the shared arrow builder."""
from __future__ import annotations

import xml.etree.ElementTree as ET

from cdxml_toolkit import cdxml_builder
from cdxml_toolkit.cdxml_builder import build_reaction_cdxml, mol_to_atom_bond_dicts
from cdxml_toolkit.render import renderer


def _mol(smiles, dx):
    atoms, bonds = mol_to_atom_bond_dicts(smiles, center_x=dx, center_y=300.0)
    return {"atoms": atoms, "bonds": bonds}


def _root(conditions):
    cdxml = build_reaction_cdxml([_mol("CCO", 100.0)], [_mol("CC=O", 300.0)], conditions)
    return ET.fromstring(cdxml[cdxml.index("<CDXML"):])


def _text_boxes(root):
    return {t.get("id"): [float(v) for v in t.get("BoundingBox").split()] for t in root.iter("t")}


def test_several_lines_above_the_arrow_stack_upward():
    root = _root({"above": ["Pd2(dba)3 (5 mol%)", "BINAP (10 mol%)", "Cs2CO3"],
                  "below": ["dioxane", "100 °C, 24 h"]})
    arrow_y = float(root.find(".//arrow").get("Tail3D").split()[1])
    step = root.find(".//step")
    boxes = _text_boxes(root)
    above = boxes[step.get("ReactionStepObjectsAboveArrow")]
    below = boxes[step.get("ReactionStepObjectsBelowArrow")]
    assert above[3] < arrow_y < below[1]
    above_t = next(t for t in root.iter("t") if t.get("id") == step.get("ReactionStepObjectsAboveArrow"))
    first_baseline = float(above_t.get("p").split()[1])
    assert first_baseline + 2 * renderer._LINE_ADVANCE < arrow_y


def test_condition_formulas_are_subscripted():
    root = _root({"above": ["Cs2CO3"]})
    faces = [s.get("face") for s in root.iter("s")]
    assert "32" in faces


def test_the_builder_has_no_arrow_or_page_of_its_own():
    assert not hasattr(cdxml_builder, "_build_arrow")
    assert not hasattr(cdxml_builder, "_PAGE_OPEN")
    root = _root({})
    page = root.find("page")
    assert float(page.get("Width")) < 1620
