"""Bounded structural comparison with explicit incomplete/ambiguous states."""
from rdkit import Chem
from rdkit.Chem import rdFMCS


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
        ma = a.GetSubstructMatches(query, uniquify=False, maxMatches=2)
        mb = b.GetSubstructMatches(query, uniquify=False, maxMatches=2)
        if len(ma) != 1 or len(mb) != 1:
            result.update(status='partial', reason='ambiguous_atom_mapping')
            return result
        mapping = dict(zip(ma[0], mb[0]))
        result['atom_mapping'] = [[i, j] for i, j in mapping.items()]
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
        result.update(status='completed', atom_changes=atoms, bond_changes=changes, stereo_changes=stereo,
                      stereo_scope='mapped tetrahedral CIP and bond stereo; not proof of spatial inversion')
        if not atoms and not changes and not stereo:
            result.update(status='partial', reason='unclassified_semantic_difference')
    except Exception as exc:
        result.update(status='not_completed', reason='comparison_exception', error_type=type(exc).__name__)
    return result
