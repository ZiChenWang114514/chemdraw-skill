"""Catalog of the CDXML document model: which elements and attributes ChemDraw itself writes.

ChemDraw ships no DTD, so the evidence is empirical:

* ``observed``: the element appears in CDXML that ChemDraw wrote (the templates and samples
  it installs, its own conversions of the bundled CDX files, and objects built through COM
  and saved by ChemDraw). Only these elements list attributes, nesting and value shapes.
* ``binary``: the name appears in ChemDraw's own binaries but no observed document uses it.
* neither: a candidate name from the CDXML format that this installation gave no evidence for.

The catalog records value *shapes* (integer, numbers, enum with a short value list), never
document text. It cannot prove that an element or attribute is absent from the format.
"""

from __future__ import annotations

import json
import os
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Iterable, Optional

ENUM_LIMIT = 16
ENUM_VALUE = re.compile(r"^[A-Za-z0-9_.+\-]{1,24}$")
_INTEGER = re.compile(r"^-?\d+$")
_NUMBER = re.compile(r"^-?\d+(\.\d+)?([eE][-+]?\d+)?$")

# Element names of the CDXML format, kept by hand: the candidates the binaries are checked for.
CANDIDATES = (
    "CDXML", "page", "group", "fragment", "n", "b", "t", "s", "annotation", "altgroup", "arrow",
    "bioshape", "border", "bracketattachment", "bracketedgroup", "chemicalproperty", "color",
    "colortable", "constraint", "crossingbond", "curve", "embeddedobject", "font", "fonttable",
    "geometry", "graphic", "marker", "objecttag", "plasmidmap", "plasmidmarker", "plasmidregion",
    "represent", "scheme", "sgcomponent", "sgdatum", "spectrum", "splitter", "step", "stoichiometrygrid",
    "table", "templategrid", "tlclane", "tlcplate", "tlcspot", "gepband", "geplane", "gepplate",
    "stereocenter", "regenerationclass", "mixedprotein",
)


def summarise_values(values: set[str]) -> dict[str, Any]:
    """Describe the shape of an attribute's observed values without keeping free text."""
    if all(_INTEGER.match(v) for v in values):
        return {"kind": "integer"}
    if all(_NUMBER.match(v) for v in values):
        return {"kind": "number"}
    if all(all(_NUMBER.match(part) for part in v.split()) and v.strip() for v in values):
        return {"kind": "numbers"}
    if len(values) <= ENUM_LIMIT and all(ENUM_VALUE.match(v) for v in values):
        return {"kind": "enum", "values": sorted(values)}
    return {"kind": "string"}


def scan_documents(paths: Iterable[Path]) -> dict[str, Any]:
    """Collect elements, attributes, nesting and value shapes from CDXML files."""
    elements: dict[str, dict[str, Any]] = {}
    documents = unparsable = 0
    for path in paths:
        try:
            root = ET.parse(str(path)).getroot()
        except (ET.ParseError, OSError, UnicodeDecodeError):
            unparsable += 1
            continue
        documents += 1
        seen_elements: set[str] = set()
        seen_attributes: set[tuple[str, str]] = set()
        for parent in root.iter():
            entry = elements.setdefault(
                parent.tag,
                {"count": 0, "documents": 0, "attributes": {}, "children": set(), "parents": set()},
            )
            entry["count"] += 1
            if parent.tag not in seen_elements:
                seen_elements.add(parent.tag)
                entry["documents"] += 1
            for name, value in parent.attrib.items():
                attribute = entry["attributes"].setdefault(
                    name, {"count": 0, "documents": 0, "samples": set()}
                )
                attribute["count"] += 1
                if (parent.tag, name) not in seen_attributes:
                    seen_attributes.add((parent.tag, name))
                    attribute["documents"] += 1
                if len(attribute["samples"]) <= ENUM_LIMIT + 1:
                    attribute["samples"].add(value)
            for child in parent:
                entry["children"].add(child.tag)
                elements.setdefault(
                    child.tag,
                    {"count": 0, "documents": 0, "attributes": {}, "children": set(), "parents": set()},
                )["parents"].add(parent.tag)
    for entry in elements.values():
        for attribute in entry["attributes"].values():
            attribute.update(summarise_values(attribute.pop("samples")))
        entry["children"] = sorted(entry["children"])
        entry["parents"] = sorted(entry["parents"])
    return {"documents": documents, "unparsable": unparsable, "elements": elements}


def binary_names(paths: Iterable[Path], names: Iterable[str]) -> set[str]:
    """Names that occur as standalone ASCII strings in the given binaries."""
    wanted = list(names)
    found: set[str] = set()
    for path in paths:
        data = Path(path).read_bytes()
        for name in wanted:
            if name not in found and re.search(rb"(?<![A-Za-z0-9_])" + re.escape(name.encode()) + rb"(?![A-Za-z0-9_])", data):
                found.add(name)
    return found


