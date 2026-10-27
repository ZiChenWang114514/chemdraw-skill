"""chemdraw_object edits any CDXML object; chemdraw_inventory reads the ChemDraw interface catalog."""

from __future__ import annotations

from collections import Counter
from functools import lru_cache
from typing import Any

from cdxml_toolkit import model

from . import artifact_safety

OPERATIONS = ("list", "get", "set", "add", "delete")
MAX_TARGETS = 1000


def _failure(errors: list[str], **extra: Any) -> dict:
    return {"ok": False, "operation": "chemdraw_object", "errors": errors, **extra}


def _outermost(document: model.Document, matches: list) -> list:
    """Matches that are not inside another match; deleting those removes the rest with them."""
    parents = document.parent_map()
    chosen = {id(node) for node in matches}
    kept = []
    for node in matches:
        ancestor = parents.get(id(node))
        while ancestor is not None and id(ancestor) not in chosen:
            ancestor = parents.get(id(ancestor))
        if ancestor is None:
            kept.append(node)
    return kept


def _fingerprint(document: model.Document, skip: set[str]) -> dict[str, tuple]:
    return {node.get("id"): tuple(node.attrib.items()) for node in document.elements()
            if node.get("id") is not None and node.get("id") not in skip}


def _issue_key(issue: dict) -> tuple:
    return tuple(sorted((key, str(value)) for key, value in issue.items()))


def _verify(before: model.Document, edited: model.Document, expected_delta: int, touched: set[str]) -> dict:
    """Re-read what would be written and compare it with the input outside the edit."""
    reread = model.parse(edited.dumps())
    elements_before = sum(1 for _ in before.elements())
    elements_after = sum(1 for _ in reread.elements())
    known = {_issue_key(issue) for issue in before.check()}
    new_issues = [issue for issue in reread.check() if _issue_key(issue) not in known]
    problems = []
    if elements_after - elements_before != expected_delta:
        problems.append(f"expected {expected_delta:+d} elements, found {elements_after - elements_before:+d}")
    if new_issues:
        problems.append(f"new structural problems: {new_issues[:5]}")
    before_attrs = _fingerprint(before, touched)
    after_attrs = _fingerprint(reread, touched)
    changed = sorted(identifier for identifier in before_attrs if after_attrs.get(identifier) != before_attrs[identifier])
    if changed:
        problems.append(f"objects outside the edit changed: {changed[:10]}")
    report = {
        "status": "failed" if problems else "passed",
        "elements_before": elements_before,
        "elements_after": elements_after,
        "unchanged_checked": len(before_attrs),
        "new_issues": new_issues,
    }
    if problems:
        report["problems"] = problems
    return report


def chemdraw_object(
    op: str,
    input_path: str,
    selector: str | None = None,
    tag: str | None = None,
    props: dict | None = None,
    children: list | None = None,
    text: str | None = None,
    output_path: str | None = None,
    allow_unknown: bool = False,
    dry_run: bool = False,
    verify: bool = True,
    limit: int = 200,
) -> dict:
    """List, read, change, add or delete any object in a CDXML file, without touching the input.

    op is list, get, set, add or delete. selector picks elements: steps joined by ">" of
    tag#id[Attr=value] (for example "fragment > n[Element=8]", "b#5", "*[id=6]"); the first step
    matches anywhere, later steps match direct children. list without a selector counts the
    elements by tag; with one it describes up to limit matches. get needs a selector and
    returns the attributes and children count of each match. set changes the attributes in
    props ({name: value}, null removes one) on every match; an attribute the ChemDraw catalog
    does not list for that element is refused unless the element already carries it or
    allow_unknown is true, and integer/number/list values are checked. add appends a new tag
    to the one element that selector matches, with props, optional text and nested children
    [{tag, props, text, children}]; an id is assigned when the element type has one. delete
    removes the matched objects with their contents and refuses objects that other objects
    still point at (a bond's atoms, a bracket's members). Every other element, attribute and
    comment of the file is kept as read, in order, including ones this tool does not know.
    Changes are written to a new CDXML (output_path, or a fresh name beside the input);
    an existing file is never replaced. dry_run reports the changes and writes nothing.
    verify (default true) re-reads what would be written and checks the element count, that
    objects outside the edit are unchanged and that no duplicate id or dangling reference
    appeared; a failed check writes nothing. The edit is structural: render the result
    with ChemDraw before treating it as a final figure.
    """
    if op not in OPERATIONS:
        return _failure([f"op must be one of {', '.join(OPERATIONS)}, got {op!r}"])
    try:
        source = artifact_safety.validate_input_file(input_path, suffixes=(".cdxml",))
        document = model.load(source)
    except (FileNotFoundError, ValueError, OSError) as exc:
        return _failure([str(exc)])
    limit = max(1, min(int(limit or 200), MAX_TARGETS))

    if op == "list" and not selector:
        counts = Counter(node.tag for node in document.elements())
        return {"ok": True, "operation": "chemdraw_object", "op": op, "input_path": str(source),
                "elements": sum(counts.values()), "counts": dict(sorted(counts.items()))}

    if not selector:
        return _failure([f"{op} needs a selector"])
    try:
        matches = document.select(selector)
    except ValueError as exc:
        return _failure([str(exc)])
    if op not in ("list",) and not matches:
        return _failure([f"selector {selector!r} matched no element"])

    if op in ("list", "get"):
        parents = document.parent_map()
        shown = matches[:limit]
        return {"ok": True, "operation": "chemdraw_object", "op": op, "input_path": str(source),
                "matched": len(matches), "truncated": len(matches) > len(shown),
                "elements": [document.describe(node, parents) for node in shown]}

    if len(matches) > MAX_TARGETS:
        return _failure([f"selector {selector!r} matched {len(matches)} elements; narrow it to at most {MAX_TARGETS}"])

    reference = model.load(source)
    changes: list[dict] = []
    added: list[dict] = []
    removed = 0
    touched: set[str] = set()
    try:
        if op == "set":
            if not isinstance(props, dict) or not props:
                return _failure(["set needs props: an object of attribute values"])
            for node in matches:
                done = document.set_properties(node, props, allow_unknown=allow_unknown)
                if done:
                    changes.append({"id": node.get("id"), "tag": node.tag,
                                    "attributes": {name: {"old": old, "new": new} for name, (old, new) in done.items()}})
                touched.add(node.get("id"))
            expected_delta = 0
        elif op == "add":
            if len(matches) != 1:
                return _failure([f"add needs exactly one parent: selector {selector!r} matched {len(matches)}"])
            if not tag:
                return _failure(["add needs tag, the element to create"])
            node = document.add(matches[0], tag, props, children=children, text=text, allow_unknown=allow_unknown)
            subtree = [item for item in node.iter() if isinstance(item.tag, str)]
            added.append({"tag": node.tag, "id": node.get("id"), "path": document.path_of(node)})
            touched = {item.get("id") for item in subtree} | {matches[0].get("id")}
            expected_delta = len(subtree)
        else:
            for node in _outermost(document, matches):
                touched |= {item.get("id") for item in node.iter() if isinstance(item.tag, str)}
                removed += document.delete(node)
            expected_delta = -removed
    except (ValueError, KeyError, TypeError) as exc:
        return _failure([str(exc)])
    touched.discard(None)

    verification: dict[str, Any] = {"status": "skipped"}
    if verify:
        verification = _verify(reference, document, expected_delta, touched)
        if verification["status"] == "failed":
            return _failure(["Verification failed; nothing was written: " + "; ".join(verification["problems"])],
                            verification=verification)

    report: dict[str, Any] = {"ok": True, "operation": "chemdraw_object", "op": op, "input_path": str(source),
                              "matched": len(matches), "verification": verification}
    if op == "set":
        report["changes"] = changes
    elif op == "add":
        report["added"] = added
    else:
        report["removed"] = removed
    if dry_run:
        report["dry_run"] = True
        return report
    try:
        target = artifact_safety.resolve_destination(
            source=source, output_path=output_path, tag="edited", suffix=".cdxml")
        with artifact_safety.staging_file(target) as stage:
            stage.write_bytes(document.dump_bytes())
            artifact_safety.publish_file(stage, target)
    except (ValueError, OSError) as exc:  # includes OutputExistsError
        return _failure([str(exc)])
    report["output_path"] = str(target)
    return artifact_safety.with_artifacts(report, [target])


