"""Single collision-checked registry shared by MCP and worker processes."""

from __future__ import annotations

from dataclasses import dataclass
import importlib
import inspect
import json
from pathlib import Path
import sys
from typing import Any, Callable

# Where the extended tools live: (module in this package, attribute, what to call it in a
# collision report). The attribute is a {name: function} table, or one function registered
# under its own name. Modules are imported when a registry is built, or one at a time by
# load_tool, so a process that calls a single tool does not import every tool's dependencies.
EXTENDED_SOURCES = (
    ("extended_tools", "PUBLIC_TOOLS", "public tools"),
    ("chemistry_compare", "COMPARISON_TOOLS", "molecule comparison tools"),
    ("chemscript_sdk", "CHEMSCRIPT_SDK_TOOLS", "ChemScript SDK tools"),
    ("capabilities", "SYSTEM_TOOLS", "system tools"),
    ("figure_tools", "FIGURE_TOOLS", "figure and RDKit tools"),
    ("publication_figure", "publication_figure", "publication figures"),
    ("figure_draw", "draw_figure", "figure drawing"),
    ("object_tools", "OBJECT_TOOLS", "object and catalog tools"),
    ("com_call", "COM_TOOLS", "ChemDraw COM tools"),
    ("markush_tools", "MARKUSH_TOOLS", "Markush tools"),
    ("report_tools", "REPORT_TOOLS", "report tools"),
    ("scientific_tool", "SCIENTIFIC_TOOLS", "scientific workflow tools"),
    ("engine_tools", "ENGINE_TOOLS", "prediction engine tools"),
    ("live_chemdraw", "LIVE_CHEMDRAW_TOOLS", "live ChemDraw session tools"),
    ("tool_registry", "build_acs_figure", "ACS figure builder"),
    ("ui_apps", "UI_APP_TOOLS", "interactive UI apps"),
)
MANIFEST_PATH = Path(__file__).with_name("tool_manifest.json")


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

    from .. import acs_builder

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
    meta: dict[str, Any] | None = None


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


