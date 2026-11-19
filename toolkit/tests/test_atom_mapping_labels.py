"""Atom mapping keeps isotope labels and reads map numbers from the right atoms."""

import pytest

Chem = pytest.importorskip("rdkit.Chem")

from cdxml_toolkit import atom_mapping

M = Chem.MolFromSmiles


def _isotopes(mols):
    return sorted((a.GetSymbol(), a.GetIsotope()) for m in mols for a in m.GetAtoms() if a.GetIsotope())


C13 = ([("ester", M("[13CH3]C(=O)OC"))], [("acid", M("[13CH3]C(=O)O")), ("methane", M("C"))])
D3 = ([("ester", M("[2H]C([2H])([2H])OC(C)=O")), ("water", M("O"))],
      [("alcohol", M("[2H]C([2H])([2H])O")), ("acid", M("CC(=O)O"))])


@pytest.mark.parametrize("left,right", [C13, D3])
def test_mcs_mapping_keeps_isotopes(left, right):
    result = atom_mapping.map_atoms(left, right, method="mcs")
    assert _isotopes(result["left_mapped"]) == _isotopes(m for _, m in left)
    assert _isotopes(result["right_mapped"]) == _isotopes(m for _, m in right)


@pytest.mark.parametrize("left,right,mapped", [
    (*C13, "[13CH3:1][C:2](=[O:3])[O:4][CH3:5]>>[13CH3:1][C:2](=[O:3])[OH:4].[CH4:5]"),
    (*D3, "[2H:1][C:2]([2H:3])([2H:4])[O:5][C:6]([CH3:7])=[O:8].[OH2:9]>>"
          "[2H:1][C:2]([2H:3])([2H:4])[OH:5].[CH3:7][C:6](=[O:8])[OH:9]"),
])
def test_learned_mapper_output_with_isotopes_is_read(left, right, mapped):
    mapper = atom_mapping._Mapper(left, right)
    p2l, skipped = atom_mapping._from_mapped_smiles(mapper, mapped)
    assert skipped == 0
    assert len(p2l) == mapper.right.size
    for p, l in p2l.items():
        assert mapper.right.element[p] == mapper.left.element[l]
    result = atom_mapping._describe(mapper, p2l, {}, False, "rxnmapper")
    assert _isotopes(result["right_mapped"]) == _isotopes(m for _, m in right)


def test_map_numbers_read_after_hydrogen_removal():
    # Explicit hydrogens written before the heavy atoms shift atom indices.
    left, right = [("a", M("CCO"))], [("b", M("CC=O"))]
    mapper = atom_mapping._Mapper(left, right)
    p2l, _ = atom_mapping._from_mapped_smiles(
        mapper, "[H][C:1]([H])([H])[C:2]([H])([H])[O:3][H]>>[H][C:1]([H])([H])[C:2]([H])=[O:3]")
    pairs = {(mapper.right.element[p], mapper.right.local[p]): (mapper.left.element[l], mapper.left.local[l])
             for p, l in p2l.items()}
    assert pairs == {("C", 0): ("C", 0), ("C", 1): ("C", 1), ("O", 2): ("O", 2)}


def test_claisen_rearrangement_maps():
    result = atom_mapping.map_atoms([("allyl vinyl ether", M("C=CCOC=C"))],
                                    [("aldehyde", M("C=CCCC=O"))], method="mcs")
    assert result["status"] in ("complete", "ambiguous")
    assert len(result["map"]) + sum(len(e["candidates"]) > 0 for e in result["ambiguous"]) == 6
