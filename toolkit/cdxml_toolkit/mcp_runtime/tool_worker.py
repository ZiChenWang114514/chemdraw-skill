"""Execute one registered ChemDraw MCP function outside MCP stdio."""

from __future__ import annotations

import asyncio
from contextlib import redirect_stdout
import difflib
import importlib.util
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
# Tools that load the local DECIMER model, a TensorFlow SavedModel.
TENSORFLOW_TOOLS = frozenset({"extract_structures_from_image"})


def _write_envelope(payload: dict) -> None:
    json.dump(payload, sys.stdout, default=str, separators=(",", ":"))
    sys.stdout.write("\n")


def worker_log_dir() -> Path:
    """Folder of ``worker-<id>.log`` files (``cdx.py doctor --paths`` prints it)."""
    base = os.environ.get("LOCALAPPDATA") or os.environ.get("TEMP")
    if not base and sys.platform == "darwin":
        # Not $HOME/chemdraw-skill: that is where the repository is usually cloned.
        return Path.home() / "Library" / "Logs" / "chemdraw-skill"
    return Path(base or Path.home()) / "chemdraw-skill" / "logs"


def _failure_log(exc: BaseException) -> str:
    error_id = uuid.uuid4().hex
    root = worker_log_dir()
    try:
        root.mkdir(parents=True, exist_ok=True)
        (root / f"worker-{error_id}.log").write_text(
            "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)),
            encoding="utf-8",
        )
    except OSError:
        pass
    return error_id


def _import_tensorflow_first(tool_name: str) -> None:
    """Import TensorFlow before RDKit and OpenCV for tools that load a SavedModel.

    With either already loaded, the DECIMER model loads about four times slower
    (65 s instead of 15 s on an arm64 Mac); TensorFlow itself imports in about 2 s.
    """
    if tool_name not in TENSORFLOW_TOOLS or importlib.util.find_spec("tensorflow") is None:
        return
    os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")
    try:
        importlib.import_module("tensorflow")
    except ImportError:
        pass  # The tool reports the missing dependency itself.


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
    if isinstance(exc, FileExistsError) or getattr(exc, "error_code", None) == "output_exists":
        # An existing output was protected. The caller needs the path, and nothing failed.
        return (
            {
                "ok": False,
                "error": {"code": "output_exists", "message": str(exc)[:1000]},
            },
            1,
        )
    error_id = _failure_log(exc)
    error_code = getattr(exc, "error_code", None)
    if error_code is None and isinstance(exc, (ValueError, FileNotFoundError, TypeError)):
        # Bad arguments, missing inputs and missing confirmations: the caller can act on the reason.
        return (
            {
                "ok": False,
                "error": {"code": "invalid_input", "message": str(exc)[:1000], "id": error_id},
            },
            1,
        )
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


def common_path_names(fn) -> dict[str, str]:
    """The common names a caller may use for this tool's file arguments.

    Most tools take `input_path`, `output_path` and `output_dir`. A tool that names its one
    required file argument for its content (`cdxml_path`, `image_path`, `source`) also answers
    to `input_path`; `output_cdxml` answers to `output_path` and `out_dir` to `output_dir`.
    Nothing is offered when the tool has the common name itself or the choice is not unique.
    """
    parameters = inspect.signature(fn).parameters
    if any(p.kind == inspect.Parameter.VAR_KEYWORD for p in parameters.values()):
        return {}

    def sole(names: list[str]) -> str | None:
        return names[0] if len(names) == 1 else None

    candidates = {
        "input_path": sole([
            name for name, parameter in parameters.items()
            if parameter.default is inspect.Parameter.empty and not name.startswith("output")
            and (name in ("path", "source") or name.endswith("_path"))
        ]),
        "output_path": sole([name for name in parameters if name.startswith("output_") and name != "output_dir"]),
        "output_dir": "out_dir" if "out_dir" in parameters else None,
    }
    return {common: own for common, own in candidates.items() if own and common not in parameters}


def _use_common_path_names(fn, call_kwargs: dict) -> None:
    for common, own in common_path_names(fn).items():
        if common in call_kwargs and own not in call_kwargs:
            call_kwargs[own] = call_kwargs.pop(common)


def _bind_or_explain(tool_name: str, fn, call_args: list, call_kwargs: dict) -> None:
    """Validate call signature before execution so TypeError names valid parameters and close matches."""
    sig = inspect.signature(fn)
    try:
        sig.bind(*call_args, **call_kwargs)
    except TypeError as exc:
        valid_names = [
            p.name
            for p in sig.parameters.values()
            if p.kind not in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)
        ]
        has_var_kw = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values())
        hints: list[str] = []
        if not has_var_kw:
            for key in call_kwargs:
                if key not in sig.parameters:
                    matches = difflib.get_close_matches(key, valid_names, n=3, cutoff=0.5)
                    if matches:
                        hints.append(f"Did you mean {matches[0]!r} for {key!r}?")
        params_desc = ", ".join(valid_names) if valid_names else "(none)"
        hint_text = (" " + " ".join(hints)) if hints else ""
        raise TypeError(
            f"{tool_name}: {exc}; valid parameters: {params_desc}.{hint_text} Run `cdx.py sig {tool_name}`."
        ) from None


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
            _import_tensorflow_first(payload["tool"])
            from rdkit import RDLogger

            RDLogger.DisableLog("rdApp.*")
            from cdxml_toolkit.mcp_server import _compat

            _compat.tools_only()
            from .tool_registry import build_registry, load_tool, normalize_profile

            profile = normalize_profile(payload.get("profile"))
            # Profiles filter public exposure, not internal calls between tool implementations.
            # The manifest names the one module this tool needs; without it, load them all.
            known = load_tool(payload["tool"]) if isinstance(payload.get("tool"), str) else None
            registry = {known.name: known} if known is not None else build_registry()
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
        def call(call_args: list, call_kwargs: dict):
            with redirect_stdout(sys.stderr):
                _use_common_path_names(spec.function, call_kwargs)
                _bind_or_explain(tool_name, spec.function, call_args, call_kwargs)
                result = spec.function(*call_args, **call_kwargs)
                if inspect.isawaitable(result):
                    result = asyncio.run(result)
            return _jsonable(result)

        each = payload.get("each")
        if each is not None and (not isinstance(each, list) or not all(isinstance(item, dict) for item in each)):
            raise ValueError("Worker batch must be a list of keyword-argument objects")
        with native_resource_lock(
            spec.resource_class,
            _resource_timeout(timeout_seconds),
        ):
            if each is None:
                result = call(list(payload.get("args", [])), dict(payload.get("kwargs", {})))
            else:
                # The same tool, once per item, in this one process: the imports and any
                # helper server are paid for once. One item failing does not stop the rest.
                result = []
                for call_kwargs in each:
                    try:
                        result.append({"ok": True, "result": call([], dict(call_kwargs))})
                    except Exception as exc:
                        result.append(_error_envelope(exc)[0])
        _write_envelope({"ok": True, "result": result})
        return 0
    except BaseException as exc:
        envelope, return_code = _error_envelope(exc)
        _write_envelope(envelope)
        return return_code


if __name__ == "__main__":
    raise SystemExit(main())
