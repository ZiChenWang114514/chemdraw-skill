"""Deterministic chemistry reports: property sheets, reaction balance, structure export and names.

Every number comes from RDKit applied to a grounded structure (SMILES, MOL/SDF or a CDXML
fragment read back from the file). Nothing here recognises, guesses or edits structures.
"""
from __future__ import annotations

import csv
import io
import json
import sys
from collections import Counter
from fractions import Fraction
from math import gcd
from pathlib import Path
from xml.etree import ElementTree as ET

from rdkit import Chem, rdBase
from rdkit.Chem import Descriptors, Lipinski, QED, rdMolDescriptors
from rdkit.Chem import Crippen

from ..chemistry_semantics import read_fragments
from . import artifact_safety
from .chemistry_compare import _bridge_factory
from .figure_tools import _mol as _single_molecule

MAX_STRUCTURES = 256
MAX_EXPORT = 2000
ELECTRON = 0.00054858
PROTON = 1.00727646

# name, charge, mass added to M (electrons already accounted for), ESI mode
ADDUCTS = (
    ('[M+H]+', 1, 1.00727646, 'positive'),
    ('[M+NH4]+', 1, 18.03382, 'positive'),
    ('[M+Na]+', 1, 22.98922, 'positive'),
    ('[M+K]+', 1, 38.96316, 'positive'),
    ('[M+H-H2O]+', 1, 1.00727646 - 18.01056468, 'positive'),
    ('[M+2H]2+', 2, 2 * 1.00727646, 'positive'),
    ('[M-H]-', -1, -1.00727646, 'negative'),
    ('[M+Cl]-', -1, 34.96940, 'negative'),
    ('[M+HCOO]-', -1, 44.99820, 'negative'),
    ('[M+CH3COO]-', -1, 59.01385, 'negative'),
    ('[M-2H]2-', -2, -2 * 1.00727646, 'negative'),
)

# Natural isotope abundance (percent) by offset from the lightest isotope.
ISOTOPES = {
    'H': [99.9885, 0.0115], 'C': [98.93, 1.07], 'N': [99.636, 0.364],
    'O': [99.757, 0.038, 0.205], 'F': [100.0], 'P': [100.0], 'I': [100.0],
    'Na': [100.0], 'S': [94.99, 0.75, 4.25, 0.0, 0.01], 'Cl': [75.76, 0.0, 24.24],
    'Br': [50.69, 0.0, 49.31], 'Si': [92.223, 4.685, 3.092], 'B': [19.9, 80.1],
    'K': [93.258, 0.012, 6.730],
}
PEAKS = 5

BYPRODUCTS = {
    'H2O': 'water', 'HCl': 'hydrogen chloride', 'HBr': 'hydrogen bromide', 'HI': 'hydrogen iodide',
    'HF': 'hydrogen fluoride', 'CO2': 'carbon dioxide', 'H2': 'hydrogen', 'N2': 'nitrogen',
    'NH3': 'ammonia', 'CH4O': 'methanol', 'C2H6O': 'ethanol', 'C2H4O2': 'acetic acid',
    'CO': 'carbon monoxide', 'O2': 'oxygen', 'H2O2': 'hydrogen peroxide', 'H2S': 'hydrogen sulfide',
    'NaCl': 'sodium chloride', 'SO2': 'sulfur dioxide', 'N2O': 'nitrous oxide', 'Cl2': 'chlorine',
}


# --- input records ---------------------------------------------------------

def _label(record, index):
    given = record.get('label') or record.get('name')
    return given if given else f'#{index}'


def _check_grounded(mol, label):
    if any(atom.GetAtomicNum() == 0 for atom in mol.GetAtoms()):
        raise ValueError(f'{label}: generic atoms (R groups, *) have no mass or composition; '
                         'draw a specific structure first')


def _expand(records, *, limit):
    """Records -> [{'label', 'mol', 'source', 'record'}]; CDXML/SDF files can expand to all members."""
    if isinstance(records, (str, dict)):
        records = [records]
    if not records:
        raise ValueError('Provide at least one grounded structure')
    expanded = []
    for record in records:
        record = {'smiles': record} if isinstance(record, str) else dict(record)
        path = Path(record['file']).expanduser().resolve() if record.get('file') else None
        if path is not None and record.get('all_fragments'):
            if not path.is_file():
                raise ValueError(f'Input file does not exist: {path}')
            for ident, mol, name in _members(path):
                expanded.append({'mol': mol, 'record': {**record, 'label': record.get('label') or name},
                                 'source': {'file': str(path), 'fragment_id': ident}})
            continue
        if 'mol' in record:  # a structure already read from a drawn file
            mol = record['mol']
            source = {'fragment_id': record.get('fragment_id')}
            record = {k: v for k, v in record.items() if k not in ('mol', 'fragment_id')}
        else:
            mol = _single_molecule(record)
            source = {'file': str(path), 'fragment_id': None} if path else {'smiles': record.get('smiles')}
        expanded.append({'mol': mol, 'record': record, 'source': source})
        if len(expanded) > limit:
            break
    if len(expanded) > limit:
        raise ValueError(f'At most {limit} structures per call')
    for index, item in enumerate(expanded, 1):
        item['label'] = _label(item['record'], index)
    return expanded


def _members(path):
    """(fragment_id, mol, name) for each structure in a CDXML, MOL, SDF or SMILES file."""
    suffix = path.suffix.lower()
    if suffix == '.cdxml':
        try:
            return [(ident, mol, None) for ident, mol in read_fragments(path)]
        except ET.ParseError as exc:
            raise ValueError(f'Not a readable CDXML file: {path}') from exc
    if suffix == '.sdf':
        out = []
        for index, mol in enumerate(Chem.SDMolSupplier(str(path), removeHs=False)):
            if mol is None:
                raise ValueError(f'Unreadable SDF record {index + 1} in {path.name}')
            out.append((str(index + 1), mol, mol.GetProp('_Name') if mol.HasProp('_Name') and mol.GetProp('_Name') else None))
        return out
    if suffix == '.mol':
        mol = Chem.MolFromMolFile(str(path), removeHs=False)
        if mol is None:
            raise ValueError(f'Unreadable MOL file: {path}')
        return [('1', mol, mol.GetProp('_Name') if mol.HasProp('_Name') and mol.GetProp('_Name') else None)]
    if suffix in ('.smi', '.smiles', '.txt'):
        out = []
        for number, line in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
            parts = line.split(None, 1)
            if not parts or parts[0].startswith('#'):
                continue
            mol = Chem.MolFromSmiles(parts[0])
            if mol is None:
                raise ValueError(f'Invalid SMILES on line {number} of {path.name}')
            out.append((str(number), mol, parts[1].strip() if len(parts) > 1 else None))
        return out
    if suffix == '.cdx':
        raise ValueError('Binary CDX is not read directly; convert it with convert_cdx_cdxml first')
    raise ValueError(f'Unsupported structure file {path.name}: use CDXML, MOL, SDF or SMILES')


# --- publication of text artifacts -----------------------------------------

def _publish(output_path, renderers):
    """Write one file in the format its extension names, never replacing an existing file."""
    suffix = Path(output_path).suffix.lower()
    if suffix not in renderers:
        raise ValueError(f'output_path must end in one of {sorted(renderers)}')
    target = artifact_safety.resolve_destination(source=None, output_path=output_path,
                                                 tag='report', suffix=suffix)
    with artifact_safety.staging_file(target) as stage:
        stage.write_text(renderers[suffix](), encoding='utf-8', newline='')
        artifact_safety.publish_file(stage, target)
    return target


def _csv(rows, columns):
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=columns, extrasaction='ignore', lineterminator='\n')
    writer.writeheader()
    for row in rows:
        writer.writerow({key: ('' if row.get(key) is None else row.get(key)) for key in columns})
    return buffer.getvalue()


def _markdown(rows, columns, headings=None):
    headings = headings or columns
    lines = ['| #  | ' + ' | '.join(headings) + ' |', '| --- | ' + ' | '.join('---' for _ in columns) + ' |']
    for index, row in enumerate(rows, 1):
        cells = ['' if row.get(key) is None else str(row.get(key)) for key in columns]
        lines.append(f'| {index} | ' + ' | '.join(cell.replace('|', '\\|') for cell in cells) + ' |')
    return '\n'.join(lines) + '\n'


def _inchi(mol):
    """(InChI, InChIKey), or (None, None) when the structure has none (generic atoms)."""
    with rdBase.BlockLogs():
        inchi = Chem.MolToInchi(mol) or None
    return inchi, (Chem.InchiToInchiKey(inchi) if inchi else None)


def _smiles(mol):
    """CXSMILES without the drawing coordinates a CDXML read-back attaches."""
    clean = Chem.RemoveHs(mol)
    clean.RemoveAllConformers()
    return Chem.MolToCXSmiles(clean)


# --- molecule_report --------------------------------------------------------

def _isotope_pattern(mol):
    counts = Counter()
    for atom in Chem.AddHs(mol).GetAtoms():
        if atom.GetIsotope():
            return None
        counts[atom.GetSymbol()] += 1
    if any(symbol not in ISOTOPES for symbol in counts):
        return None
    total = [1.0] + [0.0] * (PEAKS - 1)
    for symbol, number in counts.items():
        element = [x / 100.0 for x in ISOTOPES[symbol]][:PEAKS]
        for _ in range(number):
            total = [sum(total[i] * element[k - i] for i in range(k + 1) if 0 <= k - i < len(element))
                     for k in range(PEAKS)]
    tallest = max(total)
    return [{'offset': k, 'relative_percent': round(value / tallest * 100.0, 2)}
            for k, value in enumerate(total)]


def _adducts(mol, exact):
    charge = Chem.GetFormalCharge(mol)
    if charge:
        z = abs(charge)
        from ..characterization import atoms_mass
        mz = (atoms_mass(mol) - charge * ELECTRON) / z
        sign = '+' if charge > 0 else '-'
        name = f'[M]{sign}' if z == 1 else f'[M]{z}{sign}'
        return [{'name': name, 'mz': round(mz, 5), 'mode': 'positive' if charge > 0 else 'negative'}]
    return [{'name': name, 'mz': round((exact + delta) / abs(z), 5), 'mode': mode}
            for name, z, delta, mode in ADDUCTS]


def _hill(counts):
    def part(key):
        n = counts[key]
        return f'{key}{n}' if n > 1 else key
    keys = [k for k, n in counts.items() if n]
    if 'C' in counts and counts['C']:
        first = [k for k in ('C', 'H') if k in keys]
        rest = sorted(k for k in keys if k not in ('C', 'H'))
        return ''.join(part(k) for k in first + rest)
    return ''.join(part(k) for k in sorted(keys))


