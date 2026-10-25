"""What a mapped reaction did: its reaction centre as a SMARTS, its type, and its map numbers in a drawing.

``reaction_center`` reads an atom-mapped reaction and keeps only the atoms whose bonds or charge
change, their direct neighbours, and the leaving atoms next to them, as a reaction SMARTS with
the maps renumbered from 1. ``classify`` names the reaction by running a short list of generic
reaction templates on the structures and comparing what they make with the products; it reads the
structures only (never the conditions) and answers "unclassified" instead of guessing.
``write_map_numbers`` adds the map numbers beside the atoms of a ChemDraw scheme.
"""

from __future__ import annotations

import itertools
import math
import re
from functools import lru_cache
from xml.etree import ElementTree as ET

from rdkit import Chem, rdBase
from rdkit.Chem import rdChemReactions

MAX_CANDIDATES = 8

_NUCLEOPHILE = '[NX3;H2,H1;!$(NC=[O,S,N])'
_LEAVING = '[Cl,Br,I,$(OS(=O)=O)]'

# (name, reaction SMARTS). The first product of a template is the one that has to be among the
# drawn products; the order decides which match is named first (the more specific first).
TEMPLATES = (
    ('Amide formation (acid chloride and amine)',
     f'[CX3:1](=[O:2])[Cl,Br,I].{_NUCLEOPHILE}:3]>>[C:1](=[O:2])[N:3]'),
    ('Sulfonamide formation (sulfonyl chloride and amine)',
     f'[SX4:1](=[O:2])(=[O:3])[Cl].{_NUCLEOPHILE}:4]>>[S:1](=[O:2])(=[O:3])[N:4]'),
    ('Amide coupling (carboxylic acid and amine)',
     f'[CX3:1](=[O:2])[OX2H1].{_NUCLEOPHILE}:3]>>[C:1](=[O:2])[N:3]'),
    ('N-Acylation with an anhydride (for example Boc protection)',
     f'{_NUCLEOPHILE}:1].[CX3:2](=[O:3])O[CX3]=O>>[C:2](=[O:3])[N:1]'),
    ('Ester formation (acid chloride and alcohol)',
     '[CX3:1](=[O:2])[Cl,Br,I].[OX2H1:3][#6;!$(C=O):4]>>[C:1](=[O:2])[O:3][#6:4]'),
    ('Esterification (carboxylic acid and alcohol)',
     '[CX3:1](=[O:2])[OX2H1].[OX2H1:3][#6;!$(C=O):4]>>[C:1](=[O:2])[O:3][#6:4]'),
    ('Suzuki-type coupling (aryl or vinyl halide and organoboron)',
     '[#6;$([#6]=,:[#6]):1][Cl,Br,I].[#6;$([#6]=,:[#6]):2][B]>>[#6:1][#6:2]'),
    ('Aryl amination (SNAr or Pd/Cu-catalysed C-N coupling)',
     f'[c:1][F,Cl,Br,I].{_NUCLEOPHILE}:2]>>[c:1][N:2]'),
    ('N-Alkylation (SN2)',
     f'[CX4:1]{_LEAVING}.{_NUCLEOPHILE}:2]>>[C:1][N:2]'),
    ('O-Alkylation (Williamson ether synthesis)',
     f'[CX4:1]{_LEAVING}.[OX2H1:2][#6;!$(C=O):3]>>[C:1][O:2][#6:3]'),
    ('Reductive amination (carbonyl and amine)',
     f'[CX3;!$(C-[O,N,S]):1]=O.{_NUCLEOPHILE}:2]>>[C:1][N:2]'),
    ('Carbonyl reduction (aldehyde or ketone to alcohol)',
     '[CX3;!$(C-[O,N,S]);!$(C=C):1]=[O:2]>>[C:1][O:2]'),
    ('Alcohol oxidation (to an aldehyde or ketone)',
     '[CX4;H2,H1;!$(C-[N,S]):1][OX2H1:2]>>[C:1]=[O:2]'),
    ('Ester hydrolysis (to the carboxylic acid)',
     '[CX3:1](=[O:2])[OX2:3][CX4]>>[C:1](=[O:2])[O:3]'),
    ('Boc deprotection',
     '[NX3:1]C(=O)OC(C)(C)C>>[N:1]'),
    ('Nitro reduction (to the amine)',
     '[#6:1][N+:2](=O)[O-]>>[#6:1][N+0:2]'),
    ('Hydrogenation of a C=C bond',
     '[CX3:1]=[CX3:2]>>[C:1][C:2]'),
    ('Azide-alkyne cycloaddition (click, to a 1,2,3-triazole)',
     '[CH:1]#[C:2].[#6:6][N:3]=[N+:4]=[N-:5]>>[cH:1]1:[c:2]:[n+0:5]:[n+0:4]:[n+0:3]:1-[#6:6]'),
    ('Diels-Alder cycloaddition',
     '[C:1]=[C:2][C:3]=[C:4].[C:5]=[C:6]>>[C:1]1[C:2]=[C:3][C:4][C:5][C:6]1'),
)


