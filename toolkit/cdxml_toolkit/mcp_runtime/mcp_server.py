"""Windows-safe MCP launcher with isolated, timeout-bounded workers."""

from __future__ import annotations

import argparse
import asyncio
import contextlib
from contextvars import ContextVar
import functools
import hmac
import inspect
import ipaddress
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import typing
import weakref

from . import mcp_compat
from . import telemetry
mcp_compat.install_legacy_fastmcp_alias()

from cdxml_toolkit.mcp_server import server as upstream

from .process_control import _assign_kill_job, _close_job, _terminate_process_tree
from .tool_registry import DEFAULT_PROFILE, PROFILE_CHOICES, build_registry, normalize_profile


_WORKER_MODULE = "cdxml_toolkit.mcp_runtime.tool_worker"
DEFAULT_WORKER_TIMEOUT_SECONDS = 570
DEFAULT_WORKER_INPUT_BYTES = 16 * 1024 * 1024
DEFAULT_WORKER_OUTPUT_BYTES = 8 * 1024 * 1024
_TIMEOUT_RETURN_CODE = -1001
_CANCELLED_RETURN_CODE = -1002
_OUTPUT_LIMIT_RETURN_CODE = -1003
_NATIVE_LOCKS: weakref.WeakKeyDictionary = weakref.WeakKeyDictionary()
_NATIVE_LOCKS_GUARD = threading.Lock()
_LOOPBACK_HOSTS = {"localhost", "127.0.0.1", "::1"}
_ENVIRONMENT_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")
_CALL_PROFILE: ContextVar[str | None] = ContextVar("chemdraw_profile", default=None)


def _positive_env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be a positive integer") from exc
    if value <= 0:
        raise RuntimeError(f"{name} must be a positive integer")
    return value


def _timeout(value: int | None = None) -> int:
    timeout = value if value is not None else _positive_env_int(
        "CHEMDRAW_MCP_WORKER_TIMEOUT_SECONDS", DEFAULT_WORKER_TIMEOUT_SECONDS
    )
    if timeout <= 0:
        raise RuntimeError("Worker timeout must be positive")
    return timeout


def _worker_environment() -> dict[str, str]:
    exact = {
        "ALL_PROXY", "ALLUSERSPROFILE", "APPDATA",
        "COMMONPROGRAMFILES", "COMMONPROGRAMFILES(X86)", "COMMONPROGRAMW6432",
        "COMPUTERNAME", "COMSPEC", "DRIVERDATA", "HOMEDRIVE", "HOMEPATH",
        "CONDA_PREFIX", "JAVA_HOME", "OPSIN_JAR", "CDXML_TOOLKIT_OPSIN_JAR",
        "HTTP_PROXY", "HTTPS_PROXY", "LOCALAPPDATA", "NO_PROXY", "PATH",
        "NUMBER_OF_PROCESSORS", "OS", "PATHEXT",
        "PROCESSOR_ARCHITECTURE", "PROCESSOR_IDENTIFIER",
        "PROCESSOR_LEVEL", "PROCESSOR_REVISION",
        "PROGRAMDATA", "PROGRAMFILES", "PROGRAMFILES(X86)",
        "PROGRAMW6432", "REQUESTS_CA_BUNDLE", "SSL_CERT_FILE", "SYSTEMROOT",
        "PUBLIC", "SYSTEMDRIVE", "TEMP", "TMP", "USERDOMAIN",
        "USERDOMAIN_ROAMINGPROFILE", "USERNAME", "USERPROFILE", "WINDIR",
        # POSIX user context (macOS): home, per-user temp directory and locale.
        "HOME", "TMPDIR", "USER", "LOGNAME", "LANG", "LC_ALL", "LC_CTYPE",
        "__CF_USER_TEXT_ENCODING",
    }
    prefixes = ("CHEMDRAW_", "CHEMSCRIPT_", "DECIMER_", "TF_")
    credential_markers = ("API_KEY", "TOKEN", "PASSWORD", "SECRET", "CREDENTIAL")
    environment = {}
    for key, value in os.environ.items():
        upper = key.upper()
        if any(marker in upper for marker in credential_markers):
            continue
        if upper in exact or upper.startswith(prefixes):
            environment[key] = value
    environment["PYTHONIOENCODING"] = "utf-8"
    return environment


def _monitor_process(
    process: subprocess.Popen,
    *,
    timeout_seconds: int,
    cancellation: threading.Event,
    stdout_path: Path,
    stderr_path: Path,
    output_limit: int,
) -> str:
    deadline = time.monotonic() + timeout_seconds
    while process.poll() is None:
        if cancellation.is_set():
            return "cancelled"
        if time.monotonic() >= deadline:
            return "timeout"
        for path in (stdout_path, stderr_path):
            try:
                if path.stat().st_size > output_limit:
                    return "output_limit"
            except FileNotFoundError:
                pass
        time.sleep(0.025)
    return "exit"


