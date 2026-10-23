from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
from unittest import mock

from cdxml_toolkit.chemdraw import mac_automation
from cdxml_toolkit.mcp_runtime import runtime_diagnostics, runtime_discovery


def _fake_bundle(root: Path, scriptable: bool = True) -> Path:
    bundle = root / "ChemDraw.app"
    (bundle / "Contents" / "MacOS").mkdir(parents=True)
    (bundle / "Contents" / "Resources").mkdir()
    (bundle / "Contents" / "MacOS" / "ChemDraw").write_bytes(b"")
    if scriptable:
        (bundle / "Contents" / "Resources" / "ChemDraw.sdef").write_text("<dictionary/>", encoding="utf-8")
    import plistlib

    with (bundle / "Contents" / "Info.plist").open("wb") as handle:
        plistlib.dump(
            {
                "CFBundleIdentifier": "com.revvity.ChemDraw",
                "CFBundleExecutable": "ChemDraw",
                "CFBundleShortVersionString": "26.0.0.6599",
                "NSAppleScriptEnabled": scriptable,
                "OSAScriptingDefinition": "ChemDraw.sdef",
            },
            handle,
        )
    return bundle


class MacDiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.bundle = _fake_bundle(Path(self.temp.name))
        patches = [
            mock.patch.object(mac_automation, "is_macos", return_value=True),
            mock.patch.object(mac_automation, "find_application", return_value=self.bundle),
            mock.patch.dict("os.environ", {}, clear=False),
        ]
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)
        import os

        os.environ.pop("CHEMDRAW_EXE", None)

    def tearDown(self):
        self.temp.cleanup()

    def test_chemdraw_for_macos_is_found_without_configuration(self):
        discovery = runtime_discovery.find_chemdraw()

        self.assertEqual(discovery.source, "macos-application")
        self.assertEqual(Path(discovery.path), self.bundle / "Contents" / "MacOS" / "ChemDraw")

    def test_applescript_automation_reports_native_capability(self):
        executable, automation = runtime_diagnostics._chemdraw_capabilities()

        self.assertEqual(executable["status"], "available")
        self.assertEqual(automation["status"], "available")
        self.assertEqual(automation["automation"], "applescript")
        self.assertEqual(automation["version"], "26.0.0.6599")

    def test_unscriptable_application_reports_missing_automation(self):
        bundle = _fake_bundle(Path(self.temp.name) / "plain", scriptable=False)
        with mock.patch.object(mac_automation, "find_application", return_value=bundle):
            _executable, automation = runtime_diagnostics._chemdraw_capabilities()

        self.assertEqual(automation["status"], "missing")

    def test_office_dependencies_do_not_require_win32com_on_macos(self):
        with mock.patch.object(runtime_diagnostics, "_module_available", side_effect=lambda name: name != "win32com.client"):
            office = runtime_diagnostics._office_capability()

        self.assertNotIn("win32com", office["dependencies"])
        self.assertEqual(office["status"], "unverified")

    def test_office_reports_word_and_powerpoint_for_pdf_previews(self):
        from cdxml_toolkit.office import mac_office

        apps = {".docx": Path("/Applications/Microsoft Word.app"), ".pptx": None}
        with mock.patch.object(runtime_diagnostics, "_module_available", return_value=True), \
                mock.patch.object(mac_office, "application_path", side_effect=apps.get):
            office = runtime_diagnostics._office_capability()

        self.assertEqual(office["status"], "unverified")
        self.assertEqual(
            office["pdf_export"],
            {"word": str(apps[".docx"]), "powerpoint": None},
        )


class MacStageCleanupTests(unittest.TestCase):
    def test_timed_out_stage_still_stops_the_chemdraw_it_launched(self):
        import time

        launched = {101: {"pid": 101, "parent_pid": 555, "name": "ChemDraw"}}
        snapshots = iter([launched, {}])
        with mock.patch.object(runtime_diagnostics.sys, "platform", "darwin"), \
                mock.patch.object(runtime_diagnostics, "snapshot_automation_processes",
                                  side_effect=lambda **_: next(snapshots)), \
                mock.patch("cdxml_toolkit.mcp_runtime.process_control.terminate_pid",
                           return_value=True) as terminate:
            cleanup = runtime_diagnostics._audit_stage_processes(
                {}, stage_pid=555, timed_out=True, deadline=time.monotonic()
            )

        terminate.assert_called_once()
        self.assertEqual(cleanup["terminated_pids"], [101])


if __name__ == "__main__":
    unittest.main()


class OpsinDiscoveryTests(unittest.TestCase):
    def test_opsin_installed_by_the_installer_is_found_without_configuration(self):
        with tempfile.TemporaryDirectory() as temp:
            jar = Path(temp) / "chemdraw-skill" / "opsin" / "opsin-cli-2.9.0-jar-with-dependencies.jar"
            jar.parent.mkdir(parents=True)
            jar.write_bytes(b"PK")
            environment = {"XDG_DATA_HOME": temp, "LOCALAPPDATA": temp}
            with mock.patch.dict(runtime_diagnostics.os.environ, environment):
                for variable in ("OPSIN_JAR", "CDXML_TOOLKIT_OPSIN_JAR"):
                    runtime_diagnostics.os.environ.pop(variable, None)
                _, opsin = runtime_diagnostics._java_opsin_capabilities()

        self.assertEqual(opsin["status"], "available")
        self.assertEqual(Path(opsin["path"]).name, jar.name)
