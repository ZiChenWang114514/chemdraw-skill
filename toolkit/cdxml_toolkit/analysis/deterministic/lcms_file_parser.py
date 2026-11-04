"""Unified LCMS file parser dispatcher.

Routes ``.mzml`` and ``.mzxml`` files to :func:`parse_mzml`, Waters ``.raw``
directories to :func:`parse_waters_raw`, and vendor report files
(``.pdf``, ``.rpt``, ``.daml``, ``.txt``) to :func:`parse_report`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Union

from ..lcms_analyzer import LCMSReport, parse_report
from .mzml_parser import (
    Chromatogram,
    LCMSAnalysis,
    LCMSPeak,
    MassSpectrum,
    SampleInfoDict,
    parse_mzml,
)
from .waters_raw import parse_waters_header, parse_waters_raw

SUPPORTED_LCMS_EXTENSIONS = (".mzml", ".mzxml", ".raw", ".pdf", ".rpt", ".daml", ".txt", ".d")


def _report_to_analysis(report: LCMSReport, file_path: Path, fmt: str) -> LCMSAnalysis:
    """Convert a parsed ``LCMSReport`` into an ``LCMSAnalysis`` object."""
    peaks = []
    for p in report.peaks:
        spectra = [
            MassSpectrum(
                mz_values=list(ms.top_ions),
                intensities=list(ms.intensities) if ms.intensities else [100.0] * len(ms.top_ions),
                mode=ms.mode,
                rt=p.rt,
                top_ions=list(ms.top_ions),
            )
            for ms in p.ms_spectra
        ]
        peaks.append(
            LCMSPeak(
                peak_id=p.peak_id,
                rt=p.rt,
                area=p.area,
                area_pct=p.area_pct,
                ms_spectra=spectra,
                spectrum=spectra[0] if spectra else None,
                uv_lambda_max=list(p.uv_lambda_max),
                area_220nm=p.area_220nm,
                area_254nm=p.area_254nm,
            )
        )
    all_spectra = [s for pk in peaks for s in pk.ms_spectra]
    acq_date = f"{report.date} {report.time}".strip()
    sample_info = SampleInfoDict(
        {
            "Sample Description": report.sample_name,
            "sample_description": report.sample_name,
            "sample_name": report.sample_name,
            "Instrument": report.instrument,
            "instrument": report.instrument,
            "Acquired Date": report.date,
            "Acquired Time": report.time,
            "acquisition_date": acq_date,
            "Inlet Method": report.method_path,
            "Conditions": report.method_short,
        }
    )
    return LCMSAnalysis(
        filename=report.filename or file_path.name,
        file_path=str(file_path.resolve()),
        format=fmt,
        chromatograms=[],
        peaks=peaks,
        spectra=all_spectra,
        sample_info=sample_info,
        instrument=report.instrument,
        acquisition_date=acq_date,
        method=report.method_path or report.method_short,
        method_path=report.method_path,
        method_short=report.method_short,
        sample_name=report.sample_name,
        date=report.date,
        time=report.time,
        detector=report.detector,
    )


def parse_lcms_file(path: Union[str, Path], *, sample: Optional[Union[int, str]] = None) -> LCMSAnalysis:
    """Parse an LCMS file or directory into an ``LCMSAnalysis`` instance.

    Supported formats:
    - ``.mzml`` / ``.mzxml`` -> :func:`parse_mzml`
    - ``.raw`` directory -> :func:`parse_waters_raw`
    - ``.pdf``, ``.rpt``, ``.daml``, ``.txt``, ``.d`` -> :func:`parse_report`
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"LCMS file not found: {p}")

    ext = p.suffix.lower()
    if ext in (".mzml", ".mzxml"):
        return parse_mzml(p)

    if p.is_dir():
        if ext == ".raw" or (p / "_HEADER.TXT").exists() or (p / "_header.txt").exists():
            return parse_waters_raw(p)
        if ext == ".d" and (p / "report.txt").exists():
            rep = parse_report(str(p / "report.txt"), sample=sample)
            return _report_to_analysis(rep, p, "Agilent .D")
        raise ValueError(f"Unsupported LCMS directory format: {p}")

    if p.name.upper() in ("_HEADER.TXT", "HEADER.TXT") and p.parent.suffix.lower() == ".raw":
        return parse_waters_raw(p.parent)

    if ext in (".pdf", ".rpt", ".daml", ".txt"):
        rep = parse_report(str(p), sample=sample)
        return _report_to_analysis(rep, p, ext.lstrip("."))

    raise ValueError(f"Unsupported LCMS file extension '{ext}' for {p}")


__all__ = [
    "Chromatogram",
    "LCMSAnalysis",
    "LCMSPeak",
    "MassSpectrum",
    "SUPPORTED_LCMS_EXTENSIONS",
    "parse_lcms_file",
    "parse_mzml",
    "parse_waters_header",
    "parse_waters_raw",
]
