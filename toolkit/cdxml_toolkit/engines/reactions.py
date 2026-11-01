"""Product prediction and retrosynthesis. Every answer is a model prediction, ranked, never a recommendation."""

from __future__ import annotations

import time

from . import env, envelope
from .registry import ENGINES, by_task


def _canonical(smiles: str, label: str) -> str:
    from rdkit import Chem, RDLogger
    RDLogger.DisableLog('rdApp.*')
    mol = Chem.MolFromSmiles((smiles or '').strip())
    if mol is None or mol.GetNumAtoms() == 0:
        raise ValueError(f'{label} is not a valid SMILES: {smiles!r}')
    return Chem.MolToSmiles(mol)


def _pick(engine, task, default):
    name = engine or default
    if name not in ENGINES or ENGINES[name]['task'] != task:
        raise ValueError(f'unknown {task} engine {name!r} (choose from {", ".join(by_task(task))})')
    return name


def _reaction_smiles(reactants, product):
    return f'{".".join(reactants)}>>{product}'


def products(reactants: str, reagents: str | None = None, engine: str | None = None, count: int = 5,
             timeout_seconds: int = 600) -> dict:
    """Predict the products of ``reactants`` (dot-separated SMILES), optionally with ``reagents``."""
    name = _pick(engine, 'products', 'reactiont5-forward')
    clean = _canonical(reactants, 'reactants')
    reagent = _canonical(reagents, 'reagents') if reagents else ' '
    started = time.time()
    try:
        answers = env.call(name, 'predict', {'inputs': [f'REACTANT:{clean}REAGENT:{reagent}'], 'count': count},
                           timeout=timeout_seconds)[0]
    except env.EngineError as exc:
        return envelope.failure('products', name, ENGINES[name], str(exc))
    structures = [envelope.describe(a['smiles'], a['score'], rank=i) for i, a in enumerate(answers, 1)]
    return envelope.result('products', name, ENGINES[name], structures, reactants=clean, reagents=reagent.strip() or None,
                           score_meaning='mean log-probability of the generated sequence (closer to 0 is likelier)',
                           reactions=[_reaction_smiles([clean], s['smiles']) for s in structures if s['valid']],
                           elapsed_s=round(time.time() - started, 2),
                           warnings=['model predictions: unvalidated by experiment; the real product may be absent'])


def _flatten(node, steps):
    """Reaction SMILES (reactants>>product) for every step of an AiZynthFinder route tree."""
    reaction = node.get('reaction')
    if not reaction:
        return
    steps.append(_reaction_smiles([r['smiles'] for r in reaction['reactants']], node['smiles']))
    for reactant in reaction['reactants']:
        _flatten(reactant, steps)


def _leaves(node, out):
    reaction = node.get('reaction')
    if not reaction:
        out.append((node['smiles'], bool(node.get('in_stock'))))
    else:
        for reactant in reaction['reactants']:
            _leaves(reactant, out)


def retrosynthesis(product: str, engine: str | None = None, steps: str = 'single', count: int = 5,
                   time_limit: int = 60, timeout_seconds: int = 900) -> dict:
    """Suggest precursors (``steps='single'``) or whole routes (``'multi'``, AiZynthFinder only) for ``product``."""
    name = _pick(engine, 'retrosynthesis', 'aizynthfinder')
    if steps not in ('single', 'multi'):
        raise ValueError("steps must be 'single' or 'multi'")
    if name == 'synplanner' and steps != 'multi':
        raise ValueError("synplanner plans whole routes: use steps='multi'")
    if name == 'reactiont5-retro' and steps == 'multi':
        raise ValueError('reactiont5-retro predicts one step; use aizynthfinder for multi-step routes')
    target = _canonical(product, 'product')
    started = time.time()
    try:
        if name == 'reactiont5-retro':
            answers = env.call(name, 'predict', {'inputs': [f'PRODUCT:{target}'], 'count': count}, timeout=timeout_seconds)[0]
            options = [{'rank': i, 'reactants': a['smiles'].split('.'), 'score': a['score']}
                       for i, a in enumerate(answers, 1)]
            body = {'steps': 'single', 'options': options}
        else:
            raw = env.call(name, 'predict', {'smiles': target, 'steps': steps, 'count': count, 'time_limit': time_limit},
                           timeout=timeout_seconds)
            if steps == 'single':
                options = [{'rank': i, 'reactants': ['.'.join(group) for group in o['reactants']][0].split('.'),
                            'probability': o['probability'], 'template': o['template']}
                           for i, o in enumerate(raw['options'], 1)]
                body = {'steps': 'single', 'options': options}
            else:
                routes = []
                for i, route in enumerate(raw['routes'], 1):
                    flat, leaves = [], []
                    _flatten(route, flat)
                    _leaves(route, leaves)
                    routes.append({'rank': i, 'steps': len(flat), 'reactions': flat,
                                   'starting_materials': [{'smiles': s, 'in_stock': stock} for s, stock in leaves],
                                   'all_in_stock': all(stock for _, stock in leaves), 'tree': route})
                body = {'steps': 'multi', 'solved': raw['solved'], 'top_score': raw['top_score'], 'routes': routes}
                if raw.get('target_in_stock'):
                    body['target_in_stock'] = True
                    body['note'] = 'the target is itself a purchasable building block: no search was run'
    except env.EngineError as exc:
        return envelope.failure('retrosynthesis', name, ENGINES[name], str(exc))
    out = envelope.result('retrosynthesis', name, ENGINES[name], [], target=target, elapsed_s=round(time.time() - started, 2),
                          warnings=['model predictions: precursors are suggestions from learned reaction templates; '
                                    'check chemistry, selectivity and availability before use'], **body)
    if name == 'reactiont5-retro':
        out['warnings'].append('reactiont5-retro lists reagents and solvents together with the reactants and can miss '
                               'the obvious precursor (for aspirin it did not propose acetic anhydride); prefer '
                               'aizynthfinder and treat these sets as hints')
    for option in out.get('options', []):
        option['reaction'] = _reaction_smiles(option['reactants'], target)
        option['reactants_checked'] = [envelope.describe(r) for r in option['reactants']]
    return out
