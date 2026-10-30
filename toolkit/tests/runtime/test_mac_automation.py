from __future__ import annotations

import os
from pathlib import Path
import struct
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
    '</fonttable><page><t><s font="5">\u53cd\u5e94</s></t></page></CDXML>'
)

_REGISTRY = tempfile.TemporaryDirectory()
_REGISTRY_PATCH = mock.patch.object(mac_automation, "LAUNCH_REGISTRY", Path(_REGISTRY.name))


def setUpModule():
    # Session launches in these tests must never touch the user's launch registry.
    _REGISTRY_PATCH.start()


def tearDownModule():
    _REGISTRY_PATCH.stop()
    _REGISTRY.cleanup()


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
            {"SimSun": "Songti SC", "Calibri": "Helvetica Neue", "\u5b8b\u4f53": "Songti SC"},
        )

    def test_installed_fonts_and_document_content_are_preserved(self):
        mac_automation.substitute_missing_fonts(self.path, available=MAC_FAMILIES)

        text = self.path.read_text(encoding="utf-8")
        self.assertIn('name="Arial"', text)
        self.assertIn("<!DOCTYPE CDXML", text)
        self.assertIn('<s font="5">\u53cd\u5e94</s>', text)

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


def _cdx_with_fonts(fonts) -> bytes:
    """A minimal CDX: document > font table, one page with a caption property, end."""
    table = struct.pack("<HH", 0, len(fonts))
    for font_id, charset, name in fonts:
        raw = name.encode("cp936" if charset == 936 else "latin-1")
        table += struct.pack("<HHH", font_id, charset, len(raw)) + raw
    header = b"VjCD0100" + struct.pack("<I", 0x01020304) + bytes(10)
    page = struct.pack("<HI", 0x8001, 2) + struct.pack("<HH", 0x0700, 3) + b"abc" + b"\0\0"
    return (header + struct.pack("<HI", 0x8000, 1) + struct.pack("<HH", 0x0100, len(table)) + table
            + page + b"\0\0")


class CdxFontSubstitutionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "input.cdx"

    def tearDown(self):
        self.temp.cleanup()

    def _fonts(self):
        from cdxml_toolkit.chemdraw import style_sheet

        properties = style_sheet._document_properties(self.path.read_bytes())
        return {font_id: name for font_id, (name, _charset) in style_sheet._font_table(properties[0x0100]).items()}

    def test_missing_fonts_in_a_binary_cdx_are_renamed(self):
        self.path.write_bytes(_cdx_with_fonts(
            [(3, 1252, "Arial"), (5, 936, "SimSun"), (6, 936, "\u5b8b\u4f53"), (7, 1252, "Calibri")]))

        changes = mac_automation.substitute_missing_fonts(self.path, available=MAC_FAMILIES)

        self.assertEqual(changes, {"SimSun": "Songti SC", "\u5b8b\u4f53": "Songti SC", "Calibri": "Helvetica Neue"})
        self.assertEqual(self._fonts(), {3: "Arial", 5: "Songti SC", 6: "Songti SC", 7: "Helvetica Neue"})
        # Objects after the font table are kept byte for byte.
        self.assertTrue(self.path.read_bytes().endswith(_cdx_with_fonts([])[-16:]))

    def test_cdx_without_missing_fonts_is_not_rewritten(self):
        original = _cdx_with_fonts([(3, 1252, "Arial")])
        self.path.write_bytes(original)

        self.assertEqual(mac_automation.substitute_missing_fonts(self.path, available=MAC_FAMILIES), {})
        self.assertEqual(self.path.read_bytes(), original)

    def test_staging_substitutes_cdx_fonts_on_macos(self):
        self.path.write_bytes(_cdx_with_fonts([(5, 936, "SimSun")]))
        with mock.patch.object(mac_automation, "is_macos", return_value=True), mock.patch.object(
            mac_automation, "installed_font_families", return_value=MAC_FAMILIES
        ):
            native_io.normalize_cdxml_staging(self.path)
        self.assertEqual(self._fonts(), {5: "Songti SC"})


