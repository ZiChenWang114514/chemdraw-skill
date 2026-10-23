from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
from unittest import mock

from cdxml_toolkit.chemdraw import cdx_converter, mac_automation


CDX_BYTES = b"VjCD0100" + b"\x00" * 24
CDXML_TEXT = '<?xml version="1.0" encoding="UTF-8" ?><CDXML><page/></CDXML>'


def _fake_convert(source, destination, **_kwargs):
    destination = Path(destination)
    if destination.suffix == ".cdx":
        destination.write_bytes(CDX_BYTES)
    else:
        destination.write_text(CDXML_TEXT, encoding="utf-8")
    return str(destination)


class _FakeSession:
    instances: list = []

    def __init__(self, **_kwargs):
        self.exports = []
        type(self).instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        return False

    def export(self, source, *destinations):
        self.exports.append(source)
        return [_fake_convert(source, destination) for destination in destinations]


class MacConverterTests(unittest.TestCase):
    def test_applescript_backend_is_registered_for_every_conversion(self):
        self.assertIn("applescript", cdx_converter._FILE_CONVERTERS)
        self.assertIn("applescript", cdx_converter._CDX_TO_CDXML)
        self.assertIn("applescript", cdx_converter._CDXML_TO_CDX)

    def test_macos_prefers_chemdraw_before_other_backends(self):
        order = cdx_converter._backend_order(is_macos=True)
        self.assertEqual(order[0], "applescript")
        self.assertEqual(cdx_converter._backend_order(is_macos=False)[0], "com")

    def test_cdx_bytes_round_trip_through_chemdraw_for_macos(self):
        with mock.patch.object(mac_automation, "convert_file", side_effect=_fake_convert):
            cdxml = cdx_converter._mac_cdx_to_cdxml(CDX_BYTES)
            cdx = cdx_converter._mac_cdxml_to_cdx(CDXML_TEXT)

        self.assertIn("<CDXML>", cdxml)
        self.assertEqual(cdx[:8], b"VjCD0100")

    def test_batch_conversion_reuses_one_chemdraw_session(self):
        _FakeSession.instances = []
        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory) / "a.cdx"
            second = Path(directory) / "b.cdxml"
            first.write_bytes(CDX_BYTES)
            second.write_text(CDXML_TEXT, encoding="utf-8")
            with mock.patch.object(mac_automation, "MacChemDrawSession", _FakeSession), mock.patch.dict(
                cdx_converter._FILE_CONVERTERS, {"applescript": cdx_converter._mac_convert_file}
            ):
                results = cdx_converter.batch_convert_files([str(first), str(second)], method="applescript")

            self.assertEqual(len(_FakeSession.instances), 1)
            self.assertEqual(results[str(first)]["output"], str(first.with_suffix(".cdxml")))
            self.assertEqual(results[str(second)]["output"], str(second.with_suffix(".cdx")))
            self.assertTrue(first.with_suffix(".cdxml").is_file())


class _PngSession(_FakeSession):
    def export(self, source, *destinations):
        from PIL import Image

        self.exports.append(source)
        for destination in destinations:
            Image.new("RGBA", (40, 20), (0, 0, 0, 0)).save(destination, dpi=(300, 300))
        return [str(destination) for destination in destinations]


class MacImageRenderTests(unittest.TestCase):
    def setUp(self):
        from cdxml_toolkit.chemdraw import cdxml_to_image

        self.module = cdxml_to_image
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.sources = []
        for name in ("a.cdxml", "b.cdxml"):
            path = self.root / name
            path.write_text(CDXML_TEXT, encoding="utf-8")
            self.sources.append(str(path))
        _PngSession.instances = []
        patches = [
            mock.patch.object(cdxml_to_image, "is_macos", return_value=True),
            mock.patch.object(cdxml_to_image, "MacChemDrawSession", _PngSession),
        ]
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)

    def tearDown(self):
        self.temp.cleanup()

    def test_single_render_uses_chemdraw_for_macos_with_white_background(self):
        from PIL import Image

        output = self.module.cdxml_to_image(self.sources[0], png_dpi=150)

        with Image.open(output) as image:
            self.assertEqual(image.mode, "RGB")
            self.assertEqual(image.size, (20, 10))
            self.assertEqual(image.getpixel((0, 0)), (255, 255, 255))

    def test_batch_render_reuses_one_session(self):
        results = self.module.batch_render(self.sources)

        self.assertEqual(len(_PngSession.instances), 1)
        self.assertTrue(all(info["error"] is None for info in results.values()))


if __name__ == "__main__":
    unittest.main()
