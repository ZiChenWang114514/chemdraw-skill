"""Contracts of the scheme DSL: writer/parser keys, layout names, wrapping, routes, species."""
from __future__ import annotations

import inspect
import re
import xml.etree.ElementTree as ET

import pytest
import yaml

from cdxml_toolkit.render import renderer
from cdxml_toolkit.render.parser import parse_yaml
from cdxml_toolkit.render.route_graph import classify_route, convergent_sections, cycle_order
from cdxml_toolkit.render.schema import VALID_LAYOUTS, StepDescriptor
from cdxml_toolkit.render.scheme_yaml_writer import _build_yaml_dict


def _species():
    return [
        {"id": "sm", "role": "atom_contributing", "is_sm": True, "smiles": "c1ccccc1Br", "name": "PhBr"},
        {"id": "p", "role": "product", "smiles": "c1ccccc1C#N", "name": "PhCN"},
    ]


def test_writer_yield_survives_parsing():
    data = _build_yaml_dict(_species(), [], {"product_yield": "72%"}, include_run_arrows=False)

    scheme = parse_yaml(yaml.safe_dump(data))

    assert scheme.steps[0].yield_ == "72%"


def test_parser_accepts_the_old_yield_key_as_an_alias():
    text = "structures: {A: {smiles: CCO}, B: {smiles: CC=O}}\nsteps:\n  - {substrates: [A], products: [B], yield_: '50%'}\n"
    assert parse_yaml(text).steps[0].yield_ == "50%"


def test_every_valid_layout_has_a_renderer_and_every_renderer_is_valid():
    assert set(renderer.LAYOUT_RENDERERS) == set(VALID_LAYOUTS)
    source = inspect.getsource(renderer._render_impl)
    assert "scheme.layout ==" not in source


def test_a_cycle_layout_named_in_yaml_renders():
    text = """
layout: catalytic-cycle
structures: {A: {smiles: CCO}, B: {smiles: CC=O}, C: {smiles: CC(=O)O}}
steps:
  - {substrates: [A], products: [B]}
  - {substrates: [B], products: [C]}
  - {substrates: [C], products: [A]}
"""
    cdxml = renderer.render(parse_yaml(text))
    assert cdxml.count("<arrow") >= 3


def test_serpentine_uses_the_automatic_steps_per_row():
    text = """
layout: sequential
wrap: serpentine
max_row_width: 300
structures:
  A: {smiles: "c1ccccc1C(=O)O"}
  B: {smiles: "c1ccccc1C(=O)OC"}
  C: {smiles: "c1ccccc1C(=O)N"}
  D: {smiles: "c1ccccc1C#N"}
steps:
  - {substrates: [A], products: [B]}
  - {substrates: [B], products: [C]}
  - {substrates: [C], products: [D]}
"""
    cdxml = renderer.render(parse_yaml(text))
    root = ET.fromstring(cdxml[cdxml.index("<CDXML"):])
    heights = {round(float(a.get("Tail3D").split()[1])) for a in root.iter("arrow")}
    assert len(heights) > 1


def _steps(*pairs):
    return [StepDescriptor(substrates=s.split("+"), products=p.split("+"), id=f"s{i}")
            for i, (s, p) in enumerate(pairs, 1)]


def test_a_cyclic_route_is_refused_with_a_clear_error():
    steps = _steps(("A", "B"), ("B", "C"), ("C", "A"))
    with pytest.raises(ValueError, match="cycle"):
        convergent_sections(steps)


def test_a_cycle_with_a_tail_is_refused():
    steps = _steps(("X", "A"), ("A+C", "B"), ("B", "C"))
    with pytest.raises(ValueError, match="cycle"):
        classify_route(steps)
    assert cycle_order(_steps(("A", "B"), ("B", "A"))) == [0, 1]


def test_page_follows_the_content_with_a_margin():
    text = "structures: {A: {smiles: CCO}, B: {smiles: CC=O}}\nsteps:\n  - {substrates: [A], products: [B]}\n"
    cdxml = renderer.render(parse_yaml(text))
    root = ET.fromstring(cdxml[cdxml.index("<CDXML"):])
    page = root.find("page")
    xs = [float(n.get("p").split()[0]) for n in root.iter("n")]
    ys = [float(n.get("p").split()[1]) for n in root.iter("n")]
    width, height = float(page.get("Width")), float(page.get("Height"))
    assert max(xs) < width < 1620
    assert max(ys) < height < 2160
    bbox = [float(v) for v in root.get("BoundingBox").split()]
    assert bbox[2] <= width and bbox[3] <= height


# --- bare species: structure or name ---------------------------------------

def _structures(text):
    return parse_yaml(text).structures


def test_bare_smiles_in_an_arrow_list_is_a_structure():
    text = ("steps:\n  - substrates: [c1ccccc1Br]\n    products: [c1ccccc1-c1ccccc1]\n"
            "    above_arrow: [OB(O)c1ccccc1]\n")
    refs = _structures(text)
    assert refs["OB(O)c1ccccc1"].smiles == "OB(O)c1ccccc1"


@pytest.mark.parametrize("name", ["Boc2O", "CO2Me", "Bn", "DMF"])
def test_abbreviations_stay_names(name):
    text = f"steps:\n  - substrates: [c1ccccc1O]\n    products: [{name}]\n"
    ref = _structures(text)[name]
    assert ref.smiles is None


def test_letter_only_smiles_that_is_not_a_known_name_is_a_structure():
    text = "steps:\n  - substrates: [CCCO]\n    products: [CCC=O]\n"
    refs = _structures(text)
    assert any(r.smiles == "CCCO" for r in refs.values())
