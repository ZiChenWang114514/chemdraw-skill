#!/usr/bin/env python3
"""
Format Procedure Entry — Agent-driven lab book entry formatter.

Takes a JSON list of entries from an LLM agent and produces a complete lab
book entry.  All numbers (RT, m/z, area%, purity, conversion%) come from
re-parsing the LCMS PDFs via parse_report().  The LLM only provides:
  - Peak identification: (name, approximate RT, ion) as search keys
  - Labels, detector choice, free-form text
  - Peak assignments (compound_related flags for conversion)

Entry types:
  text          — passthrough (procedure, section headers, notes)
  lcms-species  — RT + ion + UV for assigned peaks, optionally purity
  lcms-areas    — area% for assigned peaks from one file
  lcms-manual   — area% from manually integrated LC PDF, optionally with
                  MS data from a Waters report
  nmr           — NMR data strings, rendered verbatim

Usage:
    python format_procedure_entry.py --input assignments.json
    python format_procedure_entry.py --input assignments.json --output entry.txt
    echo '{ ... }' | python format_procedure_entry.py
"""

import argparse
import json
import math
import os
import sys
from typing import List, Optional, Dict, Tuple

from .lcms_analyzer import (
    parse_report, LCMSReport, ChromPeak,
    parse_manual_report, ManualLCMSReport, ManualLCMSSample, ManualPeak,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

RT_TOLERANCE = 0.05  # minutes — tolerance for peak matching by RT

# ---------------------------------------------------------------------------
# Peak matching
# ---------------------------------------------------------------------------


def _match_peak(report: LCMSReport, rt: float,
                ion: Optional[dict] = None,
                tol: float = RT_TOLERANCE) -> Optional[ChromPeak]:
    """Find a peak in *report* matching the given RT (±tol).

    If *ion* is provided ({"mode": "ES+", "mz": 346.1}), it is used to
    disambiguate when multiple peaks fall within the RT window: the peak
    whose top ion is closest to the requested m/z wins.  If no ion is
    given, the peak closest in RT wins.
    """
    candidates = [p for p in report.peaks if abs(p.rt - rt) <= tol]
    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0]

    # Multiple candidates — disambiguate
    if ion:
        target_mode = ion.get("mode", "ES+")
        target_mz = ion.get("mz")
        if target_mz is not None:
            def _ion_distance(peak: ChromPeak) -> float:
                for spec in peak.ms_spectra:
                    if spec.mode == target_mode and spec.top_ions:
                        return min(abs(mz - target_mz) for mz in spec.top_ions)
                return 9999.0
            candidates.sort(key=_ion_distance)
            if _ion_distance(candidates[0]) < 2.0:  # reasonable m/z match
                return candidates[0]

    # Fall back to closest RT
    candidates.sort(key=lambda p: abs(p.rt - rt))
    return candidates[0]


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------


def _format_lambda_max(wavelengths: List[float]) -> str:
    """Format UV lambda max values, e.g. 'λmax 218, 254 nm'."""
    if not wavelengths:
        return ""
    wl_strs = [str(math.floor(wl + 0.5)) for wl in sorted(wavelengths)]
    return f"λmax {', '.join(wl_strs)} nm"


def _select_ion(peak: ChromPeak, override: Optional[dict] = None) -> str:
    """Select the representative ion string for a peak.

    Returns e.g. "ESI+ 346.1" or "ESI- 344.1" or "UV only".
    If *override* is given ({"mode": "ES-", "rank": 1}), use that mode/rank.
    """
    if override:
        mode = override.get("mode", "ES+")
        rank = override.get("rank", 0)  # 0-indexed
        for spec in peak.ms_spectra:
            if spec.mode == mode and len(spec.top_ions) > rank:
                mode_label = "ESI+" if mode == "ES+" else "ESI−"
                return f"{mode_label} {spec.top_ions[rank]:.1f}"

    # Default: top ESI+ ion, then ESI-, then UV only
    for mode_pref in ("ES+", "ES-"):
        for spec in peak.ms_spectra:
            if spec.mode == mode_pref and spec.top_ions:
                mode_label = "ESI+" if mode_pref == "ES+" else "ESI−"
                return f"{mode_label} {spec.top_ions[0]:.1f}"

    return "UV only"