def _enrich_ui_meta(meta: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(meta, dict):
        return None
    ui_block = meta.get("ui")
    uri = ui_block.get("resourceUri") if isinstance(ui_block, dict) else None
    if not uri:
        return meta
    return {
        **meta,
        "openai/outputTemplate": uri,
        "openai/widgetAccessible": True,
    }


def _merge_named_tools(existing: dict, incoming: dict, *, source: str) -> dict:
    collisions = sorted(set(existing).intersection(incoming))
    if collisions:
        raise RuntimeError(f"Tool registry collision from {source}: {', '.join(collisions)}")
    return {**existing, **incoming}


PROFILE_EXTENSION_TOOLS = {
    # What a server lists by default: the core tools and the everyday drawing, checking and
    # diagnosis tools. A short list costs the client less context on every request.
    "standard": {
        "build_acs_figure",
        "check_reaction_balance",
        "chemdraw_object",
        "diagnose_runtime",
        "draw_figure",
        "export_structures",
        "molecule_report",
        "open_drawing_studio",  # the two interactive apps exist only through MCP
        "rdkit_workbench",
        "view_molecule_3d",
    },
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
FULL_PROFILE = "full"
# The profile a server uses when none is named. Code that builds a registry without naming a
# profile (the worker, the command line) gets every tool.
DEFAULT_PROFILE = "standard"
# Earlier releases called the full tool set "codex"; existing client configurations that
# pass `--profile codex` keep working through this alias.
PROFILE_ALIASES = {"codex": FULL_PROFILE}
SUPPORTED_PROFILES = {"core", FULL_PROFILE, *PROFILE_EXTENSION_TOOLS}
PROFILE_CHOICES = tuple(sorted(SUPPORTED_PROFILES | set(PROFILE_ALIASES)))


def normalize_profile(profile: str | None = None) -> str:
    """Return the canonical profile name; None means CHEMDRAW_MCP_PROFILE or the default."""
    import os

    selected = (profile or os.environ.get("CHEMDRAW_MCP_PROFILE") or DEFAULT_PROFILE).strip().lower()
    return PROFILE_ALIASES.get(selected, selected)


def _source(module: str, attribute: str) -> dict[str, Callable[..., Any]]:
    value = getattr(importlib.import_module(f"{__package__}.{module}"), attribute)
    return dict(value) if isinstance(value, dict) else {attribute: value}


def _official_specs() -> dict[str, ToolSpec]:
    from cdxml_toolkit.mcp_server import server as upstream

    from .official_overrides import OFFICIAL_OVERRIDES

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
    return official


def _remote_specs() -> dict[str, ToolSpec]:
    return {
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
        for name, function in _source("remote_tools", "REMOTE_TOOLS").items()
    }


def _extended_spec(name: str, function: Callable[..., Any]) -> ToolSpec:
    return ToolSpec(
        name=name,
        function=function,
        title=name.replace("_", " ").title(),
        description=inspect.getdoc(function) or name,
        return_json_text=True,
        group="extended",
        resource_class=_resource_class(name),
        timeout_seconds=_tool_timeout(name),
        meta=_enrich_ui_meta(getattr(function, "_chemdraw_mcp_meta", None)),
    )


def _all_specs() -> tuple[dict[str, ToolSpec], dict[str, tuple[str, str]]]:
    """Every tool, and for each extended tool the (module, attribute) it came from."""
    official = _official_specs()
    registry = _merge_named_tools(official, _remote_specs(), source="remote tools")
    extended: dict[str, Callable[..., Any]] = {}
    origin: dict[str, tuple[str, str]] = {}
    for module, attribute, label in EXTENDED_SOURCES:
        table = _source(module, attribute)
        extended = _merge_named_tools(extended, table, source=label)
        origin.update({name: (module, attribute) for name in table})
    registry = _merge_named_tools(
        registry,
        {name: _extended_spec(name, function) for name, function in extended.items()},
        source="extended tools",
    )
    return registry, origin


def build_registry(profile: str | None = None) -> dict[str, ToolSpec]:
    registry, _origin = _all_specs()
    selected = (profile or FULL_PROFILE).strip().lower()
    selected = PROFILE_ALIASES.get(selected, selected)
    if selected not in SUPPORTED_PROFILES:
        expected = ", ".join(sorted(SUPPORTED_PROFILES))
        raise ValueError(f"Unknown MCP profile {selected!r}; choose one of: {expected}")
    if selected == FULL_PROFILE:
        return registry
    names = {name for name, spec in registry.items() if spec.group == "official"} | {"get_toolkit_capabilities"}
    if selected != "core":
        names |= PROFILE_EXTENSION_TOOLS[selected]
    return {name: spec for name, spec in registry.items() if name in names}


def render_manifest() -> str:
    """The generated tool manifest: where each tool lives and how long it may run.

    A caller that only launches a worker reads this file instead of importing the registry,
    and the worker uses it to import the one module its tool needs.
    """
    registry, origin = _all_specs()
    tools = {}
    for name, spec in sorted(registry.items()):
        entry: dict[str, Any] = {"group": spec.group}
        if name in origin:
            entry["module"], entry["attribute"] = origin[name]
        if spec.timeout_seconds is not None:
            entry["timeout_seconds"] = spec.timeout_seconds
        tools[name] = entry
    return json.dumps({"tools": tools}, indent=2, sort_keys=True) + "\n"


def tool_manifest() -> dict[str, dict[str, Any]]:
    """The committed manifest's tool table; empty when the file is missing or unreadable."""
    try:
        tools = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))["tools"]
    except (OSError, ValueError, KeyError, TypeError):
        return {}
    return tools if isinstance(tools, dict) else {}


def load_tool(name: str) -> ToolSpec | None:
    """One tool's spec, importing only the module that defines it.

    None when the manifest does not place the tool; the caller then builds the full registry,
    so a stale manifest costs time, never correctness.
    """
    entry = tool_manifest().get(name)
    if not isinstance(entry, dict):
        return None
    group = entry.get("group")
    try:
        if group == "official":
            return _official_specs().get(name)
        if group == "remote":
            return _remote_specs().get(name)
        function = _source(str(entry.get("module")), str(entry.get("attribute"))).get(name)
    except (ImportError, AttributeError):
        return None
    return _extended_spec(name, function) if function is not None else None
