#!/usr/bin/env python3
"""
OpenLynx ``.rpt`` report parser.

Waters MassLynx / OpenLynx can write an "RPT" text export in which every
sample is a ``[SAMPLE]`` block.  Each block holds one ``[FUNCTION]`` per
detector (ES+, ES-, DAD, ...) with ``[SPECTRUM]`` blocks (one per integrated
peak) and ``[CHROMATOGRAM]`` blocks (trace plus ``[PEAK]`` integration rows)::

    [SAMPLE]
    {
    Sample  1
    Well    4:1
    FileName    AACM10177-01
    ...
    [FUNCTION]
    {
    Function    1
    IonMode     ES+
    Type        MS
    [SPECTRUM]
    {
    Peak ID     1
    Time        1.2300
    [MS]
    {
    ;Mass   % BPI
    102.96  6.765
    ...

This module turns that text into the same ``LCMSReport`` / ``ChromPeak`` /
``MassSpectrum`` data the PDF analyzer (``lcms_analyzer.parse_report``)
produces, so every downstream tool accepts either format.  One ``.rpt`` file
usually holds many samples (a plate or an auto-sampler batch), so
``parse_rpt`` returns a list with one ``LCMSReport`` per sample.

Mapping to the PDF data shape:
  - ``ChromPeak.area`` / ``area_pct``: the DAD total-absorbance trace
    ("DAD: TIC", the PDF "TAC" table).  Without a DAD TIC trace the MS TIC
    trace is used instead and ``LCMSReport.detector`` says so.
  - ``area_220nm`` / ``area_254nm``: single-wavelength DAD traces near 220
    and 254 nm, when the export has them.
  - ``ms_spectra``: one ``MassSpectrum`` per ionisation mode with the tallest
    ions (by % base peak), plus their relative intensities.
  - ``uv_lambda_max``: local maxima of the DAD spectrum of the peak.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from cdxml_toolkit.analysis.lcms_analyzer import (
    ChromPeak,
    LCMSReport,
    MassSpectrum,
    parse_method_short,
)

# Ions below this fraction of the base peak are not reported (the OpenLynx
# default acceptance threshold for "relative" mode is 20 %).
MIN_ION_REL_PCT = 20.0
MAX_IONS_PER_MODE = 5
# A UV maximum must reach this fraction of the spectrum maximum.
UV_MIN_REL_PCT = 10.0
UV_MAX_MAXIMA = 4
# Peaks of two detectors are the same peak when their apex times are this close.
RT_MATCH_TOL = 0.03
# A wavelength trace counts as 220 or 254 nm within this many nm.
WAVELENGTH_TOL = 2.0


# ---------------------------------------------------------------------------
# Generic block parser
# ---------------------------------------------------------------------------

@dataclass
class _Node:
    name: str
    props: Dict[str, str] = field(default_factory=dict)
    children: List["_Node"] = field(default_factory=list)
    rows: List[Tuple[float, float]] = field(default_factory=list)
    n_rows: int = 0

    def get(self, key: str, default: str = "") -> str:
        return self.props.get(key, default)

    def kids(self, name: str) -> List["_Node"]:
        return [c for c in self.children if c.name == name]


# Blocks whose body is free text, or numeric rows we keep / only count.
_RAW_BLOCKS = {"INLET PARAMETERS"}
_ROW_BLOCKS = {"MS"}
_COUNT_ROW_BLOCKS = {"TRACE"}

_SECTION_RE = re.compile(r"^\[([^\]]+)\]\s*$")


def decode_rpt(data: bytes) -> str:
    """Decode the bytes of an .rpt file (UTF-16 with BOM, UTF-8, else cp1252)."""
    if data[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return data.decode("utf-16", errors="replace")
    if data[:3] == b"\xef\xbb\xbf":
        return data[3:].decode("utf-8", errors="replace")
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode("cp1252", errors="replace")


def _to_float(token: str) -> Optional[float]:
    try:
        return float(token)
    except ValueError:
        return None


def _parse_block(lines: List[str]) -> _Node:
    """Parse the lines of one top-level [SAMPLE] block into a node tree."""
    root = _Node("SAMPLE")
    stack: List[_Node] = [root]
    pending: Optional[str] = None
    raw_depth = 0
    started = False
    for line in lines:
        node = stack[-1]
        if raw_depth:
            if line == "}":
                raw_depth = 0
                stack.pop()
            continue
        if pending is not None:
            name, pending = pending, None
            if line.strip() == "{":
                if not started and name == "SAMPLE":
                    started = True
                    continue
                child = _Node(name)
                node.children.append(child)
                stack.append(child)
                if name in _RAW_BLOCKS:
                    raw_depth = 1
                continue
        stripped = line.strip()
        m = _SECTION_RE.match(stripped)
        if m:
            pending = m.group(1)
            continue
        if stripped == "}":
            if len(stack) > 1:
                stack.pop()
            continue
        if stripped == "{" or not stripped:
            continue
        if node.name in _ROW_BLOCKS or node.name in _COUNT_ROW_BLOCKS:
            if stripped.startswith(";"):
                continue
            parts = stripped.split("\t")
            if len(parts) >= 2:
                x, y = _to_float(parts[0]), _to_float(parts[1])
                if x is not None and y is not None:
                    node.n_rows += 1
                    if node.name in _ROW_BLOCKS:
                        node.rows.append((x, y))
            continue
        key, _, value = line.partition("\t")
        key = key.strip()
        if key and key not in node.props:
            node.props[key] = value.strip()
    return root


def _split_samples(text: str) -> List[List[str]]:
    blocks: List[List[str]] = []
    current: Optional[List[str]] = None
    for line in text.splitlines():
        if line.strip() == "[SAMPLE]":
            current = []
            blocks.append(current)
        if current is not None:
            current.append(line)
    return blocks


# ---------------------------------------------------------------------------
# Detection
# ---------------------------------------------------------------------------

def is_openlynx_rpt(path: str) -> bool:
    """True when *path* looks like an OpenLynx RPT export (content based)."""
    try:
        if os.path.splitext(path)[1].lower() != ".rpt":
            return False
        with open(path, "rb") as fh:
            head = decode_rpt(fh.read(4096))
    except OSError:
        return False
    lines = [ln.strip() for ln in head.splitlines() if ln.strip()]
    return bool(lines) and lines[0].lstrip("﻿") == "[SAMPLE]"


def count_rpt_samples(path: str) -> int:
    """Number of [SAMPLE] blocks in an .rpt file (cheap line scan)."""
    count = 0
    with open(path, "rb") as fh:
        text = decode_rpt(fh.read())
    for line in text.splitlines():
        if line.strip() == "[SAMPLE]":
            count += 1
    return count


# ---------------------------------------------------------------------------
# Block -> LCMSReport
# ---------------------------------------------------------------------------

def _wavelength_of(function: _Node, chrom: _Node) -> Optional[float]:
    """Wavelength (nm) of a single-wavelength DAD trace, else None."""
    desc = chrom.get("Description")
    m = re.search(r"DAD[^\d]*(\d{3}(?:\.\d+)?)\s*(?:nm)?\s*$", desc, re.IGNORECASE)
    if m:
        return float(m.group(1))
    m = re.match(r"^\(\s*(\d+(?:\.\d+)?)\s*:\s*(\d+(?:\.\d+)?)\s*\)", function.get("Description"))
    if m and m.group(1) == m.group(2) and "TIC" not in desc.upper():
        return float(m.group(1))
    return None


def _classify_chrom(function: _Node, chrom: _Node) -> str:
    """'TAC', '220nm', '254nm', 'MS-TIC' or 'other'."""
    ftype = function.get("Type").strip().upper()
    desc = chrom.get("Description").upper()
    if ftype.startswith("DAD"):
        wl = _wavelength_of(function, chrom)
        if wl is not None:
            if abs(wl - 220.0) <= WAVELENGTH_TOL:
                return "220nm"
            if abs(wl - 254.0) <= WAVELENGTH_TOL:
                return "254nm"
            return "other"
        if "TIC" in desc or "TAC" in desc or "TOTAL" in desc:
            return "TAC"
        return "other"
    if "TIC" in desc and function.get("IonMode").strip():
        return "MS-TIC"
    return "other"


def _top_ions(rows: List[Tuple[float, float]]) -> Tuple[List[float], List[float]]:
    """Tallest ions (m/z, % of base peak) at or above the reporting threshold."""
    if not rows:
        return [], []
    top = max(y for _, y in rows)
    if top <= 0:
        return [], []
    ranked = sorted(rows, key=lambda r: (-r[1], r[0]))
    mz: List[float] = []
    rel: List[float] = []
    for x, y in ranked:
        pct = 100.0 * y / top
        if pct < MIN_ION_REL_PCT or len(mz) >= MAX_IONS_PER_MODE:
            break
        mz.append(round(x, 4))
        rel.append(round(pct, 1))
    return mz, rel


def _uv_maxima(rows: List[Tuple[float, float]]) -> List[float]:
    """Wavelengths of the local maxima of a DAD spectrum (ascending)."""
    ys = [abs(y) for _, y in rows]
    if len(ys) < 3:
        return []
    top = max(ys)
    if top <= 0:
        return []
    floor = top * UV_MIN_REL_PCT / 100.0
    found: List[Tuple[float, float]] = []
    for i in range(1, len(ys) - 1):
        if ys[i] > ys[i - 1] and ys[i] >= ys[i + 1] and ys[i] >= floor:
            # Ignore ripples: the maximum must stand out from the nearest
            # valley on both sides by at least 3 % of the spectrum maximum.
            left = min(ys[max(0, i - 8):i])
            right = min(ys[i + 1:i + 9])
            if ys[i] - max(left, right) >= 0.03 * top:
                found.append((rows[i][0], ys[i]))
    found.sort(key=lambda t: -t[1])
    return sorted(round(w, 2) for w, _ in found[:UV_MAX_MAXIMA])


def _peak_key(peak_id: str, rt: float, by_id: Dict[str, ChromPeak]) -> Optional[ChromPeak]:
    peak = by_id.get(peak_id)
    if peak is not None and abs(peak.rt - rt) <= max(RT_MATCH_TOL, 0.15):
        return peak
    return None


def _sample_to_report(node: _Node, filename: str, fallback_index: int) -> LCMSReport:
    functions = node.kids("FUNCTION")

    # --- chromatograms: classify, pick the area source per detector --------
    chroms: Dict[str, List[_Node]] = {}
    for fn in functions:
        for chrom in fn.kids("CHROMATOGRAM"):
            if not chrom.kids("PEAK"):
                continue
            chroms.setdefault(_classify_chrom(fn, chrom), []).append(chrom)

    detector = "TAC"
    primary = chroms.get("TAC", [])
    if not primary and chroms.get("MS-TIC"):
        primary, detector = chroms["MS-TIC"], "MS TIC"

    peaks: List[ChromPeak] = []
    by_id: Dict[str, ChromPeak] = {}

    def find_or_add(peak_node: _Node, rt_match: bool) -> ChromPeak:
        pid = peak_node.get("Peak ID") or str(len(peaks) + 1)
        rt = _to_float(peak_node.get("Time")) or 0.0
        existing = _peak_key(pid, rt, by_id)
        if existing is not None:
            return existing
        if rt_match and peaks:
            nearest = min(peaks, key=lambda p: abs(p.rt - rt))
            if abs(nearest.rt - rt) <= RT_MATCH_TOL:
                return nearest
        peak = ChromPeak(peak_num=pid, rt=rt)
        if pid in by_id:                      # duplicate ID at a different time
            n = 2
            while f"{pid}.{n}" in by_id:
                n += 1
            peak.peak_num = f"{pid}.{n}"
        peaks.append(peak)
        by_id[peak.peak_num] = peak
        return peak

    def fill(peak: ChromPeak, p: _Node, slot: str) -> None:
        area = _to_float(p.get("AreaAbs"))
        pct = _to_float(p.get("Area %Total"))
        if slot == "TAC":
            peak.area, peak.area_pct = area, pct
            peak.width = _to_float(p.get("Width"))
            peak.height = _to_float(p.get("Height"))
        elif slot == "220nm":
            peak.area_220nm, peak.area_pct_220nm = area, pct
        elif slot == "254nm":
            peak.area_254nm, peak.area_pct_254nm = area, pct

    for chrom in primary:
        for p in chrom.kids("PEAK"):
            fill(find_or_add(p, False), p, "TAC")
    for slot in ("220nm", "254nm"):
        for chrom in chroms.get(slot, []):
            for p in chrom.kids("PEAK"):
                fill(find_or_add(p, True), p, slot)

    # --- spectra -----------------------------------------------------------
    ms_by_peak: Dict[int, Dict[str, MassSpectrum]] = {}
    for fn in functions:
        ftype = fn.get("Type").strip().upper()
        mode = fn.get("IonMode").strip().upper().replace(" ", "")
        for spec in fn.kids("SPECTRUM"):
            ms_nodes = spec.kids("MS")
            if not ms_nodes:
                continue
            rows = ms_nodes[0].rows
            holder = ChromPeak(peak_num=spec.get("Peak ID") or "?", rt=_to_float(spec.get("Time")) or 0.0)
            peak = None
            key = _peak_key(holder.peak_num, holder.rt, by_id)
            if key is not None:
                peak = key
            else:
                for p in peaks:
                    if abs(p.rt - holder.rt) <= RT_MATCH_TOL:
                        peak = p
                        break
            if peak is None:                  # spectrum of a peak the tables lack
                peak = holder
                peaks.append(peak)
                by_id[peak.peak_num] = peak
            if ftype.startswith("DAD") or not mode:
                maxima = _uv_maxima(rows)
                if maxima and not peak.uv_lambda_max:
                    peak.uv_lambda_max = maxima
            elif mode in ("ES+", "ES-"):
                ions, rel = _top_ions(rows)
                if ions:
                    ms_by_peak.setdefault(id(peak), {})[mode] = MassSpectrum(
                        mode=mode, top_ions=ions, intensities=rel,
                    )
    for peak in peaks:
        modes = ms_by_peak.get(id(peak), {})
        peak.ms_spectra = [modes[m] for m in ("ES+", "ES-") if m in modes]
        if peak.ms_spectra:
            peak.mass_found = ", ".join(
                f"{s.top_ions[0]:.2f} ({s.mode})" for s in peak.ms_spectra
            )

    peaks.sort(key=lambda p: (p.rt, p.peak_num))

    method_path = node.get("Method") or node.get("MSMethod") or "Unknown"
    try:
        sample_index: Optional[int] = int(node.get("Sample"))
    except ValueError:
        sample_index = fallback_index
    return LCMSReport(
        filename=filename,
        sample_name=node.get("FileName") or "Unknown",
        date=node.get("Date") or "Unknown",
        instrument=node.get("Instrument") or "Unknown",
        method_path=method_path,
        method_short=parse_method_short(method_path),
        peaks=peaks,
        file_modified=None,
        run_time=node.get("Time") or None,
        source_format="openlynx_rpt",
        sample_id=node.get("SampleID"),
        well=node.get("Well"),
        sample_index=sample_index,
        detector=detector,
        column_name=node.get("ColumnName").strip(),
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_rpt_text(text: str, filename: str = "report.rpt") -> List[LCMSReport]:
    """Parse the text of an OpenLynx .rpt export into one report per sample."""
    reports: List[LCMSReport] = []
    for i, lines in enumerate(_split_samples(text), start=1):
        reports.append(_sample_to_report(_parse_block(lines), filename, i))
    return reports


def parse_rpt(path: str) -> List[LCMSReport]:
    """Parse an OpenLynx .rpt file; returns one LCMSReport per [SAMPLE]."""
    with open(path, "rb") as fh:
        text = decode_rpt(fh.read())
    reports = parse_rpt_text(text, os.path.basename(path))
    if not reports:
        raise ValueError(f"No [SAMPLE] blocks found in {path}")
    return reports


def select_sample(reports: List[LCMSReport], sample) -> LCMSReport:
    """Pick one sample of a multi-sample export.

    *sample* may be the 1-based sample number (int or digit string), a well
    label such as ``"A1"`` / ``"4:1"``, a SampleID or an acquired file name.
    With ``None`` the report must hold exactly one sample.
    """
    if sample is None:
        if len(reports) == 1:
            return reports[0]
        raise ValueError(
            f"{reports[0].filename} holds {len(reports)} samples; pass sample= "
            "(sample number, well, SampleID or file name) or use parse_rpt()"
        )
    token = str(sample).strip()
    for r in reports:
        if token.isdigit() and r.sample_index == int(token):
            return r
    for r in reports:
        if token.lower() in (r.well.lower(), r.sample_id.lower(), r.sample_name.lower()):
            return r
    raise ValueError(f"Sample {sample!r} not found in {reports[0].filename}")


def report_datetime(report: LCMSReport) -> Optional[str]:
    """Acquisition time of an .rpt sample as 'YYYY-MM-DD HH:MM:SS'."""
    if not report.run_time or report.date in ("", "Unknown"):
        return None
    try:
        dt = datetime.strptime(f"{report.date} {report.run_time}", "%d-%b-%Y %H:%M:%S")
    except ValueError:
        return None
    return dt.strftime("%Y-%m-%d %H:%M:%S")
