"""OpenLynx .rpt support: parser, routing through the LCMS entry points.

The fixtures under ``tests/fixtures/openlynx`` are trimmed copies of public
sample exports (instrument log and chromatogram traces removed, spectra kept):

- ``waters_qda_*.rpt``: Waters ACQUITY QDa batch (PyParse example dataset,
  Example1 = 24-well plate of quinoline products, Example2 = 48-well plate).
- ``xevo_qtof_2samples.rpt``: Xevo G2-XS QTof protein run, MS TIC trace only.

Expected retention times, masses and Area %Total come from the reference
tool's own output tables (``output/compoundtable.csv``), copied below.  The
opt-in test at the end checks the complete files when they are on disk
(``CDX_LCMS_SAMPLES`` or ``D:\\lcms-samples``).
"""

from __future__ import annotations

import csv
import json
import os
import shutil
from pathlib import Path

import pytest

from cdxml_toolkit.analysis.lcms_analyzer import (
    LCMSReport,
    format_basic_report,
    format_table,
    is_waters_report,
    parse_report,
    parse_reports,
)
from cdxml_toolkit.analysis.openlynx_rpt import (
    count_rpt_samples,
    decode_rpt,
    is_openlynx_rpt,
    parse_rpt_text,
    report_datetime,
)

FIXTURES = Path(__file__).parent / "fixtures" / "openlynx"
PLATE4 = FIXTURES / "waters_qda_4samples.rpt"
SINGLE = FIXTURES / "waters_qda_single.rpt"
PLATE_SUBSET = FIXTURES / "waters_qda_plate_subset.rpt"
XEVO = FIXTURES / "xevo_qtof_2samples.rpt"

# well -> (RT, ESI+ mass, ESI- mass or None, Area %Total) from compoundtable.csv
EXAMPLE1_EXPECTED = {
    "4:1": (1.23, 243.94, None, 100.0),
    "4:2": (1.30, 240.05, None, 98.93),
    "4:3": (0.59, 202.13, 200.21, 100.0),
    "4:4": (0.55, 202.16, 200.05, 98.21),
}
EXAMPLE2_EXPECTED = {
    "3:31": (1.01, 354.32, 352.11, 61.77),   # C7  Byproduct1
    "3:34": (1.04, 208.11, None, 61.89),     # C10 Reactant1
    "3:36": (0.73, 227.24, None, 39.06),     # C12 Product1
    "3:46": (1.49, 274.28, None, 23.31),     # D10 InternalSTD
}


def _peak_at(report: LCMSReport, rt: float):
    hits = [p for p in report.peaks if abs(p.rt - rt) < 0.011]
    assert hits, f"no peak near {rt} in {report.sample_name}: {[p.rt for p in report.peaks]}"
    return hits[0]


def _ions(peak, mode):
    return [s for s in peak.ms_spectra if s.mode == mode]


def _check_against(report, rt, mass_pos, mass_neg, pct):  # rt: 2-decimal reference value
    peak = _peak_at(report, rt)
    assert peak.area_pct == pytest.approx(pct, abs=0.011)
    pos = _ions(peak, "ES+")
    assert pos and any(abs(mz - mass_pos) < 0.011 for mz in pos[0].top_ions)
    if mass_neg is not None:
        neg = _ions(peak, "ES-")
        assert neg and any(abs(mz - mass_neg) < 0.011 for mz in neg[0].top_ions)


# ---------------------------------------------------------------------------
# Detection and header
# ---------------------------------------------------------------------------

def test_detection_is_content_based(tmp_path):
    assert is_openlynx_rpt(str(PLATE4))
    assert is_waters_report(str(PLATE4))          # .rpt counts as a standard report
    assert count_rpt_samples(str(PLATE4)) == 4
    bogus = tmp_path / "notes.rpt"
    bogus.write_text("just some text\nno samples here\n", encoding="utf-8")
    assert not is_openlynx_rpt(str(bogus))
    wrong_ext = tmp_path / "copy.txt"
    shutil.copy(PLATE4, wrong_ext)
    assert not is_openlynx_rpt(str(wrong_ext))
    assert not is_openlynx_rpt(str(tmp_path / "missing.rpt"))


