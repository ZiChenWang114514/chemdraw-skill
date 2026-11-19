"""The plugin is built from the one Skill folder; nothing is kept as a second copy."""

from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import build_plugin  # noqa: E402


class PluginBuildTests(unittest.TestCase):
    def build(self, folder: str) -> Path:
        return build_plugin.build(Path(folder) / "out")

    def test_the_plugin_holds_the_skill_without_its_tests(self):
        with tempfile.TemporaryDirectory() as folder:
            plugin = self.build(folder)
            skill = plugin / "skills" / "chemdraw"
            self.assertTrue((skill / "SKILL.md").is_file())
            self.assertTrue((skill / "scripts" / "cdx.py").is_file())
            self.assertFalse((skill / "tests").exists())
            self.assertFalse(list(plugin.rglob("__pycache__")))
            self.assertEqual((skill / "SKILL.md").read_bytes(),
                             (ROOT / "skill" / "chemdraw" / "SKILL.md").read_bytes())

    def test_the_plugin_manifest_follows_the_toolkit_version(self):
        with tempfile.TemporaryDirectory() as folder:
            plugin = self.build(folder)
            manifest = json.loads((plugin / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["name"], "chemdraw-skill")
            self.assertEqual(manifest["version"], build_plugin.toolkit_version())
            self.assertIn("ChemDraw", manifest["description"])
            self.assertTrue(manifest["repository"].startswith("https://github.com/"))

    def test_every_file_is_listed_with_its_checksum(self):
        with tempfile.TemporaryDirectory() as folder:
            plugin = self.build(folder)
            listed = json.loads((plugin / "MANIFEST.json").read_text(encoding="utf-8"))["files"]
            present = {path.relative_to(plugin).as_posix() for path in plugin.rglob("*")
                       if path.is_file() and path.name != "MANIFEST.json"}
            self.assertEqual(set(listed), present)
            for name, digest in listed.items():
                self.assertEqual(hashlib.sha256((plugin / name).read_bytes()).hexdigest(), digest, name)

    def test_an_existing_folder_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as folder:
            self.build(folder)
            with self.assertRaises(FileExistsError):
                self.build(folder)

    def test_no_built_plugin_is_committed(self):
        self.assertFalse((ROOT / ".claude-plugin").exists())
        self.assertFalse((ROOT / "skills").exists())


if __name__ == "__main__":
    unittest.main()
