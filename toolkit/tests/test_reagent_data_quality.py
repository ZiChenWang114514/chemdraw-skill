"""Data-quality gate for the reagent tables used by the name resolver.

The curated table (``reagent_abbreviations.json``) is compared offline with a
PubChem snapshot (``tests/fixtures/reagent_reference.json``, rebuilt by
``scripts/build_reagent_reference.py``). The large secondary table is gated by
a generated quarantine list that must stay in sync with its generator.
"""

import json
from pathlib import Path

import pytest

Chem = pytest.importorskip("rdkit.Chem")
from rdkit.Chem import rdMolDescriptors  # noqa: E402

from cdxml_toolkit.resolve import reagent_quality  # noqa: E402

RESOLVE = Path(__file__).resolve().parents[1] / "cdxml_toolkit" / "resolve"
TABLE = json.loads((RESOLVE / "reagent_abbreviations.json").read_text(encoding="utf-8"))
REFERENCE = json.loads(
    (Path(__file__).parent / "fixtures" / "reagent_reference.json").read_text(encoding="utf-8")
)["entries"]

# Genuine radicals that are stored as such on purpose.
RADICAL_ALLOWLIST = {"tempo"}
# Entries whose stored species carries a net charge on purpose (none today).
CHARGE_ALLOWLIST: set = set()
# Entries PubChem cannot confirm. Raising this cap needs a reason in the snapshot.
UNVERIFIED_CAP = 12


def _smiles_list(entry):
    value = entry.get("smiles")
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def _structured():
    return [(key, entry) for key, entry in TABLE.items() if _smiles_list(entry)]


@pytest.mark.parametrize("key,entry", _structured(), ids=lambda v: v if isinstance(v, str) else "")
def test_entry_parses_and_is_consistent(key, entry):
    for smi in _smiles_list(entry):
        mol = Chem.MolFromSmiles(smi)
        assert mol is not None, f"{key}: SMILES does not parse: {smi}"
        canon = entry.get("canonical_smiles")
        if canon is not None:
            canon_list = canon if isinstance(canon, list) else [canon]
            assert Chem.MolToSmiles(mol) in canon_list, f"{key}: canonical_smiles is stale"


@pytest.mark.parametrize("key,entry", _structured(), ids=lambda v: v if isinstance(v, str) else "")
def test_entry_has_no_undeclared_radical_or_charge(key, entry):
    for smi in _smiles_list(entry):
        mol = Chem.MolFromSmiles(smi)
        radicals = reagent_quality.nonmetal_radical_atoms(mol)
        if key not in RADICAL_ALLOWLIST:
            assert not radicals, f"{key}: radical on {radicals}"
        if key not in CHARGE_ALLOWLIST:
            assert Chem.GetFormalCharge(mol) == 0, f"{key}: net charge {Chem.GetFormalCharge(mol)}"


def test_reference_snapshot_covers_the_table():
    assert set(REFERENCE) == set(TABLE)


@pytest.mark.parametrize("key,entry", _structured(), ids=lambda v: v if isinstance(v, str) else "")
def test_entry_formula_matches_reference(key, entry):
    ref = REFERENCE[key]
    if ref.get("formula") is None:
        assert ref["status"] == "unverified"
        return
    for smi in _smiles_list(entry):
        mol = Chem.MolFromSmiles(smi)
        formula = rdMolDescriptors.CalcMolFormula(mol)
        assert reagent_quality.same_formula(formula, ref["formula"]), (
            f"{key}: {formula} != reference {ref['formula']} ({ref.get('query') or ref.get('reason')})")
        assert Chem.GetFormalCharge(mol) == ref.get("charge", 0)


def test_unverified_entries_are_explained_and_capped():
    unverified = {k: v for k, v in REFERENCE.items() if v["status"] == "unverified"}
    for key, ref in unverified.items():
        assert ref.get("reason"), key
    assert len(unverified) <= UNVERIFIED_CAP, sorted(unverified)


def test_secondary_quarantine_is_in_sync_with_generator():
    secondary = json.loads((RESOLVE / "chemscanner_abbreviations.json").read_text(encoding="utf-8"))
    stored = json.loads((RESOLVE / "chemscanner_quarantine.json").read_text(encoding="utf-8"))
    assert stored == reagent_quality.build_secondary_quarantine(secondary)
