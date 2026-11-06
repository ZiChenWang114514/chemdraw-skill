"""Comprehensive tests for conformer/projection templates, acs_builder power-user tricks,
and draw_figure ring_fills / atom_halos / ts_bracket decorations.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

import pytest

from cdxml_toolkit.mcp_runtime import figure_draw
from cdxml_toolkit.templates import (
    bicyclic_cage,
    build_conformer_cdxml,
    chair_cyclohexane,
    fischer_projection,
    haworth_pyranose,
    newman_projection,
)

SKILL_SCRIPTS = Path(__file__).resolve().parents[2] / "skill" / "chemdraw" / "scripts"
if str(SKILL_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SKILL_SCRIPTS))

import acs_builder  # noqa: E402


# ---------------------------------------------------------------------------
# 1. Conformer & Perspective Templates (conformers.py)
# ---------------------------------------------------------------------------

def test_chair_cyclohexane_chair1_and_chair2_geometry():
    c1 = chair_cyclohexane(
        flip=False,
        substituents={1: {"ax": "OH", "eq": "Me"}, 4: {"eq": "tBu"}},
        cx=180.0,
        cy=160.0,
        bond_length=14.4,
    )
    c2 = chair_cyclohexane(
        flip=True,
        substituents={1: {"ax": "OH", "eq": "Me"}, 4: {"ax": "tBu"}},
        cx=180.0,
        cy=160.0,
        bond_length=14.4,
    )

    assert c1["conformation"] == "chair1" and c2["conformation"] == "chair2"
    for chair in (c1, c2):
        pts = chair["ring_coords"]
        assert len(pts) == 6
        # Opposite ring bonds (0-1 vs 3-4, 1-2 vs 4-5, 2-3 vs 5-0) are strictly parallel
        for k in range(3):
            v1 = (pts[(k + 1) % 6][0] - pts[k][0], pts[(k + 1) % 6][1] - pts[k][1])
            v2 = (pts[(k + 4) % 6][0] - pts[k + 3][0], pts[(k + 4) % 6][1] - pts[k + 3][1])
            assert math.isclose(math.hypot(*v1), 14.4, abs_tol=1e-6)
            assert math.isclose(math.hypot(*v2), 14.4, abs_tol=1e-6)
            cross = v1[0] * v2[1] - v1[1] * v2[0]
            assert abs(cross) < 1e-6

        # Equatorial vectors are parallel to the (i +/- 2) ring bonds and point outward
        for pos in range(1, 7):
            eq_x, eq_y = chair["equatorial_vectors"][pos]
            assert math.isclose(math.hypot(eq_x, eq_y), 14.4, abs_tol=1e-6)
            ref_a = pts[pos % 6]
            ref_b = pts[(pos + 1) % 6]
            rv_x, rv_y = ref_b[0] - ref_a[0], ref_b[1] - ref_a[1]
            assert abs(eq_x * rv_y - eq_y * rv_x) < 1e-6
            outward = (pts[pos - 1][0] - 180.0) * eq_x + (pts[pos - 1][1] - 160.0) * eq_y
            assert outward > 0.0

    # Axial vectors are strictly vertical and invert on ring flip
    for pos in (1, 3, 5):
        assert c1["axial_vectors"][pos] == (0.0, 14.4)
        assert c2["axial_vectors"][pos] == (0.0, -14.4)
    for pos in (2, 4, 6):
        assert c1["axial_vectors"][pos] == (0.0, -14.4)
        assert c2["axial_vectors"][pos] == (0.0, 14.4)

    root = ET.fromstring(c1["cdxml"])
    labels = ["".join(n.itertext()) for n in root.findall(".//fragment/n") if list(n)]
    assert "OH" in labels and "Me" in labels and "tBu" in labels


def test_newman_projection_staggered_and_eclipsed():
    stag = newman_projection(
        conformation="staggered",
        front=("Me", "H", "H"),
        rear=("Br", "H", "Me"),
        cx=180.0,
        cy=160.0,
        bond_length=24.0,
    )
    eclip = newman_projection(
        conformation="eclipsed",
        front=("Me", "H", "H"),
        rear=("Br", "H", "Me"),
        cx=180.0,
        cy=160.0,
        bond_length=24.0,
    )

    assert stag["front_angles"] == (-90.0, 30.0, 150.0)
    assert stag["rear_angles"] == (-30.0, 90.0, 210.0)
    assert eclip["rear_angles"] == (-76.0, 44.0, 164.0)

    expected_r = 0.48 * 24.0
    assert math.isclose(stag["circle_radius"], expected_r, abs_tol=1e-6)
    for sx, sy in stag["rear_spoke_starts"]:
        assert math.isclose(math.hypot(sx - 180.0, sy - 160.0), expected_r, abs_tol=1e-5)

    root = ET.fromstring(stag["cdxml"])
    oval = root.find('.//page/graphic[@GraphicType="Oval"]')
    assert oval is not None
    assert oval.get("OvalType") == "Circle Filled"
    assert oval.get("color") == "2"


def test_haworth_fischer_and_bicyclic_cages(tmp_path):
    haw = haworth_pyranose(anomer="beta", bond_length=18.0)
    h_root = ET.fromstring(haw["cdxml"])
    displays = [b.get("Display") for b in h_root.findall(".//fragment/b") if b.get("Display")]
    assert "Bold" in displays
    assert displays.count("WedgeBegin") == 2

    fisch = fischer_projection(
        centers=[{"left": "H", "right": "OH"}, {"left": "OH", "right": "H"}],
        top="CHO",
        bottom="CH2OH",
        bond_length=18.0,
    )
    f_root = ET.fromstring(fisch["cdxml"])
    f_texts = ["".join(n.itertext()) for n in f_root.findall(".//fragment/n") if list(n)]
    assert "CHO" in f_texts and "CH2OH" in f_texts and f_texts.count("OH") == 2

    for scaf in ("norbornane", "bicyclo_222", "adamantane"):
        cage = bicyclic_cage(scaffold=scaf, substituents={1: "Br"}, bond_length=16.0)
        c_root = ET.fromstring(cage["cdxml"])
        crossing = [b for b in c_root.findall(".//fragment/b") if b.get("CrossingBonds")]
        assert len(crossing) >= 1, f"{scaf} missing CrossingBonds"

    out_file = tmp_path / "chair_out.cdxml"
    cdxml_str = build_conformer_cdxml({"template": "chair", "flip": True}, output_path=out_file)
    assert out_file.is_file() and "<CDXML" in cdxml_str


# ---------------------------------------------------------------------------
# 2. acs_builder.py Power-User Tricks
# ---------------------------------------------------------------------------

def test_acs_builder_ring_fills_atom_halos_and_z_ordering(tmp_path):
    spec = {
        "objects": [
            {
                "type": "molecule",
                "smiles": "c1ccccc1O",
                "at": [150, 120],
                "ring_fills": [{"ring_index": 0, "color": "pastel_blue", "style": "polygon", "inset": 1.0}],
                "atom_halos": [{"atoms": [0, 6], "color": "pastel_yellow", "radius": 8.0}],
            }
        ]
    }
    spec_path = tmp_path / "spec.json"
    spec_path.write_text(json.dumps(spec), encoding="utf-8")
    out_path = acs_builder.build_from_spec(spec_path, tmp_path / "out.cdxml")
    root = ET.parse(out_path).getroot()
    page = root.find("page")
    assert page is not None

    children_tags = [el.tag for el in list(page)]
    frag_idx = children_tags.index("fragment")
    # Background curve and oval graphics must precede <fragment> in <page>
    assert "curve" in children_tags[:frag_idx]
    assert "graphic" in children_tags[:frag_idx]

    curve = page.find("curve")
    assert curve is not None
    assert curve.get("Closed") == "yes"
    assert curve.get("FillType") == "Solid"
    assert curve.get("LineType") == "None"
    assert curve.get("Z") == "1"

    halos = [g for g in page.findall("graphic") if g.get("OvalType") == "Circle Filled"]
    assert len(halos) == 2


def test_acs_builder_ferrocene_multi_attachment_ts_bracket_orbital_and_interaction():
    doc = acs_builder.Doc()
    # Ferrocene: Fe (atom 0) + two Cp rings (atoms 1..5 and 6..10)
    doc.add_smiles(
        "[Fe].c1cc[cH-]c1.c1cc[cH-]c1",
        at=(180, 140),
        multi_attachments=[
            {"metal_atom": 0, "ligand_atoms": [1, 2, 3, 4, 5], "bond_display": "WedgeBegin", "bond_order": "dative"},
            {"metal_atom": 0, "ligand_atoms": [6, 7, 8, 9, 10], "bond_display": "Dash", "bond_order": "dative"},
        ],
    )
    doc.add_ts_bracket((120, 90, 240, 190), superscript="\u2021")
    doc.add_orbital(180, 140, orbital_type="pShaded", angle_deg=-90.0, length=18.0, width=7.5, color="jacs_blue")
    doc.add_interaction((140, 140), (220, 140), style="dashed", color="jacs_red", label="2.05 A", clip_margin=3.5)
    doc.add_conformer({"template": "norbornane", "at": [320, 140]})

    cdxml = doc.to_cdxml()
    root = ET.fromstring(cdxml)

    ma_nodes = root.findall('.//fragment/n[@NodeType="MultiAttachment"]')
    assert len(ma_nodes) == 2
    assert all(len(n.get("Attachments", "").split()) == 5 for n in ma_nodes)

    dative_bonds = [b for b in root.findall(".//fragment/b") if b.get("Order") == "dative"]
    assert len(dative_bonds) == 2

    brackets = root.findall('.//page/graphic[@GraphicType="Bracket"]')
    assert len(brackets) == 2
    assert root.find(".//page/bracketedgroup") is not None
    all_text = " ".join("".join(t.itertext()) for t in root.findall(".//page/t"))
    assert "\u2021" in all_text
    assert "2.05 A" in all_text

    orbital = root.find('.//page/graphic[@GraphicType="Orbital"]')
    assert orbital is not None and orbital.get("OrbitalType") == "pShaded"

    dashed_lines = [
        g for g in root.findall('.//page/graphic[@GraphicType="Line"]') if g.get("LineType") == "Dashed"
    ]
    assert len(dashed_lines) == 1


# ---------------------------------------------------------------------------
# 3. draw_figure with ring_fills, atom_halos, and ts_bracket
# ---------------------------------------------------------------------------

def test_draw_figure_with_ring_fills_atom_halos_and_ts_bracket(tmp_path, monkeypatch):
    monkeypatch.setenv("CHEMDRAW_OFFLINE", "1")
    brief = {
        "species": [
            {
                "id": "SM",
                "smiles": "c1ccccc1Br",
                "label": "1",
                "ring_fills": [{"ring_index": 0, "color": "pastel_blue", "style": "polygon", "inset": 1.0}],
                "atom_halos": [{"atoms": [6], "color": "pastel_yellow", "radius": 7.5}],
            },
            {
                "id": "TS",
                "smiles": "c1ccccc1O",
                "label": "TS-1",
                "ts_bracket": True,
            },
        ],
        "steps": [
            {
                "substrates": ["SM"],
                "products": ["TS"],
                "above": ["Pd(PPh3)4, KOH"],
                "below": ["80 C, 4 h"],
            }
        ],
    }
    out_path = tmp_path / "decorated_scheme.cdxml"
    report = figure_draw.draw_figure(brief, output_path=str(out_path))
    assert report["ok"] is True
    assert report["lint"]["issues"] == []
    assert report["readback"]["status"] == "matched"
    assert report["checks_passed"] is True

    root = ET.parse(out_path).getroot()
    page = root.find("page")
    assert page is not None
    tags = [el.tag for el in list(page)]
    first_frag = tags.index("fragment")
    # Ring fill <curve> and atom halo <graphic> are placed before <fragment>
    assert "curve" in tags[:first_frag]
    assert "graphic" in tags[:first_frag]

    # Transition-state brackets and double dagger (\u2021) are present
    brackets = page.findall('graphic[@GraphicType="Bracket"]')
    assert len(brackets) == 2
    assert page.find("bracketedgroup") is not None
    page_texts = ["".join(t.itertext()) for t in page.findall("t")]
    assert "\u2021" in page_texts
