import json

import pytest

from cdxml_toolkit.mcp_runtime.report_tools import route_summary
from cdxml_toolkit.mcp_runtime.tool_registry import build_registry


def step(label, **fields):
    return {'label': label, **fields}


def test_a_linear_route_chains_the_yields_and_scales_each_step_to_what_the_next_one_uses():
    result = route_summary([
        step('1', yield_percent=80, input_mg=1000, product_mg=200, used_mg=100),
        step('2', yield_percent=50, input_mg=500, product_mg=40),
    ])
    assert result['ok'] and result['step_count'] == 2
    assert result['overall_yield_percent'] == pytest.approx(40.0)
    assert result['longest_sequence'] == ['1', '2']
    # step 1 is run at half scale: its product (200 mg) is more than step 2 needs (100 mg)
    scales = {s['label']: s['scale'] for s in result['steps']}
    assert scales == {'1': pytest.approx(0.5), '2': pytest.approx(1.0)}
    assert result['cumulative_pmi'] == pytest.approx((1000 * 0.5 + 500) / 40.0, rel=1e-4)
    assert result['cumulative_e_factor'] == pytest.approx(result['cumulative_pmi'] - 1)
    assert result['lower_bound'] is False


def test_a_convergent_route_adds_both_branches_and_takes_the_longest_sequence_for_the_yield():
    result = route_summary([
        step('A', yield_percent=50, input_mg=100, product_mg=50, used_mg=25, into='C'),
        step('B', yield_percent=90, input_mg=200, product_mg=100, used_mg=100, into='C'),
        step('C', yield_percent=60, input_mg=300, product_mg=60),
    ])
    assert result['cumulative_pmi'] == pytest.approx((100 * 0.5 + 200 * 1.0 + 300) / 60.0, rel=1e-4)
    assert result['longest_sequence'] == ['A', 'C']
    assert result['overall_yield_percent'] == pytest.approx(30.0)
    assert result['step_count'] == 3


def test_a_longer_branch_decides_the_longest_sequence():
    result = route_summary([
        step('A', yield_percent=90, input_mg=10, product_mg=9, used_mg=9, into='B'),
        step('B', yield_percent=90, input_mg=10, product_mg=9, used_mg=9, into='D'),
        step('C', yield_percent=10, input_mg=10, product_mg=1, used_mg=1, into='D'),
        step('D', yield_percent=100, input_mg=10, product_mg=10),
    ])
    assert result['longest_sequence'] == ['A', 'B', 'D']
    assert result['overall_yield_percent'] == pytest.approx(81.0)


def test_steps_given_as_reactions_use_their_calculator_totals_and_find_the_intermediate_by_structure():
    result = route_summary([
        {'label': '1', 'reaction': {'reactants': [{'smiles': 'CC(=O)Cl'}, {'smiles': 'CCN'}],
                                    'products': [{'smiles': 'CC(=O)NCC', 'isolated_mg': 70.0}]},
         'options': {'scale_mmol': 1.0}},
        {'label': '2', 'reaction': {'reactants': [{'smiles': 'CC(=O)NCC'}],
                                    'products': [{'smiles': 'CCNCC', 'isolated_mg': 25.0}]},
         'options': {'scale_mmol': 0.5}},
    ])
    first, second = result['steps']
    # the second step consumes 0.5 mmol of N-ethylacetamide (87.12 g/mol); step 1 made 70 mg of it
    assert first['used_mg'] == pytest.approx(0.5 * 87.12, rel=1e-3)
    assert first['scale'] == pytest.approx(0.5 * 87.12 / 70.0, rel=1e-3)
    assert second['scale'] == pytest.approx(1.0)
    expected = (first['input_mg'] * first['scale'] + second['input_mg']) / second['product_mg']
    assert result['cumulative_pmi'] == pytest.approx(expected, rel=1e-4)
    assert result['overall_yield_percent'] == pytest.approx(first['yield_percent'] * second['yield_percent'] / 100.0, rel=1e-3)


def test_a_solvent_without_a_mass_makes_the_pmi_a_lower_bound():
    result = route_summary([
        {'label': '1', 'reaction': {'reactants': [{'smiles': 'CC(=O)Cl'}, {'smiles': 'CCN'}],
                                    'agents': [{'smiles': 'CC(C)(C)CC(C)(C)C', 'role': 'solvent'}],
                                    'products': [{'smiles': 'CC(=O)NCC', 'isolated_mg': 70.0}]}},
    ])
    assert result['lower_bound'] is True
    assert any('solvent' in w for w in result['warnings'])


def test_missing_numbers_are_reported_not_guessed():
    result = route_summary([step('1', yield_percent=80), step('2', yield_percent=50)])
    assert result['overall_yield_percent'] == pytest.approx(40.0)
    assert result['cumulative_pmi'] is None
    assert any('mass' in w for w in result['warnings'])
    with pytest.raises(ValueError, match='used_mg'):
        route_summary([step('1', input_mg=10, product_mg=5), step('2', input_mg=10, product_mg=5)])
    nothing = route_summary([step('1', input_mg=10), step('2', input_mg=10)])
    assert nothing['overall_yield_percent'] is None


def test_the_route_must_be_one_tree_ending_at_the_last_step():
    with pytest.raises(ValueError, match='later step'):
        route_summary([step('1', into='1', yield_percent=1), step('2', yield_percent=1)])
    with pytest.raises(ValueError, match='no step called'):
        route_summary([step('1', into='x', yield_percent=1), step('2', yield_percent=1)])
    with pytest.raises(ValueError, match='Provide at least one step'):
        route_summary([])
    with pytest.raises(ValueError, match='Duplicate step label'):
        route_summary([step('1', yield_percent=1), step('1', yield_percent=1)])
    with pytest.raises(ValueError, match='between 0 and'):
        route_summary([step('1', yield_percent=-5)])


def test_the_table_is_written_as_markdown_csv_or_json_and_never_overwritten(tmp_path):
    steps = [step('1', yield_percent=80, input_mg=1000, product_mg=200, used_mg=100),
             step('2', yield_percent=50, input_mg=500, product_mg=40)]
    out = route_summary(steps, output_path=str(tmp_path / 'route.md'))
    text = (tmp_path / 'route.md').read_text(encoding='utf-8')
    assert 'Overall yield' in text and '40' in text and 'Cumulative PMI' in text
    assert out['output_path'].endswith('route.md')
    route_summary(steps, output_path=str(tmp_path / 'route.csv'))
    assert (tmp_path / 'route.csv').read_text(encoding='utf-8').splitlines()[0].startswith('step,')
    route_summary(steps, output_path=str(tmp_path / 'route.json'))
    assert json.loads((tmp_path / 'route.json').read_text(encoding='utf-8'))['overall_yield_percent'] == pytest.approx(40.0)
    with pytest.raises(Exception):
        route_summary(steps, output_path=str(tmp_path / 'route.md'))
    with pytest.raises(ValueError, match='output_path'):
        route_summary(steps, output_path=str(tmp_path / 'route.txt'))


def test_the_tool_is_in_the_full_profile():
    assert 'route_summary' in build_registry()
