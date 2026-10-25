"""The calculator as one self-contained HTML file: no network, no external scripts or fonts."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from rdkit import Chem
from rdkit.Chem import Descriptors, rdMolDescriptors

from . import library
from .state import plain_json

_HERE = Path(__file__).parent


@lru_cache(maxsize=1)
def _library_payload() -> list[dict]:
    out = []
    for entry in library.entries():
        mol = Chem.MolFromSmiles(entry['smiles'])
        out.append({'name': entry['name'], 'aliases': entry['aliases'], 'role': entry['role'],
                    'density': entry['density'], 'smiles': entry['smiles'],
                    'formula': rdMolDescriptors.CalcMolFormula(mol), 'mw': round(Descriptors.MolWt(mol), 4)})
    return out


def render_page(state: dict, *, token: str | None = None) -> str:
    """HTML for a state; ``token`` switches on the buttons that talk to the local server."""
    template = (_HERE / 'page.html').read_text(encoding='utf-8')
    payload = {'state': state, 'library': _library_payload(), 'api': {'token': token} if token else None}
    parts = {
        '/*STYLE*/': (_HERE / 'calculator.css').read_text(encoding='utf-8'),
        '/*PAYLOAD*/': plain_json(payload),
        '/*ENGINE*/': (_HERE / 'engine.js').read_text(encoding='utf-8'),
        '/*SCRIPT*/': (_HERE / 'calculator.js').read_text(encoding='utf-8'),
    }
    for marker, text in parts.items():
        assert template.count(marker) == 1, marker
        template = template.replace(marker, text)
    return template
