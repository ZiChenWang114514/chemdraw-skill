#!/usr/bin/env python3
"""
LCMS Report Analyzer
Parses Waters MassLynx PDF reports using pdfplumber with spatial word-level
extraction. Extracts peak tables from all three detectors (TAC, 220nm, 254nm),
mass spectra (ESI+/ESI-), and UV lambda-max data. Optionally identifies
SM/product peaks by expected mass.

PDF layout handling:
- Pages 1-2: chromatograms + peak tables (TAC, 220nm, 254nm) — parsed from
  full-page extracted text.
- Pages 3+: mass spectra + UV panels in a 2-column × 4-row grid — parsed
  using word-level coordinates to avoid column interleaving. Each panel is
  isolated by bounding box (left column x < 306, right column x >= 306).

Data structures:
- LCMSReport: header info (sample name, date, instrument, method) + peaks
- ChromPeak: RT, area/area% for each detector, MS spectra, UV lambda-max
  - peak_num is a string: "4", or "2a"/"2b" when a table has duplicate numbers
- MassSpectrum: mode ("ES+"/"ES-") + top_ions (m/z values, descending intensity)

Usage:
    python lcms_analyzer.py \\
        --sm-mass 445 \\
        --product-mass 345 \\
        --procedure "KL-7003-008 (100 mg, 224 umol) was dissolved in..." \\
        file1.pdf file2.pdf ...
"""

import argparse
import re
import os
import sys
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict
from datetime import datetime
from collections import defaultdict

from cdxml_toolkit.constants import (
    LCMS_COLUMN_BOUNDARY,
    LCMS_MS_AXIS_TICKS,
    LCMS_UV_AXIS_TICKS,
    LCMS_UV_WAVELENGTH_MIN,
    LCMS_UV_WAVELENGTH_MAX,
)

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class MassSpectrum:
    """ESI+ or ESI- spectrum for a single chromatographic peak."""
    mode: str  # "ES+" or "ES-"
    top_ions: List[float] = field(default_factory=list)  # Up to 2 m/z values, tallest first

@dataclass
class ChromPeak:
    """A single integrated peak from the UV chromatogram."""
    peak_num: str  # e.g. "4", "2a", "2b"
    rt: float
    area: Optional[float] = None          # TAC area
    area_pct: Optional[float] = None      # TAC area %
    width: Optional[float] = None
    height: Optional[float] = None
    mass_found: Optional[str] = None
    ms_spectra: List[MassSpectrum] = field(default_factory=list)
    uv_lambda_max: List[float] = field(default_factory=list)
    area_220nm: Optional[float] = None
    area_pct_220nm: Optional[float] = None
    area_254nm: Optional[float] = None
    area_pct_254nm: Optional[float] = None

@dataclass
class LCMSReport:
    """Parsed contents of one MassLynx PDF report."""
    filename: str
    sample_name: str
    date: str
    instrument: str
    method_path: str
    method_short: str  # abbreviated method name for annotation
    peaks: List[ChromPeak] = field(default_factory=list)
    file_modified: Optional[str] = None
    run_time: Optional[str] = None  # "HH:MM:SS" from PDF header

# ---------------------------------------------------------------------------
# PDF text extraction
# ---------------------------------------------------------------------------

def extract_all_text(pdf_path: str) -> str:
    """Extract all text from all pages of a PDF."""
    import pdfplumber
    texts = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                texts.append(t)
    return "\n\n".join(texts)

# ---------------------------------------------------------------------------
# Parsing logic
# ---------------------------------------------------------------------------

def parse_method_short(method_path: str) -> str:
    """
    Extract a short method description from the full MassLynx method path.

    e.g. '...21_CSH_C18_AmF_5to100_ACN_220_254nm_TAC_TIC_1p9min.olp'
    -> 'CSH C18, AmF, 5-100%, 1.9 min'

    e.g. '...21_CSH_C18_AmB_50to100_ACN_220_254nm_TAC_TIC_1p9min.olp'
    -> 'CSH C18, AmB, 50-100%, 1.9 min'
    """
    basename = os.path.basename(method_path).replace('.olp', '')
    parts = basename.split('_')

    column = ""
    buffer_type = ""
    gradient = ""
    runtime = ""

    for p in parts:
        pl = p.lower()
        # Column type
        if any(kw in pl for kw in ('c18', 'c8', 'beh', 'csh', 'hss')):
            column = (column + " " + p).strip()
        # Buffer/modifier — check AmB before AmF to avoid false match
        # ('amb' doesn't contain 'amf' so order doesn't matter for exclusion,
        #  but we guard against future overlap)
        if not buffer_type:
            if pl in ('amb', 'ambic') or pl.startswith('amb'):
                buffer_type = "AmB"
            elif pl in ('amf',) or pl.startswith('amf'):
                buffer_type = "AmF"
            elif pl == 'fa':
                buffer_type = "FA"
            elif pl in ('tfa',) or pl.startswith('tfa'):
                buffer_type = "TFA"
        # Gradient range: 5to100, 5to50, 50to100
        m_grad = re.match(r'(\d+)to(\d+)', pl)
        if m_grad and not gradient:
            gradient = f"{m_grad.group(1)}-{m_grad.group(2)}%"
        # Runtime: 1p9min -> 1.9 min
        if 'min' in pl and not runtime:
            runtime = p.replace('p', '.').replace('min', ' min')

    pieces = [x for x in [column, buffer_type, gradient, runtime] if x]
    return ", ".join(pieces) if pieces else basename


def method_basename(method_path: str) -> str:
    """Return the method filename without directory and extension, lowercased.

    Used for grouping files by exact method — files with the same method
    basename are comparable (same column, buffer, gradient, runtime).
    """
    return os.path.basename(method_path).replace('.olp', '').lower()


