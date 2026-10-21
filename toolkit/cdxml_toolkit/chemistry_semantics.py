"""Output-derived chemical identity. Never infer success from drawing metadata."""
from __future__ import annotations

from collections import Counter
from pathlib import Path
from xml.etree import ElementTree as ET
from rdkit import Chem


def semantic_key(mol):
    copy = Chem.Mol(mol)
    for atom in copy.GetAtoms():
        atom.SetAtomMapNum(0)
    copy = Chem.RemoveHs(copy)
    # Canonicalize groups, including the equivalent explicit/implicit ABS case.
    copy = Chem.CanonicalizeStereoGroups(copy)
    return Chem.MolToCXSmiles(copy, Chem.SmilesWriteParams(), Chem.CXSmilesFields.CX_ENHANCEDSTEREO)


def require_supported(mol):
    allowed = {Chem.ChiralType.CHI_UNSPECIFIED, Chem.ChiralType.CHI_TETRAHEDRAL_CW,
               Chem.ChiralType.CHI_TETRAHEDRAL_CCW}
    if any(a.GetChiralTag() not in allowed for a in mol.GetAtoms()):
        raise ValueError('unsupported_stereochemistry: non-tetrahedral center needs a native template')
    if any(a.GetNumRadicalElectrons() for a in mol.GetAtoms()):
        raise ValueError('unsupported_radical: use a verified native template; radical export is not yet validated')
    if any(b.GetStereo() in (Chem.BondStereo.STEREOATROPCW, Chem.BondStereo.STEREOATROPCCW)
           for b in mol.GetBonds()):
        raise ValueError('unsupported_stereochemistry: atropisomer needs a native template')


def read_molecules(value):
    root = ET.parse(str(value)).getroot() if isinstance(value, Path) else ET.fromstring(value)
    # Reaction text IDs are not molecules. Parse each top-level fragment separately.
    parents = {child: parent for parent in root.iter() for child in parent}
    results = []
    for fragment in root.iter('fragment'):
        parent = parents.get(fragment)
        nested = False
        while parent is not None:
            if parent.tag == 'fragment':
                nested = True
                break
            parent = parents.get(parent)
        if nested:
            continue
        block = '<CDXML><page id="90000000">' + ET.tostring(fragment, encoding='unicode') + '</page></CDXML>'
        parsed = Chem.MolsFromCDXML(block)
        if not parsed:
            raise ValueError('unreadable_chemical_fragment: ' + fragment.get('id', '?'))
        results.extend(parsed)
    if not results:
        raise ValueError('no_chemical_fragments')
    return results


def validate_fragment(smiles, xml):
    source = Chem.MolFromSmiles(smiles)
    if source is None:
        raise ValueError('invalid_source_smiles')
    require_supported(source)
    actual = read_molecules('<CDXML><page id="90000000">' + xml + '</page></CDXML>')
    combined = actual[0]
    for mol in actual[1:]:
        combined = Chem.CombineMols(combined, mol)
    expected, observed = semantic_key(source), semantic_key(combined)
    if expected != observed:
        raise ValueError(f'chemical_semantics_changed: source={expected}; roundtrip={observed}')
    return {'status': 'preserved', 'source_cxsmiles': expected,
            'roundtrip_cxsmiles': observed, 'method': 'final_cdxml_roundtrip',
            'stereo_groups': len(source.GetStereoGroups())}


def document_inventory(path):
    return Counter(semantic_key(m) for m in read_molecules(Path(path)))


def validate_document_preserved(source, output):
    before, after = document_inventory(source), document_inventory(output)
    if before != after:
        raise ValueError('chemical_semantics_changed: layout operation changed the molecule inventory')
    return {'status': 'preserved', 'method': 'final_cdxml_roundtrip', 'molecules': sum(after.values())}
