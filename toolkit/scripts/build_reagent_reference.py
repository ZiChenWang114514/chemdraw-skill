"""Build the PubChem reference snapshot for the curated reagent table.

One-off developer script (needs network access). For every entry of
``cdxml_toolkit/resolve/reagent_abbreviations.json`` it asks PubChem, by public
reagent name, for the molecular formula and net charge, and writes
``tests/fixtures/reagent_reference.json``. The offline test
``tests/test_reagent_data_quality.py`` compares the table against that snapshot.

Entries PubChem cannot answer, or answers with a record for a different form
of the reagent, are written as ``"status": "unverified"`` with a reason; the
test caps how many there may be. Entries marked ``"pinned": true`` are kept as
written on a rebuild: they record where PubChem's record is a different form
(a neutral metal atom, a radical boron) and carry the supplier formula instead.

Run from ``toolkit/``::

    python ../skill/chemdraw/scripts/cdx.py py scripts/build_reagent_reference.py
"""

from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOLKIT = HERE.parent
TABLE = TOOLKIT / "cdxml_toolkit" / "resolve" / "reagent_abbreviations.json"
OUT = TOOLKIT / "tests" / "fixtures" / "reagent_reference.json"

PUG = "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{}/property/MolecularFormula,Charge/JSON"

# PubChem query names for entries whose key, display text and aliases are not
# names PubChem knows (abbreviations that are ambiguous or not indexed).
QUERY_NAMES = {
    "pd2dba3": "tris(dibenzylideneacetone)dipalladium(0)",
    "pd2(dba)3": "tris(dibenzylideneacetone)dipalladium(0)",
    "pd(dba)2": "bis(dibenzylideneacetone)palladium(0)",
    "pd(oac)2": "palladium(II) acetate",
    "pd(pph3)4": "tetrakis(triphenylphosphine)palladium(0)",
    "pd(pph3)2cl2": "bis(triphenylphosphine)palladium(II) dichloride",
    "pdcl2": "palladium(II) chloride",
    "pd/c": "palladium",
    "pd(oh)2/c": "palladium hydroxide",
    "pd2cl2(allyl)2": "allylpalladium(II) chloride dimer",
    "peppsi-ipr": "PEPPSI-IPr",
    "binap": "BINAP",
    "rac-binap": "BINAP",
    "dppf": "1,1'-bis(diphenylphosphino)ferrocene",
    "dppe": "1,2-bis(diphenylphosphino)ethane",
    "dppp": "1,3-bis(diphenylphosphino)propane",
    "ruphos": "2-dicyclohexylphosphino-2',6'-diisopropoxybiphenyl",
    "cdmt": "2-chloro-4,6-dimethoxy-1,3,5-triazine",
    "dcm": "dichloromethane",
    "kf": "potassium fluoride",
    "znbr2": "zinc bromide",
    "pd(dppf)cl2·dcm": "95464-05-4",
    "dtbpf": "1,1'-bis(di-tert-butylphosphino)ferrocene",
    "catacxium a": "butyldi-1-adamantylphosphine",
    "p(cy)3": "tricyclohexylphosphine",
    "p(tbu)3": "tri-tert-butylphosphine",
    "naot-bu": "sodium tert-butoxide",
    "naotbu": "sodium tert-butoxide",
    "kot-bu": "potassium tert-butoxide",
    "kotbu": "potassium tert-butoxide",
    "liotbu": "lithium tert-butoxide",
    "lihmds": "lithium bis(trimethylsilyl)amide",
    "nahmds": "sodium bis(trimethylsilyl)amide",
    "khmds": "potassium bis(trimethylsilyl)amide",
    "lda": "lithium diisopropylamide",
    "nah": "sodium hydride",
    "n-buli": "n-butyllithium",
    "t-buli": "tert-butyllithium",
    "diea": "N,N-diisopropylethylamine",
    "dipea": "N,N-diisopropylethylamine",
    "edc": "N-(3-dimethylaminopropyl)-N'-ethylcarbodiimide",
    "edc·hcl": "N-(3-dimethylaminopropyl)-N'-ethylcarbodiimide hydrochloride",
    "t3p": "propylphosphonic anhydride",
    "dcc": "N,N'-dicyclohexylcarbodiimide",
    "dic": "N,N'-diisopropylcarbodiimide",
    "nabh4": "sodium borohydride",
    "nabh3cn": "sodium cyanoborohydride",
    "lialh4": "lithium aluminium hydride",
    "dibal-h": "diisobutylaluminium hydride",
    "dmp": "Dess-Martin periodinane",
    "pcc": "pyridinium chlorochromate",
    "pdc": "pyridinium dichromate",
    "tpap": "tetrapropylammonium perruthenate",
    "oxone": "potassium peroxymonosulfate",
    "tbhp": "tert-butyl hydroperoxide",
    "dma": "N,N-dimethylacetamide",
    "dce": "1,2-dichloroethane",
    "tfaa": "trifluoroacetic anhydride",
    "fmoc-cl": "9-fluorenylmethyl chloroformate",
    "cbz-cl": "benzyl chloroformate",
    "tbscl": "tert-butyldimethylsilyl chloride",
    "tmscl": "chlorotrimethylsilane",
    "tipscl": "triisopropylsilyl chloride",
    "tbaf": "tetrabutylammonium fluoride",
    "cui": "copper(I) iodide",
    "cucl": "copper(I) chloride",
    "cubr": "copper(I) bromide",
    "cu(oac)2": "copper(II) acetate",
    "cuso4": "copper(II) sulfate",
    "cuso4·5h2o": "copper(II) sulfate pentahydrate",
    "ni(cod)2": "bis(1,5-cyclooctadiene)nickel(0)",
    "nicl2": "nickel(II) chloride",
    "nicl2(dme)": "nickel(II) chloride ethylene glycol dimethyl ether complex",
    "b2pin2": "bis(pinacolato)diboron",
    "b(oh)3": "boric acid",
    "pinbh": "pinacolborane",
    "hbpin": "pinacolborane",
    "fecl3": "iron(III) chloride",
    "fecl2": "iron(II) chloride",
    "bf3·oet2": "boron trifluoride diethyl etherate",
    "tf2o": "trifluoromethanesulfonic anhydride",
    "zn dust": "zinc",
    "mg turnings": "magnesium",
    "tmsi": "iodotrimethylsilane",
    "nbs": "N-bromosuccinimide",
    "ncs": "N-chlorosuccinimide",
    "nis": "N-iodosuccinimide",
    "naso3cf3": "sodium trifluoromethanesulfonate",
    "cf3so2na": "sodium trifluoromethanesulfinate",
    "dast": "diethylaminosulfur trifluoride",
    "p(oet)3": "triethyl phosphite",
    "grubbs ii": "Grubbs catalyst 2nd generation",
    "hoveyda-grubbs ii": "Hoveyda-Grubbs catalyst 2nd generation",
    "dme": "1,2-dimethoxyethane",
    "tempo": "TEMPO",
    "tbuxphos": "tBuXPhos",
    "pd(dppf)cl2": "72287-26-4",
    "pd2(dba)3·chcl3": "tris(dibenzylideneacetone)dipalladium(0)-chloroform adduct",
    "nmm": "4-methylmorpholine",
    "ppts": "pyridinium p-toluenesulfonate",
    "dppa": "diphenylphosphoryl azide",
    "pifa": "[bis(trifluoroacetoxy)iodo]benzene",
    "tesotf": "triethylsilyl trifluoromethanesulfonate",
    "hmds": "hexamethyldisilazane",
    "et3n·hcl": "triethylamine hydrochloride",
}


