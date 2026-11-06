"""Compare what several OCSR engines read from the same image. Never picks a winner on its own."""

from __future__ import annotations

import re

_SUBSCRIPT_MAP = str.maketrans(
    '\u2080\u2081\u2082\u2083\u2084\u2085\u2086\u2087\u2088\u2089\u207a\u207b',
    '0123456789+-',
)


class _RelationResult(str):
    """String relation label that also supports dict-style metadata lookup."""

    def __new__(cls, value: str, meta: dict | None = None):
        obj = super().__new__(cls, value)
        obj._meta = dict(meta or {})
        obj._meta.setdefault('relation', str(value))
        return obj

    def __getitem__(self, key):
        if isinstance(key, str):
            if key in self._meta:
                return self._meta[key]
            raise KeyError(key)
        return super().__getitem__(key)

    def get(self, key: str, default=None):
        return self._meta.get(key, default)

    def to_dict(self) -> dict:
        return dict(self._meta)


def _as_mol(mol_or_smiles):
    from rdkit import Chem, rdBase

    if mol_or_smiles is None:
        return None
    if hasattr(mol_or_smiles, 'GetNumAtoms'):
        return mol_or_smiles
    if isinstance(mol_or_smiles, dict):
        smi = mol_or_smiles.get('canonical') or mol_or_smiles.get('smiles') or ''
    else:
        smi = str(mol_or_smiles)
    if not smi:
        return None
    with rdBase.BlockLogs():
        return Chem.MolFromSmiles(smi)


def _check_abbreviation_skeleton_match(mol_a, mol_b) -> bool:
    """Return True when two OCSR readings share >= 75% of their heavy-atom MCS
    and differ only at a single terminal attachment point.
    """
    from rdkit import Chem, rdBase
    from rdkit.Chem import rdFMCS

    a = _as_mol(mol_a)
    b = _as_mol(mol_b)
    if a is None or b is None:
        return False
    heavy_a = a.GetNumHeavyAtoms()
    heavy_b = b.GetNumHeavyAtoms()
    min_heavy = min(heavy_a, heavy_b)
    if min_heavy < 3:
        return False
    with rdBase.BlockLogs():
        mcs = rdFMCS.FindMCS(
            [a, b],
            atomCompare=rdFMCS.AtomCompare.CompareElements,
            bondCompare=rdFMCS.BondCompare.CompareOrder,
            ringMatchesRingOnly=True,
            completeRingsOnly=True,
            timeout=10,
        )
        if not mcs.numAtoms or not mcs.smartsString:
            return False
        patt = Chem.MolFromSmarts(mcs.smartsString)
        if patt is None:
            return False
        match_a = a.GetSubstructMatch(patt)
        match_b = b.GetSubstructMatch(patt)
    if not match_a or not match_b:
        return False
    mcs_heavy = sum(1 for idx in match_a if a.GetAtomWithIdx(idx).GetAtomicNum() > 1)
    if mcs_heavy / max(1, min_heavy) < 0.75:
        return False

    set_a = set(match_a)
    set_b = set(match_b)
    unmapped_a = set(range(a.GetNumAtoms())) - set_a
    unmapped_b = set(range(b.GetNumAtoms())) - set_b
    if not unmapped_a and not unmapped_b:
        return False

    attach_a = {
        idx
        for idx in set_a
        if any(nb.GetIdx() in unmapped_a for nb in a.GetAtomWithIdx(idx).GetNeighbors())
    }
    attach_b = {
        idx
        for idx in set_b
        if any(nb.GetIdx() in unmapped_b for nb in b.GetAtomWithIdx(idx).GetNeighbors())
    }
    if len(attach_a) > 1 or len(attach_b) > 1:
        return False
    if not attach_a and not attach_b:
        return False
    if attach_a and attach_b:
        a_to_b = dict(zip(match_a, match_b))
        if a_to_b.get(next(iter(attach_a))) != next(iter(attach_b)):
            return False
    # A real chemical difference (H vs Me, OH vs NH2, an extra CH2OH) is not an abbreviation
    # problem: at least one side must carry a label-like atom in its unmapped part.
    return any(_is_label_like(a.GetAtomWithIdx(i)) for i in unmapped_a) or any(
        _is_label_like(b.GetAtomWithIdx(i)) for i in unmapped_b
    )


