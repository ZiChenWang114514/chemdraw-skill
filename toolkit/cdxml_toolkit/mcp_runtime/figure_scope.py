"""Substrate-scope panels for draw_figure: a list of compounds with labels and values.

The brief carries the compounds and the numbers the user gave. This module
grounds each structure, writes the table the publication layout reads and lets
``publication_figure`` pack, label and check the pages. A value the brief does
not contain is drawn as a dash and named in the notes; nothing is filled in.
"""
from __future__ import annotations

import csv
import json
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any

from rdkit import Chem

from ..chemistry_semantics import document_inventory, semantic_key
from . import artifact_safety
from .figure_draw import _as_list, _failure, _ground

SCOPE_KEYS = {"kind", "species", "fields", "conditions", "footnotes", "title", "style", "width_mm", "height_mm"}
SPECIES_KEYS = {"id", "smiles", "name", "label", "group", "values"}
MAX_SPECIES = 1000


def _fields(brief: dict) -> tuple[list[dict], list[str]]:
    errors: list[str] = []
    given = brief.get("fields")
    if given is None:
        keys = list(dict.fromkeys(k for e in brief["species"] if isinstance(e, dict) for k in (e.get("values") or {})))
        return [{"key": k, "label": k, "unit": None} for k in keys], errors
    if not isinstance(given, list):
        return [], ["fields must be a list of keys or {key, label, unit} objects."]
    fields: list[dict] = []
    for item in given:
        if isinstance(item, str):
            item = {"key": item}
        if not isinstance(item, dict) or not str(item.get("key") or "").strip():
            errors.append("Every field needs a key.")
            continue
        key = str(item["key"])
        if any(f["key"] == key for f in fields):
            errors.append(f"Field {key}: duplicate key.")
            continue
        label = item.get("label", key)
        fields.append({"key": key, "label": "" if label is None else str(label), "unit": item.get("unit") or None})
    return fields, errors


def _validate(brief: dict) -> list[str]:
    errors: list[str] = []
    unknown = sorted(set(brief) - SCOPE_KEYS)
    if unknown:
        errors.append(f"Unknown brief keys: {unknown}")
    if brief.get("style", "acs1996") != "acs1996":
        errors.append("style: only 'acs1996' is available.")
    for key, low, high in (("width_mm", 60, 400), ("height_mm", 60, 500)):
        value = brief.get(key)
        if value is not None and not (isinstance(value, (int, float)) and low <= value <= high):
            errors.append(f"{key} must be a number from {low} to {high} millimetres.")
    footnotes = brief.get("footnotes")
    if footnotes is not None and not (isinstance(footnotes, list) and all(isinstance(f, str) for f in footnotes)):
        errors.append("footnotes must be a list of text lines.")
    for key in ("title", "conditions"):
        if brief.get(key) is not None and not isinstance(brief[key], str):
            errors.append(f"{key} must be text.")

    species = brief.get("species")
    if not isinstance(species, list) or not species:
        return errors + ["species: list every compound, each with an id and a smiles or a name."]
    if len(species) > MAX_SPECIES:
        errors.append(f"A scope panel holds at most {MAX_SPECIES} compounds.")
    ids: set[str] = set()
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
        if not isinstance(entry.get("values") or {}, dict):
            errors.append(f"Species {ident}: values must be an object of field -> value.")

    fields, field_errors = _fields(brief)
    errors += field_errors
    known = {f["key"] for f in fields}
    for entry in species:
        if isinstance(entry, dict) and isinstance(entry.get("values") or {}, dict):
            for key in entry.get("values") or {}:
                if key not in known:
                    errors.append(f"Species {entry.get('id')}: a value for {key!r}, which is not in fields.")
    return errors


def _free_directory() -> Path:
    base = Path(tempfile.gettempdir()) / "scope-figure"
    candidate, index = base, 2
    while candidate.exists():
        candidate = base.with_name(f"{base.name}_{index}")
        index += 1
    return candidate


def _text(value: Any) -> str:
    return "" if value is None else str(value)


