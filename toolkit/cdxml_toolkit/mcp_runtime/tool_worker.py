"""Execute one registered ChemDraw MCP function outside MCP stdio."""

from __future__ import annotations

import asyncio
from contextlib import redirect_stdout
import inspect
import json
import os
from pathlib import Path
import re
import sys
import traceback
import uuid

from .resource_lock import ResourceBusyError, native_resource_lock


DEFAULT_WORKER_INPUT_BYTES = 16 * 1024 * 1024


def _write_envelope(payload: dict) -> None:
    json.dump(payload, sys.stdout, default=str, separators=(",", ":"))
    sys.stdout.write("\n")


def _failure_log(exc: BaseException) -> str:
    error_id = uuid.uuid4().hex
    root = Path(
        os.environ.get("LOCALAPPDATA")
        or os.environ.get("TEMP")
        or Path.home()
    ) / "Codex" / "chemdraw-mcp" / "logs"
    try:
        root.mkdir(parents=True, exist_ok=True)
        (root / f"worker-{error_id}.log").write_text(
            "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)),
            encoding="utf-8",
        )
    except OSError:
        pass
    return error_id


def _jsonable(value):
    if hasattr(value, "model_dump"):
        value = value.model_dump()
    try:
        json.dumps(value, default=str)
    except (TypeError, ValueError):
        return str(value)
    return value


def _input_limit() -> int:
    raw = os.environ.get("CHEMDRAW_MCP_WORKER_INPUT_BYTES")
    if raw is None:
        return DEFAULT_WORKER_INPUT_BYTES
    value = int(raw)
    if value <= 0:
        raise ValueError("CHEMDRAW_MCP_WORKER_INPUT_BYTES must be positive")
    return value


def _read_payload() -> dict:
    limit = _input_limit()
    arguments = sys.argv[1:]
    if arguments:
        if len(arguments) != 2 or arguments[0] != "--request-file":
            raise ValueError("Worker accepts only --request-file PATH")
        request_path = Path(arguments[1])
        if request_path.stat().st_size > limit:
            raise ValueError("Worker request exceeds the configured input limit")
        request_bytes = request_path.read_bytes()
    else:
        request_bytes = sys.stdin.buffer.read(limit + 1)
    if len(request_bytes) > limit:
        raise ValueError("Worker request exceeds the configured input limit")
    payload = json.loads(request_bytes)
    if not isinstance(payload, dict):
        raise ValueError("Worker request must be a JSON object")
    return payload


def _error_envelope(exc: BaseException) -> tuple[dict, int]:
    if isinstance(exc, ResourceBusyError):
        return (
            {
                "ok": False,
                "error": {
                    "code": "resource_busy",
                    "message": str(exc),
                },
            },
            3,
        )
    error_id = _failure_log(exc)
    error_code = getattr(exc, "error_code", None)
    if isinstance(error_code, str) and re.fullmatch(r"[a-z0-9_]{1,100}", error_code):
        public_message = str(
            getattr(exc, "public_message", None)
            or "Native automation failed; inspect the local diagnostic log"
        )[:1000]
        return (
            {
                "ok": False,
                "error": {
                    "code": error_code,
                    "message": public_message,
                    "id": error_id,
                },
            },
            1,
        )
    return (
        {
            "ok": False,
            "error": {
                "code": "tool_execution_failed",
                "message": "Tool execution failed; inspect the local diagnostic log",
                "id": error_id,
            },
        },
        1,
    )


def _resource_timeout(worker_timeout_seconds: int) -> int:
    return max(1, worker_timeout_seconds - 5)


def main() -> int:
    try:
        payload = _read_payload()
        if not isinstance(payload, dict) or not isinstance(payload.get("tool"), str):
            _write_envelope({
                "ok": False,
                "error": {"code": "invalid_request", "message": "Worker request is invalid"},
            })
            return 2
        with redirect_stdout(sys.stderr):
            from rdkit import RDLogger

            RDLogger.DisableLog("rdApp.*")
            from .tool_registry import build_registry

            profile = payload.get("profile", os.environ.get("CHEMDRAW_MCP_PROFILE", "codex"))
            build_registry(profile=profile)  # Validate the server's selected profile.
            # Profiles filter public exposure, not internal calls between tool implementations.
            registry = build_registry()
            # This worker handles one request; never mutate the parent server's environment.
            os.environ["CHEMDRAW_MCP_PROFILE"] = profile
        tool_name = payload["tool"]
        spec = registry.get(tool_name)
        if spec is None:
            _write_envelope({
                "ok": False,
                "error": {"code": "unknown_tool", "message": "Requested tool is not registered"},
            })
            return 2
        timeout_seconds = payload.get("timeout_seconds", 570)
        if isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, int):
            raise ValueError("Worker timeout must be an integer")
        with native_resource_lock(
            spec.resource_class,
            _resource_timeout(timeout_seconds),
        ):
            with redirect_stdout(sys.stderr):
                result = spec.function(*payload.get("args", []), **payload.get("kwargs", {}))
                if inspect.isawaitable(result):
                    result = asyncio.run(result)
        _write_envelope({"ok": True, "result": _jsonable(result)})
        return 0
    except BaseException as exc:
        envelope, return_code = _error_envelope(exc)
        _write_envelope(envelope)
        return return_code


if __name__ == "__main__":
    raise SystemExit(main())
