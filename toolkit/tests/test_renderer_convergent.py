from __future__ import annotations

import xml.etree.ElementTree as ET

import pytest

from cdxml_toolkit.mcp_runtime import figure_lint
from cdxml_toolkit.render import renderer
from cdxml_toolkit.render.parser import parse_yaml

CONVERGENT = """
layout: convergent
{extra}
structures:
  A: {{smiles: "OC(=O)c1ccccc1", label: "1"}}
  B: {{smiles: "ClC(=O)c1ccccc1", label: "2"}}
  C: {{smiles: "Nc1ccccc1", label: "3"}}
  D: {{smiles: "Cc1ccc(N)cc1", label: "4"}}
  E: {{smiles: "O=C(Nc1ccc(C)cc1)c1ccccc1", label: "5"}}
  F: {{smiles: "O=C(Nc1ccc(CO)cc1)c1ccccc1", label: "6"}}
steps:
  - {{substrates: [A], products: [B], above_arrow: {{text: ["SOCl2"]}}}}
  - {{substrates: [C], products: [D], above_arrow: {{text: ["Me-Br"]}}}}
  - {{substrates: [B, D], products: [E], above_arrow: {{text: ["Et3N, DCM"]}}, below_arrow: {{text: ["0 C to rt"]}}, yield_: "81%"}}
  - {{substrates: [E], products: [F], above_arrow: {{text: ["NBS"]}}}}
"""


def _render(tmp_path, extra=""):
    source = tmp_path / "scheme.yaml"
    source.write_text(CONVERGENT.format(extra=extra), encoding="utf-8")
    cdxml = renderer.render(parse_yaml(str(source)))
    return cdxml, ET.fromstring(cdxml[cdxml.index("<CDXML"):])


def _row_heights(root):
    return sorted({round(float(a.get("Tail3D").split()[1])) for a in root.iter("arrow")})


def test_the_arms_are_rows_and_the_merge_row_repeats_what_it_joins(tmp_path):
    cdxml, root = _render(tmp_path)

    assert len(_row_heights(root)) == 3
    # arm 1: A, B; arm 2: C, D; merge row: B, D, E, F
    assert len(list(root.iter("fragment"))) == 8
    assert cdxml.chemistry_validation["status"] == "preserved"


def test_the_arms_come_before_the_merge_in_reading_order(tmp_path):
    _, root = _render(tmp_path)

    rows = {}
    for arrow in root.iter("arrow"):
        y = round(float(arrow.get("Tail3D").split()[1]))
        rows.setdefault(y, []).append(arrow)
    merge_row = max(rows, key=lambda y: len(rows[y]))

    assert merge_row == max(rows)
    assert len(rows[merge_row]) == 2  # B + D -> E, then E -> F


def test_the_drawing_has_no_overlaps(tmp_path):
    cdxml, _ = _render(tmp_path)

    assert figure_lint.lint_cdxml(cdxml) == []


def test_a_width_budget_wraps_the_long_merge_row(tmp_path):
    _, root = _render(tmp_path, extra="max_row_width: 300")

    assert len(_row_heights(root)) == 4


def test_gap_scale_applies_to_every_row(tmp_path):
    def width(extra):
        _, root = _render(tmp_path, extra=extra)
        xs = [float(n.get("p").split()[0]) for n in root.iter("n")]
        return max(xs) - min(xs)

    assert width("gap_scale: 1.6") > width("") + 20


def test_a_route_that_is_not_convergent_is_refused(tmp_path):
    source = tmp_path / "scheme.yaml"
    source.write_text(
        'layout: convergent\nstructures:\n  A: {smiles: "CC"}\n  B: {smiles: "CCC"}\n  C: {smiles: "CCCC"}\n'
        "steps:\n  - {substrates: [A], products: [B]}\n  - {substrates: [A], products: [C]}\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="divergent"):
        renderer.render(parse_yaml(str(source)))
