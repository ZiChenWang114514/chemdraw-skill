#!/usr/bin/env python3
"""
Shimadzu LabSolutions ``.daml`` report parser.

Shimadzu LabSolutions Open Access / LCMS exports can write self-contained
``.daml`` XML files holding acquisition metadata (``<datafile_attribs>``),
UV/PDA chromatogram peak integrations (``<results>/<lc_chros>/<chro>``),
centroided MS spectra (``<results>/<spectra>/<spec>``), and PDA UV spectra
(``<results>/<pda_spectra>/<pda_spec>``), with numeric arrays and peak tables
stored as Base64-encoded semicolon-delimited ASCII strings.

This module converts a ``.daml`` file into the standard ``LCMSReport`` /
``ChromPeak`` / ``MassSpectrum`` data structures produced by
``lcms_analyzer.parse_report``, so all downstream tools (``parse_analysis_file``,
``format_procedure_entry``, ``multi_lcms_analyzer``, ``discover_experiment_files``)
accept Shimadzu ``.daml`` files seamlessly.
"""

from __future__ import annotations

import base64
import binascii
import os
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from cdxml_toolkit.analysis.lcms_analyzer import (
    ChromPeak,
    LCMSReport,
    MassSpectrum,
    parse_method_short,
)

# Ions below this fraction of the base peak are not reported (matches OpenLynx
# .rpt convention in openlynx_rpt.py).
MIN_ION_REL_PCT = 20.0
MAX_IONS_PER_MODE = 5

# UV PDA maximum selection thresholds (matches openlynx_rpt.py, restricted to
# positive absorbance at >= 210 nm to ignore negative solvent/baseline dips).
UV_MIN_WAVELENGTH = 210.0
UV_MIN_REL_PCT = 10.0
UV_MAX_MAXIMA = 4

# Retention-time tolerances (minutes).
CHRO_MERGE_RT_TOL = 0.02
SPEC_MATCH_RT_TOL = 0.03

# Timestamp formats observed in Shimadzu LabSolutions exports.
_TIMESTAMP_FORMATS: Tuple[str, ...] = (
    "%m/%d/%Y %I:%M:%S %p",
    "%m/%d/%Y %H:%M:%S",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%dT%H:%M:%S",
    "%Y/%m/%d %H:%M:%S",
    "%Y/%m/%d %I:%M:%S %p",
    "%d/%m/%Y %H:%M:%S",
    "%d/%m/%Y %I:%M:%S %p",
    "%d-%b-%Y %H:%M:%S",
    "%d-%b-%y %H:%M:%S",
)

_DATE_ONLY_FORMATS: Tuple[str, ...] = (
    "%Y-%m-%d",
    "%m/%d/%Y",
    "%Y/%m/%d",
    "%d-%b-%Y",
)

