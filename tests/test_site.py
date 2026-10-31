from __future__ import annotations

import functools
import gzip
import json
import os
import re
import shutil
import subprocess
import tempfile
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
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
LAB_PAGES = {"zh": SITE / "lab" / "index.html", "en": SITE / "en" / "lab" / "index.html"}
WORDS = {"zh": SITE / "words.zh.js", "en": SITE / "words.en.js"}
VALENCE = {"C": 4, "N": 3, "O": 2, "S": 2, "F": 1, "Cl": 1, "Br": 1}
NODE = shutil.which("node")


def molecules() -> dict:
    source = (SITE / "chem.js").read_text(encoding="utf-8")
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
                table_words = words(language)
                keys[language] = table_words
                self.assertRegex(html, rf'<script src="(\.\./)?words\.{language}\.js" defer></script>')
                self.assertRegex(html, r'<script src="(\.\./)?chem\.js" defer></script>')
                self.assertEqual(set(table_words["names"]), set(table))
                tabs = re.findall(r'data-mol="(\w+)"', html)
                self.assertEqual(tabs, list(table))
                for marker in ("ask", "resolve", "build", "readback"):
                    self.assertIn(f'data-log="{marker}"', html)
                for tool in ("move", "bond", "atom", "ring", "erase"):
                    self.assertIn(f'data-tool="{tool}"', html)
                    self.assertIn(tool, table_words["hint"])
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
    prelude = f"const E = require({json.dumps(str(SITE / 'chem.js'))});\n"
    done = subprocess.run([NODE, "-e", prelude + script], capture_output=True, text=True, timeout=60, check=True)
    return json.loads(done.stdout)


def canonical(smiles: str) -> str:
    return Chem.MolToSmiles(Chem.MolFromSmiles(smiles))


def words(language: str) -> dict:
    """The interface words of one language: words.<language>.js is one JSON object behind an assignment."""
    source = WORDS[language].read_text(encoding="utf-8")
    return json.loads(source[source.index("{"):source.rindex("}") + 1])


def key_shape(value):
    """The nested keys of a table, so the two languages can be compared without comparing their text."""
    if isinstance(value, dict):
        return {k: key_shape(v) for k, v in value.items()}
    return len(value) if isinstance(value, list) else None


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


# What each challenge should end with: PubChem's SMILES for the named compound, cross-checked with
# `cdx.py call resolve_name`. Never edit one by hand; look the compound up again.
CHALLENGE_ANSWERS = {
    "salicylic": "O=C(O)c1ccccc1O",
    "aminophenol": "Nc1ccc(O)cc1",
    "acetanilide": "CC(=O)Nc1ccccc1",
    "phenylAcetate": "CC(=O)Oc1ccccc1",
    "theophylline": "Cn1c(=O)c2[nH]cnc2n(C)c1=O",
    "theobromine": "Cn1cnc2c1c(=O)[nH]c(=O)n2C",
    "paraxanthine": "Cn1c(=O)[nH]c2ncn(C)c2c1=O",
    "xanthine": "O=c1[nH]c(=O)c2[nH]cnc2[nH]1",
    "ibufenac": "CC(C)Cc1ccc(CC(=O)O)cc1",
    "protocatechuic": "O=Cc1ccc(O)c(O)c1",
    "fluoroacetanilide": "CC(=O)Nc1ccc(F)cc1",
    "vanillylAlcohol": "COc1cc(CO)ccc1O",
    "ibuprofenAmide": "CC(C)Cc1ccc(C(C)C(N)=O)cc1",
    "isovanillin": "COc1ccc(C=O)cc1O",
    "wintergreen": "COC(=O)c1ccccc1O",
    "ibuprofenMethyl": "COC(=O)C(C)c1ccc(CC(C)C)cc1",
    "vanillic": "COc1cc(C(=O)O)ccc1O",
    "ethylVanillin": "CCOc1cc(C=O)ccc1O",
    "veratraldehyde": "COc1ccc(C=O)cc1OC",
    "phenacetin": "CCOc1ccc(NC(C)=O)cc1",
}

