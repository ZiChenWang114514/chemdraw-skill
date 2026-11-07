from __future__ import annotations

import copy
import json
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
from rdkit import Chem

from cdxml_toolkit.chemistry_semantics import read_fragments
from cdxml_toolkit.publication import house_styles
from cdxml_toolkit.publication.house_styles import (
    house_style, list_house_styles, load_house_styles, resolve_style, validate_card,
)
from cdxml_toolkit.mcp_runtime.figure_draw import draw_figure

EXAMPLE = {
    "slug": "_example",
    "kind": "journal",
    "display_name": "Example Journal",
    "applies_to": ["Ex. J."],
    "base_preset": "nature",
    "measured": {"bond_length_over_cap_height": 1.5},
    "conventions": {
        "compound_label_face": "bold",
        "yield_placement": "under_product_label",
        "yield_format": "{value}%",
        "substrate_layout": "inline_plus",
        "abbreviate_groups": [],
        "new_bond_color": None,
        "substrate_colors": None,
        "arrow_style": "plain",
        "signature_features": ["bold numbers"],
        "notes": "test card",
    },
    "evidence": [{"doi": "10.0000/example", "citation": "Example 2025", "licence": "CC BY 4.0"}],
}

SUZUKI = {
    "species": [
        {"id": "ArBr", "smiles": "COC(=O)c1ccc(Br)cc1", "label": "1"},
        {"id": "ArB", "smiles": "COc1ccc(B(O)O)cc1", "label": "2"},
        {"id": "P", "smiles": "COC(=O)c1ccc(-c2ccc(OC)cc2)cc1", "label": "3"},
    ],
    "steps": [{"substrates": ["ArBr", "ArB"], "products": ["P"],
               "above": ["Pd(PPh3)4, K2CO3"], "below": ["dioxane/H2O, 90 °C"], "yield": "85%"}],
}


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.setenv("CHEMDRAW_OFFLINE", "1")


def _card(tmp_path: Path, monkeypatch, **conventions) -> dict:
    card = copy.deepcopy(EXAMPLE)
    card["conventions"].update(conventions)
    (tmp_path / "cards").mkdir(exist_ok=True)
    (tmp_path / "cards" / "_example.json").write_text(json.dumps(card), encoding="utf-8")
    monkeypatch.setattr(house_styles, "DATA_DIR", tmp_path / "cards")
    return card


def _draw(tmp_path: Path, brief: dict) -> tuple[dict, ET.Element]:
    report = draw_figure({**copy.deepcopy(brief), "style": "_example"}, str(tmp_path / "out.cdxml"))
    assert report["ok"], report
    return report, ET.parse(report["output_path"]).getroot()


def _text(t: ET.Element) -> str:
    return "".join(s.text or "" for s in t.iter("s"))


def _page_texts(root: ET.Element) -> list[ET.Element]:
    return root.find("page").findall("t")


# --- loader --------------------------------------------------------------------

def test_the_example_card_loads_and_resolves(tmp_path, monkeypatch):
    _card(tmp_path, monkeypatch)
    style = house_style("Example Journal")
    assert style.slug == "_example" and style.base_preset == "nature" and len(style.evidence) == 1
    assert [s.slug for s in list_house_styles()] == ["_example"]
    assert resolve_style("nature")[0] == "preset"
    kind, value = resolve_style("_example")
    assert kind == "house" and value.slug == style.slug


@pytest.mark.parametrize("change, message", [
    ({"conventions": {"yield_placement": "in_a_table"}}, "yield_placement"),
    ({"base_preset": "no_such_journal"}, "base_preset"),
    ({"evidence": []}, "evidence"),
    ({"conventions": {"abbreviate_groups": ["Xyz"]}}, "unknown groups"),
    ({"conventions": {"made_up": 1}}, "unknown conventions"),
    ({"kind": "lab"}, "kind"),
])
def test_invalid_cards_are_rejected(change, message):
    card = copy.deepcopy(EXAMPLE)
    for key, value in change.items():
        if key == "conventions":
            card["conventions"].update(value)
        else:
            card[key] = value
    with pytest.raises(ValueError, match=message):
        validate_card(card)


def test_a_card_whose_slug_does_not_match_its_file_is_rejected(tmp_path):
    (tmp_path / "other.json").write_text(json.dumps(EXAMPLE), encoding="utf-8")
    with pytest.raises(ValueError, match="file name"):
        load_house_styles(tmp_path)


def test_shipped_cards_validate():
    for style in list_house_styles():
        assert style.evidence and style.base_preset


