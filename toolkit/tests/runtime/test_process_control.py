from __future__ import annotations

import json
from pathlib import Path
import subprocess
import unittest
from unittest import mock

try:
    from cdxml_toolkit.mcp_runtime import process_control
except ImportError:
    process_control = None


class AutomationProcessCleanupTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(process_control, "shared process control module is required")

    def test_cleanup_never_terminates_baseline_processes(self):
        before = {
            100: {"pid": 100, "parent_pid": 1, "name": "ChemDraw.exe", "command_line": "ChemDraw.exe"}
        }
        after = dict(before)
        with mock.patch.object(process_control, "terminate_pid") as terminate:
            result = process_control.cleanup_automation_processes(
                before, after, stage_pid=999
            )

        self.assertEqual(result["status"], "confirmed")
        terminate.assert_not_called()

    def test_cleanup_terminates_only_attributed_new_processes(self):
        after = {
            201: {
                "pid": 201,
                "parent_pid": 999,
                "name": "WINWORD.EXE",
                "command_line": "WINWORD.EXE",
            },
            202: {
                "pid": 202,
                "parent_pid": 4,
                "name": "ChemDraw.exe",
                "command_line": "ChemDraw.exe /Automation -Embedding",
            },
        }
        with mock.patch.object(
            process_control, "terminate_pid", return_value=True
        ) as terminate:
            result = process_control.cleanup_automation_processes(
                {}, after, stage_pid=999
            )

        self.assertEqual(result["status"], "unconfirmed")
        self.assertEqual(result["terminated_pids"], [201])
        self.assertEqual(result["unknown_pids"], [202])
        self.assertEqual([call.args[0] for call in terminate.call_args_list], [201])

    def test_normal_job_close_disarms_kill_on_close(self):
        win32api = mock.Mock()
        win32job = mock.Mock()
        win32job.JobObjectExtendedLimitInformation = 9
        win32job.JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x2000
        win32job.QueryInformationJobObject.return_value = {
            "BasicLimitInformation": {"LimitFlags": 0x2000}
        }

        closed = process_control._close_job(("job", win32api, win32job))

        self.assertTrue(closed)
        information = win32job.SetInformationJobObject.call_args.args[2]
        self.assertEqual(information["BasicLimitInformation"]["LimitFlags"], 0)
        win32api.CloseHandle.assert_called_once_with("job")

    def test_normal_job_close_does_not_close_if_disarm_fails(self):
        win32api = mock.Mock()
        win32job = mock.Mock()
        win32job.JobObjectExtendedLimitInformation = 9
        win32job.QueryInformationJobObject.side_effect = RuntimeError("busy")

        closed = process_control._close_job(("job", win32api, win32job))

        self.assertFalse(closed)
        win32api.CloseHandle.assert_not_called()

    def test_cleanup_reports_unconfirmed_process_without_terminating_it(self):
        after = {
            303: {
                "pid": 303,
                "parent_pid": 4,
                "name": "POWERPNT.EXE",
                "command_line": "POWERPNT.EXE",
            }
        }
        with mock.patch.object(process_control, "terminate_pid") as terminate:
            result = process_control.cleanup_automation_processes(
                {}, after, stage_pid=999
            )

        self.assertEqual(result["status"], "unconfirmed")
        self.assertEqual(result["unknown_pids"], [303])
        terminate.assert_not_called()

    def test_normal_completion_audit_never_terminates_exiting_automation(self):
        after = {
            404: {
                "pid": 404,
                "parent_pid": 999,
                "name": "ChemDraw.exe",
                "command_line": "ChemDraw.exe /Automation -Embedding",
            }
        }
        with mock.patch.object(process_control, "terminate_pid") as terminate:
            result = process_control.cleanup_automation_processes(
                {}, after, stage_pid=999, terminate=False
            )

        self.assertEqual(result["status"], "unconfirmed")
        self.assertEqual(result["lingering_pids"], [404])
        terminate.assert_not_called()

    def test_snapshot_filters_signaled_process_records(self):
        completed = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout=json.dumps(
                [
                    {
                        "pid": 505,
                        "parent_pid": 1,
                        "name": "ChemDraw.exe",
                        "command_line": None,
                        "created": "now",
                    }
                ]
            ),
            stderr="",
        )
        with mock.patch.object(
            process_control, "_system_executable", return_value=Path("powershell.exe")
        ), mock.patch.object(
            process_control.subprocess, "run", return_value=completed
        ), mock.patch.object(
            process_control, "pid_is_running", return_value=False
        ):
            snapshot = process_control.snapshot_automation_processes()

        self.assertEqual(snapshot, {})

    def test_snapshot_queries_only_supported_automation_processes(self):
        completed = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="[]",
            stderr="",
        )
        with mock.patch.object(
            process_control, "_system_executable", return_value=Path("powershell.exe")
        ), mock.patch.object(
            process_control.subprocess, "run", return_value=completed
        ) as run:
            process_control.snapshot_automation_processes()

        command = run.call_args.args[0][-1]
        self.assertIn("-Filter", command)
        self.assertIn("Name='ChemDraw.exe'", command)
        self.assertNotIn("Where-Object", command)

    def test_snapshot_ignores_terminated_records_even_if_pid_probe_is_inconclusive(self):
        completed = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout=json.dumps(
                {
                    "pid": 606,
                    "parent_pid": 1,
                    "name": "ChemDraw.exe",
                    "thread_count": 0,
                    "virtual_size": 0,
                }
            ),
            stderr="",
        )
        with mock.patch.object(
            process_control, "_system_executable", return_value=Path("powershell.exe")
        ), mock.patch.object(
            process_control.subprocess, "run", return_value=completed
        ), mock.patch.object(
            process_control, "pid_is_running", return_value=True
        ):
            snapshot = process_control.snapshot_automation_processes()

        self.assertEqual(snapshot, {})


if __name__ == "__main__":
    unittest.main()
