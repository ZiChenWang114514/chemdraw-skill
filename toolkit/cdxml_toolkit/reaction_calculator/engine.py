"""Stoichiometry of one reaction: the amounts that follow from what has been fixed.

The same rules run in calculator.js, so the page recomputes live and this module gives the
agent identical numbers headlessly. tests/runtime/test_reaction_calculator.py runs both on the
same cases. Units: mg, mmol, mL, g/mL, mol/L (= mmol/mL), g/mol.

A row is a dict. Rows with an amount (role reactant, reagent or catalyst) carry one
``basis`` and its ``value``: ``equiv`` (relative to the limiting row), ``mmol``, ``mass``
(mg of the weighed material, corrected by ``purity``) or ``volume`` (mL, of a neat liquid with a
``density`` or of a solution with ``solution_m``). The limiting row cannot use ``equiv``.
Solvent rows use ``volume`` or ``conc`` (the molarity of the limiting row once dissolved).
Product rows use ``mass`` (isolated mg), ``yield`` (percent of theoretical) or nothing.
"""

from __future__ import annotations

import math
from copy import deepcopy

AMOUNT_ROLES = ('reactant', 'reagent', 'catalyst')
ROLES = AMOUNT_ROLES + ('solvent', 'product')
BASES = {
    'reactant': ('equiv', 'mmol', 'mass', 'volume'),
    'reagent': ('equiv', 'mmol', 'mass', 'volume'),
    'catalyst': ('equiv', 'mmol', 'mass', 'volume'),
    'solvent': ('volume', 'conc'),
    'product': ('mass', 'yield', None),
}


def _number(row, key, *, positive=False, default=None):
    value = row.get(key, default)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0 \
            or (positive and value == 0):
        raise ValueError(f"{row.get('name') or row.get('id')}: {key} must be a "
                         f"{'positive' if positive else 'non-negative'} number")
    return float(value)


def _mmol(row):
    """Amount of substance of a row whose basis is mmol, mass or volume."""
    basis, value = row['basis'], _number(row, 'value')
    mw = _number(row, 'mw', positive=True)
    purity = _number(row, 'purity', default=1.0)
    if not purity or purity > 1:
        raise ValueError(f"{row.get('name') or row['id']}: purity must be between 0 and 1")
    if value is None:
        raise ValueError(f"{row.get('name') or row['id']}: the {basis} has no value")
    if basis == 'mmol':
        return value
    if basis == 'mass':
        return value * purity / mw
    solution = _number(row, 'solution_m', positive=True)
    density = _number(row, 'density', positive=True)
    if solution:
        return value * solution
    if density:
        return value * density * 1000.0 * purity / mw
    raise ValueError(f"{row.get('name') or row['id']}: a volume needs a density or a solution molarity")


