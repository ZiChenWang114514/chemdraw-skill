"""One call from a drawing brief to a checked reaction scheme.

The caller (an agent) turns a request into a brief: the species, the steps and
the conditions the user gave. This module does everything else without a
language model: grounds each structure, checks atom balance, lays the scheme
out, measures the result, re-lays it out once if a check fails, reads the file
back and says what was and was not verified. Nothing is invented: a condition
the brief does not contain is not drawn, and an unresolved name stops the run.
"""
from __future__ import annotations

import math

import copy
import json
from collections import Counter
from collections.abc import Mapping
from pathlib import Path
from typing import Any
import xml.etree.ElementTree as ET

from rdkit import Chem

from ..chemistry_semantics import document_inventory, read_fragments, semantic_key
from ..render import renderer
from ..render.route_graph import classify_route
from ..render.schema import ArrowContent, SchemeDescriptor, StepDescriptor, StructureRef
from ..resolve.network_policy import network_allowed
from . import artifact_safety, figure_lint, official_overrides
from .report_tools import check_reaction_balance
from ..chemdraw.style_presets import (
    DEFAULT_STYLE_PRESET, STYLE_PRESETS, apply_style_preset, style_preset_bond_length, style_preset_slug,
)

DEFAULT_MAX_WIDTH = 504.0  # a double-column ACS page, 7 in
RELAYOUT_GAP_SCALE = 1.4
RELAYOUT_WIDTH_FACTOR = 0.75
RELAYOUT_MIN_LINE_CHARS = 16
ARROWS = ("solid", "dashed", "failed", "reversible", "resonance")
BRIEF_KEYS = {"kind", "species", "steps", "max_width", "title", "style", "layout"}

JACS_PALETTE = {
    "pastel_blue": "#D6EAF8",
    "pastel_red": "#FADBD8",
    "pastel_green": "#D5F5E3",
    "pastel_yellow": "#FCF3CF",
    "pastel_purple": "#E8DAEF",
    "pastel_orange": "#FDEBD0",
    "pastel_teal": "#D1F2EB",
    "jacs_blue": "#005AB5",
    "jacs_red": "#DC3220",
    "jacs_green": "#008060",
    "jacs_purple": "#6A3D9A",
}


def _as_list(value: Any) -> list:
    if value is None:
        return []
    return list(value) if isinstance(value, (list, tuple)) else [value]


def _read_brief(brief: Any) -> tuple[dict | None, list[str]]:
    if isinstance(brief, str):
        try:
            brief = json.loads(brief)
        except ValueError as exc:
            return None, [f"The brief is not valid JSON: {exc}"]
    if not isinstance(brief, dict):
        return None, ["The brief must be an object with species and steps."]
    return copy.deepcopy(brief), []


def _validate(brief: dict) -> list[str]:
    errors: list[str] = []
    unknown = sorted(set(brief) - BRIEF_KEYS)
    if unknown:
        errors.append(f"Unknown brief keys: {unknown}")
    kind = brief.get("kind", "scheme")
    if kind != "scheme":
        errors.append(f"kind {kind!r} is not available yet; only 'scheme', 'scope' and 'mechanism' can be drawn.")
    style_error = style_preset_error(brief.get("style"))
    if style_error:
        errors.append(style_error)
    width = brief.get("max_width")
    if width is not None and not (isinstance(width, (int, float)) and width > 0):
        errors.append("max_width must be a positive number of points.")

    species = brief.get("species")
    ids: set[str] = set()
    if not isinstance(species, list) or not species:
        errors.append("species: list every structure that is drawn, each with an id and a smiles or a name.")
        species = []
    for entry in species:
        if not isinstance(entry, dict) or not str(entry.get("id") or "").strip():
            errors.append("Every species needs an id.")
            continue
        ident = str(entry["id"])
        if ident in ids:
            errors.append(f"Species {ident}: duplicate id.")
        ids.add(ident)
        if not entry.get("smiles") and not entry.get("name"):
            errors.append(f"Species {ident} needs a smiles or a name.")

    steps = brief.get("steps")
    if not isinstance(steps, list) or not steps:
        errors.append("steps: give at least one step with substrates and products.")
        steps = []
    for number, step in enumerate(steps, 1):
        if not isinstance(step, dict):
            errors.append(f"Step {number} must be an object.")
            continue
        for side in ("substrates", "products"):
            members = _as_list(step.get(side))
            if not members:
                errors.append(f"Step {number} needs {side}.")
            for member in members:
                if member not in ids:
                    errors.append(f"Step {number} names {member!r} in {side}, which is not in species.")
        if step.get("arrow", "solid") not in ARROWS:
            errors.append(f"Step {number}: arrow must be one of {list(ARROWS)}.")
    if steps and not errors:
        try:
            _route_layout(_step_descriptors(brief), brief.get("layout"))
        except ValueError as exc:
            errors.append(str(exc))
    return errors


