"""Ring and group templates with named locants for Markush specs.

A template is a SMILES whose atom order matches ``locants``.  Specs and small
models refer to atoms as ``fragment:locant`` (``ind:C5``), never by index.
"""
from __future__ import annotations

from functools import lru_cache

from rdkit import Chem
from rdkit.Chem import rdDepictor

TEMPLATES: dict[str, tuple[str, tuple[str, ...]]] = {
    'benzene': ('c1ccccc1', ('1', '2', '3', '4', '5', '6')),
    'pyridine': ('n1ccccc1', ('N1', 'C2', 'C3', 'C4', 'C5', 'C6')),
    'pyrimidine': ('n1cnccc1', ('N1', 'C2', 'N3', 'C4', 'C5', 'C6')),
    'pyrazine': ('n1ccncc1', ('N1', 'C2', 'C3', 'N4', 'C5', 'C6')),
    'pyrrole': ('[nH]1cccc1', ('N1', 'C2', 'C3', 'C4', 'C5')),
    'furan': ('o1cccc1', ('O1', 'C2', 'C3', 'C4', 'C5')),
    'thiophene': ('s1cccc1', ('S1', 'C2', 'C3', 'C4', 'C5')),
    'imidazole': ('[nH]1cncc1', ('N1', 'C2', 'N3', 'C4', 'C5')),
    'pyrazole': ('[nH]1nccc1', ('N1', 'N2', 'C3', 'C4', 'C5')),
    'thiazole': ('s1cncc1', ('S1', 'C2', 'N3', 'C4', 'C5')),
    'oxazole': ('o1cncc1', ('O1', 'C2', 'N3', 'C4', 'C5')),
    'indole': ('[nH]1ccc2ccccc12', ('N1', 'C2', 'C3', 'C3a', 'C4', 'C5', 'C6', 'C7', 'C7a')),
    'indazole': ('[nH]1ncc2ccccc12', ('N1', 'N2', 'C3', 'C3a', 'C4', 'C5', 'C6', 'C7', 'C7a')),
    'benzimidazole': ('[nH]1cnc2ccccc12', ('N1', 'C2', 'N3', 'C3a', 'C4', 'C5', 'C6', 'C7', 'C7a')),
    'naphthalene': ('c1cccc2ccccc12', ('C1', 'C2', 'C3', 'C4', 'C4a', 'C5', 'C6', 'C7', 'C8', 'C8a')),
    'quinoline': ('n1cccc2ccccc12', ('N1', 'C2', 'C3', 'C4', 'C4a', 'C5', 'C6', 'C7', 'C8', 'C8a')),
    'cyclopropane': ('C1CC1', ('1', '2', '3')),
    'cyclobutane': ('C1CCC1', ('1', '2', '3', '4')),
    'cyclopentane': ('C1CCCC1', ('1', '2', '3', '4', '5')),
    'cyclohexane': ('C1CCCCC1', ('1', '2', '3', '4', '5', '6')),
    'pyrrolidine': ('N1CCCC1', ('N1', 'C2', 'C3', 'C4', 'C5')),
    'piperidine': ('N1CCCCC1', ('N1', 'C2', 'C3', 'C4', 'C5', 'C6')),
    'piperazine': ('N1CCNCC1', ('N1', 'C2', 'C3', 'N4', 'C5', 'C6')),
    'morpholine': ('O1CCNCC1', ('O1', 'C2', 'C3', 'N4', 'C5', 'C6')),
    'hexahydropyridazine': ('N1NCCCC1', ('N1', 'N2', 'C3', 'C4', 'C5', 'C6')),
    'carbonyl': ('C=O', ('C', 'O')),
    'carboxyl': ('C(=O)O', ('C', 'O1', 'O2')),
    'sulfonyl': ('S(=O)=O', ('S', 'O1', 'O2')),
}


def template_names() -> list[str]:
    return sorted(TEMPLATES)


@lru_cache(maxsize=None)
def template_mol(name: str) -> Chem.Mol:
    """Kekulized template with 2D coordinates; atom i has locant ``locants[i]``."""
    if name not in TEMPLATES:
        raise ValueError(f'Unknown template {name!r}; choose one of: {", ".join(template_names())}')
    smiles, locants = TEMPLATES[name]
    mol = Chem.MolFromSmiles(smiles)
    if mol.GetNumAtoms() != len(locants):
        raise AssertionError(f'Template {name} has {mol.GetNumAtoms()} atoms but {len(locants)} locants')
    Chem.Kekulize(mol, clearAromaticFlags=True)
    rdDepictor.Compute2DCoords(mol)
    for atom, locant in zip(mol.GetAtoms(), locants):
        atom.SetProp('locant', locant)
    return mol


def locants(name: str) -> tuple[str, ...]:
    template_mol(name)
    return TEMPLATES[name][1]