def test_header_fields():
    first = parse_reports(str(PLATE4))[0]
    assert isinstance(first, LCMSReport)
    assert first.source_format == "openlynx_rpt"
    assert first.filename == "waters_qda_4samples.rpt"
    assert first.sample_name == "AACM10177-01"
    assert first.sample_id == "ELP11455-1-1"
    assert first.well == "4:1"
    assert first.sample_index == 1
    assert first.date == "02-Mar-2023"
    assert first.run_time == "08:53:04"
    assert first.instrument == "ACQ-QDA#NotSet"
    assert first.method_path.endswith("CSH~2min_HPH.olp")
    assert first.detector == "TAC"
    assert "UPLC" in first.column_name and "C18" in first.column_name
    assert report_datetime(first) == "2023-03-02 08:53:04"


# ---------------------------------------------------------------------------
# Peaks, spectra, UV against the reference tool's output
# ---------------------------------------------------------------------------

def test_example1_matches_reference_output():
    reports = parse_reports(str(PLATE4))
    assert [r.well for r in reports] == list(EXAMPLE1_EXPECTED)
    for report in reports:
        _check_against(report, *EXAMPLE1_EXPECTED[report.well])


def test_example2_matches_reference_output():
    reports = parse_reports(str(PLATE_SUBSET))
    assert {r.well for r in reports} == set(EXAMPLE2_EXPECTED)
    for report in reports:
        _check_against(report, *EXAMPLE2_EXPECTED[report.well])


def test_spectra_shape():
    peak = parse_reports(str(PLATE4))[0].peaks[0]
    pos, neg = peak.ms_spectra
    assert (pos.mode, neg.mode) == ("ES+", "ES-")
    assert pos.top_ions[0] == pytest.approx(243.94)       # base peak first
    assert pos.intensities[0] == 100.0
    assert len(pos.top_ions) == len(pos.intensities) <= 5
    assert pos.intensities == sorted(pos.intensities, reverse=True)
    assert all(i >= 20.0 for i in pos.intensities)
    assert peak.mass_found.startswith("243.94 (ES+)")
    assert 234.95 in peak.uv_lambda_max                    # chromophore band
    assert peak.area == pytest.approx(1071910.25)
    assert peak.width == pytest.approx(0.04)


def test_two_peak_sample_is_ordered_by_retention_time():
    report = parse_reports(str(PLATE4))[1]
    assert [round(p.rt, 2) for p in report.peaks] == [0.35, 1.30]
    assert [p.peak_num for p in report.peaks] == ["1", "2"]
    assert report.peaks[0].area_pct == pytest.approx(1.07)
    assert sum(p.area_pct for p in report.peaks) == pytest.approx(100.0, abs=0.1)


def test_ms_tic_fallback_when_no_dad_trace():
    reports = parse_reports(str(XEVO))
    assert len(reports) == 2
    first = reports[0]
    assert first.detector == "MS TIC"
    assert first.instrument.startswith("XEVO-G2XSQTOF")
    peak = first.peaks[0]
    assert peak.rt == pytest.approx(0.7975)
    assert peak.area_pct == 100.0
    assert peak.ms_spectra[0].mode == "ES+"
    assert peak.ms_spectra[0].top_ions[0] == pytest.approx(25247.0)
    assert "Area basis" in format_table(first)
    assert "Area basis" in format_basic_report(first)
    assert "Area basis" not in format_table(parse_reports(str(PLATE4))[0])


def test_wavelength_traces_fill_220_and_254_slots():
    text = decode_rpt(PLATE4.read_bytes())
    first = text.split("[SAMPLE]")[1]
    # add 220 and 254 nm DAD traces next to the TAC one (same Peak ID, shifted apex)
    extra = (
        "[FUNCTION]\n{\nFunction\t4\nIonMode\t\nType\tDAD \nDescription\t(220:220) \n"
        "[CHROMATOGRAM]\n{\nTraceNumber\t1\nDescription\tDAD: 220\n[TRACE]\n{\n}\n"
        "[PEAK]\n{\nPeak ID\t1\nPeak Ref\t1\nTime\t1.2310\nHeight\t5.0\nAreaAbs\t500.0\n"
        "Area %Total\t91.50\nWidth\t0.04\n}\n}\n}\n"
        "[FUNCTION]\n{\nFunction\t5\nIonMode\t\nType\tDAD \nDescription\t(254:254) \n"
        "[CHROMATOGRAM]\n{\nTraceNumber\t1\nDescription\tDAD: 254\n[TRACE]\n{\n}\n"
        "[PEAK]\n{\nPeak ID\t1\nPeak Ref\t1\nTime\t1.2290\nHeight\t5.0\nAreaAbs\t250.0\n"
        "Area %Total\t88.25\nWidth\t0.04\n}\n}\n}\n"
    )
    marker = "[ACCEPTANCE CRITERIA]"
    patched = "[SAMPLE]" + first.replace(marker, extra + marker, 1)
    report = parse_rpt_text(patched, "synthetic.rpt")[0]
    assert len(report.peaks) == 1
    peak = report.peaks[0]
    assert (peak.area_pct, peak.area_pct_220nm, peak.area_pct_254nm) == (100.0, 91.5, 88.25)
    assert (peak.area_220nm, peak.area_254nm) == (500.0, 250.0)


