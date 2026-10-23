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
    def test_chemdraw_extras_are_default_where_chemdraw_runs(self) -> None:
        import importlib.util

        spec = importlib.util.spec_from_file_location("chemdraw_install", INSTALLER)
        installer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(installer)

        for platform in ("win32", "darwin"):
            self.assertIn("office", installer.default_extras(platform))
            self.assertIn("chemscript", installer.default_extras(platform))
        self.assertNotIn("office", installer.default_extras("linux"))

    def _installer(self):
        import importlib.util

        spec = importlib.util.spec_from_file_location("chemdraw_install", INSTALLER)
        installer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(installer)
        return installer

    def test_opsin_download_is_verified_before_it_is_kept(self) -> None:
        installer = self._installer()
        payload = b"opsin jar bytes"
        digest = __import__("hashlib").sha256(payload).hexdigest()

        class Response:
            def __init__(self, data):
                self.data = data

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

            def read(self, size=-1):
                data, self.data = (self.data, b"") if size < 0 else (self.data[:size], self.data[size:])
                return data

        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "opsin"
            jar = installer.install_opsin(folder, sha256=digest, opener=lambda url, timeout: Response(payload))
            self.assertEqual(jar.read_bytes(), payload)
            self.assertEqual(jar.name, installer.OPSIN_JAR_NAME)
            jar.unlink()
            with self.assertRaisesRegex(OSError, "SHA-256"):
                installer.install_opsin(folder, sha256="0" * 64, opener=lambda url, timeout: Response(payload))
            self.assertEqual(list(folder.iterdir()), [])

    def test_opsin_proposal_downloads_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp).resolve()
            result = run("--opsin", home=home)
            self.assertEqual(result.returncode, 0, result.stderr)
            opsin = json.loads(result.stdout)["opsin"]
            self.assertEqual(opsin["action"], "download")
            self.assertTrue(opsin["url"].startswith("https://github.com/dan2097/opsin/releases/download/"))
            self.assertEqual(Path(opsin["path"]).parent, home / "data" / "chemdraw-skill" / "opsin")
            self.assertFalse((home / "data" / "chemdraw-skill" / "opsin").exists())

    def test_default_proposal_targets_the_claude_skill_folder_and_installs_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp).resolve()
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
            home = Path(tmp).resolve()
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
            home = Path(tmp).resolve()
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
            home = Path(tmp).resolve()
            skill = home / ".claude" / "skills" / "chemdraw"
            skill.mkdir(parents=True)
            (skill / "SKILL.md").write_text("old", encoding="ascii")
            install = self._module()
            real = install.fingerprint(install.SOURCE)
            # The staged copy verifies, the swapped-in copy does not: the old copy must come back.
            with mock.patch.object(install, "fingerprint", side_effect=[real, "corrupted"]):
                with self.assertRaises(RuntimeError):
                    install.install_one(skill, real, home / "backups")
            self.assertEqual((skill / "SKILL.md").read_text(encoding="ascii"), "old")
            self.assertEqual([p.name for p in skill.parent.iterdir()], ["chemdraw"])

    def test_runtime_proposal_uses_one_shared_venv(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp).resolve()
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
        # The runtime is built from the toolkit bundled in this checkout, never from elsewhere.
        self.assertEqual(Path(runtime["toolkit_path"]), (ROOT / "toolkit").resolve())

    def test_runtime_reuses_a_venv_beside_an_existing_skill(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp).resolve()
            venv = home / ".claude" / "skills" / "chemdraw-venv"
            python = venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
            python.parent.mkdir(parents=True)
            python.write_bytes(b"")
            result = run("--runtime", home=home)
            self.assertEqual(result.returncode, 0, result.stderr)
            runtime = json.loads(result.stdout)["runtime"]
        self.assertEqual(runtime["action"], "reuse")
        self.assertEqual(Path(runtime["venv"]).name, "chemdraw-venv")

    def _module(self):
        sys.path.insert(0, str(ROOT / "scripts"))
        try:
            import install
        finally:
            sys.path.pop(0)
        return install

    def test_base_python_path_with_spaces_is_passed_as_one_argument(self) -> None:
        install = self._module()
        base = r"C:\Program Files\Python312\python.exe" if os.name == "nt" else "/opt/my python/bin/python3"
        with tempfile.TemporaryDirectory() as tmp:
            venv = Path(tmp) / "venv"
            plan = {"action": "create", "venv": str(venv), "python": str(install.venv_python(venv)),
                    "base_python": [base], "extras": ["publication"], "toolkit_path": None}
            with mock.patch.object(install.subprocess, "run") as run:
                run.return_value.returncode = 0
                install.install_runtime(plan, install.SOURCE)
        self.assertEqual(run.call_args_list[0].args[0][:3], [base, "-m", "venv"])

    def test_runtime_proposal_keeps_the_base_command_as_a_list(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp).resolve()
            result = run("--runtime", "--python", sys.executable, home=home)
        if not ((3, 10) <= sys.version_info[:2] <= (3, 13)):
            self.assertNotEqual(result.returncode, 0)
            return
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["runtime"]["base_python"], [sys.executable])

    def test_runtime_location_is_recorded_for_installations_and_the_checkout(self) -> None:
        install = self._module()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            copy, checkout = root / "skills" / "chemdraw", root / "repo" / "skill" / "chemdraw"
            copy.mkdir(parents=True)
            checkout.mkdir(parents=True)
            python = root / "elsewhere" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
            written = install.record_runtime([copy, checkout], python)
            self.assertEqual(written, [copy / "runtime.local.json", checkout / "runtime.local.json"])
            self.assertEqual(json.loads((checkout / "runtime.local.json").read_text(encoding="utf-8")),
                             {"runtime_python": str(python)})
            # A venv in a searched location needs no record.
            beside = install.venv_python(copy.parent / "chemdraw-venv")
            self.assertEqual(install.record_runtime([copy], beside), [])

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
