"""Tests for the Agilent ChemStation report.txt parser and pipeline wiring."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cdxml_toolkit.analysis import is_agilent_txt_path
from cdxml_toolkit.analysis.agilent_txt import (
    decode_agilent_txt,
    is_agilent_report_txt,
    parse_agilent_txt,
    parse_agilent_txt_text,
    report_datetime,
)
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
from cdxml_toolkit.mcp_runtime.extended_tools import analyze_lcms_series

REAL_NAVY_D_DIR = Path(r"D:\lcms-samples\rainbow_tests\navy.D")


SINGLE_SIGNAL_REPORT = """\
Data File C:\\Chem32\\1\\Data\\Batch01\\007-P1-A03-SYNTH-CMPD-07.D
Sample Name: SYNTH-CMPD-07
LCMSD 5/24/2021 4:05:19 PM Chemist
=====================================================================
Acq. Operator : Chemist                               Seq. Line :   7
Acq. Instrument : Agilent1260                          Location :   P1-A03
Injection Date : 5/24/2021 3:59:11 PM                       Inj :   1
                                                     Inj Volume : 2.000 \u00b5l
Method         : C:\\Chem32\\1\\Methods\\FAST_GRAD_2MIN.M (Sequence
                 Method)
=====================================================================
                         Area Percent Report
=====================================================================

Sorted By             :      Signal
Multiplier            :      1.0000
Dilution              :      1.0000

Peak RetTime Sig Type     Area      Height     Area
  #   [min]             [mAU*s]     [mAU]        %
----|-------|---|----|----------|----------|--------|
   1   0.542  1  BV    215.40000   42.10000   1.7301
   2   1.318  1  MM R  1.22350e4 2890.55000  98.2699
Totals :               1.24504e4 2932.65000

=====================================================================
                         *** End of Report ***
"""


MULTI_SIGNAL_REPORT = """\
Data File : C:\\Chem32\\1\\Data\\Tracking\\EXP200_t15.D
Sample Name :
LCMSD 24-May-21, 16:10:00 Operator
=====================================================================
Acq. Operator : Operator                              Seq. Line :   2
                                                       Location :   Vial 4
Injection Date : 24-May-21, 16:05:30                        Inj :   1
Acq. Method    : C:\\Chem32\\1\\Methods\\CSH_C18_AmF_5to100_2min.M
=====================================================================
                         Area Percent Report
=====================================================================

Signal 1: DAD1 A, Sig=254,4 Ref=360,100

Peak RetTime Type  Width     Area      Height     Area
  #   [min]       [min]   [mAU*s]     [mAU]        %
----|-------|----|-------|----------|----------|--------|
   1   0.810 BB    0.0320   400.0000   95.0000  25.0000
   2   1.520 BBA   0.0450  1200.0000  310.0000  75.0000
Totals :                   1600.0000  405.0000

Signal 2: DAD1 B, Sig=220,4 Ref=off

Peak RetTime Type  Width     Area      Height     Area
  #   [min]       [min]   [mAU*s]     [mAU]        %
----|-------|----|-------|----------|----------|--------|
   1   0.822 BV    0.0330   800.0000  180.0000  32.0000
   2   1.515 MM R  0.0460  1500.0000  380.0000  60.0000
   3   2.105 BB    0.0400   200.0000   45.0000   8.0000
Totals :                   2500.0000  605.0000

=====================================================================
                         *** End of Report ***
"""


NO_PEAKS_REPORT = """\
Data File C:\\Chem32\\1\\Data\\Blank\\BLANK-01.D
Sample Name: Solvent-Blank
1290UHPLC 2024-06-01 09:12:05 SYSTEM
=====================================================================
Acq. Operator : SYSTEM
VWD1 A, Wavelength=254 nm
=====================================================================
                       External Standard Report
=====================================================================

Signal 1: VWD1 A, Wavelength=254 nm

No peaks found

=====================================================================
                         *** End of Report ***
