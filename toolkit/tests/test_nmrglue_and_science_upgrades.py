"""Tests for nmrglue native NMR formats, MagNET Boltzmann averaging, vectorized NMR simulation,
element-wise reaction balance checks, LCMS adducts/isotopologues, and expanded reagent hazards.
"""

from __future__ import annotations

import sys
import types
from pathlib import Path

import numpy as np
import pytest

from cdxml_toolkit.analysis.deterministic.lcms_identifier import (
    IdentifiedPeak,
    match_ions_to_species,
    verify_halogen_isotope_pattern,
)
from cdxml_toolkit.analysis.deterministic.mass_resolver import (
    ADDUCT_PRIORITY,
    ADDUCTS,
    ExpectedSpecies,
    _compute_adducts,
    build_adducts,
    has_heavy_halogens,
    needs_m_plus_2,
)
from cdxml_toolkit.analysis.lcms_analyzer import ChromPeak, MassSpectrum
from cdxml_toolkit.engines import env, nmr, reactions, worker
from cdxml_toolkit.reaction_calculator import hazards
from cdxml_toolkit.scientific.spectra import analyze_spectrum, read_spectrum


OPEN_SPECTRA_1H = Path(r"D:\open-spectra\bmrb\bmse000152\nmr\set01\1H")
OPEN_SPECTRA_13C = Path(r"D:\open-spectra\bmrb\bmse000152\nmr\set01\13C")


# ---------------------------------------------------------------------------
# Task 1: nmrglue native NMR formats, solvent flagging & multiplet grouping
# ---------------------------------------------------------------------------

def _write_synthetic_jcamp(path: Path, ppm_axis: np.ndarray, y: np.ndarray, *,
                           obs_freq: float = 400.0, nucleus: str = "^1H",
                           solvent: str = "CDCl3", xunits: str = "PPM") -> Path:
    if xunits.upper() == "HZ":
        firstx = float(ppm_axis[0] * obs_freq)
        lastx = float(ppm_axis[-1] * obs_freq)
    else:
        firstx = float(ppm_axis[0])
        lastx = float(ppm_axis[-1])
    deltax = (lastx - firstx) / (len(ppm_axis) - 1)
    lines = [
        "##TITLE= Synthetic 1D NMR",
        "##JCAMP-DX= 5.00",
        "##DATA TYPE= NMR SPECTRUM",
        f"##.OBSERVE FREQUENCY= {obs_freq}",
        f"##.OBSERVE NUCLEUS= {nucleus}",
        f"##.SOLVENT NAME= {solvent}",
        f"##XUNITS= {xunits}",
        "##YUNITS= ARBITRARY UNITS",
        f"##FIRSTX= {firstx:.6f}",
        f"##LASTX= {lastx:.6f}",
        f"##DELTAX= {deltax:.6f}",
        f"##NPOINTS= {len(ppm_axis)}",
        "##XYDATA= (X++(Y..Y))",
    ]
    for xval, yval in zip( np.linspace(firstx, lastx, len(ppm_axis)), y):
        lines.append(f"{xval:.5f} {yval:.5f}")
    lines.append("##END=")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def test_jcamp_dx_read_and_analyze_ppm_and_hz(tmp_path: Path):
    ppm = np.linspace(10.0, 0.0, 2001)
    # Peaks at 7.26 ppm (CDCl3 residual) and a doublet at 3.50 +/- 0.01 ppm (J = 8 Hz at 400 MHz)
    y = (
        0.8 * np.exp(-((ppm - 7.26) / 0.004) ** 2)
        + 2.0 * np.exp(-((ppm - 3.51) / 0.003) ** 2)
        + 2.0 * np.exp(-((ppm - 3.49) / 0.003) ** 2)
    )
    jdx_ppm = _write_synthetic_jcamp(tmp_path / "sample_ppm.jdx", ppm, y, xunits="PPM")
    jdx_hz = _write_synthetic_jcamp(tmp_path / "sample_hz.dx", ppm, y, xunits="HZ")

    x1, y1 = read_spectrum(jdx_ppm)
    x2, y2 = read_spectrum(jdx_hz)
    assert len(x1) == 2001 and len(x2) == 2001
    assert np.allclose(x1, x2, atol=1e-3)
    assert np.allclose(y1, y2, atol=1e-4)

    res = analyze_spectrum(jdx_ppm, {"prominence": 0.2})
    assert len(res["peaks"]) == 3
    assert len(res["solvent_peaks"]) == 1
    assert res["solvent_peaks"][0]["solvent"] == "CDCl3"
    assert abs(res["solvent_peaks"][0]["ppm"] - 7.26) < 0.02

    # Multiplet grouping from JCAMP-DX metadata (400 MHz)
    assert len(res["multiplets"]) == 1
    mult = res["multiplets"][0]
    assert mult["multiplicity"] == "d"
    assert abs(mult["center_ppm"] - 3.50) < 0.01
    assert len(mult["j_hz"]) == 1 and abs(mult["j_hz"][0] - 8.0) < 1.0

    # With exclude_solvent=True, solvent peak is removed from peaks but still recorded in solvent_peaks
    res_excl = analyze_spectrum(jdx_ppm, {"prominence": 0.2, "exclude_solvent": True})
    assert len(res_excl["solvent_peaks"]) == 1
    assert len(res_excl["peaks"]) == 2


