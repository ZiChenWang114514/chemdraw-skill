"""Heuristic atom-to-atom mapping of a reaction by repeated maximum-common-substructure search.

Heavy atoms only. Each round pairs the product fragment and the reactant fragment that share
the largest connected piece of the not-yet-mapped atoms (elements and connectivity match, bond
orders are ignored while matching); ties are explored within a small budget and the complete
mapping with the fewest unmapped product atoms and then the fewest bond changes is kept. A
single-atom swap test then reports every product atom whose source could be another reactant
atom at the same cost: such atoms are listed as ambiguous instead of being decided silently.

This is a bookkeeping heuristic, not a statement about the mechanism.
"""

from __future__ import annotations

from collections import Counter

from rdkit import Chem
from rdkit.Chem import rdFMCS

MAX_ATOMS = 120
LEAF_BUDGET = 24
BRANCH = 3
MCS_TIMEOUT = 3
ORDER_NAMES = {1.0: 'single', 1.5: 'aromatic', 2.0: 'double', 3.0: 'triple'}
METHOD = ('Heavy atoms are paired by repeated maximum-common-substructure matching (elements and connectivity; '
          'bond orders are ignored while matching) and the pairing with the fewest bond changes is kept. '
          'Hydrogens are not mapped. This is a heuristic bookkeeping aid, not a statement about the mechanism.')


def hill(counts) -> str:
    counts = Counter(counts)
    order = (['C', 'H'] if 'C' in counts else []) + sorted(e for e in counts if e not in ('C', 'H') or 'C' not in counts)
    return ''.join(e + (str(counts[e]) if counts[e] > 1 else '') for e in order)


class _Table:
    """The atoms of a list of molecules under one numbering."""

    def __init__(self, items):
        self.labels = [label for label, _ in items]
        self.mols = [Chem.RemoveHs(mol) for _, mol in items]
        self.offset, self.owner, self.local, self.element, self.klass, self.bonds = [], [], [], [], [], []
        self.hydrogens = []
        total = 0
        for index, mol in enumerate(self.mols):
            self.offset.append(total)
            ranks = list(Chem.CanonicalRankAtoms(mol, breakTies=False))
            key = Chem.MolToSmiles(mol)
            for atom in mol.GetAtoms():
                self.owner.append(index)
                self.local.append(atom.GetIdx())
                self.element.append(atom.GetSymbol())
                self.hydrogens.append(atom.GetTotalNumHs())
                self.klass.append((key, ranks[atom.GetIdx()]))
            for bond in mol.GetBonds():
                self.bonds.append((total + bond.GetBeginAtomIdx(), total + bond.GetEndAtomIdx(), bond.GetBondTypeAsDouble()))
            total += mol.GetNumAtoms()
        self.size = total

    def mapped_locals(self, index, gids):
        return {self.local[g] for g in gids if self.owner[g] == index}


def _remaining(mol, drop):
    rw = Chem.RWMol(mol)
    for atom in rw.GetAtoms():
        atom.SetIntProp('orig', atom.GetIdx())
    for index in sorted(drop, reverse=True):
        rw.RemoveAtom(index)
    sub = rw.GetMol()
    sub.UpdatePropertyCache(strict=False)
    Chem.FastFindRings(sub)
    return sub


def _origin(sub, match):
    return tuple(sub.GetAtomWithIdx(k).GetIntProp('orig') for k in match)


