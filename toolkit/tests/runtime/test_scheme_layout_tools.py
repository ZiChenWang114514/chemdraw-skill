from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

from cdxml_toolkit.cdxml_utils import drawn_fragment_bbox
from cdxml_toolkit.mcp_runtime import extended_tools as tools
from cdxml_toolkit.mcp_runtime import figure_lint

DATA = Path(__file__).parent / "data"
ASPIRIN = DATA / "aspirin-step.cdxml"
TAUTOMER = DATA / "tautomer-step.cdxml"


def _root(path):
    text = Path(path).read_text(encoding="utf-8")
    return text, ET.fromstring(text[text.index("<CDXML"):])


def _page(root):
    return {el.get("id"): el for el in root.find("page")}


def _text(el):
    return "".join(el.itertext()).strip()


def _box(el):
    if el.tag == "fragment":
        return drawn_fragment_bbox(el)
    return tuple(float(v) for v in el.get("BoundingBox").split())


def _arrow_y(arrow):
    return float(arrow.get("Head3D").split()[1])


def _labels_follow_atoms(root):
    for n in root.iter("n"):
        x, y = (float(v) for v in n.get("p").split()[:2])
        for t in n.findall("t"):
            tx, ty = (float(v) for v in t.get("p").split()[:2])
            assert abs(tx - x) < 8 and abs(ty - y) < 8, (n.get("id"), (x, y), (tx, ty))


def _assert_plus_clears_the_reactants(root):
    page = _page(root)
    step = root.find(".//step")
    first, second = (page[i] for i in step.get("ReactionStepReactants").split())
    plus = next(el for el in page.values() if el.tag == "t" and _text(el) == "+")
    # The "+" clears the OH of the first reactant and the second reactant, with room to spare.
    assert _box(first)[2] + 5 < _box(plus)[0] and _box(plus)[2] + 5 < _box(second)[0]


def test_cleanup_puts_the_plus_between_the_species_and_keeps_conditions_in_place(tmp_path):
    out = tmp_path / "clean.cdxml"
    tools.clean_scheme_layout(str(ASPIRIN), str(out), render_preview=False)
    text, root = _root(out)
    assert figure_lint.lint_cdxml(text) == []
    _assert_plus_clears_the_reactants(root)
    page = _page(root)
    step = root.find(".//step")
    arrow = page[step.get("ReactionStepArrows")]
    above = page[step.get("ReactionStepObjectsAboveArrow")]
    assert _text(above).startswith("H2SO4") and _box(above)[3] <= _arrow_y(arrow)


def test_polish_lists_the_merged_conditions_below_the_arrow(tmp_path):
    out = tmp_path / "polish.cdxml"
    tools.polish_reaction_scheme(str(ASPIRIN), str(out), render_preview=False)
    text, root = _root(out)
    assert figure_lint.lint_cdxml(text) == []
    _assert_plus_clears_the_reactants(root)
    page = _page(root)
    step = root.find(".//step")
    arrow = page[step.get("ReactionStepArrows")]
    below = [page[i] for i in step.get("ReactionStepObjectsBelowArrow", "").split()]
    above = [page[i] for i in step.get("ReactionStepObjectsAboveArrow", "").split()]
    assert not [el for el in above if el.tag == "t"]
    block = next(el for el in below if el.tag == "t")
    assert "H2SO4" in _text(block) and _box(block)[1] >= _arrow_y(arrow)
    # Atom labels move with their atoms when a structure is cleaned or turned.
    _labels_follow_atoms(root)
    # A fragment's box is what it draws, not a margin reaching into its neighbours.
    for frag in root.iter("fragment"):
        if frag.get("BoundingBox"):
            written = tuple(float(v) for v in frag.get("BoundingBox").split())
            drawn = drawn_fragment_bbox(frag)
            assert all(abs(a - b) < 7.5 for a, b in zip(written, drawn)), (frag.get("id"), written, drawn)


def test_adjacent_merge_moves_each_scheme_whole_and_keeps_its_step(tmp_path):
    out = tmp_path / "merged.cdxml"
    tools.merge_reaction_schemes([str(ASPIRIN), str(TAUTOMER)], str(out), mode="adjacent",
                                 render_preview=False)
    text, root = _root(out)
    assert figure_lint.lint_cdxml(text) == []
    page = _page(root)
    steps = list(root.iter("step"))
    assert len(steps) == 2
    seen = set()
    for step in steps:
        ids = {attr: step.get(attr).split() for attr in step.attrib if attr.startswith("ReactionStep")}
        assert all(i in page for refs in ids.values() for i in refs), ids
        reactants = [_box(page[i]) for i in ids["ReactionStepReactants"]]
        products = [_box(page[i]) for i in ids["ReactionStepProducts"]]
        arrow = page[ids["ReactionStepArrows"][0]]
        tail, head = (float(arrow.get(k).split()[0]) for k in ("Tail3D", "Head3D"))
        # The arrow still runs from this step's reactants to its products.
        assert max(b[2] for b in reactants) < min(tail, head) and max(tail, head) < min(b[0] for b in products)
        seen.update(ids["ReactionStepReactants"])
    assert len(seen) == 3


def test_drawn_fragment_box_covers_whole_labels():
    frag = ET.fromstring(
        '<fragment><n id="1" p="0 0"/><n id="2" p="20 0">'
        '<t p="17 4" BoundingBox="17 -4 23 4"><s>OH</s></t></n></fragment>'
    )
    # The label box names only the O; the H is drawn on the far side of the structure.
    assert drawn_fragment_bbox(frag) == (0.0, -4.0, 29.0, 4.0)
