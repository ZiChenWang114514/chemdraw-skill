from __future__ import annotations

import json
import re
import shutil
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
import unittest

try:
    from rdkit import Chem, RDLogger
    RDLogger.DisableLog("rdApp.*")
except ImportError:  # the portable suite runs without RDKit
    Chem = None


ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
PAGES = {"zh": SITE / "index.html", "en": SITE / "en" / "index.html"}
VALENCE = {"C": 4, "N": 3, "O": 2, "S": 2, "F": 1, "Cl": 1, "Br": 1}
NODE = shutil.which("node")


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


def run_editor(script: str):
    """Run a snippet against editor.js in Node (the file exports its pure functions) and return its JSON."""
    prelude = f"const E = require({json.dumps(str(SITE / 'editor.js'))});\n"
    done = subprocess.run([NODE, "-e", prelude + script], capture_output=True, text=True, timeout=60, check=True)
    return json.loads(done.stdout)


def canonical(smiles: str) -> str:
    return Chem.MolToSmiles(Chem.MolFromSmiles(smiles))


def i18n(html: str) -> dict:
    return json.loads(re.search(r'<script type="application/json" id="i18n">(.*?)</script>', html, re.S).group(1))


@unittest.skipUnless(NODE, "Node.js runs the editor's exporters")
class EditorExportTests(unittest.TestCase):
    def test_smiles_export_describes_every_molecule_in_the_table(self) -> None:
        out = run_editor("console.log(JSON.stringify(Object.fromEntries(Object.keys(E.MOLS).map((n) => [n, E.toSmiles(E.load(n))]))));")
        self.assertEqual(set(out), set(molecules()))
        if Chem is None:
            self.skipTest("RDKit compares the SMILES")
        for name, smiles in out.items():
            with self.subTest(molecule=name):
                self.assertIsNotNone(Chem.MolFromSmiles(smiles), smiles)
                self.assertEqual(canonical(smiles), canonical(molecules()[name]["smiles"]))

    def test_smiles_export_handles_fragments_rings_and_over_valent_atoms(self) -> None:
        out = run_editor("""
const ring = { atoms: [0, 1, 2, 3, 4, 5].map((k) => ({ s: "C", x: k, y: 0 })), bonds: [0, 1, 2, 3, 4, 5].map((k) => ({ a: k, b: (k + 1) % 6, o: k % 2 ? 1 : 2 })) };
const salt = { atoms: [{ s: "C", x: 0, y: 0 }, { s: "Cl", x: 50, y: 0 }, { s: "O", x: 100, y: 0 }], bonds: [{ a: 0, b: 1, o: 1 }] };
const bad = { atoms: [{ s: "O", x: 0, y: 0 }, { s: "C", x: 1, y: 0 }, { s: "C", x: 2, y: 0 }, { s: "C", x: 3, y: 0 }], bonds: [{ a: 0, b: 1, o: 1 }, { a: 0, b: 2, o: 1 }, { a: 0, b: 3, o: 1 }] };
console.log(JSON.stringify([E.toSmiles(ring), E.toSmiles(salt), E.toSmiles(bad), E.toSmiles({ atoms: [], bonds: [] })]));
""")
        ring, salt, bad, empty = out
        self.assertIsNone(bad)
        self.assertEqual(empty, "")
        self.assertEqual(salt.count("."), 1)
        if Chem is not None:
            self.assertEqual(canonical(ring), "c1ccccc1")
            self.assertEqual(canonical(salt), canonical("CCl.O"))

    def test_cdxml_export_is_an_acs_1996_document_of_the_drawing(self) -> None:
        out = run_editor("console.log(JSON.stringify(Object.fromEntries(Object.keys(E.MOLS).map((n) => [n, E.toCdxml(E.load(n))]))));")
        numbers = {"C": "6", "N": "7", "O": "8", "S": "16", "F": "9", "Cl": "17", "Br": "35"}
        for name, text in out.items():
            molecule = molecules()[name]
            with self.subTest(molecule=name):
                self.assertTrue(text.startswith('<?xml version="1.0" encoding="UTF-8" ?>'))
                self.assertIn("<!DOCTYPE CDXML", text)
                root = ET.fromstring(text[text.index("<CDXML"):])
                self.assertEqual(root.get("BondLength"), "14.40")
                self.assertEqual(root.get("LabelFont"), "3")
                nodes, bonds = root.findall(".//n"), root.findall(".//b")
                self.assertEqual(len(nodes), len(molecule["atoms"]))
                self.assertEqual(len(bonds), len(molecule["bonds"]))
                for node, (symbol, _x, _y) in zip(nodes, molecule["atoms"]):
                    if symbol == "C":
                        self.assertIsNone(node.get("Element"))
                    else:
                        self.assertEqual(node.get("Element"), numbers[symbol])
                        self.assertTrue(node.find("t/s").text.startswith(symbol))
                lengths = []
                points = {node.get("id"): tuple(map(float, node.get("p").split())) for node in nodes}
                for bond, (_a, _b, order) in zip(bonds, molecule["bonds"]):
                    self.assertEqual(bond.get("Order"), None if order == 1 else str(order))
                    (x1, y1), (x2, y2) = points[bond.get("B")], points[bond.get("E")]
                    lengths.append(((x1 - x2) ** 2 + (y1 - y2) ** 2) ** 0.5)
                self.assertAlmostEqual(sum(lengths) / len(lengths), 14.4, delta=0.05)
                if Chem is not None:
                    read = Chem.MolsFromCDXML(text)
                    self.assertEqual(len(read), 1)
                    self.assertEqual(Chem.MolToSmiles(read[0]), canonical(molecule["smiles"]))

    def test_clean_up_restores_bond_lengths_and_keeps_the_drawing_on_the_canvas(self) -> None:
        out = run_editor("""
const result = {};
for (const name of Object.keys(E.MOLS)) {
  const g = E.load(name);
  const L = E.bondLength(g);
  let seed = 7;
  const rand = () => { seed = (seed * 16807) % 2147483647; return seed / 2147483647 - 0.5; };
  g.atoms.forEach((a) => { a.x += rand() * 30; a.y += rand() * 30; });
  const clean = E.cleanUp(g, L);
  const lengths = g.bonds.map((b) => Math.hypot(clean[b.a].x - clean[b.b].x, clean[b.a].y - clean[b.b].y) / L);
  result[name] = { worst: Math.max(...lengths.map((r) => Math.abs(r - 1))), xs: clean.map((p) => p.x), ys: clean.map((p) => p.y) };
}
console.log(JSON.stringify(result));
""")
        for name, r in out.items():
            with self.subTest(molecule=name):
                self.assertLess(r["worst"], 0.08)
                self.assertTrue(all(0 <= x <= 323 for x in r["xs"]) and all(0 <= y <= 262 for y in r["ys"]))


