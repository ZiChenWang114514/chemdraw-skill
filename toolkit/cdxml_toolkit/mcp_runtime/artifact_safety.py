"""Transactional artifact publication and integrity metadata."""

from __future__ import annotations

from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
import time
from typing import Any, Callable, Iterable, Iterator
import xml.etree.ElementTree as ET
import zipfile


def validate_input_file(
    path: str | Path,
    *,
    suffixes: tuple[str, ...] | None = None,
) -> Path:
    source = Path(path).expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(f"Input file does not exist: {source}")
    if suffixes and source.suffix.lower() not in suffixes:
        raise ValueError(f"Input must use one of {suffixes}: {source}")
    return source


def _available_path(candidate: Path) -> Path:
    if not candidate.exists():
        return candidate
    index = 2
    while True:
        alternative = candidate.with_name(
            f"{candidate.stem}_{index}{candidate.suffix}"
        )
        if not alternative.exists():
            return alternative
        index += 1


def resolve_destination(
    *,
    source: str | Path | None,
    output_path: str | Path | None,
    tag: str,
    suffix: str,
    base_dir: str | Path | None = None,
) -> Path:
    source_path = Path(source).expanduser().resolve() if source is not None else None
    if output_path is not None:
        destination = Path(output_path).expanduser().resolve()
        if destination.exists() or destination == source_path:
            raise ValueError(f"Refusing to overwrite an existing file: {destination}")
        if destination.suffix.lower() != suffix.lower():
            raise ValueError(f"output_path must end in {suffix}: {destination}")
    else:
        directory = (
            source_path.parent
            if source_path is not None
            else Path(base_dir or tempfile.gettempdir()).expanduser().resolve()
        )
        filename = (
            f"{source_path.stem}_{tag}{suffix}"
            if source_path is not None
            else f"{tag}{suffix}"
        )
        candidate = directory / filename
        destination = _available_path(candidate)
    destination.parent.mkdir(parents=True, exist_ok=True)
    return destination


def resolve_directory_destination(
    *,
    source: str | Path,
    output_dir: str | Path | None,
    tag: str,
) -> Path:
    source_path = Path(source).expanduser().resolve()
    if output_dir is not None:
        destination = Path(output_dir).expanduser().resolve()
        if destination.exists():
            raise ValueError(f"Refusing to overwrite an existing directory: {destination}")
    else:
        candidate = source_path.parent / f"{source_path.stem}_{tag}"
        destination = candidate
        index = 2
        while destination.exists():
            destination = candidate.with_name(f"{candidate.name}_{index}")
            index += 1
    destination.parent.mkdir(parents=True, exist_ok=True)
    return destination


def validate_artifact(path: str | Path) -> Path:
    artifact = Path(path).resolve()
    if not artifact.is_file() or artifact.stat().st_size == 0:
        raise RuntimeError(f"Expected output was not created: {artifact}")
    suffix = artifact.suffix.lower()
    try:
        if suffix == ".json":
            json.loads(artifact.read_text(encoding="utf-8"))
        elif suffix in {".cdxml", ".svg"}:
            root = ET.parse(artifact).getroot()
            expected = "CDXML" if suffix == ".cdxml" else "svg"
            if root.tag.rsplit("}", 1)[-1].lower() != expected.lower():
                raise ValueError(f"expected {expected} root, found {root.tag}")
        elif suffix == ".cdx":
            if not artifact.read_bytes().startswith(b"VjCD"):
                raise ValueError("CDX header is missing")
        elif suffix in {".pptx", ".docx", ".xlsx"}:
            with zipfile.ZipFile(artifact, "r") as package:
                corrupt = package.testzip()
                if corrupt:
                    raise ValueError(f"corrupt OOXML part: {corrupt}")
    except (OSError, UnicodeError, ValueError, ET.ParseError, zipfile.BadZipFile) as exc:
        raise RuntimeError(f"Invalid generated output {artifact}: {exc}") from exc
    return artifact


@contextmanager
def staging_file(destination: str | Path) -> Iterator[Path]:
    destination_path = Path(destination).resolve()
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix=f".{destination_path.stem}-", dir=destination_path.parent
    ) as temporary_directory:
        yield Path(temporary_directory) / destination_path.name


@contextmanager
def staging_directory(destination: str | Path) -> Iterator[Path]:
    destination_path = Path(destination).resolve()
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix=f".{destination_path.name}-", dir=destination_path.parent
    ) as temporary_directory:
        stage = Path(temporary_directory) / "payload"
        stage.mkdir()
        yield stage


