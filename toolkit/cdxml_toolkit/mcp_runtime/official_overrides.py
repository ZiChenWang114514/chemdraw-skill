"""Transactional replacements for official MCP tools that write artifacts."""

from __future__ import annotations

import inspect
import json
import os
from pathlib import Path
import tempfile
from typing import Any, Optional, Union

from . import artifact_safety
from . import mcp_compat
from . import native_io
from . import native_renderer
mcp_compat.install_legacy_fastmcp_alias()


_TEMP_OUTPUT = Path(tempfile.gettempdir()) / "codex-chemdraw"


def _raw_upstream(function):
    wrapped = getattr(function, "__wrapped__", None)
    return wrapped if inspect.isfunction(wrapped) else function


def _validate_generated(path: Path, *, office_objects: int | None = None) -> None:
    artifact_safety.validate_artifact(path)
    from .extended_tools import _assert_output

    _assert_output(path, expected_ole_objects=office_objects)


def _destination(
    source: str | Path | None,
    output_path: str | None,
    *,
    tag: str,
    suffix: str,
) -> Path:
    return artifact_safety.resolve_destination(
        source=source,
        output_path=output_path,
        tag=tag,
        suffix=suffix,
        base_dir=_TEMP_OUTPUT,
    )


def _publish_upstream_result(
    result: Any,
    staged: Path,
    destination: Path,
    *,
    validator=_validate_generated,
) -> Any:
    if not isinstance(result, dict) or not result.get("ok"):
        return result
    validator(staged)
    artifact_safety.publish_file(staged, destination)
    rewritten = artifact_safety.rewrite_paths(result, staged, destination)
    rewritten["size"] = destination.stat().st_size
    return artifact_safety.with_artifacts(rewritten, [destination])


def _run_file_tool(destination: Path, call, *, validator=_validate_generated) -> Any:
    with artifact_safety.staging_file(destination) as staged:
        result = call(staged)
        return _publish_upstream_result(
            result, staged, destination, validator=validator
        )


def draw_molecule(mol_json: dict, output_path: Optional[str] = None) -> dict:
    """Draw a molecule through a validated no-overwrite staging file."""
    from cdxml_toolkit.mcp_server.server import draw_molecule as upstream

    upstream = _raw_upstream(upstream)

    smiles = mol_json.get("smiles") if isinstance(mol_json, dict) else None
    if isinstance(mol_json, str):
        try:
            decoded = json.loads(mol_json)
            smiles = decoded.get("smiles") if isinstance(decoded, dict) else None
        except json.JSONDecodeError:
            smiles = None
    if not mol_json or not smiles:
        return upstream(mol_json, output_path=output_path)
    destination = _destination(None, output_path, tag="molecule", suffix=".cdxml")

    def draw_and_validate(staged: Path):
        result = upstream(mol_json, output_path=str(staged))
        if isinstance(result, dict) and result.get("ok"):
            from .structure_fidelity import repair_and_validate_drawn_cdxml

            validation = repair_and_validate_drawn_cdxml(str(smiles), staged)
            metadata = dict(result.get("metadata") or {})
            metadata["chemistry_validation"] = validation
            result = {**result, "metadata": metadata}
        return result

    return _run_file_tool(
        destination,
        draw_and_validate,
    )


def render_scheme(
    yaml_text: Optional[str] = None,
    compact_text: Optional[str] = None,
    json_path: Optional[str] = None,
    layout: str = "auto",
    output_path: Optional[str] = None,
) -> str:
    """Render a scheme through a validated no-overwrite staging file."""
    from cdxml_toolkit.mcp_server.server import render_scheme as upstream

    upstream = _raw_upstream(upstream)

    if not any(value is not None for value in (yaml_text, compact_text, json_path)):
        return upstream(
            yaml_text=yaml_text,
            compact_text=compact_text,
            json_path=json_path,
            layout=layout,
            output_path=output_path,
        )
    anchor = json_path if json_path else None
    destination = _destination(anchor, output_path, tag="rendered", suffix=".cdxml")
    return _run_file_tool(
        destination,
        lambda staged: upstream(
            yaml_text=yaml_text,
            compact_text=compact_text,
            json_path=json_path,
            layout=layout,
            output_path=str(staged),
        ),
    )