# What each challenge should end with, as published SMILES of the named compound.
CHALLENGE_ANSWERS = {
    "salicylic": "OC(=O)c1ccccc1O",
    "aminophenol": "Nc1ccc(O)cc1",
    "vanillic": "COc1cc(C(=O)O)ccc1O",
    "theophylline": "CN1C2=C(C(=O)N(C1=O)C)NC=N2",
    "ibuprofenMethyl": "CC(C)Cc1ccc(C(C)C(=O)OC)cc1",
    "wintergreen": "COC(=O)c1ccccc1O",
}


@unittest.skipUnless(NODE, "Node.js runs the editor's challenge checks")
class ChallengeTests(unittest.TestCase):
    def test_every_challenge_is_solved_by_its_moves_and_only_by_them(self) -> None:
        out = run_editor("""
const r = {};
for (const c of E.CHALLENGES) {
  const start = E.load(c.mol), solved = E.applyMoves(E.load(c.mol), c.solve);
  r[c.id] = { smiles: E.toSmiles(solved), solved: E.graphKey(solved) === E.challengeKey(c), start: E.graphKey(start) === E.challengeKey(c) };
}
console.log(JSON.stringify(r));
""")
        self.assertEqual(set(out), set(CHALLENGE_ANSWERS))
        for cid, r in out.items():
            with self.subTest(challenge=cid):
                self.assertTrue(r["solved"])
                self.assertFalse(r["start"])
                if Chem is not None:
                    self.assertEqual(canonical(r["smiles"]), canonical(CHALLENGE_ANSWERS[cid]))

    def test_graph_key_ignores_layout_and_kekule_form_but_not_isomers(self) -> None:
        out = run_editor("""
const a = E.load("aspirin");
const moved = E.load("aspirin"); moved.atoms.forEach((p) => { p.x = p.x * 0.7 + 30; p.y = 200 - p.y; });
// The same benzene ring with its double bonds in the other Kekule positions.
const flipped = E.load("aspirin"); [4, 5, 6, 7, 8, 12].forEach((k) => { flipped.bonds[k].o = flipped.bonds[k].o === 2 ? 1 : 2; });
const iso = E.applyMoves(E.load("aspirin"), [["erase", 0], ["erase", 0], ["erase", 0]]);
const iso2 = E.applyMoves(E.load("aspirin"), [["erase", 0], ["erase", 0], ["erase", 0], ["grow", 9]]);
const iso3 = E.applyMoves(E.load("aspirin"), [["erase", 0], ["erase", 0], ["erase", 0], ["grow", 0]]);
console.log(JSON.stringify([E.graphKey(a) === E.graphKey(moved), E.graphKey(a) === E.graphKey(flipped), E.graphKey(iso2) === E.graphKey(iso3), E.graphKey(iso) === E.graphKey(a)]));
""")
        self.assertEqual(out, [True, True, False, False])

    def test_both_pages_describe_every_challenge(self) -> None:
        ids = set(CHALLENGE_ANSWERS)
        for language, path in PAGES.items():
            with self.subTest(page=language):
                table = i18n(path.read_text(encoding="utf-8"))["challenge"]
                self.assertEqual(set(table["tasks"]), ids)
                for cid in ids:
                    self.assertTrue(table["tasks"][cid]["task"] and table["tasks"][cid]["hint"])
                for key in ("title", "hint", "skip", "next", "close", "done", "all", "count", "matches", "aim"):
                    self.assertIn(key, table)


