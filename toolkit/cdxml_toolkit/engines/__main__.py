"""``python -m cdxml_toolkit.engines`` (``cdx.py engines`` / ``cdx.py install-engines``)."""

from __future__ import annotations

import argparse
import json
import sys

from . import env
from .registry import BUNDLES, ENGINES, RECOMMEND, RECOMMEND_ALIASES

LOCAL = ('local', 'jar')  # installable here; the rest are remote services


def _command(argv: list[str]) -> str:
    """The `cdx.py` command this run came from: all three share this one parser."""
    if '--remove' in argv:
        return 'cdx.py remove-engines'
    return 'cdx.py engines' if '--recommend' in argv else 'cdx.py install-engines'


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else list(argv)
    parser = argparse.ArgumentParser(prog=_command(argv), description=(
        'Install optional prediction engines, each in its own environment under '
        f'{env.home()} (hundreds of MB to a few GB each, with weights). Nothing is uploaded.'))
    parser.add_argument('engines', nargs='*', metavar='ENGINE', help=f'{", ".join(ENGINES)}')
    tasks = sorted({spec['task'] for spec in ENGINES.values() if spec['kind'] in LOCAL})
    parser.add_argument('--task', help=f'install every local engine of one task: {", ".join(tasks)}')
    parser.add_argument('--bundle', help=f'install a ready-made set: {", ".join(BUNDLES)}')
    parser.add_argument('--dry-run', action='store_true', help='print what would be installed')
    parser.add_argument('--allow-runtime-changes', action='store_true', help='let an engine that installs into the shared '
                        'toolkit runtime add, move or remove packages there (refused otherwise; a failed install is rolled back)')
    parser.add_argument('--recommend', metavar='NEED', help=f'what to install for a need '
                                                           f'({", ".join([*RECOMMEND, *RECOMMEND_ALIASES])}), '
                                                           'with sizes; downloads nothing')
    parser.add_argument('--remove', action='store_true', help='delete the named engines (a dry run unless --yes)')
    parser.add_argument('--yes', action='store_true', help='with --remove: really delete')
    parser.add_argument('--status', action='store_true', help='print which engines are available; install nothing')
    parser.add_argument('--sizes', action='store_true', help='with --status: measure every engine folder again '
                                                             '(slow; otherwise the size recorded at install is shown)')
    ns = parser.parse_args(argv)

    def refuse(message: str) -> None:
        parser.exit(2, f'{parser.prog}: {message}\n')

    unknown = [name for name in ns.engines if name not in ENGINES]
    if unknown:
        refuse(f'unknown engine {unknown[0]!r} (choose from {", ".join(ENGINES)})')
    if ns.bundle and ns.bundle not in BUNDLES:
        refuse(f'unknown bundle {ns.bundle!r} (choose from {", ".join(BUNDLES)})')
    if ns.task and ns.task not in tasks:
        refuse(f'unknown task {ns.task!r} (choose from {", ".join(tasks)})')
    if ns.status:
        print(json.dumps(env.status(sizes=ns.sizes), indent=2))
        return 0
    if ns.recommend:
        try:
            print(json.dumps(env.recommend(ns.recommend), indent=2))
        except ValueError as exc:
            refuse(str(exc))
        return 0
    names = list(ns.engines)
    if ns.bundle:
        names += BUNDLES[ns.bundle]['engines']
    if ns.task:
        names += [n for n, s in ENGINES.items() if s['task'] == ns.task and s['kind'] in LOCAL]
    if not names and ns.remove:
        refuse('name what to delete: cdx.py remove-engines NAME... [--yes]; `cdx.py engines` lists what is installed')
    if not names:
        refuse('name an engine, or use --bundle or --task; '
               f'`cdx.py engines --recommend NEED` says what to install ({", ".join(RECOMMEND)})')
    if ns.remove:
        reports = [env.remove(name, dry_run=not ns.yes) for name in dict.fromkeys(names)]
        print(json.dumps({'home': str(env.home()), 'removed_mb': sum(r['disk_mb'] for r in reports if r.get('removed')),
                          'reports': reports, 'note': None if ns.yes else 'dry run: add --yes to delete'}, indent=2))
        return 0 if all(r.get('ok') for r in reports) else 1
    reports = [env.install(name, dry_run=ns.dry_run, allow_runtime_changes=ns.allow_runtime_changes) for name in dict.fromkeys(names)]
    total = sum(r.get('disk_mb') or 0 for r in reports)
    print(json.dumps({'home': str(env.home()), 'download_mb_estimate': total, 'reports': reports}, indent=2))
    return 0 if ns.dry_run or all(r.get('ok') for r in reports) else 1


if __name__ == '__main__':
    sys.exit(main())
