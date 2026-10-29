from __future__ import annotations

import re

from cdxml_toolkit.mcp_runtime import figure_lint


def _page(*elements: str) -> str:
    return '<CDXML><page id="1">' + "".join(elements) + "</page></CDXML>"


def _fragment(ident, x1, y1, x2, y2, label_box=None):
    inner = ""
    if label_box:
        inner = (f'<n id="{ident}1" p="{x1} {y1}"><t id="{ident}2" p="{x1} {y1}" '
                 f'BoundingBox="{label_box}"><s size="10">OH</s></t></n>')
    return f'<fragment id="{ident}" BoundingBox="{x1} {y1} {x2} {y2}">{inner}</fragment>'


def _text(ident, x1, y1, x2, y2, size=10, body="text"):
    return (f'<t id="{ident}" p="{x1} {y2}" BoundingBox="{x1} {y1} {x2} {y2}">'
            f'<s size="{size}">{body}</s></t>')


def _arrow(ident, x1, x2, y):
    return (f'<arrow id="{ident}" BoundingBox="{x1} {y - 4} {x2} {y + 4}" '
            f'Tail3D="{x1} {y} 0" Head3D="{x2} {y} 0"/>')


def _kinds(issues):
    return sorted(issue["kind"] for issue in issues)


def test_a_clean_scheme_has_no_issues():
    cdxml = _page(
        _fragment("1", 100, 270, 150, 330),
        _text("2", 165, 295, 170, 305, body="+"),
        _fragment("3", 185, 270, 240, 330),
        _arrow("4", 260, 330, 300),
        _text("5", 270, 280, 320, 292),
        _text("6", 270, 308, 320, 320),
        _fragment("7", 350, 270, 400, 330),
    )

    assert figure_lint.lint_cdxml(cdxml) == []


def test_label_overhang_counts_as_part_of_the_structure():
    # The OH label sticks out of the fragment box and touches the plus sign.
    cdxml = _page(
        _fragment("1", 100, 270, 150, 330, label_box="146 300 156 310"),
        _text("2", 155, 295, 160, 305, body="+"),
        _fragment("3", 175, 270, 230, 330),
    )

    assert "overlap" in _kinds(figure_lint.lint_cdxml(cdxml))


def test_two_structures_that_overlap_are_reported():
    cdxml = _page(_fragment("1", 100, 270, 160, 330), _fragment("2", 150, 270, 210, 330))

    issues = figure_lint.lint_cdxml(cdxml)

    assert _kinds(issues) == ["overlap"]
    assert set(issues[0]["ids"]) == {"1", "2"}


def test_condition_text_on_the_arrow_shaft_is_reported():
    cdxml = _page(_arrow("1", 100, 200, 300), _text("2", 120, 296, 180, 308))

    assert _kinds(figure_lint.lint_cdxml(cdxml)) == ["overlap"]


def test_text_just_above_the_arrow_is_fine():
    cdxml = _page(_arrow("1", 100, 200, 300), _text("2", 120, 284, 180, 296))

    assert figure_lint.lint_cdxml(cdxml) == []


def test_an_arrow_through_a_structure_is_reported():
    cdxml = _page(_arrow("1", 100, 300, 300), _fragment("2", 150, 270, 210, 330))

    assert _kinds(figure_lint.lint_cdxml(cdxml)) == ["overlap"]


def test_small_text_is_reported():
    cdxml = _page(_text("1", 100, 100, 130, 106, size=5))

    assert _kinds(figure_lint.lint_cdxml(cdxml)) == ["small_text"]


def test_a_row_wider_than_the_budget_is_reported():
    cdxml = _page(_fragment("1", 80, 270, 130, 330), _fragment("2", 640, 270, 700, 330))

    issues = figure_lint.lint_cdxml(cdxml, max_width=504)

    assert _kinds(issues) == ["too_wide"]
    assert issues[0]["width"] > 504


def test_no_budget_means_no_width_check():
    cdxml = _page(_fragment("1", 80, 270, 130, 330), _fragment("2", 2000, 270, 2060, 330))

    assert figure_lint.lint_cdxml(cdxml) == []


def test_an_empty_page_is_reported():
    assert _kinds(figure_lint.lint_cdxml(_page())) == ["empty"]


