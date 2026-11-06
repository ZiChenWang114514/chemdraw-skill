"""Single collision-checked registry shared by MCP and worker processes."""

from __future__ import annotations

from dataclasses import dataclass
import inspect
import sys
from typing import Any, Callable

from . import mcp_compat
mcp_compat.install_legacy_fastmcp_alias()

from cdxml_toolkit.mcp_server import server as upstream

from .chemistry_compare import COMPARISON_TOOLS
from .chemscript_sdk import CHEMSCRIPT_SDK_TOOLS
from .capabilities import SYSTEM_TOOLS
from .extended_tools import PUBLIC_TOOLS
from .official_overrides import OFFICIAL_OVERRIDES
from .remote_tools import REMOTE_TOOLS
from .figure_tools import FIGURE_TOOLS
from .markush_tools import MARKUSH_TOOLS
from .com_call import COM_TOOLS
from .object_tools import OBJECT_TOOLS
from .report_tools import REPORT_TOOLS
from .scientific_tool import SCIENTIFIC_TOOLS
from .engine_tools import ENGINE_TOOLS
from .live_chemdraw import LIVE_CHEMDRAW_TOOLS
from .figure_draw import draw_figure
from .publication_figure import publication_figure


def _load_acs_builder():
    import importlib.util
    from pathlib import Path

    script_path = Path(__file__).resolve().parents[3] / "skill" / "chemdraw" / "scripts" / "acs_builder.py"
    if script_path.is_file():
        mod_spec = importlib.util.spec_from_file_location("chemdraw_skill_acs_builder", script_path)
        if mod_spec is not None and mod_spec.loader is not None:
            module = importlib.util.module_from_spec(mod_spec)
            mod_spec.loader.exec_module(module)
            return module
    import acs_builder  # type: ignore[import-not-found]
    return acs_builder


def build_acs_figure(
    spec: dict[str, Any] | str,
    output_path: str | None = None,
    render: bool = False,
) -> dict[str, Any]:
    """Build an ACS Document 1996 CDXML figure from an acs_builder JSON spec.

    Supports molecule, conformer (chair, newman, haworth, fischer, norbornane), text,
    arrow, box, and label_box objects, plus ring_fills, atom_halos, multi_attachments,
    ts_bracket, orbital, and interaction styling.

    Args:
        spec: Spec dict, JSON string, or path to a .json spec file.
        output_path: Optional destination .cdxml path (never overwrites an existing file).
        render: If True, also render a native 300 dpi PNG beside the CDXML when ChemDraw is available.
    """
    import json
    from pathlib import Path
    import tempfile
    from . import artifact_safety

    source_anchor: Path | None = None
    if isinstance(spec, dict):
        spec_dict = spec
    elif isinstance(spec, str):
        stripped = spec.lstrip("\ufeff").strip()
        if stripped.startswith("{"):
            spec_dict = json.loads(stripped)
        else:
            candidate = Path(stripped).expanduser().resolve()
            if not candidate.is_file():
                raise FileNotFoundError(f"ACS spec file not found: {candidate}")
            source_anchor = candidate
            spec_dict = json.loads(candidate.read_text(encoding="utf-8-sig"))
    else:
        raise ValueError("spec must be a dict, JSON string, or path to a JSON file")

    if not isinstance(spec_dict, dict) or not isinstance(spec_dict.get("objects"), list):
        raise ValueError('spec must be a JSON object with an "objects" list')

    acs_builder = _load_acs_builder()
    destination = artifact_safety.resolve_destination(
        source=source_anchor,
        output_path=output_path,
        tag="acs-figure",
        suffix=".cdxml",
    )
    with artifact_safety.staging_file(destination) as staged:
        with tempfile.TemporaryDirectory(prefix="acs-spec-") as tmp_dir:
            spec_file = Path(tmp_dir) / "spec.json"
            spec_file.write_text(json.dumps(spec_dict, ensure_ascii=False), encoding="utf-8")
            acs_builder.build_from_spec(str(spec_file), str(staged))
        artifact_safety.validate_artifact(staged)
        artifact_safety.publish_file(staged, destination)

    cdxml_text = destination.read_text(encoding="utf-8")
    files = [destination]
    png_path: str | None = None
    warnings: list[str] = []
    native_render = "not_requested"
    if render:
        from .official_overrides import render_to_png

        png_dest = destination.with_suffix(".png")
        try:
            rendered = render_to_png(str(destination), output_path=str(png_dest))
            if isinstance(rendered, dict) and rendered.get("ok"):
                png_path = str(rendered.get("output") or png_dest)
                if Path(png_path).is_file():
                    files.append(Path(png_path))
                native_render = "ok"
            else:
                native_render = "unrendered_draft"
                warnings.append("Native ChemDraw rendering was unavailable; returning unrendered CDXML draft.")
        except Exception as exc:
            native_render = "unrendered_draft"
            warnings.append(f"Native ChemDraw rendering was unavailable ({exc}); returning unrendered CDXML draft.")

    artifacts = artifact_safety.artifact_records(files)
    outputs = {
        "output_path": str(destination),
        "cdxml_path": str(destination),
        "png_path": png_path,
        "native_render": native_render,
    }
    return {
        "ok": True,
        "output_path": str(destination),
        "cdxml_path": str(destination),
        "cdxml": cdxml_text,
        "png_path": png_path,
        "native_render": native_render,
        "outputs": outputs,
        "warnings": warnings,
        "artifacts": artifacts,
        "metadata": {"network_used": False, "artifacts": artifacts},
    }


