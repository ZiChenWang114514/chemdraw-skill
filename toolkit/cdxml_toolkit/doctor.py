#!/usr/bin/env python3
"""
cdxml-doctor — Diagnostic and test runner for cdxml-toolkit.

Reports dependency availability, runs the test suite, and prints
ChemScript setup instructions when needed.
"""

import os
import json
import subprocess
import sys


def _check_dependency(name, import_fn):
    """Try importing a dependency, return (ok, version_or_error)."""
    try:
        mod = import_fn()
        ver = getattr(mod, "__version__", getattr(mod, "version", "OK"))
        return True, str(ver)
    except Exception as e:
        return False, str(e).split("\n")[0][:60]


def _check_chemdraw_com():
    """Check if ChemDraw COM is registered (without launching it)."""
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_CLASSES_ROOT,
                             "ChemDraw.Application\\CLSID")
        winreg.CloseKey(key)
        return True, "registered"
    except Exception:
        return False, "not registered"


def _check_chemscript():
    """Check if ChemScript bridge is configured and working."""
    try:
        from cdxml_toolkit.chemdraw.chemscript_bridge import (
            ChemScriptBridge, _load_config,
        )
        cfg = _load_config()
        if not cfg.get("python32"):
            return False, "not configured (no python32 in config)"
        if not cfg.get("dll_dir"):
            return False, "not configured (no dll_dir in config)"
        cs = ChemScriptBridge()
        result = cs._call("ping")
        cs.close()
        if result.get("ok"):
            return True, "OK"
        return False, result.get("error", "ping failed")
    except Exception as e:
        return False, str(e).split("\n")[0][:60]


def _print_diagnostics():
    """Print system and dependency diagnostics."""
    print("=== cdxml-toolkit doctor ===\n")

    # System info
    try:
        from cdxml_toolkit import __version__ as pkg_ver
    except (ImportError, AttributeError):
        pkg_ver = "unknown"
    print(f"  Python:       {sys.version.split()[0]} ({sys.executable})")
    print(f"  Platform:     {sys.platform}")
    print(f"  Package:      {pkg_ver}")
    print()

    # Ensure bundled JRE is extracted before checking OPSIN
    # (py2opsin checks for java at import time)
    try:
        from cdxml_toolkit.resolve.jre_manager import ensure_java_on_path
        ensure_java_on_path(download=False)
    except Exception:
        pass

    # Dependencies
    checks = [
        ("RDKit", lambda: __import__("rdkit.Chem", fromlist=["Chem"])),
        ("PyYAML", lambda: __import__("yaml")),
        ("pywin32", lambda: __import__("win32com.client", fromlist=["client"])),
        ("OPSIN", lambda: __import__("py2opsin")),
        ("DECIMER", lambda: __import__("DECIMER")),
        ("pdfplumber", lambda: __import__("pdfplumber")),
        ("MCP", lambda: __import__("mcp")),
        ("pythonnet", lambda: __import__("pythonnet")),
    ]

    print("  Dependencies:")
    for name, fn in checks:
        ok, info = _check_dependency(name, fn)
        status = f"OK ({info})" if ok else f"MISSING ({info})"
        print(f"    {name:14s} {status}")

    # ChemDraw COM
    ok, info = _check_chemdraw_com()
    print(f"    {'ChemDraw COM':14s} {'OK' if ok else 'MISSING'} ({info})")

    # ChemScript
    cs_ok, cs_info = _check_chemscript()
    print(f"    {'ChemScript':14s} {'OK' if cs_ok else 'NOT CONFIGURED'} ({cs_info})")
    print()

    return cs_ok


