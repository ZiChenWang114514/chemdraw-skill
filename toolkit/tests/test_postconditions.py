"""Tests for the generic result post-conditions."""

import pytest

from cdxml_toolkit import postconditions as pc


def _doc(node_attrs: str, loose_text: str = "") -> str:
    text = f'<t id="9" p="150 100"><s>{loose_text}</s></t>' if loose_text else ""
    return ('<CDXML><page id="1"><fragment id="2">'
            f'<n id="3" p="100 100" Element="6" {node_attrs}/>'
            f'</fragment>{text}</page></CDXML>')


class TestChanged:
    def test_real_edit_passes(self):
        assert pc.check_changed("CCO", "CCN").ok

    def test_noop_fails_even_with_different_spelling(self):
        result = pc.check_changed("OCC", "C(O)C")
        assert not result.ok and result.code == "no_change"


class TestPreserved:
    def test_change_on_targeted_atom_passes(self):
        # Cl -> Br on atom 5; the edit may touch the halogen and its carbon (4)
        assert pc.check_preserved("OCC(N)CCl", "OCC(N)CBr", targeted_atoms=[4, 5]).ok

    def test_change_elsewhere_fails(self):
        # the same exchange while only the hydroxyl oxygen was targeted
        result = pc.check_preserved("OCC(N)CCl", "OCC(N)CBr", targeted_atoms=[0])
        assert not result.ok and result.code == "structure_not_preserved"

    def test_identity_passes(self):
        assert pc.check_preserved("CCO", "OCC").ok


class TestStereo:
    def test_complete(self):
        result = pc.check_stereocentres("C[C@H](N)C(=O)O")
        assert result.ok and result.details["count"] == 0

    def test_unspecified_counted(self):
        result = pc.check_stereocentres("CC(N)C(=O)O")
        assert not result.ok and result.code == "stereo_incomplete" and result.details["count"] == 1
        assert pc.check_stereocentres("CC(N)C(=O)O", max_unspecified=1).ok
        assert pc.unspecified_stereocentres("CC(N)C(O)C(=O)O") == [1, 3]


class TestCharge:
    def test_conserved(self):
        assert pc.check_charge_conserved("CC(=O)[O-].[Na+]", "CC(=O)[O-].[K+]").ok

    def test_not_conserved(self):
        result = pc.check_charge_conserved("CC(=O)O", "CC(=O)[O-]")
        assert not result.ok and result.details == {"before": 0, "after": -1, "expected_change": 0}
        assert pc.check_charge_conserved("CC(=O)O", "CC(=O)[O-]", expected_change=-1).ok


class TestConnectedMetal:
    def test_lone_palladium_with_four_phosphines_fails(self):
        ligand = "P(c1ccccc1)(c1ccccc1)c1ccccc1"
        result = pc.check_connected_metal("[Pd]." + ".".join([ligand] * 4))
        assert not result.ok and result.code == "disconnected_organometallic"

    def test_salt_and_bonded_complex_pass(self):
        assert pc.check_connected_metal("[K+].[K+].[O-]C([O-])=O").ok
        assert pc.check_connected_metal("CC(=O)O[Cu]OC(C)=O").ok
        assert pc.check_connected_metal("[Mg].BrCC").ok


class TestFormula:
    def test_formula_parser(self):
        assert pc.formula_counts("Ca(OH)2") == {"Ca": 1, "O": 2, "H": 2}
        assert pc.hill_formula(pc.formula_counts("BrC4H9")) == "C4H9Br"
        with pytest.raises(ValueError):
            pc.formula_counts("C4H9Br!")

    def test_match(self):
        assert pc.check_formula("C4H9Br", "CC(C)(C)Br").ok
        assert pc.check_formula({"C": 2, "H": 6, "O": 1}, "CCO").ok

    def test_mismatch(self):
        result = pc.check_formula("C4H9Br", "CCBr")
        assert not result.ok and result.details == {"expected": "C4H9Br", "actual": "C2H5Br"}


class TestCdxmlAnnotations:
    def test_charge_and_radical_on_nodes_pass(self):
        assert pc.check_cdxml_annotations(_doc('NumHydrogens="3" Radical="Doublet"')).ok
        assert pc.check_cdxml_annotations(_doc('NumHydrogens="3" Charge="1"')).ok

    def test_loose_charge_text_fails(self):
        result = pc.check_cdxml_annotations(_doc('NumHydrogens="4"', "+"))
        assert not result.ok and result.details["visible_charge"] == 1
        assert result.details["semantic_charge"] == 0

    def test_loose_radical_dot_fails(self):
        result = pc.check_cdxml_annotations(_doc('NumHydrogens="4"', "•"))
        assert not result.ok and result.details["visible_radicals"] == 1


class TestPayload:
    def test_failure_payload(self):
        failed = pc.check_changed("CCO", "CCO")
        payload = pc.failure_payload(failed, {"smiles": "CCO"}, hint="Name a different atom.")
        assert payload["ok"] is False
        assert payload["error"]["code"] == "postcondition_failed"
        assert payload["error"]["postcondition"] == "no_change"
        assert payload["error"]["hint"] == "Name a different atom."
        assert payload["rejected_result"] == {"smiles": "CCO"}

    def test_payload_rejects_passed_result_and_first_failure(self):
        with pytest.raises(ValueError):
            pc.failure_payload(pc.check_changed("CCO", "CCN"))
        assert pc.first_failure(pc.check_changed("C", "N")) is None
        assert pc.first_failure(pc.check_changed("C", "N"), pc.check_changed("C", "C")).code == "no_change"
