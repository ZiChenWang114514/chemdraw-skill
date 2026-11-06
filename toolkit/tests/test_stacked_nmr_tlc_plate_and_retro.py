"""Unit tests for stacked NMR comparisons, co-spot/stain/2D TLC plates,
LCMS 24/96-well purity heatmaps, multi-engine retrosynthesis comparison sheets,
and decoupled NMR shift matching.
"""

from __future__ import annotations

import json
from pathlib import Path
import types
import xml.etree.ElementTree as ET

import numpy as np
import pytest

from cdxml_toolkit.engines import env, nmr, reactions, worker
from cdxml_toolkit.mcp_runtime.engine_tools import (
    ENGINE_TOOLS,
    compare_nmr_shifts,
    predict_nmr,
    predict_retrosynthesis,
)
from cdxml_toolkit.mcp_runtime.scientific_tool import OPERATIONS, scientific_workflow
from cdxml_toolkit.scientific import __main__ as sci_cli
from cdxml_toolkit.scientific.apparatus import build_apparatus_cdxml, draw_apparatus
from cdxml_toolkit.scientific.common import Drawing
from cdxml_toolkit.scientific.plots import (
    build_lcms_plate_cdxml,
    build_plot_cdxml,
    plot_xy,
)
from cdxml_toolkit.scientific.spectra import (
    analyze_spectrum,
    build_nmr_cdxml,
    build_stacked_nmr_cdxml,
    load_nmr_spectrum,
    stack_spectra,
)
from cdxml_toolkit.scientific.tlc import (
    TLC_VISUALIZATION_PALETTES,
    _inject_cospot_lanes,
    build_tlc_cdxml,
    draw_tlc,
)


def _write_nmr_csv(path: Path, ppm: np.ndarray, intensity: np.ndarray) -> Path:
    np.savetxt(
        path,
        np.c_[ppm, intensity],
        delimiter=",",
        header="ppm,intensity",
        comments="",
    )
    return path


def test_drawing_dynamic_colortable_and_filled_rect():
    d = Drawing(400, 300)
    idx1 = d.color("#007c83")
    idx2 = d.color("#1565c0")
    idx1_dup = d.color("#007C83")
    assert idx1 == "4"
    assert idx2 == "5"
    assert idx1_dup == "4"

    colortable = d.root.find("colortable")
    assert colortable is not None
    # 2 built-in colors (white, black) + 2 dynamically registered colors
    assert len(colortable.findall("color")) == 4

    line_el = d.line((10, 10), (50, 50), color="#007c83", dashed=True)
    assert line_el.get("color") == "4"
    assert line_el.get("LineType") == "Dashed"

    curve_el = d.curve([(10, 10), (20, 30), (40, 10)], color="#1565c0")
    assert curve_el.get("color") == "5"

    txt_el = d.text((15, 25), "Label", size=9, color="#c62828")
    assert txt_el.get("color") == "6"
    assert txt_el.find("s").get("color") == "6"

    rect_el = d.filled_rect(10, 20, 60, 50, fill_color="#c8e6c9", border_color="#9e9e9e")
    assert rect_el.tag == "curve"
    assert rect_el.get("Closed") == "yes"
    assert rect_el.get("FillType") == "Solid"
    assert rect_el.get("LineType") == "Solid"
    assert rect_el.get("color") == d.color("#c8e6c9")


def test_build_nmr_cdxml_numeric_dimensions_and_inset(tmp_path: Path):
    ppm = np.linspace(0.0, 10.0, 2000)
    y = (
        2.5 * np.exp(-((ppm - 7.35) / 0.01) ** 2)
        + 2.5 * np.exp(-((ppm - 7.33) / 0.01) ** 2)
        + 4.0 * np.exp(-((ppm - 2.10) / 0.01) ** 2)
    )
    out_cdxml = tmp_path / "nmr_single.cdxml"
    xml_str = build_nmr_cdxml(
        ppm,
        y,
        inset_region=(7.1, 7.6),
        title="Custom Aromatic NMR",
        output_path=out_cdxml,
    )
    assert out_cdxml.is_file()
    root = ET.fromstring(xml_str)
    assert root.get("BoundingBox") == "0 0 540 320"
    page = root.find("page")
    assert page is not None
    assert float(page.get("Width")) == 540.0
    assert float(page.get("Height")) == 320.0
    all_texts = ["".join(t.itertext()) for t in root.iter("t")]
    assert any("Custom Aromatic NMR" in t for t in all_texts)
    assert any("Inset zoom:" in t for t in all_texts)


