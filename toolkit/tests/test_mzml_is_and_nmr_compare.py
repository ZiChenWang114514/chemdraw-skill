"""Tests for open MS format parsing (mzML/mzXML), Waters .raw header metadata,
multi-LCMS internal standard (IS) normalization, 1H residual solvent tables,
NMR zoom inset_region in CDXML, Karplus 3J_HH couplings, NMRNet++ multi-fold
shift_std, and Hungarian-algorithm nmr.compare_shifts.
"""

from __future__ import annotations

import base64
import math
import pickle
import struct
import xml.etree.ElementTree as ET
import zlib
from pathlib import Path
from unittest import mock

import numpy as np
import pytest
from rdkit import Chem
from rdkit.Chem import AllChem

from cdxml_toolkit.analysis.deterministic.lcms_file_parser import parse_lcms_file
from cdxml_toolkit.analysis.deterministic.multi_lcms_analyzer import (
    MassResolver,
    analyze_multi_lcms,
)
from cdxml_toolkit.analysis.deterministic.mzml_parser import (
    Chromatogram,
    LCMSAnalysis,
    LCMSPeak,
    MassSpectrum,
    decode_binary_array,
    parse_mzml,
)
from cdxml_toolkit.analysis.deterministic.waters_raw import (
    parse_waters_header,
    parse_waters_raw,
)
from cdxml_toolkit.engines import compare_shifts as engines_compare_shifts
from cdxml_toolkit.engines import nmr as engines_nmr
from cdxml_toolkit.engines import worker as engines_worker
from cdxml_toolkit.scientific.spectra import (
    analyze_spectrum,
    build_nmr_cdxml,
    nmr_to_cdxml,
    plot_nmr,
)
from cdxml_toolkit.spectral_text import (
    SOLVENT_PEAKS_13C,
    SOLVENT_PEAKS_1H,
    filter_solvent_peaks_1h,
    is_solvent_peak_1h,
)


def _encode_floats(values: list[float], *, precision: int = 64, compress: bool = False, endian: str = "<") -> str:
    fmt_char = "d" if precision == 64 else "f"
    raw = struct.pack(f"{endian}{len(values)}{fmt_char}", *values)
    if compress:
        raw = zlib.compress(raw)
    return base64.b64encode(raw).decode("ascii")


# ---------------------------------------------------------------------------
# 1. Open MS Format Parser (.mzML / .mzXML) & Waters .raw Header Metadata
# ---------------------------------------------------------------------------


