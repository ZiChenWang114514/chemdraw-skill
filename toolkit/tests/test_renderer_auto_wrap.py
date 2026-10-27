from __future__ import annotations

import xml.etree.ElementTree as ET

from cdxml_toolkit.render import renderer
from cdxml_toolkit.render.compact_parser import parse_compact
from cdxml_toolkit.render.parser import parse_yaml

FOUR_STEPS = """
layout: sequential
{extra}
structures:
  A: {{smiles: "c1ccccc1C(=O)O", label: "1"}}
  B: {{smiles: "c1ccccc1C(=O)OC", label: "2"}}
  C: {{smiles: "c1ccccc1C(=O)N", label: "3"}}
  D: {{smiles: "c1ccccc1C#N", label: "4"}}
  E: {{smiles: "c1ccccc1C", label: "5"}}
steps:
  - {{substrates: [A], products: [B], above_arrow: {{text: ["MeOH, H2SO4"]}}}}
  - {{substrates: [B], products: [C], above_arrow: {{text: ["NH3, MeOH"]}}}}
  - {{substrates: [C], products: [D], above_arrow: {{text: ["POCl3, 80 C"]}}}}
  - {{substrates: [D], products: [E], above_arrow: {{text: ["H2, Pd/C"]}}}}
"""


def _render(tmp_path, extra=""):
    source = tmp_path / "scheme.yaml"
    source.write_text(FOUR_STEPS.format(extra=extra), encoding="utf-8")
    cdxml = renderer.render(parse_yaml(str(source)))
    return ET.fromstring(cdxml[cdxml.index("<CDXML"):])


def _rows(root) -> int:
    """Number of distinct arrow heights, i.e. rows of the scheme."""
    return len({round(float(a.get("Tail3D").split()[1])) for a in root.iter("arrow")})


def _right_edge(root) -> float:
    return max(float(n.get("p").split()[0]) for n in root.iter("n"))


def test_without_a_budget_the_row_is_left_alone(tmp_path):
    assert _rows(_render(tmp_path)) == 1


def test_budget_wraps_a_long_row(tmp_path):
    root = _render(tmp_path, extra="max_row_width: 420")

    assert _rows(root) > 1
    # Rows start at 80 pt; every structure must stay inside the budget.
    assert _right_edge(root) <= 80 + 420


def test_a_generous_budget_keeps_one_row(tmp_path):
    assert _rows(_render(tmp_path, extra="max_row_width: 5000")) == 1


def test_an_explicit_steps_per_row_wins_over_the_budget(tmp_path):
    root = _render(tmp_path, extra="steps_per_row: 4\nmax_row_width: 100")

    assert _rows(root) == 1


def test_compact_text_accepts_the_budget():
    text = "@max_row_width 400\nA{c1ccccc1C(=O)O} --> B{c1ccccc1C(=O)OC} --> C{c1ccccc1C(=O)N}"
    scheme = parse_compact(text)

    assert scheme.max_row_width == 400.0
