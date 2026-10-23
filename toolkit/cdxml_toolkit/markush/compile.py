"""Compile a Markush spec into a labelled graph, CXSMILES and V3000.

CXSMILES is written here, not by ``Chem.MolToCXSmiles``: RDKit drops the
``m:`` (variable attachment) field when it writes, and the field indices
must follow the SMILES output order.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field

from rdkit import Chem

from .spec import ELEMENTS, _bond_parts, label_runs, load_spec, plain_label, validate_spec
from .templates import template_mol


class SpecError(ValueError):
    def __init__(self, errors):
        super().__init__('Markush spec is invalid:\n- ' + '\n- '.join(errors))
        self.errors = list(errors)


@dataclass
class Graph:
    mol: Chem.RWMol
    atoms: list[dict]                 # per mol atom: ref, label, kind, fragment, locant
    bonds: list[dict]                 # per mol bond: a, b, order, display
    groups: list[dict] = field(default_factory=list)   # variable_position groups
    rings: list[dict] = field(default_factory=list)    # variable rings
    links: list[dict] = field(default_factory=list)
    index: dict[str, int] = field(default_factory=dict)


def cx_label(info: dict) -> str:
    return info.get('plain') or plain_label(info['label'])


def _definition(defs: dict, info: dict):
    """Definitions are keyed by atom id/ref or by the plain label (``G1`` for ``ar:3``)."""
    return defs.get(info['ref']) or defs.get(cx_label(info))


def _new_atom(mol, element=0):
    atom = Chem.Atom(element)
    atom.SetNoImplicit(False)
    return mol.AddAtom(atom)


def build_graph(spec) -> Graph:
    spec = load_spec(spec)
    errors = validate_spec(spec)
    if errors:
        raise SpecError(errors)
    mol = Chem.RWMol()
    atoms, index, bonds = [], {}, []

    def add(ref, element=0, **info):
        idx = _new_atom(mol, element)
        index[ref] = idx
        atoms.append({'ref': ref, **info})
        return idx

    for frag in spec.get('fragments', []):
        tpl = template_mol(frag['template'])
        replace = frag.get('replace') or {}
        local = []
        for atom in tpl.GetAtoms():
            loc = atom.GetProp('locant')
            ref = f"{frag['id']}:{loc}"
            if loc in replace:
                idx = add(ref, 0, label=replace[loc], kind='generic', fragment=frag['id'], locant=loc)
            else:
                idx = add(ref, atom.GetAtomicNum(), fragment=frag['id'], locant=loc)
                mol.GetAtomWithIdx(idx).SetNumExplicitHs(atom.GetTotalNumHs())
                mol.GetAtomWithIdx(idx).SetNoImplicit(True)
            local.append(idx)
        double = {frozenset(pair) for pair in frag.get('double') or []}
        for bond in tpl.GetBonds():
            btype = bond.GetBondType()
            if double:  # the drawing's Kekule pattern, e.g. [["C2","C3"], ...]
                pair = frozenset((bond.GetBeginAtom().GetProp('locant'), bond.GetEndAtom().GetProp('locant')))
                if btype in (Chem.BondType.SINGLE, Chem.BondType.DOUBLE):
                    btype = Chem.BondType.DOUBLE if pair in double else Chem.BondType.SINGLE
            mol.AddBond(local[bond.GetBeginAtomIdx()], local[bond.GetEndAtomIdx()], btype)
            bonds.append({'a': atoms[local[bond.GetBeginAtomIdx()]]['ref'],
                          'b': atoms[local[bond.GetEndAtomIdx()]]['ref'],
                          'order': {Chem.BondType.DOUBLE: 2, Chem.BondType.TRIPLE: 3}.get(btype, 1),
                          'display': None, 'template': True})
    rings = []
    for atom in spec.get('atoms', []):
        if 'element' in atom:
            idx = add(atom['id'], ELEMENTS[atom['element']])
            if 'h' in atom:
                mol.GetAtomWithIdx(idx).SetNumExplicitHs(int(atom['h']))
                mol.GetAtomWithIdx(idx).SetNoImplicit(True)
        else:
            kind = 'ring' if atom.get('kind') == 'variable_ring' else 'generic'
            idx = add(atom['id'], 0, label=atom['label'], kind=kind)
            if kind == 'ring':
                rings.append({'ref': atom['id'], 'label': atom['label'],
                              'members': list(atom.get('members') or [])})
    order_type = {1: Chem.BondType.SINGLE, 2: Chem.BondType.DOUBLE, 3: Chem.BondType.TRIPLE}

    def bond(a, b, order=1, display=None):
        ia, ib = index[a], index[b]
        mol.AddBond(ia, ib, order_type[order])
        for i in (ia, ib):  # an explicit H on a template N (indole [nH]) is used up by the bond
            at = mol.GetAtomWithIdx(i)
            if at.GetAtomicNum() and at.GetNoImplicit() and at.GetNumExplicitHs() and \
                    atoms[i].get('fragment') and not atoms[i].get('h_fixed'):
                at.SetNumExplicitHs(max(0, at.GetNumExplicitHs() - order))
        bonds.append({'a': a, 'b': b, 'order': order, 'display': display})

    for item in spec.get('bonds', []):
        a, b, order, display = _bond_parts(item)
        bond(a, b, order, display)
    for ring in rings:  # a drawn-member ring closes through its pseudo atom
        if ring['members']:
            bond(ring['members'][-1], ring['ref'])
            bond(ring['ref'], ring['members'][0])
    groups = []
    for g in spec.get('variable_position', []):
        star = add(f"{g['group']}:attach", 0, kind='attach')
        lab = add(g['group'], 0, label=g.get('label') or g['group'], kind='generic', plain=g['group'])
        mol.AddBond(star, lab, Chem.BondType.SINGLE)
        groups.append({'group': g['group'], 'count': g.get('count'), 'on': list(g['on']),
                       'star': star, 'label_atom': lab, 'label': g.get('label') or g['group']})
    links = [dict(l) for l in spec.get('link_nodes', [])]
    for i, info in enumerate(atoms):
        if info.get('label'):
            mol.GetAtomWithIdx(i).SetProp('dummyLabel', cx_label(info))
    flags = Chem.SanitizeFlags.SANITIZE_ALL ^ Chem.SanitizeFlags.SANITIZE_SETAROMATICITY \
        ^ Chem.SanitizeFlags.SANITIZE_KEKULIZE
    problems = []
    for at in mol.GetAtoms():
        at.UpdatePropertyCache(strict=False)
    try:
        Chem.SanitizeMol(mol, flags)
    except Exception as exc:  # valence problems name the atom for the caller
        problems.append(f'Chemistry check failed: {exc}. Check bond orders and H counts near that atom.')
    if problems:
        raise SpecError(problems)
    return Graph(mol=mol, atoms=atoms, bonds=bonds, groups=groups, rings=rings, links=links, index=index)


def to_cxsmiles(graph: Graph) -> str:
    mol = Chem.Mol(graph.mol)
    smiles = Chem.MolToSmiles(mol, kekuleSmiles=True, canonical=True)
    order = list(mol.GetPropsAsDict(True, True)['_smilesAtomOutputOrder'])
    pos = {old: new for new, old in enumerate(order)}
    labels = []
    for old in order:
        info = graph.atoms[old]
        labels.append(cx_label(info) if info.get('label') else '')
    fields = ['$' + ';'.join(labels) + '$']
    if graph.groups:
        parts = [f"{pos[g['star']]}:" + '.'.join(str(pos[graph.index[r]]) for r in g['on'])
                 for g in graph.groups]
        fields.append('m:' + ','.join(parts))
    if graph.links:
        parts = []
        for link in graph.links:
            idx = graph.index[link['atom']]
            nbrs = [n.GetIdx() for n in graph.mol.GetAtomWithIdx(idx).GetNeighbors()]
            tail = '.' + '.'.join(str(pos[n]) for n in nbrs[:2]) if len(nbrs) == 2 else ''
            parts.append(f"{pos[idx]}:{link['min']}.{link['max']}{tail}")
        fields.append('LN:' + ','.join(parts))
    return f"{smiles} |{','.join(fields)}|"


def check_cxsmiles(graph: Graph, cxsmiles: str) -> list[str]:
    """Parse the written CXSMILES back and compare labels and attachment sets."""
    params = Chem.SmilesParserParams()
    params.sanitize = False
    mol = Chem.MolFromSmiles(cxsmiles, params)
    if mol is None:
        return ['CXSMILES does not parse']
    problems = []
    if mol.GetNumAtoms() != graph.mol.GetNumAtoms():
        problems.append('atom count changed in CXSMILES')
    want = sorted(cx_label(a) for a in graph.atoms if a.get('label'))
    got = sorted(a.GetProp('atomLabel') for a in mol.GetAtoms() if a.HasProp('atomLabel'))
    if want != got:
        problems.append(f'labels differ: {want} vs {got}')
    endpoints = sorted(len(b.GetProp('_MolFileBondEndPts').strip('()').split()) - 1
                       for b in mol.GetBonds() if b.HasProp('_MolFileBondEndPts'))
    if endpoints != sorted(len(g['on']) for g in graph.groups):
        problems.append('variable attachment sets differ after readback')
    return problems


def to_molblock(cxsmiles: str, coords: dict[int, tuple[float, float]] | None = None) -> str:
    params = Chem.SmilesParserParams()
    params.sanitize = False
    mol = Chem.MolFromSmiles(cxsmiles, params)
    mol.UpdatePropertyCache(strict=False)
    from rdkit.Chem import rdDepictor
    rdDepictor.Compute2DCoords(mol)
    return Chem.MolToV3KMolBlock(mol)


def enumerate_members(spec, n: int = 5, seed: int = 0) -> dict:
    """Sample concrete molecules using definition ``values`` (``[*:1]`` fragments)."""
    spec = load_spec(spec)
    graph = build_graph(spec)
    defs = spec.get('definitions') or {}
    rng = random.Random(seed)
    missing = sorted({cx_label(a) for a in graph.atoms
                      if a.get('kind') in ('generic', 'ring') and not _definition(defs, a)})
    results, failures = [], []
    for k in range(n * 4):
        if len(results) >= n:
            break
        try:
            smi = _one_member(spec, graph, defs, rng)
        except Exception as exc:  # noqa: BLE001 - report and keep sampling
            failures.append(str(exc))
            continue
        if smi and smi not in results:
            results.append(smi)
    skipped = [g['group'] for g in graph.groups
               if all(graph.atoms[graph.index[r]].get('kind') == 'ring' for r in g['on'])]
    return {'members': results, 'undefined': missing, 'failures': failures[:5],
            'not_enumerated': skipped,
            'note': '[*:1], [*:2] follow the order in which the bonds of that atom are listed in the spec'}


def _one_member(spec, graph, defs, rng):
    mol = Chem.RWMol(graph.mol)
    # variable-position groups: attach the group value at random allowed atoms
    removal = []
    for g in graph.groups:
        removal += [g['star'], g['label_atom']]
        item = defs.get(g['group'])
        if not item or not item.get('values'):
            raise ValueError(f"no values for {g['group']}")
        lo, hi = (item.get('count_range') or [1, 1])
        sites = [r for r in g['on'] if graph.atoms[graph.index[r]].get('kind') != 'ring']
        if not sites:  # substituent on a variable ring: its atoms only exist after expansion
            continue
        k = rng.randint(lo, min(hi, len(sites)))
        for ref in rng.sample(sites, k):
            _attach(mol, graph.index[ref], rng.choice(item['values']))
    # pseudo atoms: replace by a value with matching attachment count
    for i, info in enumerate(graph.atoms):
        if info.get('kind') not in ('generic', 'ring') or info['ref'] in {g['group'] for g in graph.groups}:
            continue
        item = _definition(defs, info)
        if info['ref'] in {g['group'] for g in graph.groups}:
            continue
        if not item or not item.get('values'):
            raise ValueError(f"no values for {cx_label(info)}")
        mol.GetAtomWithIdx(i).SetProp('_replace', rng.choice(item['values']))
    for idx in sorted(removal, reverse=True):
        mol.RemoveAtom(idx)
    mol = _expand_pseudo(mol)
    Chem.SanitizeMol(mol)
    return Chem.MolToSmiles(mol)


def _attach(mol, idx, value):
    frag = Chem.MolFromSmiles(value)
    if frag is None:
        raise ValueError(f'bad value SMILES {value!r}')
    combo = Chem.RWMol(Chem.CombineMols(mol, frag))
    offset = mol.GetNumAtoms()
    star = next(a.GetIdx() + offset for a in frag.GetAtoms() if a.GetAtomicNum() == 0)
    nbr = combo.GetAtomWithIdx(star).GetNeighbors()[0].GetIdx()
    combo.AddBond(idx, nbr, Chem.BondType.SINGLE)
    at = combo.GetAtomWithIdx(idx)
    if at.GetNumExplicitHs():
        at.SetNumExplicitHs(at.GetNumExplicitHs() - 1)
    combo.RemoveAtom(star)
    mol.__init__(combo)


def _expand_pseudo(mol):
    while True:
        target = next((a for a in mol.GetAtoms() if a.HasProp('_replace')), None)
        if target is None:
            return mol
        text = target.GetProp('_replace')
        target.ClearProp('_replace')
        if text in ELEMENTS:  # atom-list variable such as G = C or N
            target.SetAtomicNum(ELEMENTS[text])
            target.SetNoImplicit(False)
            target.SetNumExplicitHs(0)
            continue
        value = Chem.MolFromSmiles(text)
        if value is None:
            raise ValueError(f'bad value SMILES {text!r}')
        stars = sorted((a for a in value.GetAtoms() if a.GetAtomicNum() == 0),
                       key=lambda a: a.GetAtomMapNum())
        nbrs = [(n.GetIdx(), mol.GetBondBetweenAtoms(target.GetIdx(), n.GetIdx()).GetBondType())
                for n in target.GetNeighbors()]
        if len(stars) != len(nbrs):
            raise ValueError(f'value has {len(stars)} attachment points, atom needs {len(nbrs)}')
        combo = Chem.RWMol(Chem.CombineMols(mol, value))
        offset = mol.GetNumAtoms()
        for (nbr, btype), star in zip(nbrs, stars):
            inner = star.GetNeighbors()[0].GetIdx() + offset
            combo.AddBond(nbr, inner, btype)
        for idx in sorted([s.GetIdx() + offset for s in stars] + [target.GetIdx()], reverse=True):
            combo.RemoveAtom(idx)
        mol = combo


def compile_spec(spec) -> dict:
    """Spec -> {'cxsmiles', 'molblock', 'labels', 'checks'} plus the graph for writers."""
    graph = build_graph(spec)
    cx = to_cxsmiles(graph)
    return {'graph': graph, 'cxsmiles': cx, 'molblock': to_molblock(cx),
            'checks': check_cxsmiles(graph, cx)}


__all__ = ['Graph', 'SpecError', 'build_graph', 'to_cxsmiles', 'check_cxsmiles', 'to_molblock',
           'enumerate_members', 'compile_spec', 'label_runs']
