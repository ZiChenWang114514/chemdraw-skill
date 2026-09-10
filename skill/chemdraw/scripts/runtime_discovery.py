"""Compatibility proxy for cdxml_toolkit.mcp_runtime.runtime_discovery."""

from __future__ import annotations

from importlib import import_module as _import_module
import sys as _sys

_runtime = _import_module("cdxml_toolkit.mcp_runtime.runtime_discovery")

if __name__ == "__main__":
    import os as _os
    from pathlib import Path as _Path

    # COM is a Windows capability, not a prerequisite for portable MCP work.
    if _sys.platform != "win32":
        _runtime.REQUIRED_IMPORTS = tuple(
            name for name in _runtime.REQUIRED_IMPORTS if name != "win32com.client"
        )

    # The installed package cannot infer the location of this Skill proxy.
    # Explicit arguments and the user's environment keep their precedence.
    if not _os.environ.get("CHEMDRAW_SKILL_ROOT") and not any(
        arg == "--skill-root" or arg.startswith("--skill-root=")
        for arg in _sys.argv[1:]
    ):
        _sys.argv.extend(["--skill-root", str(_Path(__file__).resolve().parent.parent)])
    _main = getattr(_runtime, "main", None)
    if _main is None:
        raise SystemExit("This compatibility module has no command-line interface.")
    raise SystemExit(_main())
else:
    _sys.modules[__name__] = _runtime