def parse_header(text: str) -> dict:
    """Extract header fields from the report text."""
    info = {}

    m = re.search(r'Sample Name:\s*(\S+)', text)
    info['sample_name'] = m.group(1) if m else "Unknown"

    m = re.search(r'Date:\s*(\S+)', text)
    info['date'] = m.group(1) if m else "Unknown"

    m = re.search(r'Time:\s*(\d{1,2}:\d{2}:\d{2})', text)
    info['run_time'] = m.group(1) if m else None

    # Instrument name is on the line after "Page 1", before "_UPLC" or
    # similar suffix.  e.g. "PPIMSA05_UPLC-PDA-MS Open Access ..."
    m = re.search(r'Page\s+1\s*\n(\w+)', text)
    info['instrument'] = m.group(1).split('_')[0] if m else "Unknown"

    m = re.search(r'Method:\s*(.+?)(?:\n|Report)', text)
    info['method_path'] = m.group(1).strip() if m else "Unknown"

    return info


# ---------------------------------------------------------------------------
# Peak table parsing — all three detectors (TAC, 220nm, 254nm)
# ---------------------------------------------------------------------------

_ROW_PATTERN = re.compile(
    r'^\s*(\d+)\s+'           # peak number
    r'(\d+\.\d+)\s+'         # retention time
    r'(\d+)\s+'              # area
    r'(\d+\.\d+)\s+'         # area %
    r'(\d+\.\d+)\s+'         # width
    r'(\d+)\s+'              # height
    r'(.+?)$',               # mass found
    re.MULTILINE
)

_TABLE_HEADER = re.compile(r'Peak\s+Time\s+Area\s+Area\s*%', re.IGNORECASE)


def _parse_table_rows(text_block: str) -> List[dict]:
    """Parse peak rows from a single table text block."""
    rows = []
    for m in _ROW_PATTERN.finditer(text_block):
        rows.append({
            'peak_num_raw': int(m.group(1)),
            'rt': float(m.group(2)),
            'area': float(m.group(3)),
            'area_pct': float(m.group(4)),
            'width': float(m.group(5)),
            'height': float(m.group(6)),
            'mass_found': m.group(7).strip(),
        })
    return rows


def _identify_detector(text: str, header_start: int) -> str:
    """Look backward from a table header to identify detector type."""
    before = text[:header_start]
    tac_pos = max((m.start() for m in re.finditer(r'TAC:\s*Wavelength|UV Detector:\s*TAC', before)), default=-1)
    ch1_pos = max((m.start() for m in re.finditer(r'Ch1\s*220nm|PDA\s*Ch1', before)), default=-1)
    ch2_pos = max((m.start() for m in re.finditer(r'Ch2\s*254nm|PDA\s*Ch2', before)), default=-1)

    best = max(('TAC', tac_pos), ('220nm', ch1_pos), ('254nm', ch2_pos), key=lambda x: x[1])
    return best[0] if best[1] >= 0 else 'TAC'


def _build_peak_id_map(tables_raw: Dict[str, List[dict]]) -> Dict[Tuple[int, float], str]:
    """
    Build mapping from (raw_peak_num, rt) -> string peak_id.
    Assigns 'a', 'b' suffixes when a peak number appears at multiple distinct RTs.
    """
    all_pairs = set()
    for rows in tables_raw.values():
        for row in rows:
            all_pairs.add((row['peak_num_raw'], row['rt']))

    by_num: Dict[int, List[float]] = defaultdict(list)
    for num, rt in all_pairs:
        by_num[num].append(rt)

    mapping = {}
    for num, rts in by_num.items():
        rts_sorted = sorted(set(rts))
        if len(rts_sorted) == 1:
            mapping[(num, rts_sorted[0])] = str(num)
        else:
            for i, rt in enumerate(rts_sorted):
                mapping[(num, rt)] = f"{num}{chr(ord('a') + i)}"

    return mapping


def _lookup_peak_id(id_map: Dict[Tuple[int, float], str], raw_num: int, rt: float,
                    tolerance: float = 0.02) -> str:
    """Look up string peak ID with RT tolerance for fuzzy matching."""
    if (raw_num, rt) in id_map:
        return id_map[(raw_num, rt)]
    for (num, map_rt), pid in id_map.items():
        if num == raw_num and abs(map_rt - rt) < tolerance:
            return pid
    return str(raw_num)


def parse_all_peak_tables(text: str) -> Tuple[List[ChromPeak], Dict[Tuple[int, float], str]]:
    """
    Parse all UV peak integration tables (TAC, 220nm, 254nm).
    Returns (peaks, id_map) where id_map maps (raw_num, rt) -> string peak_id.
    """
    headers = list(_TABLE_HEADER.finditer(text))
    if not headers:
        return [], {}

    tables_raw: Dict[str, List[dict]] = {}
    for i, header in enumerate(headers):
        start = header.end()
        end = headers[i + 1].start() if i + 1 < len(headers) else len(text)
        table_text = text[start:end]
        detector = _identify_detector(text, header.start())
        rows = _parse_table_rows(table_text)
        if detector not in tables_raw:
            tables_raw[detector] = rows
        else:
            tables_raw[detector].extend(rows)

    id_map = _build_peak_id_map(tables_raw)

    peaks_dict: Dict[str, ChromPeak] = {}
    for detector, rows in tables_raw.items():
        for row in rows:
            pid = id_map[(row['peak_num_raw'], row['rt'])]
            if pid not in peaks_dict:
                peaks_dict[pid] = ChromPeak(
                    peak_num=pid,
                    rt=row['rt'],
                    width=row['width'],
                    height=row['height'],
                    mass_found=row['mass_found'],
                )
            p = peaks_dict[pid]
            if detector == 'TAC':
                p.area = row['area']
                p.area_pct = row['area_pct']
            elif detector == '220nm':
                p.area_220nm = row['area']
                p.area_pct_220nm = row['area_pct']
            elif detector == '254nm':
                p.area_254nm = row['area']
                p.area_pct_254nm = row['area_pct']

    peaks = sorted(peaks_dict.values(), key=lambda p: (p.rt, p.peak_num))
    return peaks, id_map