@dataclass(frozen=True)
class ToolSpec:
    name: str
    function: Callable[..., Any]
    title: str | None
    description: str
    annotations: Any = None
    return_json_text: bool = False
    group: str = "official"
    resource_class: str | None = None
    timeout_seconds: int | None = None


CHEMDRAW_COM_TOOLS = {
    "chemdraw_com_call",
    "parse_reaction",
    "convert_cdx_cdxml",
    "render_to_png",
    "draw_figure",
    "extract_cdxml_from_office",
    "embed_cdxml_in_office",
    "clean_scheme_layout",
    "merge_reaction_schemes",
    "polish_reaction_scheme",
    "render_cdxml_files",
    "fill_office_template",
    "batch_embed_cdxml_in_office",
    "inspect_chemdraw_objects_in_office",
    "replace_chemdraw_objects_in_office",
    "diagnose_runtime",
    "markush_compile",
    "stoichiometry_grid",
}


# ChemScript runs in-process on Windows; the macOS emulation drives ChemDraw itself.
MAC_CHEMDRAW_TOOLS = {
    "batch_compare_molecules",
    "chemdraw_chemical_properties",
    "compare_molecules",
    "execute_chemscript_sdk",
    "inspect_chemscript_sdk",
    "structure_to_name",
}


def _resource_class(name: str, platform: str | None = None) -> str | None:
    platform = platform or sys.platform
    if name in CHEMDRAW_COM_TOOLS or (platform == "darwin" and name in MAC_CHEMDRAW_TOOLS):
        return "chemdraw_com"
    return None


def _tool_timeout(name: str) -> int | None:
    return {
        "modify_molecule": 90,
        "compare_molecules": 120,
        "batch_compare_molecules": 300,
        "inspect_chemscript_sdk": 240,
        "structure_to_name": 300,
        "execute_chemscript_sdk": 300,
        "publication_figure": 600,
        "draw_figure": 300,
        "chemdraw_com_call": 240,
        "chemdraw_chemical_properties": 600,
        "markush_compile": 180,
        "markush_detect": 120,
        "stoichiometry_grid": 300,
        "recognize_structure": 1800,
        "extract_structures_from_document": 3600,
        "predict_products": 900,
        "predict_conditions": 1200,
        "predict_nmr": 1200,
        "predict_retrosynthesis": 1200,
    }.get(name)


def _merge_named_tools(existing: dict, incoming: dict, *, source: str) -> dict:
    collisions = sorted(set(existing).intersection(incoming))
    if collisions:
        raise RuntimeError(f"Tool registry collision from {source}: {', '.join(collisions)}")
    return {**existing, **incoming}


PROFILE_EXTENSION_TOOLS = {
    "office": {
        "batch_embed_cdxml_in_office",
        "fill_office_template",
        "inspect_chemdraw_objects_in_office",
        "replace_chemdraw_objects_in_office",
        "render_cdxml_files",
    },
    "analysis": {
        "analyze_lcms_series",
        "assemble_lab_book",
        "discover_experiment_files",
        "parse_scifinder_rdf",
        "scientific_workflow",
    },
    "chemscript": {
        "batch_compare_molecules",
        "chemdraw_chemical_properties",
        "compare_molecules",
        "execute_chemscript_sdk",
        "inspect_chemscript_sdk",
        "structure_to_name",
    },
}
DEFAULT_PROFILE = "full"
# Earlier releases called the full tool set "codex"; existing client configurations that
# pass `--profile codex` keep working through this alias.
PROFILE_ALIASES = {"codex": DEFAULT_PROFILE}
SUPPORTED_PROFILES = {"core", DEFAULT_PROFILE, *PROFILE_EXTENSION_TOOLS}
PROFILE_CHOICES = tuple(sorted(SUPPORTED_PROFILES | set(PROFILE_ALIASES)))


