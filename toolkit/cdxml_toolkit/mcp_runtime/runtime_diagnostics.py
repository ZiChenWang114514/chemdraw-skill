"""Offline runtime capability diagnostics with opt-in native probes."""

from __future__ import annotations

import argparse
from contextlib import redirect_stdout
import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Any

from .process_control import (
    _assign_kill_job,
    _close_job,
    _terminate_process_tree,
    cleanup_automation_processes,
    snapshot_automation_processes,
)


NATIVE_PROBE_TIMEOUT_SECONDS = 75
CHEMSCRIPT_PROBE_TIMEOUT_SECONDS = 30
OFFICE_PROBE_TIMEOUT_SECONDS = 60
PROBE_HARD_LIMIT_SECONDS = 240


def _status(available: bool, **details: Any) -> dict[str, Any]:
    return {"status": "available" if available else "missing", **details}


def _module_available(name: str) -> bool:
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError):
        return False


def _distribution(name: str) -> dict[str, Any]:
    try:
        version = importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return _status(False, detail=f"Python distribution is not installed: {name}")
    return _status(True, version=version)


def _toolkit_distribution() -> dict[str, Any]:
    community = _distribution("cdxml-toolkit-community")
    legacy = _distribution("cdxml-toolkit")
    try:
        import cdxml_toolkit

        module_version = getattr(cdxml_toolkit, "__version__", "unknown")
        module_path = str(Path(cdxml_toolkit.__file__).resolve())
    except (ImportError, AttributeError, OSError):
        module_version = "unknown"
        module_path = None
    installed = {
        "cdxml-toolkit-community": community.get("version")
        if community.get("status") == "available"
        else None,
        "cdxml-toolkit": legacy.get("version")
        if legacy.get("status") == "available"
        else None,
    }
    present = [name for name, version in installed.items() if version]
    return _status(
        bool(module_path),
        version=module_version,
        path=module_path,
        distributions=installed,
        conflict=len(present) > 1,
    )


def _chemdraw_capabilities() -> tuple[dict[str, Any], dict[str, Any]]:
    from . import runtime_discovery
    try:
        discovery = runtime_discovery.find_chemdraw()
        executable = _status(True, path=discovery.path, source=discovery.source)
    except RuntimeError as exc:
        executable = _status(False, detail=str(exc))
    command = runtime_discovery._registry_local_server_command()
    registered = bool(command)
    com = _status(
        registered,
        registered=registered,
        **({"local_server": command} if command else {}),
    )
    return executable, com


def _java_opsin_capabilities() -> tuple[dict[str, Any], dict[str, Any]]:
    java_home = os.environ.get("JAVA_HOME")
    java_candidates = []
    if java_home:
        java_candidates.extend(
            [Path(java_home) / "bin" / "java.exe", Path(java_home) / "bin" / "java"]
        )
    path_java = shutil.which("java")
    if path_java:
        java_candidates.append(Path(path_java))
    java = next((path.resolve() for path in java_candidates if path.is_file()), None)

    opsin_candidates = []
    for variable in ("OPSIN_JAR", "CDXML_TOOLKIT_OPSIN_JAR"):
        value = os.environ.get(variable)
        if value:
            opsin_candidates.append(Path(value).expanduser())
    opsin = next((path.resolve() for path in opsin_candidates if path.is_file()), None)
    return (
        _status(java is not None, **({"path": str(java)} if java else {})),
        _status(
            opsin is not None,
            **({"path": str(opsin)} if opsin else {"detail": "OPSIN JAR was not configured"}),
        ),
    )


def _decimer_capability() -> dict[str, Any]:
    configured = os.environ.get("DECIMER_MODEL_DIR")
    root = (
        Path(configured).expanduser().resolve()
        if configured
        else (Path.home() / ".data" / "DECIMER-V2").resolve()
    )
    models = {}
    for key, relative in (
        ("standard", "DECIMER_model/saved_model.pb"),
        ("handdrawn", "DECIMER_HandDrawn_model/saved_model.pb"),
    ):
        marker = root / relative
        receipt = marker.parent / ".model.json"
        models[key] = {
            "status": "available" if marker.is_file() else "missing",
            "marker": str(marker),
            "receipt": str(receipt) if receipt.is_file() else None,
            "integrity": "recorded" if receipt.is_file() else "unverified",
        }
    available = all(item["status"] == "available" for item in models.values())
    return _status(available, root=str(root), models=models)


