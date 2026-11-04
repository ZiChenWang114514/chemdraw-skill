"""Tests for the Shimadzu LabSolutions .daml parser and pipeline wiring.

Fixture Attribution & License
-----------------------------
``tests/fixtures/shimadzu/socs2a_3peaks.daml`` and ``socs2a_0peaks.daml`` are
trimmed subsets of ``SOCS2A-478-RP3573-0.daml`` and ``SOCS2A-478-RP3573-1.daml``
from the GSK PyParse v1.1.0 example dataset (Joe Mason et al., Zenodo DOI:
10.5281/zenodo.10590646), distributed under the Apache License, Version 2.0.
"""

from __future__ import annotations

import base64
import csv
import json
from pathlib import Path

import pytest

from cdxml_toolkit.analysis import is_daml_path
from cdxml_toolkit.analysis.deterministic.discover_experiment_files import (
    discover_experiment_files,
)
from cdxml_toolkit.analysis.deterministic.multi_lcms_analyzer import (
    extract_run_datetime,
    main as multi_main,
)
from cdxml_toolkit.analysis.format_procedure_entry import process_entries
from cdxml_toolkit.analysis.lcms_analyzer import (
    format_table,
    is_manual_integration,
    is_waters_report,
    method_basename,
    parse_report,
    parse_reports,
)
from cdxml_toolkit.analysis.parse_analysis_file import parse_analysis_file
from cdxml_toolkit.analysis.shimadzu_daml import (
    is_shimadzu_daml,
    parse_daml,
    parse_daml_text,
    report_datetime,
)
from cdxml_toolkit.mcp_runtime.extended_tools import analyze_lcms_series

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "shimadzu"
FIXTURE_3PEAKS = FIXTURE_DIR / "socs2a_3peaks.daml"
FIXTURE_0PEAKS = FIXTURE_DIR / "socs2a_0peaks.daml"

REAL_SHIMADZU_DIR = Path(
    r"D:\lcms-samples\zenodo_PyParse_v1.1.0\extracted\example_dataset\Shimadzu"
)


def _b64(text: str) -> str:
    return base64.b64encode(text.encode("ascii")).decode("ascii")


def _build_synthetic_daml(
    *,
    sample_name: str = "EXP001-t0",
    sample_id: str = "SID-01",
    vial: str = "  12  ",
    instrument: str = "Shimadzu LCMS-2020",
    method: str = r"C:\LabSolutions\Data\Project1\5-95_acid_pos-neg_3min.lcm",
    timestamp: str = "9/28/2023 6:20:43 PM",
    chros_xml: str = "",
    spectra_xml: str = "",
    pda_xml: str = "",
) -> str:
    return f"""<?xml version="1.0" encoding="utf-8"?>
<DAML version="30" timestamp="{timestamp}">
  <datafile_attribs>
    <sample_name>{sample_name}</sample_name>
    <sample_id>{sample_id}</sample_id>
    <vial>{vial}</vial>
    <instrument>{instrument}</instrument>
    <method_file_name>{method}</method_file_name>
    <raw_datafile_last_write>{timestamp}</raw_datafile_last_write>
  </datafile_attribs>
  <results>
    <lc_chros>{chros_xml}</lc_chros>
    <spectra>{spectra_xml}</spectra>
    <pda_spectra>{pda_xml}</pda_spectra>
  </results>
</DAML>
"""


# ---------------------------------------------------------------------------
# Detection
# ---------------------------------------------------------------------------


def test_fixture_sizes_are_small():
    assert FIXTURE_3PEAKS.stat().st_size < 30_000
    assert FIXTURE_0PEAKS.stat().st_size < 10_000


