"""Hardened MCP runtime and extended ChemDraw tool collection."""

from __future__ import annotations

from . import temp_compat

# Workers and every staged output create temp folders; make sure a restricted sandbox can write in them.
temp_compat.ensure_usable_mkdtemp()


def build_server(*args, **kwargs):
    """Build the complete MCP server without importing it during package discovery."""
    from .mcp_server import build_server as _build_server

    return _build_server(*args, **kwargs)


__all__ = ["build_server"]
