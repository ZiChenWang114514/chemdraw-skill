from __future__ import annotations

import xml.etree.ElementTree as ET

import pytest

from cdxml_toolkit.render import renderer
from cdxml_toolkit.render.parser import parse_yaml

NAME_ONLY = """
layout: linear
structures:
  Amide: {name: "DMF", label: "1"}
  Product: {smiles: "CN(C)C", label: "2"}
steps:
  - substrates: [Amide]
    products: [Product]
"""

UNKNOWN_NAME = NAME_ONLY.replace("DMF", "no such reagent zzq")


def _elements(cdxml: str) -> list[str]:
    root = ET.fromstring(cdxml[cdxml.index("<CDXML"):])
    return [n.get("Element") for n in root.iter("n")]


def test_structure_given_only_by_name_is_drawn(tmp_path):
    source = tmp_path / "name_only.yaml"
    source.write_text(NAME_ONLY, encoding="utf-8")

    cdxml = renderer.render(parse_yaml(str(source)))

    # DMF (CN(C)C=O) contributes an oxygen that the SMILES-only product lacks.
    assert "8" in _elements(cdxml)


def test_unknown_name_still_asks_for_a_smiles(tmp_path):
    source = tmp_path / "unknown.yaml"
    source.write_text(UNKNOWN_NAME, encoding="utf-8")

    with pytest.raises(ValueError, match="Provide a SMILES"):
        renderer.render(parse_yaml(str(source)))
