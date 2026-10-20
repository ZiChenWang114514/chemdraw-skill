"""Cross-process resource locks for native ChemDraw automation."""

from __future__ import annotations

from contextlib import contextmanager
import os
from typing import Iterator


CHEMDRAW_COM_MUTEX = r"Local\CodexChemDrawComAutomation"


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
    """Serialize ChemDraw COM calls across workers in the current user session."""
    if resource_class is None or os.name != "nt":
        yield
        return
    if resource_class != "chemdraw_com":
        raise ValueError(f"Unknown native resource class: {resource_class}")
    if timeout_seconds <= 0:
        raise ValueError("Resource lock timeout must be positive")

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
