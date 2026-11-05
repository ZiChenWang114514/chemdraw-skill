#!/usr/bin/env python3
"""
parse_analysis_file.py — Unified LCMS / NMR analysis file parser.

Detects whether a file is an LCMS report (Waters MassLynx PDF, standard or
manual integration; OpenLynx ``.rpt`` export; Shimadzu LabSolutions ``.daml``
file; Agilent ChemStation ``report.txt`` file; mzML / mzXML file; or Waters
``.raw`` folder) or an NMR PDF, then delegates to the appropriate parser and
returns a normalised dict.

Python API:
    from cdxml_toolkit.analysis.parse_analysis_file import parse_analysis_file
    result = parse_analysis_file("KL-7001-011-purified.pdf")
    # result["file_type"]  -> "lcms" or "nmr"
    # result["data"]       -> parsed data dict
"""

from __future__ import annotations

import dataclasses
import traceback
from typing import Any, Dict


def _dataclass_to_dict(obj: Any) -> Any:
    """Recursively convert dataclasses (and lists/dicts thereof) to plain dicts."""
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return {k: _dataclass_to_dict(v) for k, v in dataclasses.asdict(obj).items()}
    if isinstance(obj, list):
        return [_dataclass_to_dict(i) for i in obj]
    if isinstance(obj, dict):
        return {k: _dataclass_to_dict(v) for k, v in obj.items()}
    return obj


def _lcms_data(report: Any) -> Dict[str, Any]:
    """A parsed sample as a plain dict; an mzML / .raw dataset reports its traces by size, not point by point."""
    if hasattr(report, "to_dict"):
        data = report.to_dict()
        data["chromatograms"] = [
            {"trace_type": c["trace_type"], "wavelength": c["wavelength"], "units": c["units"],
             "points": len(c["times"]), "max_intensity": max(c["intensities"], default=0.0)}
            for c in data["chromatograms"]
        ]
        return data
    return _dataclass_to_dict(report)


def parse_analysis_file(pdf_path: str) -> Dict[str, Any]:
    """Detect and parse an LCMS report (PDF, .rpt, .daml, report.txt, mzML/mzXML, Waters .raw) or an NMR PDF.

    Detection order:
      0.  Registered LCMS formats (``lcms_analyzer.LCMS_FORMATS``): OpenLynx ``.rpt``,
          Shimadzu ``.daml``, Agilent ``report.txt``, mzML / mzXML, Waters ``.raw``
      1.  Waters MassLynx standard report    → ``parse_report()``
      2.  Waters MassLynx manual integration → ``parse_manual_report()``
      3.  NMR PDF (MestReNova)               → ``extract_nmr_data()``
      4.  None of the above                  → error dict

    Args:
        pdf_path: Absolute or relative path to the PDF, .rpt, .daml, or .txt file.

    Returns:
        Dict with keys:
            ok (bool)
            file_type ("lcms" | "nmr") — only present when ok=True
            file_path (str)
            data (dict) — parsed content; structure depends on file_type:
                lcms (.rpt, one sample):  LCMSReport as dict
                lcms (.rpt, several):     {"source_format": "openlynx_rpt",
                                  "sample_count": N, "samples": [LCMSReport dict, ...]}
                lcms (.daml / .txt / standard PDF): LCMSReport as dict
                lcms (mzML / mzXML / .raw): LCMSAnalysis as dict, traces summarised
                lcms (manual):    ManualLCMSReport as dict, plus
                                  "variant": "manual_integration"
                nmr:              {"nmr_strings": ["1H NMR ..."]}
            error (str) — only present when ok=False
    """
    from cdxml_toolkit.analysis.lcms_analyzer import (
        is_waters_report,
        lcms_format,
        parse_report,
        is_manual_integration,
        parse_manual_report,
    )
    from cdxml_toolkit.analysis.deterministic.procedure_writer import extract_nmr_data

    base_result: Dict[str, Any] = {"file_path": pdf_path}

    # --- Attempt 0: a registered LCMS format (.rpt, .daml, report.txt, mzML/mzXML, Waters .raw) ---
    fmt = lcms_format(pdf_path)
    if fmt is not None:
        try:
            if not fmt.detect(pdf_path):
                return {**base_result, "ok": False, "error": f"Not a {fmt.label}."}
            reports = fmt.parse(pdf_path)
        except Exception as exc:
            return {
                **base_result,
                "ok": False,
                "file_type": "lcms",
                "error": f"{fmt.label} detected but parsing failed: {exc}",
                "traceback": traceback.format_exc(),
            }
        if len(reports) == 1:
            data: Any = _lcms_data(reports[0])
        else:
            data = {
                "source_format": fmt.key,
                "sample_count": len(reports),
                "samples": [_lcms_data(r) for r in reports],
            }
        return {**base_result, "ok": True, "file_type": "lcms", "data": data}

    # --- Attempt 1: standard Waters report ---
    try:
        if is_waters_report(pdf_path):
            report = parse_report(pdf_path)
            return {
                **base_result,
                "ok": True,
                "file_type": "lcms",
                "data": _dataclass_to_dict(report),
            }
    except Exception as exc:
        return {
            **base_result,
            "ok": False,
            "file_type": "lcms",
            "error": f"Waters report detected but parsing failed: {exc}",
            "traceback": traceback.format_exc(),
        }

    # --- Attempt 2: manual integration report ---
    try:
        if is_manual_integration(pdf_path):
            report = parse_manual_report(pdf_path)
            data = _dataclass_to_dict(report)
            data["variant"] = "manual_integration"
            return {
                **base_result,
                "ok": True,
                "file_type": "lcms",
                "data": data,
            }
    except Exception as exc:
        return {
            **base_result,
            "ok": False,
            "file_type": "lcms",
            "error": f"Manual integration report detected but parsing failed: {exc}",
            "traceback": traceback.format_exc(),
        }

    # --- Attempt 3: NMR PDF ---
    try:
        nmr_strings = extract_nmr_data(pdf_path)
        if nmr_strings:
            return {
                **base_result,
                "ok": True,
                "file_type": "nmr",
                "data": {"nmr_strings": nmr_strings},
            }
    except Exception as exc:
        return {
            **base_result,
            "ok": False,
            "error": f"NMR extraction failed: {exc}",
            "traceback": traceback.format_exc(),
        }

    # --- Nothing matched ---
    return {
        **base_result,
        "ok": False,
        "error": (
            "Could not detect file type: not a Waters standard report, "
            "not a manual integration export, and no NMR data strings found."
        ),
    }
