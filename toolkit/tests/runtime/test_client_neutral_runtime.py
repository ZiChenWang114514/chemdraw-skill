"""The runtime is part of a client-neutral Skill: no agent product names in its defaults."""
from __future__ import annotations

import os
from pathlib import Path
import re
from unittest import mock

import pytest

from cdxml_toolkit.mcp_runtime import capabilities, mcp_server, official_overrides, tool_registry, tool_worker

PACKAGE = Path(tool_registry.__file__).resolve().parents[1]


def test_full_profile_is_the_default_and_codex_stays_an_alias():
    default = tool_registry.build_registry()
    assert tool_registry.DEFAULT_PROFILE == "full"
    assert set(default) == set(tool_registry.build_registry("full"))
    # Existing client configurations that pass --profile codex keep working unchanged.
    assert set(tool_registry.build_registry("codex")) == set(default)
    assert tool_registry.normalize_profile(" Codex ") == "full"
    assert len(default) == 54


def test_unknown_profile_is_still_rejected():
    with pytest.raises(ValueError, match="Unknown MCP profile"):
        tool_registry.build_registry("everything")


@pytest.mark.parametrize("value", ["full", "codex"])
def test_cli_accepts_the_neutral_name_and_the_alias(value):
    assert mcp_server.parse_args(["--profile", value]).profile == value


def test_environment_default_profile_is_neutral():
    with mock.patch.dict(os.environ, {}, clear=False):
        os.environ.pop("CHEMDRAW_MCP_PROFILE", None)
        assert mcp_server.parse_args([]).profile == "full"
        assert capabilities.get_toolkit_capabilities(detail="summary")["outputs"]["tool_count"] == 54


def test_failure_logs_and_native_temp_use_neutral_folders(tmp_path):
    with mock.patch.dict(os.environ, {"LOCALAPPDATA": str(tmp_path)}):
        error_id = tool_worker._failure_log(RuntimeError("boom"))
    logs = list(tmp_path.rglob(f"worker-{error_id}.log"))
    assert logs and logs[0].parent == tmp_path / "chemdraw-skill" / "logs"
    assert official_overrides._TEMP_OUTPUT.name == "chemdraw-skill-native"


def test_package_has_no_client_specific_configuration_writer():
    assert not (PACKAGE / "mcp_runtime" / "codex_config.py").exists()
    # Only the deliberate compatibility alias and the shared COM mutex name may mention it.
    allowed = {"tool_registry.py", "resource_lock.py"}
    offenders = [
        path.relative_to(PACKAGE).as_posix()
        for path in PACKAGE.rglob("*.py")
        if path.name not in allowed
        and re.search(r"\b(codex|openai)\b", path.read_text(encoding="utf-8"), re.IGNORECASE)
    ]
    assert offenders == []


def test_macos_failure_logs_go_to_library_logs(tmp_path):
    env = {k: v for k, v in os.environ.items() if k not in ("LOCALAPPDATA", "TEMP")}
    with mock.patch.dict(os.environ, env, clear=True), \
            mock.patch.object(tool_worker.sys, "platform", "darwin"), \
            mock.patch.object(tool_worker.Path, "home", return_value=tmp_path):
        # $HOME/chemdraw-skill is where the README clones the repository.
        assert tool_worker.worker_log_dir() == tmp_path / "Library" / "Logs" / "chemdraw-skill"
