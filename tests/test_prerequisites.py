from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
CHECKER = ROOT / "scripts" / "check_prerequisites.ps1"


class PrerequisiteCheckerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
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

    def test_reports_supported_host_and_explicit_python(self) -> None:
        completed = self._run(
            "-Python",
            sys.executable,
            "-SkipChemDraw",
            "-SkipPythonPackages",
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        report = json.loads(completed.stdout)
        checks = {item["name"]: item for item in report["checks"]}

        self.assertEqual(report["schema_version"], 1)
        self.assertTrue(report["ok"])
        self.assertEqual(report["selected_capabilities"], ["core"])
        self.assertEqual(checks["windows"]["status"], "pass")
        self.assertFalse(checks["windows"]["required"])
        self.assertIn("64-bit", checks["windows"]["detail"])
        self.assertEqual(checks["powershell"]["status"], "pass")
        self.assertEqual(checks["python_runtime"]["status"], "pass")
        self.assertEqual(checks["python_packages"]["status"], "skipped")
        self.assertEqual(checks["chemdraw_com"]["status"], "skipped")
        self.assertIsInstance(report["next_steps"], list)

    def test_no_agent_client_is_required(self) -> None:
        completed = self._run("-Python", sys.executable, "-SkipPythonPackages")
        self.assertEqual(completed.returncode, 0, completed.stderr)
        names = {item["name"] for item in json.loads(completed.stdout)["checks"]}
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

        self.assertEqual(completed.returncode, 0, completed.stderr)
        report = json.loads(completed.stdout)
        checks = {item["name"]: item for item in report["checks"]}
        self.assertEqual(checks["conda"]["status"], "pass")
        self.assertIn("PowerShell Function", checks["conda"]["detail"])
        self.assertNotIn("must not be invoked", checks["conda"]["detail"])


if __name__ == "__main__":
    unittest.main()
