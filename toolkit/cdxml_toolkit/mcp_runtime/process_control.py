"""Shared Windows process containment and attributed automation cleanup."""

from __future__ import annotations

import ctypes
import json
import os
from pathlib import Path
import subprocess
import time
from typing import Any


_AUTOMATION_NAMES = {"chemdraw.exe", "winword.exe", "powerpnt.exe"}


def _system_executable(relative: str) -> Path | None:
    root = os.environ.get("SystemRoot") or os.environ.get("WINDIR")
    if not root:
        return None
    candidate = Path(root) / relative
    return candidate if candidate.is_file() else None


def _assign_kill_job(process: subprocess.Popen) -> tuple[Any, Any, Any] | None:
    if os.name != "nt" or not isinstance(getattr(process, "_handle", None), int):
        return None
    try:
        import win32api
        import win32job

        job = win32job.CreateJobObject(None, "")
        information = win32job.QueryInformationJobObject(
            job, win32job.JobObjectExtendedLimitInformation
        )
        information["BasicLimitInformation"]["LimitFlags"] |= (
            win32job.JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        )
        win32job.SetInformationJobObject(
            job, win32job.JobObjectExtendedLimitInformation, information
        )
        win32job.AssignProcessToJobObject(job, int(process._handle))
        return job, win32api, win32job
    except Exception:
        try:
            if "job" in locals():
                win32api.CloseHandle(job)
        except Exception:
            pass
        return None


def _close_job(
    job: tuple[Any, Any, Any] | None,
    *,
    terminate: bool = False,
) -> bool:
    if not job:
        return True
    handle, win32api, win32job = job
    if not terminate:
        try:
            information = win32job.QueryInformationJobObject(
                handle, win32job.JobObjectExtendedLimitInformation
            )
            information["BasicLimitInformation"]["LimitFlags"] &= ~(
                win32job.JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
            )
            win32job.SetInformationJobObject(
                handle, win32job.JobObjectExtendedLimitInformation, information
            )
        except Exception:
            # Leaking a diagnostic-only handle is safer than killing a COM server
            # that may still be completing normal shutdown.
            return False
    try:
        win32api.CloseHandle(handle)
        return True
    except Exception:
        return False


