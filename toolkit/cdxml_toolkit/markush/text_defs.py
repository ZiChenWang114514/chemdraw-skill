"""Find the claim clauses that define each Markush variable.

The model gets one short passage per variable instead of the whole patent.
Passages are located with patterns, not by a model: ``R1 is``, ``R^1 is``,
``each RB independently``, ``Ring A is`` and ``q is 0, 1 or 2``.  PDF text
loses superscripts, so ``RA`` is also matched as ``R A`` and ``R<sup>A</sup>``.
"""
from __future__ import annotations

import re
from pathlib import Path

_VERB = r'(?:\b(?:is|are|represents?|denotes?|means?|independently|each|selected)\b|=|:)'
_MAX_CHARS = 1200


def load_text(path) -> str:
    path = Path(path)
    if path.suffix.lower() == '.pdf':
        import fitz  # PyMuPDF
        with fitz.open(path) as doc:
            text = '\n'.join(page.get_text() for page in doc)
    else:
        text = path.read_text(encoding='utf-8-sig', errors='replace')
    text = re.sub(r'</?su[bp]>', '', text)
    return re.sub(r'[ \t]+', ' ', text)


def _name_pattern(name: str) -> str:
    """``RA`` -> R, optional space/caret/brace, A; ``L1`` -> L ?1."""
    m = re.match(r'^([A-Za-z])(.*)$', name)
    head, tail = m.group(1), m.group(2)
    if not tail:
        return rf'(?<![A-Za-z0-9]){re.escape(head)}(?![A-Za-z0-9])'
    return rf'(?<![A-Za-z0-9]){re.escape(head)}[\s^{{_]*{re.escape(tail)}\}}?(?![A-Za-z0-9])'


def _clause(text: str, pos: int) -> str:
    """The clause around ``pos``: between the surrounding ``;``, line break or sentence end."""
    stops = re.compile(r';|\n|\.(?=\s+[A-Z(])')
    start = max([m.end() for m in stops.finditer(text, 0, pos)], default=0)
    m = stops.search(text, pos)
    end = m.end() if m else len(text)
    return text[start:min(end, start + _MAX_CHARS // 2)].strip()


def locate(text: str, names, counts=None, rings=()) -> dict[str, str]:
    """``{name: passage}`` for every variable whose definition appears in the text."""
    counts = counts or {}
    found = {}
    for name in names:
        pat = _name_pattern(name)
        if name in rings:
            pat = rf'(?:ring\s+){pat}|{pat}(?=\s+ring)'
        clauses = []
        flags = re.I if name in rings else 0
        for m in re.finditer(rf'({pat})[^;.\n]{{0,50}}?{_VERB}', text, flags):
            piece = _clause(text, m.start())
            if piece and piece not in clauses:
                clauses.append(piece)
            if sum(len(c) for c in clauses) > _MAX_CHARS:
                break
        count = counts.get(name)
        if count:
            m = re.search(rf'(?<![A-Za-z0-9]){re.escape(count)}\s+(?:is|are)\b', text)
            if m and (piece := _clause(text, m.start())) not in clauses:
                clauses.append(piece)
        if clauses:
            found[name] = '\n'.join(clauses)[:_MAX_CHARS]
    return found
