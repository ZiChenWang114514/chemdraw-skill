"""Tests for the ChemDraw 2D Studio & Mol* 3D Workbench VS Code (.vsix) extension."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[1]
VSCODE_DIR = ROOT / "vscode"


def _load_builder():
    spec = importlib.util.spec_from_file_location(
        "chemdraw_build_vsix",
        VSCODE_DIR / "scripts" / "build_vsix.py",
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


class VsCodeExtensionTests(unittest.TestCase):
    def test_manifest_commands_views_and_custom_editors_match_extension_js(self) -> None:
        pkg = json.loads((VSCODE_DIR / "package.json").read_text(encoding="utf-8"))
        ext_js = (VSCODE_DIR / "src" / "extension.js").read_text(encoding="utf-8")

        declared_cmds = {c["command"] for c in pkg["contributes"]["commands"]}
        for kb in pkg["contributes"]["keybindings"]:
            self.assertIn(kb["command"], declared_cmds)
        for group_items in pkg["contributes"]["menus"].values():
            for item in group_items:
                self.assertIn(item["command"], declared_cmds)
        for cmd in declared_cmds:
            self.assertIn(f'"{cmd}"', ext_js, f"Command {cmd} missing in extension.js")

        for ce in pkg["contributes"]["customEditors"]:
            self.assertIn(f'"{ce["viewType"]}"', ext_js)

        for view in pkg["contributes"]["views"]["chemdraw-workbench"]:
            self.assertIn(f'"{view["id"]}"', ext_js)

    def test_build_vsix_produces_valid_opc_archive_and_parsers_work(self) -> None:
        builder = _load_builder()
        with tempfile.TemporaryDirectory() as tmp:
            vsix_path = Path(tmp) / "chemdraw-studio-test.vsix"
            icon = VSCODE_DIR / "media" / "icon.png"
            icon_before = icon.read_bytes()
            built = builder.build_vsix(vsix_path)
            self.assertEqual(icon.read_bytes(), icon_before, "a build must not rewrite the tracked icon")
            self.assertTrue(built.is_file())
            self.assertGreater(built.stat().st_size, 40_000)

            with zipfile.ZipFile(built, "r") as zf:
                names = set(zf.namelist())
                required = {
                    "[Content_Types].xml",
                    "extension.vsixmanifest",
                    "extension/package.json",
                    "extension/LICENSE.txt",
                    "extension/README.md",
                    "extension/CHANGELOG.md",
                    "extension/src/extension.js",
                    "extension/src/webview-bridge.js",
                    "extension/media/icon.png",
                    "extension/media/activity-icon.svg",
                    "extension/media/generated/studio-fragment.html",
                    "extension/media/generated/molstar-app.html",
                }
                self.assertTrue(required.issubset(names), required - names)
                icon_bytes = zf.read("extension/media/icon.png")
                self.assertTrue(icon_bytes.startswith(b"\x89PNG\r\n\x1a\n"))
                ET.fromstring(zf.read("extension.vsixmanifest").decode("utf-8"))
                ET.fromstring(zf.read("[Content_Types].xml").decode("utf-8"))

        node = shutil.which("node")
        if node:
            probe = r"""
const Module = require('module');
const orig = Module._load;
Module._load = function(req, parent, isMain) {
  if (req === 'vscode') return {};
  return orig(req, parent, isMain);
};
const ext = require(process.argv[1]);
const g1 = ext.parseCdxmlToGraph('<CDXML><page><fragment><n id="1" p="10 10"/><n id="2" p="24.4 10" Element="8"/><b id="9" B="1" E="2" Order="2"/></fragment></page></CDXML>', 'test.cdxml');
if (g1.atoms.length !== 2 || g1.atoms[1].s !== 'O' || g1.bonds[0].o !== 2) process.exit(2);
const mol = 'Ethanol\n  test\n\n  3  2  0  0  0  0            999 V2000\n    0.0000    0.0000    0.0000 C   0  0\n    1.5400    0.0000    0.0000 C   0  0\n    3.0800    0.0000    0.0000 O   0  0\n  1  2  1  0\n  2  3  1  1\nM  END\n';
const g2 = ext.parseMolfileToGraph(mol, 'etoh.mol');
if (g2.atoms.length !== 3 || g2.bonds[1].o !== 4) process.exit(3);
const s3 = ext.parse3DTextScene('2\nh2\nH 0 0 0\nH 0.74 0 0\n', '.xyz');
if (s3.atoms.length !== 2 || s3.bonds.length !== 1) process.exit(4);
console.log('EXTENSION_PARSERS_OK');
"""
            res = subprocess.run(
                [node, "-e", probe, str(VSCODE_DIR / "src" / "extension.js")],
                capture_output=True,
                text=True,
                check=True,
            )
            self.assertIn("EXTENSION_PARSERS_OK", res.stdout)


if __name__ == "__main__":
    unittest.main()
