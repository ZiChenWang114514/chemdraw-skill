from __future__ import annotations

from pathlib import Path
import struct
import tempfile
import unittest
from unittest import mock

from PIL import Image

from cdxml_toolkit.chemdraw import mac_automation
from cdxml_toolkit.mcp_runtime import native_io, office_objects
from cdxml_toolkit.office import emf_preview, mac_office, ole_embedder


MINIMAL_PDF = (
    b"%PDF-1.7\n1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n"
    b"xref\n0 1\n0000000000 65535 f \ntrailer << /Root 1 0 R >>\nstartxref\n9\n%%EOF\n"
)
SAVED_CDXML = (
    '<?xml version="1.0" encoding="UTF-8" ?>'
    '<CDXML BoundingBox="10 20 110 70"><page id="1"/></CDXML>'
)


def write_png(path: Path, size=(30, 20), dpi=300) -> None:
    image = Image.new("RGBA", size, (0, 0, 0, 0))
    image.putpixel((0, 0), (255, 0, 0, 255))
    image.save(path, dpi=(dpi, dpi))


class BitmapEmfTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.png = Path(self.temp.name) / "p.png"

    def tearDown(self):
        self.temp.cleanup()

    def test_png_becomes_a_structurally_valid_emf(self):
        write_png(self.png)

        data = emf_preview.png_to_emf(self.png)

        self.assertTrue(native_io._is_structurally_valid_emf(data))
        self.assertEqual(struct.unpack_from("<I", data, 52)[0], 3)  # header, bitmap, EOF
        self.assertEqual(struct.unpack_from("<I", data, len(data) - 20)[0], 14)

    def test_frame_keeps_the_physical_size_of_the_picture(self):
        write_png(self.png, size=(300, 150), dpi=300)

        data = emf_preview.png_to_emf(self.png)

        # rclFrame is in 0.01 mm: 1 in x 0.5 in.
        self.assertEqual(struct.unpack_from("<iiii", data, 24), (0, 0, 2539, 1269))

    def test_bitmap_rows_are_bottom_up_bgr_on_white(self):
        write_png(self.png, size=(2, 2))

        data = emf_preview.png_to_emf(self.png)

        record = 108
        self.assertEqual(struct.unpack_from("<I", data, record)[0], 81)
        bits_offset = struct.unpack_from("<I", data, record + 56)[0]
        # Last stored row is the top row; its first pixel is red (B, G, R).
        top_row = data[record + bits_offset + 8: record + bits_offset + 11]
        self.assertEqual(top_row, bytes((0, 0, 255)))
        self.assertEqual(data[record + bits_offset: record + bits_offset + 3], b"\xff\xff\xff")