def _ground(species: list[dict]) -> tuple[list[dict], list[str]]:
    """Attach a checked SMILES and its provenance to every species."""
    from ..naming.mol_builder import resolve_compound

    grounded: list[dict] = []
    errors: list[str] = []
    for entry in species:
        ident = str(entry["id"])
        record = {"id": ident, "label": entry.get("label"), "name": entry.get("name")}
        smiles = entry.get("smiles")
        if smiles:
            source = "user"
        else:
            found = resolve_compound(str(entry["name"]), use_network=network_allowed())
            if not found.get("ok") or not found.get("smiles"):
                errors.append(
                    f"Species {ident}: could not resolve the name {entry['name']!r} "
                    f"({found.get('error', 'no match')}). Give a SMILES instead."
                )
                continue
            smiles, source = found["smiles"], str(found.get("source") or "resolved")
        if Chem.MolFromSmiles(smiles) is None:
            errors.append(f"Species {ident}: {smiles!r} is not a valid SMILES.")
            continue
        grounded.append({**record, "smiles": smiles, "source": source})
    return grounded, errors


def _check_balance(brief: dict, smiles: dict[str, str]) -> tuple[list[dict], list[str]]:
    reports: list[dict] = []
    warnings: list[str] = []
    for number, step in enumerate(brief["steps"], 1):
        reaction = {
            "reactants": [{"smiles": smiles[i], "label": i} for i in _as_list(step["substrates"])],
            "agents": [],
            "products": [{"smiles": smiles[i], "label": i} for i in _as_list(step["products"])],
        }
        try:
            result = check_reaction_balance(reaction)["reactions"][0]
        except Exception as exc:  # generic atoms, unsupported isotopes, ...
            reports.append({"step": number, "balanced": None, "missing": None, "error": str(exc)})
            warnings.append(f"Step {number}: the balance could not be checked ({exc}).")
            continue
        missing = None
        for key in ("missing_from_products", "missing_from_reactants"):
            if result.get(key):
                missing = {"side": key.rsplit("_", 1)[-1], "formula": result[key]["formula"],
                           "name": result[key].get("common_name")}
        reports.append({"step": number, "balanced": bool(result["balanced"]), "missing": missing})
        if not result["balanced"]:
            what = ""
            if missing:
                name = f" ({missing['name']})" if missing["name"] else ""
                what = f": the {missing['side']} lack {missing['formula']}{name}"
            warnings.append(
                f"Step {number} does not balance as drawn{what}. Check the structures against "
                "the source before treating it as a by-product; nothing was added to the drawing."
            )
    return reports, warnings


def _scheme(brief: dict, grounded: list[dict], max_width: float | None, gap_scale: float,
            line_chars: int | None = None) -> SchemeDescriptor:
    structures = {
        g["id"]: StructureRef(id=g["id"], smiles=g["smiles"], label=(str(g["label"]) if g["label"] else None))
        for g in grounded
    }
    steps = _step_descriptors(brief, line_chars)
    layout, order = _route_layout(steps, brief.get("layout"))
    return SchemeDescriptor(
        structures=structures, steps=[steps[i] for i in order], layout=layout,
        max_row_width=max_width, gap_scale=gap_scale, title=brief.get("title"),
    )


def _broken_lines(lines: list[str], line_chars: int | None) -> list[str]:
    """Break each condition line longer than ``line_chars`` after its commas; the text is unchanged."""
    if not line_chars:
        return lines
    out: list[str] = []
    for line in lines:
        current = ""
        for part in line.split(", "):
            candidate = f"{current}, {part}" if current else part
            if current and len(candidate) > line_chars:
                out.append(current + ",")
                current = part
            else:
                current = candidate
        out.append(current)
    return out


def _longest_line(brief: dict) -> int:
    return max((len(str(t)) for step in brief["steps"] for side in ("above", "below")
                for t in _as_list(step.get(side))), default=0)


