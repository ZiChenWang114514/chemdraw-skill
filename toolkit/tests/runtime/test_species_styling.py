"""Brief-level styling: species colours, orientation, abbreviations and condition text runs."""
from __future__ import annotations

import copy
import json
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
from rdkit import Chem

from cdxml_toolkit.chemistry_semantics import read_fragments
from cdxml_toolkit.mcp_runtime.figure_draw import draw_figure
from cdxml_toolkit.publication import house_styles
from cdxml_toolkit.publication.house_styles import ABBREVIATIONS

SUZUKI = {
    "species": [
        {"id": "ArBr", "smiles": "COC(=O)c1ccc(Br)cc1", "label": "1"},
        {"id": "ArB", "smiles": "COc1ccc(B(O)O)cc1", "label": "2"},
        {"id": "P", "smiles": "COC(=O)c1ccc(-c2ccc(OC)cc2)cc1", "label": "3"},
    ],
    "steps": [{"substrates": ["ArBr", "ArB"], "products": ["P"],
               "above": ["Pd(PPh3)4, K2CO3"], "below": ["dioxane/H2O, 90 °C"]}],
}


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.setenv("CHEMDRAW_OFFLINE", "1")


def _brief(**species_keys) -> dict:
    brief = copy.deepcopy(SUZUKI)
    for sp in brief["species"]:
        sp.update(species_keys.get(sp["id"], {}))
    return brief


def _draw(tmp_path: Path, brief: dict, name: str = "out.cdxml") -> tuple[dict, ET.Element]:
    report = draw_figure(brief, str(tmp_path / name))
    assert report["ok"], report
    return report, ET.parse(report["output_path"]).getroot()


def _index(root: ET.Element, hex_color: str) -> str:
    rgb = tuple(round(int(hex_color[i:i + 2], 16) / 255.0, 4) for i in (1, 3, 5))
    for k, c in enumerate(root.find("colortable").findall("color")):
        if tuple(round(float(c.get(a)), 4) for a in "rgb") == rgb:
            return str(k + 2)
    raise AssertionError(f"{hex_color} not in the colour table")


def _fragments(root: ET.Element) -> list[ET.Element]:
    return root.find("page").findall("fragment")


def _run_text(t: ET.Element) -> str:
    return "".join(s.text or "" for s in t.iter("s"))


def test_a_species_colour_paints_only_that_structure(tmp_path):
    report, root = _draw(tmp_path, _brief(ArB={"color": "#D55E00"}))
    red = _index(root, "#D55E00")
    frags = _fragments(root)
    assert all(el.get("color") == red for el in frags[1].findall("n") + frags[1].findall("b"))
    for frag in (frags[0], frags[2]):
        assert not any(el.get("color") == red for el in frag.iter())
    assert report["readback"]["status"] == "matched"
    assert any(a.startswith("species colours") for a in report["style"]["applied"])


def test_atom_and_bond_colours_follow_smiles_order(tmp_path):
    # COC(=O)c1ccc(Br)cc1: atoms 0 and 1 are the methyl carbon and the ester oxygen; 7-8 is C-Br.
    brief = _brief(ArBr={"atom_colors": [{"atoms": [0, 1], "color": "#0072B2"}],
                         "bond_colors": [{"bonds": [[7, 8]], "color": "#009E73"}]})
    report, root = _draw(tmp_path, brief)
    blue, green = _index(root, "#0072B2"), _index(root, "#009E73")
    frag = _fragments(root)[0]
    nodes = {n.get("id"): n for n in frag.findall("n")}
    blue_nodes = [n for n in frag.findall("n") if n.get("color") == blue]
    assert len(blue_nodes) == 2 and any(n.get("Element") == "8" for n in blue_nodes)
    assert len([b for b in frag.findall("b") if b.get("color") == blue]) == 1
    green_bonds = [b for b in frag.findall("b") if b.get("color") == green]
    assert len(green_bonds) == 1
    ends = {nodes[green_bonds[0].get("B")].get("Element"), nodes[green_bonds[0].get("E")].get("Element")}
    assert "35" in ends
    assert report["readback"]["status"] == "matched"


def test_a_species_can_abbreviate_without_a_house_style(tmp_path):
    report, root = _draw(tmp_path, _brief(P={"abbreviate": ["CO2Me", "OMe"]}))
    labels = sorted(_run_text(n.find("t")) for n in root.iter("n") if n.get("NodeType") == "Fragment")
    assert len(labels) == 2 and set(labels) <= {"CO2Me", "MeO2C", "OMe", "MeO"}
    assert report["readback"]["status"] == "matched"
    assert "species abbreviations (2 contracted)" in report["style"]["applied"]


