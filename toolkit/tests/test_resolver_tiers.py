"""Name-resolver tier order, provenance fields and the audit regression cases."""

import pytest

Chem = pytest.importorskip("rdkit.Chem")
from rdkit.Chem import rdMolDescriptors  # noqa: E402

from cdxml_toolkit.naming import mol_builder  # noqa: E402
from cdxml_toolkit.resolve.reagent_db import get_reagent_db  # noqa: E402


@pytest.fixture
def offline(monkeypatch):
    """No ChemDraw, no OPSIN, no network: only the local tables answer."""
    monkeypatch.setattr(mol_builder, "_get_cs", lambda: None)
    monkeypatch.setattr(mol_builder, "_resolve_opsin", lambda name: None)
    monkeypatch.setattr(mol_builder, "_resolve_pubchem", lambda name: pytest.fail("network tier ran offline"))
    return monkeypatch


def _formula(smiles):
    return rdMolDescriptors.CalcMolFormula(Chem.MolFromSmiles(smiles))


# Formulae from PubChem (CID in the comment) or, where PubChem stores a
# different form, from the supplier record named in reagent_reference.json.
AUDIT_CASES = {
    "LiHMDS": "C6H18LiNSi2",       # CAS 4039-32-1, lithium amide salt
    "DCC": "C13H22N2",             # CID 10868
    "HBpin": "C6H13BO2",           # CAS 25015-63-8, B-H bond
    "NMM": "C5H11NO",              # CID 7972
    "PPTS": "C12H13NO3S",          # CID 466102
    "DPPA": "C12H10N3O3P",         # CID 123414
    "PIFA": "C10H5F6IO4",          # CID 102317
    "TESOTf": "C7H15F3O3SSi",      # CID 2733308
    "HMDS": "C6H19NSi2",           # CID 13838
    "Et3N·HCl": "C6H16ClN",   # CID 11130
    "Pd(dppf)Cl2": "C34H28Cl2FeP2Pd",  # CID 71310626
}


@pytest.mark.parametrize("name,formula", sorted(AUDIT_CASES.items()))
def test_audit_cases_resolve_correctly_offline(offline, name, formula):
    res = mol_builder._resolve_query(name, use_network=False)
    assert res is not None, name
    assert _formula(res["smiles"]) == formula
    assert Chem.GetFormalCharge(Chem.MolFromSmiles(res["smiles"])) == 0
    assert res["source_tier"] == "primary"


def test_result_carries_provenance_fields(offline):
    res = mol_builder._resolve_query("Cs2CO3", use_network=False)
    assert res["source"] == "reagent_db"
    assert res["source_tier"] == "primary"
    assert res["unspecified_stereocentres"] == 0
    assert sorted(c["count"] for c in res["components"]) == [1, 2]  # CO3 2-, 2 Cs+


def test_salt_suffix_is_kept_as_a_component(offline):
    res = mol_builder._resolve_query("DIPEA·HCl", use_network=False)
    assert res is not None
    assert _formula(res["smiles"]) == "C8H20ClN"
    assert [c["display"] for c in res["components"]] == ["DIPEA", "HCl"]


def test_hydrate_counts_water(offline):
    res = mol_builder._resolve_query("CuSO4·5H2O", use_network=False)
    assert _formula(res["smiles"]) == "H10CuO9S"  # RDKit Hill order of CuSO4.5H2O


def test_opsin_runs_before_the_secondary_table(monkeypatch):
    monkeypatch.setattr(mol_builder, "_get_cs", lambda: None)
    monkeypatch.setattr(mol_builder, "_resolve_opsin", lambda name: "C[N+]1([O-])CCOCC1")
    res = mol_builder._resolve_query("NMO", use_network=False)
    assert res["source_tier"] == "opsin"


def test_pubchem_runs_before_the_secondary_table_only_when_allowed(monkeypatch):
    monkeypatch.setattr(mol_builder, "_get_cs", lambda: None)
    monkeypatch.setattr(mol_builder, "_resolve_opsin", lambda name: None)
    monkeypatch.setattr(mol_builder, "_resolve_pubchem", lambda name: "C[N+]1([O-])CCOCC1")
    monkeypatch.delenv("CHEMDRAW_OFFLINE", raising=False)
    assert mol_builder._resolve_query("NMO", use_network=True)["source_tier"] == "pubchem"
    low = mol_builder._resolve_query("NMO", use_network=False)
    assert low["source_tier"] == "secondary"
    assert low["confidence"] == "low"
    monkeypatch.setenv("CHEMDRAW_OFFLINE", "1")
    assert mol_builder._resolve_query("NMO", use_network=True)["source_tier"] == "secondary"


def test_quarantined_secondary_entry_never_resolves(offline):
    assert mol_builder._resolve_query("MMN", use_network=False) is None
    assert get_reagent_db().entry_for_name("mmn") is None


def test_condensed_formula_is_the_last_tier(offline):
    res = mol_builder._resolve_query("PhCH2Br", use_network=False)
    assert res["source_tier"] == "condensed"
    assert res["source"] == "formula"


def test_reverse_lookup_uses_the_primary_table_only():
    db = get_reagent_db()
    assert db.entry_for_smiles("CCN(CC)CC")["display"] == "Et3N"
    assert db.entry_for_smiles("C[N+]1([O-])CCOCC1") is None  # NMO lives in the secondary table only


def test_offline_resolution_never_reaches_the_network_through_the_prefix_lookup(offline):
    """``use_network=False`` holds for the whole call, including the substituent-prefix lookup."""
    for query in ("an unlisted trivial name", "CC(C)(C)c1ccc(cc1)C(C)(C)C", "aspirin"):
        mol_builder.resolve_compound(query, use_network=False)
        mol_builder.get_prefix_form(query, use_network=False)


def test_the_offline_switch_wins_over_the_argument(offline):
    offline.setenv("CHEMDRAW_OFFLINE", "1")
    mol_builder.resolve_compound("an unlisted trivial name", use_network=True)
    mol_builder.get_prefix_form("an unlisted trivial name")