def _step_descriptors(brief: dict, line_chars: int | None = None) -> list[StepDescriptor]:
    steps = []
    for number, step in enumerate(brief["steps"], 1):
        above = _broken_lines([str(t) for t in _as_list(step.get("above"))], line_chars)
        below = _broken_lines([str(t) for t in _as_list(step.get("below"))], line_chars)
        steps.append(StepDescriptor(
            substrates=[str(i) for i in _as_list(step["substrates"])],
            products=[str(i) for i in _as_list(step["products"])],
            above_arrow=ArrowContent(text=above) if above else None,
            below_arrow=ArrowContent(text=below) if below else None,
            yield_=(str(step["yield"]) if step.get("yield") not in (None, "") else None),
            arrow_style=step.get("arrow", "solid"),
            id=str(number),
        ))
    return steps


def _route_layout(steps: list[StepDescriptor], requested_layout: str | None = None) -> tuple[str, list[int]]:
    """Renderer layout name and the order to draw the steps in; ValueError if the route fits none."""
    if requested_layout in ("catalytic-cycle", "cycle"):
        from ..render.route_graph import cycle_order

        return "catalytic-cycle", cycle_order(steps)
    kind, order = classify_route(steps)
    if kind == "linear":
        return ("sequential" if len(steps) > 1 else "linear"), order
    return kind, order


def _fmt_rgb(c: int) -> str:
    if c <= 0:
        return "0"
    if c >= 255:
        return "1"
    return f"{c / 255.0:.4f}".rstrip("0").rstrip(".")


def _curve_points(ring_pts: list[tuple[float, float]], style: str = "polygon", inset: float = 0.0) -> str:
    n = len(ring_pts)
    rcx = sum(p[0] for p in ring_pts) / n
    rcy = sum(p[1] for p in ring_pts) / n
    adjusted: list[tuple[float, float]] = []
    for px, py in ring_pts:
        dx, dy = rcx - px, rcy - py
        dist = math.hypot(dx, dy)
        if inset and dist > 1e-6:
            step = min(float(inset), dist * 0.45)
            px += (dx / dist) * step
            py += (dy / dist) * step
        adjusted.append((px, py))

    if style == "spline" and n >= 3:
        ctrl: list[tuple[float, float]] = []
        for i in range(n):
            p_prev = adjusted[(i - 1) % n]
            p_curr = adjusted[i]
            p_next = adjusted[(i + 1) % n]
            tx = (p_next[0] - p_prev[0]) * 0.16
            ty = (p_next[1] - p_prev[1]) * 0.16
            ctrl.extend([(p_curr[0] - tx, p_curr[1] - ty), p_curr, (p_curr[0] + tx, p_curr[1] + ty)])
        return " ".join(f"{x:.2f} {y:.2f}" for x, y in ctrl)

    poly = [q for p in adjusted for q in (p, p, p)]
    return " ".join(f"{x:.2f} {y:.2f}" for x, y in poly)


def _species_atom_points(frag_mol: Any, src_mol: Any, top_pts: list[tuple[float, float]],
                         sp_id: str) -> list[tuple[float, float]]:
    """Drawn position of each species SMILES atom, by substructure match to the drawn fragment.

    RDKit's CDXML reader keeps node coordinates (scaled by 65536, y flipped); atoms inside
    an abbreviation snap to the visible abbreviation node.
    """
    if src_mol is None or frag_mol is None or not frag_mol.GetNumConformers():
        raise ValueError(f"species {sp_id!r}: cannot map decoration atoms onto the drawn structure")
    match = frag_mol.GetSubstructMatch(src_mol)
    if len(match) != src_mol.GetNumAtoms():
        raise ValueError(
            f"species {sp_id!r}: drawn fragment does not match its SMILES, so ring_fills/atom_halos "
            "atom indices cannot be placed"
        )
    conf = frag_mol.GetConformer()
    pts: list[tuple[float, float]] = []
    for frag_idx in match:
        pos = conf.GetAtomPosition(frag_idx)
        x, y = pos.x / 65536.0, -pos.y / 65536.0
        pts.append(min(top_pts, key=lambda q: (q[0] - x) ** 2 + (q[1] - y) ** 2))
    return pts