def compute(state: dict) -> dict:
    """Amounts of every row from the limiting row and the quantity fixed on each row."""
    rows = [deepcopy(r) for r in state.get('rows', [])]
    ids = [r.get('id') for r in rows]
    if len(set(ids)) != len(ids):
        raise ValueError('row ids must be unique')
    for r in rows:
        if r.get('role') not in ROLES:
            raise ValueError(f"{r.get('name') or r.get('id')}: role must be one of {', '.join(ROLES)}")
        if r.get('basis') not in BASES[r['role']]:
            raise ValueError(f"{r.get('name') or r['id']}: a {r['role']} cannot use basis {r.get('basis')!r}")
    limiting = next((r for r in rows if r['id'] == state.get('limiting')), None)
    if limiting is None or limiting['role'] not in AMOUNT_ROLES:
        raise ValueError('limiting must name a reactant, reagent or catalyst row')
    if limiting['basis'] == 'equiv':
        raise ValueError('The limiting row sets the scale; give it mmol, mass or volume, not equiv')
    base = _mmol(limiting)
    if base <= 0:
        raise ValueError('The limiting row needs a positive amount')
    warnings = []
    solvent_ml = 0.0
    for r in rows:
        role, mw = r['role'], _number(r, 'mw', positive=True)
        if role in AMOUNT_ROLES:
            mmol = _number(r, 'value') * base if r['basis'] == 'equiv' else _mmol(r)
            purity = _number(r, 'purity', default=1.0)
            r['mmol'] = mmol
            r['equiv'] = mmol / base
            r['mass_mg'] = mmol * mw / purity
            solution, density = _number(r, 'solution_m', positive=True), _number(r, 'density', positive=True)
            r['volume_ml'] = mmol / solution if solution else (r['mass_mg'] / 1000.0 / density if density else None)
        elif role == 'solvent':
            value = _number(r, 'value')
            if value is None or (r['basis'] == 'conc' and value == 0):
                raise ValueError(f"{r.get('name') or r['id']}: the {r['basis']} needs a positive value")
            r['volume_ml'] = value if r['basis'] == 'volume' else base / value
            density = _number(r, 'density', positive=True)
            r['mass_mg'] = r['volume_ml'] * density * 1000.0 if density else None
            solvent_ml += r['volume_ml']
    first_reactant = limiting['coefficient'] if limiting.get('coefficient') else 1.0
    for r in rows:
        if r['role'] != 'product':
            continue
        coefficient = _number(r, 'coefficient', positive=True, default=1.0)
        mw = _number(r, 'mw', positive=True)
        r['theory_mmol'] = base * coefficient / first_reactant
        r['theory_mg'] = r['theory_mmol'] * mw
        r['actual_mg'] = r['yield_percent'] = None
        value = _number(r, 'value')
        if r.get('basis') == 'mass' and value is not None:
            r['actual_mg'] = value
            r['yield_percent'] = value / r['theory_mg'] * 100.0
        elif r.get('basis') == 'yield' and value is not None:
            r['yield_percent'] = value
            r['actual_mg'] = r['theory_mg'] * value / 100.0
        if r['yield_percent'] is not None and r['yield_percent'] > 100.0:
            warnings.append(f"{r.get('name') or r['id']}: yield above 100% (wet or impure product, or a wrong "
                            'limiting reagent or molecular weight)')
    reactants = [r for r in rows if r['role'] == 'reactant']
    products = [r for r in rows if r['role'] == 'product']
    totals = {'concentration_m': base / solvent_ml if solvent_ml else None, 'solvent_ml': solvent_ml or None,
              'limiting_mmol': base,
              'input_mg': sum(r['mass_mg'] for r in rows if r['role'] in AMOUNT_ROLES)}
    solvents = [r for r in rows if r['role'] == 'solvent']
    solvent_mg = sum(r['mass_mg'] for r in solvents if r['mass_mg'] is not None)
    totals['solvent_mg'] = solvent_mg or None
    totals['solvents_without_mass'] = sum(1 for r in solvents if r['mass_mg'] is None)
    reactant_mass = sum(r['mw'] * (_number(r, 'coefficient', positive=True, default=1.0)) for r in reactants)
    if products and reactant_mass:
        main = products[0]
        coefficient = _number(main, 'coefficient', positive=True, default=1.0)
        totals['atom_economy_percent'] = main['mw'] * coefficient / reactant_mass * 100.0
        if main['actual_mg'] is not None:
            weighed = sum(r['mass_mg'] for r in reactants)
            totals['reaction_mass_efficiency_percent'] = main['actual_mg'] / weighed * 100.0
    if products and products[0]['actual_mg']:
        # process mass intensity of the reaction step: everything put in per mass of isolated product
        actual = products[0]['actual_mg']
        totals['pmi'] = (totals['input_mg'] + solvent_mg) / actual
        totals['e_factor'] = totals['pmi'] - 1.0
        totals['pmi_no_solvent'] = totals['input_mg'] / actual
    return {'limiting': limiting['id'], 'rows': rows, 'totals': totals, 'warnings': warnings}


def rebase(state: dict, new_limiting: str) -> dict:
    """The same reaction with another limiting row, every amount unchanged."""
    result = compute(state)
    rows = {r['id']: r for r in result['rows']}
    if new_limiting not in rows or rows[new_limiting]['role'] not in AMOUNT_ROLES:
        raise ValueError('limiting must name a reactant, reagent or catalyst row')
    base = rows[new_limiting]['mmol']
    out = deepcopy(state)
    for r in out['rows']:
        computed = rows[r['id']]
        if r['role'] in AMOUNT_ROLES and r['basis'] == 'equiv':
            r['value'] = computed['mmol'] / base
        elif r['role'] == 'solvent' and r['basis'] == 'conc':
            r['basis'], r['value'] = 'volume', computed['volume_ml']
    target = next(r for r in out['rows'] if r['id'] == new_limiting)
    if target['basis'] == 'equiv':
        target['basis'], target['value'] = 'mmol', rows[new_limiting]['mmol']
    out['limiting'] = new_limiting
    return out