def test_parse_mzml_32_64_zlib_and_uncompressed(tmp_path: Path) -> None:
    """Verify .mzML parsing with TIC/BPC/UV chromatograms, ES+/ES- spectra, 32/64-bit, zlib/raw."""
    tic_times_sec = [30.0, 60.0, 90.0, 120.0, 150.0, 180.0, 210.0]
    tic_ints = [100.0, 5000.0, 150.0, 200.0, 10000.0, 180.0, 100.0]
    uv_times_min = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5]
    uv_ints = [10.0, 1200.0, 20.0, 15.0, 2400.0, 25.0, 10.0]

    # Spectrum 1 at RT=1.0 min (60 s), ES+, 64-bit zlib
    s1_mzs = [169.08, 191.06, 337.15]
    s1_ints = [10000.0, 2500.0, 800.0]
    # Spectrum 2 at RT=2.5 min (150 s), ES-, 32-bit uncompressed
    s2_mzs = [249.10, 251.10, 285.07]
    s2_ints = [15000.0, 5000.0, 1200.0]

    mzml_content = f"""<?xml version="1.0" encoding="utf-8"?>
<mzML xmlns="http://psi.hupo.org/ms/mzml" version="1.1.0">
  <instrumentConfigurationList count="1">
    <instrumentConfiguration id="IC1">
      <cvParam cvRef="MS" accession="MS:1000126" name="Waters QDa"/>
    </instrumentConfiguration>
  </instrumentConfigurationList>
  <sampleList count="1">
    <sample id="S1" name="KL-2001-010-1h"/>
  </sampleList>
  <run id="run1" startTimeStamp="2026-11-04T14:30:00Z" sampleRef="S1">
    <chromatogramList count="2">
      <chromatogram index="0" id="TIC" defaultArrayLength="{len(tic_times_sec)}">
        <cvParam cvRef="MS" accession="MS:1000235" name="total ion current chromatogram"/>
        <binaryDataArrayList count="2">
          <binaryDataArray>
            <cvParam cvRef="MS" accession="MS:1000523" name="64-bit float"/>
            <cvParam cvRef="MS" accession="MS:1000574" name="zlib compression"/>
            <cvParam cvRef="MS" accession="MS:1000595" name="time array" unitAccession="UO:0000010" unitName="second"/>
            <binary>{_encode_floats(tic_times_sec, precision=64, compress=True)}</binary>
          </binaryDataArray>
          <binaryDataArray>
            <cvParam cvRef="MS" accession="MS:1000521" name="32-bit float"/>
            <cvParam cvRef="MS" accession="MS:1000576" name="no compression"/>
            <cvParam cvRef="MS" accession="MS:1000515" name="intensity array"/>
            <binary>{_encode_floats(tic_ints, precision=32, compress=False)}</binary>
          </binaryDataArray>
        </binaryDataArrayList>
      </chromatogram>
      <chromatogram index="1" id="DAD_UV_254" defaultArrayLength="{len(uv_times_min)}">
        <cvParam cvRef="MS" accession="MS:1000812" name="absorption chromatogram"/>
        <cvParam cvRef="MS" accession="MS:1000618" name="wavelength" value="254.0"/>
        <binaryDataArrayList count="2">
          <binaryDataArray>
            <cvParam cvRef="MS" accession="MS:1000523" name="64-bit float"/>
            <cvParam cvRef="MS" accession="MS:1000576" name="no compression"/>
            <cvParam cvRef="MS" accession="MS:1000595" name="time array" unitAccession="UO:0000031" unitName="minute"/>
            <binary>{_encode_floats(uv_times_min, precision=64, compress=False)}</binary>
          </binaryDataArray>
          <binaryDataArray>
            <cvParam cvRef="MS" accession="MS:1000523" name="64-bit float"/>
            <cvParam cvRef="MS" accession="MS:1000574" name="zlib compression"/>
            <cvParam cvRef="MS" accession="MS:1000515" name="intensity array"/>
            <binary>{_encode_floats(uv_ints, precision=64, compress=True)}</binary>
          </binaryDataArray>
        </binaryDataArrayList>
      </chromatogram>
    </chromatogramList>
    <spectrumList count="2">
      <spectrum index="0" id="scan=1" defaultArrayLength="{len(s1_mzs)}">
        <cvParam cvRef="MS" accession="MS:1000511" name="ms level" value="1"/>
        <cvParam cvRef="MS" accession="MS:1000130" name="positive scan"/>
        <scanList count="1">
          <scan>
            <cvParam cvRef="MS" accession="MS:1000016" name="scan start time" value="60.0" unitAccession="UO:0000010" unitName="second"/>
          </scan>
        </scanList>
        <binaryDataArrayList count="2">
          <binaryDataArray>
            <cvParam cvRef="MS" accession="MS:1000523" name="64-bit float"/>
            <cvParam cvRef="MS" accession="MS:1000574" name="zlib compression"/>
            <cvParam cvRef="MS" accession="MS:1000514" name="m/z array"/>
            <binary>{_encode_floats(s1_mzs, precision=64, compress=True)}</binary>
          </binaryDataArray>
          <binaryDataArray>
            <cvParam cvRef="MS" accession="MS:1000523" name="64-bit float"/>
            <cvParam cvRef="MS" accession="MS:1000574" name="zlib compression"/>
            <cvParam cvRef="MS" accession="MS:1000515" name="intensity array"/>
            <binary>{_encode_floats(s1_ints, precision=64, compress=True)}</binary>
          </binaryDataArray>
        </binaryDataArrayList>
      </spectrum>
      <spectrum index="1" id="scan=2" defaultArrayLength="{len(s2_mzs)}">
        <cvParam cvRef="MS" accession="MS:1000511" name="ms level" value="1"/>
        <cvParam cvRef="MS" accession="MS:1000129" name="negative scan"/>
        <scanList count="1">
          <scan>
            <cvParam cvRef="MS" accession="MS:1000016" name="scan start time" value="2.5" unitAccession="UO:0000031" unitName="minute"/>
          </scan>
        </scanList>
        <binaryDataArrayList count="2">
          <binaryDataArray>
            <cvParam cvRef="MS" accession="MS:1000521" name="32-bit float"/>
            <cvParam cvRef="MS" accession="MS:1000576" name="no compression"/>
            <cvParam cvRef="MS" accession="MS:1000514" name="m/z array"/>
            <binary>{_encode_floats(s2_mzs, precision=32, compress=False)}</binary>
          </binaryDataArray>
          <binaryDataArray>
            <cvParam cvRef="MS" accession="MS:1000521" name="32-bit float"/>
            <cvParam cvRef="MS" accession="MS:1000576" name="no compression"/>
            <cvParam cvRef="MS" accession="MS:1000515" name="intensity array"/>
            <binary>{_encode_floats(s2_ints, precision=32, compress=False)}</binary>
          </binaryDataArray>
        </binaryDataArrayList>
      </spectrum>
    </spectrumList>
  </run>
</mzML>
"""
    mzml_path = tmp_path / "sample_run.mzML"
    mzml_path.write_text(mzml_content, encoding="utf-8")

    analysis = parse_lcms_file(mzml_path)
    assert isinstance(analysis, LCMSAnalysis)
    assert analysis.format == "mzML"
    assert "Waters QDa" in analysis.instrument
    assert analysis.acquisition_date == "2026-11-04T14:30:00Z"
    assert analysis.sample_name == "KL-2001-010-1h"

    tic_chrom = analysis.get_chromatogram("TIC")
    uv_chrom = analysis.get_chromatogram("UV")
    assert tic_chrom is not None
    assert uv_chrom is not None
    assert tic_chrom.times == pytest.approx([0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5], abs=1e-4)
    assert uv_chrom.wavelength == pytest.approx(254.0)

    assert len(analysis.spectra) == 2
    assert analysis.spectra[0].mode == "ES+"
    assert analysis.spectra[0].mz_values == pytest.approx(s1_mzs, abs=1e-3)
    assert analysis.spectra[0].intensities == pytest.approx(s1_ints, abs=1e-1)
    assert analysis.spectra[1].mode == "ES-"
    assert analysis.spectra[1].mz_values == pytest.approx(s2_mzs, abs=1e-3)

    assert len(analysis.peaks) == 2
    assert analysis.peaks[0].rt == pytest.approx(1.0, abs=0.05)
    assert analysis.peaks[1].rt == pytest.approx(2.5, abs=0.05)
    assert analysis.peaks[0].area_pct == pytest.approx(33.33, abs=1.0)
    assert analysis.peaks[1].area_pct == pytest.approx(66.67, abs=1.0)