def _apply_decorations(cdxml: str, brief: dict, grounded: list[dict]) -> str:
    """Inject ring_fills, atom_halos, and ts_bracket decorations around species fragments."""
    raw_species = {str(s["id"]): s for s in brief.get("species", []) if isinstance(s, Mapping) and s.get("id")}
    step_ts_ids: set[str] = set()
    for step in brief.get("steps", []):
        if not isinstance(step, Mapping):
            continue
        ts_val = step.get("ts_bracket")
        if ts_val is None or ts_val is False:
            continue
        if isinstance(ts_val, bool):
            raise ValueError(
                'steps[].ts_bracket must name the transition-state species id '
                '(ts_bracket: "<species id>"), not true; or set ts_bracket on that species'
            )
        if isinstance(ts_val, str):
            step_ts_ids.add(ts_val)
        elif isinstance(ts_val, (list, tuple)):
            for sid in ts_val:
                step_ts_ids.add(str(sid))

    has_any = bool(step_ts_ids) or any(
        sp.get("ring_fills") or sp.get("atom_halos") or sp.get("ts_bracket")
        for sp in raw_species.values()
    )
    if not has_any:
        return cdxml

    smiles_by_id = {g["id"]: g["smiles"] for g in grounded}
    key_to_ids: dict[str, list[str]] = {}
    for g in grounded:
        mol = Chem.MolFromSmiles(g["smiles"])
        if mol is not None:
            key_to_ids.setdefault(semantic_key(mol), []).append(g["id"])

    root = ET.fromstring(str(cdxml))
    page = root.find("page")
    if page is None:
        return cdxml

    frag_elem_by_id = {f.get("id", ""): f for f in page.findall("fragment")}
    try:
        parsed_frags = read_fragments(str(cdxml))
    except Exception:
        return cdxml

    colortable = root.find("colortable")
    base_colors = len(colortable) if colortable is not None else 8
    added_colors: list[str] = []
    color_cache: dict[tuple[int, int, int], str] = {}

    def resolve_color(c_spec: Any) -> str:
        text = str(c_spec or "pastel_blue").strip()
        if text.isdigit():
            return text
        lower = text.lower()
        if lower in JACS_PALETTE:
            text = JACS_PALETTE[lower]
        if text.startswith("#"):
            text = text[1:]
        if len(text) == 3:
            text = "".join(ch * 2 for ch in text)
        if len(text) != 6:
            return "4"
        rgb = (int(text[0:2], 16), int(text[2:4], 16), int(text[4:6], 16))
        if rgb in color_cache:
            return color_cache[rgb]
        idx = str(base_colors + 2 + len(added_colors))
        added_colors.append(
            f'<color r="{_fmt_rgb(rgb[0])}" g="{_fmt_rgb(rgb[1])}" b="{_fmt_rgb(rgb[2])}"/>'
        )
        color_cache[rgb] = idx
        return idx

    used_ids = [int(v) for el in root.iter() for v in [el.get("id")] if v and v.isdigit()]
    next_id = max(used_ids, default=0)
    key_seen: dict[str, int] = {}
    bg_xml: list[str] = []
    fg_xml: list[str] = []

    for frag_id_str, frag_mol in parsed_frags:
        frag_el = frag_elem_by_id.get(str(frag_id_str))
        if frag_el is None:
            continue
        f_key = semantic_key(frag_mol)
        cand_ids = key_to_ids.get(f_key, [])
        if not cand_ids:
            continue
        # Species sharing a structure are consumed in document order, one fragment each.
        seen = key_seen.get(f_key, 0)
        key_seen[f_key] = seen + 1
        sp_id = cand_ids[min(seen, len(cand_ids) - 1)]
        sp_cfg = raw_species.get(sp_id, {})
        src_mol = Chem.MolFromSmiles(smiles_by_id.get(sp_id, ""))

        node_ids: list[str] = []
        top_pts: list[tuple[float, float]] = []
        for n_el in frag_el.findall("n"):
            if n_el.get("NodeType") == "ExternalConnectionPoint":
                continue
            parts = (n_el.get("p") or "").split()
            if len(parts) >= 2:
                top_pts.append((float(parts[0]), float(parts[1])))
                node_ids.append(n_el.get("id", ""))

        if not top_pts:
            continue

        needs_atoms = bool(sp_cfg.get("ring_fills") or sp_cfg.get("atom_halos"))
        node_pts: list[tuple[float, float]] = []
        if needs_atoms:
            node_pts = _species_atom_points(frag_mol, src_mol, top_pts, sp_id)

        # 1. Ring fills
        ring_fills = sp_cfg.get("ring_fills") or []
        if ring_fills and src_mol is not None:
            atom_rings = list(src_mol.GetRingInfo().AtomRings())
            for rf in ring_fills:
                if not isinstance(rf, Mapping):
                    continue
                if "atoms" in rf:
                    r_atoms = [int(x) for x in rf["atoms"]]
                else:
                    r_idx = int(rf.get("ring_index", 0))
                    if 0 <= r_idx < len(atom_rings):
                        r_atoms = list(atom_rings[r_idx])
                    else:
                        continue
                r_pts = [node_pts[i] for i in r_atoms if 0 <= i < len(node_pts)]
                if len(r_pts) < 3:
                    continue
                c_idx = resolve_color(rf.get("color", "pastel_blue"))
                style = str(rf.get("style", "polygon")).lower()
                inset = float(rf.get("inset", 0.0))
                c_pts = _curve_points(r_pts, style=style, inset=inset)
                rx1, ry1 = min(p[0] for p in r_pts), min(p[1] for p in r_pts)
                rx2, ry2 = max(p[0] for p in r_pts), max(p[1] for p in r_pts)
                next_id += 1
                bg_xml.append(
                    f'<curve id="{next_id}" Closed="yes" FillType="Solid" LineType="None" '
                    f'color="{c_idx}" Z="1" BoundingBox="{rx1:.2f} {ry1:.2f} {rx2:.2f} {ry2:.2f}" '
                    f'CurvePoints="{c_pts}"/>'
                )

        # 2. Atom halos
        atom_halos = sp_cfg.get("atom_halos") or []
        for halo in atom_halos:
            if not isinstance(halo, Mapping):
                continue
            h_atoms = halo.get("atoms")
            if h_atoms is None and "atom" in halo:
                h_atoms = [halo["atom"]]
            if not h_atoms:
                continue
            r = float(halo.get("radius", 8.0))
            c_idx = resolve_color(halo.get("color", "pastel_yellow"))
            for a_idx in h_atoms:
                idx_i = int(a_idx)
                if 0 <= idx_i < len(node_pts):
                    ax, ay = node_pts[idx_i]
                    next_id += 1
                    bg_xml.append(
                        f'<graphic id="{next_id}" GraphicType="Oval" OvalType="Circle Filled" '
                        f'color="{c_idx}" Z="1" '
                        f'BoundingBox="{ax - r:.2f} {ay - r:.2f} {ax + r:.2f} {ay + r:.2f}" '
                        f'Center3D="{ax:.2f} {ay:.2f} 0" '
                        f'MajorAxisEnd3D="{ax + r:.2f} {ay:.2f} 0" '
                        f'MinorAxisEnd3D="{ax:.2f} {ay + r:.2f} 0"/>'
                    )

        # 3. Transition-state bracket
        ts_spec = sp_cfg.get("ts_bracket") or (sp_id in step_ts_ids)
        if ts_spec:
            ts_dict = ts_spec if isinstance(ts_spec, Mapping) else {}
            superscript = str(ts_dict.get("superscript", "\u2021"))
            bracket_type = str(ts_dict.get("bracket_type", "Square"))
            lip = float(ts_dict.get("lip_size", 5.0))
            fx1, fy1 = min(p[0] for p in top_pts), min(p[1] for p in top_pts)
            fx2, fy2 = max(p[0] for p in top_pts), max(p[1] for p in top_pts)
            bx1, by1, bx2, by2 = fx1 - 5.0, fy1 - 4.0, fx2 + 5.0, fy2 + 4.0
            next_id += 1
            left_id = next_id
            next_id += 1
            right_id = next_id
            next_id += 1
            bg_id = next_id
            next_id += 1
            att1_id = next_id
            next_id += 1
            att2_id = next_id
            next_id += 1
            tid = next_id
            tx = bx2 + 2.5
            ty = by1 - 2.0
            fg_xml.append(
                f'<graphic id="{left_id}" BoundingBox="{bx1:.2f} {by1:.2f} {bx1 + lip:.2f} {by2:.2f}" '
                f'GraphicType="Bracket" BracketType="{bracket_type}" LipSize="{lip:g}"/>'
            )
            fg_xml.append(
                f'<graphic id="{right_id}" BoundingBox="{bx2:.2f} {by1:.2f} {bx2 - lip:.2f} {by2:.2f}" '
                f'GraphicType="Bracket" BracketType="{bracket_type}" LipSize="{lip:g}"/>'
            )
            fg_xml.append(
                f'<bracketedgroup id="{bg_id}" BracketedObjectIDs="{' '.join(node_ids)}" BracketType="{bracket_type}">'
                f'<bracketattachment id="{att1_id}" GraphicID="{left_id}"/>'
                f'<bracketattachment id="{att2_id}" GraphicID="{right_id}"/>'
                f'</bracketedgroup>'
            )
            fg_xml.append(
                f'<t id="{tid}" p="{tx:.2f} {ty:.2f}" '
                f'BoundingBox="{tx:.2f} {ty - 7.5:.2f} {tx + 5.5:.2f} {ty + 1.0:.2f}" '
                f'InterpretChemically="no">'
                f'<s font="3" size="10" color="0" face="0">{superscript}</s></t>'
            )

    if not bg_xml and not fg_xml:
        return cdxml

    text_out = str(cdxml)
    if added_colors and "</colortable>" in text_out:
        text_out = text_out.replace("</colortable>", "\n".join(added_colors) + "\n</colortable>", 1)
    if bg_xml:
        page_match = text_out.find("<page ")
        if page_match >= 0:
            page_end = text_out.find(">", page_match)
            if page_end >= 0:
                text_out = text_out[: page_end + 1] + "\n" + "\n".join(bg_xml) + text_out[page_end + 1 :]
    if fg_xml and "</page>" in text_out:
        text_out = text_out.replace("</page>", "\n".join(fg_xml) + "\n</page>", 1)

    wrapped = renderer._ValidatedCDXML(text_out)
    wrapped.chemistry_validation = getattr(cdxml, "chemistry_validation", None)
    return wrapped