def candidate_names(key: str, entry: dict) -> list[str]:
    names = []
    if key in QUERY_NAMES:
        names.append(QUERY_NAMES[key])
    names.extend(sorted(entry.get("aliases", []), key=len, reverse=True))
    names.extend([entry.get("display", ""), key])
    seen, out = set(), []
    for name in names:
        if name and name.lower() not in seen:
            seen.add(name.lower())
            out.append(name)
    return out


def query_pubchem(name: str) -> dict | None:
    url = PUG.format(urllib.parse.quote(name, safe=""))
    request = urllib.request.Request(url, headers={"User-Agent": "cdxml-toolkit-reference-builder"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                props = json.load(response)["PropertyTable"]["Properties"]
            return props[0] if props else None
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return None
            time.sleep(2 + attempt * 2)
        except (urllib.error.URLError, TimeoutError):
            time.sleep(2 + attempt * 2)
    return None


def main() -> int:
    table = json.loads(TABLE.read_text(encoding="utf-8"))
    previous = {}
    if OUT.exists():
        previous = json.loads(OUT.read_text(encoding="utf-8")).get("entries", {})
    entries = {}
    for key, entry in table.items():
        if previous.get(key, {}).get("pinned"):
            # Hand-kept verdict: PubChem's record is a different form of the reagent.
            entries[key] = previous[key]
            continue
        if entry.get("smiles") is None:
            entries[key] = {"status": "unverified", "reason": "entry stores no structure (a solution or mixture)"}
            continue
        hit = None
        for name in candidate_names(key, entry):
            props = query_pubchem(name)
            time.sleep(0.25)
            if props:
                hit = {"status": "verified", "query": name, "cid": props.get("CID"),
                       "formula": props.get("MolecularFormula"), "charge": props.get("Charge", 0)}
                break
        if hit is None:
            # Keep a hand-written reason from a previous run instead of a generic one.
            old = previous.get(key, {})
            reason = old.get("reason") if old.get("status") == "unverified" else None
            hit = {"status": "unverified", "reason": reason or "PubChem has no record under any name of this entry"}
        entries[key] = hit
        print(key, hit, file=sys.stderr)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"source": "PubChem PUG REST, MolecularFormula and Charge by name",
                               "entries": entries}, indent=1, ensure_ascii=True) + "\n",
                   encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
