from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "scripts" / "install.py"


def run(*args: str, home: Path | None = None) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    if home is not None:
        env.update(HOME=str(home), USERPROFILE=str(home), LOCALAPPDATA=str(home / "data"),
                   XDG_DATA_HOME=str(home / "data"))
    return subprocess.run([sys.executable, str(INSTALLER), *args], capture_output=True, text=True,
                          encoding="utf-8", env=env)


class InstallerTests(unittest.TestCase):
    def test_default_proposal_targets_the_claude_skill_folder_and_installs_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            result = run(home=home)
            self.assertEqual(result.returncode, 0, result.stderr)
            proposal = json.loads(result.stdout)
            self.assertEqual(proposal["status"], "proposal")
            [item] = proposal["installations"]
            self.assertEqual(Path(item["destination"]).parts[-3:], (".claude", "skills", "chemdraw"))
            self.assertEqual(proposal["runtime"], {"action": "skip"})
            self.assertFalse((home / ".claude").exists())

    def test_every_agent_preset_has_user_and_project_folders(self) -> None:
        agents = ["claude", "agents", "gemini", "copilot", "cursor", "opencode"]
        with tempfile.TemporaryDirectory() as tmp:
            result = run("--agent", *agents, "--project", tmp)
            self.assertEqual(result.returncode, 0, result.stderr)
            folders = {Path(i["destination"]).relative_to(Path(tmp).resolve()).as_posix()
                       for i in json.loads(result.stdout)["installations"]}
        self.assertEqual(folders, {f"{d}/skills/chemdraw" for d in
                                   (".claude", ".agents", ".gemini", ".github", ".cursor", ".opencode")})

    def test_apply_installs_each_agent_copy_with_a_manifest_and_no_caches(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            result = run("--agent", "claude", "agents", "--apply", home=home)
            self.assertEqual(result.returncode, 0, result.stderr)
            record = json.loads(result.stdout)
            for item in record["installations"]:
                self.assertEqual(item["installed_fingerprint"], record["source_fingerprint"])
                skill = Path(item["destination"])
                self.assertEqual(list(skill.rglob("__pycache__")), [])
                check = subprocess.run([sys.executable, str(skill / "scripts" / "check_installation.py")],
                                       capture_output=True, text=True)
                self.assertEqual(check.returncode, 0, check.stdout + check.stderr)

    def test_reinstall_moves_the_old_copy_outside_every_skill_folder(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            skill = home / ".claude" / "skills" / "chemdraw"
            skill.mkdir(parents=True)
            (skill / "SKILL.md").write_text("old", encoding="ascii")
            result = run("--apply", home=home)
            self.assertEqual(result.returncode, 0, result.stderr)
            backup = Path(json.loads(result.stdout)["installations"][0]["backup"])
            self.assertEqual((backup / "SKILL.md").read_text(encoding="ascii"), "old")
            self.assertEqual((backup / "BACKUP_ORIGIN.txt").read_text(encoding="utf-8").strip(), str(skill))
            self.assertNotIn("skills", backup.relative_to(home).parts)
            self.assertNotEqual((skill / "SKILL.md").read_text(encoding="utf-8"), "old")

    def test_failed_install_restores_the_previous_copy(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            skill = home / ".claude" / "skills" / "chemdraw"
            skill.mkdir(parents=True)
            (skill / "SKILL.md").write_text("old", encoding="ascii")
            sys.path.insert(0, str(ROOT / "scripts"))
            try:
                import install
            finally:
                sys.path.pop(0)
            real = install.fingerprint(install.SOURCE)
            # The staged copy verifies, the swapped-in copy does not: the old copy must come back.
            with mock.patch.object(install, "fingerprint", side_effect=[real, "corrupted"]):
                with self.assertRaises(RuntimeError):
                    install.install_one(skill, real, home / "backups")
            self.assertEqual((skill / "SKILL.md").read_text(encoding="ascii"), "old")
            self.assertEqual([p.name for p in skill.parent.iterdir()], ["chemdraw"])

    def test_runtime_proposal_uses_one_shared_venv(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            result = run("--agent", "claude", "gemini", "--runtime", "--python", sys.executable,
                         "--extras", "publication", home=home)
        if not ((3, 10) <= sys.version_info[:2] <= (3, 13)):
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("3.10-3.13", result.stdout + result.stderr)
            return
        self.assertEqual(result.returncode, 0, result.stderr)
        runtime = json.loads(result.stdout)["runtime"]
        self.assertEqual(runtime["action"], "create")
        self.assertEqual(Path(runtime["venv"]).parts[-2:], ("chemdraw-skill", "venv"))
        self.assertEqual(runtime["extras"], ["publication"])

    def test_runtime_reuses_a_venv_beside_an_existing_skill(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            venv = home / ".claude" / "skills" / "chemdraw-venv"
            python = venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
            python.parent.mkdir(parents=True)
            python.write_bytes(b"")
            result = run("--runtime", home=home)
            self.assertEqual(result.returncode, 0, result.stderr)
            runtime = json.loads(result.stdout)["runtime"]
        self.assertEqual(runtime["action"], "reuse")
        self.assertEqual(Path(runtime["venv"]).name, "chemdraw-venv")

    def test_destination_inside_the_source_is_refused(self) -> None:
        result = run("--destination", str(ROOT / "skill" / "chemdraw" / "nested"))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("outside the repository Skill source", result.stderr)

    def test_installer_is_runnable_without_third_party_packages(self) -> None:
        result = subprocess.run([sys.executable, "-I", "-S", str(INSTALLER), "--help"],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--agent", result.stdout)


if __name__ == "__main__":
    unittest.main()
