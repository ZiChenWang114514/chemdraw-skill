"""Unit tests for vision/stereo_audit.py, upgraded rdkit_workbench and compose_chemical_figure,
dummy-atom canonical comparison in chemistry_compare.py, and AbbreviationMismatch in consensus.py.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest import mock
import xml.etree.ElementTree as ET

import numpy as np
import pytest
from PIL import Image
from rdkit import Chem
from rdkit.Chem import Draw, rdDepictor

from cdxml_toolkit.engines import consensus, envelope
from cdxml_toolkit.engines.registry import ENGINES
from cdxml_toolkit.mcp_runtime import chemistry_compare
from cdxml_toolkit.mcp_runtime.figure_tools import compose_chemical_figure, rdkit_workbench
from cdxml_toolkit.vision import stereo_audit


STEROID = "C[C@]12CC[C@H]3[C@@H](CC=C4C[C@@H](O)CC[C@@]43C)[C@@H]1CC[C@@H]2O"


def _same_inchi(a: str, b: str) -> bool:
    ma = Chem.MolFromSmiles(a)
    mb = Chem.MolFromSmiles(b)
    assert ma is not None and mb is not None
    return Chem.MolToInchiKey(ma) == Chem.MolToInchiKey(mb)


def _drawn_mol(smiles: str) -> Chem.Mol:
    mol = Chem.MolFromSmiles(smiles)
    rdDepictor.Compute2DCoords(mol)
    Chem.WedgeMolBonds(mol, mol.GetConformer())
    return mol


def _molscribe_reading(mol: Chem.Mol, scale: float = 40.0) -> dict:
    conf = mol.GetConformer()
    atoms = [
        {
            "symbol": a.GetSymbol(),
            "x": 200.0 + scale * conf.GetAtomPosition(a.GetIdx()).x,
            "y": 200.0 - scale * conf.GetAtomPosition(a.GetIdx()).y,
            "confidence": 0.92,
        }
        for a in mol.GetAtoms()
    ]
    kinds = {
        Chem.BondDir.BEGINWEDGE: "solid wedge",
        Chem.BondDir.BEGINDASH: "dashed wedge",
    }
    order_names = {
        Chem.BondType.SINGLE: "single",
        Chem.BondType.DOUBLE: "double",
        Chem.BondType.TRIPLE: "triple",
        Chem.BondType.AROMATIC: "aromatic",
    }
    bonds = [
        {
            "type": kinds.get(b.GetBondDir(), order_names.get(b.GetBondType(), "single")),
            "atoms": [b.GetBeginAtomIdx(), b.GetEndAtomIdx()],
            "confidence": 0.95,
        }
        for b in mol.GetBonds()
    ]
    return {
        "ok": True,
        "smiles": Chem.MolToSmiles(mol),
        "confidence": 0.92,
        "atoms": atoms,
        "bonds": bonds,
        "molfile": Chem.MolToMolBlock(mol),
    }


# ---------------------------------------------------------------------------
# 1. stereo_audit: stereo_from_wedges, transfer_stereo, read_wedges, depict_like,
#    snap_with, audit_stereo_wedges, render_diff_overlay
# ---------------------------------------------------------------------------


def test_stereo_from_wedges_atoms_bonds_and_mapped_smiles():
    mol = _drawn_mol("C[C@H](N)C(=O)O")
    reading = _molscribe_reading(mol)
    res = stereo_audit.stereo_from_wedges(reading["atoms"], reading["bonds"], flip_y=True)
    assert _same_inchi(res["smiles"], "C[C@H](N)C(=O)O")
    assert 1 in res and res[1][0] == "S"
    assert res[1][1] == pytest.approx(0.95)

    # Mapped SMILES mode
    s_up = stereo_audit.stereo_from_wedges(
        "[NH2:2][CH:1]([CH3:3])[C:4](=O)O",
        {1: {2: (-1, 0.5, "plain"), 4: (1, 0.5, "plain"), 3: (0, -1, "wedge")}},
    )
    s_down = stereo_audit.stereo_from_wedges(
        "[NH2:2][CH:1]([CH3:3])[C:4](=O)O",
        {1: {2: (-1, 0.5, "plain"), 4: (1, 0.5, "plain"), 3: (0, -1, "hash")}},
    )
    assert not _same_inchi(s_up, s_down)


def test_transfer_stereo_handles_permutation_parity_and_substituent_mismatch():
    truth = "C[C@H]1CC[C@]2([C@H]([C@]1(C)CO)CCC=C2C)C"
    src_with_wedges = "C[C@H]1CC[C@]2([C@H]([C@]1(C)CC)CCC=C2C)C"
    dst_skeleton = "CC1CCC2(C(C1(C)CO)CCC=C2C)C"

    res = stereo_audit.transfer_stereo(src_with_wedges, dst_skeleton)
    assert _same_inchi(res["smiles"], truth)
    assert all(c["status"] == "copied" for c in res["centers"])

    # Also test Mol inputs and atom-order independence
    res2 = stereo_audit.transfer_stereo(
        Chem.MolFromSmiles("C[C@H](N)C(=O)O"),
        Chem.MolFromSmiles("OC(=O)C(C)N"),
    )
    assert _same_inchi(res2["smiles"], "C[C@H](N)C(=O)O")


def test_read_wedges_computes_2d_coords_and_handles_compass_h():
    flat_ala = "CC(N)C(=O)O"
    res_wedge = stereo_audit.read_wedges(flat_ala, [{"atom": 1, "neighbor": 0, "kind": "wedge"}])
    res_hash = stereo_audit.read_wedges(flat_ala, [{"atom": 1, "neighbor": 0, "kind": "hash"}])
    assert res_wedge["smiles"] != res_hash["smiles"]
    assert res_wedge["cip_labels"][1] in ("R", "S")
    assert res_hash["cip_labels"][1] in ("R", "S")
    assert res_wedge["cip_labels"][1] != res_hash["cip_labels"][1]

    # Explicit H with h_at compass direction
    pos = {0: (0.0, -1.0), 1: (0.0, 0.0), 2: (-1.0, 0.6), 3: (1.0, 0.6)}
    h_w, cips_w = stereo_audit.read_wedges(
        "C[CH](N)C(=O)O",
        [{"atom": 1, "neighbor": "H", "kind": "wedge", "h_at": "up-left"}],
        positions=[pos],
    )
    h_h, cips_h = stereo_audit.read_wedges(
        "C[CH](N)C(=O)O",
        [{"atom": 1, "neighbor": "H", "kind": "hash", "h_at": "up-left"}],
        positions=[pos],
    )
    assert not _same_inchi(h_w, h_h)
    assert cips_w[1] != cips_h[1]


def test_depict_like_matches_orientation_and_writes_side_by_side(tmp_path: Path):
    mol = Chem.MolFromSmiles(STEROID)
    rdDepictor.SetPreferCoordGen(True)
    rdDepictor.Compute2DCoords(mol)
    base = mol.GetConformer().GetPositions()[:, :2]
    ref = Chem.Mol(mol)
    xy_ref = base @ np.array([[0, -1], [1, 0]]).T
    xy_ref[:, 0] *= -1
    for i, (x, y) in enumerate(xy_ref):
        ref.GetConformer().SetAtomPosition(i, (float(x), float(y), 0.0))
    ref_path = tmp_path / "ref_steroid.png"
    Draw.MolToImage(ref, size=(400, 400)).save(ref_path)

    _, xy = stereo_audit.depict_like(STEROID, ref_path, coords=True)

    def _norm(p):
        p = p - p.mean(0)
        return p / np.abs(p).max()

    assert np.abs(_norm(xy) - _norm(xy_ref)).max() < 1e-6

    out_path = tmp_path / "review_side_by_side.png"
    dep_res = stereo_audit.depict_like(STEROID, ref_path, output_path=out_path, annotate_indices=True)
    assert out_path.is_file()
    assert dep_res["ok"] is True
    assert dep_res["width"] > 400


def test_snap_with_audit_stereo_wedges_and_render_diff_overlay(tmp_path: Path):
    from rdkit.Chem.Draw import rdMolDraw2D

    mol = _drawn_mol(STEROID)
    d = rdMolDraw2D.MolDraw2DCairo(400, 400)
    d.drawOptions().padding = 0.1
    rdMolDraw2D.PrepareAndDrawMolecule(d, mol)
    d.FinishDrawing()
    img_path = tmp_path / "steroid.png"
    img_path.write_bytes(d.GetDrawingText())

    reading = _molscribe_reading(mol)
    true_xy = []
    for i, a in enumerate(reading["atoms"]):
        p = d.GetDrawCoords(i)
        true_xy.append([p.x, p.y])
        a["x"] = 200.0 + 1.15 * (p.x - 200.0)
        a["y"] = 200.0 + 1.10 * (p.y - 200.0)
    true_xy_arr = np.array(true_xy, dtype=float)

    snapped = stereo_audit.snap_with(img_path, reading["atoms"], reading["bonds"])
    snapped_arr = np.asarray(snapped)
    assert np.median(np.hypot(*(snapped_arr - true_xy_arr).T)) < 4.0

    # Flip one chiral center in candidate SMILES to trigger a conflict
    bad_mol = Chem.Mol(mol)
    first_chiral = next(a.GetIdx() for a in bad_mol.GetAtoms() if a.GetChiralTag() != Chem.ChiralType.CHI_UNSPECIFIED)
    bad_mol.GetAtomWithIdx(first_chiral).InvertChirality()
    cand_smiles = Chem.MolToSmiles(bad_mol)

    audit_res = stereo_audit.audit_stereo_wedges(cand_smiles, reading, image_path=img_path)
    assert audit_res["status"] == "conflict"
    assert len(audit_res["conflicts"]) == 1
    assert len(audit_res["agreed"]) == 6

    overlay_out = tmp_path / "diff_overlay.png"
    ov_res = stereo_audit.render_diff_overlay(img_path, cand_smiles, reading, output_path=overlay_out)
    assert overlay_out.is_file()
    assert ov_res["ok"] is True
    assert ov_res["patch_count"] == 1
    assert ov_res["width"] > 400


# ---------------------------------------------------------------------------
# 2. rdkit_workbench: edit_structure, read_wedges, enumerate_markush,
#    visual_checkpoints, diagnose_smiles_error
# ---------------------------------------------------------------------------


def test_rdkit_workbench_edit_structure_and_operations(tmp_path: Path):
    # 1. set_atom (C=C1CCCCC1 -> O=C1CCCCC1)
    res_atom = rdkit_workbench(
        [{"smiles": "C=C1CCCCC1"}],
        operation="edit_structure",
        options={"set_atom": [{"atom": 0, "element": "O", "charge": 0, "h": None}]},
        output_path=str(tmp_path / "edit_atom.json"),
    )
    assert res_atom["ok"] is True
    assert Chem.CanonSmiles(res_atom["results"][0]["canonical_smiles"]) == "O=C1CCCCC1"

    # 2. set_bond (cyclize hexane -> cyclohexane)
    res_bond = rdkit_workbench(
        [{"smiles": "CCCCCC"}],
        operation="edit_structure",
        options={"set_bond": [{"atoms": [0, 5], "order": 1}]},
        output_path=str(tmp_path / "edit_bond.json"),
    )
    assert res_bond["results"][0]["canonical_smiles"] == "C1CCCCC1"

    # 3. add_group & remove_atoms (convert TMS to TBS)
    tms = "CO[Si](C)(C)C"
    res_grp = rdkit_workbench(
        [{"smiles": tms}],
        operation="edit_structure",
        options={
            "remove_atoms": [3],
            "add_group": [{"atom": 2, "smiles": "[*]C(C)(C)C"}],
        },
        output_path=str(tmp_path / "edit_group.json"),
    )
    assert Chem.CanonSmiles(res_grp["results"][0]["canonical_smiles"]) == Chem.CanonSmiles("CO[Si](C)(C)C(C)(C)C")
    assert any("TBS" in cp or "6 carbons" in cp for cp in res_grp["checkpoints"])

    # 4. set_ez (CC=CC -> Z and E)
    res_ez = rdkit_workbench(
        [{"smiles": "CC=CC"}],
        operation="edit_structure",
        options={"set_ez": [{"atoms": [1, 2], "geometry": "Z"}]},
        output_path=str(tmp_path / "edit_ez.json"),
    )
    assert Chem.CanonSmiles(res_ez["results"][0]["canonical_smiles"]) == Chem.CanonSmiles("C/C=C\\C")

    # 5. read_wedges via rdkit_workbench
    res_rw = rdkit_workbench(
        [{"smiles": "CC(N)C(=O)O"}],
        operation="read_wedges",
        options={"wedges": [{"atom": 1, "neighbor": 0, "kind": "wedge"}]},
        output_path=str(tmp_path / "rw.json"),
    )
    assert res_rw["ok"] is True
    assert "@" in res_rw["results"][0]["canonical_smiles"]
    assert res_rw["cip_labels"][1] in ("R", "S")

    # 6. enumerate_markush via rdkit_workbench
    res_mk = rdkit_workbench(
        [{"smiles": "[*:1]c1ccc([*:2])cc1"}],
        operation="enumerate_markush",
        options={
            "r_groups_by_label": {
                "5a": ["[*:1]F", "[*:2]C"],
                "5b": ["[*:1]Cl", "[*:2]OC"],
            }
        },
        output_path=str(tmp_path / "markush.json"),
    )
    assert res_mk["ok"] is True
    assert Chem.CanonSmiles(res_mk["products"]["5a"]) == Chem.CanonSmiles("Cc1ccc(F)cc1")
    assert Chem.CanonSmiles(res_mk["products"]["5b"]) == Chem.CanonSmiles("COc1ccc(Cl)cc1")


def test_visual_checkpoints_and_diagnose_smiles_error_in_workbench(tmp_path: Path):
    # Checkpoints for terminal =CH2, Si carbon count (TBS), and ortho/meta/para benzene
    smi = "C=C(C)c1ccc(O[Si](C)(C)C(C)(C)C)cc1"
    res = rdkit_workbench([{"smiles": smi}], operation="inspect", output_path=str(tmp_path / "inspect_cp.json"))
    cps = " | ".join(res["checkpoints"])
    assert "terminal =CH2" in cps
    assert "6 carbons" in cps and "TBS" in cps
    assert "para" in cps

    # Invalid SMILES returns diagnose_smiles_error details instead of bare "Invalid SMILES"
    bad_ring = rdkit_workbench([{"smiles": "C1CC(C"}])
    assert bad_ring["ok"] is False
    assert "ring-closure digit(s) opened but never closed: 1" in bad_ring["diagnosis"]
    assert "'(' at position 4 is never closed" in bad_ring["diagnosis"]

    diag_rad = stereo_audit.diagnose_smiles_error("[C]CC[N]")
    assert "[C], [N]" in diag_rad
    assert len(diag_rad["bare_bracket_radicals"]) == 2


# ---------------------------------------------------------------------------
# 3. compose_chemical_figure: ring_fills, filled highlight_atoms behind <fragment>,
#    multi_attachments, crossings without a template, and ts_bracket
# ---------------------------------------------------------------------------


def test_compose_figure_power_features_without_template(tmp_path: Path):
    manifest = {
        "objects": [
            {
                "id": "cat",
                "type": "molecule",
                "smiles": "[Fe].c1cc[cH-]c1",
                "position": [160, 140],
                "ring_fills": [{"ring_index": 0, "color": "#D6EAF8"}],
                "highlight_atoms": [1],
                "highlight_color": "#FADBD8",
                "multi_attachments": [
                    {"metal_atom": 0, "ligand_atoms": [1, 2, 3, 4, 5], "bond_display": "Dash"}
                ],
                "crossings": [{"front": [1, 2], "back": [3, 4]}],
            },
            {
                "id": "ts",
                "type": "ts_bracket",
                "start": [110, 90],
                "end": [210, 190],
            },
            {
                "id": "orb",
                "type": "orbital",
                "center": [160, 120],
                "orbital_type": "pShaded",
                "angle_deg": -90,
            },
            {
                "id": "bg_box",
                "type": "rectangle",
                "start": [90, 70],
                "end": [230, 210],
                "fill_type": "faded",
                "round_edge": True,
                "dashed": True,
                "background": True,
                "color": "#D5F5E3",
            },
        ]
    }
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    out_cdxml = tmp_path / "composed.cdxml"

    result = compose_chemical_figure(str(manifest_path), str(out_cdxml))
    assert result["ok"] is True
    assert out_cdxml.is_file()

    root = ET.parse(out_cdxml).getroot()
    page = root.find("page")
    assert page is not None

    children = list(page)
    frag_idx = next(i for i, el in enumerate(children) if el.tag == "fragment")
    before_frag = children[:frag_idx]

    # 1. Filled highlight_atoms oval is placed BEFORE <fragment> with Z="1" and OvalType="Circle Filled"
    halos = [
        el for el in before_frag
        if el.tag == "graphic" and el.get("GraphicType") == "Oval" and el.get("OvalType") == "Circle Filled"
    ]
    assert len(halos) == 1
    assert halos[0].get("Z") == "1"

    # 2. ring_fills <curve Closed="yes" FillType="Solid" LineType="None" Z="1"> placed BEFORE <fragment>
    ring_curves = [
        el for el in before_frag
        if el.tag == "curve" and el.get("Closed") == "yes" and el.get("FillType") == "Solid" and el.get("LineType") == "None"
    ]
    assert len(ring_curves) == 1
    assert ring_curves[0].get("Z") == "1"

    # 3. Background rectangle with fill_type, round_edge, dashed, and Z="1" before <fragment>
    rects = [el for el in before_frag if el.tag == "graphic" and el.get("GraphicType") == "Rectangle"]
    assert len(rects) == 1
    assert rects[0].get("FillType") == "Faded"
    assert rects[0].get("RectangleType") == "RoundEdge"
    assert rects[0].get("LineType") == "Dashed"
    assert rects[0].get("Z") == "1"

    # 4. MultiAttachment node and coordination bond inside <fragment>
    frag = children[frag_idx]
    ma_nodes = frag.findall('n[@NodeType="MultiAttachment"]')
    assert len(ma_nodes) == 1
    assert len(ma_nodes[0].get("Attachments", "").split()) == 5
    ma_id = ma_nodes[0].get("id")
    coord_bonds = [b for b in frag.findall("b") if b.get("E") == ma_id]
    assert len(coord_bonds) == 1
    assert coord_bonds[0].get("Display") == "Dash"

    # 5. Crossings resolved on fresh molecule without template
    crossing_bonds = [b for b in frag.findall("b") if b.get("CrossingBonds")]
    assert len(crossing_bonds) == 2

    # 6. ts_bracket (GraphicType="Bracket" BracketType="Square" LipSize="5" + double dagger \u2021)
    brackets = page.findall('graphic[@GraphicType="Bracket"]')
    assert len(brackets) == 2
    assert all(b.get("BracketType") == "Square" and b.get("LipSize") == "5" for b in brackets)
    texts = "".join("".join(t.itertext()) for t in page.findall("t"))
    assert "\u2021" in texts

    # 7. Orbital graphic
    orbitals = page.findall('graphic[@GraphicType="Orbital"]')
    assert len(orbitals) == 1


# ---------------------------------------------------------------------------
# 4. Dummy-atom [*:1] vs [*:2] distinction in chemistry_compare.py and
#    AbbreviationMismatch in consensus.py
# ---------------------------------------------------------------------------


def test_chemistry_compare_preserves_dummy_atom_numbering():
    class _FakeBridge:
        def __init__(self, mapping):
            self.mapping = mapping

        def get_info(self, src):
            return dict(self.mapping[src])

        def close(self):
            pass

    # Even if ChemScript returns the same stripped InChI for two positional [*:1]/[*:2] isomers,
    # chemistry_compare must distinguish [*:1] vs [*:2] via isotope-mapped canonical SMILES.
    shared_inchi = "InChI=1S/C6H4O/c7-6-4-2-1-3-5-6/h1-4,7H"
    fake = _FakeBridge(
        {
            "isomer_a": {
                "ok": True,
                "type": "structure",
                "smiles": "[*:1]c1ccc(O)c([*:2])c1",
                "inchi": shared_inchi,
                "formula": "C6H4O",
                "atom_count": 9,
                "bond_count": 9,
            },
            "isomer_b": {
                "ok": True,
                "type": "structure",
                "smiles": "[*:2]c1ccc(O)c([*:1])c1",
                "inchi": shared_inchi,
                "formula": "C6H4O",
                "atom_count": 9,
                "bond_count": 9,
            },
            "isomer_a_iso": {
                "ok": True,
                "type": "structure",
                "smiles": "[1*]c1ccc(O)c([2*])c1",
                "inchi": shared_inchi,
                "formula": "C6H4O",
                "atom_count": 9,
                "bond_count": 9,
            },
        }
    )
    with mock.patch.object(chemistry_compare, "_bridge_factory", return_value=fake):
        diff_res = chemistry_compare.compare_molecules("isomer_a", "isomer_b")
        same_res = chemistry_compare.compare_molecules("isomer_a", "isomer_a_iso")

    assert diff_res["outputs"]["exact_match"] is False
    assert same_res["outputs"]["exact_match"] is True


def test_consensus_abbreviation_mismatch_detection():
    # Engine 1 expands OTBS on a bromo-phenethyl alcohol scaffold; Engine 2 misreads OTBS as [Ti]O
    expanded_otbs = "CC(C)(C)[Si](C)(C)OCCc1ccc(Br)cc1"
    misread_ti = "[Ti]OCCc1ccc(Br)cc1"

    assert consensus._check_abbreviation_skeleton_match(expanded_otbs, misread_ti) is True
    assert consensus._chemistry_relation(expanded_otbs, misread_ti) == "AbbreviationMismatch"

    e1 = envelope.result("ocsr", "molscribe", ENGINES["molscribe"], [envelope.describe(expanded_otbs)])
    e2 = envelope.result("ocsr", "molnextr", ENGINES["molnextr"], [envelope.describe(misread_ti)])
    outcome = consensus.compare([e1, e2])

    assert outcome["agreement"] == "split"
    assert len(outcome["pairwise_diagnostics"]) == 1
    assert outcome["pairwise_diagnostics"][0]["relation"] == "AbbreviationMismatch"
