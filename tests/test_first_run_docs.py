"""The first-run documentation stays in step with the installer and works in every shell it names."""

from __future__ import annotations

import importlib.util
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
README_PAGES = ("README.md", "README.zh-cn.md")
GUIDE_PAGES = ("docs/guide.md", "docs/guide.zh-cn.md")
SITE_PAGES = ("site/en/index.html", "site/index.html")
# The one install command a new user copies; README and guide must show the same line.
CANONICAL_INSTALL = "python scripts/install.py --agent claude agents --runtime --apply"
PREREQUISITES = "<!-- prerequisites -->"


def _text(name: str) -> str:
    return (ROOT / name).read_text(encoding="utf-8")


def _installer_agents() -> dict:
    spec = importlib.util.spec_from_file_location("chemdraw_install_docs", ROOT / "scripts" / "install.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.AGENTS


def _fences(text: str) -> list[str]:
    return re.findall(r"(?ms)^```[a-z]*\n(.*?)^```", text)


class FirstRunDocsTests(unittest.TestCase):
    def test_site_install_picker_matches_the_installer_agents(self):
        agents = _installer_agents()
        expected = {name: folders[0] for name, folders in agents.items()}
        for page in SITE_PAGES:
            picker = dict(re.findall(r'name="agent" value="([^"]+)" data-dir="([^"]+)"', _text(page)))
            self.assertEqual(picker, expected, page)

    def test_readme_and_guide_name_every_installer_agent(self):
        for page in README_PAGES + GUIDE_PAGES:
            text = _text(page)
            missing = [name for name in _installer_agents() if f"`{name}`" not in text]
            self.assertEqual(missing, [], page)

    def test_readme_and_guide_share_one_install_command(self):
        for page in README_PAGES + GUIDE_PAGES:
            self.assertIn(CANONICAL_INSTALL, _text(page), page)

    def test_prerequisites_come_before_the_first_native_request(self):
        for page in README_PAGES:
            text = _text(page)
            self.assertIn(PREREQUISITES, text, page)
            first_step = "**1. Install" if page == "README.md" else "**1. \u5b89\u88c5"
            self.assertLess(text.index(PREREQUISITES), text.index(first_step), page)
        for page in SITE_PAGES:
            text = _text(page)
            self.assertIn('class="prereq"', text, page)
            self.assertLess(text.index('class="prereq"'), text.index('class="say"'), page)

    def test_prerequisites_name_what_a_new_user_must_bring(self):
        for page in README_PAGES + SITE_PAGES:
            text = _text(page)
            block = text[text.index(PREREQUISITES if page.endswith(".md") else 'class="prereq"'):]
            block = block[:2500]
            for needed in ("ChemDraw", "3.10", "MB", "--opsin", "Java", "Tesseract", "--extras"):
                self.assertIn(needed, block, f"{page}: {needed}")

    def test_documented_commands_avoid_shell_specific_forms(self):
        found = []
        for page in README_PAGES + GUIDE_PAGES:
            text = _text(page)
            commands = _fences(text) + re.findall(r"`(python [^`]+)`", text)
            for command in commands:
                if "~/" in command:
                    found.append(f"{page}: ~/ in {command.strip()[:60]}")
                if re.search(r"--json\s+'", command):
                    found.append(f"{page}: single-quoted JSON in {command.strip()[:60]}")
        self.assertEqual(found, [])

    def test_site_faq_names_every_picker_agent(self):
        for page in SITE_PAGES:
            text = _text(page)
            labels = re.findall(r'name="agent" value="[^"]+" data-dir="[^"]+"[^>]*><span>([^<]+)</span>', text)
            faq = text[text.index('id="faq"'):]
            missing = [label for label in labels if not re.search(rf"\b{re.escape(label)}\b", faq)]
            self.assertEqual(missing, [], page)


if __name__ == "__main__":
    unittest.main()
