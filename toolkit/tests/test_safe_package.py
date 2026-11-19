"""Office packages come from users and mail: every reader opens them through one bounded door."""

import re
import zipfile
from pathlib import Path

import pytest

from cdxml_toolkit.office import safe_xml

TOOLKIT = Path(safe_xml.__file__).resolve().parents[1]


def package(path, members):
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as out:
        for name, data in members.items():
            out.writestr(name, data)
    return path


def test_an_ordinary_package_opens_and_reads(tmp_path):
    source = package(tmp_path / "a.docx", {"word/document.xml": "<w/>" * 100})
    with safe_xml.open_package(source) as opened:
        assert opened.read("word/document.xml").startswith(b"<w/>")


def test_a_part_that_inflates_out_of_proportion_is_refused(tmp_path):
    source = package(tmp_path / "bomb.docx", {"word/document.xml": b"0" * (60 * 1024 * 1024)})
    with pytest.raises(safe_xml.UnsafePackage, match="word/document.xml"):
        safe_xml.open_package(source)


def test_a_package_over_the_total_size_is_refused(tmp_path, monkeypatch):
    monkeypatch.setattr(safe_xml, "MAX_PACKAGE_BYTES", 1000)
    source = package(tmp_path / "big.pptx", {"a.bin": bytes(range(256)) * 8})
    with pytest.raises(safe_xml.UnsafePackage, match="unpacks to"):
        safe_xml.open_package(source)


def test_a_package_with_too_many_parts_is_refused(tmp_path, monkeypatch):
    monkeypatch.setattr(safe_xml, "MAX_PACKAGE_MEMBERS", 3)
    source = package(tmp_path / "many.docx", {f"p{i}.xml": "<a/>" for i in range(4)})
    with pytest.raises(safe_xml.UnsafePackage, match="parts"):
        safe_xml.open_package(source)


def test_readers_of_user_packages_use_the_bounded_door():
    """No Office reader opens a user's package with a bare ZipFile."""
    bare = re.compile(r"zipfile\.ZipFile\(\s*[^,)]+(?:,\s*[\"']r[\"'])?\s*\)")
    offenders = []
    for folder in ("office", "mcp_runtime"):
        for path in sorted((TOOLKIT / folder).glob("*.py")):
            if path.name in {"safe_xml.py", "install_decimer_models.py"}:
                continue
            for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if bare.search(line):
                    offenders.append(f"{path.name}:{number}")
    assert offenders == []
