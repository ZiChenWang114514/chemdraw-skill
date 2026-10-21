"""Compatibility helpers for MCP Python SDK 1.x and 2.x."""

from __future__ import annotations

import importlib.metadata
import sys
import types
from typing import Any


SUPPORTED_MCP_MAJORS = {1, 2}


def sdk_version() -> str:
    """Return the installed MCP Python SDK distribution version."""
    return importlib.metadata.version("mcp")


def sdk_major(version: str | None = None) -> int:
    """Return a supported MCP SDK major version or raise a clear error."""
    resolved = version or sdk_version()
    try:
        major = int(resolved.split(".", 1)[0])
    except (TypeError, ValueError) as exc:
        raise RuntimeError(f"Cannot parse MCP Python SDK version: {resolved!r}") from exc
    if major not in SUPPORTED_MCP_MAJORS:
        supported = ", ".join(f"{item}.x" for item in sorted(SUPPORTED_MCP_MAJORS))
        raise RuntimeError(
            f"Unsupported MCP Python SDK {resolved}; supported versions: {supported}"
        )
    return major


def server_class() -> type[Any]:
    """Return the high-level server class for the installed SDK."""
    if sdk_major() == 2:
        from mcp.server import MCPServer

        return MCPServer
    from mcp.server.fastmcp import FastMCP

    return FastMCP


def install_legacy_fastmcp_alias() -> None:
    """Provide the removed FastMCP import path when MCP SDK 2.x is installed."""
    if sdk_major() == 1:
        return

    import mcp.server as server_package
    from mcp.server import MCPServer

    module_name = "mcp.server.fastmcp"
    compatibility_module = sys.modules.get(module_name)
    if compatibility_module is None:
        compatibility_module = types.ModuleType(module_name)
        compatibility_module.__doc__ = (
            "Compatibility alias supplied by cdxml-toolkit-community."
        )
        compatibility_module.FastMCP = MCPServer
        sys.modules[module_name] = compatibility_module
    setattr(server_package, "fastmcp", compatibility_module)