def publish_file(staged: str | Path, destination: str | Path) -> None:
    source = Path(staged).resolve()
    target = Path(destination).resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    published = False
    try:
        os.link(source, target)
        published = True
    except FileExistsError as exc:
        raise ValueError(f"Refusing to overwrite an existing file: {target}") from exc
    except OSError:
        created = False
        try:
            with source.open("rb") as source_handle, target.open("xb") as target_handle:
                created = True
                shutil.copyfileobj(source_handle, target_handle)
                target_handle.flush()
                os.fsync(target_handle.fileno())
            published = True
        except FileExistsError as exc:
            raise ValueError(f"Refusing to overwrite an existing file: {target}") from exc
        except Exception:
            if created:
                target.unlink(missing_ok=True)
            raise
    try:
        source.unlink(missing_ok=True)
    except Exception as exc:
        if published:
            try:
                target.unlink(missing_ok=True)
            except Exception as rollback_exc:
                raise RuntimeError(
                    f"Failed to roll back published artifact {target}: {rollback_exc}"
                ) from exc
        raise


def publish_files(staged_outputs: Iterable[tuple[Path, Path]]) -> None:
    outputs = [(Path(source), Path(target)) for source, target in staged_outputs]
    for _, target in outputs:
        if target.exists():
            raise ValueError(f"Refusing to overwrite an existing file: {target}")
    committed: list[Path] = []
    try:
        for source, target in outputs:
            publish_file(source, target)
            committed.append(target)
    except Exception:
        for target in committed:
            target.unlink(missing_ok=True)
        raise


def publish_directory(staged: str | Path, destination: str | Path) -> None:
    source = Path(staged).resolve()
    target = Path(destination).resolve()
    if target.exists():
        raise ValueError(f"Refusing to overwrite an existing directory: {target}")
    for attempt in range(6):
        try:
            source.rename(target)
            return
        except FileExistsError as exc:
            raise ValueError(
                f"Refusing to overwrite an existing directory: {target}"
            ) from exc
        except PermissionError as exc:
            if target.exists():
                raise ValueError(
                    f"Refusing to overwrite an existing directory: {target}"
                ) from exc
            if attempt == 5:
                raise
            time.sleep(min(0.05 * (2**attempt), 0.5))
        except OSError as exc:
            if target.exists():
                raise ValueError(
                    f"Refusing to overwrite an existing directory: {target}"
                ) from exc
            raise


def artifact_record(path: str | Path) -> dict[str, Any]:
    artifact = validate_artifact(path)
    digest = hashlib.sha256()
    with artifact.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return {
        "path": str(artifact),
        "bytes": artifact.stat().st_size,
        "sha256": digest.hexdigest(),
    }


def artifact_records(paths: Iterable[str | Path]) -> list[dict[str, Any]]:
    seen: set[Path] = set()
    records = []
    for path in paths:
        artifact = Path(path).expanduser().resolve()
        if artifact in seen or not artifact.is_file():
            continue
        seen.add(artifact)
        records.append(artifact_record(artifact))
    return records


def paths_from_value(value: Any) -> list[Path]:
    paths: list[Path] = []
    if isinstance(value, dict):
        for child in value.values():
            paths.extend(paths_from_value(child))
    elif isinstance(value, (list, tuple, set)):
        for child in value:
            paths.extend(paths_from_value(child))
    elif isinstance(value, (str, os.PathLike)):
        try:
            candidate = Path(value).expanduser()
            if candidate.is_file():
                paths.append(candidate.resolve())
        except (OSError, ValueError):
            pass
    return paths


def with_artifacts(result: dict[str, Any], paths: Iterable[str | Path]) -> dict[str, Any]:
    enriched = dict(result)
    metadata = dict(enriched.get("metadata") or {})
    metadata["artifacts"] = artifact_records(paths)
    enriched["metadata"] = metadata
    return enriched


def rewrite_paths(value: Any, old_root: str | Path, new_root: str | Path) -> Any:
    old = Path(old_root).resolve()
    new = Path(new_root).resolve()
    if isinstance(value, dict):
        return {key: rewrite_paths(child, old, new) for key, child in value.items()}
    if isinstance(value, list):
        return [rewrite_paths(child, old, new) for child in value]
    if isinstance(value, tuple):
        return tuple(rewrite_paths(child, old, new) for child in value)
    if isinstance(value, str):
        try:
            candidate = Path(value).resolve()
            relative = candidate.relative_to(old)
        except (OSError, ValueError):
            return value
        return str(new / relative)
    return value


def stage_validate_publish(
    destination: str | Path,
    writer: Callable[[Path], Any],
    *,
    validator: Callable[[Path], Any] = validate_artifact,
) -> tuple[Any, Path]:
    target = Path(destination).resolve()
    with staging_file(target) as staged:
        result = writer(staged)
        validator(staged)
        publish_file(staged, target)
    return result, target
