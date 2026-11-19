"""Choosing the component to draw from a multi-component recognition result.

A recognised SMILES with several dot-separated components (a salt, a
counter-ion, a second molecule, or recognition debris) is drawn as its main
component, but nothing is dropped silently: the full SMILES stays on the
entry and every other component is listed in ``dropped_components`` with a
warning.
"""

from __future__ import annotations

from typing import Dict, List


def _rank(component: str):
    """(heavy atoms, heteroatoms, rings) counted by RDKit; unreadable text ranks last."""
    from rdkit import Chem

    mol = Chem.MolFromSmiles(component)
    if mol is None:
        return (-1, 0, 0)
    hetero = sum(1 for a in mol.GetAtoms() if a.GetAtomicNum() not in (1, 6))
    return (mol.GetNumHeavyAtoms(), hetero, mol.GetRingInfo().NumRings())


def split_components(smiles: str) -> Dict:
    """``{"smiles", "main", "dropped_components", "warning"}`` for a recognised SMILES.

    ``main`` is the component with the most heavy atoms (ties go to more
    heteroatoms, then more rings, then the first one); ``dropped_components``
    lists every other component in input order.
    """
    parts: List[str] = [p.strip() for p in smiles.split(".") if p.strip()]
    if len(parts) <= 1:
        return {"smiles": smiles, "main": parts[0] if parts else smiles,
                "dropped_components": [], "warning": None}
    ranks = [_rank(p) for p in parts]
    best = max(range(len(parts)), key=lambda i: (ranks[i], -i))
    dropped = [p for i, p in enumerate(parts) if i != best]
    warning = (f"Recognised structure has {len(parts)} components; drew {parts[best]} "
               f"and left out {', '.join(dropped)} (full SMILES kept as 'smiles').")
    return {"smiles": smiles, "main": parts[best], "dropped_components": dropped, "warning": warning}


def main_component(entry: Dict, smiles: str) -> str:
    """The component of *smiles* to draw for *entry*; records what was left out on the entry."""
    split = split_components(smiles)
    if split["dropped_components"]:
        entry["dropped_components"] = split["dropped_components"]
        warnings = entry.setdefault("warnings", [])
        if split["warning"] not in warnings:
            warnings.append(split["warning"])
    return split["main"]