def test_build_stacked_nmr_cdxml_two_and_three_traces_with_connectors(tmp_path: Path):
    ppm = np.linspace(0.0, 10.0, 2048)
    y_sm = 3.0 * np.exp(-((ppm - 3.80) / 0.015) ** 2) + 2.0 * np.exp(-((ppm - 7.20) / 0.015) ** 2)
    y_rxn = 3.2 * np.exp(-((ppm - 4.15) / 0.015) ** 2) + 2.1 * np.exp(-((ppm - 7.45) / 0.015) ** 2)

    sm_csv = _write_nmr_csv(tmp_path / "sm.csv", ppm, y_sm)
    rxn_csv = _write_nmr_csv(tmp_path / "rxn.csv", ppm, y_rxn)

    assert load_nmr_spectrum is not None
    assert stack_spectra is build_stacked_nmr_cdxml

    # Predicted shifts dict (auto-simulated via engines.nmr.simulate)
    pred_dict = {
        "predicted": True,
        "engine": "magnet",
        "frequency_mhz": 400.0,
        "peaks": {
            "1H": [
                {"nucleus": "1H", "shift_ppm": 7.42, "count": 2},
                {"nucleus": "1H", "shift_ppm": 4.10, "count": 3},
            ]
        },
    }

    # 2-trace comparison with match_shifts connectors
    matches = [
        {"predicted_shift": 7.42, "experimental_shift": 7.45, "error": 0.03},
        {"predicted_shift": 4.10, "experimental_shift": 4.15, "error": 0.05},
    ]
    out_2 = tmp_path / "stacked_2.cdxml"
    res_2 = build_stacked_nmr_cdxml(
        [pred_dict, rxn_csv],
        output_path=out_2,
        labels=["Predicted 1H", "Measured Product"],
        ppm_range=(9.0, 0.5),
        match_shifts=matches,
    )
    assert out_2.is_file()
    assert res_2["trace_count"] == 2
    assert res_2["ppm_range"] == [9.0, 0.5]
    assert res_2["labels"] == ["Predicted 1H", "Measured Product"]

    root_2 = ET.fromstring(res_2["cdxml"])
    dashed_lines = [
        g for g in root_2.findall(".//graphic")
        if g.get("GraphicType") == "Line" and g.get("LineType") == "Dashed"
    ]
    assert len(dashed_lines) >= 2
    texts_2 = ["".join(t.itertext()) for t in root_2.iter("t")]
    assert any("\u0394\u03b4" in t for t in texts_2)

    # 3-trace stack (CSV path + analyze_spectrum dict + predicted shift dict)
    analyzed_sm = analyze_spectrum(sm_csv)
    out_3 = tmp_path / "stacked_3.cdxml"
    res_3 = stack_spectra(
        [analyzed_sm, rxn_csv, pred_dict],
        output_path=out_3,
        labels=["Starting Material", "Crude Rxn", "Predicted Product"],
    )
    assert out_3.is_file()
    assert res_3["trace_count"] == 3
    root_3 = ET.fromstring(res_3["cdxml"])
    curves_3 = root_3.findall(".//curve")
    assert len(curves_3) >= 3


