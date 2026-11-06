"""Regression tests for draw_figure decorations and condition-label subscripts."""

from __future__ import annotations

import xml.etree.ElementTree as ET

import pytest

from cdxml_toolkit.mcp_runtime import figure_draw
from cdxml_toolkit.text_formatting import build_formatted_s_xml, needs_subscript

# Methanol drawn with an explicit H node first and O before C: CDXML node order
# (H, O, C) differs from the species SMILES "CO" order (C, O).
_SWAPPED = """<?xml version="1.0" encoding="UTF-8" ?>
<CDXML><colortable><color r="1" g="1" b="1"/><color r="0" g="0" b="0"/></colortable>
<page id="1">
<fragment id="10">
<n id="11" p="100 100" Element="1"/>
<n id="12" p="114.4 100" Element="8"/>
<n id="13" p="128.8 100"/>
<b id="14" B="11" E="12"/><b id="15" B="12" E="13"/>
</fragment>
<fragment id="20">
<n id="21" p="200 100" Element="1"/>
<n id="22" p="214.4 100" Element="8"/>
<n id="23" p="228.8 100"/>
<b id="24" B="21" E="22"/><b id="25" B="22" E="23"/>
</fragment>
</page></CDXML>"""


def _halo_centers(cdxml: str) -> list[str]:
    page = ET.fromstring(str(cdxml).split("?>", 1)[-1]).find("page")
    return [g.get("Center3D") for g in page.findall('graphic[@OvalType="Circle Filled"]')]


def test_atom_halo_maps_smiles_index_through_substructure_match():
    brief = {"species": [{"id": "M", "smiles": "CO", "atom_halos": [{"atoms": [0]}]}]}
    grounded = [{"id": "M", "smiles": "CO"}]
    centers = _halo_centers(figure_draw._apply_decorations(_SWAPPED, brief, grounded))
    # Atom 0 of "CO" is the carbon, drawn at x=128.8 (third node), in both fragments.
    assert centers[0].startswith("128.80 100.00")


def test_species_sharing_a_structure_each_get_their_own_decorations():
    brief = {"species": [
        {"id": "M1", "smiles": "CO", "atom_halos": [{"atoms": [0]}]},
        {"id": "M2", "smiles": "OC", "atom_halos": [{"atoms": [0]}]},
    ]}
    grounded = [{"id": "M1", "smiles": "CO"}, {"id": "M2", "smiles": "OC"}]
    centers = _halo_centers(figure_draw._apply_decorations(_SWAPPED, brief, grounded))
    # M1 atom 0 = C of the first fragment; M2 atom 0 = O of the second fragment.
    assert sorted(c.split()[0] for c in centers) == ["128.80", "214.40"]


def test_unmatched_fragment_fails_loudly(monkeypatch):
    brief = {"species": [{"id": "M", "smiles": "CO", "atom_halos": [{"atoms": [0]}]}]}
    grounded = [{"id": "M", "smiles": "CO"}]
    monkeypatch.setattr(figure_draw, "semantic_key", lambda mol: "same")
    from rdkit import Chem
    monkeypatch.setattr(figure_draw, "read_fragments",
                        lambda c: [("10", _with_coords("CCl"))])
    with pytest.raises(ValueError, match="does not match"):
        figure_draw._apply_decorations(_SWAPPED, brief, grounded)


def test_species_ts_bracket_uses_fresh_ids_and_atom_ids():
    brief = {"species": [{"id": "M", "smiles": "CO", "ts_bracket": True}]}
    out = str(figure_draw._apply_decorations(_SWAPPED, brief, [{"id": "M", "smiles": "CO"}]))
    page = ET.fromstring(out.split("?>", 1)[-1]).find("page")
    group = page.findall("bracketedgroup")
    assert len(group) == 2  # both drawings of the species
    assert group[0].get("BracketedObjectIDs") == "11 12 13"
    new_ids = [int(el.get("id")) for el in page.iter() if el.tag in ("graphic", "bracketedgroup", "t")]
    assert min(new_ids) == 26


def test_step_ts_bracket_true_is_rejected():
    brief = {"species": [{"id": "M", "smiles": "CO"}], "steps": [{"products": ["M"], "ts_bracket": True}]}
    with pytest.raises(ValueError, match="species id"):
        figure_draw._apply_decorations(_SWAPPED, brief, [{"id": "M", "smiles": "CO"}])
    brief["steps"][0]["ts_bracket"] = "M"
    out = str(figure_draw._apply_decorations(_SWAPPED, brief, [{"id": "M", "smiles": "CO"}]))
    assert "bracketedgroup" in out


@pytest.mark.parametrize("label", ["L1 (15 mol%)", "L2", "P1, CuI", "cat. 3"])
def test_ligand_labels_are_not_subscripted(label):
    xml = build_formatted_s_xml(label)
    assert 'face="32"' not in xml
    # The formula face (96) would make ChemDraw subscript the digit itself.
    token = label.split()[0].rstrip(",")
    if token[0].isupper() and token[1:].isdigit():
        assert f'face="0">{token}</s>' in xml


@pytest.mark.parametrize("formula,digits", [
    ("H2O", "2"), ("Et3N", "3"), ("NiBr2", "2"), ("CO2Me", "2"), ("K2CO3", "2"), ("H2, Pd/C", "2"),
])
def test_formula_digits_stay_subscripted(formula, digits):
    assert needs_subscript(formula)
    assert f'face="32">{digits}</s>' in build_formatted_s_xml(formula)


def test_draw_figure_condition_with_ligand_label(monkeypatch, tmp_path):
    monkeypatch.setenv("CHEMDRAW_OFFLINE", "1")
    brief = {
        "species": [{"id": "A", "smiles": "Brc1ccccc1"}, {"id": "B", "smiles": "c1ccccc1"}],
        "steps": [{"substrates": ["A"], "products": ["B"], "above": ["NiBr2, L1 (15 mol%)"]}],
    }
    out = tmp_path / "s.cdxml"
    figure_draw.draw_figure(brief, output_path=str(out))
    runs = [(s.get("face"), s.text) for s in ET.parse(out).getroot().iter("s")]
    assert ("32", "2") in runs
    assert ("0", "L1") in runs
    assert all(not (face == "96" and "L1" in (text or "")) for face, text in runs)


def _with_coords(smiles):
    from rdkit import Chem
    from rdkit.Chem import AllChem

    mol = Chem.MolFromSmiles(smiles)
    AllChem.Compute2DCoords(mol)
    return mol
