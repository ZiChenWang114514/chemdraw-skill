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
    # Each scheme is kept as drawn: the merge adds no problem its inputs did not have.
    drawn = [i["kind"] for path in (ASPIRIN, TAUTOMER) for i in figure_lint.lint_cdxml(_root(path)[0])]
    assert sorted(i["kind"] for i in figure_lint.lint_cdxml(text)) == sorted(drawn)
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
    assert drawn_fragment_bbox(frag) == (0.0, -4.0, 30.0, 4.0)


def test_drawn_fragment_box_counts_a_charge_as_a_small_sign():
    frag = ET.fromstring(
        '<fragment><n id="1" p="0 0"><t p="-3 4" BoundingBox="-3 -4 3 4">'
        '<s face="96">OH</s><s face="64">-</s></t></n></fragment>'
    )
    # The superscript charge is narrower than a letter, as the renderer spaces it.
    assert drawn_fragment_bbox(frag)[2] == 3.0 + 7.0 + 4.0
    # In formula style the count of NH2 is a subscript too.
    frag = ET.fromstring('<fragment><n id="1" p="0 0"><t p="-3 4" BoundingBox="-3 -4 3 4">'
                         '<s face="96">NH2</s></t></n></fragment>')
    assert drawn_fragment_bbox(frag)[2] == 3.0 + 7.0 + 4.0


ROUTE = DATA / "four-step-route-untidy.cdxml"


def _rows(root):
    """Per step: its box (species, arrow, conditions) and its arrow y."""
    page = _page(root)
    rows = []
    for step in root.iter("step"):
        ids = [i for attr in step.attrib if attr.startswith("ReactionStep") and attr != "ReactionStepArrows"
               for i in step.get(attr).split()]
        boxes = [_box(page[i]) for i in ids]
        arrow = page[step.get("ReactionStepArrows")]
        rows.append((step, [min(b[0] for b in boxes), min(b[1] for b in boxes),
                            max(b[2] for b in boxes), max(b[3] for b in boxes)], _arrow_y(arrow)))
    return page, rows


def _compound_numbers_hang_under_their_structures(root):
    page = _page(root)
    numbers = [el for el in page.values() if el.tag == "t" and _text(el).isdigit()]
    assert len(numbers) == 8
    for t in numbers:
        x, y = (float(v) for v in t.get("p").split()[:2])
        owners = []
        for frag in (el for el in page.values() if el.tag == "fragment"):
            xs = [float(n.get("p").split()[0]) for n in frag.findall("n")]
            ys = [float(n.get("p").split()[1]) for n in frag.findall("n")]
            if min(xs) <= x <= max(xs) and 5 <= y - max(ys) <= 25:
                owners.append(frag.get("id"))
        assert len(owners) == 1, (_text(t), owners)


def test_cleanup_lays_out_every_step_of_a_route(tmp_path):
    out = tmp_path / "clean.cdxml"
    tools.clean_scheme_layout(str(ROUTE), str(out), render_preview=False)
    text, root = _root(out)
    assert figure_lint.lint_cdxml(text) == []
    page, rows = _rows(root)
    assert len(rows) == 4
    for step, _, arrow_y in rows:
        # Every species of every step sits on its arrow, not only the first step's.
        for i in step.get("ReactionStepReactants").split() + step.get("ReactionStepProducts").split():
            box = _box(page[i])
            assert abs((box[1] + box[3]) / 2 - arrow_y) < 6, (step.get("id"), i)
    _compound_numbers_hang_under_their_structures(root)
    # The rows share a left edge and are spaced evenly.
    lefts = [box[0] for _, box, _ in rows]
    assert max(lefts) - min(lefts) < 1
    arrows = [arrow_y for _, _, arrow_y in rows]
    pitches = [b - a for a, b in zip(arrows, arrows[1:])]
    assert all(60 < p < 110 for p in pitches), pitches


def test_polish_tidies_the_conditions_of_every_step(tmp_path):
    out = tmp_path / "polish.cdxml"
    tools.polish_reaction_scheme(str(ROUTE), str(out), render_preview=False)
    text, root = _root(out)
    assert figure_lint.lint_cdxml(text) == []
    page, rows = _rows(root)
    for step, _, arrow_y in rows:
        above = [page[i] for i in step.get("ReactionStepObjectsAboveArrow", "").split()]
        below = [page[i] for i in step.get("ReactionStepObjectsBelowArrow", "").split()]
        assert not [el for el in above if el.tag == "t"], step.get("id")
        assert len([el for el in below if el.tag == "t"]) == 1, step.get("id")
    _compound_numbers_hang_under_their_structures(root)