def test_solvent_flagging_1h_and_13c_and_multiplets(tmp_path: Path):
    # Synthetic 1H spectrum with DMSO-d6 (2.50), singlet at 8.10, triplet at 4.00 (J = 7.2 Hz @ 400 MHz),
    # and quartet at 1.20 (J = 7.2 Hz @ 400 MHz)
    ppm = np.linspace(0.0, 10.0, 10001)
    j_ppm = 7.2 / 400.0
    y = (
        0.6 * np.exp(-((ppm - 2.50) / 0.002) ** 2)
        + 3.0 * np.exp(-((ppm - 8.10) / 0.002) ** 2)
        + 1.0 * np.exp(-((ppm - (4.00 - j_ppm)) / 0.002) ** 2)
        + 2.0 * np.exp(-((ppm - 4.00) / 0.002) ** 2)
        + 1.0 * np.exp(-((ppm - (4.00 + j_ppm)) / 0.002) ** 2)
        + 1.0 * np.exp(-((ppm - (1.20 - 1.5 * j_ppm)) / 0.002) ** 2)
        + 3.0 * np.exp(-((ppm - (1.20 - 0.5 * j_ppm)) / 0.002) ** 2)
        + 3.0 * np.exp(-((ppm - (1.20 + 0.5 * j_ppm)) / 0.002) ** 2)
        + 1.0 * np.exp(-((ppm - (1.20 + 1.5 * j_ppm)) / 0.002) ** 2)
    )
    csv_path = tmp_path / "mult.csv"
    csv_path.write_text(
        "ppm,intensity\n" + "".join(f"{px:.5f},{py:.5f}\n" for px, py in zip(ppm, y)),
        encoding="utf-8",
    )
    out = analyze_spectrum({"path": str(csv_path), "solvent": "DMSO-d6", "frequency_mhz": 400.0, "prominence": 0.3})
    assert len(out["solvent_peaks"]) == 1
    assert out["solvent_peaks"][0]["solvent"] == "DMSO-d6"
    by_mult = {m["multiplicity"]: m for m in out["multiplets"]}
    assert set(by_mult) == {"s", "t", "q"}
    assert abs(by_mult["s"]["center_ppm"] - 8.10) < 0.01
    assert abs(by_mult["t"]["center_ppm"] - 4.00) < 0.01 and abs(by_mult["t"]["j_hz"][0] - 7.2) < 0.8
    assert abs(by_mult["q"]["center_ppm"] - 1.20) < 0.01 and abs(by_mult["q"]["j_hz"][0] - 7.2) < 0.8

    # 13C solvent flagging for CDCl3 (77.16 ppm) and DMSO-d6 (39.52 ppm)
    c_ppm = np.linspace(0.0, 200.0, 4001)
    c_y = (
        1.5 * np.exp(-((c_ppm - 77.15) / 0.08) ** 2)
        + 4.0 * np.exp(-((c_ppm - 168.5) / 0.08) ** 2)
    )
    c_csv = tmp_path / "c13.csv"
    c_csv.write_text(
        "ppm,intensity\n" + "".join(f"{px:.4f},{py:.4f}\n" for px, py in zip(c_ppm, c_y)),
        encoding="utf-8",
    )
    c_out = analyze_spectrum(c_csv, {"solvent": "CDCl3", "nucleus": "13C", "prominence": 0.5})
    assert len(c_out["solvent_peaks"]) == 1
    assert c_out["solvent_peaks"][0]["nucleus"] == "13C"
    assert abs(c_out["solvent_peaks"][0]["ppm"] - 77.15) < 0.1