def build_catalog(
    observed: dict[str, Any],
    *,
    binary_names: set[str],
    candidates: Iterable[str] = CANDIDATES,
    fixtures: Optional[list[dict[str, Any]]] = None,
    verified_on: str = "unverified",
) -> dict[str, Any]:
    names = sorted(set(observed["elements"]) | set(candidates))
    elements = []
    for name in names:
        seen = observed["elements"].get(name)
        evidence = []
        if seen is not None:
            evidence.append("observed")
        if name in binary_names and seen is None:
            evidence.append("binary")
        row: dict[str, Any] = {"name": name, "evidence": evidence}
        if seen is not None:
            row["count"] = seen["count"]
            row["documents"] = seen["documents"]
            row["attributes"] = [
                {"name": attr, **{k: v for k, v in info.items()}}
                for attr, info in sorted(seen["attributes"].items())
            ]
            row["children"] = seen["children"]
            row["parents"] = seen["parents"]
        elements.append(row)
    observed_count = sum("observed" in row["evidence"] for row in elements)
    binary_only = sum(row["evidence"] == ["binary"] for row in elements)
    return {
        "schema": 1,
        "layer": "cdxml",
        "verified_on": verified_on,
        "sources": ["chemdraw_authored_documents", "binary_strings"],
        "limits": "Empirical: no DTD ships with ChemDraw, so absence of an element or attribute proves nothing.",
        "documents_scanned": observed["documents"],
        "documents_unparsable": observed["unparsable"],
        "fixtures": fixtures or [],
        "counts": {
            "elements": len(elements),
            "attributes": sum(len(row.get("attributes", [])) for row in elements),
            "elements_observed": observed_count,
            "elements_binary_only": binary_only,
            "elements_unconfirmed": len(elements) - observed_count - binary_only,
        },
        "elements": elements,
    }


def _data_roots() -> list[Path]:
    roots = []
    for variable in ("ProgramData", "ALLUSERSPROFILE"):
        base = os.environ.get(variable)
        if base:
            for vendor in ("PerkinElmerInformatics", "Revvity"):
                candidate = Path(base) / vendor
                if candidate.is_dir() and candidate not in roots:
                    roots.append(candidate)
    return roots


# (name, how to build the object in an empty document); each runs best-effort.
FIXTURES = (
    ("caption", lambda doc: doc.MakeCaption()),
    ("spline", lambda doc: doc.MakeSpline()),
    ("arrow", lambda doc: doc.MakeArrow()),
    ("rectangle", lambda doc: doc.MakeRectangle()),
    ("ellipse", lambda doc: doc.MakeEllipse()),
    ("bracket", lambda doc: doc.MakeBracket(0)),
    ("symbol", lambda doc: doc.MakeSymbol(0)),
    ("orbital", lambda doc: doc.MakeOrbital(0)),
    ("table", lambda doc: doc.MakeTable()),
    ("altgroup", lambda doc: doc.MakeAltGroup()),
    ("geometry", lambda doc: doc.MakeGeometry(0)),
    ("constraint", lambda doc: doc.MakeConstraint(0)),
    ("tlcplate", lambda doc: doc.MakeTLCPlate()),
    ("stoichiometrygrid", lambda doc: doc.MakeStoichiometryGrid()),
    ("plasmidmap", lambda doc: doc.MakePlasmidMap()),
)


def _chemdraw_outputs(install_dir: Path, workdir: Path) -> tuple[list[Path], list[dict[str, Any]]]:
    """Have a private ChemDraw convert its bundled CDX files and save fixture documents."""
    import gc

    import pythoncom
    import win32com.client as win32

    from ..mcp_runtime.resource_lock import native_resource_lock

    outputs: list[Path] = []
    fixtures: list[dict[str, Any]] = []
    with native_resource_lock("chemdraw_com", 300):
        pythoncom.CoInitialize()
        try:
            application = win32.DispatchEx("ChemDraw.Application")
            try:
                for source in sorted(install_dir.rglob("*.cdx")):
                    target = workdir / f"roundtrip_{source.stem}.cdxml"
                    try:
                        document = application.Documents.Open(str(source))
                        document.SaveAs(str(target))
                        document.Close()
                        outputs.append(target)
                    except Exception:
                        continue
                for name, build in FIXTURES:
                    target = workdir / f"fixture_{name}.cdxml"
                    status = "ok"
                    try:
                        document = application.Documents.Add()
                        build(document)
                        document.SaveAs(str(target))
                        document.Close()
                        outputs.append(target)
                    except Exception as error:
                        status = f"failed: {str(error)[:80]}"
                    fixtures.append({"name": name, "status": status})
            finally:
                try:
                    application.Quit()
                except Exception:
                    pass
                application = None
                document = None
                gc.collect()
        finally:
            pythoncom.CoUninitialize()
    return outputs, fixtures


def extract_live(workdir, *, verified_on: Optional[str] = None) -> dict[str, Any]:
    """Scan the CDXML ChemDraw installs, plus what it writes for the bundled CDX files and fixtures."""
    from ..mcp_runtime import runtime_discovery

    workdir = Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    executable = Path(runtime_discovery.find_chemdraw().path)
    install_dir = executable.parent
    documents = [path for root in _data_roots() for path in sorted(root.rglob("*.cdxml"))]
    written, fixtures = _chemdraw_outputs(install_dir, workdir)
    documents.extend(written)
    binaries = [path for path in sorted(install_dir.glob("*.dll")) if path.stat().st_size > 100_000]
    binaries.append(executable)
    observed = scan_documents(documents)
    found = binary_names(binaries, [name for name in CANDIDATES if len(name) > 1])
    return build_catalog(
        observed,
        binary_names=found,
        fixtures=fixtures,
        verified_on=verified_on or os.environ.get("CDX_VERIFIED_ON", "unverified"),
    )


def dump(catalog: dict[str, Any]) -> str:
    return json.dumps(catalog, ensure_ascii=False, indent=1) + "\n"
