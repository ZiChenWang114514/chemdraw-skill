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


def test_adducts_use_the_proton_mass():
    from cdxml_toolkit.analysis.deterministic.mass_resolver import PROTON_MASS, build_adducts

    assert PROTON_MASS == 1.007276
    adducts = build_adducts(180.0)
    assert adducts["[M+H]+"] == pytest.approx(181.007276, abs=1e-6)
    assert adducts["[M-H]-"] == pytest.approx(178.992724, abs=1e-6)


def test_salt_ions_come_from_the_organic_component():
    from cdxml_toolkit.analysis.deterministic.mass_resolver import build_adducts, compute_masses

    # triethylammonium chloride: the free base Et3N (101.1204) is what [M+H]+ is built on
    neutral, full = compute_masses("CC[NH+](CC)CC.[Cl-]")
    assert neutral == pytest.approx(101.1204, abs=1e-3)
    assert full > neutral + 30
    # tetramethylammonium bromide: a permanent cation, seen as [M]+ only
    smiles = "C[N+](C)(C)C.[Br-]"
    neutral, _full = compute_masses(smiles)
    assert build_adducts(neutral, smiles=smiles) == {"[M]+": pytest.approx(74.0964, abs=1e-3)}
    # sodium benzoate: the organic anion, not sodium
    neutral, _full = compute_masses("[Na+].[O-]C(=O)c1ccccc1")
    assert neutral == pytest.approx(122.0368, abs=1e-3)


def _timepoint(name, peaks):
    from cdxml_toolkit.analysis.deterministic.mzml_parser import LCMSAnalysis, LCMSPeak, MassSpectrum

    return LCMSAnalysis(
        filename=name, instrument="SQD2", method="AmF_2min",
        peaks=[LCMSPeak(peak_id=i + 1, rt=rt, area=area, area_pct=area / 10.0,
                        ms_spectra=[MassSpectrum([mz], [1000.0], mode)])
               for i, (rt, area, mz, mode) in enumerate(peaks)],
    )


def test_internal_standard_ion_must_match_polarity():
    from cdxml_toolkit.analysis.deterministic.multi_lcms_analyzer import MassResolver
    from cdxml_toolkit.analysis.deterministic.mzml_parser import LCMSPeak, MassSpectrum

    # [M+H]+ of 168.08 is 169.09; seen in a negative-mode trace it is not this compound
    neg = LCMSPeak(peak_id=1, rt=2.1, ms_spectra=[MassSpectrum([169.09], [1.0], "ES-")])
    pos = LCMSPeak(peak_id=1, rt=2.1, ms_spectra=[MassSpectrum([169.09], [1.0], "ES+")])
    assert MassResolver.match_peak(pos, 168.08)
    assert not MassResolver.match_peak(neg, 168.08)


def test_internal_standard_missing_at_a_time_point_warns():
    from cdxml_toolkit.analysis.deterministic.multi_lcms_analyzer import analyze_multi_lcms

    t0 = _timepoint("t0.mzML", [(1.45, 600.0, 221.1, "ES+"), (2.10, 200.0, 169.09, "ES+")])
    t1 = _timepoint("t1.mzML", [(1.46, 150.0, 221.1, "ES+")])
    out = analyze_multi_lcms([t0, t1], internal_standard_mw=168.08)
    assert any("t1.mzML" in w and "internal standard" in w.lower() for w in out["warnings"])


def test_internal_standard_rt_tolerance_is_a_parameter():
    from cdxml_toolkit.analysis.deterministic.multi_lcms_analyzer import analyze_multi_lcms

    t0 = _timepoint("t0.mzML", [(1.45, 600.0, 221.1, "ES+"), (2.10, 200.0, 169.09, "ES+")])
    t1 = _timepoint("t1.mzML", [(1.46, 150.0, 221.1, "ES+"), (2.12, 200.0, 169.09, "ES+")])
    wide = analyze_multi_lcms([t0, t1], internal_standard_rt=2.0)
    assert wide["internal_standard"]["area_pct"] == pytest.approx(20.0)
    narrow = analyze_multi_lcms([t0, t1], internal_standard_rt=2.0, internal_standard_rt_tol=0.05)
    assert narrow["internal_standard"]["area_pct"] is None