@lru_cache(maxsize=None)
def _reaction(smarts):
    rxn = rdChemReactions.ReactionFromSmarts(smarts)
    if rxn is None:
        raise ValueError(f'Invalid reaction template: {smarts}')
    return rxn


def _flat(mol):
    """Canonical SMILES of ``mol`` without maps, stereo, isotopes or coordinates."""
    mol = Chem.RemoveHs(Chem.Mol(mol))
    mol.RemoveAllConformers()
    Chem.RemoveStereochemistry(mol)
    for atom in mol.GetAtoms():
        atom.SetAtomMapNum(0)
        atom.SetIsotope(0)
    return Chem.MolToSmiles(mol)


def _made(rxn, reactants):
    """Flat SMILES of the first product of every way the template runs on ``reactants``."""
    out = set()
    with rdBase.BlockLogs():
        outcomes = rxn.RunReactants(tuple(reactants), 20)
    for products in outcomes:
        try:
            product = Chem.Mol(products[0])
            Chem.SanitizeMol(product)
            out.add(_flat(product))
        except Exception:
            continue
    return out


def classify(reactants, agents, products) -> dict:
    """Name the reaction by the generic template that makes the drawn products from its structures.

    ``reactants``, ``agents`` and ``products`` are lists of ``(label, mol)``. Agents may supply a
    reactant (a reagent that becomes part of the product). Several templates can fit one reaction;
    all are listed, the first is the name.
    """
    candidates = [(label, mol, 'reactant') for label, mol in reactants] + \
                 [(label, mol, 'agent') for label, mol in agents]
    note_extra = ''
    if len(candidates) > MAX_CANDIDATES:
        candidates = candidates[:MAX_CANDIDATES]
        note_extra = f' Only the first {MAX_CANDIDATES} structures were tried.'
    drawn = {_flat(mol) for _, mol in products}
    matches = []
    for name, smarts in TEMPLATES:
        rxn = _reaction(smarts)
        size = rxn.GetNumReactantTemplates()
        for combination in itertools.permutations(range(len(candidates)), size):
            chosen = [candidates[i] for i in combination]
            if _made(rxn, [Chem.RemoveHs(m) for _, m, _ in chosen]) & drawn:
                matches.append({'name': name, 'species': [label for label, _, _ in chosen],
                                'roles': [role for _, _, role in chosen]})
                break
    if not matches:
        return {'name': None, 'matches': [], 'basis': 'reaction centre',
                'note': 'unclassified: none of the generic templates (' + str(len(TEMPLATES)) + ') makes the '
                        'drawn products from these structures; this does not mean the reaction is wrong.' + note_extra}
    note = ('Named from the structures alone (the reaction centre); the conditions are not read. '
            + ('Other templates also fit: ' + '; '.join(m['name'] for m in matches[1:]) + '. ' if len(matches) > 1 else '')
            + 'A name is a label for the bond changes, not a statement of mechanism.')
    return {'name': matches[0]['name'], 'matches': matches, 'basis': 'reaction centre', 'note': note + note_extra}


# --- the reaction centre ---------------------------------------------------

def _signature(atom):
    """What the bonds of a mapped atom look like: mapped neighbours and bond orders, count of the others."""
    mapped, other = [], []
    for bond in atom.GetBonds():
        neighbour = bond.GetOtherAtom(atom)
        if neighbour.GetAtomMapNum():
            mapped.append((neighbour.GetAtomMapNum(), bond.GetBondTypeAsDouble()))
        else:
            other.append((neighbour.GetSymbol(), bond.GetBondTypeAsDouble()))
    return tuple(sorted(mapped)), tuple(sorted(other)), atom.GetFormalCharge()


def _side(text):
    mols = []
    for piece in filter(None, text.split('.')):
        mol = Chem.MolFromSmiles(piece)
        if mol is None:
            raise ValueError(f'Not a mapped reaction SMILES: {piece}')
        mols.append(mol)
    return mols


def _fragment(mol, atoms, renumber):
    copy = Chem.Mol(mol)
    for atom in copy.GetAtoms():
        atom.SetAtomMapNum(renumber.get(atom.GetAtomMapNum(), 0))
    bonds = [b.GetIdx() for b in copy.GetBonds() if b.GetBeginAtomIdx() in atoms and b.GetEndAtomIdx() in atoms]
    return Chem.MolFragmentToSmarts(copy, atomsToUse=sorted(atoms), bondsToUse=bonds)


