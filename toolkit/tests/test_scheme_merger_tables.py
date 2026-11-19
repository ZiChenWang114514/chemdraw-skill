"""scheme_merger: temporary reference files, style tables and id references of merged schemes."""
from __future__ import annotations

import os
import xml.etree.ElementTree as ET

from cdxml_toolkit.layout import scheme_merger
from cdxml_toolkit.model.document import REFERENCES, Document


def _tree(font_name: str, rgb: str, offset: int = 0) -> ET.ElementTree:
    r, g, b = rgb.split()
    xml = f"""<CDXML>
<colortable><color r="1" g="1" b="1"/><color r="0" g="0" b="0"/><color r="{r}" g="{g}" b="{b}"/></colortable>
<fonttable><font id="3" charset="iso-8859-1" name="{font_name}"/></fonttable>
<page id="1">
<fragment id="10" ConnectionOrder="11"><n id="11" p="{100 + offset} 100" Attachments="12"/><n id="12" p="{114 + offset} 100"/>
<b id="13" B="11" E="12" BondCircularOrdering="13"/></fragment>
<bracketedgroup id="20" BracketedObjectIDs="11 12"><bracketattachment id="21" GraphicID="22"/></bracketedgroup>
<graphic id="22" BoundingBox="{90 + offset} 90 {130 + offset} 110"/>
<t id="30" p="{100 + offset} 130"><s font="3" size="10" color="4">label</s></t>
</page></CDXML>"""
    return ET.ElementTree(ET.fromstring(xml))


def _font_of(root, s):
    return next(f.get("name") for f in root.find("fonttable") if f.get("id") == s.get("font"))


def _rgb_of(root, s):
    colors = list(root.find("colortable"))
    c = colors[int(s.get("color")) - 2]  # index 0 black, 1 white, table from 2
    return c.get("r"), c.get("g"), c.get("b")


def test_adjacent_schemes_keep_their_fonts_and_colours():
    merged = scheme_merger.adjacent_place([_tree("Arial", "0 0 1"), _tree("Times New Roman", "1 0 0", 300)])
    root = merged.getroot()
    runs = list(root.iter("s"))
    assert [_font_of(root, s) for s in runs] == ["Arial", "Times New Roman"]
    assert [_rgb_of(root, s) for s in runs] == [("0", "0", "1"), ("1", "0", "0")]


def test_adjacent_schemes_remap_every_id_reference():
    merged = scheme_merger.adjacent_place([_tree("Arial", "0 0 1"), _tree("Arial", "0 0 1", 300)])
    doc = Document(merged.getroot())
    assert [i for i in doc.check() if i.get("code") == "dangling_reference"] == []
    ids = [n.get("id") for n in merged.getroot().iter() if n.get("id")]
    assert len(ids) == len(set(ids))
    groups = list(merged.getroot().iter("bracketedgroup"))
    node_ids = {n.get("id") for n in groups[1].iter()} | {n.get("id") for f in merged.getroot().iter("fragment") for n in f}
    assert set(groups[1].get("BracketedObjectIDs").split()) <= node_ids
    assert groups[1].get("BracketedObjectIDs") != groups[0].get("BracketedObjectIDs")


def test_references_table_names_the_merger_attributes():
    for key in [("step", "ReactionStepReactants"), ("step", "ReactionStepProducts"),
                ("step", "ReactionStepArrows"), ("step", "ReactionStepObjectsAboveArrow"),
                ("b", "BondCircularOrdering"), ("fragment", "ConnectionOrder"), ("n", "Attachments")]:
        assert key in REFERENCES


def test_temporary_reference_file_has_a_page():
    root = _tree("Arial", "0 0 1").getroot()
    frag = root.find(".//fragment")
    path = scheme_merger._write_temp_fragment_cdxml(frag, root)
    try:
        written = ET.parse(path).getroot()
    finally:
        os.unlink(path)
    page = written.find("page")
    assert page is not None and page.find("fragment") is not None
