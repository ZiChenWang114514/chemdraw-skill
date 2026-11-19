"""Reading a CDXML fragment must keep its chemistry (stereo, charge, isotope,
radical, bond order) and re-layout must not change it."""

import copy
import xml.etree.ElementTree as ET

import pytest

Chem = pytest.importorskip("rdkit.Chem")

from cdxml_toolkit.cdxml_builder import mol_to_cdxml
from cdxml_toolkit.chemistry_semantics import semantic_key
from cdxml_toolkit.rdkit_utils import cleanup_fragment_rdkit, frag_to_mol


def _fragment(smiles):
    root = ET.fromstring(mol_to_cdxml(smiles))
    return root.find(".//fragment")


def _key(smiles):
    return semantic_key(Chem.MolFromSmiles(smiles))


@pytest.mark.parametrize("smiles", [
    "C[C@H](N)C(=O)O",            # wedge-bearing stereocentre
    "C[C@@H](N)C(=O)O",
    "C[NH3+]",                     # ammonium
    "CC(=O)[O-]",                  # carboxylate
    "[2H]C([2H])([2H])O",          # deuterium
    "[13CH3]C(=O)O",               # carbon-13
    "c1ccccc1O",                   # aromatic ring
])
def test_frag_to_mol_keeps_chemistry(smiles):
    mol, atoms = frag_to_mol(_fragment(smiles))
    assert mol is not None
    assert semantic_key(mol) == _key(smiles)
    assert [a["idx"] for a in atoms] == list(range(mol.GetNumAtoms()))


def _hand_fragment(nodes, bonds):
    xml = "<fragment id=\"1\">"
    for nid, (x, y, attrs) in nodes.items():
        extra = "".join(f' {k}="{v}"' for k, v in attrs.items())
        xml += f'<n id="{nid}" p="{x} {y}"{extra}/>'
    for i, (b, e, attrs) in enumerate(bonds):
        extra = "".join(f' {k}="{v}"' for k, v in attrs.items())
        xml += f'<b id="{100 + i}" B="{b}" E="{e}"{extra}/>'
    return ET.fromstring(xml + "</fragment>")


def test_frag_to_mol_reads_radical():
    frag = _hand_fragment(
        {1: (0, 0, {}), 2: (14.4, 0, {"Radical": "Doublet"})},
        [(1, 2, {})],
    )
    mol, _ = frag_to_mol(frag)
    assert mol.GetAtomWithIdx(1).GetNumRadicalElectrons() == 1


def test_frag_to_mol_reads_aromatic_order():
    ring = {i + 1: (14.4 * x, 14.4 * y, {}) for i, (x, y) in enumerate(
        [(0, 0), (0.866, -0.5), (1.732, 0), (1.732, 1), (0.866, 1.5), (0, 1)])}
    bonds = [(i, i % 6 + 1, {"Order": "1.5"}) for i in range(1, 7)]
    mol, _ = frag_to_mol(_hand_fragment(ring, bonds))
    assert semantic_key(mol) == _key("c1ccccc1")


def test_frag_to_mol_reads_dative_order():
    frag = _hand_fragment(
        {1: (0, 0, {"Element": "7"}), 2: (14.4, 0, {"Element": "5"})},
        [(1, 2, {"Order": "dative"})],
    )
    mol, _ = frag_to_mol(frag)
    assert mol.GetBondWithIdx(0).GetBondType() == Chem.BondType.DATIVE


def test_atom_ids_map_to_indices():
    frag = _fragment("C[C@H](N)C(=O)O")
    mol, atoms = frag_to_mol(frag)
    nodes = frag.findall("n")
    for a in atoms:
        assert a["id"] == int(nodes[a["idx"]].get("id"))
        assert a["xml"] is nodes[a["idx"]]


def test_alignment_reader_is_the_shared_reader():
    from cdxml_toolkit.layout import alignment
    from cdxml_toolkit import rdkit_utils
    assert alignment._frag_to_mol is rdkit_utils.frag_to_mol


def _distort(frag):
    for i, n in enumerate(frag.findall("n")):
        x, y = (float(v) for v in n.get("p").split())
        n.set("p", f"{x + (i % 3) * 3.1:.3f} {y - (i % 2) * 2.7:.3f}")


@pytest.mark.parametrize("smiles", [
    "C[C@H](N)C(=O)O",
    "C[C@@H](O)CC[C@H](C)Cl",
    "C/C=C/C(=O)O",
])
def test_cleanup_preserves_stereo(smiles):
    frag = _fragment(smiles)
    _distort(frag)
    before = semantic_key(frag_to_mol(frag)[0])
    cleanup_fragment_rdkit(frag)
    assert semantic_key(frag_to_mol(frag)[0]) == before


def test_cleanup_with_mirrored_wedges_keeps_original_when_stereo_changes():
    # A wedge drawn so that the re-laid-out geometry and the old Display
    # attribute would describe the opposite enantiomer must not slip through.
    frag = _fragment("C[C@H](N)C(=O)O")
    for n in frag.findall("n"):
        x, y = (float(v) for v in n.get("p").split())
        n.set("p", f"{-x:.3f} {y:.3f}")   # mirror image: opposite configuration
    before = semantic_key(frag_to_mol(frag)[0])
    cleanup_fragment_rdkit(frag)
    assert semantic_key(frag_to_mol(frag)[0]) == before


def test_alignment_rewrite_keeps_target_stereo():
    from cdxml_toolkit.layout import alignment
    from cdxml_toolkit.rdkit_utils import (
        avg_bond_length_from_atoms, rdkit_default_bond_length, set_cdxml_conformer)
    ref_frag = _fragment("C[C@@H](N)C(=O)OC")
    tgt_frag = _fragment("C[C@H](N)C(=O)O")
    ref_mol, ref_atoms = frag_to_mol(ref_frag)
    tgt_mol, tgt_atoms = frag_to_mol(tgt_frag)
    before = semantic_key(tgt_mol)
    scale = rdkit_default_bond_length() / avg_bond_length_from_atoms(ref_atoms, ref_mol)
    set_cdxml_conformer(ref_mol, ref_atoms, scale)
    atom_map, _ = alignment._find_mcs_match(ref_mol, tgt_mol)
    alignment._rdkit_align_and_write(
        tgt_frag, ref_mol, tgt_mol, tgt_atoms, atom_map, scale, (0.0, 0.0))
    assert semantic_key(frag_to_mol(tgt_frag)[0]) == before