def _select_area(peak: ChromPeak, detector: str) -> Optional[float]:
    """Read area% for the given detector."""
    if detector.upper() == "TAC":
        return peak.area_pct
    elif detector == "220nm":
        return peak.area_pct_220nm
    elif detector == "254nm":
        return peak.area_pct_254nm
    return None


def _method_header(report: LCMSReport) -> str:
    """Format '(instrument, method)' string."""
    return f"({report.instrument}, {report.method_short})"


# ---------------------------------------------------------------------------
# Report cache — avoid re-parsing the same PDF multiple times
# ---------------------------------------------------------------------------

_report_cache: Dict[str, LCMSReport] = {}
_manual_cache: Dict[str, ManualLCMSReport] = {}


def _get_report(path: str) -> LCMSReport:
    """Parse and cache a standard Waters LCMS report."""
    abs_path = os.path.abspath(path)
    if abs_path not in _report_cache:
        _report_cache[abs_path] = parse_report(path)
    return _report_cache[abs_path]


def _get_manual_report(path: str) -> ManualLCMSReport:
    """Parse and cache a manual integration PDF."""
    abs_path = os.path.abspath(path)
    if abs_path not in _manual_cache:
        _manual_cache[abs_path] = parse_manual_report(path)
    return _manual_cache[abs_path]


def _find_manual_sample(report: ManualLCMSReport,
                        sample_name: Optional[str]) -> ManualLCMSSample:
    """Find a sample by name in a manual integration report.

    If *sample_name* is None and there's only one sample, return it.
    Otherwise match by substring (case-insensitive).
    """
    if not report.samples:
        raise ValueError(f"No samples in {report.filename}")
    if sample_name is None:
        if len(report.samples) == 1:
            return report.samples[0]
        raise ValueError(
            f"{report.filename} has {len(report.samples)} samples; "
            f"specify 'sample' in the entry. Available: "
            + ", ".join(s.sample_name for s in report.samples))
    # Substring match (case-insensitive)
    target = sample_name.lower()
    for s in report.samples:
        if target in s.sample_name.lower():
            return s
    raise ValueError(
        f"Sample '{sample_name}' not found in {report.filename}. "
        f"Available: " + ", ".join(s.sample_name for s in report.samples))


def _match_manual_peak(sample: ManualLCMSSample, rt: float,
                       tol: float = RT_TOLERANCE) -> Optional[ManualPeak]:
    """Find a peak in a manual sample by RT proximity."""
    candidates = [p for p in sample.peaks if abs(p.rt - rt) <= tol]
    if not candidates:
        return None
    candidates.sort(key=lambda p: abs(p.rt - rt))
    return candidates[0]


# ---------------------------------------------------------------------------
# Entry processors
# ---------------------------------------------------------------------------


def _process_text(entry: dict) -> str:
    """Passthrough text entry."""
    return entry.get("content", "")


def _process_nmr(entry: dict) -> str:
    """NMR data entry — render verbatim, one per line."""
    data = entry.get("data", [])
    if isinstance(data, str):
        data = [data]
    return "\n".join(data)


