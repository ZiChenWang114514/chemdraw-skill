"""Install the toolkit runtime into the current Python environment.

Source, in order: --toolkit-path; the `toolkit/` folder of the repository checkout this
Skill lives in; otherwise the exact commit pinned in runtime.json (this repository's
`toolkit` subdirectory, fetched by pip).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

SKILL_ROOT = Path(__file__).resolve().parents[1]
BASELINE = SKILL_ROOT / 'runtime.json'
DISTRIBUTION = 'cdxml-toolkit-community'


def _is_toolkit(path: Path) -> bool:
    return (path / 'pyproject.toml').is_file() and (path / 'cdxml_toolkit').is_dir()


def local_toolkit() -> Path | None:
    """`<repo>/toolkit` when this Skill is the `skill/chemdraw` folder of a checkout."""
    candidate = SKILL_ROOT.parent.parent / 'toolkit'
    return candidate.resolve() if SKILL_ROOT.parent.name == 'skill' and _is_toolkit(candidate) else None


def drop_stale_build(source: Path) -> None:
    """Remove setuptools' build/ cache in a local toolkit folder.

    pip builds a local folder in place, and setuptools reuses build/lib: a module deleted from
    the source would come back into the runtime from that cache.
    """
    build = source / 'build'
    if build.is_dir() and not build.is_symlink():
        shutil.rmtree(build)


def requirement(extras: list[str], toolkit_path: str | None = None) -> str:
    if any(not re.fullmatch(r'[a-z][a-z0-9_-]*', extra) for extra in extras):
        raise ValueError('Extras must be package extra names')
    suffix = '[' + ','.join(sorted(set(extras))) + ']' if extras else ''
    if toolkit_path:
        path = Path(toolkit_path).expanduser().resolve()
        if not _is_toolkit(path):
            raise ValueError('Expected a toolkit source folder (pyproject.toml and cdxml_toolkit/)')
        return str(path) + suffix
    local = local_toolkit()
    if local:
        return str(local) + suffix
    baseline = json.loads(BASELINE.read_text(encoding='utf-8'))
    if not re.fullmatch(r'[0-9a-f]{40}', baseline['commit']):
        raise ValueError('Runtime baseline must use a full commit SHA')
    subdirectory = baseline.get('subdirectory')
    fragment = f'#subdirectory={subdirectory}' if subdirectory else ''
    return f"{DISTRIBUTION}{suffix} @ git+{baseline['repository']}@{baseline['commit']}{fragment}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--extras', nargs='*', default=[])
    parser.add_argument('--toolkit-path', help='toolkit source folder to install instead (development)')
    parser.add_argument('--print-requirement', action='store_true', help='Print without installing')
    args = parser.parse_args(argv)
    try:
        selected = requirement(args.extras, args.toolkit_path)
    except (ValueError, KeyError, OSError) as exc:
        parser.error(str(exc))
    print(selected, flush=True)
    if args.print_requirement:
        return 0
    source = Path(args.toolkit_path).expanduser().resolve() if args.toolkit_path else local_toolkit()
    if source:
        drop_stale_build(source)
    return subprocess.run([sys.executable, '-m', 'pip', 'install', selected]).returncode


if __name__ == '__main__':
    raise SystemExit(main())