def _atoms_fragment(ident, atoms, label=None):
    """A fragment drawn from atom points; ``label`` is (atom index, text, label box)."""
    nodes = []
    for n, (x, y) in enumerate(atoms):
        inner = ""
        if label and label[0] == n:
            inner = f'<t id="{ident}l" p="{x} {y}" BoundingBox="{label[2]}"><s size="10">{label[1]}</s></t>'
        nodes.append(f'<n id="{ident}{n}" p="{x} {y}">{inner}</n>')
    xs, ys = [x for x, _ in atoms], [y for _, y in atoms]
    return (f'<fragment id="{ident}" BoundingBox="{min(xs)} {min(ys)} {max(xs)} {max(ys)}">'
            + "".join(nodes) + "</fragment>")


def test_a_plus_away_from_the_species_is_reported():
    # Left behind at the top of the page when the species moved.
    cdxml = _page(
        _text("9", 60, 100, 65, 110, body="+"),
        _fragment("1", 100, 270, 150, 330),
        _fragment("3", 185, 270, 240, 330),
    )

    issues = figure_lint.lint_cdxml(cdxml)

    assert _kinds(issues) == ["stray_plus"]
    assert issues[0]["ids"] == ["9"]


def test_a_plus_off_the_line_of_its_species_is_reported():
    cdxml = _page(
        _fragment("1", 100, 270, 150, 330),
        _text("2", 165, 340, 170, 350, body="+"),
        _fragment("3", 185, 270, 240, 330),
    )

    assert _kinds(figure_lint.lint_cdxml(cdxml)) == ["stray_plus"]


def test_a_plus_far_from_one_neighbour_is_reported():
    cdxml = _page(
        _fragment("1", 100, 270, 150, 330),
        _text("2", 165, 295, 170, 305, body="+"),
        _fragment("3", 300, 270, 350, 330),
    )

    assert _kinds(figure_lint.lint_cdxml(cdxml)) == ["stray_plus"]


def test_a_plus_crowding_a_label_is_reported():
    # The label box names only the O of OH; the H reaches to x = 159, 1 pt from the plus.
    cdxml = _page(
        _atoms_fragment("1", [(110, 290), (150, 300)], label=(1, "OH", "147 296 153 304")),
        _text("2", 160, 295, 165, 305, body="+"),
        _fragment("3", 180, 270, 230, 330),
    )

    issues = figure_lint.lint_cdxml(cdxml)

    assert _kinds(issues) == ["crowded_plus"]
    assert issues[0]["ids"] == ["2"]


def test_a_plus_between_a_structure_and_a_reagent_name_is_fine():
    cdxml = _page(
        _fragment("1", 100, 270, 150, 330),
        _text("2", 165, 295, 170, 305, body="+"),
        _text("3", 185, 293, 210, 305, body="HCl"),
    )

    assert figure_lint.lint_cdxml(cdxml) == []


def _salt(apart):
    """Na+ and OH- in one fragment, ``apart`` pt between the atoms."""
    def ion(ident, x, element, hydrogens, text, charge):
        return (f'<n id="{ident}" p="{x} 300" Element="{element}" NumHydrogens="{hydrogens}" Charge="{charge}">'
                f'<t id="{ident}t" p="{x - 3} 303.5" BoundingBox="{x - 3} 292.5 {x + 3} 300">'
                f'<s size="10" face="96">{text}</s><s size="10" face="64">{"+" if charge > 0 else "-"}</s></t></n>')
    return _page(f'<fragment id="1" BoundingBox="100 300 {100 + apart} 300">'
                 + ion("2", 100, 8, 1, "OH", -1) + ion("3", 100 + apart, 11, 0, "Na", 1) + "</fragment>")


def test_two_labels_of_one_structure_that_run_together_are_reported():
    # RDKit put Na+ one bond from OH-: ChemDraw printed "OHNa+".
    issues = figure_lint.lint_cdxml(_salt(14.4))
    assert _kinds(issues) == ["label_clash"] and issues[0]["ids"] == ["1"]


def test_labels_with_room_between_them_are_fine():
    assert figure_lint.lint_cdxml(_salt(24.0)) == []


def _bent_chain(ident):
    """An L-shaped chain (100,200) -> (200,200) -> (200,300); its box is mostly empty."""
    atoms = [(100, 200), (150, 200), (200, 200), (200, 250), (200, 300)]
    nodes = "".join(f'<n id="{ident}{n}" p="{x} {y}"/>' for n, (x, y) in enumerate(atoms))
    bonds = "".join(f'<b id="{ident}b{n}" B="{ident}{n}" E="{ident}{n + 1}"/>' for n in range(len(atoms) - 1))
    return f'<fragment id="{ident}" BoundingBox="100 200 200 300">{nodes}{bonds}</fragment>'


def test_text_in_the_empty_corner_of_a_bent_structure_is_fine():
    # A paper figure puts the arrow and its conditions beside a concave molecule.
    cdxml = _page(_bent_chain("1"), _text("9", 110, 260, 180, 272, body="reflux"),
                  _arrow("8", 120, 190, 285))

    assert figure_lint.lint_cdxml(cdxml) == []


