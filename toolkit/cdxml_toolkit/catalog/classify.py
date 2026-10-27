"""Tier every catalog row: T1 dedicated tool, T2 run-verified recipe, T3 documented only.

The catalogs say what ChemDraw has; ``classification.json`` (hand-edited) and the recipes
say what this Skill can already do with it. A row is T2 only when a recipe that was run
covers it, and T1 only when a registered tool does the job. Everything else is T3 and carries
the reason, which later phases replace as tools arrive.
"""

from __future__ import annotations

import json
from importlib import resources
from typing import Any, Iterable, Optional

LAYERS = ("chemscript", "com", "menu", "cdxml")
CATALOG_FILES = {
    "chemscript": "chemscript_22_2.json",
    "com": "com_22_2.json",
    "menu": "menu_22_2.json",
    "cdxml": "cdxml_model_22_2.json",
}
TIERS = ("T1", "T2", "T3")


def _data(name: str) -> dict[str, Any]:
    return json.loads(resources.files(__package__).joinpath("data", name).read_text(encoding="utf-8"))


def load_catalog(layer: str) -> dict[str, Any]:
    return _data(CATALOG_FILES[layer])


def load_classification() -> dict[str, Any]:
    return _data("classification.json")


def _row(layer: str, symbol: str, kind: str, tier: str, **extra: Any) -> dict[str, Any]:
    row = {"id": f"{layer}:{symbol}", "layer": layer, "symbol": symbol, "kind": kind, "tier": tier}
    row.update({key: value for key, value in extra.items() if value not in (None, "")})
    return row


def _verified_members(chemscript: dict[str, Any], recipes: Iterable[dict[str, Any]]) -> dict[tuple[str, str], dict[str, Any]]:
    from .recipes import declaring_type

    verified: dict[tuple[str, str], dict[str, Any]] = {}
    for recipe in recipes:
        for symbol in recipe["members"]:
            type_name, member = symbol.split(".")
            owner = declaring_type(chemscript, type_name, member)
            if owner is not None:
                verified.setdefault((owner, member), recipe)
    return verified


def _chemscript_rows(catalog, recipes, reasons) -> list[dict[str, Any]]:
    verified = _verified_members(catalog, recipes)
    rows = []
    for entry in catalog["types"]:
        if entry["role"] != "api":
            reason = reasons[f"chemscript.{entry['role']}"]
            rows.append(_row("chemscript", entry["name"], f"type:{entry['role']}", "T3", reason=reason,
                             members=entry.get("member_count"), doc=entry.get("doc")))
            continue
        groups: dict[tuple[str, str], list[dict[str, Any]]] = {}
        for member in entry.get("members", []):
            groups.setdefault((member["kind"], member["name"]), []).append(member)
        for (kind, name), overloads in sorted(groups.items(), key=lambda item: (item[0][0] != "constructor", item[0][1])):
            recipe = verified.get((entry["name"], name))
            doc = next((m["doc"] for m in overloads if m.get("doc")), None)
            symbol = f"{entry['name']}.{name}"
            if recipe is not None:
                rows.append(_row("chemscript", symbol, kind, "T2", tool=recipe["tool"], recipe=recipe["id"],
                                 overloads=len(overloads), doc=doc))
            else:
                rows.append(_row("chemscript", symbol, kind, "T3", via="execute_chemscript_sdk",
                                 reason=reasons["chemscript.unverified"], overloads=len(overloads), doc=doc))
    return rows


def _com_rows(catalog, reasons) -> list[dict[str, Any]]:
    rows = []
    seen = set()
    libraries = [catalog["object_library"]]
    if "control_library" in catalog:
        libraries.append(catalog["control_library"])
    for library in libraries:
        for entry in library["types"]:
            if entry["name"] in seen:
                continue
            seen.add(entry["name"])
            if entry["kind"] in ("enum", "coclass", "alias", "record", "module", "union"):
                key = "com.enum" if entry["kind"] == "enum" else "com.coclass" if entry["kind"] == "coclass" else "com.default"
                rows.append(_row("com", entry["name"], f"type:{entry['kind']}", "T3", reason=reasons[key],
                                 members=len(entry.get("members", [])) or None, doc=entry.get("doc")))
                continue
            for member in entry.get("members", []):
                rows.append(_row("com", f"{entry['name']}.{member['name']}", member["kind"], "T3",
                                 reason=reasons["com.default"], doc=member.get("doc")))
    return rows


def _menu_rows(catalog, reasons) -> list[dict[str, Any]]:
    rows = []
    for menu in catalog["menus"]:
        for item in menu["items"]:
            symbol = f"{menu['caption']}/{item['caption']}"
            rows.append(_row("menu", symbol, "popup" if item.get("popup") else "command", "T3",
                             reason=reasons["menu.default"], command_id=item.get("command_id")))
    return rows


def _cdxml_rows(catalog, reasons) -> list[dict[str, Any]]:
    rows = []
    for element in catalog["elements"]:
        evidence = element["evidence"]
        joined = ",".join(evidence) or None
        if "observed" in evidence:
            rows.append(_row("cdxml", element["name"], "element", "T1", tool="chemdraw_object",
                             note=reasons["cdxml.object"], evidence=joined))
        elif evidence:
            rows.append(_row("cdxml", element["name"], "element", "T3", via="chemdraw_object",
                             reason=reasons["cdxml.default"], evidence=joined))
        else:
            rows.append(_row("cdxml", element["name"], "element", "T3", reason=reasons["cdxml.unconfirmed"]))
    return rows


def classify(catalogs: dict[str, dict[str, Any]], recipes: list[dict[str, Any]], classification: dict[str, Any]) -> list[dict[str, Any]]:
    reasons = classification["reasons"]
    rows: list[dict[str, Any]] = []
    rows += _chemscript_rows(catalogs["chemscript"], recipes, reasons)
    rows += _com_rows(catalogs["com"], reasons)
    rows += _menu_rows(catalogs["menu"], reasons)
    rows += _cdxml_rows(catalogs["cdxml"], reasons)

    index = {row["id"]: row for row in rows}
    for override in classification.get("overrides", []):
        target = index.get(f"{override['layer']}:{override['symbol']}")
        if target is None:
            raise ValueError(f"classification override names an unknown symbol: {override['layer']}:{override['symbol']}")
        for stale in ("via", "reason"):
            target.pop(stale, None)
        target.update({"tier": override["tier"], "tool": override["tool"], "note": override.get("reason")})
    return rows


def summarize(rows: Iterable[dict[str, Any]]) -> dict[str, dict[str, int]]:
    summary = {layer: {tier: 0 for tier in TIERS} for layer in LAYERS}
    for row in rows:
        summary[row["layer"]][row["tier"]] += 1
    return summary


def all_rows() -> list[dict[str, Any]]:
    from . import recipes

    catalogs = {layer: load_catalog(layer) for layer in LAYERS}
    return classify(catalogs, recipes.load(), load_classification())


def find_row(rows: Iterable[dict[str, Any]], row_id: str) -> Optional[dict[str, Any]]:
    return next((row for row in rows if row["id"] == row_id), None)
