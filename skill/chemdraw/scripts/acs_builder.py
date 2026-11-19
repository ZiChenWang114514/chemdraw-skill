"""ACS Document 1996 CDXML writer for exam, lecture and paper figures.

The implementation lives in the toolkit as ``cdxml_toolkit.acs_builder``, so the
registered tool ``build_acs_figure`` works from an installed runtime. This script
keeps ``import acs_builder`` (and ``cdx.py build``) working: importing it gives the
toolkit module itself, with every public name (Fig, Doc, runs, build_from_spec, ...).

Library use:  fig = Fig(); fig.mol('[*:1]CC(=O)O', at=(100, 80), labels={1: 'C10H21'}); fig.write('a.cdxml')
CLI use:      cdx.py build spec.json out.cdxml --render   (spec format: build_from_spec)
"""
import importlib
import importlib.util
import sys
from pathlib import Path


def _load():
    try:
        return importlib.import_module('cdxml_toolkit.acs_builder')
    except ModuleNotFoundError as exc:
        if exc.name != 'cdxml_toolkit.acs_builder':
            raise
    # A source checkout whose runtime predates the module: load it from the checkout's toolkit.
    source = Path(__file__).resolve().parents[3] / 'toolkit' / 'cdxml_toolkit' / 'acs_builder.py'
    if not source.is_file():
        raise ModuleNotFoundError('cdxml_toolkit.acs_builder is missing; rebuild the runtime '
                                  '(scripts/install.py --runtime-only --apply)')
    spec = importlib.util.spec_from_file_location('cdxml_toolkit.acs_builder', source)
    module = importlib.util.module_from_spec(spec)
    sys.modules['cdxml_toolkit.acs_builder'] = module
    spec.loader.exec_module(module)
    return module


sys.modules[__name__] = _load()
