"""README example assets live in one tree, and every toolkit document is reachable."""

from __future__ import annotations

import hashlib
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets" / "readme"
TOOLKIT_ASSETS = ROOT / "toolkit" / "assets" / "readme"
TOOLKIT_DOCS = ROOT / "toolkit" / "docs"
# Pages that list toolkit documents for developers.
DOC_INDEXES = [ROOT / "toolkit" / "README.md", *TOOLKIT_DOCS.glob("*.md")]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class AssetTreeTests(unittest.TestCase):
    def test_toolkit_assets_do_not_copy_the_readme_assets(self):
        shared = {_sha256(path) for path in ASSETS.rglob("*") if path.is_file()}
        copies = sorted(
            path.relative_to(ROOT).as_posix()
            for path in TOOLKIT_ASSETS.rglob("*")
            if path.is_file() and _sha256(path) in shared
        )
        self.assertEqual(copies, [])

    def test_every_toolkit_document_has_an_inbound_link(self):
        linked = set()
        for page in DOC_INDEXES:
            for target in re.findall(r"\]\(([^)#\s]+)", page.read_text(encoding="utf-8")):
                linked.add((page.parent / target).resolve())
        orphans = sorted(doc.name for doc in TOOLKIT_DOCS.glob("*.md") if doc.resolve() not in linked)
        self.assertEqual(orphans, [])


if __name__ == "__main__":
    unittest.main()
