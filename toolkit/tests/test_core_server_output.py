"""The 15 compatible core tools never replace a file that already exists."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

server = pytest.importorskip("cdxml_toolkit.mcp_server.server")


def test_an_existing_file_is_kept_and_the_next_free_name_is_used(tmp_path):
    target = tmp_path / "scheme.cdxml"
    target.write_text("original", encoding="utf-8")
    result = server._write_output("new", str(target), "scheme", ".cdxml")
    assert target.read_text(encoding="utf-8") == "original"
    assert result["output_path"] == str(tmp_path / "scheme_2.cdxml")
    assert Path(result["output_path"]).read_text(encoding="utf-8") == "new"


def test_structured_results_follow_the_same_rule(tmp_path):
    target = tmp_path / "reaction.json"
    target.write_text("{}", encoding="utf-8")
    result = server._write_output({"ok": True}, str(target), "reaction", ".json")
    assert target.read_text(encoding="utf-8") == "{}"
    assert result["output_path"] == str(tmp_path / "reaction_2.json")


def test_draw_molecule_writes_its_file_once_and_keeps_an_existing_one(tmp_path):
    target = tmp_path / "ethanol.cdxml"
    target.write_text("keep me", encoding="utf-8")
    result = json.loads(server.draw_molecule({"smiles": "CCO", "name": "ethanol"}, output_path=str(target)))
    assert result["ok"] is True
    assert target.read_text(encoding="utf-8") == "keep me"
    assert result["output_path"] == str(tmp_path / "ethanol_2.cdxml")
    assert "<CDXML" in Path(result["output_path"]).read_text(encoding="utf-8")
    assert sorted(path.name for path in tmp_path.iterdir()) == ["ethanol.cdxml", "ethanol_2.cdxml"]