def test_parse_mzxml_32_and_64_bit(tmp_path: Path) -> None:
    """Verify .mzXML parsing with interleaved m/z-intensity pairs (zlib and uncompressed)."""
    pairs_scan1 = [150.0, 2000.0, 225.1, 8000.0, 449.2, 1500.0]
    pairs_scan2 = [180.0, 500.0, 310.2, 12000.0]

    mzxml_content = f"""<?xml version="1.0" encoding="utf-8"?>
<mzXML xmlns="http://sashimi.sourceforge.net/schema_revision/mzXML_3.2">
  <msRun scanCount="2" startTime="PT0.0S" endTime="PT180.0S">
    <msInstrument>
      <msManufacturer category="msManufacturer" value="Agilent"/>
      <msModel category="msModel" value="6120 Quadrupole"/>
    </msInstrument>
    <scan num="1" msLevel="1" peaksCount="3" polarity="+" retentionTime="PT72.0S" totIonCurrent="11500.0">
      <peaks precision="32" byteOrder="network" compressionType="zlib">{_encode_floats(pairs_scan1, precision=32, compress=True, endian=">")}</peaks>
    </scan>
    <scan num="2" msLevel="1" peaksCount="2" polarity="-" retentionTime="PT2.4M" totIonCurrent="12500.0">
      <peaks precision="64" byteOrder="network" compressionType="none">{_encode_floats(pairs_scan2, precision=64, compress=False, endian=">")}</peaks>
    </scan>
  </msRun>
</mzXML>
"""
    mzxml_path = tmp_path / "run.mzXML"
    mzxml_path.write_text(mzxml_content, encoding="utf-8")

    analysis = parse_lcms_file(mzxml_path)
    assert analysis.format == "mzXML"
    assert "Agilent" in analysis.instrument
    assert len(analysis.spectra) == 2
    assert analysis.spectra[0].mode == "ES+"
    assert analysis.spectra[0].rt == pytest.approx(1.2, abs=1e-4)
    assert analysis.spectra[0].mz_values == pytest.approx([150.0, 225.1, 449.2], abs=1e-3)
    assert analysis.spectra[1].mode == "ES-"
    assert analysis.spectra[1].rt == pytest.approx(2.4, abs=1e-4)
    assert analysis.spectra[1].mz_values == pytest.approx([180.0, 310.2], abs=1e-3)
    assert len(analysis.peaks) == 2