def parse_reaction(
    cdxml: Optional[str] = None,
    cdx: Optional[str] = None,
    csv: Optional[str] = None,
    rxn: Optional[str] = None,
    input_dir: Optional[str] = None,
    output_path: Optional[str] = None,
) -> dict:
    """Parse a reaction and atomically publish its JSON descriptor."""
    from cdxml_toolkit.mcp_server.server import parse_reaction as upstream

    upstream = _raw_upstream(upstream)

    if not any((cdxml, cdx, csv, rxn, input_dir)):
        return upstream()
    anchor = next((value for value in (cdxml, cdx, csv, rxn) if value), None)
    if anchor is None and input_dir:
        anchor = Path(input_dir) / "reaction"
    destination = _destination(anchor, output_path, tag="parsed", suffix=".json")
    def invoke(staged: Path):
        if input_dir:
            with native_io.ascii_input_directory(input_dir) as staged_directory:
                native_dir, replacements = staged_directory
                if cdx:
                    with native_io.ascii_inputs([cdx]) as native_paths:
                        replacements[os.path.normcase(str(native_paths[0]))] = str(
                            Path(cdx).expanduser().resolve()
                        )
                        result = upstream(
                            cdxml=cdxml,
                            cdx=str(native_paths[0]),
                            csv=csv,
                            rxn=rxn,
                            input_dir=str(native_dir),
                            output_path=str(staged),
                        )
                        native_io.rewrite_json_paths(staged, replacements)
                        return result
                result = upstream(
                    cdxml=cdxml,
                    cdx=cdx,
                    csv=csv,
                    rxn=rxn,
                    input_dir=str(native_dir),
                    output_path=str(staged),
                )
                native_io.rewrite_json_paths(staged, replacements)
                return result
        if cdx:
            with native_io.ascii_inputs([cdx]) as native_paths:
                result = upstream(
                    cdxml=cdxml,
                    cdx=str(native_paths[0]),
                    csv=csv,
                    rxn=rxn,
                    output_path=str(staged),
                )
                native_io.rewrite_json_paths(
                    staged,
                    {
                        os.path.normcase(str(native_paths[0])): str(
                            Path(cdx).expanduser().resolve()
                        )
                    },
                )
                return result
        return upstream(
            cdxml=cdxml,
            cdx=cdx,
            csv=csv,
            rxn=rxn,
            output_path=str(staged),
        )

    return _run_file_tool(destination, invoke)


def parse_scheme(cdxml_path: str, output_path: Optional[str] = None) -> dict:
    """Parse a scheme and atomically publish its JSON descriptor."""
    from cdxml_toolkit.mcp_server.server import parse_scheme as upstream

    upstream = _raw_upstream(upstream)

    if not cdxml_path or not cdxml_path.strip():
        return upstream(cdxml_path, output_path=output_path)
    destination = _destination(cdxml_path, output_path, tag="parsed", suffix=".json")
    return _run_file_tool(
        destination,
        lambda staged: upstream(cdxml_path, output_path=str(staged)),
    )


def convert_cdx_cdxml(
    input_path: str,
    output_path: Optional[str] = None,
) -> dict:
    """Convert CDX/CDXML through a validated no-overwrite staging file."""
    from cdxml_toolkit.mcp_server.server import convert_cdx_cdxml as upstream

    upstream = _raw_upstream(upstream)

    if not input_path or not input_path.strip():
        return upstream(input_path, output_path=output_path)
    source = artifact_safety.validate_input_file(
        input_path, suffixes=(".cdx", ".cdxml")
    )
    suffix = ".cdxml" if source.suffix.lower() == ".cdx" else ".cdx"
    destination = _destination(source, output_path, tag="converted", suffix=suffix)
    return _run_file_tool(
        destination,
        lambda staged: native_io.bridge_file(
            source,
            staged,
            lambda native_source, native_destination: upstream(
                str(native_source), output_path=str(native_destination)
            ),
            output_kind=suffix.lstrip("."),
        ),
    )


