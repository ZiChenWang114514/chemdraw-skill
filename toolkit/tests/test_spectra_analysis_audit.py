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