# ---------------------------------------------------------------------------
# Spatial mass spectrum + UV parsing (fixes two-column layout)
# ---------------------------------------------------------------------------

_MS_AXIS_TICKS = LCMS_MS_AXIS_TICKS
_UV_AXIS_TICKS = LCMS_UV_AXIS_TICKS


def _find_panel_headers(words: List[dict]) -> List[dict]:
    """Find 'Peak' words that are part of spectrum 'Peak Time Mass' headers.

    Rejects peak-table headers ('Peak Time Area Area% Width Height Mass Found')
    which also contain 'Peak', 'Time', and 'Mass' but are NOT spectrum panels.
    The discriminator is the presence of 'Area' or 'Height' as neighbours.
    """
    results = []
    for w in words:
        if w['text'] != 'Peak':
            continue
        y = w['top']
        neighbors = [nw['text'] for nw in words
                     if abs(nw['top'] - y) < 3 and nw['x0'] > w['x0']
                     and nw['x0'] < w['x0'] + 400]
        if 'Time' in neighbors and 'Mass' in neighbors:
            # Reject peak-table headers which have "Area" / "Height" / "Width"
            if 'Area' in neighbors or 'Height' in neighbors or 'Width' in neighbors:
                continue
            results.append(w)
    return results


def _group_headers_into_rows(headers: List[dict], y_tolerance: float = 5.0):
    """Group panel headers by y-coordinate into rows. Returns [(y, [headers])]."""
    if not headers:
        return []
    sorted_h = sorted(headers, key=lambda w: w['top'])
    rows = []
    current = [sorted_h[0]]
    current_y = sorted_h[0]['top']
    for h in sorted_h[1:]:
        if abs(h['top'] - current_y) < y_tolerance:
            current.append(h)
        else:
            rows.append((current_y, current))
            current = [h]
            current_y = h['top']
    rows.append((current_y, current))
    return rows


def _extract_mz_values(word_text: str) -> List[float]:
    """
    Extract m/z values from a word string, splitting joined numbers.
    MassLynx reports m/z to 1 decimal place, so we match \\d+\\.\\d patterns.
    E.g. '569.1814.6874.9' -> [569.1, 814.6, 874.9]
    """
    values = []
    for m in re.finditer(r'(\d+\.\d)', word_text):
        val = float(m.group(1))
        if 50 < val < 2000 and val not in _MS_AXIS_TICKS:
            values.append(val)
    return values


def _parse_ms_from_words(panel_words: List[dict]) -> List[MassSpectrum]:
    """
    Parse MS spectra from a panel's word list.
    Words are sorted top-to-bottom. MassLynx labels ions tallest-first.
    """
    results = []

    # Sort words by vertical position
    sorted_words = sorted(panel_words, key=lambda w: (w['top'], w['x0']))

    # Find MS mode markers and their positions
    ms_markers = []
    for w in sorted_words:
        m = re.match(r'(ES[+-])$', w['text'])
        if m:
            ms_markers.append((w['top'], m.group(1)))

    if not ms_markers:
        return results

    # For each MS mode section, collect m/z values from words below it
    for idx, (marker_y, mode) in enumerate(ms_markers):
        # Section ends at next MS marker, or at UV section, or at end
        if idx + 1 < len(ms_markers):
            section_end_y = ms_markers[idx + 1][0]
        else:
            # Find UV section start if present
            uv_words = [w for w in sorted_words if 'UV' in w['text'] or w['text'] == 'Nm']
            if uv_words:
                section_end_y = min(w['top'] for w in uv_words)
            else:
                section_end_y = float('inf')

        # Collect m/z values, splitting any joined numbers
        section_nums = []
        for w in sorted_words:
            if w['top'] <= marker_y or w['top'] >= section_end_y:
                continue
            section_nums.extend(_extract_mz_values(w['text']))

        if section_nums:
            results.append(MassSpectrum(mode=mode, top_ions=section_nums))

    return results


def _parse_uv_from_words(panel_words: List[dict]) -> List[float]:
    """Parse UV lambda-max wavelengths from a panel's word list."""
    sorted_words = sorted(panel_words, key=lambda w: (w['top'], w['x0']))

    # Find "AU" word position — wavelengths come after it
    au_y = None
    for w in sorted_words:
        if w['text'] == 'AU':
            au_y = w['top']
            break

    if au_y is None:
        return []

    wavelengths = []
    for w in sorted_words:
        if w['top'] <= au_y:
            continue
        try:
            val = float(w['text'])
            if LCMS_UV_WAVELENGTH_MIN <= val <= LCMS_UV_WAVELENGTH_MAX and val not in _UV_AXIS_TICKS:
                wavelengths.append(val)
        except ValueError:
            continue

    return wavelengths


