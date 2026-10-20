"""Windows-safe MCP launcher with isolated, timeout-bounded workers."""

from __future__ import annotations

import argparse
import asyncio
from contextvars import ContextVar
import functools
import hmac
import inspect
import ipaddress
import json
import os
from pathlib import Path
import re
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
from .tool_registry import build_registry


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
        "CONDA_PREFIX", "JAVA_HOME",
        "HTTP_PROXY", "HTTPS_PROXY", "LOCALAPPDATA", "NO_PROXY", "PATH",
        "NUMBER_OF_PROCESSORS", "OS", "PATHEXT",
        "PROCESSOR_ARCHITECTURE", "PROCESSOR_IDENTIFIER",
        "PROCESSOR_LEVEL", "PROCESSOR_REVISION",
        "PROGRAMDATA", "PROGRAMFILES", "PROGRAMFILES(X86)",
        "PROGRAMW6432", "REQUESTS_CA_BUNDLE", "SSL_CERT_FILE", "SYSTEMROOT",
        "PUBLIC", "SYSTEMDRIVE", "TEMP", "TMP", "USERDOMAIN",
        "USERDOMAIN_ROAMINGPROFILE", "USERNAME", "USERPROFILE", "WINDIR",
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
    with tempfile.TemporaryDirectory(prefix="chemdraw-worker-") as temp_dir:
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
        "profile": _CALL_PROFILE.get() or os.environ.get("CHEMDRAW_MCP_PROFILE", "codex"),
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
    except OSError:
        return {
            "ok": False,
            "error": {"code": "worker_launch_failed", "message": "Could not launch the isolated worker"},
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


def build_server(*, profile: str | None = None, **server_settings):
    server_type = mcp_compat.server_class()
    selected_profile = profile or os.environ.get("CHEMDRAW_MCP_PROFILE", "codex")
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
    _register_observability_routes(mcp, tool_count=len(registry))
    return mcp


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--transport",
        choices=("stdio", "streamable-http"),
        default=os.environ.get("CHEMDRAW_MCP_TRANSPORT", "stdio"),
    )
    parser.add_argument(
        "--profile",
        choices=("core", "codex", "office", "analysis", "chemscript"),
        default=os.environ.get("CHEMDRAW_MCP_PROFILE", "codex"),
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
