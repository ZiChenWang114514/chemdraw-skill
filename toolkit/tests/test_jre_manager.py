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


def _fake_jdk(root: Path) -> Path:
    java = root / "Contents" / "Home" / "bin" / "java"
    java.parent.mkdir(parents=True)
    java.write_bytes(b"")
    return java


def test_macos_java_stub_resolves_to_real_jdk(tmp_path, monkeypatch):
    java = _fake_jdk(tmp_path / "temurin.jdk")
    monkeypatch.setattr(jre_manager.sys, "platform", "darwin")
    monkeypatch.setattr(jre_manager.shutil, "which", lambda _name: "/usr/bin/java")
    monkeypatch.setattr(jre_manager, "_macos_java_home", lambda: str(java.parents[1]))

    assert jre_manager._find_system_java() == str(java)


def test_macos_java_stub_without_jdk_is_not_java(tmp_path, monkeypatch):
    monkeypatch.setattr(jre_manager.sys, "platform", "darwin")
    monkeypatch.setattr(jre_manager.shutil, "which", lambda _name: "/usr/bin/java")
    monkeypatch.setattr(jre_manager, "_macos_java_home", lambda: None)
    monkeypatch.delenv("JAVA_HOME", raising=False)

    assert jre_manager._find_system_java() is None


def test_java_home_never_points_at_the_macos_stub(tmp_path, monkeypatch):
    java = _fake_jdk(tmp_path / "temurin.jdk")
    monkeypatch.setattr(jre_manager.sys, "platform", "darwin")
    monkeypatch.setattr(jre_manager.shutil, "which", lambda _name: "/usr/bin/java")
    monkeypatch.setattr(jre_manager, "_macos_java_home", lambda: str(java.parents[1]))
    monkeypatch.setattr(jre_manager, "_java_exe", None)
    monkeypatch.setenv("PATH", "/usr/bin")
    monkeypatch.delenv("JAVA_HOME", raising=False)

    assert jre_manager.ensure_java_on_path(download=False)

    assert jre_manager.os.environ["JAVA_HOME"] == str(java.parents[1])


def test_windows_jre_download_is_skipped_off_windows(monkeypatch):
    monkeypatch.setattr(jre_manager.os, "name", "posix")
    monkeypatch.setattr(
        jre_manager.urllib.request,
        "urlopen",
        lambda *_a, **_k: pytest.fail("must not download a Windows JRE"),
    )

    assert jre_manager._download_jre() is None
