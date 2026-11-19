"""Sequential merge: the shared intermediate is the linked product, not the first product."""
from __future__ import annotations

from rdkit import Chem

from cdxml_toolkit.cdxml_builder import build_reaction_cdxml, mol_to_atom_bond_dicts
from cdxml_toolkit.layout import scheme_merger
from cdxml_toolkit.rdkit_utils import frag_to_smiles


def _mol(smiles, x):
    atoms, bonds = mol_to_atom_bond_dicts(smiles, center_x=x, center_y=300.0)
    return {"atoms": atoms, "bonds": bonds}


def _write(path, reactants, products):
    mols = [_mol(s, 100.0 + 120 * i) for i, s in enumerate(reactants)]
    prods = [_mol(s, 400.0 + 120 * i) for i, s in enumerate(products)]
    path.write_text(build_reaction_cdxml(mols, prods, {"above": ["reagent"]}), encoding="utf-8")
    return str(path)


def _canon(smiles):
    return Chem.MolToSmiles(Chem.MolFromSmiles(smiles))


def test_second_step_starts_from_the_linked_product(tmp_path):
    # Step 1 gives a by-product first and the intermediate second.
    first = _write(tmp_path / "s1.cdxml", ["c1ccccc1C(=O)O"], ["O", "c1ccccc1C(=O)OC"])
    second = _write(tmp_path / "s2.cdxml", ["c1ccccc1C(=O)OC"], ["c1ccccc1CO"])
    schemes = [scheme_merger.parse_scheme(first), scheme_merger.parse_scheme(second)]

    root = scheme_merger.sequential_merge(schemes).getroot()

    page = root.find("page")
    by_id = {el.get("id"): el for el in page.iter() if el.get("id")}
    steps = list(root.iter("step"))
    assert len(steps) == 2
    reactants = steps[1].get("ReactionStepReactants").split()
    smiles = {_canon(frag_to_smiles(by_id[r])) for r in reactants}
    assert _canon("c1ccccc1C(=O)OC") in smiles
    assert _canon("O") not in smiles
