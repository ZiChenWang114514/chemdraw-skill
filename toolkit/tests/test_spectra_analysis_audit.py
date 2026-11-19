"""Regression tests for the spectra and analysis audit fixes."""

from __future__ import annotations

from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.mark.parametrize(
    "name",
    ["openlynx/waters_qda_single.rpt", "shimadzu/socs2a_3peaks.daml", "shimadzu/socs2a_0peaks.daml"],
)
def test_report_files_convert_to_analysis(name):
    from cdxml_toolkit.analysis.deterministic.lcms_file_parser import parse_lcms_file
    from cdxml_toolkit.analysis.lcms_analyzer import parse_report

    path = FIXTURES / name
    report = parse_report(str(path))
    analysis = parse_lcms_file(path)
    assert [p.peak_id for p in analysis.peaks] == [p.peak_num for p in report.peaks]
    assert [p.area_pct_220nm for p in analysis.peaks] == [p.area_pct_220nm for p in report.peaks]
