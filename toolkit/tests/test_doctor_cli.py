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
