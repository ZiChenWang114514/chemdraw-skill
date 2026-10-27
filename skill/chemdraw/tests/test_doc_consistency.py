"""Facts that several documents state must agree with the code that owns them."""

from __future__ import annotations

import re
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parent.parent
REPO = SKILL_ROOT.parent.parent
REFERENCES = SKILL_ROOT / "references"
PROFILE_ROW = re.compile(r"^\| `(\w+)`(?: \(default\))? \| (\d+) \|", re.MULTILINE)
TOOL_COUNT = re.compile(r"\b(\d+)[- ]tools?\b")
SUBCOMMAND = re.compile(r"sub\.add_parser\('([a-z-]+)'")


class ToolCountTests(unittest.TestCase):
    def test_toolkit_profile_table_matches_registry(self):
        from cdxml_toolkit.mcp_runtime import tool_registry

        table = dict(
            PROFILE_ROW.findall((REPO / "toolkit" / "README.md").read_text(encoding="utf-8"))
        )
        self.assertEqual(set(table), {"full", "core", "office", "analysis", "chemscript"})
        live = {name: len(tool_registry.build_registry(name)) for name in table}
        self.assertEqual({k: int(v) for k, v in table.items()}, live)

    def test_prose_tool_counts_are_real_profile_sizes(self):
        from cdxml_toolkit.mcp_runtime import tool_registry

        known = {
            len(tool_registry.build_registry(name))
            for name in ("full", "core", "office", "analysis", "chemscript")
        }
        known.add(15)  # the compatible core server in cdxml_toolkit.mcp_server
        generated = {"mcp-tools.md", "mcp-schema.json"}
        stale: list[str] = []
        pages = [REPO / "toolkit" / "README.md", *(REPO / "toolkit" / "docs").glob("*.md")]
        for page in pages:
            if page.name in generated:
                continue
            for number in TOOL_COUNT.findall(page.read_text(encoding="utf-8")):
                if int(number) not in known:
                    stale.append(f"{page.relative_to(REPO).as_posix()}: {number} tools")
        self.assertEqual(stale, [])


class CommandReferenceTests(unittest.TestCase):
    def test_every_cdx_subcommand_is_in_the_command_reference(self):
        source = (SKILL_ROOT / "scripts" / "cdx.py").read_text(encoding="utf-8")
        names = set(SUBCOMMAND.findall(source))
        self.assertGreaterEqual(len(names), 15)
        reference = (REFERENCES / "agent-integration.md").read_text(encoding="utf-8")
        block = reference.split("## Command reference", 1)[1].split("```", 2)[1]
        documented = {
            line.split()[1] for line in block.splitlines() if line.startswith("cdx.py ")
        }
        self.assertEqual(sorted(names - documented), [])


class GeneratedWordingTests(unittest.TestCase):
    def test_interface_pages_do_not_deny_existing_tools(self):
        for name in ("interface-com.md", "interface-menu.md"):
            text = (REFERENCES / name).read_text(encoding="utf-8")
            self.assertNotIn("No generic COM tool exists yet", text, name)
            self.assertNotRegex(text, r"\byet\b", name)

    def test_signatures_do_not_require_a_closed_chemdraw(self):
        text = (REFERENCES / "mcp-signatures.md").read_text(encoding="utf-8")
        self.assertNotRegex(text, r"(?i)chemdraw must be closed|closed before calling")
        self.assertNotIn("uses ChemDraw COM exclusively", text)


if __name__ == "__main__":
    unittest.main()