def test_parse_waters_raw_header_metadata(tmp_path: Path) -> None:
    """Verify parse_waters_header and parse_waters_raw extract _HEADER.TXT fields."""
    raw_dir = tmp_path / "KL-1001-042-2h.raw"
    raw_dir.mkdir()
    header_txt = """$$ Waters MassLynx Header
$$ Acquired Date: 04-Nov-2026
$$ Acquired Time: 16:45:12
$$ Sample Description: KL-1001-042-2h reaction aliquot
$$ Instrument: Acquity SQD2
$$ Conditions: AmF_2min_10_95
$$ Inlet Method: C:\\MassLynx\\Methods\\AmF_2min.olp
"""
    (raw_dir / "_HEADER.TXT").write_text(header_txt, encoding="utf-8")

    hdr = parse_waters_header(raw_dir)
    assert hdr["Acquired Date"] == "04-Nov-2026"
    assert hdr["Acquired Time"] == "16:45:12"
    assert hdr["Sample Description"] == "KL-1001-042-2h reaction aliquot"
    assert hdr["Instrument"] == "Acquity SQD2"
    assert hdr["Conditions"] == "AmF_2min_10_95"
    assert hdr["Inlet Method"] == "C:\\MassLynx\\Methods\\AmF_2min.olp"

    analysis = parse_waters_raw(raw_dir)
    assert analysis.instrument == "Acquity SQD2"
    assert "04-Nov-2026" in analysis.acquisition_date
    assert "16:45:12" in analysis.acquisition_date
    assert "KL-1001-042-2h reaction aliquot" in analysis.sample_info
    assert analysis.sample_info["Sample Description"] == "KL-1001-042-2h reaction aliquot"

    # Also test via parse_lcms_file dispatcher
    dispatched = parse_lcms_file(raw_dir)
    assert dispatched.instrument == "Acquity SQD2"


# ---------------------------------------------------------------------------
# 2. Multi-LCMS Internal Standard (IS) Normalization
# ---------------------------------------------------------------------------