def test_cleanup_leaves_a_step_that_shares_a_species_with_an_earlier_one(tmp_path):
    from cdxml_toolkit.layout.reaction_cleanup import run_cleanup

    text, root = _root(ROUTE)
    first, second = list(root.iter("step"))[:2]
    # Draw the second step from the first step's product itself, as in A -> B -> C on one row.
    second.set("ReactionStepReactants", first.get("ReactionStepProducts"))
    source = tmp_path / "shared.cdxml"
    source.write_text(text[:text.index("<CDXML")] + ET.tostring(root, encoding="unicode"), encoding="utf-8")
    info = run_cleanup(str(source), str(tmp_path / "out.cdxml"))
    assert info["skipped_steps"] == [second.get("id")]
    assert info["num_steps"] == 3 and info["rows_normalized"] is False


def test_cleanup_itself_moves_compound_numbers_with_their_structures(tmp_path):
    from cdxml_toolkit.layout.reaction_cleanup import run_cleanup

    out = tmp_path / "out.cdxml"
    info = run_cleanup(str(ROUTE), str(out))
    assert info["num_steps"] == 4 and info["rows_normalized"] is True
    _, root = _root(out)
    _compound_numbers_hang_under_their_structures(root)


def test_sequential_merge_keeps_numbers_plus_signs_and_conditions_in_place(tmp_path):
    out = tmp_path / "route.cdxml"
    steps = [str(DATA / f"route-step{n}.cdxml") for n in range(1, 5)]
    tools.merge_reaction_schemes(steps, str(out), mode="sequential", render_preview=False)
    text, root = _root(out)
    assert figure_lint.lint_cdxml(text) == []
    _assert_plus_clears_the_reactants(root)
    page = _page(root)
    numbers = sorted(_text(el) for el in page.values() if el.tag == "t" and _text(el).isdigit())
    # One number per compound: the shared intermediates are drawn once, with one number.
    assert numbers == ["1", "2", "3", "4", "5"]
    arrow_y = _rows(root)[1][0][2]
    for t in (el for el in page.values() if el.tag == "t" and _text(el).isdigit()):
        # Each number hangs under the row, not at the height of its old file.
        assert 0 < float(t.get("p").split()[1]) - arrow_y < 40, _text(t)
    for step, _, arrow_y in _rows(root)[1]:
        above = [page[i] for i in step.get("ReactionStepObjectsAboveArrow", "").split()]
        below = [page[i] for i in step.get("ReactionStepObjectsBelowArrow", "").split()]
        assert not [el for el in above if el.tag == "t"]
        assert all(_box(el)[1] >= arrow_y for el in below if el.tag == "t")


def _step_with_a_reagent_beside_the_intermediate(tmp_path, reagent_first):
    """route-step2 with a second reactant, joined to the shared intermediate by a "+"."""
    import copy

    _, first = _root(DATA / "route-step1.cdxml")
    first_page = _page(first)
    reagent, plus = copy.deepcopy(first_page["1035"]), copy.deepcopy(first_page["1033"])
    for el in (reagent, plus):
        for node in el.iter():
            # Atom and bond ids, and the atoms a bond joins, move together.
            for attr in ("id", "B", "E"):
                if node.get(attr, "").isdigit():
                    node.set(attr, str(int(node.get(attr)) + 7000))
    head_text = (DATA / "route-step2.cdxml").read_text(encoding="utf-8")
    root = ET.fromstring(head_text[head_text.index("<CDXML"):])
    page = root.find("page")
    intermediate = _page(root)["1156"]
    x0, y0, x1, y1 = drawn_fragment_bbox(intermediate)
    rx0, ry0, rx1, ry1 = drawn_fragment_bbox(reagent)
    dx = (x0 - 40 - rx1) if reagent_first else (x1 + 40 - rx0)
    dy = (y0 + y1) / 2 - (ry0 + ry1) / 2
    for node in reagent.iter():
        if node.get("p"):
            a = node.get("p").split()
            node.set("p", f"{float(a[0]) + dx:.2f} {float(a[1]) + dy:.2f}")
        node.attrib.pop("BoundingBox", None)
    plus.set("p", f"{(x0 - 20) if reagent_first else (x1 + 20):.2f} {(y0 + y1) / 2:.2f}")
    plus.attrib.pop("BoundingBox", None)
    at = list(page).index(intermediate) + 1
    page.insert(at, reagent)
    page.insert(at, plus)
    ids = f"{reagent.get('id')} 1156" if reagent_first else f"1156 {reagent.get('id')}"
    root.find(".//step").set("ReactionStepReactants", ids)
    path = tmp_path / "step2-with-reagent.cdxml"
    path.write_text(head_text[:head_text.index("<CDXML")] + ET.tostring(root, encoding="unicode"),
                    encoding="utf-8")
    return path


