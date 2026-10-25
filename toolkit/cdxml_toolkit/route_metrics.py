"""Overall yield and cumulative process mass intensity of a synthetic route.

A route is a list of steps in the order they are run; the last step makes the final product.
Step ``k`` feeds the step named in ``into`` (default: the next one), so a list is a linear route
and ``into`` makes it convergent. Everything is arithmetic on numbers the caller gives:

* overall yield: the product of the step yields along the longest linear sequence;
* cumulative PMI: the mass put into every step, each step scaled so that it makes exactly the
  amount of product the next step uses, over the mass of the final product. E-factor = PMI - 1.
"""

from __future__ import annotations

import math

NUMBERS = ('yield_percent', 'input_mg', 'product_mg', 'used_mg')


def _number(step, key):
    value = step.get(key)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
        raise ValueError(f"step {step['label']}: {key} must be a number between 0 and 100"
                         if key == 'yield_percent' else f"step {step['label']}: {key} must be a non-negative number")
    return float(value)


def _steps(raw):
    if not raw:
        raise ValueError('Provide at least one step')
    steps, seen = [], {}
    for index, item in enumerate(raw):
        label = str(item.get('label') or index + 1)
        if label in seen:
            raise ValueError(f'Duplicate step label {label!r}')
        seen[label] = index
        steps.append({**{k: v for k, v in item.items() if k not in NUMBERS}, 'label': label})
        steps[-1].update({key: _number({**item, 'label': label}, key) for key in NUMBERS})
    for index, step in enumerate(steps):
        target = step.get('into')
        if index == len(steps) - 1:
            step['into'] = None
            continue
        if target is None:
            step['into'] = steps[index + 1]['label']
            continue
        target = str(target)
        if target not in seen:
            raise ValueError(f"step {step['label']}: no step called {target!r} to feed into")
        if seen[target] <= index:
            raise ValueError(f"step {step['label']} must feed into a later step, not {target!r}")
        step['into'] = target
    return steps, seen


def summarize(raw) -> dict:
    steps, index = _steps(raw)
    warnings = []
    for step in steps:
        if step['yield_percent'] is not None and step['yield_percent'] > 100:
            warnings.append(f"step {step['label']}: yield above 100% (wet or impure product, or a wrong basis)")
    # longest linear sequence: the longest chain from a step nothing feeds into to the final step
    fed = {step['into'] for step in steps if step['into']}
    depth = {}
    for step in reversed(steps):
        depth[step['label']] = 1 + (depth[step['into']] if step['into'] else 0)
    leaf = max((s for s in steps if s['label'] not in fed), key=lambda s: (depth[s['label']], -index[s['label']]))
    chain, step = [], leaf
    while step:
        chain.append(step['label'])
        step = steps[index[step['into']]] if step['into'] else None
    yields = [steps[index[label]]['yield_percent'] for label in chain]
    overall = None
    if all(y is not None for y in yields):
        overall = math.prod(y / 100.0 for y in yields) * 100.0
    else:
        missing = [label for label, y in zip(chain, yields) if y is None]
        warnings.append(f"overall yield not calculated: no yield for step {', '.join(missing)}")
    # cumulative PMI, from the last step backwards
    final = steps[-1]
    why = None
    for step in steps:
        if step['input_mg'] is None or step['product_mg'] is None:
            why = f"step {step['label']} has no input or product mass"
            break
    scale = {final['label']: 1.0}
    if why is None:
        for step in reversed(steps[:-1]):
            if step['used_mg'] is None:
                raise ValueError(f"step {step['label']}: give used_mg, the mass of its product that step "
                                 f"{step['into']} uses (it is not stated and could not be read from the structures)")
            if not step['product_mg']:
                why = f"step {step['label']} made no product"
                break
            scale[step['label']] = scale[step['into']] * step['used_mg'] / step['product_mg']
    pmi = None
    if why is None and final['product_mg']:
        pmi = sum(step['input_mg'] * scale[step['label']] for step in steps) / (final['product_mg'] * scale[final['label']])
    elif why is None:
        why = 'the final product has no mass'
    if why:
        warnings.append(f'cumulative PMI not calculated: {why}')
    lower = any(step.get('solvents_without_mass') for step in steps)
    if lower and pmi is not None:
        warnings.append('some solvent has no known mass (no density), so the PMI is a lower bound')
    rows = []
    for step in steps:
        label = step['label']
        rows.append({'label': label, 'into': step['into'], 'yield_percent': step['yield_percent'],
                     'input_mg': step['input_mg'], 'product_mg': step['product_mg'], 'used_mg': step['used_mg'],
                     'scale': scale.get(label) if why is None else None,
                     'step_pmi': step['input_mg'] / step['product_mg'] if step['input_mg'] is not None and step['product_mg'] else None,
                     'on_longest_sequence': label in chain})
    return {'steps': rows, 'step_count': len(steps), 'longest_sequence': chain, 'overall_yield_percent': overall,
            'cumulative_pmi': pmi, 'cumulative_e_factor': pmi - 1.0 if pmi is not None else None,
            'lower_bound': bool(lower), 'warnings': warnings}
