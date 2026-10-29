from __future__ import annotations

import xml.etree.ElementTree as ET

from cdxml_toolkit.render import renderer
from cdxml_toolkit.render.parser import parse_yaml

SUZUKI = """
layout: linear
structures:
  ArBr: {smiles: "COc1ccc(Br)cc1", label: "1"}
  Boronic: {smiles: "OB(O)c1ccccc1", label: "2"}
  Biaryl: {smiles: "COc1ccc(-c2ccccc2)cc1", label: "3"}
steps:
  - substrates: [ArBr, Boronic]
    products: [Biaryl]
"""


def test_label_width_extends_the_fragment_box():
    carbon = renderer._fragment_bbox([{"x": 0.0, "y": 0.0, "symbol": "C"}])
    bromine = renderer._fragment_bbox([{"x": 0.0, "y": 0.0, "symbol": "Br", "num_hydrogens": 0}])
    hydroxyl = renderer._fragment_bbox([{"x": 0.0, "y": 0.0, "symbol": "O", "num_hydrogens": 1},
                                        {"x": 14.4, "y": 0.0, "symbol": "C"}])

    assert carbon[2] == renderer._FRAG_PAD_W
    assert bromine[2] > carbon[2] + 4
    # In a structure ChemDraw may draw OH as HO, so the hydrogen widens both sides.
    assert hydroxyl[0] < carbon[0] - 4


def test_plus_sign_clears_a_terminal_bromine(tmp_path):
    source = tmp_path / "suzuki.yaml"
    source.write_text(SUZUKI, encoding="utf-8")
    root = ET.fromstring(_body(renderer.render(parse_yaml(str(source)))))

    bromine_x = next(float(n.get("p").split()[0]) for n in root.iter("n") if n.get("Element") == "35")
    plus_x = next(float(t.get("p").split()[0]) for t in root.iter("t")
                  if "".join(t.itertext()).strip() == "+")
    # "Br" ends about 7 pt right of the atom; keep a visible gap before the "+".
    assert plus_x - bromine_x >= 12.0


def _body(cdxml: str) -> str:
    return cdxml[cdxml.index("<CDXML"):]


def _component_boxes(atoms, bonds):
    groups = {a["index"]: {a["index"]} for a in atoms}
    for b in bonds:
        merged = groups[b["atom1"]] | groups[b["atom2"]]
        for i in merged:
            groups[i] = merged
    unique = {id(g): g for g in groups.values()}.values()
    return [renderer._fragment_bbox([a for a in atoms if a["index"] in g]) for g in unique]


def test_the_ions_of_a_salt_do_not_run_into_each_other():
    for smiles in ("[Na+].[OH-]", "[K+].[I-]", "[Li+].[Cl-]", "[Na+].[O-]C(C)=O"):
        atoms, bonds = renderer._smiles_to_fragment_data(smiles)
        boxes = sorted(_component_boxes(atoms, bonds))
        for left, right in zip(boxes, boxes[1:]):
            apart = right[0] - left[2] >= 3.0 or right[1] - left[3] >= 0 or left[1] - right[3] >= 0
            assert apart, (smiles, left, right)


def test_ions_that_are_clear_of_each_other_stay_where_they_are():
    from rdkit import Chem
    from rdkit.Chem import AllChem

    smiles = "CC[NH+](CC)CC.[Cl-]"
    atoms, _ = renderer._smiles_to_fragment_data(smiles)
    mol = Chem.MolFromSmiles(smiles)
    AllChem.Compute2DCoords(mol)
    conf = mol.GetConformer()
    # Relative placement of the chloride is RDKit's, unchanged.
    rdkit_dx = conf.GetAtomPosition(7).x - conf.GetAtomPosition(2).x
    drawn_dx = (atoms[7]["x"] - atoms[2]["x"]) / renderer.ACS_BOND_LENGTH * 1.5
    assert abs(rdkit_dx - drawn_dx) < 0.05


def test_conditions_beside_a_serpentine_turn_are_written_like_the_others():
    from pathlib import Path

    showcase = Path(__file__).parent.parent / "experiments" / "scheme_dsl" / "showcase"
    cdxml = renderer.render(parse_yaml(str(showcase / "12_serpentine_5step.yaml")))
    texts = [" ".join("".join(t.itertext()).split()) for t in ET.fromstring(_body(cdxml)).iter("t")]
    # The turn's "DCM, -78 C" gets its degree sign, as conditions on a row arrow do.
    assert any("78 °C" in t for t in texts) and not any(t.endswith("78 C") for t in texts), texts
