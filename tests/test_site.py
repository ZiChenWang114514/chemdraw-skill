from __future__ import annotations

import json
import re
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
PAGES = {"zh": SITE / "index.html", "en": SITE / "en" / "index.html"}
VALENCE = {"C": 4, "N": 3, "O": 2, "S": 2, "F": 1, "Cl": 1, "Br": 1}


def molecules() -> dict:
    source = (SITE / "editor.js").read_text(encoding="utf-8")
    table = re.search(r"const MOLS = (\{.*?\n  \});", source, re.S).group(1)
    # The table is written as JSON with a trailing comma after the last entry.
    return json.loads(re.sub(r",(\s*\})\s*$", r"\1", table))


def hill_formula(molecule: dict) -> str:
    used = [0] * len(molecule["atoms"])
    for a, b, order in molecule["bonds"]:
        used[a] += order
        used[b] += order
    counts: dict[str, int] = {}
    for (symbol, _x, _y), bonds in zip(molecule["atoms"], used):
        counts[symbol] = counts.get(symbol, 0) + 1
        counts["H"] = counts.get("H", 0) + max(0, VALENCE[symbol] - bonds)
    rest = sorted(s for s in counts if s not in ("C", "H") and counts[s])
    order = ["C", "H", *rest] if counts.get("C") else sorted(s for s in counts if counts[s])
    return "".join(s + (str(counts[s]) if counts[s] > 1 else "") for s in order if counts[s])


class HeroEditorTests(unittest.TestCase):
    def test_molecule_table_matches_its_declared_formulas(self) -> None:
        table = molecules()
        self.assertGreaterEqual(len(table), 3)
        for name, molecule in table.items():
            with self.subTest(molecule=name):
                self.assertEqual(hill_formula(molecule), molecule["formula"])

    def test_molecule_geometry_fits_the_canvas_and_references_real_atoms(self) -> None:
        for name, molecule in molecules().items():
            with self.subTest(molecule=name):
                for symbol, x, y in molecule["atoms"]:
                    self.assertIn(symbol, VALENCE)
                    self.assertTrue(0 <= x <= 323 and 0 <= y <= 262, (symbol, x, y))
                for a, b, order in molecule["bonds"]:
                    self.assertTrue(0 <= a < len(molecule["atoms"]) and 0 <= b < len(molecule["atoms"]))
                    self.assertIn(order, (1, 2, 3))

    def test_both_pages_load_the_editor_with_matching_text_tables(self) -> None:
        table = molecules()
        keys = {}
        for language, path in PAGES.items():
            with self.subTest(page=language):
                html = path.read_text(encoding="utf-8")
                self.assertRegex(html, r'<script src="(\.\./)?editor\.js" defer></script>')
                i18n = json.loads(re.search(r'<script type="application/json" id="i18n">(.*?)</script>', html, re.S).group(1))
                keys[language] = i18n
                self.assertEqual(set(i18n["names"]), set(table))
                tabs = re.findall(r'data-mol="(\w+)"', html)
                self.assertEqual(tabs, list(table))
                for marker in ("ask", "resolve", "build", "readback"):
                    self.assertIn(f'data-log="{marker}"', html)
                for tool in ("move", "bond", "atom", "ring", "erase"):
                    self.assertIn(f'data-tool="{tool}"', html)
                    self.assertIn(tool, i18n["hint"])
                self.assertIn('id="doc-canvas"', html)
        self.assertEqual(keys["zh"].keys(), keys["en"].keys())
        self.assertEqual(keys["zh"]["hint"].keys(), keys["en"]["hint"].keys())

    def test_page_text_does_not_hide_the_real_commands(self) -> None:
        # The "How it works" command panels show output that was produced by the bundled runtime.
        for language, path in PAGES.items():
            with self.subTest(page=language):
                html = path.read_text(encoding="utf-8")
                self.assertEqual(html.count('<details class="cmd">'), 4)
                self.assertIn("cdx.py call resolve_name", html)
                self.assertIn("cdx.py chemscript-info aspirin.cdxml", html)


if __name__ == "__main__":
    unittest.main()
