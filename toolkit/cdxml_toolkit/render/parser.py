"""
parser.py — Parse YAML scheme files into SchemeDescriptor dataclasses.

Validates structure references, layout keywords, and produces clear error
messages for malformed input.

A ``_normalize_scheme_data`` preprocessing pass converts common LLM-generated
patterns (inline structures, ``reagents`` key, ``species`` alias, bare SMILES
refs, etc.) into the canonical format before the main parsing logic runs.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import yaml

from .schema import (
    ArrowContent,
    RunArrowEntry,
    SchemeDescriptor,
    SectionDescriptor,
    StepDescriptor,
    StepRunArrows,
    StructureRef,
)

# Valid layout and wrap keywords
VALID_LAYOUTS = {
    "linear", "sequential", "divergent", "stacked-rows",
    "numbered-parallel", "convergent",
}
VALID_WRAPS = {"repeat", "serpentine", "none"}
VALID_ARROW_STYLES = {"solid", "dashed", "failed"}

# Unambiguous SMILES syntax characters (never appear in plain identifiers)
_SMILES_SYNTAX_RE = re.compile(r'[=()\[\]#@\\\/]')

# Letters that appear in English words / abbreviations but are NOT valid
# SMILES atom symbols or bond/ring characters.
# SMILES-valid letters: B C F H I K L M N O P R S V (uppercase)
#                       b c n o p s (aromatic lowercase)
#                       r l (part of Br, Cl two-char elements)
# "Word-only" letters: A D E G J Q T U W X Y Z (uppercase)
#                      a d e f g h i j k m q t u v w x y z (lowercase,
#                        except c n o p s b r l)
_WORD_ONLY_LETTER_RE = re.compile(r'[ADEGJQTUWXYZadeghijkmqtuvwxyz]')

# Pure uppercase organic-element chains of 3+ chars with no underscores,
# hyphens, or digits (e.g. "CCO", "CCCC", "COC", "CCOCC")
_ORGANIC_CHAIN_RE = re.compile(r'^[BCFIKLMNOPRSV]{3,}$')


class SchemeParseError(Exception):
    """Raised when YAML content is invalid or violates schema rules."""
    pass


def parse_yaml(source: Union[str, Path]) -> SchemeDescriptor:
    """
    Parse a YAML file or string into a SchemeDescriptor.

    Parameters
    ----------
    source : str or Path
        If a Path or string ending in .yaml/.yml, read as file.
        Otherwise, interpret as raw YAML text.

    Returns
    -------
    SchemeDescriptor

    Raises
    ------
    SchemeParseError
        On any validation failure.
    """
    text = _load_yaml_text(source)
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as e:
        raise SchemeParseError(f"Invalid YAML syntax: {e}") from e

    if not isinstance(data, dict):
        raise SchemeParseError("Top-level YAML must be a mapping (dict)")

    # Allow either top-level keys directly or wrapped in 'scheme:'
    if "scheme" in data and isinstance(data["scheme"], dict):
        data = data["scheme"]

    # Normalize LLM-friendly patterns into canonical form before parsing
    data = _normalize_scheme_data(data)

    return _parse_scheme(data)


# ---------------------------------------------------------------------------
# Normalization helpers
# ---------------------------------------------------------------------------

def _smiles_id(smiles: str, existing: Dict[str, Any], counter: List[int]) -> str:
    """
    Return a deterministic, collision-safe structure ID for a SMILES string.

    Uses the first 8 hex chars of the SHA-1 of the SMILES.  Falls back to a
    sequential ``struct_N`` name when the hash already exists with a different
    SMILES (collision is astronomically unlikely but handled anyway).
    """
    token = "s_" + hashlib.sha1(smiles.encode()).hexdigest()[:8]
    if token not in existing:
        return token
    # Hash collision or same SMILES used twice — return existing key if same
    entry = existing[token]
    existing_smiles = entry.get("smiles") if isinstance(entry, dict) else entry
    if existing_smiles == smiles:
        return token  # already registered with this SMILES
    # True collision: fall back to sequential name
    idx = counter[0]
    counter[0] += 1
    return f"struct_{idx}"


def _looks_like_smiles(s: str) -> bool:
    """
    Return True if *s* looks like a SMILES string rather than a structure ID.

    Strategy: reject strings that contain "word-only" letters (letters that
    are not valid in any SMILES notation) or identifier punctuation (``_``,
    space, ``-``).  Then apply positive evidence checks.

    "Word-only" letters are those that never appear as SMILES atom symbols
    or in element two-char symbols: ``A``, ``D``, ``E``, ``G``, ``J``, ``Q``,
    ``T``, ``U``, ``W``, ``X``, ``Y``, ``Z`` (uppercase) and all lowercase
    letters except ``b``, ``c``, ``h``, ``n``, ``o``, ``p``, ``r``, ``s``,
    ``l`` (which appear in two-char elements like Br, Cl or aromatic atoms).
    In practice ``h`` and ``l`` and ``r`` can appear in words too, but the
    other word-only letters (``d``, ``e``, ``g``, etc.) are highly diagnostic.

    Positive evidence tiers:

    1. Unambiguous SMILES syntax: ``=``, ``(``, ``)``, ``[``, ``]``, ``#``,
       ``@``, ``\\``, ``/``.

    2. Pure uppercase organic-element chain of 3+ chars containing ``C``
       (catches ``CCO``, ``CCCC``, ``COC`` while rejecting ``SM``, ``TFA``).

    3. Single-character organic element symbol.
    """
    # Reject identifiers
    if "_" in s or " " in s:
        return False
    if "-" in s and not _SMILES_SYNTAX_RE.search(s):
        return False
    # Strings with word-only letters are plain names/abbreviations
    if _WORD_ONLY_LETTER_RE.search(s):
        return False

    if len(s) == 1 and s in "BCFIKLMNOPRSV":
        return True  # single organic element
    if _SMILES_SYNTAX_RE.search(s):
        return True
    # At this point the string contains only SMILES-compatible characters.
    # Require at least one lowercase letter (aromatic atom) OR a pure
    # uppercase organic chain of length >= 3 with a carbon.
    if re.search(r'[a-z]', s):  # has an aromatic or two-char element letter
        return True
    if _ORGANIC_CHAIN_RE.match(s) and "C" in s:
        return True
    return False


def _normalize_entry_list(
    entries: Any,
    structures: Dict[str, Any],
    counter: List[int],
) -> List[str]:
    """
    Normalise a substrate/product/above-arrow structures list.

    Each entry may be:
    - A plain string: kept as-is (may be an existing ID or bare SMILES).
    - A dict with at least ``smiles``: auto-registered into *structures*.

    Returns a list of structure ID strings.
    """
    if not isinstance(entries, list):
        entries = [entries]

    result: List[str] = []
    for entry in entries:
        if isinstance(entry, dict):
            smiles = entry.get("smiles")
            name = entry.get("name")
            label = entry.get("label")
            sid = entry.get("id")
            if smiles and not sid:
                sid = _smiles_id(smiles, structures, counter)
            elif not sid:
                # No smiles and no id — use name as key, or generate one
                if name:
                    sid = name
                else:
                    sid = f"struct_{counter[0]}"
                    counter[0] += 1
            # Register if not already present
            if sid not in structures:
                struct_def: Dict[str, Any] = {}
                if smiles:
                    struct_def["smiles"] = smiles
                if name:
                    struct_def["name"] = name
                if label:
                    struct_def["label"] = label
                structures[sid] = struct_def if struct_def else smiles or sid
            result.append(sid)
        else:
            result.append(str(entry))

    return result


def _normalize_scheme_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalise LLM-friendly YAML patterns into the canonical form expected by
    ``_parse_scheme``.

    This function is **idempotent**: running it on already-canonical YAML
    produces the same result.  It mutates and returns a shallow copy of *data*.

    Changes applied
    ---------------
    1. ``species`` key is renamed to ``structures``.
    2. ``structures`` given as a list of dicts is converted to a keyed mapping.
    3. Inline structure dicts inside ``substrates``/``products``/
       ``above_arrow.structures`` are auto-registered and replaced with IDs.
    4. Bare SMILES strings in ``substrates``/``products`` are auto-registered.
    5. ``reactants`` is accepted as an alias for ``substrates`` inside steps.
    6. ``text`` scalar is wrapped in a list inside ``above_arrow``/``below_arrow``.
    7. ``reagents`` list inside a step is distributed into ``above_arrow`` or
       ``below_arrow`` depending on an ``above_arrow`` flag on each reagent.
    8. Redundant ``id`` field inside structure defs is silently accepted
       (already handled by ``_parse_structure``; nothing to do here).
    """
    import copy
    data = copy.deepcopy(data)

    # 1. Accept ``species`` / ``substrates`` as alias for ``structures``
    for alias in ("species", "substrates"):
        if alias in data and "structures" not in data:
            data["structures"] = data.pop(alias)
            break

    # 2. Accept ``structures`` as a list of dicts (convert to keyed mapping)
    raw_structs = data.get("structures")
    if isinstance(raw_structs, list):
        converted: Dict[str, Any] = {}
        for idx, item in enumerate(raw_structs):
            if isinstance(item, dict):
                key = str(item.get("id", f"struct_{idx}"))
                # Remove the redundant 'id' key from the value dict to keep
                # it clean (harmless either way — _parse_structure ignores it)
                val = {k: v for k, v in item.items() if k != "id"}
                converted[key] = val if val else item.get("smiles", f"struct_{idx}")
            else:
                converted[f"struct_{idx}"] = str(item)
        data["structures"] = converted

    # Work with the normalised structures mapping (may be empty / absent)
    structures: Dict[str, Any] = data.setdefault("structures", {})
    counter = [0]  # mutable counter shared across steps

    # Normalise each step
    raw_steps = data.get("steps", [])
    if not isinstance(raw_steps, list):
        raw_steps = []
    normalised_steps = []
    for step in raw_steps:
        if not isinstance(step, dict):
            normalised_steps.append(step)
            continue
        step = dict(step)  # shallow copy so we can mutate

        # 5. ``reactants`` alias for ``substrates``
        if "reactants" in step and "substrates" not in step:
            step["substrates"] = step.pop("reactants")

        # 3 & 4. Inline / bare-SMILES substrates
        if "substrates" in step:
            step["substrates"] = _normalize_entry_list(
                step["substrates"], structures, counter
            )
            # Bare SMILES strings in the resulting list
            step["substrates"] = _register_bare_smiles(
                step["substrates"], structures, counter
            )

        # 3 & 4. Inline / bare-SMILES products
        if "products" in step:
            step["products"] = _normalize_entry_list(
                step["products"], structures, counter
            )
            step["products"] = _register_bare_smiles(
                step["products"], structures, counter
            )

        # 6. ``text`` as string in above_arrow / below_arrow
        for arrow_key in ("above_arrow", "below_arrow"):
            if arrow_key in step and isinstance(step[arrow_key], dict):
                arrow = dict(step[arrow_key])
                if isinstance(arrow.get("text"), str):
                    arrow["text"] = [arrow["text"]]
                # 3. Inline structs inside above_arrow.structures
                if "structures" in arrow:
                    arrow["structures"] = _normalize_entry_list(
                        arrow["structures"], structures, counter
                    )
                    arrow["structures"] = _register_bare_smiles(
                        arrow["structures"], structures, counter
                    )
                step[arrow_key] = arrow

        # 7. ``reagents`` key: distribute into above_arrow / below_arrow
        if "reagents" in step:
            reagents = step.pop("reagents")
            if not isinstance(reagents, list):
                reagents = [reagents]
            for reagent in reagents:
                if isinstance(reagent, dict):
                    goes_above = reagent.get("above_arrow", False)
                    # Normalise the reagent as a structure entry
                    reg_ids = _normalize_entry_list([reagent], structures, counter)
                    # Also accept bare SMILES
                    reg_ids = _register_bare_smiles(reg_ids, structures, counter)
                    if goes_above:
                        above = step.setdefault("above_arrow", {})
                        if isinstance(above, dict):
                            structs = above.setdefault("structures", [])
                            if isinstance(structs, list):
                                structs.extend(reg_ids)
                    else:
                        # Render as text using the display name or SMILES
                        below = step.setdefault("below_arrow", {})
                        if isinstance(below, dict):
                            texts = below.setdefault("text", [])
                            if isinstance(texts, list):
                                for rid in reg_ids:
                                    entry = structures.get(rid, {})
                                    display = (
                                        entry.get("name") if isinstance(entry, dict)
                                        else None
                                    ) or rid
                                    texts.append(display)
                else:
                    # Plain string reagent — add as below_arrow text
                    below = step.setdefault("below_arrow", {})
                    if isinstance(below, dict):
                        texts = below.setdefault("text", [])
                        if isinstance(texts, list):
                            texts.append(str(reagent))

        normalised_steps.append(step)
    data["steps"] = normalised_steps

    # Normalise steps inside sections as well
    raw_sections = data.get("sections", [])
    if isinstance(raw_sections, list):
        for sec in raw_sections:
            if isinstance(sec, dict) and "steps" in sec:
                sec_steps = sec.get("steps", [])
                if isinstance(sec_steps, list):
                    # Re-use the same normalisation by temporarily building a
                    # sub-dict and merging back
                    sub = _normalize_scheme_data(
                        {"structures": structures, "steps": sec_steps}
                    )
                    sec["steps"] = sub["steps"]
                    structures.update(sub.get("structures", {}))

    return data


