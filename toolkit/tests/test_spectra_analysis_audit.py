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


def test_waters_raw_without_readable_spectra_fails_with_a_conversion_hint(tmp_path):
    from cdxml_toolkit.analysis.parse_analysis_file import parse_analysis_file

    raw = tmp_path / "S1.raw"
    raw.mkdir()
    (raw / "_HEADER.TXT").write_text("$$ Instrument: Acquity SQD2\n", encoding="utf-8")
    (raw / "_FUNC001.DAT").write_bytes(b"\x00" * 64)
    result = parse_analysis_file(str(raw))
    assert result["ok"] is False
    assert "spectra" in result["error"] and "msconvert" in result["error"]


def _lines(offsets_hz, intensities, *, center=3.0, mhz=400.0):
    return [{"ppm": center + o / mhz, "intensity": i, "prominence": i} for o, i in zip(offsets_hz, intensities)]


def _one(lines, mhz=400.0, nucleus="1H"):
    from cdxml_toolkit.scientific.spectra import _group_multiplets

    found = _group_multiplets(lines, mhz, nucleus=nucleus)
    assert len(found) == 1, found
    return found[0]


def test_first_order_multiplets_are_named_with_confidence():
    dd = _one(_lines([0, 2, 8, 10], [1, 1, 1, 1]))
    assert dd["multiplicity"] == "dd" and dd["j_hz"] == pytest.approx([8, 2], abs=0.1)
    dt = _one(_lines([0, 3, 6, 10, 13, 16], [1, 2, 1, 1, 2, 1]))
    assert dt["multiplicity"] == "dt" and dt["j_hz"] == pytest.approx([10, 3], abs=0.1)
    td = _one(_lines([0, 2, 7, 9, 14, 16], [1, 1, 2, 2, 1, 1]))
    assert td["multiplicity"] == "td" and td["j_hz"] == pytest.approx([7, 2], abs=0.1)
    ddd = _one(_lines([0, 2, 5, 7, 8, 10, 13, 15], [1] * 8))
    assert ddd["multiplicity"] == "ddd" and ddd["j_hz"] == pytest.approx([8, 5, 2], abs=0.1)
    d = _one(_lines([0, 8], [1, 0.95]))
    assert d["multiplicity"] == "d" and d["confidence"] > 0.8
    for m in (dd, dt, td, ddd):
        assert 0 < m["confidence"] <= 1


def test_unequal_neighbours_are_not_called_a_doublet():
    from cdxml_toolkit.scientific.spectra import _group_multiplets

    found = _group_multiplets(_lines([0, 16], [1, 0.4]), 400.0, nucleus="1H")
    assert all(m["multiplicity"] != "d" for m in found)
    assert all(m["confidence"] < 0.5 for m in found)
    # J beyond what H-H coupling gives is not a doublet either
    found = _group_multiplets(_lines([0, 19.5], [1, 1]), 400.0, nucleus="1H")
    assert all(m["multiplicity"] != "d" for m in found)


def _csv(path, ppm, y):
    path.write_text("ppm,intensity\n" + "".join(f"{a:.5f},{b:.6f}\n" for a, b in zip(ppm, y)), encoding="utf-8")
    return path


def test_13c_uses_the_carbon_frequency(tmp_path):
    import numpy as np
    from cdxml_toolkit.scientific.spectra import analyze_spectrum

    ppm = np.linspace(0.0, 200.0, 40001)
    y = np.exp(-((ppm - 120.0) / 0.02) ** 2)
    out = analyze_spectrum(_csv(tmp_path / "c.csv", ppm, y), {"nucleus": "13C", "frequency_mhz": 400.0})
    assert out["frequency_mhz"] == pytest.approx(100.58, abs=0.05)
    assert any("13C" in w for w in out["warnings"])


def test_solvent_table_has_water_for_every_solvent():
    from cdxml_toolkit.scientific.spectra import RESIDUAL_SOLVENT_PEAKS

    water = {"CDCl3": 1.56, "DMSO-d6": 3.33, "CD3OD": 4.87, "CD3CN": 2.13, "C6D6": 0.40,
             "Acetone-d6": 2.84, "D2O": 4.79, "CD2Cl2": 1.52, "THF-d8": 2.46, "Toluene-d8": 0.43}
    for solvent, shift in water.items():
        assert shift in RESIDUAL_SOLVENT_PEAKS["1H"][solvent], solvent


def test_nmr_drawing_has_round_ticks_and_1h_integrals():
    import re
    import numpy as np
    from cdxml_toolkit.scientific.spectra import build_nmr_cdxml

    ppm = np.linspace(0.37, 9.83, 2000)
    y = np.exp(-((ppm - 7.2) / 0.01) ** 2) + np.exp(-((ppm - 1.2) / 0.01) ** 2)
    xml = build_nmr_cdxml(ppm, y, nucleus="1H",
                          integrals=[{"limits_ppm": [7.1, 7.3], "normalized": 1.0},
                                     {"limits_ppm": [1.1, 1.3], "normalized": 3.02}])
    labels = [float(v) for v in re.findall(r">(-?\d+(?:\.\d+)?)</s>", xml)]
    ticks = [v for v in labels if v not in (1.0, 3.02)]
    assert ticks and all(abs(v * 2 - round(v * 2)) < 1e-9 for v in ticks)
    assert "3.02" in xml


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
