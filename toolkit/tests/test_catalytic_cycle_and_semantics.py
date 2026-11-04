"""Tests for catalytic-cycle layout, dative/radical/atropisomer semantics, 118-element table, and bridge pool."""
from __future__ import annotations

import importlib
import math
import xml.etree.ElementTree as ET
from unittest import mock

import pytest
from rdkit import Chem

from cdxml_toolkit import cdxml_builder, chemistry_semantics, rdkit_utils
from cdxml_toolkit.mcp_runtime import figure_draw, figure_lint, figure_validation
from cdxml_toolkit.perception import reaction_parser, scheme_reader
from cdxml_toolkit.render import renderer, route_graph
from cdxml_toolkit.render.schema import ArrowContent, SchemeDescriptor, StepDescriptor, StructureRef

reaction_from_image = importlib.import_module("cdxml_toolkit.image.reaction_from_image")


# ---------------------------------------------------------------------------
# 1. Catalytic Cycle Layout (route_graph, renderer, draw_figure)
# ---------------------------------------------------------------------------

def test_catalytic_cycle_route_classification_and_ordering():
    steps = [
        StepDescriptor(substrates=["pd0"], products=["ox_add"]),
        StepDescriptor(substrates=["transmet"], products=["pd0"]),
        StepDescriptor(substrates=["ox_add"], products=["transmet"]),
    ]
    kind, order = route_graph.classify_route(steps)
    assert kind == "catalytic-cycle"
    assert order == [0, 2, 1]


def test_catalytic_cycle_3_step_pd_cycle_via_draw_figure(tmp_path):
    brief = {
        "species": [
            {"id": "pd0", "smiles": "[Pd]", "label": "Pd(0)"},
            {"id": "int1", "smiles": "c1ccccc1[Pd]Br", "label": "Ph-Pd-Br"},
            {"id": "int2", "smiles": "c1ccccc1[Pd]c2ccccc2", "label": "Ph-Pd-Ph"},
        ],
        "steps": [
            {
                "substrates": ["pd0"],
                "products": ["int1"],
                "above": ["PhBr"],
                "below": ["oxidative addition"],
            },
            {
                "substrates": ["int1"],
                "products": ["int2"],
                "above": ["PhB(OH)2, NaOH"],
                "below": ["transmetallation"],
            },
            {
                "substrates": ["int2"],
                "products": ["pd0"],
                "above": ["reductive elimination"],
                "below": ["Ph-Ph"],
            },
        ],
    }
    out_path = tmp_path / "pd_cycle_3step.cdxml"
    report = figure_draw.draw_figure(brief, output_path=str(out_path))
    assert report["ok"] is True
    assert report["layout"] == "catalytic-cycle"
    assert report["lint"]["issues"] == []
    assert report["readback"]["status"] == "matched"
    assert report["readback"]["structures_drawn"] == 3

    root = ET.parse(out_path).getroot()
    page = root.find("page")
    assert page is not None
    fragments = page.findall("fragment")
    arrows = page.findall("arrow")
    assert len(fragments) == 3
    assert len(arrows) == 3
    assert len(root.findall(".//scheme/step")) == 3

    # Verify structures sit on a circle around (280, 240)
    cx, cy = 280.0, 240.0
    radii = []
    for frag in fragments:
        bb = [float(v) for v in frag.attrib["BoundingBox"].split()]
        fcx = (bb[0] + bb[2]) / 2.0
        fcy = (bb[1] + bb[3]) / 2.0
        radii.append(math.hypot(fcx - cx, fcy - cy))
    assert max(radii) - min(radii) < 15.0
    assert min(radii) >= 85.0