@contextlib.contextmanager
def _scratch_dir():
    """A temp folder whose removal never fails the call.

    A restricted sandbox can create the folder yet refuse to list or delete it afterwards; the worker
    has already finished by then, so a leftover empty folder is the lesser problem.
    """
    path = tempfile.mkdtemp(prefix="chemdraw-worker-")
    try:
        yield path
    finally:
        try:
            shutil.rmtree(path, ignore_errors=True)
        except OSError:
            pass


def _execute_worker_process(
    payload: bytes,
    *,
    timeout_seconds: int,
    output_limit: int,
    cancellation: threading.Event,
    holder: dict[str, typing.Any],
) -> tuple[int, bytes, bytes]:
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    creationflags |= getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    with _scratch_dir() as temp_dir:
        request_path = Path(temp_dir) / "request.json"
        request_path.write_bytes(payload)
        stdout_path = Path(temp_dir) / "stdout.bin"
        stderr_path = Path(temp_dir) / "stderr.bin"
        with stdout_path.open("wb") as stdout_file, stderr_path.open("wb") as stderr_file:
            process = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    _WORKER_MODULE,
                    "--request-file",
                    str(request_path),
                ],
                stdin=subprocess.DEVNULL,
                stdout=stdout_file,
                stderr=stderr_file,
                env=_worker_environment(),
                creationflags=creationflags,
                # POSIX: its own session, so the whole tree can be signalled together.
                start_new_session=os.name != "nt",
            )
            holder["process"] = process
            job = _assign_kill_job(process)
            holder["job"] = job
            try:
                status = _monitor_process(
                    process,
                    timeout_seconds=timeout_seconds,
                    cancellation=cancellation,
                    stdout_path=stdout_path,
                    stderr_path=stderr_path,
                    output_limit=output_limit,
                )
                if status == "exit":
                    returncode = process.returncode
                else:
                    _terminate_process_tree(process, job)
                    holder["job"] = None
                    returncode = {
                        "timeout": _TIMEOUT_RETURN_CODE,
                        "cancelled": _CANCELLED_RETURN_CODE,
                        "output_limit": _OUTPUT_LIMIT_RETURN_CODE,
                    }[status]
            except BaseException:
                # An interrupted caller (Ctrl+C, cancelled task) must not leave the worker,
                # or the ChemDraw it drives, running without an owner.
                _terminate_process_tree(process, holder.get("job"))
                holder["job"] = None
                raise
            finally:
                holder.pop("process", None)
                _close_job(holder.pop("job", None))
        stdout = stdout_path.read_bytes()[: output_limit + 1]
        stderr = stderr_path.read_bytes()[: output_limit + 1]
    return int(returncode), stdout, stderr


def _safe_message(value: typing.Any) -> str:
    message = str(value or "Tool execution failed")[:1000]
    message = re.sub(r"(?i)(authorization|token|password|secret|api[_-]?key)\s*[:=]\s*\S+", r"\1=<redacted>", message)
    message = re.sub(r"https?://[^\s?#]+[?#]\S+", "<redacted-url>", message)
    return message


_OUT_OF_MEMORY = re.compile(
    r"MemoryError|Unable to allocate|Memory allocation still failed|Insufficient memory"
    r"|out of memory|std::bad_alloc",
    re.IGNORECASE,
)


def _worker_crash(returncode: int, stdout: bytes, stderr: bytes) -> dict[str, str] | None:
    """Explain a worker that died before writing its response envelope."""
    if returncode == 0 or stdout.strip():
        return None
    lines = [line.strip() for line in stderr.decode("utf-8", errors="replace").splitlines() if line.strip()]
    if not lines:
        return {"code": "worker_crashed", "message": f"Worker exited with code {returncode} and no output"}
    if _OUT_OF_MEMORY.search("\n".join(lines[-40:])):
        return {
            "code": "worker_out_of_memory",
            "message": "The worker ran out of memory; close other programs or retry later. "
            + _safe_message(lines[-1])[:300],
        }
    return {"code": "worker_crashed", "message": _safe_message(" | ".join(lines[-3:]))}