def test_detection_accepts_valid_daml_and_rejects_non_daml(tmp_path, monkeypatch):
    assert is_daml_path(str(FIXTURE_3PEAKS))
    assert is_shimadzu_daml(str(FIXTURE_3PEAKS))
    assert is_shimadzu_daml(str(FIXTURE_0PEAKS))
    assert is_waters_report(str(FIXTURE_3PEAKS))

    # Case-insensitive .DAML and UTF-16 BOM
    upper_daml = tmp_path / "SAMPLE.DAML"
    upper_daml.write_bytes(b"\xff\xfe" + _build_synthetic_daml().encode("utf-16-le"))
    assert is_daml_path(str(upper_daml))
    assert is_shimadzu_daml(str(upper_daml))

    # Non-DAML XML with .daml extension (e.g. CDXML / SVG / wrapped tag)
    cdxml_fake = tmp_path / "not_shimadzu.daml"
    cdxml_fake.write_text('<?xml version="1.0"?><CDXML><page/></CDXML>', encoding="utf-8")
    assert is_daml_path(str(cdxml_fake))
    assert not is_shimadzu_daml(str(cdxml_fake))
    assert not is_waters_report(str(cdxml_fake))

    wrapped_fake = tmp_path / "wrapped.daml"
    wrapped_fake.write_text("<Wrapper><DAML version='30'/></Wrapper>", encoding="utf-8")
    assert not is_shimadzu_daml(str(wrapped_fake))

    # Valid DAML content with wrong extension
    wrong_ext = tmp_path / "sample.xml"
    wrong_ext.write_text(_build_synthetic_daml(), encoding="utf-8")
    assert not is_daml_path(str(wrong_ext))
    assert not is_shimadzu_daml(str(wrong_ext))

    # Directory and missing path
    daml_dir = tmp_path / "dir.daml"
    daml_dir.mkdir()
    assert not is_shimadzu_daml(str(daml_dir))
    assert not is_shimadzu_daml(str(tmp_path / "missing.daml"))

    # is_manual_integration returns False immediately without touching pdfplumber
    import pdfplumber

    monkeypatch.setattr(
        pdfplumber,
        "open",
        lambda *_a, **_kw: (_ for _ in ()).throw(AssertionError("pdfplumber called")),
    )
    assert not is_manual_integration(str(FIXTURE_3PEAKS))
    assert not is_manual_integration(str(cdxml_fake))


# ---------------------------------------------------------------------------
# Core parsing: Apache-2.0 fixtures & synthetic edge cases
# ---------------------------------------------------------------------------


def test_parse_trimmed_3peaks_fixture():
    report = parse_daml(str(FIXTURE_3PEAKS))
    assert report.source_format == "shimadzu_daml"
    assert report.filename == "socs2a_3peaks.daml"
    assert report.sample_name == "SOCS2A-478-RP3573-0"
    assert report.well == "1"
    assert report.instrument == "Shimadzu LC/MS"
    assert method_basename(report.method_path) == "5-95_acid_pos-neg_3min"
    assert report.detector == "UV 254nm"
    assert report.date == "2023-09-28"
    assert report.run_time is not None
    dt = report_datetime(report)
    assert dt is not None and dt.startswith("2023-09-28 ")

    assert len(report.peaks) == 3
    p3, p9, p10 = report.peaks

    # Peak 3: Product1 at 1.1582 min (8.62% area, [M+H]+ = 189.0 in ES+)
    # Fixture retains the nearby MS-TIC scan (peak_id=27 at 1.174 min); direct
    # peak_id=15 linking must win so 189.0 (63.6% BPI) stays in top_ions.
    assert p3.peak_num == "3"
    assert p3.rt == pytest.approx(1.1582, abs=1e-4)
    assert p3.area_pct == pytest.approx(8.6159, abs=0.01)
    assert p3.area_pct_254nm == pytest.approx(8.6159, abs=0.01)
    modes_p3 = {s.mode: s for s in p3.ms_spectra}
    assert set(modes_p3) == {"ES+", "ES-"}
    assert any(abs(mz - 189.0) < 0.1 for mz in modes_p3["ES+"].top_ions)
    assert all(i >= 20.0 for i in modes_p3["ES+"].intensities)
    assert p3.uv_lambda_max == [217.0]

    # Peak 9: 1.7483 min, dual PDA maxima at 232 & 290 nm (negative 190-205 nm ignored)
    assert p9.peak_num == "9"
    assert p9.rt == pytest.approx(1.7483, abs=1e-4)
    assert p9.uv_lambda_max == [232.0, 290.0]

    # Peak 10: major peak at 2.1351 min (54.59%)
    assert p10.peak_num == "10"
    assert p10.area_pct == pytest.approx(54.5901, abs=0.01)
    assert p10.uv_lambda_max == [257.0]

    table = format_table(report)
    assert "**Area basis:** UV 254nm" in table
    assert "| 3 | 1.16 |" in table


def test_parse_0peaks_fixture():
    report = parse_daml(str(FIXTURE_0PEAKS))
    assert report.source_format == "shimadzu_daml"
    assert report.peaks == []
    assert report.well == "13"
    assert "(no peaks detected)" in format_table(report)


def test_parse_daml_rejects_non_daml_xml():
    with pytest.raises(ValueError, match="Expected <DAML>"):
        parse_daml_text("<CDXML><page/></CDXML>", filename="bad.daml")
    with pytest.raises(ValueError, match="Invalid XML"):
        parse_daml_text("<DAML><unclosed>", filename="broken.daml")


