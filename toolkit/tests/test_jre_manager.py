from __future__ import annotations

import hashlib
from pathlib import Path
import zipfile

import pytest

from cdxml_toolkit.resolve import jre_manager


def _archive(path: Path, member: str = "jdk/bin/java.exe") -> str:
    with zipfile.ZipFile(path, "w") as bundle:
        bundle.writestr(member, b"java fixture")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_verified_local_jre_archive_is_published_with_manifest(tmp_path, monkeypatch):
    archive = tmp_path / "runtime.zip"
    digest = _archive(archive)
    monkeypatch.setattr(jre_manager, "_JRE_BASE", tmp_path / "installed")

    java = jre_manager.install_jre_archive(
        archive, expected_sha256=digest, source="fixture"
    )

    assert java is not None
    assert Path(java).read_bytes() == b"java fixture"
    manifest = Path(java).parents[2] / "cdxml-toolkit-install.json"
    assert digest in manifest.read_text(encoding="utf-8")


def test_jre_archive_rejects_hash_mismatch_without_installation(tmp_path, monkeypatch):
    archive = tmp_path / "runtime.zip"
    _archive(archive)
    destination = tmp_path / "installed"
    monkeypatch.setattr(jre_manager, "_JRE_BASE", destination)

    with pytest.raises(ValueError, match="SHA-256"):
        jre_manager.install_jre_archive(archive, expected_sha256="0" * 64)

    assert not destination.exists()


def test_jre_archive_rejects_parent_path(tmp_path, monkeypatch):
    archive = tmp_path / "runtime.zip"
    _archive(archive, "../outside/java.exe")
    monkeypatch.setattr(jre_manager, "_JRE_BASE", tmp_path / "installed")

    with pytest.raises(ValueError, match="unsafe path"):
        jre_manager.install_jre_archive(archive)

    assert not (tmp_path / "outside").exists()