def _office_capability() -> dict[str, Any]:
    dependencies = {
        "python-pptx": _module_available("pptx"),
        "python-docx": _module_available("docx"),
        "olefile": _module_available("olefile"),
        "win32com": _module_available("win32com.client"),
    }
    ready = all(dependencies.values())
    return {
        "status": "unverified" if ready else "missing",
        "dependencies": dependencies,
        "detail": (
            "Dependencies are present; enable run_office_probe for native validation"
            if ready
            else "One or more Office/OLE dependencies are missing"
        ),
    }


def _native_probe() -> dict[str, Any]:
    from cdxml_toolkit.naming.mol_builder import resolve_compound
    from PIL import Image

    from . import official_overrides
    with tempfile.TemporaryDirectory(prefix="chemdraw-native-probe-") as temp_dir:
        root = Path(temp_dir)
        cdxml = root / "aspirin.cdxml"
        png = root / "aspirin.png"
        molecule = resolve_compound("aspirin", use_network=False)
        drawn = official_overrides.draw_molecule(molecule, output_path=str(cdxml))
        if not isinstance(drawn, dict) or not drawn.get("ok"):
            raise RuntimeError(f"CDXML probe failed: {drawn}")
        rendered = official_overrides.render_to_png(str(cdxml), output_path=str(png))
        if not isinstance(rendered, dict) or not rendered.get("ok"):
            raise RuntimeError(f"PNG probe failed: {rendered}")
        with Image.open(png) as image:
            image.verify()
        with Image.open(png) as image:
            dimensions = list(image.size)
        return {
            "status": "available",
            "cdxml_bytes": cdxml.stat().st_size,
            "png_bytes": png.stat().st_size,
            "png_dimensions": dimensions,
        }


