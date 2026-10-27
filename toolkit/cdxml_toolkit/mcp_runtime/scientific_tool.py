"""MCP wrapper for the scientific workflows: TLC plates, apparatus, NMR, plots and mechanisms."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from . import artifact_safety

# operation -> the suffix of its single output file, or None when it writes a directory
OPERATIONS = {
    "tlc": ".cdxml",
    "apparatus": ".cdxml",
    "mechanism": ".cdxml",
    "nmr": None,
    "plot": None,
}
MAX_SPEC_BYTES = 5 * 1024 * 1024


def scientific_workflow(operation: str, spec_path: str, output_path: str) -> dict[str, Any]:
    """Draw or analyse a scientific figure from a JSON spec file: tlc, apparatus, mechanism, nmr or plot.

    tlc, apparatus and mechanism write one editable .cdxml at output_path; nmr and plot write
    a new directory (figures, the full data as CSV and a JSON analysis with the source file's
    SHA-256). Relative file names inside the spec resolve against the spec's folder. The spec
    formats are in the scientific workflows reference (examples for each operation ship with
    the toolkit). Nothing is recognised or invented: peaks and integrals come from the supplied
    processed spectrum, plots from the supplied columns. Output is written to a staging
    location and published only when the workflow succeeds; an existing output_path is never
    replaced.
    """
    if operation not in OPERATIONS:
        raise ValueError(f"operation must be one of: {', '.join(OPERATIONS)}")
    spec = Path(spec_path).expanduser().resolve()
    if not spec.is_file():
        raise ValueError(f"spec_path is not a file: {spec}")
    if spec.stat().st_size > MAX_SPEC_BYTES:
        raise ValueError(f"spec file is larger than {MAX_SPEC_BYTES} bytes")
    from ..scientific.__main__ import run

    suffix = OPERATIONS[operation]
    if suffix is not None:
        target = artifact_safety.resolve_destination(source=spec, output_path=output_path, tag=operation, suffix=suffix)
        with artifact_safety.staging_file(target) as staged:
            result = run(operation, spec, staged)
            artifact_safety.validate_artifact(staged)
            result = artifact_safety.rewrite_paths(result, staged, target)
            artifact_safety.publish_file(staged, target)
        files = [target]
    else:
        target = artifact_safety.resolve_directory_destination(source=spec, output_dir=output_path, tag=operation)
        with artifact_safety.staging_directory(target) as staged:
            produced = staged / target.name
            result = run(operation, spec, produced)
            result = artifact_safety.rewrite_paths(result, produced, target)
            artifact_safety.publish_directory(produced, target)
        files = sorted(target.rglob("*"))
    return {
        "ok": True,
        "outputs": {"operation": operation, "output_path": str(target), "result": result},
        "warnings": [],
        "metadata": {"network_used": False, "artifacts": artifact_safety.artifact_records(files)},
    }


SCIENTIFIC_TOOLS = {"scientific_workflow": scientific_workflow}