def test_bruker_synthetic_pdata_and_fid(tmp_path: Path):
    # Build minimal Bruker directory with acqus, fid, and pdata/1/1r + procs
    exp_dir = tmp_path / "bruker_exp"
    pdata_dir = exp_dir / "pdata" / "1"
    pdata_dir.mkdir(parents=True)
    (exp_dir / "acqus").write_text(
        "##TITLE= Parameter file\n"
        "##JCAMPDX= 5.0\n"
        "##$SW_h= 4000.0\n"
        "##$SFO1= 400.0\n"
        "##$BF1= 400.0\n"
        "##$O1= 2000.0\n"
        "##$NUC1= <1H>\n"
        "##$SOLVENT= <CDCl3>\n"
        "##$TD= 1024\n"
        "##$BYTORDA= 0\n"
        "##$DTYPA= 0\n"
        "##$AQ_mod= 1\n"
        "##END=\n",
        encoding="utf-8",
    )
    (pdata_dir / "procs").write_text(
        "##TITLE= Parameter file\n"
        "##JCAMPDX= 5.0\n"
        "##$OFFSET= 10.0\n"
        "##$SW_p= 4000.0\n"
        "##$SF= 400.0\n"
        "##$SI= 512\n"
        "##$BYTORDP= 0\n"
        "##$DTYPP= 0\n"
        "##$FT_mod= 4\n"
        "##END=\n",
        encoding="utf-8",
    )
    # Write 1r (512 int32 points)
    spec_1r = np.zeros(512, dtype="<i4")
    spec_1r[200] = 10000
    (pdata_dir / "1r").write_bytes(spec_1r.tobytes())

    # Test reading from 1r file, pdata/1 dir, and exp_dir
    for target in (pdata_dir / "1r", pdata_dir, exp_dir):
        x, y = read_spectrum(target)
        assert len(x) == 512 and len(y) == 512
        res = analyze_spectrum(target, {"prominence": 100.0})
        assert len(res["peaks"]) == 1

    # Now write synthetic FID in a FID-only Bruker directory
    fid_dir = tmp_path / "bruker_fid_only"
    fid_dir.mkdir()
    (fid_dir / "acqus").write_text((exp_dir / "acqus").read_text(encoding="utf-8"), encoding="utf-8")
    t = np.arange(512, dtype=float) / 4000.0
    fid_complex = (np.exp(2j * np.pi * 500.0 * t) * np.exp(-t * 5.0)) * 1000.0
    interleaved = np.empty(1024, dtype="<i4")
    interleaved[0::2] = np.real(fid_complex).astype("<i4")
    interleaved[1::2] = np.imag(fid_complex).astype("<i4")
    (fid_dir / "fid").write_bytes(interleaved.tobytes())

    res_fid = analyze_spectrum(fid_dir, {"prominence": 50.0})
    assert res_fid["processing"]["source_format"] == "bruker_fid"
    assert res_fid["processing"]["fft"] is True
    assert res_fid["processing"]["line_broadening_hz"] == 0.3
    assert res_fid["sample_count"] >= 1024