"""


# ---------------------------------------------------------------------------
# Decoding & detection
# ---------------------------------------------------------------------------


def test_decode_agilent_txt_encodings_and_newlines():
    raw_text = "Line1\r\nInjection Volume : 1.0 \u00b5l\r\n"
    expected = "Line1\nInjection Volume : 1.0 \u00b5l\n"

    # UTF-16 LE BOM, UTF-16 BE BOM, UTF-8 BOM, cp1252
    assert decode_agilent_txt(b"\xff\xfe" + raw_text.encode("utf-16-le")) == expected
    assert decode_agilent_txt(b"\xfe\xff" + raw_text.encode("utf-16-be")) == expected
    assert decode_agilent_txt(raw_text.encode("utf-8-sig")) == expected
    assert decode_agilent_txt(raw_text.encode("cp1252")) == expected


def test_detection_accepts_agilent_reports_and_rejects_other_txt(tmp_path, monkeypatch):
    utf16_rep = tmp_path / "report.TXT"
    utf16_rep.write_bytes(
        b"\xff\xfe" + SINGLE_SIGNAL_REPORT.replace("\n", "\r\n").encode("utf-16-le")
    )
    assert is_agilent_txt_path(str(utf16_rep))
    assert is_agilent_report_txt(str(utf16_rep))
    assert is_waters_report(str(utf16_rep))

    # Norm Percent / Internal Standard banners with Signal + RetTime + [min]
    norm_rep = tmp_path / "norm.txt"
    norm_rep.write_text(
        "Norm Percent Report\nSignal 1: DAD1 A, Sig=254,4\nPeak RetTime [min] Area %\n",
        encoding="utf-8",
    )
    assert is_agilent_report_txt(str(norm_rep))

    # Random non-Agilent .txt files MUST return False
    notes_txt = tmp_path / "reaction_notes.txt"
    notes_txt.write_text(
        "Added 2 eq of K2CO3 and stirred at 80 C overnight. RetTime ~ 1.2 min.\n",
        encoding="utf-8",
    )
    banner_only = tmp_path / "banner_only.txt"
    banner_only.write_text("Area Percent Report\nNothing else here.\n", encoding="utf-8")

    for non_rep in (notes_txt, banner_only):
        assert not is_agilent_report_txt(str(non_rep))
        assert not is_waters_report(str(non_rep))

    # Wrong extension, directory, missing file
    wrong_ext = tmp_path / "report.log"
    wrong_ext.write_text(SINGLE_SIGNAL_REPORT, encoding="utf-8")
    assert not is_agilent_txt_path(str(wrong_ext))
    assert not is_agilent_report_txt(str(wrong_ext))

    d_txt = tmp_path / "folder.txt"
    d_txt.mkdir()
    assert not is_agilent_report_txt(str(d_txt))
    assert not is_agilent_report_txt(str(tmp_path / "does_not_exist.txt"))

    # pdfplumber and NMR extraction must NEVER run on .txt files
    import pdfplumber
    from cdxml_toolkit.analysis.deterministic import procedure_writer

    monkeypatch.setattr(
        pdfplumber,
        "open",
        lambda *_a, **_kw: (_ for _ in ()).throw(AssertionError("pdfplumber called on .txt")),
    )
    monkeypatch.setattr(
        procedure_writer,
        "extract_nmr_data",
        lambda *_a, **_kw: (_ for _ in ()).throw(AssertionError("extract_nmr_data called on .txt")),
    )
    assert not is_manual_integration(str(utf16_rep))
    assert not is_manual_integration(str(notes_txt))
    assert not is_waters_report(str(notes_txt))
    res_bad = parse_analysis_file(str(notes_txt))
    assert res_bad["ok"] is False


# ---------------------------------------------------------------------------
# Core parsing: single-signal, multi-signal, scientific notation, 0-peak
# ---------------------------------------------------------------------------


def test_parse_single_signal_table_and_scientific_notation(tmp_path):
    p = tmp_path / "report.txt"
    p.write_bytes(b"\xff\xfe" + SINGLE_SIGNAL_REPORT.encode("utf-16-le"))
    report = parse_agilent_txt(str(p))

    assert report.source_format == "agilent_chemstation_txt"
    assert report.sample_name == "SYNTH-CMPD-07"
    assert report.instrument == "Agilent1260"
    assert report.well == "P1-A03"
    assert method_basename(report.method_path) == "fast_grad_2min"
    assert report.date == "2021-05-24"
    assert report.run_time == "15:59:11"
    assert report_datetime(report) == "2021-05-24 15:59:11"

    assert len(report.peaks) == 2
    pk1, pk2 = report.peaks
    assert pk1.peak_num == "1"
    assert pk1.rt == pytest.approx(0.542)
    assert pk1.area == pytest.approx(215.4)
    assert pk1.area_pct == pytest.approx(1.7301)
    assert pk1.ms_spectra == []

    # Scientific notation 1.22350e4 and multi-token peak type "MM R"
    assert pk2.peak_num == "2"
    assert pk2.rt == pytest.approx(1.318)
    assert pk2.area == pytest.approx(12235.0)
    assert pk2.height == pytest.approx(2890.55)
    assert pk2.area_pct == pytest.approx(98.2699)


def test_parse_multi_signal_merges_254_and_220_within_rt_tolerance():
    report = parse_agilent_txt_text(MULTI_SIGNAL_REPORT, filename="report.txt")

    # Empty Sample Name falls back to .D stem; missing Acq. Instrument falls back to line 3
    assert report.sample_name == "EXP200_t15"
    assert report.instrument == "LCMSD"
    assert report.well == "Vial 4"
    assert report.detector == "DAD"
    assert method_basename(report.method_path) == "csh_c18_amf_5to100_2min"
    assert report.method_short == "CSH C18, AmF, 5-100%, 2 min"
    assert report_datetime(report) == "2021-05-24 16:05:30"

    assert len(report.peaks) == 3
    p1, p2, p3 = report.peaks

    # Peak 1: 0.810 min (254nm) merged with 0.822 min (220nm, delta=0.012 <= 0.02)
    assert p1.rt == pytest.approx(0.810)
    assert p1.width == pytest.approx(0.032)
    assert p1.area_pct == pytest.approx(25.0)
    assert p1.area_pct_254nm == pytest.approx(25.0)
    assert p1.area_pct_220nm == pytest.approx(32.0)

    # Peak 2: 1.520 min (BBA) merged with 1.515 min (MM R, delta=0.005 <= 0.02)
    assert p2.rt == pytest.approx(1.520)
    assert p2.area_254nm == pytest.approx(1200.0)
    assert p2.area_pct_254nm == pytest.approx(75.0)
    assert p2.area_220nm == pytest.approx(1500.0)
    assert p2.area_pct_220nm == pytest.approx(60.0)

    # Peak 3: 2.105 min present only in 220nm signal
    assert p3.rt == pytest.approx(2.105)
    assert p3.area_254nm is None
    assert p3.area_pct_220nm == pytest.approx(8.0)
    assert p3.area_pct == pytest.approx(8.0)

    table = format_table(report)
    assert "| 1 | 0.81 | 25.0 | 32.0 | 25.0 |" in table


def test_parse_0_peaks_no_peaks_found_report():
    report = parse_agilent_txt_text(NO_PEAKS_REPORT, filename="blank.txt")
    assert report.sample_name == "Solvent-Blank"
    assert report.instrument == "1290UHPLC"
    assert report.detector == "UV 254nm"
    assert report_datetime(report) == "2024-06-01 09:12:05"
    assert report.peaks == []


# ---------------------------------------------------------------------------
# Pipeline integration (.txt and .D/report.txt)
# ---------------------------------------------------------------------------


def test_pipeline_parse_format_series_and_d_folder_discovery(tmp_path):
    # Create two .D directories for timepoints t0 and 30min + an unrelated .txt
    exp_dir = tmp_path / "EXP300"
    exp_dir.mkdir()
    (exp_dir / "EXP300.csv").write_text(
        "EXPERIENCE_NAME;DESCRIPTION\nEXP300;Suzuki coupling\n", encoding="utf-8"
    )
    (exp_dir / "EXP300_notes.txt").write_text("Random lab note text\n", encoding="utf-8")

    def _make_d_report(folder_name: str, inj_dt: str, sm_pct: float, dp_pct: float) -> Path:
        d_dir = exp_dir / folder_name
        d_dir.mkdir()
        txt = f"""\
