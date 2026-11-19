"""cdxml_toolkit.acs_builder: lone-pair placement, XML escaping, no overwrite, packaged tool."""
import xml.etree.ElementTree as ET

import pytest

from cdxml_toolkit import acs_builder


def _root(text):
    return ET.fromstring(text.split("?>", 1)[1].split(">", 1)[1])  # skip the XML declaration and DOCTYPE


def _lone_pair_y(side):
    fig = acs_builder.Fig()
    pts = fig.mol("CO", at=(100, 100), lone_pairs=[(1, side)])
    texts = [t for t in _root(fig.to_cdxml()).iter("t") if t.get("InterpretChemically") == "no"]
    return pts[1][1], float(texts[-1].get("p").split()[1])


def test_lone_pairs_up_sit_above_and_down_below_the_atom():
    # CDXML y grows downward: "up" has the smaller y. The pair text baseline sits below its dots,
    # so compare against the atom label's own baseline (atom y + 3.5).
    atom_y, up = _lone_pair_y("up")
    _, down = _lone_pair_y("down")
    _, right = _lone_pair_y("right")
    assert up < atom_y < down
    assert up < right < down


def test_text_and_labels_are_xml_escaped():
    fig = acs_builder.Fig()
    fig.mol("[*:1]CC(=O)O", at=(100, 80), labels={1: 'R&D<"x">'})
    fig.text(50, 50, "A & B < C")
    fig.add_interaction((10, 10), (60, 10), label="H&<b")
    root = _root(fig.to_cdxml())
    assert any(n.get("GenericNickname") == 'R&D<"x">' for n in root.iter("n"))
    assert "A & B < C" in ["".join(t.itertext()) for t in root.iter("t")]


def test_write_refuses_an_existing_file(tmp_path):
    target = tmp_path / "a.cdxml"
    target.write_text("keep", encoding="utf-8")
    fig = acs_builder.Fig()
    fig.text(10, 10, "x")
    with pytest.raises(FileExistsError):
        fig.write(target)
    assert target.read_text(encoding="utf-8") == "keep"
    spec = {"objects": [{"type": "text", "at": [10, 10], "text": "x"}], "style": "wiley"}
    with pytest.raises(FileExistsError):
        acs_builder.build_from_spec(spec, target)
    assert target.read_text(encoding="utf-8") == "keep"


def test_build_acs_figure_uses_the_packaged_module(tmp_path):
    from cdxml_toolkit.mcp_runtime import tool_registry

    assert "skill" not in acs_builder.__file__.replace("\\", "/").split("/cdxml_toolkit/")[-1]
    result = tool_registry.build_acs_figure({"objects": [{"type": "text", "at": [10, 10], "text": "a & b"}]},
                                            output_path=str(tmp_path / "f.cdxml"))
    assert result["ok"] is True
