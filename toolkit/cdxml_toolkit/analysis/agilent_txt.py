#!/usr/bin/env python3
"""
Agilent ChemStation / OpenLab ``report.txt`` parser.

Agilent ChemStation writes human-readable ASCII / UTF-16 ``report.txt`` files
inside ``.D`` acquisition directories (or exported standalone) containing run
metadata (``Data File``, ``Sample Name``, ``Acq. Instrument``, ``Location``,
``Injection Date``, ``Method``) followed by an integration report banner
(``Area Percent Report``, ``External Standard Report``, ``Internal Standard
Report``, or ``Norm Percent Report``) and either:

  1. A single combined peak table with a ``Sig`` column
     (``Peak # | RetTime [min] | Sig | Type | Area | Height | Area %``), or
  2. One or more ``Signal N: ...`` detector blocks
     (``Peak # | RetTime [min] | Type | Width [min] | Area | Height | Area %``),
     including ``No peaks found`` blocks when 0 peaks are integrated.

This module parses both layouts into ``LCMSReport`` / ``ChromPeak`` objects
(``source_format="agilent_chemstation_txt"``) so all downstream LCMS tools
accept Agilent ChemStation ``report.txt`` reports directly.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from cdxml_toolkit.analysis.lcms_analyzer import (
    ChromPeak,
    LCMSReport,
    parse_method_short,
)

# Retention-time tolerance (minutes) when merging peaks across DAD/VWD signals.
SIGNAL_MERGE_RT_TOL = 0.02

_REPORT_BANNERS: Tuple[str, ...] = (
    "Area Percent Report",
    "External Standard Report",
    "Internal Standard Report",
    "Norm Percent Report",
)

_TIMESTAMP_FORMATS: Tuple[str, ...] = (
    "%m/%d/%Y %I:%M:%S %p",
    "%m/%d/%y %I:%M:%S %p",
    "%m/%d/%Y %H:%M:%S",
    "%m/%d/%y %H:%M:%S",
    "%d-%b-%y %H:%M:%S",
    "%d-%b-%Y %H:%M:%S",
    "%d-%b-%y %I:%M:%S %p",
    "%d-%b-%Y %I:%M:%S %p",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%dT%H:%M:%S",
    "%Y/%m/%d %H:%M:%S",
    "%Y/%m/%d %I:%M:%S %p",
    "%d.%m.%Y %H:%M:%S",
    "%d/%m/%Y %H:%M:%S",
    "%d/%m/%Y %I:%M:%S %p",
)

_DATE_ONLY_FORMATS: Tuple[str, ...] = (
    "%Y-%m-%d",
    "%m/%d/%Y",
    "%d-%b-%Y",
    "%d-%b-%y",
)

# Matches line-3 summary header such as:
#   "1290UHPLC 1/26/2024 7:42:22 PM SYSTEM"
#   "LCMSD 5/24/2021 4:05:19 PM SYSTEM"
_LINE3_INST_TS_RE = re.compile(
    r"^\s*([A-Za-z0-9_.-]+(?:\s+\d+)?)\s+"
    r"(\d{1,4}[-/.][A-Za-z0-9]{1,3}[-/.]\d{2,4},?\s+"
    r"\d{1,2}:\d{2}:\d{2}(?:\s*[APap][Mm])?)\b"
)

_SIGNAL_HEADER_RE = re.compile(r"^\s*Signal\s+(\d+)\s*:\s*(.+?)\s*$", re.IGNORECASE)
_TABLE_SEP_RE = re.compile(r"^\s*-{2,}(?:\|-+){3,}\|?\s*$")


# ---------------------------------------------------------------------------
# Decoding & detection
# ---------------------------------------------------------------------------

def decode_agilent_txt(data: bytes) -> str:
    """Decode raw bytes of an Agilent ``report.txt`` and normalize newlines."""
    if data[:2] in (b"\xff\xfe", b"\xfe\xff"):
        text = data.decode("utf-16", errors="replace")
    else:
        try:
            text = data.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = data.decode("cp1252", errors="replace")
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _has_agilent_markers(text: str) -> bool:
    """True when *text* contains an Agilent report banner and header/table markers."""
    if not any(banner in text for banner in _REPORT_BANNERS):
        return False
    return (
        "Data File" in text
        or "Acq. Operator" in text
        or ("Signal " in text and "RetTime" in text and "[min]" in text)
    )


def is_agilent_report_txt(path: str) -> bool:
    """True when *path* is a regular ``.txt`` file with Agilent report markers."""
    try:
        if os.path.splitext(str(path))[1].lower() != ".txt":
            return False
        if not os.path.isfile(path):
            return False
        with open(path, "rb") as fh:
            head = decode_agilent_txt(fh.read(16384))
    except OSError:
        return False
    return _has_agilent_markers(head)


# ---------------------------------------------------------------------------
# Header & timestamp helpers
# ---------------------------------------------------------------------------

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


def _parse_timestamp(raw: str) -> Tuple[Optional[str], Optional[str]]:
    """Parse an Agilent timestamp string into ('YYYY-MM-DD', 'HH:MM:SS')."""
    s = re.sub(r"\s+", " ", raw.replace(",", " ")).strip()
    if not s:
        return None, None
    for fmt in _TIMESTAMP_FORMATS:
        try:
            dt = datetime.strptime(s, fmt)
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


def _extract_d_stem(data_file: str) -> str:
    """Extract sample stem from an Agilent Data File path (preferring .D folder stem)."""
    if not data_file:
        return ""
    parts = [p.strip() for p in data_file.replace("\\", "/").split("/") if p.strip()]
    for part in reversed(parts):
        if part.lower().endswith(".d") and len(part) > 2:
            return part[:-2]
    if parts:
        return os.path.splitext(parts[-1])[0]
    return ""


def _clean_method_value(raw_method: str) -> str:
    """Strip ChemStation '(Sequence Method)' / '(Modified ...)' suffixes."""
    cleaned = re.sub(r"\s*\(.*$", "", raw_method).strip()
    return cleaned


def _parse_header_block(lines: List[str]) -> Dict[str, str]:
    """Extract metadata fields from lines preceding the report banner."""
    info: Dict[str, str] = {}
    banner_idx = len(lines)
    for idx, ln in enumerate(lines):
        if any(b in ln for b in _REPORT_BANNERS):
            banner_idx = idx
            break

    header_lines = lines[:banner_idx]
    i = 0
    while i < len(header_lines):
        line = header_lines[i]
        stripped = line.strip()
        if not stripped:
            i += 1
            continue

        # Line 1: Data File [:] <path>
        m_df = re.match(r"^\s*Data File\s*:?\s*(.+?)\s*$", line, re.IGNORECASE)
        if m_df and "data_file" not in info:
            info["data_file"] = m_df.group(1).strip()
            i += 1
            continue

        # Line 2: Sample Name [:] <name>
        m_sn = re.match(
            r"^\s*Sample Name\s*:\s*(.*?)(?:\s{2,}[A-Za-z][A-Za-z.\s]*:.*)?\s*$",
            line,
            re.IGNORECASE,
        )
        if m_sn and "sample_name" not in info:
            val = m_sn.group(1).strip()
            if val:
                info["sample_name"] = val
            i += 1
            continue

        # Right-column Location : <well> (may share line with Acq. Instrument)
        m_loc = re.search(
            r"(?:^|\s{2,})Location\s*:\s*(.+?)(?:\s{2,}[A-Za-z][A-Za-z.\s]*:.*)?\s*$",
            line,
            re.IGNORECASE,
        )
        if m_loc and "well" not in info:
            loc_val = m_loc.group(1).strip()
            if loc_val and loc_val not in ("-", "N/A"):
                info["well"] = loc_val

        # Left-column Acq. Instrument : <inst>
        m_inst = re.match(
            r"^\s*(?:Acq\.\s*)?Instrument\s*:\s*(.+?)(?:\s{2,}[A-Za-z][A-Za-z.\s]*:.*)?\s*$",
            line,
            re.IGNORECASE,
        )
        if m_inst:
            inst_val = m_inst.group(1).strip()
            if inst_val:
                info["instrument"] = inst_val

        # Injection Date : <timestamp>
        m_inj = re.match(
            r"^\s*Injection Date\s*:\s*(.+?)(?:\s{2,}[A-Za-z][A-Za-z.\s]*:.*)?\s*$",
            line,
            re.IGNORECASE,
        )
        if m_inj and "injection_date" not in info:
            inj_val = m_inj.group(1).strip()
            if inj_val:
                info["injection_date"] = inj_val

        # Acq. Method / Method / Analysis Method : <path>
        m_meth = re.match(
            r"^\s*(Acq\.\s*Method|Method|Analysis\s*Method)\s*:\s*(.+?)\s*$",
            line,
            re.IGNORECASE,
        )
        if m_meth:
            kind = m_meth.group(1).lower()
            raw_val = m_meth.group(2).strip()
            # Join wrapped path continuation if .M/.lcm/.olp has not appeared yet
            if (
                not re.search(r"\.(?:m|lcm|olp)\b", raw_val, re.IGNORECASE)
                and "(" not in raw_val
                and i + 1 < len(header_lines)
            ):
                nxt = header_lines[i + 1]
                if re.match(r"^\s{8,}\S+", nxt) and ":" not in nxt:
                    raw_val = raw_val + nxt.strip()
                    i += 1
            cleaned_meth = _clean_method_value(raw_val)
            if cleaned_meth:
                # Prefer Acq. Method or Method over Analysis Method
                if "analysis" not in kind or "method" not in info:
                    info["method"] = cleaned_meth

        # Line-3 style summary ("1290UHPLC 1/26/2024 7:42:22 PM SYSTEM")
        if not stripped.startswith("=") and not re.match(
            r"^\s*[A-Za-z][A-Za-z.\s]*\s*:", line
        ):
            m_l3 = _LINE3_INST_TS_RE.match(line)
            if m_l3:
                info.setdefault("line3_instrument", m_l3.group(1).strip())
                info.setdefault("line3_timestamp", m_l3.group(2).strip())

        i += 1

    return info


# ---------------------------------------------------------------------------
# Signal & peak-table parsing
# ---------------------------------------------------------------------------

@dataclass
class _AgilentPeakRow:
    peak_num: str
    rt: float
    sig: Optional[str]
    peak_type: str
    width: Optional[float]
    area: Optional[float]
    height: Optional[float]
    area_pct: Optional[float]


@dataclass
class _SignalBlock:
    sig_id: str
    description: str
    wavelength: Optional[float]
    slot: str  # "TAC", "254nm", "220nm", "other"
    peaks: List[_AgilentPeakRow]


def _extract_signal_wavelength(desc: str) -> Tuple[Optional[float], str]:
    """Extract (wavelength_nm, slot) from an Agilent Signal header description."""
    upper = desc.upper()
    if "TWC" in upper or "TAC" in upper or "TOTAL WAVELENGTH" in upper:
        return None, "TAC"

    wl: Optional[float] = None
    for pat in (
        r"\bSig\s*=\s*(\d+(?:\.\d+)?)",
        r"\bWavelength\s*=\s*(\d+(?:\.\d+)?)",
        r"\b(\d{3}(?:\.\d+)?)\s*nm\b",
    ):
        m = re.search(pat, desc, re.IGNORECASE)
        if m:
            wl = _to_float(m.group(1))
            if wl is not None:
                break

    if wl is not None:
        if 250.0 <= wl <= 258.0:
            return wl, "254nm"
        if 214.0 <= wl <= 225.0:
            return wl, "220nm"
    return wl, "other"


def _parse_peak_row(
    line: str, has_sig: bool, has_width: bool
) -> Optional[_AgilentPeakRow]:
    """Parse one numeric peak row from an Agilent integration table."""
    tokens = line.split()
    head_count = 3 if has_sig else 2
    tail_count = 4 if has_width else 3
    if len(tokens) < head_count + tail_count:
        return None

    if not tokens[0].isdigit():
        return None
    rt = _to_float(tokens[1])
    if rt is None:
        return None

    sig_val = tokens[2] if has_sig else None

    tail_floats = [_to_float(tok) for tok in tokens[-tail_count:]]
    if any(v is None for v in tail_floats):
        return None

    if has_width:
        width, area, height, area_pct = tail_floats  # type: ignore[misc]
    else:
        width = None
        area, height, area_pct = tail_floats  # type: ignore[misc]

    type_tokens = tokens[head_count:-tail_count]
    peak_type = " ".join(type_tokens)

    return _AgilentPeakRow(
        peak_num=tokens[0],
        rt=round(rt, 4),
        sig=sig_val,
        peak_type=peak_type,
        width=round(width, 4) if width is not None else None,
        area=round(area, 4) if area is not None else None,
        height=round(height, 4) if height is not None else None,
        area_pct=round(area_pct, 4) if area_pct is not None else None,
    )


def _parse_table_after_sep(
    lines: List[str], sep_idx: int
) -> Tuple[List[_AgilentPeakRow], int]:
    """Parse peak rows starting after dashed separator at *sep_idx*."""
    hdr_window = " ".join(lines[max(0, sep_idx - 3):sep_idx])
    has_sig = bool(re.search(r"\bSig\b", hdr_window))
    has_width = bool(re.search(r"\bWidth\b", hdr_window))

    rows: List[_AgilentPeakRow] = []
    i = sep_idx + 1
    while i < len(lines):
        stripped = lines[i].strip()
        if not stripped:
            i += 1
            continue
        if (
            stripped.startswith(("Totals", "***", "===", "Signal "))
            or "End of Report" in stripped
            or "No peaks found" in stripped
        ):
            break
        row = _parse_peak_row(stripped, has_sig=has_sig, has_width=has_width)
        if row is not None:
            rows.append(row)
        i += 1
    return rows, i


def _parse_signal_blocks(lines: List[str]) -> Tuple[List[_SignalBlock], str]:
    """Extract all Signal blocks (or single combined table) and detector name."""
    blocks: List[_SignalBlock] = []
    current_sig_id: Optional[str] = None
    current_desc = ""
    current_rows: List[_AgilentPeakRow] = []
    combined_rows: List[_AgilentPeakRow] = []

    def _flush_signal() -> None:
        if current_sig_id is None:
            return
        wl, slot = _extract_signal_wavelength(current_desc)
        blocks.append(
            _SignalBlock(
                sig_id=current_sig_id,
                description=current_desc,
                wavelength=wl,
                slot=slot,
                peaks=list(current_rows),
            )
        )

    i = 0
    while i < len(lines):
        line = lines[i]
        m_sig = _SIGNAL_HEADER_RE.match(line)
        if m_sig:
            _flush_signal()
            current_sig_id = m_sig.group(1)
            current_desc = m_sig.group(2).strip()
            current_rows = []
            i += 1
            continue

        if _TABLE_SEP_RE.match(line):
            parsed_rows, next_i = _parse_table_after_sep(lines, i)
            if current_sig_id is not None:
                current_rows.extend(parsed_rows)
            else:
                combined_rows.extend(parsed_rows)
            i = next_i
            continue

        i += 1

    _flush_signal()

    if blocks:
        non_tac = [b for b in blocks if b.slot != "TAC"]
        if any(b.slot == "TAC" for b in blocks):
            detector = "TAC"
        elif len(blocks) == 1:
            b0 = blocks[0]
            fam = "DAD" if "DAD" in b0.description.upper() else "UV"
            if b0.wavelength is not None:
                wl_str = (
                    str(int(b0.wavelength))
                    if b0.wavelength == int(b0.wavelength)
                    else f"{b0.wavelength:g}"
                )
                detector = f"{fam} {wl_str}nm"
            else:
                detector = fam
        else:
            detector = (
                "DAD"
                if any("DAD" in b.description.upper() for b in non_tac)
                else "UV"
            )
        return blocks, detector

    # Layout 1: single combined table without "Signal N:" headers
    if combined_rows:
        by_sig: Dict[str, List[_AgilentPeakRow]] = {}
        sig_order: List[str] = []
        for r in combined_rows:
            sk = r.sig or "1"
            if sk not in by_sig:
                by_sig[sk] = []
                sig_order.append(sk)
            by_sig[sk].append(r)
        for sk in sig_order:
            blocks.append(
                _SignalBlock(
                    sig_id=sk,
                    description=f"Signal {sk}",
                    wavelength=None,
                    slot="other",
                    peaks=by_sig[sk],
                )
            )
    return blocks, "DAD"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_agilent_txt(path: str) -> LCMSReport:
    """Parse an Agilent ChemStation ``report.txt`` file into an ``LCMSReport``."""
    with open(path, "rb") as fh:
        text = decode_agilent_txt(fh.read())
    report = parse_agilent_txt_text(text, filename=os.path.basename(path))
    if report.sample_name in ("Unknown", "report"):
        parent = os.path.basename(os.path.dirname(os.path.abspath(path)))
        if parent.lower().endswith(".d") and len(parent) > 2:
            report.sample_name = parent[:-2]
    return report


def parse_agilent_txt_text(
    text: str, filename: str = "<memory>"
) -> LCMSReport:
    """Parse decoded text of an Agilent ChemStation ``report.txt``."""
    normalized = text.lstrip("\ufeff").replace("\r\n", "\n").replace("\r", "\n")
    if not _has_agilent_markers(normalized):
        raise ValueError(
            f"Not an Agilent ChemStation report.txt in {filename}"
        )

    lines = normalized.split("\n")
    hdr = _parse_header_block(lines)

    data_file = hdr.get("data_file", "")
    d_stem = _extract_d_stem(data_file)
    file_stem = ""
    if filename and filename != "<memory>":
        stem = os.path.splitext(os.path.basename(filename))[0]
        if stem.lower() != "report":
            file_stem = stem

    sample_name = hdr.get("sample_name") or d_stem or file_stem or "Unknown"
    instrument = (
        hdr.get("instrument")
        or hdr.get("line3_instrument")
        or "Agilent LC/MS"
    )
    well = hdr.get("well", "")
    method_path = hdr.get("method") or "Unknown"
    method_short = parse_method_short(method_path)

    date_str = "Unknown"
    run_time: Optional[str] = None
    for raw_ts in (hdr.get("injection_date", ""), hdr.get("line3_timestamp", "")):
        if not raw_ts:
            continue
        parsed_date, parsed_time = _parse_timestamp(raw_ts)
        if parsed_date is not None:
            date_str = parsed_date
            run_time = parsed_time
            break
        if date_str == "Unknown":
            date_str = raw_ts

    blocks, detector = _parse_signal_blocks(lines)

    tac_idx = next((i for i, b in enumerate(blocks) if b.slot == "TAC"), None)
    ordered_indices = list(range(len(blocks)))
    if tac_idx is not None and tac_idx != 0:
        ordered_indices.remove(tac_idx)
        ordered_indices.insert(0, tac_idx)

    peaks: List[ChromPeak] = []
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

    for order_pos, blk_idx in enumerate(ordered_indices):
        blk = blocks[blk_idx]
        is_primary = order_pos == 0
        for row in blk.peaks:
            target: Optional[ChromPeak] = None
            if not is_primary and peaks:
                nearest = min(peaks, key=lambda p: abs(p.rt - row.rt))
                if abs(nearest.rt - row.rt) <= SIGNAL_MERGE_RT_TOL:
                    target = nearest
            if target is None:
                target = ChromPeak(
                    peak_num=_assign_unique_peak_num(row.peak_num),
                    rt=row.rt,
                )
                peaks.append(target)

            if is_primary or (tac_idx is None and target.area is None):
                target.area = row.area
                target.area_pct = row.area_pct
                if target.height is None:
                    target.height = row.height
                if target.width is None:
                    target.width = row.width

            if blk.slot == "254nm":
                target.area_254nm = row.area
                target.area_pct_254nm = row.area_pct
            elif blk.slot == "220nm":
                target.area_220nm = row.area
                target.area_pct_220nm = row.area_pct

    peaks.sort(key=lambda p: (p.rt, p.peak_num))

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
        source_format="agilent_chemstation_txt",
        sample_id="",
        well=well,
        sample_index=None,
        detector=detector,
    )


def report_datetime(report: LCMSReport) -> Optional[str]:
    """Acquisition timestamp of an Agilent report.txt as 'YYYY-MM-DD HH:MM:SS'."""
    if not report.run_time or not report.date or report.date == "Unknown":
        return None
    combined = f"{report.date} {report.run_time}".strip()
    parsed_date, parsed_time = _parse_timestamp(combined)
    if parsed_date and parsed_time:
        return f"{parsed_date} {parsed_time}"
    return None
