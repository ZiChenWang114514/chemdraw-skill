from __future__ import annotations

from pathlib import Path
import shutil
import tempfile
import unittest
from unittest import mock
import xml.etree.ElementTree as ET

from cdxml_toolkit.chemdraw import mac_automation
from cdxml_toolkit.deterministic_pipeline.legacy import eln_cdx_cleanup, scheme_polisher


ELN_CDXML = (
    '<?xml version="1.0" encoding="UTF-8" ?>'
    '<CDXML BondLength="30" LabelFont="3" LabelSize="12"><fonttable>'
    '<font id="3" charset="iso-8859-1" name="Times New Roman"/></fonttable>'
    '<page id="1"><fragment id="2">'
    '<n id="3" p="100 200"/><n id="4" p="130 200" Element="8">'
    '<t p="130 200"><s font="3" size="12" face="0">O</s></t></n>'
    '<b id="5" B="3" E="4"/></fragment>'
    '<t id="6" p="100 250"><s font="3" size="12" face="0">reflux, 2 h</s></t>'
    '</page></CDXML>'
)


class FakeSession:
    def __init__(self, *args, **kwargs):
        self.calls = []

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def clean(self, source, destination, *, reaction=False):
        self.calls.append(("clean", reaction, Path(source).read_text(encoding="utf-8")))
        shutil.copyfile(source, destination)
        return str(destination)

    def apply_menu(self, source, destination, *commands, select_all=True):
        self.calls.append(("menu", commands, select_all))
        shutil.copyfile(source, destination)
        return str(destination)


class LegacyCleanupOnMacTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.session = FakeSession()
        for patch in (
            mock.patch.object(mac_automation, "is_macos", return_value=True),
            mock.patch.object(mac_automation, "MacChemDrawSession", return_value=self.session),
        ):
            patch.start()
            self.addCleanup(patch.stop)

    def test_eln_cleanup_applies_acs_style_fonts_then_both_chemdraw_cleanups(self):
        source = self.root / "eln.cdxml"
        source.write_text(ELN_CDXML, encoding="utf-8")
        output = self.root / "out.cdxml"

        eln_cdx_cleanup.cleanup_eln_cdx(str(source), str(output), scale_factor=1.0)

        self.assertEqual([(kind, flag) for kind, flag, _ in self.session.calls],
                         [("clean", False), ("clean", True)])
        styled = ET.fromstring(self.session.calls[0][2])
        self.assertEqual(styled.get("BondLength"), "14.40")
        self.assertEqual([n.get("p") for n in styled.iter("n")], ["100 200", "130 200"])
        arial = next(f.get("id") for f in styled.iter("font") if f.get("name") == "Arial")
        self.assertEqual((styled.get("LabelFont"), styled.get("LabelSize"), styled.get("LabelFace")),
                         (arial, "10", "96"))
        caption = next(t for t in styled.iter("t") if t.get("id") == "6").find("s")
        self.assertEqual((caption.get("font"), caption.get("size"), caption.get("face")), (arial, "10", "96"))
        label = styled.find(".//n/t/s")
        self.assertEqual(label.get("font"), "3")  # atom labels follow LabelFont, not caption styling
        self.assertTrue(output.is_file())

    def test_eln_cleanup_applies_a_custom_style_sheet_on_macos(self):
        from .test_style_sheet import write_style_sheet

        source = self.root / "eln.cdxml"
        source.write_text(ELN_CDXML, encoding="utf-8")
        sheet = self.root / "journal.cds"
        write_style_sheet(sheet, bond_length=17.0)

        eln_cdx_cleanup.cleanup_eln_cdx(str(source), str(self.root / "out.cdxml"),
                                        scale_factor=1.0, style_path=str(sheet))

        styled = ET.fromstring(self.session.calls[0][2])
        self.assertEqual((styled.get("BondLength"), styled.get("LineWidth")), ("17", "0.75"))
        # As ApplySettings on Windows: settings change, coordinates (already scaled
        # by scale_factor) are left to Clean Up.
        self.assertEqual([n.get("p") for n in styled.iter("n")], ["100 200", "130 200"])

    def test_eln_cdx_input_is_converted_by_chemdraw_for_macos(self):
        source = self.root / "eln.cdx"
        source.write_bytes(b"VjCD0100" + b"\0" * 24)

        def convert(cdx, cdxml, **_kwargs):
            Path(cdxml).write_text(ELN_CDXML, encoding="utf-8")
            return str(cdxml)

        with mock.patch.object(mac_automation, "convert_file", side_effect=convert) as converted:
            eln_cdx_cleanup.cleanup_eln_cdx(str(source), str(self.root / "out.cdxml"), scale_factor=1.0)

        self.assertEqual(Path(converted.call_args.args[0]), source)

    def test_scheme_polisher_runs_clean_up_reaction_three_times(self):
        source = self.root / "scheme.cdxml"
        source.write_text(ELN_CDXML, encoding="utf-8")
        output = self.root / "polished.cdxml"

        scheme_polisher._chemdraw_cleanup_reaction(str(source), str(output))

        self.assertEqual(self.session.calls, [("menu", (("Structure", "Clean Up Reaction"),) * 3, True)])
        self.assertTrue(output.is_file())


if __name__ == "__main__":
    unittest.main()
