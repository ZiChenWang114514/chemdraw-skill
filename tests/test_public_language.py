"""Public pages read without session history, and each translation follows its English page."""

from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PUBLIC_MARKDOWN = [
    ROOT / "README.md",
    ROOT / "README.zh-cn.md",
    *(ROOT / "docs").glob("*.md"),
    *(ROOT / "toolkit" / "docs").glob("*.md"),
    ROOT / "toolkit" / "README.md",
    *(ROOT / "site").rglob("*.html"),
    *(ROOT / "assets" / "readme").rglob("provenance.json"),
]
PAIRS = [
    ("README.md", "README.zh-cn.md"),
    ("docs/guide.md", "docs/guide.zh-cn.md"),
    ("site/en/index.html", "site/index.html"),
    ("site/en/lab/index.html", "site/lab/index.html"),
]
# Work-log wording and internal names that readers cannot place.
FORBIDDEN = [
    "controlled replay",
    "started with no prior context",
    "rxn-experiments",
    "\u4e09\u5904\u6807\u9898\u5b57\u53f7\u7684\u56de\u653e",
    "\u4ece\u96f6\u4e0a\u4e0b\u6587\u5f00\u59cb",
    "low-cost model",
    "low-cost language model",
    "\u4f4e\u6210\u672c\u6a21\u578b",
]
# Third parties whose code, data or service the toolkit uses; each needs a notice entry.
THIRD_PARTIES = ["ChemScanner", "RDKit", "OPSIN", "PubChem", "DECIMER", "MolScribe", "MolNexTR", "MolVec",
                 "AiZynthFinder", "SynPlanner", "ReactionT5", "MagNET"]
# Test-data identifiers stay out of the landing pages (README galleries may name the paper compound).
HOMEPAGE_FORBIDDEN = ["Sceptrin"]


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class PublicLanguageTests(unittest.TestCase):
    def test_public_pages_have_no_work_log_wording(self):
        found = [
            f"{page.relative_to(ROOT).as_posix()}: {phrase}"
            for page in PUBLIC_MARKDOWN
            for phrase in FORBIDDEN
            if phrase in _text(page)
        ]
        self.assertEqual(found, [])

    def test_landing_pages_name_no_test_data(self):
        found = [
            f"{name}: {word}"
            for name in ("site/index.html", "site/en/index.html")
            for word in HOMEPAGE_FORBIDDEN
            if word.lower() in _text(ROOT / name).lower()
        ]
        self.assertEqual(found, [])


class NoticeTests(unittest.TestCase):
    def test_notice_has_an_entry_for_every_third_party(self):
        headings = re.findall(r"(?m)^## (.+)$", _text(ROOT / "toolkit" / "NOTICE.md"))
        missing = [name for name in THIRD_PARTIES if not any(name in heading for heading in headings)]
        self.assertEqual(missing, [])


class TranslationParityTests(unittest.TestCase):
    def test_translations_keep_the_structure_of_the_english_page(self):
        for english, chinese in PAIRS:
            en, zh = _text(ROOT / english), _text(ROOT / chinese)
            for label, pattern in (
                ("h2", r"^## "),
                ("h3", r"^### "),
                ("code fences", r"^\s*```"),
                ("details blocks", r"<details"),
                ("images", r"<img |!\["),
            ):
                self.assertEqual(
                    len(re.findall(pattern, en, re.MULTILINE)),
                    len(re.findall(pattern, zh, re.MULTILINE)),
                    f"{label}: {english} vs {chinese}",
                )


if __name__ == "__main__":
    unittest.main()