# ---------------------------------------------------------------------------
# Routing: parse_report, analyze entry points
# ---------------------------------------------------------------------------

def test_parse_report_single_and_selection():
    single = parse_report(str(SINGLE))
    assert single.sample_name == "AACM10177-02"
    with pytest.raises(ValueError, match="holds 4 samples"):
        parse_report(str(PLATE4))
    assert parse_report(str(PLATE4), sample=3).sample_name == "AACM10177-03"
    assert parse_report(str(PLATE4), sample="4:4").sample_name == "AACM10177-04"
    assert parse_report(str(PLATE4), sample="elp11455-2-1").well == "4:2"
    assert parse_report(str(PLATE4), sample="AACM10177-01").well == "4:1"
    with pytest.raises(ValueError, match="not found"):
        parse_report(str(PLATE4), sample="Z99")


def test_parse_analysis_file_handles_rpt():
    from cdxml_toolkit.analysis.parse_analysis_file import parse_analysis_file

    one = parse_analysis_file(str(SINGLE))
    assert one["ok"] and one["file_type"] == "lcms"
    assert one["data"]["sample_name"] == "AACM10177-02"
    assert one["data"]["peaks"][1]["ms_spectra"][0]["mode"] == "ES+"

    many = parse_analysis_file(str(PLATE4))
    assert many["ok"] and many["file_type"] == "lcms"
    assert many["data"]["sample_count"] == 4
    assert [s["well"] for s in many["data"]["samples"]] == list(EXAMPLE1_EXPECTED)
    json.dumps(many)                                    # plain JSON types only


def test_parse_analysis_file_rejects_non_rpt_text(tmp_path):
    from cdxml_toolkit.analysis.parse_analysis_file import parse_analysis_file

    bogus = tmp_path / "x.rpt"
    bogus.write_text("hello\n", encoding="utf-8")
    result = parse_analysis_file(str(bogus))
    assert result["ok"] is False and "OpenLynx" in result["error"]


def test_multi_analyzer_expands_samples_into_timepoints(tmp_path):
    from cdxml_toolkit.analysis.deterministic.multi_lcms_analyzer import main

    out = tmp_path / "series.json"
    assert main([str(PLATE4), "--json-output", str(out), "--output", str(tmp_path / "t.txt")]) == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    assert [f["filename"] for f in data["files"]] == [
        "AACM10177-01", "AACM10177-02", "AACM10177-03", "AACM10177-04",
    ]
    assert data["files"][0]["date"] == "02-Mar-2023"
    assert any(abs(c["canonical_rt"] - 1.30) < 0.02 for c in data["compounds"])


def test_series_tool_accepts_one_multi_sample_rpt(tmp_path):
    from cdxml_toolkit.mcp_runtime import extended_tools

    result = extended_tools.analyze_lcms_series(
        [str(PLATE4)], output_path=str(tmp_path / "series.json")
    )
    assert result["ok"] and result["metadata"]["file_count"] == 1
    assert json.loads((tmp_path / "series.json").read_text(encoding="utf-8"))["files"]
    with pytest.raises(ValueError, match="at least two"):
        extended_tools.analyze_lcms_series([str(SINGLE)])


def test_discovery_picks_single_sample_rpt_and_skips_batches(tmp_path):
    from cdxml_toolkit.analysis.deterministic.discover_experiment_files import (
        discover_experiment_files,
    )

    shutil.copy(SINGLE, tmp_path / "EXP-1-t0.rpt")
    shutil.copy(PLATE4, tmp_path / "EXP-1-t30.rpt")
    found = discover_experiment_files(str(tmp_path), "EXP-1")
    assert [os.path.basename(f.path) for f in found.lcms_files] == ["EXP-1-t0.rpt"]
    assert any("EXP-1-t30.rpt" in w and "4 samples" in w for w in found.warnings)


