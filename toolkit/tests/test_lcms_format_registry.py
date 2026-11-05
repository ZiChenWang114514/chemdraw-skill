"""One LCMS format registry: mzML / mzXML and Waters .raw reach every agent-facing LCMS path."""

from __future__ import annotations

import base64
import json
import struct
from pathlib import Path

import pytest

from cdxml_toolkit.analysis import lcms_analyzer
from cdxml_toolkit.analysis.deterministic.discover_experiment_files import discover_experiment_files
from cdxml_toolkit.analysis.deterministic.multi_lcms_analyzer import extract_run_datetime, main as multi_main
from cdxml_toolkit.analysis.parse_analysis_file import parse_analysis_file
from cdxml_toolkit.mcp_runtime import extended_tools


def _floats(values) -> str:
    return base64.b64encode(struct.pack(f"<{len(values)}d", *values)).decode("ascii")


def _write_mzml(path: Path, *, stamp: str, product_area: float, sm_area: float) -> Path:
    """A two-peak TIC (SM near 1.0 min at m/z 221.1, product near 2.0 min at m/z 311.2) with a spectrum per peak."""
    times = [i * 12.0 for i in range(1, 16)]               # seconds, 12 .. 180
    tic = [10.0] * 15
    tic[4], tic[5], tic[6] = sm_area / 3, sm_area, sm_area / 3          # peak at 72 s = 1.2 min
    tic[9], tic[10], tic[11] = product_area / 3, product_area, product_area / 3   # peak at 132 s = 2.2 min

    def spectrum(index: int, seconds: float, mz: float) -> str:
        return f"""<spectrum index="{index}" id="scan={index + 1}" defaultArrayLength="2">
        <cvParam cvRef="MS" accession="MS:1000511" name="ms level" value="1"/>
        <cvParam cvRef="MS" accession="MS:1000130" name="positive scan"/>
        <scanList count="1"><scan><cvParam cvRef="MS" accession="MS:1000016" name="scan start time" value="{seconds}" unitAccession="UO:0000010" unitName="second"/></scan></scanList>
        <binaryDataArrayList count="2">
          <binaryDataArray><cvParam cvRef="MS" accession="MS:1000523" name="64-bit float"/><cvParam cvRef="MS" accession="MS:1000576" name="no compression"/><cvParam cvRef="MS" accession="MS:1000514" name="m/z array"/><binary>{_floats([mz, mz + 22.0])}</binary></binaryDataArray>
          <binaryDataArray><cvParam cvRef="MS" accession="MS:1000523" name="64-bit float"/><cvParam cvRef="MS" accession="MS:1000576" name="no compression"/><cvParam cvRef="MS" accession="MS:1000515" name="intensity array"/><binary>{_floats([9000.0, 1000.0])}</binary></binaryDataArray>
        </binaryDataArrayList></spectrum>"""

    path.write_text(f"""<?xml version="1.0" encoding="utf-8"?>
<mzML xmlns="http://psi.hupo.org/ms/mzml" version="1.1.0">
  <instrumentConfigurationList count="1"><instrumentConfiguration id="IC1"><cvParam cvRef="MS" accession="MS:1000126" name="Waters QDa"/></instrumentConfiguration></instrumentConfigurationList>
  <sampleList count="1"><sample id="S1" name="{path.stem}"/></sampleList>
  <run id="run1" startTimeStamp="{stamp}" sampleRef="S1">
    <chromatogramList count="1">
      <chromatogram index="0" id="TIC" defaultArrayLength="15">
        <cvParam cvRef="MS" accession="MS:1000235" name="total ion current chromatogram"/>
        <binaryDataArrayList count="2">
          <binaryDataArray><cvParam cvRef="MS" accession="MS:1000523" name="64-bit float"/><cvParam cvRef="MS" accession="MS:1000576" name="no compression"/><cvParam cvRef="MS" accession="MS:1000595" name="time array" unitAccession="UO:0000010" unitName="second"/><binary>{_floats(times)}</binary></binaryDataArray>
          <binaryDataArray><cvParam cvRef="MS" accession="MS:1000523" name="64-bit float"/><cvParam cvRef="MS" accession="MS:1000576" name="no compression"/><cvParam cvRef="MS" accession="MS:1000515" name="intensity array"/><binary>{_floats(tic)}</binary></binaryDataArray>
        </binaryDataArrayList>
      </chromatogram>
    </chromatogramList>
    <spectrumList count="2">
      {spectrum(0, 72.0, 221.1)}
      {spectrum(1, 132.0, 311.2)}
    </spectrumList>
  </run>
</mzML>
""", encoding="utf-8")
    return path


def _write_raw(path: Path, *, date: str = "04-Nov-2026", time: str = "16:45:12") -> Path:
    path.mkdir()
    (path / "_HEADER.TXT").write_text(
        f"$$ Acquired Date: {date}\n$$ Acquired Time: {time}\n$$ Sample Description: {path.stem}\n"
        "$$ Instrument: Acquity SQD2\n$$ Conditions: AmF_2min\n", encoding="utf-8")
    return path


@pytest.fixture
def series(tmp_path: Path) -> list[Path]:
    return [_write_mzml(tmp_path / "EXP1-t0.mzML", stamp="2026-11-04T14:30:00Z", product_area=200.0, sm_area=900.0),
            _write_mzml(tmp_path / "EXP1-t1.mzML", stamp="2026-11-04T15:30:00Z", product_area=800.0, sm_area=300.0)]


