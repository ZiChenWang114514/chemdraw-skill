import pytest

from cdxml_toolkit.engines import env, reactions
from cdxml_toolkit.mcp_runtime.engine_tools import (ENGINE_TOOLS, list_engines, predict_conditions, predict_products,
                                                    predict_retrosynthesis)

ASPIRIN = 'CC(=O)Oc1ccccc1C(=O)O'
ROUTE = {
    'smiles': ASPIRIN, 'in_stock': False,
    'reaction': {'template': 't', 'policy_probability': 0.9, 'reactants': [
        {'smiles': 'CC(=O)OC(C)=O', 'in_stock': True, 'reaction': None},
        {'smiles': 'O=C(O)c1ccccc1O', 'in_stock': True, 'reaction': None}]}}


def test_products_sends_the_reactt5_prompt_and_labels_the_answer(monkeypatch):
    seen = {}

    def call(name, action, params, timeout=0):
        seen.update(name=name, params=params)
        return [[{'smiles': ASPIRIN, 'score': -0.1}, {'smiles': 'not smiles ((', 'score': -4.0}]]

    monkeypatch.setattr(env, 'call', call)
    answer = predict_products('CC(=O)OC(C)=O.OC(=O)c1ccccc1O', 'CCN')
    assert seen['name'] == 'reactiont5-forward'
    assert seen['params']['inputs'] == ['REACTANT:CC(=O)OC(C)=O.O=C(O)c1ccccc1OREAGENT:CCN']
    assert answer['provenance'] == 'model_prediction' and answer['ok']
    assert [s['valid'] for s in answer['structures']] == [True, False]
    assert answer['reactions'] == [f'CC(=O)OC(C)=O.O=C(O)c1ccccc1O>>{ASPIRIN}']  # only valid products become reactions
    assert any('predictions' in w for w in answer['warnings'])


def test_products_reports_a_missing_engine_instead_of_raising():
    answer = predict_products('CCO.CC(=O)O')
    assert answer['ok'] is False and 'install-engines reactiont5-forward' in answer['error']


def test_bad_smiles_and_wrong_engine_are_rejected_before_any_engine_runs(monkeypatch):
    monkeypatch.setattr(env, 'call', lambda *a, **k: pytest.fail('engine must not start'))
    with pytest.raises(ValueError, match='reactants is not a valid SMILES'):
        predict_products('C(C)(C)(C)(C)C')
    with pytest.raises(ValueError, match='unknown products engine'):
        predict_products('CCO', engine='molscribe')
    with pytest.raises(ValueError, match='steps'):
        predict_retrosynthesis('CCO', steps='three')
    with pytest.raises(ValueError, match='one step'):
        predict_retrosynthesis('CCO', engine='reactiont5-retro', steps='multi')


def test_single_step_options_carry_reaction_smiles_and_checked_reactants(monkeypatch):
    monkeypatch.setattr(env, 'call', lambda *a, **k: {'steps': 'single', 'options': [
        {'reactants': [['CC(=O)OC(C)=O', 'O=C(O)c1ccccc1O']], 'template': 't', 'probability': 0.7}]})
    answer = predict_retrosynthesis(ASPIRIN)
    option = answer['options'][0]
    assert option['reaction'] == f'CC(=O)OC(C)=O.O=C(O)c1ccccc1O>>{ASPIRIN}'
    assert all(r['valid'] for r in option['reactants_checked']) and answer['provenance'] == 'model_prediction'


def test_multi_step_route_is_flattened_into_renderable_reactions(monkeypatch):
    monkeypatch.setattr(env, 'call', lambda *a, **k: {'steps': 'multi', 'target': ASPIRIN, 'solved': True,
                                                      'top_score': 0.99, 'routes': [ROUTE]})
    answer = predict_retrosynthesis(ASPIRIN, steps='multi')
    route = answer['routes'][0]
    assert route['steps'] == 1 and route['all_in_stock'] is True
    assert route['reactions'] == [f'CC(=O)OC(C)=O.O=C(O)c1ccccc1O>>{ASPIRIN}']
    assert {m['smiles'] for m in route['starting_materials']} == {'CC(=O)OC(C)=O', 'O=C(O)c1ccccc1O'}


def test_reactiont5_retro_splits_reactant_sets(monkeypatch):
    monkeypatch.setattr(env, 'call', lambda *a, **k: [[{'smiles': 'CC(=O)Cl.OC(=O)c1ccccc1O', 'score': -0.3}]])
    answer = predict_retrosynthesis(ASPIRIN, engine='reactiont5-retro')
    assert answer['options'][0]['reactants'] == ['CC(=O)Cl', 'OC(=O)c1ccccc1O']
    assert any('reagents and solvents' in w for w in answer['warnings'])


def test_the_tools_are_registered_and_list_engines_names_every_engine():
    assert {'list_engines', 'recognize_structure', 'predict_products', 'predict_retrosynthesis'} <= set(ENGINE_TOOLS)
    listing = list_engines()
    assert listing['ok'] and 'aizynthfinder' in listing['engines'] and listing['engines']['decimer-api']['available']


def test_synplanner_plans_routes_and_says_when_the_target_can_be_bought(monkeypatch):
    monkeypatch.setattr(env, 'call', lambda *a, **k: {'steps': 'multi', 'target': ASPIRIN, 'solved': True,
                                                      'target_in_stock': False, 'routes_found': 416,
                                                      'top_score': 0.37, 'routes': [ROUTE]})
    answer = predict_retrosynthesis(ASPIRIN, engine='synplanner', steps='multi')
    assert answer['engine'] == 'synplanner' and answer['routes'][0]['reactions']
    assert 'target_in_stock' not in answer
    monkeypatch.setattr(env, 'call', lambda *a, **k: {'steps': 'multi', 'target': ASPIRIN, 'solved': False,
                                                      'target_in_stock': True, 'routes_found': 0, 'top_score': None,
                                                      'routes': []})
    bought = predict_retrosynthesis(ASPIRIN, engine='synplanner', steps='multi')
    assert bought['target_in_stock'] is True and 'purchasable' in bought['note'] and bought['routes'] == []


