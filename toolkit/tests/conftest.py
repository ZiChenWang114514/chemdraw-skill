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