class _Mapper:
    def __init__(self, left, right):
        self.left, self.right = _Table(left), _Table(right)
        self.cache, self.timed_out, self.truncated = {}, False, False

    # --- scoring -------------------------------------------------------------

    def changes(self, p2l, skip_left=(), skip_right=(), limit=None):
        """Bond changes of a mapping as tuples (kind, left atoms, right atoms, order before, order after)."""
        left, right = self.left, self.right
        l2p = {l: p for p, l in p2l.items()}
        out, before = [], {}
        for a, b, order in left.bonds:
            if a in skip_left or b in skip_left:
                continue
            pa, pb = l2p.get(a), l2p.get(b)
            if pa is None and pb is None:
                continue
            if pa is None or pb is None:
                out.append(('broken', (a, b), None, order, None))
                if limit is not None and len(out) > limit:
                    return out
            else:
                before[(min(pa, pb), max(pa, pb))] = (order, a, b)
        seen = set()
        for a, b, order in right.bonds:
            if a in skip_right or b in skip_right:
                continue
            la, lb = p2l.get(a), p2l.get(b)
            if la is None or lb is None:
                continue
            key = (min(a, b), max(a, b))
            seen.add(key)
            old = before.get(key)
            if old is None:
                out.append(('formed', (la, lb), (a, b), None, order))
            elif old[0] != order:
                out.append(('order_changed', (la, lb), (a, b), old[0], order))
            if limit is not None and len(out) > limit:
                return out
        for key, (order, a, b) in before.items():
            if key not in seen:
                out.append(('broken', (a, b), key, order, None))
        return out

    def score(self, p2l, limit=None):
        """(unmapped product atoms, bond changes, hydrogen-count differences of paired atoms); lower is better."""
        changed = len(self.changes(p2l, limit=limit))
        hydrogens = sum(abs(self.right.hydrogens[p] - self.left.hydrogens[l]) for p, l in p2l.items())
        return (self.right.size - len(p2l), changed, hydrogens)

    # --- one round of matching -----------------------------------------------

    def _alignments(self, i, j, p2l, strict):
        right, left = self.right, self.left
        rdrop = right.mapped_locals(i, p2l)
        ldrop = left.mapped_locals(j, p2l.values())
        key = (i, j, strict, frozenset(rdrop), frozenset(ldrop))
        if key in self.cache:
            return self.cache[key]
        rmol, lmol = right.mols[i], left.mols[j]
        found = (0, [])
        if len(rdrop) < rmol.GetNumAtoms() and len(ldrop) < lmol.GetNumAtoms():
            a, b = _remaining(rmol, rdrop), _remaining(lmol, ldrop)
            if {x.GetSymbol() for x in a.GetAtoms()} & {x.GetSymbol() for x in b.GetAtoms()}:
                found = self._match(i, j, a, b, strict)
        self.cache[key] = found
        return found

    def _match(self, i, j, a, b, strict):
        right, left = self.right, self.left
        params = rdFMCS.MCSParameters()
        params.AtomTyper = rdFMCS.AtomCompare.CompareElements
        params.BondTyper = rdFMCS.BondCompare.CompareAny
        params.MaximizeBonds = False
        params.Timeout = MCS_TIMEOUT
        if strict:  # ring atoms pair with ring atoms and rings match whole
            params.AtomCompareParameters.RingMatchesRingOnly = True
            params.BondCompareParameters.RingMatchesRingOnly = True
            params.BondCompareParameters.CompleteRingsOnly = True
        result = rdFMCS.FindMCS([a, b], params)
        if result.canceled:
            self.timed_out = True
        if result.numAtoms == 0:
            return 0, []
        query = Chem.MolFromSmarts(result.smartsString)
        pms = a.GetSubstructMatches(query, uniquify=False, maxMatches=300)
        lms = b.GetSubstructMatches(query, uniquify=False, maxMatches=300)
        qbonds = [(x.GetBeginAtomIdx(), x.GetEndAtomIdx()) for x in query.GetBonds()]
        rmol, lmol = right.mols[i], left.mols[j]
        best = {}
        for pm in pms:
            po = _origin(a, pm)
            for lm in lms:
                lo = _origin(b, lm)
                cost = [0, 0, 0]
                for k1, k2 in qbonds:
                    if (rmol.GetBondBetweenAtoms(po[k1], po[k2]).GetBondTypeAsDouble()
                            != lmol.GetBondBetweenAtoms(lo[k1], lo[k2]).GetBondTypeAsDouble()):
                        cost[0] += 1
                for p, l in zip(po, lo):
                    ra, la = rmol.GetAtomWithIdx(p), lmol.GetAtomWithIdx(l)
                    cost[1] += ra.GetFormalCharge() != la.GetFormalCharge()
                    cost[2] += abs(ra.GetTotalNumHs() - la.GetTotalNumHs())
                pairs = tuple((right.offset[i] + p, left.offset[j] + l) for p, l in zip(po, lo))
                signature = (frozenset((right.klass[p], left.klass[l]) for p, l in pairs),
                             frozenset(p for p, _ in pairs), frozenset(l for _, l in pairs))
                entry = (tuple(cost), pairs)
                if signature not in best or entry < best[signature]:
                    best[signature] = entry
        ranked = sorted(best.values())
        return result.numAtoms, [pairs for cost, pairs in ranked if cost == ranked[0][0]][:BRANCH]

    def _options(self, p2l):
        for strict in (True, False):  # rings stay rings unless nothing else is left to pair
            sized = []
            for i in range(len(self.right.mols)):
                for j in range(len(self.left.mols)):
                    size, alignments = self._alignments(i, j, p2l, strict)
                    if size:
                        sized.append((size, i, j, alignments))
            if sized:
                break
        if not sized:
            return []
        top = max(entry[0] for entry in sized)
        options = []
        for size, i, j, alignments in [entry for entry in sized if entry[0] == top][:BRANCH]:
            options += alignments
        return options

    def solve(self):
        leaves, visited = {}, set()

        def go(p2l):
            if len(leaves) >= LEAF_BUDGET:
                self.truncated = True
                return
            state = frozenset(p2l.items())
            if state in visited:
                return
            visited.add(state)
            options = self._options(p2l)
            if not options:
                leaves[state] = p2l
                return
            for pairs in options:
                go({**p2l, **dict(pairs)})

        go({})
        if not leaves:
            return {}
        return min(leaves.values(), key=lambda m: (*self.score(m), sorted(m.items())))

    # --- ambiguity -----------------------------------------------------------

    def ambiguity(self, p2l):
        """{product atom: [other reactant atoms it could come from at the same cost]}."""
        left, right = self.left, self.right
        base = self.score(p2l)
        owner = {l: p for p, l in p2l.items()}
        found = {}
        for p, l in sorted(p2l.items()):
            seen = {left.klass[l]}
            for l2 in range(left.size):
                if left.element[l2] != right.element[p] or left.klass[l2] in seen:
                    continue
                seen.add(left.klass[l2])
                move = dict(p2l)
                q = owner.get(l2)
                if q is not None:
                    # exchanging two symmetry-equivalent product atoms only renames them
                    if right.element[q] != left.element[l] or right.klass[q] == right.klass[p]:
                        continue
                    move[q] = l
                move[p] = l2
                if self.score(move, limit=base[1]) == base:  # an early exit leaves a larger change count
                    found.setdefault(p, []).append(l2)
        return found


