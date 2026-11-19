"""Cross-process resource locks for native ChemDraw automation."""

from __future__ import annotations

from contextlib import contextmanager
import os
from pathlib import Path
import sys
import tempfile
import threading
import time
from typing import Iterator


# Keep this name: it is the mutex every runtime version shares, so older and newer runtimes
# still exclude each other on one machine. Changing it would allow two ChemDraw COM sessions.
CHEMDRAW_COM_MUTEX = r"Local\CodexChemDrawComAutomation"
# macOS equivalent: an flock()ed per-user file.  Its path must not depend on
# TMPDIR, which differs between a session and a worker started without it.
CHEMDRAW_LOCK_FILE = (
    Path.home() / "Library" / "Caches" / "chemdraw-skill" / "native.lock"
    if sys.platform == "darwin"
    else Path(tempfile.gettempdir()) / f"chemdraw-skill-native-{os.getuid()}.lock"
    if hasattr(os, "getuid")
    else Path(tempfile.gettempdir()) / "chemdraw-skill-native.lock"
)
# Set while a process holds the lock; its child processes share that hold, as a
# worker started by a lock holder must not wait for its own parent.
LOCK_HOLDER_ENV = "CHEMDRAW_NATIVE_LOCK_HOLDER"

_held = threading.local()


class ResourceBusyError(RuntimeError):
    """Raised when an exclusive native resource cannot be acquired in time."""

    def __init__(self, resource_class: str, timeout_seconds: int):
        self.resource_class = resource_class
        self.timeout_seconds = timeout_seconds
        super().__init__(
            f"Resource {resource_class} remained busy for {timeout_seconds} seconds"
        )


@contextmanager
def native_resource_lock(
    resource_class: str | None,
    timeout_seconds: int,
) -> Iterator[None]:
    """Serialize ChemDraw automation across workers in the current user session."""
    if resource_class is None or (os.name != "nt" and sys.platform != "darwin"):
        yield
        return
    if resource_class != "chemdraw_com":
        raise ValueError(f"Unknown native resource class: {resource_class}")
    if timeout_seconds <= 0:
        raise ValueError("Resource lock timeout must be positive")
    depth = getattr(_held, "depth", 0)
    if depth or _held_by_ancestor():
        # Re-entrant within a thread, and shared with the workers a holder starts:
        # a worker must not wait for the lock its own parent is holding.
        _held.depth = depth + 1
        try:
            yield
        finally:
            _held.depth -= 1
        return
    acquire = _windows_mutex if os.name == "nt" else _file_lock
    with acquire(resource_class, timeout_seconds):
        _held.depth = 1
        previous = os.environ.get(LOCK_HOLDER_ENV)
        os.environ[LOCK_HOLDER_ENV] = str(os.getpid())
        try:
            yield
        finally:
            if previous is None:
                os.environ.pop(LOCK_HOLDER_ENV, None)
            else:
                os.environ[LOCK_HOLDER_ENV] = previous
            _held.depth = 0


@contextmanager
def _windows_mutex(resource_class: str, timeout_seconds: int) -> Iterator[None]:
    import win32api
    import win32event

    handle = win32event.CreateMutex(None, False, CHEMDRAW_COM_MUTEX)
    acquired = False
    try:
        result = win32event.WaitForSingleObject(handle, int(timeout_seconds * 1000))
        abandoned = getattr(win32event, "WAIT_ABANDONED", 0x80)
        if result in {win32event.WAIT_OBJECT_0, abandoned}:
            acquired = True
        elif result == win32event.WAIT_TIMEOUT:
            raise ResourceBusyError(resource_class, timeout_seconds)
        else:
            raise RuntimeError(f"Unexpected native resource wait result: {result}")
        yield
    finally:
        if acquired:
            win32event.ReleaseMutex(handle)
        win32api.CloseHandle(handle)


@contextmanager
def _file_lock(resource_class: str, timeout_seconds: int) -> Iterator[None]:
    """flock() a per-user file."""
    import fcntl

    CHEMDRAW_LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(CHEMDRAW_LOCK_FILE, os.O_RDWR | os.O_CREAT, 0o600)
    try:
        deadline = time.monotonic() + timeout_seconds
        while True:
            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise ResourceBusyError(resource_class, timeout_seconds) from None
                time.sleep(0.05)
        try:
            yield
        finally:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
    finally:
        os.close(descriptor)


def _process_is_running(pid: int) -> bool:
    if os.name == "nt":
        # os.kill(pid, 0) terminates the process on Windows; ask for its exit code instead.
        import win32api
        import win32con
        import win32process

        try:
            handle = win32api.OpenProcess(win32con.PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        except win32api.error:
            return False
        try:
            return win32process.GetExitCodeProcess(handle) == win32con.STILL_ACTIVE
        finally:
            win32api.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _held_by_ancestor() -> bool:
    """True when a still-running parent process passed its lock hold down to us."""
    value = os.environ.get(LOCK_HOLDER_ENV, "")
    if not value.isdigit() or int(value) == os.getpid():
        return False
    return _process_is_running(int(value))