def test_scientific_main_nmr_inset_and_clean_analysis_json(tmp_path: Path):
    ppm = np.linspace(0.0, 10.0, 2001)
    y = (
        0.5 * np.exp(-((ppm - 7.26) / 0.005) ** 2)
        + 3.0 * np.exp(-((ppm - 7.80) / 0.005) ** 2)
        + 3.0 * np.exp(-((ppm - 7.78) / 0.005) ** 2)
    )
    csv_path = _write_nmr_csv(tmp_path / "spec.csv", ppm, y)
    spec_file = tmp_path / "nmr_spec.json"
    spec_file.write_text(
        json.dumps({
            "input": "spec.csv",
            "title": "Purified Product 1H NMR",
            "solvent": "CDCl3",
            "spectrometer_frequency_mhz": 400.0,
            "exclude_solvent": True,
            "inset_region": [7.65, 7.95],
        }),
        encoding="utf-8",
    )
    out_dir = tmp_path / "nmr_out"
    res = sci_cli.run("nmr", spec_file, out_dir)
    assert Path(res["analysis_path"]).is_file()
    analysis_data = json.loads((out_dir / "analysis.json").read_text(encoding="utf-8"))
    # Ensure raw CDXML is not left inside analysis.json
    assert "cdxml" not in analysis_data
    assert analysis_data["inset_region"] == [7.65, 7.95]
    assert len(analysis_data["solvent_peaks"]) == 1

    plot_cdxml_text = (out_dir / "plot.cdxml").read_text(encoding="utf-8")
    plot_root = ET.fromstring(plot_cdxml_text)
    all_texts = ["".join(t.itertext()) for t in plot_root.iter("t")]
    assert any("Inset zoom:" in t for t in all_texts)


def test_scientific_main_multi_series_plot_and_new_operations(tmp_path: Path):
    x = np.linspace(0.0, 5.0, 50)
    csv_a = tmp_path / "a.csv"
    csv_b = tmp_path / "b.csv"
    np.savetxt(csv_a, np.c_[x, np.sin(x)], delimiter=",", header="time,conv", comments="")
    np.savetxt(csv_b, np.c_[x, np.cos(x)], delimiter=",", header="time,conv", comments="")

    plot_spec = tmp_path / "multi_plot.json"
    plot_spec.write_text(
        json.dumps({
            "title": "Kinetic Overlay",
            "x_label": "Time / h",
            "y_label": "Conversion",
            "dpi": 150,
            "series": [
                {"label": "Catalyst A", "input": "a.csv", "x_column": "time", "y_column": "conv"},
                {"label": "Catalyst B", "input": "b.csv", "x_column": "time", "y_column": "conv"},
            ],
        }),
        encoding="utf-8",
    )
    out_plot_dir = tmp_path / "plot_out"
    plot_res = sci_cli.run("plot", plot_spec, out_plot_dir)
    assert plot_res["series_count"] == 2
    assert plot_res["dpi"] == 150
    assert (out_plot_dir / "plot.cdxml").is_file()

    # Check stack_nmr and lcms_plate in OPERATIONS and scientific_workflow
    assert "stack_nmr" in OPERATIONS
    assert "lcms_plate" in OPERATIONS

    stack_spec = tmp_path / "stack_spec.json"
    _write_nmr_csv(tmp_path / "s1.csv", np.linspace(0, 10, 300), np.ones(300))
    _write_nmr_csv(tmp_path / "s2.csv", np.linspace(0, 10, 300), np.ones(300) * 2.0)
    stack_spec.write_text(
        json.dumps({
            "title": "Workflow Stack",
            "spectra": ["s1.csv", "s2.csv"],
            "labels": ["Run 1", "Run 2"],
        }),
        encoding="utf-8",
    )
    wf_stack = scientific_workflow("stack_nmr", str(stack_spec), str(tmp_path / "wf_stack.cdxml"))
    assert wf_stack["ok"] is True
    assert Path(wf_stack["outputs"]["output_path"]).is_file()


