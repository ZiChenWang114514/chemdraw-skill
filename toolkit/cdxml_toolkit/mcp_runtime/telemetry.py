"""Content-free runtime telemetry for the ChemDraw MCP server."""

from __future__ import annotations

from collections import Counter, defaultdict
import math
import threading
import time
from typing import Iterable


HISTOGRAM_BUCKETS = (0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0, 600.0)
_FAILURE_CODES = {
    "tool_timeout",
    "tool_cancelled",
    "worker_launch_failed",
    "worker_output_limit",
    "worker_protocol_error",
    "worker_failed",
    "tool_execution_failed",
    "tool_business_error",
    "resource_busy",
}
_lock = threading.RLock()
_started_at = time.monotonic()
_allowed_tools: set[str] = set()
_tool_calls: Counter[tuple[str, str]] = Counter()
_duration_count: Counter[tuple[str, str]] = Counter()
_duration_sum: defaultdict[tuple[str, str], float] = defaultdict(float)
_duration_buckets: Counter[tuple[str, str, float]] = Counter()
_worker_failures: Counter[tuple[str, str]] = Counter()
_worker_timeouts: Counter[str] = Counter()
_worker_active = 0
_native_queue = 0
_native_active = 0


def configure_tools(names: Iterable[str]) -> None:
    """Set the finite tool-label vocabulary used by exported metrics."""
    with _lock:
        _allowed_tools.clear()
        _allowed_tools.update(str(name) for name in names)


def _tool_label(name: str) -> str:
    return name if name in _allowed_tools else "unknown"


def worker_started(tool: str) -> None:
    del tool
    global _worker_active
    with _lock:
        _worker_active += 1


def worker_finished(
    tool: str,
    *,
    duration_seconds: float,
    ok: bool,
    error_code: str | None,
) -> None:
    global _worker_active
    status = "success" if ok else "error"
    duration = max(0.0, float(duration_seconds))
    with _lock:
        label = _tool_label(tool)
        _worker_active = max(0, _worker_active - 1)
        _tool_calls[(label, status)] += 1
        _duration_count[(label, status)] += 1
        _duration_sum[(label, status)] += duration
        for bucket in HISTOGRAM_BUCKETS:
            if duration <= bucket:
                _duration_buckets[(label, status, bucket)] += 1
        if not ok:
            code = error_code if error_code in _FAILURE_CODES else "other"
            _worker_failures[(label, code)] += 1
            if code == "tool_timeout":
                _worker_timeouts[label] += 1


def native_wait_started() -> None:
    global _native_queue
    with _lock:
        _native_queue += 1


def native_wait_finished() -> None:
    global _native_queue
    with _lock:
        _native_queue = max(0, _native_queue - 1)


def native_active_started() -> None:
    global _native_active
    with _lock:
        _native_active += 1


def native_active_finished() -> None:
    global _native_active
    with _lock:
        _native_active = max(0, _native_active - 1)


def health_snapshot(*, tool_count: int) -> dict:
    """Return process health without input, output, filename, or molecule data."""
    with _lock:
        return {
            "status": "ok",
            "uptime_seconds": round(max(0.0, time.monotonic() - _started_at), 3),
            "tool_count": int(tool_count),
            "workers_active": _worker_active,
            "chemdraw_queue_length": _native_queue,
            "chemdraw_active": _native_active,
        }


def _escape_label(value: str) -> str:
    return value.replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')


def _labels(**values: str) -> str:
    rendered = ",".join(f'{key}="{_escape_label(value)}"' for key, value in values.items())
    return "{" + rendered + "}"


def _number(value: float | int) -> str:
    if isinstance(value, float):
        if math.isinf(value):
            return "+Inf" if value > 0 else "-Inf"
        return format(value, ".12g")
    return str(value)


def render_prometheus() -> str:
    """Render the current process metrics using the Prometheus text format."""
    with _lock:
        calls = dict(_tool_calls)
        duration_count = dict(_duration_count)
        duration_sum = dict(_duration_sum)
        duration_buckets = dict(_duration_buckets)
        failures = dict(_worker_failures)
        timeouts = dict(_worker_timeouts)
        active = _worker_active
        queue = _native_queue
        native_active = _native_active

    lines = [
        "# HELP chemdraw_mcp_tool_calls_total Completed MCP tool calls.",
        "# TYPE chemdraw_mcp_tool_calls_total counter",
    ]
    for (tool, status), value in sorted(calls.items()):
        lines.append(
            f"chemdraw_mcp_tool_calls_total{_labels(tool=tool, status=status)} {value}"
        )
    lines.extend(
        [
            "# HELP chemdraw_mcp_tool_duration_seconds MCP tool execution duration.",
            "# TYPE chemdraw_mcp_tool_duration_seconds histogram",
        ]
    )
    for tool, status in sorted(duration_count):
        for bucket in HISTOGRAM_BUCKETS:
            value = duration_buckets.get((tool, status, bucket), 0)
            lines.append(
                "chemdraw_mcp_tool_duration_seconds_bucket"
                f"{_labels(tool=tool, status=status, le=_number(bucket))} {value}"
            )
        count = duration_count[(tool, status)]
        lines.append(
            "chemdraw_mcp_tool_duration_seconds_bucket"
            f"{_labels(tool=tool, status=status, le='+Inf')} {count}"
        )
        lines.append(
            "chemdraw_mcp_tool_duration_seconds_sum"
            f"{_labels(tool=tool, status=status)} {_number(duration_sum[(tool, status)])}"
        )
        lines.append(
            "chemdraw_mcp_tool_duration_seconds_count"
            f"{_labels(tool=tool, status=status)} {count}"
        )
    lines.extend(
        [
            "# HELP chemdraw_mcp_worker_timeouts_total Worker hard timeouts.",
            "# TYPE chemdraw_mcp_worker_timeouts_total counter",
        ]
    )
    for tool, value in sorted(timeouts.items()):
        lines.append(f"chemdraw_mcp_worker_timeouts_total{_labels(tool=tool)} {value}")
    lines.extend(
        [
            "# HELP chemdraw_mcp_worker_failures_total Worker failures by stable code.",
            "# TYPE chemdraw_mcp_worker_failures_total counter",
        ]
    )
    for (tool, code), value in sorted(failures.items()):
        lines.append(
            f"chemdraw_mcp_worker_failures_total{_labels(tool=tool, code=code)} {value}"
        )
    lines.extend(
        [
            "# HELP chemdraw_mcp_worker_active Active isolated workers.",
            "# TYPE chemdraw_mcp_worker_active gauge",
            f"chemdraw_mcp_worker_active {active}",
            "# HELP chemdraw_mcp_chemdraw_queue_length Calls waiting for local ChemDraw automation.",
            "# TYPE chemdraw_mcp_chemdraw_queue_length gauge",
            f"chemdraw_mcp_chemdraw_queue_length {queue}",
            "# HELP chemdraw_mcp_chemdraw_active Local ChemDraw automation calls currently executing.",
            "# TYPE chemdraw_mcp_chemdraw_active gauge",
            f"chemdraw_mcp_chemdraw_active {native_active}",
        ]
    )
    return "\n".join(lines) + "\n"


def reset_for_tests() -> None:
    global _started_at, _worker_active, _native_queue, _native_active
    with _lock:
        _started_at = time.monotonic()
        _allowed_tools.clear()
        _tool_calls.clear()
        _duration_count.clear()
        _duration_sum.clear()
        _duration_buckets.clear()
        _worker_failures.clear()
        _worker_timeouts.clear()
        _worker_active = 0
        _native_queue = 0
        _native_active = 0
