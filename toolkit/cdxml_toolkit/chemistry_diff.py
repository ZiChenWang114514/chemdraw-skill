"""Bounded structural comparison with explicit incomplete/ambiguous states."""
import json

from rdkit import Chem
from rdkit.Chem import rdFMCS

# At most this many core mappings (pairs of matches in the two molecules) are
# compared; more than that and the comparison is reported as incomplete.
MAX_CORE_MAPPINGS = 256


def core_mappings(a, b, query, limit: int = MAX_CORE_MAPPINGS):
    """Every mapping of *query* matches in *a* onto those in *b*, or None past *limit*.

    Mappings that pair each atom of *a* with the same symmetry class of *b*
    give the same result and are kept once.
    """
    ma = a.GetSubstructMatches(query, uniquify=False, maxMatches=limit + 1)
    mb = b.GetSubstructMatches(query, uniquify=False, maxMatches=limit + 1)
    if not ma or not mb or len(ma) * len(mb) > limit:
        return None if ma and mb else []
    rank_b = list(Chem.CanonicalRankAtoms(b, breakTies=False))
    seen, mappings = set(), []
    for x in ma:
        for y in mb:
            key = frozenset((i, rank_b[j]) for i, j in zip(x, y))
            if key not in seen:
                seen.add(key)
                mappings.append(dict(zip(x, y)))
    return mappings


def _changes(a, b, mapping):
    """``(atom_changes, bond_changes, stereo_changes)`` of *a* -> *b* under *mapping*."""
    changes = []
    for bond in a.GetBonds():
        i, j = bond.GetBeginAtomIdx(), bond.GetEndAtomIdx()
        other = b.GetBondBetweenAtoms(mapping[i], mapping[j]) if i in mapping and j in mapping else None
        if other is None:
            changes.append({'kind':'removed', 'before_atoms':[i,j]})
        elif bond.GetBondType() != other.GetBondType():
            changes.append({'kind':'order', 'before_atoms':[i,j],
                            'after_atoms':[mapping[i],mapping[j]],
                            'before':str(bond.GetBondType()), 'after':str(other.GetBondType())})
    reverse = {j:i for i,j in mapping.items()}
    atoms = [{'kind':'removed','before_atom':i} for i in range(a.GetNumAtoms()) if i not in mapping]
    atoms += [{'kind':'added','after_atom':j} for j in range(b.GetNumAtoms()) if j not in reverse]
    for i,j in mapping.items():
        x,y=a.GetAtomWithIdx(i),b.GetAtomWithIdx(j)
        for property_name, getter in [('formal_charge','GetFormalCharge'),('isotope','GetIsotope')]:
            old,new=getattr(x,getter)(),getattr(y,getter)()
            if old!=new:
                atoms.append({'kind':property_name,'before_atom':i,'after_atom':j,'before':old,'after':new})
    for bond in b.GetBonds():
        i,j = bond.GetBeginAtomIdx(),bond.GetEndAtomIdx()
        if i not in reverse or j not in reverse or a.GetBondBetweenAtoms(reverse[i],reverse[j]) is None:
            changes.append({'kind':'added', 'after_atoms':[i,j]})
    ca = dict(Chem.FindMolChiralCenters(a, includeUnassigned=True, useLegacyImplementation=False))
    cb = dict(Chem.FindMolChiralCenters(b, includeUnassigned=True, useLegacyImplementation=False))
    stereo = []
    for i,j in mapping.items():
        x,y = ca.get(i,'?'),cb.get(j,'?')
        if x != y:
            stereo.append({'before_atom':i,'after_atom':j,'before_cip':x,'after_cip':y,
                'kind':'added_assignment' if x=='?' else 'lost_assignment' if y=='?' else 'cip_changed'})
    for bond in a.GetBonds():
        i,j=bond.GetBeginAtomIdx(),bond.GetEndAtomIdx()
        other=b.GetBondBetweenAtoms(mapping[i],mapping[j]) if i in mapping and j in mapping else None
        if other is not None and bond.GetStereo()!=other.GetStereo():
            stereo.append({'kind':'bond_stereo_changed','before_atoms':[i,j],
                'after_atoms':[mapping[i],mapping[j]],'before':str(bond.GetStereo()),'after':str(other.GetStereo())})
    return atoms, changes, stereo


def _signature(a, b, outcome):
    """The changes with atom indices replaced by symmetry classes, so symmetric mappings agree."""
    rank_a = list(Chem.CanonicalRankAtoms(a, breakTies=False))
    rank_b = list(Chem.CanonicalRankAtoms(b, breakTies=False))

    def classes(entry):
        out = {}
        for key, value in entry.items():
            if key.startswith('before_atom'):
                value = sorted(rank_a[i] for i in value) if isinstance(value, list) else rank_a[value]
            elif key.startswith('after_atom'):
                value = sorted(rank_b[i] for i in value) if isinstance(value, list) else rank_b[value]
            out[key] = value
        return json.dumps(out, sort_keys=True)

    return tuple(tuple(sorted(classes(e) for e in group)) for group in outcome)


def structural_diff(before: str, after: str, timeout: int = 5) -> dict:
    if type(timeout) is not int or not 1 <= timeout <= 30:
        raise ValueError('timeout must be an integer in 1..30')
    result = dict(status='not_completed', method='rdkit_mcs', reason=None,
                  atom_mapping=None, atom_changes=None, bond_changes=None, stereo_changes=None,
                  mcs_smarts=None)
    a, b = Chem.MolFromSmiles(before), Chem.MolFromSmiles(after)
    if a is None or b is None:
        result['reason'] = 'invalid_structure'
        return result
    if Chem.MolToCXSmiles(a) == Chem.MolToCXSmiles(b):
        result.update(status='completed', method='canonical_identity',
                      atom_changes=[], bond_changes=[], stereo_changes=[])
        return result
    try:
        mcs = rdFMCS.FindMCS([a, b], timeout=timeout, ringMatchesRingOnly=True,
                            completeRingsOnly=True)
        if mcs.canceled:
            result['reason'] = 'mcs_timeout'
            return result
        if not mcs.numAtoms:
            result['reason'] = 'no_common_substructure'
            return result
        result['mcs_smarts'] = mcs.smartsString
        query = Chem.MolFromSmarts(mcs.smartsString)
        mappings = core_mappings(a, b, query)
        if mappings is None:
            result.update(status='partial', reason='too_many_atom_mappings')
            return result
        outcomes = [_changes(a, b, mapping) for mapping in mappings]
        signatures = {_signature(a, b, outcome) for outcome in outcomes}
        result['atom_mappings_considered'] = len(mappings)
        if len(signatures) != 1:
            # Equally valid mappings of the common core describe different
            # changes: report that instead of picking one.
            result.update(status='partial', reason='ambiguous_atom_mapping')
            return result
        mapping = mappings[0]
        atoms, changes, stereo = outcomes[0]
        result['atom_mapping'] = [[i, j] for i, j in mapping.items()]
        result.update(status='completed', atom_changes=atoms, bond_changes=changes, stereo_changes=stereo,
                      stereo_scope='mapped tetrahedral CIP and bond stereo; not proof of spatial inversion')
        if not atoms and not changes and not stereo:
            result.update(status='partial', reason='unclassified_semantic_difference')
    except Exception as exc:
        result.update(status='not_completed', reason='comparison_exception', error_type=type(exc).__name__)
    return result
