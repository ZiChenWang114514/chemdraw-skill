"""The RDKit fallback renderer draws the molecule as drawn: not mirrored, same stereo."""

import pytest

Chem = pytest.importorskip("rdkit.Chem")

from cdxml_toolkit.cdxml_builder import build_molecule_cdxml, mol_to_cdxml
from cdxml_toolkit.chemdraw.cdxml_to_image_rdkit import cdxml_to_image_rdkit, cdxml_to_rdkit_mol
from cdxml_toolkit.chemistry_semantics import semantic_key


def _write(tmp_path, text, name="m.cdxml"):
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return str(path)


def test_atom_drawn_on_top_renders_on_top(tmp_path):
    # Oxygen drawn above the carbon: smaller CDXML y.
    atoms = [
        {"index": 1, "symbol": "C", "x": 100.0, "y": 120.0},
        {"index": 2, "symbol": "O", "x": 100.0, "y": 105.6},
    ]
    bonds = [{"index": 1, "order": 1, "atom1": 1, "atom2": 2}]
    mol = cdxml_to_rdkit_mol(_write(tmp_path, build_molecule_cdxml(atoms, bonds)))
    conf = mol.GetConformer()
    o = next(a.GetIdx() for a in mol.GetAtoms() if a.GetSymbol() == "O")
    c = next(a.GetIdx() for a in mol.GetAtoms() if a.GetSymbol() == "C")
    assert conf.GetAtomPosition(o).y > conf.GetAtomPosition(c).y


@pytest.mark.parametrize("smiles", ["C[C@H](N)C(=O)O", "C[C@@H](N)C(=O)O", "C[NH3+].[Cl-]"])
def test_rendered_conformer_keeps_source_stereo(tmp_path, smiles):
    mol = cdxml_to_rdkit_mol(_write(tmp_path, mol_to_cdxml(smiles)))
    assert semantic_key(mol) == semantic_key(Chem.MolFromSmiles(smiles))
    # Stereo re-derived from the rendered 2D conformer alone must agree.
    rederived = Chem.Mol(mol)
    Chem.WedgeMolBonds(rederived, rederived.GetConformer())
    for atom in rederived.GetAtoms():
        atom.SetChiralTag(Chem.ChiralType.CHI_UNSPECIFIED)
    Chem.AssignChiralTypesFromBondDirs(rederived)
    Chem.AssignStereochemistry(rederived, cleanIt=True, force=True)
    assert Chem.MolToSmiles(rederived) == Chem.MolToSmiles(Chem.MolFromSmiles(smiles))


def test_svg_output_written(tmp_path):
    out = cdxml_to_image_rdkit(_write(tmp_path, mol_to_cdxml("CCO")), str(tmp_path / "m.svg"))
    assert "<svg" in (tmp_path / "m.svg").read_text(encoding="utf-8")
    assert out.endswith("m.svg")


def test_reaction_rejected(tmp_path):
    text = mol_to_cdxml("CCO").replace("</page>", '<arrow id="9999" Head3D="1 1 0" Tail3D="0 0 0"/></page>')
    with pytest.raises(ValueError, match="Reaction scheme"):
        cdxml_to_rdkit_mol(_write(tmp_path, text))