@pytest.mark.skipif(not OPEN_SPECTRA_1H.exists(), reason="D:\\open-spectra\\bmrb\\bmse000152 not present")
def test_real_bruker_open_spectra_1r_and_raw_fid():
    res_1r = analyze_spectrum(OPEN_SPECTRA_1H / "pdata" / "1" / "1r")
    res_fid = analyze_spectrum(OPEN_SPECTRA_1H / "fid")
    assert res_1r["sample_count"] == 32768
    assert res_fid["processing"]["source_format"] == "bruker_fid"
    assert res_fid["processing"]["digital_filter_removed"] is True
    assert len(res_1r["peaks"]) >= 1 and len(res_fid["peaks"]) >= 1
    # Dominant HOD peak in D2O around 4.79 ppm in both processed 1r and raw FID
    top_1r = max(res_1r["peaks"], key=lambda p: p["intensity"])["ppm"]
    top_fid = max(res_fid["peaks"], key=lambda p: p["intensity"])["ppm"]
    assert abs(top_1r - top_fid) < 0.05

    if OPEN_SPECTRA_13C.exists():
        res_13c_fid = analyze_spectrum(OPEN_SPECTRA_13C / "fid")
        assert res_13c_fid["processing"]["line_broadening_hz"] == 1.0


def test_jeol_and_varian_readers_via_nmrglue(monkeypatch, tmp_path: Path):
    import nmrglue as ng

    # Mock JEOL .jdf
    jdf_file = tmp_path / "test.jdf"
    jdf_file.write_bytes(b"JEOL_MOCK")
    t = np.arange(256, dtype=float) / 4000.0
    fid_data = np.exp(2j * np.pi * 300.0 * t) * np.exp(-t * 4.0)
    monkeypatch.setattr(ng.jeol, "read", lambda p: ({"param": {"solvent": "CDCl3"}}, fid_data))
    monkeypatch.setattr(
        ng.jeol,
        "guess_udic",
        lambda d, data: {
            "ndim": 1,
            0: {"sw": 4000.0, "obs": 400.0, "car": 1600.0, "size": len(data), "label": "1H", "time": True, "freq": False},
        },
    )
    res_jdf = analyze_spectrum(jdf_file)
    assert res_jdf["processing"]["source_format"] == "jeol_jdf"
    assert res_jdf["sample_count"] == 512

    # Mock Varian .fid directory
    vdir = tmp_path / "sample.fid"
    vdir.mkdir()
    (vdir / "fid").write_bytes(b"VARIAN_FID")
    (vdir / "procpar").write_text("sfrq 400.0\n", encoding="utf-8")
    monkeypatch.setattr(
        ng.varian,
        "read",
        lambda p: (
            {"procpar": {"sfrq": {"values": ["400.0"]}, "sw": {"values": ["4000.0"]}, "tn": {"values": ["H1"]}, "solvent": {"values": ["cdcl3"]}}},
            fid_data,
        ),
    )
    monkeypatch.setattr(
        ng.varian,
        "guess_udic",
        lambda d, data: {
            "ndim": 1,
            0: {"sw": 4000.0, "obs": 400.0, "car": 1800.0, "size": len(data), "label": "1H", "time": True, "freq": False},
        },
    )
    res_var = analyze_spectrum(vdir)
    assert res_var["processing"]["source_format"] == "varian_fid"
    assert res_var["sample_count"] == 512


# ---------------------------------------------------------------------------
# Task 2: MagNET Boltzmann conformer averaging, vectorized nmr.simulate, reactions.py
# ---------------------------------------------------------------------------