def _register_bare_smiles(
    ids: List[str],
    structures: Dict[str, Any],
    counter: List[int],
) -> List[str]:
    """
    For each string in *ids* that is not an existing structure key and looks
    like SMILES, auto-register it and return the canonical ID in its place.
    """
    result: List[str] = []
    for sid in ids:
        if sid not in structures and _looks_like_smiles(sid):
            new_id = _smiles_id(sid, structures, counter)
            structures[new_id] = {"smiles": sid}
            result.append(new_id)
        else:
            result.append(sid)
    return result


def _load_yaml_text(source: Union[str, Path]) -> str:
    """Load YAML text from a file path or return raw string."""
    if isinstance(source, Path):
        return source.read_text(encoding="utf-8")
    if isinstance(source, str) and (
        source.endswith(".yaml") or source.endswith(".yml")
    ):
        return Path(source).read_text(encoding="utf-8")
    return source


def _parse_scheme(data: Dict[str, Any]) -> SchemeDescriptor:
    """Parse the scheme-level dict."""
    # --- Source (reaction_parser JSON) ---
    source = data.get("source")
    if source is not None:
        source = str(source)

    # --- Structures ---
    raw_structs = data.get("structures", {})
    if raw_structs is None:
        raw_structs = {}
    if not isinstance(raw_structs, dict):
        raise SchemeParseError("'structures' must be a mapping")
    structures = {}
    for key, val in raw_structs.items():
        key = str(key)
        structures[key] = _parse_structure(key, val)

    # --- Sections (for stacked-rows layout) ---
    raw_sections = data.get("sections", [])
    if not isinstance(raw_sections, list):
        raise SchemeParseError("'sections' must be a list")
    sections = [_parse_section(i, s) for i, s in enumerate(raw_sections)]

    # --- Steps ---
    raw_steps = data.get("steps", [])
    if not isinstance(raw_steps, list):
        raise SchemeParseError("'steps' must be a list")
    if not raw_steps and not sections:
        raise SchemeParseError("At least one step is required (or use 'sections' for stacked-rows)")
    steps = [_parse_step(i, s) for i, s in enumerate(raw_steps)]

    # --- Validate structure refs in steps and sections ---
    # When source is present, refs may be resolved from JSON at render time,
    # so we only validate refs that are NOT in the declared structures block
    # (the renderer will handle resolution failures for source-backed refs).
    def _validate_step_refs(step_list, context_prefix=""):
        for i, step in enumerate(step_list):
            prefix = f"{context_prefix}step {i+1}"
            _validate_refs(f"{prefix} substrates", step.substrates, structures)
            _validate_refs(f"{prefix} products", step.products, structures)
            if step.above_arrow:
                _validate_refs(
                    f"{prefix} above_arrow.structures",
                    step.above_arrow.structures,
                    structures,
                )
            if step.below_arrow:
                _validate_refs(
                    f"{prefix} below_arrow.structures",
                    step.below_arrow.structures,
                    structures,
                )

    if not source:
        _validate_step_refs(steps)
        for sec_idx, sec in enumerate(sections):
            _validate_step_refs(sec.steps, f"section {sec_idx+1} ")

    # --- Layout ---
    layout = str(data.get("layout", "linear"))
    if layout not in VALID_LAYOUTS:
        raise SchemeParseError(
            f"Invalid layout '{layout}'. Must be one of: {sorted(VALID_LAYOUTS)}"
        )

    # --- Wrap ---
    wrap = str(data.get("wrap", "repeat"))
    if wrap not in VALID_WRAPS:
        raise SchemeParseError(
            f"Invalid wrap '{wrap}'. Must be one of: {sorted(VALID_WRAPS)}"
        )

    # --- Steps per row ---
    steps_per_row = data.get("steps_per_row")
    if steps_per_row is not None:
        steps_per_row = int(steps_per_row)
        if steps_per_row < 1:
            raise SchemeParseError("steps_per_row must be >= 1")

    # --- Title ---
    title = data.get("title")
    if title is not None:
        title = str(title)

    # --- Run arrows ---
    raw_runs = data.get("run_arrows", [])
    if not isinstance(raw_runs, list):
        raise SchemeParseError("'run_arrows' must be a list")
    run_arrows = [_parse_run_arrows(r) for r in raw_runs]

    # --- Condition key ---
    condition_key = data.get("condition_key")
    if condition_key is not None and not isinstance(condition_key, dict):
        raise SchemeParseError("'condition_key' must be a mapping")

    return SchemeDescriptor(
        source=source,
        structures=structures,
        steps=steps,
        layout=layout,
        wrap=wrap,
        steps_per_row=steps_per_row,
        title=title,
        run_arrows=run_arrows,
        condition_key=condition_key,
        sections=sections,
    )