def parse_analysis_file(
    pdf_path: str,
    output_path: Optional[str] = None,
) -> dict:
    """Parse an analysis file and atomically publish verified JSON."""
    from cdxml_toolkit.mcp_server.server import parse_analysis_file as upstream

    upstream = _raw_upstream(upstream)

    if not pdf_path or not pdf_path.strip():
        return upstream(pdf_path, output_path=output_path)
    destination = _destination(pdf_path, output_path, tag="parsed", suffix=".json")
    return _run_file_tool(
        destination,
        lambda staged: upstream(pdf_path, output_path=str(staged)),
    )


def format_lab_entry(
    entries_json: Union[list[dict], dict, str],
    output_path: Optional[str] = None,
) -> dict:
    """Format a lab entry and atomically publish verified text."""
    from cdxml_toolkit.mcp_server.server import format_lab_entry as upstream

    upstream = _raw_upstream(upstream)

    if entries_json in (None, [], {}, ""):
        return upstream(entries_json, output_path=output_path)
    destination = _destination(None, output_path, tag="lab_entry", suffix=".txt")
    return _run_file_tool(
        destination,
        lambda staged: upstream(entries_json, output_path=str(staged)),
    )


def extract_cdxml_from_office(
    file_path: str,
    output_dir: Optional[str] = None,
) -> dict:
    """Extract every object transactionally; publish nothing on partial failure."""
    if not file_path or not file_path.strip():
        from cdxml_toolkit.mcp_server.server import extract_cdxml_from_office as upstream

        upstream = _raw_upstream(upstream)
        return upstream(file_path, output_dir=output_dir)

    from cdxml_toolkit.office.ole_extractor import extract_from_office

    source = artifact_safety.validate_input_file(
        file_path, suffixes=(".pptx", ".docx", ".xlsx", ".xls")
    )
    destination = artifact_safety.resolve_directory_destination(
        source=source, output_dir=output_dir, tag="chemdraw"
    )
    try:
        with artifact_safety.staging_directory(destination) as staged:
            results = extract_from_office(
                str(source), output_dir=str(staged), output_format="cdxml"
            )
            objects = []
            failures = []
            for result in results:
                entry: dict[str, Any] = {"source_path": result.source_path}
                if result.cdxml_output:
                    artifact_safety.validate_artifact(result.cdxml_output)
                    entry["cdxml_output"] = result.cdxml_output
                if result.cdx_output:
                    artifact_safety.validate_artifact(result.cdx_output)
                    entry["cdx_output"] = result.cdx_output
                if result.error:
                    entry["error"] = result.error
                    failures.append(str(result.error))
                objects.append(entry)
            if failures:
                return {
                    "ok": False,
                    "error": "Extraction was rolled back: " + "; ".join(failures),
                    "input": str(source),
                }
            artifact_safety.publish_directory(staged, destination)
        rewritten = artifact_safety.rewrite_paths(objects, staged, destination)
        paths = artifact_safety.paths_from_value(rewritten)
        return artifact_safety.with_artifacts(
            {
                "ok": True,
                "input": str(source),
                "output_dir": str(destination),
                "count": len(rewritten),
                "objects": rewritten,
            },
            paths,
        )
    except Exception as exc:
        return {
            "ok": False,
            "error": f"Extraction failed validation: {exc}",
            "input": str(source),
        }


