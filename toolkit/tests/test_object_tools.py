"""chemdraw_object and chemdraw_inventory: contracts, refusals and verification."""

import json

import pytest

from cdxml_toolkit import model
from cdxml_toolkit.mcp_runtime import object_tools
from cdxml_toolkit.mcp_runtime.tool_registry import build_registry

SAMPLE = (
    '<?xml version="1.0" encoding="UTF-8" ?>\n'
    '<!DOCTYPE CDXML SYSTEM "http://www.cambridgesoft.com/xml/cdxml.dtd" >\n'
    '<CDXML BondLength="14.4"><page id="1">'
    '<fragment id="2"><n id="3" p="10 10" Element="8"/><n id="4" p="20 10"/>'
    '<b id="5" B="3" E="4" Order="1"/></fragment>'
    '<t id="6" p="30 30"><s font="3" size="10">Hello</s></t></page></CDXML>\n'
)


@pytest.fixture
def source(tmp_path):
    path = tmp_path / "in.cdxml"
    path.write_text(SAMPLE, encoding="utf-8")
    return path


def test_registered_in_the_default_profile_and_not_a_native_tool():
    registry = build_registry()
    assert {"chemdraw_object", "chemdraw_inventory"} <= set(registry)
    assert registry["chemdraw_object"].resource_class is None
    assert "chemdraw_object" not in build_registry("core")


def test_list_without_selector_counts_tags(source):
    result = object_tools.chemdraw_object("list", str(source))
    assert result["ok"] is True
    assert result["counts"]["n"] == 2 and result["counts"]["fragment"] == 1
    assert "output_path" not in result


def test_list_with_selector_returns_descriptions_and_truncates(source):
    result = object_tools.chemdraw_object("list", str(source), selector="n", limit=1)
    assert result["matched"] == 2 and len(result["elements"]) == 1 and result["truncated"] is True
    assert result["elements"][0]["attributes"]["Element"] == "8"


def test_get_requires_a_selector_and_a_match(source):
    assert object_tools.chemdraw_object("get", str(source))["ok"] is False
    missing = object_tools.chemdraw_object("get", str(source), selector="n#999")
    assert missing["ok"] is False and "matched no element" in missing["errors"][0]
    found = object_tools.chemdraw_object("get", str(source), selector="b")
    assert found["elements"][0]["attributes"]["Order"] == "1"


def test_set_writes_a_new_file_and_leaves_the_input_alone(source, tmp_path):
    before = source.read_bytes()
    result = object_tools.chemdraw_object(
        "set", str(source), selector="b#5", props={"Order": "2"}, output_path=str(tmp_path / "out.cdxml"))
    assert result["ok"] is True and result["changes"] == [
        {"id": "5", "tag": "b", "attributes": {"Order": {"old": "1", "new": "2"}}}]
    assert source.read_bytes() == before
    written = model.load(result["output_path"])
    assert written.select("b")[0].get("Order") == "2"
    assert result["verification"]["status"] == "passed"
    assert [a["path"] for a in result["metadata"]["artifacts"]] == [result["output_path"]]


def test_chemistry_edits_on_labelled_atoms_warn_that_the_label_text_is_unchanged(tmp_path):
    labelled = tmp_path / "labelled.cdxml"
    labelled.write_text(SAMPLE.replace('<n id="3" p="10 10" Element="8"/>',
                                       '<n id="3" p="10 10" Element="8"><t id="9"><s font="3">O</s></t></n>'),
                        encoding="utf-8")
    result = object_tools.chemdraw_object("set", str(labelled), selector="n", props={"Charge": "-1"}, dry_run=True)
    assert result["ok"] is True
    assert any("label text" in warning and "3" in warning for warning in result["warnings"])
    plain = object_tools.chemdraw_object("set", str(labelled), selector="n#4", props={"Charge": "-1"}, dry_run=True)
    assert plain["warnings"] == []
    layout = object_tools.chemdraw_object("set", str(labelled), selector="n#3", props={"Z": "5"}, dry_run=True)
    assert layout["warnings"] == []


def test_default_output_is_a_new_name_beside_the_input(source):
    first = object_tools.chemdraw_object("set", str(source), selector="b", props={"Order": "2"})
    second = object_tools.chemdraw_object("set", str(source), selector="b", props={"Order": "3"})
    assert first["output_path"] != second["output_path"] != str(source)
    assert first["output_path"].endswith("in_edited.cdxml")


