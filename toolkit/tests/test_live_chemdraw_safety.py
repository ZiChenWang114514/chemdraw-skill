"""The live ChemDraw bridge must never silently alter the user's open document."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from cdxml_toolkit.mcp_runtime import live_chemdraw

CDXML = '<?xml version="1.0"?><CDXML><page/></CDXML>'


@pytest.fixture(autouse=True)
def _stage(tmp_path, monkeypatch):
    monkeypatch.setattr(live_chemdraw, "_LIVE_STAGE_DIR", tmp_path / "stage")
    monkeypatch.setattr(live_chemdraw, "_extract_smiles_from_objects", lambda *a, **k: "")


class FakeObjects:
    def __init__(self, fail=False):
        self.data = None
        self.fail = fail

    def SetData(self, fmt, value):
        if self.fail:
            raise RuntimeError("SetData refused")
        self.data = (fmt, value)


class FakeDoc:
    def __init__(self, name, fail=False):
        self.Name = name
        self.Objects = FakeObjects(fail)

    def Activate(self):
        pass


class FakeDocs:
    def __init__(self, add_fails=False, open_result="doc"):
        self.added = []
        self.opened = []
        self.add_fails = add_fails
        self.open_result = open_result

    def Add(self):
        doc = FakeDoc("New", fail=self.add_fails)
        self.added.append(doc)
        return doc

    def Open(self, path):
        self.opened.append(path)
        return FakeDoc("Opened") if self.open_result == "doc" else None


def _run(monkeypatch, docs, **kw):
    user_doc = FakeDoc("Mine.cdxml")
    app = SimpleNamespace(ActiveDocument=user_doc, Documents=docs)
    monkeypatch.setattr(live_chemdraw, "_get_active_com_application", lambda: app)
    return user_doc, live_chemdraw.live_chemdraw_session("insert_cdxml", cdxml=CDXML, **kw)


def test_insert_never_writes_into_the_active_document(monkeypatch):
    docs = FakeDocs()
    user_doc, result = _run(monkeypatch, docs)
    assert user_doc.Objects.data is None
    assert docs.added and docs.added[0].Objects.data == ("text/xml", CDXML)
    assert result["ok"] is True and result["inserted"] is True


def test_failed_insert_reports_failure_with_a_reason(monkeypatch):
    docs = FakeDocs(add_fails=True, open_result=None)
    user_doc, result = _run(monkeypatch, docs)
    assert user_doc.Objects.data is None
    assert result["ok"] is False and result["inserted"] is False
    assert result["reason"]


def test_fallback_opens_a_staged_copy_not_the_output_artifact(monkeypatch, tmp_path):
    docs = FakeDocs(add_fails=True)
    out = tmp_path / "out" / "mine.cdxml"
    _, result = _run(monkeypatch, docs, output_path=str(out))
    assert result["ok"] is True
    assert docs.opened and docs.opened[0] != result["output_path"]
    assert "stage" in docs.opened[0]


def test_macos_read_snapshot_is_persistent_and_saves_back(monkeypatch):
    from cdxml_toolkit.chemdraw import mac_automation

    scripts = []

    def fake_run(script, timeout_seconds=0):
        scripts.append(script)
        for line in script.splitlines():
            if "ChemDraw XML" in line:
                path = line.split('POSIX file "')[1].split('"')[0]
                open(path, "w", encoding="utf-8").write(CDXML)
        return "Mine.cdxml|CCO"

    monkeypatch.setattr(mac_automation, "find_application", lambda: "/App")
    monkeypatch.setattr(mac_automation, "bundle_identifier", lambda b: "com.x")
    monkeypatch.setattr(mac_automation, "is_running", lambda b: True)
    monkeypatch.setattr(mac_automation, "run_applescript", fake_run)
    result = live_chemdraw._macos_session("read_active", cdxml="", smiles="", output_path="")
    assert result["ok"] is True
    script = scripts[0]
    # The document is saved back to its own file after the snapshot, so it is not re-pointed.
    assert script.index("ChemDraw XML") < script.index("save d in (POSIX file origPath)")
    # The snapshot persists (an untitled document may stay attached to it).
    from pathlib import Path

    assert result["snapshot_path"] and Path(result["snapshot_path"]).is_file()