def test_multi_lcms_internal_standard_normalization_by_mw_and_rt() -> None:
    """Verify IS peak identification (by MW via MassResolver and by RT) and is_normalized_ratio."""
    # Internal standard: 1,3,5-trimethoxybenzene (MW = 168.08, [M+H]+ = 169.09) at RT = 2.10 min
    # Starting material SM (MW = 220.1, [M+H]+ = 221.1) at RT = 1.45 min: decreases from 600 to 150
    # Product DP (MW = 310.2, [M+H]+ = 311.2) at RT = 2.85 min: increases from 200 to 650
    # IS area stays constant at 200 across both timepoints
    t0 = LCMSAnalysis(
        filename="rxn_t0.mzML",
        instrument="SQD2",
        method="AmF_2min",
        peaks=[
            LCMSPeak(peak_id=1, rt=1.45, area=600.0, area_pct=60.0, ms_spectra=[MassSpectrum([221.1], [10000.0], "ES+")]),
            LCMSPeak(peak_id=2, rt=2.10, area=200.0, area_pct=20.0, ms_spectra=[MassSpectrum([169.09], [8000.0], "ES+")]),
            LCMSPeak(peak_id=3, rt=2.85, area=200.0, area_pct=20.0, ms_spectra=[MassSpectrum([311.2], [5000.0], "ES+")]),
        ],
    )
    t1 = LCMSAnalysis(
        filename="rxn_t1.mzML",
        instrument="SQD2",
        method="AmF_2min",
        peaks=[
            LCMSPeak(peak_id=1, rt=1.46, area=150.0, area_pct=15.0, ms_spectra=[MassSpectrum([221.1], [3000.0], "ES+")]),
            LCMSPeak(peak_id=2, rt=2.12, area=200.0, area_pct=20.0, ms_spectra=[MassSpectrum([169.09], [8200.0], "ES+")]),
            LCMSPeak(peak_id=3, rt=2.84, area=650.0, area_pct=65.0, ms_spectra=[MassSpectrum([311.2], [14000.0], "ES+")]),
        ],
    )

    # 1) Match by internal_standard_mw via MassResolver
    res_mw = analyze_multi_lcms(
        [t0, t1],
        internal_standard_mw=168.08,
        internal_standard_name="TMB",
    )
    assert "internal_standard" in res_mw
    assert res_mw["internal_standard"]["name"] == "TMB"
    assert res_mw["internal_standard"]["rt"] == pytest.approx(2.11, abs=0.05)
    assert res_mw["internal_standard"]["area_pct"] == pytest.approx(20.0, abs=0.1)

    compounds = res_mw["compounds"]
    assert len(compounds) == 3
    sm_comp = next(c for c in compounds if abs(c["canonical_rt"] - 1.45) < 0.1)
    is_comp = next(c for c in compounds if abs(c["canonical_rt"] - 2.11) < 0.1)
    dp_comp = next(c for c in compounds if abs(c["canonical_rt"] - 2.85) < 0.1)

    # Check SM ratios: t0 = 600/200 = 3.0, t1 = 150/200 = 0.75
    assert sm_comp["is_normalized_ratio"][0] == pytest.approx(3.0, abs=1e-4)
    assert sm_comp["is_normalized_ratio"][1] == pytest.approx(0.75, abs=1e-4)
    # Check IS ratios: 1.0 across both timepoints
    assert is_comp["is_normalized_ratio"][0] == pytest.approx(1.0, abs=1e-4)
    assert is_comp["is_normalized_ratio"][1] == pytest.approx(1.0, abs=1e-4)
    # Check DP ratios: t0 = 200/200 = 1.0, t1 = 650/200 = 3.25
    assert dp_comp["is_normalized_ratio"][0] == pytest.approx(1.0, abs=1e-4)
    assert dp_comp["is_normalized_ratio"][1] == pytest.approx(3.25, abs=1e-4)

    # 2) Match by internal_standard_rt within 0.15 min tolerance
    res_rt = analyze_multi_lcms(
        [t0, t1],
        internal_standard_rt=2.05,  # within 0.15 min of 2.10/2.12
        internal_standard_name="IS-Ref",
    )
    assert res_rt["internal_standard"]["name"] == "IS-Ref"
    assert res_rt["internal_standard"]["area_pct"] == pytest.approx(20.0, abs=0.1)
    dp_rt = next(c for c in res_rt["compounds"] if abs(c["canonical_rt"] - 2.85) < 0.1)
    assert dp_rt["timeline"][1]["is_normalized_ratio"] == pytest.approx(3.25, abs=1e-4)


# ---------------------------------------------------------------------------
# 3. 1H Residual Solvent Table & NMR Zoom Inset (inset_region)
# ---------------------------------------------------------------------------


