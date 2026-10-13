"""Tests for the static cdxml-toolkit interface inventory generator."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import tempfile
import textwrap
import unittest
from unittest import mock


MODULE_PATH = Path(__file__).with_name("audit_toolkit_interfaces.py")


def load_auditor():
    if not MODULE_PATH.is_file():
        raise AssertionError("audit_toolkit_interfaces.py has not been implemented")
    spec = importlib.util.spec_from_file_location("audit_toolkit_interfaces", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class InterfaceAuditTests(unittest.TestCase):
    def test_inventory_labels_the_loaded_source_version(self):
        import cdxml_toolkit
        auditor = load_auditor()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / 'module.py').write_text('def work(): pass\n')
            out = root / 'out.md'
            with mock.patch.object(cdxml_toolkit, '__version__', '9.9.9'), mock.patch.object(
                sys, 'argv', ['audit', '--package-root', str(root), '--output', str(out)]):
                auditor.main()
            self.assertIn('cdxml-toolkit 9.9.9', out.read_text())

    def test_scans_public_functions_classes_and_methods_only(self):
        auditor = load_auditor()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "sample_pkg"
            root.mkdir()
            (root / "example.py").write_text(
                textwrap.dedent(
                    '''
                    def useful(value: int = 2) -> str:
                        """Return a useful value."""
                        return str(value)

                    def _private():
                        pass

                    def main():
                        pass

                    class Helper:
                        """Public helper class."""

                        def run(self, path: str) -> bool:
                            """Run the helper."""
                            return True

                        def _hidden(self):
                            pass

                        @property
                        def count(self) -> int:
                            return 1
                    '''
                ),
                encoding="utf-8",
            )
            symbols = auditor.scan_package(root)

        names = [symbol["qualified_name"] for symbol in symbols]
        self.assertEqual(names, ["Helper", "Helper.count", "Helper.run", "useful"])
        count = next(symbol for symbol in symbols if symbol["qualified_name"] == "Helper.count")
        self.assertEqual(count["kind"], "property")
        self.assertEqual(count["signature"], "Helper.count")
        useful = next(symbol for symbol in symbols if symbol["qualified_name"] == "useful")
        self.assertEqual(useful["signature"], "useful(value: int = 2) -> str")
        self.assertEqual(useful["summary"], "Return a useful value.")

    def test_renders_progressive_inventory_with_module_links(self):
        auditor = load_auditor()
        symbols = [
            {
                "module": "layout.cleanup",
                "qualified_name": "run_cleanup",
                "kind": "function",
                "signature": "run_cleanup(input_path: str)",
                "summary": "Clean a scheme.",
                "line": 12,
            }
        ]
        rendered = auditor.render_inventory("0.5.17", symbols)
        self.assertIn("cdxml-toolkit 0.5.17", rendered)
        self.assertIn("toolkit-render-layout-interfaces.md", rendered)
        self.assertIn("`run_cleanup(input_path: str)`", rendered)
        self.assertIn("Clean a scheme.", rendered)

    def test_renders_small_index_and_domain_shard(self):
        auditor = load_auditor()
        symbols = [
            {
                "module": "layout.cleanup", "qualified_name": "run_cleanup",
                "kind": "function", "signature": "run_cleanup(path: str)",
                "summary": "Clean a scheme.", "line": 12,
            }
        ]
        index, shards = auditor.render_inventory_shards("0.5.17", symbols)
        self.assertIn("inventory/render-layout.md", index)
        self.assertIn("render-layout.md", shards)
        self.assertIn("`run_cleanup(path: str)`", shards["render-layout.md"])

    def test_scan_fails_closed_on_unparseable_module(self):
        auditor = load_auditor()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "sample_pkg"
            root.mkdir()
            broken = root / "broken.py"
            broken.write_text("def incomplete(:\n", encoding="utf-8")

            with self.assertRaisesRegex(RuntimeError, r"broken\.py"):
                auditor.scan_package(root)

    def test_inventory_generator_writes_lf_on_windows(self):
        auditor = load_auditor()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "sample_pkg"
            root.mkdir()
            (root / "example.py").write_text(
                "def useful() -> bool:\n    return True\n",
                encoding="utf-8",
            )
            output_dir = Path(temp_dir) / "references"
            with mock.patch.object(
                sys,
                "argv",
                [
                    "audit_toolkit_interfaces.py",
                    "--package-root",
                    str(root),
                    "--output-dir",
                    str(output_dir),
                    "--version",
                    "0.0.0",
                ],
            ):
                self.assertEqual(auditor.main(), 0)
            generated = [
                output_dir / "toolkit-public-inventory.md",
                *(output_dir / "inventory").glob("*.md"),
            ]
            self.assertTrue(generated)
            for path in generated:
                self.assertNotIn(b"\r\n", path.read_bytes(), path.name)


if __name__ == "__main__":
    unittest.main()