def _parse_spectrum_pages(pdf) -> Tuple[Dict[int, Tuple[float, list]],
                                        Dict[int, Tuple[float, list]]]:
    """
    Parse mass spectra and UV lambda-max from spectrum pages using spatial cropping.
    Uses word-level extraction to avoid joined-number artifacts from extract_text().

    Returns:
        ms_data: {raw_peak_num: (rt, [MassSpectrum, ...])}
        uv_data: {raw_peak_num: (rt, [wavelength, ...])}
    """
    ms_data = {}
    uv_data = {}

    # Start from page 2 (index 1): MassLynx sometimes places the first
    # peak's mass spectrum at the bottom of page 2 after the peak tables.
    # Panel header detection rejects peak-table headers via "Area" filter.
    for page_idx in range(1, len(pdf.pages)):
        page = pdf.pages[page_idx]
        words = page.extract_words()
        if not words:
            continue

        headers = _find_panel_headers(words)
        if not headers:
            continue

        rows = _group_headers_into_rows(headers)
        page_width = float(page.width)
        page_height = float(page.height)
        col_mid = LCMS_COLUMN_BOUNDARY

        for i, (y_start, headers_in_row) in enumerate(rows):
            y_end = rows[i + 1][0] if i + 1 < len(rows) else page_height

            for hdr in headers_in_row:
                x_center = (hdr['x0'] + hdr['x1']) / 2
                if x_center < col_mid:
                    x_start, x_end = 0, col_mid
                else:
                    x_start, x_end = col_mid, page_width

                # Filter words to this panel's bounding box
                panel_words = [w for w in words
                               if w['x0'] >= x_start and w['x1'] <= x_end
                               and w['top'] >= y_start - 2 and w['top'] < y_end]

                if not panel_words:
                    continue

                # Extract peak number and RT from panel words
                # Look for the first integer followed by a decimal (e.g. "4" then "0.64")
                peak_num = None
                rt = None
                num_words = sorted(panel_words, key=lambda w: (w['top'], w['x0']))
                for j, w in enumerate(num_words):
                    if peak_num is not None:
                        break
                    if re.match(r'^\d+$', w['text']) and w['text'] != '0':
                        # Check if next word at similar y is a decimal (RT)
                        for nw in num_words[j+1:j+4]:
                            if abs(nw['top'] - w['top']) < 3 and re.match(r'^\d+\.\d+$', nw['text']):
                                peak_num = int(w['text'])
                                rt = float(nw['text'])
                                break

                if peak_num is None:
                    continue

                # Check panel content type from word texts
                panel_texts = [w['text'] for w in panel_words]
                has_ms = any('ES+' in t or 'ES-' in t for t in panel_texts)
                has_uv = any('UV' in t for t in panel_texts) and any('Detector' in t for t in panel_texts)

                # Parse MS data
                if has_ms:
                    ms_list = _parse_ms_from_words(panel_words)
                    if ms_list:
                        if peak_num not in ms_data:
                            ms_data[peak_num] = (rt, [])
                        ms_data[peak_num][1].extend(ms_list)

                # Parse UV data
                if has_uv:
                    wavelengths = _parse_uv_from_words(panel_words)
                    if wavelengths:
                        if peak_num not in uv_data:
                            uv_data[peak_num] = (rt, [])
                        uv_data[peak_num][1].extend(wavelengths)

    return ms_data, uv_data


def is_waters_report(pdf_path: str) -> bool:
    """Quick content-based check: is this PDF a standard Waters MassLynx report?

    Manually integrated chromatograms (e.g. LC-only or MS-only exports) lack
    the structured headers of a full UPLC-PDA-MS Open Access report. This
    function reads only the first page and checks for Waters report markers.

    Returns True for standard reports, False for manually integrated exports
    or other non-standard PDFs.
    """
    import pdfplumber
    try:
        with pdfplumber.open(pdf_path) as pdf:
            if not pdf.pages:
                return False
            text = pdf.pages[0].extract_text() or ""
            # Standard Waters MassLynx reports contain these markers on page 1
            # Check for at least 2 of 3 markers for robustness
            markers = [
                "Sample Name:" in text,
                "Instrument:" in text or "UPLC" in text,
                "Date:" in text and "Time:" in text,
            ]
            return sum(markers) >= 2
    except Exception:
        return False


def parse_report(pdf_path: str) -> LCMSReport:
    """Parse a complete MassLynx PDF report."""
    import pdfplumber

    with pdfplumber.open(pdf_path) as pdf:
        # Extract all text for header and peak tables
        texts = []
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                texts.append(t)
        text = "\n\n".join(texts)

        header = parse_header(text)
        peaks, id_map = parse_all_peak_tables(text)

        # Parse mass spectra and UV using spatial approach
        ms_data, uv_data = _parse_spectrum_pages(pdf)

    # Attach MS spectra to peaks
    for raw_num, (rt, ms_list) in ms_data.items():
        pid = _lookup_peak_id(id_map, raw_num, rt)
        for peak in peaks:
            if peak.peak_num == pid:
                peak.ms_spectra = ms_list
                break

    # Attach UV lambda-max to peaks
    for raw_num, (rt, wavelengths) in uv_data.items():
        pid = _lookup_peak_id(id_map, raw_num, rt)
        for peak in peaks:
            if peak.peak_num == pid:
                peak.uv_lambda_max = wavelengths
                break

    # Get file modified time
    mtime = os.path.getmtime(pdf_path)
    modified = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")

    return LCMSReport(
        filename=os.path.basename(pdf_path),
        sample_name=header['sample_name'],
        date=header['date'],
        instrument=header['instrument'],
        method_path=header['method_path'],
        method_short=parse_method_short(header['method_path']),
        peaks=peaks,
        file_modified=modified,
        run_time=header.get('run_time'),
    )

# ---------------------------------------------------------------------------
# Manual integration reports (LC-only / MS-only MassLynx exports)
# ---------------------------------------------------------------------------

@dataclass
class ManualPeak:
    """A peak from a manually integrated chromatogram."""
    peak_num: str
    rt: float
    area: float
    area_pct: float
    height: Optional[float] = None


@dataclass
class ManualLCMSSample:
    """One chromatogram section from a manual integration PDF."""
    sample_name: str
    peaks: List[ManualPeak] = field(default_factory=list)
    detector: str = ""  # e.g. "Diode Array 290nm"
    from_labels: bool = False  # True if parsed from RT;Area labels (best-effort)


@dataclass
class ManualLCMSReport:
    """Parsed contents of a manually integrated MassLynx PDF."""
    filename: str
    instrument: str
    date: str
    samples: List[ManualLCMSSample] = field(default_factory=list)
    run_time: Optional[str] = None


def is_manual_integration(pdf_path: str) -> bool:
    """Check if this PDF is a MassLynx manual integration export.

    Manual integration PDFs have "Diode Array" but lack the structured
    "Sample Name:" / "Date:" / "Time:" headers of a full Waters report.
    """
    import pdfplumber
    try:
        with pdfplumber.open(pdf_path) as pdf:
            if not pdf.pages:
                return False
            text = pdf.pages[0].extract_text() or ""
            has_diode_array = "Diode Array" in text
            has_waters_header = "Sample Name:" in text
            return has_diode_array and not has_waters_header
    except Exception:
        return False


