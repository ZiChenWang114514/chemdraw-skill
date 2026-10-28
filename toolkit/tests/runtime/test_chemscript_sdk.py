from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from cdxml_toolkit.mcp_runtime import chemscript_sdk
from cdxml_toolkit.mcp_runtime import chemscript_sdk_runtime
class ChemScriptSdkTests(unittest.TestCase):
    def test_catalog_returns_complete_coverage_summary_without_importing_sdk(self):
        runtime_result = {
            "ok": True,
            "assembly": "CambridgeSoft.ChemScript, Version=22.0.0.0",
            "coverage": {
                "public_types_discovered": 85,
                "public_types_catalogued": 85,
                "public_members_discovered": 3029,
                "public_members_catalogued": 3029,
                "catalog_percent": 100.0,
                "eligible_members": 901,
                "eligible_members_with_execution_path": 901,
                "execution_path_percent": 100.0,
                "interop_infrastructure_members": 2128,
            },
            "members": [{"type": "StructureData", "name": "Formula"}],
            "page": {"offset": 0, "limit": 100, "returned": 1, "matched": 1},
        }
        with mock.patch.object(
            chemscript_sdk, "_invoke_runtime", return_value=runtime_result
        ):
            result = chemscript_sdk.inspect_chemscript_sdk(query="Formula")

        self.assertTrue(result["ok"])
        self.assertEqual(result["outputs"]["coverage"]["catalog_percent"], 100.0)
        self.assertEqual(
            result["outputs"]["coverage"]["execution_path_percent"], 100.0
        )
        self.assertEqual(result["metadata"]["network_used"], False)

    def test_catalog_can_publish_a_full_json_file_without_overwrite(self):
        runtime_result = {
            "ok": True,
            "assembly": "ChemScript 22",
            "coverage": {"catalog_percent": 100.0},
            "members": [{"type": "StructureData", "name": "Formula"}],
            "page": {"offset": 0, "limit": 0, "returned": 1, "matched": 1},
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "catalog.json"
            with mock.patch.object(
                chemscript_sdk, "_invoke_runtime", return_value=runtime_result
            ):
                result = chemscript_sdk.inspect_chemscript_sdk(
                    output_path=str(output)
                )
            self.assertTrue(output.is_file())
            self.assertEqual(json.loads(output.read_text(encoding="utf-8")), runtime_result)
            self.assertEqual(result["outputs"]["catalog_json"], str(output.resolve()))
            with self.assertRaisesRegex(ValueError, "overwrite"):
                chemscript_sdk.inspect_chemscript_sdk(output_path=str(output))

    def test_program_validation_covers_all_supported_operation_kinds(self):
        program = [
            {"op": "construct", "type": "Point", "args": [0, 0], "as": "point"},
            {
                "op": "call_static",
                "type": "StructureData",
                "member": "LoadData",
                "args": ["CCO", "chemical/x-smiles"],
                "as": "mol",
            },
            {"op": "call", "target": "mol", "member": "Formula", "as": "formula"},
            {"op": "get", "target": "mol", "member": "ExactMass", "as": "mass"},
            {"op": "set", "target": "point", "member": "x", "value": 1.0},
            {"op": "get_index", "target": "items", "index": 0, "as": "first"},
            {"op": "set_index", "target": "items", "index": 0, "value": 2},
            {"op": "iterate", "target": "items", "as": "values"},
            {"op": "dispose", "target": "mol"},
        ]
        normalized = chemscript_sdk_runtime.validate_program(program)
        self.assertEqual([step["op"] for step in normalized], [step["op"] for step in program])

    def test_program_rejects_unknown_ops_alias_reuse_and_implicit_file_io(self):
        with self.assertRaisesRegex(ValueError, "operation"):
            chemscript_sdk_runtime.validate_program([{"op": "eval", "code": "1+1"}])
        with self.assertRaisesRegex(ValueError, "alias"):
            chemscript_sdk_runtime.validate_program(
                [
                    {"op": "construct", "type": "Point", "as": "same"},
                    {"op": "construct", "type": "Point", "as": "same"},
                ]
            )
        with self.assertRaisesRegex(ValueError, "file I/O"):
            chemscript_sdk_runtime.validate_program(
                [
                    {
                        "op": "call_static",
                        "type": "StructureData",
                        "member": "LoadFile",
                        "args": ["input.cdx"],
                    }
                ],
                allow_file_io=False,
            )
        with self.assertRaisesRegex(ValueError, "file I/O"):
            chemscript_sdk_runtime.validate_program(
                [
                    {
                        "op": "construct",
                        "type": "SDFileWriter",
                        "args": ["output.sdf"],
                    }
                ],
                allow_file_io=False,
            )

    def test_program_rejects_interop_pointer_members_by_default(self):
        with self.assertRaisesRegex(ValueError, "interop"):
            chemscript_sdk_runtime.validate_program(
                [
                    {
                        "op": "call_static",
                        "type": "StructureData",
                        "member": "getCPtr",
                        "args": [{"$ref": "mol"}],
                    }
                ],
                allow_unsafe_interop=False,
            )

    def test_execute_returns_structured_program_results(self):
        runtime_result = {
            "ok": True,
            "assembly": "ChemScript 22",
            "results": [
                {"step": 0, "op": "call_static", "value": {"$ref": "mol", "$type": "StructureData"}},
                {"step": 1, "op": "call", "value": "C2H6O"},
            ],
            "disposed": 1,
        }
        program = [
            {
                "op": "call_static",
                "type": "StructureData",
                "member": "LoadData",
                "args": ["CCO", "chemical/x-smiles"],
                "as": "mol",
            },
            {"op": "call", "target": "mol", "member": "Formula"},
        ]
        with mock.patch.object(
            chemscript_sdk, "_invoke_runtime", return_value=runtime_result
        ) as invoke:
            result = chemscript_sdk.execute_chemscript_sdk(program)

        self.assertTrue(result["ok"])
        self.assertEqual(result["outputs"]["results"][1]["value"], "C2H6O")
        self.assertFalse(invoke.call_args.args[0]["allow_file_io"])
        self.assertFalse(invoke.call_args.args[0]["allow_unsafe_interop"])


    def test_sdk_programs_run_in_the_toolkit_python_on_macos(self):
        completed = mock.Mock(returncode=0, stdout="", stderr="")

        def fake_run(command, **kwargs):
            response = Path(command[command.index("--response-file") + 1])
            response.write_text(json.dumps({"ok": True, "assembly": "emulation"}), encoding="utf-8")
            return completed

        with mock.patch.object(chemscript_sdk.sys, "platform", "darwin"), \
                mock.patch.dict(chemscript_sdk.os.environ, {"CHEMSCRIPT_PYTHON": "/elsewhere/python.exe"}), \
                mock.patch.object(chemscript_sdk.subprocess, "run", side_effect=fake_run) as run:
            chemscript_sdk._invoke_runtime({"action": "catalog"})

        self.assertEqual(run.call_args.args[0][0], chemscript_sdk.sys.executable)

    def test_a_refused_program_reaches_the_caller_as_a_value_error_with_its_reason(self):
        # The isolated runtime marks request mistakes; the caller must see them as input errors
        # (invalid_input with the reason), not as a failed tool.
        def fake_run(command, **kwargs):
            response = Path(command[command.index("--response-file") + 1])
            response.write_text(json.dumps({
                "ok": False,
                "error": {"code": "invalid_sdk_request", "message": "GetType is a .NET reflection member"},
            }), encoding="utf-8")
            return mock.Mock(returncode=2, stdout="", stderr="")

        # The error mapping is the same wherever the SDK runs; pin a supported platform so the
        # test also runs on Linux hosts, which refuse SDK programs before starting the runtime.
        with mock.patch.object(chemscript_sdk.sys, "platform", "darwin"), \
                mock.patch.object(chemscript_sdk.subprocess, "run", side_effect=fake_run):
            with self.assertRaisesRegex(ValueError, "reflection member"):
                chemscript_sdk._invoke_runtime({"action": "catalog"})

    def test_sdk_programs_are_refused_where_neither_sdk_nor_emulation_exists(self):
        with mock.patch.object(chemscript_sdk.sys, "platform", "linux"), \
                mock.patch.object(chemscript_sdk.subprocess, "run") as run:
            with self.assertRaises(RuntimeError) as raised:
                chemscript_sdk.inspect_chemscript_sdk(query="Formula")

        self.assertEqual(raised.exception.error_code, "chemscript_sdk_unavailable")
        run.assert_not_called()


class FakeBackend:
    """Canned answers of the macOS ChemScript backend (no ChemDraw)."""

    def __init__(self):
        self.calls = []

    def call(self, command, args):
        self.calls.append((command, args))
        if command == "write_data":
            if args["source"] == "not a molecule":
                return {"ok": False, "error": "Could not load"}
            return {"ok": True, "data": "<CDXML/>" if args["target_format"] == "text/xml" else "CCO"}
        if command == "get_formula":
            return {"ok": True, "formula": "C2H6O"}
        if command == "substructure_search":
            return {"ok": True, "contains": True, "maps": [{"C1": "C2", "O2": "O3"}]}
        if command == "largest_common_substructure":
            return {"ok": True, "atom_map": [{"common": "C1", "mol1": "C1", "mol2": "C4"}]}
        if command == "load_reaction":
            return {"ok": True, "formula": "C2H6O >> C2H4O",
                    "reactants": [{"smiles": "CCO", "formula": "C2H6O"}],
                    "products": [{"smiles": "CC=O", "formula": "C2H4O"}]}
        raise AssertionError(command)


class MacEmulationTests(unittest.TestCase):
    def setUp(self):
        from cdxml_toolkit.mcp_runtime import chemscript_sdk_mac

        self.emulation = chemscript_sdk_mac
        self.backend = FakeBackend()
        patch = mock.patch.object(chemscript_sdk_mac, "_backend", return_value=self.backend)
        patch.start()
        self.addCleanup(patch.stop)
        self.runtime = chemscript_sdk_mac.MacSdkRuntime()

    def run_program(self, program, **request):
        return chemscript_sdk_runtime.execute_program(self.runtime, {"program": program, **request})

    def test_structure_programs_written_for_windows_run_unchanged(self):
        result = self.run_program([
            {"op": "call_static", "type": "CambridgeSoft.ChemScript16.StructureData",
             "member": "LoadData", "args": ["CCO", "chemical/x-smiles"], "as": "mol"},
            {"op": "call", "target": "mol", "member": "Formula"},
            {"op": "call", "target": "mol", "member": "WriteData", "args": ["text/xml"]},
        ])

        self.assertTrue(result["ok"])
        self.assertIn("macOS emulation", result["assembly"])
        self.assertEqual(result["results"][0]["value"]["$type"], "CambridgeSoft.ChemScript16.StructureData")
        self.assertEqual(result["results"][1]["value"], "C2H6O")
        self.assertEqual(result["results"][2]["value"], "<CDXML/>")

    def test_atom_maps_serialize_like_dotnet_dictionaries(self):
        result = self.run_program([
            {"op": "call_static", "type": "StructureData", "member": "LoadData", "args": ["CO"], "as": "query"},
            {"op": "call_static", "type": "StructureData", "member": "LoadData", "args": ["CCO"], "as": "target"},
            {"op": "call", "target": "query", "member": "AtomByAtomSearch", "args": [{"$ref": "target"}]},
            {"op": "call_static", "type": "LargestCommonSubstructure", "member": "Compute",
             "args": [{"$ref": "query"}, {"$ref": "target"}], "as": "lcs"},
            {"op": "call", "target": "lcs", "member": "AtomMapM2"},
        ])

        self.assertEqual(result["results"][2]["value"], [[
            {"key": {"$type": "CambridgeSoft.ChemScript16.Atom", "display": "C1"},
             "value": {"$type": "CambridgeSoft.ChemScript16.Atom", "display": "C2"}},
            {"key": {"$type": "CambridgeSoft.ChemScript16.Atom", "display": "O2"},
             "value": {"$type": "CambridgeSoft.ChemScript16.Atom", "display": "O3"}},
        ]])
        self.assertEqual(result["results"][4]["value"][0]["value"]["display"], "C4")

    def test_reactions_expose_reactants_and_products(self):
        result = self.run_program([
            {"op": "call_static", "type": "ReactionData", "member": "LoadData", "args": ["CCO>>CC=O"], "as": "rxn"},
            {"op": "get", "target": "rxn", "member": "Products", "as": "products"},
            {"op": "get_index", "target": "products", "index": 0, "as": "product"},
            {"op": "call", "target": "product", "member": "Formula"},
        ])

        self.assertEqual(result["results"][3]["value"], "C2H6O")

    def test_unloadable_data_returns_null_like_chemscript(self):
        result = self.run_program([
            {"op": "call_static", "type": "StructureData", "member": "LoadData", "args": ["not a molecule"]},
        ])

        self.assertIsNone(result["results"][0]["value"])

    def test_only_emulated_public_members_are_reachable(self):
        refused = [
            [{"op": "call_static", "type": "StructureData", "member": "_valid", "args": ["C", None]}],
            [{"op": "call_static", "type": "StructureData", "member": "__init__", "args": []}],
            [{"op": "call_static", "type": "System.IO.File", "member": "Delete", "args": ["x"]}],
            [{"op": "call_static", "type": "StructureData", "member": "LoadData", "args": ["CCO"], "as": "mol"},
             {"op": "get", "target": "mol", "member": "__class__"}],
            [{"op": "call_static", "type": "StructureData", "member": "LoadData", "args": ["CCO"], "as": "mol"},
             {"op": "set", "target": "mol", "member": "_data", "value": "C"}],
            [{"op": "call_static", "type": "StructureData", "member": "LoadData", "args": ["CCO"], "as": "mol"},
             {"op": "call", "target": "mol", "member": "Formula", "as": "text"},
             {"op": "call", "target": "text", "member": "format"}],
        ]
        for program in refused:
            with self.subTest(program=program[-1]):
                with self.assertRaises(ValueError):
                    self.run_program(program)

    def test_file_writes_still_need_permission(self):
        with tempfile.TemporaryDirectory() as temp:
            existing = Path(temp) / "out.smi"
            existing.write_text("old", encoding="utf-8")
            with self.assertRaises(ValueError):
                self.run_program([
                    {"op": "call_static", "type": "StructureData", "member": "LoadData", "args": ["CCO"], "as": "mol"},
                    {"op": "call", "target": "mol", "member": "WriteFile", "args": [str(existing)]},
                ], allow_file_io=True)
            self.assertEqual(existing.read_text(encoding="utf-8"), "old")

    def test_data_naming_a_file_is_never_read_without_file_permission(self):
        with tempfile.TemporaryDirectory() as temp:
            secret = Path(temp) / "secret.mol"
            secret.write_text("private", encoding="utf-8")
            named_like_smiles = Path(temp) / "CCO"
            named_like_smiles.write_text("private", encoding="utf-8")
            cwd = os.getcwd()
            os.chdir(temp)
            try:
                result = self.run_program([
                    {"op": "call_static", "type": "StructureData", "member": "LoadData", "args": [str(secret)]},
                    {"op": "call_static", "type": "ReactionData", "member": "LoadData", "args": [str(secret)]},
                    {"op": "call_static", "type": "StructureData", "member": "LoadData", "args": ["CCO"], "as": "mol"},
                ])
            finally:
                os.chdir(cwd)

        self.assertIsNone(result["results"][0]["value"])
        self.assertIsNone(result["results"][1]["value"])
        sources = [str(args.get("source")) for _command, args in self.backend.calls]
        self.assertNotIn(str(secret), sources)
        self.assertNotIn("CCO", sources)  # the SMILES reaches the backend as content, not a path
        self.assertEqual(result["results"][2]["value"]["$type"], "CambridgeSoft.ChemScript16.StructureData")

    def test_catalog_lists_exactly_the_emulated_members(self):
        result = chemscript_sdk_runtime.catalog_sdk(self.runtime, {"query": "AtomByAtomSearch"})

        self.assertTrue(result["ok"])
        self.assertIn("macOS emulation", result["assembly"])
        self.assertEqual([item["name"] for item in result["members"]], ["AtomByAtomSearch"])
        self.assertEqual(self.backend.calls, [])


class _NetType:
    def __init__(self, full_name):
        self.FullName = full_name


class _NetObject:
    """Stands in for a Python.NET object: a .NET type name plus a few members."""

    def __init__(self, full_name, **members):
        self._type = _NetType(full_name)
        self.__dict__.update(members)

    def GetType(self):
        return self._type


class _WindowsLikeRuntime:
    """The Windows runtime has no check_member of its own (unlike the macOS emulation)."""

    assembly = _NetType("CambridgeSoft.ChemScript, Version=22.0.0.0")

    def __init__(self, written):
        self.written = written

    def reflection_type(self, name):
        return _NetType(f"CambridgeSoft.ChemScript.{name}")

    def python_type(self, name):
        written = self.written

        class StructureData:
            @staticmethod
            def LoadData(text, mime):
                return _NetObject("CambridgeSoft.ChemScript.StructureData", Formula="C2H6O",
                                  WriteFile=lambda *args: written.append(args) or True)
        return StructureData

    def member_is_interop(self, reflection_type, member):
        return False

    def resolve_argument(self, item, aliases, *, unsafe=False):
        return aliases[item["$ref"]] if isinstance(item, dict) and "$ref" in item else item


class WindowsSdkMemberPolicyTests(unittest.TestCase):
    load = {"op": "call_static", "type": "StructureData", "member": "LoadData",
            "args": ["CCO", "chemical/x-smiles"], "as": "mol"}

    def run_program(self, program, written=None, **request):
        runtime = _WindowsLikeRuntime([] if written is None else written)
        return chemscript_sdk_runtime.execute_program(runtime, {"program": program, **request})

    def test_ordinary_sdk_members_still_work(self):
        result = self.run_program([self.load, {"op": "get", "target": "mol", "member": "Formula"}])
        self.assertTrue(result["ok"])
        self.assertEqual(result["results"][1]["value"], "C2H6O")

    def test_reflection_members_are_refused_on_sdk_objects(self):
        for member in ("GetType", "Invoke", "GetMethod", "InvokeMember"):
            with self.assertRaisesRegex(ValueError, "reflection"):
                self.run_program([self.load, {"op": "call", "target": "mol", "member": member, "args": []}])

    def test_members_of_non_sdk_objects_are_refused(self):
        with self.assertRaisesRegex(ValueError, "not part of the ChemScript SDK"):
            self.run_program([self.load, {"op": "get", "target": "mol", "member": "Formula", "as": "f"},
                              {"op": "get", "target": "f", "member": "Length"}])

    def test_overwrite_check_covers_every_path_argument(self):
        with tempfile.TemporaryDirectory() as tmp:
            existing = Path(tmp) / "out.cdxml"
            existing.write_text("<CDXML/>")
            written = []
            with self.assertRaisesRegex(ValueError, "allow_overwrite"):
                self.run_program([self.load, {"op": "call", "target": "mol", "member": "WriteFile",
                                              "args": ["chemical/x-cdxml", str(existing)]}],
                                 written, allow_file_io=True)
            self.assertEqual(written, [])


if __name__ == "__main__":
    unittest.main()
