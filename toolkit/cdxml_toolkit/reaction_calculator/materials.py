"""Materials tables for a batch of reactions: Markdown, CSV and a printable HTML page.

Pure renderers over the entries ``si_materials_tables`` builds; nothing here calculates chemistry.
"""

from __future__ import annotations

import csv
import html
import io

from . import hazards

COLUMNS = ['reaction', 'material', 'role', 'mw', 'equiv', 'mmol', 'mass_mg', 'volume_ml', 'density_g_ml',
           'limiting', 'assumed', 'theory_mg', 'actual_mg', 'yield_percent', 'hrms', 'bond_changes', 'hazards']
HEAD = ['Material', 'Role', 'MW', 'equiv', 'mmol', 'mass (mg)', 'volume (mL)']


def trim(value, digits: int = 3) -> str:
    """Significant digits without trailing zeros: 1.00 -> 1, 94.2 -> 94.2."""
    if value is None:
        return ''
    text = f'{float(value):.{digits}g}'
    return f'{float(value):.0f}' if 'e' in text else text


def volume_phrase(ml: float) -> str:
    return f'{trim(ml * 1000.0)} µL' if ml < 0.1 else f'{trim(ml)} mL'


def _amount(row: dict) -> str:
    parts = []
    if row.get('volume_ml') is not None:
        parts.append(volume_phrase(row['volume_ml']) + (f" of {trim(row['solution_m'])} M solution" if row.get('solution_m') else ''))
    elif row.get('mass_mg') is not None:
        parts.append(f"{trim(row['mass_mg'])} mg")
    parts.append(f"{trim(row['mmol'])} mmol")
    parts.append(f"{trim(row['equiv'])} equiv")
    return '(' + ', '.join(parts) + ')'


def procedure(rows: list[dict], limiting: str, totals: dict) -> str:
    """One sentence in the usual experimental style, from computed rows."""
    lead = next(r for r in rows if r['id'] == limiting)
    added = [r for r in rows if r['role'] in ('reactant', 'reagent', 'catalyst') and r['id'] != limiting]
    solvents = [r for r in rows if r['role'] == 'solvent' and r.get('volume_ml')]
    medium = ''
    if solvents:
        molar = f", {trim(totals['concentration_m'], 2)} M" if totals.get('concentration_m') else ''
        medium = ' in ' + ' / '.join(f"{s['name']} ({volume_phrase(s['volume_ml'])}{molar if i == 0 else ''})"
                                     for i, s in enumerate(solvents))
    if added:
        text = (f"To a solution of {lead['name']} {_amount(lead)}{medium} was added "
                + ', '.join(f"{r['name']} {_amount(r)}" for r in added) + '.')
    else:
        text = f"{lead['name']} {_amount(lead)}{medium}."
    for product in (r for r in rows if r['role'] == 'product'):
        if product.get('actual_mg') is not None:
            text += (f" Isolated {product['name']}: {trim(product['actual_mg'])} mg "
                     f"({trim(product['yield_percent'])}% of {trim(product['theory_mg'])} mg theoretical).")
        elif product.get('theory_mg') is not None:
            text += (f" Theoretical yield of {product['name']}: {trim(product['theory_mg'])} mg "
                     f"({trim(product['theory_mmol'])} mmol).")
    return text


def _cells(row: dict, limiting: str) -> list[str]:
    role = row['role']
    if role == 'product':
        return [row['name'], 'product (theoretical)', trim(row.get('mw'), 4), '', trim(row.get('theory_mmol')),
                trim(row.get('theory_mg')), '']
    if role == 'solvent':
        return [row['name'], 'solvent', trim(row.get('mw'), 4), '', '', trim(row.get('mass_mg')), trim(row.get('volume_ml'))]
    return [row['name'], role + (' (limiting)' if row['id'] == limiting else ''), trim(row.get('mw'), 4),
            trim(row.get('equiv')), trim(row.get('mmol')), trim(row.get('mass_mg')), trim(row.get('volume_ml'))]


def _footer(entry: dict) -> list[str]:
    lines, totals, product = [], entry['totals'], entry.get('product') or {}
    facts = []
    if totals.get('concentration_m'):
        facts.append(f"concentration {trim(totals['concentration_m'], 2)} M")
    if totals.get('atom_economy_percent') is not None:
        facts.append(f"atom economy {trim(totals['atom_economy_percent'])}%")
    if totals.get('reaction_mass_efficiency_percent') is not None:
        facts.append(f"reaction mass efficiency {trim(totals['reaction_mass_efficiency_percent'])}%")
    if facts:
        lines.append('; '.join(facts).capitalize() + '.')
    if product.get('actual_mg') is not None:
        lines.append(f"Isolated {product['name']}: {trim(product['actual_mg'])} mg, {trim(product['yield_percent'])}% yield.")
    if product.get('hrms'):
        lines.append(product['hrms'] + '.')
    mapping = entry.get('mapping')
    if mapping:
        lines.append(f"Bond changes ({mapping['title']}): {mapping['summary']}.")
    return lines + hazards.lines(entry.get('safety') or [])


