"""ChemDraw COM automation entry points.

ChemDraw publishes its automation server under a name that depends on the
build: ``ChemDraw_x64.Application`` for the 64-bit application, which is the
only ProgID registered by ChemDraw 23 (Revvity Signals) and later, and
``ChemDraw.Application`` for the older 32-bit releases that are still around on
some workstations. Probing only the legacy name reports "ChemDraw COM is
missing" on a perfectly healthy 64-bit installation, so every entry point tries
the names in :data:`PROGIDS` order and uses the first one that answers.

The helpers exist so callers never hard-code a ProgID: toolkits that wrap COM
should call :func:`dispatch`, :func:`dispatch_ex` or :func:`get_active`, and
diagnostics should use :func:`registered_progids` or
:func:`local_server_command`.
"""

from __future__ import annotations

from typing import Any, Callable, Iterable

#: Automation ProgIDs in probing order: current 64-bit build first, then the
#: legacy name that older and 32-bit releases register.
PROGIDS = ("ChemDraw_x64.Application", "ChemDraw.Application")


def _client() -> Any:
    """The pywin32 client module, imported lazily so non-Windows hosts import us."""

    import win32com.client as win32

    return win32


def _winreg() -> Any:
    """The ``winreg`` module, or ``None`` where it does not exist."""

    try:
        import winreg
    except ImportError:  # macOS, Linux
        return None
    return winreg


def _query_default(winreg: Any, path: str) -> str | None:
    """Default value of the registry key ``path``, or ``None`` when unreadable."""

    try:
        key = winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, path)
    except (OSError, TypeError, ValueError):
        return None
    try:
        value = winreg.QueryValueEx(key, "")[0]
    except (OSError, TypeError, ValueError):
        return None
    finally:
        close = getattr(winreg, "CloseKey", None)
        if close is not None:
            try:
                close(key)
            except OSError:
                pass
    return str(value) if value else None


def _clsid_for(name: str) -> str | None:
    """CLSID registered for the ProgID ``name``, or ``None`` when it is absent."""

    winreg = _winreg()
    if winreg is None:
        return None
    return _query_default(winreg, rf"{name}\CLSID")


def _local_server(clsid: str) -> str | None:
    """``LocalServer32`` command line registered for ``clsid``."""

    winreg = _winreg()
    if winreg is None:
        return None
    return _query_default(winreg, rf"CLSID\{clsid}\LocalServer32")


def registered_progids(progids: Iterable[str] = PROGIDS) -> list[str]:
    """The subset of ``progids`` that HKCR actually registers."""

    return [name for name in progids if _clsid_for(name)]


def local_server_command() -> str | None:
    """Command line of the first registered ChemDraw automation server."""

    for name in PROGIDS:
        clsid = _clsid_for(name)
        if not clsid:
            continue
        command = _local_server(clsid)
        if command:
            return command
    return None


def _first(factory: Callable[[str], Any]) -> Any:
    """Result of ``factory`` for the first ProgID that accepts it.

    pywin32 signals an unregistered class with ``com_error``; other OSErrors are
    possible from a broken registration, so any exception means "try the next
    name". The last failure is re-raised when every name fails.
    """

    error: Exception | None = None
    for name in PROGIDS:
        try:
            return factory(name)
        except Exception as exc:  # noqa: BLE001 - any COM failure means "not this one"
            error = exc
    if error is None:  # pragma: no cover - PROGIDS is never empty
        raise RuntimeError("no ChemDraw ProgID to try")
    raise error


def dispatch() -> Any:
    """Attach to a ChemDraw automation instance, starting the application if needed."""

    return _first(_client().Dispatch)


def dispatch_ex() -> Any:
    """Start a dedicated ChemDraw automation instance for one operation."""

    return _first(_client().DispatchEx)


def get_active() -> Any:
    """Attach to the ChemDraw instance that is already running."""

    return _first(_client().GetActiveObject)