# Elements an organic drawing uses as written; anything else in an unmatched branch is
# most likely a misread abbreviation label (OTBS read as [Ti], Ph as [P]h ...).
_ORGANIC_ELEMENTS = frozenset({1, 5, 6, 7, 8, 9, 14, 15, 16, 17, 35, 53})


def _is_label_like(atom) -> bool:
    """A dummy/R-group/nickname atom, or an element unusual enough to be a misread label."""
    if atom.GetAtomicNum() == 0:
        return True
    for prop in ('dummyLabel', 'molFileAlias', '_MolFileRLabel', 'atomLabel'):
        if atom.HasProp(prop):
            return True
    return atom.GetAtomicNum() not in _ORGANIC_ELEMENTS


def _chemistry_relation(mol_a, mol_b) -> _RelationResult:
    """Classify the chemical relationship between two OCSR candidate structures."""
    from rdkit import Chem, rdBase

    a = _as_mol(mol_a)
    b = _as_mol(mol_b)
    if a is None or b is None:
        return _RelationResult('Unparseable', {'relation': 'Unparseable'})
    with rdBase.BlockLogs():
        smi_a = Chem.MolToSmiles(a, isomericSmiles=True)
        smi_b = Chem.MolToSmiles(b, isomericSmiles=True)
        if smi_a == smi_b:
            return _RelationResult('ExactMatch', {'relation': 'ExactMatch'})
        flat_a = Chem.MolToSmiles(a, isomericSmiles=False)
        flat_b = Chem.MolToSmiles(b, isomericSmiles=False)
        if flat_a == flat_b:
            return _RelationResult('SameConnectivity', {'relation': 'SameConnectivity'})
    if _check_abbreviation_skeleton_match(a, b):
        return _RelationResult('AbbreviationMismatch', {'relation': 'AbbreviationMismatch'})
    return _RelationResult('DifferentSkeleton', {'relation': 'DifferentSkeleton'})


def _primary(entry: dict) -> dict | None:
    """The first valid structure an engine returned for the image."""
    found = next((s for s in entry.get('structures', []) if s.get('valid')), None)
    if found is not None:
        return found
    if entry.get('smiles'):
        from . import envelope
        desc = envelope.describe(entry['smiles'], entry.get('score'))
        if desc.get('valid'):
            return desc
    return None


def _identity(item: dict) -> str:
    """The full InChIKey, or the canonical SMILES of a structure InChI cannot express (R groups, ``*``)."""
    return item['inchikey'] or item['canonical']


def _skeleton(group: dict) -> str:
    """The connectivity block of the InChIKey; without a key, the structure itself."""
    return group['inchikey'].split('-')[0] if group['inchikey'] else group['canonical']


def _normalize_hill_formula(formula: str | None) -> str:
    """Normalize a molecular formula into standard Hill order for comparison."""
    if not formula:
        return ''
    cleaned = re.sub(r'\s+', '', str(formula).translate(_SUBSCRIPT_MAP))
    if not cleaned:
        return ''
    charge = ''
    charge_match = re.search(r'([+-]\d*|\d+[+-])$', cleaned)
    body = cleaned
    if charge_match:
        raw_charge = charge_match.group(1)
        body = cleaned[:charge_match.start()]
        sign = '+' if '+' in raw_charge else '-'
        mag = raw_charge.replace('+', '').replace('-', '')
        charge = sign if mag in ('', '1') else f'{sign}{mag}'
    tokens = re.findall(r'([A-Z][a-z]?)(\d*)', body)
    if not tokens or ''.join(el + cnt for el, cnt in tokens) != body:
        return cleaned
    counts: dict[str, int] = {}
    for el, cnt in tokens:
        counts[el] = counts.get(el, 0) + (int(cnt) if cnt else 1)
    if 'C' in counts:
        order = ['C'] + (['H'] if 'H' in counts else []) + sorted(k for k in counts if k not in ('C', 'H'))
    else:
        order = sorted(counts)
    hill = ''.join(f'{el}{counts[el] if counts[el] > 1 else ""}' for el in order)
    return hill + charge


