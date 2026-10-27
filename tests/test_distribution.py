from __future__ import annotations

import json
import re
from pathlib import Path
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skill" / "chemdraw"


class DistributionTests(unittest.TestCase):
    CHINESE_DOCUMENTS = {"README.zh-cn.md", "docs/guide.zh-cn.md", "docs/zh-cn.md"}
    # The landing page (docs/website.md) has a Chinese home page and error page.
    CHINESE_PAGES = {"site/index.html", "site/404.html"}

    def test_chinese_text_is_limited_to_chinese_documents(self) -> None:
        tracked = subprocess.check_output(
            ["git", "ls-files", "-z"], cwd=ROOT
        ).decode("utf-8").split("\0")
        violations = []
        for name in filter(None, tracked):
            if name in self.CHINESE_DOCUMENTS or name in self.CHINESE_PAGES:
                continue
            path = ROOT / name
            try:
                content = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            if re.search(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]", content):
                violations.append(name)
        self.assertEqual(violations, [], "Use English outside the Chinese documents")

    def test_chinese_documents_are_actually_chinese(self) -> None:
        # Files named *.zh-cn.md / zh-cn.md must be translations, not copies of the English text.
        cjk = re.compile("[" + chr(0x4E00) + "-" + chr(0x9FFF) + "]")  # CJK ideographs, kept out of this file
        for name in sorted(self.CHINESE_DOCUMENTS):
            with self.subTest(document=name):
                text = (ROOT / name).read_text(encoding="utf-8")
                self.assertGreaterEqual(len(cjk.findall(text)), 100, f"{name} is not written in Chinese")
        self.assertNotEqual((ROOT / "docs/guide.zh-cn.md").read_bytes(), (ROOT / "docs/guide.md").read_bytes())

    def test_required_repository_files_exist(self) -> None:
        required = [
            "README.md",
            "README.zh-cn.md",
            "LICENSE",
            "AGENTS.md",
            ".gitignore",
            ".gitattributes",
            ".github/contributing.md",
            ".github/SECURITY.md",
            ".github/workflows/validate.yml",
            ".github/ISSUE_TEMPLATE/bug_report.yml",
            ".github/ISSUE_TEMPLATE/feature_request.yml",
            "docs/guide.md",
            "docs/guide.zh-cn.md",
            "docs/zh-cn.md",
            "scripts/check_prerequisites.ps1",
            "scripts/install.py",
            "scripts/validate_distribution.py",
        ]
        missing = [item for item in required if not (ROOT / item).is_file()]
        self.assertEqual(missing, [], f"Missing repository files: {missing}")

    def test_root_markdown_is_minimal(self) -> None:
        root_markdown = {path.name for path in ROOT.glob("*.md")}
        self.assertEqual(root_markdown, {"README.md", "README.zh-cn.md", "AGENTS.md"})

    def test_repository_documentation_is_consolidated(self) -> None:
        repository_markdown = {
            path.relative_to(ROOT).as_posix()
            for path in ROOT.rglob("*.md")
            if path.relative_to(ROOT).parts[0] not in {
                ".git", "skill", "toolkit", ".pytest_cache", ".mypy_cache", ".ruff_cache"
            }
        }
        self.assertEqual(
            repository_markdown,
            {
                "README.md",
                "README.zh-cn.md",
                "AGENTS.md",
                ".github/contributing.md",
                ".github/SECURITY.md",
                ".github/pull_request_template.md",
                "docs/guide.md",
                "docs/guide.zh-cn.md",
                "docs/zh-cn.md",
                "docs/website.md",
            },
        )

    def test_toolkit_documentation_stays_in_its_documented_places(self) -> None:
        toolkit = ROOT / "toolkit"
        top = {path.name for path in toolkit.glob("*.md")}
        self.assertEqual(top, {"README.md", "AGENTS.md", "NOTICE.md"})
        allowed_roots = {"docs", "examples", "experiments", "assets"}
        stray = [path.relative_to(ROOT).as_posix() for path in toolkit.rglob("*.md")
                 if path.parent != toolkit and path.relative_to(toolkit).parts[0] not in allowed_roots]
        self.assertEqual(stray, [])
        # Workflows only run from the repository root; a nested .github would silently do nothing.
        self.assertFalse((toolkit / ".github").exists())
        self.assertTrue((toolkit / "LICENSE").is_file() and (toolkit / "NOTICE.md").is_file())

    def test_no_personal_machine_paths_in_tracked_sources(self) -> None:
        # samples/ keeps the recorded provenance of its fixtures and is exempt.
        pattern = re.compile(r"[A-Za-z]:[\\/]Users[\\/](?!<|you|user|USERNAME|example)[A-Za-z0-9_.-]+[\\/]")
        tracked = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).decode("utf-8").split("\0")
        offenders = []
        for name in filter(None, tracked):
            if name.startswith("toolkit/samples/") or not name.endswith((".py", ".md", ".ps1", ".yml", ".yaml", ".toml")):
                continue
            path = ROOT / name
            if path.is_file() and pattern.search(path.read_text(encoding="utf-8", errors="replace")):
                offenders.append(name)
        self.assertEqual(offenders, [])

    def test_markush_example_ships_with_the_skill_and_matches_the_toolkit(self) -> None:
        # An installed Skill has no toolkit/examples, so markush.md points at its own copy.
        for name in ("indole-macrocycle.json", "indole-macrocycle.layout.json"):
            bundled = SKILL / "assets" / "markush" / name
            source = ROOT / "toolkit" / "examples" / "markush" / name
            self.assertEqual(json.loads(bundled.read_text(encoding="utf-8")),
                             json.loads(source.read_text(encoding="utf-8")), name)
        self.assertIn("<skill>/assets/markush/indole-macrocycle.json",
                      (SKILL / "references" / "markush.md").read_text(encoding="utf-8"))

    def test_skill_bundle_is_self_contained(self) -> None:
        self.assertTrue((SKILL / "SKILL.md").is_file())
        self.assertTrue((SKILL / "references" / "workflow-router.md").is_file())
        self.assertTrue((SKILL / "scripts" / "check_prerequisites.ps1").is_file())
        self.assertTrue((SKILL / "scripts" / "cdx.py").is_file())
        self.assertTrue((SKILL / "scripts" / "acs_builder.py").is_file())
        self.assertTrue((SKILL / "tests" / "conftest.py").is_file())
        self.assertFalse((SKILL / "README.md").exists())
        self.assertFalse((SKILL / "manifest.json").exists(), "manifest.json is written by the installer")
        # Thin re-export modules were removed; the toolkit package is imported directly.
        self.assertEqual(sorted(p.name for p in (SKILL / "scripts").glob("test_*.py")), [])

    def test_agent_names_only_appear_in_installation_documents(self) -> None:
        # The Skill is client-neutral; agents are named only where users pick an install target.
        brands = re.compile(r"\b(co" + r"dex|open" + r"ai|gemini|copilot|opencode)\b", re.IGNORECASE)
        allowed = {"README.md", "README.zh-cn.md", "docs/guide.md", "docs/guide.zh-cn.md",
                   "site/index.html", "site/en/index.html",
                   ".github/workflows/validate.yml", "scripts/install.py", "scripts/agent_eval.py",
                   "skill/chemdraw/references/agent-integration.md",
                   # The toolkit documents and implements one compatibility alias (`--profile codex`).
                   "toolkit/README.md", "toolkit/AGENTS.md", "toolkit/docs/maintenance.md",
                   "toolkit/cdxml_toolkit/mcp_runtime/tool_registry.py"}
        tracked = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).decode("utf-8").split("\0")
        offenders = []
        for name in filter(None, tracked):
            if name in allowed or name.startswith("tests/") or "/tests/" in name:
                continue
            try:
                text = (ROOT / name).read_text(encoding="utf-8")
            except (UnicodeDecodeError, FileNotFoundError):
                continue
            if brands.search(text):
                offenders.append(name)
        self.assertEqual(offenders, [])
        adapters = [name for name in tracked if name.endswith((".yaml", ".svg")) and "agents/" in name]
        self.assertEqual(adapters, [], "client-specific adapter files")

    def test_generated_and_local_state_are_not_distributed(self) -> None:
        forbidden_names = {"__pycache__", ".pytest_cache", ".mypy_cache", ".env"}
        if (ROOT / ".git").is_dir():
            completed = subprocess.run(
                ["git", "ls-files", "-z"],
                cwd=ROOT,
                check=True,
                capture_output=True,
            )
            paths = [ROOT / item.decode("utf-8") for item in completed.stdout.split(b"\0") if item]
        else:
            paths = [
                path
                for path in ROOT.rglob("*")
                if not any(part in forbidden_names for part in path.relative_to(ROOT).parts)
            ]
        offenders = [
            path.relative_to(ROOT).as_posix()
            for path in paths
            if path.name in forbidden_names or path.suffix in {".pyc", ".pyo"}
        ]
        self.assertEqual(offenders, [], f"Generated/local files present: {offenders}")

    def test_skill_has_no_machine_specific_paths_or_credentials(self) -> None:
        # Build sensitive tokens in pieces so this test does not flag itself.
        patterns = {
            "local user profile": re.compile(r"C:\\Users\\" + "11234", re.IGNORECASE),
            "local legacy runtime": re.compile(r"D:\\" + "ProgramFiles", re.IGNORECASE),
            "OpenAI-style secret": re.compile(r"s" + r"k-[A-Za-z0-9_-]{20,}"),
            "GitHub classic token": re.compile(r"g" + r"hp_[A-Za-z0-9]{20,}"),
            "GitHub fine-grained token": re.compile(r"github" + r"_pat_[A-Za-z0-9_]{20,}"),
        }
        offenders: list[str] = []
        for path in SKILL.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in {".md", ".py", ".ps1", ".yaml", ".yml", ".json"}:
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            for label, pattern in patterns.items():
                if pattern.search(text):
                    offenders.append(f"{path.relative_to(ROOT).as_posix()}: {label}")
        self.assertEqual(offenders, [], "Unsafe distribution content:\n" + "\n".join(offenders))

    def test_local_markdown_links_resolve(self) -> None:
        link_pattern = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")
        missing: list[str] = []
        for path in ROOT.rglob("*.md"):
            text = path.read_text(encoding="utf-8", errors="replace")
            for raw_target in link_pattern.findall(text):
                target = raw_target.strip().split("#", 1)[0]
                if not target or "://" in target or target.startswith("mailto:"):
                    continue
                candidate = (path.parent / target).resolve()
                if not candidate.exists():
                    missing.append(f"{path.relative_to(ROOT).as_posix()} -> {raw_target}")
        self.assertEqual(missing, [], "Broken local Markdown links:\n" + "\n".join(missing))

    def test_local_markdown_anchors_resolve(self) -> None:
        link_pattern = re.compile(r"(?<!!)\[[^\]]+\]\(([^)\s]+)\)")
        fence = re.compile(r"^\s*(```|~~~)")

        def slugs(path: Path) -> set[str]:
            found: set[str] = set()
            counts: dict[str, int] = {}
            in_fence = False
            body = path.read_text(encoding="utf-8", errors="replace")
            found.update(re.findall(r"""\b(?:id|name)=["']([^"']+)["']""", body))
            for line in body.splitlines():
                if fence.match(line):
                    in_fence = not in_fence
                    continue
                match = re.match(r"^#{1,6}\s+(.*?)\s*#*\s*$", line)
                if in_fence or not match:
                    continue
                title = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", match.group(1))
                slug = re.sub(r"[^\w\- ]", "", title.replace("`", "").lower()).replace(" ", "-")
                n = counts.get(slug, 0)
                counts[slug] = n + 1
                found.add(slug if n == 0 else f"{slug}-{n}")
            return found

        cache: dict[Path, set[str]] = {}
        missing: list[str] = []
        for path in ROOT.rglob("*.md"):
            if "node_modules" in path.parts:
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            for raw_target in link_pattern.findall(text):
                if "://" in raw_target or raw_target.startswith("mailto:") or "#" not in raw_target:
                    continue
                file_part, anchor = raw_target.split("#", 1)
                target = (path.parent / file_part).resolve() if file_part else path
                if target.suffix != ".md" or not target.exists() or not anchor:
                    continue
                if target not in cache:
                    cache[target] = slugs(target)
                if anchor.lower() not in cache[target]:
                    missing.append(f"{path.relative_to(ROOT).as_posix()} -> {raw_target}")
        self.assertEqual(missing, [], "Broken Markdown anchors:\n" + "\n".join(missing))

    def test_ci_has_pinned_full_portable_skill_validation(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "validate.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("full-portable-tests:", workflow)
        self.assertIn('python-version: "3.12"', workflow)
        self.assertIn('skill/chemdraw/scripts/install_runtime.py', workflow)
        import json
        baseline = json.loads((SKILL / 'runtime.json').read_text(encoding='utf-8'))
        self.assertRegex(baseline['commit'], r'^[0-9a-f]{40}$')
        self.assertIn('mcp-version: ["1.28.1", "2.0.0"]', workflow)
        self.assertIn('os: [windows-latest, ubuntu-latest]', workflow)
        self.assertIn('pytest skill/chemdraw/tests', workflow)
        self.assertIn('check_prerequisites.ps1', workflow)
        self.assertIn('installer-end-to-end:', workflow)
        self.assertIn('os: [windows-latest, ubuntu-latest, macos-latest]', workflow)


if __name__ == "__main__":
    unittest.main()
