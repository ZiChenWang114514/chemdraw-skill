"""Inspect and replace editable ChemDraw objects inside OOXML packages."""

from __future__ import annotations

from contextlib import contextmanager
import hashlib
import json
from pathlib import Path, PurePosixPath
import posixpath
import re
from typing import Any
import xml.etree.ElementTree as ET
import zipfile

from . import native_io
from . import native_renderer
_R_ID = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
_R_EMBED = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed"
_RELATIONSHIP_TYPE = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/"
_PT_TO_EMU = 12700


@contextmanager
def com_apartment():
    """Initialize COM for the current worker thread and release it symmetrically."""
    import pythoncom

    pythoncom.CoInitialize()
    try:
        yield
    finally:
        pythoncom.CoUninitialize()


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _relationship_target(relationship_part: str, target: str) -> str:
    normalized_target = target.replace("\\", "/")
    if normalized_target.startswith("/"):
        normalized = posixpath.normpath(normalized_target.lstrip("/"))
    else:
        rel_path = PurePosixPath(relationship_part)
        source_directory = rel_path.parent.parent
        normalized = posixpath.normpath(str(source_directory / normalized_target))
    if normalized == ".." or normalized.startswith("../"):
        raise ValueError(f"OOXML relationship escapes the package: {target}")
    return normalized.lstrip("./")


def _host_part(relationship_part: str) -> str:
    path = PurePosixPath(relationship_part)
    if path.parent.name != "_rels" or not path.name.endswith(".rels"):
        raise ValueError(f"Unsupported OOXML relationship part: {relationship_part}")
    return str(path.parent.parent / path.name[:-5])


def _ancestor(
    element: ET.Element,
    parents: dict[ET.Element, ET.Element],
    names: set[str],
) -> ET.Element | None:
    current = element
    while current in parents:
        current = parents[current]
        if _local_name(current.tag) in names:
            return current
    return None


def _integer_attribute(element: ET.Element | None, name: str) -> int | None:
    if element is None:
        return None
    value = element.attrib.get(name)
    try:
        return int(value) if value is not None else None
    except ValueError:
        return None


def _ppt_context(
    root: ET.Element,
    relationship_id: str,
    host_part: str,
) -> dict[str, Any]:
    parents = {child: parent for parent in root.iter() for child in parent}
    occurrences = [
        element
        for element in root.iter()
        if _local_name(element.tag) == "oleObj"
        and element.attrib.get(_R_ID) == relationship_id
    ]
    if not occurrences:
        raise ValueError(
            f"OLE relationship {relationship_id} is not referenced by {host_part}"
        )
    frames = [
        frame
        for element in occurrences
        if (frame := _ancestor(element, parents, {"graphicFrame"})) is not None
    ]
    frame = frames[0] if frames else None
    shape = next(
        (
            item
            for item in frame.iter()
            if _local_name(item.tag) == "cNvPr"
        ),
        None,
    ) if frame is not None else None
    transform = next(
        (
            item
            for item in frame.iter()
            if _local_name(item.tag) == "xfrm"
        ),
        None,
    ) if frame is not None else None
    transform_children = list(transform) if transform is not None else []
    offset = next(
        (item for item in transform_children if _local_name(item.tag) == "off"),
        None,
    )
    extent = next(
        (item for item in transform_children if _local_name(item.tag) == "ext"),
        None,
    )
    preview_id = None
    for occurrence in occurrences:
        for item in occurrence.iter():
            if _local_name(item.tag) == "blip" and item.attrib.get(_R_EMBED):
                preview_id = item.attrib[_R_EMBED]
                break
        if preview_id:
            break
    match = re.search(r"slide(\d+)\.xml$", host_part, flags=re.IGNORECASE)
    return {
        "host": {
            "kind": "slide",
            "number": int(match.group(1)) if match else None,
        },
        "shape_name": shape.attrib.get("name") if shape is not None else None,
        "geometry": {
            "x_emu": _integer_attribute(offset, "x"),
            "y_emu": _integer_attribute(offset, "y"),
            "width_emu": _integer_attribute(extent, "cx"),
            "height_emu": _integer_attribute(extent, "cy"),
        },
        "preview_relationship_id": preview_id,
    }


def _style_points(style: str, property_name: str) -> float | None:
    match = re.search(
        rf"(?:^|;)\s*{re.escape(property_name)}\s*:\s*([0-9.]+)pt(?:;|$)",
        style,
        flags=re.IGNORECASE,
    )
    return float(match.group(1)) if match else None


