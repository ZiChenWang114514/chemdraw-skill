"""High-resolution MS characterization lines ("calcd for C9H10O2Na [M+Na]+ 173.0573").

The ion formula and m/z are computed from a grounded structure: the neutral monoisotopic mass
plus the atoms an adduct adds or removes, less the electron mass for a positive ion and plus it
for a negative one. This is the convention of ``molecule_report``; ``electron_mass=False``
reproduces the value ChemDraw-style calculators give (differences are about 0.0005 per charge).
"""

from __future__ import annotations

import re
from collections import Counter

from rdkit import Chem
from rdkit.Chem import rdMolDescriptors

ELECTRON = 0.00054858
_TABLE = Chem.GetPeriodicTable()

# adduct -> (atoms added (+) or removed (-), charge)
ADDUCTS = {
    '[M+H]+': ({'H': 1}, 1),
    '[M+Li]+': ({'Li': 1}, 1),
    '[M+Na]+': ({'Na': 1}, 1),
    '[M+K]+': ({'K': 1}, 1),
    '[M+NH4]+': ({'N': 1, 'H': 4}, 1),
    '[M+H-H2O]+': ({'H': -1, 'O': -1}, 1),
    '[M+2H]2+': ({'H': 2}, 2),
    '[M-H]-': ({'H': -1}, -1),
    '[M-2H]2-': ({'H': -2}, -2),
    '[M+Cl]-': ({'Cl': 1}, -1),
    '[M+Br]-': ({'Br': 1}, -1),
    '[M+HCOO]-': ({'C': 1, 'H': 1, 'O': 2}, -1),
    '[M+CH3COO]-': ({'C': 2, 'H': 3, 'O': 2}, -1),
    'M+.': ({}, 1),  # electron impact molecular ion
}
ALIASES = {'[M]+.': 'M+.', '[M]+•': 'M+.', 'M+•': 'M+.', '[M+•]+': 'M+.', '[M]•+': 'M+.', 'M': 'M+.'}
DEFAULT = {'positive': '[M+H]+', 'negative': '[M-H]-'}
IONIZATION = re.compile(r'^[A-Za-z0-9][A-Za-z0-9 \-+/]{0,19}$')


def _hill(counts) -> str:
    def part(symbol):
        return f'{symbol}{counts[symbol]}' if counts[symbol] > 1 else symbol
    symbols = [s for s, n in counts.items() if n]
    if counts.get('C'):
        order = [s for s in ('C', 'H') if s in symbols] + sorted(s for s in symbols if s not in ('C', 'H'))
    else:
        order = sorted(symbols)
    return ''.join(part(s) for s in order)


def _counts(mol) -> Counter:
    counts = Counter()
    for atom in Chem.AddHs(mol).GetAtoms():
        counts[atom.GetSymbol()] += 1
    return counts


def atoms_mass(mol) -> float:
    """Sum of the monoisotopic (or labelled-isotope) atom masses, without any electron correction.

    RDKit's ExactMolWt subtracts the electron mass of a charged molecule in recent versions and
    not in older ones; summing the atoms keeps the result independent of the RDKit version.
    """
    total = 0.0
    for atom in Chem.AddHs(mol).GetAtoms():
        number, isotope = atom.GetAtomicNum(), atom.GetIsotope()
        total += _TABLE.GetMassForIsotope(number, isotope) if isotope else _TABLE.GetMostCommonIsotopeMass(number)
    return total


def default_adduct(mol, mode: str = 'positive', ionization: str = 'ESI') -> str:
    if Chem.GetFormalCharge(mol):
        return '[M]+' if Chem.GetFormalCharge(mol) > 0 else '[M]-'
    if ionization.upper() == 'EI':
        return 'M+.'
    return DEFAULT[mode]


def hrms_entry(mol, adduct: str | None = '[M+H]+', *, ionization: str = 'ESI', decimals: int = 4,
               found: float | None = None, electron_mass: bool = True) -> dict:
    """{adduct, ion_formula, charge, calcd_mz, found_mz, error_ppm, line} for one ion of ``mol``."""
    if not IONIZATION.match(ionization or ''):
        raise ValueError('ionization is a short label such as ESI, APCI, EI or ESI-TOF')
    if not 1 <= decimals <= 6:
        raise ValueError('decimals must be between 1 and 6')
    mol = Chem.RemoveHs(mol)
    if any(a.GetAtomicNum() == 0 for a in mol.GetAtoms()):
        raise ValueError('generic atoms (R groups, *) have no mass; draw a specific structure first')
    charge_of_mol = Chem.GetFormalCharge(mol)
    neutral = _counts(mol)
    exact = atoms_mass(mol)
    if charge_of_mol:
        if adduct not in (None, '[M]+', '[M]-', f'[M]{"+" if charge_of_mol > 0 else "-"}'):
            raise ValueError('The structure is already charged; its ion is [M]+ or [M]-, adducts do not apply')
        sign = '+' if charge_of_mol > 0 else '-'
        z = abs(charge_of_mol)
        name = f'[M]{sign}' if z == 1 else f'[M]{z}{sign}'
        added, charge = {}, charge_of_mol
    else:
        key = ALIASES.get(adduct, adduct) if adduct else '[M+H]+'
        if key not in ADDUCTS:
            raise ValueError(f'Unknown adduct {adduct!r}. Supported adducts: ' + ', '.join(ADDUCTS))
        added, charge = ADDUCTS[key]
        name = 'M+.' if key == 'M+.' else key
    ion = Counter(neutral)
    delta = 0.0
    for symbol, number in added.items():
        if ion[symbol] + number < 0:
            raise ValueError(f'The structure has no more hydrogen to lose for {name}' if symbol == 'H'
                             else f'The structure has no {symbol} to lose for {name}')
        ion[symbol] += number
        delta += number * _TABLE.GetMostCommonIsotopeMass(symbol)
    z = abs(charge)
    mz = (exact + delta - (charge * ELECTRON if electron_mass else 0.0)) / z
    # papers write the attached cation or anion last: C9H10O2Na, C9H10O2Cl
    tail = [s for s in ('Li', 'Na', 'K', 'Cl', 'Br') if added.get(s, 0) > 0 and not neutral[s]]
    formula = _hill(Counter({k: v for k, v in ion.items() if k not in tail})) + ''.join(
        f'{s}{ion[s]}' if ion[s] > 1 else s for s in tail)
    shown = '[M]+•' if name == 'M+.' else name
    line = f'HRMS ({ionization}) m/z calcd for {formula} {shown} {mz:.{decimals}f}'
    entry = {'adduct': shown, 'ion_formula': formula, 'charge': charge, 'calcd_mz': round(mz, 5),
             'found_mz': None, 'error_ppm': None}
    if found is not None:
        entry['found_mz'] = float(found)
        entry['error_ppm'] = round((float(found) - mz) / mz * 1e6, 1)
        line += f', found {float(found):.{decimals}f}'
    entry['line'] = line
    entry['molecular_formula'] = rdMolDescriptors.CalcMolFormula(mol)
    return entry