# The constitutional isomers of each hunt set. A breadth-first build checks these counts independently.
ISOMER_COUNTS = {"C2H6O": 2, "C3H8O": 3, "C5H12": 3, "C6H14": 5, "C4H10O": 7, "C4H8": 5}


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

    def test_every_solved_level_exports_cdxml_that_reads_back_as_its_compound(self) -> None:
        if Chem is None:
            self.skipTest("RDKit reads the exported CDXML")
        out = run_editor("""
const r = {};
for (const c of E.CHALLENGES) r[c.id] = E.toCdxml(E.targetOf(c));
console.log(JSON.stringify(r));
""")
        for cid, text in out.items():
            with self.subTest(challenge=cid):
                read = Chem.MolsFromCDXML(text)
                self.assertEqual(len(read), 1)
                self.assertEqual(Chem.MolToSmiles(read[0]), canonical(CHALLENGE_ANSWERS[cid]))

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
                table = words(language)["challenge"]
                self.assertEqual(set(table["tasks"]), ids)
                for cid in ids:
                    entry = table["tasks"][cid]
                    self.assertTrue(entry["name"] and entry["task"] and entry["hint"] and entry["fact"])
                for key in ("title", "hint", "skip", "next", "close", "done", "matches", "aim"):
                    self.assertIn(key, table)


