"""Stoichiometry state from a reaction: rows with structure, molecular weight and a starting basis.

Anything the caller did not fix gets a default that is marked ``assumed`` so the materials tables
can show which numbers are choices rather than data.
"""

from __future__ import annotations

from rdkit import Chem

from . import library
from .engine import compute

AMOUNT_KEYS = {'equiv': 'equiv', 'mmol': 'mmol', 'mass_mg': 'mass', 'volume_ml': 'volume'}
DEFAULT_MOLARITY = 0.2
DEFAULT_CATALYST_EQUIV = 0.05
DEFAULT_REAGENT_EQUIV = 1.0


def _is_metal_complex(smiles: str) -> bool:
    mol = Chem.MolFromSmiles(smiles)
    return mol is not None and any(a.GetSymbol() in library.TRANSITION_METALS for a in mol.GetAtoms())


def _given_amount(record):
    given = [key for key in AMOUNT_KEYS if record.get(key) is not None]
    if len(given) > 1:
        raise ValueError(f"{record.get('label') or record.get('name') or record.get('smiles')}: give only one of "
                         f"{', '.join(AMOUNT_KEYS)}, found {', '.join(given)}")
    return (AMOUNT_KEYS[given[0]], float(record[given[0]])) if given else (None, None)


def _name(species):
    record = species['record']
    given = record.get('name') or record.get('label')
    if given and not str(given).startswith('fragment '):
        return str(given)
    known = library.by_smiles(species['smiles'])
    return known['name'] if known else species['formula']


def _hrms_line(smiles):
    """The calculated HRMS sentence of a product, or None when its ion cannot be written."""
    from ..characterization import default_adduct, hrms_entry
    mol = Chem.MolFromSmiles(smiles)
    try:
        return hrms_entry(mol, default_adduct(mol))['line']
    except ValueError:
        return None


def _row(species, row_id, role, known):
    record = species['record']
    row = {'id': row_id, 'role': role, 'name': _name(species), 'formula': species['formula'],
           'smiles': species['smiles'], 'mw': round(species['mw'], 4), 'coefficient': species['coefficient'],
           'density': None, 'solution_m': None, 'purity': 1.0}
    density = record.get('density_g_ml') or (known['density'] if known and role != 'product' else None)
    row['density'] = float(density) if density else None
    if role == 'product':
        row['hrms'] = _hrms_line(species['smiles'])
    if record.get('concentration_m'):
        row['solution_m'] = float(record['concentration_m'])
    if record.get('purity') is not None:
        purity = float(record['purity'])
        row['purity'] = purity / 100.0 if purity > 1 else purity
    return row


def build_state(sides: dict, options: dict | None = None) -> dict:
    """Rows for one reaction; ``sides`` maps reactants, agents and products to species dicts."""
    options = dict(options or {})
    unknown = set(options) - {'scale_mmol', 'limiting', 'molarity', 'title', 'step'}
    if unknown:
        raise ValueError(f'Unknown options: {sorted(unknown)}')
    scale = options.get('scale_mmol', 1.0)
    if isinstance(scale, bool) or not isinstance(scale, (int, float)) or scale <= 0:
        raise ValueError('scale_mmol must be a positive number')
    molarity = options.get('molarity', DEFAULT_MOLARITY)
    if isinstance(molarity, bool) or not isinstance(molarity, (int, float)) or molarity <= 0:
        raise ValueError('molarity must be a positive number')
    reactants, agents, products = sides['reactants'], sides['agents'], sides['products']
    limiting = options.get('limiting', 0)
    if not isinstance(limiting, int) or isinstance(limiting, bool) or not 0 <= limiting < len(reactants):
        raise ValueError(f'limiting must be a reactant index between 0 and {len(reactants) - 1}')
    rows, base = [], reactants[limiting]['coefficient']
    for index, species in enumerate(reactants):
        row = _row(species, f'r{index + 1}', 'reactant', library.by_smiles(species['smiles']))
        basis, value = _given_amount(species['record'])
        if index == limiting:
            if basis == 'equiv':
                raise ValueError('The limiting reactant sets the scale; give it mmol, mass_mg or volume_ml')
            row['basis'], row['value'] = (basis, value) if basis else ('mmol', float(scale))
            row['assumed'] = basis is None
        else:
            row['basis'], row['value'] = (basis, value) if basis else ('equiv', species['coefficient'] / base)
            row['assumed'] = basis is None
        rows.append(row)
    solvents = 0
    for index, species in enumerate(agents):
        known = library.by_smiles(species['smiles'])
        record = species['record']
        role = record.get('role') or ('solvent' if known and known['role'] == 'solvent' else
                                      'catalyst' if _is_metal_complex(species['smiles']) else 'reagent')
        if role not in ('solvent', 'reagent', 'catalyst'):
            raise ValueError("an agent's role must be solvent, reagent or catalyst")
        row = _row(species, f'a{index + 1}', role, known)
        basis, value = _given_amount(record)
        if role == 'solvent':
            if basis == 'volume':
                row['basis'], row['value'], row['assumed'] = 'volume', value, False
            elif solvents == 0:
                row['basis'], row['value'], row['assumed'] = 'conc', float(molarity), True
            else:
                row['basis'], row['value'], row['assumed'] = 'volume', 0.0, True
            solvents += 1
        else:
            default = DEFAULT_CATALYST_EQUIV if role == 'catalyst' else DEFAULT_REAGENT_EQUIV
            row['basis'], row['value'] = (basis, value) if basis else ('equiv', default)
            row['assumed'] = basis is None
        rows.append(row)
    for index, species in enumerate(products):
        row = _row(species, f'p{index + 1}', 'product', None)
        record = species['record']
        if record.get('isolated_mg') is not None:
            row['basis'], row['value'] = 'mass', float(record['isolated_mg'])
        elif record.get('yield_percent') is not None:
            row['basis'], row['value'] = 'yield', float(record['yield_percent'])
        else:
            row['basis'], row['value'] = None, None
        row['assumed'] = False
        rows.append(row)
    state = {'title': options.get('title') or ' + '.join(r['name'] for r in rows if r['role'] == 'reactant')
             + ' → ' + ' + '.join(r['name'] for r in rows if r['role'] == 'product'),
             'limiting': rows[limiting]['id'], 'rows': rows}
    compute(state)  # fail now, with the reason, when the starting amounts cannot be resolved
    return state

