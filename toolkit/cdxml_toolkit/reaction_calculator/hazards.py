"""Hazard reminders for common solvents and reagents: GHS pictograms, H-statements, boiling and flash point.

A built-in table, nothing is looked up or uploaded. Values are the usual classification of the pure
substance as supplier safety data sheets give it (EU CLP wording); suppliers differ in detail, and a
species that is not in the table is reported as not listed instead of being guessed. The table is a
reminder, not a replacement for the supplier's SDS.
"""

from __future__ import annotations

from functools import lru_cache

from rdkit import Chem

DISCLAIMER = 'from a built-in table of common reagents; a reminder, not a substitute for the supplier SDS'

GHS_NAME = {
    'GHS01': 'explosive', 'GHS02': 'flammable', 'GHS03': 'oxidising', 'GHS04': 'gas under pressure',
    'GHS05': 'corrosive', 'GHS06': 'acutely toxic', 'GHS07': 'harmful or irritant', 'GHS08': 'health hazard',
    'GHS09': 'hazardous to the environment',
}

H_TEXT = {
    'H224': 'extremely flammable liquid and vapour', 'H225': 'highly flammable liquid and vapour',
    'H226': 'flammable liquid and vapour', 'H242': 'heating may cause a fire',
    'H260': 'in contact with water releases flammable gases which may ignite spontaneously',
    'H290': 'may be corrosive to metals',
    'H300': 'fatal if swallowed', 'H301': 'toxic if swallowed', 'H302': 'harmful if swallowed',
    'H304': 'may be fatal if swallowed and enters airways',
    'H310': 'fatal in contact with skin', 'H311': 'toxic in contact with skin', 'H312': 'harmful in contact with skin',
    'H314': 'causes severe skin burns and eye damage', 'H315': 'causes skin irritation',
    'H317': 'may cause an allergic skin reaction', 'H318': 'causes serious eye damage',
    'H319': 'causes serious eye irritation',
    'H330': 'fatal if inhaled', 'H331': 'toxic if inhaled', 'H332': 'harmful if inhaled',
    'H335': 'may cause respiratory irritation', 'H336': 'may cause drowsiness or dizziness',
    'H340': 'may cause genetic defects', 'H341': 'suspected of causing genetic defects',
    'H350': 'may cause cancer', 'H351': 'suspected of causing cancer',
    'H360D': 'may damage the unborn child', 'H361d': 'suspected of damaging the unborn child',
    'H361f': 'suspected of damaging fertility',
    'H370': 'causes damage to organs', 'H372': 'causes damage to organs through prolonged or repeated exposure',
    'H373': 'may cause damage to organs through prolonged or repeated exposure',
    'H410': 'very toxic to aquatic life with long lasting effects', 'H411': 'toxic to aquatic life with long lasting effects',
    'H412': 'harmful to aquatic life with long lasting effects', 'H413': 'may cause long lasting harmful effects to aquatic life',
}

# Statements that carry the signal word "Danger"; any other statement gives "Warning".
_DANGER = frozenset({'H224', 'H225', 'H242', 'H260', 'H300', 'H301', 'H304', 'H310', 'H311', 'H314', 'H318', 'H330',
                     'H331', 'H340', 'H350', 'H360D', 'H370', 'H372'})
_NO_SIGNAL = frozenset({'H412', 'H413'})