@unittest.skipUnless(NODE, "Node.js runs the game logic")
class GameLogicTests(unittest.TestCase):
    def test_an_over_valent_drawing_never_matches_a_target(self) -> None:
        out = run_editor("""
const good = E.load("aspirin"), bad = E.load("aspirin");
bad.bonds[12].o = 2;  // the ring bond between the two substituted carbons: both now have five bonds
console.log(JSON.stringify([E.graphKey(good) === E.graphKey(bad), E.analyse(bad).over.some(Boolean)]));
""")
        self.assertEqual(out, [False, True])

    def test_graph_key_sees_a_difference_at_the_far_end_of_a_long_chain(self) -> None:
        out = run_editor("""
const chain = (n, end) => ({ atoms: Array.from({ length: n }, (_, k) => ({ s: k === n - 1 ? end : "C", x: k * 10, y: 0 })), bonds: Array.from({ length: n - 1 }, (_, k) => ({ a: k, b: k + 1, o: 1 })) });
// Fourteen-atom chains with the oxygen one place apart: only a walk the length of the chain separates them.
const a = chain(14, "O"), b = chain(14, "C"); b.atoms[12].s = "O";
const c = chain(14, "C"); c.atoms[11].s = "O";
console.log(JSON.stringify([E.graphKey(a) === E.graphKey(b), E.graphKey(b) === E.graphKey(c)]));
""")
        self.assertEqual(out, [False, False])

    def test_stars_reward_the_shortest_route_without_a_hint(self) -> None:
        out = run_editor("console.log(JSON.stringify([E.stars(3, 3, false), E.stars(2, 3, false), E.stars(4, 3, false), E.stars(3, 3, true), E.stars(9, 3, true)]));")
        self.assertEqual(out, [3, 3, 2, 1, 1])

    def test_daily_compound_changes_every_day_and_visits_all_of_them(self) -> None:
        out = run_editor("""
const days = Array.from({ length: E.CHALLENGES.length }, (_, k) => new Date(Date.UTC(2026, 10, 1 + k)).toISOString().slice(0, 10));
const ids = days.map((d) => E.dailyPick(d).id);
console.log(JSON.stringify({ ids, n: E.CHALLENGES.length, first: E.dailyNumber("2026-10-31"), later: E.dailyNumber("2027-01-01"), before: E.dailyPick("2020-01-01").id.length > 0 }));
""")
        self.assertEqual(len(set(out["ids"])), out["n"])
        self.assertTrue(all(a != b for a, b in zip(out["ids"], out["ids"][1:])))
        self.assertEqual(out["first"], 1)
        self.assertEqual(out["later"], 63)
        self.assertTrue(out["before"])

    def test_streak_counts_consecutive_local_days_across_month_and_year_ends(self) -> None:
        out = run_editor("""
const step = (d, day) => E.nextStreak(d, day);
const a = step({ last: "", streak: 0, best: 0 }, "2026-12-31");
const b = step(a, "2027-01-01");
const same = step(b, "2027-01-01");
const gap = step(b, "2027-01-03");
const leap = step({ last: "2028-02-28", streak: 4, best: 4 }, "2028-02-29");
console.log(JSON.stringify([a.streak, b.streak, same.streak, gap.streak, gap.best, leap.streak]));
""")
        self.assertEqual(out, [1, 2, 2, 1, 2, 5])

    def test_local_date_uses_the_visitors_calendar_day(self) -> None:
        self.assertEqual(run_editor('console.log(JSON.stringify(E.localDate(new Date(2027, 0, 5, 23, 59))));'), "2027-01-05")

    def test_shared_drawings_round_trip_and_hostile_links_are_refused(self) -> None:
        out = run_editor("""
const g = E.load("caffeine"), code = E.encodeDrawing(g), back = E.decodeDrawing(code);
const wrap = (x) => Buffer.from(JSON.stringify(x)).toString("base64url");
const ok = [[["C", 10, 10], ["O", 40, 40]], [[0, 1, 1]]];
const hostile = [
  "", "%%%", "null", wrap(null), wrap({}), wrap([[], []]), wrap([[["<img src=x onerror=alert(1)>", 10, 10]], []]),
  wrap([[["__proto__", 10, 10]], []]), wrap([[["constructor", 10, 10]], []]), wrap([[["C", "1", 10]], []]),
  wrap([[["C", 1e9, 10]], []]), wrap([[["C", NaN, 10]], []]), wrap([[["C", 10, 10]], [[0, 0, 1]]]),
  wrap([[["C", 10, 10]], [[0, 5, 1]]]), wrap([[["C", 10, 10], ["C", 40, 10]], [[0, 1, 4]]]),
  wrap([[["C", 10, 10], ["C", 40, 10]], [[0, 1, 1], [1, 0, 2]]]), wrap([[["C", 10, 10], ["C", 40, 10]], [[0.5, 1, 1]]]),
  wrap([Array.from({ length: 200 }, () => ["C", 10, 10]), []]), "A".repeat(100000),
];
console.log(JSON.stringify({ same: E.graphKey(back) === E.graphKey(g), ok: E.decodeDrawing(wrap(ok)) !== null, refused: hostile.map((h) => E.decodeDrawing(h)) }));
""")
        self.assertTrue(out["same"])
        self.assertTrue(out["ok"])
        self.assertEqual(out["refused"], [None] * len(out["refused"]))

    def test_saved_progress_survives_damage_and_ignores_what_it_does_not_know(self) -> None:
        out = run_editor("""
const empty = E.emptyStore();
const damaged = ["", "not json", "null", "[]", "{\\"v\\":99,\\"levels\\":{\\"salicylic\\":{\\"stars\\":3}}}"].map((t) => JSON.stringify(E.parseStore(t)) === JSON.stringify(empty));
const odd = E.parseStore(JSON.stringify({ v: 1, levels: { salicylic: { stars: 3, moves: 3 }, nothing: { stars: 3 }, xanthine: { stars: 9 } }, daily: { last: 5, streak: "x", best: -1 }, badges: ["first", "<b>"], hunt: { best: 900 }, isomers: { C5H12: ["%%%"], other: [] } }));
const s = E.emptyStore();
const r1 = E.record(s, "salicylic", { moves: 5, hinted: false });
const r2 = E.record(s, "salicylic", { moves: 3, hinted: false });
const r3 = E.record(s, "salicylic", { moves: 3, hinted: true });
console.log(JSON.stringify({ damaged, odd, r: [r1, r2, r3], kept: s.levels.salicylic }));
""")
        self.assertEqual(out["damaged"], [True] * 5)
        self.assertEqual(out["odd"]["levels"], {"salicylic": {"stars": 3, "moves": 3}})
        self.assertEqual(out["odd"]["badges"], ["first"])
        self.assertEqual(out["odd"]["daily"], {"last": "", "streak": 0, "best": 0, "solved": {}})
        self.assertEqual(out["odd"]["hunt"]["best"], 0)
        self.assertEqual(out["odd"]["isomers"], {})
        self.assertEqual(out["r"], [2, 3, 1])
        self.assertEqual(out["kept"], {"stars": 3, "moves": 3})

    def test_badges_follow_from_saved_progress(self) -> None:
        out = run_editor("""
const s = E.emptyStore();
const seen = [E.earned(s)];
E.record(s, "theophylline", { moves: 1, hinted: false });
seen.push(E.earned(s));
for (const id of ["theobromine", "paraxanthine", "xanthine"]) E.record(s, id, { moves: 9, hinted: true });
seen.push(E.earned(s));
for (const c of E.CHALLENGES) E.record(s, c.id, { moves: 9, hinted: true });
s.daily.best = 7; s.hunt.best = 8; s.exported = true; s.isomers.C2H6O = [E.encodeDrawing({ atoms: [{ s: "C", x: 10, y: 10 }], bonds: [] }), "b"];
seen.push(E.earned(s));
console.log(JSON.stringify({ seen, ids: E.BADGES }));
""")
        self.assertEqual(out["seen"][0], [])
        self.assertEqual(set(out["seen"][1]), {"first", "perfect"})
        self.assertIn("xanthines", out["seen"][2])
        self.assertEqual(set(out["seen"][3]), set(out["ids"]))
        self.assertLessEqual(len(out["ids"]), 8)
        for language in PAGES:
            self.assertEqual(set(words(language)["lab"]["badges"]), set(out["ids"]))

    def test_every_hunt_round_has_one_findable_error(self) -> None:
        out = run_editor("""
const rounds = [], kinds = {};
for (let seed = 0; seed < 300; seed++) {
  for (const r of E.makeHunt(seed)) {
    kinds[r.kind] = (kinds[r.kind] || 0) + 1;
    rounds.push({ id: r.id, kind: r.kind, differs: E.graphKey(r.truth) !== E.graphKey(r.shown),
      hit: r.hot.atoms.length + r.hot.bonds.length,
      atomsOk: r.hot.atoms.every((i) => i >= 0 && i < r.shown.atoms.length && Number.isInteger(i)),
      bondsOk: r.hot.bonds.every((k) => k >= 0 && k < r.shown.bonds.length && Number.isInteger(k)),
      inCanvas: r.shown.atoms.every((a) => a.x >= 0 && a.x <= 323 && a.y >= 0 && a.y <= 262) });
  }
}
const size = new Set([0, 1, 2, 3].map((s) => E.makeHunt(s).length));
const repeat = JSON.stringify(E.makeHunt(42)) === JSON.stringify(E.makeHunt(42));
const distinct = new Set(E.makeHunt(7).map((r) => r.id)).size;
console.log(JSON.stringify({ rounds, kinds, size: [...size], repeat, distinct }));
""")
        self.assertEqual(out["size"], [8])
        self.assertTrue(out["repeat"])
        self.assertEqual(out["distinct"], 8)
        self.assertEqual(set(out["kinds"]), {"element", "ringN", "order", "extra", "missing", "valence"})
        for language in PAGES:
            self.assertEqual(set(words(language)["lab"]["huntKinds"]), set(out["kinds"]))
        for round_ in out["rounds"]:
            self.assertTrue(round_["differs"], round_)
            self.assertGreater(round_["hit"], 0, round_)
            self.assertTrue(round_["atomsOk"] and round_["bondsOk"] and round_["inCanvas"], round_)

    def test_isomer_hunt_accepts_only_a_whole_valid_molecule_of_the_formula(self) -> None:
        out = run_editor("""
const line = (symbols) => ({ atoms: symbols.map((s, k) => ({ s, x: 40 + k * 40, y: 100 })), bonds: symbols.slice(1).map((_, k) => ({ a: k, b: k + 1, o: 1 })) });
const ethanol = line(["C", "C", "O"]), ether = line(["C", "O", "C"]);
const apart = line(["C", "C", "O"]); apart.bonds.pop();
const wrong = line(["C", "C", "C"]);
const over = line(["C", "C", "O"]); over.bonds.push({ a: 0, b: 2, o: 1 }, { a: 1, b: 2, o: 2 });
console.log(JSON.stringify({ sets: E.ISOMERS.map((s) => [s.formula, s.count]), a: E.isomerKey(ethanol, "C2H6O") === E.graphKey(ethanol), b: E.isomerKey(ether, "C2H6O") !== E.isomerKey(ethanol, "C2H6O"), apart: E.isomerKey(apart, "C2H6O"), wrong: E.isomerKey(wrong, "C2H6O"), over: E.isomerKey(over, "C2H6O") }));
""")
        self.assertEqual(dict(out["sets"]), ISOMER_COUNTS)
        self.assertTrue(out["a"] and out["b"])
        self.assertIsNone(out["apart"])
        self.assertIsNone(out["wrong"])
        self.assertIsNone(out["over"])

    @unittest.skipIf(Chem is None, "RDKit enumerates the isomers")
    def test_isomer_counts_are_complete_and_the_graph_key_separates_them(self) -> None:
        for formula, count in ISOMER_COUNTS.items():
            with self.subTest(formula=formula):
                found = enumerate_isomers(formula)
                self.assertEqual(len(found), count, sorted(found))
                graphs = [mol_graph(Chem.MolFromSmiles(smiles)) for smiles in sorted(found)]
                out = run_editor(f"console.log(JSON.stringify({json.dumps(graphs)}.map((g) => E.isomerKey(g, {json.dumps(formula)}))));")
                self.assertNotIn(None, out)
                self.assertEqual(len(set(out)), count)


