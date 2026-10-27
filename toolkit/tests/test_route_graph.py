from __future__ import annotations

import pytest

from cdxml_toolkit.render.route_graph import classify_route, convergent_sections
from cdxml_toolkit.render.schema import StepDescriptor


def _steps(*pairs):
    """('A+B', 'C') -> a step; ids are single letters."""
    return [StepDescriptor(substrates=list(s.split("+")), products=list(p.split("+")), id=f"s{i}")
            for i, (s, p) in enumerate(pairs, 1)]


def _ids(sections):
    return [[step.id for step in section] for section in sections]


def test_a_single_step_is_linear():
    assert classify_route(_steps(("A+B", "C"))) == ("linear", [0])


def test_a_chain_is_linear_whatever_order_it_is_given_in():
    steps = _steps(("C", "D"), ("A", "B"), ("B", "C"))

    kind, order = classify_route(steps)

    assert kind == "linear"
    assert [steps[i].id for i in order] == ["s2", "s3", "s1"]


def test_two_arms_meeting_in_one_step_are_convergent():
    steps = _steps(("A", "B"), ("C", "D"), ("B+D", "E"))

    assert classify_route(steps)[0] == "convergent"
    assert _ids(convergent_sections(steps)) == [["s1"], ["s2"], ["s3"]]


def test_a_chain_after_the_merge_stays_in_the_merge_row():
    steps = _steps(("A", "B"), ("C", "D"), ("B+D", "E"), ("E", "F"))

    assert _ids(convergent_sections(steps)) == [["s1"], ["s2"], ["s3", "s4"]]


def test_a_chain_before_the_merge_stays_in_its_arm():
    steps = _steps(("A", "B"), ("B", "C"), ("X", "D"), ("C+D", "E"))

    assert _ids(convergent_sections(steps)) == [["s1", "s2"], ["s3"], ["s4"]]


def test_a_merge_inside_an_arm_is_laid_out_before_the_final_merge():
    steps = _steps(("A", "B"), ("B+C", "D"), ("E", "F"), ("D+F", "G"))

    assert _ids(convergent_sections(steps)) == [["s1", "s2"], ["s3"], ["s4"]]


def test_one_starting_material_giving_several_products_is_divergent():
    steps = _steps(("A", "B"), ("A", "C"), ("A", "D"))

    assert classify_route(steps)[0] == "divergent"


@pytest.mark.parametrize(
    "pairs, fragment",
    [
        ((("A", "B"), ("C", "B")), "more than one step"),
        ((("A", "B"), ("B", "A")), "cycle"),
        ((("A", "B"), ("A", "C"), ("B+C", "D")), "not a linear"),
        ((("A", "B"), ("C", "D")), "not a linear"),
    ],
)
def test_routes_that_are_none_of_these_are_refused(pairs, fragment):
    with pytest.raises(ValueError, match=fragment):
        classify_route(_steps(*pairs))


def test_convergent_sections_refuse_a_route_that_is_not_convergent():
    with pytest.raises(ValueError):
        convergent_sections(_steps(("A", "B"), ("A", "C")))
