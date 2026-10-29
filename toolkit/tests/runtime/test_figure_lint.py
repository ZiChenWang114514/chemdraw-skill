from __future__ import annotations

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
