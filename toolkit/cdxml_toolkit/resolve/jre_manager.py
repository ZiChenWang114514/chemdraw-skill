"""Discover or explicitly install a Java runtime used by OPSIN."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import tempfile
from typing import Optional
import urllib.request
import zipfile


_JRE_BASE = Path.home() / ".cdxml-toolkit" / "jre"
_ADOPTIUM_URL = (
    "https://api.adoptium.net/v3/binary/latest/21/ga/windows/x64/jre/"
    "hotspot/normal/eclipse?project=jdk"
)
_MAX_ARCHIVE_BYTES = 128 * 1024 * 1024
_MAX_EXTRACTED_BYTES = 768 * 1024 * 1024
_java_exe: Optional[str] = None


def _find_system_java() -> Optional[str]:
    java = shutil.which("java")
    if java:
        return java
    java_home = os.environ.get("JAVA_HOME")
    if java_home:
        for name in ("java.exe", "java"):
            candidate = Path(java_home) / "bin" / name
            if candidate.is_file():
                return str(candidate)
    return None


def _find_java_under(root: Path) -> Optional[str]:
    if not root.is_dir():
        return None
    for executable in ("java.exe", "java"):
        for candidate in root.glob(f"**/bin/{executable}"):
            if candidate.is_file():
                return str(candidate.resolve())
    return None


def _find_extracted_java() -> Optional[str]:
    return _find_java_under(_JRE_BASE)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _safe_extract(archive: Path, destination: Path) -> None:
    destination = destination.resolve()
    total = 0
    with zipfile.ZipFile(archive) as bundle:
        for member in bundle.infolist():
            total += max(0, member.file_size)
            if total > _MAX_EXTRACTED_BYTES:
                raise ValueError("JRE archive expands beyond the configured size limit")
            mode = member.external_attr >> 16
            if stat.S_ISLNK(mode):
                raise ValueError("JRE archive contains a symbolic link")
            target = (destination / member.filename).resolve()
            try:
                target.relative_to(destination)
            except ValueError as exc:
                raise ValueError("JRE archive contains an unsafe path") from exc
        bundle.extractall(destination)


def install_jre_archive(
    archive_path: str | os.PathLike[str],
    *,
    expected_sha256: str | None = None,
    source: str = "local",
) -> Optional[str]:
    """Verify and install a JRE ZIP without modifying an existing installation."""
    archive = Path(archive_path).expanduser().resolve()
    if not archive.is_file():
        raise FileNotFoundError(f"JRE archive does not exist: {archive}")
    if archive.stat().st_size > _MAX_ARCHIVE_BYTES:
        raise ValueError("JRE archive exceeds the configured size limit")
    actual_hash = _sha256(archive)
    if expected_sha256 and actual_hash.lower() != expected_sha256.strip().lower():
        raise ValueError("JRE archive SHA-256 does not match the approved value")

    _JRE_BASE.mkdir(parents=True, exist_ok=True)
    destination = _JRE_BASE / f"temurin-{actual_hash[:16]}"
    if destination.exists():
        return _find_java_under(destination)
    with tempfile.TemporaryDirectory(prefix="cdxml-jre-", dir=_JRE_BASE.parent) as temp_dir:
        staged = Path(temp_dir) / "runtime"
        staged.mkdir()
        _safe_extract(archive, staged)
        java = _find_java_under(staged)
        if not java:
            raise ValueError("JRE archive does not contain a Java executable")
        os.replace(staged, destination)
    manifest = {
        "source": source,
        "sha256": actual_hash,
        "archive_bytes": archive.stat().st_size,
    }
    (destination / "cdxml-toolkit-install.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8", newline="\n"
    )
    return _find_java_under(destination)


def _configured_archive() -> tuple[Path, str | None] | None:
    value = os.environ.get("CDXML_TOOLKIT_JRE_ZIP")
    if not value:
        return None
    return Path(value).expanduser(), os.environ.get("CDXML_TOOLKIT_JRE_SHA256")


def _download_jre() -> Optional[str]:
    _JRE_BASE.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(
        _ADOPTIUM_URL,
        headers={"User-Agent": "cdxml-toolkit-community/0.7"},
    )
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            prefix="cdxml-jre-download-",
            suffix=".zip",
            delete=False,
            dir=_JRE_BASE.parent,
        ) as target:
            temporary = Path(target.name)
            with urllib.request.urlopen(request, timeout=120) as response:
                expected = response.headers.get("X-Checksum-Sha256")
                written = 0
                while True:
                    block = response.read(1024 * 1024)
                    if not block:
                        break
                    written += len(block)
                    if written > _MAX_ARCHIVE_BYTES:
                        raise ValueError("JRE download exceeds the configured size limit")
                    target.write(block)
        return install_jre_archive(
            temporary,
            expected_sha256=expected,
            source="Adoptium API",
        )
    except (OSError, ValueError, zipfile.BadZipFile):
        return None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def get_java(download: bool = True) -> Optional[str]:
    """Return Java from the system, a verified installation, or an approved download."""
    global _java_exe
    if _java_exe is not None:
        return _java_exe
    _java_exe = _find_system_java() or _find_extracted_java()
    if _java_exe:
        return _java_exe
    configured = _configured_archive()
    if configured:
        archive, expected = configured
        try:
            _java_exe = install_jre_archive(
                archive,
                expected_sha256=expected,
                source="CDXML_TOOLKIT_JRE_ZIP",
            )
        except (OSError, ValueError, zipfile.BadZipFile):
            _java_exe = None
        if _java_exe:
            return _java_exe
    if download:
        _java_exe = _download_jre()
    return _java_exe


def ensure_java_on_path(download: bool = True) -> bool:
    """Discover Java and expose its executable directory to subprocesses."""
    java = get_java(download=download)
    if not java:
        return False
    java_bin_dir = os.path.dirname(java)
    path = os.environ.get("PATH", "")
    if java_bin_dir not in path.split(os.pathsep):
        os.environ["PATH"] = java_bin_dir + os.pathsep + path
    os.environ["JAVA_HOME"] = os.path.dirname(java_bin_dir)
    return True
