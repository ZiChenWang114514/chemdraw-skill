"""figure_lint: crossings between molecules, text over bonds, grouped objects and curved arrows."""
from cdxml_toolkit.mcp_runtime import figure_lint


def _frag(fid, a, b):
    return (f'<fragment id="{fid}"><n id="{fid}1" p="{a[0]} {a[1]}"/><n id="{fid}2" p="{b[0]} {b[1]}"/>'
            f'<b id="{fid}3" B="{fid}1" E="{fid}2"/></fragment>')


def _doc(*parts):
    return '<CDXML><page id="1">' + "".join(parts) + "</page></CDXML>"


def _kinds(issues):
    return {(i["kind"], tuple(sorted(i["ids"]))) for i in issues}


def test_bonds_of_two_molecules_that_cross_are_reported():
    issues = figure_lint.lint_cdxml(_doc(_frag(10, (0, 0), (40, 40)), _frag(20, (0, 40), (40, 0))))
    assert ("overlap", ("10", "20")) in _kinds(issues)


def test_a_text_label_over_a_bond_is_reported():
    issues = figure_lint.lint_cdxml(_doc(_frag(10, (0, 20), (60, 20)), '<t id="30" p="20 23"><s size="10">Ts</s></t>'))
    assert ("overlap", ("10", "30")) in _kinds(issues)


def test_objects_inside_a_group_are_checked():
    issues = figure_lint.lint_cdxml(_doc('<group id="5">' + _frag(10, (0, 0), (40, 40)) + "</group>",
                                         _frag(20, (0, 40), (40, 0))))
    assert ("overlap", ("10", "20")) in _kinds(issues)


CURVE = '<curve id="40" CurvePoints="0 0 0 0 20 -40 40 -40 60 0 60 0" ArrowheadHead="Full"/>'


def test_a_curved_arrow_through_a_structure_is_reported():
    issues = figure_lint.lint_cdxml(_doc(_frag(10, (30, -40), (30, -20)), CURVE))
    assert ("curve_collision", ("10", "40")) in _kinds(issues)


def test_a_curved_arrow_that_only_starts_and_ends_on_structures_passes():
    # Bonds at both ends of the arrow, none under its arc.
    issues = figure_lint.lint_cdxml(_doc(_frag(10, (-20, 0), (0, 0)), _frag(20, (60, 0), (80, 0)), CURVE))
    assert not [i for i in issues if i["kind"] == "curve_collision"]


def test_a_closed_fill_curve_is_not_an_arrow():
    fill = '<curve id="41" Closed="yes" CurvePoints="0 0 0 0 30 -40 60 0 60 0 60 0"/>'
    issues = figure_lint.lint_cdxml(_doc(_frag(10, (20, -25), (40, -25)), fill))
    assert not [i for i in issues if i["kind"] == "curve_collision"]