def test_a_species_list_overrides_the_card(tmp_path, monkeypatch):
    card = {
        "slug": "_example", "kind": "journal", "display_name": "Example", "applies_to": ["Ex."],
        "base_preset": "nature", "measured": {},
        "conventions": {"abbreviate_groups": ["CO2Me", "OMe"], "signature_features": ["x"], "notes": "t"},
        "evidence": [{"doi": "10.0000/x", "citation": "Ex 2025", "licence": "CC BY 4.0"}],
    }
    (tmp_path / "cards").mkdir()
    (tmp_path / "cards" / "_example.json").write_text(json.dumps(card), encoding="utf-8")
    monkeypatch.setattr(house_styles, "DATA_DIR", tmp_path / "cards")
    brief = {**_brief(P={"abbreviate": []}), "style": "_example"}
    report, root = _draw(tmp_path, brief)
    product = _fragments(root)[2]
    assert not any(n.get("NodeType") == "Fragment" for n in product.iter("n"))
    contracted = [n for frag in _fragments(root)[:2] for n in frag.iter("n") if n.get("NodeType") == "Fragment"]
    assert len(contracted) == 2
    assert report["readback"]["status"] == "matched"


@pytest.mark.parametrize("orientation", ["flip_horizontal", "flip_vertical", "rotate_180"])
def test_orientation_moves_atoms_and_keeps_stereo(tmp_path, orientation):
    base = {"species": [{"id": "A", "smiles": "C[C@H](N)c1ccccc1", "label": "1"},
                        {"id": "B", "smiles": "C[C@H](NC(C)=O)c1ccccc1", "label": "2"}],
            "steps": [{"substrates": ["A"], "products": ["B"], "above": ["Ac2O"]}]}
    _, plain = _draw(tmp_path, base, "plain.cdxml")
    turned_brief = copy.deepcopy(base)
    turned_brief["species"][0]["orientation"] = orientation
    report, turned = _draw(tmp_path, turned_brief, "turned.cdxml")
    assert report["readback"]["status"] == "matched"

    def relative(root):
        pts = [tuple(map(float, n.get("p").split())) for n in _fragments(root)[0].findall("n")]
        cx = sum(p[0] for p in pts) / len(pts)
        cy = sum(p[1] for p in pts) / len(pts)
        return [(x - cx, y - cy) for x, y in pts]

    before, after = relative(plain), relative(turned)
    assert len(before) == len(after)
    sx = -1 if orientation in ("flip_horizontal", "rotate_180") else 1
    sy = -1 if orientation in ("flip_vertical", "rotate_180") else 1
    for (xb, yb), (xa, ya) in zip(before, after):
        assert xa == pytest.approx(sx * xb, abs=0.6) and ya == pytest.approx(sy * yb, abs=0.6)
    drawn = [Chem.MolToSmiles(m) for _, m in read_fragments(Path(report["output_path"]).read_text(encoding="utf-8"))]
    assert Chem.MolToSmiles(Chem.MolFromSmiles("C[C@H](N)c1ccccc1")) in drawn


def test_condition_runs_take_colour_and_face(tmp_path):
    brief = copy.deepcopy(SUZUKI)
    brief["steps"][0]["above"] = [[{"text": "Pd(PPh3)4", "color": "#DC3220", "bold": True}, {"text": ", K2CO3"}]]
    brief["steps"][0]["below"] = [{"text": "dioxane/H2O, 90 °C", "italic": True}]
    report, root = _draw(tmp_path, brief)
    red = _index(root, "#DC3220")
    texts = root.find("page").findall("t")
    above = next(t for t in texts if "K2" in _run_text(t) or "K" in _run_text(t) and "CO" in _run_text(t))
    red_runs = [s for s in above.iter("s") if s.get("color") == red]
    assert "".join(s.text for s in red_runs) == "Pd(PPh3)4"
    assert all(int(s.get("face")) & 1 for s in red_runs)
    assert not any(s.get("color") == red for s in above.iter("s") if "K" in (s.text or ""))
    below = next(t for t in texts if "dioxane" in _run_text(t))
    assert all(int(s.get("face")) & 2 for s in below.iter("s") if (s.text or "").strip())
    assert "condition text runs (2 styled)" in report["style"]["applied"]


@pytest.mark.parametrize("species_keys, message", [
    ({"color": "red"}, "hex colour"),
    ({"orientation": "rotate_90"}, "orientation must be one of"),
    ({"abbreviate": ["Xyz"]}, "unknown groups"),
    ({"atom_colors": [{"atoms": ["a"], "color": "#000000"}]}, "atom indices"),
    ({"bond_colors": [{"bonds": [[1]], "color": "#000000"}]}, "pairs of atom indices"),
])
def test_bad_species_styles_are_rejected(tmp_path, species_keys, message):
    report = draw_figure(_brief(ArBr=species_keys), str(tmp_path / "bad.cdxml"))
    assert not report["ok"] and message in json.dumps(report)