def test_catalytic_cycle_4_step_renderer_layout():
    scheme = SchemeDescriptor(
        layout="catalytic-cycle",
        structures={
            "I1": StructureRef(id="I1", smiles="[Pd](Cl)Cl", label="I"),
            "I2": StructureRef(id="I2", smiles="c1ccccc1[Pd]Cl", label="II"),
            "I3": StructureRef(id="I3", smiles="C=CC[Pd]c1ccccc1", label="III"),
            "I4": StructureRef(id="I4", smiles="c1ccc(CC=C)cc1", label="IV"),
        },
        steps=[
            StepDescriptor(
                substrates=["I1"],
                products=["I2"],
                above_arrow=ArrowContent(text=["PhB(OH)2"]),
                below_arrow=ArrowContent(text=["step 1"]),
            ),
            StepDescriptor(
                substrates=["I2"],
                products=["I3"],
                above_arrow=ArrowContent(text=["allylCl"]),
                below_arrow=ArrowContent(text=["step 2"]),
            ),
            StepDescriptor(
                substrates=["I3"],
                products=["I4"],
                above_arrow=ArrowContent(text=["beta-el"]),
                below_arrow=ArrowContent(text=["step 3"]),
            ),
            StepDescriptor(
                substrates=["I4"],
                products=["I1"],
                above_arrow=ArrowContent(text=["HCl"]),
                below_arrow=ArrowContent(text=["step 4"]),
            ),
        ],
    )
    cdxml = renderer.render(scheme)
    issues = figure_lint.lint_cdxml(cdxml)
    assert issues == []
    root = ET.fromstring(cdxml)
    assert len(root.findall(".//page/fragment")) == 4
    assert len(root.findall(".//page/arrow")) == 4


# ---------------------------------------------------------------------------
# 2. Dative Bonds, Radicals (TEMPO), & Axial Chirality in cdxml_builder
# ---------------------------------------------------------------------------

def test_tempo_radical_cdxml_generation_and_roundtrip():
    tempo_smiles = "[O]N1C(C)(C)CCCC1(C)C"
    mol = Chem.MolFromSmiles(tempo_smiles)
    assert mol is not None

    cdxml = cdxml_builder.build_molecule_cdxml(mol)
    root = ET.fromstring(cdxml)
    radical_nodes = [n for n in root.findall(".//n") if n.get("Radical") == "Doublet"]
    assert len(radical_nodes) == 1
    assert radical_nodes[0].get("Element") == "8"
    assert radical_nodes[0].get("NumHydrogens") == "0"

    parsed = chemistry_semantics.read_molecules(cdxml)
    assert len(parsed) == 1
    assert chemistry_semantics.semantic_key(parsed[0]) == chemistry_semantics.semantic_key(mol)


def test_dative_bond_cdxml_generation_and_roundtrip():
    dative_smiles = "[Pd](Cl)(Cl)<-n1ccccc1"
    mol = Chem.MolFromSmiles(dative_smiles)
    assert mol is not None

    # Dative bonds are supported by require_supported
    chemistry_semantics.require_supported(mol)

    cdxml = cdxml_builder.build_molecule_cdxml(mol)
    root = ET.fromstring(cdxml)
    dative_bonds = [b for b in root.findall(".//b") if b.get("Order") == "dative"]
    assert len(dative_bonds) == 1

    # Verify B is the nitrogen donor and E is the palladium acceptor
    nodes_by_id = {n.get("id"): n for n in root.findall(".//n")}
    donor_node = nodes_by_id[dative_bonds[0].get("B")]
    acceptor_node = nodes_by_id[dative_bonds[0].get("E")]
    assert donor_node.get("Element") == "7"
    assert acceptor_node.get("Element") == "46"

    parsed = chemistry_semantics.read_molecules(cdxml)
    assert len(parsed) == 1
    assert chemistry_semantics.semantic_key(parsed[0]) == chemistry_semantics.semantic_key(mol)


def test_axial_chirality_atropisomer_cdxml_roundtrip():
    atrop_smiles = "Cc1cccc(C)c1-c1c(C)cccc1O |wU:7.7|"
    mol = Chem.MolFromSmiles(atrop_smiles)
    assert mol is not None

    chemistry_semantics.require_supported(mol)
    cdxml = cdxml_builder.build_molecule_cdxml(mol)
    parsed = chemistry_semantics.read_molecules(cdxml)
    assert len(parsed) == 1
    assert chemistry_semantics.semantic_key(parsed[0]) == chemistry_semantics.semantic_key(mol)


