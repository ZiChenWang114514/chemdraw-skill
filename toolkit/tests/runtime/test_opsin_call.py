"""OPSIN name lookups stage their input in a file no other call shares."""

from __future__ import annotations

from pathlib import Path
import tempfile

from cdxml_toolkit.resolve.opsin_call import py2opsin_private

PACKAGE = Path(__file__).resolve().parents[2] / "cdxml_toolkit"


def test_each_call_gets_its_own_input_file():
    seen = []

    def fake_py2opsin(name, tmp_fpath):
        seen.append(Path(tmp_fpath))
        Path(tmp_fpath).write_text(name, encoding="utf-8")
        return "CCO"

    assert py2opsin_private(fake_py2opsin, "ethanol") == "CCO"
    assert py2opsin_private(fake_py2opsin, "ethanol") == "CCO"
    assert seen[0] != seen[1]
    assert all(path.parent != Path(tempfile.gettempdir()) for path in seen)
    assert not any(path.exists() for path in seen)


def test_no_module_uses_the_shared_py2opsin_input_path():
    offenders = [
        str(path.relative_to(PACKAGE))
        for path in PACKAGE.rglob("*.py")
        if "py2opsin_temp_input" in path.read_text(encoding="utf-8")
    ]
    assert offenders == []