def _parse_section(index: int, data: Any) -> SectionDescriptor:
    """Parse a single section entry (for stacked-rows layout)."""
    if not isinstance(data, dict):
        raise SchemeParseError(
            f"Section {index+1} must be a mapping, got {type(data).__name__}"
        )
    label = data.get("label")
    if label is not None:
        label = str(label)

    raw_steps = data.get("steps", [])
    if not isinstance(raw_steps, list):
        raise SchemeParseError(f"Section {index+1} 'steps' must be a list")
    if not raw_steps:
        raise SchemeParseError(f"Section {index+1} must have at least one step")
    steps = [_parse_step(i, s) for i, s in enumerate(raw_steps)]

    layout = str(data.get("layout", "linear"))

    return SectionDescriptor(label=label, steps=steps, layout=layout)


def _parse_structure(key: str, val: Any) -> StructureRef:
    """Parse a single structure entry."""
    if isinstance(val, str):
        # Shorthand: just a SMILES string
        return StructureRef(id=key, smiles=val)
    if not isinstance(val, dict):
        raise SchemeParseError(
            f"Structure '{key}' must be a mapping or SMILES string, got {type(val).__name__}"
        )
    return StructureRef(
        id=key,
        smiles=val.get("smiles"),
        name=val.get("name"),
        file=val.get("file"),
        cdxml_id=val.get("cdxml_id"),
        label=val.get("label"),
    )


