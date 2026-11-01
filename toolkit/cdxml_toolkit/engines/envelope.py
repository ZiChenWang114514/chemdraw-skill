"""One result shape for every engine, and the RDKit checks that go with it."""

from __future__ import annotations

PROVENANCE = 'model_prediction'


def describe(smiles: str | None, score=None, **extra) -> dict:
    """A predicted structure: the engine's SMILES plus what RDKit can say about it."""
    item = {'smiles': smiles, 'valid': False, 'canonical': None, 'inchikey': None, 'formula': None}
    if score is not None:
        item['score'] = float(score)
    item.update(extra)
    if not smiles:
        return item
    try:
        from rdkit import Chem, RDLogger
        from rdkit.Chem import rdMolDescriptors
        RDLogger.DisableLog('rdApp.*')
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return item
        item.update(valid=True, canonical=Chem.MolToSmiles(mol), inchikey=Chem.MolToInchiKey(mol),
                    formula=rdMolDescriptors.CalcMolFormula(mol))
    except ImportError:
        pass
    return item


def result(task: str, engine: str, spec: dict, structures=None, **extra) -> dict:
    """The envelope: ``ok`` is true when the engine ran, not when its answer is right."""
    out = {'ok': True, 'task': task, 'engine': engine, 'kind': spec.get('kind'), 'license': spec.get('license'),
           'provenance': PROVENANCE, 'structures': structures or [], 'warnings': []}
    out.update(extra)
    if out['structures'] and not any(s.get('valid') for s in out['structures']):
        out['warnings'].append('none of the predicted SMILES is valid chemistry')
    return out


def failure(task: str, engine: str, spec: dict, error: str, **extra) -> dict:
    return {'ok': False, 'task': task, 'engine': engine, 'kind': spec.get('kind'), 'provenance': PROVENANCE,
            'structures': [], 'warnings': [], 'error': error, **extra}


def molfile_to_smiles(molfile: str) -> str | None:
    from rdkit import Chem, RDLogger
    RDLogger.DisableLog('rdApp.*')
    mol = Chem.MolFromMolBlock(molfile, sanitize=True)
    return Chem.MolToSmiles(mol) if mol is not None else None
