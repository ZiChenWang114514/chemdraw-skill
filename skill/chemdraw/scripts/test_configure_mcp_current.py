from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import textwrap
import tomlkit
import unittest

from test_runtime_discovery import (
    CONFIGURE_SCRIPT,
    PowerShellHarness,
    SKILL_ROOT,
    _run_powershell,
)


class CurrentConfigureMcpTests(unittest.TestCase):
    def test_successful_import_with_stderr_warning_can_register(self):
        with tempfile.TemporaryDirectory() as tmp:
            harness = PowerShellHarness(Path(tmp))
            # Emit only during the MCP --help probe, not discovery's JSON output.
            (Path(tmp) / "sitecustomize.py").write_text(
                "import sys\nif '--help' in sys.argv: "
                "sys.stderr.write('nonfatal import warning\\n')\n",
                encoding="utf-8",
            )
            environment = self._environment(harness)
            environment["PYTHONPATH"] = tmp
            result = _run_powershell(
                CONFIGURE_SCRIPT,
                [*self._arguments(harness), "-Apply"],
                environment=environment,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(json.loads(result.stdout)["status"], "applied")

    def _arguments(self, harness: PowerShellHarness) -> list[str]:
        return [
            "-Python",
            sys.executable,
            "-SkillRoot",
            str(SKILL_ROOT),
            "-ConfigPath",
            str(harness.config),
            "-CodexCommand",
            str(harness.codex),
        ]

    def test_failed_import_probe_does_not_change_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            harness = PowerShellHarness(Path(tmp))
            original = harness.write_roundtrippable_config()
            (Path(tmp) / "sitecustomize.py").write_text(
                "import os, sys\nif '--help' in sys.argv: os._exit(7)\n",
                encoding="utf-8",
            )
            environment = self._environment(harness)
            environment["PYTHONPATH"] = tmp
            result = _run_powershell(
                CONFIGURE_SCRIPT,
                [*self._arguments(harness), "-Apply"],
                environment=environment,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("exit code 7", result.stdout + result.stderr)
            self.assertEqual(harness.config.read_text(encoding="utf-8"), original)

    @staticmethod
    def _environment(harness: PowerShellHarness) -> dict[str, str]:
        environment = harness.environment()
        environment["FAKE_CODEX_LIVE_CONFIG"] = "1"
        return environment

    def test_apply_preserves_extended_settings_environment_and_comments(self):
        with tempfile.TemporaryDirectory() as tmp:
            harness = PowerShellHarness(Path(tmp))
            original = textwrap.dedent(
                """
                # retained comment
                [mcp_servers.cdxml-toolkit]
                command = "wrong-python.exe"
                args = ["wrong-server.py"]
                startup_timeout_sec = 120.0
                tool_timeout_sec = 600.0
                default_tools_approval_mode = "approve"

                [mcp_servers.cdxml-toolkit.env]
                HTTPS_PROXY = "http://127.0.0.1:7897"
                """
            ).lstrip()
            harness.config.write_text(original, encoding="utf-8")

            result = _run_powershell(
                CONFIGURE_SCRIPT,
                [*self._arguments(harness), "-Apply"],
                environment=self._environment(harness),
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            proposal = json.loads(result.stdout)
            data = tomlkit.parse(harness.config.read_text(encoding="utf-8"))
            server = data["mcp_servers"]["cdxml-toolkit"]
            self.assertEqual(proposal["status"], "applied")
            self.assertTrue(
                harness.config.read_text(encoding="utf-8").startswith(
                    "# retained comment"
                )
            )
            self.assertEqual(server["command"], str(Path(sys.executable).resolve()))
            self.assertEqual(
                server["args"],
                ["-m", "cdxml_toolkit.mcp_runtime", "--profile", "codex"],
            )
            self.assertEqual(server["startup_timeout_sec"], 120.0)
            self.assertEqual(server["tool_timeout_sec"], 600.0)
            self.assertEqual(server["default_tools_approval_mode"], "approve")
            self.assertEqual(
                server["env"]["HTTPS_PROXY"], "http://127.0.0.1:7897"
            )
            self.assertEqual(
                [
                    call
                    for call in harness.calls()
                    if call[:2] in (["mcp", "add"], ["mcp", "remove"])
                ],
                [],
            )
            self.assertEqual(
                len(list(harness.config.parent.glob("config.toml.chemdraw-*.bak"))),
                1,
            )

    def test_preview_does_not_change_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            harness = PowerShellHarness(Path(tmp))
            original = harness.write_roundtrippable_config()

            result = _run_powershell(
                CONFIGURE_SCRIPT,
                self._arguments(harness),
                environment=self._environment(harness),
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(json.loads(result.stdout)["status"], "proposal")
            self.assertEqual(harness.config.read_text(encoding="utf-8"), original)
            self.assertEqual(
                list(harness.config.parent.glob("config.toml.chemdraw-*.bak")), []
            )

    def test_missing_config_is_created_without_backup(self):
        with tempfile.TemporaryDirectory() as tmp:
            harness = PowerShellHarness(Path(tmp))

            result = _run_powershell(
                CONFIGURE_SCRIPT,
                [*self._arguments(harness), "-Apply"],
                environment=self._environment(harness),
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            server = tomlkit.parse(
                harness.config.read_text(encoding="utf-8")
            )["mcp_servers"]["cdxml-toolkit"]
            self.assertEqual(server["command"], str(Path(sys.executable).resolve()))
            self.assertEqual(
                list(harness.config.parent.glob("config.toml.chemdraw-*.bak")), []
            )

    def test_invalid_registration_json_is_redacted_and_does_not_modify_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            harness = PowerShellHarness(Path(tmp))
            original = harness.write_roundtrippable_config()
            environment = self._environment(harness)
            environment["FAKE_CODEX_INVALID_JSON"] = "1"

            result = _run_powershell(
                CONFIGURE_SCRIPT,
                self._arguments(harness),
                environment=environment,
            )

            combined = result.stdout + result.stderr
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("invalid JSON", combined)
            self.assertNotIn("sk-test-secret", combined)
            self.assertEqual(harness.config.read_text(encoding="utf-8"), original)


if __name__ == "__main__":
    unittest.main()