def _same_connectivity_notes(ordered: list[dict]) -> list[str]:
    """Explain why groups that share a connectivity block differ (omitted vs inverted stereo, charge, isotopes)."""
    block3 = {
        g['inchikey'].split('-')[2]
        for g in ordered
        if g.get('inchikey') and len(g['inchikey'].split('-')) == 3
    }
    has_protonation = len(block3) > 1
    has_omitted_stereo = False
    has_inverted_stereo = False
    has_isotope = False

    try:
        from rdkit import Chem, rdBase

        with rdBase.BlockLogs():
            mols = [Chem.MolFromSmiles(g['canonical']) if g.get('canonical') else None for g in ordered]
        if all(m is not None for m in mols):
            if len({Chem.GetFormalCharge(m) for m in mols}) > 1:
                has_protonation = True
            iso_sigs = [
                tuple(sorted((a.GetSymbol(), a.GetIsotope()) for a in m.GetAtoms() if a.GetIsotope()))
                for m in mols
            ]
            if len(set(iso_sigs)) > 1:
                has_isotope = True
            spec_counts = [
                sum(1 for s in Chem.FindPotentialStereo(m) if s.specified == Chem.StereoSpecified.Specified)
                for m in mols
            ]
            for i in range(len(mols)):
                for j in range(i + 1, len(mols)):
                    ik_i = (ordered[i].get('inchikey') or '').split('-')
                    ik_j = (ordered[j].get('inchikey') or '').split('-')
                    if len(ik_i) >= 2 and len(ik_j) >= 2 and ik_i[1] == ik_j[1]:
                        continue
                    if iso_sigs[i] != iso_sigs[j]:
                        continue
                    m_i, m_j = mols[i], mols[j]
                    c_i, c_j = spec_counts[i], spec_counts[j]
                    i_matches_j = m_i.HasSubstructMatch(m_j, useChirality=True)
                    j_matches_i = m_j.HasSubstructMatch(m_i, useChirality=True)
                    if c_i != c_j and (i_matches_j or j_matches_i or min(c_i, c_j) == 0):
                        has_omitted_stereo = True
                    elif c_i > 0 and c_j > 0 and not (i_matches_j and j_matches_i):
                        has_inverted_stereo = True
    except Exception:
        pass

    out: list[str] = []
    if has_omitted_stereo:
        out.append(
            'the engines agree on the connectivity and differ by omitted stereochemistry '
            '(unassigned vs specified (R)/(S) or (E)/(Z))'
        )
    if has_inverted_stereo:
        out.append(
            'the engines agree on the connectivity but report inverted stereochemistry '
            '(conflicting (R)/(S) or (E)/(Z) assignments)'
        )
    if has_protonation:
        out.append('the engines agree on the connectivity and differ in protonation or charge state')
    if not out or (has_isotope and not (has_omitted_stereo or has_inverted_stereo or has_protonation)):
        if not out:
            out.append('the engines agree on the connectivity and differ only in stereochemistry or isotopes')
    return out


def _tautomer_notes(ordered: list[dict]) -> list[str]:
    """Check whether groups with different InChIKey connectivity blocks are canonical tautomers."""
    try:
        from rdkit import Chem, rdBase
        from rdkit.Chem.MolStandardize import rdMolStandardize

        with rdBase.BlockLogs():
            enumerator = rdMolStandardize.TautomerEnumerator()
            by_tautomer: dict[str, list[dict]] = {}
            for g in ordered:
                smi = g.get('canonical')
                if not smi or '*' in smi:
                    continue
                mol = Chem.MolFromSmiles(smi)
                if mol is None:
                    continue
                canon_taut = enumerator.Canonicalize(mol)
                if canon_taut is None:
                    continue
                ik = Chem.MolToInchiKey(canon_taut)
                key = ik.split('-')[0] if ik else Chem.MolToSmiles(canon_taut, isomericSmiles=False)
                by_tautomer.setdefault(key, []).append(g)
        notes: list[str] = []
        for taut_list in by_tautomer.values():
            if len({_skeleton(g) for g in taut_list}) > 1:
                summary = ', '.join(f'{g["canonical"]} ({"/".join(g["engines"])})' for g in taut_list)
                notes.append(f'candidates are canonical tautomers of each other: {summary}')
        return notes
    except Exception:
        return []