# --- conventions ---------------------------------------------------------------

def test_bold_labels_and_yield_under_the_product_label(tmp_path, monkeypatch):
    _card(tmp_path, monkeypatch)
    report, root = _draw(tmp_path, SUZUKI)
    texts = _page_texts(root)
    labels = [t for t in texts if _text(t) in {"1", "2", "3"}]
    assert len(labels) == 3 and all(s.get("face") == "1" for t in labels for s in t.iter("s"))
    yield_t = [t for t in texts if _text(t) == "85%"]
    assert len(yield_t) == 1
    product_label = next(t for t in labels if _text(t) == "3")
    lx, ly = map(float, product_label.get("p").split())
    yx, yy = map(float, yield_t[0].get("p").split())
    assert abs(lx - yx) < 0.5 and yy > ly
    assert not any("85" in _text(t) and t is not yield_t[0] for t in texts)
    style = report["style"]
    assert style["house"] == "_example" and style["preset"] == "nature"
    assert "compound_label_face=bold" in style["applied"]
    assert "yield_placement=under_product_label" in style["applied"]
    assert any(s.startswith("new_bond_color: not specified") for s in style["skipped"])
    assert report["readback"]["status"] == "matched"


def test_stacked_substrates_share_a_column_with_the_plus_between(tmp_path, monkeypatch):
    _card(tmp_path, monkeypatch, substrate_layout="stacked_plus")
    report, root = _draw(tmp_path, SUZUKI)
    page = root.find("page")
    centres = []
    for frag in page.findall("fragment")[:2]:
        pts = [tuple(map(float, n.get("p").split())) for n in frag.findall("n")]
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        centres.append(((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, min(ys), max(ys)))
    (x1, _, top1, bottom1), (x2, _, top2, bottom2) = centres
    assert abs(x1 - x2) < 8.0  # centred on the drawn extent, heteroatom labels included
    plus = [t for t in _page_texts(root) if _text(t) == "+"]
    assert len(plus) == 1
    px, py = map(float, plus[0].get("p").split())
    assert abs(px - (x1 + x2) / 2) < 6.0 and bottom1 < py < top2
    assert not report["lint"]["issues"], report["lint"]["issues"]


def test_abbreviated_groups_read_back_as_the_same_molecule(tmp_path, monkeypatch):
    _card(tmp_path, monkeypatch, abbreviate_groups=["CO2Me", "OMe"])
    report, root = _draw(tmp_path, SUZUKI)
    page = root.find("page")
    labels = [_text(n.find("t")) for n in page.iter("n") if n.get("NodeType") == "Fragment"]
    assert sorted(labels) and set(labels) <= {"CO2Me", "MeO2C", "OMe", "MeO"} and len(labels) == 4
    drawn = sorted(Chem.MolToSmiles(m) for _, m in read_fragments(Path(report["output_path"]).read_text(encoding="utf-8")))
    wanted = sorted(Chem.MolToSmiles(Chem.MolFromSmiles(s["smiles"])) for s in SUZUKI["species"])
    assert drawn == wanted
    assert report["readback"]["status"] == "matched"
    assert "abbreviate_groups (4 contracted)" in report["style"]["applied"]


def _colour_index(root: ET.Element, hex_color: str) -> str:
    rgb = tuple(round(int(hex_color[i:i + 2], 16) / 255.0, 4) for i in (1, 3, 5))
    for k, c in enumerate(root.find("colortable").findall("color")):
        if tuple(round(float(c.get(a)), 4) for a in "rgb") == rgb:
            return str(k + 2)
    raise AssertionError(f"{hex_color} not in the colour table")


def test_the_new_biaryl_bond_is_coloured(tmp_path, monkeypatch):
    _card(tmp_path, monkeypatch, new_bond_color="#DC3220")
    report, root = _draw(tmp_path, SUZUKI)
    index = _colour_index(root, "#DC3220")
    product = root.find("page").findall("fragment")[2]
    nodes = {n.get("id"): n for n in product.findall("n")}
    coloured = [b for b in product.findall("b") if b.get("color") == index]
    assert len(coloured) == 1
    a, b = nodes[coloured[0].get("B")], nodes[coloured[0].get("E")]
    # The biaryl bond joins two ring carbons, each with three carbon neighbours.
    assert a.get("Element") is None and b.get("Element") is None
    for frag in root.find("page").findall("fragment")[:2]:
        assert not any(el.get("color") == index for el in frag.iter())
    assert "new_bond_color" in report["style"]["applied"]


def test_substrate_colours(tmp_path, monkeypatch):
    _card(tmp_path, monkeypatch, substrate_colors=["#005AB5", "#DC3220"])
    _, root = _draw(tmp_path, SUZUKI)
    blue, red = _colour_index(root, "#005AB5"), _colour_index(root, "#DC3220")
    frags = root.find("page").findall("fragment")
    for frag, index in zip(frags[:2], (blue, red)):
        items = frag.findall("n") + frag.findall("b")
        assert items and all(el.get("color") == index for el in items)
    assert not any(el.get("color") for el in frags[2].iter() if el.tag in ("n", "b"))


def test_bold_arrows_and_the_preset_are_applied(tmp_path, monkeypatch):
    _card(tmp_path, monkeypatch, arrow_style="bold")
    report, root = _draw(tmp_path, SUZUKI)
    assert root.get("BondLength") == "10.8"
    assert all(a.get("LineWidth") == "0.9" for a in root.iter("arrow"))
    assert "arrow_style=bold" in report["style"]["applied"]


def test_an_unknown_style_lists_presets_and_house_styles(tmp_path, monkeypatch):
    _card(tmp_path, monkeypatch)
    report = draw_figure({**SUZUKI, "style": "no_such_style"}, str(tmp_path / "x.cdxml"))
    assert not report["ok"] and "_example" in report["errors"][0] and "acs1996" in report["errors"][0]


@pytest.mark.parametrize("placement, separator, expected", [
    ("after_product_label", None, ("3", ", 85%")),
    ("after_product_label", ": ", ("3", ": 85%")),
    ("after_product_label_parenthesised", None, ("3", " (85%)")),
])
def test_yield_on_the_label_line(tmp_path, monkeypatch, placement, separator, expected):
    _card(tmp_path, monkeypatch, yield_placement=placement, yield_separator=separator)
    _, root = _draw(tmp_path, SUZUKI)
    label = next(t for t in _page_texts(root) if _text(t).startswith("3"))
    runs = list(label.iter("s"))
    assert tuple(r.text for r in runs) == expected
    assert runs[0].get("face") == "1" and runs[1].get("face") == "0"
    assert not any(_text(t) == "85%" for t in _page_texts(root))


def test_more_groups_contract_and_read_back(tmp_path, monkeypatch):
    _card(tmp_path, monkeypatch, abbreviate_groups=["OCF3", "CF3", "CN", "Boc", "Ph"])
    brief = {
        "species": [
            {"id": "A", "smiles": "N#Cc1ccc(OC(F)(F)F)cc1", "label": "4"},
            {"id": "B", "smiles": "CC(C)(C)OC(=O)N1CCC(c2ccccc2)CC1", "label": "5"},
        ],
        "steps": [{"substrates": ["A"], "products": ["B"], "above": ["conditions"]}],
    }
    report, root = _draw(tmp_path, brief)
    labels = sorted(_text(n.find("t")) for n in root.iter("n") if n.get("NodeType") == "Fragment")
    assert set(labels) <= {"CN", "NC", "OCF3", "F3CO", "Boc", "Ph"}
    assert len(labels) == 4
    assert report["readback"]["status"] == "matched"


def test_ome_abbreviation_leaves_methyl_esters_alone():
    from rdkit import Chem
    from cdxml_toolkit.publication.house_styles import ABBREVIATIONS
    patt = Chem.MolFromSmarts(ABBREVIATIONS["OMe"][0])
    assert Chem.MolFromSmiles("COc1ccccc1").HasSubstructMatch(patt)
    assert not Chem.MolFromSmiles("COC(=O)c1ccccc1").HasSubstructMatch(patt)


# --- figure types ----------------------------------------------------------------

FIGURES = {
    "mechanism": {"conventions": {"curved_arrow_color": "#E3001B", "curved_arrow_weight": "thin",
                                  "show_lone_pairs": True},
                  "signature_features": ["red curved arrows"], "crops": ["evidence/x-01.png"]},
    "catalytic_cycle": {"conventions": {"cycle_arrow_color": "#1F4E9E", "center_label": True},
                        "signature_features": ["blue cycle arrows"], "crops": ["evidence/x-01.png"]},
}


def _figure_card(tmp_path, monkeypatch, figure_types=None):
    card = copy.deepcopy(EXAMPLE)
    card["evidence"][0]["crop"] = "evidence/x-01.png"
    card["figure_types"] = copy.deepcopy(FIGURES if figure_types is None else figure_types)
    (tmp_path / "cards").mkdir(exist_ok=True)
    (tmp_path / "cards" / "_example.json").write_text(json.dumps(card), encoding="utf-8")
    monkeypatch.setattr(house_styles, "DATA_DIR", tmp_path / "cards")
    return card


def test_figure_type_sections_load(tmp_path, monkeypatch):
    _figure_card(tmp_path, monkeypatch)
    style = house_style("_example")
    assert style.figure_convention("mechanism", "curved_arrow_color") == "#E3001B"
    assert style.figure_convention("energy_profile", "energy_unit", "kcal/mol") == "kcal/mol"
    assert style.as_dict()["figure_types"]["catalytic_cycle"]["conventions"]["center_label"] is True


@pytest.mark.parametrize("figure_types, message", [
    ({"poster": {"crops": ["evidence/x-01.png"]}}, "unknown figure type"),
    ({"mechanism": {"conventions": {"energy_unit": "eV"}, "crops": ["evidence/x-01.png"]}}, "does not apply"),
    ({"mechanism": {"conventions": {"curved_arrow_weight": "huge"}, "crops": ["evidence/x-01.png"]}}, "must be one of"),
    ({"mechanism": {"conventions": {"curved_arrow_color": "red"}, "crops": ["evidence/x-01.png"]}}, "colour"),
    ({"mechanism": {"conventions": {}, "crops": ["evidence/other.png"]}}, "not crops of the evidence"),
    ({"mechanism": {"conventions": {}}}, "crops must list"),
    ({"energy_profile": {"conventions": {"pathway_colors": []}, "crops": ["evidence/x-01.png"]}}, "list of"),
])
def test_invalid_figure_type_sections_are_rejected(figure_types, message):
    card = copy.deepcopy(EXAMPLE)
    card["evidence"][0]["crop"] = "evidence/x-01.png"
    card["figure_types"] = figure_types
    with pytest.raises(ValueError, match=message):
        validate_card(card)


def test_mechanism_arrows_take_the_card_colour_and_weight(tmp_path, monkeypatch):
    _figure_card(tmp_path, monkeypatch)
    from cdxml_toolkit.chemdraw.style_presets import style_preset
    brief = {
        "kind": "mechanism", "style": "_example",
        "species": [{"id": "ald", "smiles": "CC=O", "label": "1"}, {"id": "hyd", "smiles": "[OH-]"},
                    {"id": "alk", "smiles": "CC([O-])O", "label": "2"}],
        "steps": [{"substrates": ["ald", "hyd"], "products": ["alk"], "moves": [
            {"from": {"species": "hyd", "atom": 0}, "to": {"species": "ald", "atom": 1}},
            {"from": {"species": "ald", "bond": [1, 2]}, "to": {"species": "ald", "atom": 2}}]}],
    }
    report = draw_figure(brief, str(tmp_path / "mech.cdxml"))
    assert report["ok"], report
    assert "mechanism.curved_arrow_color=#E3001B" in report["style"]["applied"]
    assert any("show_lone_pairs" in s and "guidance" in s for s in report["style"]["skipped"])
    root = ET.parse(report["output_path"]).getroot()
    rgb = [tuple(float(c.get(k)) for k in "rgb") for c in root.find("colortable").findall("color")]
    curves = list(root.iter("curve"))
    assert len(curves) == 2
    width = 0.75 * float(style_preset("nature")["attributes"]["LineWidth"])
    for curve in curves:
        r, g, b = rgb[int(curve.get("color")) - 2]
        assert (round(r * 255), round(g * 255), round(b * 255)) == (0xE3, 0x00, 0x1B)
        assert float(curve.get("LineWidth")) == pytest.approx(width)


def test_catalytic_cycle_arrows_take_the_card_colour(tmp_path, monkeypatch):
    _figure_card(tmp_path, monkeypatch)
    brief = {
        "layout": "catalytic-cycle",
        "species": [{"id": "A", "smiles": "CCO", "label": "A"}, {"id": "B", "smiles": "CC=O", "label": "B"},
                    {"id": "C", "smiles": "CC(=O)O", "label": "C"}],
        "steps": [{"substrates": ["A"], "products": ["B"]}, {"substrates": ["B"], "products": ["C"]},
                  {"substrates": ["C"], "products": ["A"]}],
    }
    report, root = _draw(tmp_path, brief)
    assert report["layout"] == "catalytic-cycle"
    assert "catalytic_cycle.cycle_arrow_color=#1F4E9E" in report["style"]["applied"]
    arrows = list(root.iter("arrow"))
    assert arrows and all(a.get("color") == arrows[0].get("color") != "0" for a in arrows)


def test_a_card_without_the_figure_type_says_so(tmp_path, monkeypatch):
    _figure_card(tmp_path, monkeypatch, figure_types={})
    from cdxml_toolkit.mcp_runtime import figure_house
    _, applied, skipped = figure_house.apply_figure_type_conventions(
        '<?xml version="1.0" ?><CDXML><page/></CDXML>', house_style("_example"), "mechanism", "nature")
    assert applied == [] and "describes no mechanism figures" in skipped[0]


def test_every_figure_type_lists_known_conventions():
    assert set(house_styles.FIGURE_TYPES) == set(house_styles.FIGURE_TYPE_CONVENTIONS)
    for keys in house_styles.FIGURE_TYPE_CONVENTIONS.values():
        assert all(key in house_styles.FIGURE_CONVENTIONS for key in keys)
    for figure_type, keys in house_styles.APPLIED_FIGURE_CONVENTIONS.items():
        assert set(keys) <= set(house_styles.FIGURE_TYPE_CONVENTIONS[figure_type])


# --- measured geometry -------------------------------------------------------------

def _measured_card(tmp_path, monkeypatch, measured):
    card = copy.deepcopy(EXAMPLE)
    card["measured"] = measured
    (tmp_path / "cards").mkdir(exist_ok=True)
    (tmp_path / "cards" / "_example.json").write_text(json.dumps(card), encoding="utf-8")
    monkeypatch.setattr(house_styles, "DATA_DIR", tmp_path / "cards")


def test_measured_ratios_set_line_width_bold_width_and_label_size(tmp_path, monkeypatch):
    _measured_card(tmp_path, monkeypatch, {"line_width_over_bond_length": 0.05,
                                           "bold_width_over_bond_length": 0.15,
                                           "bond_length_over_cap_height": 2.0})
    report, root = _draw(tmp_path, SUZUKI)
    bond = float(root.get("BondLength"))
    assert float(root.get("LineWidth")) == pytest.approx(0.05 * bond, rel=0.01)
    assert float(root.get("BoldWidth")) == pytest.approx(0.15 * bond, rel=0.01)
    size = float(root.get("LabelSize"))
    assert size == pytest.approx(bond / 2.0 / 0.716, rel=0.01)
    br = next(n for n in root.iter("n") if n.get("Element") == "35")
    assert float(next(br.iter("s")).get("size")) == pytest.approx(size, rel=0.01)
    applied = " ".join(report["style"]["applied"])
    assert "measured.line_width" in applied and "measured.atom_label_size" in applied


def test_measured_values_are_clamped(tmp_path, monkeypatch):
    _measured_card(tmp_path, monkeypatch, {"line_width_over_bond_length": 5.0,
                                           "bond_length_over_cap_height": 0.01})
    _, root = _draw(tmp_path, SUZUKI)
    assert float(root.get("LineWidth")) == pytest.approx(3.0)
    assert float(root.get("LabelSize")) == pytest.approx(14.0)


def _arrow_length(root) -> float:
    arrow = next(root.iter("arrow"))
    head = [float(v) for v in arrow.get("Head3D").split()[:2]]
    tail = [float(v) for v in arrow.get("Tail3D").split()[:2]]
    return ((head[0] - tail[0]) ** 2 + (head[1] - tail[1]) ** 2) ** 0.5


def test_measured_arrow_length_raises_the_shortest_arrow(tmp_path, monkeypatch):
    from cdxml_toolkit.render import renderer
    short = {"species": SUZUKI["species"][:1] + SUZUKI["species"][2:],
             "steps": [{"substrates": ["ArBr"], "products": ["P"], "above": ["a"]}]}
    _measured_card(tmp_path, monkeypatch, {})
    _, plain = _draw(tmp_path, short)
    (tmp_path / "out.cdxml").unlink()
    _measured_card(tmp_path, monkeypatch, {"arrow_length_over_bond_length": 9.0})
    report, long = _draw(tmp_path, short)
    assert _arrow_length(long) > _arrow_length(plain) * 1.4
    assert _arrow_length(long) >= 9.0 * float(long.get("BondLength")) * 0.95
    assert renderer.MIN_ARROW_BONDS == 5.0
    assert any(a.startswith("measured.arrow_length") for a in report["style"]["applied"])
