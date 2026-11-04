"""Regression tests for Office OLE safety, batch COM sessions, divergent layout,
scientific multi-series UTF-8 300-DPI plots, and image module imports/elements.
"""

from __future__ import annotations

import io
import json
import sys
import types
import zipfile
from pathlib import Path
from unittest import mock
from xml.etree import ElementTree as ET

import numpy as np
import olefile
import pytest

import importlib
import warnings
from cdxml_toolkit import cdxml_builder
from cdxml_toolkit.mcp_runtime import office_objects

reaction_from_image = importlib.import_module("cdxml_toolkit.image.reaction_from_image")
structure_from_image = importlib.import_module("cdxml_toolkit.image.structure_from_image")
from cdxml_toolkit.office import ole_embedder, ole_extractor
from cdxml_toolkit.render import renderer
from cdxml_toolkit.render.schema import (
    ArrowContent,
    SchemeDescriptor,
    StepDescriptor,
    StructureRef,
)
from cdxml_toolkit.scientific import common as sci_common
from cdxml_toolkit.scientific import plots as sci_plots


# ---------------------------------------------------------------------------
# 1. Office OLE Compound File (< 1 KB and > 100 KB) & DispatchEx safety
# ---------------------------------------------------------------------------


def test_build_ole_compound_file_small_payload_passes_strict_olefile():
    payload = b"VjCD0100" + b"\x01\x02\x03\x04" * 126  # 512 bytes (< 1 KB)
    assert len(payload) == 512

    ole_bytes = ole_embedder.build_ole_compound_file(payload)
    assert olefile.isOleFile(io.BytesIO(ole_bytes))

    with olefile.OleFileIO(
        io.BytesIO(ole_bytes), raise_defects=olefile.DEFECT_INCORRECT
    ) as ole:
        assert ole.exists("CONTENTS")
        stream_data = ole.openstream("CONTENTS").read()
        assert stream_data.startswith(payload)
        assert stream_data[len(payload) :].strip(b"\x00") == b""


def test_build_ole_compound_file_large_multi_fat_payload_passes_strict_olefile():
    # 150,000 bytes (> 100 KB, requires multiple FAT sectors)
    rng = np.random.default_rng(42)
    payload = b"VjCD0100" + rng.bytes(150_000 - 8)
    assert len(payload) == 150_000

    ole_bytes = ole_embedder.build_ole_compound_file(payload)
    assert olefile.isOleFile(io.BytesIO(ole_bytes))

    with olefile.OleFileIO(
        io.BytesIO(ole_bytes), raise_defects=olefile.DEFECT_INCORRECT
    ) as ole:
        assert ole.exists("CONTENTS")
        stream_data = ole.openstream("CONTENTS").read()
        assert len(stream_data) == len(payload)
        assert stream_data == payload


def test_ole_embedder_batch_convert_uses_dispatchex_not_dispatch(tmp_path):
    cdxml_path = tmp_path / "sample.cdxml"
    cdxml_path.write_text("<CDXML/>", encoding="utf-8")

    fake_doc = mock.MagicMock()

    def _save_as(path, fmt=None):
        Path(path).write_bytes(b"FAKE_OUT")

    fake_doc.SaveAs.side_effect = _save_as
    fake_app = mock.MagicMock()
    fake_app.Documents.Open.return_value = fake_doc

    fake_win32_client = types.SimpleNamespace(
        Dispatch=mock.MagicMock(side_effect=AssertionError("Dispatch must not be called")),
        DispatchEx=mock.MagicMock(return_value=fake_app),
    )
    fake_win32com = types.SimpleNamespace(client=fake_win32_client)

    with mock.patch.dict(
        sys.modules,
        {"win32com": fake_win32com, "win32com.client": fake_win32_client},
    ):
        results = ole_embedder.batch_convert([str(cdxml_path)])

    assert fake_win32_client.DispatchEx.call_count == 1
    fake_win32_client.DispatchEx.assert_called_once_with("ChemDraw.Application")
    assert fake_win32_client.Dispatch.call_count == 0
    fake_app.Quit.assert_called_once()
    assert len(results) == 1
    assert results[0]["path"] == str(cdxml_path)
    assert results[0]["cdx_data"] == b"FAKE_OUT"


# ---------------------------------------------------------------------------
# 2. Batch ChemDraw COM sessions in office_objects.py & ole_extractor.py
# ---------------------------------------------------------------------------


