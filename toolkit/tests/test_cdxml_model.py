"""The lossless CDXML model: parse, select, edit, validate and write back."""

from pathlib import Path
import xml.etree.ElementTree as ET

import pytest

from cdxml_toolkit import model

PROLOGUE = (
    '<?xml version="1.0" encoding="UTF-8" ?>\n'
    '<!DOCTYPE CDXML SYSTEM "http://www.cambridgesoft.com/xml/cdxml.dtd" >\n'
)
SAMPLE = PROLOGUE + (
    '<CDXML BondLength="14.4" Future="kept"><page id="1">'
    '<fragment id="2"><n id="3" p="10 10" Element="8"/><n id="4" p="20 10" FromTheFuture="x y z"/>'
    '<b id="5" B="3" E="4" Order="2"/></fragment>'
    '<t id="6" p="30 30"><s font="3" size="10">Hello</s></t>'
    '<!-- note --></page></CDXML>\n'
)


def snapshot(element):
    """Everything that matters for a lossless round trip, in document order."""
    return (
        element.tag,
        tuple(element.attrib.items()),
        (element.text or "").strip(),
        tuple(snapshot(child) for child in element if isinstance(child.tag, str)),
    )


def test_round_trip_keeps_every_element_attribute_and_comment():
    document = model.parse(SAMPLE)
    again = model.parse(document.dumps())
    assert snapshot(document.root) == snapshot(again.root)
    assert document.dumps().startswith(PROLOGUE.rstrip("\n").split("\n")[0])
    assert "<!DOCTYPE CDXML SYSTEM" in document.dumps()
    assert "<!-- note -->" in document.dumps()
    assert 'FromTheFuture="x y z"' in document.dumps()


def test_attribute_order_and_unknown_attributes_survive_an_edit():
    document = model.parse(SAMPLE)
    document.set_properties(document.select("n#3")[0], {"Charge": "1"})
    text = document.dumps()
    assert 'FromTheFuture="x y z"' in text and 'Future="kept"' in text
    order = [match for match in ("p=", "Element=", "Charge=") if match in text.split('id="3"')[1].split(">")[0]]
    assert order == ["p=", "Element=", "Charge="]


@pytest.mark.parametrize(
    "selector, expected",
    [
        ("n", ["3", "4"]),
        ("#5", ["5"]),
        ("n[Element=8]", ["3"]),
        ("fragment > n", ["3", "4"]),
        ("page > n", []),
        ("b#5[Order=2]", ["5"]),
        ("b#5[Order=1]", []),
        ("*[id=6]", ["6"]),
    ],
)
def test_selectors(selector, expected):
    document = model.parse(SAMPLE)
    assert [element.get("id") for element in document.select(selector)] == expected


def test_bad_selector_is_refused():
    with pytest.raises(ValueError, match="selector"):
        model.parse(SAMPLE).select("n[Element")


def test_describe_lists_tag_id_parent_and_attributes():
    document = model.parse(SAMPLE)
    entry = document.describe(document.select("b")[0])
    assert entry["tag"] == "b" and entry["id"] == "5" and entry["parent"] == {"tag": "fragment", "id": "2"}
    assert entry["attributes"] == {"id": "5", "B": "3", "E": "4", "Order": "2"}
    assert entry["children"] == 0


def test_set_properties_replaces_adds_and_removes():
    document = model.parse(SAMPLE)
    bond = document.select("b")[0]
    changed = document.set_properties(bond, {"Order": "1", "Display": "WedgeBegin", "E": None})
    assert changed == {"Order": ("2", "1"), "Display": (None, "WedgeBegin"), "E": ("4", None)}
    assert dict(bond.attrib) == {"id": "5", "B": "3", "Order": "1", "Display": "WedgeBegin"}


def test_catalog_validation_checks_value_kinds_and_unknown_names():
    document = model.parse(SAMPLE)
    atom = document.select("n#3")[0]
    with pytest.raises(ValueError, match="Element.*integer"):
        document.set_properties(atom, {"Element": "oxygen"})
    with pytest.raises(ValueError, match="Nonsense.*not an attribute of <n>"):
        document.set_properties(atom, {"Nonsense": "1"})
    document.set_properties(atom, {"Nonsense": "1"}, allow_unknown=True)
    assert atom.get("Nonsense") == "1"


def test_unknown_attributes_already_on_an_element_may_be_edited():
    document = model.parse(SAMPLE)
    atom = document.select("n#4")[0]
    document.set_properties(atom, {"FromTheFuture": "other"})
    assert atom.get("FromTheFuture") == "other"


def test_add_assigns_the_next_free_id_and_validates_the_tag():
    document = model.parse(SAMPLE)
    parent = document.select("fragment")[0]
    added = document.add(parent, "n", {"p": "30 10", "Element": "7"})
    assert added.get("id") == "7" and list(parent)[-1] is added
    with pytest.raises(ValueError, match="not a CDXML element"):
        document.add(parent, "widget", {})
    explicit = document.add(parent, "n", {"id": "40", "p": "1 1"})
    assert explicit.get("id") == "40"
    with pytest.raises(ValueError, match="already used"):
        document.add(parent, "n", {"id": "40", "p": "1 1"})


def test_add_builds_nested_children():
    document = model.parse(SAMPLE)
    page = document.select("page")[0]
    group = document.add(
        page,
        "group",
        {},
        children=[{"tag": "t", "props": {"p": "1 2"}, "children": [{"tag": "s", "props": {"font": "3"}, "text": "hi"}]}],
    )
    text_run = group.find("t/s")
    assert text_run.text == "hi" and group.find("t").get("id")


def test_delete_removes_a_subtree_and_refuses_referenced_ids():
    document = model.parse(SAMPLE)
    with pytest.raises(ValueError, match="referenced"):
        document.delete(document.select("n#3")[0])
    removed = document.delete(document.select("t")[0])
    assert removed == 2 and not document.select("t")
    removed = document.delete(document.select("fragment")[0])
    assert removed >= 4


def test_delete_refuses_the_root():
    document = model.parse(SAMPLE)
    with pytest.raises(ValueError, match="root"):
        document.delete(document.root)


def test_check_reports_duplicate_ids_and_dangling_references():
    document = model.parse(SAMPLE.replace('id="4"', 'id="3"').replace('E="4"', 'E="99"'))
    problems = {issue["code"] for issue in document.check()}
    assert {"duplicate_id", "dangling_reference"} <= problems
    assert model.parse(SAMPLE).check() == []


def test_parse_refuses_documents_that_are_not_cdxml():
    with pytest.raises(ValueError, match="CDXML"):
        model.parse("<html/>")
    with pytest.raises(ValueError, match="XML"):
        model.parse("<CDXML>")


def test_catalog_index_knows_observed_elements():
    index = model.catalog_index()
    assert "fragment" in index and "Order" in index["b"]
    assert index["b"]["Order"]["kind"] == "enum"


REPO = Path(__file__).resolve().parents[1]


def test_every_checked_in_cdxml_round_trips():
    paths = sorted((REPO / "assets").rglob("*.cdxml"))
    assert paths, "expected checked-in CDXML files"
    for path in paths:
        document = model.load(path)
        again = model.parse(document.dumps())
        assert snapshot(document.root) == snapshot(again.root), path.name
        assert document.check() == [], path.name
        original = ET.parse(path).getroot()
        assert snapshot(original) == snapshot(again.root), path.name
