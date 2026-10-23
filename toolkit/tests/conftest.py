"""Shared pytest fixtures for chem-tools test suite."""

import os
import sys

import pytest

# ---------------------------------------------------------------------------
# Project root — used for test data path resolution.
# The cdxml_toolkit package is installed via pip (no sys.path hack needed).
# ---------------------------------------------------------------------------
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ---------------------------------------------------------------------------
# Test data lives outside the project tree to keep the code directory clean.
# Override with CHEM_TEST_DATA env var if needed.
# ---------------------------------------------------------------------------
TEST_DATA_ROOT = os.environ.get(
    "CHEM_TEST_DATA",
    os.path.join(os.path.dirname(PROJECT_ROOT), "chem-test-data"),
)


# ---------------------------------------------------------------------------
# On macOS the ChemScript-compatible backend drives the user's real ChemDraw,
# restarting it for every name it rejects, and ChemScript-marked suites ran
# for over an hour. Tests see a Mac without ChemDraw unless the run opts in
# with CDXML_LIVE_CHEMDRAW=1: ChemDraw is not found and the toolkit cannot run
# `open` or `osascript`. Tests that fake ChemDraw patch those calls themselves.
# ---------------------------------------------------------------------------
if sys.platform == "darwin" and os.environ.get("CDXML_LIVE_CHEMDRAW") != "1":
    import subprocess as _subprocess
    import types as _types

    from cdxml_toolkit.chemdraw import mac_automation as _mac

    def _no_live_applications(args, *pargs, **kwargs):
        if args and args[0] in ("open", "osascript"):
            raise FileNotFoundError("live ChemDraw is disabled in tests; set CDXML_LIVE_CHEMDRAW=1")
        return _subprocess.run(args, *pargs, **kwargs)

    # A private copy of subprocess, so tests that patch mac_automation.subprocess.run
    # still replace the guarded run and the rest of the process keeps the real one.
    _guarded = _types.ModuleType("subprocess")
    _guarded.__dict__.update(vars(_subprocess))
    _guarded.run = _no_live_applications
    _mac.subprocess = _guarded
    _mac.find_application = lambda *_args, **_kwargs: None


@pytest.fixture
def project_root():
    """Absolute path to the chem-tools project root."""
    return PROJECT_ROOT


@pytest.fixture
def test_data():
    """Absolute path to test data directory (external, sibling to project)."""
    return TEST_DATA_ROOT


@pytest.fixture
def lcms_dir():
    """Absolute path to the KL-7001 LCMS PDF directory."""
    return os.path.join(
        TEST_DATA_ROOT,
        "procedurefilltest",
        "KL-7001-incomplete",
        "LCMS files",
    )


@pytest.fixture
def python_exe():
    """Path to the Python interpreter running the tests."""
    return sys.executable