def parse_manual_report(pdf_path: str) -> ManualLCMSReport:
    """Parse a manually integrated MassLynx PDF.

    Handles three variants:
      1. Single sample with peak table (Time Height Area Area%)
      2. Multi-sample with peak tables per section
      3. Multi-sample with only RT;Area chromatogram labels (no table)

    Returns a ManualLCMSReport with one ManualLCMSSample per chromatogram.
    """
    text = extract_all_text(pdf_path)
    filename = os.path.basename(pdf_path)

    # --- Header: first line is "SampleName Instrument Date" ---
    # Instrument is an alphanumeric code (e.g. PPIMSA05, UPLCMS01, SQD2)
    # immediately followed by a date in DD-Mon-YYYY format.
    header_match = re.match(
        r'(.+?)\s+([A-Z][A-Za-z0-9]+)\s+'
        r'(\d{1,2}-\w{3}-\d{4})\s*\n\s*(\d{2}:\d{2}:\d{2})?',
        text
    )
    instrument = header_match.group(2) if header_match else ""
    date_str = header_match.group(3) if header_match else ""
    run_time = header_match.group(4) if header_match else None

    # --- Split into per-sample sections ---
    # Each section starts with a sample name followed by optional smoothing
    # params and "3: Diode Array" or similar detector marker.
    # Pattern: "SampleName [Sm (Mn, 2x3)] 3: Diode Array"
    section_pattern = re.compile(
        r'^([\w][\w\-]+(?:\s+Sm\s*\([^)]+\))?)\s+'
        r'(\d+:\s*Diode Array)\s*\n'
        r'(.*?)(?=^[\w][\w\-]+(?:\s+Sm\s*\([^)]+\))?\s+\d+:\s*Diode Array|\Z)',
        re.MULTILINE | re.DOTALL
    )

    samples = []
    for m in section_pattern.finditer(text):
        raw_name = m.group(1).strip()
        detector_str = m.group(2).strip()
        section_text = m.group(3)

        # Clean sample name: strip smoothing params
        sample_name = re.sub(r'\s+Sm\s*\([^)]+\)', '', raw_name).strip()

        # Try to extract detector wavelength
        wl_match = re.search(r'(\d{3})', detector_str)
        detector = f"Diode Array {wl_match.group(1)}nm" if wl_match else detector_str

        # --- Try peak table first (Time Height Area Area%) ---
        # Table rows may be interleaved with Y-axis tick labels (e.g.
        # "5.5e+1") from pdfplumber. We search for the header, then
        # scan subsequent lines for 4-number rows that look like
        # Time Height Area Area% data.
        peaks = []
        header_match = re.search(r'Time\s+Height\s+Area\s+Area%', section_text)
        if header_match:
            after_header = section_text[header_match.end():]
            # Find rows of 4 numbers where RT is plausible (<20 min)
            # and Area% is 0-100
            row_pattern = re.compile(
                r'(\d+\.\d+)\s+(\d+)\s+(\d+(?:\.\d+)?)\s+(\d+\.\d+)'
            )
            for rm in row_pattern.finditer(after_header):
                rt = float(rm.group(1))
                height = float(rm.group(2))
                area = float(rm.group(3))
                area_pct = float(rm.group(4))
                # Sanity: RT < 20 min, area% <= 100
                if rt < 20.0 and area_pct <= 100.0:
                    peaks.append(ManualPeak(
                        peak_num=str(len(peaks) + 1),
                        rt=rt,
                        height=height,
                        area=area,
                        area_pct=area_pct,
                    ))
        else:
            # --- Fallback: parse RT;Area labels from chromatogram ---
            # Labels appear as "RT;Area" or "RT\nArea" (area on next line)
            label_pattern = re.compile(
                r'([\d.]+);([\d.]+)'  # "0.56;404"
            )
            raw_peaks = []
            for lm in label_pattern.finditer(section_text):
                raw_peaks.append((float(lm.group(1)), float(lm.group(2))))

            # Also catch "RT\nArea" patterns (RT alone, area on next line)
            # These show up when the label wraps, e.g. "1.32\n20"
            # But we need to avoid matching axis ticks. Axis ticks are on
            # lines starting with "-0.00" or in sequences.
            # Strategy: look for floating numbers that aren't matched by
            # the RT;Area pattern and aren't axis-like.
            standalone_rt_pattern = re.compile(
                r'(?<!\d[;.])(?:^|\s)((?:0\.\d{2}|1\.\d{2}))\s*\n\s*(\d+)(?:\s|$)',
                re.MULTILINE
            )
            for sm in standalone_rt_pattern.finditer(section_text):
                rt_val = float(sm.group(1))
                area_val = float(sm.group(2))
                # Deduplicate: skip if we already have a peak at this RT
                if not any(abs(rt_val - rp[0]) < 0.02 for rp in raw_peaks):
                    raw_peaks.append((rt_val, area_val))

            # Sort by RT and compute area%
            raw_peaks.sort(key=lambda x: x[0])
            total_area = sum(a for _, a in raw_peaks) if raw_peaks else 1.0
            for i, (rt, area) in enumerate(raw_peaks, 1):
                peaks.append(ManualPeak(
                    peak_num=str(i),
                    rt=rt,
                    area=area,
                    area_pct=(area / total_area * 100) if total_area > 0 else 0.0,
                ))

        used_labels = not bool(header_match)
        samples.append(ManualLCMSSample(
            sample_name=sample_name,
            peaks=peaks,
            detector=detector,
            from_labels=used_labels,
        ))

    return ManualLCMSReport(
        filename=filename,
        instrument=instrument,
        date=date_str,
        samples=samples,
        run_time=run_time,
    )


