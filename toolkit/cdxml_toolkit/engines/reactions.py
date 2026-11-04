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


def _device_extra(name: str, warnings: list) -> dict:
    meta = env.last_call_meta(name)
    extra = {'device': meta['device']}
    if meta.get('device_fallback'):
        extra['device_fallback'] = True
        warnings.append(f'{name}: CUDA failed at runtime; fell back to CPU.')
    return extra


def products(reactants: str, reagents: str | None = None, engine: str | None = None, count: int = 5,
             timeout_seconds: int = 600) -> dict:
    """Predict the products of ``reactants`` (dot-separated SMILES), optionally with ``reagents``."""
    name = _pick(engine, 'products', 'reactiont5-forward')
    clean = _canonical(reactants, 'reactants')
    reagent = _canonical(reagents, 'reagents') if reagents else ' '
    started = time.time()
    env._LAST_CALL_META.set(None)
    try:
        answers = env.call(name, 'predict', {'inputs': [f'REACTANT:{clean}REAGENT:{reagent}'], 'count': count},
                           timeout=timeout_seconds)[0]
    except env.EngineError as exc:
        return envelope.failure('products', name, ENGINES[name], exc)
    warnings = ['model predictions: unvalidated by experiment; the real product may be absent']
    device_extra = _device_extra(name, warnings)
    structures = [envelope.describe(a['smiles'], a['score'], rank=i) for i, a in enumerate(answers, 1)]
    return envelope.result('products', name, ENGINES[name], structures, reactants=clean, reagents=reagent.strip() or None,
                           **device_extra,
                           score_meaning='mean log-probability of the generated sequence (closer to 0 is likelier)',
                           reactions=[_reaction_smiles([clean], s['smiles']) for s in structures if s['valid']],
                           elapsed_s=round(time.time() - started, 2),
                           warnings=warnings)


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


def _short_of_atoms(reaction: str) -> bool:
    """True when the reactants hold fewer heavy atoms than the product: no reaction can make it from them."""
    from rdkit import Chem
    left, right = reaction.split('>>')
    count = lambda text: sum(m.GetNumHeavyAtoms() for m in (Chem.MolFromSmiles(x) for x in text.split('.')) if m is not None)
    return count(left) < count(right)


