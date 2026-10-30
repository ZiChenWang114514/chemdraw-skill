import pytest
from rdkit import Chem
from rdkit.Chem import rdDepictor

from cdxml_toolkit.chemistry_semantics import require_supported, validate_fragment


@pytest.mark.parametrize("smiles", ["[Mg]", "[Li]", "[Na]", "[Zn]", "[Cu]", "[Mg].[I][I]"])
def test_an_elemental_metal_is_not_a_radical(smiles):
    # "[Mg]" is magnesium metal (Grignard turnings); RDKit counts its free valences as radicals.
    require_supported(Chem.MolFromSmiles(smiles))


@pytest.mark.parametrize("smiles", ["[CH3]", "[O]", "C[CH2]", "CC[O]"])
def test_a_real_radical_is_still_refused(smiles):
    with pytest.raises(ValueError, match="unsupported_radical"):
        require_supported(Chem.MolFromSmiles(smiles))


def test_an_elemental_metal_survives_the_cdxml_round_trip():
    from cdxml_toolkit.image.structure_from_image import _rdkit_mol_to_atom_bond_dicts
    from cdxml_toolkit.render.renderer import _IDGen, _build_fragment

    mol = Chem.MolFromSmiles("[Mg]")
    rdDepictor.Compute2DCoords(mol)
    atoms, bonds = _rdkit_mol_to_atom_bond_dicts(mol)
    xml, _, _ = _build_fragment(atoms, bonds, _IDGen())
    assert validate_fragment("[Mg]", xml)["status"] == "preserved"