class InteractionMarkupTests(unittest.TestCase):
    def pages(self) -> dict:
        return {language: path.read_text(encoding="utf-8") for language, path in PAGES.items()}

    def test_every_capability_has_an_example_request_and_a_filter_group(self) -> None:
        kinds = {}
        for language, html in self.pages().items():
            with self.subTest(page=language):
                caps = re.search(r'<dl class="caps">(.*?)</dl>', html, re.S).group(1)
                items = re.findall(r'<div data-kind="(\w+)">(.*?)</div>\n', caps, re.S)
                self.assertEqual(len(items), 15)
                for _kind, body in items:
                    self.assertIn('<details class="try">', body)
                    ask = re.search(r'<p class="ask">(.*?)</p>', body).group(1)
                    self.assertGreater(len(re.sub(r"<[^>]+>", "", ask)), 12)
                # Example requests come before the quick start, so the prerequisites are named ahead of them.
                note = html.index('class="try-note"')
                self.assertLess(note, html.index('<details class="try">'))
                self.assertIn('href="#start"', html[note:note + 300])
                self.assertIn("ChemDraw", html[note:note + 300])
                chips = re.findall(r'data-filter="(\w+)"', html)
                self.assertEqual(chips[0], "all")
                self.assertEqual(set(chips[1:]), {kind for kind, _ in items})
                kinds[language] = [kind for kind, _ in items]
        self.assertEqual(kinds["zh"], kinds["en"])

    def test_both_pages_carry_the_same_interface_words(self) -> None:
        tables = {language: i18n(html) for language, html in self.pages().items()}
        for language, table in tables.items():
            with self.subTest(page=language):
                for key in ("cleaned", "smiles", "copied", "download", "noSmiles", "keys", "copyAsk", "copiedAsk", "run", "running", "rerun"):
                    self.assertIn(key, table)
                for key in ("open", "close", "prev", "next", "zoomIn", "zoomOut", "fit", "count", "hint"):
                    self.assertIn(key, table["lightbox"])
        self.assertEqual(tables["zh"]["lightbox"].keys(), tables["en"]["lightbox"].keys())

    def test_editor_exposes_clean_up_and_export_controls(self) -> None:
        for language, html in self.pages().items():
            with self.subTest(page=language):
                for marker in ('data-tool-action="clean"', 'data-export="smiles"', 'data-export="cdxml"', 'class="progress"',
                               'class="challenge"', 'data-challenge-open', 'data-run'):
                    self.assertIn(marker, html)
                self.assertEqual(html.count("data-zoom"), 7)


if __name__ == "__main__":
    unittest.main()
