"""Quality checks for the reagent tables and the secondary-table quarantine.

``build_secondary_quarantine`` decides which entries of the large secondary
table (``chemscanner_abbreviations.json``) may never take part in name
resolution. Its output is stored in ``chemscanner_quarantine.json``; a test
keeps the stored file equal to what this function produces. Regenerate with::

    python -m cdxml_toolkit.resolve.reagent_quality
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Dict, List

HERE = Path(__file__).resolve().parent
SECONDARY_PATH = HERE / "chemscanner_abbreviations.json"
QUARANTINE_PATH = HERE / "chemscanner_quarantine.json"

UNSPECIFIED_STEREO_LIMIT = 3

# Main-group elements: a radical on one of these is a structure error, while
# RDKit reports unpaired d electrons on transition-metal ions as radicals.
_NONMETALS = {"H", "B", "C", "N", "O", "F", "Si", "P", "S", "Cl", "As", "Se", "Br", "Te", "I"}

# Entries confirmed wrong by comparison with PubChem; the reason names the
# correct species. These names resolve from the curated table instead.
KNOWN_WRONG: Dict[str, str] = {
    "mmn": "alias NMM points to an unrelated menthyl ether; N-methylmorpholine is CN1CCOCC1 (PubChem CID 7972)",
    "ppts": "stores a thiophosphate; PPTS is pyridinium p-toluenesulfonate (PubChem CID 466102)",
    "dppa": "stores a phosphinic azide without the P-O-aryl oxygens; DPPA is (PhO)2P(O)N3 (PubChem CID 123414)",
    "bti": "alias PIFA stores ring-substituted trifluoroacetates; PIFA is PhI(OCOCF3)2 (PubChem CID 102317)",
    "tesotf": "stores a trifluoroacetate; TESOTf is the triflate Et3SiOSO2CF3 (PubChem CID 2733308)",
    "hmds": "stores a pentamethyl Si-H species; HMDS is (Me3Si)2NH (PubChem CID 13838)",
}

# Stereo descriptors in a name: (R), (S), (1R,2S), (5aR,10bS), (E), (Z), (+), (-).
_CIP = re.compile(r"\((?:\d+[a-z]*'*)?[rs](?:\s*,\s*(?:\d+[a-z]*'*)?[rs])*\)|\((?:\d+[a-z]*)?[ez]\)|\([+-]\)")
_EZ = re.compile(r"\((?:\d+[a-z]*)?[ez]\)")


def nonmetal_radical_atoms(mol) -> List[str]:
    """Symbols of main-group atoms that carry unpaired electrons."""
    return [a.GetSymbol() for a in mol.GetAtoms()
            if a.GetNumRadicalElectrons() and a.GetSymbol() in _NONMETALS]


def unspecified_stereocentres(mol) -> int:
    from rdkit import Chem
    centres = Chem.FindMolChiralCenters(mol, includeUnassigned=True, useLegacyImplementation=False)
    return sum(1 for _, label in centres if label == "?")


def _formula_counts(formula: str) -> Counter:
    counts: Counter = Counter()
    for element, number in re.findall(r"([A-Z][a-z]?)(\d*)", formula.split("+")[0].split("-")[0]):
        counts["H" if element in ("D", "T") else element] += int(number or 1)
    return counts


def same_formula(a: str, b: str) -> bool:
    """Compare two molecular formulae element by element (D and T count as H)."""
    return _formula_counts(a) == _formula_counts(b)


def _quarantine_reasons(key: str, entry: dict) -> List[str]:
    from rdkit import Chem, rdBase

    if key in KNOWN_WRONG:
        return ["known_wrong: " + KNOWN_WRONG[key]]
    smiles = entry.get("smiles")
    smiles_list = smiles if isinstance(smiles, list) else [smiles]
    reasons: List[str] = []
    names = [key] + list(entry.get("aliases", []))
    blocker = rdBase.BlockLogs()
    try:
        for smi in smiles_list:
            mol = Chem.MolFromSmiles(smi) if smi else None
            if mol is None:
                reasons.append("unparsable")
                continue
            if nonmetal_radical_atoms(mol):
                reasons.append("radical")
            if unspecified_stereocentres(mol) >= UNSPECIFIED_STEREO_LIMIT:
                reasons.append("unspecified_stereocentres")
            has_tetrahedral = "@" in smi
            has_double_bond_stereo = "/" in smi or "\\" in smi
            for name in names:
                for match in _CIP.findall(name):
                    wanted = has_double_bond_stereo if _EZ.fullmatch(match) else has_tetrahedral
                    if not wanted:
                        reasons.append("name_stereo_missing_in_smiles")
                        break
    finally:
        del blocker
    return sorted(set(reasons))


def build_secondary_quarantine(secondary: dict) -> dict:
    """Return the quarantine document for the secondary table."""
    entries = {}
    for key in sorted(secondary):
        reasons = _quarantine_reasons(key, secondary[key])
        if reasons:
            entries[key] = reasons
    return {
        "generator": "cdxml_toolkit.resolve.reagent_quality.build_secondary_quarantine",
        "criteria": [
            "known_wrong: confirmed wrong against PubChem",
            "unparsable: SMILES does not parse in RDKit",
            "radical: unpaired electrons on a main-group atom",
            f"unspecified_stereocentres: {UNSPECIFIED_STEREO_LIMIT} or more stereocentres left unassigned",
            "name_stereo_missing_in_smiles: a name carries R/S, E/Z or (+)/(-) descriptors the SMILES lacks",
        ],
        "entries": entries,
    }


def main() -> int:
    secondary = json.loads(SECONDARY_PATH.read_text(encoding="utf-8"))
    document = build_secondary_quarantine(secondary)
    QUARANTINE_PATH.write_text(json.dumps(document, indent=1, ensure_ascii=True) + "\n", encoding="utf-8")
    counts = Counter(r.split(":")[0] for reasons in document["entries"].values() for r in reasons)
    print(f"{len(document['entries'])} quarantined entries: {dict(counts)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