def test_tlc_auto_cospot_stains_multi_eluent_and_2d_mode(tmp_path: Path):
    assert build_tlc_cdxml is draw_tlc
    for key in ("uv254", "uv365", "kmno4", "pma", "ninhydrin", "anisaldehyde", "iodine"):
        assert key in TLC_VISUALIZATION_PALETTES

    # Test _inject_cospot_lanes directly and via auto_cospot=True
    lanes = [
        {"label": "SM", "spots": [{"rf": 0.25}, {"rf": 0.60}]},
        {"label": "Rxn", "spots": [{"rf": 0.258}, {"rf": 0.78}]},
    ]
    injected = _inject_cospot_lanes(lanes, rf_tol=0.015)
    assert len(injected) == 3
    assert injected[1]["label"] == "SM + Rxn"
    # 0.25 and 0.258 are within rf_tol=0.015 so they deduplicate to 1 spot; total 3 spots in co-spot lane
    assert len(injected[1]["spots"]) == 3

    cospot_path = tmp_path / "tlc_cospot.cdxml"
    res_cospot = build_tlc_cdxml(
        {
            "title": "Reaction Monitoring TLC",
            "stain": "kmno4",
            "auto_cospot": True,
            "solvent": "30% EtOAc/hexanes",
            "lanes": lanes,
        },
        cospot_path,
    )
    assert res_cospot["lane_count"] == 3
    root_cospot = ET.parse(cospot_path).getroot()
    assert len(root_cospot.findall(".//tlclane")) == 3
    spots_xml = root_cospot.findall(".//tlcspot")
    assert all(s.get("color") is not None for s in spots_xml)

    # Multi-eluent side-by-side plates
    multi_path = tmp_path / "tlc_multi.cdxml"
    res_multi = build_tlc_cdxml(
        {
            "title": "Eluent Screening",
            "visualization": "uv254",
            "plates": [
                {"solvent": "10% EtOAc/hexanes", "lanes": [{"label": "SM", "spots": [{"rf": 0.15}]}]},
                {"solvent": "40% EtOAc/hexanes", "lanes": [{"label": "SM", "spots": [{"rf": 0.55}]}]},
            ],
        },
        multi_path,
    )
    assert res_multi["plate_count"] == 2
    root_multi = ET.parse(multi_path).getroot()
    assert len(root_multi.findall(".//tlcplate")) == 2

    # 2D TLC mode with diagonal decomposition reference line
    tlc_2d_path = tmp_path / "tlc_2d.cdxml"
    res_2d = build_tlc_cdxml(
        {
            "mode": "2d",
            "title": "2D Silica Stability TLC",
            "solvent_1": "25% EtOAc/hexanes",
            "solvent_2": "25% EtOAc/hexanes",
            "spots": [
                {"rf1": 0.45, "rf2": 0.45, "label": "Product (stable)"},
                {"rf1": 0.65, "rf2": 0.25, "label": "Decomp."},
            ],
        },
        tlc_2d_path,
    )
    assert res_2d["mode"] == "2d"
    assert res_2d["spot_count"] == 2
    assert res_2d["off_diagonal_spots"] == 1
    root_2d = ET.parse(tlc_2d_path).getroot()
    dashed_diag = [
        g for g in root_2d.findall(".//graphic")
        if g.get("GraphicType") == "Line" and g.get("LineType") == "Dashed"
    ]
    assert len(dashed_diag) >= 1
    assert len(root_2d.findall(".//arrow")) >= 2