def test_registry_covers_every_format_and_each_has_detect_parse_and_datetime():
    keys = {fmt.key: fmt for fmt in lcms_analyzer.LCMS_FORMATS}
    assert set(keys) == {"openlynx_rpt", "shimadzu_daml", "agilent_chemstation_txt", "mzml", "waters_raw"}
    assert keys["mzml"].suffixes == (".mzml", ".mzxml")
    assert {".pdf", ".rpt", ".daml", ".txt", ".mzml", ".mzxml", ".raw"} == set(lcms_analyzer.LCMS_FILE_SUFFIXES)
    for name, fmt in keys.items():
        assert callable(fmt.detect) and callable(fmt.parse) and callable(fmt.report_datetime), name
    assert lcms_analyzer.lcms_format("A/B.MzXML").key == "mzml"
    assert lcms_analyzer.lcms_format("x.pdf") is None


def test_detection_is_by_content_not_only_by_name(tmp_path, series):
    assert lcms_analyzer.is_waters_report(str(series[0])) is True
    liar = tmp_path / "notes.mzML"
    liar.write_text("just text", encoding="utf-8")
    assert lcms_analyzer.is_waters_report(str(liar)) is False
    with pytest.raises(ValueError, match="Not a mzML / mzXML file"):
        lcms_analyzer.parse_reports(str(liar))

    raw = _write_raw(tmp_path / "S1.raw")
    assert lcms_analyzer.is_waters_report(str(raw)) is True
    empty = tmp_path / "S2.raw"
    empty.mkdir()
    assert lcms_analyzer.is_waters_report(str(empty)) is False


def test_report_datetime_comes_from_the_registry_for_every_format(tmp_path, series):
    report = lcms_analyzer.parse_reports(str(series[0]))[0]
    assert report.source_format == "mzml"
    assert lcms_analyzer.report_datetime(report) == "2026-11-04 14:30:00"
    assert extract_run_datetime(str(series[1])) == "2026-11-04 15:30:00"

    raw = _write_raw(tmp_path / "S1.raw")
    assert extract_run_datetime(str(raw)) == "2026-11-04 16:45:12"
    assert lcms_analyzer.parse_report(str(raw)).source_format == "waters_raw"


def test_parse_analysis_file_reads_mzml_and_raw_without_dumping_whole_traces(tmp_path, series):
    result = parse_analysis_file(str(series[0]))
    assert result["ok"] is True and result["file_type"] == "lcms"
    data = result["data"]
    assert data["format"] == "mzML" and data["instrument"] == "Waters QDa"
    assert data["chromatograms"][0]["points"] == 15 and "times" not in data["chromatograms"][0]
    assert len(data["peaks"]) == 2

    raw = parse_analysis_file(str(_write_raw(tmp_path / "S1.raw")))
    assert raw["ok"] is True and raw["data"]["instrument"] == "Acquity SQD2"

    liar = tmp_path / "x.mzML"
    liar.write_text("nope", encoding="utf-8")
    failed = parse_analysis_file(str(liar))
    assert failed["ok"] is False and "mzML / mzXML" in failed["error"]


def test_analyze_lcms_series_accepts_mzml_and_reports_trends(tmp_path, series):
    out = tmp_path / "series.json"
    result = extended_tools.analyze_lcms_series([str(p) for p in series], output_path=str(out))
    assert result["ok"] is True and result["metadata"]["file_count"] == 2
    data = json.loads(out.read_text(encoding="utf-8"))
    trends = sorted(c["trend"] for c in data["compounds"])
    assert "decreasing" in trends and "increasing" in trends

    strange = [tmp_path / "a.xyz", tmp_path / "b.xyz"]
    for path in strange:
        path.write_text("x", encoding="utf-8")
    with pytest.raises(ValueError, match="one of"):
        extended_tools.analyze_lcms_series([str(p) for p in strange])


def test_analyze_lcms_series_takes_a_waters_raw_folder(tmp_path, series):
    raw = _write_raw(tmp_path / "EXP1-t2.raw")
    result = extended_tools.analyze_lcms_series([str(series[0]), str(raw)], output_path=str(tmp_path / "r.json"))
    assert result["ok"] is True and result["metadata"]["file_count"] == 2  # a different instrument: its own group


def test_internal_standard_is_an_option_of_analyze_lcms_series(tmp_path, series):
    out = tmp_path / "is.json"
    extended_tools.analyze_lcms_series([str(p) for p in series], output_path=str(out), internal_standard_rt=1.2)
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["internal_standard"]["rt"] == pytest.approx(1.2)
    assert all("internal_standard" in f for f in data["files"])

    rc = multi_main([*map(str, series), "--internal-standard-mw", "310.2", "--internal-standard-name", "TMB",
                     "--json-output", str(tmp_path / "cli.json")])
    assert rc == 0
    assert json.loads((tmp_path / "cli.json").read_text(encoding="utf-8"))["internal_standard"]["name"] == "TMB"


def test_discovery_finds_mzml_files_and_waters_raw_folders(tmp_path):
    exp = tmp_path / "EXP7"
    exp.mkdir()
    (exp / "EXP7.csv").write_text("a,b\n1,2\n", encoding="utf-8")
    _write_mzml(exp / "EXP7-t0.mzML", stamp="2026-11-04T14:30:00Z", product_area=100.0, sm_area=900.0)
    _write_raw(exp / "EXP7-t30.raw")
    (exp / "EXP7-t60.raw").mkdir()  # no header: not a Waters folder
    found = discover_experiment_files(str(exp))
    assert sorted(Path(lf.path).name for lf in found.lcms_files) == ["EXP7-t0.mzML", "EXP7-t30.raw"]