def format_manual_table(report: ManualLCMSReport) -> str:
    """Format a manual integration report as markdown for LLM consumption."""
    lines = []

    lines.append(f"**File:** {report.filename} (manual integration)")
    lines.append(f"**Instrument:** {report.instrument}")
    date_str = report.date
    if report.run_time:
        date_str += f" {report.run_time}"
    lines.append(f"**Date:** {date_str}")

    for sample in report.samples:
        lines.append("")
        lines.append(f"### {sample.sample_name}")
        if not sample.peaks:
            lines.append("(no peaks)")
            continue

        lines.append(f"| # | RT | Area% |")
        lines.append(f"|---|------|-------|")
        total_pct = 0.0
        for peak in sample.peaks:
            lines.append(f"| {peak.peak_num} | {peak.rt:.2f} | {peak.area_pct:.1f} |")
            total_pct += peak.area_pct
        if total_pct < 95.0:
            lines.append(f"")
            lines.append(f"*Warning: parsed peaks sum to {total_pct:.1f}% — some peaks may not have been extracted.*")
        elif sample.from_labels:
            lines.append(f"")
            lines.append(f"*Note: area% computed from chromatogram labels (no peak table in PDF). Some small peaks may be missing.*")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Peak identification by expected mass
# ---------------------------------------------------------------------------

def identify_peak(peak: ChromPeak, sm_mass: float, product_mass: float,
                  tolerance: float = 1.5) -> Optional[str]:
    """
    Try to identify a peak as SM, product, or unknown based on ESI mass data.

    Checks for [M+H]+, [M-H]-, [M+Na]+, [M+formate]- adducts.
    Returns: "SM", "DP" (desired product), or None

    Key subtlety: if ESI+ matches product but ESI- matches SM for the same peak,
    that's likely SM with in-source fragmentation (e.g. Boc loss). We collect
    evidence from both polarities and resolve conflicts.
    """
    adducts_pos = [
        ("M+H", 1.008),
        ("M+Na", 22.990),
    ]
    adducts_neg = [
        ("M-H", -1.008),
        ("M+formate", 44.998),
    ]

    # Collect all evidence: list of (identity, mode, adduct_name, mz, is_base_peak)
    evidence = []

    for spec in peak.ms_spectra:
        if not spec.top_ions:
            continue
        for i, mz in enumerate(spec.top_ions):
            is_base = (i == 0)  # First ion is the tallest
            if spec.mode == "ES+":
                for adduct_name, adduct_mass in adducts_pos:
                    if abs(mz - (product_mass + adduct_mass)) < tolerance:
                        evidence.append(("DP", spec.mode, adduct_name, mz, is_base))
                    if abs(mz - (sm_mass + adduct_mass)) < tolerance:
                        evidence.append(("SM", spec.mode, adduct_name, mz, is_base))
            elif spec.mode == "ES-":
                for adduct_name, adduct_mass in adducts_neg:
                    if abs(mz - (product_mass + adduct_mass)) < tolerance:
                        evidence.append(("DP", spec.mode, adduct_name, mz, is_base))
                    if abs(mz - (sm_mass + adduct_mass)) < tolerance:
                        evidence.append(("SM", spec.mode, adduct_name, mz, is_base))

    if not evidence:
        return None

    # Resolve: do we have conflicting identities?
    identities_found = set(e[0] for e in evidence)

    if len(identities_found) == 1:
        return identities_found.pop()

    if "SM" in identities_found and "DP" in identities_found:
        # Conflict! Common case: SM fragments in ESI+ to look like product.
        # Heuristic: if ESI- clearly shows SM (via [M-H]-), trust that over
        # ESI+ showing product (which is likely in-source fragmentation).
        sm_neg = [e for e in evidence if e[0] == "SM" and e[1] == "ES-"]
        dp_pos = [e for e in evidence if e[0] == "DP" and e[1] == "ES+"]

        if sm_neg:
            # ESI- says SM — trust it. The ESI+ "product" signal is fragmentation.
            return "SM"

        sm_pos = [e for e in evidence if e[0] == "SM" and e[1] == "ES+"]
        dp_neg = [e for e in evidence if e[0] == "DP" and e[1] == "ES-"]

        if dp_neg:
            return "DP"

        # Both in same polarity — go with the one that has base peak evidence
        sm_base = [e for e in evidence if e[0] == "SM" and e[4]]
        dp_base = [e for e in evidence if e[0] == "DP" and e[4]]
        if dp_base and not sm_base:
            return "DP"
        if sm_base and not dp_base:
            return "SM"

        # Default: return the one with more evidence
        sm_count = sum(1 for e in evidence if e[0] == "SM")
        dp_count = sum(1 for e in evidence if e[0] == "DP")
        return "SM" if sm_count >= dp_count else "DP"

    return None

# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------

def format_annotation(report: LCMSReport, sm_mass: float, product_mass: float) -> str:
    """
    Format section (1): LCMS annotation line.
    Template: [Instrument], [Method short], SM RT = X.XX min, ESI+/- XXX.X; DP RT = X.XX min, ESI+/- XXX.X
    """
    instrument_short = report.instrument.split('#')[0] if '#' in report.instrument else report.instrument

    sm_parts = []
    dp_parts = []

    for peak in report.peaks:
        identity = identify_peak(peak, sm_mass, product_mass)
        if identity == "SM":
            best_ion = _find_best_ion_for(peak, sm_mass)
            sm_parts.append((peak.rt, peak.area_pct, best_ion))
        elif identity == "DP":
            best_ion = _find_best_ion_for(peak, product_mass)
            dp_parts.append((peak.rt, peak.area_pct, best_ion))

    # Pick the highest-area match for SM and DP
    sm_parts.sort(key=lambda x: x[1], reverse=True)
    dp_parts.sort(key=lambda x: x[1], reverse=True)

    parts = []
    parts.append(f"{instrument_short}")
    parts.append(f"{report.method_short}")

    if sm_parts:
        rt, area_pct, ion_str = sm_parts[0]
        parts.append(f"SM RT = {rt:.2f} min, {ion_str}")

    if dp_parts:
        rt, area_pct, ion_str = dp_parts[0]
        parts.append(f"DP RT = {rt:.2f} min, {ion_str}")

    return ", ".join(parts)


