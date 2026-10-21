#!/usr/bin/env python3
"""
Multi-LCMS Analyzer
Collates peaks across multiple LCMS files from the same reaction to:
1. Match peaks across files (same compound identification by RT + UV ratio)
2. Merge mass spectrum ions into recurring vs one-off lists
3. Track area% trends over time (increasing / decreasing / stable)

Input: MassLynx PDF files (parsed internally via lcms_analyzer.parse_report).
Output: Text report (default) or structured JSON (--json).

Usage:
    python multi_lcms_analyzer.py \\
        file1.pdf file2.pdf file3.pdf ... \\
        --rt-tolerance 0.02 \\
        --mz-tolerance 0.5 \\
        --trend-threshold 0.2
"""

import argparse
import json
import os
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from statistics import median
from typing import List, Optional, Dict, Tuple

from cdxml_toolkit.constants import (
    LCMS_RT_TOLERANCE,
    LCMS_MZ_TOLERANCE,
    LCMS_TREND_THRESHOLD,
    LCMS_MIN_SUMMARY_AREA,
)
from ..lcms_analyzer import (
    parse_report, LCMSReport, ChromPeak, MassSpectrum, format_basic_report,
    is_waters_report, method_basename,
)
from .lcms_file_categorizer import categorize_lcms_file, _AMBIGUOUS_SORT_KEYS

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class FileEntry:
    """Metadata for one LCMS file in the analysis."""
    path: str
    filename: str
    category: str       # "tracking", "workup", "purification", "final"
    sort_key: float
    report: Optional[LCMSReport] = None
    run_datetime: Optional[str] = None   # "YYYY-MM-DD HH:MM:SS" from PDF
    ambiguous_time: bool = False         # True for "beforeadd" etc.
    group_prefix: Optional[str] = None   # tracking group prefix (from batch categorizer)
    method_variant: Optional[str] = None # filename-derived method hint (AmB, AmF, etc.)

@dataclass
class IonCluster:
    """A group of m/z values across files that represent the same ion."""
    mean_mz: float
    mode: str               # "ES+" or "ES-"
    occurrences: int         # number of files this ion appeared in
    best_rank: int           # best (lowest) rank seen across files (0 = base peak)
    mz_values: List[float] = field(default_factory=list)

@dataclass
class Compound:
    """A matched compound tracked across multiple LCMS files."""
    compound_id: int
    canonical_rt: float = 0.0
    uv_ratio: Optional[float] = None   # area_220nm / area_254nm

    # Per-file data: keyed by file index (chronological order)
    rt_by_file: Dict[int, float] = field(default_factory=dict)
    area_pct_by_file: Dict[int, Optional[float]] = field(default_factory=dict)
    area_220_by_file: Dict[int, Optional[float]] = field(default_factory=dict)
    area_254_by_file: Dict[int, Optional[float]] = field(default_factory=dict)
    area_pct_220_by_file: Dict[int, Optional[float]] = field(default_factory=dict)
    area_pct_254_by_file: Dict[int, Optional[float]] = field(default_factory=dict)

    # Raw ion collection: (mode, mz, rank_in_top_ions, file_index)
    all_ions: List[Tuple[str, float, int, int]] = field(default_factory=list)

    # Merged ion clusters (populated after matching)
    recurring_ions: List[IonCluster] = field(default_factory=list)
    other_ions: List[IonCluster] = field(default_factory=list)

    # UV lambda-max consensus
    uv_lambda_max: List[float] = field(default_factory=list)

    # Trend
    trend: str = "stable"
    trend_detail: str = ""
    max_area: float = 0.0  # max observed area% (excluding outlier files)

@dataclass
class AnalysisResult:
    """Complete result of the multi-file LCMS analysis."""
    instrument: str
    method_short: str
    method_key: str = ""                 # method basename for grouping (lowercased)
    files: List[FileEntry] = field(default_factory=list)
    compounds: List[Compound] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    excluded_files: set = field(default_factory=set)   # indices of outlier files
    ambiguous_files: set = field(default_factory=set)  # indices with uncertain timing
    discarded_files: List[FileEntry] = field(default_factory=list)  # files from other groups

# ---------------------------------------------------------------------------
# Note: File categorization code has been extracted to lcms_file_categorizer.py
# ---------------------------------------------------------------------------

def extract_run_datetime(pdf_path: str) -> Optional[str]:
    """
    Extract the acquisition date+time from a MassLynx PDF.
    Looks for 'Date:DD-Mon-YYYY' and 'Time:HH:MM:SS' in the header.
    Returns ISO-format string 'YYYY-MM-DD HH:MM:SS' or None.
    """
    from ..lcms_analyzer import extract_all_text

    try:
        text = extract_all_text(pdf_path)
    except Exception:
        return None

    date_m = re.search(r'Date:(\d{1,2}-\w{3}-\d{4})', text)
    time_m = re.search(r'Time:(\d{1,2}:\d{2}:\d{2})', text)

    if not date_m or not time_m:
        return None

    try:
        from datetime import datetime as _dt
        dt = _dt.strptime(f"{date_m.group(1)} {time_m.group(1)}",
                          "%d-%b-%Y %H:%M:%S")
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# UV ratio helpers
# ---------------------------------------------------------------------------

def compute_uv_ratio(peak: ChromPeak) -> Optional[float]:
    """
    Compute area_220nm / area_254nm for a peak.
    Returns None if either area is missing or zero (inconclusive data).
    Only returns a meaningful ratio when both areas are present and non-zero.
    """
    a220 = peak.area_220nm
    a254 = peak.area_254nm
    if a220 is None or a254 is None:
        return None
    if a220 == 0 or a254 == 0:
        return None
    return a220 / a254


def check_uv_compatibility(ratio_a: Optional[float],
                           ratio_b: Optional[float]) -> Optional[bool]:
    """
    Check if two UV ratios are compatible.
    Returns True (compatible), False (incompatible), or None (inconclusive).

    Only rejects when BOTH ratios are finite and clearly outside 2x of each
    other. If either ratio is None, returns None (inconclusive — the peak
    might just not have been detected on one channel in a particular run).
    """
    if ratio_a is None or ratio_b is None:
        return None

    if ratio_b == 0:
        return None

    factor = ratio_a / ratio_b
    if 0.5 <= factor <= 2.0:
        return True
    return False

