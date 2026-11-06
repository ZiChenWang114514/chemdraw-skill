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