def test_sequential_merge_keeps_a_plus_between_the_shared_intermediate_and_its_partner(tmp_path):
    for reagent_first in (False, True):
        step2 = _step_with_a_reagent_beside_the_intermediate(tmp_path, reagent_first)
        out = tmp_path / f"route-{reagent_first}.cdxml"
        tools.merge_reaction_schemes([str(DATA / "route-step1.cdxml"), str(step2)], str(out),
                                     mode="sequential", render_preview=False)
        text, root = _root(out)
        assert figure_lint.lint_cdxml(text) == [], reagent_first
        page = _page(root)
        second = list(root.iter("step"))[1]
        left, right = sorted((page[i] for i in second.get("ReactionStepReactants").split()),
                             key=lambda el: _box(el)[0])
        plus = [tuple(float(v) for v in el.get("p").split()[:2]) for el in page.values()
                if el.tag == "t" and _text(el) == "+" and float(el.get("p").split()[0]) > _box(left)[0] - 1]
        assert len(plus) == 1, reagent_first
        # The "+" sits in the gap between the two reactants, clear of both, on their line.
        (px, py), gap = plus[0], (_box(left)[2], _box(right)[0])
        assert gap[0] + 5 < px < gap[1] - 5, reagent_first
        assert abs(py - (_box(left)[1] + _box(left)[3]) / 2) < 25, reagent_first


def test_parallel_merge_says_when_a_run_with_other_conditions_is_not_drawn(tmp_path):
    other = tmp_path / "other-run.cdxml"
    other.write_text((DATA / "route-step2.cdxml").read_text(encoding="utf-8")
                     .replace("MeOH, 0 °C", "EtOH, rt"), encoding="utf-8")
    for mode in ("parallel", "auto"):
        result = tools.merge_reaction_schemes([str(DATA / "route-step2.cdxml"), str(other)],
                                              str(tmp_path / f"{mode}.cdxml"), mode=mode,
                                              render_preview=False)
        warnings = " ".join(result["warnings"])
        assert "EtOH, rt" in warnings and "not drawn" in warnings, (mode, result["warnings"])
    same = tools.merge_reaction_schemes([str(DATA / "route-step2.cdxml")] * 2,
                                        str(tmp_path / "same.cdxml"), mode="parallel",
                                        render_preview=False)
    assert not [w for w in same["warnings"] if "not drawn" in w]


def _lone_atom(element, hydrogens, text):
    return ET.fromstring(
        f'<fragment><n id="1" p="0 0" Element="{element}" NumHydrogens="{hydrogens}">'
        f'<t p="-3 4" BoundingBox="-3 -4 3 4" LabelJustification="Left"><s face="96">{text}</s></t>'
        '</n></fragment>'
    )


def test_a_lone_atom_label_reaches_the_side_chemdraw_draws_it_on():
    # ChemDraw for macOS writes water as H2O and HCl with the H first, right-aligned on
    # the atom; OH and NH3 keep the H after it (measured on ChemDraw 26.0).
    water = drawn_fragment_bbox(_lone_atom(8, 2, "OH2"))
    assert water[0] == -3.0 - 7.0 - 4.0 and water[2] == 3.0
    acid = drawn_fragment_bbox(_lone_atom(17, 1, "ClH"))
    assert acid[0] == -3.0 - 6.0 - 7.0 and acid[2] == 3.0
    ammonia = drawn_fragment_bbox(_lone_atom(7, 3, "NH3"))
    assert ammonia[0] == -3.0 and ammonia[2] == 3.0 + 7.0 + 4.0