def test_a_bad_condition_run_is_rejected(tmp_path):
    brief = copy.deepcopy(SUZUKI)
    brief["steps"][0]["above"] = [{"color": "#DC3220"}]
    report = draw_figure(brief, str(tmp_path / "bad.cdxml"))
    assert not report["ok"] and "non-empty text" in json.dumps(report)


@pytest.mark.parametrize("smiles, group", [
    ("[N-]=[N+]=NCc1ccccc1", "N3"),
    ("C[Si](C)(C)Oc1ccccc1", "OTMS"),
    ("O=S(=O)(Oc1ccccc1)C(F)(F)F", "OTf"),
    ("Cc1ccc(S(=O)(=O)OCCc2ccccc2)cc1", "OTs"),
    ("CC1(C)OB(c2ccccc2)OC1(C)C", "Bpin"),
    ("CC(C)[Si](C#Cc1ccccc1)(C(C)C)C(C)C", "TIPS"),
    ("CCCCc1ccccc1", "nBu"),
    ("CC(C)c1ccccc1", "iPr"),
    ("CN(C)c1ccccc1", "NMe2"),
    ("CS(=O)(=O)OCc1ccccc1", "OMs"),
    ("O=C(OCc1ccccc1)c1ccccc1", "OBz"),
])
def test_new_abbreviations_contract_and_read_back(tmp_path, smiles, group):
    brief = {"species": [{"id": "A", "smiles": smiles, "label": "1", "abbreviate": [group]},
                         {"id": "B", "smiles": "CCO", "label": "2"}],
             "steps": [{"substrates": ["A"], "products": ["B"], "above": ["x"]}]}
    report, root = _draw(tmp_path, brief)
    labels = [_run_text(n.find("t")) for n in root.iter("n") if n.get("NodeType") == "Fragment"]
    left, right = ABBREVIATIONS[group][2], ABBREVIATIONS[group][3]
    assert len(labels) == 1 and labels[0] in (left, right), labels
    assert report["readback"]["status"] == "matched"


# --- title, panel label, captions and boxes ---------------------------------------

def test_the_title_and_panel_label_are_drawn_above_the_figure(tmp_path):
    brief = {**copy.deepcopy(SUZUKI), "panel_label": "a", "title": [{"text": "Suzuki coupling"},
                                                                    {"text": " (this work)", "italic": True}]}
    report, root = _draw(tmp_path, brief)
    page = root.find("page")
    title = next(t for t in page.findall("t") if "Suzuki coupling" in _run_text(t))
    assert _run_text(title).startswith("a  Suzuki coupling (this work)")
    runs = list(title.iter("s"))
    assert int(runs[0].get("face")) & 1 and runs[0].text == "a"
    assert any(int(s.get("face")) & 2 and "this work" in s.text for s in runs)
    title_y = float(title.get("p").split()[1])
    assert all(float(n.get("p").split()[1]) > title_y for n in page.iter("n"))
    assert "panel label and title" in report["style"]["applied"]


def test_a_plain_title_is_no_longer_dropped(tmp_path):
    report, root = _draw(tmp_path, {**copy.deepcopy(SUZUKI), "title": "Scheme 1"})
    assert any(_run_text(t) == "Scheme 1" for t in root.find("page").findall("t"))


def test_a_caption_goes_under_the_compound_number(tmp_path):
    brief = _brief(P={"caption": {"text": "gram scale", "italic": True}})
    report, root = _draw(tmp_path, brief)
    page = root.find("page")
    caption = next(t for t in page.findall("t") if _run_text(t) == "gram scale")
    number = next(t for t in page.findall("t") if _run_text(t) == "3")
    assert float(caption.get("p").split()[1]) > float(number.get("p").split()[1])
    assert abs(float(caption.get("p").split()[0]) - float(number.get("p").split()[0])) < 1.0
    assert all(int(s.get("face")) & 2 for s in caption.iter("s"))
    assert "captions (1)" in report["style"]["applied"]