def test_magnet_boltzmann_conformer_averaging(monkeypatch):
    calls = []

    def fake_predict_shifts(numbers, xyz, solvent="chloroform", n_passes=2, checkpoints_dir=None, device=None):
        calls.append((numbers, xyz, solvent, n_passes))
        if isinstance(xyz, list):
            # Return distinct shifts per conformer so Boltzmann weighting is testable
            out = []
            for idx, coords in enumerate(xyz):
                nums = numbers[idx]
                arr = np.full(len(nums), np.nan, dtype=float)
                for a_idx, z in enumerate(nums):
                    if int(z) == 6:
                        arr[a_idx] = 20.0 + idx * 1.0
                    elif int(z) == 1:
                        arr[a_idx] = 1.5 + idx * 0.1
                out.append(arr)
            return out
        arr = np.full(len(numbers), np.nan, dtype=float)
        arr[numbers == 6] = 20.0
        arr[numbers == 1] = 1.5
        return arr

    fake_mod = types.ModuleType("magnet")
    fake_mod.predict_shifts = fake_predict_shifts
    monkeypatch.setitem(sys.modules, "magnet", fake_mod)
    monkeypatch.setattr(worker, "_device", lambda: "cpu")

    # Butane has multiple rotamers within 3.0 kcal/mol
    res = worker._magnet({"smiles": "CCCC", "solvent": "chloroform"}, data_dir=".", spec={})
    assert res["conformer_count"] >= 1
    assert res["conformer_count"] <= 8
    assert "ETKDGv3 + MMFF94 Boltzmann average" in res["geometry"]
    assert isinstance(res["conformer_energy_kcal"], float)
    c_shifts = [a["shift"] for a in res["atoms"] if a["element"] == "C"]
    assert all(s is not None and 20.0 <= s <= 28.0 for s in c_shifts)


def test_vectorized_nmr_simulate_matches_reference():
    peaks = [
        {"shift_ppm": 7.26, "count": 2},
        {"shift_ppm": 3.85, "count": 3},
        {"shift_ppm": 1.25, "count": 6},
    ]
    rows = nmr.simulate(peaks, "1H", 400.0, width_hz=1.5, points=2048)
    assert len(rows) == 2048
    assert rows[0][0] > rows[-1][0]  # High ppm first

    # Compare against pure-Python formula at sample points
    low, high = -1.0, 12.0
    step = (high - low) / (2048 - 1)
    half = max(1.5 / 400.0 / 2.0, 2 * step)
    for x, total in rows[::128]:
        expected = sum(p["count"] * half * half / ((x - p["shift_ppm"]) ** 2 + half * half) for p in peaks)
        assert abs(total - expected) < 1e-10


def test_reactions_element_deficit_and_warnings(monkeypatch):
    # Transmutation: benzene (6 C) >> pyridine (5 C, 1 N) — same heavy-atom count (6), but N is invented!
    assert reactions._element_deficit("c1ccccc1", "c1ccncc1") == {"N": 1}
    assert reactions._short_of_atoms("c1ccccc1>>c1ccncc1") is True
    # When reagent supplies the element, deficit is empty
    assert reactions._element_deficit("c1ccccc1Br", "c1ccccc1C#N", reagents="C#N") == {}

    # products() attaches unbalanced_elements and warns
    monkeypatch.setattr(
        env,
        "call",
        lambda *a, **k: [[{"smiles": "c1ccncc1", "score": -0.1}, {"smiles": "c1ccccc1", "score": -0.5}]],
    )
    prod_ans = reactions.products("c1ccccc1")
    assert prod_ans["structures"][0]["unbalanced_elements"] == {"N": 1}
    assert "unbalanced_elements" not in prod_ans["structures"][1]
    assert any("unbalanced_elements" in w for w in prod_ans["warnings"])

    # retrosynthesis(steps='single') flags transmuted precursors
    monkeypatch.setattr(
        env,
        "call",
        lambda *a, **k: {"steps": "single", "options": [{"reactants": [["c1ccccc1"]], "probability": 0.8, "template": "t1"}]},
    )
    retro_single = reactions.retrosynthesis("c1ccncc1", engine="aizynthfinder", steps="single")
    assert retro_single["options"][0]["unbalanced_elements"] == {"N": 1}
    assert any("unbalanced_elements" in w for w in retro_single["warnings"])

    # conditions() allows incomplete mapping when main skeleton is mapped and emits a warning
    monkeypatch.setattr(
        env,
        "call",
        lambda *a, **k: {
            "template_level": "r1",
            "candidates": [{"catalyst": "None", "solvents": ["CN(C)C=O"], "reagents": [], "score": 0.5}],
        },
    )
    cond_ans = reactions.conditions("c1ccccc1Br", "c1ccccc1C#N")
    assert cond_ans["ok"] is True
    assert ":" in cond_ans["mapped_reaction"]
    assert any("incomplete" in w for w in cond_ans["warnings"])