class SlidePreviewTests(unittest.TestCase):
    """Readers that take the VML ``mc:Choice`` (macOS Quick Look, PowerPoint for
    macOS without an OLE server) need the preview picture there too."""

    NS = {
        "mc": "http://schemas.openxmlformats.org/markup-compatibility/2006",
        "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
        "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    }

    def assert_both_branches_show_the_preview(self, element):
        for branch in ("mc:Choice", "mc:Fallback"):
            blips = element.findall(f"{branch}//p:oleObj/p:pic//a:blip", self.NS)
            self.assertEqual(len(blips), 1, branch)
        ids = [node.get("id") for node in element.iter("{%s}cNvPr" % self.NS["p"])]
        self.assertEqual(len(ids), len(set(ids)))

    def test_generated_slide(self):
        from lxml import etree

        slide = (
            '<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">'
            "<p:cSld><p:spTree/></p:cSld></p:sld>"
        )
        xml = ole_embedder._build_slide_xml(
            slide.encode(), {"width_emu": 100, "height_emu": 50}, 1
        )
        root = etree.fromstring(xml)
        self.assert_both_branches_show_the_preview(root.find(".//mc:AlternateContent", self.NS))

    def test_template_slide(self):
        from cdxml_toolkit.office import doc_from_template

        element = doc_from_template._make_pptx_ole_xml(1, 0, 0, 100, 50)
        self.assert_both_branches_show_the_preview(element)


VECTOR_SVG = (
    '<svg width="100px" height="50px" viewBox="0 0 100 50" xmlns="http://www.w3.org/2000/svg">'
    '<path fill="#000000" d="M 10,10 L 90,10 L 90,12 L 10,12 Z"/>'
    '<text x="0" y="0" fill="#000000" transform="matrix(0.05 0 0 0.05 40 40)" '
    'font-size="200px" font-family="Arial">OH</text></svg>'
)


def emf_record_types(data: bytes) -> list[int]:
    offset, kinds = 0, []
    while offset < len(data):
        kind, size = struct.unpack_from("<II", data, offset)
        kinds.append(kind)
        offset += size
    return kinds


class FakeSession:
    svg = VECTOR_SVG

    def __init__(self, *args, **kwargs):
        self.exports = []
        self.closed = False

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.closed = True

    def export(self, source, *destinations):
        self.exports.append((Path(source), [Path(item) for item in destinations]))
        for destination in map(Path, destinations):
            if destination.suffix == ".cdx":
                destination.write_bytes(b"VjCD0100" + b"\0" * 24)
            elif destination.suffix == ".cdxml":
                destination.write_text(SAVED_CDXML, encoding="utf-8")
            elif destination.suffix == ".png":
                write_png(destination)
            elif destination.suffix == ".svg":
                destination.write_text(self.svg, encoding="utf-8")
        return [str(item) for item in destinations]


class BatchConvertOnMacTests(unittest.TestCase):
    def convert(self, session):
        with tempfile.TemporaryDirectory() as temp, \
                mock.patch.object(mac_automation, "is_macos", return_value=True), \
                mock.patch.object(mac_automation, "MacChemDrawSession", return_value=session):
            source = Path(temp) / "scheme.cdxml"
            source.write_text(SAVED_CDXML, encoding="utf-8")
            return ole_embedder.batch_convert([str(source)])

    def test_chemdraw_for_macos_supplies_cdx_vector_preview_and_bbox(self):
        session = FakeSession()
        results = self.convert(session)

        self.assertEqual(len(results), 1)
        item = results[0]
        self.assertEqual(item["name"], "scheme")
        self.assertTrue(item["cdx_data"].startswith(b"VjCD0100"))
        self.assertTrue(native_io._is_structurally_valid_emf(item["emf_data"]))
        kinds = emf_record_types(item["emf_data"])
        self.assertIn(62, kinds)  # EMR_FILLPATH
        self.assertIn(84, kinds)  # EMR_EXTTEXTOUTW
        self.assertNotIn(81, kinds)  # no bitmap
        self.assertEqual(item["content_bbox"], (10.0, 20.0, 110.0, 70.0))
        self.assertEqual([path.suffix for path in session.exports[0][1]], [".cdx", ".cdxml", ".png", ".svg"])
        self.assertTrue(session.closed)

    def test_drawings_the_vector_converter_cannot_reproduce_get_a_bitmap_preview(self):
        session = FakeSession()
        session.svg = VECTOR_SVG.replace("L 90,12", "A 5 5 0 0 1 90,12")

        item = self.convert(session)[0]

        self.assertTrue(native_io._is_structurally_valid_emf(item["emf_data"]))
        self.assertEqual(emf_record_types(item["emf_data"]), [1, 81, 14])


class OfficeHelpersOnMacTests(unittest.TestCase):
    def setUp(self):
        self.container = tempfile.TemporaryDirectory()
        patches = [
            mock.patch.object(office_objects.sys, "platform", "darwin"),
            mock.patch.object(mac_office, "OFFICE_GROUP_CONTAINER", Path(self.container.name)),
            mock.patch.object(mac_automation, "application_pid", return_value=None),
            mock.patch.object(mac_automation, "launch_hidden", return_value=4242),
            mock.patch.object(mac_automation, "LAUNCH_REGISTRY", Path(self.container.name) / "launched"),
        ]
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)
        self.addCleanup(self.container.cleanup)

    def test_com_apartment_is_not_needed_off_windows(self):
        with office_objects.com_apartment():
            pass

    def test_office_stuck_on_a_dialog_is_stopped_and_reported(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "doc.docx"
            source.write_bytes(b"docx")
            stuck = mac_automation.MacAutomationError("native_timeout", "slow")
            with mock.patch.object(mac_automation, "run_applescript", side_effect=stuck), \
                    mock.patch.object(mac_automation, "terminate_process") as terminate:
                with self.assertRaises(mac_office.OfficeAutomationError) as caught:
                    mac_office.export_pdf(source, Path(temp) / "doc.pdf")

        self.assertEqual(caught.exception.error_code, "office_not_ready")
        terminate.assert_called_once_with(4242)
        self.assertEqual(list(Path(self.container.name).rglob("*.docx")), [])

    def test_users_own_office_is_never_stopped(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "deck.pptx"
            source.write_bytes(b"pptx")
            stuck = mac_automation.MacAutomationError("native_timeout", "slow")
            with mock.patch.object(mac_automation, "run_applescript", side_effect=stuck) as run, \
                    mock.patch.object(mac_automation, "application_pid", return_value=99), \
                    mock.patch.object(mac_automation, "launch_hidden") as launch, \
                    mock.patch.object(mac_automation, "terminate_process") as terminate:
                with self.assertRaises(mac_office.OfficeAutomationError):
                    mac_office.export_pdf(source, Path(temp) / "deck.pdf")

        launch.assert_not_called()
        terminate.assert_not_called()
        self.assertEqual(run.call_args.args[1][3], "keep")

    def test_pdf_export_drives_word_through_applescript(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "doc.docx"
            source.write_bytes(b"docx")
            destination = Path(temp) / "doc.pdf"

            def fake_script(script, args, timeout_seconds):
                self.assertIn('com.microsoft.Word', script)
                self.assertEqual(args[3], "quit")
                Path(args[1]).write_bytes(MINIMAL_PDF)
                return ""

            with mock.patch.object(mac_automation, "run_applescript", side_effect=fake_script) as run:
                office_objects.render_office_pdf(source, destination)

            self.assertTrue(destination.read_bytes().startswith(b"%PDF-"))
            self.assertEqual(Path(run.call_args.args[1][0]).suffix, ".docx")

    def test_pdf_export_drives_powerpoint_for_presentations(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "deck.pptx"
            source.write_bytes(b"pptx")
            destination = Path(temp) / "deck.pdf"

            def fake_script(script, args, timeout_seconds):
                self.assertIn('com.microsoft.Powerpoint', script)
                Path(args[1]).write_bytes(MINIMAL_PDF)
                return ""

            with mock.patch.object(mac_automation, "run_applescript", side_effect=fake_script):
                office_objects.render_office_pdf(source, destination)

            self.assertTrue(destination.is_file())

    def test_each_export_opens_a_document_no_one_else_has_open(self):
        # Office finds the opened document by name: a fixed name would export, and
        # close unsaved, a document of the same name the user has open.
        names = []
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "document.docx"
            source.write_bytes(b"docx")

            def fake_script(script, args, timeout_seconds):
                names.append(args[2])
                self.assertEqual(Path(args[0]).name, args[2])
                Path(args[1]).write_bytes(MINIMAL_PDF)
                return ""

            with mock.patch.object(mac_automation, "run_applescript", side_effect=fake_script):
                for _ in range(2):
                    mac_office.export_pdf(source, Path(temp) / "doc.pdf")

        self.assertNotEqual(names[0], names[1])
        self.assertNotIn("document.docx", names)
        self.assertTrue(all(name.endswith(".docx") for name in names))


if __name__ == "__main__":
    unittest.main()
