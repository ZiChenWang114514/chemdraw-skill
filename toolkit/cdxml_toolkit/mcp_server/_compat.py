"""Compatibility helpers for MCP Python SDK 1.x and 2.x."""

from __future__ import annotations

import sys
import types
from typing import Any


SUPPORTED_MCP_MAJORS = {1, 2}


def sdk_version() -> str:
    """Return the installed MCP Python SDK distribution version."""
    import importlib.metadata

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


class RecordedTool:
    """What the tool registry reads from a registered tool."""

    def __init__(self, fn):
        self.name = fn.__name__
        self.fn = fn
        self.description = fn.__doc__ or ""
        self.title = None
        self.annotations = None


class ToolRecorder:
    """Stands in for the MCP server object in a process that only calls tools.

    The command line and the isolated worker need the tool functions, not a
    protocol server; importing the MCP SDK for them costs over a second per process.
    """

    def __init__(self, name, instructions=None, **_settings):
        self.name = name
        self.instructions = instructions
        self._tools = {}
        self._tool_manager = self

    def tool(self, *args, **options):
        if args or options:
            raise TypeError("ToolRecorder registers plain @mcp.tool() functions only")

        def register(fn):
            self._tools[fn.__name__] = RecordedTool(fn)
            return fn

        return register

    def list_tools(self):
        return list(self._tools.values())

    def run(self, *args, **kwargs):
        raise RuntimeError("This process loaded the tools without the MCP server; start the server instead")


_TOOLS_ONLY = False


def tools_only() -> None:
    """Call before the tool modules are imported, in a process that will not serve MCP."""
    global _TOOLS_ONLY
    _TOOLS_ONLY = True


def high_level_server() -> type[Any]:
    """The class the core module builds its `mcp` object from."""
    if _TOOLS_ONLY:
        return ToolRecorder
    install_legacy_fastmcp_alias()
    from mcp.server.fastmcp import FastMCP

    return FastMCP
