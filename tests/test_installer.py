from __future__ import annotations

import json
from pathlib import Path
import shutil
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

    def test_default_destination_is_agent_neutral(self) -> None:
        shell = shutil.which("pwsh") or shutil.which("powershell")
        result = subprocess.run(
            [shell, "-NoProfile", "-File", str(INSTALLER)],
            capture_output=True, text=True, encoding="utf-8-sig", check=True,
        )
        proposal = json.loads(result.stdout)
        self.assertEqual(Path(proposal["destination"]).parts[-3:], (".agents", "skills", "chemdraw"))
        self.assertFalse(proposal["configure_mcp"])

    def test_existing_skill_backup_is_outside_discovery_directory(self) -> None:
        shell = shutil.which("pwsh") or shutil.which("powershell")
        self.assertIsNotNone(shell, "PowerShell is required to test the supplied installer")
        with tempfile.TemporaryDirectory() as tmp:
            codex_home = Path(tmp) / ".codex"
            destination = codex_home / "skills" / "chemdraw"
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
