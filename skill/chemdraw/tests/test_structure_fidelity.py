from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from cdxml_toolkit.mcp_runtime import official_overrides
from cdxml_toolkit.mcp_runtime import structure_fidelity
class StructureFidelityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_draw_molecule_preserves_tetrahedral_stereochemistry(self):
        first = self.root / "first.cdxml"
        second = self.root / "second.cdxml"
        first_smiles = "N[C@@H]1CC[C@H](O)C1"
        second_smiles = "N[C@@H]1CC[C@@H](O)C1"

        first_result = official_overrides.draw_molecule(
            {"smiles": first_smiles}, output_path=str(first)
        )
        second_result = official_overrides.draw_molecule(
            {"smiles": second_smiles}, output_path=str(second)
        )

        self.assertNotEqual(first.read_bytes(), second.read_bytes())
        self.assertIn("Display=\"Wedge", first.read_text(encoding="utf-8"))
        self.assertIn("Display=\"Wedge", second.read_text(encoding="utf-8"))
        self.assertNotIn("WedgedHash", first.read_text(encoding="utf-8"))
        self.assertIn("WedgedHash", second.read_text(encoding="utf-8"))
        for result in (first_result, second_result):
            validation = result["metadata"]["chemistry_validation"]
            self.assertEqual(validation["status"], "preserved")
            self.assertEqual(validation["specified_chiral_centers"], 2)
            self.assertGreaterEqual(validation["wedge_bonds"], 1)

    def test_draw_molecule_preserves_double_bond_geometry(self):
        trans = self.root / "trans.cdxml"
        cis = self.root / "cis.cdxml"

        trans_result = official_overrides.draw_molecule(
            {"smiles": "F/C=C/F"}, output_path=str(trans)
        )
        cis_result = official_overrides.draw_molecule(
            {"smiles": "F/C=C\\F"}, output_path=str(cis)
        )

        self.assertNotEqual(trans.read_bytes(), cis.read_bytes())
        self.assertEqual(
            trans_result["metadata"]["chemistry_validation"]["stereo_double_bonds"],
            1,
        )
        self.assertEqual(
            cis_result["metadata"]["chemistry_validation"]["stereo_double_bonds"],
            1,
        )

    def test_draw_molecule_preserves_isotopes_and_charges(self):
        output = self.root / "isotope-charge.cdxml"

        result = official_overrides.draw_molecule(
            {"smiles": "[2H][C@H]([NH3+])C(=O)[O-]"}, output_path=str(output)
        )

        text = output.read_text(encoding="utf-8")
        self.assertIn('Isotope="2"', text)
        self.assertIn('Charge="1"', text)
        self.assertIn('Charge="-1"', text)
        validation = result["metadata"]["chemistry_validation"]
        self.assertEqual(validation["isotope_atoms"], 1)
        self.assertEqual(validation["charged_atoms"], 2)

    def test_draw_molecule_accepts_kekulized_aromatic_cdxml(self):
        output = self.root / "aspirin.cdxml"

        result = official_overrides.draw_molecule(
            {"smiles": "CC(=O)Oc1ccccc1C(=O)O"}, output_path=str(output)
        )

        self.assertTrue(output.is_file())
        self.assertEqual(
            result["metadata"]["chemistry_validation"]["status"], "preserved"
        )

    def test_stereochemical_input_is_rejected_when_cdxml_has_no_wedges(self):
        output = self.root / "broken.cdxml"
        from cdxml_toolkit.mcp_server.server import draw_molecule

        draw_molecule.__wrapped__(
            {"smiles": "F[C@H](Cl)Br"}, output_path=str(output)
        )

        from xml.dom import minidom
        document = minidom.parse(str(output))
        for bond in document.getElementsByTagName("b"):
            if bond.hasAttribute("Display"):
                bond.removeAttribute("Display")
        output.write_bytes(document.toxml(encoding="UTF-8"))

        with self.assertRaises(structure_fidelity.StructureFidelityError) as raised:
            structure_fidelity.repair_and_validate_drawn_cdxml(
                "F[C@H](Cl)Br", output, repair_stereo=False
            )

        self.assertEqual(raised.exception.error_code, "stereochemistry_not_preserved")


if __name__ == "__main__":
    unittest.main()
