from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest
from unittest import mock

import runtime_discovery


SCRIPT_ROOT = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_ROOT.parent
REFERENCES = SKILL_ROOT / "references"
CONFIGURE_SCRIPT = SCRIPT_ROOT / "configure_mcp.ps1"
HEALTH_SCRIPT = SCRIPT_ROOT / "health_check.ps1"
SERVER_SCRIPT = SCRIPT_ROOT / "mcp_server.py"
REQUIRED_IMPORTS = ("cdxml_toolkit", "mcp", "rdkit", "win32com.client")


def _minimal_environment() -> dict[str, str]:
    keys = ("SystemRoot", "WINDIR", "USERPROFILE", "HOME", "PATH", "PATHEXT")
    return {key: os.environ[key] for key in keys if key in os.environ}


class RuntimeDiscoveryTests(unittest.TestCase):
    def test_explicit_python_wins_after_import_probe(self):
        with tempfile.TemporaryDirectory() as tmp:
            executable = Path(tmp) / "python.exe"
            executable.write_bytes(b"MZ")
            with (
                mock.patch.dict(
                    os.environ, {"CHEMDRAW_MCP_PYTHON": "ignored"}, clear=False
                ),
                mock.patch.object(
                    runtime_discovery, "_probe_python", return_value=None, create=True
                ) as probe,
            ):
                result = runtime_discovery.find_python(str(executable))
        self.assertEqual(result.path, str(executable.resolve()))
        self.assertEqual(result.source, "explicit")
        self.assertIsNotNone(probe.call_args)
        self.assertEqual(probe.call_args.args[0], executable.resolve())

    def test_environment_python_is_second_after_import_probe(self):
        with tempfile.TemporaryDirectory() as tmp:
            executable = Path(tmp) / "python.exe"
            executable.write_bytes(b"MZ")
            with (
                mock.patch.dict(
                    os.environ,
                    {"CHEMDRAW_MCP_PYTHON": str(executable)},
                    clear=False,
                ),
                mock.patch.object(
                    runtime_discovery, "_probe_python", return_value=None, create=True
                ) as probe,
            ):
                result = runtime_discovery.find_python()
        self.assertEqual(result.source, "environment")
        self.assertIsNotNone(probe.call_args)
        self.assertEqual(probe.call_args.args[0], executable.resolve())

    def test_missing_explicit_path_is_clear_error(self):
        with self.assertRaisesRegex(RuntimeError, "explicit"):
            runtime_discovery.find_python("Z:\\missing\\python.exe")

    def test_unusable_explicit_python_is_a_clear_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            executable = Path(tmp) / "python.exe"
            executable.write_bytes(b"MZ")
            with mock.patch.object(
                runtime_discovery,
                "_probe_python",
                return_value="missing required import: mcp",
                create=True,
            ):
                with self.assertRaisesRegex(
                    RuntimeError, "explicit.*missing required import: mcp"
                ):
                    runtime_discovery.find_python(str(executable))

    def test_unusable_environment_python_is_a_clear_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            executable = Path(tmp) / "python.exe"
            executable.write_bytes(b"MZ")
            with (
                mock.patch.dict(
                    os.environ,
                    {"CHEMDRAW_MCP_PYTHON": str(executable)},
                    clear=False,
                ),
                mock.patch.object(
                    runtime_discovery,
                    "_probe_python",
                    return_value="missing required import: rdkit",
                    create=True,
                ),
            ):
                with self.assertRaisesRegex(
                    RuntimeError,
                    "CHEMDRAW_MCP_PYTHON.*missing required import: rdkit",
                ):
                    runtime_discovery.find_python()

    def test_unusable_implicit_python_is_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "bad-python.exe"
            good = Path(tmp) / "good-python.exe"
            bad.write_bytes(b"MZ")
            good.write_bytes(b"MZ")

            def probe(path: Path) -> str | None:
                return "imports failed" if path == bad.resolve() else None

            with (
                mock.patch.dict(os.environ, _minimal_environment(), clear=True),
                mock.patch.object(runtime_discovery.sys, "executable", str(bad)),
                mock.patch.object(runtime_discovery.shutil, "which", return_value=str(good)),
                mock.patch.object(
                    runtime_discovery, "_probe_python", side_effect=probe, create=True
                ),
            ):
                result = runtime_discovery.find_python()
        self.assertEqual(result.path, str(good.resolve()))
        self.assertEqual(result.source, "PATH")

    def test_conda_environment_registry_finds_named_cdxml_environment(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            environment = Path(tmp) / "portable-conda" / "envs" / "cdxml"
            executable = environment / "python.exe"
            executable.parent.mkdir(parents=True)
            executable.write_bytes(b"MZ")
            registry = home / ".conda" / "environments.txt"
            registry.parent.mkdir(parents=True)
            registry.write_text(str(environment) + "\n", encoding="utf-8")

            with (
                mock.patch.dict(os.environ, _minimal_environment(), clear=True),
                mock.patch.object(runtime_discovery.Path, "home", return_value=home),
                mock.patch.object(runtime_discovery.sys, "executable", "Z:\\missing\\python.exe"),
                mock.patch.object(runtime_discovery.shutil, "which", return_value=None),
                mock.patch.object(runtime_discovery, "_probe_python", return_value=None),
            ):
                result = runtime_discovery.find_python()

        self.assertEqual(result.path, str(executable.resolve()))
        self.assertEqual(result.source, "conda-environment-registry")

    def test_runtime_discovery_has_no_machine_specific_python_fallback(self):
        source = Path(runtime_discovery.__file__).read_text(encoding="utf-8")
        self.assertNotIn("D:\\" + "ProgramFiles", source)

    def test_python_probe_imports_every_required_module(self):
        self.assertTrue(hasattr(runtime_discovery, "_probe_python"))
        completed = subprocess.CompletedProcess([], 0, stdout="", stderr="")
        with mock.patch.object(
            runtime_discovery.subprocess, "run", return_value=completed
        ) as run:
            error = runtime_discovery._probe_python(Path(sys.executable))
        self.assertIsNone(error)
        command = run.call_args.args[0]
        self.assertEqual(command[0], str(Path(sys.executable)))
        self.assertEqual(command[1], "-c")
        for module in runtime_discovery.REQUIRED_IMPORTS:
            self.assertIn(module, command[2])
        self.assertGreater(run.call_args.kwargs["timeout"], 0)

    def test_quoted_localserver_command_extracts_executable(self):
        self.assertTrue(
            hasattr(runtime_discovery, "_extract_local_server_executable")
        )
        command = '"C:\\Program Files\\ChemDraw\\ChemDraw.exe" /Automation'
        self.assertEqual(
            runtime_discovery._extract_local_server_executable(command),
            r"C:\Program Files\ChemDraw\ChemDraw.exe",
        )

    def test_unquoted_localserver_command_extracts_executable(self):
        self.assertTrue(
            hasattr(runtime_discovery, "_extract_local_server_executable")
        )
        command = r"D:\Program Files\ChemOffice\ChemDraw\ChemDraw.exe /Automation"
        self.assertEqual(
            runtime_discovery._extract_local_server_executable(command),
            r"D:\Program Files\ChemOffice\ChemDraw\ChemDraw.exe",
        )

    def test_chemdraw_registry_precedes_common_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            registry_exe = Path(tmp) / "registry" / "ChemDraw.exe"
            common_exe = Path(tmp) / "common" / "ChemDraw.exe"
            registry_exe.parent.mkdir()
            common_exe.parent.mkdir()
            registry_exe.write_bytes(b"MZ")
            common_exe.write_bytes(b"MZ")
            command = f'"{registry_exe}" /Automation'
            with (
                mock.patch.object(
                    runtime_discovery,
                    "_registry_local_server_command",
                    return_value=command,
                    create=True,
                ),
                mock.patch.object(
                    runtime_discovery,
                    "_common_chemdraw_candidates",
                    return_value=[common_exe],
                    create=True,
                ),
                mock.patch.dict(
                    os.environ,
                    {key: value for key, value in os.environ.items() if key != "CHEMDRAW_EXE"},
                    clear=True,
                ),
            ):
                try:
                    result = runtime_discovery.find_chemdraw()
                except RuntimeError as exc:
                    self.fail(str(exc))
        self.assertEqual(result.path, str(registry_exe.resolve()))
        self.assertEqual(result.source, "registry-HKCR")

    def test_chemdraw_common_paths_include_nested_revvity_layouts(self):
        with tempfile.TemporaryDirectory() as tmp:
            executable = (
                Path(tmp)
                / "Revvity Signals Software"
                / "ChemOffice2025"
                / "ChemDraw"
                / "ChemDraw.exe"
            )
            executable.parent.mkdir(parents=True)
            executable.write_bytes(b"MZ")
            environment = _minimal_environment()
            environment["ProgramFiles"] = tmp
            environment["ProgramFiles(x86)"] = ""
            environment["ProgramW6432"] = tmp
            with (
                mock.patch.dict(os.environ, environment, clear=True),
                mock.patch.object(
                    runtime_discovery,
                    "_registry_local_server_command",
                    return_value=None,
                    create=True,
                ),
            ):
                try:
                    result = runtime_discovery.find_chemdraw()
                except RuntimeError as exc:
                    self.fail(str(exc))
        self.assertEqual(result.path, str(executable.resolve()))
        self.assertEqual(result.source, "common-path")


class PowerShellHarness:
    def __init__(self, root: Path):
        self.root = root
        self.config = root / "codex-home" / "config.toml"
        self.state = root / "codex-state.json"
        self.log = root / "codex-calls.jsonl"
        self.runtime_helper = root / "fake_runtime.py"
        self.runtime = root / "fake-python.cmd"
        self.runtime_log = root / "runtime-calls.jsonl"
        self.codex_helper = root / "fake_codex.py"
        self.codex = root / "fake-codex.cmd"
        self.clean_references = root / "clean-references"
        self._write_helpers()

    @staticmethod
    def _cmd_invocation(helper: Path) -> str:
        return subprocess.list2cmdline([sys.executable, str(helper)])

    def _write_helpers(self) -> None:
        self.runtime_helper.write_text(
            textwrap.dedent(
                """
                import json
                import os
                from pathlib import Path
                import shutil
                import sys
                import time
                import tomlkit

                args = sys.argv[1:]
                log_value = os.environ.get("FAKE_RUNTIME_LOG")
                if log_value:
                    with Path(log_value).open("a", encoding="utf-8") as stream:
                        stream.write(json.dumps(args) + "\\n")
                if args[:1] == ["-c"] and "CHEMDRAW_MCP_CONFIG_AUDIT" in args[1]:
                    config = Path(args[2])
                    if not config.is_file():
                        print("{}")
                    else:
                        data = tomlkit.parse(config.read_text(encoding="utf-8"))
                        block = data.get("mcp_servers", {}).get("cdxml-toolkit", {})
                        print(json.dumps(block))
                    raise SystemExit(0)
                if args[:2] == ["-m", "pip"] and os.environ.get("FAKE_PIP_SLEEP"):
                    time.sleep(float(os.environ["FAKE_PIP_SLEEP"]))
                if args and args[0].endswith("runtime_discovery.py"):
                    runtime = os.environ["CHEMDRAW_MCP_PYTHON"]
                    skill_root = str(Path(args[0]).resolve().parent.parent)
                    print(json.dumps({
                        "python": {"path": runtime, "source": "explicit"},
                        "skill_root": {"path": skill_root, "source": "script"},
                        "chemdraw": {"path": runtime, "source": "fixture"},
                    }))
                    raise SystemExit(0)
                source_value = os.environ.get("FAKE_GENERATED_REFERENCE_SOURCE")
                source = Path(source_value) if source_value else None
                if args and args[0].endswith("audit_toolkit_interfaces.py"):
                    output = Path(args[args.index("--output-dir") + 1])
                    output.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source / "toolkit-public-inventory.md", output)
                    shutil.copytree(source / "inventory", output / "inventory")
                elif args and args[0].endswith("generate_tool_reference.py"):
                    output = Path(args[args.index("--output") + 1])
                    output.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source / "mcp-signatures.md", output)
                elif args and args[0].endswith("runtime_diagnostics.py"):
                    capabilities = {
                        "python": {"status": "available"},
                        "cdxml_toolkit": {"status": "available", "version": "0.5.17"},
                        "tool_registry": {"status": "available", "count": 34},
                        "decimer_models": {"status": "missing"},
                    }
                    if "--native-probe" in args:
                        capabilities["native_probe"] = {"status": "available"}
                    if "--office-probe" in args:
                        capabilities["office_probe"] = {"status": "available"}
                    print(json.dumps({
                        "ok": True,
                        "outputs": {"capabilities": capabilities},
                        "warnings": ["decimer_models: capability is unavailable"],
                        "metadata": {"tool_count": 34, "network_used": False},
                    }))
                raise SystemExit(0)
                """
            ).lstrip(),
            encoding="ascii",
        )
        self.runtime.write_text(
            "@echo off\r\n"
            + self._cmd_invocation(self.runtime_helper)
            + " %*\r\nexit /b %ERRORLEVEL%\r\n",
            encoding="ascii",
        )
        self.codex_helper.write_text(
            textwrap.dedent(
                """
                import json
                import os
                from pathlib import Path
                import sys
                import tomlkit

                args = sys.argv[1:]
                config = Path(os.environ["FAKE_CODEX_CONFIG"])
                state = Path(os.environ["FAKE_CODEX_STATE"])
                log = Path(os.environ["FAKE_CODEX_LOG"])
                log.parent.mkdir(parents=True, exist_ok=True)
                with log.open("a", encoding="utf-8") as stream:
                    stream.write(json.dumps(args) + "\\n")

                if args[:2] == ["mcp", "get"]:
                    if os.environ.get("FAKE_CODEX_FAIL_GET") == "1":
                        print("forced get failure")
                        raise SystemExit(8)
                    if os.environ.get("FAKE_CODEX_INVALID_JSON") == "1":
                        print('{"transport":{"env":{"API_KEY":"sk-test-secret"}}')
                        raise SystemExit(0)
                    if (
                        os.environ.get("FAKE_CODEX_LIVE_CONFIG") == "1"
                        and config.is_file()
                    ):
                        data = tomlkit.parse(config.read_text(encoding="utf-8"))
                        block = data.get("mcp_servers", {}).get("cdxml-toolkit")
                        if block:
                            payload = {
                                "name": "cdxml-toolkit",
                                "enabled": True,
                                "transport": {
                                    "type": "stdio",
                                    "command": block.get("command"),
                                    "args": block.get("args", []),
                                    "env": block.get("env", {}),
                                },
                            }
                            for key in (
                                "startup_timeout_sec",
                                "tool_timeout_sec",
                                "default_tools_approval_mode",
                            ):
                                if key in block:
                                    payload[key] = block[key]
                            print(json.dumps(payload))
                            raise SystemExit(0)
                    if not state.is_file():
                        print("No MCP server named 'cdxml-toolkit'.")
                        raise SystemExit(1)
                    print(state.read_text(encoding="utf-8"))
                    raise SystemExit(0)

                if args[:2] == ["mcp", "remove"]:
                    state.unlink(missing_ok=True)
                    config.parent.mkdir(parents=True, exist_ok=True)
                    config.write_text("removed\\n", encoding="utf-8")
                    raise SystemExit(0)

                if args[:2] == ["mcp", "add"]:
                    config.parent.mkdir(parents=True, exist_ok=True)
                    if os.environ.get("FAKE_CODEX_FAIL_ADD") == "1":
                        if os.environ.get("FAKE_CODEX_CONCURRENT_EDIT") == "1":
                            config.write_text("concurrent-user-edit\\n", encoding="utf-8")
                        print("forced add failure", file=sys.stderr)
                        raise SystemExit(9)
                    config.write_text("partial\\n", encoding="utf-8")
                    separator = args.index("--")
                    command = args[separator + 1]
                    command_args = args[separator + 2:]
                    environment = {}
                    index = 3
                    while index < separator:
                        if args[index] == "--env":
                            key, value = args[index + 1].split("=", 1)
                            environment[key] = value
                            index += 2
                        else:
                            index += 1
                    payload = {
                        "name": "cdxml-toolkit",
                        "enabled": True,
                        "transport": {
                            "type": "stdio",
                            "command": command,
                            "args": command_args,
                            "env": environment,
                        },
                    }
                    state.write_text(json.dumps(payload), encoding="utf-8")
                    config.write_text("registered\\n", encoding="utf-8")
                    raise SystemExit(0)

                raise SystemExit(2)
                """
            ).lstrip(),
            encoding="ascii",
        )
        self.codex.write_text(
            "@echo off\r\n"
            + self._cmd_invocation(self.codex_helper)
            + " %*\r\nexit /b %ERRORLEVEL%\r\n",
            encoding="ascii",
        )
        self.config.parent.mkdir(parents=True)
        shutil.copytree(REFERENCES / "inventory", self.clean_references / "inventory")
        for name in ("toolkit-public-inventory.md", "mcp-signatures.md"):
            shutil.copy2(REFERENCES / name, self.clean_references / name)

    def environment(self) -> dict[str, str]:
        environment = os.environ.copy()
        environment.update(
            {
                "CHEMDRAW_MCP_PYTHON": str(self.runtime),
                "CHEMDRAW_EXE": str(self.runtime),
                "FAKE_CODEX_CONFIG": str(self.config),
                "FAKE_CODEX_STATE": str(self.state),
                "FAKE_CODEX_LOG": str(self.log),
                "FAKE_RUNTIME_LOG": str(self.runtime_log),
                "FAKE_GENERATED_REFERENCE_SOURCE": str(self.clean_references),
                "PYTHONIOENCODING": "utf-8",
            }
        )
        return environment

    def write_state(
        self,
        *,
        command: str,
        args: list[str],
        environment: dict[str, str] | None = None,
        extra: dict[str, object] | None = None,
    ) -> None:
        payload = {
            "name": "cdxml-toolkit",
            "enabled": True,
            "transport": {
                "type": "stdio",
                "command": command,
                "args": args,
                "env": environment
                or {
                    "TF_CPP_MIN_LOG_LEVEL": "3",
                    "TF_ENABLE_ONEDNN_OPTS": "0",
                },
            },
        }
        if extra:
            payload.update(extra)
        self.state.write_text(json.dumps(payload), encoding="utf-8")

    def write_roundtrippable_config(self) -> str:
        content = textwrap.dedent(
            """
            [mcp_servers.cdxml-toolkit]
            command = "wrong-python.exe"
            args = ["wrong-server.py"]

            [mcp_servers.cdxml-toolkit.env]
            TF_CPP_MIN_LOG_LEVEL = "3"
            TF_ENABLE_ONEDNN_OPTS = "0"
            """
        ).lstrip()
        self.config.write_text(content, encoding="ascii")
        return content

    def calls(self) -> list[list[str]]:
        if not self.log.is_file():
            return []
        return [
            json.loads(line)
            for line in self.log.read_text(encoding="utf-8").splitlines()
        ]

    def runtime_calls(self) -> list[list[str]]:
        if not self.runtime_log.is_file():
            return []
        return [
            json.loads(line)
            for line in self.runtime_log.read_text(encoding="utf-8").splitlines()
        ]


def _run_powershell(
    script: Path,
    arguments: list[str],
    *,
    environment: dict[str, str],
    timeout: int = 60,
) -> subprocess.CompletedProcess[str]:
    powershell = shutil.which("powershell.exe") or shutil.which("powershell")
    if not powershell:
        raise unittest.SkipTest("Windows PowerShell is unavailable")
    return subprocess.run(
        [
            powershell,
            "-NoLogo",
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(script),
            *arguments,
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=environment,
        timeout=timeout,
    )


@unittest.skip(
    "Superseded by test_configure_mcp_current and package codex_config tests."
)
class ConfigureMcpTests(unittest.TestCase):
    def test_config_hash_does_not_depend_on_get_file_hash_cmdlet(self):
        source = CONFIGURE_SCRIPT.read_text(encoding="utf-8")
        self.assertNotIn("Get-FileHash", source)
        self.assertIn("Security.Cryptography.SHA256", source)

    def _arguments(self, harness: PowerShellHarness) -> list[str]:
        return [
            "-Python",
            str(harness.runtime),
            "-SkillRoot",
            str(SKILL_ROOT),
            "-ConfigPath",
            str(harness.config),
            "-CodexCommand",
            str(harness.codex),
        ]

    def test_runtime_discovery_is_the_only_final_selector(self):
        source = CONFIGURE_SCRIPT.read_text(encoding="utf-8")
        self.assertIn("runtime_discovery.py", source)
        self.assertNotIn("$env:CHEMDRAW_MCP_PYTHON", source)
        self.assertNotIn("$env:CONDA_PREFIX", source)
        self.assertNotIn("D:\\" + "ProgramFiles\\Anaconda", source)

    def test_new_registration_does_not_add_dead_decimer_flag(self):
        with tempfile.TemporaryDirectory() as tmp:
            harness = PowerShellHarness(Path(tmp))
            harness.write_roundtrippable_config()
            harness.write_state(command="wrong-python.exe", args=["wrong-server.py"])
            result = _run_powershell(
                CONFIGURE_SCRIPT,
                [*self._arguments(harness), "-Apply"],
                environment=harness.environment(),
            )
            add_calls = [call for call in harness.calls() if call[:2] == ["mcp", "add"]]
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(len(add_calls), 1)
            separator = add_calls[0].index("--")
            self.assertEqual(
                add_calls[0][separator + 1 :],
                [str(harness.runtime.resolve()), str(SERVER_SCRIPT.resolve())],
            )

    def test_missing_registration_is_added(self):
        with tempfile.TemporaryDirectory() as tmp:
            harness = PowerShellHarness(Path(tmp))
            result = _run_powershell(
                CONFIGURE_SCRIPT,
                [*self._arguments(harness), "-Apply"],
                environment=harness.environment(),
            )
            add_calls = [
                call for call in harness.calls() if call[:2] == ["mcp", "add"]
            ]
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(len(add_calls), 1)
            self.assertEqual(json.loads(result.stdout)["status"], "applied")
            self.assertEqual(
                list(harness.config.parent.glob("config.toml.chemdraw-*.bak")), []
            )

    def test_legacy_dead_arg_is_compatible_and_preserved_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            harness = PowerShellHarness(Path(tmp))
            harness.config.write_text("original\n", encoding="utf-8")
            harness.write_state(
                command=str(harness.runtime.resolve()),
                args=[str(SERVER_SCRIPT.resolve()), "--no-preload-decimer"],
                environment={
                    "TF_CPP_MIN_LOG_LEVEL": "3",
                    "TF_ENABLE_ONEDNN_OPTS": "0",
                    "HTTP_PROXY": "http://127.0.0.1:7897",
                    "HTTPS_PROXY": "http://127.0.0.1:7897",
                    "ALL_PROXY": "http://127.0.0.1:7897",
                },
                extra={
                    "startup_timeout_sec": 120.0,
                    "tool_timeout_sec": 600.0,
                },
            )
            result = _run_powershell(
                CONFIGURE_SCRIPT,
                [*self._arguments(harness), "-Apply"],
                environment=harness.environment(),
            )
            mutating_calls = [
                call for call in harness.calls() if call[:2] in (["mcp", "add"], ["mcp", "remove"])
            ]
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(json.loads(result.stdout)["status"], "unchanged")
            self.assertEqual(harness.config.read_text(encoding="utf-8"), "original\n")
            self.assertEqual(mutating_calls, [])
            self.assertEqual(
                list(harness.config.parent.glob("config.toml.chemdraw-*.bak")), []
            )

    def test_replacement_preserves_every_existing_environment_entry(self):
        with tempfile.TemporaryDirectory() as tmp:
            harness = PowerShellHarness(Path(tmp))
            harness.write_roundtrippable_config()
            existing_environment = {
                "TF_CPP_MIN_LOG_LEVEL": "3",
                "TF_ENABLE_ONEDNN_OPTS": "0",
                "HTTP_PROXY": "http://127.0.0.1:7897",
                "HTTPS_PROXY": "http://127.0.0.1:7897",
                "ALL_PROXY": "http://127.0.0.1:7897",
                "NO_PROXY": "localhost,127.0.0.1,::1",
            }
            harness.write_state(
                command="wrong-python.exe",
                args=["wrong-server.py"],
                environment=existing_environment,
            )
            result = _run_powershell(
                CONFIGURE_SCRIPT,
                [*self._arguments(harness), "-Apply"],
                environment=harness.environment(),
            )
            add_call = next(
                call for call in harness.calls() if call[:2] == ["mcp", "add"]
            )
            separator = add_call.index("--")
            registered_environment = {}
            index = 3
            while index < separator:
                if add_call[index] == "--env":
                    key, value = add_call[index + 1].split("=", 1)
                    registered_environment[key] = value
                    index += 2
                else:
                    index += 1
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(registered_environment, existing_environment)

    def test_preview_redacts_preserved_environment_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            harness = PowerShellHarness(Path(tmp))
            harness.config.write_text("original\n", encoding="ascii")
            secret_proxy = "http://user:secret@127.0.0.1:7897"
            harness.write_state(
                command="wrong-python.exe",
                args=["wrong-server.py"],
                environment={
                    "TF_CPP_MIN_LOG_LEVEL": "3",
                    "TF_ENABLE_ONEDNN_OPTS": "0",
                    "HTTPS_PROXY": secret_proxy,
                },
            )
            result = _run_powershell(
                CONFIGURE_SCRIPT,
                self._arguments(harness),
                environment=harness.environment(),
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            proposal = json.loads(result.stdout)
            self.assertNotIn(secret_proxy, result.stdout)
            self.assertIn("--env HTTPS_PROXY=<preserved>", proposal["command"])

    def test_failed_get_is_not_treated_as_missing_registration(self):
        with tempfile.TemporaryDirectory() as tmp:
            harness = PowerShellHarness(Path(tmp))
            original = harness.write_roundtrippable_config()
            harness.write_state(command="wrong-python.exe", args=["wrong-server.py"])
            environment = harness.environment()
            environment["FAKE_CODEX_FAIL_GET"] = "1"
            result = _run_powershell(
                CONFIGURE_SCRIPT,
                [*self._arguments(harness), "-Apply"],
                environment=environment,
            )
            mutating_calls = [
                call
                for call in harness.calls()
                if call[:2] in (["mcp", "add"], ["mcp", "remove"])
            ]
            combined = result.stdout + result.stderr
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("codex mcp get failed", combined)
            self.assertNotIn("forced get failure", combined)
            self.assertEqual(harness.config.read_text(encoding="utf-8"), original)
            self.assertEqual(mutating_calls, [])
            self.assertEqual(
                list(harness.config.parent.glob("config.toml.chemdraw-*.bak")), []
            )

    def test_invalid_registration_json_does_not_leak_environment_secrets(self):
        with tempfile.TemporaryDirectory() as tmp:
            harness = PowerShellHarness(Path(tmp))
            original = harness.write_roundtrippable_config()
            environment = harness.environment()
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

    def test_non_roundtrippable_scalar_settings_refuse_replacement(self):
        with tempfile.TemporaryDirectory() as tmp:
            harness = PowerShellHarness(Path(tmp))
            original = textwrap.dedent(
                """
                [mcp_servers.cdxml-toolkit]
                command = "wrong-python.exe"
                args = ["wrong-server.py"]
                startup_timeout_sec = 120
                tool_timeout_sec = 600
                default_tools_approval_mode = "approve"

                [mcp_servers.cdxml-toolkit.env]
                TF_CPP_MIN_LOG_LEVEL = "3"
                TF_ENABLE_ONEDNN_OPTS = "0"
                """
            ).lstrip()
            harness.config.write_text(original, encoding="ascii")
            harness.write_state(
                command="wrong-python.exe",
                args=["wrong-server.py"],
                extra={
                    "startup_timeout_sec": 120.0,
                    "tool_timeout_sec": 600.0,
                },
            )
            result = _run_powershell(
                CONFIGURE_SCRIPT,
                [*self._arguments(harness), "-Apply"],
                environment=harness.environment(),
            )
            mutating_calls = [
                call for call in harness.calls() if call[:2] in (["mcp", "add"], ["mcp", "remove"])
            ]
            combined = (result.stdout + result.stderr).lower()
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("round-trip", combined)
            self.assertIn("default_tools_approval_mode", combined)
            self.assertEqual(harness.config.read_text(encoding="utf-8"), original)
            self.assertEqual(mutating_calls, [])
            self.assertEqual(
                list(harness.config.parent.glob("config.toml.chemdraw-*.bak")), []
            )

    def test_correct_registration_is_preserved_without_backup(self):
        with tempfile.TemporaryDirectory() as tmp:
            harness = PowerShellHarness(Path(tmp))
            harness.config.write_text("original\n", encoding="utf-8")
            harness.write_state(
                command=str(harness.runtime.resolve()), args=[str(SERVER_SCRIPT.resolve())]
            )
            result = _run_powershell(
                CONFIGURE_SCRIPT,
                [*self._arguments(harness), "-Apply"],
                environment=harness.environment(),
            )
            backups = list(harness.config.parent.glob("config.toml.chemdraw-*.bak"))
            mutating_calls = [
                call for call in harness.calls() if call[:2] in (["mcp", "add"], ["mcp", "remove"])
            ]
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(json.loads(result.stdout)["status"], "unchanged")
            self.assertEqual(harness.config.read_text(encoding="utf-8"), "original\n")
            self.assertEqual(backups, [])
            self.assertEqual(mutating_calls, [])

    def test_whatif_does_not_mutate_or_backup(self):
        with tempfile.TemporaryDirectory() as tmp:
            harness = PowerShellHarness(Path(tmp))
            harness.config.write_text("original\n", encoding="utf-8")
            harness.write_state(command="wrong-python.exe", args=["wrong-server.py"])
            result = _run_powershell(
                CONFIGURE_SCRIPT,
                [*self._arguments(harness), "-Apply", "-WhatIf"],
                environment=harness.environment(),
            )
            backups = list(harness.config.parent.glob("config.toml.chemdraw-*.bak"))
            mutating_calls = [
                call for call in harness.calls() if call[:2] in (["mcp", "add"], ["mcp", "remove"])
            ]
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(harness.config.read_text(encoding="utf-8"), "original\n")
            self.assertEqual(backups, [])
            self.assertEqual(mutating_calls, [])

    def test_failed_registration_restores_backup_automatically(self):
        with tempfile.TemporaryDirectory() as tmp:
            harness = PowerShellHarness(Path(tmp))
            original = harness.write_roundtrippable_config()
            harness.write_state(command="wrong-python.exe", args=["wrong-server.py"])
            environment = harness.environment()
            environment["FAKE_CODEX_FAIL_ADD"] = "1"
            result = _run_powershell(
                CONFIGURE_SCRIPT,
                [*self._arguments(harness), "-Apply"],
                environment=environment,
            )
            backups = list(harness.config.parent.glob("config.toml.chemdraw-*.bak"))
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(harness.config.read_text(encoding="utf-8"), original)
            self.assertEqual(len(backups), 1)
            self.assertEqual(backups[0].read_text(encoding="utf-8"), original)
            self.assertIn("restored", (result.stdout + result.stderr).lower())

    def test_failed_registration_does_not_overwrite_concurrent_config_edit(self):
        with tempfile.TemporaryDirectory() as tmp:
            harness = PowerShellHarness(Path(tmp))
            original = harness.write_roundtrippable_config()
            harness.write_state(command="wrong-python.exe", args=["wrong-server.py"])
            environment = harness.environment()
            environment["FAKE_CODEX_FAIL_ADD"] = "1"
            environment["FAKE_CODEX_CONCURRENT_EDIT"] = "1"
            result = _run_powershell(
                CONFIGURE_SCRIPT,
                [*self._arguments(harness), "-Apply"],
                environment=environment,
            )
            backups = list(harness.config.parent.glob("config.toml.chemdraw-*.bak"))
            combined = (result.stdout + result.stderr).lower()
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(
                harness.config.read_text(encoding="utf-8"), "concurrent-user-edit\n"
            )
            self.assertEqual(len(backups), 1)
            self.assertEqual(backups[0].read_text(encoding="utf-8"), original)
            self.assertIn("concurrent", combined)
            self.assertIn("not overwritten", combined)


class HealthCheckTests(unittest.TestCase):
    def _arguments(
        self, harness: PowerShellHarness, references: Path, timeout_seconds: int = 5
    ) -> list[str]:
        return [
            "-Python",
            str(harness.runtime),
            "-ReferenceRoot",
            str(references),
            "-CodexCommand",
            str(harness.codex),
            "-CommandTimeoutSeconds",
            str(timeout_seconds),
        ]

    def test_health_uses_runtime_discovery_and_bounded_process_helper(self):
        source = HEALTH_SCRIPT.read_text(encoding="utf-8")
        self.assertIn("runtime_discovery.py", source)
        self.assertIn("runtime_diagnostics.py", source)
        self.assertIn("Invoke-BoundedNative", source)
        self.assertNotIn("$env:CHEMDRAW_MCP_PYTHON", source)
        self.assertNotIn("$env:CONDA_PREFIX", source)
        self.assertNotIn("& $Python", source)
        self.assertNotIn("Get-FileHash", source)
        self.assertIn("Security.Cryptography.SHA256", source)
        self.assertIn("pwsh.exe", source)

    def test_health_generates_and_compares_mcp_signatures(self):
        source = HEALTH_SCRIPT.read_text(encoding="utf-8")
        self.assertIn("generate_tool_reference.py", source)
        self.assertIn("mcp-signatures.md", source)

    def test_health_uses_diagnostic_warnings_and_not_registry_only_success(self):
        source = HEALTH_SCRIPT.read_text(encoding="utf-8")
        self.assertIn("Write-Warning", source)
        self.assertNotIn("ChemDraw COM: registered (read-only check)", source)
        self.assertNotIn("$comKey", source)

    def test_health_allows_bounded_full_diagnostics_to_finish(self):
        source = HEALTH_SCRIPT.read_text(encoding="utf-8")
        self.assertIn("[int]$CommandTimeoutSeconds = 300", source)
        self.assertIn("$diagnosticTimeoutSeconds = 270", source)
        self.assertIn("-TimeoutSeconds $diagnosticTimeoutSeconds", source)

    def test_skip_native_chemdraw_warns_and_omits_chemscript_ping(self):
        source = HEALTH_SCRIPT.read_text(encoding="utf-8")
        self.assertIn("[switch]$SkipNativeChemDraw", source)
        with tempfile.TemporaryDirectory() as tmp:
            harness = PowerShellHarness(Path(tmp))
            expected = Path(tmp) / "expected-references"
            shutil.copytree(harness.clean_references, expected)
            harness.write_state(command="python.exe", args=["mcp_server.py"])
            result = _run_powershell(
                HEALTH_SCRIPT,
                [*self._arguments(harness, expected), "-SkipNativeChemDraw"],
                environment=harness.environment(),
            )
            combined = result.stdout + result.stderr
            self.assertIn("Native ChemDraw checks skipped", combined)
            self.assertFalse(
                any(
                    argument in {"--native-probe", "--office-probe"}
                    for call in harness.runtime_calls()
                    for argument in call
                )
            )

    def test_obsolete_inventory_shard_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            harness = PowerShellHarness(Path(tmp))
            expected = Path(tmp) / "expected-references"
            shutil.copytree(harness.clean_references, expected)
            obsolete = expected / "inventory" / "obsolete.md"
            obsolete.write_text("obsolete\n", encoding="ascii")
            harness.write_state(command="python.exe", args=["mcp_server.py"])
            result = _run_powershell(
                HEALTH_SCRIPT,
                self._arguments(harness, expected),
                environment=harness.environment(),
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("obsolete.md", result.stdout + result.stderr)

    def test_mcp_signature_drift_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            harness = PowerShellHarness(Path(tmp))
            expected = Path(tmp) / "expected-references"
            shutil.copytree(harness.clean_references, expected)
            signature = expected / "mcp-signatures.md"
            signature.write_text("stale\n", encoding="ascii")
            harness.write_state(command="python.exe", args=["mcp_server.py"])
            result = _run_powershell(
                HEALTH_SCRIPT,
                self._arguments(harness, expected),
                environment=harness.environment(),
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("mcp-signatures.md", result.stdout + result.stderr)

    def test_native_command_timeout_is_enforced(self):
        with tempfile.TemporaryDirectory() as tmp:
            harness = PowerShellHarness(Path(tmp))
            expected = Path(tmp) / "expected-references"
            shutil.copytree(harness.clean_references, expected)
            harness.write_state(command="python.exe", args=["mcp_server.py"])
            environment = harness.environment()
            environment["FAKE_PIP_SLEEP"] = "5"
            started = time.monotonic()
            result = _run_powershell(
                HEALTH_SCRIPT,
                self._arguments(harness, expected, timeout_seconds=1),
                environment=environment,
                timeout=20,
            )
            duration = time.monotonic() - started
            self.assertNotEqual(result.returncode, 0)
            self.assertLess(duration, 18)
            self.assertIn("timed out", (result.stdout + result.stderr).lower())


if __name__ == "__main__":
    unittest.main()
