"""Direct checks of the route arithmetic and of name alignment, against hand-worked answers."""

import pytest

from cdxml_toolkit import route_metrics
from cdxml_toolkit.naming import aligned_namer


def test_linear_route_yield_and_cumulative_pmi_by_hand():
    # Step 1 makes 500 mg, of which step 2 uses 250 mg: half of step 1 counts.
    # PMI = (1000 * 0.5 + 2000) / 200 = 12.5; overall yield = 0.8 * 0.5 = 40%.
    result = route_metrics.summarize([
        {"label": "1", "yield_percent": 80, "input_mg": 1000, "product_mg": 500, "used_mg": 250},
        {"label": "2", "yield_percent": 50, "input_mg": 2000, "product_mg": 200},
    ])
    assert result["overall_yield_percent"] == pytest.approx(40.0)
    assert result["cumulative_pmi"] == pytest.approx(12.5)
    assert result["cumulative_e_factor"] == pytest.approx(11.5)
    assert [row["scale"] for row in result["steps"]] == pytest.approx([0.5, 1.0])
    assert result["steps"][0]["step_pmi"] == pytest.approx(2.0)
    assert result["warnings"] == []


def test_using_all_of_an_intermediate_counts_all_of_its_inputs():
    result = route_metrics.summarize([
        {"yield_percent": 100, "input_mg": 300, "product_mg": 100, "used_mg": 100},
        {"yield_percent": 100, "input_mg": 400, "product_mg": 100},
    ])
    assert result["cumulative_pmi"] == pytest.approx(7.0)


def test_convergent_route_takes_the_longest_linear_sequence_and_sums_both_branches():
    result = route_metrics.summarize([
        {"label": "A", "into": "C", "yield_percent": 90, "input_mg": 100, "product_mg": 50, "used_mg": 50},
        {"label": "B", "into": "C", "yield_percent": 50, "input_mg": 200, "product_mg": 100, "used_mg": 25},
        {"label": "C", "yield_percent": 80, "input_mg": 300, "product_mg": 60},
    ])
    assert result["longest_sequence"] == ["A", "C"]
    assert result["overall_yield_percent"] == pytest.approx(72.0)
    # (100 * 1 + 200 * 0.25 + 300) / 60
    assert result["cumulative_pmi"] == pytest.approx(7.5)


def test_missing_numbers_are_named_not_guessed():
    with pytest.raises(ValueError, match="used_mg"):
        route_metrics.summarize([
            {"yield_percent": 80, "input_mg": 1000, "product_mg": 500},
            {"yield_percent": 50, "input_mg": 2000, "product_mg": 200},
        ])
    partial = route_metrics.summarize([{"label": "1", "input_mg": 10, "product_mg": 5}])
    assert partial["overall_yield_percent"] is None
    assert any("no yield for step 1" in warning for warning in partial["warnings"])
    no_mass = route_metrics.summarize([{"label": "1", "yield_percent": 120}])
    assert no_mass["cumulative_pmi"] is None
    assert any("above 100%" in warning for warning in no_mass["warnings"])
    assert any("PMI not calculated" in warning for warning in no_mass["warnings"])


@pytest.mark.parametrize("steps, message", [
    ([], "at least one step"),
    ([{"label": "a"}, {"label": "a"}], "Duplicate step label"),
    ([{"label": "a", "into": "z"}, {"label": "b"}], "no step called"),
    ([{"label": "a"}, {"label": "b", "into": "a"}, {"label": "c"}], "later step"),
    ([{"label": "a", "input_mg": -1}], "non-negative"),
    ([{"label": "a", "yield_percent": True}], "yield_percent"),
])
def test_malformed_routes_are_refused(steps, message):
    with pytest.raises(ValueError, match=message):
        route_metrics.summarize(steps)


def test_name_diff_reports_exactly_the_inserted_substituent():
    diff = aligned_namer.name_diff("4-chlorobenzoic acid", "4-chloro-2-fluorobenzoic acid")
    assert [part for part in diff if part[0] != "equal"] == [("insert", "", "-2-fluoro")]
    assert "".join(part[1] for part in diff) == "4-chlorobenzoic acid"
    assert "".join(part[2] for part in diff) == "4-chloro-2-fluorobenzoic acid"


def test_name_similarity_and_token_distance_are_zero_distance_for_identical_names():
    assert aligned_namer.name_similarity("ethanol", "ethanol") == 1.0
    assert aligned_namer.chem_token_diff_count("ethanol", "ethanol") == 0.0
    near = aligned_namer.name_similarity("4-chlorobenzoic acid", "4-chloro-2-fluorobenzoic acid")
    far = aligned_namer.name_similarity("4-chlorobenzoic acid", "cyclohexanone")
    assert 0 < far < near < 1
    assert aligned_namer.chem_token_diff_count("4-chlorobenzoic acid", "4-chloro-2-fluorobenzoic acid") > 0


def test_a_functional_group_change_is_shown_as_the_changed_suffix():
    assert aligned_namer.format_name_diff("ethanol", "ethanal") == "ol -> al"
    assert aligned_namer.extract_parent_ring("pyridine") == "pyridine"
