from __future__ import annotations

from pathlib import Path
import re
import tempfile
import unittest
from unittest import mock

from rdkit import Chem
from rdkit.Chem import rdDepictor

from cdxml_toolkit.chemdraw import chemscript_bridge, chemscript_mac, mac_automation


ASPIRIN = "CC(=O)Oc1ccccc1C(=O)O"
TWO_ATOM_CDXML = (
    '<?xml version="1.0" encoding="UTF-8" ?><CDXML><page id="1"><fragment id="2">'
    '<n id="3" p="100 200"/><n id="4" p="114.4 200" Element="8"/>'
    '<b id="5" B="3" E="4"/></fragment></page></CDXML>'
)


class FakeChemDraw:
    """Answers run_steps like ChemDraw for macOS, from canned readings."""

    def __init__(self, smiles=ASPIRIN, formula="C9H8O4", names=("2-acetoxybenzoic acid",)):
        self.smiles = smiles
        self.formula = formula
        self.names = list(names)
        self.calls = []
        self.source_texts = []
        self.name_requests = []
        self.closed = False
        self.launched = True

    def run_steps(self, source, steps, timeout_seconds=None):
        steps = [str(step) for step in steps]
        self.calls.append((Path(source), steps))
        self.source_texts.append(Path(source).read_text(encoding="utf-8", errors="replace"))
        answers = []
        named = "Convert Structure to Name" in steps
        i = 0
        while i < len(steps):
            step = steps[i]
            if step == "query":
                answers += [self.smiles, self.formula, "180.16", "180.04"]
                i += 1
            elif step == "save":
                destination = Path(steps[i + 1])
                if destination.suffix == ".cdxml":
                    captions = "".join(
                        f'<t p="0 0"><s>{name}</s></t>' for name in (self.names if named else [])
                    )
                    destination.write_text(
                        TWO_ATOM_CDXML.replace("</page>", captions + "</page>"), encoding="utf-8"
                    )
                else:
                    destination.write_text(f"saved {destination.suffix}", encoding="utf-8")
                i += 3
            elif step == "menu":
                i += 3
            else:
                i += 1
        return answers

    def name_to_structure(self, name, destination):
        self.name_requests.append(name)
        Path(destination).write_text(TWO_ATOM_CDXML, encoding="utf-8")
        return str(destination)

    def close(self):
        self.closed = True


class MacChemScriptTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.chemdraw = FakeChemDraw()
        self.opsin = mock.Mock(return_value=None)
        self.backend = chemscript_mac.MacChemScript(session=self.chemdraw, opsin=self.opsin)

    def tearDown(self):
        self.backend.close()
        self.temp.cleanup()

    def file(self, name: str, text: str = TWO_ATOM_CDXML) -> str:
        path = self.root / name
        path.write_text(text, encoding="utf-8")
        return str(path)

    def steps(self) -> list[str]:
        return self.chemdraw.calls[-1][1]

    def test_unknown_command_is_reported_like_the_chemscript_server(self):
        self.assertEqual(
            self.backend.call("format_disk", {}),
            {"ok": False, "error": "Unknown command: format_disk"},
        )

    def test_formula_and_smiles_are_chemdraws_own_reading(self):
        result = self.backend.call("get_formula", {"source": self.file("a.cdxml")})

        self.assertEqual(result, {"ok": True, "formula": "C9H8O4"})
        self.assertEqual(self.steps()[:2], ["select-all", "query"])

    def test_name_of_a_smiles_string_uses_chemdraw_struct_to_name(self):
        result = self.backend.call("get_name", {"source": ASPIRIN})

        self.assertEqual(result, {"ok": True, "name": "2-acetoxybenzoic acid"})
        source, steps = self.chemdraw.calls[-1]
        # Staged as CDXML: ChemDraw for macOS stalls opening molfiles wider than its page.
        self.assertEqual(source.suffix, ".cdxml")
        self.assertIn('BondLength="14.40"', self.chemdraw.source_texts[-1])
        self.assertIn("Convert Structure to Name", steps)

    def test_unnamed_structure_is_an_error(self):
        self.chemdraw.names = []
        result = self.backend.call("get_name", {"source": "[Na+].[Cl-]"})

        self.assertFalse(result["ok"])

    def test_a_name_missing_once_is_asked_for_again(self):
        # ChemDraw for macOS occasionally saves before Convert Structure to Name has added its caption.
        names, self.chemdraw.names = self.chemdraw.names, []
        original = self.chemdraw.run_steps

        def first_unnamed(source, steps, timeout_seconds=None):
            answers = original(source, steps, timeout_seconds)
            self.chemdraw.names = names
            return answers

        self.chemdraw.run_steps = first_unnamed
        result = self.backend.call("get_name", {"source": ASPIRIN})

        self.assertEqual(result, {"ok": True, "name": "2-acetoxybenzoic acid"})
        self.assertEqual(len(self.chemdraw.calls), 2)

    def test_names_resolve_offline_with_opsin_before_chemdraw(self):
        self.opsin.return_value = "C1COCCN1"
        result = self.backend.call(
            "write_data", {"source": "morpholine", "target_format": "smiles", "source_format": "name"}
        )

        self.assertEqual(result, {"ok": True, "data": "C1COCCN1"})
        self.assertEqual(self.chemdraw.name_requests, [])

    def test_names_opsin_cannot_parse_fall_back_to_chemdraw(self):
        self.chemdraw.smiles = "CO"
        result = self.backend.call(
            "write_data", {"source": "aspirin", "target_format": "smiles", "source_format": "name"}
        )

        self.assertEqual(result, {"ok": True, "data": "CO"})
        self.assertEqual(self.chemdraw.name_requests, ["aspirin"])

    def test_unresolvable_name_is_an_error(self):
        self.chemdraw.name_to_structure = mock.Mock(
            side_effect=mac_automation.MacAutomationError("name_not_recognized", "no")
        )
        result = self.backend.call("name_to_cdxml", {"name": "xyzzy"})

        self.assertFalse(result["ok"])
        self.assertIn("xyzzy", result["error"])

    def test_a_name_chemdraw_rejected_is_not_asked_again(self):
        rejected = mac_automation.MacAutomationError("name_not_recognized", "no")
        self.chemdraw.name_to_structure = mock.Mock(side_effect=rejected)
        for _ in range(3):
            result = self.backend.call(
                "write_data", {"source": "niline", "target_format": "smiles", "source_format": "name"}
            )
            self.assertFalse(result["ok"])

        self.assertEqual(self.chemdraw.name_to_structure.call_count, 1)
        self.assertEqual(self.opsin.call_count, 1)

    def test_smiles_to_cdxml_is_cleaned_up_by_chemdraw(self):
        result = self.backend.call("smiles_to_cdxml", {"smiles": "CO"})

        self.assertTrue(result["ok"])
        self.assertIn("<CDXML>", result["cdxml"])
        self.assertEqual(result["smiles"], "CO")
        self.assertIn("Clean Up Structure", self.steps())

    def test_invalid_smiles_is_an_error(self):
        result = self.backend.call("smiles_to_cdxml", {"smiles": "C1CC"})

        self.assertFalse(result["ok"])

    def test_structure_info_matches_chemscript_fields(self):
        result = self.backend.call("get_info", {"source": ASPIRIN})

        self.assertEqual(result["type"], "structure")
        self.assertEqual(result["formula"], "C9H8O4")
        self.assertEqual(result["name"], "2-acetoxybenzoic acid")
        self.assertEqual(result["atom_count"], 13)
        self.assertEqual(result["bond_count"], 13)
        self.assertTrue(result["inchi"].startswith("InChI=1S/C9H8O4"))

    def test_reaction_info_lists_components(self):
        self.chemdraw.smiles = "CC(=O)O.OCC>>CC(=O)OCC"
        result = self.backend.call("get_info", {"source": self.file("r.cdxml")})

        self.assertEqual(result["type"], "reaction")
        self.assertEqual([item["formula"] for item in result["reactants"]], ["C2H4O2", "C2H6O"])
        self.assertEqual([item["formula"] for item in result["products"]], ["C4H8O2"])

    def test_substructure_search_uses_rdkit_without_chemdraw(self):
        contains = self.backend.call("contains_substructure", {
            "target": ASPIRIN, "target_format": "smiles", "query": "c1ccccc1", "query_format": "smiles",
        })
        search = self.backend.call("substructure_search", {
            "target": "CCO", "target_format": "smiles", "query": "CO", "query_format": "smiles",
        })

        self.assertEqual(contains, {"ok": True, "contains": True})
        self.assertEqual(search["maps"], [{"C1": "C2", "O2": "O3"}])
        self.assertEqual(self.chemdraw.calls, [])

    def test_largest_common_substructure_maps_both_molecules(self):
        result = self.backend.call("largest_common_substructure", {
            "mol1": "c1ccccc1O", "mol1_format": "smiles", "mol2": "Cc1ccccc1", "mol2_format": "smiles",
        })

        self.assertEqual(result["common_atom_count"], 6)
        self.assertEqual({entry["mol1"][0] for entry in result["atom_map"]}, {"C"})

    def test_reaction_smiles_are_split_into_components(self):
        result = self.backend.call("load_reaction", {
            "source": "CC(=O)O.OCC>>CC(=O)OCC", "format": "smiles", "include_cdxml": False,
        })

        self.assertTrue(result["ok"])
        self.assertEqual(len(result["reactants"]), 2)
        self.assertEqual(result["products"][0]["smiles"], "CCOC(C)=O")
        self.assertEqual(result["formula"], "C2H4O2 + C2H6O >> C4H8O2")

    def test_overlay_moves_matched_atoms_onto_the_reference(self):
        result = self.backend.call("overlay", {"source": "CO", "target": TWO_ATOM_CDXML})

        self.assertTrue(result["success"])
        points = re.findall(r'<n\b[^>]*\bp="([^"]+)"', result["aligned_cdxml"])
        coordinates = [tuple(round(float(value), 1) for value in point.split()) for point in points]
        self.assertEqual(coordinates[:2], [(100.0, 200.0), (114.4, 200.0)])

    def test_substructure_align_keeps_target_coordinates(self):
        result = self.backend.call("substructure_align", {"query": "O", "target": TWO_ATOM_CDXML})

        self.assertTrue(result["contains"])
        target = Chem.MolFromMolBlock(result["target_mol"])
        self.assertEqual([atom.GetSymbol() for atom in target.GetAtoms()], ["C", "O"])
        self.assertIn('p="114.40 200.00"', result["target_cdxml"])

    def test_convert_saves_through_chemdraw(self):
        output = self.root / "out.cdx"
        result = self.backend.call("convert", {"input": self.file("a.cdxml"), "output": str(output)})

        self.assertEqual(result, {"ok": True, "type": "structure", "formula": "C9H8O4"})
        self.assertTrue(output.is_file())
        self.assertIn("ChemDraw", self.steps())

    def test_close_releases_chemdraw(self):
        self.backend.close()
        self.assertTrue(self.chemdraw.closed)