def terminate_pid(pid: int, timeout_seconds: float = 10) -> bool:
    taskkill = _system_executable(r"System32\taskkill.exe")
    if taskkill is None:
        return False
    if timeout_seconds <= 0:
        return not pid_is_running(pid)
    try:
        result = subprocess.run(
            [str(taskkill), "/PID", str(pid), "/T", "/F"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=timeout_seconds,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            check=False,
        )
        return result.returncode == 0 or not pid_is_running(pid)
    except Exception:
        return not pid_is_running(pid)


def pid_is_running(pid: int) -> bool:
    if os.name != "nt":
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False
    try:
        kernel32 = ctypes.windll.kernel32
        kernel32.OpenProcess.argtypes = [ctypes.c_uint32, ctypes.c_int, ctypes.c_uint32]
        kernel32.OpenProcess.restype = ctypes.c_void_p
        kernel32.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
        kernel32.WaitForSingleObject.restype = ctypes.c_uint32
        kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
        kernel32.CloseHandle.restype = ctypes.c_int
        handle = kernel32.OpenProcess(0x00100000, False, int(pid))
        if not handle:
            return kernel32.GetLastError() != 87
        try:
            return kernel32.WaitForSingleObject(handle, 0) == 0x00000102
        finally:
            kernel32.CloseHandle(handle)
    except (AttributeError, OSError, ValueError):
        return True


def _terminate_process_tree(
    process: subprocess.Popen,
    job: tuple[Any, Any, Any] | None = None,
    *,
    deadline: float | None = None,
) -> None:
    _close_job(job, terminate=True)
    if process.poll() is not None:
        return
    remaining = None if deadline is None else max(0.0, deadline - time.monotonic())
    pid = getattr(process, "pid", None)
    if os.name == "nt" and isinstance(pid, int) and (remaining is None or remaining > 0):
        terminate_pid(pid, timeout_seconds=min(10.0, remaining or 10.0))
    try:
        process.kill()
    except Exception:
        pass
    remaining = None if deadline is None else max(0.0, deadline - time.monotonic())
    if remaining is None or remaining > 0:
        try:
            process.wait(timeout=min(5.0, remaining or 5.0))
        except Exception:
            pass


def snapshot_automation_processes(timeout_seconds: float = 5) -> dict[int, dict[str, Any]]:
    if os.name != "nt":
        return {}
    powershell = _system_executable(
        r"System32\WindowsPowerShell\v1.0\powershell.exe"
    )
    if powershell is None:
        raise RuntimeError("Windows PowerShell is unavailable for process attribution")
    script = (
        "$items=@(Get-CimInstance -ClassName Win32_Process -Filter "
        "\"Name='ChemDraw.exe' OR Name='WINWORD.EXE' OR Name='POWERPNT.EXE'\" | "
        "ForEach-Object {[pscustomobject]@{pid=[int]$_.ProcessId;"
        "parent_pid=[int]$_.ParentProcessId;name=[string]$_.Name;"
        "command_line=[string]$_.CommandLine;created=[string]$_.CreationDate;"
        "thread_count=[int]$_.ThreadCount;virtual_size=[uint64]$_.VirtualSize;"
        "handle_count=[int]$_.HandleCount}});"
        "ConvertTo-Json -InputObject $items -Compress"
    )
    result = subprocess.run(
        [
            str(powershell),
            "-NoLogo",
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            script,
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout_seconds,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError("Automation process snapshot failed")
    try:
        decoded = json.loads(result.stdout or "[]")
    except json.JSONDecodeError as exc:
        raise RuntimeError("Automation process snapshot returned invalid JSON") from exc
    if isinstance(decoded, dict):
        decoded = [decoded]
    snapshot: dict[int, dict[str, Any]] = {}
    for item in decoded if isinstance(decoded, list) else []:
        if not isinstance(item, dict):
            continue
        try:
            pid = int(item.get("pid"))
            parent_pid = int(item.get("parent_pid"))
        except (TypeError, ValueError):
            continue
        name = str(item.get("name") or "")
        if name.lower() not in _AUTOMATION_NAMES:
            continue
        try:
            thread_count = int(item.get("thread_count") or 0)
            virtual_size = int(item.get("virtual_size") or 0)
        except (TypeError, ValueError):
            continue
        if thread_count <= 0 or virtual_size <= 0:
            continue
        if not pid_is_running(pid):
            continue
        snapshot[pid] = {
            "pid": pid,
            "parent_pid": parent_pid,
            "name": name,
            "command_line": str(item.get("command_line") or ""),
            "created": str(item.get("created") or ""),
            "thread_count": thread_count,
            "virtual_size": virtual_size,
            "handle_count": int(item.get("handle_count") or 0),
        }
    return snapshot


def cleanup_automation_processes(
    before: dict[int, dict[str, Any]],
    after: dict[int, dict[str, Any]],
    *,
    stage_pid: int,
    terminate: bool = True,
    deadline: float | None = None,
) -> dict[str, Any]:
    terminated: list[int] = []
    lingering: list[int] = []
    unknown: list[int] = []
    failed: list[int] = []
    for pid in sorted(set(after) - set(before)):
        item = after[pid]
        name = str(item.get("name") or "").lower()
        if name not in _AUTOMATION_NAMES:
            continue
        parent_pid = item.get("parent_pid")
        attributed = parent_pid == stage_pid
        if not attributed:
            unknown.append(pid)
            continue
        if not terminate:
            lingering.append(pid)
            continue
        remaining = None if deadline is None else max(0.0, deadline - time.monotonic())
        if remaining is not None and remaining <= 0:
            failed.append(pid)
        elif terminate_pid(pid, timeout_seconds=min(10.0, remaining or 10.0)):
            terminated.append(pid)
        else:
            failed.append(pid)
    confirmed = not lingering and not unknown and not failed
    return {
        "status": "confirmed" if confirmed else "unconfirmed",
        "terminated_pids": terminated,
        "lingering_pids": lingering,
        "unknown_pids": unknown,
        "failed_pids": failed,
    }