def _build_embedded_office(source: Path, destination: Path) -> dict[str, Any]:
    from cdxml_toolkit.office.ole_embedder import (
        batch_convert,
        build_docx,
        build_pptx,
        get_cdxml_content_size,
    )
    from .extended_tools import _build_chemdraw_ole

    converted = native_io.batch_convert_cdxml([source], batch_convert)
    if len(converted) != 1 or not isinstance(converted[0], dict):
        return {"ok": False, "error": "ChemDraw COM conversion returned no output"}
    item = converted[0]
    cdx_data = item.get("cdx_data")
    emf_data = item.get("emf_data")
    if not isinstance(cdx_data, (bytes, bytearray, memoryview)) or not cdx_data:
        return {"ok": False, "error": "ChemDraw COM conversion returned empty CDX"}
    if not isinstance(emf_data, (bytes, bytearray, memoryview)) or not emf_data:
        return {"ok": False, "error": "ChemDraw COM conversion returned empty EMF"}
    width, height = get_cdxml_content_size(str(source))
    items = [
        {
            "ole_data": _build_chemdraw_ole(bytes(cdx_data)),
            "emf_data": bytes(emf_data),
            "width_emu": width,
            "height_emu": height,
            "name": item.get("name") or source.stem,
        }
    ]
    if destination.suffix.lower() == ".pptx":
        build_pptx(items, str(destination))
    else:
        build_docx(items, str(destination))
    return {
        "ok": True,
        "input_cdxml": str(source),
        "output": str(destination),
        "format": destination.suffix.lstrip("."),
        "num_objects_embedded": 1,
    }


def embed_cdxml_in_office(
    cdxml_path: str,
    office_path: str,
    output_path: str | None = None,
) -> dict:
    """Create a new validated PPTX or DOCX and reject all existing targets."""
    source = artifact_safety.validate_input_file(cdxml_path, suffixes=(".cdxml",))
    office = Path(office_path).expanduser().resolve()
    if office.suffix.lower() not in {".pptx", ".docx"}:
        return {"ok": False, "error": "office_path must end in .pptx or .docx"}
    if office.exists():
        return {
            "ok": False,
            "error": (
                "Refusing to use an existing Office file because the upstream embedder "
                "cannot preserve its content; choose a new office_path"
            ),
        }
    try:
        destination = artifact_safety.resolve_destination(
            source=None,
            output_path=output_path or str(office),
            tag="office",
            suffix=office.suffix,
        )
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}

    def validate(path: Path) -> None:
        _validate_generated(path, office_objects=1)

    try:
        result = _run_file_tool(
            destination,
            lambda staged: _build_embedded_office(source, staged),
            validator=validate,
        )
        if isinstance(result, dict) and result.get("ok"):
            result["output"] = str(destination)
            result["created_new_file"] = True
        return result
    except Exception as exc:
        return {"ok": False, "error": f"Embedding failed validation: {exc}"}


def render_to_png(
    cdxml_path: str,
    output_path: Optional[str] = None,
) -> dict:
    """Render CDXML to a validated PNG through a staging file."""
    if not cdxml_path or not cdxml_path.strip():
        from cdxml_toolkit.mcp_server.server import render_to_png as upstream

        upstream = _raw_upstream(upstream)
        return upstream(cdxml_path, output_path=output_path)
    source = artifact_safety.validate_input_file(cdxml_path, suffixes=(".cdxml",))
    destination = _destination(source, output_path, tag="rendered", suffix=".png")
    return _run_file_tool(
        destination,
        lambda staged: native_io.bridge_file(
            source,
            staged,
            lambda native_source, native_destination: {
                "ok": True,
                "output": native_renderer.render_cdxml(
                    native_source, native_destination, dpi=300
                ),
            },
            output_kind="png",
        ),
    )


OFFICIAL_OVERRIDES = {
    "draw_molecule": draw_molecule,
    "render_scheme": render_scheme,
    "parse_reaction": parse_reaction,
    "parse_scheme": parse_scheme,
    "convert_cdx_cdxml": convert_cdx_cdxml,
    "parse_analysis_file": parse_analysis_file,
    "format_lab_entry": format_lab_entry,
    "extract_cdxml_from_office": extract_cdxml_from_office,
    "embed_cdxml_in_office": embed_cdxml_in_office,
    "render_to_png": render_to_png,
}