def _docx_context(
    root: ET.Element,
    relationship_id: str,
    host_part: str,
) -> dict[str, Any]:
    parents = {child: parent for parent in root.iter() for child in parent}
    occurrence = next(
        (
            element
            for element in root.iter()
            if _local_name(element.tag) == "OLEObject"
            and element.attrib.get(_R_ID) == relationship_id
        ),
        None,
    )
    if occurrence is None:
        raise ValueError(
            f"OLE relationship {relationship_id} is not referenced by {host_part}"
        )
    container = _ancestor(occurrence, parents, {"object"})
    shape = next(
        (
            item
            for item in container.iter()
            if _local_name(item.tag) == "shape"
        ),
        None,
    ) if container is not None else None
    image = next(
        (
            item
            for item in container.iter()
            if _local_name(item.tag) == "imagedata"
        ),
        None,
    ) if container is not None else None
    paragraph = _ancestor(occurrence, parents, {"p"})
    paragraph_number = None
    if paragraph is not None:
        paragraphs = [item for item in root.iter() if _local_name(item.tag) == "p"]
        paragraph_number = paragraphs.index(paragraph) + 1
    style = shape.attrib.get("style", "") if shape is not None else ""
    width = _style_points(style, "width")
    height = _style_points(style, "height")
    return {
        "host": {
            "kind": "document",
            "page": None,
            "paragraph": paragraph_number,
        },
        "shape_name": shape.attrib.get("id") if shape is not None else None,
        "geometry": {
            "x_emu": None,
            "y_emu": None,
            "width_emu": round(width * _PT_TO_EMU) if width is not None else None,
            "height_emu": round(height * _PT_TO_EMU) if height is not None else None,
        },
        "preview_relationship_id": image.attrib.get(_R_ID) if image is not None else None,
    }


def _object_sort_key(item: dict[str, Any]) -> tuple[Any, ...]:
    host = item["host"]
    relationship_match = re.search(r"(\d+)$", item["relationship_id"])
    relationship_number = (
        int(relationship_match.group(1)) if relationship_match else 2**31
    )
    if host.get("kind") == "slide":
        return (
            0,
            host.get("number") if host.get("number") is not None else 2**31,
            relationship_number,
            item["relationship_id"],
        )
    return (
        1,
        0 if item["host_part"] == "word/document.xml" else 1,
        item["host_part"],
        host.get("paragraph") if host.get("paragraph") is not None else 2**31,
        relationship_number,
        item["relationship_id"],
    )


def scan_office_objects(input_path: str | Path) -> tuple[str, list[dict[str, Any]]]:
    source = Path(input_path).expanduser().resolve()
    if source.suffix.lower() not in {".pptx", ".docx"}:
        raise ValueError("Only PPTX and DOCX files are supported")
    source_hash = sha256_file(source)
    from cdxml_toolkit.office.ole_extractor import extract_cdx_from_ole

    objects: list[dict[str, Any]] = []
    with zipfile.ZipFile(source, "r") as package:
        members = set(package.namelist())
        for relationship_part in sorted(
            name for name in members if name.endswith(".rels")
        ):
            relationships = ET.fromstring(package.read(relationship_part))
            by_id = {
                relationship.attrib.get("Id"): relationship
                for relationship in relationships
                if relationship.attrib.get("Id")
            }
            for relationship_id, relationship in sorted(by_id.items()):
                if not relationship.attrib.get("Type", "").endswith("/oleObject"):
                    continue
                if relationship.attrib.get("TargetMode") == "External":
                    continue
                target = relationship.attrib.get("Target")
                if not target:
                    raise ValueError(
                        f"OLE relationship {relationship_id} has no target"
                    )
                embedding_part = _relationship_target(relationship_part, target)
                if embedding_part not in members:
                    raise ValueError(f"Missing OLE package part: {embedding_part}")
                ole_data = package.read(embedding_part)
                cdx_data = extract_cdx_from_ole(ole_data)
                if not cdx_data:
                    continue
                host_part = _host_part(relationship_part)
                if host_part not in members:
                    raise ValueError(f"Missing OLE host XML part: {host_part}")
                root = ET.fromstring(package.read(host_part))
                context = (
                    _ppt_context(root, relationship_id, host_part)
                    if source.suffix.lower() == ".pptx"
                    else _docx_context(root, relationship_id, host_part)
                )
                preview_id = context.pop("preview_relationship_id")
                preview_part = None
                preview_hash = None
                if preview_id:
                    preview_relationship = by_id.get(preview_id)
                    if preview_relationship is None:
                        raise ValueError(
                            f"Missing preview relationship {preview_id} in {relationship_part}"
                        )
                    if not preview_relationship.attrib.get("Type", "").endswith("/image"):
                        raise ValueError(
                            f"Preview relationship {preview_id} is not an image"
                        )
                    preview_target = preview_relationship.attrib.get("Target")
                    if not preview_target:
                        raise ValueError(
                            f"Preview relationship {preview_id} has no target"
                        )
                    preview_part = _relationship_target(
                        relationship_part, preview_target
                    )
                    if preview_part not in members:
                        raise ValueError(f"Missing preview package part: {preview_part}")
                    preview_hash = _sha256(package.read(preview_part))
                object_key = "\0".join(
                    (source_hash, host_part, relationship_id, embedding_part)
                ).encode("utf-8")
                objects.append(
                    {
                        "object_id": "chemdraw-" + _sha256(object_key),
                        "host_part": host_part,
                        "relationship_part": relationship_part,
                        "relationship_id": relationship_id,
                        "embedding_part": embedding_part,
                        "embedding_sha256": _sha256(ole_data),
                        "preview_relationship_id": preview_id,
                        "preview_part": preview_part,
                        "preview_sha256": preview_hash,
                        **context,
                        "_cdx_data": cdx_data,
                    }
                )
    objects.sort(key=_object_sort_key)
    for ordinal, item in enumerate(objects, start=1):
        item["ordinal"] = ordinal
    return source_hash, objects


