from __future__ import annotations

import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
CHECKER = ROOT / "scripts" / "check_prerequisites.ps1"
# The checker accepts the toolkit's supported range only; on any other host Python
# (for example 3.14) it must report a structured failure instead of passing.
HOST_PYTHON_SUPPORTED = (3, 10) <= sys.version_info[:2] <= (3, 13)


class PrerequisiteCheckerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        # Linux runners ship pwsh too, but the checker only reports on Windows hosts.
        if os.name != "nt":
            raise unittest.SkipTest("The supplied checker is for Windows hosts")
        cls.shell = shutil.which("pwsh") or shutil.which("powershell")
        if cls.shell is None:
            raise unittest.SkipTest("PowerShell is required to test the supplied checker")

    def _run(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                str(self.shell),
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(CHECKER),
                "-Json",
                *arguments,
            ],
            capture_output=True,
            text=True,
            encoding="utf-8-sig",
        )

    def _assert_host_python_verdict(self, completed: subprocess.CompletedProcess[str]) -> dict:
        """The exit code and python_runtime status follow the host interpreter's version."""
        report = json.loads(completed.stdout)
        checks = {item["name"]: item for item in report["checks"]}
        self.assertEqual(completed.returncode, 0 if HOST_PYTHON_SUPPORTED else 1, completed.stderr)
        self.assertEqual(report["ok"], HOST_PYTHON_SUPPORTED)
        self.assertEqual(checks["python_runtime"]["status"], "pass" if HOST_PYTHON_SUPPORTED else "fail")
        self.assertIn(f"{sys.version_info[0]}.{sys.version_info[1]}", checks["python_runtime"]["detail"])
        return report

    def test_reports_supported_host_and_explicit_python(self) -> None:
        completed = self._run(
            "-Python",
            sys.executable,
            "-SkipChemDraw",
            "-SkipPythonPackages",
        )
        report = self._assert_host_python_verdict(completed)
        checks = {item["name"]: item for item in report["checks"]}

        self.assertEqual(report["schema_version"], 1)
        self.assertEqual(report["selected_capabilities"], ["core"])
        self.assertEqual(checks["windows"]["status"], "pass")
        self.assertFalse(checks["windows"]["required"])
        self.assertIn("64-bit", checks["windows"]["detail"])
        self.assertEqual(checks["powershell"]["status"], "pass")
        self.assertEqual(checks["python_packages"]["status"], "skipped")
        self.assertEqual(checks["chemdraw_com"]["status"], "skipped")
        self.assertIsInstance(report["next_steps"], list)

    def test_no_agent_client_is_required(self) -> None:
        completed = self._run("-Python", sys.executable, "-SkipPythonPackages")
        report = self._assert_host_python_verdict(completed)
        names = {item["name"] for item in report["checks"]}
        self.assertFalse(any(name.endswith("_cli") for name in names), names)

    def test_missing_explicit_python_is_a_structured_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "missing-python.exe"
            completed = self._run(
                "-Python",
                str(missing),
                "-SkipChemDraw",
                "-SkipPythonPackages",
            )

        self.assertEqual(completed.returncode, 1)
        report = json.loads(completed.stdout)
        checks = {item["name"]: item for item in report["checks"]}
        self.assertFalse(report["ok"])
        self.assertEqual(checks["python_runtime"]["status"], "fail")
        self.assertIn("does not exist", checks["python_runtime"]["detail"])

    def test_shell_function_commands_are_supported(self) -> None:
        checker = str(CHECKER).replace("'", "''")
        python = sys.executable.replace("'", "''")
        command = (
            "function conda { throw 'shell function must not be invoked' }; "
            f"& '{checker}' -Json -Python '{python}' "
            "-SkipChemDraw -SkipPythonPackages; "
            "exit $LASTEXITCODE"
        )
        completed = subprocess.run(
            [str(self.shell), "-NoProfile", "-Command", command],
            capture_output=True,
            text=True,
            encoding="utf-8-sig",
        )

        report = self._assert_host_python_verdict(completed)
        checks = {item["name"]: item for item in report["checks"]}
        self.assertEqual(checks["conda"]["status"], "pass")
        self.assertIn("PowerShell Function", checks["conda"]["detail"])
        self.assertNotIn("must not be invoked", checks["conda"]["detail"])

    def test_comma_separated_capabilities_work_from_another_shell(self) -> None:
        # `pwsh script.ps1 -Capabilities core,native` (the documented form, launched from bash or
        # cmd) passes "core,native" as ONE string; the checker must split it, not reject it.
        completed = self._run("-Capabilities", "core,native", "-Python", sys.executable,
                              "-SkipChemDraw", "-SkipPythonPackages")
        report = json.loads(completed.stdout)
        self.assertEqual(report["selected_capabilities"], ["core", "native"])
        windows = {item["name"]: item for item in report["checks"]}["windows"]
        self.assertTrue(windows["required"])

    def test_unknown_capability_is_rejected_by_name(self) -> None:
        completed = self._run("-Capabilities", "core,bogus", "-Python", sys.executable,
                              "-SkipChemDraw", "-SkipPythonPackages")
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("bogus", completed.stdout + completed.stderr)

    def test_documented_command_lines_use_the_supported_capability_form(self) -> None:
        for name in ("docs/guide.md", "docs/guide.zh-cn.md"):
            text = (ROOT / name).read_text(encoding="utf-8")
            for line in re.findall(r"check_prerequisites\.ps1[^\n]*", text):
                with self.subTest(document=name, line=line):
                    for value in re.findall(r"-Capabilities\s+(\S+)", line):
                        self.assertTrue(set(value.split(",")) <= {"core", "native", "chemscript", "office", "decimer"}, line)

    @unittest.skipUnless(HOST_PYTHON_SUPPORTED, "the DECIMER probe runs only on a supported Python")
    def test_decimer_probe_reads_the_toolkit_result_envelope(self) -> None:
        # diagnose_runtime() returns {"ok", "outputs": {"capabilities": ...}, ...}; the checker
        # must read outputs.capabilities. A fake toolkit keeps this test independent of the runtime.
        with tempfile.TemporaryDirectory() as tmp:
            package = Path(tmp) / "cdxml_toolkit" / "mcp_runtime"
            package.mkdir(parents=True)
            (package.parent / "__init__.py").write_text("", encoding="utf-8")
            (package / "__init__.py").write_text("", encoding="utf-8")
            (package / "runtime_diagnostics.py").write_text(
                "def diagnose_runtime():\n"
                "    return {'ok': True, 'warnings': [], 'metadata': {}, 'outputs': {'capabilities': {\n"
                "        'decimer_models': {'status': 'available', 'root': 'FAKE-ROOT'}}}}\n",
                encoding="utf-8")
            env = dict(__import__("os").environ, PYTHONPATH=tmp)
            completed = subprocess.run(
                [str(self.shell), "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(CHECKER),
                 "-Json", "-Python", sys.executable, "-Capabilities", "decimer",
                 "-SkipChemDraw", "-SkipPythonPackages"],
                capture_output=True, text=True, encoding="utf-8-sig", env=env)
        checks = {item["name"]: item for item in json.loads(completed.stdout)["checks"]}
        self.assertEqual(checks["decimer_models"]["status"], "pass", checks["decimer_models"]["detail"])
        self.assertIn("FAKE-ROOT", checks["decimer_models"]["detail"])

    def test_tested_toolkit_version_comes_from_runtime_json(self) -> None:
        # The checker must not hard-code a toolkit version that drifts from runtime.json.
        script = (ROOT / "skill" / "chemdraw" / "scripts" / "check_prerequisites.ps1").read_text(encoding="utf-8")
        baseline = json.loads((ROOT / "skill" / "chemdraw" / "runtime.json").read_text(encoding="utf-8"))
        self.assertIn("runtime.json", script)
        self.assertNotRegex(script, r"0\.\d+\.\d+a\d+", "hard-coded toolkit version in the checker")
        self.assertNotIn("install_decimer_models.py", script)
        # ChemScript configuration goes through the runtime, which cdx.py py always selects.
        self.assertIn("cdx.py py -m cdxml_toolkit.doctor --no-tests --configure-chemscript", script)
        self.assertNotIn("register the MCP runtime", script)
        self.assertRegex(baseline["toolkit_version"], r"^\d+\.\d+")


if __name__ == "__main__":
    unittest.main()
