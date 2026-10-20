"""Content-free runtime identity and capability reporting."""

from __future__ import annotations

import hashlib
import importlib.metadata
import inspect
import json
import os
from pathlib import Path
import sys
from typing import Any


def _distribution(name: str) -> str | None:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None


def _code_digest(root: Path) -> str:
    """Identify loaded Python sources, independent of cache files and install path."""
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*.py"), key=lambda item: item.relative_to(root).as_posix()):
        if "__pycache__" in path.parts:
            continue
        relative = path.relative_to(root).as_posix().encode("utf-8")
        # Normalize checkout newlines so a wheel and its Windows checkout agree.
        content = path.read_text(encoding="utf-8-sig").encode("utf-8")
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        digest.update(hashlib.sha256(content).digest())
    return digest.hexdigest()


def get_toolkit_capabilities(detail: str = "full") -> dict[str, Any]:
    """Return runtime identity and diagnostics; detail='summary' omits tool signatures."""
    from .runtime_diagnostics import diagnose_runtime
    from .tool_registry import build_registry

    if detail not in {"full", "summary"}:
        raise ValueError("detail must be full or summary")
    profile = os.environ.get("CHEMDRAW_MCP_PROFILE", "codex")
    registry = build_registry(profile=profile)
    schema = [
        {
            "name": name,
            "signature": str(inspect.signature(spec.function)),
            "group": spec.group,
            "resource_class": spec.resource_class,
        }
        for name, spec in sorted(registry.items())
    ]
    digest = hashlib.sha256(
        json.dumps(schema, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    diagnostics = diagnose_runtime()
    distributions = {
        "cdxml-toolkit-community": _distribution("cdxml-toolkit-community"),
        "cdxml-toolkit": _distribution("cdxml-toolkit"),
        "mcp": _distribution("mcp"),
    }
    installed_toolkits = [
        name
        for name, version in distributions.items()
        if version and name != "mcp"
    ]
    warnings = list(diagnostics.get("warnings", []))
    import cdxml_toolkit
    runtime_identity = {
        "version": cdxml_toolkit.__version__,
        "code_sha256": _code_digest(Path(cdxml_toolkit.__file__).resolve().parent),
        "digest_scope": "normalized_python_sources",
    }
    installed_version = distributions["cdxml-toolkit-community"]
    if installed_version and installed_version != runtime_identity["version"]:
        warnings.append("Loaded source version differs from installed distribution metadata; reinstall this checkout or wheel.")
    if len(installed_toolkits) > 1:
        warnings.append(
            "Both cdxml-toolkit-community and cdxml-toolkit are installed; remove the legacy distribution."
        )
    result = {
        "ok": True,
        "outputs": {
            "profile": profile,
            "tool_count": len(registry),
            "tool_schema_sha256": digest,
            "tools": schema,
            "distributions": distributions,
            "runtime_identity": runtime_identity,
            "python": {
                "path": str(Path(sys.executable).resolve()),
                "version": sys.version.split()[0],
                "bits": 64 if sys.maxsize > 2**32 else 32,
            },
            "capabilities": diagnostics.get("outputs", {}).get("capabilities", {}),
        },
        "warnings": warnings,
        "metadata": {"content_free": True},
    }
    if detail == "summary":
        result["outputs"].pop("tools")
    return result


SYSTEM_TOOLS = {"get_toolkit_capabilities": get_toolkit_capabilities}