def test_synplanner_refuses_single_step_requests(monkeypatch):
    monkeypatch.setattr(env, 'call', lambda *a, **k: pytest.fail('engine must not start'))
    with pytest.raises(ValueError, match="steps='multi'"):
        predict_retrosynthesis(ASPIRIN, engine='synplanner')


def test_retrochimera_single_step_carries_probability_and_the_research_warning(monkeypatch):
    seen = {}

    def call(name, action, params, timeout=0):
        seen.update(name=name, params=params)
        return {'steps': 'single', 'options': [{'reactants': [['CC(=O)OC(C)=O', 'O=C(O)c1ccccc1O']],
                                                'probability': 0.62, 'score': 3.1}]}

    monkeypatch.setattr(env, 'call', call)
    answer = predict_retrosynthesis(ASPIRIN, engine='retrochimera', steps='single', count=5)
    assert seen['name'] == 'retrochimera' and seen['params']['steps'] == 'single'
    option = answer['options'][0]
    assert option['probability'] == 0.62 and option['score'] == 3.1 and option['template'] is None
    assert option['reaction'] == f'CC(=O)OC(C)=O.O=C(O)c1ccccc1O>>{ASPIRIN}'
    assert any('research' in w and 'hallucinated' in w for w in answer['warnings'])


def test_retrochimera_multi_step_route_is_searched_and_flattened(monkeypatch):
    route = {'smiles': ASPIRIN, 'in_stock': False, 'reaction': {'metadata': {'policy_probability': 0.9}, 'reactants': [
        {'smiles': 'CC(=O)OC(C)=O', 'in_stock': True}, {'smiles': 'O=C(O)c1ccccc1O', 'in_stock': True}]}}
    monkeypatch.setattr(env, 'call', lambda *a, **k: {'steps': 'multi', 'target': ASPIRIN, 'solved': True,
                                                      'top_score': None, 'routes': [route]})
    answer = predict_retrosynthesis(ASPIRIN, engine='retrochimera', steps='multi')
    assert answer['solved'] is True and answer['routes'][0]['all_in_stock'] is True
    assert answer['routes'][0]['reactions'] == [f'CC(=O)OC(C)=O.O=C(O)c1ccccc1O>>{ASPIRIN}']
    assert any('building blocks' in w for w in answer['warnings'])


def test_conditions_maps_the_reaction_then_ranks_what_the_engine_returns(monkeypatch):
    seen = {}

    def call(name, action, params, timeout=0):
        seen.update(name=name, params=params)
        return {'template_level': 'r1', 'candidates': [
            {'catalyst': 'none', 'solvents': ['CCOC(C)=O'], 'reagents': ['CCN(CC)CC'], 'score': 0.31},
            {'catalyst': 'none', 'solvents': ['C1CCOC1'], 'reagents': [], 'score': 0.12}]}

    monkeypatch.setattr(env, 'call', call)
    answer = predict_conditions('CC(=O)OC(C)=O.OC(=O)c1ccccc1O', ASPIRIN, count=1)
    assert seen['name'] == 'reacon' and ':' in seen['params']['mapped_reaction']  # atom-map numbers were added
    assert answer['provenance'] == 'model_prediction' and answer['template_level'] == 'r1'
    assert [o['rank'] for o in answer['options']] == [1] and answer['options'][0]['score'] == 0.31
    assert any('candidates, not a recommended procedure' in w for w in answer['warnings'])


def test_conditions_warns_when_no_template_matched_and_reports_a_missing_engine(monkeypatch):
    monkeypatch.setattr(env, 'call', lambda *a, **k: {'template_level': 'none', 'candidates': [
        {'catalyst': 'none', 'solvents': [], 'reagents': [], 'score': 0.01}]})
    answer = predict_conditions('CC(=O)OC(C)=O.OC(=O)c1ccccc1O', ASPIRIN)
    assert any('no template' in w for w in answer['warnings'])
    monkeypatch.undo()
    missing = predict_conditions('CC(=O)OC(C)=O.OC(=O)c1ccccc1O', ASPIRIN)
    assert missing['ok'] is False and 'install-engines reacon' in missing['error']
    assert missing['install_hint']['license'].startswith('not declared')


def test_conditions_rejects_reactions_it_cannot_map(monkeypatch):
    monkeypatch.setattr(env, 'call', lambda *a, **k: pytest.fail('engine must not start'))
    with pytest.raises(ValueError, match='could not be mapped'):
        predict_conditions('CCO', 'c1ccccc1Br')


def test_a_route_step_that_cannot_make_its_product_is_flagged(monkeypatch):
    bad = {'smiles': 'CCNC(=O)COc1ccc(NC(C)=O)cc1', 'in_stock': False, 'reaction': {'reactants': [
        {'smiles': 'CC(=O)Nc1ccc(O)cc1', 'in_stock': True}]}}
    monkeypatch.setattr(env, 'call', lambda *a, **k: {'steps': 'multi', 'target': bad['smiles'], 'solved': True,
                                                      'top_score': None, 'routes': [bad, ROUTE]})
    answer = predict_retrosynthesis(bad['smiles'], engine='retrochimera', steps='multi')
    assert answer['routes'][0]['unbalanced_steps'] and answer['routes'][1]['unbalanced_steps'] == []
    assert any('unbalanced_steps' in w for w in answer['warnings'])