# smiles, name, bp (C), flash point (C), pictograms, H-statements, note
_PEROXIDES = 'forms explosive peroxides on storage'
_ENTRIES = (
    # solvents
    ('C1CCOC1', 'tetrahydrofuran', 66, -14, 'GHS02 GHS07 GHS08', 'H225 H302 H319 H335 H351', _PEROXIDES),
    ('ClCCl', 'dichloromethane', 40, None, 'GHS07 GHS08', 'H315 H319 H335 H336 H351 H373', None),
    ('ClC(Cl)Cl', 'chloroform', 61, None, 'GHS06 GHS07 GHS08', 'H302 H315 H319 H331 H336 H351 H361d H372', None),
    ('ClCCCl', '1,2-dichloroethane', 83, 13, 'GHS02 GHS06 GHS07 GHS08', 'H225 H302 H315 H319 H331 H335 H350', None),
    ('CN(C)C=O', 'N,N-dimethylformamide', 153, 58, 'GHS02 GHS07 GHS08', 'H226 H312 H319 H332 H360D', None),
    ('CS(C)=O', 'dimethyl sulfoxide', 189, 87, '', '', 'carries dissolved substances through the skin'),
    ('CC#N', 'acetonitrile', 82, 2, 'GHS02 GHS07', 'H225 H302 H312 H319 H332', None),
    ('Cc1ccccc1', 'toluene', 111, 4, 'GHS02 GHS07 GHS08', 'H225 H304 H315 H336 H361d H373', None),
    ('c1ccccc1', 'benzene', 80, -11, 'GHS02 GHS07 GHS08', 'H225 H304 H315 H319 H340 H350 H372', 'carcinogen; use a substitute where one will do'),
    ('CCO', 'ethanol', 78, 13, 'GHS02 GHS07', 'H225 H319', None),
    ('CO', 'methanol', 65, 11, 'GHS02 GHS06 GHS08', 'H225 H301 H311 H331 H370', 'poisonous by skin contact and inhalation as well'),
    ('CC(C)O', 'isopropanol', 82, 12, 'GHS02 GHS07', 'H225 H319 H336', None),
    ('O', 'water', 100, None, '', '', None),
    ('CCOC(C)=O', 'ethyl acetate', 77, -4, 'GHS02 GHS07', 'H225 H319 H336', None),
    ('CCOCC', 'diethyl ether', 35, -45, 'GHS02 GHS07', 'H224 H302 H336', _PEROXIDES),
    ('COC(C)(C)C', 'tert-butyl methyl ether', 55, -28, 'GHS02 GHS07', 'H225 H315', None),
    ('C1COCCO1', '1,4-dioxane', 101, 12, 'GHS02 GHS07 GHS08', 'H225 H319 H335 H350', _PEROXIDES),
    ('CC(C)=O', 'acetone', 56, -17, 'GHS02 GHS07', 'H225 H319 H336', None),
    ('CN1CCCC1=O', 'N-methyl-2-pyrrolidone', 202, 91, 'GHS07 GHS08', 'H315 H319 H335 H360D', None),
    ('CC1CCCO1', '2-methyltetrahydrofuran', 80, -11, 'GHS02 GHS05 GHS07', 'H225 H302 H315 H318', _PEROXIDES),
    ('CCCCC', 'pentane', 36, -49, 'GHS02 GHS07 GHS08 GHS09', 'H225 H304 H336 H411', None),
    ('CCCCCC', 'hexane', 69, -22, 'GHS02 GHS07 GHS08 GHS09', 'H225 H304 H315 H336 H361f H373 H411', None),
    ('CCCCCCC', 'heptane', 98, -4, 'GHS02 GHS07 GHS08 GHS09', 'H225 H304 H315 H336 H410', None),
    ('C1CCCCC1', 'cyclohexane', 81, -18, 'GHS02 GHS07 GHS08 GHS09', 'H225 H304 H315 H336 H410', None),
    # liquid reagents, acids and bases
    ('CCN(CC)CC', 'triethylamine', 89, -11, 'GHS02 GHS05 GHS06', 'H225 H302 H311 H314 H331 H335', None),
    ('CCN(C(C)C)C(C)C', 'N,N-diisopropylethylamine', 127, 10, 'GHS02 GHS05 GHS06', 'H225 H302 H314 H331 H412', None),
    ('c1ccncc1', 'pyridine', 115, 20, 'GHS02 GHS07', 'H225 H302 H312 H315 H319 H332', None),
    ('C1CCNCC1', 'piperidine', 106, 16, 'GHS02 GHS05 GHS06', 'H225 H302 H311 H314 H331', None),
    ('CC(=O)OC(C)=O', 'acetic anhydride', 140, 49, 'GHS02 GHS05 GHS06', 'H226 H302 H314 H330', 'reacts with water'),
    ('CC(=O)O', 'acetic acid', 118, 39, 'GHS02 GHS05', 'H226 H314', None),
    ('OC=O', 'formic acid', 101, 49, 'GHS02 GHS05 GHS06', 'H226 H302 H314 H331', None),
    ('OC(=O)C(F)(F)F', 'trifluoroacetic acid', 72, None, 'GHS05 GHS07', 'H290 H314 H332 H412', 'volatile and strongly corrosive'),
    ('CC(=O)Cl', 'acetyl chloride', 51, 4, 'GHS02 GHS05', 'H225 H314', 'reacts violently with water, releasing HCl'),
    ('ClS(Cl)=O', 'thionyl chloride', 76, None, 'GHS05 GHS06', 'H302 H314 H331', 'reacts violently with water, releasing HCl and SO2'),
    ('CI', 'iodomethane', 42, None, 'GHS06 GHS07 GHS08', 'H301 H312 H315 H331 H335 H351', 'volatile alkylating agent'),
    ('Nc1ccccc1', 'aniline', 184, 70, 'GHS05 GHS06 GHS08 GHS09', 'H301 H311 H317 H318 H331 H341 H351 H372 H410', 'absorbed through the skin'),
    ('O=Cc1ccccc1', 'benzaldehyde', 179, 64, 'GHS07', 'H302 H412', None),
    ('OCc1ccccc1', 'benzyl alcohol', 205, 93, 'GHS07', 'H302 H319 H332', None),
    ('COC(=O)C=C', 'methyl acrylate', 80, -3, 'GHS02 GHS07', 'H225 H302 H312 H315 H317 H319 H332 H335', 'can polymerise exothermically'),
    ('Brc1ccccc1', 'bromobenzene', 156, 51, 'GHS02 GHS07 GHS09', 'H226 H315 H411', None),
    # solids
    ('[BH4-].[Na+]', 'sodium borohydride', None, None, 'GHS02 GHS05 GHS06', 'H260 H301 H314', 'releases flammable hydrogen with water'),
    ('[AlH4-].[Li+]', 'lithium aluminium hydride', None, None, 'GHS02 GHS05', 'H260 H314', 'reacts violently with water, releasing hydrogen'),
    ('[K+].[K+].[O-]C([O-])=O', 'potassium carbonate', None, None, 'GHS07', 'H315 H319 H335', None),
    ('[Cs+].[Cs+].[O-]C([O-])=O', 'caesium carbonate', None, None, 'GHS07', 'H315 H319 H335', None),
    ('[Na+].[OH-]', 'sodium hydroxide', None, None, 'GHS05', 'H290 H314', None),
    ('OOC(=O)c1cccc(Cl)c1', '3-chloroperoxybenzoic acid', None, None, 'GHS02 GHS07', 'H242 H315 H319 H335', 'organic peroxide: keep cool, heating can cause a fire'),
    ('C1CCC(CC1)N=C=NC1CCCCC1', 'N,N\'-dicyclohexylcarbodiimide', None, None, 'GHS05 GHS06', 'H302 H311 H317 H318', 'strong skin sensitiser'),
    ('c1ccc(cc1)P(c1ccccc1)c1ccccc1', 'triphenylphosphine', None, None, 'GHS07 GHS08', 'H302 H317 H373 H413', None),
    ('[N-]=[N+]=[N-].[Na+]', 'sodium azide', None, None, 'GHS06 GHS08 GHS09', 'H300 H310 H373 H410', 'forms explosive azides with heavy metals and toxic HN3 with acids'),
)