def _write_inputs(work: Path, brief: dict, grounded: list[dict], fields: list[dict], render: bool) -> Path:
    columns = {f["key"]: f"v{i}" for i, f in enumerate(fields, 1)}
    with (work / "table.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["compound_id", "smiles", "label", "group", *columns.values()])
        by_id = {str(e["id"]): e for e in brief["species"]}
        for item in grounded:
            entry = by_id[item["id"]]
            values = entry.get("values") or {}
            writer.writerow([item["id"], item["smiles"], _text(entry.get("label")), _text(entry.get("group")),
                             *(_text(values.get(f["key"])) for f in fields)])
    style = {k: brief[k] for k in ("width_mm", "height_mm") if brief.get(k) is not None}
    spec = {
        "mode": "scope", "table": "table.csv", "label_column": "label", "group_column": "group",
        "fields": [{"column": columns[f["key"]], "label": f["label"], **({"unit": f["unit"]} if f["unit"] else {})}
                   for f in fields],
        "title": brief.get("title") or "Substrate scope",
        "conditions": brief.get("conditions") or "",
        "footnotes": brief.get("footnotes") or [],
        "style": style,
        "native_render": render,
    }
    path = work / "spec.json"
    path.write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
    return path


def _readback(pages: list[Path], grounded: list[dict]) -> dict:
    wanted: Counter = Counter()
    for item in grounded:
        wanted.update(semantic_key(m) for m in Chem.GetMolFrags(Chem.MolFromSmiles(item["smiles"]), asMols=True))
    found: Counter = Counter()
    for page in pages:
        found.update(document_inventory(page))
    missing = sorted((wanted - found).elements())
    extra = sorted((found - wanted).elements())
    return {
        "status": "matched" if not missing and not extra else "mismatch",
        "structures_drawn": sum(found.values()),
        "missing": len(missing),
        "unexpected": len(extra),
    }


def draw_scope(brief: dict, output_path: str | None, render: bool) -> dict:
    """Draw a scope panel; called by draw_figure for ``kind: scope``."""
    from . import publication_figure as publication

    errors = _validate(brief)
    if errors:
        return _failure(errors, kind="scope")
    grounded, errors = _ground(brief["species"])
    if errors:
        return _failure(errors, kind="scope")
    fields, _ = _fields(brief)

    target = Path(output_path).expanduser().resolve() if output_path else _free_directory()
    if target.exists():
        return _failure([f"Refusing to overwrite an existing folder: {target}"], kind="scope")

    try:
        with tempfile.TemporaryDirectory(prefix="scope-inputs-") as scratch:
            spec = _write_inputs(Path(scratch), brief, grounded, fields, render)
            result = publication.publication_figure("create", str(spec), str(target))
    except Exception as exc:
        return _failure([f"The scope panel could not be drawn: {exc}"], kind="scope")
    if not result.get("ok"):
        return _failure([f"The panel has {result.get('conflicts', 'some')} data-binding conflict(s); "
                         f"see {result.get('output_dir')}."], kind="scope")

    project = json.loads((target / "project.json").read_text(encoding="utf-8"))
    per_page = Counter(c["page"] for c in project["compounds"].values())
    pages = [{"path": str(target / p["file"]), "file": p["file"], "compounds": per_page[i]}
             for i, p in enumerate(project["pages"])]
    checks = result["checks"]
    readback = _readback([Path(p["path"]) for p in pages], grounded)

    notes: list[str] = []
    warnings: list[str] = []
    for entry in brief["species"]:
        values = entry.get("values") or {}
        blank = [f["key"] for f in fields if values.get(f["key"]) in (None, "")]
        if blank:
            notes.append(f"species {entry['id']} has no {', '.join(blank)}; shown as a dash, not as zero.")
    for item in checks["layout"]["issues"]:
        warnings.append(f"Layout check: {item}")
    for item in checks["data_binding"]["errors"]:
        warnings.append(f"Data binding: {item}")
    for item in project.get("warnings", []):
        warnings.append(f"{item.get('compound_id')}: {item.get('message')}")
    if readback["status"] != "matched":
        warnings.append(f"The saved pages do not match the brief: {readback['missing']} missing, "
                        f"{readback['unexpected']} unexpected structure(s).")

    preview = checks.get("native_preview", {})
    produced: list[Path] = [Path(p["path"]) for p in pages]
    if render and preview.get("status") == "rendered_pending_visual_review":
        pngs = sorted((target / "png").glob("*.png"))
        native: dict[str, Any] = {"status": "rendered", "png_paths": [str(p) for p in pngs]}
        produced += pngs
    else:
        reason = preview.get("error") or ("native rendering was not requested" if not render else "native rendering did not run")
        native = {"status": "not_run", "reason": reason}
        notes.append("The panel has not been rendered natively; look at a render before treating it as final."
                     if not render else "Native rendering did not run, so the panel is an unrendered draft.")

    report = {
        "ok": True,
        "operation": "draw_figure",
        "kind": "scope",
        "output_dir": str(target),
        "pages": pages,
        "species": [{k: g[k] for k in ("id", "label", "name", "smiles", "source")} for g in grounded],
        "fields": fields,
        "checks": {"data_binding": checks["data_binding"], "chemistry": checks["chemistry"]},
        "lint": {"issues": checks["layout"]["issues"], "relayout": None},
        "readback": readback,
        "native": native,
        "checks_passed": (checks["data_binding"]["status"] == "passed" and checks["chemistry"]["status"] == "passed"
                          and not checks["layout"]["issues"] and readback["status"] == "matched"),
        "notes": notes,
        "warnings": warnings,
    }
    return artifact_safety.with_artifacts(report, produced)


__all__ = ["SCOPE_KEYS", "draw_scope"]
