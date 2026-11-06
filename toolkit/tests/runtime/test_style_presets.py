from __future__ import annotations

import copy
import json
import math
import struct
import xml.etree.ElementTree as ET

import pytest

from cdxml_toolkit.chemdraw import style_sheet
from cdxml_toolkit.chemdraw.style_presets import (
    STYLE_PRESETS, apply_style_preset, list_style_presets, style_preset, style_preset_as_manifest_style,
)
from cdxml_toolkit.mcp_runtime.figure_draw import draw_figure
from cdxml_toolkit.mcp_runtime.figure_tools import compose_chemical_figure

from .test_draw_mechanism import ADDITION
from .test_draw_scope import SCOPE
from .test_style_sheet import CDXML

ASPIRIN = {
    "species": [
        {"id": "SA", "smiles": "OC(=O)c1ccccc1O", "label": "1"},
        {"id": "Ac2O", "smiles": "CC(=O)OC(C)=O"},
        {"id": "ASP", "smiles": "CC(=O)Oc1ccccc1C(=O)O", "label": "2"},
    ],
    "steps": [{"substrates": ["SA", "Ac2O"], "products": ["ASP"], "above": ["H2SO4 (cat.)"], "below": ["RT, 2 h"]}],
}


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.setenv("CHEMDRAW_OFFLINE", "1")


# --- registry ---------------------------------------------------------------

@pytest.mark.parametrize("slug, bond, line, bold, hash_, margin, label_size, font", [
    ("acs1996", "14.4", "0.6", "2", "2.5", "1.6", "10", "Arial"),
    ("wiley", "17", "0.75", "2.6", "2.6", "2", "12", "Arial"),
    ("rsc", "12.2", "0.45", "1.6", "1.75", "1.25", "7", "Helvetica"),
    ("nature", "10.8", "0.6", "1.56", "1.7", "1.19", "6", "Arial"),
])
def test_the_registry_pins_the_stock_style_sheet_settings(slug, bond, line, bold, hash_, margin, label_size, font):
    preset = style_preset(slug)
    attributes = preset["attributes"]
    assert (attributes["BondLength"], attributes["LineWidth"], attributes["BoldWidth"], attributes["HashSpacing"],
            attributes["MarginWidth"], attributes["LabelSize"]) == (bond, line, bold, hash_, margin, label_size)
    assert preset["fonts"]["label"][0] == font


def test_the_acs_preset_matches_the_toolkit_acs_constants():
    from cdxml_toolkit.constants import ACS_STYLE

    attributes = style_preset("acs1996")["attributes"]
    for name in ("BondLength", "LineWidth", "MarginWidth", "HashSpacing", "BondSpacing", "BoldWidth", "ChainAngle"):
        assert float(attributes[name]) == float(ACS_STYLE[name]), name


def test_presets_are_listed_default_first_and_cannot_be_changed():
    listed = list_style_presets()
    assert listed[0]["slug"] == "acs1996"
    assert {p["slug"] for p in listed} >= {"wiley", "adv_synth_catal", "rsc", "rsc_1col", "nature", "synthesis",
                                           "science_of_synthesis", "helv_chim_acta", "j_het_chem",
                                           "j_chin_chem_soc", "j_mol_mod", "phytomedicine", "chemdraw_default",
                                           "chemdraw_slide", "chemdraw_a4"}
    assert all(p["used_by"] and p["sheet"] for p in listed)
    with pytest.raises(TypeError):
        STYLE_PRESETS["acs1996"]["attributes"]["BondLength"] = "1"


def test_a_preset_is_found_by_slug_or_sheet_name_in_any_case():
    assert style_preset("NATURE")["slug"] == "nature"
    assert style_preset("Nature Research Document")["slug"] == "nature"
    assert style_preset("rsc (1 column) document")["slug"] == "rsc_1col"


def test_an_unknown_preset_names_the_available_ones():
    with pytest.raises(ValueError, match="acs1996.*wiley"):
        style_preset("chem-comm-2030")


def test_the_manifest_style_carries_the_preset_measurements():
    assert style_preset_as_manifest_style("rsc") == {
        "font": "Helvetica", "font_size": 7.0, "bond_length": 12.2, "line_width": 0.45,
        "bold_width": 1.6, "hash_spacing": 1.75, "margin_width": 1.25,
    }


# --- applying -------------------------------------------------------------

def test_applying_a_preset_sets_its_settings_and_rescales_every_coordinate():
    source = CDXML.replace('</fragment>', '</fragment><arrow id="9" Head3D="200 200 0" Tail3D="160 200 0"/>'
                           '<t id="10" p="120 230"><s font="3" size="10">rt</s></t>')
    root = ET.fromstring(apply_style_preset(source, "nature"))

    assert root.get("BondLength") == "10.8" and root.get("LineWidth") == "0.6"
    factor = 10.8 / 34
    assert [n.get("p") for n in root.iter("n")] == [f"{100 * factor:.2f} {200 * factor:.2f}",
                                                    f"{134 * factor:.2f} {200 * factor:.2f}"]
    assert root.find(".//arrow").get("Head3D") == f"{200 * factor:.2f} {200 * factor:.2f} 0.00"
    assert root.find(".//s").get("size") == "6"


def test_without_rescale_only_the_settings_change():
    root = ET.fromstring(apply_style_preset(CDXML, "wiley", rescale=False))
    assert root.get("BondLength") == "17"
    assert [n.get("p") for n in root.iter("n")] == ["100 200", "134 200"]


# --- style sheet header layouts ---------------------------------------------

