from __future__ import annotations

from pathlib import Path
import subprocess
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "sync_skill_runtime.py"


def test_skill_export_uses_package_proxies_and_copies_generated_references(tmp_path):
    skill_root = tmp_path / "chemdraw"

    subprocess.run(
        [sys.executable, str(SCRIPT), str(skill_root)],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    server = (skill_root / "scripts" / "mcp_server.py").read_text(encoding="utf-8")
    http_test = (skill_root / "scripts" / "test_http_transport.py").read_text(
        encoding="utf-8"
    )
    assert 'import_module("cdxml_toolkit.mcp_runtime.mcp_server")' in server
    assert "def build_registry" not in server
    discovery=(skill_root/'scripts'/'runtime_discovery.py').read_text()
    assert 'CHEMDRAW_SKILL_ROOT' in discovery
    assert 'win32com.client' in discovery
    assert "from cdxml_toolkit.mcp_runtime import mcp_server" in http_test
    assert (skill_root / "scripts" / "test_capabilities.py").is_file()
    assert (skill_root / "scripts" / "test_codex_config.py").is_file()
    assert (skill_root / "references" / "mcp-signatures.md").read_bytes() == (
        REPO_ROOT / "docs" / "mcp-tools.md"
    ).read_bytes()
    assert (skill_root / "references" / "mcp-schema.json").read_bytes() == (
        REPO_ROOT / "docs" / "mcp-schema.json"
    ).read_bytes()


def test_exported_mcp_launcher_retains_command_line_interface(tmp_path):
    skill_root = tmp_path / "chemdraw"
    subprocess.run(
        [sys.executable, str(SCRIPT), str(skill_root)],
        cwd=REPO_ROOT,
        check=True,
    )

    result = subprocess.run(
        [sys.executable, str(skill_root / "scripts" / "mcp_server.py"), "--help"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode == 0
    assert "--profile" in result.stdout


def test_check_mode_detects_drift_and_accepts_current_export(tmp_path):
    skill_root = tmp_path / "chemdraw"
    subprocess.run(
        [sys.executable, str(SCRIPT), str(skill_root)],
        cwd=REPO_ROOT,
        check=True,
    )

    current = subprocess.run(
        [sys.executable, str(SCRIPT), str(skill_root), "--check"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert current.returncode == 0
    assert "is current" in current.stdout

    (skill_root / "scripts" / "test_http_transport.py").write_text(
        "stale\n", encoding="utf-8"
    )
    stale = subprocess.run(
        [sys.executable, str(SCRIPT), str(skill_root), "--check"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert stale.returncode == 1
    assert "stale:" in stale.stderr
    assert "test_http_transport.py" in stale.stderr
