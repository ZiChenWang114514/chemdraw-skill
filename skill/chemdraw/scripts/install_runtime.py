"""Install the shared, pinned runtime baseline or an explicit local development checkout."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import subprocess
import sys

BASELINE = Path(__file__).resolve().parents[1] / 'runtime.json'


def requirement(extras: list[str], toolkit_path: str | None = None) -> str:
    if any(not re.fullmatch(r'[a-z][a-z0-9_-]*', extra) for extra in extras):
        raise ValueError('Extras must be package extra names')
    suffix = '[' + ','.join(sorted(set(extras))) + ']' if extras else ''
    if toolkit_path:
        path = Path(toolkit_path).expanduser().resolve()
        if not (path / 'pyproject.toml').is_file() or not (path / 'cdxml_toolkit').is_dir():
            raise ValueError('Expected a cdxml-toolkit source checkout')
        return str(path) + suffix
    baseline = json.loads(BASELINE.read_text(encoding='utf-8'))
    if not re.fullmatch(r'[0-9a-f]{40}', baseline['commit']):
        raise ValueError('Runtime baseline must use a full commit SHA')
    return 'cdxml-toolkit-community' + suffix + ' @ git+' + baseline['repository'] + '@' + baseline['commit']


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--extras', nargs='*', default=[])
    parser.add_argument('--toolkit-path', help='Explicit local checkout for unreleased development')
    parser.add_argument('--print-requirement', action='store_true', help='Print without installing')
    args = parser.parse_args(argv)
    try:
        selected = requirement(args.extras, args.toolkit_path)
    except (ValueError, KeyError, OSError) as exc:
        parser.error(str(exc))
    print(selected, flush=True)
    if args.print_requirement:
        return 0
    return subprocess.run([sys.executable, '-m', 'pip', 'install', selected]).returncode


if __name__ == '__main__':
    raise SystemExit(main())