def test_office_objects_write_inspection_batches_multiple_records(tmp_path, monkeypatch):
    from PIL import Image

    source_docx = tmp_path / "input.docx"
    with zipfile.ZipFile(source_docx, "w") as zf:
        zf.writestr("[Content_Types].xml", "<Types/>")

    records = [
        {
            "object_id": "obj_001",
            "ordinal": 1,
            "location": "page_1",
            "ole_part": "word/embeddings/oleObject1.bin",
            "source_part": "word/document.xml",
            "_cdx_data": b"VjCD0100_A",
            "ole_size": 128,
            "cdx_size": 10,
        },
        {
            "object_id": "obj_002",
            "ordinal": 2,
            "location": "page_2",
            "ole_part": "word/embeddings/oleObject2.bin",
            "source_part": "word/document.xml",
            "_cdx_data": b"VjCD0100_B",
            "ole_size": 128,
            "cdx_size": 10,
        },
    ]

    batch_calls = []

    def _fake_batch_convert(records_arg):
        batch_calls.append(len(records_arg))
        return [
            "<CDXML><page id='1'/></CDXML>",
            "<CDXML><page id='2'/></CDXML>",
        ]

    session_entries = []

    class _FakeSession:
        def __enter__(self):
            session_entries.append("enter")
            return self

        def __exit__(self, exc_type, exc, tb):
            session_entries.append("exit")

        def render(self, cdxml_path, output_path, dpi=300):
            img = Image.new("RGB", (16, 16), color=(255, 255, 255))
            img.save(output_path, format="PNG")
            return str(output_path)

    monkeypatch.setattr(
        office_objects, "scan_office_objects", lambda src: ("deadbeef", records)
    )
    monkeypatch.setattr(office_objects, "_batch_convert_cdx_records", _fake_batch_convert)
    monkeypatch.setattr(office_objects.native_renderer, "NativeRenderSession", _FakeSession)

    out_dir = tmp_path / "bundle"
    result = office_objects.write_inspection(
        source_docx,
        out_dir,
        render_previews=True,
    )

    assert batch_calls == [2]
    assert session_entries == ["enter", "exit"]
    assert len(result["objects"]) == 2
    assert all(obj.get("cdxml") for obj in result["objects"])
    assert all(obj.get("preview_png") for obj in result["objects"])


def test_ole_extractor_batches_multiple_cdx_objects(tmp_path, monkeypatch):
    docx_path = tmp_path / "multi.docx"
    ole1 = ole_embedder.build_ole_compound_file(b"VjCD0100_ONE")
    ole2 = ole_embedder.build_ole_compound_file(b"VjCD0100_TWO")
    doc_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"
                xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
                xmlns:o="urn:schemas-microsoft-com:office:office">
      <w:body>
        <w:p><w:r><w:object><o:OLEObject r:id="rId1" ProgID="ChemDraw.Document.6.0"/></w:object></w:r></w:p>
        <w:p><w:r><w:object><o:OLEObject r:id="rId2" ProgID="ChemDraw.Document.6.0"/></w:object></w:r></w:p>
      </w:body>
    </w:document>"""
    rels_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
      <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/oleObject" Target="embeddings/oleObject1.bin"/>
      <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/oleObject" Target="embeddings/oleObject2.bin"/>
    </Relationships>"""
    with zipfile.ZipFile(docx_path, "w") as zf:
        zf.writestr("word/document.xml", doc_xml)
        zf.writestr("word/_rels/document.xml.rels", rels_xml)
        zf.writestr("word/embeddings/oleObject1.bin", ole1)
        zf.writestr("word/embeddings/oleObject2.bin", ole2)

    batch_calls = []

    class _FakeConverter:
        @staticmethod
        def batch_convert_files(input_paths, method="auto"):
            batch_calls.append(len(input_paths))
            out = {}
            for src in input_paths:
                dst = str(Path(src).with_suffix(".cdxml"))
                Path(dst).write_text("<CDXML/>", encoding="utf-8")
                out[src] = {"output": dst, "error": None}
            return out

    monkeypatch.setattr(ole_extractor, "_get_converter", lambda fmt: _FakeConverter)

    out_dir = tmp_path / "extracted"
    items = ole_extractor.extract_from_office(
        str(docx_path), output_dir=str(out_dir), output_format="cdxml"
    )
    assert batch_calls == [2]
    assert len(items) == 2
    assert all(item.cdxml_output and Path(item.cdxml_output).exists() for item in items)


