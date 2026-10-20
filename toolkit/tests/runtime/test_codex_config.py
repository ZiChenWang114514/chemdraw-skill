from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
import tomlkit

from cdxml_toolkit.mcp_runtime.codex_config import update_config


def test_config_update_preserves_settings_comments_and_environment(tmp_path):
    python = tmp_path / "python.exe"
    python.write_bytes(b"fixture")
    config = tmp_path / "config.toml"
    config.write_text(
        """# retained comment
[mcp_servers.cdxml-toolkit]
command = "old-python"
args = ["old-server.py"]
startup_timeout_sec = 120.0
tool_timeout_sec = 600.0
default_tools_approval_mode = "approve"

[mcp_servers.cdxml-toolkit.env]
HTTP_PROXY = "http://127.0.0.1:7897"
""",
        encoding="utf-8",
    )
    digest = hashlib.sha256(config.read_bytes()).hexdigest()

    result = update_config(config, python, expected_sha256=digest)
    data = tomlkit.parse(config.read_text(encoding="utf-8"))
    server = data["mcp_servers"]["cdxml-toolkit"]

    assert result["changed"] is True
    assert config.read_text(encoding="utf-8").startswith("# retained comment")
    assert server["startup_timeout_sec"] == 120.0
    assert server["tool_timeout_sec"] == 600.0
    assert server["default_tools_approval_mode"] == "approve"
    assert server["env"]["HTTP_PROXY"] == "http://127.0.0.1:7897"
    assert list(server["args"]) == [
        "-m",
        "cdxml_toolkit.mcp_runtime",
        "--profile",
        "codex",
    ]


def test_config_update_rejects_changed_source(tmp_path):
    python = tmp_path / "python.exe"
    python.write_bytes(b"fixture")
    config = tmp_path / "config.toml"
    config.write_text("[mcp_servers]\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match="changed"):
        update_config(config, python, expected_sha256="0" * 64)