def style_preset_error(style: Any) -> str | None:
    """Error text for a brief ``style`` that is not a built-in preset, else None."""
    if style is None:
        return None
    try:
        style_preset_slug(str(style))
    except ValueError:
        return f"style: unknown preset {style!r}; available: {', '.join(STYLE_PRESETS)}."
    return None


def brief_style(brief: dict) -> tuple[str, float]:
    """The brief's preset slug and the factor from ACS layout geometry to that preset."""
    slug = style_preset_slug(brief.get("style") or DEFAULT_STYLE_PRESET)
    return slug, style_preset_bond_length(slug) / renderer.ACS_BOND_LENGTH


def styled(cdxml: Any, slug: str) -> Any:
    """Apply a preset to a document laid out at ACS geometry; ACS documents are unchanged."""
    if slug == DEFAULT_STYLE_PRESET:
        return cdxml
    wrapped = renderer._ValidatedCDXML(apply_style_preset(str(cdxml), slug, rescale=True))
    wrapped.chemistry_validation = getattr(cdxml, "chemistry_validation", None)
    return wrapped


def style_report(slug: str) -> dict:
    return {"preset": slug, "bond_length": style_preset_bond_length(slug)}


def _draw(brief: dict, grounded: list[dict], layout_width: float, gap_scale: float, budget: float,
          line_chars: int | None = None):
    """Lay out with ``layout_width`` but always measure against the requested ``budget``.

    The layout is made at ACS geometry, so both widths are converted to ACS points
    first and the brief's style preset is applied (with rescaling) afterwards.
    """
    slug, scale = brief_style(brief)
    cdxml = renderer.render(_scheme(brief, grounded, layout_width / scale, gap_scale, line_chars))
    cdxml = _apply_decorations(cdxml, brief, grounded)
    issues = figure_lint.lint_cdxml(cdxml, max_width=budget / scale)
    return styled(cdxml, slug), issues