def compare(entries: list, expected_formula: str | None = None) -> dict:
    """Group the engines by the structure they read.

    ``agreed_smiles`` is set only when at least two engines ran and every engine that produced a valid
    structure produced the same one; even then it is a candidate to check against the image, not a
    result. Any disagreement, an engine without a valid structure, or a single engine leaves it null
    and sets ``needs_review``.
    """
    groups: dict = {}
    silent = []
    for entry in entries:
        if not entry.get('ok'):
            silent.append({'engine': entry.get('engine'), 'reason': entry.get('error', 'failed')})
            continue
        primary = _primary(entry)
        if primary is None:
            silent.append({'engine': entry.get('engine'), 'reason': 'no valid structure'})
            continue
        group = groups.setdefault(_identity(primary), {'inchikey': primary['inchikey'], 'canonical': primary['canonical'],
                                                       'formula': primary['formula'], 'engines': []})
        group['engines'].append(entry['engine'])
    ordered = sorted(groups.values(), key=lambda g: (-len(g['engines']), _identity(g)))
    ran = sum(len(g['engines']) for g in ordered)
    blocks = {_skeleton(g) for g in ordered}
    notes = []
    pairwise_diagnostics = []
    if len(ordered) > 1:
        for i in range(len(ordered)):
            for j in range(i + 1, len(ordered)):
                rel = _chemistry_relation(ordered[i].get('canonical'), ordered[j].get('canonical'))
                pairwise_diagnostics.append({
                    'engines_a': list(ordered[i]['engines']),
                    'engines_b': list(ordered[j]['engines']),
                    'smiles_a': ordered[i].get('canonical'),
                    'smiles_b': ordered[j].get('canonical'),
                    'relation': str(rel),
                })
        if len(blocks) == 1:
            notes.extend(_same_connectivity_notes(ordered))
        else:
            notes.append('the engines read different structures: check each against the image')
            notes.extend(_tautomer_notes(ordered))
            if any(d['relation'] == 'AbbreviationMismatch' for d in pairwise_diagnostics):
                notes.append(
                    'candidates share the main skeleton and differ at a single terminal attachment point '
                    '(likely an abbreviated group vs superatom misread)'
                )
    if expected_formula is not None and str(expected_formula).strip():
        norm_expected = _normalize_hill_formula(expected_formula)
        matching_groups = []
        for g in ordered:
            matches = bool(norm_expected) and _normalize_hill_formula(g.get('formula')) == norm_expected
            g['matches_expected_formula'] = matches
            if matches:
                matching_groups.append(f'{g["canonical"]} ({", ".join(g["engines"])})')
        if matching_groups:
            notes.append(f'matches expected formula {norm_expected}: {"; ".join(matching_groups)}')
        else:
            notes.append(f'no candidate matches expected formula {norm_expected}')
    if silent:
        notes.append('no usable structure from: ' + ', '.join(s['engine'] for s in silent))
    agreed = ordered[0]['canonical'] if len(ordered) == 1 and ran >= 2 else None
    agreed_inchikey = ordered[0]['inchikey'] if agreed is not None else None
    connectivity_match = ran >= 2 and len(blocks) == 1
    if ran < 2:
        notes.append('fewer than two engines produced a structure: nothing to compare')
    return {'agreement': 'single' if ran < 2 else ('all' if len(ordered) == 1 else 'split'),
            'groups': ordered, 'no_result': silent, 'agreed_smiles': agreed,
            'agreed_inchikey': agreed_inchikey, 'connectivity_match': connectivity_match,
            'pairwise_diagnostics': pairwise_diagnostics,
            'selected': None, 'needs_review': agreed is None or bool(silent), 'notes': notes,
            'rule': 'candidates only: compare every structure with the image before using it'}