class StructureFileTests(unittest.TestCase):
    def test_elements_outside_the_common_table_keep_their_identity(self):
        # The decomposer names astatine probes; a silent carbon would rename the molecule.
        for smiles in ("[At]c1ccccc1", "[Sn](C)(C)(C)c1ccccc1", "O=[Ge]=O"):
            mol = Chem.MolFromSmiles(smiles)
            rdDepictor.Compute2DCoords(mol)
            cdxml = chemscript_mac.rdkit_to_cdxml(mol)
            for atom in mol.GetAtoms():
                if atom.GetAtomicNum() != 6:
                    self.assertIn(f'Element="{atom.GetAtomicNum()}"', cdxml, smiles)


class AcsStyleTests(unittest.TestCase):
    def test_rescaling_touches_only_coordinate_attributes(self):
        cdxml = (
            '<CDXML BondLength="30" ChemPropCritTemp="Critical Temp: "><page>'
            '<n id="1" p="60 30"/></page></CDXML>'
        )

        styled = chemscript_bridge._inject_acs_style(cdxml)

        self.assertIn('ChemPropCritTemp="Critical Temp: "', styled)
        self.assertIn('p="28.80 14.40"', styled)


class BridgeOnMacTests(unittest.TestCase):
    def setUp(self):
        chemscript_mac._shared = None
        self.addCleanup(setattr, chemscript_mac, "_shared", None)

    def test_bridges_in_one_process_share_one_chemdraw(self):
        # A second session would take the first one's ChemDraw for the user's
        # and refuse name conversion (chemdraw_in_use).
        with mock.patch.object(mac_automation, "is_macos", return_value=True), \
                mock.patch.object(mac_automation, "find_application", return_value=Path("/Applications/ChemDraw.app")), \
                mock.patch.object(chemscript_mac.mac_automation, "MacChemDrawSession",
                                  side_effect=lambda **_kw: FakeChemDraw()) as sessions:
            first = chemscript_bridge.ChemScriptBridge()
            second = chemscript_bridge.ChemScriptBridge()

        self.assertIs(first._mac, second._mac)
        self.assertEqual(sessions.call_count, 1)

    def test_bridge_uses_the_macos_backend_without_windows_python(self):
        fake = FakeChemDraw()
        with mock.patch.object(mac_automation, "is_macos", return_value=True), \
                mock.patch.object(mac_automation, "find_application", return_value=Path("/Applications/ChemDraw.app")), \
                mock.patch.object(chemscript_mac.mac_automation, "MacChemDrawSession", return_value=fake), \
                mock.patch.object(chemscript_bridge, "_find_python_for_chemscript") as windows_python:
            bridge = chemscript_bridge.ChemScriptBridge()
            formula = bridge.get_formula(ASPIRIN)
            bridge.close()

        windows_python.assert_not_called()
        self.assertEqual(formula, "C9H8O4")
        self.assertTrue(fake.closed)

    def test_bridge_reports_missing_chemdraw_for_macos(self):
        with mock.patch.object(mac_automation, "is_macos", return_value=True), \
                mock.patch.object(mac_automation, "find_application", return_value=None):
            with self.assertRaisesRegex(RuntimeError, "ChemDraw for macOS"):
                chemscript_bridge.ChemScriptBridge()


if __name__ == "__main__":
    unittest.main()
