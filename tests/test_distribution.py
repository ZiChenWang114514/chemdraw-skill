from __future__ import annotations

import re
from pathlib import Path
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skill" / "chemdraw"


class DistributionTests(unittest.TestCase):
    def test_chinese_text_is_limited_to_chinese_readme(self) -> None:
        tracked = subprocess.check_output(
            ["git", "ls-files", "-z"], cwd=ROOT
        ).decode("utf-8").split("\0")
        violations = []
        for name in filter(None, tracked):
            if name == "README.zh-cn.md":
                continue
            path = ROOT / name
            try:
                content = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            if re.search(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]", content):
                violations.append(name)
        self.assertEqual(violations, [], "Use English outside README.zh-cn.md")

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
                ".git", "skill", ".pytest_cache", ".mypy_cache", ".ruff_cache"
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
                "docs/guide.md",
                "docs/guide.zh-cn.md",
                "docs/zh-cn.md",
            },
        )

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
                   ".github/workflows/validate.yml", "scripts/install.py",
                   "skill/chemdraw/references/agent-integration.md"}
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

    def test_doctor_probes_are_opt_in(self) -> None:
        cdx = (SKILL / "scripts" / "cdx.py").read_text(encoding="utf-8")
        for flag in ("'--native'", "'--office'", "'--chemscript'", "'--paths'"):
            self.assertIn(flag, cdx)

    def test_removed_fastmcp_import_is_isolated_to_compatibility_module(self) -> None:
        matches = []
        for path in (ROOT / "skill" / "chemdraw" / "scripts").glob("*.py"):
            if path.name == "mcp_compat.py" or path.name.startswith("test_"):
                continue
            if "mcp.server.fastmcp" in path.read_text(encoding="utf-8"):
                matches.append(path.name)
        self.assertEqual(matches, [])


if __name__ == "__main__":
    unittest.main()