def normalize_profile(profile: str | None = None) -> str:
    """Return the canonical profile name; None means CHEMDRAW_MCP_PROFILE or the default."""
    import os

    selected = (profile or os.environ.get("CHEMDRAW_MCP_PROFILE") or DEFAULT_PROFILE).strip().lower()
    return PROFILE_ALIASES.get(selected, selected)


def build_registry(profile: str | None = None) -> dict[str, ToolSpec]:
    official: dict[str, ToolSpec] = {}
    for tool in upstream.mcp._tool_manager.list_tools():
        override = OFFICIAL_OVERRIDES.get(tool.name)
        function = override or tool.fn
        upstream_description = inspect.cleandoc(tool.description or inspect.getdoc(tool.fn) or tool.name)
        description = upstream_description
        if override is not None:
            description = (
                f"{upstream_description}\n\nSafety override: "
                f"{inspect.getdoc(override) or 'transactional artifact publication'}"
            )
        official[tool.name] = ToolSpec(
            name=tool.name,
            function=function,
            title=tool.title,
            description=description,
            annotations=tool.annotations,
            group="official",
            resource_class=_resource_class(tool.name),
            timeout_seconds=_tool_timeout(tool.name),
        )

    remote = {
        name: ToolSpec(
            name=name,
            function=function,
            title=name.replace("_", " ").title(),
            description=inspect.getdoc(function) or name,
            return_json_text=True,
            group="remote",
            resource_class=_resource_class(name),
            timeout_seconds=_tool_timeout(name),
        )
        for name, function in REMOTE_TOOLS.items()
    }
    extended_functions = _merge_named_tools(
        PUBLIC_TOOLS, COMPARISON_TOOLS, source="molecule comparison tools"
    )
    extended_functions = _merge_named_tools(
        extended_functions, CHEMSCRIPT_SDK_TOOLS, source="ChemScript SDK tools"
    )
    extended_functions = _merge_named_tools(
        extended_functions, SYSTEM_TOOLS, source="system tools"
    )
    extended_functions = _merge_named_tools(
        extended_functions, FIGURE_TOOLS, source="figure and RDKit tools"
    )
    extended_functions = _merge_named_tools(
        extended_functions, {"publication_figure": publication_figure}, source="publication figures"
    )
    extended_functions = _merge_named_tools(
        extended_functions, {"draw_figure": draw_figure}, source="figure drawing"
    )
    extended_functions = _merge_named_tools(
        extended_functions, OBJECT_TOOLS, source="object and catalog tools"
    )
    extended_functions = _merge_named_tools(
        extended_functions, COM_TOOLS, source="ChemDraw COM tools"
    )
    extended_functions = _merge_named_tools(
        extended_functions, MARKUSH_TOOLS, source="Markush tools"
    )
    extended_functions = _merge_named_tools(
        extended_functions, REPORT_TOOLS, source="report tools"
    )
    extended_functions = _merge_named_tools(
        extended_functions, SCIENTIFIC_TOOLS, source="scientific workflow tools"
    )
    extended_functions = _merge_named_tools(
        extended_functions, ENGINE_TOOLS, source="prediction engine tools"
    )
    extended_functions = _merge_named_tools(
        extended_functions, LIVE_CHEMDRAW_TOOLS, source="live ChemDraw session tools"
    )
    extended_functions = _merge_named_tools(
        extended_functions, {"build_acs_figure": build_acs_figure}, source="ACS figure builder"
    )
    extended = {
        name: ToolSpec(
            name=name,
            function=function,
            title=name.replace("_", " ").title(),
            description=inspect.getdoc(function) or name,
            return_json_text=True,
            group="extended",
            resource_class=_resource_class(name),
            timeout_seconds=_tool_timeout(name),
        )
        for name, function in extended_functions.items()
    }
    registry = _merge_named_tools(official, remote, source="remote tools")
    registry = _merge_named_tools(registry, extended, source="extended tools")
    selected = PROFILE_ALIASES.get((profile or DEFAULT_PROFILE).strip().lower(),
                                   (profile or DEFAULT_PROFILE).strip().lower())
    if selected not in SUPPORTED_PROFILES:
        expected = ", ".join(sorted(SUPPORTED_PROFILES))
        raise ValueError(f"Unknown MCP profile {selected!r}; choose one of: {expected}")
    if selected == DEFAULT_PROFILE:
        return registry
    names = set(official) | {"get_toolkit_capabilities"}
    if selected != "core":
        names |= PROFILE_EXTENSION_TOOLS[selected]
    return {name: spec for name, spec in registry.items() if name in names}
