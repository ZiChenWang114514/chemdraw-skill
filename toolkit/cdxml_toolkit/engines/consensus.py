"""Compare what several OCSR engines read from the same image. Never picks a winner on its own."""

from __future__ import annotations


def _primary(entry: dict) -> dict | None:
    """The first valid structure an engine returned for the image."""
    return next((s for s in entry.get('structures', []) if s.get('valid')), None)


def compare(entries: list) -> dict:
    """Group the engines by the structure they read (full InChIKey).

    ``agreed_smiles`` is set only when at least two engines ran and every engine that produced a valid
    structure produced the same one; even then it is a candidate to check against the image, not a
    result. Any disagreement, an engine without a valid structure, or a single engine leaves it null
    and sets ``needs_review``.
    """
    groups: dict = {}
    silent = []
    for entry in entries:
        if not entry.get('ok'):
            silent.append({'engine': entry.get('engine'), 'reason': entry.get('error', 'failed')})
            continue
        primary = _primary(entry)
        if primary is None:
            silent.append({'engine': entry.get('engine'), 'reason': 'no valid structure'})
            continue
        group = groups.setdefault(primary['inchikey'], {'inchikey': primary['inchikey'], 'canonical': primary['canonical'],
                                                        'formula': primary['formula'], 'engines': []})
        group['engines'].append(entry['engine'])
    ordered = sorted(groups.values(), key=lambda g: (-len(g['engines']), g['inchikey']))
    ran = sum(len(g['engines']) for g in ordered)
    notes = []
    if len(ordered) > 1:
        blocks = {g['inchikey'].split('-')[0] for g in ordered}
        if len(blocks) == 1:
            notes.append('the engines agree on the connectivity and differ only in stereochemistry or isotopes')
        else:
            notes.append('the engines read different structures: check each against the image')
    if silent:
        notes.append('no usable structure from: ' + ', '.join(s['engine'] for s in silent))
    agreed = ordered[0]['canonical'] if len(ordered) == 1 and ran >= 2 else None
    if ran < 2:
        notes.append('fewer than two engines produced a structure: nothing to compare')
    return {'agreement': 'single' if ran < 2 else ('all' if len(ordered) == 1 else 'split'),
            'groups': ordered, 'no_result': silent, 'agreed_smiles': agreed, 'selected': None,
            'needs_review': agreed is None or bool(silent), 'notes': notes,
            'rule': 'candidates only: compare every structure with the image before using it'}
