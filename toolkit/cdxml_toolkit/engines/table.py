"""The engine and bundle tables of the Skill's engines reference, written from the registry.

``cdx.py regen-signatures`` replaces the text between the markers in ``references/engines.md``, so a
size, licence or bundle is stated once, in ``registry.py``.
"""
from __future__ import annotations

import re

from .registry import BUNDLES, ENGINES, disk_mb

MARKERS = {'engines': ('<!-- engines-table:start -->', '<!-- engines-table:end -->'),
           'bundles': ('<!-- bundles-table:start -->', '<!-- bundles-table:end -->')}


def _where(spec: dict) -> str:
    kind = spec['kind']
    if kind == 'remote':
        return 'remote (default)'
    if kind == 'runtime':
        return f'runtime (extra `{spec["extra"]}`)'
    if kind == 'jar':
        return 'Java jar'
    low, high = spec['python']
    versions = f'3.{low}' if low == high else f'3.{low} or 3.{high}' if high == low + 1 else f'3.{low} to 3.{high}'
    return f'own env, Python {versions}' + ('; NVIDIA GPU when present' if spec.get('gpu') else '')


def engines_table() -> str:
    rows = ['| Engine | Task | Where it runs | Licence | Size |', '| --- | --- | --- | --- | --- |']
    for name, spec in ENGINES.items():
        licence = f'**{spec["license"]}**' if spec.get('restricted') else spec['license']
        rows.append(f'| `{name}` | {spec["does"]} | {_where(spec)} | {licence} | {spec.get("size") or "none"} |')
    return '\n'.join(rows)


def bundles_table() -> str:
    rows = ['| Bundle | Engines | For |', '| --- | --- | --- |']
    for name, bundle in BUNDLES.items():
        engines = ', '.join(f'`{engine}`' for engine in bundle['engines'])
        rows.append(f'| `{name}` | {engines} | {bundle["about"]} |')
    return '\n'.join(rows)


SIZE_MARKER = re.compile(r'<!--size:([\w-]+)-->.*?<!--/size-->')


def download_size(bundle: str) -> str:
    """What installing ``bundle`` takes on disk, from the registry's measured engine sizes: ``about 4.7 GB``."""
    if bundle not in BUNDLES:
        raise ValueError(f'the engines reference names the size of {bundle!r}, which is not a bundle')
    megabytes = disk_mb(BUNDLES[bundle]['engines'])
    return f'{megabytes} MB' if megabytes < 1000 else f'about {megabytes / 1000:.1f} GB'


def render(text: str) -> str:
    """``text`` with every marked table replaced by the one the registry gives, and every ``<!--size:BUNDLE-->`` span
    by that bundle's size; a missing marker is an error."""
    text = SIZE_MARKER.sub(lambda m: f'<!--size:{m[1]}-->{download_size(m[1])}<!--/size-->', text)
    for key, body in (('engines', engines_table()), ('bundles', bundles_table())):
        start, end = MARKERS[key]
        pattern = re.compile(re.escape(start) + r'.*?' + re.escape(end), re.S)
        if not pattern.search(text):
            raise ValueError(f'the engines reference has no {start} ... {end} block')
        text = pattern.sub(lambda _: f'{start}\n{body}\n{end}', text, count=1)
    return text