def test_multi_wavelength_merge_ms_dedup_ms2_filter_and_uv_baseline():
    # Channel 1: 254 nm (2 peaks at 1.000 min and 2.000 min)
    pk1_254 = _b64("Version=2;ID=101;PN=1;ApRT=60000;StRT=58000;EdRT=62000;A=5000;APc=40.0;Hgt=1200")
    pk2_254 = _b64("Version=2;ID=102;PN=2;ApRT=120000;StRT=118000;EdRT=122000;A=7500;APc=60.0;Hgt=1800")
    # Channel 2: 220 nm (peak at 1.012 min merges within 0.02 min; peak at 2.500 min is 220nm-only)
    pk1_220 = _b64("Version=2;ID=201;PN=1;ApRT=60720;A=10000;APc=80.0;Hgt=2400")
    pk3_220 = _b64("Version=2;ID=202;PN=2;ApRT=150000;A=2500;APc=20.0;Hgt=600")

    chros_xml = f"""
      <chro><wavelength>254</wavelength>
        <peak><data>{pk1_254}</data></peak>
        <peak><data>{pk2_254}</data></peak>
      </chro>
      <chro><wavelength>220</wavelength>
        <peak><data>{pk1_220}</data></peak>
        <peak><data>{pk3_220}</data></peak>
      </chro>
    """

    # Spectra:
    # - Two ES+ MS1 scans on peak 101: lower BPI (1000) vs higher BPI (9000) -> 9000 wins, no duplicate ES+
    # - One MS2 scan (ms_stage=2) on peak 101 -> ignored
    # - One ES- MS1 scan with peak_id=0 at RT 2.015 min (120900 ms, within 0.03 min of peak 2) -> RT fallback
    sp_low = _b64("t1;t2;m/z;Int;3010000;1000;1500000;500")
    sp_high = _b64("t1;t2;m/z;Int;3461200;9000;3681000;2700;1990000;900")  # 199.0 is 10% < 20% cutoff
    sp_ms2 = _b64("t1;t2;m/z;Int;1200000;99999")
    sp_rt_fallback = _b64("t1;t2;m/z;Int;4441000;5000")

    spectra_xml = f"""
      <spec><id>1</id><peak_id>101</peak_id><rt>60100</rt><polarity>0</polarity><ms_stage>1</ms_stage><data>{sp_low}</data></spec>
      <spec><id>2</id><peak_id>101</peak_id><rt>60050</rt><polarity>0</polarity><ms_stage>1</ms_stage><data>{sp_high}</data></spec>
      <spec><id>3</id><peak_id>101</peak_id><rt>60000</rt><polarity>0</polarity><ms_stage>2</ms_stage><data>{sp_ms2}</data></spec>
      <spec><id>4</id><peak_id>0</peak_id><rt>120900</rt><polarity>1</polarity><ms_stage></ms_stage><data>{sp_rt_fallback}</data></spec>
    """

    # PDA spectrum on peak 201 (merged with peak 101!): huge negative dip at 195-205 nm, real peak at 254 nm
    uv_pts = []
    for wl in range(190, 321, 2):
        if wl < 210:
            y = -500000.0 if wl == 198 else -200000.0
        else:
            y = max(0.0, 10000.0 - ((wl - 254) ** 2) * 40.0)
        uv_pts.extend([str(wl * 100), f"{y:.1f}"])
    pda_data = _b64("1.00;1.00;;;" + ";".join(uv_pts))
    pda_xml = f"<pda_spec><id>10</id><peak_id>201</peak_id><rt>60720</rt><data>{pda_data}</data></pda_spec>"

    xml_text = _build_synthetic_daml(
        sample_name="",
        sample_id="",
        vial="  B4 ",
        timestamp="2024-03-15 14:05:09",
        chros_xml=chros_xml,
        spectra_xml=spectra_xml,
        pda_xml=pda_xml,
    )
    report = parse_daml_text(xml_text, filename="FallbackStem.daml")

    assert report.sample_name == "FallbackStem"
    assert report.well == "B4"
    assert report.detector == "PDA"
    assert report_datetime(report) == "2024-03-15 14:05:09"
    assert len(report.peaks) == 3

    pk_a, pk_b, pk_c = report.peaks
    assert pk_a.rt == pytest.approx(1.0, abs=1e-4)
    assert pk_a.area == pytest.approx(5000.0)
    assert pk_a.area_pct == pytest.approx(40.0)
    assert pk_a.area_254nm == pytest.approx(5000.0)
    assert pk_a.area_pct_254nm == pytest.approx(40.0)
    assert pk_a.area_220nm == pytest.approx(10000.0)
    assert pk_a.area_pct_220nm == pytest.approx(80.0)
    assert len(pk_a.ms_spectra) == 1
    assert pk_a.ms_spectra[0].mode == "ES+"
    assert pk_a.ms_spectra[0].top_ions == [346.12, 368.1]
    assert pk_a.uv_lambda_max == [254.0]

    assert pk_b.rt == pytest.approx(2.0, abs=1e-4)
    assert len(pk_b.ms_spectra) == 1
    assert pk_b.ms_spectra[0].mode == "ES-"
    assert pk_b.ms_spectra[0].top_ions == [444.1]

    # 220nm-only peak preserved with fallback primary area
    assert pk_c.rt == pytest.approx(2.5, abs=1e-4)
    assert pk_c.area_pct_220nm == pytest.approx(20.0)
    assert pk_c.area_pct == pytest.approx(20.0)