def test_build_lcms_plate_cdxml_24_and_96_well_and_openlynx_rpt(tmp_path: Path):
    assert build_plot_cdxml is plot_xy
    assert build_apparatus_cdxml is draw_apparatus

    # 24-well auto-detected from A1..D6 wells
    wells_24 = [
        {"well": "A1", "purity": 88.4, "rt": 1.42, "found_ion": "[M+H]+"},
        {"well": "B3", "purity": 54.0, "rt": 1.41, "found_ion": "[M+H]+"},
        {"well": "C2", "purity": 14.5, "rt": 1.39, "found_ion": "[M+H]+"},
        {"well": "D6", "purity": 0.0, "rt": None, "found_ion": None},
    ]
    out_24 = tmp_path / "plate24.cdxml"
    res_24 = build_lcms_plate_cdxml(wells_24, output_path=out_24, title="Buchwald 24-Well Screen")
    assert out_24.is_file()
    assert res_24["plate_format"] == "24-well"
    assert res_24["rows"] == ["A", "B", "C", "D"]
    assert res_24["columns"] == [1, 2, 3, 4, 5, 6]
    assert res_24["best_wells"][0] == "A1"
    assert "Best Wells: A1 (88.4%" in res_24["best_wells_summary"]
    root_24 = ET.fromstring(res_24["cdxml"])
    texts_24 = ["".join(t.itertext()) for t in root_24.iter("t")]
    assert any("Best Wells:" in t for t in texts_24)
    assert any("tR 1.42" in t for t in texts_24)

    # 96-well auto-detected when well H12 is present
    wells_96 = [
        {"well": "A1", "purity": 72.0, "rt": 1.10},
        {"well": "H12", "purity": 94.6, "rt": 1.12},
    ]
    out_96 = tmp_path / "plate96.cdxml"
    res_96 = build_lcms_plate_cdxml(wells_96, output_path=out_96)
    assert res_96["plate_format"] == "96-well"
    assert len(res_96["rows"]) == 8 and len(res_96["columns"]) == 12
    assert res_96["best_wells"] == ["H12", "A1"]

    # Synthetic OpenLynx .rpt file input with product_mass filtering
    rpt_text = """[SAMPLE]
{
Sample\t1
Well\tA1
FileName\tSCR-001
Date\t06-Nov-2026
Time\t10:00:00
[FUNCTION]
{
Function\t1
Type\tDAD
[CHROMATOGRAM]
{
Description\tDAD: TIC
[PEAK]
{
Peak ID\t1
Time\t1.35
AreaAbs\t5000
Area %Total\t85.5
}
}
}
[FUNCTION]
{
Function\t2
IonMode\tES+
Type\tMS
[SPECTRUM]
{
Peak ID\t1
Time\t1.35
[MS]
{
;Mass\t% BPI
346.1\t100.0
}
}
}
}
"""
    rpt_file = tmp_path / "screen.rpt"
    rpt_file.write_text(rpt_text, encoding="utf-8")
    res_rpt = build_lcms_plate_cdxml(rpt_file, product_mass=345.1, plate_format=24)
    assert res_rpt["plate_format"] == "24-well"
    assert res_rpt["best_wells"] == ["A1"]
    assert res_rpt["wells"][0]["purity"] == pytest.approx(85.5)


def test_worker_molscribe_returns_atoms_bonds_molfile_with_fallback(monkeypatch):
    class FakeTorch:
        @staticmethod
        def device(dev):
            return dev

    class FakeMolScribeNew:
        def __init__(self, path, device=None):
            pass

        def predict_image_file(self, path, return_atoms_bonds=False, return_confidence=False):
            assert return_atoms_bonds is True and return_confidence is True
            return {
                "smiles": "c1ccccc1",
                "confidence": 0.97,
                "atoms": [{"atom_symbol": "C", "x": 0.1, "y": 0.2}],
                "bonds": [{"atom_1": 0, "atom_2": 1, "bond_type": "aromatic"}],
                "molfile": "FAKE_MOLBLOCK",
            }

    fake_ms_mod = types.ModuleType("molscribe")
    fake_ms_mod.MolScribe = FakeMolScribeNew
    fake_ms_mod.chemistry = types.SimpleNamespace(multiprocessing=types.SimpleNamespace(Pool=None))
    monkeypatch.setitem(worker.sys.modules, "torch", FakeTorch)
    monkeypatch.setitem(worker.sys.modules, "molscribe", fake_ms_mod)
    monkeypatch.setattr(worker, "_device", lambda: "cpu")
    worker._MODEL_CACHE.clear()

    out_new = worker._molscribe({"images": ["img1.png"]}, data_dir=".", spec={})
    assert out_new[0]["smiles"] == "c1ccccc1"
    assert out_new[0]["score"] == pytest.approx(0.97)
    assert out_new[0]["atoms"] == [{"atom_symbol": "C", "x": 0.1, "y": 0.2}]
    assert out_new[0]["bonds"] == [{"atom_1": 0, "atom_2": 1, "bond_type": "aromatic"}]
    assert out_new[0]["molfile"] == "FAKE_MOLBLOCK"

    # Fallback when predict_image_file does not accept return_atoms_bonds
    class FakeMolScribeOld:
        def __init__(self, path, device=None):
            pass

        def predict_image_file(self, path, return_confidence=False):
            return {"smiles": "CCO", "confidence": 0.88}

    fake_ms_mod.MolScribe = FakeMolScribeOld
    worker._MODEL_CACHE.clear()
    out_old = worker._molscribe({"images": ["img2.png"]}, data_dir=".", spec={})
    assert out_old == [{"smiles": "CCO", "score": pytest.approx(0.88)}]


