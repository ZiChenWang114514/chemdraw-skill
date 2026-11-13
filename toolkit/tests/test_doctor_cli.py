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


def _setup_64bit(run, tmp_path):
    dlls = {"bitness": 64, "managed_path": "m.dll", "native_path": "n.dll", "dll_dir": str(tmp_path), "assembly": "a"}
    with mock.patch.object(doctor.sys, "platform", "win32"), mock.patch(
        "cdxml_toolkit.chemdraw.chemscript_bridge._find_chemdraw_root", return_value=tmp_path
    ), mock.patch(
        "cdxml_toolkit.chemdraw.chemscript_bridge._find_chemscript_dlls", return_value=dlls
    ), mock.patch(
        "cdxml_toolkit.chemdraw.chemscript_bridge._find_python_for_chemscript", return_value=None
    ), mock.patch(
        "cdxml_toolkit.chemdraw.chemscript_bridge._load_config", return_value={}
    ), mock.patch(
        "cdxml_toolkit.chemdraw.chemscript_bridge._save_config"
    ) as save, mock.patch.object(doctor.subprocess, "run", side_effect=run):
        doctor._setup_chemscript(assume_yes=True)
    return save


def test_chemscript_setup_installs_a_supported_pythonnet_with_a_time_limit(tmp_path):
    calls = []

    def run(command, **kwargs):
        calls.append((command, kwargs))
        return doctor.subprocess.CompletedProcess(command, 0, "", "")

    save = _setup_64bit(run, tmp_path)
    (command, kwargs), = calls
    assert command[-1] == doctor.PYTHONNET_REQUIREMENT == "pythonnet>=3.0"
    assert kwargs["timeout"] > 0
    save.assert_called_once()


def test_a_hung_chemscript_install_ends_with_a_message(tmp_path, capsys):
    def run(command, **kwargs):
        raise doctor.subprocess.TimeoutExpired(command, kwargs["timeout"])

    save = _setup_64bit(run, tmp_path)
    save.assert_not_called()
    assert "timed out" in capsys.readouterr().out


def test_find_chemdraw_root_prefers_registry_view_with_chemscript_dlls(tmp_path):
    import sys
    import types
    from cdxml_toolkit.chemdraw import chemscript_bridge

    x86_root = tmp_path / "Program Files (x86)" / "Vendor"
    x64_root = tmp_path / "Program Files" / "Vendor"
    x86_exe = x86_root / "ChemOffice" / "ChemDraw" / "ChemDraw.exe"
    x64_exe = x64_root / "ChemOffice" / "ChemDraw" / "ChemDraw.exe"
    x86_exe.parent.mkdir(parents=True)
    x64_exe.parent.mkdir(parents=True)
    x86_exe.write_bytes(b"exe")
    x64_exe.write_bytes(b"exe")

    cs_net = x64_root / "ChemOffice" / "ChemScript" / "Lib" / "Net"
    cs_net.mkdir(parents=True)
    (cs_net / "CambridgeSoft.ChemScript.dll").write_bytes(b"managed" * 10)
    (cs_net.parent / "ChemScript.dll").write_bytes(b"native" * 100)

    fake_winreg = types.SimpleNamespace(
        HKEY_CLASSES_ROOT=1,
        HKEY_LOCAL_MACHINE=2,
        KEY_READ=1,
        KEY_WOW64_64KEY=256,
        KEY_WOW64_32KEY=512,
        OpenKey=lambda root, subkey, _zero=0, access=1: (root, subkey, access),
        QueryValue=lambda key, _name="": (
            "{FAKE-CLSID}" if key[0] == 1
            else (f'"{x64_exe}" /Automation' if (key[2] & 256) else f'"{x86_exe}" /Automation')
        ),
        CloseKey=lambda _key: None,
    )
    with mock.patch.dict(sys.modules, {"winreg": fake_winreg}), mock.patch.object(
        chemscript_bridge, "_dll_bitness", return_value=64
    ):
        assert chemscript_bridge._find_chemdraw_root() == str(x64_root)


def test_chemscript_bridge_self_heals_stale_python_path_in_config(tmp_path):
    import sys
    from cdxml_toolkit.chemdraw import chemscript_bridge

    saved = []
    stale_cfg = {
        "python32": str(tmp_path / "deleted" / "python.exe"),
        "bitness": 64,
        "dll_dir": str(tmp_path),
        "assembly": "CambridgeSoft.ChemScript",
    }
    with mock.patch.object(chemscript_bridge.mac_automation, "is_macos", return_value=False), mock.patch.object(
        chemscript_bridge, "_load_config", return_value=stale_cfg
    ), mock.patch.object(
        chemscript_bridge, "_save_config", side_effect=lambda cfg: saved.append(dict(cfg))
    ):
        bridge = chemscript_bridge.ChemScriptBridge()
    assert bridge._python32 == sys.executable
    assert saved and saved[-1]["python32"] == sys.executable
