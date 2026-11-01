#!/usr/bin/env python3
"""Measure the installed OCSR engines on clean RDKit depictions.

Usage:
    python scripts/ocsr_benchmark.py [--engines molscribe,molvec] [--out report.json]

Each reference SMILES is drawn to a PNG, every installed engine reads it, and the
answer counts as correct when the full InChIKey matches. These are clean computer
drawings, so the numbers are an upper bound; they say nothing about scanned papers
or hand drawings. Not run in CI. Nothing is uploaded: remote engines are skipped.
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "toolkit"))

REFERENCE = [
    "CC(=O)Oc1ccccc1C(=O)O",
    "CN1C=NC2=C1C(=O)N(C(=O)N2C)C",
    "CC(C)Cc1ccc(cc1)C(C)C(=O)O",
    "O=C(O)C[C@H](N)C(=O)O",
    "CC(=O)Nc1ccc(O)cc1",
    "c1ccc2c(c1)[nH]c1ccccc12",
    "CCN(CC)CCNC(=O)c1ccc(N)cc1",
    "OC[C@H]1O[C@@H](O)[C@H](O)[C@@H](O)[C@@H]1O",
    "C1CCC(CC1)N2CCOCC2",
    "Clc1ccc(cc1)C(c1ccccc1)N1CCN(CC1)C",
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--engines", default="molscribe,molnextr,molvec")
    parser.add_argument("--out", default=None)
    args = parser.parse_args()

    from rdkit import Chem
    from rdkit.Chem import Draw
    from cdxml_toolkit.engines import ocsr

    names = [n.strip() for n in args.engines.split(",") if n.strip()]
    stats = {n: {"correct": 0, "failed": 0, "seconds": 0.0} for n in names}
    rows = []
    with tempfile.TemporaryDirectory() as tmp:
        for i, smiles in enumerate(REFERENCE):
            mol = Chem.MolFromSmiles(smiles)
            truth = Chem.MolToInchiKey(mol)
            image = Path(tmp) / f"ref-{i}.png"
            Draw.MolToFile(mol, str(image), size=(500, 400))
            row = {"smiles": smiles, "results": {}}
            for name in names:
                started = time.time()
                try:
                    out = ocsr.recognize(str(image), engines=name)
                    entry = out["engines"][0]
                    preds = entry.get("structures") or []
                    got = preds[0].get("smiles") if preds else None
                    ok = bool(preds) and preds[0].get("inchikey") == truth
                    if not entry.get("ok"):
                        stats[name]["failed"] += 1
                except Exception as exc:  # report, keep going
                    got, ok = None, False
                    stats[name]["failed"] += 1
                    row["results"][name] = {"error": str(exc)[:200]}
                    continue
                finally:
                    stats[name]["seconds"] += time.time() - started
                stats[name]["correct"] += int(ok)
                row["results"][name] = {"smiles": got, "correct": ok}
            rows.append(row)

    total = len(REFERENCE)
    print(f"{total} clean RDKit depictions; match on full InChIKey")
    for name, s in stats.items():
        print(f"{name:12s} {s['correct']:>2}/{total}  failed {s['failed']}  {s['seconds'] / total:.1f} s per image")
    if args.out:
        Path(args.out).write_text(json.dumps({"stats": stats, "rows": rows}, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