def test_text_across_a_bond_of_a_bent_structure_is_reported():
    cdxml = _page(_bent_chain("1"), _text("9", 170, 240, 230, 252, body="reflux"))

    assert _kinds(figure_lint.lint_cdxml(cdxml)) == ["overlap"]


def test_structures_whose_boxes_interlock_without_touching_are_fine():
    # A second chain sits inside the first one's corner.
    atoms = [(110, 290), (150, 290), (190, 290), (190, 250)]
    nodes = "".join(f'<n id="2{n}" p="{x} {y}"/>' for n, (x, y) in enumerate(atoms))
    bonds = "".join(f'<b id="2b{n}" B="2{n}" E="2{n + 1}"/>' for n in range(3))
    cdxml = _page(_bent_chain("1"), f'<fragment id="2" BoundingBox="110 250 190 290">{nodes}{bonds}</fragment>')

    assert figure_lint.lint_cdxml(cdxml) == []


def test_text_boxes_that_only_share_their_line_spacing_are_fine():
    # A text box includes line spacing: stacked lines and a caption next to
    # an arrow may touch by a fraction of a point.
    cdxml = _page(_text("1", 100, 140, 150, 153.8, body="Et2O"), _text("2", 102, 153.5, 148, 167, body="air"),
                  _text("3", 200, 179, 206, 187, body="D"), _arrow("4", 180, 240, 190.8))

    assert figure_lint.lint_cdxml(cdxml) == []


def test_an_atom_number_beside_a_bond_is_fine():
    cdxml = _page(_bent_chain("1"), _text("9", 160, 200.5, 166, 208, body="5"))

    assert figure_lint.lint_cdxml(cdxml) == []


def test_objects_without_a_stored_box_are_measured():
    # ChemDraw computes boxes on open, so a written CDXML may store none.
    def strip(xml):
        return re.sub(r' BoundingBox="[^"]*"', "", xml)

    clean = _page(strip(_bent_chain("1")), strip(_arrow("2", 220, 290, 250)),
                  '<t id="3" p="300 254"><s size="10">2</s></t>')
    clashing = _page(strip(_bent_chain("1")), strip(_arrow("2", 150, 250, 250)))

    assert figure_lint.lint_cdxml(clean) == []
    assert _kinds(figure_lint.lint_cdxml(clashing)) == ["overlap"]


def test_measured_text_uses_narrow_punctuation_and_small_scripts():
    # "MsCl, Et3N" in 13 pt ends about 64 pt from its anchor, clear of an arrow at 64.5.
    text = ('<t id="1" p="0 147"><s size="13">MsCl, Et</s><s size="13" face="32">3</s>'
            '<s size="13">N</s></t>')
    cdxml = _page(text, '<arrow id="2" Tail3D="68.5 132 0" Head3D="68.5 160 0"/>')

    assert figure_lint.lint_cdxml(cdxml) == []


def test_a_headless_stroke_drawn_on_a_structure_is_fine():
    stroke = '<arrow id="2" Tail3D="150 199 0" Head3D="152 201 0" ArrowheadHead="None"/>'

    assert figure_lint.lint_cdxml(_page(_bent_chain("1"), stroke)) == []


def test_text_close_above_the_shaft_but_clear_of_the_head_is_fine():
    # The box of an arrow is as tall as its head; along the shaft only the line counts.
    cdxml = _page(_arrow("1", 100, 260, 300), _text("2", 120, 285, 200, 298, body="K2CO3"))

    assert figure_lint.lint_cdxml(cdxml) == []


def test_text_on_the_arrowhead_is_reported():
    cdxml = _page(_arrow("1", 100, 260, 300), _text("2", 240, 285, 300, 298, body="K2CO3"))

    assert _kinds(figure_lint.lint_cdxml(cdxml)) == ["overlap"]


def test_an_arrowhead_is_as_wide_as_the_arrow_says():
    # ArrowheadWidth and HeadSize are hundredths of the line width: a 0.6 pt
    # ACS arrow has a head 1.5 pt half-wide, clear of text 2 pt above the shaft.
    arrow = ('<arrow id="1" Tail3D="260 300 0" Head3D="100 300 0" ArrowheadHead="Full" '
             'HeadSize="1000" ArrowheadWidth="250" LineWidth="0.6"/>')

    assert figure_lint.lint_cdxml(_page(arrow, _text("2", 102, 285, 160, 298, body="HC(OMe)3"))) == []
