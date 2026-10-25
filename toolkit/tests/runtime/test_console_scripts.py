"""Every console script in pyproject.toml must import and expose its main()."""

import importlib
from pathlib import Path

import pytest

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10
    tomllib = pytest.importorskip("tomli")

PYPROJECT = Path(__file__).resolve().parents[2] / "pyproject.toml"
SCRIPTS = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))["project"]["scripts"]


@pytest.mark.parametrize("name", sorted(SCRIPTS))
def test_console_script_entry_point_imports(name):
    module, _, attribute = SCRIPTS[name].partition(":")
    assert callable(getattr(importlib.import_module(module), attribute))
