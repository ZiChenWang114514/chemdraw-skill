#!/usr/bin/env python3
"""
parse_analysis_file.py — Unified LCMS / NMR analysis file parser.

Detects whether a file is an LCMS report (Waters MassLynx PDF, standard or
manual integration; OpenLynx ``.rpt`` export; Shimadzu LabSolutions ``.daml``
file; or Agilent ChemStation ``report.txt`` file) or an NMR PDF, then
delegates to the appropriate parser and returns a normalised dict.

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


def parse_analysis_file(pdf_path: str) -> Dict[str, Any]:
    """Detect and parse an LCMS report (PDF, .rpt, .daml, or report.txt) or an NMR PDF.

    Detection order:
      0a. OpenLynx ``.rpt`` export           → ``parse_reports()``
      0b. Shimadzu LabSolutions ``.daml``    → ``parse_report()``
      0c. Agilent ChemStation ``report.txt`` → ``parse_report()``
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
                lcms (manual):    ManualLCMSReport as dict, plus
                                  "variant": "manual_integration"
                nmr:              {"nmr_strings": ["1H NMR ..."]}
            error (str) — only present when ok=False
    """
    from cdxml_toolkit.analysis.lcms_analyzer import (
        is_waters_report,
        parse_report,
        parse_reports,
        is_manual_integration,
        parse_manual_report,
        is_rpt_path,
        is_daml_path,
        is_agilent_txt_path,
    )
    from cdxml_toolkit.analysis.deterministic.procedure_writer import extract_nmr_data

    base_result: Dict[str, Any] = {"file_path": pdf_path}

    # --- Attempt 0a: OpenLynx .rpt export (text, one or many samples) ---
    if is_rpt_path(pdf_path):
        try:
            from cdxml_toolkit.analysis.openlynx_rpt import is_openlynx_rpt
            if not is_openlynx_rpt(pdf_path):
                return {
                    **base_result,
                    "ok": False,
                    "error": "Not an OpenLynx .rpt export (no [SAMPLE] block at the start).",
                }
            reports = parse_reports(pdf_path)
        except Exception as exc:
            return {
                **base_result,
                "ok": False,
                "file_type": "lcms",
                "error": f"OpenLynx .rpt detected but parsing failed: {exc}",
                "traceback": traceback.format_exc(),
            }
        if len(reports) == 1:
            data: Any = _dataclass_to_dict(reports[0])
        else:
            data = {
                "source_format": "openlynx_rpt",
                "sample_count": len(reports),
                "samples": [_dataclass_to_dict(r) for r in reports],
            }
        return {**base_result, "ok": True, "file_type": "lcms", "data": data}

    # --- Attempt 0b: Shimadzu LabSolutions .daml export ---
    if is_daml_path(pdf_path):
        try:
            from cdxml_toolkit.analysis.shimadzu_daml import is_shimadzu_daml
            if not is_shimadzu_daml(pdf_path):
                return {
                    **base_result,
                    "ok": False,
                    "error": "Not a Shimadzu LabSolutions .daml file (missing <DAML> root element).",
                }
            report = parse_report(pdf_path)
        except Exception as exc:
            return {
                **base_result,
                "ok": False,
                "file_type": "lcms",
                "error": f"Shimadzu .daml detected but parsing failed: {exc}",
                "traceback": traceback.format_exc(),
            }
        return {
            **base_result,
            "ok": True,
            "file_type": "lcms",
            "data": _dataclass_to_dict(report),
        }

    # --- Attempt 0c: Agilent ChemStation report.txt ---
    if is_agilent_txt_path(pdf_path):
        try:
            from cdxml_toolkit.analysis.agilent_txt import is_agilent_report_txt
            if not is_agilent_report_txt(pdf_path):
                return {
                    **base_result,
                    "ok": False,
                    "error": "Not an Agilent ChemStation report.txt file.",
                }
            report = parse_report(pdf_path)
        except Exception as exc:
            return {
                **base_result,
                "ok": False,
                "file_type": "lcms",
                "error": f"Agilent report.txt detected but parsing failed: {exc}",
                "traceback": traceback.format_exc(),
            }
        return {
            **base_result,
            "ok": True,
            "file_type": "lcms",
            "data": _dataclass_to_dict(report),
        }

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