def mol_graph(mol) -> dict:
    atoms = [{"s": a.GetSymbol(), "x": 20 + 30 * a.GetIdx(), "y": 40} for a in mol.GetAtoms()]
    Chem.Kekulize(mol, clearAromaticFlags=True)
    bonds = [{"a": b.GetBeginAtomIdx(), "b": b.GetEndAtomIdx(), "o": int(b.GetBondTypeAsDouble())} for b in mol.GetBonds()]
    return {"atoms": atoms, "bonds": bonds}


def enumerate_isomers(formula: str) -> set:
    """Every connected structure of a C/O formula, built one bond at a time and deduplicated by RDKit."""
    from rdkit.Chem.rdMolDescriptors import CalcMolFormula

    carbons = int(re.search(r"C(\d*)", formula).group(1) or 1)
    oxygens = int((re.search(r"O(\d*)", formula) or [0, 0])[1] or 1) if "O" in formula else 0
    symbols = ["C"] * carbons + ["O"] * oxygens
    limit = {"C": 4, "O": 2}
    order = {1: Chem.BondType.SINGLE, 2: Chem.BondType.DOUBLE, 3: Chem.BondType.TRIPLE}
    seen, frontier, found = set(), {tuple()}, set()
    pairs = [(i, j) for i in range(len(symbols)) for j in range(i + 1, len(symbols))]
    while frontier:
        following = set()
        for bonds in frontier:
            table = dict(((i, j), o) for i, j, o in bonds)
            used = [sum(o for (i, j), o in table.items() if k in (i, j)) for k in range(len(symbols))]
            mol = Chem.RWMol()
            for symbol in symbols:
                mol.AddAtom(Chem.Atom(symbol))
            for (i, j), o in table.items():
                mol.AddBond(i, j, order[o])
            Chem.SanitizeMol(mol)
            smiles = Chem.MolToSmiles(mol)
            if smiles in seen:
                continue
            seen.add(smiles)
            if "." not in smiles and CalcMolFormula(mol) == formula:
                found.add(smiles)
            for i, j in pairs:
                o = table.get((i, j), 0)
                if o >= 3 or used[i] >= limit[symbols[i]] or used[j] >= limit[symbols[j]]:
                    continue
                grown = dict(table)
                grown[(i, j)] = o + 1
                following.add(tuple(sorted((a, b, c) for (a, b), c in grown.items())))
        frontier = following
    return found


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
        tables = {language: words(language) for language in PAGES}
        for language, table in tables.items():
            with self.subTest(page=language):
                for key in ("cleaned", "smiles", "copied", "download", "noSmiles", "keys", "copyAsk", "copiedAsk", "run", "running", "rerun"):
                    self.assertIn(key, table)
                for key in ("open", "close", "prev", "next", "zoomIn", "zoomOut", "fit", "count", "hint"):
                    self.assertIn(key, table["lightbox"])
        self.assertEqual(key_shape(tables["zh"]), key_shape(tables["en"]))

    def test_editor_exposes_clean_up_and_export_controls(self) -> None:
        for language, html in self.pages().items():
            with self.subTest(page=language):
                for marker in ('data-tool-action="clean"', 'data-export="smiles"', 'data-export="cdxml"', 'class="progress"',
                               'class="challenge"', 'data-challenge-open', 'data-run'):
                    self.assertIn(marker, html)
                self.assertEqual(html.count("data-zoom"), 7)


