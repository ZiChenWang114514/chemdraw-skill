"""Write the calculator's amounts into a ChemDraw scheme as text under (or over) each structure.

The scheme file is read with ElementTree to find the top-level structures, matched to calculator
rows by their connectivity, and the new ``<t>`` objects are spliced into the original text so the
file keeps its header, DOCTYPE and every existing object untouched.
"""

from __future__ import annotations

import re
from xml.etree import ElementTree as ET

from rdkit import Chem

from ..chemistry_semantics import read_fragments

SHOW = ('equiv', 'mmol', 'mass', 'volume')
LINE = 11.55          # distance between baselines of 10 pt text
CHAR = 5.4            # average advance of one character
GAP_BELOW, GAP_ABOVE = 14.0, 5.0
CLEAR = 12.0          # baseline distance below a caption that already sits under a structure
CAPTION_REACH = 40.0  # a caption this close under a structure belongs to it (a compound number)


def key(mol_or_smiles) -> str | None:
    mol = Chem.MolFromSmiles(mol_or_smiles) if isinstance(mol_or_smiles, str) else mol_or_smiles
    if mol is None:
        return None
    mol = Chem.RemoveHs(mol)
    mol.RemoveAllConformers()
    return Chem.MolToSmiles(mol, isomericSmiles=False)


def sig(value: float, digits: int = 3) -> str:
    text = f'{value:#.{digits}g}'
    if 'e' in text:
        text = f'{value:.0f}'
    return text.rstrip('.')


def equiv_text(value: float) -> str:
    text = f'{value:.2f}'.rstrip('0')
    return text + '0' if text.endswith('.') else text


def mass_text(mg: float) -> str:
    return f'{sig(mg / 1000.0)} g' if mg >= 1000 else f'{sig(mg)} mg'


def volume_text(ml: float) -> str:
    return f'{sig(ml * 1000.0)} µL' if ml < 0.1 else f'{sig(ml)} mL'


def lines_for(row: dict, limiting: bool, show) -> list[str]:
    """The text lines of one row: amounts for what is added, mass and yield for a product."""
    if row['role'] == 'product':
        out = []
        if row.get('actual_mg') is not None:
            if 'mass' in show:
                out.append(mass_text(row['actual_mg']))
            if row.get('yield_percent') is not None:
                out.append(f"{sig(row['yield_percent'])}% yield")
        elif 'mass' in show and row.get('theory_mg') is not None:
            out.append(f"{mass_text(row['theory_mg'])} theoretical")
        return out
    out = []
    if 'equiv' in show and row.get('equiv') is not None:
        out.append(f"{equiv_text(row['equiv'])} equiv")
    if 'mmol' in show and row.get('mmol') is not None:
        out.append(f"{sig(row['mmol'])} mmol")
    mass = mass_text(row['mass_mg']) if 'mass' in show and row.get('mass_mg') is not None else None
    volume = volume_text(row['volume_ml']) if 'volume' in show and row.get('volume_ml') else None
    return out + [line for line in (mass, volume) if line]


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


def _text_object(ident: int, lines: list[str], cx: float, baseline: float, z: int) -> str:
    width = max(len(line) for line in lines) * CHAR
    box = (cx - width / 2, baseline - 8.9, cx + width / 2, baseline + LINE * (len(lines) - 1) + 2.2)
    runs = '<s font="3" size="10.0" color="0" face="96">' + '&#xA;'.join(_escape(line) for line in lines) + '</s>'
    return (f'<t id="{ident}" p="{cx:.2f} {baseline:.2f}" BoundingBox="{box[0]:.2f} {box[1]:.2f} {box[2]:.2f} {box[3]:.2f}" '
            f'Z="{z}" CaptionJustification="Center" Justification="Center" LineHeight="auto">\n{runs}\n</t>\n')


def _escape(text: str) -> str:
    return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def _label_bottom(captions, x0, x1, y1) -> float:
    """Bottom of the lowest caption directly under a structure (its compound number), else y1."""
    bottom = y1
    for a, b, c, d in captions:
        if a < x1 and x0 < c and y1 - 2 <= b <= y1 + CAPTION_REACH:
            bottom = max(bottom, d)
    return bottom


def annotate(path, rows: list[dict], limiting: str | None, show=SHOW) -> tuple[str, list[str]]:
    """(annotated CDXML text, names of rows that have no structure in the file).

    ``rows`` are computed calculator rows (amounts plus smiles). Solvents and any row whose
    structure is not drawn are returned as unplaced; nothing in the file is changed apart from
    the added text objects.
    """
    show = tuple(show)
    bad = set(show) - set(SHOW)
    if bad:
        raise ValueError(f'scheme_show may contain {list(SHOW)}; got {sorted(bad)}')
    text = path.read_text(encoding='utf-8') if hasattr(path, 'read_text') else str(path)
    root = ET.fromstring(text.encode('utf-8'))
    page = root.find('page')
    if page is None:
        raise ValueError('The file has no page')
    above = set()
    for step in page.iter('step'):
        above.update((step.get('ReactionStepObjectsAboveArrow') or '').split())
    pool: dict[str, list[dict]] = {}
    for row in rows:
        if row.get('smiles') and row['role'] != 'solvent':
            pool.setdefault(key(row['smiles']), []).append(row)
    captions = [tuple(float(v) for v in t.get('BoundingBox').split()) for t in page.findall('t')
                if t.get('BoundingBox')]
    fragments = {ident: mol for ident, mol in read_fragments_from_text(text)}
    placed, additions = set(), []
    ident = _next_id(text)
    z = max([int(v) for v in re.findall(r'\bZ="(\d+)"', text)] or [1000]) + 1
    for fragment in page.findall('fragment'):
        mol = fragments.get(fragment.get('id'))
        candidates = pool.get(key(mol)) if mol is not None else None
        if not candidates:
            continue
        row = candidates.pop(0)
        lines = lines_for(row, row['id'] == limiting, show)
        if not lines:
            placed.add(row['id'])
            continue
        x0, y0, x1, y1 = (float(v) for v in fragment.get('BoundingBox').split())
        cx = (x0 + x1) / 2
        if fragment.get('id') in above:
            baseline = y0 - GAP_ABOVE - LINE * (len(lines) - 1)
        else:
            baseline = max(y1 + GAP_BELOW, _label_bottom(captions, x0, x1, y1) + CLEAR)
        additions.append((fragment.get('id'), _text_object(ident, lines, cx, baseline, z)))
        ident, z = ident + 1, z + 1
        placed.add(row['id'])
    for fragment_id, element in additions:
        start = text.index(f'<fragment id="{fragment_id}"')
        end = _tag_end(text, start, 'fragment')
        text = text[:end] + '\n' + element + text[end:].lstrip('\n')
    unplaced = [row['name'] for row in rows if row['id'] not in placed]
    return text, unplaced


def read_fragments_from_text(text: str):
    """(id, mol) of each top-level fragment of CDXML text."""
    import tempfile
    from pathlib import Path
    with tempfile.TemporaryDirectory(prefix='cdx-annotate-') as folder:
        target = Path(folder) / 'scheme.cdxml'
        target.write_text(text, encoding='utf-8')
        return read_fragments(target)