Data File C:\\Chem32\\1\\Data\\{folder_name}
Sample Name: {folder_name[:-2]}
Acq. Operator : Chemist
Acq. Instrument : 1290UHPLC                            Location :   P1-B01
Injection Date : {inj_dt}                                   Inj :   1
Method         : C:\\Chem32\\1\\Methods\\GRAD_3MIN.M
=====================================================================
                         Area Percent Report
=====================================================================

Signal 1: DAD1 A, Sig=254,4 Ref=off

Peak RetTime Type  Width     Area      Height     Area
  #   [min]       [min]   [mAU*s]     [mAU]        %
----|-------|----|-------|----------|----------|--------|
   1   0.750 BB    0.0300  {sm_pct * 10:8.3f}   100.000  {sm_pct:7.4f}
   2   1.480 BB    0.0400  {dp_pct * 10:8.3f}   200.000  {dp_pct:7.4f}
Totals :                   1000.000   300.000
"""
        rpath = d_dir / "report.txt"
        rpath.write_bytes(b"\xff\xfe" + txt.encode("utf-16-le"))
        # Add a non-report .txt inside .D to verify it is ignored
        (d_dir / "acq_methhist.txt").write_text("Method history log\n", encoding="utf-8")
        return rpath

    r_t0 = _make_d_report("EXP300_0min.D", "5/24/2021 10:00:00 AM", 90.0, 10.0)
    r_t30 = _make_d_report("EXP300_30min.D", "5/24/2021 10:30:00 AM", 15.0, 85.0)

    # 1. parse_report / parse_reports / parse_analysis_file
    rep0 = parse_report(str(r_t0))
    assert rep0.sample_name == "EXP300_0min"
    assert len(parse_reports(str(r_t0))) == 1

    paf = parse_analysis_file(str(r_t30))
    assert paf["ok"] is True
    assert paf["file_type"] == "lcms"
    assert paf["data"]["source_format"] == "agilent_chemstation_txt"

    with pytest.raises(ValueError, match="Agilent"):
        parse_report(str(exp_dir / "EXP300_notes.txt"))

    # 2. format_procedure_entry (UV-only peaks render cleanly)
    formatted = process_entries(
        [
            {
                "type": "lcms-species",
                "file": str(r_t30),
                "label": "t = 30 min",
                "peaks": [{"name": "Product", "rt": 1.48, "purity": True, "detector": "254nm"}],
            },
            {
                "type": "lcms-areas",
                "file": str(r_t30),
                "label": "t = 30 min",
                "detector": "254nm",
                "peaks": [
                    {"name": "SM", "rt": 0.75, "compound_related": True},
                    {"name": "Product", "rt": 1.48, "compound_related": True},
                ],
            },
        ]
    )
    assert "Product" in formatted
    assert "UV only" in formatted
    assert "85.0%" in formatted

    # 3. multi_lcms_analyzer & extended_tools.analyze_lcms_series on .D/report.txt
    assert extract_run_datetime(str(r_t0)) == "2021-05-24 10:00:00"
    series_out = tmp_path / "agilent_series.json"
    rc = multi_main([str(r_t0), str(r_t30), "--json-output", str(series_out)])
    assert rc == 0
    sdata = json.loads(series_out.read_text(encoding="utf-8"))
    trends = {round(c["canonical_rt"], 2): c["trend"] for c in sdata["compounds"]}
    assert trends[0.75] == "decreasing"
    assert trends[1.48] == "increasing"

    mcp_res = analyze_lcms_series(
        [str(r_t0), str(r_t30)],
        output_path=str(tmp_path / "mcp_agilent.json"),
    )
    assert mcp_res["ok"] is True

    # 4. discover_experiment_files: both single-experiment mode and parent-dir mode
    disc_single = discover_experiment_files(str(exp_dir))
    assert [Path(lf.path) for lf in disc_single.lcms_files] == [r_t0, r_t30]
    assert [lf.category for lf in disc_single.lcms_files] == ["tracking", "tracking"]

    # Add another experiment's .D folder in parent tmp_path to verify prefix filtering
    other_d = tmp_path / "OTHER999_t0.D"
    other_d.mkdir()
    (other_d / "report.txt").write_text(SINGLE_SIGNAL_REPORT, encoding="utf-8")
    disc_parent = discover_experiment_files(str(tmp_path), experiment_name="EXP300")
    assert [Path(lf.path) for lf in disc_parent.lcms_files] == [r_t0, r_t30]


# ---------------------------------------------------------------------------
# Real local sample validation (skipped when D:\lcms-samples is absent)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not (REAL_NAVY_D_DIR / "report.txt").is_file(),
    reason="Local rainbow navy.D sample not present on D:",
)
def test_real_navy_d_report_txt_and_sibling_txt_rejection():
    report_path = REAL_NAVY_D_DIR / "report.txt"
    assert is_agilent_report_txt(str(report_path))

    # Non-report .txt files in the same .D directory must be rejected
    for sibling in ("acq_methhist.txt", "scstate.txt"):
        sib_path = REAL_NAVY_D_DIR / sibling
        if sib_path.is_file():
            assert not is_agilent_report_txt(str(sib_path))

    rep = parse_report(str(report_path))
    assert rep.source_format == "agilent_chemstation_txt"
    assert rep.sample_name == "DEMO-SAMPLE-23"
    assert rep.instrument == "1290UHPLC"
    assert rep.well == "D3F-B11"
    assert method_basename(rep.method_path) == "demo_isocratic"
    assert report_datetime(rep) == "2024-01-26 19:36:13"

    assert len(rep.peaks) == 2
    assert rep.peaks[0].rt == pytest.approx(0.708)
    assert rep.peaks[0].area_pct == pytest.approx(1.0227)
    assert rep.peaks[1].rt == pytest.approx(1.239)
    assert rep.peaks[1].area == pytest.approx(12242.4)
    assert rep.peaks[1].area_pct == pytest.approx(70.2641)