def _properties(mol):
    mol = Chem.RemoveHs(mol)
    exact = Descriptors.ExactMolWt(mol)
    mw = Descriptors.MolWt(mol)
    logp = Crippen.MolLogP(mol)
    tpsa = rdMolDescriptors.CalcTPSA(mol)
    hbd, hba = Lipinski.NumHDonors(mol), Lipinski.NumHAcceptors(mol)
    rotatable = rdMolDescriptors.CalcNumRotatableBonds(mol)
    centers = Chem.FindMolChiralCenters(mol, includeUnassigned=True, useLegacyImplementation=False)
    lipinski_rules = {'mw_le_500': mw <= 500, 'logp_le_5': logp <= 5, 'hbd_le_5': hbd <= 5, 'hba_le_10': hba <= 10}
    veber_rules = {'rotatable_le_10': rotatable <= 10, 'tpsa_le_140': tpsa <= 140}
    try:
        qed = round(QED.qed(mol), 3)
    except Exception:  # RDKit's QED rejects a few unusual valences
        qed = None
    inchi, inchikey = _inchi(mol)
    return {
        'smiles': _smiles(mol),
        'formula': rdMolDescriptors.CalcMolFormula(mol),
        'mw': round(mw, 3), 'exact_mass': round(exact, 5),
        'inchi': inchi, 'inchikey': inchikey,
        'charge': Chem.GetFormalCharge(mol), 'components': len(Chem.GetMolFrags(mol)),
        'heavy_atoms': mol.GetNumHeavyAtoms(),
        'rings': rdMolDescriptors.CalcNumRings(mol), 'aromatic_rings': rdMolDescriptors.CalcNumAromaticRings(mol),
        'stereocenters': {'defined': sum(1 for _, tag in centers if tag != '?'),
                          'undefined': sum(1 for _, tag in centers if tag == '?')},
        'fraction_csp3': round(rdMolDescriptors.CalcFractionCSP3(mol), 3),
        'logp': round(logp, 3), 'tpsa': round(tpsa, 2), 'hbd': hbd, 'hba': hba,
        'rotatable_bonds': rotatable, 'qed': qed,
        'lipinski': {'violations': sum(1 for ok in lipinski_rules.values() if not ok), 'rules': lipinski_rules},
        'veber': {'pass': all(veber_rules.values()), 'rules': veber_rules},
        'adducts': _adducts(mol, exact), 'isotope_pattern': _isotope_pattern(mol),
    }


REPORT_COLUMNS = ['label', 'formula', 'mw', 'exact_mass', 'mz_pos', 'mz_neg', 'logp', 'tpsa', 'hbd', 'hba',
                  'rotatable_bonds', 'lipinski_violations', 'inchikey', 'smiles']
REPORT_HEADINGS = ['label', 'formula', 'MW', 'exact mass', '[M+H]+', '[M-H]-', 'cLogP', 'TPSA', 'HBD', 'HBA',
                   'RotB', 'Ro5 violations', 'InChIKey', 'SMILES']


def _flat(row):
    adducts = {a['name']: a['mz'] for a in row['adducts']}
    return {**row, 'mz_pos': adducts.get('[M+H]+', adducts.get('[M]+')),
            'mz_neg': adducts.get('[M-H]-', adducts.get('[M]-')),
            'lipinski_violations': row['lipinski']['violations']}


def molecule_report(molecules: list[dict], output_path: str | None = None) -> dict:
    """Property sheet for grounded molecules: formula, masses, MS adducts, drug-likeness.

    Each record is a SMILES/CXSMILES, molblock or file (CDXML/MOL/SDF) record with an optional
    label; a bare SMILES string also works. A CDXML or SDF record with all_fragments=true
    contributes every structure in the file. Reports formula, average and monoisotopic mass,
    InChI/InChIKey, ESI adduct m/z values (positive and negative mode, electron mass included),
    the isotope pattern scaled to the tallest peak, Crippen logP, TPSA, H-bond donors and
    acceptors, rotatable bonds, QED, stereocentre counts and Lipinski/Veber rule results.
    Descriptors are computed by RDKit from the structure as given; logP and TPSA are
    calculated estimates, not measurements, and generic atoms (R groups) are rejected.
    output_path ends in .json, .csv or .md and is never overwritten. At most 256 structures.
    """
    warnings, rows = [], []
    for item in _expand(molecules, limit=MAX_STRUCTURES):
        _check_grounded(item['mol'], item['label'])
        row = {'label': item['label'], 'source': item['source'], **_properties(item['mol'])}
        if row['components'] > 1:
            warnings.append(f"{row['label']}: {row['components']} components; values describe the whole record, "
                            'not the largest fragment.')
        if row['charge']:
            warnings.append(f"{row['label']}: net charge {row['charge']:+d}; adducts are reported as the "
                            'intact ion only.')
        rows.append(row)
    flat = [_flat(r) for r in rows]
    markdown = _markdown(flat, REPORT_COLUMNS, REPORT_HEADINGS)
    result = {'ok': True, 'operation': 'molecule_report', 'count': len(rows), 'results': rows,
              'markdown': markdown, 'warnings': warnings}
    if output_path:
        target = _publish(output_path, {
            '.json': lambda: json.dumps({'results': rows}, ensure_ascii=False, indent=2),
            '.csv': lambda: _csv(flat, REPORT_COLUMNS),
            '.md': lambda: markdown,
        })
        result = artifact_safety.with_artifacts({**result, 'output_path': str(target)}, [target])
    return result


# --- check_reaction_balance --------------------------------------------------

def _composition(mol):
    counts = Counter()
    for atom in Chem.AddHs(mol).GetAtoms():
        if atom.GetAtomicNum() == 0:
            raise ValueError('generic atoms (R groups, *) cannot be balanced; draw specific structures first')
        symbol = atom.GetSymbol()
        counts[f'[{atom.GetIsotope()}{symbol}]' if atom.GetIsotope() else symbol] += 1
    return counts


def _species(item, coefficient, role):
    counts = _composition(item['mol'])
    formula = rdMolDescriptors.CalcMolFormula(item['mol'])
    label = formula if item['label'].startswith('#') else item['label']
    return {'label': label, 'role': role, 'coefficient': coefficient,
            'formula': formula,
            'smiles': _smiles(item['mol']),
            'mw': Descriptors.MolWt(item['mol']), 'charge': Chem.GetFormalCharge(item['mol']),
            'counts': counts, 'record': item['record']}


def _coefficient(record):
    value = record.get('coefficient', 1)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0 or value > 99:
        raise ValueError('coefficient must be a number between 0 and 99')
    return int(value) if float(value).is_integer() else float(value)


def _side(records, role):
    items = _expand(records, limit=MAX_STRUCTURES) if records else []
    return [_species(item, _coefficient(item['record']), role) for item in items]


def _from_smiles(text):
    if text.count('>') != 2:
        raise ValueError('A reaction string needs the form reactants>agents>products, for example CCO.CC(=O)O>>CCOC(C)=O.O')
    reactants, agents, products = (part.strip() for part in text.split('>'))
    if not reactants or not products:
        raise ValueError('The reaction string needs structures on both sides of the arrow')
    split = lambda part: [{'smiles': s} for s in part.split('.') if s]
    return {'reactants': split(reactants), 'agents': split(agents), 'products': split(products)}


def _from_cdxml(path, steps):
    path = Path(path).expanduser().resolve()
    if not path.is_file():
        raise ValueError(f'Input file does not exist: {path}')
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError as exc:
        raise ValueError(f'Not a readable CDXML file: {path}') from exc
    elements = list(root.iter('step'))
    if not elements:
        raise ValueError('No reaction step is stored in this file (a loose arrow and structures do not '
                         'define one); give a reaction SMILES or explicit reactants and products instead')
    fragments = {}
    for ident, mol in read_fragments(path):
        fragments.setdefault(ident, mol)
    out = []
    for element in elements:
        group = {}
        for role, attributes in (('reactants', ['ReactionStepReactants']), ('products', ['ReactionStepProducts']),
                                 ('agents', ['ReactionStepObjectsAboveArrow', 'ReactionStepObjectsBelowArrow'])):
            ids = [i for attribute in attributes for i in element.get(attribute, '').split()]
            group[role] = [{'mol': fragments[i], 'label': f'fragment {i}', 'fragment_id': i}
                           for i in ids if i in fragments]
        if not group['reactants'] or not group['products']:
            raise ValueError(f"Reaction step {element.get('id')} has no drawn reactants or products")
        out.append({'step_id': element.get('id'), **group})
    if steps is not None:
        out = [entry for entry in out if entry['step_id'] in steps]
        if not out:
            raise ValueError('None of the requested steps exist in the file')
    return out


