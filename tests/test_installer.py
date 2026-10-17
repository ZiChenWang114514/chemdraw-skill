from __future__ import annotations

import json
from pathlib import Path
import shutil
import sys
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "scripts" / "install.ps1"


class InstallerTests(unittest.TestCase):
    def test_apply_ignores_test_and_typecheck_caches(self) -> None:
        shell = shutil.which("pwsh") or shutil.which("powershell")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            installer = root / "scripts" / "install.ps1"
            installer.parent.mkdir()
            shutil.copy2(INSTALLER, installer)
            source = root / "skill" / "chemdraw"
            source.mkdir(parents=True)
            (source / "SKILL.md").write_text("test skill", encoding="ascii")
            for cache in ("__pycache__", ".pytest_cache", ".mypy_cache"):
                folder = source / "scripts" / cache
                folder.mkdir(parents=True)
                (folder / "cache.txt").write_text("local only", encoding="ascii")
            result = subprocess.run(
                [shell, "-NoProfile", "-File", str(installer), "-Apply",
                 "-Destination", str(root / "installed")],
                capture_output=True, text=True, encoding="utf-8-sig",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            record = json.loads(result.stdout)
            self.assertEqual(record["source_fingerprint"], record["installed_fingerprint"])
            self.assertEqual(list((root / "installed").rglob("cache.txt")), [])

    def test_default_destination_is_the_claude_code_skill_directory(self) -> None:
        shell = shutil.which("pwsh") or shutil.which("powershell")
        result = subprocess.run(
            [shell, "-NoProfile", "-File", str(INSTALLER)],
            capture_output=True, text=True, encoding="utf-8-sig", check=True,
        )
        proposal = json.loads(result.stdout)
        self.assertEqual(Path(proposal["destination"]).parts[-3:], (".claude", "skills", "chemdraw"))
        self.assertEqual(proposal["runtime"]["action"], "skip")

    def test_runtime_proposal_uses_a_sibling_venv(self) -> None:
        shell = shutil.which("pwsh") or shutil.which("powershell")
        with tempfile.TemporaryDirectory() as tmp:
            destination = Path(tmp) / "skills" / "chemdraw"
            result = subprocess.run(
                [shell, "-NoProfile", "-File", str(INSTALLER), "-Runtime", "-Python", sys.executable,
                 "-Extras", "publication", "-Destination", str(destination)],
                capture_output=True, text=True, encoding="utf-8-sig",
            )
        if sys.version_info >= (3, 14) or sys.version_info < (3, 10):
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("3.10-3.13", result.stdout + result.stderr)
            return
        self.assertEqual(result.returncode, 0, result.stderr)
        runtime = json.loads(result.stdout)["runtime"]
        self.assertEqual(runtime["action"], "create")
        # resolve() normalizes 8.3 short names (e.g. RUNNER~1) that PowerShell expands.
        self.assertEqual(Path(runtime["venv"]).resolve(), (destination.parent / "chemdraw-venv").resolve())
        self.assertEqual(runtime["extras"], ["publication"])
        self.assertFalse(destination.exists(), "a proposal must not install anything")

    def test_apply_writes_an_installation_manifest(self) -> None:
        shell = shutil.which("pwsh") or shutil.which("powershell")
        with tempfile.TemporaryDirectory() as tmp:
            destination = Path(tmp) / "skills" / "chemdraw"
            result = subprocess.run(
                [shell, "-NoProfile", "-File", str(INSTALLER), "-Apply", "-Python", sys.executable,
                 "-Destination", str(destination)],
                capture_output=True, text=True, encoding="utf-8-sig",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            record = json.loads(result.stdout)
            self.assertEqual(record["source_fingerprint"], record["installed_fingerprint"])
            manifest = json.loads((destination / "manifest.json").read_text(encoding="utf-8"))
            self.assertIn("SKILL.md", manifest)
            check = subprocess.run(
                [sys.executable, str(destination / "scripts" / "check_installation.py")],
                capture_output=True, text=True,
            )
            self.assertEqual(check.returncode, 0, check.stdout + check.stderr)

    def test_existing_skill_backup_is_outside_discovery_directory(self) -> None:
        shell = shutil.which("pwsh") or shutil.which("powershell")
        self.assertIsNotNone(shell, "PowerShell is required to test the supplied installer")
        with tempfile.TemporaryDirectory() as tmp:
            agent_home = Path(tmp) / ".claude"
            destination = agent_home / "skills" / "chemdraw"
            destination.mkdir(parents=True)
            (destination / "SKILL.md").write_text("existing", encoding="ascii")

            completed = subprocess.run(
                [
                    str(shell),
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(INSTALLER),
                    "-Destination",
                    str(destination),
                ],
                check=True,
                capture_output=True,
                text=True,
                encoding="utf-8-sig",
            )
            proposal = json.loads(completed.stdout)
            destination_survived = destination.is_dir()

        backup_root = Path(proposal["backup_root"])
        self.assertEqual(backup_root.name, "chemdraw")
        self.assertEqual(backup_root.parent.name, "skills")
        self.assertEqual(backup_root.parent.parent.name, "backups")
        self.assertNotEqual(backup_root.parent, destination.parent)
        self.assertEqual(Path(proposal["backup"]).parent, backup_root)
        self.assertTrue(destination_survived)


if __name__ == "__main__":
    unittest.main()
