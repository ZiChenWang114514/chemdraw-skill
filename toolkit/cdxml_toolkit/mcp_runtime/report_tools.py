"""Deterministic chemistry reports: property sheets, reaction balance, structure export and names.

Every number comes from RDKit applied to a grounded structure (SMILES, MOL/SDF or a CDXML
fragment read back from the file). Nothing here recognises, guesses or edits structures.
"""
from __future__ import annotations

import csv
import io
import json
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
        mz = (exact - charge * ELECTRON) / z
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
    if isinstance(reaction, str):
        sources = [{'step_id': None, **_from_smiles(reaction)}]
    elif isinstance(reaction, dict) and 'cdxml' in reaction:
        steps = reaction.get('steps')
        sources = _from_cdxml(reaction['cdxml'], set(map(str, steps)) if steps else None)
    elif isinstance(reaction, dict) and reaction.get('reactants') and reaction.get('products'):
        sources = [{'step_id': None, 'reactants': reaction['reactants'], 'agents': reaction.get('agents') or [],
                    'products': reaction['products']}]
    else:
        raise ValueError('reaction must be a reaction SMILES, {"reactants": [...], "products": [...]} or {"cdxml": path}')
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


REPORT_TOOLS = {f.__name__: f for f in (molecule_report, check_reaction_balance, export_structures,
                                         structure_to_name)}
