from __future__ import annotations

from pathlib import Path
import struct
import tempfile
import unittest
import xml.etree.ElementTree as ET

from cdxml_toolkit.chemdraw import style_sheet


def _property(tag: int, value: bytes) -> bytes:
    return struct.pack("<HH", tag, len(value)) + value


def _coordinate(points: float) -> bytes:
    return struct.pack("<i", round(points * 65536))


def write_style_sheet(path: Path, *, bond_length=17.0, label=("Arial", 12), caption=("Times New Roman", 10)) -> None:
    """A ChemDraw style sheet: a CDX document carrying only drawing settings."""
    fonts = [(3, 1252, label[0]), (4, 1252, caption[0])]
    table = struct.pack("<HH", 0, len(fonts)) + b"".join(
        struct.pack("<HHH", font_id, charset, len(name)) + name.encode("latin-1")
        for font_id, charset, name in fonts
    )
    body = b"".join((
        _property(0x0003, b"\0\0ChemDraw 25.1.0.0"),
        _property(0x0100, table),
        _property(0x0803, struct.pack("<i", 120 * 65536)),
        _property(0x0804, struct.pack("<h", 180)),
        _property(0x0805, _coordinate(bond_length)),
        _property(0x0806, _coordinate(2.6)),
        _property(0x0807, _coordinate(0.75)),
        _property(0x0808, _coordinate(2.0)),
        _property(0x0809, _coordinate(2.6)),
        _property(0x080A, struct.pack("<HHHH", 3, 96, label[1] * 20, 3)),
        _property(0x080B, struct.pack("<HHHH", 4, 0, caption[1] * 20, 3)),
        # A nested page object; its properties are not document settings.
        struct.pack("<HI", 0x8001, 7), _property(0x0805, _coordinate(99.0)), b"\0\0",
    ))
    header = b"VjCD0100" + struct.pack("<I", 0x01020304) + b"\0" * 10
    path.write_bytes(header + struct.pack("<HI", 0x8000, 0) + body + b"\0\0")


CDXML = (
    '<?xml version="1.0" encoding="UTF-8" ?>'
    '<CDXML BondLength="34" LabelFont="3"><fonttable>'
    '<font id="3" charset="iso-8859-1" name="Arial"/></fonttable>'
    '<page id="1" BoundingBox="0 0 340 340"><fragment id="2">'
    '<n id="3" p="100 200"/><n id="4" p="134 200"/><b id="5" B="3" E="4"/>'
    '</fragment></page></CDXML>'
)


class StyleSheetTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "journal.cds"

    def test_reads_document_settings_in_cdxml_units(self):
        write_style_sheet(self.path)

        style = style_sheet.read_style_sheet(self.path)

        self.assertEqual(style["attributes"], {
            "BondLength": "17", "BoldWidth": "2.6", "LineWidth": "0.75", "MarginWidth": "2",
            "HashSpacing": "2.6", "ChainAngle": "120", "BondSpacing": "18",
            "LabelFace": "96", "LabelSize": "12", "CaptionFace": "0", "CaptionSize": "10",
        })
        self.assertEqual(style["fonts"], {"label": ("Arial", "iso-8859-1"),
                                          "caption": ("Times New Roman", "iso-8859-1")})

    def test_rejects_files_that_are_not_style_sheets(self):
        self.path.write_bytes(b"<CDXML/>")

        with self.assertRaises(style_sheet.StyleSheetError):
            style_sheet.read_style_sheet(self.path)

    def test_apply_sets_settings_fonts_and_rescales_to_the_new_bond_length(self):
        write_style_sheet(self.path)

        root = ET.fromstring(style_sheet.apply_style_sheet(CDXML, style_sheet.read_style_sheet(self.path)))

        self.assertEqual((root.get("BondLength"), root.get("LineWidth"), root.get("LabelSize")), ("17", "0.75", "12"))
        fonts = {font.get("name"): font.get("id") for font in root.iter("font")}
        self.assertEqual(root.get("LabelFont"), fonts["Arial"])
        self.assertEqual(root.get("CaptionFont"), fonts["Times New Roman"])
        self.assertEqual([n.get("p") for n in root.iter("n")], ["50.00 100.00", "67.00 100.00"])

    def test_bundled_acs_document_1996_matches_the_toolkit_acs_settings(self):
        bundled = Path("/Applications/ChemDraw.app/Contents/Resources/SpecialPurpose/Stationery/ACS Document 1996.cds")
        if not bundled.is_file():
            self.skipTest("ChemDraw for macOS is not installed")
        from cdxml_toolkit.constants import ACS_STYLE

        attributes = style_sheet.read_style_sheet(bundled)["attributes"]

        for name in ("BondLength", "LineWidth", "MarginWidth", "HashSpacing", "BondSpacing", "BoldWidth"):
            self.assertAlmostEqual(float(attributes[name]), float(ACS_STYLE[name]), delta=0.02, msg=name)


if __name__ == "__main__":
    unittest.main()