# ---------------------------------------------------------------------------
# Peak matching
# ---------------------------------------------------------------------------

def _update_compound_uv_ratio(compound: Compound):
    """Recompute compound's UV ratio as median of all finite observed ratios."""
    ratios = []
    for fi in compound.area_220_by_file:
        a220 = compound.area_220_by_file.get(fi)
        a254 = compound.area_254_by_file.get(fi)
        if a220 is not None and a254 is not None and a254 > 0:
            ratios.append(a220 / a254)
    if ratios:
        compound.uv_ratio = median(ratios)


def create_compound(cid: int, peak: ChromPeak, ratio: Optional[float],
                    file_idx: int) -> Compound:
    """Create a new Compound from a seed peak."""
    c = Compound(compound_id=cid, canonical_rt=peak.rt, uv_ratio=ratio)
    c.rt_by_file[file_idx] = peak.rt
    c.area_pct_by_file[file_idx] = peak.area_pct
    c.area_220_by_file[file_idx] = peak.area_220nm
    c.area_254_by_file[file_idx] = peak.area_254nm
    c.area_pct_220_by_file[file_idx] = peak.area_pct_220nm
    c.area_pct_254_by_file[file_idx] = peak.area_pct_254nm
    # Collect ions with rank info
    for spec in peak.ms_spectra:
        for rank, mz in enumerate(spec.top_ions):
            c.all_ions.append((spec.mode, mz, rank, file_idx))
    return c


def attach_peak_to_compound(compound: Compound, peak: ChromPeak,
                            file_idx: int):
    """Add a peak's data to an existing compound."""
    compound.rt_by_file[file_idx] = peak.rt
    compound.area_pct_by_file[file_idx] = peak.area_pct
    compound.area_220_by_file[file_idx] = peak.area_220nm
    compound.area_254_by_file[file_idx] = peak.area_254nm
    compound.area_pct_220_by_file[file_idx] = peak.area_pct_220nm
    compound.area_pct_254_by_file[file_idx] = peak.area_pct_254nm
    for spec in peak.ms_spectra:
        for rank, mz in enumerate(spec.top_ions):
            compound.all_ions.append((spec.mode, mz, rank, file_idx))
    # Update running canonical RT (will be finalized later)
    _update_compound_uv_ratio(compound)


def find_and_match(peak: ChromPeak, ratio: Optional[float],
                   compounds: List[Compound], rt_tol: float,
                   used_ids: set) -> Optional[Compound]:
    """
    Find the best matching compound for a peak.
    Returns the compound or None if no match found.
    """
    candidates = []
    for compound in compounds:
        if compound.compound_id in used_ids:
            continue

        rt_delta = abs(peak.rt - compound.canonical_rt)
        if rt_delta > rt_tol:
            continue

        uv_ok = check_uv_compatibility(ratio, compound.uv_ratio)
        # If UV data available and incompatible, skip
        if uv_ok is False:
            continue

        # Score: lower is better. UV confirmation halves the score.
        score = rt_delta
        if uv_ok is True:
            score *= 0.5

        candidates.append((compound, score))

    if not candidates:
        return None

    candidates.sort(key=lambda x: x[1])
    return candidates[0][0]


def match_peaks_across_files(files: List[FileEntry],
                             rt_tol: float) -> List[Compound]:
    """
    Match peaks across all files and return a list of Compounds.
    Files must be pre-sorted chronologically.
    """
    compounds: List[Compound] = []
    next_id = 1

    for file_idx, fe in enumerate(files):
        if fe.report is None:
            continue

        peaks = fe.report.peaks
        if not peaks:
            continue

        # Compute UV ratio for each peak
        peaks_with_ratio = [(p, compute_uv_ratio(p)) for p in peaks]

        if not compounds:
            # First file with peaks — seed all compounds
            for peak, ratio in peaks_with_ratio:
                compounds.append(create_compound(next_id, peak, ratio,
                                                 file_idx))
                next_id += 1
            continue

        # Match peaks: process largest peaks first for stable matching
        sorted_peaks = sorted(peaks_with_ratio,
                              key=lambda x: x[0].area_pct or 0,
                              reverse=True)
        used_ids: set = set()

        unmatched = []
        for peak, ratio in sorted_peaks:
            match = find_and_match(peak, ratio, compounds, rt_tol, used_ids)
            if match:
                attach_peak_to_compound(match, peak, file_idx)
                used_ids.add(match.compound_id)
            else:
                unmatched.append((peak, ratio))

        # Create new compounds for unmatched peaks
        for peak, ratio in unmatched:
            compounds.append(create_compound(next_id, peak, ratio, file_idx))
            next_id += 1

    return compounds

# ---------------------------------------------------------------------------
# Post-processing
# ---------------------------------------------------------------------------

def compute_canonical_rt(compound: Compound):
    """Set canonical RT by majority vote (mode of rounded values)."""
    rt_values = list(compound.rt_by_file.values())
    if not rt_values:
        return
    rounded = [round(rt, 2) for rt in rt_values]
    counter = Counter(rounded)
    max_count = max(counter.values())
    modes = sorted(rt for rt, count in counter.items() if count == max_count)
    compound.canonical_rt = modes[0] if len(modes) == 1 else round(
        median(modes), 2)


