"""Structure edits either change exactly what was asked, or say that they did not."""

import json

import pytest
from rdkit import Chem

from cdxml_toolkit.naming import mol_builder
from cdxml_toolkit.naming.mol_builder import modify_molecule


def canonical(smiles):
    return Chem.CanonSmiles(smiles)


needs_name_engine = pytest.mark.skipif(
    mol_builder._try_validate("4-chlorobenzoic acid", use_network=False) is None,
    reason="no offline name-to-structure engine on this host",
)


@needs_name_engine
def test_adding_a_substituent_keeps_the_ones_already_there():
    result = modify_molecule(
        {"smiles": "OC(=O)c1ccc(Cl)cc1", "name": "4-chlorobenzoic acid"},
        "name_surgery", add=[{"locant": "2", "prefix": "fluoro"}],
    )
    assert result["ok"], result
    assert result["output_smiles"] == canonical("OC(=O)c1ccc(Cl)cc1F")


@needs_name_engine
def test_a_name_edit_that_moves_an_existing_substituent_is_rejected(monkeypatch):
    moved = {"ok": True, "name": "3-chloro-2-fluorobenzoic acid", "valid": True,
             "smiles": "O=C(O)c1cccc(Cl)c1F"}
    monkeypatch.setattr(mol_builder, "_modify_add", lambda *a, **k: moved)
    result = modify_molecule(
        {"smiles": "OC(=O)c1ccc(Cl)cc1", "name": "4-chlorobenzoic acid"},
        "name_surgery", add=[{"locant": "2", "prefix": "fluoro"}],
    )
    assert result["ok"] is False
    assert result["error"]["postcondition"] == "structure_not_preserved"
    assert result["rejected_result"]["output_smiles"] == canonical("O=C(O)c1cccc(Cl)c1F")


def test_an_edit_that_changes_nothing_is_not_a_success():
    result = modify_molecule({"smiles": "CCO"}, "set_smiles", new_smiles="OCC")
    assert result["ok"] is False
    assert result["error"]["postcondition"] == "no_change"


def test_a_pattern_with_several_sites_reports_every_product():
    result = modify_molecule({"smiles": "Oc1ccc(O)cc1C"}, "smarts", smarts="[c:1][OH]>>[c:1]OC")
    assert result["ok"]
    assert result["product_count"] == 2
    assert len(result["alternative_products"]) == 1
    assert any("2 different products" in w for w in result["warnings"])


def test_a_pattern_with_one_site_reports_one_product():
    result = modify_molecule({"smiles": "Oc1ccccc1"}, "smarts", smarts="[c:1][OH]>>[c:1]OC")
    assert result["ok"] and result["product_count"] == 1 and "warnings" not in result


def test_operation_names_are_matched_exactly_or_refused_with_suggestions():
    pytest.importorskip("mcp")
    from cdxml_toolkit.mcp_server import server

    assert server._normalize_operation("Name Surgery", None) == ("name_surgery", None)
    assert server._normalize_operation("BOC deprotection", None) == ("reaction", "BOC_deprotection")
    for vague in ("oxidation", "reduction", "amide", "Boc", "hydrolysis"):
        with pytest.raises(server.UnknownOperation) as error:
            server._normalize_operation(vague, None)
        assert error.value.suggestions, vague

    def call(*args):
        value = server.modify_molecule(*args)
        return json.loads(value) if isinstance(value, str) else value

    refused = call({"smiles": "C=CCO"}, "oxidation")
    assert refused["ok"] is False and refused["error"]["code"] == "unknown_operation"
    assert "epoxidation" in refused["error"]["suggestions"]

    matched = call({"smiles": "CC(C)(C)OC(=O)NCc1ccccc1"}, "BOC deprotection")
    assert matched["ok"] and matched["matched_reaction"] == "BOC_deprotection"