def test_solvent_peaks_1h_and_filtering() -> None:
    """Verify SOLVENT_PEAKS_1H table, is_solvent_peak_1h, and filter_solvent_peaks_1h."""
    expected_solvents = {
        "CDCl3": (7.26, 1.56),
        "DMSO-d6": (2.50, 3.33),
        "CD3OD": (3.31, 4.87),
        "D2O": (4.79,),
        "Acetone-d6": (2.05, 2.84),
        "CD3CN": (1.94, 2.13),
        "C6D6": (7.16, 0.40),
        "THF-d8": (3.58, 1.72),
        "CD2Cl2": (5.32, 1.52),
    }
    assert set(expected_solvents).issubset(set(SOLVENT_PEAKS_1H))
    assert "CDCl3" in SOLVENT_PEAKS_13C

    for solv, ppms in expected_solvents.items():
        for p in ppms:
            hit = is_solvent_peak_1h(p + 0.01, solv, tolerance=0.05)
            assert hit is not None, f"Expected {p} ppm to match {solv}"
            assert hit["ppm"] == pytest.approx(p, abs=1e-3)
        assert is_solvent_peak_1h(8.95, solv, tolerance=0.05) is None

    raw_peaks = [
        {"ppm": 7.82, "intensity": 2.0},
        {"ppm": 7.26, "intensity": 0.8},  # CHCl3
        {"ppm": 3.91, "intensity": 3.0},
        {"ppm": 1.55, "intensity": 0.4},  # HDO in CDCl3
    ]
    cleaned = filter_solvent_peaks_1h(raw_peaks, "CDCl3", tolerance=0.05)
    assert len(cleaned) == 2
    assert [c["ppm"] for c in cleaned] == [7.82, 3.91]

    # Also test numeric list filtering
    cleaned_nums = filter_solvent_peaks_1h([7.82, 2.50, 3.33, 1.20], "DMSO-d6", tolerance=0.05)
    assert cleaned_nums == [7.82, 1.20]


def test_build_nmr_cdxml_with_inset_region(tmp_path: Path) -> None:
    """Verify build_nmr_cdxml, plot_nmr, and nmr_to_cdxml render a magnified zoom inset box."""
    ppm = np.linspace(0.0, 10.0, 2000)
    intensity = (
        1.0 / (1.0 + ((ppm - 7.28) / 0.01) ** 2)
        + 0.8 / (1.0 + ((ppm - 7.18) / 0.01) ** 2)
        + 2.5 / (1.0 + ((ppm - 2.35) / 0.015) ** 2)
    )
    peaks = [{"ppm": 7.28, "intensity": 1.0}, {"ppm": 7.18, "intensity": 0.8}, {"ppm": 2.35, "intensity": 2.5}]

    cdxml_no_inset = build_nmr_cdxml(ppm, intensity, peaks=peaks)
    cdxml_with_inset = build_nmr_cdxml(ppm, intensity, peaks=peaks, inset_region=(7.0, 7.5))

    root_no = ET.fromstring(cdxml_no_inset.split("<!DOCTYPE")[0] + cdxml_no_inset.split(">\n", 2)[-1])
    root_in = ET.fromstring(cdxml_with_inset.split("<!DOCTYPE")[0] + cdxml_with_inset.split(">\n", 2)[-1])

    groups_no = root_no.findall(".//group")
    groups_in = root_in.findall(".//group")
    curves_no = root_no.findall(".//curve")
    curves_in = root_in.findall(".//curve")

    assert len(groups_in) == len(groups_no) + 1
    assert len(curves_in) == len(curves_no) + 1
    assert "Inset zoom: 7.50-7.00 ppm" in cdxml_with_inset
    assert "7.28" in cdxml_with_inset
    assert "7.18" in cdxml_with_inset

    # Test nmr_to_cdxml and plot_nmr entry points
    out_file = tmp_path / "zoom.cdxml"
    cdxml_via_helper = nmr_to_cdxml(ppm, intensity, peaks=peaks, inset_region=[7.0, 7.5], output_path=out_file)
    assert out_file.is_file()
    assert "Inset zoom: 7.50-7.00 ppm" in cdxml_via_helper

    plot_res = plot_nmr(ppm, intensity, peaks=peaks, inset_region=(7.0, 7.5), output_dir=tmp_path / "plot_bundle")
    assert isinstance(plot_res, dict)
    assert plot_res["inset_region"] == [7.0, 7.5]
    assert Path(plot_res["cdxml_path"]).is_file()


# ---------------------------------------------------------------------------
# 4. Karplus 3J_HH Coupling, NMRNet++ Multi-Fold Uncertainty, & compare_shifts
# ---------------------------------------------------------------------------


