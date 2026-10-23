from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
from unittest import mock

from PIL import Image

from cdxml_toolkit.chemdraw import mac_automation
from cdxml_toolkit.mcp_runtime import native_io, native_renderer


CDXML_WITH_WINDOWS_FONTS = (
    '<?xml version="1.0" encoding="UTF-8" ?>\n'
    '<!DOCTYPE CDXML SYSTEM "http://www.cambridgesoft.com/xml/cdxml.dtd" >\n'
    '<CDXML><fonttable>'
    '<font id="3" charset="iso-8859-1" name="Arial"/>'
    '<font id="5" charset="Unicode" name="SimSun"/>'
    '<font id="6" charset="iso-8859-1" name="Calibri"/>'
    '<font id="7" charset="Unicode" name="&#x5B8B;&#x4F53;"/>'
    '</fonttable><page><t><s font="5">反应</s></t></page></CDXML>'
)

MAC_FAMILIES = frozenset({"Arial", "Helvetica", "Helvetica Neue", "Songti SC", "PingFang SC", "Times New Roman"})


class FontSubstitutionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "input.cdxml"
        self.path.write_text(CDXML_WITH_WINDOWS_FONTS, encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def test_missing_windows_fonts_are_mapped_to_installed_mac_fonts(self):
        changes = mac_automation.substitute_missing_fonts(self.path, available=MAC_FAMILIES)

        text = self.path.read_text(encoding="utf-8")
        self.assertIn('name="Songti SC"', text)
        self.assertIn('name="Helvetica Neue"', text)
        self.assertNotIn("SimSun", text)
        self.assertNotIn("Calibri", text)
        self.assertEqual(
            changes,
            {"SimSun": "Songti SC", "Calibri": "Helvetica Neue", "宋体": "Songti SC"},
        )

    def test_installed_fonts_and_document_content_are_preserved(self):
        mac_automation.substitute_missing_fonts(self.path, available=MAC_FAMILIES)

        text = self.path.read_text(encoding="utf-8")
        self.assertIn('name="Arial"', text)
        self.assertIn("<!DOCTYPE CDXML", text)
        self.assertIn('<s font="5">反应</s>', text)

    def test_unknown_missing_font_falls_back_by_charset(self):
        self.path.write_text(
            '<CDXML><fonttable><font id="1" charset="Unicode" name="Unknown CJK"/>'
            '<font id="2" charset="iso-8859-1" name="Unknown Latin"/></fonttable></CDXML>',
            encoding="utf-8",
        )

        changes = mac_automation.substitute_missing_fonts(self.path, available=MAC_FAMILIES)

        self.assertEqual(changes, {"Unknown CJK": "PingFang SC", "Unknown Latin": "Helvetica"})

    def test_document_without_missing_fonts_is_not_rewritten(self):
        original = '<CDXML><fonttable><font id="3" charset="iso-8859-1" name="Arial"/></fonttable></CDXML>'
        self.path.write_text(original, encoding="utf-8")

        self.assertEqual(mac_automation.substitute_missing_fonts(self.path, available=MAC_FAMILIES), {})
        self.assertEqual(self.path.read_text(encoding="utf-8"), original)

    def test_staging_substitutes_fonts_only_on_macos(self):
        with mock.patch.object(mac_automation, "is_macos", return_value=False):
            native_io.normalize_cdxml_staging(self.path)
        self.assertIn("SimSun", self.path.read_text(encoding="utf-8"))

        with mock.patch.object(mac_automation, "is_macos", return_value=True), mock.patch.object(
            mac_automation, "installed_font_families", return_value=MAC_FAMILIES
        ):
            native_io.normalize_cdxml_staging(self.path)
        self.assertNotIn("SimSun", self.path.read_text(encoding="utf-8"))


class AutomationHelpersTests(unittest.TestCase):
    def test_save_types_follow_destination_extension(self):
        self.assertEqual(mac_automation.save_type_for(Path("a.PNG")), "PNG")
        self.assertEqual(mac_automation.save_type_for(Path("a.cdxml")), "ChemDraw XML")
        self.assertEqual(mac_automation.save_type_for(Path("a.cdx")), "ChemDraw")

    def test_unsupported_format_has_stable_error_code(self):
        with self.assertRaises(mac_automation.MacAutomationError) as raised:
            mac_automation.save_type_for(Path("a.emf"))
        self.assertEqual(raised.exception.error_code, "native_format_unsupported")

    def test_denied_automation_permission_is_classified(self):
        error = mac_automation._classify(1, "execution error: Not authorized to send Apple events (-1743)")
        self.assertEqual(error.error_code, "chemdraw_automation_not_authorized")

    def test_apple_event_timeout_is_classified(self):
        error = mac_automation._classify(1, "execution error: AppleEvent timed out. (-1712)")
        self.assertEqual(error.error_code, "native_timeout")

    def test_flatten_png_removes_transparency_and_applies_dpi(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "render.png"
            Image.new("RGBA", (20, 10), (0, 0, 0, 0)).save(path, dpi=(300, 300))

            mac_automation.flatten_png(path, dpi=150)

            with Image.open(path) as image:
                self.assertEqual(image.mode, "RGB")
                self.assertEqual(image.size, (10, 5))
                self.assertEqual(image.getpixel((0, 0)), (255, 255, 255))
                self.assertAlmostEqual(image.info["dpi"][0], 150, places=0)


class _FakeSession:
    instances: list = []

    def __init__(self, *, timeout_seconds):
        self.timeout_seconds = timeout_seconds
        self.exports = []
        self.closed = False
        _FakeSession.instances.append(self)

    def export(self, source, *destinations):
        self.exports.append((Path(source), [Path(d) for d in destinations]))
        for destination in destinations:
            if Path(destination).suffix == ".svg":
                Path(destination).write_text('<svg xmlns="http://www.w3.org/2000/svg"/>', encoding="utf-8")
            else:
                Image.new("RGBA", (30, 12), (0, 0, 0, 0)).save(destination, dpi=(300, 300))
        return [str(d) for d in destinations]

    def close(self):
        self.closed = True


class MacNativeRendererTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.source = self.root / "source.cdxml"
        self.source.write_text("<CDXML><page/></CDXML>", encoding="utf-8")
        _FakeSession.instances = []

    def tearDown(self):
        self.temp.cleanup()

    def test_render_uses_chemdraw_for_macos_and_white_background(self):
        output = self.root / "output.png"
        with mock.patch.object(mac_automation, "is_macos", return_value=True), mock.patch.object(
            mac_automation, "MacChemDrawSession", _FakeSession
        ):
            result = native_renderer.render_cdxml(self.source, output, timeout_seconds=5)

        self.assertEqual(result, str(output.resolve()))
        session = _FakeSession.instances[0]
        self.assertTrue(session.closed)
        with Image.open(output) as image:
            self.assertEqual(image.mode, "RGB")
            self.assertEqual(image.getpixel((0, 0)), (255, 255, 255))

    def test_batch_session_reuses_one_macos_application(self):
        with mock.patch.object(mac_automation, "is_macos", return_value=True), mock.patch.object(
            mac_automation, "MacChemDrawSession", _FakeSession
        ):
            with native_renderer.NativeRenderSession(timeout_seconds=5) as session:
                session.render(self.source, self.root / "first.png")
                session.render(self.source, self.root / "second.svg")

        self.assertEqual(len(_FakeSession.instances), 1)
        self.assertEqual(len(_FakeSession.instances[0].exports), 2)
        self.assertTrue(_FakeSession.instances[0].closed)

    def test_macos_errors_keep_stable_codes(self):
        class _Denied(_FakeSession):
            def export(self, source, *destinations):
                raise mac_automation.MacAutomationError("chemdraw_automation_not_authorized", "denied")

        with mock.patch.object(mac_automation, "is_macos", return_value=True), mock.patch.object(
            mac_automation, "MacChemDrawSession", _Denied
        ):
            with self.assertRaises(native_renderer.NativeRenderError) as raised:
                native_renderer.render_cdxml(self.source, self.root / "x.png", timeout_seconds=5)

        self.assertEqual(raised.exception.error_code, "chemdraw_automation_not_authorized")


if __name__ == "__main__":
    unittest.main()
