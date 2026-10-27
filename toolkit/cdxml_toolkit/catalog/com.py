"""Catalog of ChemDraw's COM automation object model, read from its type libraries.

``read_typelib`` walks a registered or on-disk type library with ``pythoncom`` (Windows
only) and never starts ChemDraw: type libraries are metadata inside ``ChemDraw.exe`` and
``ChemDrawCtl.dll``. The result is plain JSON-able data.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Optional

# pythoncom type-kind numbers (TYPEKIND) and invoke kinds (INVOKEKIND).
TYPE_KINDS = {
    0: "enum", 1: "record", 2: "module", 3: "interface", 4: "dispatch",
    5: "coclass", 6: "alias", 7: "union",
}
INVOKE_KINDS = {1: "method", 2: "property_get", 4: "property_put", 8: "property_putref"}
VT_NAMES = {
    0: "empty", 1: "null", 2: "short", 3: "long", 4: "float", 5: "double", 6: "currency",
    7: "date", 8: "string", 9: "dispatch", 10: "error", 11: "bool", 12: "variant",
    13: "unknown", 14: "decimal", 16: "char", 17: "byte", 18: "ushort", 19: "ulong",
    20: "int64", 21: "uint64", 22: "int", 23: "uint", 24: "void", 25: "hresult",
    30: "lpstr", 31: "lpwstr",
}
VT_PTR, VT_SAFEARRAY, VT_CARRAY, VT_USERDEFINED = 26, 27, 28, 29
# FUNCFLAGS bits that matter to a reader.
FUNC_RESTRICTED, FUNC_HIDDEN = 0x1, 0x40
# Members every COM interface inherits; they say nothing about ChemDraw.
INHERITED = {"QueryInterface", "AddRef", "Release", "GetTypeInfoCount", "GetTypeInfo", "GetIDsOfNames", "Invoke"}


def type_name(desc, info) -> str:
    """Readable name of a TYPEDESC as pythoncom returns it: an int, or ``(vt, inner)``."""
    if isinstance(desc, int):
        return VT_NAMES.get(desc & 0xFFF, f"vt{desc}")
    vt, inner = desc[0], desc[1]
    if vt == VT_PTR:
        return type_name(inner, info) + "*"
    if vt in (VT_SAFEARRAY, VT_CARRAY):
        return type_name(inner, info) + "[]"
    if vt == VT_USERDEFINED:
        try:
            return info.GetRefTypeInfo(inner).GetDocumentation(-1)[0]
        except Exception:
            return "userdefined"
    return VT_NAMES.get(vt & 0xFFF, f"vt{vt}")


def _parameters(func, info, names) -> list[dict[str, Any]]:
    params = []
    for position, arg in enumerate(func[2]):
        desc, flags = arg[0], arg[1]
        label = names[position + 1] if position + 1 < len(names) else f"arg{position + 1}"
        entry = {"name": label, "type": type_name(desc, info)}
        if flags & 1:
            entry["in"] = True
        if flags & 2:
            entry["out"] = True
        if flags & 16:
            entry["optional"] = True
        params.append(entry)
    return params


_ACCESS = {"property_get": "get", "property_put": "put", "property_putref": "putref"}


def merge_properties(members: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Fold a property's get/put/putref accessors into one ``property`` member, in first-seen order."""
    merged: list[dict[str, Any]] = []
    properties: dict[str, dict[str, Any]] = {}
    for member in members:
        access = _ACCESS.get(member["kind"])
        if access is None:
            merged.append(member)
            continue
        prop = properties.get(member["name"])
        if prop is None:
            prop = {"kind": "property", "name": member["name"], "access": []}
            properties[member["name"]] = prop
            merged.append(prop)
        prop["access"].append(access)
        if access == "get":
            prop["type"] = member["returns"]
            if member["parameters"]:
                prop["parameters"] = member["parameters"]
        elif "type" not in prop and member["parameters"]:
            prop["type"] = member["parameters"][-1]["type"]
        if member.get("doc") and "doc" not in prop:
            prop["doc"] = member["doc"]
        if member.get("hidden"):
            prop["hidden"] = True
    for prop in properties.values():
        # "type" first, as in the other member kinds.
        ordered = {k: prop[k] for k in ("kind", "name", "type", "access", "parameters", "doc", "hidden") if k in prop}
        prop.clear()
        prop.update(ordered)
    return merged


