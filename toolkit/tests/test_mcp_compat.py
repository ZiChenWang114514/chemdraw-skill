"""MCP Python SDK compatibility checks."""

from __future__ import annotations

import importlib

import pytest

from cdxml_toolkit.mcp_server import _compat


@pytest.mark.parametrize(
    ("version", "expected"),
    [("1.9.4", 1), ("2.0.0", 2)],
)
def test_supported_sdk_major(version: str, expected: int) -> None:
    assert _compat.sdk_major(version) == expected


def test_unsupported_sdk_major_has_clear_error() -> None:
    with pytest.raises(RuntimeError, match="supported versions"):
        _compat.sdk_major("3.0.0")


def test_installed_sdk_provides_fastmcp_import() -> None:
    _compat.install_legacy_fastmcp_alias()
    module = importlib.import_module("mcp.server.fastmcp")
    assert module.FastMCP is _compat.server_class()