def _process_lcms_species(entry: dict) -> str:
    """Format RT + ion + UV for assigned peaks, optionally with purity.

    Output: "{label} ({instrument}, {method}): Name1 RT = ...; Name2 RT = ..."
    """
    report = _get_report(entry["file"])
    peaks_cfg = entry.get("peaks", [])

    parts = []
    for pcfg in peaks_cfg:
        peak = _match_peak(report, pcfg["rt"], pcfg.get("ion"))
        if peak is None:
            parts.append(f"{pcfg['name']} n.d.")
            continue

        # RT + ion
        ion_str = _select_ion(peak, pcfg.get("ion_override"))
        lmax = _format_lambda_max(peak.uv_lambda_max)

        segments = [f"{pcfg['name']} RT = {peak.rt:.2f} min", ion_str]
        if lmax:
            segments.append(lmax)

        # Purity (optional)
        if pcfg.get("purity"):
            purity_parts = []
            if peak.area_pct is not None:
                purity_parts.append(f"TAC {peak.area_pct:.1f}%")
            if peak.area_pct_220nm is not None:
                purity_parts.append(f"220nm {peak.area_pct_220nm:.1f}%")
            if peak.area_pct_254nm is not None:
                purity_parts.append(f"254nm {peak.area_pct_254nm:.1f}%")
            if purity_parts:
                segments.append("purity " + ", ".join(purity_parts))

        parts.append(", ".join(segments))

    header = f"{entry.get('label', 'LCMS')} {_method_header(report)}"
    return f"{header}: {'; '.join(parts)}"


def _process_lcms_areas(entry: dict) -> str:
    """Format area% for assigned peaks from one file.

    Output: "{label} ({instrument}, {method}, {detector}): Name1 x%, Name2 y%"
    Optionally with conversion for the SM peak.
    """
    report = _get_report(entry["file"])
    detector = entry.get("detector", "TAC")
    peaks_cfg = entry.get("peaks", [])
    show_conversion = entry.get("show_conversion", False)

    # Match all peaks
    matched = []
    for pcfg in peaks_cfg:
        peak = _match_peak(report, pcfg["rt"], pcfg.get("ion"))
        area = _select_area(peak, detector) if peak else None
        matched.append({
            "name": pcfg["name"],
            "area": area,
            "compound_related": pcfg.get("compound_related", False),
            "peak": peak,
        })

    # Compute conversion if requested
    conversion_str = None
    if show_conversion:
        sm_area = None
        compound_total = 0.0
        has_compound = False
        for m in matched:
            if m["name"].upper() == "SM" and m["area"] is not None:
                sm_area = m["area"]
            if m["compound_related"] and m["area"] is not None:
                compound_total += m["area"]
                has_compound = True

        if sm_area is None and has_compound:
            conversion_str = "complete"
        elif sm_area is not None and compound_total > 0:
            conv = (1.0 - sm_area / compound_total) * 100.0
            conversion_str = f"{conv:.0f}%"

    # Format parts
    parts = []
    for m in matched:
        if m["area"] is None:
            parts.append(f"{m['name']} n.d.")
        else:
            area_str = f"{m['name']} {m['area']:.1f}%"
            # Append conversion to SM
            if (show_conversion and m["name"].upper() == "SM"
                    and conversion_str is not None):
                area_str += f" ({conversion_str} conversion)"
            parts.append(area_str)

    header = f"{entry.get('label', 'LCMS')} {_method_header(report)}, {detector}"
    return f"{header}: {', '.join(parts)}"