# Matches optional XML prolog / comments / DOCTYPE followed by the root start tag.
_FIRST_TAG_RE = re.compile(
    r"^\s*(?:<\?.*?\?>\s*|<!--.*?-->\s*|<!DOCTYPE[^>]*>\s*)*<([A-Za-z_][\w:.-]*)(?=[\s>/])",
    re.DOTALL,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _decode_daml_bytes(data: bytes) -> str:
    """Decode raw .daml XML bytes (UTF-16 BOM, UTF-8-sig, else cp1252)."""
    if data[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return data.decode("utf-16", errors="replace")
    if data[:3] == b"\xef\xbb\xbf":
        return data[3:].decode("utf-8", errors="replace")
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode("cp1252", errors="replace")


def _local_tag(tag: str) -> str:
    """Strip an optional XML namespace URI or prefix from *tag*."""
    if "}" in tag:
        tag = tag.rsplit("}", 1)[-1]
    if ":" in tag:
        tag = tag.rsplit(":", 1)[-1]
    return tag


def _find_child(parent: Optional[ET.Element], name: str) -> Optional[ET.Element]:
    """Return the first direct child of *parent* whose local tag equals *name*."""
    if parent is None:
        return None
    for child in parent:
        if _local_tag(child.tag) == name:
            return child
    return None


def _iter_children(parent: Optional[ET.Element], name: str) -> List[ET.Element]:
    """Return all direct children of *parent* whose local tag equals *name*."""
    if parent is None:
        return []
    return [child for child in parent if _local_tag(child.tag) == name]


def _child_text(parent: Optional[ET.Element], name: str, default: str = "") -> str:
    """Return stripped text of the first direct *name* child, or *default*."""
    child = _find_child(parent, name)
    if child is None or child.text is None:
        return default
    return child.text.strip()


def _to_float(token: Optional[str]) -> Optional[float]:
    if token is None:
        return None
    s = token.strip()
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _decode_b64_ascii(b64_text: str) -> str:
    """Decode Base64 ASCII payload from a Shimadzu <data> element."""
    cleaned = "".join(b64_text.split())
    if not cleaned:
        return ""
    # Pad if Base64 length is slightly off a multiple of 4.
    rem = len(cleaned) % 4
    if rem:
        cleaned += "=" * (4 - rem)
    try:
        raw = base64.b64decode(cleaned)
    except (binascii.Error, ValueError):
        return ""
    return raw.decode("ascii", errors="replace")


def _parse_timestamp(raw: str) -> Tuple[Optional[str], Optional[str]]:
    """Parse a Shimadzu timestamp into ('YYYY-MM-DD', 'HH:MM:SS') or fallback."""
    s = raw.strip()
    if not s:
        return None, None
    # Strip trailing Z or fractional seconds on ISO timestamps if present.
    iso_clean = re.sub(r"(\d{2}:\d{2}:\d{2})\.\d+(?:Z|[+-]\d{2}:?\d{2})?$", r"\1", s)
    iso_clean = re.sub(r"Z$", "", iso_clean).strip()
    for candidate in (s, iso_clean):
        for fmt in _TIMESTAMP_FORMATS:
            try:
                dt = datetime.strptime(candidate, fmt)
                return dt.strftime("%Y-%m-%d"), dt.strftime("%H:%M:%S")
            except ValueError:
                continue
    for fmt in _DATE_ONLY_FORMATS:
        try:
            dt = datetime.strptime(s, fmt)
            return dt.strftime("%Y-%m-%d"), None
        except ValueError:
            continue
    return None, None


def _top_ions(rows: List[Tuple[float, float]]) -> Tuple[List[float], List[float]]:
    """Tallest ions (m/z, % of base peak) at or above MIN_ION_REL_PCT."""
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


def _uv_maxima_pda(rows: List[Tuple[float, float]]) -> Tuple[List[float], float]:
    """Prominent positive UV maxima (>= 210 nm) and peak positive absorbance."""
    pts = [(wl, max(0.0, y)) for wl, y in rows if wl >= UV_MIN_WAVELENGTH]
    if len(pts) < 3:
        return [], 0.0
    ys = [y for _, y in pts]
    top = max(ys)
    if top <= 0:
        return [], 0.0
    floor = top * UV_MIN_REL_PCT / 100.0
    found: List[Tuple[float, float]] = []
    for i in range(1, len(ys) - 1):
        if ys[i] > ys[i - 1] and ys[i] >= ys[i + 1] and ys[i] >= floor:
            left = min(ys[max(0, i - 8):i])
            right = min(ys[i + 1:i + 9])
            if ys[i] - max(left, right) >= 0.03 * top:
                found.append((pts[i][0], ys[i]))
    found.sort(key=lambda t: -t[1])
    return sorted(round(w, 2) for w, _ in found[:UV_MAX_MAXIMA]), top


def _parse_kv_tokens(decoded: str) -> Dict[str, str]:
    """Parse semicolon-delimited 'key=value' tokens from <peak>/<data>."""
    kv: Dict[str, str] = {}
    for tok in decoded.split(";"):
        if "=" not in tok:
            continue
        k, _, v = tok.partition("=")
        k = k.strip()
        if k:
            kv[k] = v.strip()
    return kv


def _parse_xy_pairs(decoded: str, x_scale: float) -> List[Tuple[float, float]]:
    """Parse Base64-decoded Shimadzu spectrum payload after 4 header tokens."""
    if not decoded:
        return []
    tokens = decoded.split(";")
    if len(tokens) < 6:
        return []
    pair_tokens = tokens[4:]
    rows: List[Tuple[float, float]] = []
    for i in range(0, len(pair_tokens) - 1, 2):
        x_raw = _to_float(pair_tokens[i])
        y_raw = _to_float(pair_tokens[i + 1])
        if x_raw is not None and y_raw is not None:
            rows.append((x_raw / x_scale, y_raw))
    return rows


def _classify_wavelength(wl: Optional[float]) -> str:
    """Classify a <chro>/<wavelength> value into 'TAC', '254nm', '220nm', or 'other'."""
    if wl is None or wl == 0.0:
        return "TAC"
    if 250.0 <= wl <= 258.0:
        return "254nm"
    if 214.0 <= wl <= 225.0:
        return "220nm"
    return "other"


def _format_single_detector(wl: Optional[float]) -> str:
    """Detector label for a single-channel <chro>."""
    if wl is None or wl == 0.0:
        return "PDA"
    if wl == int(wl):
        return f"UV {int(wl)}nm"
    return f"UV {wl:g}nm"


@dataclass
class _ChroPeakRow:
    internal_id: str
    peak_num: str
    rt: float
    area: Optional[float]
    area_pct: Optional[float]
    height: Optional[float]
    width: Optional[float]


def _parse_chro_peaks(chro_elem: ET.Element) -> List[_ChroPeakRow]:
    """Decode all <peak> children inside one <chro> element."""
    parsed: List[_ChroPeakRow] = []
    for idx, peak_elem in enumerate(_iter_children(chro_elem, "peak"), start=1):
        decoded = _decode_b64_ascii(_child_text(peak_elem, "data"))
        if not decoded:
            continue
        kv = _parse_kv_tokens(decoded)
        ap_rt_ms = _to_float(kv.get("ApRT"))
        if ap_rt_ms is None:
            continue
        rt = round(ap_rt_ms / 60000.0, 4)
        area_raw = _to_float(kv.get("A"))
        area_pct_raw = _to_float(kv.get("APc"))
        height_raw = _to_float(kv.get("Hgt"))
        st_rt_ms = _to_float(kv.get("StRT"))
        ed_rt_ms = _to_float(kv.get("EdRT"))
        width: Optional[float] = None
        if st_rt_ms is not None and ed_rt_ms is not None and ed_rt_ms > st_rt_ms:
            width = round((ed_rt_ms - st_rt_ms) / 60000.0, 4)
        parsed.append(
            _ChroPeakRow(
                internal_id=kv.get("ID", "").strip(),
                peak_num=kv.get("PN", "").strip() or str(idx),
                rt=rt,
                area=round(area_raw, 4) if area_raw is not None else None,
                area_pct=round(area_pct_raw, 4) if area_pct_raw is not None else None,
                height=round(height_raw, 4) if height_raw is not None else None,
                width=width,
            )
        )
    return parsed


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def is_shimadzu_daml(path: str) -> bool:
    """True when *path* is a regular ``.daml`` file starting with a ``<DAML`` tag."""
    try:
        if os.path.splitext(str(path))[1].lower() != ".daml":
            return False
        if not os.path.isfile(path):
            return False
        with open(path, "rb") as fh:
            head = _decode_daml_bytes(fh.read(8192)).lstrip("\ufeff")
    except OSError:
        return False
    m = _FIRST_TAG_RE.match(head)
    if m is not None:
        return _local_tag(m.group(1)) == "DAML"
    # Fallback if a long header comment spans past 8 KB before closing, only
    # when <DAML appears directly as an opening element tag.
    return bool(re.search(r"<DAML(?:\s|>|/)", head))


def parse_daml(path: str) -> LCMSReport:
    """Parse a Shimadzu LabSolutions ``.daml`` file into an ``LCMSReport``."""
    with open(path, "rb") as fh:
        text = _decode_daml_bytes(fh.read())
    return parse_daml_text(text, filename=os.path.basename(path))


def parse_daml_text(text: str, filename: str = "<memory>") -> LCMSReport:
    """Parse the XML text of a Shimadzu ``.daml`` report into an ``LCMSReport``."""
    cleaned = text.lstrip("\ufeff").strip()
    if not cleaned:
        raise ValueError(f"Empty DAML input in {filename}")
    try:
        root = ET.fromstring(cleaned)
    except ET.ParseError as exc:
        raise ValueError(f"Invalid XML in {filename}: {exc}") from exc

    root_tag = _local_tag(root.tag)
    if root_tag != "DAML":
        raise ValueError(
            f"Expected <DAML> root element in {filename}, got <{root_tag}>"
        )

    # --- Header metadata (<datafile_attribs>) ------------------------------
    attribs = _find_child(root, "datafile_attribs")
    sample_id = _child_text(attribs, "sample_id")
    raw_sample_name = _child_text(attribs, "sample_name")
    stem_fallback = ""
    if filename and filename != "<memory>":
        stem_fallback = os.path.splitext(os.path.basename(filename))[0]
    sample_name = raw_sample_name or sample_id or stem_fallback or "Unknown"

    well = _child_text(attribs, "vial")
    instrument = _child_text(attribs, "instrument") or "Shimadzu LC/MS"
    method_path = _child_text(attribs, "method_file_name") or "Unknown"
    method_short = parse_method_short(method_path)

    samp_num_str = _child_text(attribs, "samp_num")
    sample_index: Optional[int] = int(samp_num_str) if samp_num_str.isdigit() else None

    date_str = "Unknown"
    run_time: Optional[str] = None
    for raw_ts in (
        _child_text(attribs, "raw_datafile_last_write"),
        _child_text(attribs, "creation_date"),
        (root.attrib.get("timestamp") or "").strip(),
    ):
        if not raw_ts:
            continue
        parsed_date, parsed_time = _parse_timestamp(raw_ts)
        if parsed_date is not None:
            date_str = parsed_date
            run_time = parsed_time
            break
        if date_str == "Unknown":
            date_str = raw_ts

    # --- Chromatogram peaks (<results>/<lc_chros>/<chro>) ------------------
    results_elem = _find_child(root, "results")
    lc_chros_elem = _find_child(results_elem, "lc_chros")
    chro_elems = _iter_children(lc_chros_elem, "chro")

    channels: List[Tuple[Optional[float], str, List[_ChroPeakRow]]] = []
    for chro in chro_elems:
        wl = _to_float(_child_text(chro, "wavelength"))
        slot = _classify_wavelength(wl)
        channels.append((wl, slot, _parse_chro_peaks(chro)))

    if not channels:
        detector = "PDA"
    elif len(channels) == 1:
        detector = _format_single_detector(channels[0][0])
    else:
        detector = "PDA"

    # Reorder so a TAC channel (if any) seeds primary areas first, otherwise
    # preserve XML channel order so the first <chro> is primary.
    tac_idx = next((i for i, (_, slot, _) in enumerate(channels) if slot == "TAC"), None)
    ordered_indices = list(range(len(channels)))
    if tac_idx is not None and tac_idx != 0:
        ordered_indices.remove(tac_idx)
        ordered_indices.insert(0, tac_idx)

    peaks: List[ChromPeak] = []
    by_internal_id: Dict[str, ChromPeak] = {}
    used_peak_nums: set = set()

    def _assign_unique_peak_num(desired: str) -> str:
        if desired not in used_peak_nums:
            used_peak_nums.add(desired)
            return desired
        n = 2
        while f"{desired}.{n}" in used_peak_nums:
            n += 1
        unique = f"{desired}.{n}"
        used_peak_nums.add(unique)
        return unique

    for order_pos, ch_idx in enumerate(ordered_indices):
        wl, slot, ch_peaks = channels[ch_idx]
        is_primary_channel = order_pos == 0
        for row in ch_peaks:
            target: Optional[ChromPeak] = None
            if not is_primary_channel and peaks:
                nearest = min(peaks, key=lambda p: abs(p.rt - row.rt))
                if abs(nearest.rt - row.rt) <= CHRO_MERGE_RT_TOL:
                    target = nearest
            if target is None:
                target = ChromPeak(
                    peak_num=_assign_unique_peak_num(row.peak_num),
                    rt=row.rt,
                )
                peaks.append(target)

            if row.internal_id:
                by_internal_id[row.internal_id] = target

            if is_primary_channel or (tac_idx is None and target.area is None):
                target.area = row.area
                target.area_pct = row.area_pct
                if target.height is None:
                    target.height = row.height
                if target.width is None:
                    target.width = row.width

            if slot == "254nm":
                target.area_254nm = row.area
                target.area_pct_254nm = row.area_pct
            elif slot == "220nm":
                target.area_220nm = row.area
                target.area_pct_220nm = row.area_pct

    peaks.sort(key=lambda p: (p.rt, p.peak_num))

    # --- Mass spectra (<results>/<spectra>/<spec>) -------------------------
    # Keep best spectrum per (peak, mode) ranked by:
    #   (direct_peak_id_match, base_peak_intensity, -rt_distance)
    spectra_elem = _find_child(results_elem, "spectra")
    best_ms: Dict[Tuple[int, str], Tuple[Tuple[int, float, float], MassSpectrum]] = {}

    for spec in _iter_children(spectra_elem, "spec"):
        ms_stage = _child_text(spec, "ms_stage")
        if ms_stage not in ("", "1"):
            continue
        pol = _child_text(spec, "polarity")
        if pol in ("0", "+"):
            mode = "ES+"
        elif pol in ("1", "-"):
            mode = "ES-"
        else:
            continue

        spec_rt_ms = _to_float(_child_text(spec, "rt"))
        spec_rt = (spec_rt_ms / 60000.0) if spec_rt_ms is not None else None

        peak_id = _child_text(spec, "peak_id")
        matched_peak = by_internal_id.get(peak_id) if (peak_id and peak_id != "0") else None
        direct = matched_peak is not None

        if matched_peak is None and spec_rt is not None and peaks:
            nearest = min(peaks, key=lambda p: abs(p.rt - spec_rt))
            if abs(nearest.rt - spec_rt) <= SPEC_MATCH_RT_TOL:
                matched_peak = nearest

        if matched_peak is None:
            continue

        decoded = _decode_b64_ascii(_child_text(spec, "data"))
        xy_rows = [
            (mz, inten)
            for mz, inten in _parse_xy_pairs(decoded, 10000.0)
            if inten > 0
        ]
        if not xy_rows:
            continue

        bpi = max(inten for _, inten in xy_rows)
        ions, rel = _top_ions(xy_rows)
        if not ions:
            continue

        rt_dist = abs(matched_peak.rt - spec_rt) if spec_rt is not None else 0.0
        score = (1 if direct else 0, bpi, -rt_dist)
        key = (id(matched_peak), mode)
        prev = best_ms.get(key)
        if prev is None or score > prev[0]:
            best_ms[key] = (
                score,
                MassSpectrum(mode=mode, top_ions=ions, intensities=rel),
            )

    for peak in peaks:
        peak.ms_spectra = [
            best_ms[(id(peak), m)][1]
            for m in ("ES+", "ES-")
            if (id(peak), m) in best_ms
        ]
        if peak.ms_spectra:
            peak.mass_found = ", ".join(
                f"{s.top_ions[0]:.2f} ({s.mode})" for s in peak.ms_spectra
            )

    # --- PDA UV spectra (<results>/<pda_spectra>/<pda_spec>) ---------------
    pda_elem = _find_child(results_elem, "pda_spectra")
    best_uv: Dict[int, Tuple[Tuple[int, float, float], List[float]]] = {}

    for pda_spec in _iter_children(pda_elem, "pda_spec"):
        spec_rt_ms = _to_float(_child_text(pda_spec, "rt"))
        spec_rt = (spec_rt_ms / 60000.0) if spec_rt_ms is not None else None

        peak_id = _child_text(pda_spec, "peak_id")
        matched_peak = by_internal_id.get(peak_id) if (peak_id and peak_id != "0") else None
        direct = matched_peak is not None

        if matched_peak is None and spec_rt is not None and peaks:
            nearest = min(peaks, key=lambda p: abs(p.rt - spec_rt))
            if abs(nearest.rt - spec_rt) <= SPEC_MATCH_RT_TOL:
                matched_peak = nearest

        if matched_peak is None:
            continue

        decoded = _decode_b64_ascii(_child_text(pda_spec, "data"))
        uv_rows = _parse_xy_pairs(decoded, 100.0)
        maxima, pos_top = _uv_maxima_pda(uv_rows)
        if not maxima:
            continue

        rt_dist = abs(matched_peak.rt - spec_rt) if spec_rt is not None else 0.0
        score = (1 if direct else 0, pos_top, -rt_dist)
        prev_uv = best_uv.get(id(matched_peak))
        if prev_uv is None or score > prev_uv[0]:
            best_uv[id(matched_peak)] = (score, maxima)

    for peak in peaks:
        if id(peak) in best_uv:
            peak.uv_lambda_max = best_uv[id(peak)][1]

    return LCMSReport(
        filename=filename,
        sample_name=sample_name,
        date=date_str,
        instrument=instrument,
        method_path=method_path,
        method_short=method_short,
        peaks=peaks,
        file_modified=None,
        run_time=run_time,
        source_format="shimadzu_daml",
        sample_id=sample_id,
        well=well,
        sample_index=sample_index,
        detector=detector,
    )


def report_datetime(report: LCMSReport) -> Optional[str]:
    """Acquisition timestamp of a Shimadzu .daml report as 'YYYY-MM-DD HH:MM:SS'."""
    if not report.run_time or not report.date or report.date == "Unknown":
        return None
    combined = f"{report.date} {report.run_time}".strip()
    parsed_date, parsed_time = _parse_timestamp(combined)
    if parsed_date and parsed_time:
        return f"{parsed_date} {parsed_time}"
    return None