@lru_cache(maxsize=1)
def _table() -> dict:
    table = {}
    for smiles, name, bp, flash, ghs, h, note in _ENTRIES:
        mol = Chem.MolFromSmiles(smiles)
        codes = h.split()
        signal = None if not set(codes) - _NO_SIGNAL else ('Danger' if set(codes) & _DANGER else 'Warning')
        entry = {'name': name, 'smiles': Chem.MolToSmiles(mol), 'bp_c': bp, 'flash_c': flash, 'ghs': ghs.split(),
                 'h': codes, 'signal': signal, 'note': note}
        table[entry['smiles']] = entry
    return table


def lookup(smiles: str) -> dict | None:
    """The entry for a structure (stereo and drawing coordinates ignored), or None when it is not listed."""
    mol = Chem.MolFromSmiles(smiles) if smiles else None
    if mol is None:
        return None
    flat = Chem.Mol(mol)
    Chem.RemoveStereochemistry(flat)
    entry = _table().get(Chem.MolToSmiles(flat))
    return {**entry, 'ghs': list(entry['ghs']), 'h': list(entry['h'])} if entry else None


def entries() -> list[dict]:
    return [lookup(smiles) for smiles in _table()]


def summary(entry: dict) -> str:
    """One line: signal word, pictograms, statements, boiling and flash point, note."""
    parts = [entry['signal'] or 'no GHS classification']
    if entry['ghs']:
        parts.append(' '.join(entry['ghs']))
    if entry['h']:
        parts.append(' '.join(entry['h']))
    if entry['bp_c'] is not None:
        parts.append(f"bp {entry['bp_c']} °C")
    if entry['flash_c'] is not None:
        parts.append(f"flash point {entry['flash_c']} °C")
    if entry.get('note'):
        parts.append(entry['note'])
    return '; '.join(parts)


def for_rows(rows: list[dict]) -> list[dict]:
    """A safety item per reactant, reagent, catalyst and solvent row: the entry, or ``listed: False``."""
    items = []
    for row in rows:
        if row['role'] == 'product':
            continue
        found = lookup(row.get('smiles') or '')
        item = {'id': row['id'], 'name': row['name'], 'role': row['role']}
        if found is None:
            items.append({**item, 'listed': False})
        else:
            items.append({**item, 'listed': True, **{k: found[k] for k in ('signal', 'ghs', 'h', 'bp_c', 'flash_c', 'note')}})
    return items


def lines(items: list[dict]) -> list[str]:
    """Text lines for a table footer: the heading, one line per listed species, the species not listed."""
    if not items:
        return []
    out = [f'Safety reminders ({DISCLAIMER}):']
    out += [f"{item['name']}: {summary(item)}." for item in items if item['listed']]
    missing = [item['name'] for item in items if not item['listed']]
    if missing:
        out.append(f"Species not listed in the safety table (check the supplier SDS): {', '.join(missing)}.")
    return out