def _parse_step(index: int, data: Any) -> StepDescriptor:
    """Parse a single step entry."""
    if not isinstance(data, dict):
        raise SchemeParseError(f"Step {index+1} must be a mapping, got {type(data).__name__}")

    substrates = _as_str_list(data.get("substrates", []), f"step {index+1} substrates")
    products = _as_str_list(data.get("products", []), f"step {index+1} products")

    if not substrates:
        raise SchemeParseError(f"Step {index+1} must have at least one substrate")
    if not products:
        raise SchemeParseError(f"Step {index+1} must have at least one product")

    above = _parse_arrow_content(data.get("above_arrow"), f"step {index+1} above_arrow")
    below = _parse_arrow_content(data.get("below_arrow"), f"step {index+1} below_arrow")

    return StepDescriptor(
        substrates=substrates,
        products=products,
        above_arrow=above,
        below_arrow=below,
        yield_=data.get("yield"),
        number=data.get("number"),
        id=data.get("id"),
        arrow_style=_validate_arrow_style(data.get("arrow_style", "solid"), index),
    )


def _parse_arrow_content(data: Any, context: str) -> Optional[ArrowContent]:
    """Parse above_arrow or below_arrow content."""
    if data is None:
        return None

    # Normalize: if arrow content is a list, merge into a single dict.
    # LLMs commonly write: above_arrow: [{structures: [...]}, "text"]
    # or: above_arrow: [acid_id]  (bare list of structure refs)
    if isinstance(data, list):
        merged = {"structures": [], "text": []}
        for item in data:
            if isinstance(item, dict):
                for k, v in item.items():
                    if k == "structures" and isinstance(v, list):
                        merged["structures"].extend(v)
                    elif k == "text":
                        if isinstance(v, list):
                            merged["text"].extend(v)
                        elif isinstance(v, str):
                            merged["text"].append(v)
                    elif k == "structure":
                        # singular "structure: acid_id"
                        merged["structures"].append(v)
                    else:
                        merged["text"].append(str(v))
            elif isinstance(item, str):
                # Bare string in list — could be structure ID or text
                merged["structures"].append(item)
        data = merged

    # Normalize: if arrow content is a bare string, treat as text
    if isinstance(data, str):
        data = {"text": [data]}

    if not isinstance(data, dict):
        raise SchemeParseError(
            f"'{context}' must be a mapping (e.g. {{structures: [ID], text: ['conditions']}}), "
            f"got {type(data).__name__}. "
            f"Correct format: above_arrow: {{structures: [ReagentID], text: ['HATU']}}"
        )
    structures = _as_str_list(data.get("structures", []), f"{context}.structures")
    text = _as_str_list(data.get("text", []), f"{context}.text")
    if not structures and not text:
        return None
    return ArrowContent(structures=structures, text=text)


