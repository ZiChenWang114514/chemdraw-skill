"""ASCII-only staging for native ChemDraw and Office automation."""

from __future__ import annotations

from contextlib import contextmanager
import ctypes
import json
import os
from pathlib import Path
import re
import shutil
import struct
import tempfile
from typing import Any, Callable, Iterator, Sequence
import xml.etree.ElementTree as ET


class NativeIOError(RuntimeError):
    """Native automation failure with a stable public error code."""

    def __init__(self, error_code: str, message: str):
        super().__init__(message)
        self.error_code = error_code
        self.public_message = message


def _ascii(path: Path) -> bool:
    return str(path).isascii()


def normalize_cdxml_staging(path: Path) -> None:
    """Normalize only a staged XML declaration; preserve document content and source."""
    if path.suffix.lower() != '.cdxml':
        return
    data = path.read_bytes()
    match = re.match(br'((?:\xef\xbb\xbf)?<\?xml\s[^?]*encoding\s*=\s*[\x22\x27])utf-?8([\x22\x27][^?]*\?>)', data, re.I)
    if match and b'encoding="UTF-8"' not in match.group(0):
        data.decode('utf-8')
        path.write_bytes(match.group(1) + b'UTF-8' + match.group(2) + data[match.end():])


def _windows_short_path(path: Path) -> Path | None:
    if os.name != "nt" or not path.exists():
        return None
    try:
        size = ctypes.windll.kernel32.GetShortPathNameW(str(path), None, 0)
        if not size:
            return None
        buffer = ctypes.create_unicode_buffer(size)
        if not ctypes.windll.kernel32.GetShortPathNameW(str(path), buffer, size):
            return None
        candidate = Path(buffer.value)
        return candidate if _ascii(candidate) else None
    except (AttributeError, OSError):
        return None


def _candidate_roots() -> Iterator[Path]:
    configured = os.environ.get("CHEMDRAW_NATIVE_TEMP")
    if configured:
        yield Path(configured).expanduser()
    yield Path(tempfile.gettempdir())
    for variable, suffix in (("SystemRoot", "Temp"), ("WINDIR", "Temp")):
        value = os.environ.get(variable)
        if value:
            yield Path(value) / suffix
    public = os.environ.get("PUBLIC")
    if public:
        yield Path(public) / "Documents"


def _writable_ascii_root() -> Path:
    seen: set[str] = set()
    for raw in _candidate_roots():
        candidates = [raw]
        short = _windows_short_path(raw)
        if short is not None:
            candidates.append(short)
        for candidate in candidates:
            key = os.path.normcase(str(candidate))
            if key in seen or not _ascii(candidate):
                continue
            seen.add(key)
            try:
                candidate.mkdir(parents=True, exist_ok=True)
                probe = candidate / f"cdx-probe-{os.getpid()}.tmp"
                with probe.open("xb") as handle:
                    handle.write(b"ok")
                probe.unlink()
                absolute = candidate.absolute()
                if _ascii(absolute):
                    return absolute
            except OSError:
                continue
    raise NativeIOError(
        "native_ascii_workspace_unavailable",
        "No writable ASCII temporary directory is available for native automation",
    )


@contextmanager
def ascii_workspace(prefix: str = "cdx-") -> Iterator[Path]:
    root = _writable_ascii_root()
    if not prefix.isascii():
        prefix = "cdx-"
    workspace = Path(tempfile.mkdtemp(prefix=prefix, dir=root))
    try:
        if not _ascii(workspace):
            raise NativeIOError(
                "native_ascii_workspace_unavailable",
                "Native automation workspace path is not ASCII",
            )
        yield workspace
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


@contextmanager
def ascii_inputs(sources: Sequence[str | Path]) -> Iterator[list[Path]]:
    originals = [Path(source).expanduser().resolve() for source in sources]
    if any(not source.is_file() for source in originals):
        missing = next(source for source in originals if not source.is_file())
        raise FileNotFoundError(f"Native input does not exist: {missing}")
    with ascii_workspace() as workspace:
        native_paths = []
        for index, source in enumerate(originals, start=1):
            suffix = source.suffix.lower() if source.suffix.isascii() else ".bin"
            native = workspace / f"input_{index:04d}{suffix}"
            shutil.copy2(source, native)
            normalize_cdxml_staging(native)
            native_paths.append(native)
        yield native_paths


