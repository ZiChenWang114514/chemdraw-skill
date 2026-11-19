"""High-resolution MS characterization lines ("calcd for C9H10O2Na [M+Na]+ 173.0573").

A salt is calculated for its organic ion (see :func:`ion_component`); isotope labels stay in the
formula (D, T, 13C ...).

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


_ISOTOPE_SYMBOLS = {('H', 2): 'D', ('H', 3): 'T'}


def _symbol(atom) -> str:
    """Formula symbol of an atom: D and T for hydrogen isotopes, '13C' style for other labels."""
    symbol, isotope = atom.GetSymbol(), atom.GetIsotope()
    if not isotope:
        return symbol
    return _ISOTOPE_SYMBOLS.get((symbol, isotope), f'{isotope}{symbol}')


def _element(symbol: str) -> str:
    return {'D': 'H', 'T': 'H'}.get(symbol, symbol.lstrip('0123456789'))


def _hill(counts) -> str:
    """Hill order; an isotope label follows its element (C, 13C, H, D, T, then the rest)."""
    def part(symbol):
        return f'{symbol}{counts[symbol]}' if counts[symbol] > 1 else symbol
    symbols = [s for s, n in counts.items() if n]

    def key(symbol):
        element = _element(symbol)
        plain = symbol == element
        if counts.get('C') or any(_element(s) == 'C' for s in symbols):
            rank = {'C': 0, 'H': 1}.get(element, 2)
        else:
            rank = 2
        return (rank, element, not plain, symbol)
    return ''.join(part(s) for s in sorted(symbols, key=key))


def _counts(mol) -> Counter:
    counts = Counter()
    for atom in Chem.AddHs(mol).GetAtoms():
        counts[_symbol(atom)] += 1
    return counts


def organic_component(mol):
    """The fragment with most carbons (then most heavy atoms); the molecule itself if it has one."""
    frags = Chem.GetMolFrags(mol, asMols=True)
    if len(frags) == 1:
        return mol
    return max(frags, key=lambda m: (sum(1 for a in m.GetAtoms() if a.GetAtomicNum() == 6),
                                     m.GetNumHeavyAtoms()))


def ion_component(mol):
    """(component, kept_charge) of a multi-component record: the organic ion of a salt.

    The component is the fragment with most carbons (then most heavy atoms). A charge that a
    proton can remove or add (an ammonium or carboxylate) is neutralised; a permanent charge
    (quaternary ammonium) is kept and returned. A single-component molecule is returned as is.
    """
    if len(Chem.GetMolFrags(mol)) == 1:
        return mol, Chem.GetFormalCharge(mol)
    comp = organic_component(mol)
    if Chem.GetFormalCharge(comp) == 0:
        return comp, 0
    try:
        from rdkit.Chem.MolStandardize import rdMolStandardize
        comp = rdMolStandardize.Uncharger().uncharge(Chem.Mol(comp))
    except Exception:
        pass
    return comp, Chem.GetFormalCharge(comp)


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
    mol, _charge = ion_component(mol)
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
    mol, _charge = ion_component(mol)  # a salt is measured as its organic ion
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
