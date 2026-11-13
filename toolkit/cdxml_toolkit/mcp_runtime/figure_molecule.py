"""Standalone molecules and multi-structure grids for draw_figure.

Draws a single molecule or a grid of structures without reaction arrows, with
the same grounding, style presets, house styles, abbreviations, colours,
decorations, layout checks, semantic read-back and optional native rendering as
a reaction scheme.
"""
from __future__ import annotations

import copy
from collections.abc import Mapping
from pathlib import Path
from typing import Any
import xml.etree.ElementTree as ET

from rdkit import Chem
from rdkit.Chem import Descriptors, rdFMCS, rdMolDescriptors

from ..constants import ACS_BOND_LENGTH
from ..publication.house_styles import APPLIED_FIGURE_CONVENTIONS, HouseStyle
from ..render import renderer
from ..render.schema import StructureRef
from . import artifact_safety, figure_house, figure_lint

MOLECULE_KEYS = {"kind", "species", "max_width", "columns", "title", "panel_label", "style", "numbering", "properties"}
SPECIES_KEYS = {
    "id", "smiles", "name", "label", "caption", "orientation",
    "ring_fills", "atom_halos", "ts_bracket", "box",
    "color", "atom_colors", "bond_colors", "abbreviate",
}
NUMBERING_STYLES = (
    "arabic", "roman", "letter",
    "bold_number", "bold_roman", "plain_roman", "bold_letter", "int_number",
    "none",
)
PROPERTY_KEYS = ("formula", "mw", "exact_mass")
MAX_SPECIES = 200
X0 = 100.0
FIRST_ROW_TOP = 120.0
TITLE_ROOM = 20.0


def _assign_default_ids(brief: dict) -> dict:
    """Fill in ``id`` only for dict entries where the ``id`` key was omitted."""
    species = brief.get("species")
    if not isinstance(species, list):
        return brief
    taken = {str(sp["id"]) for sp in species if isinstance(sp, dict) and str(sp.get("id") or "").strip()}
    next_num = 1
    for entry in species:
        if isinstance(entry, dict) and "id" not in entry:
            while f"s{next_num}" in taken:
                next_num += 1
            ident = f"s{next_num}"
            entry["id"] = ident
            taken.add(ident)
            next_num += 1
    return brief


def _validate(brief: dict) -> list[str]:
    from . import figure_draw

    errors: list[str] = []
    unknown = sorted(set(brief) - MOLECULE_KEYS)
    if unknown:
        errors.append(f"Unknown brief keys: {unknown}")
    style_error = figure_draw.style_preset_error(brief.get("style"))
    if style_error:
        errors.append(style_error)
    width = brief.get("max_width")
    if width is not None and not (
        isinstance(width, (int, float)) and not isinstance(width, bool) and width > 0
    ):
        errors.append("max_width must be a positive number of points.")
    columns = brief.get("columns")
    if columns is not None and not (isinstance(columns, int) and not isinstance(columns, bool) and columns >= 1):
        errors.append("columns must be a positive whole number.")
    numbering = brief.get("numbering")
    if numbering is not None and not isinstance(numbering, bool) and numbering not in NUMBERING_STYLES:
        errors.append(f"numbering must be a boolean or one of {list(NUMBERING_STYLES)}.")
    properties = brief.get("properties")
    if properties is not None and not isinstance(properties, bool):
        if (
            not isinstance(properties, list)
            or not properties
            or any(not isinstance(k, str) or k not in PROPERTY_KEYS for k in properties)
        ):
            errors.append(f"properties must be a boolean or a non-empty list of {list(PROPERTY_KEYS)}.")
    errors += figure_house.panel_errors(brief)

    species = brief.get("species")
    ids: set[str] = set()
    if not isinstance(species, list) or not species:
        return errors + ["species: list at least one structure with a smiles or a name."]
    if len(species) > MAX_SPECIES:
        errors.append(f"A structure panel holds at most {MAX_SPECIES} structures.")
    for entry in species:
        if not isinstance(entry, dict) or not str(entry.get("id") or "").strip():
            errors.append("Every species needs an id.")
            continue
        ident = str(entry["id"])
        if ident in ids:
            errors.append(f"Species {ident}: duplicate id.")
        ids.add(ident)
        extra = sorted(set(entry) - SPECIES_KEYS)
        if extra:
            errors.append(f"Species {ident}: unknown keys {extra}.")
        if not entry.get("smiles") and not entry.get("name"):
            errors.append(f"Species {ident} needs a smiles or a name.")
        if entry.get("orientation") not in (None, *renderer.ORIENTATIONS):
            errors.append(f"Species {ident}: orientation must be one of {list(renderer.ORIENTATIONS)}.")
        errors += figure_house.species_style_errors(entry)
    return errors