@contextmanager
def ascii_input_directory(
    source: str | Path,
    *,
    suffixes: Sequence[str] = (".cdxml", ".cdx", ".csv", ".rxn"),
) -> Iterator[tuple[Path, dict[str, str]]]:
    original = Path(source).expanduser().resolve()
    if not original.is_dir():
        raise FileNotFoundError(f"Native input directory does not exist: {original}")
    allowed = {suffix.lower() for suffix in suffixes}
    with ascii_workspace(prefix="cdx-dir-") as workspace:
        native_dir = workspace / "inputs"
        native_dir.mkdir()
        replacements = {os.path.normcase(str(native_dir)): str(original)}
        for index, item in enumerate(sorted(original.iterdir()), start=1):
            if item.is_file() and item.suffix.lower() in allowed:
                suffix = item.suffix.lower()
                native_item = native_dir / f"input_{index:04d}{suffix}"
                shutil.copy2(item, native_item)
                normalize_cdxml_staging(native_item)
                replacements[os.path.normcase(str(native_item))] = str(item.resolve())
        yield native_dir, replacements


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def validate_native_output(path: str | Path, kind: str | None = None) -> Path:
    output = Path(path)
    if not output.is_file() or output.stat().st_size == 0:
        raise NativeIOError(
            "native_output_missing", "Native automation did not create its output"
        )
    normalized = (kind or output.suffix.lstrip(".")).lower()
    try:
        if normalized == "png":
            from PIL import Image

            with Image.open(output) as image:
                image.verify()
        elif normalized in {"svg", "cdxml"}:
            root = ET.parse(output).getroot()
            expected = "svg" if normalized == "svg" else "CDXML"
            if _local_name(root.tag) != expected:
                raise ValueError(f"expected {expected} root")
        elif normalized == "cdx":
            data = output.read_bytes()
            if len(data) < 16 or data[:8] != b"VjCD0100":
                raise ValueError("invalid CDX header")
        elif normalized == "emf":
            if not _is_structurally_valid_emf(output.read_bytes()):
                raise ValueError("invalid EMF signature")
        elif normalized == "pdf":
            data = output.read_bytes()
            if not _is_structurally_valid_pdf(data):
                raise ValueError("invalid or truncated PDF")
    except NativeIOError:
        raise
    except Exception as exc:
        raise NativeIOError(
            "native_output_invalid",
            f"Native automation created an invalid {normalized or 'output'} file",
        ) from exc
    return output


def _rewrite_paths(value: Any, replacements: dict[str, str]) -> Any:
    if isinstance(value, Path):
        replacement = replacements.get(os.path.normcase(str(value)))
        return Path(replacement) if replacement is not None else value
    if isinstance(value, os.PathLike):
        replacement = replacements.get(os.path.normcase(os.fspath(value)))
        return replacement if replacement is not None else value
    if isinstance(value, str):
        return replacements.get(os.path.normcase(value), value)
    if isinstance(value, list):
        return [_rewrite_paths(item, replacements) for item in value]
    if isinstance(value, tuple):
        return tuple(_rewrite_paths(item, replacements) for item in value)
    if isinstance(value, dict):
        return {key: _rewrite_paths(item, replacements) for key, item in value.items()}
    return value