def _parse_run_arrows(data: Any) -> StepRunArrows:
    """Parse a run_arrows entry."""
    if not isinstance(data, dict):
        raise SchemeParseError(f"run_arrows entry must be a mapping")
    step = data.get("step")
    if step is None:
        raise SchemeParseError("run_arrows entry must have a 'step' field")
    step = int(step)
    raw_runs = data.get("runs", [])
    if not isinstance(raw_runs, list):
        raise SchemeParseError(f"run_arrows step {step} 'runs' must be a list")
    runs = []
    for r in raw_runs:
        if not isinstance(r, dict):
            raise SchemeParseError(f"run entry must be a mapping")
        inp = r.get("input", "")
        out = r.get("output", "")
        if not inp:
            raise SchemeParseError(
                f"run entry must have an 'input' field"
            )
        note = r.get("note")
        if note is not None:
            note = str(note)
        runs.append(RunArrowEntry(input_label=str(inp), output_label=str(out),
                                  note=note))
    return StepRunArrows(step=step, runs=runs)


def _validate_arrow_style(style: str, step_idx: int) -> str:
    """Validate arrow_style value."""
    style = str(style)
    if style not in VALID_ARROW_STYLES:
        raise SchemeParseError(
            f"Step {step_idx+1}: invalid arrow_style '{style}'. "
            f"Must be one of: {sorted(VALID_ARROW_STYLES)}"
        )
    return style


def _validate_refs(
    context: str,
    refs: List[str],
    structures: Dict[str, StructureRef],
) -> None:
    """Check that all refs point to defined structures.

    Undeclared refs are auto-registered as bare StructureRefs so the renderer
    can attempt resolution via reagent_db (name → SMILES lookup).
    """
    for ref in refs:
        if ref not in structures:
            # Auto-register as a bare ref — renderer will try reagent_db
            structures[ref] = StructureRef(id=ref)


def _as_str_list(val: Any, context: str) -> List[str]:
    """Coerce a value to a list of strings."""
    if val is None:
        return []
    if isinstance(val, str):
        return [val]
    if isinstance(val, list):
        return [str(v) for v in val]
    raise SchemeParseError(f"'{context}' must be a list or string, got {type(val).__name__}")
