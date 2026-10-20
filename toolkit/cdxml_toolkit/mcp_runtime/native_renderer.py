"""Reliable ChemDraw COM rendering with stable public errors."""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
import time
from typing import Iterator

from . import native_io
class NativeRenderError(RuntimeError):
    """ChemDraw rendering failure with a stable public error code."""

    def __init__(self, error_code: str, message: str):
        super().__init__(message)
        self.error_code = error_code
        self.public_message = message


def _hresult(exc: BaseException) -> int | None:
    value = getattr(exc, "hresult", None)
    if isinstance(value, int):
        return value
    if exc.args and isinstance(exc.args[0], int):
        return exc.args[0]
    return None


def _classified_error(exc: BaseException) -> NativeRenderError:
    message = str(exc)
    lowered = message.lower()
    if _hresult(exc) == -2147221230 or "not licensed" in lowered or "\u672a\u6388\u6743" in message:
        return NativeRenderError(
            "chemdraw_license_unavailable",
            "ChemDraw COM reports that the installed product license is unavailable",
        )
    return NativeRenderError("native_render_failed", f"ChemDraw rendering failed: {message}")


def _acquire_application():
    import win32com.client as win32

    dispatch_ex = getattr(win32, "DispatchEx", None)
    if dispatch_ex is not None:
        return dispatch_ex("ChemDraw.Application"), True
    return win32.Dispatch("ChemDraw.Application"), True


@contextmanager
def _com_apartment() -> Iterator[None]:
    import pythoncom

    pythoncom.CoInitialize()
    try:
        yield
    finally:
        pythoncom.CoUninitialize()


def _wait_until_readable(path: Path, deadline: float) -> bool:
    previous_size = -1
    stable_checks = 0
    while time.monotonic() < deadline:
        try:
            size = path.stat().st_size
        except OSError:
            size = 0
        if size > 0 and size == previous_size:
            stable_checks += 1
            if stable_checks >= 2:
                return True
        else:
            stable_checks = 0
        previous_size = size
        time.sleep(0.05)
    return False


class NativeRenderSession:
    """Lazily acquire and reuse one ChemDraw application for native exports."""

    def __init__(self, *, timeout_seconds: int = 30):
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        self.timeout_seconds = timeout_seconds
        self.application = None
        self.launched = False
        self.was_visible = None
        self.original_transparent_pngs = None
        self.original_png_resolution = None
        self._apartment = None

    def __enter__(self):
        return self

    def _start(self) -> None:
        if self.application is not None:
            return
        self._apartment = _com_apartment()
        self._apartment.__enter__()
        try:
            self.application, self.launched = _acquire_application()
            self.was_visible = bool(self.application.Visible)
            if self.launched:
                self.application.Visible = False
            preferences = self.application.Preferences
            self.original_transparent_pngs = preferences.TransparentPNGs
            self.original_png_resolution = preferences.PNGResolution
            preferences.TransparentPNGs = False
        except Exception as exc:
            self._release_application()
            self._finish_apartment()
            raise _classified_error(exc) from exc

    def _finish_apartment(self) -> None:
        if self._apartment is not None:
            apartment, self._apartment = self._apartment, None
            apartment.__exit__(None, None, None)

    def _release_application(self) -> None:
        if self.application is None:
            return
        if self.launched:
            try:
                self.application.Quit()
            except Exception:
                pass
        else:
            if self.was_visible is not None:
                try:
                    self.application.Visible = self.was_visible
                except Exception:
                    pass
            try:
                preferences = self.application.Preferences
                preferences.TransparentPNGs = self.original_transparent_pngs
                preferences.PNGResolution = self.original_png_resolution
            except Exception:
                pass
        self.application = None

    def render(self, source: str | Path, destination: str | Path, dpi: int = 300) -> str:
        source_path = Path(source).expanduser().resolve()
        destination_path = Path(destination).expanduser().resolve()
        if not source_path.is_file():
            raise FileNotFoundError(f"CDXML file not found: {source_path}")
        if destination_path.exists():
            raise FileExistsError(f"Refusing to overwrite native render: {destination_path}")
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        self._start()
        deadline = time.monotonic() + self.timeout_seconds
        document = None
        try:
            self.application.Preferences.PNGResolution = dpi
            document = self.application.Documents.Open(str(source_path))
            for attempt in range(2):
                document.SaveAs(str(destination_path))
                remaining = max(0.0, deadline - time.monotonic())
                wait_deadline = time.monotonic() + (
                    remaining if attempt else min(3.0, remaining / 2.0)
                )
                if _wait_until_readable(destination_path, wait_deadline):
                    native_io.validate_native_output(destination_path)
                    return str(destination_path)
            raise NativeRenderError(
                "native_saveas_silent_failure",
                "ChemDraw returned from SaveAs twice without creating a valid output",
            )
        except NativeRenderError:
            raise
        except native_io.NativeIOError as exc:
            raise NativeRenderError(exc.error_code, exc.public_message) from exc
        except Exception as exc:
            raise _classified_error(exc) from exc
        finally:
            if document is not None:
                try:
                    document.Close(False)
                except Exception:
                    pass

    def __exit__(self, exc_type, exc, traceback):
        try:
            self._release_application()
        finally:
            self._finish_apartment()


def render_cdxml(
    source: str | Path,
    destination: str | Path,
    *,
    dpi: int = 300,
    timeout_seconds: int = 30,
) -> str:
    with NativeRenderSession(timeout_seconds=timeout_seconds) as session:
        return session.render(source, destination, dpi=dpi)