class AutomationHelpersTests(unittest.TestCase):
    def test_process_probes_never_signal_on_windows(self):
        # On Windows os.kill(pid, 0) terminates the process instead of probing it.
        refused = mock.Mock(side_effect=AssertionError("os.kill on Windows"))
        with mock.patch.object(mac_automation.sys, "platform", "win32"), \
                mock.patch.object(mac_automation.os, "kill", refused):
            self.assertFalse(mac_automation._pid_alive(4242))
            mac_automation.terminate_process(4242, grace_seconds=0)
        refused.assert_not_called()

    def test_a_chemdraw_exe_that_points_nowhere_finds_no_chemdraw(self):
        # The offline evaluation points CHEMDRAW_EXE at a missing file to keep the user's ChemDraw out.
        find_application = getattr(mac_automation, "unguarded_find_application", mac_automation.find_application)
        with tempfile.TemporaryDirectory() as folder:
            app = Path(folder) / "ChemDraw.app"
            (app / "Contents").mkdir(parents=True)
            with mock.patch.dict(os.environ, {"CHEMDRAW_EXE": str(app / "Contents" / "MacOS" / "ChemDraw")}):
                self.assertEqual(find_application(), app)
            missing = Path(folder) / "no-chemdraw-here" / "ChemDraw.exe"
            with mock.patch.dict(os.environ, {"CHEMDRAW_EXE": str(missing)}), \
                    mock.patch.object(mac_automation.subprocess, "run",
                                      side_effect=AssertionError("searched for an installed ChemDraw")):
                self.assertIsNone(find_application())

    def test_save_types_follow_destination_extension(self):
        self.assertEqual(mac_automation.save_type_for(Path("a.PNG")), "PNG")
        self.assertEqual(mac_automation.save_type_for(Path("a.cdxml")), "ChemDraw XML")
        self.assertEqual(mac_automation.save_type_for(Path("a.cdx")), "ChemDraw")

    def test_unsupported_format_has_stable_error_code(self):
        with self.assertRaises(mac_automation.MacAutomationError) as raised:
            mac_automation.save_type_for(Path("a.emf"))
        self.assertEqual(raised.exception.error_code, "native_format_unsupported")

    def test_style_sheets_are_never_opened_in_chemdraw(self):
        # ChemDraw opens stationery as an untitled document that stays behind.
        with tempfile.TemporaryDirectory() as directory:
            sheet = Path(directory) / "ACS Document 1996.cds"
            sheet.write_bytes(b"VjCD0100")
            session = mac_automation.MacChemDrawSession()
            with self.assertRaises(mac_automation.MacAutomationError) as raised:
                session._openable(sheet, Path(directory))
        self.assertEqual(raised.exception.error_code, "native_format_unsupported")

    def test_each_run_opens_a_document_with_a_name_of_its_own(self):
        # ChemDraw refers to a document by its name: with a fixed name, a document
        # left open (or the user's own input.cdxml) is the one saved and closed.
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "input.cdxml"
            source.write_text("<CDXML/>", encoding="utf-8")
            session = mac_automation.MacChemDrawSession()
            for name in "ab":
                (Path(directory) / name).mkdir()
            first = session._openable(source, Path(directory) / "a")
            second = session._openable(source, Path(directory) / "b")
        self.assertNotEqual(first.name, second.name)
        self.assertNotEqual(first.name, "input.cdxml")
        self.assertEqual(first.suffix, ".cdxml")

    def test_emf_destinations_are_converted_from_chemdraws_svg_export(self):
        svg = ('<svg width="20px" height="10px" xmlns="http://www.w3.org/2000/svg">'
               '<path d="M 1,1 L 19,1 L 19,2 Z"/></svg>')

        def run_steps(source, steps, **_kwargs):
            for index, step in enumerate(steps):
                if step == "save":
                    target = Path(steps[index + 1])
                    if target.suffix == ".svg":
                        target.write_text(svg, encoding="utf-8")
                    elif target.suffix == ".png":
                        Image.new("RGB", (4, 2), "white").save(target, dpi=(300, 300))
                    else:
                        target.write_text("<CDXML/>", encoding="utf-8")
            return []

        with tempfile.TemporaryDirectory() as directory:
            session = mac_automation.MacChemDrawSession()
            out = Path(directory)
            with mock.patch.object(session, "run_steps", side_effect=run_steps) as ran:
                written = session.export(out / "in.cdxml", out / "a.emf", out / "b.cdxml")
            data = (out / "a.emf").read_bytes()
            saved_types = [steps[i + 2] for steps in [ran.call_args.args[1]]
                           for i, step in enumerate(steps) if step == "save"]

        self.assertEqual(written, [str((out / "a.emf").resolve()), str((out / "b.cdxml").resolve())])
        self.assertEqual(data[40:44], b" EMF")
        self.assertIn(struct.pack("<I", 62), data)  # EMR_FILLPATH: a vector metafile
        self.assertNotIn("EMF", " ".join(saved_types))

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


