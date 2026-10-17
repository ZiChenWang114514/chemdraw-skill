"""Consistency tests for the chemdraw skill's progressive interface catalog."""

from __future__ import annotations

import re
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock


SKILL_ROOT = Path(__file__).resolve().parent.parent
REFERENCES = SKILL_ROOT / "references"
TOOL_HEADING = re.compile(r"^### `([a-z][a-z0-9_]*)\(", re.MULTILINE)


class InterfaceCatalogTests(unittest.TestCase):
    def test_every_mcp_tool_is_documented(self):
        from cdxml_toolkit.mcp_runtime import mcp_server

        live_tools = set(mcp_server.build_server()._tool_manager._tools)
        documented = set(
            TOOL_HEADING.findall(
                (REFERENCES / "mcp-signatures.md").read_text(encoding="utf-8")
            )
        )
        self.assertGreaterEqual(len(live_tools), 30)
        self.assertEqual(live_tools, documented)

    def test_generated_mcp_signatures_are_current(self):
        import cdx

        # Distribution/profile lines and docstring indentation (Python 3.13
        # dedents docstrings) are not part of the signature contract.
        self.assertTrue(cdx._signatures_current(), "run `cdx.py regen-signatures`")

    def test_signature_generator_writes_lf_on_windows(self):
        import cdx

        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "mcp-signatures.md"
            with mock.patch.object(cdx, "SIGNATURES", output):
                cdx.write_signatures()
            data = output.read_bytes()
            self.assertNotIn(b"\r\n", data)
            self.assertIn(b"Profile: `full (default)`", data)

    def test_decimer_guide_defers_exact_signature_to_generated_reference(self):
        guide = (REFERENCES / "decimer-api.md").read_text(encoding="utf-8")
        self.assertIn("mcp-signatures.md", guide)
        self.assertNotRegex(guide, r"extract_structures_via_decimer_api\s*\(")

    def test_every_inventory_module_has_existing_curated_guidance(self):
        index = (REFERENCES / "toolkit-public-inventory.md").read_text(encoding="utf-8")
        shards = re.findall(r"\(inventory/([^)]+\.md)\)", index)
        self.assertGreaterEqual(len(shards), 5)
        self.assertEqual([name for name in shards if not (REFERENCES / "inventory" / name).is_file()], [])


if __name__ == "__main__":
    unittest.main()