def _describe_type(lib, index: int) -> Optional[dict[str, Any]]:
    info = lib.GetTypeInfo(index)
    attr = info.GetTypeAttr()
    kind = TYPE_KINDS.get(attr[5], f"kind{attr[5]}")
    name, doc = info.GetDocumentation(-1)[:2]
    entry: dict[str, Any] = {"name": name, "kind": kind, "guid": str(attr[0])}
    if doc:
        entry["doc"] = " ".join(doc.split())
    if kind == "coclass":
        entry["implements"] = [
            info.GetRefTypeInfo(info.GetRefTypeOfImplType(i)).GetDocumentation(-1)[0]
            for i in range(attr[8])
        ]
        return entry
    members = []
    for i in range(attr[6]):
        func = info.GetFuncDesc(i)
        names = info.GetNames(func[0])
        if names[0] in INHERITED:
            continue
        member = {
            "kind": INVOKE_KINDS.get(func[4], f"invoke{func[4]}"),
            "name": names[0],
            "returns": type_name(func[8][0], info),
            "parameters": _parameters(func, info, names),
        }
        text = info.GetDocumentation(func[0])[1]
        if text:
            member["doc"] = " ".join(text.split())
        if func[9] & (FUNC_RESTRICTED | FUNC_HIDDEN):
            member["hidden"] = True
        members.append(member)
    for i in range(attr[7]):
        var = info.GetVarDesc(i)
        names = info.GetNames(var[0])
        if kind == "enum":
            member = {"kind": "constant", "name": names[0], "value": var[1]}
        elif kind == "dispatch":
            # A dispinterface variable is a property; VARFLAG_FREADONLY is bit 0 of the flags.
            member = {
                "kind": "property",
                "name": names[0],
                "type": type_name(var[2][0], info),
                "access": ["get"] if var[3] & 1 else ["get", "put"],
            }
        else:
            member = {"kind": "field", "name": names[0], "type": type_name(var[2][0], info)}
        text = info.GetDocumentation(var[0])[1]
        if text:
            member["doc"] = " ".join(text.split())
        members.append(member)
    entry["members"] = merge_properties(members)
    return entry


def read_typelib(path) -> dict[str, Any]:
    """Describe every type of the type library at ``path`` (an .exe, .dll, .ocx or .tlb)."""
    import pythoncom  # Windows only; imported late so the rest of the package stays portable

    lib = pythoncom.LoadTypeLib(str(path))
    library_name, library_doc = lib.GetDocumentation(-1)[:2]
    attr = lib.GetLibAttr()
    types = []
    for index in range(lib.GetTypeInfoCount()):
        entry = _describe_type(lib, index)
        if entry:
            types.append(entry)
    types.sort(key=lambda item: item["name"])
    return {
        "library": library_name,
        "description": library_doc,
        "guid": str(attr[0]),
        "version": f"{attr[3]}.{attr[4]}",
        "types": types,
    }


def _counts(prefix: str, library: dict[str, Any]) -> dict[str, int]:
    types = library["types"]
    return {
        f"{prefix}_types": len(types),
        f"{prefix}_members": sum(len(t.get("members", [])) for t in types),
    }


def extract_live(*, verified_on: Optional[str] = None) -> dict[str, Any]:
    """Read the type libraries of the installed ChemDraw (Windows); ChemDraw is not started."""
    from ..mcp_runtime import runtime_discovery

    exe = Path(runtime_discovery.find_chemdraw().path)
    control = exe.with_name("ChemDrawCtl.dll")
    object_library = read_typelib(exe)
    catalog: dict[str, Any] = {
        "schema": 1,
        "layer": "com",
        "verified_on": verified_on or os.environ.get("CDX_VERIFIED_ON", "unverified"),
        "sources": ["typelib"],
        "object_library": object_library,
    }
    counts = _counts("object_library", object_library)
    if control.is_file():
        control_library = read_typelib(control)
        catalog["control_library"] = control_library
        counts.update(_counts("control_library", control_library))
    catalog["counts"] = counts
    return catalog


def dump(catalog: dict[str, Any]) -> str:
    return json.dumps(catalog, ensure_ascii=False, indent=1) + "\n"