def bridge_file(
    source: str | Path,
    destination: str | Path,
    operation: Callable[[Path, Path], Any],
    *,
    output_kind: str | None = None,
    preserve_source_context: bool = False,
) -> Any:
    source_path = Path(source).expanduser().resolve()
    destination_path = Path(destination).expanduser().resolve()
    if not source_path.is_file():
        raise FileNotFoundError(f"Native input does not exist: {source_path}")
    if destination_path.exists():
        raise FileExistsError(f"Refusing to overwrite native output: {destination_path}")
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    suffix = source_path.suffix if source_path.suffix.isascii() else ".bin"
    output_suffix = destination_path.suffix if destination_path.suffix.isascii() else ".bin"
    with ascii_workspace() as workspace:
        native_parent = workspace
        if preserve_source_context:
            native_parent = workspace / "context"

            def ignore_workspace(directory: str, names: list[str]) -> set[str]:
                current = Path(directory).resolve()
                ignored = set()
                for name in names:
                    candidate = (current / name).resolve()
                    try:
                        workspace.resolve().relative_to(candidate)
                    except ValueError:
                        continue
                    ignored.add(name)
                return ignored

            shutil.copytree(
                source_path.parent,
                native_parent,
                ignore=ignore_workspace,
            )
        native_source = native_parent / f"input{suffix.lower()}"
        native_destination = workspace / f"output{output_suffix.lower()}"
        shutil.copy2(source_path, native_source)
        normalize_cdxml_staging(native_source)
        result = operation(native_source, native_destination)
        if not native_destination.exists():
            raise NativeIOError(
                "native_saveas_silent_failure",
                "Native automation returned without creating its output",
            )
        validate_native_output(native_destination, output_kind)
        _publish_exclusive(native_destination, destination_path, output_kind)
        return _rewrite_paths(
            result,
            {
                os.path.normcase(str(native_source)): str(source_path),
                os.path.normcase(str(native_destination)): str(destination_path),
            },
        )


def _validate_cdx_bytes(data: Any) -> bytes:
    if not isinstance(data, (bytes, bytearray, memoryview)):
        raise NativeIOError("native_output_invalid", "ChemDraw returned invalid CDX data")
    value = bytes(data)
    if len(value) < 16 or not value.startswith(b"VjCD0100"):
        raise NativeIOError("native_output_invalid", "ChemDraw returned invalid CDX data")
    return value


def _validate_emf_bytes(data: Any) -> bytes:
    if not isinstance(data, (bytes, bytearray, memoryview)) or not data:
        raise NativeIOError("native_output_invalid", "ChemDraw returned invalid EMF data")
    value = bytes(data)
    if not _is_structurally_valid_emf(value):
        raise NativeIOError("native_output_invalid", "ChemDraw returned invalid EMF data")
    return value


def _is_structurally_valid_emf(data: bytes) -> bool:
    if len(data) < 88:
        return False
    try:
        record_type, header_size = struct.unpack_from("<II", data, 0)
        signature = struct.unpack_from("<I", data, 40)[0]
        version, byte_count, record_count = struct.unpack_from("<III", data, 44)
        handle_count = struct.unpack_from("<H", data, 56)[0]
    except struct.error:
        return False
    return (
        record_type == 1
        and 88 <= header_size <= len(data)
        and signature == 0x464D4520
        and version >= 0x00010000
        and byte_count == len(data)
        and record_count >= 1
        and handle_count >= 1
    )


def _is_structurally_valid_pdf(data: bytes) -> bool:
    if len(data) < 64 or not data.startswith(b"%PDF-"):
        return False
    tail = data[-4096:]
    if not re.search(rb"startxref\s+\d+\s+%%EOF\s*$", tail):
        return False
    if not re.search(rb"/Type\s*/Catalog\b", data):
        return False
    return b"xref" in data or re.search(rb"/Type\s*/XRef\b", data) is not None


def _publish_exclusive(source: Path, destination: Path, kind: str | None) -> None:
    handle = tempfile.NamedTemporaryFile(
        prefix=".cdx-native-",
        suffix=destination.suffix,
        dir=destination.parent,
        delete=False,
    )
    staging = Path(handle.name)
    try:
        with handle, source.open("rb") as input_handle:
            shutil.copyfileobj(input_handle, handle)
            handle.flush()
            os.fsync(handle.fileno())
        validate_native_output(staging, kind)
        try:
            os.link(staging, destination)
        except FileExistsError:
            raise FileExistsError(f"Refusing to overwrite native output: {destination}")
        except OSError:
            created = False
            try:
                with destination.open("xb") as output_handle, staging.open("rb") as input_handle:
                    created = True
                    shutil.copyfileobj(input_handle, output_handle)
                    output_handle.flush()
                    os.fsync(output_handle.fileno())
            except Exception:
                if created:
                    destination.unlink(missing_ok=True)
                raise
    finally:
        staging.unlink(missing_ok=True)