def markdown(entries: list[dict]) -> str:
    blocks = []
    for entry in entries:
        lines = [f"### {entry['label']}", '']
        if not entry['ok']:
            blocks.append('\n'.join(lines + [f"Not calculated: {entry['error']}"]))
            continue
        lines += [f"*{entry['title']}*", '', '| ' + ' | '.join(HEAD) + ' |',
                  '| --- | --- | ' + ' | '.join('---:' for _ in HEAD[2:]) + ' |']
        for row in entry['all_rows']:
            lines.append('| ' + ' | '.join(cell.replace('|', '\\|') for cell in _cells(row, entry['limiting'])) + ' |')
        footer = _footer(entry)
        lines += [''] + [line + '  ' for line in footer] + ([''] if footer else []) + ['**Procedure.** ' + entry['procedure']]
        blocks.append('\n'.join(lines))
    return '\n\n'.join(blocks) + '\n'


def csv_text(entries: list[dict]) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=COLUMNS, lineterminator='\n')
    writer.writeheader()
    for entry in entries:
        if not entry['ok']:
            writer.writerow({'reaction': entry['label'], 'material': f"not calculated: {entry['error']}"})
            continue
        safety = {item['id']: item for item in entry.get('safety') or []}
        for row in entry['all_rows']:
            product = row['role'] == 'product'
            writer.writerow({
                'hazards': (hazards.summary(safety[row['id']]) if safety[row['id']]['listed'] else 'not listed')
                if row['id'] in safety else '',
                'reaction': entry['label'], 'material': row['name'], 'role': row['role'], 'mw': trim(row.get('mw'), 4),
                'equiv': '' if product else trim(row.get('equiv')),
                'mmol': trim(row.get('theory_mmol') if product else row.get('mmol')),
                'mass_mg': '' if product else trim(row.get('mass_mg')),
                'volume_ml': '' if product else trim(row.get('volume_ml')),
                'density_g_ml': trim(row.get('density')), 'limiting': 'yes' if row['id'] == entry['limiting'] else '',
                'assumed': 'yes' if row.get('assumed') else '',
                'theory_mg': trim(row.get('theory_mg')) if product else '', 'actual_mg': trim(row.get('actual_mg')) if product else '',
                'yield_percent': trim(row.get('yield_percent')) if product else '',
                'hrms': row.get('hrms') or '' if product else '',
                'bond_changes': (entry.get('mapping') or {}).get('summary', '') if product else ''})
    return buffer.getvalue()


CSS = """
:root{--bg:#fff;--ink:#1d2327;--muted:#667075;--line:#dcdad2;--head:#f1efe8}
@media (prefers-color-scheme:dark){:root{--bg:#14181a;--ink:#e8ecee;--muted:#94a0a6;--line:#2f383c;--head:#1c2124}}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif}
main{max-width:860px;margin:0 auto;padding:24px 16px 48px}
h2{font-size:1.05rem;margin:28px 0 2px}.title{color:var(--muted);margin:0 0 8px;font-style:italic}
table{border-collapse:collapse;width:100%;margin:6px 0;font-size:.9rem}
th,td{border-bottom:1px solid var(--line);padding:4px 8px;text-align:right}
th:first-child,td:first-child,th:nth-child(2),td:nth-child(2){text-align:left}th{background:var(--head)}
p{margin:6px 0}.hrms{font-family:ui-monospace,Consolas,monospace;font-size:.85rem}
@media print{h2{break-after:avoid}table{break-inside:avoid}}
"""


def html_text(entries: list[dict]) -> str:
    esc = html.escape
    out = ['<!doctype html><html lang="en"><head><meta charset="utf-8">',
           '<meta name="viewport" content="width=device-width,initial-scale=1"><title>Materials tables</title>',
           f'<style>{CSS}</style></head><body><main>']
    for entry in entries:
        out.append(f"<h2>{esc(entry['label'])}</h2>")
        if not entry['ok']:
            out.append(f"<p>Not calculated: {esc(entry['error'])}</p>")
            continue
        out.append(f"<p class=\"title\">{esc(entry['title'])}</p><table><thead><tr>"
                   + ''.join(f'<th>{esc(h)}</th>' for h in HEAD) + '</tr></thead><tbody>')
        for row in entry['all_rows']:
            out.append('<tr>' + ''.join(f'<td>{esc(cell)}</td>' for cell in _cells(row, entry['limiting'])) + '</tr>')
        out.append('</tbody></table>')
        for line in _footer(entry):
            tag = '<p class="hrms">' if line.startswith('HRMS') else ('<p class="safety">' if line.startswith('Safety') else '<p>')
            out.append(f'{tag}{esc(line)}</p>')
        out.append(f"<p><b>Procedure.</b> {esc(entry['procedure'])}</p>")
    out.append('</main></body></html>')
    return '\n'.join(out) + '\n'