# ---------------------------------------------------------------------------
# 3. Full 118-Element Periodic Table in reaction_from_image.py
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "symbol,expected_z",
    [
        ("Li", 3),
        ("Mg", 12),
        ("Ti", 22),
        ("Fe", 26),
        ("Ni", 28),
        ("Cu", 29),
        ("Zn", 30),
        ("Se", 34),
        ("Ru", 44),
        ("Rh", 45),
        ("Pd", 46),
        ("Sn", 50),
        ("Ir", 77),
        ("Pt", 78),
        ("Au", 79),
        ("U", 92),
        ("Og", 118),
    ],
)
def test_transition_metal_and_full_periodic_table_numbers(symbol, expected_z):
    assert reaction_from_image.ELEMENT_NUMBERS[symbol] == expected_z
    assert reaction_from_image._ELEMENT_NUMBERS[symbol] == expected_z
    assert len(reaction_from_image.ELEMENT_NUMBERS) >= 118

    ids = reaction_from_image._IDGen(100)
    frag_xml, _ = reaction_from_image._build_fragment(
        [{"index": 1, "symbol": symbol, "x": 100.0, "y": 100.0, "num_hydrogens": 0}],
        [],
        ids,
    )
    node = ET.fromstring(frag_xml).find("n")
    assert node is not None
    assert node.get("Element") == str(expected_z)


# ---------------------------------------------------------------------------
# 4. Process-Level Singleton ChemScriptBridge Pool & Batch Validation Session
# ---------------------------------------------------------------------------

def test_shared_chemscript_bridge_singleton_caching(monkeypatch):
    created = []

    class DummyBridge:
        def __init__(self):
            self.closed = False
            created.append(self)

        def close(self):
            self.closed = True

    monkeypatch.setattr(rdkit_utils, "ChemScriptBridge", DummyBridge)
    monkeypatch.setattr(rdkit_utils, "_shared_chemscript_bridge", None)

    b1 = rdkit_utils._get_shared_chemscript_bridge()
    b2 = reaction_parser._get_shared_chemscript_bridge()
    b3 = scheme_reader._get_shared_chemscript_bridge()

    assert b1 is b2
    assert b2 is b3
    assert len(created) == 1

    rdkit_utils._close_shared_chemscript_bridge()
    assert b1.closed is True
    assert rdkit_utils._shared_chemscript_bridge is None


def test_batch_figure_validation_reuses_shared_render_session(tmp_path, monkeypatch):
    from cdxml_toolkit.mcp_runtime.official_overrides import draw_molecule

    f1 = tmp_path / "m1.cdxml"
    f2 = tmp_path / "m2.cdxml"
    draw_molecule({"smiles": "CCO"}, str(f1))
    draw_molecule({"smiles": "c1ccccc1"}, str(f2))

    sessions_created = []

    class DummySession:
        def __init__(self):
            self.renders = []
            self.closed = False
            sessions_created.append(self)

        def render(self, cdxml_path, output_png=None):
            self.renders.append(cdxml_path)
            return {"ok": True, "png_path": output_png}

        def close(self):
            self.closed = True

    monkeypatch.setattr(figure_validation, "NativeRenderSession", DummySession)
    monkeypatch.setattr(figure_validation, "_shared_render_session", None)

    batch = figure_validation.validate_figures(
        [f1, f2],
        str(tmp_path / "batch_out"),
        native=False,
        render_png=True,
    )
    assert batch["ok"] is True
    assert batch["count"] == 2
    assert len(sessions_created) == 1
    assert len(sessions_created[0].renders) == 2

    figure_validation._close_shared_render_session()
    assert sessions_created[0].closed is True