def _nullspace_coefficients(species, rows):
    """Smallest positive integer coefficients balancing every row, or None."""
    columns = len(species)
    matrix = [[Fraction(sign * s['counts'].get(row, 0) if row != 'charge' else sign * s['charge'])
               for s, sign in zip(species, signs(species))] for row in rows]
    # Gauss-Jordan elimination over the rationals.
    pivots, r = [], 0
    for c in range(columns):
        pivot = next((i for i in range(r, len(matrix)) if matrix[i][c] != 0), None)
        if pivot is None:
            continue
        matrix[r], matrix[pivot] = matrix[pivot], matrix[r]
        lead = matrix[r][c]
        matrix[r] = [x / lead for x in matrix[r]]
        for i in range(len(matrix)):
            if i != r and matrix[i][c] != 0:
                factor = matrix[i][c]
                matrix[i] = [a - factor * b for a, b in zip(matrix[i], matrix[r])]
        pivots.append(c)
        r += 1
    free = [c for c in range(columns) if c not in pivots]
    if len(free) != 1:
        return None
    solution = [Fraction(0)] * columns
    solution[free[0]] = Fraction(1)
    for row, c in enumerate(pivots):
        solution[c] = -matrix[row][free[0]]
    if any(x <= 0 for x in solution):
        return None
    denominator = 1
    for x in solution:
        denominator = denominator * x.denominator // gcd(denominator, x.denominator)
    ints = [int(x * denominator) for x in solution]
    divisor = 0
    for x in ints:
        divisor = gcd(divisor, x)
    ints = [x // divisor for x in ints]
    return None if max(ints) > 99 else ints


def signs(species):
    return [1 if s['role'] == 'reactant' else -1 for s in species]


def _total(side):
    total = Counter()
    for s in side:
        for element, n in s['counts'].items():
            total[element] += n * s['coefficient']
    return total


def _difference_formula(counts):
    if not counts:
        return None
    formula = _hill(Counter(counts))
    return {'formula': formula, 'common_name': BYPRODUCTS.get(formula)} if formula in BYPRODUCTS \
        else {'formula': formula, 'common_name': None}


def _public(species):
    return {key: (round(value, 3) if key == 'mw' else value) for key, value in species.items()
            if key not in ('counts', 'record')}


def _stoichiometry(reactants, agents, products, options):
    scale = options['scale_mmol']
    if not isinstance(scale, (int, float)) or isinstance(scale, bool) or scale <= 0:
        raise ValueError('scale_mmol must be a positive number')
    limiting = options.get('limiting', 0)
    if not isinstance(limiting, int) or not 0 <= limiting < len(reactants):
        raise ValueError(f'limiting must be a reactant index between 0 and {len(reactants) - 1}')
    base = reactants[limiting]['coefficient']
    rows = []
    for role, group in (('reactant', reactants), ('agent', agents)):
        for index, s in enumerate(group):
            record = s['record']
            if 'equiv' in record:
                equiv = float(record['equiv'])
            elif role == 'reactant':
                equiv = 1.0 if group is reactants and index == limiting else s['coefficient'] / base
            else:
                continue
            mmol = scale * equiv
            mass = mmol * s['mw']
            row = {'label': s['label'], 'role': role, 'formula': s['formula'], 'mw': round(s['mw'], 3),
                   'equiv': round(equiv, 4) if equiv != int(equiv) else int(equiv),
                   'mmol': round(mmol, 4), 'mass_mg': round(mass, 3)}
            if record.get('density_g_ml'):
                row['volume_ml'] = round(mass / 1000.0 / float(record['density_g_ml']), 4)
            elif record.get('concentration_m'):
                row['volume_ml'] = round(mmol / float(record['concentration_m']), 4)
            rows.append(row)
    for s in products:
        mmol = scale * s['coefficient'] / base
        theoretical = mmol * s['mw']
        row = {'label': s['label'], 'role': 'product', 'formula': s['formula'], 'mw': round(s['mw'], 3),
               'mmol': round(mmol, 4), 'theoretical_mg': round(theoretical, 3)}
        isolated = s['record'].get('isolated_mg')
        if isolated is not None:
            row['isolated_mg'] = isolated
            row['yield_percent'] = round(float(isolated) / theoretical * 100.0, 1)
        rows.append(row)
    return rows


def _balance_one(reactants, agents, products, options, step_id=None):
    species = reactants + products
    left, right = _total(reactants), _total(products)
    elements = sorted(set(left) | set(right))
    charge_left = sum(s['charge'] * s['coefficient'] for s in reactants)
    charge_right = sum(s['charge'] * s['coefficient'] for s in products)
    short_right = {e: left[e] - right[e] for e in elements if left[e] > right[e]}
    short_left = {e: right[e] - left[e] for e in elements if right[e] > left[e]}
    balanced = not short_right and not short_left and charge_left == charge_right
    mass_left = sum(s['mw'] * s['coefficient'] for s in reactants)
    mass_right = sum(s['mw'] * s['coefficient'] for s in products)
    main = options.get('main_product', 0)
    if not isinstance(main, int) or not 0 <= main < len(products):
        raise ValueError(f'main_product must be a product index between 0 and {len(products) - 1}')
    reaction = {
        'balanced': balanced,
        'reactants': [_public(s) for s in reactants], 'products': [_public(s) for s in products],
        'agents': [_public(s) for s in agents],
        'composition': {'reactants': dict(sorted(left.items())), 'products': dict(sorted(right.items()))},
        'charge': {'reactants': charge_left, 'products': charge_right},
        'mass_balance': {'reactants': round(mass_left, 3), 'products': round(mass_right, 3),
                         'difference': round(mass_left - mass_right, 3) + 0.0},
        'atom_economy_percent': round(products[main]['mw'] * products[main]['coefficient'] / mass_left * 100.0, 2),
        'atom_economy_product': products[main]['label'],
    }
    if step_id is not None:
        reaction = {'step_id': step_id, **reaction}
    if short_right:
        reaction['missing_from_products'] = _difference_formula(short_right)
    if short_left:
        reaction['missing_from_reactants'] = _difference_formula(short_left)
    if charge_left != charge_right:
        reaction['charge_difference'] = charge_left - charge_right
    if not balanced:
        suggestion = _nullspace_coefficients(species, elements + ['charge'])
        if suggestion:
            reaction['suggested_coefficients'] = {'reactants': suggestion[:len(reactants)],
                                                  'products': suggestion[len(reactants):]}
    if 'scale_mmol' in options:
        reaction['stoichiometry'] = _stoichiometry(reactants, agents, products, options)
    return reaction


def _reaction_sources(reaction):
    """Reaction input -> [{'step_id', 'reactants', 'agents', 'products'}] of structure records."""
    if isinstance(reaction, str):
        return [{'step_id': None, **_from_smiles(reaction)}]
    if isinstance(reaction, dict) and 'cdxml' in reaction:
        steps = reaction.get('steps')
        return _from_cdxml(reaction['cdxml'], set(map(str, steps)) if steps else None)
    if isinstance(reaction, dict) and reaction.get('reactants') and reaction.get('products'):
        return [{'step_id': None, 'reactants': reaction['reactants'], 'agents': reaction.get('agents') or [],
                 'products': reaction['products']}]
    raise ValueError('reaction must be a reaction SMILES, {"reactants": [...], "products": [...]} or {"cdxml": path}')


def check_reaction_balance(reaction: str | dict, options: dict | None = None,
                           output_path: str | None = None) -> dict:
    """Check that a reaction conserves atoms and charge, and optionally tabulate its stoichiometry.

    reaction is a reaction SMILES string "reactants>agents>products" (structures separated by
    '.'), a dict {"reactants": [...], "agents": [...], "products": [...]} of structure records
    (smiles, molblock or file; optional label, coefficient, equiv, density_g_ml, concentration_m,
    isolated_mg), or {"cdxml": path, "steps": [step ids]} to read the <step> elements of a drawn
    scheme. Agents are listed but never counted. Elements are counted with implicit hydrogens;
    isotope-labelled atoms are balanced as separate species, and the charge must balance too.
    For an unbalanced reaction the result names the missing formula (for example H2O),
    and, when exactly one set of whole-number coefficients balances it, suggests them.
    Also reports mass balance and atom economy (options main_product, default the first product).
    options scale_mmol (amount of the limiting reactant, option limiting = its index, default 0)
    adds a stoichiometry table with equivalents, mmol, mass, volume and, for products with
    isolated_mg, the percent yield. A failed balance is a finding about the species as drawn:
    check the structures against their source before trusting the reaction. Generic atoms
    (R groups) are rejected. output_path ends in .json and is never overwritten.
    """
    options = dict(options or {})
    unknown = set(options) - {'scale_mmol', 'limiting', 'main_product'}
    if unknown:
        raise ValueError(f'Unknown options: {sorted(unknown)}')
    sources = _reaction_sources(reaction)
    reactions = []
    for source in sources:
        sides = {}
        for role in ('reactants', 'agents', 'products'):
            sides[role] = _side(source[role], role[:-1])
        reactions.append(_balance_one(sides['reactants'], sides['agents'], sides['products'], options,
                                      step_id=source['step_id']))
    result = {'ok': True, 'operation': 'check_reaction_balance', 'balanced': all(r['balanced'] for r in reactions),
              'reactions': reactions, 'warnings': []}
    if not result['balanced']:
        result['warnings'].append('Unbalanced as drawn: confirm every structure against its source before '
                                  'treating a missing by-product as chemistry.')
    if output_path:
        target = _publish(output_path, {'.json': lambda: json.dumps(result, ensure_ascii=False, indent=2)})
        result = artifact_safety.with_artifacts({**result, 'output_path': str(target)}, [target])
    return result


# --- export_structures -------------------------------------------------------

EXPORT_COLUMNS = ['label', 'fragment_id', 'smiles', 'inchi', 'inchikey', 'formula', 'mw', 'exact_mass']


def _sdf(rows, mols):
    buffer = io.StringIO()
    for row, mol in zip(rows, mols):
        clean = Chem.Mol(mol)
        clean.SetProp('_Name', row['label'] or '')
        for key in ('smiles', 'inchikey', 'formula'):
            if row.get(key):
                clean.SetProp({'smiles': 'SMILES', 'inchikey': 'InChIKey', 'formula': 'Formula'}[key], row[key])
        if row.get('inchi'):
            clean.SetProp('InChI', row['inchi'])
        buffer.write(Chem.MolToMolBlock(clean) + '\n'.join(f'> <{n}>\n{clean.GetProp(n)}\n' for n in
                                                          ('SMILES', 'InChIKey', 'Formula', 'InChI') if clean.HasProp(n)) + '\n$$$$\n')
    return buffer.getvalue()


def export_structures(source: str | list, options: dict | None = None,
                      output_path: str | None = None) -> dict:
    """Export every structure in a file or list as SMILES, InChI, InChIKey, formula and mass.

    source is a path to a CDXML, MOL, SDF or SMILES (.smi) file, or a list of structure records
    (smiles, molblock or file; optional label). A CDXML file contributes each top-level fragment
    in document order with its CDXML fragment id; SDF titles and SMILES-file names become
    labels. Binary CDX needs convert_cdx_cdxml first, and Office files need
    extract_cdxml_from_office. Structures with generic atoms (R groups) are listed with their
    SMILES but without InChI, and the result says so. option include_molblock adds a MOL block per
    structure. output_path ends in .csv, .json, .smi, .sdf or .md and is never overwritten.
    At most 2000 structures. Identity comes from the structure as stored; nothing is recognised or edited.
    """
    options = options or {}
    unknown = set(options) - {'include_molblock'}
    if unknown:
        raise ValueError(f'Unknown options: {sorted(unknown)}')
    if isinstance(source, str):
        path = Path(source).expanduser().resolve()
        if not path.is_file():
            raise ValueError(f'Input file does not exist: {path}')
        records = [{'file': str(path), 'all_fragments': True}]
    else:
        records = source
    mols, rows, warnings = [], [], []
    for index, item in enumerate(_expand(records, limit=MAX_EXPORT), 1):
        mol = Chem.RemoveHs(item['mol'])
        inchi, inchikey = _inchi(mol)
        label = item['record'].get('label') or item['record'].get('name')
        row = {'index': index, 'label': label, 'fragment_id': item['source'].get('fragment_id'),
               'smiles': _smiles(mol), 'inchi': inchi,
               'inchikey': inchikey,
               'formula': rdMolDescriptors.CalcMolFormula(mol), 'mw': round(Descriptors.MolWt(mol), 3),
               'exact_mass': round(Descriptors.ExactMolWt(mol), 5)}
        if inchi is None:
            warnings.append(f'Structure {index}: no InChI could be generated (generic atoms or unsupported valence).')
        if options.get('include_molblock'):
            row['molblock'] = Chem.MolToMolBlock(mol)
        mols.append(mol)
        rows.append(row)
    result = {'ok': True, 'operation': 'export_structures', 'count': len(rows), 'structures': rows,
              'warnings': warnings}
    if output_path:
        target = _publish(output_path, {
            '.csv': lambda: _csv(rows, EXPORT_COLUMNS),
            '.json': lambda: json.dumps({'structures': rows}, ensure_ascii=False, indent=2),
            '.smi': lambda: ''.join(f"{r['smiles']} {r['label'] or r['index']}\n" for r in rows),
            '.sdf': lambda: _sdf(rows, mols),
            '.md': lambda: _markdown(rows, EXPORT_COLUMNS),
        })
        result = artifact_safety.with_artifacts({**result, 'output_path': str(target)}, [target])
    return result


# --- structure_to_name -------------------------------------------------------

def _component_keys(mol):
    keys = [_inchi(fragment)[1] for fragment in Chem.GetMolFrags(Chem.RemoveHs(mol), asMols=True)]
    return None if any(key is None for key in keys) else sorted(keys)


def _component_keys_of_all(fragments):
    keys = []
    for _, mol in fragments:
        part = _component_keys(mol)
        if part is None:
            return None
        keys.extend(part)
    return sorted(keys)


def _roundtrip(bridge, name, expected):
    """Parse the name back to a structure with ChemDraw and compare it with the input by InChIKey."""
    try:
        cdxml = bridge.name_to_cdxml(name)
        parsed = _component_keys_of_all(read_fragments(cdxml))
    except Exception as exc:
        return {'status': 'unparseable', 'note': f'ChemDraw could not turn the name back into a structure: {exc}'}
    if expected is None or parsed is None:
        return {'status': 'skipped', 'note': 'An InChI could not be generated for the comparison.'}
    result = {'inchikey_input': '.'.join(expected), 'inchikey_from_name': '.'.join(parsed)}
    if expected == parsed:
        return {'status': 'same', **result}
    if [k[:14] for k in expected] == [k[:14] for k in parsed]:
        return {'status': 'same_connectivity', **result,
                'note': 'Connectivity matches but the stereochemistry, charge or isotope layers differ.'}
    return {'status': 'different', **result,
            'note': 'The name describes another structure than the one supplied.'}


NAME_COLUMNS = ['label', 'name', 'formula', 'roundtrip_status', 'smiles']


def structure_to_name(molecules: list[dict], options: dict | None = None,
                      output_path: str | None = None) -> dict:
    """Name grounded structures with ChemDraw's own structure-to-name engine and check each name.

    Records are SMILES/CXSMILES, molblock or file records (CDXML/MOL/SDF), with an optional
    label; a CDXML or SDF record with all_fragments=true names every structure in the file.
    The name is the one ChemDraw's "Convert Structure to Name" produces (ChemScript on Windows,
    ChemDraw for macOS on a Mac); it is not generated or guessed by this toolkit, and no
    structure leaves the machine. With the default option verify=true each name is parsed
    back to a structure by ChemDraw and compared with the input by InChIKey, component by
    component: roundtrip.status is same, same_connectivity (stereo, charge or isotope layers
    differ), different, unparseable or skipped. Report a name as confirmed only when the status
    is same. Enhanced (and/or) stereo groups cannot be expressed in a name and are warned about.
    One structure that ChemDraw cannot name is reported with its error and does not stop the others.
    Needs ChemScript (Windows) or ChemDraw for macOS, like compare_molecules; there is no
    offline fallback. output_path ends in .csv, .json or .md and is never overwritten.
    At most 256 structures.
    """
    options = options or {}
    unknown = set(options) - {'verify'}
    if unknown:
        raise ValueError(f'Unknown options: {sorted(unknown)}')
    verify = bool(options.get('verify', True))
    items = _expand(molecules, limit=MAX_STRUCTURES)
    for item in items:
        _check_grounded(item['mol'], item['label'])
    warnings, rows = [], []
    bridge = _bridge_factory()
    try:
        for item in items:
            mol = Chem.RemoveHs(item['mol'])
            row = {'label': item['label'], 'source': item['source'], 'smiles': _smiles(mol),
                   'formula': rdMolDescriptors.CalcMolFormula(mol), 'name': None}
            if mol.GetStereoGroups():
                warnings.append(f"{row['label']}: carries an enhanced stereo group (and/or); the name cannot "
                                'express it and describes the drawn absolute configuration only.')
            plain = Chem.Mol(mol)
            plain.RemoveAllConformers()
            try:
                named = bridge.get_info(Chem.MolToSmiles(plain)).get('name')
                if not named:
                    raise RuntimeError('ChemDraw returned no name')
                row['name'] = named
            except Exception as exc:
                row['error'] = str(exc)
                row['roundtrip'] = {'status': 'skipped', 'note': 'No name to check.'}
                warnings.append(f"{row['label']}: ChemDraw could not name this structure ({exc}).")
                rows.append(row)
                continue
            if verify:
                row['roundtrip'] = _roundtrip(bridge, named, _component_keys(mol))
                status = row['roundtrip']['status']
                if status == 'different':
                    warnings.append(f"{row['label']}: the name does not parse back to the same structure; do not use it.")
                elif status == 'unparseable':
                    warnings.append(f"{row['label']}: the name could not be parsed back, so it is unverified.")
                elif status == 'same_connectivity':
                    warnings.append(f"{row['label']}: the name matches in connectivity only; check stereochemistry.")
            else:
                row['roundtrip'] = {'status': 'skipped', 'note': 'verify=false'}
            rows.append(row)
    finally:
        bridge.close()
    flat = [{**row, 'roundtrip_status': row['roundtrip']['status']} for row in rows]
    result = {'ok': True, 'operation': 'structure_to_name', 'count': len(rows), 'results': rows,
              'warnings': warnings}
    if output_path:
        target = _publish(output_path, {
            '.json': lambda: json.dumps({'results': rows}, ensure_ascii=False, indent=2),
            '.csv': lambda: _csv(flat, NAME_COLUMNS),
            '.md': lambda: _markdown(flat, NAME_COLUMNS),
        })
        result = artifact_safety.with_artifacts({**result, 'output_path': str(target)}, [target])
    return result


# --- chemdraw_chemical_properties ---------------------------------------------

# ChemScript StructureData member, how it is read, and the row key it fills
CHEMDRAW_PROPERTIES = (
    ('Formula', 'call', 'formula'),
    ('Weight', 'get', 'average_mass'),
    ('ExactMass', 'get', 'exact_mass'),
    ('ElementalAnalysis', 'get', 'elemental_analysis'),
    ('PartitionCoefficient', 'get', 'log_p'),
    ('Refractivity', 'get', 'molar_refractivity'),
)
PROPERTY_COLUMNS = ['label', 'smiles', 'formula', 'average_mass', 'exact_mass', 'elemental_analysis',
                    'log_p', 'molar_refractivity']
# One structure takes a load step plus one step per property; ChemScript programs hold 256 steps.
PROPERTY_BATCH = 32
# ChemDraw for macOS gives no scripting access to its ClogP and molar refractivity estimates.
MAC_UNAVAILABLE_PROPERTIES = ('PartitionCoefficient', 'Refractivity')


def _readable_properties():
    if sys.platform == 'darwin':
        return tuple(prop for prop in CHEMDRAW_PROPERTIES if prop[0] not in MAC_UNAVAILABLE_PROPERTIES)
    return CHEMDRAW_PROPERTIES


def _property_program(smiles_list, properties):
    program = []
    for index, smiles in enumerate(smiles_list):
        alias = f'm{index}'
        program.append({'op': 'call_static', 'type': 'StructureData', 'member': 'LoadData',
                        'args': [smiles, 'chemical/x-smiles'], 'as': alias})
        for member, how, _ in properties:
            program.append({'op': how, 'target': alias, 'member': member})
    return program


def _read_properties(smiles_list, properties):
    """Run one ChemScript program for the structures; returns ([{member: value}], assembly)."""
    from . import chemscript_sdk

    response = chemscript_sdk.execute_chemscript_sdk(program=_property_program(smiles_list, properties))
    results = {item['step']: item['value'] for item in response['outputs']['results']}
    width = len(properties) + 1
    rows = [{member: results.get(index * width + 1 + offset)
             for offset, (member, _, _) in enumerate(properties)} for index in range(len(smiles_list))]
    return rows, response['outputs'].get('assembly')


def _valid_property(member, value):
    if member in ('Formula', 'ElementalAnalysis'):
        return isinstance(value, str) and bool(value)
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def chemdraw_chemical_properties(molecules: list[dict], output_path: str | None = None) -> dict:
    """Formula, masses, elemental analysis, logP and molar refractivity as ChemDraw computes them.

    Records are SMILES/CXSMILES, molblock or file records (CDXML/MOL/SDF), with an optional
    label; a CDXML or SDF record with all_fragments=true reports every structure in the file.
    Every value is read from ChemDraw's own chemical properties engine (ChemScript StructureData:
    Formula, Weight, ExactMass, ElementalAnalysis, PartitionCoefficient and Refractivity);
    log_p and molar_refractivity are ChemDraw's ClogP estimates, in its units. Nothing is computed
    by RDKit or any other substitute: a property ChemDraw cannot give is null with the reason in
    that row's errors, and without ChemScript (Windows) the call fails instead of falling back.
    On macOS ChemDraw itself gives the formula, masses and elemental analysis; it has no
    scripting access to ClogP or refractivity, so log_p and molar_refractivity are null there.
    Use molecule_report for the deterministic RDKit sheet. Generic atoms (R groups, *) are refused.
    output_path ends in .csv, .json or .md and is never overwritten. At most 256 structures.
    """
    from . import chemscript_sdk

    unavailable = chemscript_sdk.ChemScriptSdkUnavailable
    items = _expand(molecules, limit=MAX_STRUCTURES)
    for item in items:
        _check_grounded(item['mol'], item['label'])
    prepared = []
    for item in items:
        mol = Chem.RemoveHs(item['mol'])
        plain = Chem.Mol(mol)
        plain.RemoveAllConformers()
        prepared.append({'label': item['label'], 'source': item['source'], 'smiles': _smiles(mol),
                         'load': Chem.MolToSmiles(plain)})
    readable = _readable_properties()
    values = [{} for _ in prepared]
    errors = [dict() for _ in prepared]
    assembly = []

    def attempt(positions, properties):
        rows, seen = _read_properties([prepared[i]['load'] for i in positions], properties)
        if seen and not assembly:
            assembly.append(seen)
        return rows

    for start in range(0, len(prepared), PROPERTY_BATCH):
        positions = list(range(start, min(start + PROPERTY_BATCH, len(prepared))))
        try:
            for position, row in zip(positions, attempt(positions, readable)):
                values[position] = row
            continue
        except unavailable:
            raise
        except Exception:
            pass  # isolate the structure or property that ChemDraw rejects
        for position in positions:
            try:
                values[position] = attempt([position], readable)[0]
                continue
            except unavailable:
                raise
            except Exception:
                pass
            for prop in readable:
                try:
                    values[position].update(attempt([position], (prop,))[0])
                except unavailable:
                    raise
                except Exception as exc:
                    errors[position][prop[2]] = f'{prop[0]}: {str(exc)[:200]}'

    rows, warnings = [], []
    unreadable = [prop for prop in CHEMDRAW_PROPERTIES if prop not in readable]
    if prepared and unreadable:
        warnings.append(f"ChemDraw for macOS cannot give {', '.join(key for _, _, key in unreadable)}; "
                        "they are null in every row.")
    for position, entry in enumerate(prepared):
        row = {'label': entry['label'], 'source': entry['source'], 'smiles': entry['smiles']}
        for prop in CHEMDRAW_PROPERTIES:
            member, _, key = prop
            value = values[position].get(member)
            if prop in unreadable or key in errors[position]:
                value = None
            elif not _valid_property(member, value):
                reason = 'ChemDraw returned no value' if value is None else f'unexpected value {value!r}'
                errors[position][key] = f'{member}: {reason}'
                value = None
            row[key] = round(value, 6) if isinstance(value, float) else value
        if errors[position]:
            row['errors'] = errors[position]
            warnings.append(f"{entry['label']}: ChemDraw gave no value for {', '.join(errors[position])}.")
        rows.append(row)
    result = {'ok': True, 'operation': 'chemdraw_chemical_properties', 'count': len(rows), 'results': rows,
              'provenance': {'engine': 'ChemDraw ChemScript', 'assembly': assembly[0] if assembly else None,
                             'note': 'log_p and molar_refractivity are ChemDraw ClogP estimates; '
                                     'no value comes from RDKit or another substitute.'},
              'warnings': warnings}
    if output_path:
        target = _publish(output_path, {
            '.json': lambda: json.dumps({'provenance': result['provenance'], 'results': rows},
                                        ensure_ascii=False, indent=2),
            '.csv': lambda: _csv(rows, PROPERTY_COLUMNS),
            '.md': lambda: _markdown(rows, PROPERTY_COLUMNS),
        })
        result = artifact_safety.with_artifacts({**result, 'output_path': str(target)}, [target])
    return result


def _rounded(value, digits=4):
    return round(value, digits) + 0.0 if isinstance(value, float) else value


# --- stoichiometry_grid ------------------------------------------------------

def stoichiometry_grid(source: str, mode: str = 'analyze', output_path: str | None = None,
                       options: dict | None = None) -> dict:
    """ChemDraw's own stoichiometry grid (Structure > Analyze Stoichiometry), drawn or read back.

    mode "analyze" (Windows or macOS with desktop ChemDraw): source is a reaction SMILES
    "reactants>agents>products" (agents are drawn above the arrow) or a .cdxml/.cdx file holding
    a reaction. ChemDraw runs the command on a copy in a private window that it shows briefly
    (the command is disabled in a hidden one), and the result is saved to output_path (.cdxml,
    never overwritten; default "<name>-stoichiometry.cdxml" beside the file or
    "reaction-stoichiometry.cdxml"). The source is never changed, and a file that already holds a
    grid is refused. options.open (default false) then opens the result in the user's ChemDraw,
    where typing a mass, volume or equivalents into the grid makes ChemDraw recompute the rest.
    mode "read" (any platform, no ChemDraw): source is a saved .cdxml file; every grid in it is
    read back, for example after someone typed amounts into it and saved.
    Each grid lists one row per component with its role in the reaction step (reactant, agent or
    product) and one cell per visible column under ChemDraw's own caption (Formula, MW,
    Equivalents, Sample Mass, Reactant Moles, %Yield, ...): value is the stored number (masses in
    g, amounts in mol, percentages as fractions) and text what the grid shows, with units;
    cells someone typed are marked edited. Nothing is computed outside ChemDraw.
    """
    from ..chemdraw import stoichiometry_grid as grid
    options = dict(options or {})
    opened = bool(options.pop('open', False))
    if options:
        raise ValueError(f"Unknown options: {', '.join(sorted(options))}")
    if mode == 'read':
        if output_path:
            raise ValueError('output_path is only used by mode "analyze"')
        return grid.read_grid(source)
    if mode != 'analyze':
        raise ValueError('mode is "analyze" or "read"')
    result = grid.analyze(source, output_path, open_result=opened)
    return artifact_safety.with_artifacts(result, [Path(result['path'])])


def hrms_line(molecules: list[dict], options: dict | None = None, output_path: str | None = None) -> dict:
    """HRMS characterization lines: "HRMS (ESI) m/z calcd for C9H10O2Na [M+Na]+ 173.0573, found 173.0570".

    Each record is a grounded structure (SMILES, molblock or CDXML/MOL/SDF file, optional label).
    The ion formula and calculated m/z come from the monoisotopic mass of the structure plus the
    atoms the adduct adds or removes, with the electron mass included (options.electron_mass=false
    ignores it, as some calculators do). A record may carry adduct or adducts (default [M+H]+, or
    [M-H]- with options.mode "negative", or the molecular ion for ionization "EI"; a charged
    structure is its own ion) and found_mz: a number for its first adduct or {adduct: number}. A
    measured value adds ", found ..." and the error in ppm; more than 5 ppm is flagged. Options:
    adducts, mode (positive or negative), ionization (ESI, APCI, EI, ESI-TOF and similar labels),
    decimals (default 4), electron_mass. Supported adducts: [M+H]+, [M+Na]+, [M+K]+, [M+NH4]+,
    [M+Li]+, [M+2H]2+, [M+H-H2O]+, [M-H]-, [M-2H]2-, [M+Cl]-, [M+Br]-, [M+HCOO]-,
    [M+CH3COO]- and the EI molecular ion M+. . Output ends in .txt, .md, .csv or .json and is
    never overwritten. At most 256 structures. The values are calculated, never measured.
    """
    from ..characterization import default_adduct, hrms_entry
    options = dict(options or {})
    unknown = set(options) - {'adducts', 'mode', 'ionization', 'decimals', 'electron_mass'}
    if unknown:
        raise ValueError(f'Unknown option(s): {sorted(unknown)}')
    mode = options.get('mode', 'positive')
    if mode not in ('positive', 'negative'):
        raise ValueError('mode must be positive or negative')
    ionization = options.get('ionization', 'ESI')
    decimals = int(options.get('decimals', 4))
    electron_mass = bool(options.get('electron_mass', True))
    warnings, results = [], []
    for item in _expand(molecules, limit=MAX_STRUCTURES):
        record, mol, label = item['record'], item['mol'], item['label']
        _check_grounded(mol, label)
        adducts = (record.get('adducts') or ([record['adduct']] if record.get('adduct') else None)
                   or options.get('adducts') or [default_adduct(Chem.RemoveHs(mol), mode, ionization)])
        found = record.get('found_mz')
        entries = []
        for index, adduct in enumerate(adducts):
            value = found.get(adduct) if isinstance(found, dict) else (found if index == 0 else None)
            entry = hrms_entry(mol, adduct, ionization=ionization, decimals=decimals, found=value,
                               electron_mass=electron_mass)
            if entry['error_ppm'] is not None and abs(entry['error_ppm']) > 5:
                warnings.append(f"{label}: {entry['adduct']} found {entry['found_mz']} is {entry['error_ppm']:+.1f} ppm "
                                'from the calculated value; check the adduct, the formula and the instrument calibration.')
            entries.append(entry)
        if len(Chem.GetMolFrags(mol)) > 1:
            warnings.append(f'{label}: more than one component; the formula describes the whole record.')
        results.append({'label': label, 'source': item['source'], 'formula': entries[0]['molecular_formula'],
                        'entries': entries})
    rows = [{'label': r['label'], 'formula': r['formula'], **{k: e[k] for k in
             ('adduct', 'ion_formula', 'calcd_mz', 'found_mz', 'error_ppm', 'line')}}
            for r in results for e in r['entries']]
    text = ''.join(f"{row['label']}: {row['line']}" + chr(10) for row in rows)
    columns = ['label', 'formula', 'adduct', 'ion_formula', 'calcd_mz', 'found_mz', 'error_ppm', 'line']
    result = {'ok': True, 'operation': 'hrms_line', 'count': len(results), 'results': results,
              'text': text, 'warnings': warnings}
    if output_path:
        target = _publish(output_path, {
            '.txt': lambda: text,
            '.md': lambda: _markdown(rows, columns),
            '.csv': lambda: _csv(rows, columns),
            '.json': lambda: json.dumps({'results': results}, ensure_ascii=False, indent=2),
        })
        result = artifact_safety.with_artifacts({**result, 'output_path': str(target)}, [target])
    return result


MAX_BATCH = 100


def _batch_items(reactions):
    """Batch input -> [(label or None, reaction spec, per-reaction options)]."""
    if isinstance(reactions, (str, dict)):
        reactions = [reactions]
    if not reactions:
        raise ValueError('Provide at least one reaction')
    if len(reactions) > MAX_BATCH:
        raise ValueError(f'At most {MAX_BATCH} reactions per call')
    items = []
    for item in reactions:
        if isinstance(item, dict) and 'reaction' in item:
            items.append((item.get('label'), item['reaction'], dict(item.get('options') or {})))
        elif isinstance(item, dict):
            spec = {k: v for k, v in item.items() if k not in ('label', 'options')}
            items.append((item.get('label'), spec, dict(item.get('options') or {})))
        else:
            items.append((None, item, {}))
    return items


def _labelled_sources(label, spec, name):
    """[(entry label, source)] for one batch item: a drawing that stores several reaction steps gives one per step."""
    sources = _reaction_sources(spec)
    stem = Path(spec['cdxml']).stem if isinstance(spec, dict) and spec.get('cdxml') else None
    if len(sources) > 1:
        return [(f'{label or stem}, step {step}', source) for step, source in enumerate(sources, 1)]
    return [(label or stem or name, sources[0])]


def _calculator_rows(result):
    keys = ('id', 'role', 'name', 'formula', 'mw', 'equiv', 'mmol', 'mass_mg', 'volume_ml', 'theory_mmol',
            'theory_mg', 'actual_mg', 'yield_percent', 'hrms')
    return [{**{key: _rounded(row.get(key)) for key in keys if row.get(key) is not None},
             'fixed': {'basis': row['basis'], 'value': _rounded(row['value']), 'assumed': bool(row['assumed'])}
             if row['basis'] else None} for row in result['rows']]


def _materials_entry(label, source, options, hrms, safety=False):
    from ..characterization import default_adduct, hrms_entry
    from ..reaction_calculator import build_state, compute, hazards, materials
    options = dict(options)
    safety = bool(options.pop('reagent_safety', safety))
    sides ={role: _side(source[role], role[:-1]) for role in ('reactants', 'agents', 'products')}
    state = build_state(sides, options)
    result = compute(state)
    rows = result['rows']
    if not hrms.get('enabled', True):
        for row in rows:
            row.pop('hrms', None)
    first = next((r for r in rows if r['role'] == 'product'), None)
    warnings = list(result['warnings'])
    product = None
    if first is not None:
        product = {key: _rounded(first.get(key)) for key in ('name', 'formula', 'mw', 'theory_mmol', 'theory_mg',
                                                              'actual_mg', 'yield_percent') if first.get(key) is not None}
        if hrms.get('enabled', True):
            mol = Chem.MolFromSmiles(first['smiles'])
            try:
                product['hrms'] = hrms_entry(mol, hrms.get('adduct') or default_adduct(mol, 'positive', hrms['ionization']),
                                             ionization=hrms['ionization'])['line']
            except ValueError as exc:
                warnings.append(f'HRMS line not written: {exc}')
    assumed = [row['name'] for row in state['rows'] if row['assumed']]
    if assumed:
        warnings.append(f"amounts assumed (not given) for {', '.join(assumed)}")
    for row in rows:
        if first is not None and row['id'] == first['id'] and product and product.get('hrms'):
            row['hrms'] = product['hrms']
    entry = {'label': label, 'ok': True, 'title': state['title'], 'limiting': result['limiting'],
             'rows': _calculator_rows(result), 'all_rows': rows,
             'totals': {k: _rounded(v) for k, v in result['totals'].items() if v is not None},
             'product': product, 'assumed': assumed, 'warnings': warnings,
             'procedure': materials.procedure(rows, result['limiting'], result['totals'])}
    if safety:
        entry['safety'] = hazards.for_rows(rows)
    return entry


def si_materials_tables(reactions: list, options: dict | None = None, output_path: str | None = None) -> dict:
    """Materials tables for a batch of reactions, ready for a Supporting Information file.

    reactions is a list; each entry is a reaction SMILES "reactants>agents>products", a record
    {"reactants": [...], "agents": [...], "products": [...]}, {"cdxml": path} (one reaction per
    reaction step in the drawing) or {"label": "3a", "reaction": <any of these>, "options": {...}}.
    A record may fix its own amount with one of equiv, mmol, mass_mg or volume_ml (solvents:
    volume_ml) and may carry name, role (agents: solvent, reagent or catalyst), density_g_ml,
    concentration_m (a stock solution), purity (percent) and, for a product, isolated_mg or
    yield_percent; amounts nobody fixed get defaults (reactants by their coefficients, reagents
    1 equiv, metal catalysts 0.05 equiv, a 0.2 M solvent). Per-reaction options override the
    call's options. Options: scale_mmol (limiting reactant, default 1),
    limiting, molarity (default 0.2 of the limiting reagent in the first solvent), hrms (default
    true: add the calculated HRMS line of the first product), adduct (default [M+H]+) and
    ionization (default ESI). map_atoms (default false) adds each reaction's bond changes from
    atom mapping: all reactions go to the mapper in one call, so a learned mapper loads once;
    map_method (default auto, see map_reaction_atoms) picks the method. A reaction that cannot be
    mapped only loses that line, with a warning. reagent_safety (default false) adds, per
    reaction, "safety": the GHS pictograms, H-statements, boiling and flash point of each reactant,
    reagent and solvent from a built-in table of common reagents (a reminder, not a substitute for
    the supplier SDS); a species that is not in the table is reported as not listed, never guessed.
    Per reaction the result holds the amounts table, concentration, atom economy and reaction mass
    efficiency, the first product's formula, isolated mass and yield, its HRMS line and a procedure
    sentence; "assumed" lists the amounts nobody gave (shown in warnings). A reaction that cannot be
    read is reported with its error and the others continue. output_path ends in .md, .csv, .html
    or .json and is never overwritten. At most 100 reactions. Amounts and HRMS values are
    calculated; nothing here is a measurement.
    """
    from ..reaction_calculator import materials
    base = dict(options or {})
    hrms = {'enabled': bool(base.pop('hrms', True)), 'adduct': base.pop('adduct', None),
            'ionization': base.pop('ionization', 'ESI')}
    mapping = bool(base.pop('map_atoms', False))
    map_method = str(base.pop('map_method', 'auto'))
    safety = bool(base.pop('reagent_safety', False))
    entries, warnings = [], []
    for number, (label, spec, own) in enumerate(_batch_items(reactions), 1):
        name = label or f'Reaction {number}'
        try:
            for entry_label, source in _labelled_sources(label, spec, name):
                if len(entries) >= MAX_BATCH:
                    raise ValueError(f'At most {MAX_BATCH} reactions per call')
                entry = _materials_entry(entry_label, source, {**base, **own}, hrms, safety)
                entry['_source'] = source
                warnings += [f'{entry_label}: {w}' for w in entry['warnings']]
                entries.append(entry)
        except ValueError as exc:
            entries.append({'label': name, 'ok': False, 'error': str(exc)})
            warnings.append(f'{name}: {exc}')
    if mapping:
        _add_bond_changes(entries, warnings, map_method)
    markdown = materials.markdown(entries)
    public = [{k: v for k, v in entry.items() if k not in ('all_rows', '_source')} for entry in entries]
    result = {'ok': True, 'operation': 'si_materials_tables', 'count': len(entries), 'reactions': public,
              'markdown': markdown, 'warnings': warnings}
    if output_path:
        target = _publish(output_path, {
            '.md': lambda: markdown,
            '.csv': lambda: materials.csv_text(entries),
            '.html': lambda: materials.html_text(entries),
            '.json': lambda: json.dumps({'reactions': public}, ensure_ascii=False, indent=2),
        })
        result = artifact_safety.with_artifacts({**result, 'output_path': str(target)}, [target])
    return result


ROUTE_META = ('label', 'options', 'into', 'used_mg', 'reaction')
ROUTE_NUMBERS = ('yield_percent', 'input_mg', 'product_mg')


def _route_step(item, number):
    """One route step -> (fields for route_metrics, calculator rows or None)."""
    from ..reaction_calculator import annotate
    if isinstance(item, str):
        item = {'reaction': item}
    if not isinstance(item, dict):
        raise ValueError(f'step {number}: a step is a reaction or a dict of numbers')
    label = str(item.get('label') or number)
    drawn = 'reaction' in item or any(k in item for k in ('cdxml', 'reactants', 'products'))
    fields = {'label': label, 'into': item.get('into'), 'used_mg': item.get('used_mg')}
    if not drawn:
        fields.update({key: item.get(key) for key in ROUTE_NUMBERS})
        return fields, None
    spec = item['reaction'] if 'reaction' in item else {k: v for k, v in item.items() if k not in ROUTE_META}
    try:
        sources = _reaction_sources(spec)
        if len(sources) != 1:
            raise ValueError('the drawing stores several reaction steps: choose one with {"cdxml": path, "steps": [step id]}')
        entry = _materials_entry(label, sources[0], dict(item.get('options') or {}), {'enabled': False})
    except ValueError as exc:
        raise ValueError(f'step {label}: {exc}') from exc
    rows = entry['all_rows']
    main = next((r for r in rows if r['role'] == 'product'), None)
    totals = entry['totals']
    fields.update(
        yield_percent=main.get('yield_percent') if main else None,
        product_mg=main.get('actual_mg') if main else None,
        input_mg=totals.get('input_mg', 0.0) + totals.get('solvent_mg', 0.0),
        solvents_without_mass=totals.get('solvents_without_mass', 0))
    for key in ROUTE_NUMBERS:
        if item.get(key) is not None:
            fields[key] = item[key]
    keyed = {'product': annotate.key(main['smiles']) if main and main.get('smiles') else None,
             'fed': [(annotate.key(r['smiles']), r['mmol'] * r['mw']) for r in rows
                     if r['role'] in ('reactant', 'reagent', 'catalyst') and r.get('smiles') and r.get('mmol')]}
    return fields, keyed


def _round_all(value):
    if isinstance(value, float):
        return _rounded(value)
    if isinstance(value, dict):
        return {k: _round_all(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_round_all(v) for v in value]
    return value


def _route_markdown(result):
    head = ['Step', 'Into', 'Yield (%)', 'Input (mg)', 'Product (mg)', 'Used by next (mg)', 'Scale', 'Step PMI']
    cell = lambda v: '' if v is None else (f'{v:.4g}' if isinstance(v, float) else str(v))
    lines = ['| ' + ' | '.join(head) + ' |', '| --- | --- | ' + ' | '.join('---:' for _ in head[2:]) + ' |']
    for s in result['steps']:
        lines.append('| ' + ' | '.join(cell(s[k]) for k in ('label', 'into', 'yield_percent', 'input_mg', 'product_mg',
                                                           'used_mg', 'scale', 'step_pmi')) + ' |')
    out = ['\n'.join(lines), '']
    if result['overall_yield_percent'] is not None:
        out.append(f"Overall yield {cell(result['overall_yield_percent'])}% over the longest linear sequence "
                   f"({' > '.join(result['longest_sequence'])}).")
    if result['cumulative_pmi'] is not None:
        bound = ' (lower bound: a solvent has no known mass)' if result['lower_bound'] else ''
        out.append(f"Cumulative PMI {cell(result['cumulative_pmi'])}, E-factor {cell(result['cumulative_e_factor'])}{bound}.")
    out += [f'Note: {w}.' for w in result['warnings']]
    return '\n'.join(out) + '\n'


def route_summary(steps: list, options: dict | None = None, output_path: str | None = None) -> dict:
    """Overall yield and cumulative process mass intensity (PMI) of a synthetic route.

    steps are listed in the order they are run; the last one makes the final product. A step is a
    reaction as in si_materials_tables (a reaction SMILES, {"reactants": ..., "products": ...}
    records, {"cdxml": path} or {"label": "2", "reaction": ..., "options": {...}}, whose amounts,
    isolated mass or yield are computed as in si_materials_tables) or just numbers: {"label": "2",
    "yield_percent": 85, "input_mg": 1500, "product_mg": 340, "used_mg": 300}. input_mg is
    everything put into the step (reagents, catalysts, solvents), product_mg the isolated mass of
    its product; a reaction takes both from that computation (a solvent with no density has no mass
    and makes the PMI a lower bound), and either can be given on the step to override. A step
    feeds the next one; "into": "<later step label>" makes the route convergent. used_mg is the
    mass of a step's product that the step it feeds consumes: it is read from the structures when
    both steps are reactions and the product is drawn as a reactant of the next, and is otherwise
    required once the masses are given. Overall yield is the product of the step yields along the
    longest linear sequence. Cumulative PMI is the mass put into all steps over the mass of the
    final product, each step scaled so that it makes exactly what the next one uses (scale);
    E-factor is PMI - 1. Work-up, extraction and purification solvents count only if you include
    them in input_mg; a missing number is reported in warnings, never assumed. output_path ends in
    .md, .csv or .json and is never overwritten. At most 100 steps.
    """
    from .. import route_metrics
    options = dict(options or {})
    if options:
        raise ValueError(f'Unknown options: {sorted(options)}')
    if isinstance(steps, (str, dict)):
        steps = [steps]
    if not steps:
        raise ValueError('Provide at least one step')
    if len(steps) > MAX_BATCH:
        raise ValueError(f'At most {MAX_BATCH} steps per call')
    fields, keyed = zip(*(_route_step(item, number) for number, item in enumerate(steps, 1)))
    fields = [dict(f) for f in fields]
    labels = [f['label'] for f in fields]
    for index, (step, info) in enumerate(zip(fields, keyed)):
        if step.get('used_mg') is not None or info is None or index == len(fields) - 1:
            continue
        target = step.get('into')
        target_index = labels.index(str(target)) if target is not None and str(target) in labels else index + 1
        other = keyed[target_index] if target_index > index else None
        if other is not None and info['product']:
            used = [mass for key, mass in other['fed'] if key == info['product']]
            if len(used) == 1:
                step['used_mg'] = used[0]
    summary = route_metrics.summarize(fields)
    markdown = _route_markdown(summary)
    result = {'ok': True, 'operation': 'route_summary', **_round_all(summary), 'markdown': markdown}
    if output_path:
        columns = ['step', 'into', 'yield_percent', 'input_mg', 'product_mg', 'used_mg', 'scale', 'step_pmi',
                   'on_longest_sequence']
        rows = [{'step': s['label'], **{k: s[k] for k in columns[1:]}} for s in summary['steps']]
        target = _publish(output_path, {
            '.md': lambda: markdown,
            '.csv': lambda: _csv(rows, columns),
            '.json': lambda: json.dumps({k: v for k, v in result.items() if k != 'markdown'}, ensure_ascii=False, indent=2),
        })
        result = artifact_safety.with_artifacts({**result, 'output_path': str(target)}, [target])
    return result


def _mapping_species(records):
    """([(label, mol)], {label: drawing fragment id}) of the structures of one side."""
    out, drawn = [], {}
    for item in (_expand(records, limit=MAX_STRUCTURES) if records else []):
        _check_grounded(item['mol'], item['label'])
        record, mol = item['record'], Chem.Mol(item['mol'])
        for atom in mol.GetAtoms():
            atom.SetAtomMapNum(0)
        label = (record.get('label') or record.get('name') or record.get('smiles')
                 or rdMolDescriptors.CalcMolFormula(mol))
        out.append((label, mol))
        if item['source'].get('fragment_id'):
            drawn[label] = item['source']['fragment_id']
    return out, drawn


def _mapping_picture(mapped):
    from rdkit.Chem import rdChemReactions
    from rdkit.Chem.Draw import rdMolDraw2D
    drawer = rdMolDraw2D.MolDraw2DSVG(960, 320)
    drawer.DrawReaction(rdChemReactions.ReactionFromSmarts(mapped, useSmiles=True))
    drawer.FinishDrawing()
    return drawer.GetDrawingText()


def _mapping_job(source, include_agents):
    """One reaction source -> the species lists atom mapping works on."""
    found = [_mapping_species(source[role]) for role in ('reactants', 'agents', 'products')]
    (reactants, agents, products), drawn = [f[0] for f in found], {k: v for f in found for k, v in f[1].items()}
    include = include_agents and bool(agents)
    return {'reactants': reactants, 'agents': agents, 'products': products, 'include': include,
            'left': reactants + (agents if include else []), 'drawn': drawn}


def _template_extras(result, job, options):
    """The reaction class and reaction-centre template a mapping was asked for, added to ``result``."""
    from .. import reaction_templates
    if options['classify']:
        result['reaction_class'] = reaction_templates.classify(job['reactants'], job['agents'], job['products'])
    if options['template']:
        template = reaction_templates.reaction_center(result['mapped_reaction'])
        template['reproduces'] = template['smarts'] and reaction_templates.reproduces(
            template['smarts'], [mol for _, mol in job['left']], [mol for _, mol in job['products']])
        if not template['smarts']:
            template['note'] = (f"No bond change was found between the mapped atoms (the mapping is {result['status']}, "
                                'and the atoms that differ are left unmapped), so there is no template to extract; '
                                'try resolve_ambiguity or a learned mapper.')
        elif result['status'] != 'complete':
            template['note'] = (f"The mapping is {result['status']}: atoms left unmapped are treated as leaving "
                                'or new atoms, so check the template against the drawn reaction before reusing it.')
        result['template'] = template


def _numbered_scheme(path, job, outcome):
    """(CDXML text of the drawing at ``path`` with the map numbers of ``outcome`` beside the atoms, warnings)."""
    from .. import reaction_templates
    numbers = {}
    for entry in outcome['map']:
        for side in ('reactant', 'product'):
            fragment = job['drawn'].get(entry[side]['species'])
            if fragment is not None:
                numbers.setdefault(fragment, {})[entry[side]['atom_index']] = entry['map']
    return reaction_templates.write_map_numbers(Path(path).read_text(encoding='utf-8'), numbers)


def _mapped_reaction(job, outcome):
    """The mapped reaction SMILES of a finished mapping; takes the numbered molecules out of ``outcome``."""
    left = [Chem.MolToSmiles(m) for m in outcome.pop('left_mapped')]
    count = len(job['reactants'])
    shown = left[count:] if job['include'] else [Chem.MolToSmiles(m) for _, m in job['agents']]
    products = [Chem.MolToSmiles(m) for m in outcome.pop('right_mapped')]
    return '.'.join(left[:count]) + '>' + '.'.join(shown) + '>' + '.'.join(products)


def _bond_summary(outcome):
    """'formed C-N; broken C-Cl' from the bond changes of a mapping (with a note when it is not complete)."""
    parts = []
    for change in outcome['bond_changes']:
        text = f"{change['type'].replace('_', ' ')} {change['elements']}"
        if 'from' in change and 'to' in change:
            text += f" ({change['from']} to {change['to']})"
        if text not in parts:
            parts.append(text)
    text = '; '.join(parts) or 'none'
    return text if outcome['status'] == 'complete' else f"{text} ({outcome['status']} mapping)"


def _add_bond_changes(entries, warnings, method):
    """Add the bond changes of every calculated reaction from one batched mapping call.

    A reaction that cannot be mapped, or a method that is not installed, only costs this line.
    """
    from .. import atom_mapping
    jobs = []
    for entry in entries:
        if not entry['ok']:
            continue
        try:
            jobs.append((entry, _mapping_job(entry['_source'], False)))
        except ValueError as exc:
            warnings.append(f"{entry['label']}: bond changes not mapped: {exc}")
    if not jobs:
        return
    try:
        outcomes = atom_mapping.map_atoms_many([(job['left'], job['products']) for _, job in jobs], method=method)
    except ValueError as exc:
        warnings.append(f'bond changes not mapped: {exc}')
        return
    for (entry, _), outcome in zip(jobs, outcomes):
        if 'error' in outcome:
            warnings.append(f"{entry['label']}: bond changes not mapped: {outcome['error']}")
            continue
        entry['mapping'] = {'method': outcome['method'], 'title': atom_mapping.TITLES[outcome['method']],
                            'status': outcome['status'], 'summary': _bond_summary(outcome),
                            **{key: outcome[key] for key in ('confidence', 'confident') if key in outcome}}
        warnings += [f"{entry['label']}: {w}" for w in outcome['warnings']]


def _map_many(reactions, include_agents, settings, extras, output_path):
    """map_reaction_atoms for a list of reactions: every installed method gets them in one call."""
    from .. import atom_mapping
    items = _batch_items(reactions)
    if any(own for _, _, own in items):
        raise ValueError('Options apply to the whole list: pass them in options, not per reaction')
    entries, jobs, warnings = [], [], []
    for number, (label, spec, _) in enumerate(items, 1):
        name = label or f'Reaction {number}'
        try:
            for entry_label, source in _labelled_sources(label, spec, name):
                if len(entries) >= MAX_BATCH:
                    raise ValueError(f'At most {MAX_BATCH} reactions per call')
                job = _mapping_job(source, include_agents)
                entries.append({'label': entry_label})
                jobs.append((entries[-1], job))
        except ValueError as exc:
            entries.append({'label': name, 'ok': False, 'error': str(exc)})
            warnings.append(f'{name}: {exc}')
    outcomes = atom_mapping.map_atoms_many([(job['left'], job['products']) for _, job in jobs], **settings)
    for (entry, job), outcome in zip(jobs, outcomes):
        if 'error' in outcome:
            entry.update(ok=False, error=outcome['error'])
            warnings.append(f"{entry['label']}: {outcome['error']}")
            continue
        mapped = _mapped_reaction(job, outcome)
        entry.update({'ok': True, **outcome, 'mapped_reaction': mapped})
        _template_extras(entry, job, extras)
        warnings += [f"{entry['label']}: {w}" for w in outcome['warnings']]
    result = {'ok': True, 'operation': 'map_reaction_atoms', 'count': len(entries), 'reactions': entries,
              'warnings': warnings}
    if output_path:
        if Path(output_path).suffix.lower() == '.svg':
            raise ValueError('A picture is made one reaction at a time: use .json or .smi for several reactions')
        target = _publish(output_path, {
            '.json': lambda: json.dumps({'reactions': entries}, ensure_ascii=False, indent=2),
            '.smi': lambda: ''.join(f"{e['mapped_reaction']}\n" for e in entries if e.get('ok')),
        })
        result = artifact_safety.with_artifacts({**result, 'output_path': str(target)}, [target])
    return result


def map_reaction_atoms(reaction: str | dict | list, options: dict | None = None, output_path: str | None = None) -> dict:
    """Map each product atom to the reactant atom it comes from (atom-to-atom mapping).

    reaction is a reaction SMILES "reactants>agents>products", {"reactants": [...], "products": [...]}
    of structure records, or {"cdxml": path, "steps": [step id]} (one reaction step). A list of
    these (at most 100, each optionally {"label": "3a", "reaction": ...}; a drawing with several
    steps gives one entry per step) maps them all in one pass: a learned mapper loads its model on
    every call, so this takes about as long as one reaction. The answer then holds "reactions", one
    entry per reaction with the fields below (or ok false and an error), and output_path ends in
    .json or .smi (one mapped reaction per line). Hydrogens are
    not mapped. Methods (option method): "mcs" is built in and needs nothing installed; it pairs
    atoms by repeated maximum-common-substructure matching, keeps the pairing with the fewest
    unmapped product atoms and then the fewest bond changes, and lists product atoms with more
    than one equally good source as ambiguous instead of deciding. "rxnmapper" and "localmapper"
    are learned mappers that run locally and need the one-time download made by
    `cdx.py install-mappers`; they decide every atom, and RXNMapper also returns a confidence
    (LocalMapper a confident flag) that you should read before trusting the map. "auto" (default)
    uses LocalMapper, then RXNMapper, then "mcs", and falls back with a warning if a mapper fails.
    Option compare runs every installed method and adds a "comparison" with the product atoms they
    disagree on. This is bookkeeping, not a mechanism: pericyclic reactions and rearrangements can
    be mapped differently from the textbook arrows. The result holds the mapped reaction SMILES,
    a per-atom table, the bond changes (formed, broken, order changed), reactant atoms with no
    product counterpart (leaving groups), product atoms without a source (status "incomplete"),
    and, for "mcs", product atoms that could come from more than one reactant atom (status
    "ambiguous"; left unmapped, never decided silently). Other options: resolve_ambiguity
    (default false, "mcs" only) accepts a fixed tie-break for them, with a warning; include_agents
    (default false) also offers the agent structures as atom sources. Option template adds
    "template": the reaction centre as a reaction SMARTS (the atoms whose bonds change, their
    neighbours and the leaving atoms, written by element with maps renumbered from 1) and whether
    it reproduces the drawn products. Option classify adds "reaction_class": the name of the
    generic template (amide coupling, esterification, Suzuki-type coupling, aryl amination,
    reductive amination, Boc deprotection, ...) that makes the drawn products from the drawn
    structures, every template that fits, and null with a note when none does; it reads the
    structures only, never the conditions. Option map_numbers_into_scheme (one drawn reaction,
    {"cdxml": path}) is the path of a new .cdxml: a copy of the drawing with each map number
    written beside its atom on both sides, never overwriting a file. output_path ends in .json,
    .smi (the mapped reaction SMILES) or .svg (a picture) and is never overwritten. At most 120
    heavy atoms per side.
    """
    from .. import atom_mapping
    options = dict(options or {})
    unknown = set(options) - {'resolve_ambiguity', 'include_agents', 'method', 'compare', 'template', 'classify',
                              'map_numbers_into_scheme'}
    if unknown:
        raise ValueError(f'Unknown options: {sorted(unknown)}')
    settings = {'resolve_ambiguity': bool(options.get('resolve_ambiguity')),
                'method': str(options.get('method') or 'auto'), 'compare': bool(options.get('compare'))}
    extras = {'template': bool(options.get('template')), 'classify': bool(options.get('classify'))}
    scheme_output = options.get('map_numbers_into_scheme')
    if scheme_output:
        if isinstance(reaction, list):
            raise ValueError('map_numbers_into_scheme writes into one drawn reaction: pass {"cdxml": path}, not a list')
        if not (isinstance(reaction, dict) and reaction.get('cdxml')):
            raise ValueError('map_numbers_into_scheme needs a drawn reaction: pass {"cdxml": path}')
        if Path(str(scheme_output)).suffix.lower() != '.cdxml':
            raise ValueError('map_numbers_into_scheme must be the path of a new .cdxml file')
    if isinstance(reaction, list):
        return _map_many(reaction, bool(options.get('include_agents')), settings, extras, output_path)
    sources = _reaction_sources(reaction)
    if len(sources) != 1:
        raise ValueError(f'The file stores {len(sources)} reaction steps; choose one with {{"cdxml": path, "steps": [step id]}}')
    job = _mapping_job(sources[0], bool(options.get('include_agents')))
    outcome = atom_mapping.map_atoms(job['left'], job['products'], **settings)
    mapped = _mapped_reaction(job, outcome)
    result = {'ok': True, 'operation': 'map_reaction_atoms', **outcome, 'mapped_reaction': mapped}
    _template_extras(result, job, extras)
    scheme_target = None
    if scheme_output:
        text, notes = _numbered_scheme(Path(reaction['cdxml']).expanduser().resolve(), job, outcome)
        scheme_target = _publish(scheme_output, {'.cdxml': lambda: text})
        result['scheme_path'] = str(scheme_target)
        result['warnings'] = list(result['warnings']) + notes
    targets = [scheme_target] if scheme_target else []
    if output_path:
        target = _publish(output_path, {
            '.json': lambda: json.dumps(result, ensure_ascii=False, indent=2),
            '.smi': lambda: mapped + '\n',
            '.svg': lambda: _mapping_picture(mapped),
        })
        result = {**result, 'output_path': str(target)}
        targets.append(target)
    return artifact_safety.with_artifacts(result, targets) if targets else result


def characterization_text(compounds: list[dict], options: dict | None = None, output_path: str | None = None) -> dict:
    """ACS-style characterization paragraph per compound, in the order of the ACS Style Guide.

    Each record is a grounded structure (SMILES, molblock or CDXML/MOL/SDF file, optional label)
    with any of: appearance (text), rf ({value, eluent}), mp (number, "112-114" or [low, high]),
    optical_rotation ({value, c, solvent, temperature}), ir ({medium, values} or a list), nmr
    ({"1H": {frequency, solvent, text | peaks}, "13C": {...}, "19F": {...}}), and the HRMS fields
    of hrms_line (adduct, adducts, found_mz; "hrms": false leaves HRMS out). NMR peaks are text
    such as "7.40-7.30 (m, 5H), 5.11 (s, 2H)" or a list of numbers, strings and
    {shift | range, mult, J, n}; the digits you give are printed unchanged and ranges get an en
    dash. The paragraph reads: appearance; Rf; mp; [a]D; IR; 1H; 13C; other nuclei; HRMS.
    Checks never change a value; they add warnings: the 1H integral against the hydrogens of the
    formula, the 13C signal count against the symmetry-distinct carbons, a residual-solvent
    signal in a 13C list, an unusual multiplicity code, a wide melting range, a rotation without
    c or solvent, and an HRMS error over 5 ppm. Options are those of hrms_line (adducts, mode,
    ionization, decimals, electron_mass). Output ends in .txt, .md or .json and is never
    overwritten. At most 256 structures.
    """
    from .. import spectral_text
    from ..characterization import default_adduct, hrms_entry
    options = dict(options or {})
    unknown = set(options) - {'adducts', 'mode', 'ionization', 'decimals', 'electron_mass'}
    if unknown:
        raise ValueError(f'Unknown option(s): {sorted(unknown)}')
    mode = options.get('mode', 'positive')
    if mode not in ('positive', 'negative'):
        raise ValueError('mode must be positive or negative')
    ionization = options.get('ionization', 'ESI')
    decimals = int(options.get('decimals', 4))
    electron_mass = bool(options.get('electron_mass', True))
    warnings, results = [], []
    for item in _expand(compounds, limit=MAX_STRUCTURES):
        record, mol, label = item['record'], item['mol'], item['label']
        _check_grounded(mol, label)
        described = spectral_text.describe(record, mol, label)
        parts, found_line = described['parts'], None
        warnings += described['warnings']
        if record.get('hrms', True) is not False:
            adduct = record.get('adduct') or (record.get('adducts') or options.get('adducts') or [None])[0] \
                or default_adduct(Chem.RemoveHs(mol), mode, ionization)
            found = record.get('found_mz')
            value = found.get(adduct) if isinstance(found, dict) else found
            entry = hrms_entry(mol, adduct, ionization=ionization, decimals=decimals, found=value,
                               electron_mass=electron_mass)
            if value is None:
                warnings.append(f'{label}: no found HRMS value was given, so only the calculated value is written.')
            elif abs(entry['error_ppm']) > 5:
                warnings.append(f"{label}: {entry['adduct']} found {entry['found_mz']} is {entry['error_ppm']:+.1f} ppm "
                                'from the calculated value; check the adduct, the formula and the instrument calibration.')
            parts.append(entry['line'])
            found_line = entry
        if not parts:
            raise ValueError(f'{label}: give at least one of appearance, rf, mp, optical_rotation, ir, nmr or HRMS data')
        if len(Chem.GetMolFrags(mol)) > 1:
            warnings.append(f'{label}: more than one component; the formula and the NMR checks describe the whole record.')
        results.append({'label': label, 'source': item['source'], 'paragraph': '; '.join(parts) + '.',
                        'checks': described['checks'], 'hrms': found_line})
    text = ''.join(f"{r['label']}: {r['paragraph']}\n" for r in results)
    result = {'ok': True, 'operation': 'characterization_text', 'count': len(results), 'compounds': results,
              'text': text, 'warnings': warnings}
    if output_path:
        target = _publish(output_path, {
            '.txt': lambda: text,
            '.md': lambda: ''.join(f"**{r['label']}** {r['paragraph']}\n\n" for r in results).rstrip('\n') + '\n',
            '.json': lambda: json.dumps({'compounds': results}, ensure_ascii=False, indent=2),
        })
        result = artifact_safety.with_artifacts({**result, 'output_path': str(target)}, [target])
    return result


REPORT_TOOLS = {f.__name__: f for f in (molecule_report, check_reaction_balance, export_structures,
                                         structure_to_name, chemdraw_chemical_properties, stoichiometry_grid, hrms_line,
                                         si_materials_tables, map_reaction_atoms, characterization_text,
                                         route_summary)}