def reaction_center(mapped_reaction: str) -> dict:
    """The reaction centre of an atom-mapped reaction SMILES as a reaction SMARTS.

    Kept: the atoms whose bonds or charge change, their neighbours, and the unmapped atoms next to
    a changed one (leaving groups, new atoms). Atoms are written by element only (``[#6:1]``), so
    the template fits other substituents; its map numbers run from 1. ``reproduces`` says whether
    running the template on the drawn reactants gives the drawn products.
    """
    left_text, _, right_text = mapped_reaction.split('>')
    left, right = _side(left_text), _side(right_text)
    where = {}
    for side, mols in (('left', left), ('right', right)):
        for index, mol in enumerate(mols):
            for atom in mol.GetAtoms():
                if atom.GetAtomMapNum():
                    where.setdefault(atom.GetAtomMapNum(), {})[side] = (index, atom.GetIdx())
    changed = {number for number, sides in where.items()
               if 'left' in sides and 'right' in sides
               and _signature(left[sides['left'][0]].GetAtomWithIdx(sides['left'][1]))
               != _signature(right[sides['right'][0]].GetAtomWithIdx(sides['right'][1]))}
    keep = set(changed)
    for side, mols in (('left', left), ('right', right)):
        for number in changed:
            index, atom_index = where[number][side]
            for neighbour in mols[index].GetAtomWithIdx(atom_index).GetNeighbors():
                if neighbour.GetAtomMapNum():
                    keep.add(neighbour.GetAtomMapNum())
    if not changed:
        return {'smarts': None, 'changed_atoms': 0, 'atoms': 0}
    renumber = {number: n for n, number in enumerate(sorted(keep), 1)}
    pieces = []
    for mols, side in ((left, 'left'), (right, 'right')):
        side_pieces = []
        for index, mol in enumerate(mols):
            atoms = set()
            for atom in mol.GetAtoms():
                number = atom.GetAtomMapNum()
                if number in keep:
                    atoms.add(atom.GetIdx())
                elif not number and any(n.GetAtomMapNum() in changed for n in atom.GetNeighbors()):
                    atoms.add(atom.GetIdx())
            if atoms:
                text = _fragment(mol, atoms, renumber)
                side_pieces.append(f'({text})' if '.' in text else text)
        pieces.append('.'.join(side_pieces))
    smarts = f'{pieces[0]}>>{pieces[1]}'
    # a neighbour that does not change is any atom, so the template fits other substituents and ring atoms
    for number in keep - changed:
        smarts = re.sub(rf'\[[^\]:]*:{renumber[number]}\]', f'[*:{renumber[number]}]', smarts)
    return {'smarts': smarts, 'changed_atoms': len(changed), 'atoms': len(keep)}


def reproduces(smarts, reactants, products) -> bool | None:
    """Whether the template run on ``reactants`` (list of mols) makes one of ``products``; None if it cannot run."""
    try:
        rxn = _reaction(smarts)
    except ValueError:
        return None
    n = rxn.GetNumReactantTemplates()
    drawn = {_flat(m) for m in products}
    if n > len(reactants):
        return False
    for combination in itertools.permutations(range(len(reactants)), n):
        with rdBase.BlockLogs():
            outcomes = rxn.RunReactants(tuple(Chem.RemoveHs(reactants[i]) for i in combination), 20)
        for made in outcomes:
            try:
                flats = set()
                for product in made:
                    product = Chem.Mol(product)
                    Chem.SanitizeMol(product)
                    flats.add(_flat(product))
            except Exception:
                continue
            if flats & drawn:
                return True
    return False


# --- map numbers in a ChemDraw scheme ---------------------------------------

SCALE = 65536.0        # RDKit's CDXML conformers hold the drawing coordinates times this factor
SIZE = 7.0
MATCH = 0.5            # tolerated distance between an atom and its drawing node (points)


RADII = (10.5, 13.5, 17.0)   # distances from the atom tried in turn
ROOM = 8.0                   # free distance from the number's centre that is good enough
EXTENT = 3.0                 # half the size of a number, taken off every clearance


def _nodes(fragment):
    out = []
    for node in fragment.findall('n'):
        if node.get('p'):
            x, y = (float(v) for v in node.get('p').split()[:2])
            out.append((x, y))
    return out


def _obstacles(page):
    """Atom positions, bond segments and text boxes of the whole page."""
    points, ends, boxes = {}, [], []
    for node in page.iter('n'):
        if node.get('p'):
            points[node.get('id')] = tuple(float(v) for v in node.get('p').split()[:2])
    for bond in page.iter('b'):
        if bond.get('B') in points and bond.get('E') in points:
            ends.append((points[bond.get('B')], points[bond.get('E')]))
    for text in page.iter('t'):
        if text.get('BoundingBox'):
            boxes.append(tuple(float(v) for v in text.get('BoundingBox').split()))
    return list(points.values()), ends, boxes


