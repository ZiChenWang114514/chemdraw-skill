"""Markush spec (``markush.json``) validation and label markup.

The spec is the source of truth for a generic structure.  Atoms are named by
id (``co1``, ``Z``) or ``fragment:locant`` (``ind:C5``); indices never appear.
Error messages say what to change so a small model can repair its answer.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from .templates import TEMPLATES, locants

ELEMENTS = {'C': 6, 'N': 7, 'O': 8, 'S': 16, 'P': 15, 'F': 9, 'Cl': 17, 'Br': 35, 'I': 53, 'B': 5, 'Si': 14}
ID_RE = re.compile(r'^[A-Za-z][A-Za-z0-9_]*$')
_MARKUP_RE = re.compile(r'([\^_])(\{[^{}]*\}|.)')


def label_runs(label: str) -> list[tuple[str, str]]:
    """``R^{A}`` -> [('R','normal'), ('A','sup')]; ``(R^{B})_{q}`` keeps parentheses."""
    runs, pos = [], 0
    for match in _MARKUP_RE.finditer(label):
        if match.start() > pos:
            runs.append((label[pos:match.start()], 'normal'))
        text = match.group(2)
        text = text[1:-1] if text.startswith('{') else text
        runs.append((text, 'sup' if match.group(1) == '^' else 'sub'))
        pos = match.end()
    if pos < len(label):
        runs.append((label[pos:], 'normal'))
    return [r for r in runs if r[0]]


def plain_label(label: str) -> str:
    """Label text safe for CXSMILES ``$...$`` fields."""
    text = ''.join(t for t, _ in label_runs(label))
    return re.sub(r'[^A-Za-z0-9_]', '', text) or 'R'


def load_spec(spec) -> dict:
    if isinstance(spec, dict):
        return spec
    path = Path(spec).expanduser()
    return json.loads(path.read_text(encoding='utf-8'))


def _bond_parts(bond):
    if isinstance(bond, dict):
        return bond.get('a'), bond.get('b'), bond.get('order', 1), bond.get('display')
    if isinstance(bond, (list, tuple)) and len(bond) in (2, 3):
        return bond[0], bond[1], (bond[2] if len(bond) == 3 else 1), None
    return None, None, None, None


def references(spec: dict) -> dict[str, str]:
    """Every addressable atom reference -> kind ('template', 'atom', 'ring')."""
    refs = {}
    for frag in spec.get('fragments', []):
        if frag.get('template') in TEMPLATES:
            for loc in locants(frag['template']):
                refs[f"{frag.get('id')}:{loc}"] = 'template'
    for atom in spec.get('atoms', []):
        refs[atom.get('id')] = 'ring' if atom.get('kind') == 'variable_ring' else 'atom'
    return refs


def validate_spec(spec) -> list[str]:
    """Return a list of actionable problems; empty means the spec compiles."""
    spec = load_spec(spec)
    errors: list[str] = []
    if spec.get('version') != 1:
        errors.append('Set "version": 1.')
    seen = set()
    for i, frag in enumerate(spec.get('fragments', [])):
        fid, tpl = frag.get('id'), frag.get('template')
        if not fid or not ID_RE.match(str(fid)):
            errors.append(f'fragments[{i}]: "id" must be letters/digits/underscore and start with a letter.')
        elif fid in seen:
            errors.append(f'fragments[{i}]: id {fid!r} is used twice; give each fragment its own id.')
        seen.add(fid)
        if tpl not in TEMPLATES:
            errors.append(f'fragments[{i}] ({fid}): unknown template {tpl!r}. Allowed: {", ".join(sorted(TEMPLATES))}.')
            continue
        valid = locants(tpl)
        tmol = None
        for pair in frag.get('double') or []:
            if not (isinstance(pair, (list, tuple)) and len(pair) == 2 and all(p in valid for p in pair)):
                errors.append(f'fragments[{i}] ({fid}): "double" entries are locant pairs from {", ".join(valid)}; got {pair!r}.')
                continue
            from .templates import template_mol
            tmol = tmol or template_mol(tpl)
            idx = {a.GetProp('locant'): a.GetIdx() for a in tmol.GetAtoms()}
            if tmol.GetBondBetweenAtoms(idx[pair[0]], idx[pair[1]]) is None:
                errors.append(f'fragments[{i}] ({fid}): {pair[0]} and {pair[1]} are not bonded in {tpl}.')
        for loc, label in (frag.get('replace') or {}).items():
            if loc not in valid:
                errors.append(f'fragments[{i}] ({fid}): replace uses locant {loc!r}, but {tpl} has {", ".join(valid)}.')
            if not isinstance(label, str) or not label.strip():
                errors.append(f'fragments[{i}] ({fid}): replace[{loc!r}] must be a label string such as "G^{{1}}".')
    for i, atom in enumerate(spec.get('atoms', [])):
        aid = atom.get('id')
        if not aid or not ID_RE.match(str(aid)):
            errors.append(f'atoms[{i}]: "id" must be letters/digits/underscore and start with a letter (got {aid!r}).')
            continue
        if aid in seen:
            errors.append(f'atoms[{i}]: id {aid!r} is already used; ids must be unique.')
        seen.add(aid)
        has_el, has_label = 'element' in atom, 'label' in atom
        if has_el == has_label:
            errors.append(f'atoms[{i}] ({aid}): give exactly one of "element" (C, N, O, ...) or "label" (R^{{1}}, L, Z, ...).')
        if has_el and atom['element'] not in ELEMENTS:
            errors.append(f'atoms[{i}] ({aid}): element {atom["element"]!r} is not one of {", ".join(ELEMENTS)}.')
        if atom.get('kind') not in (None, 'variable_ring'):
            errors.append(f'atoms[{i}] ({aid}): "kind" may only be "variable_ring".')
    refs = references(spec)
    degree: dict[str, int] = {}
    pairs = set()
    for i, bond in enumerate(spec.get('bonds', [])):
        a, b, order, display = _bond_parts(bond)
        if a is None:
            errors.append(f'bonds[{i}]: write a bond as ["a", "b"] or ["a", "b", 2].')
            continue
        for ref in (a, b):
            if ref not in refs:
                hint = ''
                if isinstance(ref, str) and ':' in ref:
                    fid = ref.split(':')[0]
                    tpl = next((f['template'] for f in spec.get('fragments', []) if f.get('id') == fid), None)
                    if tpl in TEMPLATES:
                        hint = f' {fid} is {tpl} with locants {", ".join(locants(tpl))}.'
                errors.append(f'bonds[{i}]: unknown atom {ref!r}.{hint}')
        if order not in (1, 2, 3):
            errors.append(f'bonds[{i}]: order must be 1, 2 or 3.')
        if display not in (None, 'arc'):
            errors.append(f'bonds[{i}]: "display" may only be "arc".')
        key = frozenset((a, b))
        if a == b:
            errors.append(f'bonds[{i}]: an atom cannot bond to itself ({a}).')
        elif key in pairs:
            errors.append(f'bonds[{i}]: {a}-{b} is listed twice.')
        pairs.add(key)
        degree[a] = degree.get(a, 0) + 1
        degree[b] = degree.get(b, 0) + 1
    for atom in spec.get('atoms', []):
        members = atom.get('members') or []
        for m in members:
            if m not in refs:
                errors.append(f'atoms ({atom.get("id")}): ring member {m!r} is not a known atom.')
        if members and len(members) < 2:
            errors.append(f'atoms ({atom.get("id")}): a variable ring with drawn members needs at least 2 members.')
    for i, group in enumerate(spec.get('variable_position', [])):
        if not group.get('group') or not ID_RE.match(str(group.get('group'))):
            errors.append(f'variable_position[{i}]: "group" must be a plain name like "RB".')
        on = group.get('on') or []
        if not on:
            errors.append(f'variable_position[{i}]: "on" must list the atoms the group may attach to.')
        for ref in on:
            if ref not in refs:
                errors.append(f'variable_position[{i}]: unknown attachment atom {ref!r}.')
        frags = {r.split(':')[0] for r in on if ':' in r}
        if len(frags) > 1:
            errors.append(f'variable_position[{i}]: attachment atoms must be in one ring; got fragments {sorted(frags)}.')
    for i, link in enumerate(spec.get('link_nodes', [])):
        if link.get('atom') not in refs:
            errors.append(f'link_nodes[{i}]: unknown atom {link.get("atom")!r}.')
        lo, hi = link.get('min'), link.get('max')
        if not (isinstance(lo, int) and isinstance(hi, int) and 1 <= lo <= hi):
            errors.append(f'link_nodes[{i}]: need integers 1 <= min <= max.')
    for name, item in (spec.get('definitions') or {}).items():
        if not isinstance(item, dict):
            errors.append(f'definitions[{name!r}]: must be an object with "text" and/or "values".')
    return errors