def cluster_ions(compound: Compound, mz_tol: float, total_files: int,
                 max_ion_rank: Optional[int] = None):
    """Group ions within mz_tol, split into recurring vs other.

    Args:
        max_ion_rank: If set, exclude "other ions" whose best rank >= this
            value from the output (0-based). E.g. max_ion_rank=5 keeps only
            ions ranked 0-4 (base peak through rank 5 display).
    """
    # Separate by mode
    ions_by_mode: Dict[str, List[Tuple[float, int, int]]] = defaultdict(list)
    for mode, mz, rank, file_idx in compound.all_ions:
        ions_by_mode[mode].append((mz, rank, file_idx))

    all_clusters: List[IonCluster] = []

    for mode, ion_list in ions_by_mode.items():
        ion_list.sort(key=lambda x: x[0])  # sort by m/z

        clusters: list = []
        for mz, rank, file_idx in ion_list:
            placed = False
            for cl in clusters:
                if abs(mz - cl['center']) <= mz_tol:
                    cl['values'].append(mz)
                    cl['files'].add(file_idx)
                    cl['best_rank'] = min(cl['best_rank'], rank)
                    cl['center'] = sum(cl['values']) / len(cl['values'])
                    placed = True
                    break
            if not placed:
                clusters.append({
                    'center': mz,
                    'values': [mz],
                    'files': {file_idx},
                    'mode': mode,
                    'best_rank': rank,
                })

        for cl in clusters:
            all_clusters.append(IonCluster(
                mean_mz=round(sum(cl['values']) / len(cl['values']), 1),
                mode=cl['mode'],
                occurrences=len(cl['files']),
                best_rank=cl['best_rank'],
                mz_values=cl['values'],
            ))

    # Determine how many distinct files this compound was observed in
    files_observed = set()
    for _, _, _, fi in compound.all_ions:
        files_observed.add(fi)
    n_files_observed = len(files_observed)

    if n_files_observed <= 1:
        # Compound only in 1 file: ALL ions are canonical (no "other" bucket).
        # When there's only one observation, the recurring-vs-other distinction
        # is meaningless — the chemist needs to see all ions to identify the
        # compound.
        compound.recurring_ions = sorted(
            all_clusters,
            key=lambda c: (c.best_rank, c.mean_mz),
        )
        compound.other_ions = []
    else:
        # Split recurring (>=2 files) vs other
        compound.recurring_ions = sorted(
            [c for c in all_clusters if c.occurrences >= 2],
            key=lambda c: (-c.occurrences, c.best_rank, c.mean_mz),
        )
        other = [c for c in all_clusters if c.occurrences < 2]
        if max_ion_rank is not None:
            other = [c for c in other if c.best_rank < max_ion_rank]
        compound.other_ions = sorted(
            other,
            key=lambda c: (c.best_rank, c.mean_mz),
        )


def _best_area_pct(compound: Compound, fi: int) -> Optional[float]:
    """Return the best available area% for a compound in a given file.
    Prefers TAC, falls back to 220nm, then 254nm."""
    area = compound.area_pct_by_file.get(fi)
    if area is not None:
        return area
    area = compound.area_pct_220_by_file.get(fi)
    if area is not None:
        return area
    return compound.area_pct_254_by_file.get(fi)


def compute_trend(compound: Compound, total_files: int,
                  threshold: float, excluded_files: set = None):
    """
    Determine area% trend: increasing / decreasing / stable.

    For files where the compound is NOT observed but which fall between
    (or after) files where it IS observed, treat area as 0%.  This
    correctly marks consumed compounds as "decreasing" and newly formed
    compounds as "increasing".  Excluded (outlier) files are skipped.
    """
    if excluded_files is None:
        excluded_files = set()

    # Build the full timeline across ALL non-excluded files
    seen_files = set(compound.area_pct_by_file.keys()) - excluded_files
    if not seen_files:
        compound.trend = "stable"
        compound.trend_detail = "no area data"
        return

    first_seen = min(seen_files)
    last_seen = max(seen_files)

    # Only one observation → can't determine trend
    observed = []
    for fi in sorted(seen_files):
        area = _best_area_pct(compound, fi)
        if area is not None:
            observed.append((fi, area))
    if len(observed) < 1:
        compound.trend = "stable"
        compound.trend_detail = "no area data"
        return

    # Always set max_area from observed data (even with a single file,
    # so that downstream consumers like procedure_writer can filter on it)
    compound.max_area = max(a for _, a in observed)

    if len(observed) == 1 and first_seen == last_seen:
        compound.trend = "stable"
        compound.trend_detail = "single observation"
        return

    # Build complete timeline: for files between first_seen and the
    # last non-excluded file, fill in 0% where compound is absent
    last_file_idx = max(i for i in range(total_files)
                        if i not in excluded_files)
    timeline = []
    for fi in range(total_files):
        if fi in excluded_files:
            continue
        if fi < first_seen:
            # Compound not yet appeared — treat as 0%
            timeline.append((fi, 0.0))
        elif fi in compound.area_pct_by_file:
            area = _best_area_pct(compound, fi)
            timeline.append((fi, area if area is not None else 0.0))
        else:
            # File exists but compound not detected — 0%
            timeline.append((fi, 0.0))

    if len(timeline) < 2:
        compound.trend = "stable"
        compound.trend_detail = "single observation"
        return

    first_area = timeline[0][1]
    last_area = timeline[-1][1]
    max_area = max(a for _, a in timeline)

    compound.max_area = max_area

    if max_area < 0.5:
        compound.trend = "stable"
        compound.trend_detail = "trace levels throughout"
        return

    change = (last_area - first_area) / max_area

    if change > threshold:
        compound.trend = "increasing"
    elif change < -threshold:
        compound.trend = "decreasing"
    else:
        compound.trend = "stable"

    # Determine which detector was used
    det_label = _trend_detector_label(compound)

    compound.trend_detail = (
        f"{first_area:.1f}% \u2192 {last_area:.1f}% "
        f"({det_label}, max {max_area:.1f}%, change {change:+.0%})"
    )


def _trend_detector_label(compound: Compound) -> str:
    """Return which detector is primarily used for this compound's trend."""
    has_tac = any(v is not None
                  for v in compound.area_pct_by_file.values())
    if has_tac:
        return "TAC"
    has_220 = any(v is not None
                  for v in compound.area_pct_220_by_file.values())
    if has_220:
        return "220nm"
    return "254nm"


def compute_uv_consensus(compound: Compound):
    """Deduplicate UV lambda-max across all observations."""
    pass  # UV lambda-max is populated via _collect_uv_lambda_max