def test_karplus_couplings_and_multiplicity_hints() -> None:
    """Verify Karplus 3J_HH dihedral calculation and multiplicity_hint on 1H atoms."""
    # 1) Chloroethane (CCCl): CH3 (3H) coupled to CH2 (2H) -> CH3 is 't', CH2 is 'q'
    mol = Chem.AddHs(Chem.MolFromSmiles("CCCl"))
    AllChem.EmbedMolecule(mol, randomSeed=42)
    AllChem.MMFFOptimizeMolecule(mol)
    ranks = list(Chem.CanonicalRankAtoms(mol, breakTies=False))
    couplings, mults = engines_worker._compute_karplus_couplings(mol, ranks=ranks)

    # Identify CH2 and CH3 hydrogens
    ch2_h = [
        a.GetIdx()
        for a in mol.GetAtoms()
        if a.GetAtomicNum() == 1 and any(n.GetAtomicNum() == 17 for n in a.GetNeighbors()[0].GetNeighbors())
    ]
    ch3_h = [
        a.GetIdx()
        for a in mol.GetAtoms()
        if a.GetAtomicNum() == 1 and a.GetIdx() not in ch2_h
    ]
    assert len(ch2_h) == 2
    assert len(ch3_h) == 3

    for h_idx in ch2_h:
        assert mults[h_idx] == "q"
        assert len(couplings[h_idx]) == 3
        for c_entry in couplings[h_idx]:
            assert c_entry["bonds"] == 3
            assert c_entry["partner_atom_index"] in ch3_h
            assert 4.0 <= c_entry["j_hz"] <= 10.0

    for h_idx in ch3_h:
        assert mults[h_idx] == "t"
        assert len(couplings[h_idx]) == 2
        for c_entry in couplings[h_idx]:
            assert c_entry["bonds"] == 3
            assert c_entry["partner_atom_index"] in ch2_h


def test_nmrnet_pp_single_fold_vs_multifold_uncertainty(tmp_path: Path) -> None:
    """Verify _nmrnet_pp sets shift_std=None for single fold and computes std across multiple folds."""
    # Create mock NMRNet++ directory structure with fold_0..fold_2 checkpoints
    data_dir = tmp_path / "nmrnet_data"
    (data_dir / "code").mkdir(parents=True)
    (data_dir / "weight").mkdir(parents=True)
    (data_dir / "weight" / "dict.txt").write_text("H\nC\n", encoding="utf-8")
    (data_dir / "H" / "cv_seed_42_fold_0").mkdir(parents=True)
    (data_dir / "H" / "cv_seed_42_fold_0" / "checkpoint_last.pt").write_bytes(b"dummy")

    # Mock subprocess.run to write synthetic valid.out.pkl
    fold_preds = {
        0: [7.20, 7.20, 3.80],
        1: [7.30, 7.30, 3.90],
        2: [7.40, 7.40, 4.00],
    }

    def fake_run(cmd, cwd=None, capture_output=True, text=True, env=None):
        res_idx = cmd.index("--results-path") + 1
        res_dir = Path(cmd[res_idx])
        res_dir.mkdir(parents=True, exist_ok=True)
        path_idx = cmd.index("--path") + 1
        ckpt_str = cmd[path_idx]
        fold_k = 0
        for k in range(5):
            if f"fold_{k}" in ckpt_str:
                fold_k = k
                break
        # Molecule is Cl/C=C/Cl (4 heavy atoms + 2 H atoms = 6 atoms total; H at indices 4, 5)
        # select_atom has length 1 (start token) + 6 = 7
        select_atom = np.array([0, 0, 0, 0, 0, 1, 1], dtype=np.int32)
        preds = np.array(fold_preds[fold_k][:2], dtype=np.float32)

        payload = [{"select_atom": select_atom, "predict": preds}]
        out_pkl = res_dir / f"cv_seed_42_fold_{fold_k}_valid.out.pkl"
        out_pkl.write_bytes(pickle.dumps(payload))
        return mock.Mock(returncode=0, stdout="", stderr="")

    with mock.patch.object(engines_worker.subprocess, "run", side_effect=fake_run):
        # Single fold_0 only -> shift_std is None
        res_single = engines_worker._nmrnet_pp(
            {"smiles": "Cl/C=C/Cl", "nuclei": ["1H"]},
            str(data_dir),
            {},
        )
        h_atoms_single = [a for a in res_single["atoms"] if a["element"] == "H"]
        assert len(h_atoms_single) == 2
        assert all(a["shift_std"] is None for a in h_atoms_single)
        assert all(a["shift"] == pytest.approx(7.20, abs=1e-4) for a in h_atoms_single)

        # Add fold_1.pth and fold_2.pth -> multi-fold ensemble evaluated
        (data_dir / "H" / "fold_1.pth").write_bytes(b"dummy1")
        (data_dir / "H" / "fold_2.pth").write_bytes(b"dummy2")

        res_multi = engines_worker._nmrnet_pp(
            {"smiles": "Cl/C=C/Cl", "nuclei": ["1H"], "ensemble": True},
            str(data_dir),
            {},
        )
        h_atoms_multi = [a for a in res_multi["atoms"] if a["element"] == "H"]
        expected_std = round(float(np.std([7.20, 7.30, 7.40])), 3)
        for a in h_atoms_multi:
            assert a["shift"] == pytest.approx(7.30, abs=1e-4)
            assert a["shift_std"] == pytest.approx(expected_std, abs=1e-3)


