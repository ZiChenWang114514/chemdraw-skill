from __future__ import annotations

import importlib.metadata
from pathlib import Path
import socket
import subprocess
import tempfile
import unittest
from unittest import mock

from cdxml_toolkit.mcp_runtime import runtime_diagnostics
class RuntimeDiagnosticsTests(unittest.TestCase):
    def test_probe_stage_contains_secondary_timeout_during_teardown(self):
        process = mock.Mock()
        process.pid = 987
        process.communicate.side_effect = [
            subprocess.TimeoutExpired(["probe"], 1),
            subprocess.TimeoutExpired(["probe"], 1),
        ]
        with mock.patch.object(
            runtime_diagnostics, "snapshot_automation_processes", return_value={}
        ), mock.patch.object(
            runtime_diagnostics.subprocess, "Popen", return_value=process
        ), mock.patch.object(
            runtime_diagnostics, "_assign_kill_job", return_value=("job", "api", "jobapi")
        ), mock.patch.object(
            runtime_diagnostics, "_terminate_process_tree"
        ) as terminate, mock.patch.object(
            runtime_diagnostics, "_audit_stage_processes", return_value={"status": "confirmed"}
        ):
            result = runtime_diagnostics._run_probe_stage("native", 1)

        self.assertEqual(result["error_code"], "native_probe_timeout")
        self.assertTrue(result["timed_out"])
        self.assertIn("deadline", terminate.call_args.kwargs)

    def test_requested_probes_use_stage_specific_hard_timeouts(self):
        stages = {
            "chemscript": {
                "status": "available",
                "detail": "ChemScript bridge OK",
                "cleanup": {"status": "confirmed"},
            },
            "native": {
                "status": "available",
                "png_bytes": 123,
                "png_dimensions": [10, 11],
                "cleanup": {"status": "confirmed"},
            },
            "pptx": {
                "status": "available",
                "objects": 1,
                "cleanup": {"status": "confirmed"},
            },
            "docx": {
                "status": "available",
                "objects": 1,
                "cleanup": {"status": "confirmed"},
            },
        }

        with mock.patch.object(
            runtime_diagnostics,
            "_run_probe_stage",
            side_effect=lambda stage, timeout: stages[stage],
        ) as runner:
            result = runtime_diagnostics.diagnose_runtime(
                run_native_probe=True, run_office_probe=True
            )

        self.assertTrue(result["ok"])
        self.assertEqual(
            runner.call_args_list,
            [
                mock.call("chemscript", 30),
                mock.call("native", 75),
                mock.call("pptx", 60),
                mock.call("docx", 60),
            ],
        )
        self.assertEqual(result["metadata"]["probe_hard_limit_seconds"], 240)

    def test_cleanup_unconfirmed_stops_later_office_probe(self):
        chemscript = {
            "status": "available",
            "detail": "ChemScript bridge OK",
            "cleanup": {"status": "confirmed"},
        }
        native = {
            "status": "available",
            "cleanup": {"status": "confirmed"},
        }
        pptx = {
            "status": "missing",
            "detail": "probe timed out",
            "timed_out": True,
            "cleanup": {"status": "unconfirmed", "unknown_pids": [4321]},
        }
        with mock.patch.object(
            runtime_diagnostics,
            "_run_probe_stage",
            side_effect=[chemscript, native, pptx],
        ) as runner:
            result = runtime_diagnostics.diagnose_runtime(
                run_native_probe=True, run_office_probe=True
            )

        self.assertFalse(result["ok"])
        runner.assert_has_calls(
            [
                mock.call("chemscript", 30),
                mock.call("native", 75),
                mock.call("pptx", 60),
            ]
        )
        self.assertEqual(runner.call_count, 3)
        docx = result["outputs"]["capabilities"]["office_probe"]["stages"]["docx"]
        self.assertEqual(docx["status"], "not_run")
        self.assertEqual(docx["reason"], "cleanup_unconfirmed")

    def test_default_diagnostics_are_offline_read_only_and_do_not_run_probes(self):
        with tempfile.TemporaryDirectory() as temp_dir, mock.patch.object(
            runtime_diagnostics.Path, "home", return_value=Path(temp_dir)
        ), mock.patch.object(
            runtime_diagnostics, "_native_probe"
        ) as native_probe, mock.patch.object(
            runtime_diagnostics, "_chemscript_probe"
        ) as chemscript_probe, mock.patch.object(
            runtime_diagnostics, "_office_probe"
        ) as office_probe, mock.patch.object(
            socket, "create_connection", side_effect=AssertionError("network forbidden")
        ):
            result = runtime_diagnostics.diagnose_runtime()

        self.assertTrue(result["ok"])
        self.assertTrue(result["metadata"]["read_only"])
        self.assertFalse(result["metadata"]["network_used"])
        self.assertEqual(
            result["outputs"]["capabilities"]["cdxml_toolkit"]["version"],
            __import__("cdxml_toolkit").__version__,
        )
        self.assertEqual(
            result["outputs"]["capabilities"]["mcp_sdk"]["version"],
            importlib.metadata.version("mcp"),
        )
        self.assertEqual(result["metadata"]["tool_count"], 38)
        self.assertEqual(
            result["outputs"]["capabilities"]["tool_registry"]["status"],
            "available",
        )
        self.assertNotIn("native_probe", result["outputs"]["capabilities"])
        self.assertNotIn("office_probe", result["outputs"]["capabilities"])
        native_probe.assert_not_called()
        chemscript_probe.assert_not_called()
        office_probe.assert_not_called()

    def test_requested_probes_are_reported_in_capability_matrix(self):
        chemscript = {
            "status": "available",
            "detail": "ChemScript bridge OK",
            "cleanup": {"status": "confirmed"},
        }
        native = {
            "status": "available",
            "png_bytes": 123,
            "png_dimensions": [10, 11],
            "cleanup": {"status": "confirmed"},
        }
        pptx = {"status": "available", "objects": 1, "cleanup": {"status": "confirmed"}}
        docx = {"status": "available", "objects": 1, "cleanup": {"status": "confirmed"}}
        with mock.patch.object(
            runtime_diagnostics,
            "_run_probe_stage",
            side_effect=[chemscript, native, pptx, docx],
        ) as runner:
            result = runtime_diagnostics.diagnose_runtime(
                run_native_probe=True, run_office_probe=True
            )

        self.assertTrue(result["ok"])
        capabilities = result["outputs"]["capabilities"]
        self.assertEqual(capabilities["chemscript_probe"], chemscript)
        self.assertEqual(capabilities["native_probe"], native)
        self.assertEqual(capabilities["office_probe"]["pptx_objects"], 1)
        self.assertEqual(capabilities["office_probe"]["docx_objects"], 1)
        self.assertEqual(capabilities["chemscript"]["status"], "available")
        self.assertEqual(capabilities["office"]["status"], "available")
        self.assertFalse(result["metadata"]["read_only"])
        self.assertEqual(runner.call_count, 4)

    def test_native_timeout_does_not_hide_successful_chemscript_probe(self):
        chemscript = {
            "status": "available",
            "detail": "ChemScript bridge OK",
            "cleanup": {"status": "confirmed"},
        }
        native = {
            "status": "missing",
            "detail": "native probe exceeded 75 seconds",
            "cleanup": {"status": "confirmed"},
        }
        with mock.patch.object(
            runtime_diagnostics, "_run_probe_stage", side_effect=[chemscript, native]
        ):
            result = runtime_diagnostics.diagnose_runtime(run_native_probe=True)

        self.assertFalse(result["ok"])
        capabilities = result["outputs"]["capabilities"]
        self.assertEqual(capabilities["chemscript"]["status"], "available")
        self.assertEqual(capabilities["native_probe"]["status"], "missing")

    def test_requested_probe_failure_makes_diagnostic_unsuccessful(self):
        with mock.patch.object(
            runtime_diagnostics,
            "_run_probe_stage",
            return_value={"status": "missing", "detail": "ChemDraw unavailable"},
        ):
            result = runtime_diagnostics.diagnose_runtime(run_native_probe=True)

        self.assertFalse(result["ok"])
        self.assertTrue(
            any("ChemDraw unavailable" in warning for warning in result["warnings"])
        )


if __name__ == "__main__":
    unittest.main()
