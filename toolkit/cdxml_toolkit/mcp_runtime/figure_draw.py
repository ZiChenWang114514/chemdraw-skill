"""One call from a drawing brief to a checked reaction scheme.

The caller (an agent) turns a request into a brief: the species, the steps and
the conditions the user gave. This module does everything else without a
language model: grounds each structure, checks atom balance, lays the scheme
out, measures the result, re-lays it out once if a check fails, reads the file
back and says what was and was not verified. Nothing is invented: a condition
the brief does not contain is not drawn, and an unresolved name stops the run.
"""
from __future__ import annotations

import copy
import json
from collections import Counter
from pathlib import Path
from typing import Any

from rdkit import Chem

from ..chemistry_semantics import document_inventory, semantic_key
from ..render import renderer
from ..render.schema import ArrowContent, SchemeDescriptor, StepDescriptor, StructureRef
from ..resolve.network_policy import network_allowed
from . import artifact_safety, figure_lint, official_overrides
from .report_tools import check_reaction_balance

DEFAULT_MAX_WIDTH = 504.0  # a double-column ACS page, 7 in
RELAYOUT_GAP_SCALE = 1.4
RELAYOUT_WIDTH_FACTOR = 0.75
ARROWS = ("solid", "dashed", "failed")
BRIEF_KEYS = {"kind", "species", "steps", "max_width", "title", "style"}


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
        errors.append(f"kind {kind!r} is not available yet; only 'scheme' can be drawn.")
    if brief.get("style", "acs1996") != "acs1996":
        errors.append("style: only 'acs1996' is available.")
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


def _scheme(brief: dict, grounded: list[dict], max_width: float | None, gap_scale: float) -> SchemeDescriptor:
    structures = {
        g["id"]: StructureRef(id=g["id"], smiles=g["smiles"], label=(str(g["label"]) if g["label"] else None))
        for g in grounded
    }
    steps = []
    for step in brief["steps"]:
        above, below = [str(t) for t in _as_list(step.get("above"))], [str(t) for t in _as_list(step.get("below"))]
        steps.append(StepDescriptor(
            substrates=[str(i) for i in _as_list(step["substrates"])],
            products=[str(i) for i in _as_list(step["products"])],
            above_arrow=ArrowContent(text=above) if above else None,
            below_arrow=ArrowContent(text=below) if below else None,
            yield_=(str(step["yield"]) if step.get("yield") not in (None, "") else None),
            arrow_style=step.get("arrow", "solid"),
        ))
    return SchemeDescriptor(
        structures=structures, steps=steps,
        layout="sequential" if len(steps) > 1 else "linear",
        max_row_width=max_width, gap_scale=gap_scale, title=brief.get("title"),
    )


def _draw(brief: dict, grounded: list[dict], layout_width: float, gap_scale: float, budget: float):
    """Lay out with ``layout_width`` but always measure against the requested ``budget``."""
    cdxml = renderer.render(_scheme(brief, grounded, layout_width, gap_scale))
    return cdxml, figure_lint.lint_cdxml(cdxml, max_width=budget)


def _relayout(issues: list[dict], max_width: float, gap_scale: float) -> tuple[float, float, list[str]]:
    changed: list[str] = []
    kinds = {issue["kind"] for issue in issues}
    if "too_wide" in kinds:
        max_width = round(max_width * RELAYOUT_WIDTH_FACTOR, 1)
        changed.append(f"narrowed the row width budget to {max_width:g} pt so rows wrap sooner")
    if "overlap" in kinds:
        gap_scale = round(gap_scale * RELAYOUT_GAP_SCALE, 2)
        changed.append(f"widened the gaps between structures and arrows by x{RELAYOUT_GAP_SCALE:g}")
    return max_width, gap_scale, changed


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
    species [{id, smiles or name, label?}], steps [{substrates [ids], products [ids],
    above [lines], below [lines], yield, arrow solid|dashed|failed}], optional max_width
    (points, default 504, the width of a double-column ACS page) and title; kind defaults
    to "scheme" and style to "acs1996". Only the conditions in the brief are drawn; a
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
    """
    brief, errors = _read_brief(brief)
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
            new_width, new_gap, changed = _relayout(issues, max_width, gap_scale)
            if changed:
                cdxml, issues = _draw(brief, grounded, new_width, new_gap, max_width)
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
        "species": [{k: g[k] for k in ("id", "label", "name", "smiles", "source")} for g in grounded],
        "steps": balance,
        "lint": {"issues": issues, "relayout": relayout, "max_width": max_width},
        "readback": readback,
        "native": native,
        "checks_passed": (not issues and readback["status"] == "matched"
                          and readback["fragment_roundtrip"] == "preserved"),
        "notes": notes,
        "warnings": warnings,
    }
    return artifact_safety.with_artifacts(report, produced)