# ---------------------------------------------------------------------------
# Pipeline integration
# ---------------------------------------------------------------------------


def test_pipeline_parse_format_series_and_discovery(tmp_path):
    # 1. parse_report / parse_reports / parse_analysis_file
    r_single = parse_report(str(FIXTURE_3PEAKS))
    r_list = parse_reports(str(FIXTURE_3PEAKS))
    assert len(r_list) == 1 and r_list[0].peaks == r_single.peaks

    parsed = parse_analysis_file(str(FIXTURE_3PEAKS))
    assert parsed["ok"] is True
    assert parsed["file_type"] == "lcms"
    assert parsed["data"]["source_format"] == "shimadzu_daml"
    assert len(parsed["data"]["peaks"]) == 3

    # Bogus .daml returns ok=False cleanly and raises ValueError in parse_report
    bad_daml = tmp_path / "RXN100-bad.daml"
    bad_daml.write_text("<not_daml/>", encoding="utf-8")
    bad_res = parse_analysis_file(str(bad_daml))
    assert bad_res["ok"] is False
    with pytest.raises(ValueError, match="Shimadzu"):
        parse_report(str(bad_daml))

    # 2. format_procedure_entry
    entry_text = process_entries(
        [
            {
                "type": "lcms-species",
                "file": str(FIXTURE_3PEAKS),
                "label": "Crude",
                "peaks": [
                    {"name": "Product1", "rt": 1.16, "ion": {"mode": "ES+", "mz": 189.0}},
                    {"name": "Byproduct", "rt": 2.14, "ion": {"mode": "ES+", "mz": 120.1}},
                ],
            },
            {
                "type": "lcms-areas",
                "file": str(FIXTURE_3PEAKS),
                "label": "Crude",
                "detector": "254nm",
                "peaks": [
                    {"name": "Product1", "rt": 1.16, "compound_related": True},
                    {"name": "Byproduct", "rt": 2.14, "compound_related": True},
                ],
            },
        ]
    )
    assert "Product1" in entry_text
    assert "1.16 min" in entry_text
    assert "ESI+ 160.8" in entry_text
    assert "Product1 8.6%, Byproduct 54.6%" in entry_text

    # 3. Series tracking via multi_lcms_analyzer & extended_tools.analyze_lcms_series
    exp_dir = tmp_path / "exp"
    exp_dir.mkdir()
    (exp_dir / "RXN100.csv").write_text(
        "EXPERIENCE_NAME;DESCRIPTION\nRXN100;Test reaction\n", encoding="utf-8"
    )
    sp_sm = _b64("t1;t2;m/z;Int;2001000;9000")
    sp_dp = _b64("t1;t2;m/z;Int;3001000;9000")
    spec_xml = (
        f"<spec><id>1</id><peak_id>1</peak_id><rt>60000</rt><polarity>0</polarity><ms_stage>1</ms_stage><data>{sp_sm}</data></spec>"
        f"<spec><id>2</id><peak_id>2</peak_id><rt>108000</rt><polarity>0</polarity><ms_stage>1</ms_stage><data>{sp_dp}</data></spec>"
    )

    t0_path = exp_dir / "RXN100-0min.daml"
    t30_path = exp_dir / "RXN100-30min.daml"
    for path, sm_pct, dp_pct, ts in (
        (t0_path, 85.0, 15.0, "9/28/2023 1:00:00 PM"),
        (t30_path, 20.0, 80.0, "9/28/2023 1:30:00 PM"),
    ):
        p_sm = _b64(f"Version=2;ID=1;PN=1;ApRT=60000;A={sm_pct * 100};APc={sm_pct};Hgt=1000")
        p_dp = _b64(f"Version=2;ID=2;PN=2;ApRT=108000;A={dp_pct * 100};APc={dp_pct};Hgt=1000")
        chro = f"<chro><wavelength>254</wavelength><peak><data>{p_sm}</data></peak><peak><data>{p_dp}</data></peak></chro>"
        path.write_text(
            _build_synthetic_daml(
                sample_name=path.stem,
                timestamp=ts,
                chros_xml=chro,
                spectra_xml=spec_xml,
            ),
            encoding="utf-8",
        )
    # Also drop a bogus .daml in exp_dir to ensure discovery skips it
    (exp_dir / "RXN100-notdaml.daml").write_text("<svg/>", encoding="utf-8")

    assert extract_run_datetime(str(t0_path)) == "2023-09-28 13:00:00"

    out_json = tmp_path / "series.json"
    rc = multi_main([str(t0_path), str(t30_path), "--json-output", str(out_json)])
    assert rc == 0
    series_data = json.loads(out_json.read_text(encoding="utf-8"))
    trends = {round(c["canonical_rt"], 1): c["trend"] for c in series_data["compounds"]}
    assert trends[1.0] == "decreasing"
    assert trends[1.8] == "increasing"

    mcp_res = analyze_lcms_series(
        [str(t0_path), str(t30_path)],
        output_path=str(tmp_path / "mcp_series.json"),
    )
    assert mcp_res["ok"] is True
    assert mcp_res["metadata"]["file_count"] == 2

    # 4. discover_experiment_files
    disc = discover_experiment_files(str(exp_dir))
    found_names = [Path(lf.path).name for lf in disc.lcms_files]
    assert found_names == ["RXN100-0min.daml", "RXN100-30min.daml"]


