"""Catalog of the ChemScript SDK: the installed assembly joined with its shipped XML docs.

The reflection dump comes from ``inspect_chemscript_sdk`` (so it describes exactly what
``execute_chemscript_sdk`` can reach); the XML file the SDK installs supplies one-line
summaries. Only members of real API types are listed. Generated collection wrappers and
SWIG interop plumbing are counted per type, never listed.
"""

from __future__ import annotations

import json
import os
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Optional

NAMESPACE = "CambridgeSoft.ChemScript."
XML_NAME = "CambridgeSoft.ChemScript.XML"
SUMMARY_LIMIT = 220
_COLLECTION = re.compile(r"(List|Vector|Map|Enumerator|Dictionary_\w+)$")
_VERSION = re.compile(r"Version=([\d.]+)")


def _short(name: str) -> str:
    return name[len(NAMESPACE):] if name.startswith(NAMESPACE) else name


def _one_line(element: Optional[ET.Element]) -> str:
    if element is None:
        return ""
    paragraphs = element.findall("para")
    pieces = ["".join(p.itertext()) for p in paragraphs] if paragraphs else ["".join(element.itertext())]
    text = " ".join(" ".join(piece.split()) for piece in pieces if piece.strip())
    if len(text) > SUMMARY_LIMIT:
        text = text[: SUMMARY_LIMIT - 1].rstrip() + "…"
    return text


def parse_xml_docs(path) -> dict[str, str]:
    """Map each ``T:``/``M:``/``P:``/``F:`` key of the SDK's XML docs to its one-line summary."""
    root = ET.parse(str(path)).getroot()
    docs = {}
    for member in root.iter("member"):
        summary = _one_line(member.find("summary"))
        if summary:
            docs[member.get("name")] = summary
    return docs


def _top_level_commas(parameters: str) -> int:
    depth = 0
    count = 0
    for char in parameters:
        if char in "({[<":
            depth += 1
        elif char in ")}]>":
            depth -= 1
        elif char == "," and depth == 0:
            count += 1
    return count


def _doc_index(docs: dict[str, str]) -> dict[tuple[str, str], dict[int, str]]:
    index: dict[tuple[str, str], dict[int, str]] = {}
    for key, summary in docs.items():
        kind, _, rest = key.partition(":")
        if kind not in ("M", "P", "F"):
            continue
        base, paren, parameters = rest.partition("(")
        arity = 0 if not paren else 1 + _top_level_commas(parameters[:-1])
        index.setdefault((kind, base), {}).setdefault(arity, summary)
    return index


def _lookup(index, type_name: str, member: dict[str, Any]) -> Optional[str]:
    kind = member["kind"]
    name = "#ctor" if kind == "constructor" else member["name"]
    letter = {"method": "M", "constructor": "M", "property": "P", "field": "F"}[kind]
    found = index.get((letter, f"{type_name}.{name}"))
    if not found:
        return None
    arity = len(member.get("parameters") or [])
    return found.get(arity) or (next(iter(found.values())) if len(found) == 1 else None)


def build_catalog(
    reflection: dict[str, Any],
    docs: dict[str, str],
    *,
    verified_on: str = "unverified",
) -> dict[str, Any]:
    """Join a reflection dump (``include_infrastructure`` on) with XML summaries."""
    index = _doc_index(docs)
    by_type: dict[str, list[dict[str, Any]]] = {}
    for member in reflection["members"]:
        by_type.setdefault(member["type"], []).append(member)

    types = []
    listed = documented = 0
    for record in sorted(reflection["types"], key=lambda item: item["name"]):
        full = record["name"]
        members = by_type.get(full, [])
        api = [m for m in members if m["classification"] == "sdk_api"]
        entry: dict[str, Any] = {"name": _short(full), "kind": record["kind"]}
        summary = docs.get("T:" + full)
        if summary:
            entry["doc"] = summary
        if members and not api:
            entry["role"] = "interop"
            entry["member_count"] = len(members)
        elif _COLLECTION.search(_short(full)):
            entry["role"] = "collection"
            entry["member_count"] = len(members)
        else:
            entry["role"] = "api"
            listed_members = []
            for member in sorted(api, key=lambda m: (m["kind"] != "constructor", m["name"], m["signature"])):
                row: dict[str, Any] = {
                    "kind": member["kind"],
                    "name": member["name"],
                    "signature": member["signature"],
                }
                if member.get("static"):
                    row["static"] = True
                doc = _lookup(index, full, member)
                if doc:
                    row["doc"] = doc
                    documented += 1
                listed_members.append(row)
            entry["members"] = listed_members
            entry["interop_members"] = len(members) - len(api)
            listed += len(listed_members)
        types.append(entry)

    version = _VERSION.search(reflection.get("assembly", ""))
    return {
        "schema": 1,
        "layer": "chemscript",
        "assembly": reflection.get("assembly", "").split(",")[0],
        "assembly_version": version.group(1) if version else None,
        "verified_on": verified_on,
        "sources": ["reflection", "xml_docs"] if docs else ["reflection"],
        "counts": {
            "types": len(types),
            "types_api": sum(t["role"] == "api" for t in types),
            "types_collection": sum(t["role"] == "collection" for t in types),
            "types_interop": sum(t["role"] == "interop" for t in types),
            "members_total": len(reflection["members"]),
            "members_listed": listed,
            "api_members_documented": documented,
            "api_members_undocumented": listed - documented,
        },
        "types": types,
    }


def _dll_dir() -> Path:
    from ..mcp_runtime import chemscript_sdk_runtime

    configured = chemscript_sdk_runtime._load_configuration().get("dll_dir")
    if not configured:
        raise RuntimeError("ChemScript is not configured: set CHEMSCRIPT_DLL_DIR or ~/.chemscript_config.json")
    return Path(str(configured)).expanduser()


def extract_live(reflection_path, *, verified_on: Optional[str] = None) -> dict[str, Any]:
    """Read the installed SDK (Windows) and build the catalog; ``reflection_path`` must not exist."""
    from ..mcp_runtime import chemscript_sdk

    chemscript_sdk.inspect_chemscript_sdk(output_path=str(reflection_path))
    reflection = json.loads(Path(reflection_path).read_text(encoding="utf-8"))
    xml_path = _dll_dir() / XML_NAME
    docs = parse_xml_docs(xml_path) if xml_path.is_file() else {}
    return build_catalog(reflection, docs, verified_on=verified_on or os.environ.get("CDX_VERIFIED_ON", "unverified"))


def dump(catalog: dict[str, Any]) -> str:
    return json.dumps(catalog, ensure_ascii=False, indent=1, sort_keys=False) + "\n"
