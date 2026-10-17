from __future__ import annotations

import json
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


if __name__ == "__main__":
    unittest.main()
