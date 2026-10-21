#!/usr/bin/env python3
"""
parse_analysis_file.py — Unified LCMS / NMR PDF parser.

Detects whether a PDF is an LCMS report (Waters MassLynx standard or manual
integration) or an NMR report, then delegates to the appropriate parser and
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


def parse_analysis_file(pdf_path: str) -> Dict[str, Any]:
    """Detect and parse an LCMS or NMR PDF report.

    Detection order:
      1. Waters MassLynx standard report  → ``parse_report()``
      2. Waters MassLynx manual integration → ``parse_manual_report()``
      3. NMR PDF (MestReNova)             → ``extract_nmr_data()``
      4. None of the above               → error dict

    Args:
        pdf_path: Absolute or relative path to the PDF file.

    Returns:
        Dict with keys:
            ok (bool)
            file_type ("lcms" | "nmr") — only present when ok=True
            file_path (str)
            data (dict) — parsed content; structure depends on file_type:
                lcms (standard):  LCMSReport as dict
                lcms (manual):    ManualLCMSReport as dict, plus
                                  "variant": "manual_integration"
                nmr:              {"nmr_strings": ["1H NMR ..."]}
            error (str) — only present when ok=False
    """
    from cdxml_toolkit.analysis.lcms_analyzer import (
        is_waters_report,
        parse_report,
        is_manual_integration,
        parse_manual_report,
    )
    from cdxml_toolkit.analysis.deterministic.procedure_writer import extract_nmr_data

    base_result: Dict[str, Any] = {"file_path": pdf_path}

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
