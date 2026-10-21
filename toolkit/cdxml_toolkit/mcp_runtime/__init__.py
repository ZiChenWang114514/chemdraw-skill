"""Hardened MCP runtime and extended ChemDraw tool collection."""

from __future__ import annotations

def build_server(*args, **kwargs):
    """Build the complete MCP server without importing it during package discovery."""
    from .mcp_server import build_server as _build_server

    return _build_server(*args, **kwargs)


__all__ = ["build_server"]
