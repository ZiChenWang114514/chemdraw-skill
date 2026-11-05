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
LISTED_SUBCOMMAND = re.compile(r"sub\.add_parser\('([a-z-]+)', help=")  # a command with no help text is hidden from --help


class ToolCountTests(unittest.TestCase):
    def test_toolkit_profile_table_matches_registry(self):
        from cdxml_toolkit.mcp_runtime import tool_registry

        table = dict(
            PROFILE_ROW.findall((REPO / "toolkit" / "README.md").read_text(encoding="utf-8"))
        )
        self.assertEqual(set(table), {"full", "core", "office", "analysis", "chemscript"})
        live = {name: len(tool_registry.build_registry(name)) for name in table}
        self.assertEqual({k: int(v) for k, v in table.items()}, live)

    def test_engines_tables_match_the_registry(self):
        from cdxml_toolkit.engines import table

        text = (REFERENCES / "engines.md").read_text(encoding="utf-8")
        self.assertEqual(text, table.render(text), "run `cdx.py regen-signatures` to rewrite the engines tables")

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
        names = set(LISTED_SUBCOMMAND.findall(source))
        self.assertGreaterEqual(len(names), 15)
        reference = (REFERENCES / "agent-integration.md").read_text(encoding="utf-8")
        block = reference.split("## Command reference", 1)[1].split("```", 2)[1]
        documented = {
            line.split()[1] for line in block.splitlines() if line.startswith("cdx.py ")
        }
        self.assertEqual(sorted(names - documented), [])

    def test_hidden_maintainer_commands_are_named_in_operations(self):
        source = (SKILL_ROOT / "scripts" / "cdx.py").read_text(encoding="utf-8")
        hidden = set(SUBCOMMAND.findall(source)) - set(LISTED_SUBCOMMAND.findall(source))
        self.assertEqual(hidden, {"regen-signatures", "regen-catalog", "chemscript-info"})
        operations = (REFERENCES / "operations.md").read_text(encoding="utf-8")
        self.assertEqual([name for name in hidden if f"cdx.py {name}" not in operations], [])


class CoverageTableTests(unittest.TestCase):
    ROW = re.compile(r"^\| [^|]+ \| ([\d,]+) \| ([\d,]+) \| ([\d,]+) \| ([\d,]+) \|$", re.MULTILINE)

    def test_guide_tables_match_the_catalog(self):
        from cdxml_toolkit.catalog import classify

        summary = classify.summarize(classify.all_rows())
        expected = [
            [sum(summary[layer].values()), *(summary[layer][tier] for tier in ("T1", "T2", "T3"))]
            for layer in ("chemscript", "com", "cdxml", "menu")
        ]
        for name in ("guide.md", "guide.zh-cn.md"):
            text = (REPO / "docs" / name).read_text(encoding="utf-8")
            found = [[int(v.replace(",", "")) for v in row] for row in self.ROW.findall(text)]
            self.assertEqual(found, expected, name)


class NamedToolTests(unittest.TestCase):
    """A tool-like name in an agent-facing page is a real tool, command or function, never a guess."""

    # Not tools: error codes, an image-review operation and a Python-only function. Each is checked below
    # against the code that defines it, so a rename cannot leave a dead entry here.
    ALLOWED = frozenset({
        "recognize_batch", "map_reuse", "chemdraw_in_use", "chemdraw_not_found", "chemdraw_not_running",
        "chemdraw_license_unavailable", "chemdraw_automation_not_authorized",
    })
    # Words that start tool names (besides the first word of every registered tool).
    VERBS = frozenset({"build", "convert", "analyze", "compare", "render", "parse", "draw", "extract"})
    GENERATED = frozenset({
        "mcp-signatures.md", "interface-catalog.md", "interface-chemscript.md", "interface-com.md",
        "interface-cdxml-model.md", "interface-menu.md", "recipes-chemdraw.md", "toolkit-public-inventory.md",
    })
    NAME = re.compile(r"`([a-z][a-z0-9]*(?:_[a-z0-9]+)+)(?=[`(])")

    def pages(self):
        generated = [p for p in REFERENCES.glob("*.md") if p.name in self.GENERATED or p.name.endswith("-interfaces.md")]
        return [SKILL_ROOT / "SKILL.md", REPO / "README.md", REPO / "README.zh-cn.md",
                *(p for p in sorted(REFERENCES.glob("*.md")) if p not in generated)]

    def test_tool_like_names_exist(self):
        signatures = (REFERENCES / "mcp-signatures.md").read_text(encoding="utf-8")
        tools = set(re.findall(r"^### `(\w+)\(", signatures, re.MULTILINE))
        self.assertGreater(len(tools), 50)
        known = tools | set(re.findall(r"\b[a-z][a-z0-9]*(?:_[a-z0-9]+)+\b", signatures))
        source = (SKILL_ROOT / "scripts" / "cdx.py").read_text(encoding="utf-8")
        known |= {name.replace("-", "_") for name in SUBCOMMAND.findall(source)}
        starts = {tool.split("_")[0] for tool in tools} | self.VERBS
        unknown: dict[str, list[str]] = {}
        for page in self.pages():
            for name in self.NAME.findall(page.read_text(encoding="utf-8")):
                if name.split("_")[0] in starts and name not in known | self.ALLOWED:
                    unknown.setdefault(name, []).append(page.name)
        self.assertEqual(unknown, {})

    def test_the_allowlist_names_real_code(self):
        code = "\n".join(
            path.read_text(encoding="utf-8", errors="replace")
            for root in (REPO / "toolkit" / "cdxml_toolkit", SKILL_ROOT / "scripts")
            for path in root.rglob("*.py")
        )
        dead = [name for name in self.ALLOWED if not re.search(rf"\b{name}\b", code)]
        self.assertEqual(dead, [])


class SkillEntryTests(unittest.TestCase):
    """SKILL.md is read first by every agent, so it stays short and self-sufficient."""

    def setUp(self):
        self.skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")

    def test_skill_md_stays_small(self):
        self.assertLessEqual(len(self.skill.splitlines()), 70)
        self.assertLessEqual(len(self.skill.encode("utf-8")), 7700)

    def test_first_command_form_needs_no_shell_quoting(self):
        self.assertIn("--args", self.skill)
        self.assertIn("cdx.py call", self.skill)

    def test_image_check_has_a_text_only_fallback(self):
        self.assertIn("cannot view images", self.skill)

    def test_host_without_chemdraw_is_covered_in_operations(self):
        operations = (REFERENCES / "operations.md").read_text(encoding="utf-8")
        self.assertIn("## No ChemDraw on this host", operations)
        self.assertIn("operations.md#no-chemdraw-on-this-host", self.skill)

    def test_every_linked_reference_exists(self):
        links = re.findall(r"\]\((references/[^)#]+)", self.skill)
        self.assertGreaterEqual(len(links), 12)
        self.assertEqual([p for p in links if not (SKILL_ROOT / p).is_file()], [])


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