# ---------------------------------------------------------------------------
# Real local dataset validation (skipped when D:\lcms-samples is absent)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not REAL_SHIMADZU_DIR.is_dir(),
    reason="Local Zenodo PyParse Shimadzu dataset not present on D:",
)
def test_all_17_zenodo_pyparse_shimadzu_files_and_compoundtable():
    daml_files = sorted(
        REAL_SHIMADZU_DIR.glob("SOCS2A-478-RP3573-*.daml"),
        key=lambda p: int(p.stem.rsplit("-", 1)[-1]),
    )
    assert len(daml_files) == 17

    by_well = {}
    for fpath in daml_files:
        assert is_shimadzu_daml(str(fpath))
        rep = parse_daml(str(fpath))
        assert rep.source_format == "shimadzu_daml"
        assert report_datetime(rep) is not None
        idx = int(fpath.stem.rsplit("-", 1)[-1])
        if idx in (1, 16):
            assert rep.peaks == []
        else:
            assert len(rep.peaks) >= 1
        # Map 1-based 96-well vial number (12 cols/row) -> e.g. 1='A1', 13='B1', 2='A2'
        vial_num = int(rep.well)
        well_label = f"{chr(65 + (vial_num - 1) // 12)}{(vial_num - 1) % 12 + 1}"
        by_well[well_label] = rep

    ct_path = REAL_SHIMADZU_DIR / "output" / "compoundtable.csv"
    with open(ct_path, "r", encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))

    matched_products = 0
    for row in rows:
        well = row["best_well"].strip()
        if well not in by_well:
            continue
        matched_products += 1
        target_rt = float(row["time"])
        target_purity = float(row["best_purity"])
        rep = by_well[well]
        pk = min(rep.peaks, key=lambda p: abs(p.rt - target_rt))
        assert abs(pk.rt - target_rt) <= 0.04
        assert pk.area_pct == pytest.approx(target_purity, abs=0.011)

        if row["name"].startswith("Product"):
            if row["mass+"] not in ("-", ""):
                expected_pos = float(row["mass+"])
                es_pos = next(s for s in pk.ms_spectra if s.mode == "ES+")
                assert any(abs(mz - expected_pos) < 0.011 for mz in es_pos.top_ions)
            if row["mass-"] not in ("-", "") and well != "D1":
                # D1's ESI- ion (172.85) is 9.3% of base peak, below 20% threshold
                expected_neg = float(row["mass-"])
                es_neg = next(s for s in pk.ms_spectra if s.mode == "ES-")
                assert any(abs(mz - expected_neg) < 0.011 for mz in es_neg.top_ions)

    assert matched_products >= 14
