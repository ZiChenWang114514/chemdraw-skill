"""Product prediction and retrosynthesis. Every answer is a model prediction, ranked, never a recommendation."""

from __future__ import annotations

from pathlib import Path
import time
from typing import Any, Mapping, Sequence

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
    reagent_clean = reagent.strip() or None
    for s in structures:
        if s.get('valid'):
            deficit = _element_deficit(clean, s['smiles'], reagent_clean)
            if deficit:
                s['unbalanced_elements'] = deficit
    if any(s.get('unbalanced_elements') for s in structures):
        warnings.append('some predicted products contain heavy-atom elements absent from or exceeding the reactants and '
                        'reagents (see `unbalanced_elements`): a missing reagent or a hallucinated atom')
    return envelope.result('products', name, ENGINES[name], structures, reactants=clean, reagents=reagent_clean,
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


def _element_counts(smiles_text: str | None):
    from collections import Counter
    from rdkit import Chem
    counts: Counter = Counter()
    if not smiles_text or not smiles_text.strip():
        return counts
    for part in smiles_text.strip().split('.'):
        if not part:
            continue
        mol = Chem.MolFromSmiles(part)
        if mol is not None:
            for atom in mol.GetAtoms():
                if atom.GetAtomicNum() > 1:
                    counts[atom.GetSymbol()] += 1
    return counts


def _element_deficit(left: str, right: str, reagents: str | None = None) -> dict[str, int]:
    """Element-wise heavy-atom deficit: elements in ``right`` whose count exceeds ``left`` (+ ``reagents``)."""
    available = _element_counts(left) + _element_counts(reagents)
    needed = _element_counts(right)
    return {el: count - available[el] for el, count in needed.items() if count > available[el]}


def _short_of_atoms(reaction: str, reagents: str | None = None) -> bool:
    """True when the reactants lack any heavy-atom element needed to form the product."""
    left, right = reaction.split('>>')
    return bool(_element_deficit(left, right, reagents))


def _retrosynthesis_one(
    target: str,
    name: str,
    steps: str,
    count: int,
    time_limit: int,
    timeout_seconds: int,
) -> dict:
    if steps not in ('single', 'multi'):
        raise ValueError("steps must be 'single' or 'multi'")
    if name == 'synplanner' and steps != 'multi':
        raise ValueError("synplanner plans whole routes: use steps='multi'")
    if name == 'reactiont5-retro' and steps == 'multi':
        raise ValueError('reactiont5-retro predicts one step; use aizynthfinder for multi-step routes')
    started = time.time()
    env._LAST_CALL_META.set(None)
    try:
        if name == 'reactiont5-retro':
            answers = env.call(name, 'predict', {'inputs': [f'PRODUCT:{target}'], 'count': count}, timeout=timeout_seconds)[0]
            options = [{'rank': i, 'engine_id': name, 'reactants': a['smiles'].split('.'), 'score': a['score']}
                       for i, a in enumerate(answers, 1)]
            body = {'steps': 'single', 'options': options}
        else:
            raw = env.call(name, 'predict', {'smiles': target, 'steps': steps, 'count': count, 'time_limit': time_limit},
                           timeout=timeout_seconds)
            if steps == 'single':
                found = [o for o in raw['options'] if o['reactants'] and o['reactants'][0]]
                options = [{'rank': i, 'engine_id': name, 'reactants': '.'.join(o['reactants'][0]).split('.'),
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
                    routes.append({'rank': i, 'engine_id': name, 'steps': len(flat), 'reactions': flat,
                                   'starting_materials': [{'smiles': s, 'in_stock': stock} for s, stock in leaves],
                                   'all_in_stock': all(stock for _, stock in leaves), 'tree': route,
                                   'unbalanced_steps': [r for r in flat if _element_deficit(*r.split('>>'))]})
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
        out['warnings'].append('some route steps lack heavy-atom elements in the reactants that appear in the product (see '
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
        deficit = _element_deficit('.'.join(option['reactants']), target)
        if deficit:
            option['unbalanced_elements'] = deficit
    if any(option.get('unbalanced_elements') for option in out.get('options', [])):
        out['warnings'].append('some precursor sets lack heavy-atom elements present in the target product (see '
                               '`unbalanced_elements`): a missing co-reactant or a hallucinated disconnection')
    return out


def retrosynthesis(product: str, engine: str | None = None, steps: str = 'single', count: int = 5,
                   time_limit: int = 60, timeout_seconds: int = 900,
                   output_cdxml: str | None = None) -> dict:
    """Suggest precursors (``steps='single'``) or whole routes (``'multi'``) for ``product``."""
    raw_names = [n.strip() for n in (engine or 'aizynthfinder').split(',') if n.strip()]
    if not raw_names:
        raw_names = ['aizynthfinder']
    names = [_pick(n, 'retrosynthesis', 'aizynthfinder') for n in raw_names]
    if steps not in ('single', 'multi'):
        raise ValueError("steps must be 'single' or 'multi'")
    for name in names:
        if name == 'synplanner' and steps != 'multi':
            raise ValueError("synplanner plans whole routes: use steps='multi'")
        if name == 'reactiont5-retro' and steps == 'multi':
            raise ValueError('reactiont5-retro predicts one step; use aizynthfinder for multi-step routes')
    target = _canonical(product, 'product')

    if len(names) == 1:
        out = _retrosynthesis_one(target, names[0], steps, count, time_limit, timeout_seconds)
        if output_cdxml and out.get('ok'):
            routes_src = {names[0]: out.get('routes') or out.get('options') or []}
            if routes_src[names[0]]:
                comp = build_route_comparison_cdxml(routes_src, output_cdxml, target_smiles=target)
                out['output_cdxml'] = comp.get('output_path')
                out['route_comparison'] = comp
        return out

    started = time.time()
    runs: list[dict] = []
    failed: list[dict] = []
    for name in names:
        ans = _retrosynthesis_one(target, name, steps, count, time_limit, timeout_seconds)
        if ans.get('ok'):
            runs.append(ans)
        else:
            failed.append(ans)

    if not runs:
        return {**failed[0], 'failed_engines': failed} if len(failed) > 1 else failed[0]

    succeeded_names = [r['engine'] for r in runs]
    devs = list(dict.fromkeys(r.get('device') for r in runs if r.get('device')))
    any_fallback = any(r.get('device_fallback') for r in runs)
    combined_warnings: list[str] = []
    for r in runs:
        for w in r.get('warnings', []):
            if w not in combined_warnings:
                combined_warnings.append(w)
    if failed:
        combined_warnings.append(
            'did not run, so there is nothing to compare with: '
            + ', '.join(f['engine'] for f in failed)
            + ' (see `failed_engines`)'
        )

    if steps == 'single':
        merged_options: list[dict] = []
        options_by_engine: dict[str, list[dict]] = {}
        for r in runs:
            eng_id = r['engine']
            opts = [dict(o, engine_id=eng_id) for o in r.get('options', [])]
            options_by_engine[eng_id] = opts
            merged_options.extend(opts)
        body: dict[str, Any] = {
            'steps': 'single',
            'options': merged_options,
            'options_by_engine': options_by_engine,
        }
    else:
        merged_routes: list[dict] = []
        routes_by_engine: dict[str, list[dict]] = {}
        for r in runs:
            eng_id = r['engine']
            r_list = [dict(rt, engine_id=eng_id) for rt in r.get('routes', [])]
            routes_by_engine[eng_id] = r_list
            merged_routes.extend(r_list)
        body = {
            'steps': 'multi',
            'solved': any(bool(r.get('solved')) for r in runs),
            'routes': merged_routes,
            'routes_by_engine': routes_by_engine,
        }

    out = envelope.result(
        'retrosynthesis',
        ','.join(succeeded_names),
        {'kind': 'local', 'license': 'see each engine'},
        [],
        target=target,
        device=devs[0] if len(devs) == 1 else 'mixed',
        **({'device_fallback': True} if any_fallback else {}),
        engines=runs,
        elapsed_s=round(time.time() - started, 2),
        warnings=combined_warnings,
        **({'failed_engines': failed} if failed else {}),
        **body,
    )
    if output_cdxml:
        routes_map = out.get('routes_by_engine') or out.get('options_by_engine') or {}
        if any(routes_map.values()):
            comp = build_route_comparison_cdxml(routes_map, output_cdxml, target_smiles=target)
            out['output_cdxml'] = comp.get('output_path')
            out['route_comparison'] = comp
    return out


def _order_route_reactions_forward(rxns: Sequence[str], target_smiles: str | None = None) -> list[str]:
    """Ensure a route's step list runs in forward synthesis order (starting materials -> target)."""
    cleaned = [str(r).strip() for r in rxns if isinstance(r, str) and '>>' in r]
    if len(cleaned) <= 1:
        return cleaned
    first_prod = cleaned[0].split('>>', 1)[1].strip()
    last_prod = cleaned[-1].split('>>', 1)[1].strip()
    if target_smiles:
        try:
            canon_target = _canonical(target_smiles, 'target')
            canon_first = _canonical(first_prod, 'first_prod')
            canon_last = _canonical(last_prod, 'last_prod')
            if canon_first == canon_target and canon_last != canon_target:
                return list(reversed(cleaned))
        except Exception:
            pass
    # Heuristic: in AiZynthFinder _flatten, step[0] produces the target and step[1] produces a reactant of step[0]
    first_reactants = {s.strip() for s in cleaned[0].split('>>', 1)[0].split('.') if s.strip()}
    second_prod = cleaned[1].split('>>', 1)[1].strip()
    if second_prod in first_reactants:
        return list(reversed(cleaned))
    return cleaned


def _normalize_routes_by_engine(routes_by_engine: Any) -> dict[str, list[dict[str, Any]]]:
    if isinstance(routes_by_engine, Mapping):
        if 'routes_by_engine' in routes_by_engine and isinstance(routes_by_engine['routes_by_engine'], Mapping):
            routes_by_engine = routes_by_engine['routes_by_engine']
        elif 'routes' in routes_by_engine and isinstance(routes_by_engine['routes'], Sequence):
            grouped: dict[str, list[dict[str, Any]]] = {}
            for rt in routes_by_engine['routes']:
                if isinstance(rt, Mapping):
                    eng = str(rt.get('engine_id') or rt.get('engine') or routes_by_engine.get('engine') or 'route')
                    grouped.setdefault(eng, []).append(dict(rt))
            return grouped

        out: dict[str, list[dict[str, Any]]] = {}
        for eng, val in routes_by_engine.items():
            if isinstance(val, Mapping):
                r_list = val.get('routes') or val.get('options') or []
            elif isinstance(val, Sequence) and not isinstance(val, (str, bytes)):
                r_list = list(val)
            else:
                r_list = []
            norm_list: list[dict[str, Any]] = []
            for idx, item in enumerate(r_list, 1):
                if isinstance(item, str) and '>>' in item:
                    norm_list.append({'rank': idx, 'engine_id': str(eng), 'reactions': [item]})
                elif isinstance(item, Mapping):
                    d_item = dict(item)
                    if 'reactions' not in d_item:
                        if isinstance(d_item.get('reaction'), str):
                            d_item['reactions'] = [d_item['reaction']]
                        elif isinstance(d_item.get('tree'), Mapping):
                            flat: list[str] = []
                            _flatten(d_item['tree'], flat)
                            d_item['reactions'] = flat
                    d_item.setdefault('rank', idx)
                    d_item.setdefault('engine_id', str(eng))
                    if d_item.get('reactions'):
                        norm_list.append(d_item)
            if norm_list:
                out[str(eng)] = norm_list
        return out

    if isinstance(routes_by_engine, Sequence) and not isinstance(routes_by_engine, (str, bytes)):
        grouped = {}
        for idx, item in enumerate(routes_by_engine, 1):
            if isinstance(item, Mapping):
                eng = str(item.get('engine_id') or item.get('engine') or 'route')
                d_item = dict(item)
                if 'reactions' not in d_item and isinstance(d_item.get('reaction'), str):
                    d_item['reactions'] = [d_item['reaction']]
                d_item.setdefault('rank', idx)
                if d_item.get('reactions'):
                    grouped.setdefault(eng, []).append(d_item)
        return grouped

    raise ValueError('routes_by_engine must be a dict mapping engine -> routes or a sequence of route dicts')


def build_route_comparison_cdxml(
    routes_by_engine: Any,
    output_path: str | Path | None = None,
    target_smiles: str | None = None,
) -> dict[str, Any]:
    """Render top retrosynthetic routes from multiple engines into a stacked-rows CDXML figure."""
    from ..render.renderer import render as render_scheme
    from ..render.schema import (
        ArrowContent,
        SchemeDescriptor,
        SectionDescriptor,
        StepDescriptor,
        StructureRef,
    )
    from ..mcp_runtime import artifact_safety

    normalized = _normalize_routes_by_engine(routes_by_engine)
    if not normalized:
        raise ValueError('No renderable routes provided to build_route_comparison_cdxml')

    structures: dict[str, StructureRef] = {}
    sections: list[SectionDescriptor] = []
    smi_to_id: dict[str, str] = {}

    def _ref_id(smi: str) -> str:
        s_clean = smi.strip()
        if s_clean not in smi_to_id:
            sid = f'mol_{len(smi_to_id) + 1}'
            smi_to_id[s_clean] = sid
            structures[sid] = StructureRef(id=sid, smiles=s_clean)
        return smi_to_id[s_clean]

    for eng_name, route_list in normalized.items():
        for r_idx, route in enumerate(route_list, 1):
            raw_rxns = route.get('reactions') or []
            forward_rxns = _order_route_reactions_forward(raw_rxns, target_smiles=target_smiles)
            if not forward_rxns:
                continue

            sec_steps: list[StepDescriptor] = []
            prev_prod_id: str | None = None
            for step_num, rxn_str in enumerate(forward_rxns, 1):
                left_str, right_str = rxn_str.split('>>', 1)
                reactant_smis = [s.strip() for s in left_str.split('.') if s.strip()]
                product_smis = [s.strip() for s in right_str.split('.') if s.strip()]
                if not reactant_smis or not product_smis:
                    continue

                r_ids = [_ref_id(s) for s in reactant_smis]
                p_ids = [_ref_id(s) for s in product_smis]

                above_structs: list[str] = []
                if prev_prod_id is not None and prev_prod_id in r_ids and len(r_ids) > 1:
                    co_ids = [rid for rid in r_ids if rid != prev_prod_id]
                    substrates = [prev_prod_id]
                    above_structs = co_ids
                elif prev_prod_id is not None and prev_prod_id in r_ids:
                    substrates = [prev_prod_id]
                else:
                    substrates = r_ids

                above_text = [f'Step {step_num}'] if len(forward_rxns) > 1 else [str(eng_name)]
                sec_steps.append(
                    StepDescriptor(
                        substrates=substrates,
                        products=[p_ids[0]],
                        above_arrow=ArrowContent(structures=above_structs, text=above_text),
                    )
                )
                prev_prod_id = p_ids[0]

            if sec_steps:
                rank_val = route.get('rank', r_idx)
                n_s = len(sec_steps)
                sec_label = f"{eng_name} #{rank_val} ({n_s} step{'s' if n_s != 1 else ''})"
                sections.append(
                    SectionDescriptor(
                        label=sec_label,
                        steps=sec_steps,
                        layout='sequential' if len(sec_steps) > 1 else 'linear',
                    )
                )

    if not sections:
        raise ValueError('No valid reaction steps found across routes_by_engine')

    scheme = SchemeDescriptor(
        structures=structures,
        steps=sections[0].steps,
        layout='stacked-rows',
        sections=sections,
        title=f'Retrosynthesis Route Comparison ({target_smiles})' if target_smiles else 'Retrosynthesis Route Comparison',
    )
    cdxml_str = str(render_scheme(scheme))

    saved_path: str | None = None
    if output_path is not None and str(output_path).strip():
        target_file = artifact_safety.resolve_destination(
            source=None,
            output_path=str(output_path),
            tag='retro_comparison',
            suffix='.cdxml',
        )
        with artifact_safety.staging_file(target_file) as staged:
            Path(staged).write_text(cdxml_str, encoding='utf-8')
            artifact_safety.publish_file(staged, target_file)
        saved_path = str(target_file)

    return {
        'cdxml': cdxml_str,
        'output_path': saved_path,
        'section_count': len(sections),
        'engines': list(normalized.keys()),
        'target': target_smiles,
    }


def compare_retrosynthesis_routes(
    product: str,
    engines: Sequence[str] | str = ('aizynthfinder', 'synplanner', 'retrochimera'),
    max_steps: int = 6,
    top_k_per_engine: int = 2,
    output_cdxml: str | Path | None = None,
    time_limit: int = 60,
    timeout_seconds: int = 900,
) -> dict[str, Any]:
    """Run multiple retrosynthesis engines on `product` and optionally render a comparison CDXML figure."""
    if isinstance(engines, str):
        eng_list = [e.strip() for e in engines.split(',') if e.strip()]
    else:
        eng_list = [str(e).strip() for e in engines if str(e).strip()]
    if not eng_list:
        eng_list = ['aizynthfinder', 'synplanner', 'retrochimera']

    target = _canonical(product, 'product')
    routes_by_engine: dict[str, list[dict[str, Any]]] = {}
    merged_routes: list[dict[str, Any]] = []
    failed_engines: list[dict[str, Any]] = []
    warnings: list[str] = []

    for eng in eng_list:
        picked = _pick(eng, 'retrosynthesis', 'aizynthfinder')
        steps_mode = 'single' if picked == 'reactiont5-retro' else 'multi'
        ans = _retrosynthesis_one(
            target,
            picked,
            steps_mode,
            max(int(top_k_per_engine), 1),
            time_limit,
            timeout_seconds,
        )
        if not ans.get('ok'):
            failed_engines.append(ans)
            continue
        for w in ans.get('warnings', []):
            if w not in warnings:
                warnings.append(w)
        if steps_mode == 'multi':
            filtered = [
                dict(r, engine_id=picked)
                for r in ans.get('routes', [])
                if int(r.get('steps', len(r.get('reactions', [])))) <= int(max_steps)
            ][: int(top_k_per_engine)]
        else:
            filtered = [
                {
                    'rank': o['rank'],
                    'engine_id': picked,
                    'steps': 1,
                    'reactions': [o['reaction']],
                    'starting_materials': [{'smiles': s, 'in_stock': False} for s in o.get('reactants', [])],
                    'all_in_stock': False,
                }
                for o in ans.get('options', [])[: int(top_k_per_engine)]
                if o.get('reaction')
            ]
        routes_by_engine[picked] = filtered
        merged_routes.extend(filtered)

    comp_result: dict[str, Any] | None = None
    if any(routes_by_engine.values()):
        comp_result = build_route_comparison_cdxml(
            routes_by_engine,
            output_path=output_cdxml,
            target_smiles=target,
        )

    return {
        'ok': bool(routes_by_engine) or not failed_engines,
        'provenance': 'model_prediction',
        'target': target,
        'engines': list(routes_by_engine.keys()),
        'routes_by_engine': routes_by_engine,
        'routes': merged_routes,
        'cdxml': comp_result['cdxml'] if comp_result else None,
        'output_cdxml': comp_result['output_path'] if comp_result else None,
        'section_count': comp_result['section_count'] if comp_result else 0,
        'failed_engines': failed_engines,
        'warnings': warnings,
    }


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
    try:
        mapping = map_reaction_atoms(f'{left}>>{right}', {'resolve_ambiguity': True})
    except TypeError:
        mapping = map_reaction_atoms(f'{left}>>{right}')
    status = mapping.get('status')
    mapped = mapping.get('mapped_reaction') or ''
    cov = mapping.get('product_coverage') or []
    total_prod = sum(c.get('atoms', 0) for c in cov)
    mapped_prod = sum(c.get('mapped', 0) for c in cov)
    usable_partial = (
        status in ('incomplete', 'ambiguous')
        and ':' in mapped
        and (total_prod == 0 or mapped_prod * 2 >= total_prod)
    )
    if status != 'complete' and not usable_partial:
        raise ValueError('the reaction could not be mapped atom to atom without ambiguity: draw it with the '
                         'reactants that supply every product atom, or map it first with map_reaction_atoms')
    started = time.time()
    env._LAST_CALL_META.set(None)
    try:
        raw = env.call(name, 'predict', {'mapped_reaction': mapped, 'count': count}, timeout=timeout_seconds)
    except env.EngineError as exc:
        return envelope.failure('conditions', name, ENGINES[name], exc)
    warnings = ['model predictions learned from patent reactions: candidates, not a recommended '
                'procedure; they carry no temperature, time, amounts or yield',
                'the atom mapping is a prediction too: a wrong map changes the answer']
    if status in ('incomplete', 'ambiguous'):
        warnings.append(f'atom mapping status is {status!r}: unmapped or symmetry-equivalent atoms remain in '
                        '`mapped_reaction`; verify the atom map before trusting the ranked conditions')
    elif mapping.get('resolved_ambiguity'):
        warnings.append('symmetry ambiguity in atom mapping was resolved automatically; check `mapped_reaction`')
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