def _chemscript_probe() -> dict[str, Any]:
    bridge = subprocess.run(
        [
            sys.executable,
            "-m",
            "cdxml_toolkit.chemdraw.chemscript_bridge",
            "ping",
        ],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=25,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    detail = (bridge.stdout.strip() or bridge.stderr.strip())[:1000]
    return {
        "status": "available" if bridge.returncode == 0 else "missing",
        "detail": detail or (
            "ChemScript bridge ping succeeded"
            if bridge.returncode == 0
            else "ChemScript bridge ping failed"
        ),
        "returncode": bridge.returncode,
    }


def _office_probe(suffix: str | None = None) -> dict[str, Any]:
    from cdxml_toolkit.naming.mol_builder import resolve_compound

    from . import official_overrides
    from .extended_tools import _validate_office_package

    with tempfile.TemporaryDirectory(prefix="chemdraw-office-probe-") as temp_dir:
        root = Path(temp_dir)
        cdxml = root / "aspirin.cdxml"
        drawn = official_overrides.draw_molecule(
            resolve_compound("aspirin", use_network=False), output_path=str(cdxml)
        )
        if not isinstance(drawn, dict) or not drawn.get("ok"):
            raise RuntimeError(f"Office source drawing failed: {drawn}")
        suffixes = (suffix,) if suffix else (".pptx", ".docx")
        details = {}
        for current_suffix in suffixes:
            office = root / f"probe{current_suffix}"
            result = official_overrides.embed_cdxml_in_office(
                str(cdxml), str(office)
            )
            if not isinstance(result, dict) or not result.get("ok"):
                raise RuntimeError(f"{current_suffix} OLE probe failed: {result}")
            validation = _validate_office_package(office, expected_ole_objects=1)
            details[current_suffix.lstrip(".")] = {
                "bytes": office.stat().st_size,
                "ole_objects": validation["ole_objects"],
                "chemdraw_objects": validation["chemdraw_objects"],
            }
        if suffix:
            key = suffix.lstrip(".")
            return {
                "status": "available",
                "format": key,
                "bytes": details[key]["bytes"],
                "objects": details[key]["chemdraw_objects"],
            }
        return {
            "status": "available",
            "pptx_objects": details["pptx"]["chemdraw_objects"],
            "docx_objects": details["docx"]["chemdraw_objects"],
            "files": details,
        }


def _run_probe(probe) -> dict[str, Any]:
    try:
        return probe()
    except Exception as exc:
        return {"status": "missing", "detail": str(exc)}


def _probe_stage(stage: str) -> dict[str, Any]:
    if stage == "chemscript":
        return _run_probe(_chemscript_probe)
    if stage == "native":
        return _run_probe(_native_probe)
    if stage == "pptx":
        return _run_probe(lambda: _office_probe(".pptx"))
    if stage == "docx":
        return _run_probe(lambda: _office_probe(".docx"))
    return {"status": "missing", "detail": f"Unknown probe stage: {stage}"}


def _audit_stage_processes(
    before: dict[int, dict[str, Any]],
    *,
    stage_pid: int,
    timed_out: bool,
    deadline: float,
) -> dict[str, Any]:
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return {
                "status": "unconfirmed",
                "terminated_pids": [],
                "lingering_pids": [],
                "unknown_pids": [],
                "failed_pids": [],
                "detail": "Automation cleanup audit exceeded the stage deadline",
            }
        after = snapshot_automation_processes(timeout_seconds=min(5.0, remaining))
        new_pids = set(after) - set(before)
        if not new_pids:
            return {
                "status": "confirmed",
                "terminated_pids": [],
                "lingering_pids": [],
                "unknown_pids": [],
                "failed_pids": [],
            }
        if timed_out or time.monotonic() >= deadline:
            return cleanup_automation_processes(
                before,
                after,
                stage_pid=stage_pid,
                terminate=timed_out,
                deadline=deadline,
            )
        time.sleep(min(0.5, max(0.0, deadline - time.monotonic())))


def _run_probe_stage(stage: str, timeout_seconds: int) -> dict[str, Any]:
    started = time.monotonic()
    stage_deadline = started + timeout_seconds
    try:
        before = snapshot_automation_processes(
            timeout_seconds=min(5.0, max(0.1, stage_deadline - time.monotonic()))
        )
    except Exception as exc:
        return {
            "status": "missing",
            "stage": stage,
            "detail": f"Automation process baseline failed: {exc}",
            "cleanup": {"status": "unconfirmed", "unknown_pids": []},
            "duration_seconds": round(time.monotonic() - started, 3),
        }

    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "cdxml_toolkit.mcp_runtime.runtime_diagnostics",
            "--probe-stage",
            stage,
        ],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=os.environ.copy(),
        creationflags=(
            getattr(subprocess, "CREATE_NO_WINDOW", 0)
            | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        ),
    )
    job = _assign_kill_job(process)
    timed_out = False
    stdout = ""
    stderr = ""
    job_released = True
    cleanup_reserve = min(5.0, max(0.25, timeout_seconds * 0.1))
    execution_deadline = stage_deadline - cleanup_reserve
    try:
        try:
            stdout, stderr = process.communicate(
                timeout=max(0.05, execution_deadline - time.monotonic())
            )
        except subprocess.TimeoutExpired:
            timed_out = True
            _terminate_process_tree(process, job, deadline=stage_deadline)
            job = None
            remaining = stage_deadline - time.monotonic()
            if remaining > 0:
                try:
                    stdout, stderr = process.communicate(timeout=remaining)
                except subprocess.TimeoutExpired:
                    stdout = ""
                    stderr = "Probe subprocess did not exit before the stage deadline"
    finally:
        job_released = _close_job(job)

    try:
        cleanup = _audit_stage_processes(
            before,
            stage_pid=process.pid,
            timed_out=timed_out,
            deadline=(
                time.monotonic()
                if timed_out
                else min(stage_deadline, time.monotonic() + 15)
            ),
        )
    except Exception as exc:
        cleanup = {
            "status": "unconfirmed",
            "unknown_pids": [],
            "detail": f"Automation process cleanup audit failed: {exc}",
        }
    if not job_released:
        cleanup = {
            "status": "unconfirmed",
            "unknown_pids": cleanup.get("unknown_pids", []),
            "detail": "Job Object kill-on-close could not be safely disarmed",
        }

    duration = round(time.monotonic() - started, 3)
    if timed_out:
        result: dict[str, Any] = {
            "status": "missing",
            "stage": stage,
            "detail": f"{stage} probe exceeded {timeout_seconds} seconds",
            "error_code": "native_probe_timeout",
            "timed_out": True,
        }
    else:
        try:
            decoded = json.loads(stdout)
            result = decoded if isinstance(decoded, dict) else {}
        except json.JSONDecodeError:
            result = {
                "status": "missing",
                "detail": "Probe subprocess returned invalid JSON",
            }
        if not result:
            result = {
                "status": "missing",
                "detail": (stderr or "Probe subprocess returned no result")[:1000],
            }
        result["stage"] = stage
    result["duration_seconds"] = duration
    result["timeout_seconds"] = timeout_seconds
    result["cleanup"] = cleanup
    if cleanup.get("status") != "confirmed" and result.get("status") == "available":
        result["status"] = "missing"
        result["detail"] = "Probe completed but automation cleanup was unconfirmed"
    return result


def _not_run_stage(stage: str, reason: str) -> dict[str, Any]:
    return {"status": "not_run", "stage": stage, "reason": reason}