def _convert_cdx_to_cdxml(cdx_data: bytes) -> str:
    from cdxml_toolkit.chemdraw.cdx_converter import convert_file

    with com_apartment():
        return native_io.convert_cdx_bytes_to_cdxml(cdx_data, convert_file)


def _render_cdxml_preview(source: str, destination: str) -> None:
    def render(native_source: Path, native_destination: Path) -> None:
        with com_apartment():
            native_renderer.render_cdxml(
                native_source, native_destination, dpi=300
            )

    native_io.bridge_file(
        source, destination, render, output_kind="png"
    )


def _validate_cdxml_text(value: str, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RuntimeError(f"CDX conversion returned empty CDXML for {label}")
    try:
        root = ET.fromstring(value)
    except ET.ParseError as exc:
        raise RuntimeError(f"CDX conversion returned invalid CDXML for {label}: {exc}") from exc
    if _local_name(root.tag) != "CDXML":
        raise RuntimeError(f"CDX conversion returned a non-CDXML root for {label}")
    return value


def write_inspection(
    input_path: str | Path,
    output_dir: str | Path,
    *,
    render_previews: bool,
) -> dict[str, Any]:
    source = Path(input_path).resolve()
    destination = Path(output_dir).resolve()
    source_hash, records = scan_office_objects(source)
    if not records:
        raise ValueError(f"No editable ChemDraw objects were found: {source}")
    object_dir = destination / "objects"
    preview_dir = destination / "previews"
    object_dir.mkdir(parents=True, exist_ok=True)
    if render_previews:
        preview_dir.mkdir(parents=True, exist_ok=True)
    public_records = []
    for record in records:
        ordinal = record["ordinal"]
        stem = f"object_{ordinal:03d}"
        cdxml_relative = Path("objects") / f"{stem}.cdxml"
        cdxml_path = destination / cdxml_relative
        cdxml_text = _validate_cdxml_text(
            _convert_cdx_to_cdxml(record["_cdx_data"]), record["object_id"]
        )
        cdxml_path.write_text(cdxml_text, encoding="utf-8")
        public = {key: value for key, value in record.items() if not key.startswith("_")}
        public["cdxml"] = cdxml_relative.as_posix()
        if render_previews:
            preview_relative = Path("previews") / f"{stem}.png"
            preview_path = destination / preview_relative
            _render_cdxml_preview(str(cdxml_path), str(preview_path))
            if not preview_path.is_file() or preview_path.stat().st_size == 0:
                raise RuntimeError(f"ChemDraw preview was not created: {preview_path}")
            from PIL import Image

            with Image.open(preview_path) as image:
                image.verify()
            public["preview_png"] = preview_relative.as_posix()
        public_records.append(public)
    manifest = {
        "schema_version": 1,
        "kind": "chemdraw-office-inspection",
        "source_path": str(source),
        "source_sha256": source_hash,
        "objects": public_records,
    }
    manifest_path = destination / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def load_replacement_manifest(
    manifest_path: str | Path,
    *,
    source_sha256: str,
    objects: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    path = Path(manifest_path).expanduser().resolve()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Invalid replacement manifest JSON: {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("Replacement manifest root must be a JSON object")
    if data.get("schema_version") != 1 or isinstance(data.get("schema_version"), bool):
        raise ValueError("Replacement manifest schema_version must be 1")
    if data.get("source_sha256") != source_sha256:
        raise ValueError("Source Office SHA-256 changed after inspection")
    replacements = data.get("replacements")
    if not isinstance(replacements, list) or not replacements:
        raise ValueError("Replacement manifest requires a non-empty replacements list")
    known = {item["object_id"]: item for item in objects}
    seen: set[str] = set()
    base = path.parent.resolve()
    resolved = []
    for item in replacements:
        if not isinstance(item, dict):
            raise ValueError("Every replacement entry must be a JSON object")
        object_id = item.get("object_id")
        if not isinstance(object_id, str) or object_id not in known:
            raise ValueError(f"Replacement object ID is unknown or not recognized: {object_id}")
        if object_id in seen:
            raise ValueError(f"Replacement object ID is duplicate: {object_id}")
        seen.add(object_id)
        raw_path = item.get("replacement_cdxml")
        if not isinstance(raw_path, str) or not raw_path.strip():
            raise ValueError("replacement_cdxml must be a non-empty relative path")
        relative = Path(raw_path)
        if relative.is_absolute() or relative.drive:
            raise ValueError(f"replacement_cdxml must not be absolute: {raw_path}")
        if ".." in relative.parts:
            raise ValueError(f"replacement_cdxml path traversal is not allowed: {raw_path}")
        candidate = (base / relative).resolve()
        try:
            candidate.relative_to(base)
        except ValueError as exc:
            raise ValueError(
                f"replacement_cdxml must remain inside the manifest directory: {raw_path}"
            ) from exc
        if candidate.suffix.lower() != ".cdxml" or not candidate.is_file():
            raise FileNotFoundError(f"Replacement CDXML does not exist: {candidate}")
        try:
            root = ET.parse(candidate).getroot()
        except (OSError, ET.ParseError) as exc:
            raise ValueError(f"Invalid replacement CDXML {candidate}: {exc}") from exc
        if _local_name(root.tag) != "CDXML":
            raise ValueError(f"Replacement file is not CDXML: {candidate}")
        record = known[object_id]
        if not record.get("preview_part"):
            raise ValueError(
                f"ChemDraw object has no corresponding preview image: {object_id}"
            )
        resolved.append(
            {"object_id": object_id, "replacement_cdxml": candidate, "record": record}
        )
    return resolved


def rewrite_office_package(
    input_path: str | Path,
    output_path: str | Path,
    replacement_parts: dict[str, dict[str, bytes]],
) -> None:
    source = Path(input_path).resolve()
    destination = Path(output_path).resolve()
    parts: dict[str, bytes] = {}
    for object_id, replacement in replacement_parts.items():
        for key in ("embedding_part", "preview_part"):
            part = replacement.get(key)
            payload = replacement.get("ole_data" if key == "embedding_part" else "emf_data")
            if not isinstance(part, str) or not isinstance(payload, bytes) or not payload:
                raise ValueError(f"Invalid {key} replacement for {object_id}")
            if part in parts:
                raise ValueError(f"Multiple replacements target the same package part: {part}")
            parts[part] = payload
    seen: set[str] = set()
    with zipfile.ZipFile(source, "r") as package, zipfile.ZipFile(
        destination, "w", allowZip64=True
    ) as output:
        output.comment = package.comment
        for information in package.infolist():
            data = parts.get(information.filename, package.read(information.filename))
            if information.filename in parts:
                seen.add(information.filename)
            output.writestr(information, data)
    missing = sorted(set(parts) - seen)
    if missing:
        destination.unlink(missing_ok=True)
        raise ValueError(f"Replacement package parts are missing: {missing}")


def render_office_pdf(office_path: str | Path, output_path: str | Path) -> None:
    source = Path(office_path).resolve()
    destination = Path(output_path).resolve()

    def export(native_source: Path, native_destination: Path) -> None:
        import pythoncom
        import win32com.client

        pythoncom.CoInitialize()
        application = None
        document = None
        try:
            if native_source.suffix.lower() == ".pptx":
                application = win32com.client.DispatchEx("PowerPoint.Application")
                document = application.Presentations.Open(
                    str(native_source), True, False, False
                )
                document.SaveAs(str(native_destination), 32)
            else:
                application = win32com.client.DispatchEx("Word.Application")
                application.Visible = False
                document = application.Documents.Open(
                    str(native_source), False, True, False
                )
                document.ExportAsFixedFormat(str(native_destination), 17)
        finally:
            if document is not None:
                try:
                    document.Close()
                except Exception:
                    pass
            if application is not None:
                try:
                    application.Quit()
                except Exception:
                    pass
            pythoncom.CoUninitialize()

    native_io.bridge_file(
        source,
        destination,
        export,
        output_kind="pdf",
        preserve_source_context=True,
    )
    validate_pdf(destination)


def validate_pdf(path: str | Path) -> None:
    pdf = Path(path).resolve()
    try:
        native_io.validate_native_output(pdf, "pdf")
    except native_io.NativeIOError as exc:
        raise RuntimeError(f"Office PDF preview is invalid: {pdf}") from exc