def batch_convert_cdxml(
    sources: Sequence[str | Path],
    batch_convert: Callable[[list[str]], Any],
) -> list[dict[str, Any]]:
    originals = [Path(source).expanduser().resolve() for source in sources]
    if any(not source.is_file() for source in originals):
        missing = next(source for source in originals if not source.is_file())
        raise FileNotFoundError(f"Native input does not exist: {missing}")
    with ascii_inputs(originals) as native_paths:
        converted = batch_convert([str(path) for path in native_paths])
        if not isinstance(converted, list) or len(converted) != len(originals):
            raise NativeIOError(
                "native_output_missing", "ChemDraw did not convert every CDXML input"
            )
        normalized = []
        for source, item in zip(originals, converted):
            if not isinstance(item, dict):
                raise NativeIOError(
                    "native_output_invalid", "ChemDraw returned an invalid conversion result"
                )
            record = dict(item)
            record["cdx_data"] = _validate_cdx_bytes(record.get("cdx_data"))
            record["emf_data"] = _validate_emf_bytes(record.get("emf_data"))
            record["path"] = str(source)
            record["name"] = source.stem
            normalized.append(record)
        return normalized


def convert_cdx_bytes_to_cdxml(
    cdx_data: bytes,
    converter: Callable[..., Any],
) -> str:
    _validate_cdx_bytes(cdx_data)
    with ascii_workspace() as workspace:
        native_source = workspace / "input.cdx"
        native_destination = workspace / "output.cdxml"
        native_source.write_bytes(cdx_data)
        converter(
            str(native_source), str(native_destination), method="auto"
        )
        if not native_destination.exists():
            raise NativeIOError(
                "native_saveas_silent_failure",
                "Native CDX conversion returned without creating its output",
            )
        validate_native_output(native_destination, "cdxml")
        return native_destination.read_text(encoding="utf-8")


def write_shadow_manifest(
    manifest: str | Path,
    workspace: str | Path,
) -> tuple[Path, list[Path]]:
    manifest_path = Path(manifest).resolve()
    root = Path(workspace).resolve()
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    copied: list[Path] = []
    index = 0

    def rewrite(value: Any) -> Any:
        nonlocal index
        if isinstance(value, dict):
            result = {key: rewrite(item) for key, item in value.items()}
            if str(value.get("type", "")).lower() == "cdxml":
                raw = value.get("file")
                relative = Path(str(raw))
                if relative.is_absolute() or relative.drive or ".." in relative.parts:
                    raise ValueError(f"CDXML manifest path is unsafe: {raw}")
                source = (manifest_path.parent / relative).resolve()
                try:
                    source.relative_to(manifest_path.parent.resolve())
                except ValueError as exc:
                    raise ValueError(f"CDXML manifest path is unsafe: {raw}") from exc
                if not source.is_file() or source.suffix.lower() != ".cdxml":
                    raise FileNotFoundError(f"CDXML manifest input does not exist: {source}")
                index += 1
                target = root / f"structure_{index:04d}.cdxml"
                shutil.copy2(source, target)
                result["file"] = target.name
                copied.append(target)
            return result
        if isinstance(value, list):
            return [rewrite(item) for item in value]
        return value

    rewritten = rewrite(data)
    shadow = root / "manifest.json"
    shadow.write_text(json.dumps(rewritten, indent=2), encoding="utf-8")
    return shadow, copied


def rewrite_json_paths(path: str | Path, replacements: dict[str, str]) -> None:
    target = Path(path)
    data = json.loads(target.read_text(encoding="utf-8"))
    rewritten = _rewrite_paths(data, replacements)
    target.write_text(
        json.dumps(rewritten, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