def diagnose_runtime(
    run_native_probe: bool = False,
    run_office_probe: bool = False,
    run_chemscript_probe: bool = False,
) -> dict[str, Any]:
    """Report local runtime capabilities; native probes are explicit and temporary."""
    capabilities: dict[str, Any] = {
        "python": _status(
            True,
            path=str(Path(sys.executable).resolve()),
            version=sys.version.split()[0],
        ),
        "cdxml_toolkit": _toolkit_distribution(),
        "mcp_sdk": _distribution("mcp"),
    }
    capabilities["chemdraw"], capabilities["chemdraw_com"] = (
        _chemdraw_capabilities()
    )
    capabilities["chemscript"] = {
        "status": (
            "unverified"
            if _module_available("cdxml_toolkit.chemdraw.chemscript_bridge")
            else "missing"
        ),
        "detail": "Enable run_native_probe to validate ChemDraw automation",
    }
    capabilities["java"], capabilities["opsin"] = _java_opsin_capabilities()
    capabilities["office"] = _office_capability()
    capabilities["decimer_models"] = _decimer_capability()

    try:
        from .tool_registry import build_registry

        tool_count = len(build_registry(profile=os.environ.get("CHEMDRAW_MCP_PROFILE", "codex")))
        capabilities["tool_registry"] = _status(True, count=tool_count)
    except Exception as exc:
        tool_count = 0
        capabilities["tool_registry"] = _status(False, detail=str(exc), count=0)

    requested = []
    cleanup_confirmed = True
    if run_native_probe or run_chemscript_probe:
        capabilities["chemscript_probe"] = _run_probe_stage(
            "chemscript", CHEMSCRIPT_PROBE_TIMEOUT_SECONDS
        )
        chemscript = capabilities["chemscript_probe"]
        capabilities["chemscript"] = _status(
            chemscript.get("status") == "available",
            detail=chemscript.get("detail") or "ChemScript bridge ping failed",
        )
        requested.append("chemscript_probe")
    if run_native_probe:
        capabilities["native_probe"] = _run_probe_stage(
            "native", NATIVE_PROBE_TIMEOUT_SECONDS
        )
        native = capabilities["native_probe"]
        cleanup_confirmed = native.get("cleanup", {}).get("status") == "confirmed"
        requested.append("native_probe")
    if run_office_probe:
        if cleanup_confirmed:
            pptx = _run_probe_stage("pptx", OFFICE_PROBE_TIMEOUT_SECONDS)
        else:
            pptx = _not_run_stage("pptx", "cleanup_unconfirmed")
        if pptx.get("cleanup", {}).get("status") == "unconfirmed":
            docx = _not_run_stage("docx", "cleanup_unconfirmed")
        elif pptx.get("status") == "not_run":
            docx = _not_run_stage("docx", "cleanup_unconfirmed")
        else:
            docx = _run_probe_stage("docx", OFFICE_PROBE_TIMEOUT_SECONDS)
        office_available = all(
            stage.get("status") == "available" for stage in (pptx, docx)
        )
        capabilities["office_probe"] = {
            "status": "available" if office_available else "missing",
            "pptx_objects": pptx.get("objects", 0),
            "docx_objects": docx.get("objects", 0),
            "stages": {"pptx": pptx, "docx": docx},
        }
        if office_available:
            capabilities["office"] = _status(
                True, detail="Temporary PPTX and DOCX OLE probes succeeded"
            )
        requested.append("office_probe")

    required = ["python", "cdxml_toolkit", "mcp_sdk", "tool_registry", *requested]
    ok = all(capabilities[name]["status"] == "available" for name in required)
    warnings = []
    for name, capability in capabilities.items():
        if capability["status"] == "missing" and name not in {"java", "opsin"}:
            warnings.append(
                f"{name}: {capability.get('detail') or 'capability is unavailable'}"
            )
    return {
        "ok": ok,
        "outputs": {"capabilities": capabilities},
        "warnings": warnings,
        "metadata": {
            "read_only": not (
                run_native_probe or run_office_probe or run_chemscript_probe
            ),
            "network_used": False,
            "tool_count": tool_count,
            "probe_hard_limit_seconds": PROBE_HARD_LIMIT_SECONDS,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native-probe", action="store_true")
    parser.add_argument("--chemscript-probe", action="store_true")
    parser.add_argument("--office-probe", action="store_true")
    parser.add_argument(
        "--probe-stage", choices=("chemscript", "native", "pptx", "docx")
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    if args.probe_stage:
        with redirect_stdout(sys.stderr):
            result = _probe_stage(args.probe_stage)
        print(json.dumps(result, separators=(",", ":")))
        return 0 if result.get("status") == "available" else 1
    result = diagnose_runtime(
        args.native_probe,
        args.office_probe,
        args.chemscript_probe,
    )
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        for name, capability in result["outputs"]["capabilities"].items():
            print(f"{name}: {capability['status']}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