# ---------------------------------------------------------------------------
# 3. Divergent Stacked Layout, Depiction Memoization, and Hydride Labels
# ---------------------------------------------------------------------------


def test_layout_divergent_stacked_branches_have_distinct_y_coordinates():
    scheme = SchemeDescriptor(
        layout="divergent",
        structures={
            "sm1": StructureRef(id="sm1", smiles="c1ccccc1Br"),
            "sm2": StructureRef(id="sm2", smiles="c1ccccc1Cl"),
            "sm3": StructureRef(id="sm3", smiles="c1ccccc1I"),
            "p1": StructureRef(id="p1", smiles="c1ccccc1C"),
            "p2": StructureRef(id="p2", smiles="c1ccccc1O"),
            "p3": StructureRef(id="p3", smiles="c1ccccc1N"),
        },
        steps=[
            StepDescriptor(
                substrates=["sm1"],
                products=["p1"],
                above_arrow=ArrowContent(text=["MeB(OH)2"]),
            ),
            StepDescriptor(
                substrates=["sm2"],
                products=["p2"],
                above_arrow=ArrowContent(text=["KOH"]),
            ),
            StepDescriptor(
                substrates=["sm3"],
                products=["p3"],
                above_arrow=ArrowContent(text=["NH3"]),
            ),
        ],
    )
    ids = renderer._IDGen(1000)
    xml_body, lowest_y = renderer._layout_divergent_stacked(scheme, ids)
    root = ET.fromstring(f"<page>{xml_body}</page>")

    # Extract y-centers of arrows across the 3 stacked branches
    arrow_ys = []
    for arrow in root.findall("arrow"):
        head = arrow.attrib.get("Head3D")
        if head:
            parts = [float(v) for v in head.split()]
            arrow_ys.append(parts[1])
        else:
            bb = [float(v) for v in arrow.attrib["BoundingBox"].split()]
            arrow_ys.append(0.5 * (bb[1] + bb[3]))

    assert len(arrow_ys) == 3
    # Every branch must have a distinct vertical y position (not stacked at 300.0)
    assert len({round(y, 1) for y in arrow_ys}) == 3
    sorted_ys = sorted(arrow_ys)
    assert sorted_ys[1] - sorted_ys[0] >= 50.0
    assert sorted_ys[2] - sorted_ys[1] >= 50.0
    assert lowest_y > sorted_ys[-1]


def test_renderer_smiles_to_fragment_data_memoization():
    renderer._depiction_cache.clear()
    atoms1, bonds1 = renderer._smiles_to_fragment_data("c1ccccc1O")
    assert len(renderer._depiction_cache) == 1

    atoms2, bonds2 = renderer._smiles_to_fragment_data("c1ccccc1O")
    assert atoms1 == atoms2
    assert bonds1 == bonds2
    # Mutating returned data must not corrupt cache
    atoms2[0]["x"] += 999.0
    atoms3, _ = renderer._smiles_to_fragment_data("c1ccccc1O")
    assert atoms3[0]["x"] == pytest.approx(atoms1[0]["x"])


def test_cdxml_builder_binary_hydride_labels_not_reversed():
    # Single-atom neutral water, HCl, H2S should format as H2O, HCl, H2S (not OH2, ClH, SH2)
    for sym, nh, expected in [
        ("O", 2, "H2O"),
        ("Cl", 1, "HCl"),
        ("S", 2, "H2S"),
        ("F", 1, "HF"),
        ("Br", 1, "HBr"),
        ("I", 1, "HI"),
    ]:
        atoms = [{"index": 1, "symbol": sym, "x": 200.0, "y": 300.0, "num_hydrogens": nh}]
        xml_str = cdxml_builder.build_molecule_cdxml(atoms, [])
        root = ET.fromstring(xml_str)
        texts = "".join(s.text or "" for s in root.iter("s"))
        assert texts == expected, f"Expected {expected} for {sym} with {nh} H, got {texts}"


# ---------------------------------------------------------------------------
# 4. Scientific Plots: 300-DPI default, UTF-8 labels, and Multi-Series
# ---------------------------------------------------------------------------