def _find_best_ion_for(peak: ChromPeak, exact_mass: float) -> str:
    """Find the best matching ion and return formatted string like 'ESI+ 346.0' or 'ESI- 444.1'."""
    tolerance = 1.5

    for spec in peak.ms_spectra:
        for mz in spec.top_ions:
            if spec.mode == "ES+":
                if abs(mz - (exact_mass + 1.008)) < tolerance:
                    return f"ESI+ {mz:.1f}"
            elif spec.mode == "ES-":
                if abs(mz - (exact_mass - 1.008)) < tolerance:
                    return f"ESI- {mz:.1f}"

    return "mass not confirmed"


def format_peak_summary(report: LCMSReport, sm_mass: float, product_mass: float) -> str:
    """Format a summary of all peaks with identification."""
    lines = []
    for peak in report.peaks:
        identity = identify_peak(peak, sm_mass, product_mass)
        label = identity if identity else "unknown"

        ion_strs = []
        for spec in peak.ms_spectra:
            if spec.top_ions:
                ion_strs.append(f"ESI{'+' if spec.mode == 'ES+' else '-'} {spec.top_ions[0]:.1f}")

        ion_info = "; ".join(ion_strs) if ion_strs else "no MS data"
        area_str = f"{peak.area_pct:.1f}%" if peak.area_pct is not None else "-"
        lines.append(f"  Peak {peak.peak_num}: RT {peak.rt:.2f} min, {area_str}, {ion_info} → {label}")

    return "\n".join(lines)


def analyze_reaction_progress(reports: List[LCMSReport], sm_mass: float, product_mass: float) -> str:
    """
    Analyze reaction progress across multiple timepoints.
    Returns notes section.
    """
    notes = []

    for report in reports:
        sm_area = 0.0
        dp_area = 0.0
        unknown_area = 0.0

        for peak in report.peaks:
            if peak.area_pct is None:
                continue  # Skip peaks not in TAC table
            identity = identify_peak(peak, sm_mass, product_mass)
            if identity == "SM":
                sm_area += peak.area_pct
            elif identity == "DP":
                dp_area += peak.area_pct
            else:
                unknown_area += peak.area_pct

        # Infer timepoint / action from filename
        name = report.sample_name.lower()
        timepoint = _infer_timepoint(name)

        if sm_area > 0 and dp_area > 0:
            conversion = dp_area / (dp_area + sm_area) * 100
            note = f"{report.sample_name} ({report.date}): ~{conversion:.0f}% conversion{timepoint}."
            if unknown_area > 2:
                note += f" ({unknown_area:.0f}% unidentified)"
            notes.append(note)
        elif dp_area > 0 and sm_area == 0:
            note = f"{report.sample_name} ({report.date}): SM consumed{timepoint}. DP {dp_area:.0f}%"
            if unknown_area > 2:
                note += f", impurities {unknown_area:.0f}%"
            note += "."
            notes.append(note)
        elif sm_area > 0 and dp_area == 0:
            notes.append(f"{report.sample_name} ({report.date}): No product detected{timepoint}. SM {sm_area:.0f}%.")
        else:
            notes.append(f"{report.sample_name} ({report.date}): Neither SM nor DP identified in major peaks{timepoint}.")

    return "\n".join(notes)


def _infer_timepoint(name: str) -> str:
    """Try to infer timepoint or action from sample name."""
    # Common patterns in LCMS filenames
    patterns = [
        (r'(\d+)\s*h\b', lambda m: f" after {m.group(1)}h"),
        (r'(\d+)\s*min\b', lambda m: f" after {m.group(1)} min"),
        (r't(\d+)', lambda m: f" at t={m.group(1)}"),
        (r'overnight|o/?n', lambda m: " after overnight"),
        (r'ea\s*wash', lambda m: " (after EtOAc wash)"),
        (r'dcm\s*wash', lambda m: " (after DCM wash)"),
        (r'purif', lambda m: " (after purification)"),
        (r'c18', lambda m: " (C18 purification)"),
        (r'crude', lambda m: " (crude)"),
        (r'addmore', lambda m: " (after adding more reagent)"),
    ]

    for pattern, formatter in patterns:
        m = re.search(pattern, name, re.IGNORECASE)
        if m:
            return formatter(m)

    return ""


def format_basic_report(report: LCMSReport) -> str:
    """
    Format a single LCMS file report without species identification.

    Produces a simple peak table with RT, area%, ions, and UV data.
    Used when SM/product masses are not available, or when the pipeline
    has only a single tracking file (no cross-file analysis needed).
    """
    import math

    lines = []
    lines.append("=" * 60)
    lines.append("SINGLE-FILE LCMS REPORT")
    lines.append("=" * 60)
    lines.append("")
    lines.append(f"File:       {report.filename}")
    lines.append(f"Sample:     {report.sample_name}")
    lines.append(f"Date:       {report.date}"
                 + (f" {report.run_time}" if report.run_time else ""))
    lines.append(f"Instrument: {report.instrument}")
    lines.append(f"Method:     {report.method_short}")
    lines.append("")
    lines.append("-" * 60)
    lines.append("PEAK TABLE")
    lines.append("-" * 60)
    lines.append("")

    if not report.peaks:
        lines.append("  (no peaks detected)")
        return "\n".join(lines)

    for peak in report.peaks:
        # Area columns: TAC, 220nm, 254nm
        areas = []
        if peak.area_pct is not None:
            areas.append(f"TAC {peak.area_pct:.1f}%")
        if peak.area_pct_220nm is not None:
            areas.append(f"220nm {peak.area_pct_220nm:.1f}%")
        if peak.area_pct_254nm is not None:
            areas.append(f"254nm {peak.area_pct_254nm:.1f}%")
        area_str = ", ".join(areas) if areas else "(no area)"

        # Ions
        ion_strs = []
        for spec in peak.ms_spectra:
            if spec.top_ions:
                mode_str = "ESI+" if spec.mode == "ES+" else "ESI-"
                top = ", ".join(f"{mz:.1f}" for mz in spec.top_ions[:3])
                ion_strs.append(f"{mode_str} {top}")
        ion_info = "; ".join(ion_strs) if ion_strs else "no MS"

        # UV lambda max
        uv_str = ""
        if peak.uv_lambda_max:
            wl_strs = [str(math.floor(wl + 0.5)) for wl in sorted(peak.uv_lambda_max)]
            uv_str = f"  λmax {', '.join(wl_strs)} nm"

        lines.append(f"  Peak {peak.peak_num}: RT {peak.rt:.2f} min, "
                     f"{area_str}")
        lines.append(f"    Ions: {ion_info}{uv_str}")
        lines.append("")

    return "\n".join(lines)