def _segment_distance(p, a, b):
    ax, ay = a
    dx, dy = b[0] - ax, b[1] - ay
    length = dx * dx + dy * dy
    t = 0.0 if length == 0 else max(0.0, min(1.0, ((p[0] - ax) * dx + (p[1] - ay) * dy) / length))
    return math.hypot(p[0] - (ax + t * dx), p[1] - (ay + t * dy))


def _box_distance(p, box):
    dx = max(box[0] - p[0], 0.0, p[0] - box[2])
    dy = max(box[1] - p[1], 0.0, p[1] - box[3])
    return math.hypot(dx, dy)


def _clearance(p, own, points, segments, boxes):
    """How far a number centred at ``p`` is from everything drawn except its own atom."""
    near = [math.hypot(p[0] - a, p[1] - b) for a, b in points if math.hypot(a - own[0], b - own[1]) > MATCH]
    near += [_segment_distance(p, a, b) for a, b in segments]
    near += [_box_distance(p, box) + EXTENT for box in boxes]
    return min(near, default=99.0)


def _spot(own, points, segments, boxes):
    """The place for a number beside the atom at ``own``: the free spot nearest to it, else the freest."""
    best = None
    for radius in RADII:
        ring = None
        for step in range(24):
            angle = step * math.pi / 12
            p = (own[0] + radius * math.cos(angle), own[1] + radius * math.sin(angle))
            room = _clearance(p, own, points, segments, boxes)
            if ring is None or room > ring[0]:
                ring = (room, p)
        if ring[0] >= ROOM:
            return ring[1]
        if best is None or ring[0] > best[0]:
            best = ring
    return best[1]


def _label(ident, z, number, x, y):
    width = max(len(str(number)), 1) * 3.9
    baseline = y + SIZE * 0.36
    return (f'<t id="{ident}" p="{x:.2f} {baseline:.2f}" '
            f'BoundingBox="{x - width / 2:.2f} {baseline - SIZE * 0.72:.2f} {x + width / 2:.2f} {baseline + SIZE * 0.1:.2f}" '
            f'Z="{z}" MapNumber="true" CaptionJustification="Center" Justification="Center" LineHeight="auto">'
            f'<s font="3" size="{SIZE}" color="0" face="96">{number}</s></t>\n')


def write_map_numbers(text: str, numbers: dict) -> tuple[str, list]:
    """(CDXML text with the map numbers added, warnings).

    ``numbers`` is ``{fragment id: {atom index: map number}}`` where the atom index counts the
    heavy atoms of the fragment as RDKit reads it. A number is a small label placed away from the
    neighbouring atoms; nothing already in the file changes.
    """
    from .reaction_calculator.annotate import _next_id, _tag_end, read_fragments_from_text
    root = ET.fromstring(text.encode('utf-8'))
    page = root.find('page')
    if page is None:
        raise ValueError('The file has no page')
    mols = dict(read_fragments_from_text(text))
    ident = _next_id(text)
    z = max([int(v) for v in re.findall(r'\bZ="(\d+)"', text)] or [1000]) + 1
    warnings, additions = [], []
    nodes, segments, boxes = _obstacles(page)
    for fragment in page.findall('fragment'):
        wanted = numbers.get(fragment.get('id'))
        mol = mols.get(fragment.get('id'))
        if not wanted or mol is None:
            continue
        mol = Chem.RemoveHs(mol)
        if not mol.GetNumConformers():
            warnings.append(f"fragment {fragment.get('id')}: no drawing coordinates, numbers not written")
            continue
        positions = _nodes(fragment)
        conformer = mol.GetConformer()
        points = []
        for atom in mol.GetAtoms():
            point = conformer.GetAtomPosition(atom.GetIdx())
            points.append((point.x / SCALE, -point.y / SCALE))
        placed = []
        for index, number in sorted(wanted.items()):
            x, y = points[index]
            if not any(math.hypot(x - a, y - b) < MATCH for a, b in positions):
                warnings.append(f"fragment {fragment.get('id')}: atom {index} was not found in the drawing, "
                                f'number {number} not written')
                continue
            cx, cy = _spot((x, y), nodes, segments, boxes)
            placed.append(_label(ident, z, number, cx, cy))
            width = max(len(str(number)), 1) * 3.9
            boxes.append((cx - width / 2, cy - SIZE / 2, cx + width / 2, cy + SIZE / 2))
            ident, z = ident + 1, z + 1
        additions.append((fragment.get('id'), ''.join(placed)))
    for fragment_id, block in additions:
        start = text.index(f'<fragment id="{fragment_id}"')
        end = _tag_end(text, start, 'fragment')
        text = text[:end] + '\n' + block + text[end:].lstrip('\n')
    return text, warnings
