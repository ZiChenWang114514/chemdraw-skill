from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest import mock

from cdxml_toolkit.mcp_runtime import mcp_server
from cdxml_toolkit.mcp_runtime import native_io
from cdxml_toolkit.mcp_runtime import process_control
from cdxml_toolkit.mcp_runtime import resource_lock
from cdxml_toolkit.mcp_runtime import tool_registry
from cdxml_toolkit.mcp_runtime import tool_worker
def write_valid_office(path: str | Path) -> None:
    from cdxml_toolkit.office.ole_embedder import build_ole_compound_file, build_pptx

    ole_data = build_ole_compound_file(b"VjCD0100" + (b"\0" * 5000))
    build_pptx(
        [
            {
                "ole_data": ole_data,
                "emf_data": b"EMF",
                "width_emu": 914400,
                "height_emu": 914400,
                "name": "fixture",
            }
        ],
        str(path),
    )


class WorkerRuntimeTests(unittest.TestCase):
    def test_worker_preserves_structured_native_error_code_and_error_id(self):
        error = native_io.NativeIOError(
            "native_saveas_silent_failure",
            "Native automation returned without creating its output",
        )
        with mock.patch.object(tool_worker, "_failure_log", return_value="abc123"):
            envelope, return_code = tool_worker._error_envelope(error)

        self.assertEqual(return_code, 1)
        self.assertEqual(
            envelope["error"]["code"], "native_saveas_silent_failure"
        )
        self.assertEqual(envelope["error"]["id"], "abc123")
        self.assertLessEqual(len(envelope["error"]["message"]), 1000)

    def test_worker_environment_preserves_runtime_configuration_and_filters_secrets(self):
        configured = {
            "CHEMSCRIPT_DLL_DIR": r"C:\ChemScript\bin",
            "CHEMSCRIPT_ASSEMBLY": "CambridgeSoft.ChemScript23",
            "CONDA_PREFIX": r"C:\conda\envs\cdxml",
            "JAVA_HOME": r"C:\Java\jdk",
            "CHEMDRAW_EXE": r"C:\ChemDraw.exe",
            "COMPUTERNAME": "CHEM-WORKSTATION",
            "USERNAME": "chemist",
            "CommonProgramFiles": r"C:\Program Files\Common Files",
            "CHEMDRAW_MCP_HTTP_API_KEY": "must-not-cross-worker-process",
            "ANTHROPIC_AUTH_TOKEN": "must-not-cross-worker-boundary",
        }
        with mock.patch.dict(os.environ, configured, clear=False):
            environment = mcp_server._worker_environment()
        normalized_environment = {
            key.upper(): value for key, value in environment.items()
        }

        for key in (
            "CHEMSCRIPT_DLL_DIR",
            "CHEMSCRIPT_ASSEMBLY",
            "CONDA_PREFIX",
            "JAVA_HOME",
            "CHEMDRAW_EXE",
            "COMPUTERNAME",
            "USERNAME",
            "CommonProgramFiles",
        ):
            self.assertEqual(normalized_environment[key.upper()], configured[key])
        self.assertNotIn("ANTHROPIC_AUTH_TOKEN", normalized_environment)
        self.assertNotIn("CHEMDRAW_MCP_HTTP_API_KEY", normalized_environment)

    def test_registry_marks_native_chemdraw_tools_only(self):
        from cdxml_toolkit.mcp_runtime import tool_registry
        specs = tool_registry.build_registry()
        for name in (
            "parse_reaction",
            "convert_cdx_cdxml",
            "render_to_png",
            "extract_cdxml_from_office",
            "embed_cdxml_in_office",
            "clean_scheme_layout",
            "merge_reaction_schemes",
            "polish_reaction_scheme",
            "render_cdxml_files",
            "fill_office_template",
            "batch_embed_cdxml_in_office",
            "inspect_chemdraw_objects_in_office",
            "replace_chemdraw_objects_in_office",
            "diagnose_runtime",
        ):
            self.assertEqual(specs[name].resource_class, "chemdraw_com", name)
        for name in ("resolve_name", "modify_molecule", "draw_molecule", "parse_scheme"):
            self.assertIsNone(specs[name].resource_class, name)

    @unittest.skipUnless(os.name == "nt", "Windows named mutex behavior")
    def test_named_chemdraw_mutex_serializes_callers(self):
        first_entered = threading.Event()
        release_first = threading.Event()
        second_entered = threading.Event()

        def first():
            with resource_lock.native_resource_lock("chemdraw_com", 5):
                first_entered.set()
                release_first.wait(5)

        def second():
            first_entered.wait(5)
            with resource_lock.native_resource_lock("chemdraw_com", 5):
                second_entered.set()

        first_thread = threading.Thread(target=first)
        second_thread = threading.Thread(target=second)
        first_thread.start()
        second_thread.start()
        self.assertTrue(first_entered.wait(2))
        self.assertFalse(second_entered.wait(0.2))
        release_first.set()
        self.assertTrue(second_entered.wait(2))
        first_thread.join(2)
        second_thread.join(2)
        self.assertFalse(first_thread.is_alive())
        self.assertFalse(second_thread.is_alive())

    def test_worker_reports_resource_busy_without_diagnostic_log(self):
        error = resource_lock.ResourceBusyError("chemdraw_com", 2)
        with mock.patch("cdxml_toolkit.mcp_runtime.tool_worker._failure_log") as failure_log:
            envelope, return_code = tool_worker._error_envelope(error)
        self.assertEqual(return_code, 3)
        self.assertEqual(envelope["error"]["code"], "resource_busy")
        self.assertNotIn("id", envelope["error"])
        failure_log.assert_not_called()

    def test_resource_wait_finishes_before_parent_worker_timeout(self):
        self.assertEqual(tool_worker._resource_timeout(570), 565)
        self.assertEqual(tool_worker._resource_timeout(5), 1)
        self.assertEqual(tool_worker._resource_timeout(1), 1)

    def test_molecule_analysis_has_a_shorter_worker_timeout(self):
        registry = tool_registry.build_registry()

        self.assertEqual(registry["modify_molecule"].timeout_seconds, 90)

    def test_timeout_is_structured_and_terminates_worker_tree(self):
        process = mock.Mock()
        process.poll.return_value = None
        with mock.patch("cdxml_toolkit.mcp_runtime.mcp_server.subprocess.Popen", return_value=process), mock.patch(
            "cdxml_toolkit.mcp_runtime.mcp_server._monitor_process", return_value="timeout"
        ), mock.patch("cdxml_toolkit.mcp_runtime.mcp_server._terminate_process_tree") as terminate:
            result = mcp_server._run_worker("resolve_name", [], {}, timeout_seconds=2)
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "tool_timeout")
        self.assertEqual(result["metadata"]["timeout_seconds"], 2)
        terminate.assert_called_once()

    def test_worker_stages_request_instead_of_blocking_on_stdin(self):
        process = mock.Mock()
        process.poll.return_value = None
        with mock.patch("cdxml_toolkit.mcp_runtime.mcp_server.subprocess.Popen", return_value=process) as popen, mock.patch(
            "cdxml_toolkit.mcp_runtime.mcp_server._monitor_process", return_value="timeout"
        ), mock.patch("cdxml_toolkit.mcp_runtime.mcp_server._terminate_process_tree"):
            mcp_server._run_worker("resolve_name", ["aspirin"], {}, timeout_seconds=2)
        command = popen.call_args.args[0]
        self.assertIn("--request-file", command)
        self.assertEqual(popen.call_args.kwargs["stdin"], subprocess.DEVNULL)
        self.assertFalse(process.stdin.write.called)

    @unittest.skipUnless(os.name == "nt", "Windows-only process-tree fallback")
    def test_taskkill_uses_absolute_system_path(self):
        process = mock.Mock(pid=1234)
        process.poll.return_value = None
        with mock.patch("cdxml_toolkit.mcp_runtime.process_control.subprocess.run") as run:
            run.return_value.returncode = 0
            mcp_server._terminate_process_tree(process)
        taskkill = Path(run.call_args.args[0][0])
        expected = Path(os.environ["SystemRoot"]) / "System32" / "taskkill.exe"
        self.assertEqual(taskkill, expected)

    def test_worker_failure_uses_structured_stdout_not_stderr_logs(self):
        envelope = {
            "ok": False,
            "error": {"code": "tool_execution_failed", "message": "Tool execution failed", "id": "abc"},
        }
        with mock.patch(
            "cdxml_toolkit.mcp_runtime.mcp_server._execute_worker_process",
            return_value=(3, json.dumps(envelope).encode(), b"secret document log"),
        ):
            result = mcp_server._run_worker("resolve_name", [], {})
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "tool_execution_failed")
        self.assertNotIn("secret document log", json.dumps(result))

    def test_adapter_does_not_block_event_loop(self):
        async def fake_worker(name, args, kwargs, timeout_seconds=None):
            await asyncio.sleep(0.15)
            return {"ok": True, "result": "done", "metadata": {"tool": name}}

        async def run_two():
            def sample(value: str) -> str:
                return value

            adapted = mcp_server._adapt_tool("sample", sample)
            started = time.monotonic()
            self.assertEqual(await asyncio.gather(adapted("a"), adapted("b")), ["done", "done"])
            return time.monotonic() - started

        with mock.patch("cdxml_toolkit.mcp_runtime.mcp_server._run_worker_async", side_effect=fake_worker):
            elapsed = asyncio.run(run_two())
        self.assertLess(elapsed, 0.27)

    def test_worker_emits_error_envelope_on_stdout(self):
        worker = Path(tool_worker.__file__)
        completed = subprocess.run(
            [sys.executable, "-m", "cdxml_toolkit.mcp_runtime.tool_worker"],
            input=json.dumps({"tool": "definitely_missing", "args": [], "kwargs": {}}),
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertNotEqual(completed.returncode, 0)
        payload = json.loads(completed.stdout)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["error"]["code"], "unknown_tool")

    def test_registry_rejects_collisions_and_applies_official_override(self):
        from cdxml_toolkit.mcp_runtime import tool_registry
        specs = tool_registry.build_registry()
        self.assertIn("embed_cdxml_in_office", specs)
        self.assertEqual(
            specs["embed_cdxml_in_office"].function.__module__,
            "cdxml_toolkit.mcp_runtime.official_overrides",
        )
        self.assertIn("reject", specs["embed_cdxml_in_office"].description.lower())
        self.assertIn("standalone CDXML", specs["draw_molecule"].description)
        self.assertIn("no-overwrite", specs["draw_molecule"].description)
        self.assertEqual(
            {
                name
                for name, spec in specs.items()
                if spec.group == "official" and spec.function.__module__ == "cdxml_toolkit.mcp_runtime.official_overrides"
            },
            {
                "draw_molecule",
                "render_scheme",
                "parse_reaction",
                "parse_scheme",
                "convert_cdx_cdxml",
                "parse_analysis_file",
                "format_lab_entry",
                "extract_cdxml_from_office",
                "embed_cdxml_in_office",
                "render_to_png",
            },
        )
        with self.assertRaisesRegex(RuntimeError, "collision"):
            tool_registry._merge_named_tools(
                {"same": object()}, {"same": object()}, source="test"
            )

    def test_official_embed_override_rejects_existing_office_source(self):
        from cdxml_toolkit.mcp_runtime import official_overrides
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            cdxml = root / "scheme.cdxml"
            cdxml.write_text("<CDXML><page/></CDXML>", encoding="utf-8")
            office = root / "report.pptx"
            office.write_bytes(b"original-office-source")

            with mock.patch(
                "cdxml_toolkit.mcp_server.server.embed_cdxml_in_office",
            ) as upstream:
                result = official_overrides.embed_cdxml_in_office(
                    str(cdxml), str(office)
                )

            self.assertFalse(result["ok"])
            self.assertIn("existing", result["error"].lower())
            self.assertEqual(office.read_bytes(), b"original-office-source")
            upstream.assert_not_called()

    def test_official_embed_override_creates_valid_new_office_file(self):
        from cdxml_toolkit.mcp_runtime import official_overrides
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            cdxml = root / "scheme.cdxml"
            cdxml.write_text("<CDXML><page/></CDXML>", encoding="utf-8")
            office = root / "report.pptx"

            def fake_embed(_cdxml_path, output_path):
                write_valid_office(output_path)
                return {"ok": True, "output": str(output_path), "num_objects_embedded": 1}

            with mock.patch(
                "cdxml_toolkit.mcp_runtime.official_overrides._build_embedded_office",
                side_effect=fake_embed,
            ):
                result = official_overrides.embed_cdxml_in_office(str(cdxml), str(office))

            self.assertTrue(result["ok"])
            self.assertEqual(Path(result["output"]), office.resolve())
            self.assertTrue(office.is_file())


if __name__ == "__main__":
    unittest.main()
