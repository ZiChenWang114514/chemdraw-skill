"""Every COM entry point acquires ChemDraw through the one private-instance path.

Fakes stand in for ChemDraw, so these run on every platform and never start it.
"""

from __future__ import annotations

from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace

import pytest

from cdxml_toolkit.chemdraw import cdx_converter, cdxml_to_image, mac_automation, progid
from cdxml_toolkit.deterministic_pipeline.legacy import eln_cdx_cleanup
from cdxml_toolkit.mcp_runtime import native_renderer


class FakeDocument:
    def __init__(self, application):
        self.application = application

    def SaveAs(self, path):
        Path(path).write_bytes(b"exported")

    def Close(self, *args):
        self.application.calls.append(("Close", args))


class FakeApplication:
    """The user's ChemDraw: visible, with their own preferences and documents."""

    def __init__(self):
        self.calls = []
        self.Visible = True
        self.Preferences = SimpleNamespace(TransparentPNGs=True, PNGResolution=72)
        self.Documents = SimpleNamespace(Open=self._open, Count=3)

    def _open(self, path):
        self.calls.append(("Open", path))
        return FakeDocument(self)

    def Quit(self):
        self.calls.append(("Quit", ()))


@pytest.fixture
def users_chemdraw(monkeypatch):
    """ChemDraw already running: the shared path reports it as not launched."""
    application = FakeApplication()
    acquisitions = []

    def acquire():
        acquisitions.append(True)
        return application, False

    def attach_to_the_user(*_args, **_kwargs):
        raise AssertionError("COM entry points must not attach to ChemDraw on their own")

    monkeypatch.setattr(mac_automation, "is_macos", lambda: False)
    monkeypatch.setattr(native_renderer, "_com_apartment", nullcontext)
    monkeypatch.setattr(native_renderer, "_acquire_application", acquire)
    monkeypatch.setattr(progid, "get_active", attach_to_the_user)
    monkeypatch.setattr(progid, "dispatch", attach_to_the_user)
    return SimpleNamespace(application=application, acquisitions=acquisitions)


def assert_left_untouched(chemdraw):
    application = chemdraw.application
    assert chemdraw.acquisitions, "the shared acquisition path was not used"
    assert ("Quit", ()) not in application.calls
    assert application.Visible is True
    assert application.Preferences.TransparentPNGs is True
    assert application.Preferences.PNGResolution == 72
    opened = [call for call in application.calls if call[0] == "Open"]
    closed = [call for call in application.calls if call[0] == "Close"]
    assert len(closed) == len(opened) and all(args == (False,) for _, args in closed)


def test_cdx_conversion_uses_the_shared_session(users_chemdraw, tmp_path):
    source = tmp_path / "in.cdx"
    source.write_bytes(b"VjCD")
    cdx_converter._com_convert_file(str(source), str(tmp_path / "out.cdx"))
    assert_left_untouched(users_chemdraw)


def test_batch_cdx_conversion_uses_the_shared_session(users_chemdraw, tmp_path, monkeypatch):
    monkeypatch.setattr(cdx_converter, "_pick_backend", lambda method, table: ("com", None))
    sources = []
    for name in ("a.cdxml", "b.cdxml"):
        sources.append(tmp_path / name)
        sources[-1].write_text("<CDXML/>", encoding="utf-8")
    results = cdx_converter.batch_convert_files([str(path) for path in sources])
    assert all(entry["error"] is None for entry in results.values())
    assert len(users_chemdraw.acquisitions) == 1
    assert_left_untouched(users_chemdraw)


def test_image_export_uses_the_shared_session(users_chemdraw, tmp_path):
    source = tmp_path / "in.cdxml"
    source.write_text("<CDXML/>", encoding="utf-8")
    output = cdxml_to_image.cdxml_to_image(str(source), str(tmp_path / "out.png"), png_dpi=600)
    assert Path(output).read_bytes() == b"exported"
    assert_left_untouched(users_chemdraw)


def test_batch_image_export_uses_the_shared_session(users_chemdraw, tmp_path):
    source = tmp_path / "in.cdxml"
    source.write_text("<CDXML/>", encoding="utf-8")
    results = cdxml_to_image.batch_render([str(source)], png_dpi=600)
    assert results[str(source)]["error"] is None
    assert_left_untouched(users_chemdraw)


def test_legacy_cleanup_uses_the_shared_acquisition(users_chemdraw):
    application, launched = eln_cdx_cleanup._get_chemdraw()
    assert application is users_chemdraw.application and launched is False
    assert users_chemdraw.acquisitions