def test_nmr_compare_shifts_hungarian_matching_and_outliers() -> None:
    """Verify nmr.compare_shifts performs Hungarian 1-to-1 assignment and flags outliers."""
    predicted_mock = {
        "peaks": {
            "1H": [
                {"shift_ppm": 7.25, "count": 2, "atoms": [6, 7], "multiplicity_hint": "d"},
                {"shift_ppm": 3.82, "count": 3, "atoms": [8, 9, 10], "multiplicity_hint": "s"},
                {"shift_ppm": 1.25, "count": 3, "atoms": [11, 12, 13], "multiplicity_hint": "t"},
            ],
            "13C": [
                {"shift_ppm": 166.5, "count": 1, "atoms": [0]},
                {"shift_ppm": 129.0, "count": 2, "atoms": [1, 2]},
                {"shift_ppm": 52.1, "count": 1, "atoms": [3]},
                {"shift_ppm": 14.2, "count": 1, "atoms": [4]},
            ],
        }
    }
    # Experimental peaks in scrambled order, with one 1H outlier (2.10 vs 1.25 -> abs_error = 0.85 > 0.5)
    exp_1h = [3.85, 2.10, 7.28]
    exp_13c = [14.5, 52.0, 130.0, 166.0]

    res = engines_compare_shifts(
        "CCOC(=O)c1ccccc1",
        experimental_1h=exp_1h,
        experimental_13c=exp_13c,
        solvent="CDCl3",
        predicted_result=predicted_mock,
    )

    assert res["kind"] == "model_assisted_candidate_assignment"
    assert res["solvent"] == "CDCl3"
    assert res["warning"] == "Model-assisted candidate assignment only; verify with 2D NMR (COSY/HSQC/HMBC)."
    assert len(res["matches_1h"]) == 3
    assert len(res["matches_13c"]) == 4

    # Verify Hungarian 1-to-1 optimal pairing:
    # 7.25 -> 7.28 (err 0.03), 3.82 -> 3.85 (err 0.03), 1.25 -> 2.10 (err 0.85)
    m_1h_by_pred = {m["predicted_shift"]: m for m in res["matches_1h"]}
    assert m_1h_by_pred[7.25]["experimental_shift"] == pytest.approx(7.28)
    assert m_1h_by_pred[3.82]["experimental_shift"] == pytest.approx(3.85)
    assert m_1h_by_pred[1.25]["experimental_shift"] == pytest.approx(2.10)
    assert m_1h_by_pred[1.25]["is_outlier"] is True

    assert res["mae_1h"] == pytest.approx((0.03 + 0.03 + 0.85) / 3.0, abs=1e-3)
    assert res["max_error_1h"] == pytest.approx(0.85, abs=1e-4)
    assert res["mae_13c"] == pytest.approx((0.5 + 1.0 + 0.1 + 0.3) / 4.0, abs=1e-3)
    assert res["max_error_13c"] == pytest.approx(1.0, abs=1e-4)
    assert len(res["outliers"]) == 1
    assert res["outliers"][0]["predicted_shift"] == pytest.approx(1.25)