class SessionLaunchTests(unittest.TestCase):
    def test_launch_detaches_chemdraw_from_caller_stdio(self):
        running = iter([False, True])
        with mock.patch.object(mac_automation, "find_application", return_value=Path("/Applications/ChemDraw.app")), \
                mock.patch.object(mac_automation, "bundle_identifier", return_value="com.revvity.ChemDraw"), \
                mock.patch.object(mac_automation, "is_running", side_effect=lambda _bundle: next(running)), \
                mock.patch.object(mac_automation, "application_pid", return_value=4242), \
                mock.patch.object(mac_automation.subprocess, "run") as run:
            session = mac_automation.MacChemDrawSession(timeout_seconds=5)
            session.start()

        self.assertTrue(session.launched)
        kwargs = run.call_args.kwargs
        for stream in ("stdin", "stdout", "stderr"):
            self.assertIs(kwargs[stream], mac_automation.subprocess.DEVNULL)

    def test_session_only_quits_chemdraw_it_launched(self):
        with mock.patch.object(mac_automation, "run_applescript") as run:
            session = mac_automation.MacChemDrawSession(timeout_seconds=5)
            session.bundle_id = "com.revvity.ChemDraw"
            session.launched = False
            session.close()
        run.assert_not_called()

    def test_launch_keeps_chemdraw_hidden(self):
        running = iter([False, True])
        with mock.patch.object(mac_automation, "find_application", return_value=Path("/Applications/ChemDraw.app")), \
                mock.patch.object(mac_automation, "bundle_identifier", return_value="com.revvity.ChemDraw"), \
                mock.patch.object(mac_automation, "is_running", side_effect=lambda _bundle: next(running)), \
                mock.patch.object(mac_automation, "application_pid", return_value=4242), \
                mock.patch.object(mac_automation, "register_launch"), \
                mock.patch.object(mac_automation.subprocess, "run") as run:
            # register_launch would probe pid 4242 and write under the user's home folder.
            session = mac_automation.MacChemDrawSession(timeout_seconds=5)
            session.start()

        self.assertIn("-j", run.call_args.args[0])
        self.assertEqual(session.pid, 4242)


def _saved_path(args):
    """Destination of the save step in a run_steps argument list."""
    if "save-within" in args:
        return Path(args[args.index("save-within") + 2])
    return Path(args[args.index("save") + 1])


def _owned_session(launched: bool = True) -> mac_automation.MacChemDrawSession:
    session = mac_automation.MacChemDrawSession(timeout_seconds=5)
    session.bundle = Path("/Applications/ChemDraw.app")
    session.bundle_id = "com.revvity.ChemDraw"
    session.launched = launched
    session.pid = 4242 if launched else None
    return session


class SessionRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.source = self.root / "x.mol"
        self.source.write_text("mol", encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def test_owned_chemdraw_is_rehidden_after_opening_a_document(self):
        session = _owned_session()
        with mock.patch.object(mac_automation, "run_applescript", return_value="") as run:
            session.run_steps(self.source, ["select-all"])
        self.assertEqual(run.call_args.args[1][1:], ["hide", "select-all"])

    def test_every_chemdraw_run_holds_the_native_lock(self):
        session = _owned_session()
        held = []

        from contextlib import contextmanager

        @contextmanager
        def lock(resource_class, timeout_seconds):
            held.append(resource_class)
            yield

        with mock.patch.object(mac_automation, "native_resource_lock", lock), \
                mock.patch.object(mac_automation, "run_applescript", return_value=""):
            session.run_steps(self.source, ["select-all"])
        self.assertEqual(held, ["chemdraw_com"])

    def test_users_own_chemdraw_is_never_hidden(self):
        session = _owned_session(launched=False)
        with mock.patch.object(mac_automation, "run_applescript", return_value="") as run:
            session.run_steps(self.source, ["select-all"])
        self.assertEqual(run.call_args.args[1][1:], ["select-all"])

    def test_owned_chemdraw_trapped_by_an_alert_is_terminated(self):
        session = _owned_session()
        timeout = mac_automation.MacAutomationError("native_timeout", "stuck")
        signals = []

        def kill(pid, sig):
            signals.append((pid, sig))
            if sig == 0:
                raise ProcessLookupError

        with mock.patch.object(mac_automation, "run_applescript", side_effect=timeout), \
                mock.patch.object(mac_automation.sys, "platform", "darwin"), \
                mock.patch.object(mac_automation.os, "kill", side_effect=kill):
            with self.assertRaises(mac_automation.MacAutomationError):
                session.run_steps(self.source, ["select-all"])
        self.assertEqual(signals[0], (4242, mac_automation.signal.SIGTERM))
        self.assertIsNone(session.bundle_id)
        self.assertFalse(session.launched)

    def test_users_own_chemdraw_is_never_terminated(self):
        session = _owned_session(launched=False)
        timeout = mac_automation.MacAutomationError("native_timeout", "stuck")
        with mock.patch.object(mac_automation, "run_applescript", side_effect=timeout), \
                mock.patch.object(mac_automation.os, "kill") as kill:
            with self.assertRaises(mac_automation.MacAutomationError):
                session.run_steps(self.source, ["select-all"])
        kill.assert_not_called()

    def test_name_conversion_is_refused_in_the_users_chemdraw(self):
        session = _owned_session(launched=False)
        with mock.patch.object(mac_automation, "is_running", return_value=True), \
                mock.patch.object(mac_automation, "run_applescript") as run:
            with self.assertRaises(mac_automation.MacAutomationError) as raised:
                session.name_to_structure("aspirin", self.root / "out.cdxml")
        self.assertEqual(raised.exception.error_code, "chemdraw_in_use")
        run.assert_not_called()

    def test_unrecognized_name_has_stable_error_code(self):
        session = _owned_session()

        def unchanged(_script, args, **_kwargs):
            _saved_path(args).write_text(
                mac_automation._caption_document("xyz"), encoding="utf-8"
            )
            return ""

        with mock.patch.object(mac_automation, "run_applescript", side_effect=unchanged):
            with self.assertRaises(mac_automation.MacAutomationError) as raised:
                session.name_to_structure("xyz", self.root / "out.cdxml")
        self.assertEqual(raised.exception.error_code, "name_not_recognized")

    def test_structure_names_accepts_non_cdxml_sources(self):
        session = _owned_session()

        def named(_script, args, **_kwargs):
            _saved_path(args).write_text(
                mac_automation._caption_document("ethanol"), encoding="utf-8"
            )
            return ""

        with mock.patch.object(mac_automation, "run_applescript", side_effect=named):
            self.assertEqual(session.structure_names(self.source), ["ethanol"])

    def test_structure_names_drop_chemdraws_could_not_name_caption(self):
        session = _owned_session()

        def unnamed(_script, args, **_kwargs):
            _saved_path(args).write_text(
                mac_automation._caption_document("A name could not be generated for this structure."),
                encoding="utf-8",
            )
            return ""

        with mock.patch.object(mac_automation, "run_applescript", side_effect=unnamed):
            self.assertEqual(session.structure_names(self.source), [])


class LaunchRegistryTests(unittest.TestCase):
    """ChemDraw/Office launched by the toolkit are recorded with their owner process,
    so instances orphaned by a killed worker are recognized and stopped."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        alive = {4242, os.getpid()}
        for patch in (
            mock.patch.object(mac_automation, "LAUNCH_REGISTRY", Path(self.temp.name)),
            mock.patch.object(mac_automation, "_pid_alive", side_effect=alive.__contains__),
        ):
            patch.start()
            self.addCleanup(patch.stop)

    def entries(self):
        return sorted(path.name for path in Path(self.temp.name).glob("*.json"))

    def test_launch_records_the_owner_and_close_forgets_it(self):
        running = iter([False, True])
        with mock.patch.object(mac_automation, "find_application", return_value=Path("/Applications/ChemDraw.app")), \
                mock.patch.object(mac_automation, "bundle_identifier", return_value="com.revvity.ChemDraw"), \
                mock.patch.object(mac_automation, "is_running", side_effect=lambda _bundle: next(running)), \
                mock.patch.object(mac_automation, "application_pid", return_value=4242), \
                mock.patch.object(mac_automation.subprocess, "run"):
            session = mac_automation.MacChemDrawSession(timeout_seconds=5)
            session.start()

        self.assertEqual(self.entries(), ["4242.json"])
        self.assertEqual(mac_automation.launched_instances()[4242]["owner_pid"], os.getpid())
        with mock.patch.object(mac_automation, "run_applescript", return_value=""), \
                mock.patch.object(mac_automation, "_pid_alive", return_value=False), \
                mock.patch.object(mac_automation, "terminate_process") as terminate:
            session.close()
        terminate.assert_not_called()
        self.assertEqual(self.entries(), [])

    def test_launch_waits_for_the_pid_so_close_can_stop_chemdraw(self):
        # lsappinfo can lag behind a launch; a session without the pid can neither
        # record nor stop its ChemDraw, and a quit sent mid-launch is lost.
        pids = iter([None, None, 4242])
        with mock.patch.object(mac_automation, "find_application", return_value=Path("/Applications/ChemDraw.app")), \
                mock.patch.object(mac_automation, "bundle_identifier", return_value="com.revvity.ChemDraw"), \
                mock.patch.object(mac_automation, "is_running", side_effect=[False, True, True]), \
                mock.patch.object(mac_automation, "application_pid", side_effect=lambda _bundle: next(pids, 4242)), \
                mock.patch.object(mac_automation.time, "sleep"), \
                mock.patch.object(mac_automation.subprocess, "run"):
            session = mac_automation.MacChemDrawSession(timeout_seconds=5)
            session.start()

        self.assertEqual(session.pid, 4242)
        self.assertEqual(self.entries(), ["4242.json"])

    def test_launch_hidden_records_the_new_application(self):
        pids = iter([None, 4242])
        with mock.patch.object(mac_automation, "application_pid", side_effect=lambda _bundle: next(pids)), \
                mock.patch.object(mac_automation.time, "sleep"), \
                mock.patch.object(mac_automation.subprocess, "run") as run:
            pid = mac_automation.launch_hidden("com.microsoft.Word")

        self.assertEqual(pid, 4242)
        self.assertEqual(run.call_args.args[0], ["open", "-g", "-j", "-b", "com.microsoft.Word"])
        self.assertEqual(mac_automation.launched_instances()[4242]["bundle_id"], "com.microsoft.Word")

    def test_close_waits_until_chemdraw_has_exited(self):
        # quit is asynchronous: a session started right after close would
        # otherwise attach to the exiting ChemDraw and lose it mid-run (-609).
        session = _owned_session()
        alive = iter([True, True, True, False])
        with mock.patch.object(mac_automation, "run_applescript", return_value=""), \
                mock.patch.object(mac_automation, "_pid_alive", side_effect=lambda _pid: next(alive)), \
                mock.patch.object(mac_automation.time, "sleep") as sleep, \
                mock.patch.object(mac_automation, "terminate_process") as terminate:
            session.close()

        self.assertEqual(sleep.call_count, 2)
        terminate.assert_not_called()

    def test_close_does_not_message_a_chemdraw_that_already_exited(self):
        # AppleScript relaunches an application to deliver ``quit``; that
        # instance would belong to no session and stay open.
        session = _owned_session()
        with mock.patch.object(mac_automation, "run_applescript") as run, \
                mock.patch.object(mac_automation, "_pid_alive", return_value=False):
            session.close()

        run.assert_not_called()
        self.assertIsNone(session.pid)

    def test_close_terminates_chemdraw_that_never_exits(self):
        session = _owned_session()
        clock = iter(range(0, 1000, 5))
        with mock.patch.object(mac_automation, "run_applescript", return_value=""), \
                mock.patch.object(mac_automation, "_pid_alive", return_value=True), \
                mock.patch.object(mac_automation.time, "sleep"), \
                mock.patch.object(mac_automation.time, "monotonic", side_effect=lambda: next(clock)), \
                mock.patch.object(mac_automation, "terminate_process") as terminate:
            session.close()

        terminate.assert_called_once_with(4242)

    def test_close_terminates_chemdraw_that_refuses_to_quit(self):
        session = _owned_session()
        mac_automation.register_launch(4242, "com.revvity.ChemDraw")
        blocked = mac_automation.MacAutomationError("native_automation_failed", "(-128)")
        with mock.patch.object(mac_automation, "run_applescript", side_effect=blocked), \
                mock.patch.object(mac_automation, "terminate_process") as terminate:
            session.close()

        terminate.assert_called_once_with(4242)
        self.assertEqual(self.entries(), [])

    def test_instances_of_a_dead_owner_are_reaped(self):
        mac_automation.register_launch(4242, "com.revvity.ChemDraw", owner_pid=_dead_pid())
        with mock.patch.object(mac_automation, "application_pid", return_value=4242), \
                mock.patch.object(mac_automation, "terminate_process") as terminate:
            self.assertEqual(mac_automation.reap_orphans(), [4242])

        terminate.assert_called_once_with(4242)
        self.assertEqual(self.entries(), [])

    def test_instances_of_a_live_owner_are_kept(self):
        mac_automation.register_launch(4242, "com.revvity.ChemDraw")
        with mock.patch.object(mac_automation, "application_pid", return_value=4242), \
                mock.patch.object(mac_automation, "terminate_process") as terminate:
            self.assertEqual(mac_automation.reap_orphans(), [])

        terminate.assert_not_called()
        self.assertEqual(self.entries(), ["4242.json"])

    def test_a_reused_pid_is_forgotten_without_being_killed(self):
        mac_automation.register_launch(4242, "com.revvity.ChemDraw", owner_pid=_dead_pid())
        with mock.patch.object(mac_automation, "application_pid", return_value=777), \
                mock.patch.object(mac_automation, "terminate_process") as terminate:
            self.assertEqual(mac_automation.reap_orphans(), [])

        terminate.assert_not_called()
        self.assertEqual(self.entries(), [])


def _dead_pid() -> int:
    return 99999

if __name__ == "__main__":
    unittest.main()


CAPTIONED_SCHEME = (
    '<?xml version="1.0" encoding="UTF-8" ?>\n'
    '<!DOCTYPE CDXML SYSTEM "http://www.cambridgesoft.com/xml/cdxml.dtd" >\n'
    '<CDXML InterpretChemically="yes"><page id="1">'
    '<fragment id="2"><n id="3" p="0 0"/><n id="4" p="14 0" Element="8">'
    '<t id="5" p="14 0"><s>OH</s></t></n><b id="6" B="3" E="4"/></fragment>'
    '<t id="7" p="7 15"><s>MeOH</s></t>'
    '<t id="8" p="7 30" InterpretChemically="yes"><s>NaOH</s></t>'
    '<scheme id="9"><step id="10" ReactionStepReactants="2"/></scheme>'
    '</page></CDXML>'
)


class CaptionProtectionTests(unittest.TestCase):
    """ChemDraw turns a free caption such as "MeOH" into a nickname fragment and
    Clean Up Reaction then lists it as an extra reactant."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "scheme.cdxml"
        self.path.write_text(CAPTIONED_SCHEME, encoding="utf-8")

    def interpret(self, text):
        import xml.etree.ElementTree as ET

        root = ET.fromstring(text.split("\n", 2)[2])
        return {t.get("id"): t.get("InterpretChemically") for t in root.iter("t")}

    def test_free_captions_are_marked_as_plain_text(self):
        marked = mac_automation.protect_captions(self.path)

        self.assertEqual(marked, ["7"])
        flags = self.interpret(self.path.read_text(encoding="utf-8"))
        self.assertEqual(flags, {"5": None, "7": "no", "8": "yes"})
        self.assertIn("<!DOCTYPE CDXML", self.path.read_text(encoding="utf-8"))

    def test_marks_are_removed_from_the_saved_result(self):
        marked = mac_automation.protect_captions(self.path)
        mac_automation.release_captions(self.path, marked)

        self.assertEqual(self.path.read_text(encoding="utf-8"), CAPTIONED_SCHEME)

    def test_clean_up_reaction_runs_on_protected_captions_and_saves_them_unmarked(self):
        session = _owned_session()
        source = Path(self.temp.name) / "in.cdxml"
        source.write_text(CAPTIONED_SCHEME, encoding="utf-8")
        seen = []

        def chemdraw(_script, args, **_kwargs):
            staged = Path(args[0]).read_text(encoding="utf-8")
            seen.append(self.interpret(staged)["7"])
            _saved_path(args).write_text(staged, encoding="utf-8")
            return ""

        output = Path(self.temp.name) / "out.cdxml"
        with mock.patch.object(mac_automation, "run_applescript", side_effect=chemdraw), \
                mock.patch.object(mac_automation, "installed_font_families", return_value=frozenset()):
            session.clean(source, output, reaction=True)

        self.assertEqual(seen, ["no"])
        self.assertIsNone(self.interpret(output.read_text(encoding="utf-8"))["7"])

    def test_name_to_structure_keeps_captions_chemical(self):
        session = _owned_session()
        seen = []

        def chemdraw(_script, args, **_kwargs):
            seen.append(Path(args[0]).read_text(encoding="utf-8"))
            _saved_path(args).write_text(
                mac_automation._caption_document("ethanol"), encoding="utf-8")
            return ""

        with mock.patch.object(mac_automation, "run_applescript", side_effect=chemdraw):
            try:
                session.name_to_structure("ethanol", Path(self.temp.name) / "n.cdxml")
            except mac_automation.MacAutomationError:
                pass
        self.assertNotIn('InterpretChemically="no"', seen[0])


class FastNameFailureTests(unittest.TestCase):
    """ChemDraw answers an unknown name with a modal alert that blocks the menu
    command's reply; the conversion is sent without waiting and the save is
    bounded, so a rejected name fails in seconds instead of the whole timeout."""

    def test_conversion_is_sent_without_waiting_and_the_save_is_bounded(self):
        session = _owned_session()

        def chemdraw(_script, args, **_kwargs):
            Path(args[args.index("save-within") + 2]).write_text(
                "<CDXML><page><fragment/></page></CDXML>", encoding="utf-8")
            return ""

        with tempfile.TemporaryDirectory() as temp, \
                mock.patch.object(mac_automation, "run_applescript", side_effect=chemdraw) as run:
            session.name_to_structure("aniline", Path(temp) / "n.cdxml")
        steps = run.call_args.args[1][1:]
        self.assertEqual(steps[:5], ["hide", "select-all", "menu-nowait", "Structure", "Convert Name to Structure"])
        self.assertEqual(steps[5:7], ["save-within", str(mac_automation.NAME_CONVERSION_SECONDS)])

    def test_steps_script_supports_unanswered_menus_and_skips_close_behind_an_alert(self):
        script = mac_automation._steps_script("com.revvity.ChemDraw")
        self.assertIn("ignoring application responses", script)
        self.assertIn("with timeout of", script)
        self.assertIn("if errorNumber is not -1712 then close doc saving no", script)
