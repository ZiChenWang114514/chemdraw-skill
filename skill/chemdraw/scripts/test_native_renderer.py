from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
from unittest import mock

from PIL import Image

from cdxml_toolkit.mcp_runtime import native_renderer
class _Preferences:
    TransparentPNGs = True
    PNGResolution = 72


class _Document:
    def __init__(self, *, create_on_attempt: int = 1, invalid=False):
        self.create_on_attempt = create_on_attempt
        self.invalid = invalid
        self.save_attempts = 0
        self.closed = False

    def SaveAs(self, output):
        self.save_attempts += 1
        if self.save_attempts >= self.create_on_attempt:
            if self.invalid:
                Path(output).write_bytes(b"invalid image")
            else:
                Image.new("RGB", (8, 6), "white").save(output)

    def Close(self, _save):
        self.closed = True


class _Documents:
    def __init__(self, document):
        self.document = document
        self.opened = []

    def Open(self, source):
        self.opened.append(source)
        return self.document


class _Application:
    def __init__(self, document):
        self.Visible = True
        self.Preferences = _Preferences()
        self.Documents = _Documents(document)
        self.quit_calls = 0

    def Quit(self):
        self.quit_calls += 1


class _ComError(RuntimeError):
    def __init__(self, hresult, message):
        super().__init__(message)
        self.hresult = hresult


class NativeRendererTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.source = self.root / "source.cdxml"
        self.source.write_text("<CDXML><page/></CDXML>", encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def test_retries_silent_save_once_while_document_remains_open(self):
        output = self.root / "output.png"
        document = _Document(create_on_attempt=2)
        application = _Application(document)

        with mock.patch(
            "cdxml_toolkit.mcp_runtime.native_renderer._acquire_application",
            return_value=(application, True),
        ):
            result = native_renderer.render_cdxml(self.source, output, timeout_seconds=2)

        self.assertEqual(result, str(output.resolve()))
        self.assertEqual(document.save_attempts, 2)
        self.assertTrue(document.closed)
        self.assertEqual(application.quit_calls, 1)

    def test_reports_unavailable_license_with_stable_error_code(self):
        output = self.root / "output.png"
        error = _ComError(-2147221230, "Class is not licensed for use")

        with mock.patch("cdxml_toolkit.mcp_runtime.native_renderer._acquire_application", side_effect=error):
            with self.assertRaises(native_renderer.NativeRenderError) as raised:
                native_renderer.render_cdxml(self.source, output, timeout_seconds=1)

        self.assertEqual(raised.exception.error_code, "chemdraw_license_unavailable")
        self.assertFalse(output.exists())

    def test_application_acquisition_uses_a_dedicated_instance(self):
        application = _Application(_Document())

        with mock.patch(
            "win32com.client.DispatchEx", return_value=application
        ) as dispatch_ex, mock.patch(
            "win32com.client.GetActiveObject"
        ) as get_active:
            acquired, launched = native_renderer._acquire_application()

        self.assertIs(acquired, application)
        self.assertTrue(launched)
        dispatch_ex.assert_called_once_with("ChemDraw.Application")
        get_active.assert_not_called()

    def test_reports_invalid_native_output_with_stable_error_code(self):
        output = self.root / "output.png"
        application = _Application(_Document(invalid=True))

        with mock.patch(
            "cdxml_toolkit.mcp_runtime.native_renderer._acquire_application",
            return_value=(application, True),
        ):
            with self.assertRaises(native_renderer.NativeRenderError) as raised:
                native_renderer.render_cdxml(self.source, output, timeout_seconds=1)

        self.assertEqual(raised.exception.error_code, "native_output_invalid")

    def test_reused_application_is_not_quit_and_visibility_is_restored(self):
        output = self.root / "output.png"
        document = _Document()
        application = _Application(document)
        application.Visible = True

        with mock.patch(
            "cdxml_toolkit.mcp_runtime.native_renderer._acquire_application",
            return_value=(application, False),
        ):
            native_renderer.render_cdxml(self.source, output, timeout_seconds=2)

        self.assertEqual(application.quit_calls, 0)
        self.assertTrue(application.Visible)
        self.assertTrue(application.Preferences.TransparentPNGs)
        self.assertEqual(application.Preferences.PNGResolution, 72)

    def test_batch_session_reuses_one_application(self):
        first = self.root / "first.png"
        second = self.root / "second.png"
        document = _Document()
        application = _Application(document)

        with mock.patch(
            "cdxml_toolkit.mcp_runtime.native_renderer._acquire_application",
            return_value=(application, True),
        ) as acquire:
            with native_renderer.NativeRenderSession(timeout_seconds=2) as session:
                session.render(self.source, first)
                session.render(self.source, second)

        acquire.assert_called_once()
        self.assertEqual(application.quit_calls, 1)
        self.assertTrue(first.is_file())
        self.assertTrue(second.is_file())


if __name__ == "__main__":
    unittest.main()