def detect_outlier_files(files: List[FileEntry]) -> Tuple[set, set]:
    """
    Flag files that look like blanks/outliers or have ambiguous timing.

    Returns (outlier_set, ambiguous_set):
    - outlier_set: indices of blank/failed files (excluded from everything)
    - ambiguous_set: indices of files with uncertain timeline position
      (excluded from trend analysis only)
    """
    ambiguous = {i for i, fe in enumerate(files) if fe.ambiguous_time}

    if len(files) < 3:
        return set(), ambiguous

    peak_counts = []
    for fe in files:
        if fe.report:
            peak_counts.append(len(fe.report.peaks))
        else:
            peak_counts.append(0)

    sorted_counts = sorted(peak_counts)
    median_count = sorted_counts[len(sorted_counts) // 2]

    if median_count < 3:
        return set(), ambiguous

    excluded = set()
    for i, fe in enumerate(files):
        if fe.report is None:
            excluded.add(i)
            continue

        n_peaks = len(fe.report.peaks)

        # Heuristic 1: far fewer peaks than median
        if n_peaks < median_count * 0.4:
            excluded.add(i)
            continue

        # Heuristic 2: single dominant peak > 99% TAC area with very few
        # peaks AND the dominant peak is at very low RT (likely solvent/void).
        # Previous version (>95%, <=5 peaks) false-positived on legitimate
        # t=0 and near-complete reaction files where SM or DP dominates.
        tac_peaks = [(p.rt, p.area_pct) for p in fe.report.peaks
                     if p.area_pct is not None]
        if tac_peaks:
            dom_rt, dom_area = max(tac_peaks, key=lambda x: x[1])
            if dom_area > 99.0 and n_peaks <= 3 and dom_rt < 0.4:
                excluded.add(i)

    return excluded, ambiguous


def detect_outlier_files_conservative(
    files: List[FileEntry],
    compounds: List[Compound],
    excluded_files: set,
    significance_floor: float = 5.0,
    threshold: float = 0.5,
) -> set:
    """
    Second-pass outlier detection based on multi-species behaviour.

    After peak matching, check whether the MAJORITY of significant tracked
    compounds show anomalous area% in a given file.  One anomalous species is
    likely real chemistry (e.g. an intermediate consumed faster than expected);
    everything being off at once suggests a bad injection.

    Args:
        files:              All FileEntry objects (ordered chronologically).
        compounds:          Matched compounds from match_peaks_across_files().
        excluded_files:     Files already excluded by first-pass heuristics.
        significance_floor: Only consider compounds with max_area >= this value.
        threshold:          Fraction of significant compounds that must be
                            anomalous to flag a file (default 0.5 = majority).

    Returns:
        Set of additional file indices to exclude.
    """
    if len(files) < 4:
        return set()

    # Only consider "significant" compounds (visible in chromatogram)
    significant = [c for c in compounds if c.max_area >= significance_floor]
    if len(significant) < 2:
        return set()

    additional_outliers = set()

    for fi in range(len(files)):
        if fi in excluded_files:
            continue

        anomalous_count = 0
        evaluated_count = 0

        for compound in significant:
            # Collect area% from all non-excluded *other* files
            other_areas = []
            first_seen = min(compound.area_pct_by_file.keys(), default=fi)
            last_seen = max(compound.area_pct_by_file.keys(), default=fi)

            for other_fi in range(len(files)):
                if other_fi == fi or other_fi in excluded_files:
                    continue
                area = _best_area_pct(compound, other_fi)
                if area is not None:
                    other_areas.append(area)
                elif first_seen <= other_fi <= last_seen:
                    # Compound absent between first/last observation → 0%
                    other_areas.append(0.0)

            if len(other_areas) < 2:
                continue

            evaluated_count += 1

            # This file's area% (or 0% if compound absent)
            area_in_file = _best_area_pct(compound, fi)
            if area_in_file is None:
                if first_seen <= fi <= last_seen:
                    area_in_file = 0.0
                else:
                    continue  # compound not expected in this file

            # Check if this file's value is anomalous.
            # "Anomalous" = area deviates from the mean of other files by
            # more than 80% of the max observed area across other files.
            mean_other = sum(other_areas) / len(other_areas)
            max_other = max(other_areas) if other_areas else 1.0
            if max_other < 1.0:
                continue  # trace compound, skip

            deviation = abs(area_in_file - mean_other)
            if deviation > max_other * 0.8:
                anomalous_count += 1

        if evaluated_count >= 2 and anomalous_count / evaluated_count > threshold:
            additional_outliers.add(fi)

    return additional_outliers


# ---------------------------------------------------------------------------
# Output formatters
# ---------------------------------------------------------------------------

def _file_label(fe: FileEntry) -> str:
    """Short display name for a file (strip .pdf, strip common prefix)."""
    return os.path.splitext(fe.filename)[0]


def format_text_report(result: AnalysisResult,
                       min_summary_area: float = 2.0,
                       hide_other_ions: bool = False) -> str:
    """Render the full text report."""
    lines = []
    sep = "=" * 62

    # Header
    lines.append(sep)
    lines.append("MULTI-LCMS ANALYSIS")
    lines.append(sep)
    lines.append("")
    lines.append(f"Instrument: {result.instrument}")
    lines.append(f"Method:     {result.method_short}")
    lines.append("")
    lines.append(f"Files analyzed ({len(result.files)}):")
    for i, fe in enumerate(result.files):
        flags = []
        if i in result.excluded_files:
            flags.append("EXCLUDED")
        if i in result.ambiguous_files:
            flags.append("ambiguous timing")
        flag_str = f"  ** {' | '.join(flags)} **" if flags else ""
        dt_str = f"  ({fe.run_datetime})" if fe.run_datetime else ""
        lines.append(
            f"  [{i + 1}] {fe.filename:<45s} {fe.category:<14s}"
            f"{dt_str}{flag_str}"
        )
    lines.append("")

    # ---- REACTION SUMMARY (at top) ----
    lines.append(sep)
    lines.append("REACTION SUMMARY")
    lines.append(sep)
    lines.append("")

    # Sort each trend group by max observed area (descending)
    # and filter out compounds below the min_summary_area threshold
    def _above_threshold(c: Compound) -> bool:
        return c.max_area >= min_summary_area

    increasing = sorted(
        [c for c in result.compounds
         if c.trend == "increasing" and _above_threshold(c)],
        key=lambda c: c.max_area, reverse=True)
    decreasing = sorted(
        [c for c in result.compounds
         if c.trend == "decreasing" and _above_threshold(c)],
        key=lambda c: c.max_area, reverse=True)
    stable = sorted(
        [c for c in result.compounds
         if c.trend == "stable" and _above_threshold(c)],
        key=lambda c: c.max_area, reverse=True)
    hidden = [c for c in result.compounds if not _above_threshold(c)]

    n_files = len(result.files)

    def _summary_line(c: Compound) -> str:
        """Format one compound line for the summary."""
        parts = [f"  Compound {c.compound_id} \u2014 "
                 f"RT {c.canonical_rt:.2f} \u2014 {c.trend_detail}"]
        # Append recurring ions (compact)
        if c.recurring_ions:
            ions_str = ", ".join(
                f"{ic.mode} {ic.mean_mz:.1f}"
                for ic in c.recurring_ions[:4]  # limit to top 4
            )
            if len(c.recurring_ions) > 4:
                ions_str += f" (+{len(c.recurring_ions) - 4} more)"
            parts.append(f"    Ions: {ions_str}")
        return "\n".join(parts)

    if increasing:
        lines.append("Increasing (likely product / intermediate):")
        for c in increasing:
            lines.append(_summary_line(c))
        lines.append("")

    if decreasing:
        lines.append("Decreasing (likely starting material / consumed):")
        for c in decreasing:
            lines.append(_summary_line(c))
        lines.append("")

    if stable:
        lines.append("Stable:")
        for c in stable:
            lines.append(_summary_line(c))
        lines.append("")

    if hidden:
        lines.append(f"({len(hidden)} minor compound(s) below "
                     f"{min_summary_area:.0f}% max area not shown "
                     f"in summary — see details below)")
        lines.append("")

    # Warnings
    if result.warnings:
        lines.append("Warnings:")
        for w in result.warnings:
            lines.append(f"  - {w}")
        lines.append("")

    # ---- DETAILED COMPOUND SECTIONS ----
    lines.append(sep)
    lines.append("COMPOUND DETAILS")
    lines.append(sep)

    for compound in result.compounds:
        lines.append("")
        lines.append("-" * 62)
        lines.append(
            f"Compound {compound.compound_id} \u2014 "
            f"RT {compound.canonical_rt:.2f} min ({compound.trend})"
        )
        lines.append("-" * 62)

        # Trend detail
        lines.append(f"  Trend:     {compound.trend_detail}")

        # UV ratio
        if compound.uv_ratio is not None:
            if compound.uv_ratio == float('inf'):
                lines.append("  220:254:   220nm only (no 254nm absorption)")
            else:
                lines.append(f"  220:254:   {compound.uv_ratio:.2f}")

        # UV lambda-max
        if compound.uv_lambda_max:
            import math
            wl_str = ", ".join(
                str(math.floor(w + 0.5)) for w in compound.uv_lambda_max)
            lines.append(f"  UV \u03bbmax:   {wl_str} nm")

        # Recurring ions
        if compound.recurring_ions:
            lines.append("")
            lines.append("  Recurring ions:")
            for ic in compound.recurring_ions:
                rank_label = ("base peak" if ic.best_rank == 0
                              else f"rank {ic.best_rank + 1}")
                lines.append(
                    f"    {ic.mode} {ic.mean_mz:.1f} "
                    f"(seen in {ic.occurrences}/{n_files} files, "
                    f"{rank_label})"
                )

        # Other ions (single-observation; hidden with --hide-other-ions)
        if not hide_other_ions and compound.other_ions:
            lines.append("")
            lines.append("  Other ions:")
            for ic in compound.other_ions:
                rank_label = ("base peak" if ic.best_rank == 0
                              else f"rank {ic.best_rank + 1}")
                lines.append(
                    f"    {ic.mode} {ic.mean_mz:.1f} "
                    f"(seen in {ic.occurrences} file, {rank_label})"
                )

        # Area% timeline
        lines.append("")
        lines.append("  Area% timeline:")
        for fi in range(n_files):
            fe = result.files[fi]
            flags = []
            if fi in result.excluded_files:
                flags.append("EXCLUDED")
            if fi in result.ambiguous_files:
                flags.append("ambiguous timing")
            excl = f" **{'|'.join(flags)}**" if flags else ""
            if fi in compound.area_pct_by_file:
                tac = compound.area_pct_by_file[fi]
                rt = compound.rt_by_file.get(fi)
                a220 = compound.area_pct_220_by_file.get(fi)
                a254 = compound.area_pct_254_by_file.get(fi)
                det_parts = []
                if tac is not None:
                    det_parts.append(f"TAC {tac:.1f}%")
                if a220 is not None:
                    det_parts.append(f"220nm {a220:.1f}%")
                if a254 is not None:
                    det_parts.append(f"254nm {a254:.1f}%")
                det_str = ", ".join(det_parts) if det_parts else "no data"
                rt_str = f"RT {rt:.2f}" if rt is not None else ""
                lines.append(
                    f"    [{fi + 1}] {_file_label(fe):<40s} "
                    f"{rt_str}  {det_str}{excl}"
                )
            else:
                lines.append(
                    f"    [{fi + 1}] {_file_label(fe):<40s} "
                    f"        (not detected){excl}"
                )
        lines.append("")

    return "\n".join(lines)


def format_json_report(result: AnalysisResult) -> str:
    """Render structured JSON output."""
    data = {
        "instrument": result.instrument,
        "method_short": result.method_short,
        "files": [],
        "compounds": [],
        "summary": {"increasing": [], "decreasing": [], "stable": []},
        "warnings": result.warnings,
    }

    for i, fe in enumerate(result.files):
        fd = {
            "index": i,
            "filename": fe.filename,
            "category": fe.category,
            "sort_key": fe.sort_key,
        }
        if fe.report:
            fd["sample_name"] = fe.report.sample_name
            fd["date"] = fe.report.date
        data["files"].append(fd)

    for c in result.compounds:
        cd = {
            "compound_id": c.compound_id,
            "canonical_rt": c.canonical_rt,
            "uv_ratio": c.uv_ratio if c.uv_ratio != float('inf') else "inf",
            "trend": c.trend,
            "trend_detail": c.trend_detail,
            "max_area": c.max_area,
            "uv_lambda_max": c.uv_lambda_max,
            "recurring_ions": [
                {"mean_mz": ic.mean_mz, "mode": ic.mode,
                 "occurrences": ic.occurrences, "best_rank": ic.best_rank}
                for ic in c.recurring_ions
            ],
            "other_ions": [
                {"mean_mz": ic.mean_mz, "mode": ic.mode,
                 "occurrences": ic.occurrences, "best_rank": ic.best_rank}
                for ic in c.other_ions
            ],
            "timeline": [],
        }
        for fi in sorted(c.area_pct_by_file.keys()):
            entry = {
                "file_index": fi,
                "rt": c.rt_by_file.get(fi),
                "area_pct": c.area_pct_by_file.get(fi),
                "area_220": c.area_220_by_file.get(fi),
                "area_254": c.area_254_by_file.get(fi),
                "area_pct_220": c.area_pct_220_by_file.get(fi),
                "area_pct_254": c.area_pct_254_by_file.get(fi),
            }
            cd["timeline"].append(entry)
        data["compounds"].append(cd)

        # Summary
        data["summary"][c.trend].append(c.compound_id)

    return json.dumps(data, indent=2, ensure_ascii=False)


def load_analysis_from_json(json_path: str) -> AnalysisResult:
    """Reconstruct an AnalysisResult from a JSON file produced by format_json_report().

    This allows downstream tools (e.g. procedure_writer) to reuse pre-computed
    multi-LCMS analysis without re-parsing the original PDFs.
    """
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    files = []
    for fd in data.get("files", []):
        fe = FileEntry(
            path="",
            filename=fd["filename"],
            category=fd["category"],
            sort_key=fd.get("sort_key", 0),
        )
        files.append(fe)

    compounds = []
    for cd in data.get("compounds", []):
        c = Compound(
            compound_id=cd["compound_id"],
            canonical_rt=cd.get("canonical_rt", 0.0),
        )
        uv_ratio = cd.get("uv_ratio")
        if uv_ratio == "inf":
            c.uv_ratio = float("inf")
        elif uv_ratio is not None:
            c.uv_ratio = uv_ratio
        c.trend = cd.get("trend", "stable")
        c.trend_detail = cd.get("trend_detail", "")
        c.max_area = cd.get("max_area", 0.0)
        c.uv_lambda_max = cd.get("uv_lambda_max", [])

        for ic_data in cd.get("recurring_ions", []):
            c.recurring_ions.append(IonCluster(
                mean_mz=ic_data["mean_mz"],
                mode=ic_data["mode"],
                occurrences=ic_data.get("occurrences", 1),
                best_rank=ic_data.get("best_rank", 0),
            ))
        for ic_data in cd.get("other_ions", []):
            c.other_ions.append(IonCluster(
                mean_mz=ic_data["mean_mz"],
                mode=ic_data["mode"],
                occurrences=ic_data.get("occurrences", 1),
                best_rank=ic_data.get("best_rank", 0),
            ))

        for te in cd.get("timeline", []):
            fi = te["file_index"]
            if te.get("rt") is not None:
                c.rt_by_file[fi] = te["rt"]
            if te.get("area_pct") is not None:
                c.area_pct_by_file[fi] = te["area_pct"]
            if te.get("area_220") is not None:
                c.area_220_by_file[fi] = te["area_220"]
            if te.get("area_254") is not None:
                c.area_254_by_file[fi] = te["area_254"]
            if te.get("area_pct_220") is not None:
                c.area_pct_220_by_file[fi] = te["area_pct_220"]
            if te.get("area_pct_254") is not None:
                c.area_pct_254_by_file[fi] = te["area_pct_254"]

        compounds.append(c)

    return AnalysisResult(
        instrument=data.get("instrument", "Unknown"),
        method_short=data.get("method_short", "Unknown"),
        files=files,
        compounds=compounds,
        warnings=data.get("warnings", []),
    )


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def analyze(files: List[FileEntry], rt_tol: float, mz_tol: float,
            trend_threshold: float,
            ignore_instrument: bool,
            use_run_time: bool = True,
            max_ion_rank: Optional[int] = None,
            pick_biggest_group: bool = False) -> List[AnalysisResult]:
    """
    Top-level analysis.  Groups files by (instrument, method) and runs
    peak matching within each group.

    Args:
        pick_biggest_group: When True and multiple (instrument, method) groups
            exist, only analyze the largest group — discard the rest.  Used by
            the procedure_writer pipeline where cross-method comparison is not
            meaningful.  When False (default / CLI), analyze each group
            separately and return one AnalysisResult per group.
    """
    warnings: List[str] = []
    discarded_all: List[FileEntry] = []

    # Filter to files that parsed successfully
    valid = [f for f in files if f.report is not None]
    if not valid:
        return []

    # --- Group by (instrument, method) ---
    if ignore_instrument:
        # Legacy mode: ignore instrument but still respect method
        groups: Dict[str, List[FileEntry]] = defaultdict(list)
        for f in valid:
            meth = method_basename(f.report.method_path)
            groups[f"all|{meth}"].append(f)
        # If all files share the same method, simplify key to "all"
        if len(groups) == 1:
            key = next(iter(groups))
            groups = {"all": groups[key]}
    else:
        groups = defaultdict(list)
        for f in valid:
            inst = f.report.instrument
            meth = method_basename(f.report.method_path)
            groups[f"{inst}|{meth}"].append(f)

    if len(groups) > 1:
        group_summaries = []
        for k, v in sorted(groups.items(), key=lambda x: -len(x[1])):
            parts = k.split("|", 1)
            inst_part = parts[0]
            meth_part = parts[1] if len(parts) > 1 else "?"
            # Use method_short for human-readable display
            meth_display = v[0].report.method_short if v[0].report else meth_part
            group_summaries.append(
                f"{inst_part}/{meth_display} ({len(v)} files)")
        warnings.append(
            f"Files from {len(groups)} (instrument, method) groups: "
            + ", ".join(group_summaries) + "."
        )

        if pick_biggest_group:
            biggest_key = max(groups, key=lambda k: len(groups[k]))
            for k, v in list(groups.items()):
                if k != biggest_key:
                    discarded_all.extend(v)
                    disc_names = ", ".join(f.filename for f in v)
                    warnings.append(
                        f"Discarded {len(v)} file(s) from non-primary group "
                        f"({k}): {disc_names}."
                    )
            groups = {biggest_key: groups[biggest_key]}

    results = []
    for inst_key, group_files in groups.items():
        method_warn = []

        # Sort by sort_key — this is the single source of truth for ordering.
        # For Group 1 tracking files this is filename-derived (chemist controls
        # submission order).  For Group 2+ it may be recalibrated to actual
        # acquisition timestamps by the caller (lcms_identifier.py).
        group_files.sort(key=lambda f: f.sort_key)

        # Detect outlier / blank files and ambiguous-time files
        outliers, ambiguous = detect_outlier_files(group_files)
        # For trend analysis, exclude both outliers and ambiguous-time files
        trend_excluded = outliers | ambiguous
        if outliers:
            excl_names = [group_files[i].filename
                          for i in sorted(outliers)]
            method_warn.append(
                f"Excluded {len(outliers)} file(s) as likely "
                f"blank/outlier: {', '.join(excl_names)}."
            )
        if ambiguous:
            amb_names = [group_files[i].filename
                         for i in sorted(ambiguous)]
            method_warn.append(
                f"Excluded {len(ambiguous)} file(s) with ambiguous "
                f"timing from trend analysis: {', '.join(amb_names)}."
            )

        # Match peaks (uses all files for matching, even excluded ones)
        compounds = match_peaks_across_files(group_files, rt_tol)

        # Post-process — compute canonical RT, UV, ions BEFORE outlier 2nd pass
        for compound in compounds:
            compute_canonical_rt(compound)
            _update_compound_uv_ratio(compound)
            cluster_ions(compound, mz_tol, len(group_files),
                         max_ion_rank=max_ion_rank)

        # Conservative second-pass outlier detection: flag files where MOST
        # significant compounds deviate from their expected behaviour.
        conservative = detect_outlier_files_conservative(
            group_files, compounds, outliers)
        if conservative:
            cons_names = [group_files[i].filename
                          for i in sorted(conservative)]
            method_warn.append(
                f"Post-match outlier detection flagged "
                f"{len(conservative)} additional file(s) where majority "
                f"of compounds deviate: {', '.join(cons_names)}."
            )
            outliers = outliers | conservative
            trend_excluded = outliers | ambiguous

        # Compute trends with final exclusion set
        for compound in compounds:
            compute_trend(compound, len(group_files), trend_threshold,
                          excluded_files=trend_excluded)
            _collect_uv_lambda_max(compound, group_files)

        # Sort compounds by canonical RT
        compounds.sort(key=lambda c: c.canonical_rt)
        # Re-number for clean display
        for i, c in enumerate(compounds, 1):
            c.compound_id = i

        first_report = group_files[0].report
        meth_key = method_basename(
            first_report.method_path) if first_report else ""
        result = AnalysisResult(
            instrument=first_report.instrument if first_report else "Unknown",
            method_short=first_report.method_short if first_report else "Unknown",
            method_key=meth_key,
            files=group_files,
            compounds=compounds,
            warnings=warnings + method_warn,
            excluded_files=outliers,
            ambiguous_files=ambiguous,
            discarded_files=discarded_all,
        )
        results.append(result)

    return results


def _collect_uv_lambda_max(compound: Compound, files: List[FileEntry]):
    """Collect and deduplicate UV lambda-max values from matched peaks."""
    all_wl: List[float] = []
    for fi, fe in enumerate(files):
        if fi not in compound.rt_by_file or fe.report is None:
            continue
        # Find the peak in this file that was matched
        target_rt = compound.rt_by_file[fi]
        for peak in fe.report.peaks:
            if abs(peak.rt - target_rt) < 0.01:
                all_wl.extend(peak.uv_lambda_max)
                break

    # Deduplicate: group within 10nm, take mean of each cluster
    if not all_wl:
        compound.uv_lambda_max = []
        return
    all_wl.sort()
    clusters: List[List[float]] = [[all_wl[0]]]
    for wl in all_wl[1:]:
        if wl - clusters[-1][-1] <= 10:
            clusters[-1].append(wl)
        else:
            clusters.append([wl])
    compound.uv_lambda_max = [
        sum(c) / len(c) for c in clusters
    ]

# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Multi-LCMS Analyzer \u2014 collate peaks across "
                    "multiple LCMS files from the same reaction.\n"
                    "By default, files are sorted by their actual LCMS "
                    "acquisition time (extracted from PDF). Use "
                    "--out-of-order if samples were run non-chronologically.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument('files', nargs='+',
                        help='MassLynx PDF report files')
    parser.add_argument('--rt-tolerance', type=float, default=LCMS_RT_TOLERANCE,
                        help='RT matching tolerance in minutes (default: %(default)s)')
    parser.add_argument('--mz-tolerance', type=float, default=LCMS_MZ_TOLERANCE,
                        help='m/z clustering tolerance in Da (default: %(default)s)')
    parser.add_argument('--trend-threshold', type=float, default=LCMS_TREND_THRESHOLD,
                        help='Trend change threshold as fraction '
                             '(default: %(default)s)')
    parser.add_argument('--ignore-instrument', action='store_true',
                        help='Analyze all files together regardless of '
                             'instrument')
    parser.add_argument('--out-of-order', action='store_true',
                        help='Use filename-heuristic sorting instead of '
                             'actual LCMS run time. Use this when samples '
                             'were not run in chronological order. Files '
                             'with ambiguous timing (e.g. "beforeadd") '
                             'will be excluded from trend analysis.')
    parser.add_argument('--min-summary-area', type=float, default=LCMS_MIN_SUMMARY_AREA,
                        help='Hide compounds below this max area%% from '
                             'the reaction summary (default: %(default)s)')
    parser.add_argument('--max-ion-rank', type=int, default=None,
                        help='Filter out "other ions" with rank >= this value '
                             '(0-based). E.g. --max-ion-rank 5 keeps only '
                             'ions ranked 1-5 in display. Default: no filter')
    parser.add_argument('--hide-other-ions', action='store_true',
                        help='Hide single-observation "other ions" from '
                             'compound details (shown by default)')
    parser.add_argument('--output', '-o', type=str, default=None,
                        help='Output file path (default: stdout)')
    parser.add_argument('--json', action='store_true',
                        help='Output as structured JSON')
    parser.add_argument('--json-output', type=str, default=None,
                        help='Save structured JSON to this file (in addition '
                             'to the normal text output)')
    parser.add_argument('--json-errors', action='store_true',
                        help='Output structured JSON error objects to stderr '
                             'on failure (for agent orchestration)')

    args = parser.parse_args(argv)

    use_run_time = not args.out_of_order

    # Filter out non-standard PDFs (manually integrated chromatograms etc.)
    valid_files = []
    for path in args.files:
        if not is_waters_report(path):
            print(f"  Skipping non-standard PDF: {os.path.basename(path)}",
                  file=sys.stderr)
        else:
            valid_files.append(path)

    # Parse all reports
    file_entries: List[FileEntry] = []
    for path in valid_files:
        filename = os.path.basename(path)
        category, sort_key = categorize_lcms_file(filename)
        ambiguous = sort_key in _AMBIGUOUS_SORT_KEYS
        try:
            report = parse_report(path)
            # Always try to extract run datetime (shown in output)
            run_dt = extract_run_datetime(path)
            fe = FileEntry(
                path=os.path.abspath(path),
                filename=filename,
                category=category,
                sort_key=sort_key,
                report=report,
                run_datetime=run_dt,
                # Only flag ambiguous when NOT using run time for sorting
                ambiguous_time=ambiguous and not use_run_time,
            )
            file_entries.append(fe)
            dt_info = f", run={run_dt}" if run_dt else ""
            amb_info = " [ambiguous]" if fe.ambiguous_time else ""
            print(f"  Parsed: {filename} ({len(report.peaks)} peaks, "
                  f"{category}, sort={sort_key}{dt_info}{amb_info})",
                  file=sys.stderr)
        except Exception as e:
            print(f"  Warning: Could not parse {filename}: {e}",
                  file=sys.stderr)

    if not file_entries:
        msg = "No files could be parsed."
        if args.json_errors:
            _je = {"error": "no_parseable_files", "detail": msg}
            print(json.dumps(_je), file=sys.stderr)
        else:
            print(f"Error: {msg}", file=sys.stderr)
        return 1

    # Single file — no cross-file analysis needed, output basic report
    if len(file_entries) == 1:
        print("  Single file — outputting basic report (no multi-file "
              "analysis).", file=sys.stderr)
        output = format_basic_report(file_entries[0].report)
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(output)
            print(f"Output written to {args.output}", file=sys.stderr)
        else:
            sys.stdout.buffer.write(output.encode('utf-8'))
            sys.stdout.buffer.write(b'\n')
        return 0

    # Sort chronologically — by run_datetime (default) or sort_key (--out-of-order)
    if use_run_time:
        # All files with a valid run_datetime sort by that; others fall back
        has_dt = all(fe.run_datetime is not None for fe in file_entries)
        if has_dt:
            file_entries.sort(key=lambda f: f.run_datetime)
            print("  Sorting by LCMS run time (default).", file=sys.stderr)
        else:
            missing = [fe.filename for fe in file_entries
                       if fe.run_datetime is None]
            print(f"  Warning: Could not extract run time from: "
                  f"{', '.join(missing)}. Falling back to filename sort.",
                  file=sys.stderr)
            file_entries.sort(key=lambda f: f.sort_key)
    else:
        file_entries.sort(key=lambda f: f.sort_key)
        print("  Sorting by filename heuristics (--out-of-order).",
              file=sys.stderr)

    # Analyze
    results = analyze(file_entries, args.rt_tolerance, args.mz_tolerance,
                      args.trend_threshold, args.ignore_instrument,
                      use_run_time=use_run_time,
                      max_ion_rank=args.max_ion_rank)

    if not results:
        msg = "Analysis produced no results."
        if args.json_errors:
            _je = {"error": "analysis_empty", "detail": msg}
            print(json.dumps(_je), file=sys.stderr)
        else:
            print(f"Error: {msg}", file=sys.stderr)
        return 1

    # Save JSON sidecar if requested (for downstream reuse by procedure_writer)
    if args.json_output:
        json_parts = [format_json_report(r) for r in results]
        json_out = "[" + ", ".join(json_parts) + "]" \
            if len(json_parts) > 1 else json_parts[0]
        with open(args.json_output, 'w', encoding='utf-8') as f:
            f.write(json_out)
        print(f"JSON saved to {args.json_output}", file=sys.stderr)

    # Check if exclusions reduced any group to ≤1 effective file
    # If so, fall back to basic single-file reports for those files
    output_parts = []
    for result in results:
        effective_count = len(result.files) - len(result.excluded_files)
        if effective_count <= 1 and not args.json:
            # Exclusions left ≤1 file — output basic report(s) instead
            print(f"  {len(result.excluded_files)} of {len(result.files)} "
                  f"files excluded — falling back to single-file report(s).",
                  file=sys.stderr)
            for i, fe in enumerate(result.files):
                if i not in result.excluded_files and fe.report:
                    output_parts.append(format_basic_report(fe.report))
        elif args.json:
            output_parts.append(format_json_report(result))
        else:
            output_parts.append(format_text_report(
                result,
                min_summary_area=args.min_summary_area,
                hide_other_ions=args.hide_other_ions,
            ))

    output = "\n\n".join(output_parts)

    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(output)
        print(f"Output written to {args.output}", file=sys.stderr)
    else:
        sys.stdout.buffer.write(output.encode('utf-8'))
        sys.stdout.buffer.write(b'\n')

    return 0


if __name__ == '__main__':
    sys.exit(main())
