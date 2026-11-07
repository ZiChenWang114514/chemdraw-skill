"""Structural rules for the GitHub Actions workflows (standard library only)."""
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"


def workflows() -> dict[str, str]:
    return {path.name: path.read_text(encoding="utf-8") for path in sorted(WORKFLOWS.glob("*.yml"))}


def top_level_keys(text: str) -> set[str]:
    return set(re.findall(r"(?m)^([A-Za-z_-]+):", text))


class WorkflowTests(unittest.TestCase):
    def test_third_party_actions_are_pinned_to_a_commit(self) -> None:
        # A tag can be moved after review; a full commit SHA cannot. The comment keeps the
        # version readable and lets Dependabot propose updates.
        loose = []
        for name, text in workflows().items():
            for line_no, line in enumerate(text.splitlines(), 1):
                match = re.search(r"uses:\s*(\S+)(.*)", line)
                if not match or match.group(1).startswith("./"):
                    continue
                if not re.fullmatch(r"[\w.-]+/[\w./-]+@[0-9a-f]{40}", match.group(1)) \
                        or not re.match(r"\s*#\s*v\d", match.group(2)):
                    loose.append(f"{name}:{line_no}: {line.strip()}")
        self.assertEqual(loose, [], "Pin actions as owner/repo@<40-hex sha> # vX.Y.Z:\n" + "\n".join(loose))

    def test_workflows_triggered_by_pushes_cancel_superseded_runs(self) -> None:
        for name, text in workflows().items():
            triggers = text.split("\non:", 1)[1].split("\n\n", 1)[0] if "\non:" in text else ""
            if re.search(r"(?m)^  (push|pull_request):", triggers):
                self.assertIn("concurrency", top_level_keys(text), name)

    def test_validate_runs_once_per_change(self) -> None:
        # push on every branch plus pull_request ran each pull-request commit twice.
        text = workflows()["validate.yml"]
        self.assertRegex(text, r"(?m)^  push:\n    branches: \[main\]$")
        self.assertRegex(text, r"(?m)^  pull_request:$")

    def test_packages_are_built_by_one_reusable_workflow(self) -> None:
        texts = workflows()
        self.assertRegex(texts["build.yml"], r"(?m)^  workflow_call:")
        builders = [name for name, text in texts.items() if "python -m build" in text]
        self.assertEqual(builders, ["build.yml"])
        # The release reaches build.yml through validate.yml, so the artifact is uploaded once.
        self.assertIn("uses: ./.github/workflows/build.yml", texts["validate.yml"])
        self.assertNotIn("build.yml", texts["release.yml"])

    def test_releases_are_created_from_version_tags_only(self) -> None:
        text = workflows()["release.yml"]
        self.assertRegex(text, r"(?m)^    tags: \[\"v\*\"\]$")
        self.assertNotIn("branches", text)
        self.assertIn("gh release create", text)
        # Only the job that creates the release may write to the repository.
        self.assertRegex(text, r"(?m)^permissions:\n  contents: read$")
        self.assertEqual(text.count("contents: write"), 1)
        self.assertIn("uses: ./.github/workflows/validate.yml", text)
        self.assertRegex(text, r"(?m)^    needs: \[validate\]$")
        self.assertRegex(workflows()["validate.yml"], r"(?m)^  workflow_call:")

    def _toolkit_job(self, name: str) -> str:
        after = workflows()[name].split("  toolkit-tests:", 1)[1]
        return re.split(r"(?m)^  [a-z][\w-]*:$", after, maxsplit=1)[0]

    def test_windows_runs_the_newest_supported_python(self) -> None:
        pyproject = (ROOT / "toolkit" / "pyproject.toml").read_text(encoding="utf-8")
        ceiling = re.search(r'requires-python = ">=3\.(\d+),<3\.(\d+)"', pyproject).group(2)
        windows = r'- os: windows-latest\s+python-version: "3\.{}"'
        self.assertRegex(self._toolkit_job("validate.yml"), windows.format(int(ceiling) - 1))
        self.assertIn("ubuntu-latest", self._toolkit_job("validate.yml"))

    def test_pull_requests_run_a_small_set_of_jobs(self) -> None:
        # Every pull-request commit and every merge runs validate.yml, so it stays small;
        # a release runs the same file.
        text = workflows()["validate.yml"]
        entries = len(re.findall(r"(?m)^          - os: ", text))
        plain = len(re.findall(r"(?m)^    runs-on: (?!\$)", text))
        portable = re.search(r"os: \[([^\]]*)\]\n\s+mcp-version: \[([^\]]*)\]", text)
        combos = len(portable.group(1).split(",")) * len(portable.group(2).split(","))
        self.assertLessEqual(entries + plain + combos + text.count("uses: ./.github/workflows/build.yml"), 5)
        self.assertNotIn("macos-latest", text)

    def test_generated_mcp_reference_is_checked_once(self) -> None:
        job = workflows()["validate.yml"].split("  toolkit-tests:", 1)[1].split("\n  toolkit-mcp-compatibility:", 1)[0]
        self.assertIn("if: matrix.os == 'ubuntu-latest'", job)
        self.assertIn("generate_reference", job)

    def test_a_website_change_alone_skips_the_toolkit_jobs(self) -> None:
        def paths(text: str, key: str, trigger: str) -> list[str]:
            block = text.split(f"  {trigger}:\n", 1)[1].split(f"    {key}:\n", 1)[1]
            return re.findall(r'(?m)^      - "(.+)"$', re.split(r"\n(?!      - )", block, maxsplit=1)[0])

        all_workflows = workflows()
        site, validate = all_workflows["site.yml"], all_workflows["validate.yml"]
        skipped = paths(validate, "paths-ignore", "pull_request")
        self.assertIn("site/**", skipped)
        self.assertFalse([path for path in skipped if ".github" in path or "toolkit" in path or "skill" in path])
        self.assertEqual(paths(site, "paths", "pull_request"), skipped + [".github/workflows/site.yml"])
        self.assertEqual(paths(site, "paths", "push"), skipped + [".github/workflows/site.yml"])
        # A merge still runs everything.
        self.assertRegex(validate, r"(?m)^  push:\n    branches: \[main\]\n  pull_request:$")

    def test_the_website_job_runs_the_repository_checks_with_the_browser(self) -> None:
        # Validate is skipped for these changes, so the same checks have to run here.
        site = workflows()["site.yml"]
        self.assertIn('SITE_BROWSER: "1"', site)
        self.assertIn("fetch-depth: 0", site)
        self.assertIn("python scripts/validate_distribution.py", site)
        self.assertNotIn("SITE_BROWSER", workflows()["validate.yml"])

    def test_ci_runs_the_doctor_on_the_installed_runtime(self) -> None:
        text = workflows()["validate.yml"]
        job = text.split("  full-portable-tests:", 1)[1].split("\n  installer-end-to-end:", 1)[0]
        self.assertIn("cdx.py doctor", job)

    def test_python_setup_caches_pip_downloads(self) -> None:
        uncached = []
        for name, text in workflows().items():
            for block in re.split(r"(?m)^\s+- (?:name|uses|id):", text):
                if "actions/setup-python@" in block and "cache: pip" not in block:
                    uncached.append(name)
        self.assertEqual(uncached, [], "setup-python steps without cache: pip")


if __name__ == "__main__":
    unittest.main()