def test_multi_engine_retrosynthesis_and_route_comparison_cdxml(monkeypatch, tmp_path: Path):
    aspirin = "CC(=O)Oc1ccccc1C(=O)O"
    route_aiz = {
        "smiles": aspirin,
        "in_stock": False,
        "reaction": {
            "reactants": [
                {"smiles": "CC(=O)OC(C)=O", "in_stock": True, "reaction": None},
                {"smiles": "O=C(O)c1ccccc1O", "in_stock": True, "reaction": None},
            ]
        },
    }
    route_syn = {
        "smiles": aspirin,
        "in_stock": False,
        "reaction": {
            "reactants": [
                {"smiles": "CC(=O)Cl", "in_stock": True, "reaction": None},
                {"smiles": "O=C(O)c1ccccc1O", "in_stock": True, "reaction": None},
            ]
        },
    }

    def fake_call(name, action, params, timeout=0):
        env._LAST_CALL_META.set({"engine": name, "device": "cpu", "device_fallback": False})
        if name == "aizynthfinder":
            return {"steps": "multi", "target": aspirin, "solved": True, "top_score": 0.95, "routes": [route_aiz]}
        if name == "synplanner":
            return {"steps": "multi", "target": aspirin, "solved": True, "top_score": 0.82, "routes": [route_syn]}
        raise env.EngineError(f"{name} not installed")

    monkeypatch.setattr(env, "call", fake_call)

    out_retro_cdxml = tmp_path / "retro_compare.cdxml"
    multi_ans = predict_retrosynthesis(
        aspirin,
        engine="aizynthfinder,synplanner",
        steps="multi",
        output_cdxml=str(out_retro_cdxml),
    )
    assert multi_ans["ok"] is True
    assert multi_ans["engine"] == "aizynthfinder,synplanner"
    assert [r["engine_id"] for r in multi_ans["routes"]] == ["aizynthfinder", "synplanner"]
    assert out_retro_cdxml.is_file()
    root = ET.parse(out_retro_cdxml).getroot()
    assert len(root.findall(".//fragment")) >= 4
    assert len(root.findall(".//step")) >= 2

    # Direct compare_retrosynthesis_routes call (including an uninstalled 3rd engine)
    comp_out = tmp_path / "comp_sheet.cdxml"
    comp = reactions.compare_retrosynthesis_routes(
        aspirin,
        engines=("aizynthfinder", "synplanner", "retrochimera"),
        top_k_per_engine=1,
        output_cdxml=comp_out,
    )
    assert comp["ok"] is True
    assert comp["section_count"] == 2
    assert comp_out.is_file()
    assert len(comp["failed_engines"]) == 1
    assert comp["failed_engines"][0]["engine"] == "retrochimera"


def test_decoupled_compare_nmr_shifts_and_predict_nmr_fallback(monkeypatch, tmp_path: Path):
    assert "compare_nmr_shifts" in ENGINE_TOOLS
    monkeypatch.setenv("CHEMDRAW_ENGINE_HOME", str(tmp_path / "empty_engines"))

    # Even when no NMR engine is installed (predict_nmr returns ok=False),
    # experimental_comparison is still computed via RDKit topological heuristics!
    pred_ans = predict_nmr(
        "CCO",
        experimental_1h=[3.70, 2.45, 1.22],
        experimental_13c=[58.1, 18.4],
    )
    assert pred_ans["ok"] is False
    assert "experimental_comparison" in pred_ans
    exp_comp = pred_ans["experimental_comparison"]
    assert exp_comp["prediction_source"] == "heuristic"
    assert len(exp_comp["matches_1h"]) == 3
    assert len(exp_comp["matches_13c"]) == 2

    # Standalone compare_nmr_shifts tool works offline without engines
    standalone = compare_nmr_shifts(
        "c1ccccc1CC",
        experimental_1h=[7.25, 2.65, 1.22],
        experimental_13c=[144.0, 128.4, 127.9, 125.6, 28.9, 15.6],
    )
    assert standalone["kind"] == "model_assisted_candidate_assignment"
    assert len(standalone["matches_1h"]) == 3
    assert len(standalone["matches_13c"]) >= 4