_ROMAN_NUMERALS = (
    (100, "C"), (90, "XC"), (50, "L"), (40, "XL"),
    (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I"),
)


def _roman(number: int) -> str:
    rem = number
    parts: list[str] = []
    for value, glyph in _ROMAN_NUMERALS:
        while rem >= value:
            parts.append(glyph)
            rem -= value
    return "".join(parts)


def _letter(number: int) -> str:
    rem = number
    chars: list[str] = []
    while rem > 0:
        rem, mod = divmod(rem - 1, 26)
        chars.append(chr(ord("a") + mod))
    return "".join(reversed(chars))


def _format_number(index: int, style: str) -> str:
    if style in ("roman", "bold_roman", "plain_roman"):
        return _roman(index)
    if style in ("letter", "bold_letter"):
        return _letter(index)
    if style == "int_number":
        return f"Int-{index}"
    return str(index)


def _numbering_face(style: str) -> str | None:
    if style == "plain_roman":
        return "plain"
    if style in ("bold_number", "bold_roman", "bold_letter", "int_number"):
        return "bold"
    return None


def _resolve_numbering(
    brief: dict, grounded: list[dict], house: HouseStyle | None
) -> tuple[str | None, str | None]:
    """Fill missing species labels when numbering or a structure_panel card convention asks for it."""
    raw = brief.get("numbering")
    if raw is not None:
        if raw is False or raw == "none":
            return None, "numbering=none" if raw == "none" else None
        style = "bold_number" if raw is True else str(raw)
        source = f"numbering={style}"
    elif house is not None:
        card_style = house.figure_convention("structure_panel", "intermediate_label_style")
        if card_style is None:
            return None, None
        if card_style == "none":
            return None, "structure_panel.intermediate_label_style=none"
        if len(grounded) <= 1 and brief.get("kind") != "structure_panel":
            return None, None
        style = str(card_style)
        source = f"structure_panel.intermediate_label_style={style}"
    else:
        return None, None

    by_id = {str(sp["id"]): sp for sp in brief.get("species") or [] if isinstance(sp, Mapping) and sp.get("id")}
    assigned = False
    for index, g in enumerate(grounded, 1):
        sp = by_id.get(str(g["id"]))
        if sp is not None and sp.get("label") in (None, ""):
            label = _format_number(index, style)
            sp["label"] = label
            g["label"] = label
            assigned = True
    report_tag = source if (assigned or (house is not None and source.startswith("structure_panel."))) else None
    return _numbering_face(style), report_tag


def _populate_properties(brief: dict, grounded: list[dict]) -> str | None:
    """Populate formula/MW/exact-mass captions when ``properties`` is requested."""
    spec = brief.get("properties")
    if not spec:
        return None
    keys = ["formula", "mw"] if spec is True else [str(k) for k in spec]
    by_id = {str(sp["id"]): sp for sp in brief.get("species") or [] if isinstance(sp, Mapping) and sp.get("id")}
    populated = 0
    for g in grounded:
        sp = by_id.get(str(g["id"]))
        if sp is None or sp.get("caption") not in (None, "", []):
            continue
        mol = Chem.MolFromSmiles(g["smiles"])
        if mol is None:
            continue
        parts: list[str] = []
        for key in keys:
            if key == "formula":
                parts.append(rdMolDescriptors.CalcMolFormula(mol))
            elif key == "mw":
                parts.append(f"MW {Descriptors.MolWt(mol):.2f}")
            elif key == "exact_mass":
                parts.append(f"Exact {Descriptors.ExactMolWt(mol):.2f}")
        if parts:
            sp["caption"] = ", ".join(parts)
            populated += 1
    return f"properties={','.join(keys)}" if populated else None


def _apply_panel_highlights(brief: dict, grounded: list[dict], house: HouseStyle | None) -> str | None:
    """Apply ``structure_panel.highlight_fill`` or fall back to top-level ``highlight_fill``."""
    panel_fill = house.figure_convention("structure_panel", "highlight_fill") if house else None
    if not panel_fill:
        return figure_house.add_highlight_fills(brief, grounded, house)
    smiles = {g["id"]: g["smiles"] for g in grounded}
    filled = 0
    for entry in brief["species"]:
        if not isinstance(entry, dict) or entry.get("ring_fills"):
            continue
        mol = Chem.MolFromSmiles(smiles.get(str(entry["id"]), ""))
        rings = list(mol.GetRingInfo().AtomRings()) if mol is not None else []
        if rings:
            largest = max(range(len(rings)), key=lambda i: len(rings[i]))
            entry["ring_fills"] = [{"ring_index": largest, "color": panel_fill}]
            filled += 1
    return f"structure_panel.highlight_fill={panel_fill}" if filled else None


def _apply_panel_variation_color(brief: dict, grounded: list[dict], house: HouseStyle | None) -> str | None:
    """Paint varied atoms beyond the shared scaffold using ``structure_panel.variation_color``."""
    color = house.figure_convention("structure_panel", "variation_color") if house else None
    if not color or len(grounded) < 2:
        return None
    mols = [Chem.MolFromSmiles(g["smiles"]) for g in grounded]
    if any(m is None for m in mols):
        return None
    mcs = rdFMCS.FindMCS(mols, ringMatchesRingOnly=True, completeRingsOnly=False, timeout=2)
    if mcs.canceled or mcs.numAtoms < 3 or not mcs.smartsString:
        return None
    core = Chem.MolFromSmarts(mcs.smartsString)
    if core is None:
        return None
    by_id = {str(sp["id"]): sp for sp in brief.get("species") or [] if isinstance(sp, Mapping) and sp.get("id")}
    painted = 0
    for g, mol in zip(grounded, mols):
        sp = by_id.get(str(g["id"]))
        if sp is None or any(k in sp for k in ("color", "atom_colors", "bond_colors")):
            continue
        match = mol.GetSubstructMatch(core)
        if not match:
            continue
        core_atoms = set(match)
        varied = [a.GetIdx() for a in mol.GetAtoms() if a.GetIdx() not in core_atoms]
        if not varied:
            continue
        sp["atom_colors"] = [{"atoms": varied, "color": color}]
        cross_bonds = [
            [bond.GetBeginAtomIdx(), bond.GetEndAtomIdx()]
            for bond in mol.GetBonds()
            if (bond.GetBeginAtomIdx() in core_atoms) != (bond.GetEndAtomIdx() in core_atoms)
        ]
        if cross_bonds:
            sp["bond_colors"] = [{"bonds": cross_bonds, "color": color}]
        painted += 1
    return f"structure_panel.variation_color={color}" if painted else None


def _apply_panel_house_labels(
    cdxml: Any,
    grounded: list[dict],
    house: HouseStyle | None,
    face_override: str | None = None,
) -> tuple[Any, list[str], list[str]]:
    """Apply compound-label conventions without expecting reaction steps."""
    applied: list[str] = []
    skipped = (
        ["the reaction-scheme conventions (yield placement, arrows, conditions) apply to schemes only"]
        if house is not None
        else []
    )
    root = ET.fromstring(str(cdxml).split("?>", 1)[-1])
    page = root.find("page")
    colors = figure_house._Colors(root)
    labels = {g["id"]: (str(g["label"]) if g.get("label") else None) for g in grounded}
    drawn = figure_house._species_fragments(root, str(cdxml), grounded)
    label_els = [figure_house._label_of(page, el, labels.get(sp_id)) for sp_id, el, _ in drawn]
    label_els = [t for t in label_els if t is not None]
    house_face = house.convention("compound_label_face") if house is not None else None
    face = house_face if house_face in ("bold", "plain") else face_override
    changed = False
    if face in ("bold", "plain") and label_els:
        for t in label_els:
            for s in t.iter("s"):
                s.set("face", "1" if face == "bold" else "0")
        changed = True
        if house_face in ("bold", "plain"):
            applied.append(f"compound_label_face={house_face}")
    label_color = house.convention("compound_label_color") if house is not None else None
    if label_color and label_color.upper() != "#000000" and label_els:
        index = colors.index(label_color)
        for t in label_els:
            figure_house._paint(t, index)
        applied.append("compound_label_color")
        changed = True
    if house is not None and house.convention("compound_label_italic_suffix"):
        skipped.append("compound_label_italic_suffix: not applied yet; labels keep one face")
    if not changed:
        return cdxml, applied, skipped
    return figure_house._wrap(root, cdxml), applied, skipped


def _apply_abbrev_label_size(cdxml: Any) -> Any:
    """Keep contracted group labels at the styled document's atom-label size."""
    root = ET.fromstring(str(cdxml).split("?>", 1)[-1])
    size = root.get("LabelSize")
    if not size:
        return cdxml
    changed = False
    for node in root.iter("n"):
        if node.get("NodeType") == "Fragment":
            for t in node.findall("t"):
                for s in t.iter("s"):
                    if s.get("size") != size:
                        s.set("size", size)
                        changed = True
    return figure_house._wrap(root, cdxml) if changed else cdxml


def _layout_fragments(
    brief: dict, grounded: list[dict], layout_width: float, scale: float, gap_scale: float
) -> tuple[list[tuple[Any, float]], float | None]:
    """Pack structures left-to-right into rows; returns ([(frag, label_y)], title_y)."""
    by_id = {str(sp["id"]): sp for sp in brief["species"] if isinstance(sp, Mapping) and sp.get("id")}
    columns = brief.get("columns")
    h_gap = max(ACS_BOND_LENGTH * 2.5, 36.0) * gap_scale
    acs_limit = X0 + (layout_width / scale)

    resolved: list[tuple[Any, dict]] = []
    for item in grounded:
        sp = by_id[item["id"]]
        label = str(item["label"]) if item.get("label") not in (None, "") else None
        frag = renderer._resolve_structure(
            StructureRef(
                id=item["id"],
                smiles=item["smiles"],
                label=label,
                orientation=sp.get("orientation"),
            )
        )
        resolved.append((frag, sp))

    rows: list[list[tuple[Any, dict]]] = []
    current: list[tuple[Any, dict]] = []
    cursor = X0
    for frag, sp in resolved:
        width = renderer._bbox_width(frag.bbox)
        wrap_col = columns is not None and len(current) >= columns
        wrap_width = cursor + width > acs_limit
        if current and (wrap_col or wrap_width):
            rows.append(current)
            current = []
            cursor = X0
        current.append((frag, sp))
        cursor += width + h_gap
    if current:
        rows.append(current)

    placed: list[tuple[Any, float]] = []
    y_cursor = FIRST_ROW_TOP + (TITLE_ROOM if brief.get("title") or brief.get("panel_label") else 0.0)
    for row in rows:
        x_cursor = X0
        row_half_h = max(renderer._bbox_height(frag.bbox) / 2.0 for frag, _ in row)
        row_cy = y_cursor + row_half_h
        for frag, _ in row:
            width = renderer._bbox_width(frag.bbox)
            dx = (x_cursor + width / 2.0) - frag.cx
            dy = row_cy - frag.cy
            renderer._shift_atoms(frag.atoms, dx, dy)
            frag.bbox = renderer._fragment_bbox(frag.atoms)
            frag.cx, frag.cy = renderer._bbox_center(frag.bbox)
            x_cursor += width + h_gap
        row_bottom = max(frag.bbox[3] for frag, _ in row)
        row_top = min(frag.bbox[1] for frag, _ in row)
        label_y = row_bottom + 14.0
        for frag, _ in row:
            placed.append((frag, label_y))
        extra_y = 0.0
        if any(frag.ref.label for frag, _ in row):
            extra_y += 18.0
        if any(sp.get("caption") not in (None, "", []) for _, sp in row):
            extra_y += 16.0
        if any(sp.get("box") for _, sp in row):
            extra_y += 12.0
        y_cursor = row_top + (row_bottom - row_top) + extra_y + 28.0 * gap_scale

    title_y = FIRST_ROW_TOP - 4.0 if (brief.get("title") or brief.get("panel_label")) else None
    return placed, title_y


def _panel_convention_report(
    brief: Mapping, house: HouseStyle, pre_applied: list[str]
) -> list[str]:
    """Report unapplied ``structure_panel`` house-style conventions without false warnings."""
    section = (house.figure_types or {}).get("structure_panel") or {}
    if not section:
        if brief.get("kind") == "structure_panel":
            return [f"{house.slug} describes no structure_panel figures; only its base preset was applied"]
        return []
    conventions = {k: v for k, v in (section.get("conventions") or {}).items() if v is not None}
    done = {
        entry.split("=", 1)[0].split(".", 1)[1]
        for entry in pre_applied
        if entry.startswith("structure_panel.")
    }
    tool_keys = set(APPLIED_FIGURE_CONVENTIONS.get("structure_panel", ()))
    skipped = [
        f"structure_panel.{key}={value}: guidance for finishing the figure, not drawn by the tool"
        for key, value in conventions.items()
        if key not in done and key not in tool_keys
    ]
    skipped += [
        f"structure_panel.{key}: nothing to apply it to in this drawing"
        for key in conventions
        if key in tool_keys and key not in done
    ]
    return skipped


def _draw_once(
    brief: dict,
    grounded: list[dict],
    layout_width: float,
    gap_scale: float,
    budget: float,
    *,
    face_override: str | None = None,
    pre_applied: list[str] | None = None,
) -> tuple[Any, list[dict], dict]:
    from . import figure_draw

    slug, scale = figure_draw.brief_style(brief)
    house = figure_draw.brief_house(brief)
    placed, _ = _layout_fragments(brief, grounded, layout_width, scale, gap_scale)

    def build(ids) -> str:
        parts: list[str] = []
        for frag, label_y in placed:
            xml, _, _ = renderer._build_fragment(frag.atoms, frag.bonds, ids)
            parts.append(xml)
            if frag.ref.label:
                label_xml, _ = renderer._build_label_element(frag.ref.label, frag.cx, label_y, ids)
                parts.append(label_xml)
        return "\n".join(parts)

    cdxml = renderer.render_with(build)
    cdxml = figure_draw._apply_decorations(cdxml, brief, grounded)
    record: dict[str, list[str]] = {"applied": list(pre_applied or ()), "skipped": [], "warnings": []}
    if house is not None or face_override is not None:
        cdxml, applied, skipped = _apply_panel_house_labels(cdxml, grounded, house, face_override=face_override)
        record["applied"] += applied
        record["skipped"] += skipped
    cdxml, applied, warnings = figure_house.apply_species_styling(cdxml, brief, grounded, house)
    record["applied"] += applied
    record["warnings"] += warnings
    cdxml, applied, warnings = figure_house.apply_captions_and_title(cdxml, brief, grounded)
    record["applied"] += applied
    record["warnings"] += warnings
    issues = figure_lint.lint_cdxml(cdxml, max_width=budget / scale)
    # Frames go on after the overlap check: a frame is meant to surround its structure.
    cdxml, applied = figure_house.apply_species_boxes(cdxml, brief, grounded)
    record["applied"] += applied
    cdxml = figure_draw.styled(cdxml, slug)
    cdxml = _apply_abbrev_label_size(cdxml)
    if house is not None:
        cdxml, applied, _ = figure_house.apply_measured_geometry(cdxml, house, slug)
        record["applied"] += [a for a in applied if not a.startswith("measured.arrow_length")]
        record["skipped"] += _panel_convention_report(brief, house, list(pre_applied or ()))
    return cdxml, issues, record


def draw_molecule_figure(brief: dict, output_path: str | None, render: bool) -> dict:
    """Draw one molecule or a grid of structures; called by draw_figure for ``kind: molecule``."""
    from . import figure_draw

    brief = _assign_default_ids(copy.deepcopy(brief))
    errors = _validate(brief)
    if errors:
        return figure_draw._failure(errors)

    grounded, errors = figure_draw._ground(brief["species"])
    if errors:
        return figure_draw._failure(errors)

    max_width = float(brief.get("max_width") or figure_draw.DEFAULT_MAX_WIDTH)
    gap_scale = 1.0
    try:
        house = figure_draw.brief_house(brief)
        face_override, numbering_tag = _resolve_numbering(brief, grounded, house)
        properties_tag = _populate_properties(brief, grounded)
        highlight = _apply_panel_highlights(brief, grounded, house)
        variation = _apply_panel_variation_color(brief, grounded, house)
        pre_applied = [t for t in (numbering_tag, properties_tag, highlight, variation) if t]
        cdxml, issues, house_record = _draw_once(
            brief, grounded, max_width, gap_scale, max_width,
            face_override=face_override, pre_applied=pre_applied,
        )
        relayout = None
        if issues:
            first_issues = issues
            new_width, new_gap, changed, _ = figure_draw._relayout(issues, max_width, gap_scale)
            if changed:
                cdxml, issues, house_record = _draw_once(
                    brief, grounded, new_width, new_gap, max_width,
                    face_override=face_override, pre_applied=pre_applied,
                )
                relayout = {"changed": changed, "first_issues": first_issues}
    except Exception as exc:
        return figure_draw._failure([f"The layout failed: {exc}"])

    try:
        target = artifact_safety.resolve_destination(
            source=None, output_path=output_path, tag="figure", suffix=".cdxml"
        )
        with artifact_safety.staging_file(target) as stage:
            stage.write_text(str(cdxml), encoding="utf-8", newline="")
            artifact_safety.publish_file(stage, target)
    except ValueError as exc:
        return figure_draw._failure([str(exc)], warnings=house_record["warnings"])

    warnings = list(house_record["warnings"])
    for issue in issues:
        warnings.append(f"Layout check: {issue['message']}")

    used = {g["id"] for g in grounded}
    readback = figure_draw._readback(target, grounded, used, getattr(cdxml, "chemistry_validation", None))
    if readback["status"] != "matched":
        warnings.append(
            f"The saved file does not match the brief: missing {readback['missing']}, "
            f"{readback['unexpected']} unexpected structure(s)."
        )
    if readback["fragment_roundtrip"] != "preserved":
        warnings.append(
            f"Per-structure round-trip is {readback['fragment_roundtrip']}: "
            "a structure may have changed while drawing."
        )

    notes: list[str] = []
    produced = [target]
    native: dict[str, Any]
    if not render:
        native = {"status": "not_run", "reason": "native rendering was not requested"}
        notes.append("The drawing has not been rendered natively; look at a render before treating it as final.")
    else:
        png = figure_draw._png_destination(target)
        try:
            figure_draw._render_png(str(target), str(png))
            native = {"status": "rendered", "png_path": str(png)}
            produced.append(png)
        except Exception as exc:
            native = {"status": "not_run", "reason": str(exc)}
            notes.append("Native rendering did not run, so the drawing is an unrendered draft.")

    slug = figure_draw.brief_style(brief)[0]
    report = {
        "ok": True,
        "operation": "draw_figure",
        "kind": "molecule",
        "output_path": str(target),
        "layout": "molecule" if len(grounded) == 1 else "grid",
        "species": [{k: g[k] for k in ("id", "label", "name", "smiles", "source")} for g in grounded],
        "steps": [],
        "style": figure_draw.style_report(slug, house, house_record["applied"], house_record["skipped"]),
        "lint": {"issues": issues, "relayout": relayout, "max_width": max_width},
        "readback": readback,
        "native": native,
        "checks_passed": (
            not issues
            and readback["status"] == "matched"
            and readback["fragment_roundtrip"] == "preserved"
        ),
        "notes": notes,
        "warnings": warnings,
    }
    return artifact_safety.with_artifacts(report, produced)