# ---------------------------------------------------------------------------
# Task 3: LCMS multi-charge / adducts / Cl-Br isotopologues & hazards expansion
# ---------------------------------------------------------------------------

def test_lcms_expanded_adducts_and_halogen_isotopologues():
    # Low-MW compound (<300 Da): has [M+NH4]+, [M+MeCN+H]+, [2M+H]+, [2M+Na]+, [M+TFA-H]-, no [M+2H]2+
    small_adducts = _compute_adducts(180.042)
    assert list(small_adducts.keys())[:4] == ["[M+H]+", "[M-H]-", "[M+Na]+", "[M+formate]-"]
    for key in ("[M+NH4]+", "[M+MeCN+H]+", "[2M+H]+", "[2M+Na]+", "[M+TFA-H]-"):
        assert key in small_adducts
    assert "[M+2H]2+" not in small_adducts

    # High-MW compound (>=300 Da): includes [M+2H]2+
    large_adducts = build_adducts(450.200)
    assert "[M+2H]2+" in large_adducts
    assert abs(large_adducts["[M+2H]2+"] - (450.200 + 2 * 1.008) / 2.0) < 1e-4

    # Dibromobenzene (M = 233.868 Da; M+2 base peak at +1.997 Da -> [M+2+H]+ = 236.873)
    dibromo_smi = "Brc1ccc(Br)cc1"
    assert has_heavy_halogens(dibromo_smi) == (2, 0)
    assert needs_m_plus_2(dibromo_smi) is True
    br_adducts = build_adducts(233.868, smiles=dibromo_smi)
    assert "[M+2+H]+" in br_adducts and "[M+2-H]-" in br_adducts

    sp = ExpectedSpecies(
        name="DP",
        role="product",
        exact_mass=233.868,
        smiles=dibromo_smi,
        adducts=br_adducts,
    )
    # Only M+2 peak (236.9 m/z) reported as base peak — outside 1.5 Da of [M+H]+ (234.876), but matched via [M+2+H]+!
    matched = match_ions_to_species([("ES+", 236.88, 0)], [sp])
    assert matched is not None
    assert matched[0].name == "DP" and matched[1] == "[M+2+H]+"

    # Verify MassSpectrum.intensities halogen isotope check
    ms = MassSpectrum(mode="ES+", top_ions=[236.87, 234.88, 238.87], intensities=[100.0, 51.0, 49.0])
    note = verify_halogen_isotope_pattern([ms], sp, matched[1], matched[2])
    assert note is not None and "M/M+2 isotope cluster verified" in note


def test_hazards_expanded_table_parent_salt_fallback_and_smarts_alerts():
    assert len(hazards.HAZARDS) >= 110
    assert len(hazards.entries()) >= 110

    # Key bench reagents present
    for smi in (
        "[Li]CCCC",       # n-BuLi
        "[H-].[Na+]",     # NaH
        "O=C(Cl)C(=O)Cl", # oxalyl chloride
        "CS(=O)(=O)Cl",   # MsCl
        "Cc1ccc(S(=O)(=O)Cl)cc1",  # TsCl
        "C[Si](C)(C)Cl",  # TMSCl
        "CN(C)c1ccncc1",  # DMAP
        "O=[Os](=O)(=O)=O",  # OsO4
        "CCN(CC)S(F)(F)F",   # DAST
        "COCCOC",         # DME
        "CN(C)P(=O)(N(C)C)N(C)C",  # HMPA
    ):
        entry = hazards.lookup(smi)
        assert entry is not None, f"Expected {smi} in hazards table"

    # Salt-stripped parent-fragment fallback for unlisted salts of listed bases
    tea_hcl = hazards.lookup("CCN(CC)CC.Cl")
    assert tea_hcl is not None and tea_hcl["name"] == "triethylamine"
    assert "parent compound" in tea_hcl["note"]

    pyr_hcl = hazards.lookup("[nH+]1ccccc1.[Cl-]")
    assert pyr_hcl is not None and pyr_hcl["name"] == "pyridine"

    # SMARTS structural class alerts on novel unlisted molecules
    alert_cases = [
        ("c1ccc(CN=[N+]=[N-])cc1", "azide"),
        ("CC(C)(C)OOC(=O)c1ccccc1", "peroxide"),
        ("CCCCC(=O)Cl", "acyl_halide"),
        ("CCCCS(=O)(=O)Cl", "sulfonyl_halide"),
        ("CCOC(=O)C=[N+]=[N-]", "diazo"),
        ("O=C=Nc1ccccc1", "isocyanate"),
        ("N#Cc1ccccc1", "nitrile_inorganic_cyanide"),
    ]
    for smi, expected_class in alert_cases:
        info = hazards.assess(smi)
        assert info["listed"] is False
        classes = {a["class"] for a in info["class_alerts"]}
        assert expected_class in classes, f"Expected {expected_class} in {classes} for {smi}"

    # Verify for_rows keeps listed: False and attaches class_alerts when matched
    rows = [{"id": 1, "name": "benzyl azide", "role": "reagent", "smiles": "c1ccc(CN=[N+]=[N-])cc1"}]
    safety_rows = hazards.for_rows(rows)
    assert safety_rows[0]["listed"] is False
    assert any(a["class"] == "azide" for a in safety_rows[0]["class_alerts"])
    footer = "\n".join(hazards.lines(safety_rows))
    assert "structural class alert" in footer


