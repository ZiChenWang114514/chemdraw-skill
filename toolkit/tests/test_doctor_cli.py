from __future__ import annotations

import json
from unittest import mock

from cdxml_toolkit import doctor


def test_doctor_default_does_not_configure_chemscript(capsys):
    with mock.patch.object(doctor, "_print_diagnostics", return_value=False), mock.patch.object(
        doctor, "_setup_chemscript"
    ) as setup:
        assert doctor.main(["--no-tests"]) == 0
    setup.assert_not_called()
    assert "was not changed" in capsys.readouterr().out


def test_doctor_json_returns_machine_readable_report(capsys):
    report = {"ok": True, "outputs": {"capabilities": {}}, "metadata": {"read_only": True}}
    with mock.patch(
        "cdxml_toolkit.mcp_runtime.runtime_diagnostics.diagnose_runtime",
        return_value=report,
    ):
        assert doctor.main(["--json"]) == 0
    assert json.loads(capsys.readouterr().out) == report


def test_doctor_on_macos_reports_chemdraw_app_and_chemscript_backend(capsys, tmp_path):
    app = tmp_path / "ChemDraw.app"
    with mock.patch.object(doctor.sys, "platform", "darwin"), mock.patch.object(
        doctor, "_check_dependency", return_value=(True, "stub")
    ), mock.patch(
        "cdxml_toolkit.chemdraw.mac_automation.find_application", return_value=app
    ):
        assert doctor._print_diagnostics() is True
    out = capsys.readouterr().out
    assert "pywin32" not in out
    assert "ChemDraw COM" not in out
    assert "ChemDraw.app" in out
    assert "macOS backend" in out


def test_doctor_on_macos_without_chemdraw_reports_it_missing(capsys):
    with mock.patch.object(doctor.sys, "platform", "darwin"), mock.patch.object(
        doctor, "_check_dependency", return_value=(True, "stub")
    ), mock.patch(
        "cdxml_toolkit.chemdraw.mac_automation.find_application", return_value=None
    ):
        assert doctor._print_diagnostics() is False
    assert "MISSING" in capsys.readouterr().out


def test_chemscript_setup_on_macos_needs_no_configuration(capsys):
    with mock.patch.object(doctor.sys, "platform", "darwin"):
        doctor._setup_chemscript(assume_yes=True)
    assert "no configuration" in capsys.readouterr().out