def _relayout(issues: list[dict], max_width: float, gap_scale: float,
              longest_line: int = 0) -> tuple[float, float, list[str], int | None]:
    changed: list[str] = []
    line_chars = None
    kinds = {issue["kind"] for issue in issues}
    if "too_wide" in kinds:
        max_width = round(max_width * RELAYOUT_WIDTH_FACTOR, 1)
        changed.append(f"narrowed the row width budget to {max_width:g} pt so rows wrap sooner")
        # A long condition line sets the arrow length; break it so the arrow shrinks too.
        over = max(i.get("width", 0) - i.get("budget", 0) for i in issues if i["kind"] == "too_wide")
        wanted = longest_line - math.ceil((over + 12.0) / renderer._CHAR_WIDTH)
        if longest_line > RELAYOUT_MIN_LINE_CHARS and wanted < longest_line:
            line_chars = max(RELAYOUT_MIN_LINE_CHARS, wanted)
            changed.append(f"broke condition lines longer than {line_chars} characters after a comma")
    if "overlap" in kinds:
        gap_scale = round(gap_scale * RELAYOUT_GAP_SCALE, 2)
        changed.append(f"widened the gaps between structures and arrows by x{RELAYOUT_GAP_SCALE:g}")
    return max_width, gap_scale, changed, line_chars