def test_boxes_frame_and_fill_a_structure(tmp_path):
    brief = _brief(P={"box": {"color": "#1F4E9E", "fill": "#EAF2FB", "style": "dashed", "rounded": True}},
                   ArBr={"box": True})
    report, root = _draw(tmp_path, brief)
    page = root.find("page")
    rects = [g for g in page.iter("graphic") if g.get("GraphicType") == "Rectangle"]
    assert len(rects) == 3
    fill = next(g for g in rects if g.get("FillType") == "Solid")
    assert fill.get("color") == _index(root, "#EAF2FB") and list(page).index(fill) == 0
    frame = next(g for g in rects if g.get("LineType") == "Dashed")
    assert frame.get("color") == _index(root, "#1F4E9E") and frame.get("RectangleType") == "RoundEdge"
    x1, y1, x2, y2 = (float(v) for v in frame.get("BoundingBox").split())
    product = _fragments(root)[2]
    for n in product.findall("n"):
        x, y = (float(v) for v in n.get("p").split())
        assert x1 < x < x2 and y1 < y < y2
    plain = [g for g in rects if g not in (fill, frame)][0]
    assert plain.get("color") == "0" and not plain.get("LineType")
    assert "species boxes (2)" in report["style"]["applied"]


@pytest.mark.parametrize("change, message", [
    ({"panel_label": ""}, "panel_label"),
    ({"title": {"color": "#000000"}}, "non-empty text"),
])
def test_bad_panel_keys_are_rejected(tmp_path, change, message):
    report = draw_figure({**copy.deepcopy(SUZUKI), **change}, str(tmp_path / "bad.cdxml"))
    assert not report["ok"] and message in json.dumps(report)


@pytest.mark.parametrize("box, message", [
    ({"style": "dotted"}, "box style"),
    ({"colour": "#000000"}, "unknown box keys"),
    ({"fill": "blue"}, "hex colour"),
    ("yes", "box must be true or an object"),
])
def test_bad_boxes_are_rejected(tmp_path, box, message):
    report = draw_figure(_brief(P={"box": box}), str(tmp_path / "bad.cdxml"))
    assert not report["ok"] and message in json.dumps(report)


# --- scope panels ---------------------------------------------------------------

def test_scope_panels_take_the_card_and_the_species_styles(tmp_path, monkeypatch):
    card = {
        "slug": "_example", "kind": "journal", "display_name": "Example", "applies_to": ["Ex."],
        "base_preset": "nature",
        "measured": {"line_width_over_bond_length": 0.06, "bond_length_over_cap_height": 2.0},
        "conventions": {"compound_label_face": "bold", "abbreviate_groups": ["CO2Me"],
                        "signature_features": ["x"], "notes": "t"},
        "evidence": [{"doi": "10.0000/x", "citation": "Ex 2025", "licence": "CC BY 4.0"}],
    }
    (tmp_path / "cards").mkdir()
    (tmp_path / "cards" / "_example.json").write_text(json.dumps(card), encoding="utf-8")
    monkeypatch.setattr(house_styles, "DATA_DIR", tmp_path / "cards")
    brief = {"kind": "scope", "style": "_example", "species": [
        {"id": "a", "smiles": "COC(=O)c1ccc(C)cc1", "label": "3a", "values": {"y": "85%"}, "color": "#D55E00"},
        {"id": "b", "smiles": "COC(=O)c1ccc(Cl)cc1", "label": "3b", "values": {"y": "72%"}, "abbreviate": []},
    ]}
    report = draw_figure(brief, str(tmp_path / "scope"))
    assert report["ok"], report
    root = ET.parse(report["pages"][0]["path"]).getroot()
    bond = float(root.get("BondLength"))
    assert float(root.get("LineWidth")) == pytest.approx(0.06 * bond, rel=0.02)
    page = root.find("page")
    numbers = [t for t in page.iter("t") if _run_text(t) in ("3a", "3b")]
    assert len(numbers) == 2 and all(s.get("face") == "1" for t in numbers for s in t.iter("s"))
    frags = [f for f in page.iter("fragment") if f.find("n") is not None and
             not any(f in n for n in page.iter("n"))]
    red = _index(root, "#D55E00")
    painted = [f for f in frags if any(b.get("color") == red for b in f.findall("b"))]
    assert len(painted) == 1
    contracted = [n for n in page.iter("n") if n.get("NodeType") == "Fragment"]
    assert len(contracted) == 1
    size = root.get("LabelSize")
    assert all(s.get("size") == size for s in contracted[0].find("t").iter("s"))
    assert report["readback"]["status"] == "matched"
    applied = report["style"]["applied"]
    assert "compound_label_face=bold" in applied and "abbreviate_groups (1 contracted)" in applied


def test_bpin_keeps_its_spelling_on_the_left():
    # Desktop ChemDraw reverses the tokens of a left-facing label, so "pinB" would read "Bnip".
    assert ABBREVIATIONS["Bpin"][3] == "Bpin"
