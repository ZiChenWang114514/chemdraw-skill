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
    hydroxyl = renderer._fragment_bbox([{"x": 0.0, "y": 0.0, "symbol": "O", "num_hydrogens": 1}])

    assert carbon[2] == renderer._FRAG_PAD_W
    assert bromine[2] > carbon[2] + 4
    # ChemDraw may draw OH as HO, so the hydrogen widens both sides.
    assert hydroxyl[2] > carbon[2] + 4 and hydroxyl[0] < carbon[0] - 4


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
