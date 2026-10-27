"""A CHEMDRAW_EXE that points nowhere must stop native rendering before ChemDraw is started."""
import pytest

from cdxml_toolkit.mcp_runtime import native_renderer


def test_a_missing_chemdraw_exe_fails_before_any_automation_starts(monkeypatch, tmp_path):
    monkeypatch.setenv("CHEMDRAW_EXE", str(tmp_path / "ChemDraw.exe"))
    with pytest.raises(native_renderer.NativeRenderError) as caught:
        native_renderer._acquire_application()
    assert caught.value.error_code == "chemdraw_not_found"
    assert "CHEMDRAW_EXE" in caught.value.public_message
