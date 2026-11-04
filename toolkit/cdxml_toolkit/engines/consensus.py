"""Compare what several OCSR engines read from the same image. Never picks a winner on its own."""

from __future__ import annotations

import re

_SUBSCRIPT_MAP = str.maketrans('₀₁₂₃₄₅₆₇₈₉⁺⁻', '01234567₈9+-'.replace('₈', '8'))


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
    if len(ordered) > 1:
        if len(blocks) == 1:
            notes.extend(_same_connectivity_notes(ordered))
        else:
            notes.append('the engines read different structures: check each against the image')
            notes.extend(_tautomer_notes(ordered))
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
            'selected': None, 'needs_review': agreed is None or bool(silent), 'notes': notes,
            'rule': 'candidates only: compare every structure with the image before using it'}