def _interpret_worker_result(
    name: str,
    returncode: int,
    stdout: bytes,
    stderr: bytes,
    *,
    timeout: int,
    duration: float,
    output_limit: int,
) -> dict[str, typing.Any]:
    metadata = {"tool": name, "duration_seconds": round(duration, 3)}
    if returncode == _TIMEOUT_RETURN_CODE:
        return {
            "ok": False,
            "error": {"code": "tool_timeout", "message": f"{name} exceeded {timeout} seconds"},
            "metadata": {**metadata, "timeout_seconds": timeout},
        }
    if returncode == _CANCELLED_RETURN_CODE:
        return {
            "ok": False,
            "error": {"code": "tool_cancelled", "message": f"{name} was cancelled"},
            "metadata": metadata,
        }
    if returncode == _OUTPUT_LIMIT_RETURN_CODE or len(stdout) > output_limit or len(stderr) > output_limit:
        return {
            "ok": False,
            "error": {"code": "worker_output_limit", "message": "Worker output exceeded the configured limit"},
            "metadata": {**metadata, "output_limit_bytes": output_limit},
        }
    try:
        envelope = json.loads(stdout.decode("utf-8", errors="strict"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        crash = _worker_crash(returncode, stdout, stderr)
        if crash is not None:
            return {"ok": False, "error": crash, "metadata": {**metadata, "returncode": returncode}}
        return {
            "ok": False,
            "error": {"code": "worker_protocol_error", "message": "Worker returned an invalid response envelope"},
            "metadata": {**metadata, "returncode": returncode},
        }
    if not isinstance(envelope, dict) or not isinstance(envelope.get("ok"), bool):
        return {
            "ok": False,
            "error": {"code": "worker_protocol_error", "message": "Worker response envelope is incomplete"},
            "metadata": {**metadata, "returncode": returncode},
        }
    if returncode == 0 and envelope["ok"]:
        result = envelope.get("result")
        decoded = result
        if isinstance(result, str):
            try:
                decoded = json.loads(result)
            except json.JSONDecodeError:
                pass
        result_dict = decoded if isinstance(decoded, dict) else {}
        outputs = result_dict.get("outputs", result)
        warnings = result_dict.get("warnings", [])
        artifacts = result_dict.get("artifacts", [])
        result_metadata = result_dict.get("metadata", {})
        outcome = {
            "ok": result_dict.get("ok") is not False,
            "result": result,
            "outputs": outputs,
            "warnings": warnings if isinstance(warnings, list) else [str(warnings)],
            "artifacts": artifacts if isinstance(artifacts, list) else [],
            "metadata": {
                **(result_metadata if isinstance(result_metadata, dict) else {}),
                **metadata,
                "duration_ms": round(duration * 1000),
            },
        }
        if not outcome["ok"]:
            error = result_dict.get("error")
            if not error and isinstance(result_dict.get("errors"), list):
                error = "; ".join(str(item) for item in result_dict["errors"])
            details = error if isinstance(error, dict) else {}
            code = details.get("code")
            outcome["error"] = {
                "code": code if isinstance(code, str) and re.fullmatch(r"[a-z0-9_]{1,100}", code) else "tool_business_error",
                "message": _safe_message(details.get("message") if details else error),
            }
        return outcome
    error = envelope.get("error") if isinstance(envelope.get("error"), dict) else {}
    return {
        "ok": False,
        "error": {
            "code": str(error.get("code") or "worker_failed")[:100],
            "message": _safe_message(error.get("message")),
        },
        "metadata": {
            **metadata,
            "returncode": returncode,
            **({"error_id": str(error["id"])} if error.get("id") else {}),
        },
    }


def _run_worker_impl(
    name: str,
    args: list | tuple,
    kwargs: dict,
    *,
    timeout_seconds: int | None = None,
    cancellation: threading.Event | None = None,
    holder: dict[str, typing.Any] | None = None,
) -> dict[str, typing.Any]:
    if timeout_seconds is None:
        spec = build_registry().get(name)
        timeout_seconds = spec.timeout_seconds if spec is not None else None
    timeout = _timeout(timeout_seconds)
    input_limit = _positive_env_int(
        "CHEMDRAW_MCP_WORKER_INPUT_BYTES", DEFAULT_WORKER_INPUT_BYTES
    )
    output_limit = _positive_env_int(
        "CHEMDRAW_MCP_WORKER_OUTPUT_BYTES", DEFAULT_WORKER_OUTPUT_BYTES
    )
    payload = json.dumps({
        "tool": name,
        "args": args,
        "kwargs": kwargs,
        "timeout_seconds": timeout,
        "profile": _CALL_PROFILE.get() or normalize_profile(),
    }).encode("utf-8")
    if len(payload) > input_limit:
        return {
            "ok": False,
            "error": {
                "code": "worker_input_limit",
                "message": "Worker request exceeded the configured input limit",
            },
            "metadata": {
                "tool": name,
                "input_limit_bytes": input_limit,
                "request_bytes": len(payload),
            },
        }
    cancellation = cancellation or threading.Event()
    holder = holder if holder is not None else {}
    started = time.monotonic()
    try:
        returncode, stdout, stderr = _execute_worker_process(
            payload,
            timeout_seconds=timeout,
            output_limit=output_limit,
            cancellation=cancellation,
            holder=holder,
        )
    except OSError as error:
        reason = error.strerror or type(error).__name__
        return {
            "ok": False,
            "error": {"code": "worker_launch_failed", "message": f"Could not launch the isolated worker: {reason}"},
            "metadata": {"tool": name, "timeout_seconds": timeout},
        }
    return _interpret_worker_result(
        name,
        returncode,
        stdout,
        stderr,
        timeout=timeout,
        duration=time.monotonic() - started,
        output_limit=output_limit,
    )


def _run_worker(
    name: str,
    args: list | tuple,
    kwargs: dict,
    *,
    timeout_seconds: int | None = None,
) -> dict[str, typing.Any]:
    return _run_worker_impl(name, args, kwargs, timeout_seconds=timeout_seconds)


def _native_async_lock() -> asyncio.Lock:
    loop = asyncio.get_running_loop()
    with _NATIVE_LOCKS_GUARD:
        lock = _NATIVE_LOCKS.get(loop)
        if lock is None:
            lock = asyncio.Lock()
            _NATIVE_LOCKS[loop] = lock
        return lock


async def _run_worker_async_unlocked(
    name: str,
    args: list | tuple,
    kwargs: dict,
    *,
    timeout_seconds: int | None = None,
) -> dict[str, typing.Any]:
    cancellation = threading.Event()
    holder: dict[str, typing.Any] = {}
    task = asyncio.create_task(
        asyncio.to_thread(
            _run_worker_impl,
            name,
            args,
            kwargs,
            timeout_seconds=timeout_seconds,
            cancellation=cancellation,
            holder=holder,
        )
    )
    try:
        return await asyncio.shield(task)
    except asyncio.CancelledError:
        cancellation.set()
        process = holder.get("process")
        if process is not None:
            _terminate_process_tree(process, holder.get("job"))
            holder["job"] = None
        try:
            await asyncio.wait_for(asyncio.shield(task), timeout=5)
        except (asyncio.TimeoutError, asyncio.CancelledError):
            pass
        raise


async def _run_worker_async(
    name: str,
    args: list | tuple,
    kwargs: dict,
    *,
    timeout_seconds: int | None = None,
    resource_class: str | None = None,
) -> dict[str, typing.Any]:
    """Run one worker and update content-free process telemetry."""
    started = time.monotonic()
    outcome: dict[str, typing.Any] | None = None
    error_code: str | None = None
    telemetry.worker_started(name)
    waiting = False
    try:
        if resource_class == "chemdraw_com":
            telemetry.native_wait_started()
            waiting = True
            try:
                async with _native_async_lock():
                    telemetry.native_wait_finished()
                    waiting = False
                    telemetry.native_active_started()
                    try:
                        outcome = await _run_worker_async_unlocked(
                            name,
                            args,
                            kwargs,
                            timeout_seconds=timeout_seconds,
                        )
                    finally:
                        telemetry.native_active_finished()
            finally:
                if waiting:
                    telemetry.native_wait_finished()
                    waiting = False
        else:
            outcome = await _run_worker_async_unlocked(
                name,
                args,
                kwargs,
                timeout_seconds=timeout_seconds,
            )
        if not outcome["ok"]:
            error = outcome.get("error")
            if isinstance(error, dict):
                error_code = str(error.get("code") or "worker_failed")
        return outcome
    except asyncio.CancelledError:
        error_code = "tool_cancelled"
        raise
    except Exception:
        error_code = "worker_failed"
        raise
    finally:
        telemetry.worker_finished(
            name,
            duration_seconds=time.monotonic() - started,
            ok=bool(outcome and outcome.get("ok")),
            error_code=error_code,
        )


def _adapt_tool(
    name: str,
    function: typing.Callable,
    *,
    return_json_text: bool = False,
    timeout_seconds: int | None = None,
    resource_class: str | None = None,
    profile: str | None = None,
) -> typing.Callable:
    """Preserve source parameters while routing execution through a worker."""

    @functools.wraps(function)
    async def invoke(*args, **kwargs):
        options = {"timeout_seconds": timeout_seconds}
        if resource_class is not None:
            options["resource_class"] = resource_class
        token = _CALL_PROFILE.set(profile)
        try:
            outcome = await _run_worker_async(name, args, kwargs, **options)
        finally:
            _CALL_PROFILE.reset(token)
        if not outcome["ok"]:
            raise RuntimeError(json.dumps(outcome, indent=2))
        result = outcome["result"]
        if return_json_text and not isinstance(result, str):
            return json.dumps(result, indent=2, default=str)
        return result

    try:
        hints = typing.get_type_hints(function)
    except Exception:
        hints = getattr(function, "__annotations__", {})
    signature = inspect.signature(function)
    parameters = [
        parameter.replace(annotation=hints.get(parameter.name, parameter.annotation))
        for parameter in signature.parameters.values()
    ]
    return_annotation = str if return_json_text else hints.get("return", signature.return_annotation)
    invoke.__signature__ = signature.replace(
        parameters=parameters, return_annotation=return_annotation
    )
    invoke.__annotations__ = {
        **{parameter.name: parameter.annotation for parameter in parameters},
        "return": return_annotation,
    }
    return invoke


class ApiKeyMiddleware:
    """Require a bearer token without placing it in logs or worker environments."""

    def __init__(
        self,
        app: typing.Callable,
        token: str,
        *,
        public_paths: set[str] | None = None,
    ):
        self.app = app
        self._token = token.encode("utf-8")
        self._public_paths = frozenset(public_paths or set())

    async def __call__(self, scope, receive, send):
        if scope.get("type") != "http" or scope.get("path") in self._public_paths:
            await self.app(scope, receive, send)
            return
        authorization = b""
        for name, value in scope.get("headers", []):
            if name.lower() == b"authorization":
                authorization = value
                break
        expected = b"Bearer " + self._token
        if not hmac.compare_digest(authorization, expected):
            body = b'{"error":"unauthorized"}'
            await send(
                {
                    "type": "http.response.start",
                    "status": 401,
                    "headers": [
                        (b"content-type", b"application/json"),
                        (b"content-length", str(len(body)).encode("ascii")),
                        (b"www-authenticate", b"Bearer"),
                        (b"cache-control", b"no-store"),
                    ],
                }
            )
            await send({"type": "http.response.body", "body": body})
            return
        await self.app(scope, receive, send)


def _is_loopback_host(host: str) -> bool:
    candidate = host.strip().strip("[]").lower()
    if candidate in _LOOPBACK_HOSTS:
        return True
    try:
        return ipaddress.ip_address(candidate).is_loopback
    except ValueError:
        return False


def _validated_patterns(values: list[str], label: str) -> list[str]:
    patterns = []
    for value in values:
        pattern = str(value).strip()
        if not pattern or any(character.isspace() for character in pattern):
            raise ValueError(f"{label} values must be non-empty patterns without whitespace")
        if pattern not in patterns:
            patterns.append(pattern)
    return patterns


def resolve_http_configuration(
    *,
    host: str,
    port: int,
    allowed_hosts: list[str],
    allowed_origins: list[str],
    environ: typing.Mapping[str, str] | None = None,
    api_key_env: str = "CHEMDRAW_MCP_HTTP_API_KEY",
) -> dict[str, typing.Any]:
    """Validate remote HTTP exposure and return non-secret server settings."""
    environ = environ if environ is not None else os.environ
    host = str(host).strip()
    if not host:
        raise ValueError("HTTP host must not be empty")
    if isinstance(port, bool) or not isinstance(port, int) or not 1 <= port <= 65535:
        raise ValueError("HTTP port must be an integer from 1 through 65535")
    if not _ENVIRONMENT_NAME.fullmatch(api_key_env):
        raise ValueError("API key environment variable name is invalid")
    token = str(environ.get(api_key_env) or "")
    loopback = _is_loopback_host(host)
    if not loopback and not token:
        raise ValueError(
            f"Remote Streamable HTTP requires an API key in {api_key_env}"
        )
    if token and len(token.encode("utf-8")) < 32:
        raise ValueError("HTTP API key must contain at least 32 UTF-8 bytes")
    validated_hosts = _validated_patterns(allowed_hosts, "allowed host")
    validated_origins = _validated_patterns(allowed_origins, "allowed origin")
    if not validated_hosts:
        if loopback:
            validated_hosts = ["127.0.0.1:*", "localhost:*", "[::1]:*"]
        elif host not in {"0.0.0.0", "::"}:
            validated_hosts = [f"{host}:*"]
        else:
            raise ValueError(
                "Wildcard remote listening requires at least one explicit allowed host"
            )
    if not validated_origins and loopback:
        validated_origins = [
            "http://127.0.0.1:*",
            "http://localhost:*",
            "http://[::1]:*",
        ]
    return {
        "host": host,
        "port": port,
        "api_key": token or None,
        "api_key_env": api_key_env,
        "allowed_hosts": validated_hosts,
        "allowed_origins": validated_origins,
        "loopback": loopback,
    }


def _register_observability_routes(mcp, *, tool_count: int) -> None:
    from starlette.responses import JSONResponse, PlainTextResponse

    @mcp.custom_route("/health", methods=["GET"], include_in_schema=False)
    async def health(_request):
        return JSONResponse(
            telemetry.health_snapshot(tool_count=tool_count),
            headers={"Cache-Control": "no-store"},
        )

    @mcp.custom_route("/metrics", methods=["GET"], include_in_schema=False)
    async def metrics(_request):
        return PlainTextResponse(
            telemetry.render_prometheus(),
            media_type="text/plain; version=0.0.4",
            headers={"Cache-Control": "no-store"},
        )


_REGISTERED_RESOURCE_URIS = (
    "chemdraw://references/{slug}",
    "chemdraw://templates/{slug}",
    "chemdraw://style-guide/{preset}",
)
_REGISTERED_PROMPT_NAMES = (
    "draw_reaction_scheme",
    "reconstruct_figure",
    "analyze_nmr_and_lcms",
    "build_acs1996_figure",
)
_SLUG_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")
_BUILTIN_TEMPLATES: dict[str, str] = {
    "acs1996": json.dumps(
        {
            "objects": [
                {
                    "type": "molecule",
                    "smiles": "CC(=O)Oc1ccccc1C(=O)O",
                    "at": [120, 90],
                    "ring_fills": [{"atoms": [3, 4, 5, 6, 7, 8], "color": "#dbeafe"}],
                },
                {"type": "label_box", "at": [120, 145], "text": "1a"},
            ]
        },
        indent=2,
    ),
    "chair": json.dumps(
        {
            "objects": [
                {
                    "type": "conformer",
                    "kind": "chair",
                    "at": [120, 100],
                    "substituents": {"1_eq": "OH", "4_ax": "Me"},
                }
            ]
        },
        indent=2,
    ),
    "newman": json.dumps(
        {
            "objects": [
                {
                    "type": "conformer",
                    "kind": "newman",
                    "at": [120, 100],
                    "front": ["Me", "H", "H"],
                    "back": ["Me", "H", "H"],
                    "dihedral_deg": 60,
                }
            ]
        },
        indent=2,
    ),
    "catalytic-cycle": (
        "@layout catalytic-cycle\n"
        'Cat: {[Pd]} "Pd(0)"\n'
        'Int1: {c1ccccc1[Pd]Br} "Ar-Pd-Br"\n'
        'Int2: {c1ccccc1[Pd]c2ccccc2} "Ar-Pd-Ar\'"\n'
        'Cat -->|a| Int1\n'
        '  above: "ArBr, OA"\n'
        'Int1 -->|b| Int2\n'
        '  above: "Ar\'B(OH)2, TM"\n'
        'Int2 -->|c| Cat\n'
        '  above: "RE"\n'
    ),
}


def _references_directory() -> Path:
    return Path(__file__).resolve().parents[3] / "skill" / "chemdraw" / "references"


def read_reference_resource(slug: str) -> str:
    clean = (slug or "").strip()
    if clean.endswith(".md"):
        clean = clean[:-3]
    if not _SLUG_PATTERN.fullmatch(clean):
        raise ValueError(f"Invalid reference slug: {slug!r}")
    ref_dir = _references_directory()
    target = ref_dir / f"{clean}.md"
    if target.is_file():
        return target.read_text(encoding="utf-8")
    available = sorted(p.stem for p in ref_dir.glob("*.md")) if ref_dir.is_dir() else []
    return f"Reference {clean!r} not found. Available references: {', '.join(available)}"


def read_template_resource(slug: str) -> str:
    clean = (slug or "").strip()
    for ext in (".json", ".yaml", ".yml", ".cdxml"):
        if clean.endswith(ext):
            clean = clean[: -len(ext)]
    if not _SLUG_PATTERN.fullmatch(clean):
        raise ValueError(f"Invalid template slug: {slug!r}")
    if clean in _BUILTIN_TEMPLATES:
        return _BUILTIN_TEMPLATES[clean]
    examples_dir = Path(__file__).resolve().parents[2] / "examples"
    if examples_dir.is_dir():
        for path in sorted(examples_dir.rglob(f"{clean}.*")):
            if path.is_file() and path.suffix.lower() in {".json", ".yaml", ".yml", ".cdxml"}:
                return path.read_text(encoding="utf-8")
    return json.dumps(
        {
            "error": f"Unknown template {clean!r}",
            "available_templates": sorted(_BUILTIN_TEMPLATES),
        },
        indent=2,
    )


def read_style_guide_resource(preset: str) -> str:
    """JSON settings of one built-in style preset, or of all presets for ``all``."""
    from ..chemdraw.style_presets import list_style_presets, style_preset

    clean = (preset or "").strip()
    if clean.casefold() in {"", "all", "index"}:
        return json.dumps(list_style_presets(), indent=2)
    try:
        return json.dumps(style_preset(clean), indent=2)
    except ValueError as exc:
        return json.dumps({"error": str(exc)}, indent=2)


def _register_resources_and_prompts(mcp: typing.Any) -> None:
    registered_resources: list[str] = []
    registered_prompts: list[str] = []

    resource_decorator = getattr(mcp, "resource", None)
    if callable(resource_decorator):
        @resource_decorator("chemdraw://references/{slug}")
        def chemdraw_reference(slug: str) -> str:
            """Read a ChemDraw skill workflow reference document by slug."""
            return read_reference_resource(slug)

        @resource_decorator("chemdraw://templates/{slug}")
        def chemdraw_template(slug: str) -> str:
            """Read a ready-to-run ChemDraw JSON/DSL template by slug."""
            return read_template_resource(slug)

        @resource_decorator("chemdraw://style-guide/{preset}")
        def chemdraw_style_guide(preset: str) -> str:
            """Settings of a built-in journal style preset from ChemDraw's stock style sheets
            (acs1996, wiley, adv_synth_catal, rsc, rsc_1col, nature, synthesis, ...; "all" lists them)."""
            return read_style_guide_resource(preset)

        registered_resources.extend(_REGISTERED_RESOURCE_URIS)

    prompt_decorator = getattr(mcp, "prompt", None)
    if callable(prompt_decorator):
        @prompt_decorator()
        def draw_reaction_scheme(
            reactants: str = "",
            products: str = "",
            conditions: str = "",
            layout: str = "linear",
        ) -> str:
            """Guided workflow for drawing a validated reaction scheme in ACS 1996 style."""
            return (
                "Draw an editable ChemDraw reaction scheme:\n"
                f"- Reactants: {reactants or '(resolve with resolve_name)'}\n"
                f"- Products: {products or '(resolve or transform with modify_molecule)'}\n"
                f"- Conditions: {conditions or '(specify above/below arrow)'}\n"
                f"- Layout: {layout} (linear | sequential | stacked | divergent | catalytic-cycle)\n"
                "Steps:\n"
                "1. Ground every species with resolve_name or modify_molecule.\n"
                "2. Call draw_figure or render_scheme (yaml_text or compact_text).\n"
                "3. Render a 300 dpi PNG with render_to_png and visually verify labels, arrows, and stereo."
            )

        @prompt_decorator()
        def reconstruct_figure(image_path: str = "", verify_stereo: bool = True) -> str:
            """Guided workflow for reconstructing a chemical figure or screenshot into editable CDXML."""
            return (
                f"Reconstruct the chemical figure at {image_path or '<image_path>'} into editable CDXML:\n"
                "1. Run recognize_structure or extract_structures_from_image to obtain candidate SMILES.\n"
                "2. Audit wedge/dash stereochemistry and orientation with rdkit_workbench "
                f"(operations: read_wedges, depict_like, edit_structure; verify_stereo={verify_stereo}).\n"
                "3. Assemble the editable CDXML via draw_figure or build_acs_figure and verify with render_to_png."
            )

        @prompt_decorator()
        def analyze_nmr_and_lcms(
            nmr_path: str = "",
            lcms_path: str = "",
            smiles: str = "",
        ) -> str:
            """Guided workflow for processing NMR spectra, comparing shifts, and analyzing LCMS series."""
            return (
                "Analyze spectroscopic and chromatographic data:\n"
                f"- Candidate SMILES: {smiles or '(optional)'}\n"
                f"- NMR input: {nmr_path or '(Bruker/JCAMP/JEOL/Varian/CSV)'}\n"
                f"- LCMS input: {lcms_path or '(PDF/.rpt/.daml/report.txt/.mzML/.raw)'}\n"
                "Steps:\n"
                "1. For NMR: run scientific_workflow(operation='nmr' or 'stack_nmr') and compare_nmr_shifts.\n"
                "2. For LCMS: run parse_analysis_file, analyze_lcms_series (with internal_standard_name if applicable), "
                "or scientific_workflow(operation='lcms_plate')."
            )

        @prompt_decorator()
        def build_acs1996_figure(description: str = "", style: str = "jacs") -> str:
            """Guided workflow for building JACS/Angew/ACS 1996 figures with ring fills, conformers, and orbitals."""
            return (
                f"Build an ACS Document 1996 publication figure (style={style}):\n"
                f"- Brief: {description or '(structures, conformers, annotations)'}\n"
                "Capabilities available in build_acs_figure:\n"
                "- JACS_PALETTE ring_fills, atom_halos, multi_attachments (eta^n organometallics), "
                "ts_bracket ([...] double-dagger), orbital lobes, and non-covalent interaction lines.\n"
                "- Deterministic 3D conformers: chair, newman, haworth, fischer, norbornane.\n"
                "Call build_acs_figure(spec=..., output_path=..., render=True) and inspect the PNG."
            )

        registered_prompts.extend(_REGISTERED_PROMPT_NAMES)

    setattr(mcp, "_chemdraw_registered_resources", tuple(registered_resources))
    setattr(mcp, "_chemdraw_registered_prompts", tuple(registered_prompts))


def list_registered_resources_and_prompts(mcp: typing.Any = None) -> dict[str, typing.Any]:
    """Return the MCP resource URI templates and prompt names registered on the server."""
    if mcp is None:
        mcp = build_server()
    resources = list(getattr(mcp, "_chemdraw_registered_resources", _REGISTERED_RESOURCE_URIS))
    prompts = list(getattr(mcp, "_chemdraw_registered_prompts", _REGISTERED_PROMPT_NAMES))
    ref_dir = _references_directory()
    reference_slugs = sorted(p.stem for p in ref_dir.glob("*.md")) if ref_dir.is_dir() else []
    return {
        "resources": resources,
        "resource_uris": resources,
        "prompts": prompts,
        "prompt_names": prompts,
        "reference_slugs": reference_slugs,
        "template_slugs": sorted(_BUILTIN_TEMPLATES),
    }


def build_server(*, profile: str | None = None, **server_settings):
    server_type = mcp_compat.server_class()
    selected_profile = normalize_profile(profile)
    registry = build_registry(profile=selected_profile)
    telemetry.configure_tools(registry)
    mcp = server_type(
        "cdxml-toolkit", instructions=upstream.mcp.instructions, **server_settings
    )
    for spec in registry.values():
        mcp.tool(
            name=spec.name,
            title=spec.title,
            description=spec.description,
            annotations=spec.annotations,
            structured_output=False,
        )(
            _adapt_tool(
                spec.name,
                spec.function,
                return_json_text=spec.return_json_text,
                timeout_seconds=spec.timeout_seconds,
                resource_class=spec.resource_class,
                profile=selected_profile,
            )
        )
    _register_resources_and_prompts(mcp)
    _register_observability_routes(mcp, tool_count=len(registry))
    return mcp


create_server = build_server


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--transport",
        choices=("stdio", "streamable-http"),
        default=os.environ.get("CHEMDRAW_MCP_TRANSPORT", "stdio"),
    )
    parser.add_argument(
        "--profile",
        choices=PROFILE_CHOICES,
        default=os.environ.get("CHEMDRAW_MCP_PROFILE", DEFAULT_PROFILE),
    )
    parser.add_argument("--host", default=os.environ.get("CHEMDRAW_MCP_HTTP_HOST", "127.0.0.1"))
    parser.add_argument(
        "--port",
        type=int,
        default=_positive_env_int("CHEMDRAW_MCP_HTTP_PORT", 8029),
    )
    parser.add_argument("--allowed-host", action="append", default=[])
    parser.add_argument("--allowed-origin", action="append", default=[])
    parser.add_argument("--api-key-env", default="CHEMDRAW_MCP_HTTP_API_KEY")
    parser.add_argument("--mcp-path", default="/mcp")
    parser.add_argument("--stateless-http", action="store_true")
    parser.add_argument("--json-response", action="store_true")
    parser.add_argument(
        "--log-level",
        choices=("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"),
        default="INFO",
    )
    return parser.parse_args(argv)


def build_http_app(args: argparse.Namespace, *, environ=None):
    configuration = resolve_http_configuration(
        host=args.host,
        port=args.port,
        allowed_hosts=args.allowed_host,
        allowed_origins=args.allowed_origin,
        environ=environ,
        api_key_env=args.api_key_env,
    )
    if not isinstance(args.mcp_path, str) or not args.mcp_path.startswith("/"):
        raise ValueError("MCP HTTP path must begin with /")
    from mcp.server.transport_security import TransportSecuritySettings

    transport_security = TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=configuration["allowed_hosts"],
        allowed_origins=configuration["allowed_origins"],
    )
    mcp = build_server(
        profile=args.profile,
        host=configuration["host"],
        port=configuration["port"],
        streamable_http_path=args.mcp_path,
        stateless_http=bool(args.stateless_http),
        json_response=bool(args.json_response),
        log_level=args.log_level,
        transport_security=transport_security,
    )
    app = mcp.streamable_http_app()
    if configuration["api_key"]:
        app = ApiKeyMiddleware(
            app,
            configuration["api_key"],
            public_paths={"/health"},
        )
    return mcp, app, configuration


def run_streamable_http(args: argparse.Namespace) -> None:
    import uvicorn

    _mcp, app, configuration = build_http_app(args)
    server = uvicorn.Server(
        uvicorn.Config(
            app,
            host=configuration["host"],
            port=configuration["port"],
            log_level=args.log_level.lower(),
            access_log=False,
        )
    )
    server.run()


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    if args.transport == "stdio":
        build_server(profile=args.profile).run(transport="stdio")
        return
    try:
        run_streamable_http(args)
    except KeyboardInterrupt:
        return


if __name__ == "__main__":
    main()