def test_existing_output_is_refused(source, tmp_path):
    target = tmp_path / "taken.cdxml"
    target.write_text("keep", encoding="utf-8")
    result = object_tools.chemdraw_object("set", str(source), selector="b", props={"Order": "2"}, output_path=str(target))
    assert result["ok"] is False and target.read_text(encoding="utf-8") == "keep"
    same = object_tools.chemdraw_object("set", str(source), selector="b", props={"Order": "2"}, output_path=str(source))
    assert same["ok"] is False


def test_dry_run_reports_changes_and_writes_nothing(source, tmp_path):
    result = object_tools.chemdraw_object("set", str(source), selector="n", props={"Charge": 1}, dry_run=True)
    assert result["ok"] is True and result["dry_run"] is True and len(result["changes"]) == 2
    assert "output_path" not in result
    assert sorted(path.name for path in tmp_path.iterdir()) == ["in.cdxml"]


def test_set_rejects_unknown_attributes_unless_allowed(source):
    refused = object_tools.chemdraw_object("set", str(source), selector="n#3", props={"Nonsense": "1"}, dry_run=True)
    assert refused["ok"] is False and "Nonsense" in refused["errors"][0]
    allowed = object_tools.chemdraw_object("set", str(source), selector="n#3", props={"Nonsense": "1"},
                                           allow_unknown=True, dry_run=True)
    assert allowed["ok"] is True


def test_add_creates_an_object_with_a_fresh_id(source):
    result = object_tools.chemdraw_object(
        "add", str(source), selector="fragment", tag="n", props={"p": "30 10", "Element": 7})
    assert result["ok"] is True and result["added"][0]["id"] == "7"
    written = model.load(result["output_path"])
    assert written.select("n#7")[0].get("Element") == "7"
    assert result["verification"]["elements_before"] + 1 == result["verification"]["elements_after"]


def test_add_needs_exactly_one_parent(source):
    result = object_tools.chemdraw_object("add", str(source), selector="n", tag="n", props={"p": "1 1"}, dry_run=True)
    assert result["ok"] is False and "exactly one" in result["errors"][0]


def test_delete_removes_unreferenced_objects_and_refuses_referenced_ones(source):
    refused = object_tools.chemdraw_object("delete", str(source), selector="n#3", dry_run=True)
    assert refused["ok"] is False and "referenced" in refused["errors"][0]
    result = object_tools.chemdraw_object("delete", str(source), selector="t")
    assert result["ok"] is True and result["removed"] == 2
    assert not model.load(result["output_path"]).select("t")


def test_unknown_operation_and_missing_input_are_clear_errors(source, tmp_path):
    assert "op must be one of" in object_tools.chemdraw_object("frobnicate", str(source))["errors"][0]
    missing = object_tools.chemdraw_object("list", str(tmp_path / "nope.cdxml"))
    assert missing["ok"] is False and "does not exist" in missing["errors"][0]
    not_cdxml = tmp_path / "x.txt"
    not_cdxml.write_text("hello", encoding="utf-8")
    assert object_tools.chemdraw_object("list", str(not_cdxml))["ok"] is False


def test_verification_failure_publishes_nothing(source, tmp_path, monkeypatch):
    original = model.Document.dumps
    monkeypatch.setattr(model.Document, "dumps", lambda self: original(self).replace('id="4"', 'id="3"'))
    target = tmp_path / "out.cdxml"
    result = object_tools.chemdraw_object("set", str(source), selector="b", props={"Order": "2"}, output_path=str(target))
    assert result["ok"] is False and "verification" in result["errors"][0].lower()
    assert not target.exists()
    assert sorted(path.name for path in tmp_path.iterdir()) == ["in.cdxml"]


def test_inventory_filters_the_catalog_rows():
    result = object_tools.chemdraw_inventory(layer="cdxml", query="bioshape")
    assert result["ok"] is True and [row["symbol"] for row in result["rows"]] == ["bioshape"]
    assert result["rows"][0]["tier"] in ("T1", "T2", "T3")
    tiered = object_tools.chemdraw_inventory(layer="cdxml", tier="T1", limit=3)
    assert all(row["tier"] == "T1" for row in tiered["rows"]) and len(tiered["rows"]) <= 3
    assert set(tiered["summary"]) == {"chemscript", "com", "menu", "cdxml"}


def test_inventory_rejects_unknown_filters():
    assert object_tools.chemdraw_inventory(layer="nope")["ok"] is False
    assert object_tools.chemdraw_inventory(tier="T9")["ok"] is False


def test_inventory_result_is_json_serialisable():
    json.dumps(object_tools.chemdraw_inventory(query="Clean"))
