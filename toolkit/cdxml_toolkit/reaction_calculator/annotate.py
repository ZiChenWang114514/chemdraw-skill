"""Small CDXML helpers shared by the reaction tools.

``key`` matches structures by connectivity (route steps feeding each other); ``_tag_end``,
``_next_id`` and ``read_fragments_from_text`` let atom-map numbering splice text into a scheme
while keeping its header, DOCTYPE and every existing object untouched.
"""

from __future__ import annotations

import re

from rdkit import Chem

from ..chemistry_semantics import read_fragments


def key(mol_or_smiles) -> str | None:
    mol = Chem.MolFromSmiles(mol_or_smiles) if isinstance(mol_or_smiles, str) else mol_or_smiles
    if mol is None:
        return None
    mol = Chem.RemoveHs(mol)
    mol.RemoveAllConformers()
    return Chem.MolToSmiles(mol, isomericSmiles=False)


def _tag_end(text: str, start: int, name: str) -> int:
    """Index just after the closing tag of the element opened at ``start`` (nesting-aware)."""
    depth = 0
    for match in re.finditer(rf'<(/?){name}\b[^>]*?(/?)>', text[start:]):
        if match.group(1):
            depth -= 1
        elif not match.group(2):
            depth += 1
        if depth == 0:
            return start + match.end()
    raise ValueError(f'Unterminated <{name}> element in the scheme')


def _next_id(text: str) -> int:
    ids = [int(v) for v in re.findall(r'\bid="(\d+)"', text)]
    return max(ids, default=1000) + 1


def read_fragments_from_text(text: str):
    """(id, mol) of each top-level fragment of CDXML text."""
    import tempfile
    from pathlib import Path
    with tempfile.TemporaryDirectory(prefix='cdx-annotate-') as folder:
        target = Path(folder) / 'scheme.cdxml'
        target.write_text(text, encoding='utf-8')
        return read_fragments(target)