def _readback(target: Path, grounded: list[dict], used: set[str], fragments: dict) -> dict:
    wanted: dict[str, list[str]] = {}
    for item in grounded:
        if item["id"] in used:
            key = semantic_key(Chem.MolFromSmiles(item["smiles"]))
            wanted.setdefault(key, []).append(item["id"])
    found = Counter(document_inventory(target))
    missing = [i for key, ids in wanted.items() if key not in found for i in ids]
    extra = sum(1 for key in found if key not in wanted)
    return {
        "status": "matched" if not missing and not extra else "mismatch",
        "structures_drawn": sum(found.values()),
        "missing": missing,
        "unexpected": extra,
        "fragment_roundtrip": (fragments or {}).get("status", "unknown"),
    }


def _render_png(cdxml_path: str, png_path: str) -> str:
    result = official_overrides.render_to_png(cdxml_path, png_path)
    if isinstance(result, dict) and result.get("ok") is False:
        raise RuntimeError(result.get("error") or "native render failed")
    return png_path


def _png_destination(target: Path) -> Path:
    candidate, index = target.with_suffix(".png"), 2
    while candidate.exists():
        candidate = target.with_name(f"{target.stem}_{index}.png")
        index += 1
    return candidate


def _failure(errors: list[str], **extra) -> dict:
    return {"ok": False, "operation": "draw_figure", "errors": errors, **extra}


