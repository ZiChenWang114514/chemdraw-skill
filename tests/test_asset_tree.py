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


class HouseStyleGalleryTests(unittest.TestCase):
    """The style gallery lists every house style and every literature replica, and its links resolve."""

    HOUSE = ROOT / "skill" / "chemdraw" / "assets" / "house-styles"
    CARDS = ROOT / "toolkit" / "cdxml_toolkit" / "publication" / "house_styles"

    def gallery(self) -> str:
        return (self.HOUSE / "gallery" / "README.md").read_text(encoding="utf-8")

    def test_every_house_style_has_a_render_and_a_folder(self):
        text = self.gallery()
        for card in sorted(self.CARDS.glob("*.json")):
            slug = card.stem
            self.assertIn(f"(house-{slug}.png)", text, slug)
            self.assertTrue((self.HOUSE / "gallery" / f"house-{slug}.png").is_file(), slug)
            self.assertTrue((self.HOUSE / slug / "README.md").is_file(), slug)

    def test_every_replica_case_is_complete_and_listed(self):
        text = self.gallery()
        for case in sorted(self.HOUSE.glob("*/replica/*")):
            with self.subTest(case=case.name):
                self.assertTrue((case / "CASE.md").is_file(), "a replica folder needs its CASE.md")
                self.assertTrue((case / "reference.png").is_file())
                self.assertIn(f"replica/{case.name}/CASE.md)", text)

    def test_gallery_links_resolve(self):
        base = self.HOUSE / "gallery"
        targets = re.findall(r'\]\(([^)#]+)\)|src="([^"]+)"', self.gallery())
        for link in {a or b for a, b in targets}:
            self.assertTrue((base / link).exists(), link)
