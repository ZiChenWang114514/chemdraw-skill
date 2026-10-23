from __future__ import annotations

import json
import os
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

    @unittest.skipUnless(os.name == "nt", "the PowerShell process query runs only on Windows")
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


class MacAutomationProcessTests(unittest.TestCase):
    """macOS: ChemDraw/Word/PowerPoint are children of launchd, so attribution uses
    the toolkit's launch registry instead of the parent process."""

    PS_OUTPUT = (
        "  101     1 /Applications/ChemDraw.app/Contents/MacOS/ChemDraw\n"
        "  102     1 /Applications/Microsoft Word.app/Contents/MacOS/Microsoft Word\n"
        "  103     1 /System/Applications/Mail.app/Contents/MacOS/Mail\n"
        "  104     1 /Applications/Microsoft PowerPoint.app/Contents/MacOS/Microsoft PowerPoint\n"
    )

    def test_snapshot_lists_chemdraw_and_office_with_their_launching_owner(self):
        from cdxml_toolkit.chemdraw import mac_automation

        completed = subprocess.CompletedProcess(args=[], returncode=0, stdout=self.PS_OUTPUT, stderr="")
        launched = {101: {"pid": 101, "bundle_id": "com.revvity.ChemDraw", "owner_pid": 555}}
        with mock.patch.object(process_control.sys, "platform", "darwin"), \
                mock.patch.object(process_control.subprocess, "run", return_value=completed) as run, \
                mock.patch.object(mac_automation, "launched_instances", return_value=launched):
            snapshot = process_control.snapshot_automation_processes()

        self.assertEqual(run.call_args.args[0][0], "ps")
        self.assertEqual(sorted(snapshot), [101, 102, 104])
        self.assertEqual(snapshot[101]["parent_pid"], 555)
        self.assertEqual(snapshot[102]["parent_pid"], 1)
        self.assertEqual(snapshot[104]["name"], "Microsoft PowerPoint")

    def test_cleanup_stops_only_what_the_stage_launched(self):
        from cdxml_toolkit.chemdraw import mac_automation

        after = {
            101: {"pid": 101, "parent_pid": 555, "name": "ChemDraw"},
            102: {"pid": 102, "parent_pid": 1, "name": "Microsoft Word"},
        }
        with mock.patch.object(process_control.sys, "platform", "darwin"), \
                mock.patch.object(process_control.os, "name", "posix"), \
                mock.patch.object(mac_automation, "terminate_process") as terminate, \
                mock.patch.object(process_control, "pid_is_running", return_value=False):
            result = process_control.cleanup_automation_processes({}, after, stage_pid=555)

        terminate.assert_called_once_with(101, grace_seconds=mock.ANY)
        self.assertEqual(result["terminated_pids"], [101])
        self.assertEqual(result["unknown_pids"], [102])


if __name__ == "__main__":
    unittest.main()