@lru_cache(maxsize=1)
def _rows() -> tuple:
    from cdxml_toolkit.catalog import classify

    return tuple(classify.all_rows())


_ROW_FIELDS = ("id", "layer", "symbol", "kind", "tier", "tool", "recipe", "via", "command_id", "overloads", "evidence")


def chemdraw_inventory(
    layer: str | None = None,
    query: str | None = None,
    tier: str | None = None,
    kind: str | None = None,
    limit: int = 50,
) -> dict:
    """Look up ChemDraw's own interfaces and how far this Skill covers each one.

    The catalog lists what ChemDraw 22.2 reports about itself: ChemScript SDK members
    (layer chemscript), COM automation objects (com), CDXML elements (cdxml) and menu
    commands with their command ids (menu). Every row has a tier: T1 a dedicated tool does
    it (tool names it), T2 a generic tool reaches it with a recipe that was run and checked
    (recipe, tool), T3 it is documented only (reason says why). Filter by layer, tier, kind
    (for example method, property, element, command, enum) and query, a case-insensitive
    text found in the row id or its documentation; limit caps the rows returned. The summary
    counts every row per layer and tier whatever the filter. Nothing here talks to ChemDraw.
    """
    from cdxml_toolkit.catalog import classify

    errors = []
    if layer is not None and layer not in classify.LAYERS:
        errors.append(f"layer must be one of {', '.join(classify.LAYERS)}, got {layer!r}")
    if tier is not None and tier not in classify.TIERS:
        errors.append(f"tier must be one of {', '.join(classify.TIERS)}, got {tier!r}")
    if errors:
        return {"ok": False, "operation": "chemdraw_inventory", "errors": errors}
    needle = (query or "").strip().lower()
    rows = [row for row in _rows()
            if (layer is None or row["layer"] == layer)
            and (tier is None or row["tier"] == tier)
            and (kind is None or row["kind"] == kind or row["kind"].split(":")[0] == kind)
            and (not needle or needle in row["id"].lower() or needle in str(row.get("doc") or "").lower())]
    limit = max(1, min(int(limit or 50), 500))
    shown = []
    for row in rows[:limit]:
        entry = {key: row[key] for key in _ROW_FIELDS if key in row}
        note = row.get("note") or row.get("reason")
        if note:
            entry["reason" if row["tier"] == "T3" else "note"] = note
        if row.get("doc"):
            entry["doc"] = str(row["doc"])[:240]
        shown.append(entry)
    return {
        "ok": True,
        "operation": "chemdraw_inventory",
        "verified_on": classify.load_catalog("cdxml").get("verified_on"),
        "matched": len(rows),
        "truncated": len(rows) > len(shown),
        "rows": shown,
        "summary": classify.summarize(_rows()),
    }


OBJECT_TOOLS = {"chemdraw_object": chemdraw_object, "chemdraw_inventory": chemdraw_inventory}
