"""cdxml-toolkit MCP server — 15 chemistry tools via Model Context Protocol.

Tools:
    resolve_name          — Chemical name/formula/CAS → rich molecule JSON
    modify_molecule       — Analyze or transform a molecule (6 operations)
    draw_molecule         — Single molecule → CDXML document
    render_scheme         — YAML/compact text/reaction JSON → publication CDXML
    parse_reaction        — CDXML/CDX/CSV/RXN → semantic reaction JSON
    summarize_reaction    — Reaction JSON → compact context-efficient summary
    extract_structures    — Image/PDF → SMILES + bboxes via DECIMER
    parse_scheme          — CDXML scheme → structured species/steps/topology JSON
    convert_cdx_cdxml     — Bidirectional CDX ↔ CDXML file conversion
    parse_analysis_file   — LCMS/NMR PDF → peaks and data
    format_lab_entry      — Entry dicts → formatted lab book text
    extract_cdxml_from_office — PPTX/DOCX/XLS/XLSX → embedded CDXML files
    embed_cdxml_in_office — CDXML → editable OLE object in PPTX/DOCX
    search_compound       — SMILES → exact/similar matches across experiments
    render_to_png         — CDXML → PNG via ChemDraw COM

Run:
    python -m cdxml_toolkit.mcp_server                    # stdio (default)
    python -m cdxml_toolkit.mcp_server --transport http    # streamable-http
    python -m cdxml_toolkit.mcp_server --transport http --port 8080
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from ._compat import install_legacy_fastmcp_alias

install_legacy_fastmcp_alias()

from mcp.server.fastmcp import FastMCP
import functools

import asyncio
import inspect

def _json_safe_tool(fn):
    """Decorator: convert dict/list returns to JSON strings for MCP compatibility.
    Handles both sync and async functions."""
    if inspect.iscoroutinefunction(fn):
        @functools.wraps(fn)
        async def async_wrapper(*args, **kwargs):
            result = await fn(*args, **kwargs)
            if isinstance(result, (dict, list)):
                return json.dumps(result, indent=2, default=str)
            return result
        return async_wrapper
    else:
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            result = fn(*args, **kwargs)
            if isinstance(result, (dict, list)):
                return json.dumps(result, indent=2, default=str)
            return result
        return wrapper

# Patch FastMCP.tool to auto-wrap with _json_safe_tool
mcp = FastMCP(
    "cdxml-toolkit",
    instructions=(
        "Chemistry toolkit for parsing, rendering, and reasoning about reaction schemes. "
        "Core workflow: parse_reaction → summarize_reaction (inspect) → render_scheme. "
        "For structure work: resolve_name → modify_molecule → draw_molecule → render_scheme. "
        "Convention: atom-contributing species (reactants, products, key reagents) get drawn "
        "structures; text-only labels are for reagents/conditions. Use (IUPAC name + MW) as "
        "compound identifiers, not LLM-generated SMILES — always resolve names first."
    ),
)

# Patch mcp.tool to auto-wrap with JSON-safe return conversion
_original_mcp_tool_decorator = mcp.tool

def _safe_mcp_tool(*args, **kwargs):
    """Wrap mcp.tool to ensure all tool functions return strings, not dicts."""
    decorator = _original_mcp_tool_decorator(*args, **kwargs)
    def wrapper(fn):
        return decorator(_json_safe_tool(fn))
    return wrapper

mcp.tool = _safe_mcp_tool


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_TEMP_DIR = os.path.join(os.environ.get("TEMP", os.environ.get("TMP", "/tmp")),
                         "cdxml-toolkit-output")


def _write_output(content, output_path: Optional[str], prefix: str, ext: str) -> dict:
    """Write content to output_path (or auto-generated temp file) and return metadata.

    Always writes to a file — the agent never receives large inline content.
    If output_path is None, generates a temp path under _TEMP_DIR.
    Relative paths are resolved under _TEMP_DIR to avoid CWD permission errors.
    """
    os.makedirs(_TEMP_DIR, exist_ok=True)
    if output_path is None:
        import hashlib, time
        tag = hashlib.md5(str(time.time()).encode()).hexdigest()[:8]
        output_path = os.path.join(_TEMP_DIR, f"{prefix}_{tag}{ext}")
    elif not os.path.isabs(output_path):
        output_path = os.path.join(_TEMP_DIR, output_path)

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    if isinstance(content, str):
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)
    else:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(content, f, indent=2, default=str)

    return {"ok": True, "output_path": output_path, "size": os.path.getsize(output_path)}


def _coerce_mol_json(mol_json):
    """Accept a bare SMILES string in place of {"smiles": "..."}."""
    if isinstance(mol_json, str):
        mol_json = {"smiles": mol_json}
    return mol_json


def _parse_json_string(value):
    """If *value* is a JSON-encoded string (e.g. '[{"locant":"4"}]'), parse it."""
    if isinstance(value, str):
        value = value.strip()
        if value and value[0] in ("[", "{"):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                pass
    return value


# Known modify_molecule operations
_KNOWN_OPERATIONS = {"analyze", "name_surgery", "smarts", "set_smiles", "set_name", "reaction"}


def _normalize_operation(operation: str, reaction_name: Optional[str]) -> tuple:
    """Normalize the operation string for modify_molecule.

    Handles:
      - Case/whitespace: "BOC deprotection" → look up as reaction name
      - If *operation* isn't one of the 6 known ops but matches a reaction
        template, redirect to operation="reaction", reaction_name=<matched>.
    Returns (operation, reaction_name).
    """
    op = operation.strip()
    # Exact match (case-insensitive)
    op_lower = op.lower().replace(" ", "_").replace("-", "_")
    for known in _KNOWN_OPERATIONS:
        if op_lower == known.lower():
            return known, reaction_name

    # Not a known operation — maybe it's a reaction name?
    # Import lazily to check reaction templates
    if reaction_name is None:
        try:
            from cdxml_toolkit.naming.mol_builder import list_reactions
            result = list_reactions()
            rxn_list = result.get("reactions", []) if isinstance(result, dict) else []
            template_names = [r["name"] if isinstance(r, dict) else r for r in rxn_list]
            # Try exact (case-insensitive, normalize underscores)
            for name in template_names:
                if op_lower == name.lower().replace(" ", "_").replace("-", "_"):
                    return "reaction", name
            # Try fuzzy substring
            for name in template_names:
                if op_lower in name.lower() or name.lower() in op_lower:
                    return "reaction", name
        except Exception:
            pass

    return op, reaction_name


def _validate_file(path: str, label: str) -> Path:
    """Resolve and validate that *path* exists and is a file."""
    p = Path(path).resolve()
    if not p.is_file():
        raise FileNotFoundError(
            f"File not found: {p}. Check the path exists and use forward slashes."
        )
    return p


# ---------------------------------------------------------------------------
# Tool 1: resolve_name
# ---------------------------------------------------------------------------

@mcp.tool()
def resolve_name(query: str, use_network: bool = True) -> dict:
    """Resolve any chemical identifier to a rich molecule descriptor.

    Converts a name, abbreviation, condensed formula, or CAS number into a
    structured molecule dict with SMILES, formula, MW, exact mass, IUPAC name,
    reagent role, and display text. Uses a 4-tier resolution chain: curated
    reagent DB → condensed formula parser → ChemScript IUPAC → PubChem.

    Do NOT hand-construct SMILES — use this tool instead. The returned dict can
    be passed directly to modify_molecule, draw_molecule, or used to build a
    render_scheme input.

    Args:
        query: Chemical identifier — common name, IUPAC name, abbreviation,
               condensed formula (e.g. "PhB(OH)2"), or CAS number. Examples:
               "aspirin", "Cs2CO3", "2-chloropyridine", "534-17-8", "Et3N".
        use_network: Allow PubChem lookup (requires internet). Default True.

    Returns:
        Dict with keys: ok, name, smiles, formula, mw, exact_mass, iupac_name,
        source (which tier resolved it), role (if in reagent DB), display_text,
        prefix_form (IUPAC substituent prefix, if applicable).
        Returns {ok: False, error: "..."} if unresolvable.
    """
    if not query or not query.strip():
        return (
            "Usage: resolve_name(query='compound name or formula')\n"
            "Examples:\n"
            "  resolve_name(query='aspirin')\n"
            "  resolve_name(query='CF3')\n"
            "  resolve_name(query='Cs2CO3')\n"
            "  resolve_name(query='deucravacitinib')\n"
            "  resolve_name(query='534-17-8')  # CAS number\n"
            "Returns: {ok, name, smiles, formula, mw, exact_mass, role, display_text, source}"
        )

    from cdxml_toolkit.naming.mol_builder import resolve_compound

    return resolve_compound(query, use_network=use_network)


# ---------------------------------------------------------------------------
# Tool 2: modify_molecule
# ---------------------------------------------------------------------------

@mcp.tool()
def modify_molecule(
    mol_json: dict,
    operation: str,
    add: Optional[List[dict]] = None,
    remove: Optional[List[str]] = None,
    new_smiles: Optional[str] = None,
    new_name: Optional[str] = None,
    reaction_name: Optional[str] = None,
    reagent: Optional[dict] = None,
    smarts: Optional[str] = None,
    description: Optional[str] = None,
) -> dict:
    """Analyze or transform a molecule with structural verification.

    IMPORTANT: This is the ONLY correct way to modify a molecule. Never edit
    SMILES strings yourself and pass them directly to draw_molecule — always
    go through modify_molecule so you get an MCS-based structural diff to
    verify the change was correct.

    Takes a molecule dict (at minimum {"smiles": "..."}) and applies one of 6
    operations. Returns the modified molecule with a structural diff showing
    exactly what atoms/bonds were added, removed, or changed.

    Operations:
        "analyze"      — Inspect without modifying: functional groups, IUPAC
                         names, formula, MW, prefix form. No extra kwargs needed.
        "name_surgery" — Modify via IUPAC name: add/remove substituents.
                         Pass add=[{"locant": "2", "prefix": "fluoro"}] and/or
                         remove=["methyl"] kwargs.
        "smarts"       — Apply a SMARTS reaction transform. Pass smarts=
                         "reaction SMILES" (e.g. "[c:1][F]>>[c:1][Cl]") or
                         reaction_name= from list_reactions output.
        "set_smiles"   — Use when you have edited a SMILES and want to verify
                         the change. Pass the original mol_json and new_smiles=.
                         The MCS diff will confirm exactly what was added/removed.
                         Do NOT generate SMILES from scratch — use resolve_name.
        "set_name"     — Set the display name. Pass new_name=.
        "reaction"     — Apply a named template from list_reactions. Pass
                         reaction_name= and optionally reagent={"smiles": ...}
                         for binary reactions (coupling, etc.).

    Args:
        mol_json: Source molecule dict with at least {"smiles": "..."}.
        operation: One of: "analyze", "name_surgery", "smarts", "set_smiles",
                   "set_name", "reaction".
        add: For "name_surgery" — list of {"locant": str, "prefix": str} dicts.
        remove: For "name_surgery" — list of prefix strings to remove.
        new_smiles: For "set_smiles" — validated SMILES string.
        new_name: For "set_name" — new display name string.
        reaction_name: For "smarts"/"reaction" — template name.
        reagent: For "reaction" — dict with "smiles" key for the second reagent.
        smarts: For "smarts" — reaction SMARTS string.
        description: For "set_smiles" — optional context note.

    Returns:
        For "analyze": ok, input_smiles, canonical_name, alternative_names,
        functional_groups, prefix_form, bracket_tree, formula, mw.
        For modifications: ok, input_smiles, output_smiles, input_name,
        output_name, aligned_names, diff (atoms_added, atoms_removed,
        atoms_changed, mcs_smarts, delta_formula, delta_mw), formula, mw.
    """
    # ── Input normalization ──────────────────────────────────────
    mol_json = _coerce_mol_json(mol_json)

    if not mol_json or not mol_json.get("smiles"):
        return (
            "Usage: modify_molecule(mol_json={smiles: '...'}, operation='...')\n"
            "Operations: analyze, name_surgery, smarts, set_smiles, set_name, reaction\n"
            "Examples:\n"
            "  analyze:      modify_molecule({smiles:'Clc1ccncc1'}, 'analyze')\n"
            "  name_surgery: modify_molecule({smiles:'...'}, 'name_surgery', add=[{locant:'4', prefix:'fluoro'}])\n"
            "  reaction:     modify_molecule({smiles:'...'}, 'reaction', reaction_name='amide_coupling', reagent={smiles:'...'})\n"
            "  set_smiles:   modify_molecule({smiles:'...'}, 'set_smiles', new_smiles='validated_smiles')\n"
            "Tip: get mol_json from resolve_name first, not hand-written SMILES."
        )

    # Normalize operation name (e.g. "BOC deprotection" → reaction + BOC_deprotection)
    operation, reaction_name = _normalize_operation(operation, reaction_name)

    # Parse stringified JSON arrays (model sometimes sends "[{...}]" as a string)
    if add is not None:
        add = _parse_json_string(add)
    if remove is not None:
        remove = _parse_json_string(remove)

    from cdxml_toolkit.naming.mol_builder import modify_molecule as _modify

    kwargs: Dict[str, Any] = {}
    if add is not None:
        kwargs["add"] = add
    if remove is not None:
        kwargs["remove"] = remove
    if new_smiles is not None:
        kwargs["new_smiles"] = new_smiles
    if new_name is not None:
        kwargs["new_name"] = new_name
    if reaction_name is not None:
        kwargs["reaction_name"] = reaction_name
    if reagent is not None:
        kwargs["reagent"] = _coerce_mol_json(reagent)
    if smarts is not None:
        kwargs["smarts"] = smarts
    if description is not None:
        kwargs["description"] = description

    return _modify(mol_json, operation, **kwargs)


# ---------------------------------------------------------------------------
# Tool 3: draw_molecule
# ---------------------------------------------------------------------------

@mcp.tool()
def draw_molecule(mol_json: dict, output_path: Optional[str] = None) -> dict:
    """Render a single molecule to a standalone CDXML document.

    Takes a molecule dict (at minimum {"smiles": "..."}) and generates a
    self-contained CDXML string with 2D coordinates in ACS Document 1996 style
    (BondLength=14.40, Arial 10pt). Optionally places a text label below the
    structure using the "label", "name", or "iupac_name" field (in that order).

    IMPORTANT: Do NOT construct {"smiles": "..."} with hand-edited SMILES.
    Always get mol_json from another tool (resolve_name, modify_molecule,
    parse_reaction, etc.). If you need to edit a SMILES, use
    modify_molecule(operation="set_smiles") first — it gives you an MCS diff
    to verify the edit was correct before drawing.

    Args:
        mol_json: Molecule dict with at least {"smiles": "..."}. Optional display
                  fields: "label" (used verbatim), "name", "iupac_name".
                  Should come from another tool's output, not hand-constructed.
        output_path: If given, also write CDXML to this file path.

    Returns:
        Dict with keys: ok, cdxml (CDXML document string), and output_path if
        a path was specified. Returns {ok: False, error: "..."} on failure.
    """
    # ── Input normalization ──────────────────────────────────────
    mol_json = _coerce_mol_json(mol_json)

    if not mol_json or not mol_json.get("smiles"):
        return (
            "Usage: draw_molecule(mol_json={smiles:'...'}, output_path='path.cdxml')\n"
            "Examples:\n"
            "  draw_molecule({smiles:'c1ccncc1'})  # pyridine, no file written\n"
            "  draw_molecule({smiles:'c1ccncc1', label:'Pyridine'}, output_path='out.cdxml')\n"
            "Returns: {ok, cdxml (CDXML string), output_path}\n"
            "Tip: get mol_json from resolve_name — do not hand-write SMILES."
        )

    from cdxml_toolkit.naming.mol_builder import draw_molecule as _draw

    result = _draw(mol_json, output_path=output_path)

    # Always write to file — don't return large CDXML inline
    if isinstance(result, dict) and result.get("ok") and "cdxml" in result:
        cdxml = result["cdxml"]
        path = result.get("output_path") or output_path
        out = _write_output(cdxml, path, "molecule", ".cdxml")
        out["name"] = mol_json.get("name") or mol_json.get("iupac_name") or ""
        out["smiles"] = mol_json.get("smiles", "")
        return out

    return result


# ---------------------------------------------------------------------------
# Tool 4: render_scheme
# ---------------------------------------------------------------------------

@mcp.tool()
def render_scheme(
    yaml_text: Optional[str] = None,
    compact_text: Optional[str] = None,
    json_path: Optional[str] = None,
    layout: str = "auto",
    output_path: Optional[str] = None,
) -> str:
    """Render an editable chemical reaction scheme with per-fragment chemical validation.

    Accepts exactly ONE of: yaml_text, compact_text, or json_path.
    Call with NO arguments to see the full YAML schema reference.

    - yaml_text:  Write YAML with structures (ID + SMILES) and steps
                  (substrates, products, above/below arrow).
    - json_path:  Path to reaction JSON from parse_reaction (auto-layout).

    IMPORTANT: Every SMILES in the YAML must come from a tool — resolve_name,
    modify_molecule, parse_reaction, extract_structures_from_image, etc.
    Never write SMILES from built-in chemistry knowledge or from reading an
    image with vision. Always call the appropriate tool first, then use the
    SMILES from its output in your YAML.

    Place all atom-contributing substrates on the center line when appropriate.
    Catalysts and conditions may go above/below arrows. Sequential steps can
    share intermediates; spatial position does not determine chemical identity.

    Args:
        yaml_text:    YAML scheme descriptor string.
        compact_text: Compact DSL syntax string.
        json_path:    Path to a reaction JSON file.
        layout:       Layout for json_path: "auto", "landscape", "portrait".
        output_path:  If given, write the CDXML to this file and return
                      {ok, output_path, size} instead of the raw CDXML string.

    Returns:
        CDXML string (when output_path is None), or {ok, output_path, size}
        when output_path is provided, or YAML schema reference if called with
        no arguments.
    """
    from cdxml_toolkit.render.renderer import render

    modes = sum(x is not None for x in [yaml_text, compact_text, json_path])
    if modes == 0:
        return (
            "No input provided. Call with exactly one of: yaml_text, compact_text, or json_path.\n\n"
            "YAML SCHEMA REFERENCE:\n"
            "  layout: sequential       # linear | sequential | stacked-rows\n"
            "  source: reaction.json    # optional — resolve SMILES by ID from this JSON\n"
            "  structures:\n"
            "    SM:\n"
            "      smiles: \"CCO\"        # required unless source JSON provides it\n"
            "      label: \"Ethanol\"     # optional label below structure\n"
            "    Product:\n"
            "      smiles: \"CC=O\"\n"
            "  steps:\n"
            "    - substrates: [SM]\n"
            "      products: [Product]\n"
            "      above_arrow:\n"
            "        structures: [Reagent]    # drawn structures above arrow\n"
            "        text: [\"PCC (1.5 eq)\"]   # text labels above arrow\n"
            "      below_arrow:\n"
            "        text: [\"DCM, rt, 2 h\"]\n\n"
            "For stacked-rows (independent reactions), use sections:\n"
            "  sections:\n"
            "    - label: \"(i)\"\n"
            "      steps: [{substrates: [A], products: [B], ...}]\n"
            "    - label: \"(ii)\"\n"
            "      steps: [{substrates: [C], products: [D], ...}]\n\n"
            "Multiple substrates/products are supported. Use above_arrow for catalysts or conditions.\n"
            "output_path: optional — write CDXML to file and get {ok, output_path, size} back."
        )
    if modes > 1:
        raise ValueError("Provide only ONE of: yaml_text, compact_text, or json_path.")

    if yaml_text is not None:
        from cdxml_toolkit.render.parser import parse_yaml

        try:
            scheme = parse_yaml(yaml_text)
        except Exception as e:
            return {
                "ok": False,
                "error": (
                    f"YAML parse error: {e}. "
                    "Correct format: structures: {ID: {smiles: '...'}}, "
                    "steps: [{substrates: [ID], products: [ID]}]"
                ),
            }
        try:
            cdxml = render(scheme)
        except Exception as e:
            return {
                "ok": False,
                "error": (
                    f"Render failed: {e}. "
                    "Check that all structure IDs referenced in steps exist in the structures block "
                    "and that each SMILES was obtained from resolve_name, not hand-written."
                ),
            }

    elif compact_text is not None:
        from cdxml_toolkit.render.compact_parser import parse_compact

        try:
            scheme = parse_compact(compact_text)
        except Exception as e:
            return {
                "ok": False,
                "error": (
                    f"Compact text parse error: {e}. "
                    "Correct format: 'ID: {SMILES}' definitions, then 'A + B --> C' reaction lines "
                    "with optional 'above:' and 'below:' annotation lines."
                ),
            }
        try:
            cdxml = render(scheme)
        except Exception as e:
            return {
                "ok": False,
                "error": (
                    f"Render failed: {e}. "
                    "Check that all structure IDs referenced in the reaction line are defined above "
                    "and that SMILES strings came from resolve_name."
                ),
            }

    else:
        # json_path mode — auto-generate YAML then render
        import yaml

        from cdxml_toolkit.render.parser import parse_yaml
        from cdxml_toolkit.render.scheme_yaml_writer import build_scheme_yaml_dict

        p = _validate_file(json_path, "JSON file")
        try:
            yaml_dict = build_scheme_yaml_dict(str(p), layout=layout, include_run_arrows=True)
            yaml_str = yaml.dump(yaml_dict, default_flow_style=False, allow_unicode=True, sort_keys=False)
            scheme = parse_yaml(yaml_str)
            cdxml = render(scheme)
        except Exception as e:
            return {
                "ok": False,
                "error": (
                    f"Render from JSON failed: {e}. "
                    "Ensure the JSON file was produced by parse_reaction and is not corrupted. "
                    "Try summarize_reaction on it first to verify its contents."
                ),
            }

    result = _write_output(cdxml, output_path, "scheme", ".cdxml")
    if getattr(cdxml, 'chemistry_validation', None):
        result.setdefault('metadata', {})['chemistry_validation'] = cdxml.chemistry_validation
    return result


# ---------------------------------------------------------------------------
# Tool 5: parse_reaction
# ---------------------------------------------------------------------------

@mcp.tool()
def parse_reaction(
    cdxml: Optional[str] = None,
    cdx: Optional[str] = None,
    csv: Optional[str] = None,
    rxn: Optional[str] = None,
    input_dir: Optional[str] = None,
    output_path: Optional[str] = None,
) -> dict:
    """Parse reaction files into a semantic JSON descriptor.

    Extracts every species with canonical SMILES, role classification (using
    Schneider fingerprint scoring for reactant/reagent binary, plus curated
    database for semantic roles like base/solvent/catalyst), display names,
    equivalents, mass data, and adducts. Produces a single JSON source of truth
    suitable for summarize_reaction, render_scheme, or LCMS analysis.

    Provide at least one file path. Multiple may be combined (e.g. cdxml + csv)
    to merge structural data with ELN metadata.

    Args:
        cdxml:       Path to a .cdxml reaction file.
        cdx:         Path to a .cdx reaction file (converted internally).
        csv:         Path to a Findmolecule ELN CSV export.
        rxn:         Path to a .rxn file.
        input_dir:   Directory containing experiment files (auto-discovers
                     cdxml/cdx/csv/rxn by experiment ID).
        output_path: If given, write the result JSON to this file and return
                     {ok, output_path} instead of the full dict.

    Returns:
        Reaction descriptor dict with keys: version, experiment, input_files,
        reaction_smiles, reaction_class, species (list with role, smiles,
        formula, mw, etc.), conditions, and eln_data.
        When output_path is provided, returns {ok, output_path} instead.
    """
    if not any([cdxml, cdx, csv, rxn, input_dir]):
        return (
            "Usage: parse_reaction(cdxml='path.cdxml', csv='path.csv')\n"
            "Provide at least one input file; cdxml+csv is the most common combination.\n"
            "Examples:\n"
            "  parse_reaction(cdxml='experiment.cdxml')\n"
            "  parse_reaction(cdxml='experiment.cdxml', csv='experiment.csv')\n"
            "  parse_reaction(input_dir='experiments/KL-CC-001/')  # auto-discovers files\n"
            "  parse_reaction(cdxml='experiment.cdxml', output_path='reaction.json')  # save to file\n"
            "Returns: reaction descriptor JSON with species, roles, SMILES, conditions."
        )

    from cdxml_toolkit.perception.reaction_parser import parse_reaction as _parse

    kwargs: Dict[str, Any] = {}
    if cdxml:
        kwargs["cdxml"] = str(_validate_file(cdxml, "CDXML file"))
    if cdx:
        kwargs["cdx"] = str(_validate_file(cdx, "CDX file"))
    if csv:
        kwargs["csv"] = str(_validate_file(csv, "CSV file"))
    if rxn:
        kwargs["rxn"] = str(_validate_file(rxn, "RXN file"))
    if input_dir:
        p = Path(input_dir).resolve()
        if not p.is_dir():
            raise FileNotFoundError(
                f"File not found: {p}. Check the path exists and use forward slashes."
            )
        # Auto-discover files when only input_dir given (no explicit files)
        if not any([cdxml, cdx, csv, rxn]):
            for f in sorted(p.iterdir()):
                ext = f.suffix.lower()
                if ext == ".cdxml" and not cdxml:
                    kwargs["cdxml"] = str(f)
                elif ext == ".cdx" and "cdx" not in kwargs and "cdxml" not in kwargs:
                    kwargs["cdx"] = str(f)
                elif ext == ".csv" and "csv" not in kwargs:
                    kwargs["csv"] = str(f)
                elif ext == ".rxn" and "rxn" not in kwargs:
                    kwargs["rxn"] = str(f)
        else:
            kwargs["input_dir"] = str(p)

    try:
        descriptor = _parse(**kwargs, verbose=False)
        result = descriptor.to_dict()
    except Exception as e:
        return {
            "ok": False,
            "error": (
                f"Parse failed: {e}. "
                "Provide at least one of: cdxml=, csv=, rxn= file paths. "
                "If using a CDX binary file, convert it first with convert_cdx_cdxml."
            ),
        }

    out = _write_output(result, output_path, "reaction", ".json")
    if isinstance(out, dict) and out.get("ok"):
        out["hint"] = (
            "Use summarize_reaction(json_path=...) to view this result. "
            "Do NOT read the full JSON file — it is large and wastes context."
        )
    return out


# ---------------------------------------------------------------------------
# Tool 6: summarize_reaction
# ---------------------------------------------------------------------------

@mcp.tool()
def summarize_reaction(
    json_path: str,
    species_fields: Optional[List[str]] = None,
    top_fields: Optional[List[str]] = None,
    eln_fields: Optional[List[str]] = None,
) -> dict:
    """Return a compact, context-efficient view of a reaction JSON file.

    The full reaction JSON can be 3,000+ tokens with geometry data. This tool
    returns only the fields you need for a given task, making it practical for
    LLM reasoning without burning context.

    Default fields (when no arguments given):
      species:   id, name, role, role_detail, smiles, display_text, formula, mw
      top-level: experiment, conditions
      eln_data:  product_yield, reaction_type

    Pass ["*"] for any field set to get all fields (equivalent to loading the
    full JSON). Request specific fields by name for task-focused summaries.

    Args:
        json_path:      Path to a reaction JSON file from parse_reaction.
        species_fields: Species fields to include. Available: id, name, role,
                        role_detail, smiles, smiles_neutral, is_sm, is_dp,
                        is_substrate, is_solvent, exact_mass, exact_mass_full,
                        mw, formula, adducts, source, source_id, csv_equiv,
                        csv_mass, csv_name, csv_volume, csv_supplier,
                        display_text, original_geometry. Pass ["*"] for all.
        top_fields:     Top-level fields. Available: version, experiment,
                        input_files, reaction_smiles, reaction_class,
                        reaction_name, classification_confidence, warnings,
                        metadata, conditions. Pass ["*"] for all.
        eln_fields:     ELN data fields. Available: sm_mass, product_obtained,
                        product_yield, procedure_text, procedure_plain,
                        reaction_type, start_date, labbook_name, solvents,
                        solvent_details. Pass ["*"] for all.

    Returns:
        Compact dict with requested fields for each species and top-level keys.
    """
    if not json_path or not json_path.strip():
        return (
            "Usage: summarize_reaction(json_path='reaction.json')\n"
            "Examples:\n"
            "  summarize_reaction(json_path='reaction.json')  # default fields\n"
            "  summarize_reaction(json_path='reaction.json', species_fields=['id','name','smiles','adducts'])  # LCMS task\n"
            "  summarize_reaction(json_path='reaction.json', species_fields=['*'])  # all fields\n"
            "Default species fields: id, name, role, smiles, display_text, formula, mw"
        )

    from cdxml_toolkit.perception.reaction_parser import reaction_summary

    # Parse stringified JSON arrays (model sometimes sends '["name","role"]' as string)
    species_fields = _parse_json_string(species_fields) if species_fields is not None else None
    top_fields = _parse_json_string(top_fields) if top_fields is not None else None
    eln_fields = _parse_json_string(eln_fields) if eln_fields is not None else None

    p = _validate_file(json_path, "JSON file")
    return reaction_summary(
        str(p),
        species_fields=species_fields,
        top_fields=top_fields,
        eln_fields=eln_fields,
    )


# ---------------------------------------------------------------------------
# Tool 7: extract_structures_from_image
# ---------------------------------------------------------------------------

@mcp.tool()
async def extract_structures_from_image(
    image_path: str,
    detect_labels: bool = True,
) -> dict:
    """Extract chemical structures from an image using DECIMER.

    Takes a PNG, JPG, or PDF image and returns SMILES + confidence scores +
    bounding boxes for every detected chemical structure. Segments the image
    into individual structure regions automatically. Optionally detects nearby
    text labels via OCR.

    DECIMER models download on first run (~570 MB to ~/.data/DECIMER-V2/).
    Requires: DECIMER, opencv-python, and optionally pytesseract/easyocr.

    The returned SMILES should be passed through resolve_name or modify_molecule
    to verify and enrich — DECIMER SMILES may not be canonical and can have
    low confidence for complex structures.

    Args:
        image_path:    Path to PNG, JPG, or PDF file.
        detect_labels: Attempt OCR detection of text labels near structures.
                       Requires pytesseract or easyocr; labels are null without
                       an OCR library. Default True.

    Returns:
        Dict with keys: ok, image_path, structures (list of: smiles, confidence
        in [0,1], bbox [x0,y0,x1,y1], label or null). Returns {ok: False,
        error: "..."} if DECIMER is not installed or extraction fails.
    """
    if not image_path or not image_path.strip():
        return (
            "Usage: extract_structures_from_image(image_path='image.png')\n"
            "Supported formats: PNG, JPG, PDF\n"
            "Returns SMILES + confidence score + bounding box for each structure found.\n"
            "Note: DECIMER models download ~570 MB on first run.\n"
            "Tip: pass returned SMILES through resolve_name to validate and enrich."
        )

    try:
        from cdxml_toolkit.image.structure_from_image import (
            extract_structures_from_image as _extract,
        )
    except ImportError as e:
        return {
            "ok": False,
            "error": (
                f"DECIMER/OpenCV not available: {e}. "
                "Install with: pip install cdxml-toolkit-community[decimer]"
            ),
        }

    p = _validate_file(image_path, "Image file")
    try:
        # Run in a thread pool so the synchronous TF inference doesn't
        # block the MCP event loop (keeps keepalive pings responsive).
        # TF's C-level logging is suppressed via TF_CPP_MIN_LOG_LEVEL=3
        # set in main() before any TF import.
        # If --preload-decimer was used, the model is already warm and
        # this returns in ~2 s.  Otherwise, first call pays ~25 s cold
        # start, subsequent calls are fast.
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            functools.partial(
                _extract, str(p), detect_labels=detect_labels,
            ),
        )
    except Exception as e:
        return {
            "ok": False,
            "error": (
                f"Image extraction failed: {e}. "
                "Try again (DECIMER may need more time on first run to load models), "
                "or use resolve_name() to look up compounds by name instead."
            ),
        }


# ---------------------------------------------------------------------------
# Tool 8: parse_scheme
# ---------------------------------------------------------------------------

@mcp.tool()
def parse_scheme(
    cdxml_path: str,
    output_path: Optional[str] = None,
) -> dict:
    """Parse a CDXML reaction scheme into a structured description.

    Reads a CDXML file containing a reaction scheme (single- or multi-step) and
    returns a structured JSON with a species registry, reaction graph, topology
    classification, and a natural language narrative suitable for LLM reasoning.

    Uses two strategies in order: step-attribute path (reads <scheme><step>
    attributes if present) then geometry-based fallback (spatial arrow detection).
    Text labels near arrows are classified as "chemical", "condition_ref",
    "footnote", "yield", "compound_label", "citation", or "bioactivity".

    Args:
        cdxml_path:  Path to a CDXML file containing a reaction scheme.
        output_path: If given, write the result JSON to this file and return
                     {ok, output_path, size} instead of the full dict.

    Returns:
        Dict with keys: source_file, species (dict of species records with
        smiles, name, formula, mw, role, text_category), steps (list with
        reactant/product/reagent species IDs and conditions), topology
        (linear/parallel/convergent/divergent), content_type, narrative
        (human-readable summary), and optionally sub_schemes for multi-panel
        files. When output_path is provided, returns {ok, output_path, size}.
    """
    if not cdxml_path or not cdxml_path.strip():
        return (
            "Usage: parse_scheme(cdxml_path='scheme.cdxml')\n"
            "Reads a CDXML scheme and returns species, steps, topology, and narrative.\n"
            "Example: parse_scheme(cdxml_path='experiments/KL-CC-001/scheme.cdxml')\n"
            "  parse_scheme(cdxml_path='scheme.cdxml', output_path='parsed.json')  # save to file\n"
            "Returns: {species, steps, topology, content_type, narrative}"
        )

    from cdxml_toolkit.perception.scheme_reader import read_scheme

    p = _validate_file(cdxml_path, "CDXML file")
    desc = read_scheme(str(p))

    # SchemeDescription is a dataclass — convert to dict
    try:
        from dataclasses import asdict
        result = asdict(desc)
    except Exception:
        # Fallback: use to_dict if available
        if hasattr(desc, "to_dict"):
            result = desc.to_dict()
        else:
            result = {
                "source_file": getattr(desc, "source_file", str(p)),
                "species": {k: v if isinstance(v, dict) else vars(v)
                            for k, v in (desc.species or {}).items()},
                "steps": [s if isinstance(s, dict) else vars(s)
                          for s in (desc.steps or [])],
                "topology": getattr(desc, "topology", None),
                "content_type": getattr(desc, "content_type", None),
                "narrative": getattr(desc, "narrative", None),
            }

    return _write_output(result, output_path, "scheme_parsed", ".json")


# ---------------------------------------------------------------------------
# Tool 9: convert_cdx_cdxml
# ---------------------------------------------------------------------------

@mcp.tool()
def convert_cdx_cdxml(
    input_path: str,
    output_path: Optional[str] = None,
) -> dict:
    """Convert bidirectionally between CDX (binary) and CDXML (XML) formats.

    Direction is detected from the file extension:
    - .cdx input  → .cdxml output
    - .cdxml input → .cdx output

    Uses available backends in order: ChemDraw COM (best fidelity, Windows) →
    pycdxml (pure Python, partial support) → OpenBabel.

    ChemDraw COM requires ChemDraw to be installed and closed before running.

    Args:
        input_path:  Path to .cdx or .cdxml file.
        output_path: Output file path. If not given, same directory as input
                     with the swapped extension (e.g. foo.cdx → foo.cdxml).

    Returns:
        Dict with keys: ok, input, output (absolute path to written file).
        Returns {ok: False, error: "..."} if conversion fails.
    """
    if not input_path or not input_path.strip():
        return (
            "Usage: convert_cdx_cdxml(input_path='file.cdx', output_path='file.cdxml')\n"
            "Direction is auto-detected from extension: .cdx → .cdxml or .cdxml → .cdx\n"
            "Examples:\n"
            "  convert_cdx_cdxml(input_path='experiment.cdx')\n"
            "  convert_cdx_cdxml(input_path='scheme.cdxml', output_path='scheme.cdx')\n"
            "Requires ChemDraw COM (Windows, ChemDraw must be closed)."
        )

    from cdxml_toolkit.chemdraw.cdx_converter import convert_file

    p = _validate_file(input_path, "Input file")
    ext = p.suffix.lower()
    if ext not in (".cdx", ".cdxml"):
        return {
            "ok": False,
            "error": f"Unsupported extension: {ext}. Use .cdx or .cdxml.",
        }

    try:
        out = convert_file(str(p), output_path=output_path)
        return {"ok": True, "input": str(p), "output": str(Path(out).resolve())}
    except Exception as e:
        return {
            "ok": False,
            "error": (
                f"Conversion failed: {e}. "
                "Ensure ChemDraw is installed and not currently running."
            ),
            "input": str(p),
        }


# ---------------------------------------------------------------------------
# Tool 10: parse_analysis_file
# ---------------------------------------------------------------------------

@mcp.tool()
def parse_analysis_file(
    pdf_path: str,
    output_path: Optional[str] = None,
) -> dict:
    """Parse an LCMS or NMR analysis PDF to extract peaks and data.

    Supports Waters LCMS reports and MestReNova NMR PDFs. Returns structured
    peak data for LCMS species identification or NMR characterisation.

    This module is under active development. If unavailable, the tool returns
    a graceful error rather than crashing.

    Args:
        pdf_path:    Path to an LCMS or NMR PDF report.
        output_path: If given, write the parsed data as JSON to this file and
                     return {ok, output_path, size} instead of the full dict.

    Returns:
        For LCMS: dict with retention_times, peak_areas, masses, UV traces.
        For NMR: dict with chemical_shifts, multiplicities, integrations.
        When output_path is provided, returns {ok, output_path, size}.
        Returns {ok: False, error: "..."} if module unavailable or parse fails.
    """
    if not pdf_path or not pdf_path.strip():
        return (
            "Usage: parse_analysis_file(pdf_path='report.pdf')\n"
            "Supports: Waters LCMS reports, MestReNova NMR PDFs.\n"
            "Examples:\n"
            "  parse_analysis_file(pdf_path='lcms/t0.pdf')\n"
            "  parse_analysis_file(pdf_path='nmr/product_1H.pdf')\n"
            "  parse_analysis_file(pdf_path='lcms/t0.pdf', output_path='t0_parsed.json')  # save to file\n"
            "Returns: retention times, peak areas, masses (LCMS) or shifts/multiplicities (NMR)."
        )

    try:
        from cdxml_toolkit.analysis.parse_analysis_file import parse_analysis_file as _parse
    except ImportError as e:
        return {
            "ok": False,
            "error": (
                f"parse_analysis_file module not available: {e}. "
                "Install with: pip install cdxml-toolkit-community[analysis]"
            ),
        }

    p = _validate_file(pdf_path, "PDF file")
    try:
        result = _parse(str(p))
        if not isinstance(result, dict):
            result = {"ok": True, "data": result}

        return _write_output(result, output_path, "analysis", ".json")
    except Exception as e:
        return {
            "ok": False,
            "error": (
                f"Parse failed: {e}. "
                "Ensure the PDF is a Waters LCMS report or MestReNova NMR export; "
                "scanned PDFs without embedded text are not supported."
            ),
            "pdf_path": str(p),
        }


# ---------------------------------------------------------------------------
# Tool 11: format_lab_entry
# ---------------------------------------------------------------------------

@mcp.tool()
def format_lab_entry(
    entries_json: Union[List[dict], dict, str],
    output_path: Optional[str] = None,
) -> dict:
    """Format a list of entry dicts into a structured lab book text entry.

    Takes a list of typed entry dicts (or a JSON string) and produces a
    formatted lab book entry.  The tool re-parses LCMS PDFs to fill in
    exact numbers — you only provide peak identifications (name, approximate
    RT, ion) as search keys.

    IMPORTANT: Do NOT write free-form LCMS text.  Use the structured entry
    types below.  The tool will look up the actual RT, area%, m/z, and UV
    from the PDF.

    Entry types and their required fields:

      {"type": "text", "content": "Procedure paragraph or section header..."}

      {"type": "lcms-species",
       "file": "path/to/report.pdf",
       "label": "t = 0 min",
       "peaks": [
         {"name": "Product",  "rt": 1.02, "ion": {"mode": "ES-", "mz": 444.1}},
         {"name": "SM",       "rt": 0.65, "ion": {"mode": "ES+", "mz": 275.1}},
         {"name": "TPPO",     "rt": 1.02, "ion": {"mode": "ES+", "mz": 279.1}}
       ]}

      {"type": "lcms-areas",
       "file": "path/to/report.pdf",
       "label": "t = 10 min",
       "peaks": [
         {"name": "Product",     "rt": 1.03, "compound_related": true},
         {"name": "Byproduct",   "rt": 1.26, "compound_related": false}
       ]}

      {"type": "lcms-species",
       "file": "path/to/report.pdf",
       "label": "Purified product",
       "peaks": [
         {"name": "Product", "rt": 1.01, "ion": {"mode": "ES-", "mz": 444.2},
          "purity": true, "detector": "220nm"}
       ]}

      {"type": "lcms-manual",
       "file": "path/to/manual_integration.pdf",
       "label": "Manual LC",
       "peaks": [
         {"name": "Product", "rt": 1.01, "compound_related": true}
       ]}

      {"type": "nmr", "content": "1H NMR (400 MHz, DMSO-d6): ..."}

    Workflow: First call parse_analysis_file on each PDF to see peaks/masses.
    Then build entries referencing those PDFs with approximate RT and ion as
    search keys.  This tool re-reads the PDF and fills in exact numbers.

    Args:
        entries_json: List of entry dicts, or a JSON string, or {"entries": [...]}.
        output_path:  If given, write the formatted text to this file and return
                      {ok, output_path, size} instead of {ok, text}.

    Returns:
        Dict with keys: ok, text (formatted lab book entry string).
        When output_path is provided, returns {ok, output_path, size} instead.
    """
    # Return usage if called with empty/null-ish input
    if entries_json is None or entries_json == [] or entries_json == {} or entries_json == "":
        return (
            "Usage: format_lab_entry(entries_json=[...entry dicts...])\n"
            "Entry types:\n"
            "  {type:'text', content:'Procedure paragraph...'}\n"
            "  {type:'lcms-species', file:'report.pdf', label:'t=0', peaks:[{name:'Product', rt:1.02, ion:{mode:'ES+', mz:445.1}}]}\n"
            "  {type:'lcms-areas', file:'report.pdf', label:'t=10 min', peaks:[{name:'Product', rt:1.03, compound_related:true}]}\n"
            "  {type:'nmr', content:'1H NMR (400 MHz, DMSO-d6): ...'}\n"
            "Workflow: call parse_analysis_file on each PDF first to identify peaks/RTs.\n"
            "output_path: optional — write formatted text to file and get {ok, output_path, size} back."
        )

    from cdxml_toolkit.analysis.format_procedure_entry import process_entries

    # Accept a JSON string, a list, or a dict with "entries" key
    if isinstance(entries_json, str):
        try:
            entries_json = json.loads(entries_json)
        except json.JSONDecodeError as e:
            return {"ok": False, "error": f"Invalid JSON: {e}"}

    if isinstance(entries_json, dict):
        if "entries" in entries_json:
            entries = entries_json["entries"]
        elif "procedure" in entries_json or "content" in entries_json:
            # Shorthand: {procedure: "text"} or {content: "text"} → [{type: "text", content: "..."}]
            text = entries_json.get("procedure") or entries_json.get("content", "")
            entries = [{"type": "text", "content": text}]
        else:
            entries = entries_json.get("entries", [])
    elif isinstance(entries_json, list):
        entries = entries_json
    elif isinstance(entries_json, str) and not entries_json.strip().startswith("["):
        # Bare text string → wrap as text entry
        entries = [{"type": "text", "content": entries_json}]
    else:
        return {
            "ok": False,
            "error": "entries_json must be a list, a JSON string, or {\"entries\": [...]}",
        }

    try:
        text = process_entries(entries)

        return _write_output(text, output_path, "lab_entry", ".txt")
    except Exception as e:
        return {
            "ok": False,
            "error": (
                f"Entry formatting failed: {e}. "
                "Check that each entry has a valid 'type' field (text, lcms-species, lcms-areas, "
                "lcms-manual, nmr) and that PDF paths in 'file' fields exist. "
                "Call parse_analysis_file on each PDF first to identify peak RTs."
            ),
        }


# ---------------------------------------------------------------------------
# Tool 12: extract_cdxml_from_office
# ---------------------------------------------------------------------------

@mcp.tool()
def extract_cdxml_from_office(
    file_path: str,
    output_dir: Optional[str] = None,
) -> dict:
    """Extract embedded ChemDraw objects from a PPTX, DOCX, XLS, or XLSX file.

    Office files (PPTX/DOCX/XLSX) are ZIP archives that may contain ChemDraw OLE
    objects as binary blobs. XLS files are OLE2 compound documents with embedded
    ChemDraw objects stored in MBD* sub-storages. This tool extracts every
    ChemDraw object, converts it to CDXML, and writes the files to output_dir.

    Requires: olefile. CDX→CDXML conversion uses available backends.

    Args:
        file_path:  Path to a .pptx, .docx, .xlsx, or .xls file.
        output_dir: Directory for extracted CDXML files. Default: a folder
                    named "<basename>_chemdraw/" next to the input file.

    Returns:
        Dict with keys: ok, input, output_dir, objects (list of: source_path,
        cdxml_output, cdx_output, error for each extracted object).
        Returns {ok: False, error: "..."} if extraction fails entirely.
    """
    if not file_path or not file_path.strip():
        return (
            "Usage: extract_cdxml_from_office(file_path='document.pptx', output_dir='out/')\n"
            "Extracts embedded ChemDraw objects from PPTX, DOCX, XLS, or XLSX files.\n"
            "Examples:\n"
            "  extract_cdxml_from_office(file_path='presentation.pptx')\n"
            "  extract_cdxml_from_office(file_path='report.docx', output_dir='extracted/')\n"
            "  extract_cdxml_from_office(file_path='labbook.xls')\n"
            "  extract_cdxml_from_office(file_path='labbook.xlsx')\n"
            "Returns: {ok, count, objects:[{cdxml_output, source_path}]}"
        )

    from cdxml_toolkit.office.ole_extractor import extract_from_office, ExtractedObject

    p = _validate_file(file_path, "Office file")

    try:
        results = extract_from_office(
            str(p),
            output_dir=output_dir,
            output_format="cdxml",
        )
    except Exception as e:
        return {
            "ok": False,
            "error": (
                f"Extraction failed: {e}. "
                "Ensure the file is a valid .pptx, .docx, .xlsx, or .xls and that olefile "
                "is installed (pip install olefile). The file must contain embedded "
                "ChemDraw OLE objects."
            ),
            "input": str(p),
        }

    objects = []
    for obj in results:
        entry: Dict[str, Any] = {"source_path": obj.source_path}
        if obj.cdxml_output:
            entry["cdxml_output"] = obj.cdxml_output
        if obj.cdx_output:
            entry["cdx_output"] = obj.cdx_output
        if obj.error:
            entry["error"] = obj.error
        objects.append(entry)

    resolved_output_dir = output_dir
    if results:
        # derive from first result's output path
        first_out = results[0].cdxml_output or results[0].cdx_output
        if first_out:
            resolved_output_dir = str(Path(first_out).parent)

    return {
        "ok": True,
        "input": str(p),
        "output_dir": resolved_output_dir,
        "count": len(objects),
        "objects": objects,
    }


# ---------------------------------------------------------------------------
# Tool 13: embed_cdxml_in_office
# ---------------------------------------------------------------------------

@mcp.tool()
def embed_cdxml_in_office(
    cdxml_path: str,
    office_path: str,
    output_path: Optional[str] = None,
) -> dict:
    """Embed a CDXML file as an editable ChemDraw OLE object in PPTX or DOCX.

    Converts CDXML → CDX + EMF preview via ChemDraw COM, builds a CFB OLE
    compound file, and injects it into a PPTX slide or DOCX paragraph as a
    double-clickable, editable ChemDraw object.

    Requires: ChemDraw COM (Windows, ChemDraw 16+), python-pptx or python-docx.
    ChemDraw must be installed and closed before calling this tool.

    The output format (.pptx or .docx) is detected from office_path extension.
    If office_path does not exist, a new file is created.

    Args:
        cdxml_path:   Path to the CDXML file to embed.
        office_path:  Path to the target .pptx or .docx file. Created if it
                      does not exist.
        output_path:  Output file path. If not given, writes to office_path
                      (modifies in place via temp file).

    Returns:
        Dict with keys: ok, input_cdxml, output (absolute path to written
        Office file), format ("pptx" or "docx"), num_objects_embedded.
        Returns {ok: False, error: "..."} if embedding fails.
    """
    if not cdxml_path or not cdxml_path.strip():
        return (
            "Usage: embed_cdxml_in_office(cdxml_path='scheme.cdxml', office_path='output.pptx')\n"
            "Embeds a CDXML file as a double-clickable ChemDraw OLE object.\n"
            "Examples:\n"
            "  embed_cdxml_in_office(cdxml_path='scheme.cdxml', office_path='report.pptx')\n"
            "  embed_cdxml_in_office(cdxml_path='scheme.cdxml', office_path='report.docx', output_path='report_v2.docx')\n"
            "Requires: ChemDraw COM (Windows, ChemDraw must be closed), python-pptx or python-docx."
        )

    from cdxml_toolkit.office.ole_embedder import (
        batch_convert,
        get_cdxml_content_size,
        build_ole_compound_file,
        build_pptx,
        build_docx,
    )

    cdxml_p = _validate_file(cdxml_path, "CDXML file")
    ext = Path(office_path).suffix.lower()
    if ext not in (".pptx", ".docx"):
        return {
            "ok": False,
            "error": f"Unsupported office format: {ext}. Use .pptx or .docx.",
        }

    if output_path is None:
        output_path = office_path

    try:
        # Step 1: convert CDXML → CDX + EMF via ChemDraw COM
        converted = batch_convert([str(cdxml_p)])
        if not converted:
            return {"ok": False, "error": "ChemDraw COM conversion returned no output."}
        item = converted[0]

        # Step 2: compute display dimensions + build OLE compound file
        w_emu, h_emu = get_cdxml_content_size(str(cdxml_p))
        ole_data = build_ole_compound_file(item["cdx_data"])

        items = [{
            "ole_data": ole_data,
            "emf_data": item["emf_data"],
            "width_emu": w_emu,
            "height_emu": h_emu,
            "name": item["name"],
        }]

        # Step 3: build/inject into Office file
        fmt = ext.lstrip(".")
        if ext == ".pptx":
            build_pptx(items, output_path)
        else:
            build_docx(items, output_path)

        return {
            "ok": True,
            "input_cdxml": str(cdxml_p),
            "output": str(Path(output_path).resolve()),
            "format": fmt,
            "num_objects_embedded": 1,
        }

    except ImportError as e:
        return {
            "ok": False,
            "error": (
                f"ChemDraw COM or Office library not available: {e}. "
                "Requires pywin32 (ChemDraw COM) and python-pptx/python-docx."
            ),
        }
    except Exception as e:
        return {
            "ok": False,
            "error": (
                f"Embedding failed: {e}. "
                "Ensure ChemDraw is installed and not currently running, "
                "and that the target file is a valid .pptx or .docx."
            ),
        }


# ---------------------------------------------------------------------------
# Tool 14: search_compound
# ---------------------------------------------------------------------------

@mcp.tool()
def search_compound(
    smiles: str,
    experiment_dir: str,
    similarity_threshold: float = 0.85,
) -> dict:
    """Search for a compound across experiment JSON files by SMILES similarity.

    Scans a directory of reaction JSON files (from parse_reaction) and returns
    exact matches and structurally similar compounds above the given Tanimoto
    threshold. Useful for finding related experiments, checking if a compound
    has been made before, or tracing a compound through a multi-step synthesis.

    This module is under active development. If unavailable, the tool returns
    a graceful error rather than crashing.

    Args:
        smiles:               SMILES string of the compound to search for.
                              Use resolve_name to get a validated SMILES first.
        experiment_dir:       Directory containing reaction JSON files to search.
        similarity_threshold: Tanimoto similarity cutoff (0–1). Default 0.85.

    Returns:
        Dict with keys: ok, query_smiles, exact_matches (list), similar_matches
        (list with similarity scores), total_files_searched.
        Returns {ok: False, error: "..."} if module unavailable or search fails.
    """
    if not smiles or not smiles.strip():
        return (
            "Usage: search_compound(smiles='...', experiment_dir='path/to/experiments')\n"
            "Searches reaction JSON files for exact or similar compounds by Tanimoto similarity.\n"
            "Examples:\n"
            "  search_compound(smiles='c1ccncc1', experiment_dir='experiments/')\n"
            "  search_compound(smiles='c1ccncc1', experiment_dir='experiments/', similarity_threshold=0.9)\n"
            "Tip: get a validated SMILES from resolve_name before searching."
        )

    try:
        from cdxml_toolkit.perception.compound_search import search_compound as _search
    except ImportError as e:
        return {
            "ok": False,
            "error": f"compound_search module not available: {e}",
        }

    d = Path(experiment_dir).resolve()
    if not d.is_dir():
        return {
            "ok": False,
            "error": (
                f"File not found: {d}. "
                "Check the path exists and use forward slashes."
            ),
        }

    try:
        result = _search(
            smiles,
            str(d),
            similarity_threshold=similarity_threshold,
        )
        if isinstance(result, dict):
            return result
        return {"ok": True, "data": result}
    except Exception as e:
        return {
            "ok": False,
            "error": (
                f"Search failed: {e}. "
                "Ensure the SMILES is valid (use resolve_name to obtain one) "
                "and that the directory contains reaction JSON files from parse_reaction."
            ),
        }


# ---------------------------------------------------------------------------
# Tool 15: render_to_png
# ---------------------------------------------------------------------------

@mcp.tool()
def render_to_png(
    cdxml_path: str,
    output_path: Optional[str] = None,
) -> dict:
    """Render a CDXML file to PNG using ChemDraw COM.

    Uses ChemDraw's native rendering engine (via COM automation) at 300 DPI
    with a solid white background. ChemDraw must be installed (Professional
    16+) and closed before calling this tool.

    This tool uses ChemDraw COM exclusively — no RDKit fallback. For a
    quick preview without ChemDraw, use draw_molecule which returns CDXML
    that can be opened directly.

    Args:
        cdxml_path:  Path to the CDXML file to render.
        output_path: Output PNG path. If not given, writes to the same
                     directory as the input with a .png extension.

    Returns:
        Dict with keys: ok, input, output (absolute path to PNG file).
        Returns {ok: False, error: "..."} if ChemDraw COM is unavailable
        or rendering fails.
    """
    if not cdxml_path or not cdxml_path.strip():
        return (
            "Usage: render_to_png(cdxml_path='scheme.cdxml', output_path='scheme.png')\n"
            "Renders CDXML to PNG at 300 DPI using ChemDraw COM.\n"
            "Examples:\n"
            "  render_to_png(cdxml_path='scheme.cdxml')\n"
            "  render_to_png(cdxml_path='scheme.cdxml', output_path='figures/scheme.png')\n"
            "Requires: ChemDraw Professional 16+ on Windows, must be closed before calling."
        )

    try:
        from cdxml_toolkit.chemdraw.cdxml_to_image import cdxml_to_image
    except ImportError as e:
        return {
            "ok": False,
            "error": (
                f"ChemDraw COM not available: {e}. "
                "Requires pywin32 and ChemDraw Professional 16+ on Windows."
            ),
        }

    p = _validate_file(cdxml_path, "CDXML file")

    try:
        out = cdxml_to_image(str(p), output_path=output_path, png_dpi=300)
        return {"ok": True, "input": str(p), "output": str(Path(out).resolve())}
    except Exception as e:
        return {
            "ok": False,
            "error": (
                f"Rendering failed: {e}. "
                "Ensure ChemDraw Professional 16+ is installed and not currently running."
            ),
            "input": str(p),
        }


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="cdxml-toolkit MCP server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--transport",
        choices=["stdio", "http"],
        default="stdio",
        help="MCP transport mode (default: stdio)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port for HTTP transport (default: 8000)",
    )
    parser.add_argument(
        "--no-preload-decimer",
        action="store_true",
        help=(
            "Skip pre-loading the DECIMER model at startup. "
            "Saves ~25 s startup time and ~800 MB RAM, but first "
            "extract_structures_from_image call will be slow."
        ),
    )
    args = parser.parse_args()

    # Suppress TensorFlow C-level logging before any TF import.
    # This prevents TF's stdout/stderr writes from corrupting the
    # MCP JSON-RPC stdio channel.
    os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")
    os.environ.setdefault("TF_ENABLE_ONEDNN_OPTS", "0")

    # Pre-import RDKit and load the reagent DB before the MCP event loop
    # starts.  On some Windows/Python configurations, importing the RDKit C
    # extension from inside the async event loop's thread causes a hang
    # (the DLL load never completes once anyio has wrapped stdout/stderr).
    # Doing it here -- before mcp.run() -- avoids the issue entirely and
    # also eliminates the 1-2 s first-call delay for resolve_name.
    try:
        from rdkit import Chem  # noqa: F401
        from cdxml_toolkit.resolve.reagent_db import get_reagent_db
        get_reagent_db()
    except Exception:
        pass  # graceful: server still works, just slower on first call

    # Pre-load the DECIMER model in a background thread so the MCP server
    # is immediately available for other tools (resolve_name, etc.) while
    # the ~25 s model load happens asynchronously.  Disable with
    # --no-preload-decimer if DECIMER is not installed or RAM is tight.
    if not args.no_preload_decimer:
        import threading

        def _bg_load_decimer():
            import time as _t
            _t0 = _t.perf_counter()
            try:
                from cdxml_toolkit.image.structure_from_image import _load_decimer
                _load_decimer(hand_drawn=False)
                import sys
                print(
                    f"[cdxml-toolkit] DECIMER preloaded in "
                    f"{_t.perf_counter() - _t0:.1f}s",
                    file=sys.stderr,
                )
            except Exception as exc:
                import sys
                print(
                    f"[cdxml-toolkit] DECIMER preload skipped: {exc}",
                    file=sys.stderr,
                )

        t = threading.Thread(target=_bg_load_decimer, daemon=True)
        t.start()

    if args.transport == "stdio":
        mcp.run(transport="stdio")
    else:
        mcp.run(transport="streamable-http", host="0.0.0.0", port=args.port)


if __name__ == "__main__":
    main()
