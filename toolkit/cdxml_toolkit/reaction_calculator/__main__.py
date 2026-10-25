"""``python -m cdxml_toolkit.reaction_calculator``: open the calculator in a browser (``cdx.py calc``)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .server import CalculatorApp
from .state import build_state, empty_state


def load_state(source: str | None, scale: float, molarity: float | None):
    """State for a reaction SMILES, a .cdxml scheme or a JSON reaction record file; empty without one."""
    if not source:
        return empty_state()
    from cdxml_toolkit.mcp_runtime.report_tools import _reaction_sources, _side
    if '>' in source and not Path(source).exists():
        reaction = source
    elif source.lower().endswith('.cdxml'):
        reaction = {'cdxml': source}
    else:
        reaction = json.loads(Path(source).read_text(encoding='utf-8'))
    sources = _reaction_sources(reaction)
    sides = {role: _side(sources[0][role], role[:-1]) for role in ('reactants', 'agents', 'products')}
    options = {'scale_mmol': scale}
    if molarity:
        options['molarity'] = molarity
    return build_state(sides, options)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog='cdx.py calc', description=__doc__)
    parser.add_argument('reaction', nargs='?', help='reaction SMILES "A.B>agents>P", a .cdxml scheme or a JSON '
                        'file of reactants/agents/products records; omit to start empty and draw in ChemDraw')
    parser.add_argument('--scale', type=float, default=1.0, help='mmol of the limiting reactant (default 1)')
    parser.add_argument('--molarity', type=float, help='mol/L of the limiting reactant in the first solvent (default 0.2)')
    parser.add_argument('--offline', action='store_true', help='never send a name to an online lookup service')
    parser.add_argument('--no-open', action='store_true', help='print the address instead of opening a browser')
    parser.add_argument('--port', type=int, default=0)
    parser.add_argument('--idle', type=float, default=180.0, help='stop this many seconds after the page is closed')
    parser.add_argument('--workdir', help='folder for the ChemDraw canvas files (default: a new temporary folder)')
    ns = parser.parse_args(argv)
    try:
        state = load_state(ns.reaction, ns.scale, ns.molarity)
    except (ValueError, OSError, KeyError) as exc:
        print(json.dumps({'ok': False, 'error': str(exc)}), file=sys.stderr)
        return 2
    CalculatorApp(state, offline=ns.offline, idle_seconds=ns.idle,
                  workdir=Path(ns.workdir) if ns.workdir else None).serve(port=ns.port, open_browser=not ns.no_open)
    return 0


if __name__ == '__main__':
    sys.exit(main())