def format_table(report: LCMSReport) -> str:
    """Format an LCMS report as a markdown table for LLM consumption.

    Output is pure data — no peak identification, no conversion, no
    interpretation.  Header key-value lines followed by a 7-column table:
    peak#, RT, TAC%, 220nm%, 254nm%, ESI+ ions, ESI- ions.
    """
    import math

    lines = []

    # Header metadata
    lines.append(f"**Sample:** {report.sample_name}")
    lines.append(f"**Instrument:** {report.instrument}")
    lines.append(f"**Method:** {report.method_short}")
    date_str = report.date
    if report.run_time:
        date_str += f" {report.run_time}"
    lines.append(f"**Date:** {date_str}")
    lines.append("")

    if not report.peaks:
        lines.append("(no peaks detected)")
        return "\n".join(lines)

    # Table header
    lines.append("| # | RT | TAC% | 220nm% | 254nm% | ESI+ | ESI\u2212 |")
    lines.append("|---|------|-------|--------|--------|------|------|")

    for peak in report.peaks:
        # Area columns
        tac = f"{peak.area_pct:.1f}" if peak.area_pct is not None else "\u2014"
        a220 = f"{peak.area_pct_220nm:.1f}" if peak.area_pct_220nm is not None else "\u2014"
        a254 = f"{peak.area_pct_254nm:.1f}" if peak.area_pct_254nm is not None else "\u2014"

        # ESI columns: top 2-3 ions per mode, comma-separated
        esi_plus = "\u2014"
        esi_minus = "\u2014"
        for spec in peak.ms_spectra:
            ions_str = ", ".join(f"{mz:.1f}" for mz in spec.top_ions[:3])
            if not ions_str:
                continue
            if spec.mode == "ES+":
                esi_plus = ions_str
            elif spec.mode == "ES-":
                esi_minus = ions_str

        lines.append(
            f"| {peak.peak_num} | {peak.rt:.2f} "
            f"| {tac} | {a220} | {a254} "
            f"| {esi_plus} | {esi_minus} |"
        )

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="LCMS Report Analyzer")
    parser.add_argument('files', nargs='+', help='MassLynx PDF report files')
    parser.add_argument('--sm-mass', type=float, default=None,
                       help='Exact mass of starting material')
    parser.add_argument('--product-mass', type=float, default=None,
                       help='Exact mass of desired product')
    parser.add_argument('--procedure', type=str, default='',
                       help='Original procedure text (for context)')
    parser.add_argument('--output', type=str, default=None,
                       help='Output file path (default: stdout)')
    parser.add_argument('--format', type=str, default='table',
                       choices=['basic', 'table'],
                       help='Output format: table (default, markdown for LLM) or basic')

    args = parser.parse_args(argv)

    # Parse all reports (auto-detect manual integration vs Waters)
    reports = []          # standard Waters reports
    manual_reports = []   # manual integration exports
    for f in sorted(args.files):
        try:
            if is_manual_integration(f):
                manual_reports.append(parse_manual_report(f))
            else:
                reports.append(parse_report(f))
        except Exception as e:
            print(f"Warning: Could not parse {f}: {e}", file=sys.stderr)

    if not reports and not manual_reports:
        print("Error: No reports could be parsed.", file=sys.stderr)
        return 1

    # Sort by date/time
    reports.sort(key=lambda r: r.date)

    # Table format: pure data for LLM consumption, ignores SM/product masses
    if args.format == 'table':
        parts = [format_table(r) for r in reports]
        parts += [format_manual_table(r) for r in manual_reports]
        result = "\n\n".join(parts)
    elif args.sm_mass is None or args.product_mass is None:
        result = "\n\n".join(format_basic_report(r) for r in reports)
    else:
        # Build full annotated output
        output_lines = []

        # Section 1: Annotation
        output_lines.append("=" * 60)
        output_lines.append("(1) LCMS ANNOTATION")
        output_lines.append("=" * 60)
        for report in reports:
            # Header line: sample name + date/time
            time_str = f" {report.run_time}" if report.run_time else ""
            output_lines.append(
                f"{report.sample_name} (Date: {report.date}{time_str}, "
                f"{report.instrument}):"
            )
            annotation = format_annotation(report, args.sm_mass, args.product_mass)
            output_lines.append(f"  {annotation}")
            # Also show peak breakdown
            output_lines.append(format_peak_summary(report, args.sm_mass, args.product_mass))
            output_lines.append("")

        # Section 2: Tentative procedure
        output_lines.append("=" * 60)
        output_lines.append("(2) TENTATIVE PROCEDURE")
        output_lines.append("=" * 60)
        if args.procedure:
            output_lines.append(args.procedure)
        else:
            output_lines.append("[No procedure provided]")
        output_lines.append("")

        # Section 3: Notes
        output_lines.append("=" * 60)
        output_lines.append("(3) NOTES")
        output_lines.append("=" * 60)
        output_lines.append(analyze_reaction_progress(reports, args.sm_mass, args.product_mass))

        result = "\n".join(output_lines)

    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(result)
        print(f"Output written to {args.output}", file=sys.stderr)
    else:
        sys.stdout.buffer.write(result.encode('utf-8'))
        sys.stdout.buffer.write(b'\n')

    return 0


if __name__ == '__main__':
    sys.exit(main())