def draw_figure(brief: dict | str, output_path: str | None = None, render: bool = False) -> dict:
    """Draw a reaction scheme from a brief and check it, in one call.

    brief is an object (or its JSON text) the caller writes from the user's request:
    species [{id, smiles or name, label?, ring_fills?, atom_halos?, ts_bracket?}],
    steps [{substrates [ids], products [ids], above [lines], below [lines], yield,
    arrow solid|dashed|failed|reversible|resonance, ts_bracket? (a species id)}], optional layout
    (e.g. "catalytic-cycle"), max_width (points, default 504, the width of a double-column
    ACS page) and title; kind defaults to "scheme". style names a built-in journal preset
    from ChemDraw's stock style sheets (default "acs1996"; others include "wiley", "rsc",
    "nature"; chemdraw://style-guide/{preset} lists its settings): the scheme is laid out at
    ACS geometry and then rescaled to the preset's bond length, and max_width is the width
    of the styled figure. The steps may
    form a linear route, a convergent route (arms that merge), one starting material with
    several products (divergent), or a closed catalytic-cycle (a loop of >= 3 steps or
    layout="catalytic-cycle"), in any order; the report names the layout used, and steps
    that fit none of these are refused. Species entries may also specify optional visual
    decorations: ring_fills ([{ring_index, color, style, inset}]), atom_halos ([{atoms,
    color, radius}]), or ts_bracket (true or {superscript, bracket_type, lip_size}) to
    wrap the species fragment in a [...] transition-state bracket with a top-right double
    dagger; a step's ts_bracket names the bracketed species id (true is refused). Atom and
    ring indices are RDKit indices of the species SMILES. Only the conditions in the brief are drawn; a
    step without any is reported, never filled in. Structures given as SMILES are used
    as they are; names go through the curated reagent table and, when the network is
    allowed, PubChem; a name that cannot be resolved stops the run. Each step is checked
    for atom balance (a missing by-product is named, not drawn), the layout is measured
    for overlaps, tiny text and width, and one automatic re-layout is tried if that
    fails; the report says what changed and what still fails. The saved file is read back
    and its structures compared with the brief. render=True also renders a PNG with
    ChemDraw and returns its path; without ChemDraw the report says native: not_run. The
    file is never written over an existing one: without output_path a fresh name is made
    in the temp directory, and an existing output_path is refused.

    kind "scope" draws a substrate-scope panel instead: species [{id, smiles or name,
    label?, group?, values {field: text}}], optional fields [{key, label?, unit?}] (default:
    the keys used in values), conditions, footnotes, title, width_mm and height_mm. The
    structures are packed onto as many editable pages as needed, grouped in first-seen
    order, each label and value bound to its structure; a missing value is drawn as a
    dash and listed in the notes. output_path is then a new folder (page-001.cdxml, ...;
    PNGs in png/ with render=True) and the report lists the pages.

    kind "mechanism" draws the structures of a mechanism with the curved arrows the brief
    lists: species [{id, smiles or name, label?}] and steps [{substrates, products, above?,
    below?, arrow?, moves [{from, to, electrons?}]}] drawn in the order given. A move runs
    from {species, atom} or {species, bond [i, j]} to the same kind of end, in species that
    are substrates of the step; atoms are numbered from 0 in SMILES order (the report lists
    them) and electrons is 2 (full head, default) or 1 (half head). Nothing is inferred: a
    step without moves is refused, a two-electron arrow that starts on an atom without a lone
    pair or charge is drawn and flagged, and the arrows are checked for passing through
    another atom (one automatic re-layout). A step with one substrate and one product
    continues the same row with the intermediate drawn once; any other step starts a new
    row, with its substrates drawn again. show_atom_numbers=true prints the atom numbers on a
    draft so the moves can be checked.
    """
    brief, errors = _read_brief(brief)
    if brief is not None and brief.get("kind") == "scope":
        from .figure_scope import draw_scope

        return draw_scope(brief, output_path, render)
    if brief is not None and brief.get("kind") == "mechanism":
        from .figure_mechanism import draw_mechanism

        return draw_mechanism(brief, output_path, render)
    if brief is not None:
        errors = _validate(brief)
    if errors:
        return _failure(errors)

    grounded, errors = _ground(brief["species"])
    if errors:
        return _failure(errors)
    smiles = {g["id"]: g["smiles"] for g in grounded}

    balance, warnings = _check_balance(brief, smiles)
    notes: list[str] = []
    for number, step in enumerate(brief["steps"], 1):
        if not _as_list(step.get("above")) and not _as_list(step.get("below")):
            notes.append(f"step {number} has no conditions; none are drawn.")
    used = {i for step in brief["steps"] for side in ("substrates", "products") for i in _as_list(step[side])}
    for item in grounded:
        if item["id"] not in used:
            notes.append(f"species {item['id']} is not used in any step, so it is not drawn.")

    max_width = float(brief.get("max_width") or DEFAULT_MAX_WIDTH)
    gap_scale = 1.0
    try:
        cdxml, issues = _draw(brief, grounded, max_width, gap_scale, max_width)
        relayout = None
        if issues:
            first_issues = issues
            new_width, new_gap, changed, line_chars = _relayout(issues, max_width, gap_scale,
                                                                _longest_line(brief))
            if changed:
                cdxml, issues = _draw(brief, grounded, new_width, new_gap, max_width, line_chars)
                relayout = {"changed": changed, "first_issues": first_issues}
    except Exception as exc:
        return _failure([f"The layout failed: {exc}"], warnings=warnings)

    try:
        target = artifact_safety.resolve_destination(
            source=None, output_path=output_path, tag="figure", suffix=".cdxml")
        with artifact_safety.staging_file(target) as stage:
            stage.write_text(str(cdxml), encoding="utf-8", newline="")
            artifact_safety.publish_file(stage, target)
    except ValueError as exc:  # includes OutputExistsError
        return _failure([str(exc)], warnings=warnings)

    for issue in issues:
        warnings.append(f"Layout check: {issue['message']}")
    readback = _readback(target, grounded, used, getattr(cdxml, "chemistry_validation", None))
    if readback["status"] != "matched":
        warnings.append(f"The saved file does not match the brief: missing {readback['missing']}, "
                        f"{readback['unexpected']} unexpected structure(s).")

    if readback["fragment_roundtrip"] != "preserved":
        warnings.append(f"Per-structure round-trip is {readback['fragment_roundtrip']}: "
                        "a structure may have changed while drawing.")

    native: dict[str, Any]
    produced = [target]
    if not render:
        native = {"status": "not_run", "reason": "native rendering was not requested"}
        notes.append("The drawing has not been rendered natively; look at a render before treating it as final.")
    else:
        png = _png_destination(target)
        try:
            _render_png(str(target), str(png))
            native = {"status": "rendered", "png_path": str(png)}
            produced.append(png)
        except Exception as exc:
            native = {"status": "not_run", "reason": str(exc)}
            notes.append("Native rendering did not run, so the drawing is an unrendered draft.")

    report = {
        "ok": True,
        "operation": "draw_figure",
        "output_path": str(target),
        "layout": _route_layout(_step_descriptors(brief), brief.get("layout"))[0],
        "species": [{k: g[k] for k in ("id", "label", "name", "smiles", "source")} for g in grounded],
        "steps": balance,
        "style": style_report(brief_style(brief)[0]),
        "lint": {"issues": issues, "relayout": relayout, "max_width": max_width},
        "readback": readback,
        "native": native,
        "checks_passed": (not issues and readback["status"] == "matched"
                          and readback["fragment_roundtrip"] == "preserved"),
        "notes": notes,
        "warnings": warnings,
    }
    return artifact_safety.with_artifacts(report, produced)