def retrosynthesis(product: str, engine: str | None = None, steps: str = 'single', count: int = 5,
                   time_limit: int = 60, timeout_seconds: int = 900) -> dict:
    """Suggest precursors (``steps='single'``) or whole routes (``'multi'``) for ``product``."""
    name = _pick(engine, 'retrosynthesis', 'aizynthfinder')
    if steps not in ('single', 'multi'):
        raise ValueError("steps must be 'single' or 'multi'")
    if name == 'synplanner' and steps != 'multi':
        raise ValueError("synplanner plans whole routes: use steps='multi'")
    if name == 'reactiont5-retro' and steps == 'multi':
        raise ValueError('reactiont5-retro predicts one step; use aizynthfinder for multi-step routes')
    target = _canonical(product, 'product')
    started = time.time()
    env._LAST_CALL_META.set(None)
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
                found = [o for o in raw['options'] if o['reactants'] and o['reactants'][0]]
                options = [{'rank': i, 'reactants': '.'.join(o['reactants'][0]).split('.'),
                            'probability': o['probability'], 'template': o.get('template'),
                            **({'score': o['score']} if o.get('score') is not None else {})}
                           for i, o in enumerate(found, 1)]
                body = {'steps': 'single', 'options': options}
            else:
                routes = []
                for i, route in enumerate(raw['routes'], 1):
                    flat, leaves = [], []
                    _flatten(route, flat)
                    _leaves(route, leaves)
                    routes.append({'rank': i, 'steps': len(flat), 'reactions': flat,
                                   'starting_materials': [{'smiles': s, 'in_stock': stock} for s, stock in leaves],
                                   'all_in_stock': all(stock for _, stock in leaves), 'tree': route,
                                   'unbalanced_steps': [r for r in flat if _short_of_atoms(r)]})
                body = {'steps': 'multi', 'solved': raw['solved'], 'top_score': raw['top_score'], 'routes': routes}
                if raw.get('target_in_stock'):
                    body['target_in_stock'] = True
                    body['note'] = 'the target is itself a purchasable building block: no search was run'
    except env.EngineError as exc:
        return envelope.failure('retrosynthesis', name, ENGINES[name], exc)
    warnings = ['model predictions: precursors are suggestions from learned reaction templates; '
                'check chemistry, selectivity and availability before use']
    device_extra = _device_extra(name, warnings)
    out = envelope.result('retrosynthesis', name, ENGINES[name], [], target=target, **device_extra,
                          elapsed_s=round(time.time() - started, 2),
                          warnings=warnings, **body)
    if name == 'reactiont5-retro':
        out['warnings'].append('reactiont5-retro lists reagents and solvents together with the reactants and can miss '
                               'the obvious precursor (for aspirin it did not propose acetic anhydride); prefer '
                               'aizynthfinder and treat these sets as hints')
    if any(route.get('unbalanced_steps') for route in out.get('routes', [])):
        out['warnings'].append('some route steps list fewer heavy atoms in the reactants than in the product (see '
                               '`unbalanced_steps`): a missing partner or a hallucinated step; do not follow those routes')
    if name == 'retrochimera':
        out['warnings'].append('RetroChimera is released for research and experiments: an expert must check every '
                               'suggestion, and lower-ranked reactions are more likely to be hallucinated (its authors '
                               'advise reading only the first 5 to 10); its training data ends in 2023')
        if steps == 'multi':
            out['warnings'].append('routes are searched with RetroChimera and the MCULE/Molport building blocks; '
                                   '"in stock" means the molecule is in that list, not that it can be bought today')
    for option in out.get('options', []):
        option['reaction'] = _reaction_smiles(option['reactants'], target)
        option['reactants_checked'] = [envelope.describe(r) for r in option['reactants']]
    return out


def conditions(reactants: str, products: str, engine: str | None = None, count: int = 5,
               timeout_seconds: int = 900) -> dict:
    """Rank catalyst, solvent and reagent combinations for a reaction the user already drew.

    The model needs the atoms mapped from reactants to products; the mapping is made here with the
    toolkit's own mapper (``map_reaction_atoms``) and returned, so it can be checked.
    """
    name = _pick(engine, 'conditions', 'reacon')
    left = _canonical(reactants, 'reactants')
    right = _canonical(products, 'products')
    from ..mcp_runtime.report_tools import map_reaction_atoms
    mapping = map_reaction_atoms(f'{left}>>{right}')
    if mapping.get('status') != 'complete':
        raise ValueError('the reaction could not be mapped atom to atom without ambiguity: draw it with the '
                         'reactants that supply every product atom, or map it first with map_reaction_atoms')
    mapped = mapping['mapped_reaction']
    started = time.time()
    env._LAST_CALL_META.set(None)
    try:
        raw = env.call(name, 'predict', {'mapped_reaction': mapped, 'count': count}, timeout=timeout_seconds)
    except env.EngineError as exc:
        return envelope.failure('conditions', name, ENGINES[name], exc)
    warnings = ['model predictions learned from patent reactions: candidates, not a recommended '
                'procedure; they carry no temperature, time, amounts or yield',
                'the atom mapping is a prediction too: a wrong map changes the answer']
    device_extra = _device_extra(name, warnings)
    options = [{'rank': i, **candidate} for i, candidate in enumerate(raw['candidates'][:count], 1)]
    out = envelope.result('conditions', name, ENGINES[name], [], reactants=left, products=right,
                          **device_extra,
                          mapped_reaction=mapped, mapping_method=mapping.get('method'),
                          template_level=raw.get('template_level'), options=options,
                          score_meaning='product of the component probabilities from six learned classifiers',
                          elapsed_s=round(time.time() - started, 2),
                          warnings=warnings)
    if raw.get('template_level') in (None, 'none'):
        out['warnings'].append('no template in the condition library matched this reaction: the options combine the '
                               'top three answers of each classifier and are less reliable')
    return out