class LabPageTests(unittest.TestCase):
    def test_lab_pages_are_a_linked_language_pair(self) -> None:
        for language, path in LAB_PAGES.items():
            with self.subTest(page=language):
                html = path.read_text(encoding="utf-8")
                base = "https://zichenwang114514.github.io/chemdraw-skill/"
                self.assertIn(f'<link rel="canonical" href="{base}{"en/" if language == "en" else ""}lab/">', html)
                self.assertIn(f'hreflang="zh-CN" href="{base}lab/"', html)
                self.assertIn(f'hreflang="en" href="{base}en/lab/"', html)
                self.assertRegex(html, r'<title>[^<]{10,60}</title>')
                self.assertIn('property="og:image"', html)
                for script in (f"words.{language}.js", "chem.js", "editor.js", "lab.js"):
                    self.assertRegex(html, rf'<script src="(\.\./)+{re.escape(script)}" defer></script>')
                self.assertIn('class="prereq-note"', html)
                self.assertIn("<noscript>", html)
                # The progress line tells visitors nothing leaves their browser.
                self.assertIn("data-privacy", html)

    def test_home_pages_lead_to_the_lab_and_search_engines_know_it(self) -> None:
        sitemap = (SITE / "sitemap.xml").read_text(encoding="utf-8")
        self.assertIn("<loc>https://zichenwang114514.github.io/chemdraw-skill/lab/</loc>", sitemap)
        self.assertIn("<loc>https://zichenwang114514.github.io/chemdraw-skill/en/lab/</loc>", sitemap)
        workflow = (ROOT / ".github" / "workflows" / "pages.yml").read_text(encoding="utf-8")
        self.assertIn("${base}lab/", workflow)
        self.assertIn("${base}en/lab/", workflow)
        for language, path in PAGES.items():
            with self.subTest(page=language):
                html = path.read_text(encoding="utf-8")
                self.assertIn('id="lab"', html)
                self.assertIn('href="lab/"', html)
                self.assertIn("data-daily", html)

    def test_pages_load_nothing_from_other_sites(self) -> None:
        for path in [*PAGES.values(), *LAB_PAGES.values()]:
            with self.subTest(page=str(path)):
                html = path.read_text(encoding="utf-8")
                self.assertEqual(re.findall(r'<(?:script|img|iframe)\b[^>]*\bsrc="https?:', html), [])
                self.assertEqual(re.findall(r'<link\b[^>]*rel="stylesheet"[^>]*href="https?:', html), [])
        for name in ("app.js", "chem.js", "editor.js", "lab.js"):
            source = (SITE / name).read_text(encoding="utf-8")
            self.assertNotRegex(source, r"\b(fetch|XMLHttpRequest|sendBeacon|WebSocket|importScripts)\b", name)

    def test_script_weight_stays_within_budget(self) -> None:
        # GitHub Pages serves these compressed, so that is the weight a visitor pays for.
        size = lambda *names: sum(len(gzip.compress((SITE / n).read_bytes(), 9)) for n in names)
        for word_file in ("words.zh.js", "words.en.js"):
            self.assertLessEqual(size("app.js", "chem.js", "editor.js", word_file), 34_000)
        self.assertLessEqual(size("lab.js"), 8_000)


@unittest.skipUnless(os.environ.get("SITE_BROWSER"), "set SITE_BROWSER=1 to drive headless Chrome")
class BrowserSmokeTests(unittest.TestCase):
    def test_the_site_works_with_real_input_in_a_browser(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder) / "chemdraw-skill"
            shutil.copytree(SITE, root)
            shutil.copytree(ROOT / "assets" / "readme" / "gallery", root / "gallery")
            handler = functools.partial(SimpleHTTPRequestHandler, directory=folder)
            server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
            threading.Thread(target=server.serve_forever, daemon=True).start()
            try:
                url = f"http://127.0.0.1:{server.server_address[1]}/chemdraw-skill/"
                done = subprocess.run([NODE, str(ROOT / "tests" / "site_smoke.mjs"), url], capture_output=True, text=True, timeout=300)
            finally:
                server.shutdown()
        self.assertEqual(done.returncode, 0, done.stdout[-4000:] + done.stderr[-2000:])


if __name__ == "__main__":
    unittest.main()