def _settings(bond_length: float = 17.0) -> bytes:
    return struct.pack("<HHi", 0x0805, 4, round(bond_length * 65536))


@pytest.mark.parametrize("layout", ["spec header + document", "short header + document", "spec header, top level"])
def test_style_sheets_are_read_in_all_three_cdx_header_layouts(tmp_path, layout):
    version = struct.pack("<I", 0x01020304)
    document = struct.pack("<HI", 0x8000, 0)
    if layout == "spec header + document":
        data = b"VjCD0100" + version + bytes(16) + document + _settings() + b"\0\0"
    elif layout == "short header + document":
        data = b"VjCD0100" + version + bytes(10) + document + _settings() + b"\0\0"
    else:
        data = b"VjCD0100" + version + bytes(16) + _settings() + b"\0\0"
    path = tmp_path / "sheet.cds"
    path.write_bytes(data)

    assert style_sheet.read_style_sheet(path)["attributes"]["BondLength"] == "17"


# --- compose_chemical_figure --------------------------------------------------

def _compose(tmp_path, style):
    manifest = tmp_path / "m.json"
    manifest.write_text(json.dumps({"style": style,
                                    "objects": [{"type": "molecule", "smiles": "c1ccccc1O"}]}))
    out = tmp_path / "m.cdxml"
    compose_chemical_figure(str(manifest), str(out))
    return ET.parse(out).getroot()


def test_compose_accepts_a_preset_name_as_the_style(tmp_path):
    root = _compose(tmp_path, "rsc")
    assert float(root.get("BondLength")) == 12.2 and float(root.get("LineWidth")) == 0.45


def test_compose_fields_override_the_preset(tmp_path):
    root = _compose(tmp_path, {"preset": "nature", "bond_length": 12})
    assert float(root.get("BondLength")) == 12 and float(root.get("LineWidth")) == 0.6


def test_compose_names_the_allowed_style_fields(tmp_path):
    with pytest.raises(ValueError, match="preset"):
        _compose(tmp_path, {"colour": "red"})


# --- draw_figure briefs -----------------------------------------------------

def _width(root) -> float:
    xs = [float(n.get("p").split()[0]) for n in root.iter() if n.get("p")]
    return max(xs) - min(xs)


def _mean_bond(root) -> float:
    lengths = []
    for fragment in root.iter("fragment"):
        nodes = {n.get("id"): tuple(map(float, n.get("p").split())) for n in fragment.findall("n")}
        for bond in fragment.findall("b"):
            if bond.get("B") in nodes and bond.get("E") in nodes:
                lengths.append(math.dist(nodes[bond.get("B")], nodes[bond.get("E")]))
    return sum(lengths) / len(lengths)


def test_the_acs_style_is_exactly_the_default_drawing(tmp_path):
    plain = draw_figure(ASPIRIN, output_path=str(tmp_path / "plain.cdxml"))
    styled = draw_figure({**ASPIRIN, "style": "acs1996"}, output_path=str(tmp_path / "acs.cdxml"))
    assert plain["ok"] and styled["ok"]
    assert (tmp_path / "plain.cdxml").read_bytes() == (tmp_path / "acs.cdxml").read_bytes()
    assert styled["style"] == {"preset": "acs1996", "bond_length": 14.4}


def test_a_nature_scheme_has_nature_bonds_and_is_narrower(tmp_path):
    acs = draw_figure(ASPIRIN, output_path=str(tmp_path / "acs.cdxml"))
    nature = draw_figure({**ASPIRIN, "style": "Nature"}, output_path=str(tmp_path / "nature.cdxml"))
    assert nature["ok"], nature
    assert nature["style"] == {"preset": "nature", "bond_length": 10.8}
    root = ET.parse(nature["output_path"]).getroot()
    assert root.get("BondLength") == "10.8"
    assert _mean_bond(root) == pytest.approx(10.8, rel=0.03)
    assert _width(root) < _width(ET.parse(acs["output_path"]).getroot())
    assert nature["readback"]["status"] == "matched"


def test_max_width_applies_to_the_styled_figure(tmp_path):
    report = draw_figure({**ASPIRIN, "style": "chemdraw_default", "max_width": 504},
                         output_path=str(tmp_path / "big.cdxml"))
    assert report["ok"], report
    root = ET.parse(report["output_path"]).getroot()
    assert root.get("BondLength") == "30"
    assert _width(root) <= 504 or any(i["kind"] == "too_wide" for i in report["lint"]["issues"])


def test_an_unknown_brief_style_is_refused_with_the_choices(tmp_path):
    report = draw_figure({**ASPIRIN, "style": "jacs2030"}, output_path=str(tmp_path / "x.cdxml"))
    assert not report["ok"] and "nature" in report["errors"][0]


def test_a_mechanism_takes_a_preset(tmp_path):
    report = draw_figure({**copy.deepcopy(ADDITION), "style": "rsc"}, output_path=str(tmp_path / "m.cdxml"))
    assert report["ok"], report
    root = ET.parse(report["output_path"]).getroot()
    assert report["style"]["preset"] == "rsc" and root.get("BondLength") == "12.2"
    assert _mean_bond(root) == pytest.approx(12.2, rel=0.03)


def test_a_scope_panel_takes_a_preset(tmp_path):
    report = draw_figure({**copy.deepcopy(SCOPE), "style": "wiley"}, output_path=str(tmp_path / "scope"))
    assert report["ok"], report
    assert report["style"] == {"preset": "wiley", "bond_length": 17.0}
    root = ET.parse(report["pages"][0]["path"]).getroot()
    assert float(root.get("BondLength")) == 17
