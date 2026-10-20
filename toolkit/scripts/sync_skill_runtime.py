"""Export lightweight compatibility files from the package into a ChemDraw Skill."""

from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import sys


RUNTIME_MODULES = {
    "artifact_safety": "artifact_safety",
    "chemistry_compare": "chemistry_compare",
    "chemscript_sdk": "chemscript_sdk",
    "chemscript_sdk_runtime": "chemscript_sdk_runtime",
    "decimer_api": "decimer_api",
    "extended_tools": "extended_tools",
    "install_decimer_models": "install_decimer_models",
    "mcp_compat": "mcp_compat",
    "mcp_server": "mcp_server",
    "native_io": "native_io",
    "native_renderer": "native_renderer",
    "office_objects": "office_objects",
    "official_overrides": "official_overrides",
    "process_control": "process_control",
    "remote_tools": "remote_tools",
    "resource_lock": "resource_lock",
    "runtime_diagnostics": "runtime_diagnostics",
    "runtime_discovery": "runtime_discovery",
    "structure_fidelity": "structure_fidelity",
    "telemetry": "telemetry",
    "tool_registry": "tool_registry",
    "tool_worker": "tool_worker",
    "generate_tool_reference": "generate_reference",
}

RUNTIME_TESTS = {
    "test_figure_revision.py",
    "test_figure_validation.py",
    "test_artifact_safety.py",
    "test_chemistry_compare.py",
    "test_capabilities.py",
    "test_chemscript_sdk.py",
    "test_codex_config.py",
    "test_decimer_api.py",
    "test_extended_tools.py",
    "test_generate_reference.py",
    "test_http_transport.py",
    "test_install_decimer_models.py",
    "test_mcp_compat.py",
    "test_mcp_stdio.py",
    "test_native_io.py",
    "test_native_renderer.py",
    "test_office_objects.py",
    "test_process_control.py",
    "test_runtime_diagnostics.py",
    "test_structure_fidelity.py",
    "test_worker_runtime.py",
}


REFERENCE_EXPORTS = {
    "mcp-signatures.md": Path("docs/mcp-tools.md"),
    "mcp-schema.json": Path("docs/mcp-schema.json"),
}


def _wrapper_source(module_name: str) -> str:
    bootstrap = ''
    if module_name == 'runtime_discovery':
        bootstrap = '''    import os as _os
    from pathlib import Path as _Path

    # Optional native COM must not block portable runtime discovery.
    # Also supports the pinned runtime baseline before native discovery was split.
    _runtime.REQUIRED_IMPORTS = tuple(
        name for name in _runtime.REQUIRED_IMPORTS if name != "win32com.client"
    )
    # The runtime package cannot infer the location of this Skill proxy.
    if not _os.environ.get("CHEMDRAW_SKILL_ROOT") and not any(
        arg == "--skill-root" or arg.startswith("--skill-root=")
        for arg in _sys.argv[1:]
    ):
        _sys.argv.extend(["--skill-root", str(_Path(__file__).resolve().parent.parent)])
'''
    return f'''"""Compatibility proxy for cdxml_toolkit.mcp_runtime.{module_name}."""

from __future__ import annotations

from importlib import import_module as _import_module
import sys as _sys

_runtime = _import_module("cdxml_toolkit.mcp_runtime.{module_name}")

if __name__ == "__main__":
{bootstrap}\
    _main = getattr(_runtime, "main", None)
    if _main is None:
        raise SystemExit("This compatibility module has no command-line interface.")
    raise SystemExit(_main())
else:
    _sys.modules[__name__] = _runtime
'''


def export_skill(repo_root: Path, skill_root: Path) -> None:
    scripts = skill_root / "scripts"
    references = skill_root / "references"
    runtime_tests = repo_root / "tests" / "runtime"
    scripts.mkdir(parents=True, exist_ok=True)
    references.mkdir(parents=True, exist_ok=True)

    for skill_name, package_name in sorted(RUNTIME_MODULES.items()):
        (scripts / f"{skill_name}.py").write_text(
            _wrapper_source(package_name), encoding="utf-8", newline="\n"
        )

    for filename in sorted(RUNTIME_TESTS):
        shutil.copyfile(runtime_tests / filename, scripts / filename)

    for skill_name, source_relative in REFERENCE_EXPORTS.items():
        shutil.copyfile(repo_root / source_relative, references / skill_name)


def check_skill(repo_root: Path, skill_root: Path) -> list[str]:
    """Return missing or stale files managed by this exporter."""
    problems: list[str] = []
    scripts = skill_root / "scripts"
    references = skill_root / "references"

    for skill_name, package_name in sorted(RUNTIME_MODULES.items()):
        target = scripts / f"{skill_name}.py"
        expected = _wrapper_source(package_name)
        if not target.is_file():
            problems.append(f"missing: {target}")
        elif target.read_text(encoding="utf-8") != expected:
            problems.append(f"stale: {target}")

    runtime_tests = repo_root / "tests" / "runtime"
    for filename in sorted(RUNTIME_TESTS):
        source = runtime_tests / filename
        target = scripts / filename
        if not target.is_file():
            problems.append(f"missing: {target}")
        elif target.read_bytes() != source.read_bytes():
            problems.append(f"stale: {target}")

    for skill_name, source_relative in REFERENCE_EXPORTS.items():
        source = repo_root / source_relative
        target = references / skill_name
        if not target.is_file():
            problems.append(f"missing: {target}")
        elif target.read_bytes() != source.read_bytes():
            problems.append(f"stale: {target}")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("skill_root", type=Path)
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="report missing or stale managed Skill files without changing them",
    )
    args = parser.parse_args()
    repo_root = args.repo_root.resolve()
    skill_root = args.skill_root.resolve()
    if args.check:
        problems = check_skill(repo_root, skill_root)
        if problems:
            print("\n".join(problems), file=sys.stderr)
            return 1
        print(f"Skill runtime export is current: {skill_root}")
        return 0
    export_skill(repo_root, skill_root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
