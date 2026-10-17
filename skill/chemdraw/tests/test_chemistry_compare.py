from __future__ import annotations

import json
import unittest
from unittest import mock

from cdxml_toolkit.mcp_runtime import chemistry_compare
class FakeBridge:
    def __init__(self, infos: dict[str, dict]):
        self.infos = infos
        self.calls: list[str] = []
        self.closed = False

    def get_info(self, source: str) -> dict:
        self.calls.append(source)
        value = self.infos.get(source)
        if isinstance(value, Exception):
            raise value
        if value is None:
            raise RuntimeError("unparseable molecule")
        return dict(value)

    def close(self) -> None:
        self.closed = True


def info(smiles: str, inchi: str, formula: str = "C2H6O") -> dict:
    return {
        "ok": True,
        "type": "structure",
        "smiles": smiles,
        "inchi": inchi,
        "formula": formula,
        "name": None,
        "atom_count": 3,
        "bond_count": 2,
    }


class MoleculeComparisonTests(unittest.TestCase):
    def test_compare_uses_chemscript_identity_and_rdkit_fingerprint(self):
        bridge = FakeBridge(
            {
                "ethanol-a": info("CCO", "InChI=1S/C2H6O/c1-2-3/h3H,2H2,1H3"),
                "ethanol-b": info("OCC", "InChI=1S/C2H6O/c1-2-3/h3H,2H2,1H3"),
            }
        )
        with mock.patch.object(
            chemistry_compare, "_bridge_factory", return_value=bridge
        ):
            result = chemistry_compare.compare_molecules("ethanol-a", "ethanol-b")

        self.assertTrue(result["ok"])
        self.assertTrue(result["outputs"]["exact_match"])
        self.assertEqual(result["outputs"]["tanimoto"], 1.0)
        self.assertEqual(result["metadata"]["identity_engine"], "ChemScriptBridge")
        self.assertEqual(result["metadata"]["fingerprint_engine"], "RDKit")
        self.assertEqual(bridge.calls, ["ethanol-a", "ethanol-b"])
        self.assertTrue(bridge.closed)

    def test_compare_reports_stereochemical_difference(self):
        bridge = FakeBridge(
            {
                "e": info("F/C=C/F", "InChI=1S/C2H2F2/c3-1-2-4/h1-2H/b2-1+"),
                "z": info("F/C=C\\F", "InChI=1S/C2H2F2/c3-1-2-4/h1-2H/b2-1-"),
            }
        )
        with mock.patch.object(
            chemistry_compare, "_bridge_factory", return_value=bridge
        ):
            result = chemistry_compare.compare_molecules("e", "z")

        self.assertFalse(result["outputs"]["exact_match"])
        self.assertEqual(result["outputs"]["connectivity_tanimoto"], 1.0)
        self.assertLess(result["outputs"]["tanimoto"], 1.0)
        self.assertTrue(any("stereo" in warning.lower() for warning in result["warnings"]))

    def test_compare_rejects_unknown_fingerprint_before_starting_bridge(self):
        with mock.patch.object(chemistry_compare, "_bridge_factory") as factory:
            with self.assertRaisesRegex(ValueError, "fingerprint"):
                chemistry_compare.compare_molecules("CC", "CCC", fingerprint="unknown")
        factory.assert_not_called()

    def test_batch_reuses_one_bridge_and_keeps_raw_inputs_out_of_results(self):
        secret_a = "private-molecule-a"
        secret_b = "private-molecule-b"
        bad = "private-invalid-molecule"
        bridge = FakeBridge(
            {
                secret_a: info("CCO", "inchi-a"),
                secret_b: info("OCC", "inchi-a"),
                bad: RuntimeError("cannot parse"),
            }
        )
        pairs = [
            {"pair_id": "same", "mol1": secret_a, "mol2": secret_b},
            {"pair_id": "bad", "mol1": bad, "mol2": secret_b},
        ]
        with mock.patch.object(
            chemistry_compare, "_bridge_factory", return_value=bridge
        ) as factory:
            result = chemistry_compare.batch_compare_molecules(pairs)

        self.assertTrue(result["ok"])
        self.assertEqual(result["metadata"]["total"], 2)
        self.assertEqual(result["metadata"]["succeeded"], 1)
        self.assertEqual(result["metadata"]["failed"], 1)
        self.assertEqual(result["outputs"]["results"][0]["pair_id"], "same")
        self.assertFalse(result["outputs"]["results"][1]["ok"])
        encoded = json.dumps(result)
        self.assertNotIn(secret_a, encoded)
        self.assertNotIn(secret_b, encoded)
        self.assertNotIn(bad, encoded)
        factory.assert_called_once_with()
        self.assertTrue(bridge.closed)

    def test_batch_rejects_unbounded_or_duplicate_pair_ids(self):
        with self.assertRaisesRegex(ValueError, "at most"):
            chemistry_compare.batch_compare_molecules(
                [{"mol1": "C", "mol2": "C"}] * (chemistry_compare.MAX_BATCH_PAIRS + 1)
            )
        with self.assertRaisesRegex(ValueError, "pair_id"):
            chemistry_compare.batch_compare_molecules(
                [
                    {"pair_id": "duplicate", "mol1": "C", "mol2": "C"},
                    {"pair_id": "duplicate", "mol1": "CC", "mol2": "CC"},
                ]
            )


if __name__ == "__main__":
    unittest.main()