def test_scientific_plot_300_dpi_utf8_and_multi_series(tmp_path):
    x = np.linspace(0.0, 10.0, 50)
    y1 = np.sin(x)
    y2 = np.cos(x)

    out_dir = tmp_path / "multi_utf8_plot"
    spec = {
        "title": "1H NMR \u53e0\u52a0\u8c31\u56fe (δ ppm)",
        "xlabel": "\u5316\u5b66\u4f4d\u79fb δ (ppm)",
        "ylabel": "\u5f3a\u5ea6 (a.u.)",
        "reverse_x": True,
        "series": [
            {"x": x, "y": y1, "label": "\u6837\u54c1 A (δ)", "color": "#185f72", "style": "-"},
            {"x": x, "y": y2, "label": "\u6837\u54c1 B (\u5bf9\u7167)", "color": "#d95f02", "style": "--"},
        ],
    }

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        meta = sci_plots.plot_xy(spec, out_dir)
    assert meta["dpi"] == 300
    assert meta["series_count"] == 2
    assert (out_dir / "plot.png").exists()
    assert (out_dir / "plot.svg").exists()
    assert (out_dir / "plot.cdxml").exists()

    # Check PNG DPI metadata via PIL or matplotlib image size (8x3.8 inches @ 300 DPI -> ~2400x1140 px)
    from PIL import Image

    with Image.open(out_dir / "plot.png") as img:
        w, h = img.size
        assert w >= 2000 and h >= 900

    # Check CDXML UTF-8 font charset and curve count
    cdxml_bytes = (out_dir / "plot.cdxml").read_bytes()
    root = ET.fromstring(cdxml_bytes)
    font_el = root.find("./fonttable/font")
    assert font_el is not None
    assert font_el.attrib.get("charset") == "utf-8"

    all_text = " ".join((s.text or "") for s in root.iter("s"))
    assert "δ (ppm)" in all_text
    assert "\u6837\u54c1 A" in all_text
    assert "\u6837\u54c1 B" in all_text

    curves = root.findall("./page/curve")
    assert len(curves) >= 2


# ---------------------------------------------------------------------------
# 5. Image Module Imports & Periodic Table Element Symbols
# ---------------------------------------------------------------------------


def test_structure_from_image_results_to_cdxml_imports_cdxml_builder():
    mol_data = structure_from_image.smiles_to_coords("c1ccccc1", offset_index=0)
    assert mol_data is not None
    atoms, bonds = structure_from_image.normalize_for_cdxml(
        mol_data["atoms"], mol_data["bonds"]
    )
    cdxml_str = structure_from_image.results_to_cdxml(
        [{"smiles": "c1ccccc1", "atoms": atoms, "bonds": bonds}]
    )
    assert "<CDXML" in cdxml_str
    assert "<fragment" in cdxml_str


def test_structure_and_reaction_from_image_chemscript_bridge_import(monkeypatch):
    from cdxml_toolkit.chemdraw import chemscript_bridge

    fake_instance = mock.MagicMock()
    monkeypatch.setattr(chemscript_bridge, "ChemScriptBridge", mock.MagicMock(return_value=fake_instance))

    cs = reaction_from_image._open_chemscript_bridge(verbose=False)
    assert cs is fake_instance

    # Also verify results_to_cdxml_chemscript imports chemscript_bridge cleanly
    out = structure_from_image.results_to_cdxml_chemscript([], verbose=False)
    assert out == ""
    fake_instance.close.assert_called_once()


@pytest.mark.parametrize(
    ("symbol", "expected_z"),
    [
        ("Pd", 46),
        ("Cu", 29),
        ("Li", 3),
        ("B", 5),
        ("Si", 14),
    ],
)
def test_reaction_from_image_supports_transition_metals_and_main_group_elements(
    symbol: str, expected_z: int
):
    assert reaction_from_image.ELEMENT_NUMBERS.get(symbol) == expected_z
    assert cdxml_builder.ELEMENT_NUMBERS.get(symbol) == expected_z

    ids = reaction_from_image._IDGen(100)
    atoms = [{"index": 1, "symbol": symbol, "x": 150.0, "y": 200.0, "num_hydrogens": 0}]
    frag_xml, _ = reaction_from_image._build_fragment(atoms, [], ids)
    frag_el = ET.fromstring(frag_xml)
    node_el = frag_el.find("n")
    assert node_el is not None
    assert node_el.attrib.get("Element") == str(expected_z)