def _setup_chemscript(*, assume_yes=False):
    """Detect ChemScript DLLs and interactively set up the environment."""
    from cdxml_toolkit.chemdraw.chemscript_bridge import (
        _find_chemdraw_root, _find_chemscript_dlls,
        _find_python_for_chemscript, _load_config, _save_config,
    )

    print("=== ChemScript setup ===\n")

    # Find DLLs
    root = _find_chemdraw_root()
    dll_info = None
    if root:
        dll_info = _find_chemscript_dlls(root)

    if not dll_info:
        print("  ChemScript DLLs not found.")
        print("  ChemDraw with ChemScript must be installed.")
        return

    bitness = dll_info.get("bitness")
    print(f"  Found ChemScript DLLs:")
    print(f"    Managed:  {dll_info['managed_path']} ({bitness}-bit)")
    print(f"    Native:   {dll_info['native_path']} ({bitness}-bit)")
    print()

    # Check if a suitable Python already exists
    py = _find_python_for_chemscript(bitness)
    if py:
        print(f"  Python for ChemScript: {py}")
        print("  Saving config...")
        cfg = _load_config()
        cfg["python32"] = py
        cfg["dll_dir"] = dll_info["dll_dir"]
        cfg["assembly"] = dll_info["assembly"]
        cfg["bitness"] = bitness
        _save_config(cfg)
        print("  ChemScript configured. Run cdxml-doctor again to verify.")
        print()
        return

    # Need to create a Python env
    if bitness == 64:
        # 64-bit: current interpreter works, just need pythonnet
        print("  64-bit ChemScript detected. Installing pythonnet...")
        r = subprocess.run(
            [sys.executable, "-m", "pip", "install", "pythonnet"],
            capture_output=True, text=True,
        )
        if r.returncode != 0:
            print(f"  Failed to install pythonnet: {r.stderr}")
            return
        print("  pythonnet installed. Saving config...")
        cfg = _load_config()
        cfg["python32"] = sys.executable
        cfg["dll_dir"] = dll_info["dll_dir"]
        cfg["assembly"] = dll_info["assembly"]
        cfg["bitness"] = bitness
        _save_config(cfg)
        print("  ChemScript configured. Run cdxml-doctor again to verify.")
        print()
        return

    if bitness != 32:
        print("  Could not determine DLL bitness. Cannot auto-configure.")
        return

    # 32-bit: need a 32-bit conda env
    # Find conda executable (it's a .bat on Windows, not directly callable)
    import shutil
    conda_exe = shutil.which("conda")
    if not conda_exe:
        # Derive from current Python path: .../miniconda3/envs/cdxml/python.exe
        # → .../miniconda3/Scripts/conda.exe
        conda_root = sys.executable
        for _ in range(3):  # walk up from envs/name/python.exe
            conda_root = os.path.dirname(conda_root)
        for candidate in [
            os.path.join(conda_root, "Scripts", "conda.exe"),
            os.path.join(conda_root, "condabin", "conda.bat"),
        ]:
            if os.path.isfile(candidate):
                conda_exe = candidate
                break
    if not conda_exe:
        print("  Could not find conda. Install it or add it to PATH.")
        return

    py32_path = os.path.join(
        os.path.dirname(os.path.dirname(conda_exe)),
        "envs", "chemscript32", "python.exe",
    )

    print("  32-bit ChemScript requires a 32-bit Python environment.")
    print("  The doctor will run the following commands:\n")
    print(f"    {conda_exe} create -n chemscript32 python=3.10 pip -y  (with CONDA_SUBDIR=win-32)")
    print(f"    {py32_path} -m pip install pythonnet")
    print()

    if assume_yes:
        answer = "y"
    else:
        try:
            answer = input("  Proceed? [y/N] ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\n  Skipped.")
            return

    if answer not in ("y", "yes"):
        print("  Skipped.")
        return

    # Step 1: create 32-bit conda env
    print("\n  Creating chemscript32 conda env...")
    env = os.environ.copy()
    env["CONDA_SUBDIR"] = "win-32"
    r = subprocess.run(
        [conda_exe, "create", "-n", "chemscript32", "python=3.10", "pip", "-y"],
        env=env, capture_output=True, text=True,
    )
    if r.returncode != 0:
        print(f"  Failed to create conda env:\n{r.stderr}")
        return
    print("  chemscript32 env created.")

    # Step 2: install pythonnet
    print("  Installing pythonnet in chemscript32...")
    r = subprocess.run(
        [py32_path, "-m", "pip", "install", "pythonnet"],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        print(f"  Failed to install pythonnet:\n{r.stderr}")
        return
    print("  pythonnet installed.")

    # Step 3: save config
    print("  Saving config...")
    cfg = _load_config()
    cfg["python32"] = py32_path
    cfg["dll_dir"] = dll_info["dll_dir"]
    cfg["assembly"] = dll_info["assembly"]
    cfg["bitness"] = bitness
    _save_config(cfg)
    print("  ChemScript configured. Run cdxml-doctor again to verify.")
    print()


def _run_tests():
    """Run the pytest test suite. Returns exit code."""
    print("=== Running tests ===\n")

    # Find tests directory
    try:
        import cdxml_toolkit
        pkg_dir = os.path.dirname(os.path.abspath(cdxml_toolkit.__file__))
        project_root = os.path.dirname(pkg_dir)
        tests_dir = os.path.join(project_root, "tests")
    except Exception:
        tests_dir = None

    if not tests_dir or not os.path.isdir(tests_dir):
        # Try relative to cwd
        tests_dir = os.path.join(os.getcwd(), "tests")

    if not os.path.isdir(tests_dir):
        print("  Tests directory not found.")
        print("  To run tests, cd into the cdxml-toolkit source directory first.")
        print()
        return 1

    try:
        import pytest
        return pytest.main([tests_dir, "-v", "--tb=short"])
    except ImportError:
        print("  pytest not installed. Run: pip install pytest")
        return 1


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(
        description="Diagnostic and test runner for cdxml-toolkit.",
    )
    parser.add_argument("--no-tests", action="store_true",
                        help="Skip running the test suite")
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print a machine-readable, read-only capability report",
    )
    parser.add_argument(
        "--configure-chemscript",
        action="store_true",
        help="Configure ChemScript after diagnostics",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Confirm ChemScript configuration without an interactive prompt",
    )
    args = parser.parse_args(argv)

    if args.yes and not args.configure_chemscript:
        parser.error("--yes requires --configure-chemscript")
    if args.json:
        if args.configure_chemscript:
            parser.error("--json cannot be combined with --configure-chemscript")
        from cdxml_toolkit.mcp_runtime.runtime_diagnostics import diagnose_runtime

        report = diagnose_runtime()
        print(json.dumps(report, indent=2, default=str))
        return 0 if report.get("ok") else 1

    cs_ok = _print_diagnostics()

    if not args.no_tests:
        exit_code = _run_tests()
        print()
    else:
        exit_code = 0

    if not cs_ok and args.configure_chemscript:
        _setup_chemscript(assume_yes=args.yes)
    elif not cs_ok:
        print("ChemScript configuration was not changed.")
        print("Run cdxml-doctor --no-tests --configure-chemscript when ready.")

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
