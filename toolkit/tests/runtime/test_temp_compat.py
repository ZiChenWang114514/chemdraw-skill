"""Temp folders stay usable under a sandbox that cannot write into owner-only folders."""
import os
import tempfile

from cdxml_toolkit.mcp_runtime import temp_compat


def test_a_usable_mkdtemp_is_left_alone(monkeypatch):
    original = tempfile.mkdtemp
    assert temp_compat.ensure_usable_mkdtemp(is_usable=lambda: True) is False
    assert tempfile.mkdtemp is original


def test_an_unusable_mkdtemp_is_replaced_by_one_that_inherits_the_parent_permissions(monkeypatch, tmp_path):
    monkeypatch.setattr(tempfile, "mkdtemp", tempfile.mkdtemp)  # restored after the test
    assert temp_compat.ensure_usable_mkdtemp(is_usable=lambda: False) is True
    first = tempfile.mkdtemp(prefix="cdx-", suffix="-x", dir=str(tmp_path))
    second = tempfile.mkdtemp(prefix="cdx-", suffix="-x", dir=str(tmp_path))
    assert first != second
    for path in (first, second):
        assert os.path.isdir(path) and os.path.dirname(path) == str(tmp_path)
        assert os.path.basename(path).startswith("cdx-") and path.endswith("-x")
    with tempfile.TemporaryDirectory(dir=str(tmp_path)) as folder:
        assert os.path.isdir(folder)
    assert not os.path.exists(folder)


def test_the_probe_reports_a_folder_that_refuses_writes(monkeypatch):
    def refuse(file, *args, **kwargs):
        raise PermissionError(13, "Permission denied", str(file))

    monkeypatch.setattr("builtins.open", refuse)
    assert temp_compat.mkdtemp_is_usable() is False


def test_the_probe_passes_on_an_ordinary_temp_folder():
    assert temp_compat.mkdtemp_is_usable() is True
