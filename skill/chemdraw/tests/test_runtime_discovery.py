from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest
from unittest import mock

from cdxml_toolkit.mcp_runtime import runtime_discovery


SCRIPT_ROOT = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_ROOT.parent
REFERENCES = SKILL_ROOT / "references"
REQUIRED_IMPORTS = ("cdxml_toolkit", "mcp", "rdkit", "win32com.client")


def _minimal_environment() -> dict[str, str]:
    keys = ("SystemRoot", "WINDIR", "USERPROFILE", "HOME", "PATH", "PATHEXT")
    return {key: os.environ[key] for key in keys if key in os.environ}


class RuntimeDiscoveryTests(unittest.TestCase):
    def test_explicit_python_wins_after_import_probe(self):
        with tempfile.TemporaryDirectory() as tmp:
            executable = Path(tmp) / "python.exe"
            executable.write_bytes(b"MZ")
            with (
                mock.patch.dict(
                    os.environ, {"CHEMDRAW_MCP_PYTHON": "ignored"}, clear=False
                ),
                mock.patch.object(
                    runtime_discovery, "_probe_python", return_value=None, create=True
                ) as probe,
            ):
                result = runtime_discovery.find_python(str(executable))
        self.assertEqual(result.path, str(executable.resolve()))
        self.assertEqual(result.source, "explicit")
        self.assertIsNotNone(probe.call_args)
        self.assertEqual(probe.call_args.args[0], executable.resolve())

    def test_environment_python_is_second_after_import_probe(self):
        with tempfile.TemporaryDirectory() as tmp:
            executable = Path(tmp) / "python.exe"
            executable.write_bytes(b"MZ")
            with (
                mock.patch.dict(
                    os.environ,
                    {"CHEMDRAW_MCP_PYTHON": str(executable)},
                    clear=False,
                ),
                mock.patch.object(
                    runtime_discovery, "_probe_python", return_value=None, create=True
                ) as probe,
            ):
                result = runtime_discovery.find_python()
        self.assertEqual(result.source, "environment")
        self.assertIsNotNone(probe.call_args)
        self.assertEqual(probe.call_args.args[0], executable.resolve())

    def test_missing_explicit_path_is_clear_error(self):
        with self.assertRaisesRegex(RuntimeError, "explicit"):
            runtime_discovery.find_python("Z:\\missing\\python.exe")

    def test_unusable_explicit_python_is_a_clear_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            executable = Path(tmp) / "python.exe"
            executable.write_bytes(b"MZ")
            with mock.patch.object(
                runtime_discovery,
                "_probe_python",
                return_value="missing required import: mcp",
                create=True,
            ):
                with self.assertRaisesRegex(
                    RuntimeError, "explicit.*missing required import: mcp"
                ):
                    runtime_discovery.find_python(str(executable))

    def test_unusable_environment_python_is_a_clear_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            executable = Path(tmp) / "python.exe"
            executable.write_bytes(b"MZ")
            with (
                mock.patch.dict(
                    os.environ,
                    {"CHEMDRAW_MCP_PYTHON": str(executable)},
                    clear=False,
                ),
                mock.patch.object(
                    runtime_discovery,
                    "_probe_python",
                    return_value="missing required import: rdkit",
                    create=True,
                ),
            ):
                with self.assertRaisesRegex(
                    RuntimeError,
                    "CHEMDRAW_MCP_PYTHON.*missing required import: rdkit",
                ):
                    runtime_discovery.find_python()

    def test_unusable_implicit_python_is_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "bad-python.exe"
            good = Path(tmp) / "good-python.exe"
            bad.write_bytes(b"MZ")
            good.write_bytes(b"MZ")

            def probe(path: Path) -> str | None:
                return "imports failed" if path == bad.resolve() else None

            with (
                mock.patch.dict(os.environ, _minimal_environment(), clear=True),
                mock.patch.object(runtime_discovery.sys, "executable", str(bad)),
                mock.patch.object(runtime_discovery.shutil, "which", return_value=str(good)),
                mock.patch.object(
                    runtime_discovery, "_probe_python", side_effect=probe, create=True
                ),
            ):
                result = runtime_discovery.find_python()
        self.assertEqual(result.path, str(good.resolve()))
        self.assertEqual(result.source, "PATH")

    def test_conda_environment_registry_finds_named_cdxml_environment(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            environment = Path(tmp) / "portable-conda" / "envs" / "cdxml"
            executable = environment / "python.exe"
            executable.parent.mkdir(parents=True)
            executable.write_bytes(b"MZ")
            registry = home / ".conda" / "environments.txt"
            registry.parent.mkdir(parents=True)
            registry.write_text(str(environment) + "\n", encoding="utf-8")

            with (
                mock.patch.dict(os.environ, _minimal_environment(), clear=True),
                mock.patch.object(runtime_discovery.Path, "home", return_value=home),
                mock.patch.object(runtime_discovery.sys, "executable", "Z:\\missing\\python.exe"),
                mock.patch.object(runtime_discovery.shutil, "which", return_value=None),
                mock.patch.object(runtime_discovery, "_probe_python", return_value=None),
            ):
                result = runtime_discovery.find_python()

        self.assertEqual(result.path, str(executable.resolve()))
        self.assertEqual(result.source, "conda-environment-registry")

    def test_runtime_discovery_has_no_machine_specific_python_fallback(self):
        source = Path(runtime_discovery.__file__).read_text(encoding="utf-8")
        self.assertNotIn("D:\\" + "ProgramFiles", source)

    def test_python_probe_imports_every_required_module(self):
        self.assertTrue(hasattr(runtime_discovery, "_probe_python"))
        completed = subprocess.CompletedProcess([], 0, stdout="", stderr="")
        with mock.patch.object(
            runtime_discovery.subprocess, "run", return_value=completed
        ) as run:
            error = runtime_discovery._probe_python(Path(sys.executable))
        self.assertIsNone(error)
        command = run.call_args.args[0]
        self.assertEqual(command[0], str(Path(sys.executable)))
        self.assertEqual(command[1], "-c")
        for module in runtime_discovery.REQUIRED_IMPORTS:
            self.assertIn(module, command[2])
        self.assertGreater(run.call_args.kwargs["timeout"], 0)

    def test_quoted_localserver_command_extracts_executable(self):
        self.assertTrue(
            hasattr(runtime_discovery, "_extract_local_server_executable")
        )
        command = '"C:\\Program Files\\ChemDraw\\ChemDraw.exe" /Automation'
        self.assertEqual(
            runtime_discovery._extract_local_server_executable(command),
            r"C:\Program Files\ChemDraw\ChemDraw.exe",
        )

    def test_unquoted_localserver_command_extracts_executable(self):
        self.assertTrue(
            hasattr(runtime_discovery, "_extract_local_server_executable")
        )
        command = r"D:\Program Files\ChemOffice\ChemDraw\ChemDraw.exe /Automation"
        self.assertEqual(
            runtime_discovery._extract_local_server_executable(command),
            r"D:\Program Files\ChemOffice\ChemDraw\ChemDraw.exe",
        )

    def test_chemdraw_registry_precedes_common_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            registry_exe = Path(tmp) / "registry" / "ChemDraw.exe"
            common_exe = Path(tmp) / "common" / "ChemDraw.exe"
            registry_exe.parent.mkdir()
            common_exe.parent.mkdir()
            registry_exe.write_bytes(b"MZ")
            common_exe.write_bytes(b"MZ")
            command = f'"{registry_exe}" /Automation'
            with (
                mock.patch.object(
                    runtime_discovery,
                    "_registry_local_server_command",
                    return_value=command,
                    create=True,
                ),
                mock.patch.object(
                    runtime_discovery,
                    "_common_chemdraw_candidates",
                    return_value=[common_exe],
                    create=True,
                ),
                mock.patch.dict(
                    os.environ,
                    {key: value for key, value in os.environ.items() if key != "CHEMDRAW_EXE"},
                    clear=True,
                ),
            ):
                try:
                    result = runtime_discovery.find_chemdraw()
                except RuntimeError as exc:
                    self.fail(str(exc))
        self.assertEqual(result.path, str(registry_exe.resolve()))
        self.assertEqual(result.source, "registry-HKCR")

    def test_chemdraw_common_paths_include_nested_revvity_layouts(self):
        with tempfile.TemporaryDirectory() as tmp:
            executable = (
                Path(tmp)
                / "Revvity Signals Software"
                / "ChemOffice2025"
                / "ChemDraw"
                / "ChemDraw.exe"
            )
            executable.parent.mkdir(parents=True)
            executable.write_bytes(b"MZ")
            environment = _minimal_environment()
            environment["ProgramFiles"] = tmp
            environment["ProgramFiles(x86)"] = ""
            environment["ProgramW6432"] = tmp
            with (
                mock.patch.dict(os.environ, environment, clear=True),
                mock.patch.object(
                    runtime_discovery,
                    "_registry_local_server_command",
                    return_value=None,
                    create=True,
                ),
            ):
                try:
                    result = runtime_discovery.find_chemdraw()
                except RuntimeError as exc:
                    self.fail(str(exc))
        self.assertEqual(result.path, str(executable.resolve()))
        self.assertEqual(result.source, "common-path")


if __name__ == "__main__":
    unittest.main()