def test_the_renderer_reserves_label_room_on_the_side_it_is_drawn():
    from cdxml_toolkit.render import renderer as R

    bromide = R._fragment_bbox([{"x": 0.0, "y": 0.0, "symbol": "Br", "charge": -1}])
    water = R._fragment_bbox([{"x": 0.0, "y": 0.0, "symbol": "O", "num_hydrogens": 2}])
    # Br- is drawn rightwards from the atom; nothing reaches to its left.
    assert bromide[0] == -R._FRAG_PAD_W and bromide[2] > 10
    assert water[0] <= -14.0 and water[2] == R._FRAG_PAD_W


def test_a_plus_before_water_keeps_its_room(tmp_path, monkeypatch):
    import json

    from cdxml_toolkit.mcp_runtime.figure_draw import draw_figure

    case = json.loads((Path(__file__).parent / "draw_corpus" / "15-sn1.json").read_text(encoding="utf-8"))
    monkeypatch.setenv("CHEMDRAW_OFFLINE", "1")
    report = draw_figure(case["brief"], output_path=str(tmp_path / "sn1.cdxml"))
    assert report["lint"]["issues"] == []


def test_drawn_figures_leave_the_same_room_beside_a_plus_as_cleanup(tmp_path, monkeypatch):
    import json

    from cdxml_toolkit.mcp_runtime.figure_draw import draw_figure

    monkeypatch.setenv("CHEMDRAW_OFFLINE", "1")
    # Cleanup leaves PLUS_CLEARANCE between species around a "+"; drawing does the same.
    monkeypatch.setattr(figure_lint, "PLUS_MIN_CLEARANCE", 5.0)
    for name in ("01-aspirin", "02-suzuki", "13-sn2", "15-sn1", "07-convergent-amide"):
        case = json.loads((Path(__file__).parent / "draw_corpus" / f"{name}.json").read_text(encoding="utf-8"))
        report = draw_figure(case["brief"], output_path=str(tmp_path / f"{name}.cdxml"))
        text = Path(report["output_path"]).read_text(encoding="utf-8")
        assert [i for i in figure_lint.lint_cdxml(text) if i["kind"].endswith("plus")] == [], name


def _row_gaps(root):
    """White space between consecutive rows of a figure, rows taken around its arrows."""
    page = list(root.find("page"))
    arrows = sorted({round(float(a.get("Head3D").split()[1]), 1) for a in root.iter("arrow")
                     if abs(float(a.get("Head3D").split()[1]) - float(a.get("Tail3D").split()[1])) < 1})
    bands = {y: [] for y in arrows}
    for el in page:
        if el.tag in ("scheme", "arrow") or not (el.tag == "fragment" or el.get("BoundingBox")):
            continue
        box = _box(el)
        middle = (box[1] + box[3]) / 2
        bands[min(arrows, key=lambda y: abs(y - middle))].append(box)
    return [min(b[1] for b in bands[low]) - max(b[3] for b in bands[high])
            for high, low in zip(arrows, arrows[1:])]


def test_a_wrapped_route_leaves_the_cleanup_gap_between_rows(tmp_path, monkeypatch):
    import json

    from cdxml_toolkit.layout.reaction_cleanup import ROW_GAP
    from cdxml_toolkit.mcp_runtime.figure_draw import draw_figure

    monkeypatch.setenv("CHEMDRAW_OFFLINE", "1")
    for name in ("04-wrapping-route", "07-convergent-amide"):
        case = json.loads((Path(__file__).parent / "draw_corpus" / f"{name}.json").read_text(encoding="utf-8"))
        report = draw_figure(case["brief"], output_path=str(tmp_path / f"{name}.cdxml"))
        gaps = _row_gaps(_root(report["output_path"])[1])
        assert len(gaps) >= 2 and all(abs(g - ROW_GAP) < 3 for g in gaps), (name, gaps)


def test_a_label_box_far_wider_than_its_text_is_measured_from_the_text():
    from cdxml_toolkit.cdxml_utils import label_boxes

    # A stale box (from 25 to 115) on a right-aligned "PMBO" at x=103.5: the text is ~30 pt.
    frag = ET.fromstring(
        '<fragment><n id="1" p="103.5 39.5" NodeType="Fragment"><t p="103.5 43" BoundingBox="25 30 115 44" '
        'LabelJustification="Right"><s face="96">PMBO</s></t></n><n id="2" p="118 31"/>'
        '<b B="1" E="2"/></fragment>'
    )
    (_, box), = label_boxes(frag)
    assert 60 < box[0] < 90 and 103.5 < box[2] < 110, box
