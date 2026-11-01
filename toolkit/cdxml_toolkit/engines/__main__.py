"""``python -m cdxml_toolkit.engines`` (``cdx.py engines`` / ``cdx.py install-engines``)."""

from __future__ import annotations

import argparse
import json
import sys

from . import env
from .registry import ENGINES


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog='cdx.py install-engines', description=(
        'Install optional prediction engines, each in its own environment under '
        f'{env.home()} (hundreds of MB to a few GB each, with weights). Nothing is uploaded.'))
    parser.add_argument('engines', nargs='*', metavar='ENGINE', help=f'{", ".join(ENGINES)}')
    parser.add_argument('--task', help='install every local engine of one task (ocsr, retrosynthesis, ...)')
    parser.add_argument('--dry-run', action='store_true', help='print what would be installed')
    parser.add_argument('--status', action='store_true', help='print which engines are available; install nothing')
    ns = parser.parse_args(argv)
    unknown = [name for name in ns.engines if name not in ENGINES]
    if unknown:
        parser.error(f'unknown engine {unknown[0]!r} (choose from {", ".join(ENGINES)})')
    if ns.status:
        print(json.dumps(env.status(), indent=2))
        return 0
    names = list(ns.engines)
    if ns.task:
        names += [n for n, s in ENGINES.items() if s['task'] == ns.task and s['kind'] in ('local', 'jar')]
    if not names:
        parser.error('name at least one engine, or use --task or --status')
    reports = [env.install(name, dry_run=ns.dry_run) for name in dict.fromkeys(names)]
    print(json.dumps({'home': str(env.home()), 'reports': reports}, indent=2))
    return 0 if ns.dry_run or all(r.get('ok') for r in reports) else 1


if __name__ == '__main__':
    sys.exit(main())