def _where(table, gid):
    return {'species': table.labels[table.owner[gid]], 'element': table.element[gid], 'atom_index': table.local[gid]}


def _unmapped(table, gids):
    by_species = {}
    for g in gids:
        by_species.setdefault(table.owner[g], []).append(table.element[g])
    return [{'species': table.labels[i], 'atoms': atoms, 'formula': hill(atoms)} for i, atoms in sorted(by_species.items())]


def _numbered(table, numbers):
    """Copies of the molecules with atom map numbers from {gid: number}."""
    out = []
    for index, mol in enumerate(table.mols):
        copy = Chem.Mol(mol)
        for atom in copy.GetAtoms():
            atom.SetAtomMapNum(numbers.get(table.offset[index] + atom.GetIdx(), 0))
        out.append(copy)
    return out


def map_atoms(left, right, *, resolve_ambiguity: bool = False) -> dict:
    """Map the heavy atoms of products ``right`` onto reactants ``left`` (lists of (label, mol))."""
    if sum(m.GetNumAtoms() for _, m in left) > MAX_ATOMS or sum(m.GetNumAtoms() for _, m in right) > MAX_ATOMS:
        raise ValueError(f'Atom mapping handles at most {MAX_ATOMS} heavy atoms per side')
    mapper = _Mapper(left, right)
    L, R = mapper.left, mapper.right
    full = mapper.solve()
    alternatives = mapper.ambiguity(full)
    ambiguous, resolved = [], []
    for p, others in sorted(alternatives.items()):
        entry = {'product_atom': R.element[p], 'product_species': R.labels[R.owner[p]], 'atom_index': R.local[p],
                 'candidates': [_where(L, full[p])] + [_where(L, l) for l in others]}
        (resolved if resolve_ambiguity else ambiguous).append(entry)
    final = dict(full)
    if not resolve_ambiguity:
        for p in alternatives:
            del final[p]
    numbers_right, numbers_left = {}, {}
    for number, p in enumerate(sorted(final), 1):
        numbers_right[p], numbers_left[final[p]] = number, number
    skip_left = {l for p in alternatives for l in [full[p]] + alternatives[p]} if not resolve_ambiguity else set()
    skip_right = set(alternatives) if not resolve_ambiguity else set()
    label = lambda g, table, numbers: (f'{table.element[g]}:{numbers[g]}' if g in numbers else table.element[g])
    l2p = {l: p for p, l in final.items()}
    bond_changes = []
    for kind, lefts, rights, before, after in mapper.changes(final, skip_left, skip_right):
        a, b = lefts
        pair = sorted([L.element[a], L.element[b]]) if kind == 'broken' else sorted([L.element[a], L.element[b]])
        names = [label(a, L, numbers_left), label(b, L, numbers_left)]
        bond_changes.append({'type': kind, 'elements': '-'.join(pair), 'atoms': names,
                             **({'from': ORDER_NAMES.get(before, str(before))} if before is not None else {}),
                             **({'to': ORDER_NAMES.get(after, str(after))} if after is not None else {})})
    bond_changes.sort(key=lambda c: (c['type'], c['elements'], c['atoms']))
    no_source = [g for g in range(R.size) if g not in final and g not in alternatives]
    unmapped_left = [g for g in range(L.size) if g not in l2p]
    coverage = [{'species': R.labels[i], 'mapped': sum(1 for g in final if R.owner[g] == i),
                 'atoms': R.mols[i].GetNumAtoms()} for i in range(len(R.mols))]
    warnings = []
    if no_source:
        warnings.append(f"{len(no_source)} product atom(s) have no source atom in the reactants "
                        f"({', '.join(sorted({R.element[g] for g in no_source}))}): the mapping is incomplete; "
                        'a reagent the reaction needs may be missing (try include_agents) or the reaction is not balanced.')
    if ambiguous:
        warnings.append(f'{len(ambiguous)} product atom(s) could come from more than one reactant atom at the same '
                        'cost and were left unmapped; pass resolve_ambiguity to accept the first choice.')
    if resolved:
        warnings.append(f'resolve_ambiguity: {len(resolved)} product atom(s) were assigned by a fixed tie-break among '
                        'equally good sources; treat them as a guess.')
    if mapper.timed_out:
        warnings.append(f'A substructure search stopped after {MCS_TIMEOUT} s; the mapping may be smaller than possible.')
    if mapper.truncated:
        warnings.append('The search for alternative mappings stopped at its limit; the result is the best one found.')
    status = 'incomplete' if no_source else 'ambiguous' if ambiguous else 'complete'
    return {'status': status, 'method': METHOD, 'left_mapped': _numbered(L, numbers_left),
            'right_mapped': _numbered(R, numbers_right), 'map': [
                {'map': numbers_right[p], 'element': R.element[p], 'reactant': _where(L, final[p]), 'product': _where(R, p)}
                for p in sorted(final)],
            'ambiguous': ambiguous, 'resolved_ambiguity': resolved, 'bond_changes': bond_changes,
            'unmapped_reactant_atoms': _unmapped(L, unmapped_left),
            'unmapped_product_atoms': _unmapped(R, no_source), 'product_coverage': coverage,
            'warnings': warnings, 'search': {'alternatives_explored': len(mapper.cache), 'truncated': mapper.truncated}}
