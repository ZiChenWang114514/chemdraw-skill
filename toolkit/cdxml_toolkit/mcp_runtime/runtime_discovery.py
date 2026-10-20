"""Discover portable ChemDraw Skill runtime paths on Windows."""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from typing import Iterable

try:
    import winreg
except ImportError:  # pragma: no cover - Windows is the supported platform.
    winreg = None


# Native/Office dependencies are checked only when those capabilities are requested.
REQUIRED_IMPORTS = ("cdxml_toolkit", "mcp", "rdkit")
PYTHON_PROBE_TIMEOUT_SECONDS = 30


@dataclass(frozen=True)
class Discovery:
    path: str
    source: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


def _existing_file(value: str | os.PathLike[str] | None) -> Path | None:
    if not value:
        return None
    candidate = Path(value).expanduser()
    return candidate.resolve() if candidate.is_file() else None


def _first_existing(candidates: Iterable[tuple[str, str]]) -> Discovery | None:
    for value, source in candidates:
        path = _existing_file(value)
        if path:
            return Discovery(str(path), source)
    return None


def _probe_python(
    executable: Path, timeout_seconds: int = PYTHON_PROBE_TIMEOUT_SECONDS
) -> str | None:
    """Return a diagnostic when a Python cannot import the MCP dependencies."""
    import_statement = "import " + ", ".join(REQUIRED_IMPORTS)
    try:
        completed = subprocess.run(
            [str(executable), "-c", import_statement],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except subprocess.TimeoutExpired:
        return f"required imports timed out after {timeout_seconds} seconds"
    except OSError as exc:
        return f"could not launch the runtime: {exc}"
    if completed.returncode == 0:
        return None
    detail = completed.stderr.strip() or completed.stdout.strip()
    if not detail:
        detail = f"process exited with code {completed.returncode}"
    return f"required imports failed: {detail[:2000]}"


def _strict_python(value: str, source: str, label: str) -> Discovery:
    path = _existing_file(value)
    if not path:
        raise RuntimeError(f"{label} points to a missing file: {value}")
    problem = _probe_python(path)
    if problem:
        raise RuntimeError(f"{label} is unusable: {path}: {problem}")
    return Discovery(str(path), source)


def _conda_environment_registry_candidates(home: Path) -> list[tuple[str, str]]:
    """Read Conda's per-user environment registry without invoking Conda."""
    registry = home / ".conda" / "environments.txt"
    try:
        entries = registry.read_text(encoding="utf-8-sig").splitlines()
    except (OSError, UnicodeError):
        return []

    environments = [Path(line.strip()) for line in entries if line.strip()]
    environments.sort(
        key=lambda path: (
            path.name.casefold() != "cdxml",
            os.path.normcase(str(path)),
        )
    )
    return [
        (str(environment / "python.exe"), "conda-environment-registry")
        for environment in environments
    ]


def _implicit_python_candidates() -> list[tuple[str, str]]:
    candidates: list[tuple[str, str]] = []
    conda_prefix = os.environ.get("CONDA_PREFIX")
    if conda_prefix:
        candidates.append((str(Path(conda_prefix) / "python.exe"), "active-conda"))
    candidates.append((sys.executable, "current-python"))
    path_python = shutil.which("python")
    if path_python:
        candidates.append((path_python, "PATH"))

    home = Path.home()
    candidates.extend(
        [
            (str(home / "miniconda3" / "envs" / "cdxml" / "python.exe"), "common-path"),
            (str(home / "anaconda3" / "envs" / "cdxml" / "python.exe"), "common-path"),
        ]
    )
    program_data = os.environ.get("ProgramData")
    if program_data:
        candidates.extend(
            [
                (
                    str(Path(program_data) / "miniconda3" / "envs" / "cdxml" / "python.exe"),
                    "common-path",
                ),
                (
                    str(Path(program_data) / "Anaconda3" / "envs" / "cdxml" / "python.exe"),
                    "common-path",
                ),
            ]
        )
    candidates.extend(_conda_environment_registry_candidates(home))
    return candidates


def find_python(explicit: str | None = None) -> Discovery:
    """Find and probe Python using explicit, environment, then implicit paths."""
    if explicit:
        path = _existing_file(explicit)
        if not path:
            raise RuntimeError(f"The explicit Python path does not exist: {explicit}")
        problem = _probe_python(path)
        if problem:
            raise RuntimeError(f"The explicit Python runtime is unusable: {path}: {problem}")
        return Discovery(str(path), "explicit")

    env_value = os.environ.get("CHEMDRAW_MCP_PYTHON")
    if env_value:
        return _strict_python(
            env_value, "environment", "CHEMDRAW_MCP_PYTHON"
        )

    rejected: list[str] = []
    seen: set[str] = set()
    for value, source in _implicit_python_candidates():
        path = _existing_file(value)
        if not path:
            continue
        key = os.path.normcase(str(path))
        if key in seen:
            continue
        seen.add(key)
        problem = _probe_python(path)
        if problem:
            rejected.append(f"{source} ({path}): {problem}")
            continue
        return Discovery(str(path), source)

    detail = "; ".join(rejected)
    suffix = f" Rejected candidates: {detail}" if detail else ""
    raise RuntimeError(
        "No usable Python runtime found. Set CHEMDRAW_MCP_PYTHON to the "
        f"cdxml-toolkit environment.{suffix}"
    )


def find_skill_root(explicit: str | None = None) -> Discovery:
    if explicit:
        path = Path(explicit).expanduser().resolve()
        if not (path / "SKILL.md").is_file():
            raise RuntimeError(f"The explicit skill root is invalid: {path}")
        return Discovery(str(path), "explicit")

    env_value = os.environ.get("CHEMDRAW_SKILL_ROOT")
    if env_value:
        path = Path(env_value).expanduser().resolve()
        if not (path / "SKILL.md").is_file():
            raise RuntimeError(f"CHEMDRAW_SKILL_ROOT is invalid: {path}")
        return Discovery(str(path), "environment")

    candidates = [
        (str(Path(__file__).resolve().parent.parent), "script-location"),
        (str(Path.home() / ".codex" / "skills" / "chemdraw"), "common-path"),
    ]
    for value, source in candidates:
        path = Path(value).expanduser().resolve()
        if (path / "SKILL.md").is_file():
            return Discovery(str(path), source)
    raise RuntimeError("ChemDraw Skill root not found. Set CHEMDRAW_SKILL_ROOT.")


def _extract_local_server_executable(command: str | None) -> str | None:
    """Extract an executable from a COM LocalServer32 command line."""
    if not command:
        return None
    value = os.path.expandvars(str(command)).strip()
    if not value:
        return None
    if value.startswith('"'):
        closing_quote = value.find('"', 1)
        if closing_quote < 0:
            return None
        return value[1:closing_quote].strip() or None
    match = re.match(r"^(.+?\.exe)(?:\s+.*)?$", value, flags=re.IGNORECASE)
    return match.group(1).strip() if match else None


def _registry_local_server_command() -> str | None:
    """Read HKCR ChemDraw.Application -> CLSID -> LocalServer32."""
    if winreg is None:
        return None
    try:
        with winreg.OpenKey(
            winreg.HKEY_CLASSES_ROOT, r"ChemDraw.Application\CLSID"
        ) as clsid_key:
            clsid = winreg.QueryValueEx(clsid_key, "")[0]
        with winreg.OpenKey(
            winreg.HKEY_CLASSES_ROOT, rf"CLSID\{clsid}\LocalServer32"
        ) as server_key:
            return str(winreg.QueryValueEx(server_key, "")[0])
    except (OSError, TypeError, ValueError):
        return None


def _common_chemdraw_candidates() -> list[Path]:
    bases: list[Path] = []
    for variable in ("ProgramW6432", "ProgramFiles", "ProgramFiles(x86)"):
        value = os.environ.get(variable)
        if value:
            bases.append(Path(value))
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        bases.append(Path(local_app_data) / "Programs")
    bases.extend(
        [
            Path(r"C:\Program Files"),
            Path(r"C:\Program Files (x86)"),
            Path(r"D:\Program Files"),
            Path(r"D:\Program Files (x86)"),
        ]
    )

    vendors = (
        "PerkinElmerInformatics",
        "Revvity",
        "Revvity Signals Software",
        "CambridgeSoft",
    )
    patterns = (
        "ChemOffice*/ChemDraw.exe",
        "ChemOffice*/ChemDraw/ChemDraw.exe",
        "ChemDraw*/ChemDraw.exe",
        "ChemDraw*/ChemDraw/ChemDraw.exe",
    )
    found: list[Path] = []
    seen_bases: set[str] = set()
    seen_files: set[str] = set()
    for base in bases:
        key = os.path.normcase(str(base))
        if key in seen_bases or not base.is_dir():
            continue
        seen_bases.add(key)
        base_matches: list[Path] = []
        for vendor in vendors:
            vendor_root = base / vendor
            if not vendor_root.is_dir():
                continue
            for pattern in patterns:
                base_matches.extend(vendor_root.glob(pattern))
        for path in sorted(
            (item for item in base_matches if item.is_file()),
            key=lambda item: os.path.normcase(str(item)),
            reverse=True,
        ):
            file_key = os.path.normcase(str(path.resolve()))
            if file_key not in seen_files:
                seen_files.add(file_key)
                found.append(path)
    return found


def find_chemdraw(explicit: str | None = None) -> Discovery:
    """Find ChemDraw.exe from explicit, environment, COM, then common paths."""
    if explicit:
        path = _existing_file(explicit)
        if not path:
            raise RuntimeError(f"The explicit ChemDraw path does not exist: {explicit}")
        return Discovery(str(path), "explicit")

    env_value = os.environ.get("CHEMDRAW_EXE")
    if env_value:
        path = _existing_file(env_value)
        if not path:
            raise RuntimeError(f"CHEMDRAW_EXE points to a missing file: {env_value}")
        return Discovery(str(path), "environment")

    registry_value = _extract_local_server_executable(
        _registry_local_server_command()
    )
    registry_path = _existing_file(registry_value)
    if registry_path:
        return Discovery(str(registry_path), "registry-HKCR")

    for candidate in _common_chemdraw_candidates():
        path = _existing_file(candidate)
        if path:
            return Discovery(str(path), "common-path")
    raise RuntimeError("ChemDraw.exe not found. Set CHEMDRAW_EXE.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--python")
    parser.add_argument("--skill-root")
    parser.add_argument("--chemdraw")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result: dict[str, dict[str, str] | None] = {
        "python": find_python(args.python).to_dict(),
        "skill_root": find_skill_root(args.skill_root).to_dict(),
    }
    try:
        result["chemdraw"] = find_chemdraw(args.chemdraw).to_dict()
    except RuntimeError:
        if args.chemdraw or os.environ.get("CHEMDRAW_EXE"):
            raise
        result["chemdraw"] = None
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        for name, value in result.items():
            print(f"{name}: {value['path'] if value else 'not found'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
