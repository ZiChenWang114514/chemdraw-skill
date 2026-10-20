"""Public MCP wrappers for the controlled ChemScript SDK runtime."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any, Optional

from . import artifact_safety
from . import chemscript_sdk_runtime
_RUNTIME = Path(__file__).with_name("chemscript_sdk_runtime.py")
_RUNTIME_TIMEOUT_SECONDS = 180
_RUNTIME_OUTPUT_BYTES = 8 * 1024 * 1024


def _contract(outputs: dict[str, Any], warnings=None, metadata=None) -> dict[str, Any]:
    payload = {
        "ok": True,
        "outputs": outputs,
        "warnings": list(warnings or []),
        "metadata": dict(metadata or {}),
    }
    artifacts = artifact_safety.artifact_records(
        artifact_safety.paths_from_value(outputs)
    )
    if artifacts:
        payload["metadata"]["artifacts"] = artifacts
    return payload


def _runtime_python() -> str:
    explicit = os.environ.get("CHEMSCRIPT_PYTHON")
    config_path = Path(
        os.environ.get("CHEMSCRIPT_CONFIG_PATH") or (Path.home() / ".chemscript_config.json")
    ).expanduser()
    configured = None
    if config_path.is_file():
        try:
            value = json.loads(config_path.read_text(encoding="utf-8"))
            if isinstance(value, dict):
                configured = value.get("python32")
        except (OSError, json.JSONDecodeError):
            configured = None
    candidate = explicit or configured or sys.executable
    path = Path(str(candidate)).expanduser().resolve()
    if not path.is_file():
        raise RuntimeError("Configured ChemScript Python runtime does not exist")
    return str(path)


def _invoke_runtime(request: dict[str, Any]) -> dict[str, Any]:
    payload = json.dumps(request, separators=(",", ":")).encode("utf-8")
    if len(payload) > chemscript_sdk_runtime.MAX_REQUEST_BYTES:
        raise ValueError("ChemScript SDK request exceeds the configured limit")
    with tempfile.TemporaryDirectory(prefix="chemscript-sdk-") as temp_dir:
        request_path = Path(temp_dir) / "request.json"
        response_path = Path(temp_dir) / "response.json"
        request_path.write_bytes(payload)
        try:
            completed = subprocess.run(
                [
                    _runtime_python(),
                    str(_RUNTIME),
                    "--request-file",
                    str(request_path),
                    "--response-file",
                    str(response_path),
                ],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=_RUNTIME_TIMEOUT_SECONDS,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError("ChemScript SDK runtime exceeded its hard timeout") from exc
        if not response_path.is_file():
            raise RuntimeError("ChemScript SDK runtime did not create its response file")
        if response_path.stat().st_size > _RUNTIME_OUTPUT_BYTES:
            raise RuntimeError("ChemScript SDK runtime response exceeded the configured limit")
        try:
            response = json.loads(response_path.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise RuntimeError("ChemScript SDK runtime returned invalid JSON") from exc
    if not isinstance(response, dict) or not isinstance(response.get("ok"), bool):
        raise RuntimeError("ChemScript SDK runtime returned an incomplete response")
    if completed.returncode != 0 or not response["ok"]:
        error = response.get("error") if isinstance(response.get("error"), dict) else {}
        message = str(error.get("message") or "ChemScript SDK execution failed")[:1000]
        raise RuntimeError(message)
    return response


def _catalog_destination(output_path: str) -> Path:
    destination = Path(output_path).expanduser().resolve()
    if destination.suffix.lower() != ".json":
        raise ValueError("output_path must end in .json")
    if destination.exists():
        raise ValueError(f"Refusing to overwrite existing output: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    return destination


def inspect_chemscript_sdk(
    query: Optional[str] = None,
    type_name: Optional[str] = None,
    include_infrastructure: bool = False,
    offset: int = 0,
    limit: int = 100,
    output_path: Optional[str] = None,
) -> dict[str, Any]:
    """Catalog every public ChemScript type/member, with filtering or a complete JSON export."""
    if isinstance(offset, bool) or not isinstance(offset, int) or offset < 0:
        raise ValueError("offset must be a non-negative integer")
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 500:
        raise ValueError("limit must be an integer from 1 through 500")
    destination = _catalog_destination(output_path) if output_path else None
    request = {
        "action": "catalog",
        "query": query,
        "type_name": type_name,
        "include_infrastructure": True if destination else bool(include_infrastructure),
        "offset": 0 if destination else offset,
        "limit": 0 if destination else limit,
    }
    response = _invoke_runtime(request)
    outputs: dict[str, Any] = {
        "assembly": response["assembly"],
        "coverage": response["coverage"],
        "types": response.get("types", []),
        "members": response.get("members", []),
        "page": response.get("page", {}),
    }
    warnings = []
    if response["coverage"].get("interop_infrastructure_members"):
        warnings.append(
            "SWIG pointer and handle members are catalogued separately and require allow_unsafe_interop for execution"
        )
    if destination is not None:
        with tempfile.TemporaryDirectory(prefix=".chemscript-catalog-", dir=destination.parent) as temp_dir:
            staged = Path(temp_dir) / destination.name
            staged.write_text(json.dumps(response, indent=2), encoding="utf-8")
            json.loads(staged.read_text(encoding="utf-8"))
            artifact_safety.publish_file(staged, destination)
        outputs = {
            "assembly": response["assembly"],
            "coverage": response["coverage"],
            "catalog_json": str(destination),
            "page": response.get("page", {}),
        }
    return _contract(
        outputs,
        warnings,
        {
            "network_used": False,
            "read_only": destination is None,
            "catalog_scope": "all public SDK-declared types and members",
        },
    )


def execute_chemscript_sdk(
    program: list[dict[str, Any]],
    allow_file_io: bool = False,
    allow_overwrite: bool = False,
    allow_unsafe_interop: bool = False,
    max_items: int = 100,
) -> dict[str, Any]:
    """Execute a declarative ChemScript SDK program in an isolated Python.NET process."""
    if allow_overwrite and not allow_file_io:
        raise ValueError("allow_overwrite requires allow_file_io")
    normalized = chemscript_sdk_runtime.validate_program(
        program,
        allow_file_io=allow_file_io,
        allow_unsafe_interop=allow_unsafe_interop,
    )
    if isinstance(max_items, bool) or not isinstance(max_items, int) or not 1 <= max_items <= chemscript_sdk_runtime.MAX_ITERATION_ITEMS:
        raise ValueError(
            f"max_items must be an integer from 1 through {chemscript_sdk_runtime.MAX_ITERATION_ITEMS}"
        )
    response = _invoke_runtime(
        {
            "action": "execute",
            "program": normalized,
            "allow_file_io": bool(allow_file_io),
            "allow_overwrite": bool(allow_overwrite),
            "allow_unsafe_interop": bool(allow_unsafe_interop),
            "max_items": max_items,
        }
    )
    warnings = []
    if allow_file_io:
        warnings.append("ChemScript file I/O was explicitly enabled for this program")
    if allow_overwrite:
        warnings.append("Replacing existing ChemScript file outputs was explicitly enabled")
    if allow_unsafe_interop:
        warnings.append("Native pointer/handle interoperability was explicitly enabled inside the isolated process")
    return _contract(
        {
            "assembly": response["assembly"],
            "results": response.get("results", []),
        },
        warnings,
        {
            "steps": len(normalized),
            "disposed_objects": response.get("disposed", 0),
            "network_used": False,
            "file_io_enabled": bool(allow_file_io),
            "overwrite_enabled": bool(allow_overwrite),
            "unsafe_interop_enabled": bool(allow_unsafe_interop),
        },
    )


CHEMSCRIPT_SDK_TOOLS = {
    "inspect_chemscript_sdk": inspect_chemscript_sdk,
    "execute_chemscript_sdk": execute_chemscript_sdk,
}