def test_site_chem_js_expanded_valence_sulfur_and_phosphorus():
    import json
    import shutil
    import subprocess

    if not shutil.which("node"):
        pytest.skip("node not available")
    chem_js = Path(__file__).resolve().parents[2] / "site" / "chem.js"
    script = f"""
    const C = require({json.dumps(str(chem_js))});
    const dmso = {{
      atoms: [{{s:"C",x:0,y:0}},{{s:"S",x:40,y:0}},{{s:"O",x:40,y:40}},{{s:"C",x:80,y:0}}],
      bonds: [{{a:0,b:1,o:1}},{{a:1,b:2,o:2}},{{a:1,b:3,o:1}}],
    }};
    const sulfone = {{
      atoms: [{{s:"C",x:0,y:0}},{{s:"S",x:40,y:0}},{{s:"O",x:40,y:40}},{{s:"O",x:40,y:-40}},{{s:"C",x:80,y:0}}],
      bonds: [{{a:0,b:1,o:1}},{{a:1,b:2,o:2}},{{a:1,b:3,o:2}},{{a:1,b:4,o:1}}],
    }};
    const overS = {{
      atoms: [{{s:"C",x:0,y:0}},{{s:"S",x:40,y:0}},{{s:"O",x:40,y:40}},{{s:"O",x:40,y:-40}},{{s:"C",x:80,y:0}},{{s:"C",x:0,y:40}}],
      bonds: [{{a:0,b:1,o:2}},{{a:1,b:2,o:2}},{{a:1,b:3,o:2}},{{a:1,b:4,o:1}},{{a:1,b:5,o:1}}],
    }};
    const pOxide = {{
      atoms: [{{s:"C",x:0,y:0}},{{s:"P",x:40,y:0}},{{s:"O",x:40,y:40}},{{s:"C",x:80,y:0}},{{s:"C",x:40,y:-40}}],
      bonds: [{{a:0,b:1,o:1}},{{a:1,b:2,o:2}},{{a:1,b:3,o:1}},{{a:1,b:4,o:1}}],
    }};
    console.log(JSON.stringify({{
      sv: C.EL.S.v,
      pv: C.EL.P.v,
      dmso: C.toSmiles(dmso),
      sulfone: C.toSmiles(sulfone),
      overS: C.toSmiles(overS),
      pOxide: C.toSmiles(pOxide),
    }}));
    """
    proc = subprocess.run(["node", "-e", script], capture_output=True, text=True, check=True)
    data = json.loads(proc.stdout)
    assert data["sv"] == 2
    assert data["pv"] == 3
    assert data["dmso"] == "CS(=O)C"
    assert data["sulfone"] == "CS(=O)(=O)C"
    assert data["overS"] is None
    assert data["pOxide"] == "CP(=O)(C)C"

