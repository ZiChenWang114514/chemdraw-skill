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
MARKDOWN_LINK = re.compile(r"\[[^\]]+\]\(([^)]+\.md)\)")
TOOL_HEADING = re.compile(r"^### `([a-z][a-z0-9_]*)\(", re.MULTILINE)


class InterfaceCatalogTests(unittest.TestCase):
    def test_all_local_markdown_links_resolve(self):
        files = [SKILL_ROOT / "SKILL.md", *REFERENCES.rglob("*.md")]
        missing = []
        for source in files:
            text = source.read_text(encoding="utf-8")
            for target in MARKDOWN_LINK.findall(text):
                destination = (source.parent / target).resolve()
                if not destination.is_file():
                    missing.append(f"{source.name} -> {target}")
        self.assertEqual(missing, [])

    def test_every_mcp_tool_is_documented(self):
        sys.path.insert(0, str(SKILL_ROOT / "scripts"))
        import mcp_server

        live_tools = set(mcp_server.build_server()._tool_manager._tools)
        documented = set(
            TOOL_HEADING.findall(
                (REFERENCES / "mcp-signatures.md").read_text(encoding="utf-8")
            )
        )
        self.assertGreaterEqual(len(live_tools), 30)
        self.assertEqual(live_tools, documented)

    def test_generated_mcp_signatures_are_current(self):
        sys.path.insert(0, str(SKILL_ROOT / "scripts"))
        import generate_tool_reference

        expected = generate_tool_reference.render_reference()
        actual = (REFERENCES / "mcp-signatures.md").read_text(encoding="utf-8")
        # Documentation may be generated from a newer compatible source release.
        # The CI baseline must still match every tool signature and description.
        def contract(text):
            return re.sub(r'^Distribution: .*\n', '', text, flags=re.MULTILINE)
        self.assertEqual(contract(actual), contract(expected))

    def test_signature_generator_writes_lf_on_windows(self):
        sys.path.insert(0, str(SKILL_ROOT / "scripts"))
        import generate_tool_reference

        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "mcp-signatures.md"
            with mock.patch.object(
                sys,
                "argv",
                ["generate_tool_reference.py", "--output", str(output)],
            ):
                self.assertEqual(generate_tool_reference.main(), 0)
            self.assertNotIn(b"\r\n", output.read_bytes())

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