def test_identifier_matches_expected_species_from_rpt():
    from cdxml_toolkit.analysis.deterministic.discover_experiment_files import LCMSFileRecord
    from cdxml_toolkit.analysis.deterministic.lcms_identifier import _run_single_file_tracking
    from cdxml_toolkit.analysis.deterministic.mass_resolver import ExpectedSpecies

    product = ExpectedSpecies(
        name="DP", role="product", exact_mass=236.98,
        smiles="COC1=NC2=CC=C(Br)C=C2C=C1", adducts={"[M+H]+": 237.99},
    )
    record = LCMSFileRecord(path=str(SINGLE), category="tracking", sort_key=0.0)
    analysis = _run_single_file_tracking(record, [product])
    assert [ic.species.name for ic in analysis.identified] == ["DP"]
    assert analysis.identified[0].compound.canonical_rt == pytest.approx(1.30, abs=0.01)


def test_format_procedure_entry_reads_rpt_sample():
    from cdxml_toolkit.analysis.format_procedure_entry import process_entries

    entry = {
        "type": "lcms-areas",
        "file": str(PLATE4),
        "sample": "4:2",
        "label": "t = 1 h",
        "peaks": [{"name": "Product", "rt": 1.30, "compound_related": True}],
    }
    text = process_entries([entry])
    assert "98.9" in text


# ---------------------------------------------------------------------------
# Opt-in: complete sample files
# ---------------------------------------------------------------------------

def _sample_root() -> Path:
    return Path(os.environ.get("CDX_LCMS_SAMPLES", r"D:\lcms-samples"))


_PYPARSE = _sample_root() / "zenodo_PyParse_v1.1.0" / "extracted" / "example_dataset" / "Waters"


@pytest.mark.skipif(not _PYPARSE.is_dir(), reason="full OpenLynx sample files not on disk")
@pytest.mark.parametrize(
    "folder,rpt,products_only",
    [
        ("Example1", "example_rpt.rpt", False),
        ("Example2", "LC-MS Data for 48-Well Plate.rpt", True),
    ],
)
def test_full_pyparse_exports(folder, rpt, products_only):
    base = _PYPARSE / folder
    reports = parse_reports(str(base / rpt))
    by_position = {int(r.well.split(":")[-1]): r for r in reports}
    columns = 12
    checked = 0
    with open(base / "output" / "compoundtable.csv", encoding="utf-8-sig") as fh:
        for row in csv.DictReader(fh):
            if products_only and not row["name"].startswith(
                ("Product", "Byproduct", "Reactant", "Internal")
            ):
                continue
            well = row["best_well"]
            position = (ord(well[0]) - 65) * columns + int(well[1:])
            pos = None if row["mass+"] in ("-", "") else float(row["mass+"])
            neg = None if row["mass-"] in ("-", "") else float(row["mass-"])
            peak = _peak_at(by_position[position], float(row["time"]))
            assert peak.area_pct == pytest.approx(float(row["best_purity"]), abs=0.011)
            if pos is not None:
                ions = _ions(peak, "ES+")[0].top_ions
                assert any(abs(mz - pos) < 0.011 for mz in ions), (well, pos, ions)
            if neg is not None and not (folder == "Example2" and well == "C10"):
                # C10's ESI- ion is 3 % of the base peak, below the reporting threshold
                neg_ions = _ions(peak, "ES-")[0].top_ions
                assert any(abs(mz - neg) < 0.011 for mz in neg_ions), (well, neg, neg_ions)
            checked += 1
    assert checked >= 4
    assert len(reports) in (24, 48)


@pytest.mark.skipif(
    not (_sample_root() / "smdc_openlynx_rpt" / "masslynx_example_input.rpt").is_file(),
    reason="full Xevo sample file not on disk",
)
def test_full_xevo_export():
    reports = parse_reports(str(_sample_root() / "smdc_openlynx_rpt" / "masslynx_example_input.rpt"))
    assert len(reports) == 28
    assert all(r.detector == "MS TIC" and len(r.peaks) == 1 for r in reports)
    assert all(r.peaks[0].ms_spectra for r in reports)