def _process_lcms_manual(entry: dict) -> str:
    """Format area% from a manually integrated LCMS PDF.

    Handles two cases:
      1. Tracking/composition: area% from manual file, no MS data.
      2. Purity: area% from manual file, MS data from a Waters report
         (specified via optional 'ms_file').

    JSON examples:

        Tracking:
        {"type": "lcms-manual", "label": "Manual LCAP",
         "file": "manint.pdf", "sample": "KL-7001-023-50min",
         "peaks": [{"name": "DP", "rt": 0.57}, {"name": "SM", "rt": 1.01}],
         "show_conversion": true}

        Purity:
        {"type": "lcms-manual", "label": "Purified product LC",
         "file": "LC.pdf",
         "ms_file": "driedOWE-dil.pdf",
         "peaks": [{"name": "DP", "rt": 1.12, "purity": true,
                     "ion": {"mode": "ES+", "mz": 346.0}}]}
    """
    manual = _get_manual_report(entry["file"])
    sample = _find_manual_sample(manual, entry.get("sample"))
    peaks_cfg = entry.get("peaks", [])
    show_conversion = entry.get("show_conversion", False)

    # Optionally load a Waters report for MS data
    ms_report = _get_report(entry["ms_file"]) if entry.get("ms_file") else None

    parts = []
    sm_area = None
    compound_total = 0.0
    has_compound = False
    matched_list = []

    for pcfg in peaks_cfg:
        mpeak = _match_manual_peak(sample, pcfg["rt"])
        area = mpeak.area_pct if mpeak else None
        is_compound = pcfg.get("compound_related", False)

        if area is not None:
            if pcfg["name"].upper() == "SM":
                sm_area = area
            if is_compound:
                compound_total += area
                has_compound = True

        matched_list.append({
            "name": pcfg["name"],
            "area": area,
            "mpeak": mpeak,
            "cfg": pcfg,
        })

    # Conversion
    conversion_str = None
    if show_conversion:
        if sm_area is None and has_compound:
            conversion_str = "complete"
        elif sm_area is not None and compound_total > 0:
            conv = (1.0 - sm_area / compound_total) * 100.0
            conversion_str = f"{conv:.0f}%"

    for m in matched_list:
        pcfg = m["cfg"]

        if pcfg.get("purity") and m["mpeak"] is not None:
            # Purity mode: RT + ion from Waters report, purity from manual
            segments = [f"{m['name']} RT = {m['mpeak'].rt:.2f} min"]
            if ms_report:
                ws_peak = _match_peak(ms_report, pcfg["rt"], pcfg.get("ion"))
                if ws_peak:
                    segments.append(_select_ion(ws_peak, pcfg.get("ion_override")))
                    lmax = _format_lambda_max(ws_peak.uv_lambda_max)
                    if lmax:
                        segments.append(lmax)
            segments.append(f"purity {m['mpeak'].area_pct:.1f}% (manual integration)")
            parts.append(", ".join(segments))
        elif m["area"] is None:
            parts.append(f"{m['name']} n.d.")
        else:
            area_str = f"{m['name']} {m['area']:.1f}%"
            if (show_conversion and m["name"].upper() == "SM"
                    and conversion_str is not None):
                area_str += f" ({conversion_str} conversion)"
            parts.append(area_str)

    header = f"{entry.get('label', 'Manual LC')} ({manual.instrument})"
    return f"{header}: {', '.join(parts)}"


# ---------------------------------------------------------------------------
# Entry dispatch
# ---------------------------------------------------------------------------

_PROCESSORS = {
    "text": _process_text,
    "nmr": _process_nmr,
    "lcms-species": _process_lcms_species,
    "lcms-areas": _process_lcms_areas,
    "lcms-manual": _process_lcms_manual,
}


def process_entries(entries: List[dict]) -> str:
    """Process all entries in order, return the formatted lab book entry."""
    lines = []
    for entry in entries:
        entry_type = entry.get("type", "text")
        processor = _PROCESSORS.get(entry_type)
        if processor is None:
            print(f"Warning: unknown entry type '{entry_type}', skipping",
                  file=sys.stderr)
            continue
        lines.append(processor(entry))
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Format a lab book entry from LLM agent assignments")
    parser.add_argument('--input', '-i', type=str, default=None,
                        help='JSON input file (default: stdin)')
    parser.add_argument('--output', '-o', type=str, default=None,
                        help='Output file (default: stdout)')
    args = parser.parse_args(argv)

    # Read JSON
    if args.input:
        with open(args.input, 'r', encoding='utf-8') as f:
            data = json.load(f)
    else:
        data = json.load(sys.stdin)

    entries = data.get("entries", [])
    if not entries:
        print("Error: no entries in input JSON", file=sys.stderr)
        return 1

    # Clear cache before run
    _report_cache.clear()
    _manual_cache.clear()

    result = process_entries(entries)

    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(result + "\n")
        print(f"Output written to {args.output}", file=sys.stderr)
    else:
        sys.stdout.buffer.write(result.encode('utf-8'))
        sys.stdout.buffer.write(b'\n')

    return 0


if __name__ == "__main__":
    sys.exit(main())
