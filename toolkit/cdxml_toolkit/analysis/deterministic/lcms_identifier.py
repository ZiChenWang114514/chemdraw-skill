#!/usr/bin/env python3
"""
LCMS Identifier — Species Identification from Ion m/z Values

Matches observed LCMS ions against expected species adducts to identify
compounds in tracking and purified-product chromatograms.  Handles both
multi-file tracking analysis (via multi_lcms_analyzer) and single-file
purified product analysis.

Key types:
  - IdentifiedCompound: a multi-LCMS compound matched to an expected species
  - IdentifiedPeak: a single-report peak matched to an expected species
  - TrackingAnalysis: wrapper for multi-LCMS tracking results
  - PurifiedAnalysis: wrapper for purified product LCMS results

Usage:
    from lcms_identifier import (
        match_ions_to_species, run_tracking_analysis, run_purified_analysis,
    )
"""

import os
import sys
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from ..lcms_analyzer import parse_report, LCMSReport, ChromPeak
from .lcms_file_categorizer import (
    categorize_lcms_files_batch,
    calibrate_sort_keys_hybrid,
)
from .multi_lcms_analyzer import (
    FileEntry as MultiFileEntry,
    analyze as multi_analyze,
    AnalysisResult,
    Compound as MultiCompound,
    IonCluster,
    extract_run_datetime,
    load_analysis_from_json,
)
from cdxml_toolkit.constants import MASS_TOLERANCE
from .mass_resolver import (
    ExpectedSpecies,
    ADDUCTS, ADDUCT_PRIORITY, MODE_PREFERENCE,
)

# Role-based priority: SM/DP preferred over reactants, which beat byproducts.
# Lower number = preferred.
ROLE_PRIORITY = {
    "substrate": 0,
    "product": 0,
    "reactant": 1,
    "reagent": 1,
    "byproduct": 2,
}

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class IdentifiedCompound:
    """A multi-LCMS compound matched to an expected species."""
    compound: MultiCompound
    species: ExpectedSpecies
    adduct: str          # e.g. "[M+H]+"
    matched_mz: float    # observed m/z that matched

@dataclass
class TrackingAnalysis:
    """Results of multi-LCMS tracking analysis with species identification."""
    result: Optional[AnalysisResult] = None
    identified: List[IdentifiedCompound] = field(default_factory=list)
    unidentified: List[MultiCompound] = field(default_factory=list)
    files: List[MultiFileEntry] = field(default_factory=list)

@dataclass
class IdentifiedPeak:
    """A single-report chromatographic peak matched to an expected species."""
    peak: ChromPeak
    species: ExpectedSpecies
    adduct: str
    matched_mz: float

@dataclass
class PurifiedAnalysis:
    """Results of purified product LCMS analysis."""
    report: Optional[LCMSReport] = None
    file_info: Optional[object] = None
    identified: List[IdentifiedPeak] = field(default_factory=list)
    # Per-detector purity of the product peak (None = not detected)
    purity_tac: Optional[float] = None
    purity_220nm: Optional[float] = None
    purity_254nm: Optional[float] = None
    # True when no "final" file was found and a workup file was used instead
    is_crude_fallback: bool = False

# ---------------------------------------------------------------------------
# Ion matching
# ---------------------------------------------------------------------------

def match_ions_to_species(
    ions: List[Tuple[str, float, int]],
    expected: List[ExpectedSpecies],
    tolerance: float = MASS_TOLERANCE,
) -> Optional[Tuple[ExpectedSpecies, str, float]]:
    """
    Match observed ions against expected species adducts.

    Candidate matches are ranked by:
      1. Adduct priority — [M+H]+/[M-H]- preferred over [M+Na]+/[M+formate]-
      2. Role priority — SM/DP preferred over reactants, over byproducts
      3. Ion rank — lower rank = more intense = preferred
      4. ESI mode — ESI+ preferred over ESI- (tiebreaker)
      5. Mass accuracy — closer delta preferred (final tiebreaker)

    Args:
        ions: list of (mode, m/z, rank) tuples.
              rank 0 = base peak (most intense).
        expected: list of ExpectedSpecies with computed adducts
        tolerance: matching tolerance in Da

    Returns:
        (species, adduct_name, matched_mz) or None
    """
    candidates = []

    for obs_mode, obs_mz, obs_rank in ions:
        for species in expected:
            for adduct_name, expected_mz in species.adducts.items():
                adduct_mode = ADDUCTS[adduct_name][0]
                if obs_mode != adduct_mode:
                    continue
                delta = abs(obs_mz - expected_mz)
                if delta < tolerance:
                    candidates.append((
                        ADDUCT_PRIORITY[adduct_name],   # 0=primary, 1=secondary
                        ROLE_PRIORITY.get(species.role, 1),  # 0=SM/DP, 2=byproduct
                        obs_rank,                       # 0=base peak
                        MODE_PREFERENCE.get(obs_mode, 1),  # 0=ES+, 1=ES-
                        delta,                          # mass accuracy
                        species, adduct_name, obs_mz,
                    ))

    if not candidates:
        return None

    candidates.sort(key=lambda c: c[:5])
    best = candidates[0]
    return (best[5], best[6], best[7])


def _try_assign_species(match, used_species):
    """Assign a matched species, with isomer fallback for products.

    When a compound's ions match a product species (e.g. "DP") that has
    already been assigned to a larger peak, this creates a "{name}-isomer"
    variant instead of dropping the compound to unidentified.  Handles
    regioisomeric / diastereomeric products that share the same exact mass.

    Args:
        match: result from match_ions_to_species(), or None
        used_species: set of already-assigned species names (modified in-place)

    Returns:
        (species, adduct, mz) if assigned, or None
    """
    if match is None:
        return None

    species, adduct, mz = match

    if species.name not in used_species:
        used_species.add(species.name)
        return (species, adduct, mz)

    # Isomer fallback for products
    if species.role == "product":
        isomer_name = f"{species.name}-isomer"
        if isomer_name not in used_species:
            isomer_sp = ExpectedSpecies(
                name=isomer_name,
                role=species.role,
                exact_mass=species.exact_mass,
                smiles=species.smiles,
                adducts=dict(species.adducts),
                source_file=species.source_file,
            )
            used_species.add(isomer_name)
            return (isomer_sp, adduct, mz)

    return None


# ---------------------------------------------------------------------------
# Tracking LCMS analysis (via multi_lcms_analyzer)
# ---------------------------------------------------------------------------

def _run_single_file_tracking(
    lf,
    expected: List[ExpectedSpecies],
) -> TrackingAnalysis:
    """
    Analyze a single tracking LCMS file without multi_lcms_analyzer.

    Parses the report, matches peaks to expected species, and wraps results
    in TrackingAnalysis-compatible structures.  No cross-file trending or
    ion-recurrence filtering — those require multiple files.
    """
    try:
        report = parse_report(lf.path)
        lf.report = report
        print(f"  Parsed tracking: {lf.filename} "
              f"({len(report.peaks)} peaks)", file=sys.stderr)
    except Exception as e:
        print(f"  Warning: Could not parse {lf.filename}: {e}",
              file=sys.stderr)
        return TrackingAnalysis()

    # Build FileEntry for compatibility with notes builder
    fe = MultiFileEntry(
        path=os.path.abspath(lf.path),
        filename=lf.filename,
        category=lf.category,
        sort_key=lf.sort_key,
        report=report,
    )

    # Match peaks to expected species (same approach as purified analysis)
    identified = []
    unidentified_compounds = []
    used_species = set()
    next_id = 1

    # Sort peaks by area descending — match larger peaks first
    sorted_peaks = sorted(report.peaks,
                          key=lambda p: p.area_pct or 0, reverse=True)

    for peak in sorted_peaks:
        # Build ions list from peak's mass spectra
        ions = []
        for spec in peak.ms_spectra:
            for rank, mz in enumerate(spec.top_ions):
                ions.append((spec.mode, mz, rank))

        # Build a MultiCompound wrapper for this peak
        mc = MultiCompound(compound_id=next_id, canonical_rt=peak.rt)
        mc.max_area = peak.area_pct or 0.0
        mc.uv_lambda_max = list(peak.uv_lambda_max) if peak.uv_lambda_max else []
        mc.trend = "stable"
        mc.trend_detail = "single file"
        # area maps keyed by file index (only index 0 for single file)
        if peak.area_pct is not None:
            mc.area_pct_by_file[0] = peak.area_pct
        if peak.area_pct_220nm is not None:
            mc.area_pct_220_by_file[0] = peak.area_pct_220nm
        if peak.area_pct_254nm is not None:
            mc.area_pct_254_by_file[0] = peak.area_pct_254nm
        next_id += 1

        match = match_ions_to_species(ions, expected)
        assigned = _try_assign_species(match, used_species)
        if assigned:
            species, adduct, mz = assigned
            identified.append(IdentifiedCompound(
                compound=mc, species=species, adduct=adduct, matched_mz=mz,
            ))
        else:
            unidentified_compounds.append(mc)

    # Build AnalysisResult for compatibility with characterization builder
    all_compounds = [ic.compound for ic in identified] + unidentified_compounds
    result = AnalysisResult(
        instrument=report.instrument or "Unknown",
        method_short=report.method_short or "Unknown",
        files=[fe],
        compounds=all_compounds,
    )

    return TrackingAnalysis(
        result=result,
        identified=identified,
        unidentified=unidentified_compounds,
        files=[fe],
    )


def _cross_validate_method(file_entries: List[MultiFileEntry]) -> List[str]:
    """
    Cross-validate filename method modifier (e.g. -AmB) against the actual
    PDF method path.  Returns a list of warning strings for mismatches.
    """
    warnings = []
    for fe in file_entries:
        if not fe.method_variant or not fe.report:
            continue
        pdf_method = fe.report.method_path.lower()
        # Map modifier to the substring expected in the method path
        variant = fe.method_variant.lower()
        # Strip 'foc' suffix — "-AmBfoc" still means buffer is AmB
        core_variant = variant.replace('foc', '')
        if core_variant and core_variant not in pdf_method:
            warnings.append(
                f"Method mismatch: {fe.filename} has filename modifier "
                f"'-{fe.method_variant}' but PDF method is "
                f"'{os.path.basename(fe.report.method_path)}'"
            )
    return warnings


def run_tracking_analysis(
    exp,
    expected: List[ExpectedSpecies],
) -> TrackingAnalysis:
    """
    Analyze tracking LCMS files and identify compounds.

    Single file  → direct parse + ion matching (no multi_lcms_analyzer).
    Multiple files → multi_lcms_analyzer for cross-file compound tracking.

    Groups files by (instrument, method) and picks the largest group.
    Uses hybrid sort keys: filename tokens for group 1, PDF acquisition
    timestamps for groups 2+.
    """
    tracking_files = [lf for lf in exp.lcms_files if lf.category == "tracking"]

    if not tracking_files:
        return TrackingAnalysis()

    if len(tracking_files) == 1:
        return _run_single_file_tracking(tracking_files[0], expected)

    # --- Multiple tracking files: use multi_lcms_analyzer ---
    file_entries = []
    for lf in tracking_files:
        try:
            report = parse_report(lf.path)
            run_dt = extract_run_datetime(lf.path)
            fe = MultiFileEntry(
                path=os.path.abspath(lf.path),
                filename=lf.filename,
                category=lf.category,
                sort_key=lf.sort_key,
                report=report,
                run_datetime=run_dt,
                group_prefix=getattr(lf, 'group_prefix', None),
                method_variant=getattr(lf, 'method_variant', None),
            )
            file_entries.append(fe)
            print(f"  Parsed tracking: {lf.filename} "
                  f"({len(report.peaks)} peaks)", file=sys.stderr)
        except Exception as e:
            print(f"  Warning: Could not parse {lf.filename}: {e}",
                  file=sys.stderr)

    if not file_entries:
        return TrackingAnalysis(files=file_entries)

    if len(file_entries) == 1:
        # Only one file parsed successfully — fall back to single-file
        lf = tracking_files[0]
        lf.report = file_entries[0].report
        return _run_single_file_tracking(lf, expected)

    # --- Hybrid sort key recalibration ---
    # Recalibrate groups 2+ using real PDF acquisition timestamps.
    # Group 1 keeps filename-derived sort keys (chemist controls submission
    # order at the start of a reaction).
    #
    # Recover the tracking group info from the batch categorizer.
    # We need it to know which files belong to which prefix-group.
    tracking_filenames = [lf.filename for lf in tracking_files]
    batch = categorize_lcms_files_batch(
        tracking_filenames,
        exp.experiment_name if hasattr(exp, 'experiment_name') else "")

    if batch.tracking_groups and len(batch.tracking_groups) > 1:
        run_dts = {fe.filename: fe.run_datetime
                   for fe in file_entries if fe.run_datetime}
        if run_dts:
            calibrate_sort_keys_hybrid(
                batch.tracking_groups, batch, run_dts)
            # Update FileEntry sort_keys from recalibrated batch result
            for fe in file_entries:
                fc = batch.files.get(fe.filename)
                if fc is not None:
                    fe.sort_key = fc.sort_key

    # --- Method cross-validation ---
    method_warnings = _cross_validate_method(file_entries)

    # --- Run multi-LCMS analysis ---
    # Group by (instrument, method); pick only the biggest group.
    results = multi_analyze(
        files=file_entries,
        rt_tol=0.02,
        mz_tol=0.5,
        trend_threshold=0.2,
        ignore_instrument=False,
        use_run_time=False,           # sort_key is now the single source of truth
        pick_biggest_group=True,
    )

    if not results:
        return TrackingAnalysis(files=file_entries)

    # Take the (now single) result from the biggest group
    analysis = results[0]

    # Append method cross-validation warnings
    if method_warnings:
        analysis.warnings.extend(method_warnings)

    # Match compounds to expected species
    identified = []
    unidentified = []
    used_species = set()

    # Sort compounds by max_area descending (match larger compounds first)
    sorted_compounds = sorted(
        analysis.compounds, key=lambda c: c.max_area, reverse=True)

    for compound in sorted_compounds:
        # Collect all ions as (mode, mz, rank) tuples — recurring first
        ions = []
        for ic in compound.recurring_ions:
            ions.append((ic.mode, ic.mean_mz, ic.best_rank))
        for ic in compound.other_ions:
            ions.append((ic.mode, ic.mean_mz, ic.best_rank))

        match = match_ions_to_species(ions, expected)
        assigned = _try_assign_species(match, used_species)
        if assigned:
            species, adduct, mz = assigned
            identified.append(IdentifiedCompound(
                compound=compound,
                species=species,
                adduct=adduct,
                matched_mz=mz,
            ))
        else:
            unidentified.append(compound)

    return TrackingAnalysis(
        result=analysis,
        identified=identified,
        unidentified=unidentified,
        files=file_entries,
    )


def run_tracking_from_result(
    analysis: AnalysisResult,
    expected: List[ExpectedSpecies],
) -> TrackingAnalysis:
    """
    Identify compounds in a pre-computed AnalysisResult.

    Same species-matching logic as run_tracking_analysis(), but skips PDF
    parsing and multi_analyze() — accepts an already-computed result
    (e.g. loaded from JSON via load_analysis_from_json()).
    """
    identified = []
    unidentified = []
    used_species = set()

    sorted_compounds = sorted(
        analysis.compounds, key=lambda c: c.max_area, reverse=True)

    for compound in sorted_compounds:
        ions = []
        for ic in compound.recurring_ions:
            ions.append((ic.mode, ic.mean_mz, ic.best_rank))
        for ic in compound.other_ions:
            ions.append((ic.mode, ic.mean_mz, ic.best_rank))

        match = match_ions_to_species(ions, expected)
        assigned = _try_assign_species(match, used_species)
        if assigned:
            species, adduct, mz = assigned
            identified.append(IdentifiedCompound(
                compound=compound,
                species=species,
                adduct=adduct,
                matched_mz=mz,
            ))
        else:
            unidentified.append(compound)

    return TrackingAnalysis(
        result=analysis,
        identified=identified,
        unidentified=unidentified,
        files=analysis.files,
    )


# ---------------------------------------------------------------------------
# Purified product LCMS analysis
# ---------------------------------------------------------------------------

def run_purified_analysis(
    exp,
    expected: List[ExpectedSpecies],
) -> PurifiedAnalysis:
    """Parse and analyze the purified product LCMS file.

    Selection order:
    1. Files categorized as "final" (e.g. NPpurified, C18-purified)
    2. Fallback: last workup file chronologically (e.g. crude, wash)
    """
    final_files = [lf for lf in exp.lcms_files if lf.category == "final"]
    crude_fallback = False

    if not final_files:
        # Fallback: use the chronologically last workup file
        workup_files = [lf for lf in exp.lcms_files
                        if lf.category == "workup"]
        if workup_files:
            crude_fallback = True
            # Sort by actual LCMS run datetime (preferred) then sort_key
            for wf in workup_files:
                wf._run_dt = extract_run_datetime(wf.path)
            # Files with run_datetime sort after those without; among
            # those with datetime, latest wins; ties break by sort_key.
            workup_files.sort(
                key=lambda f: (f._run_dt or "", f.sort_key))
            lf = workup_files[-1]
            print(f"  No purified-product LCMS file found — "
                  f"using last workup file: {lf.filename}"
                  f"{' (run ' + lf._run_dt + ')' if lf._run_dt else ''}",
                  file=sys.stderr)
        else:
            return PurifiedAnalysis()
    else:
        # Use the last final file (most relevant)
        lf = final_files[-1]
    try:
        report = parse_report(lf.path)
        lf.report = report
        print(f"  Parsed purified: {lf.filename} "
              f"({len(report.peaks)} peaks)", file=sys.stderr)
    except Exception as e:
        print(f"  Warning: Could not parse {lf.filename}: {e}",
              file=sys.stderr)
        return PurifiedAnalysis(file_info=lf)

    # Match peaks to expected species
    identified = []
    for peak in report.peaks:
        # Build ions list from peak's mass spectra (with rank)
        ions = []
        for spec in peak.ms_spectra:
            for rank, mz in enumerate(spec.top_ions):
                ions.append((spec.mode, mz, rank))

        match = match_ions_to_species(ions, expected)
        if match:
            species, adduct, mz = match
            identified.append(IdentifiedPeak(
                peak=peak, species=species, adduct=adduct, matched_mz=mz,
            ))

    # Product purity: area% of the product peak on each detector.
    # If multiple peaks match the product, use the highest-area one.
    purity_tac = None
    purity_220 = None
    purity_254 = None
    for ip in identified:
        if ip.species.role == "product":
            if ip.peak.area_pct is not None and (
                    purity_tac is None or ip.peak.area_pct > purity_tac):
                purity_tac = ip.peak.area_pct
            if ip.peak.area_pct_220nm is not None and (
                    purity_220 is None or ip.peak.area_pct_220nm > purity_220):
                purity_220 = ip.peak.area_pct_220nm
            if ip.peak.area_pct_254nm is not None and (
                    purity_254 is None or ip.peak.area_pct_254nm > purity_254):
                purity_254 = ip.peak.area_pct_254nm

    return PurifiedAnalysis(
        report=report,
        file_info=lf,
        identified=identified,
        purity_tac=purity_tac,
        purity_220nm=purity_220,
        purity_254nm=purity_254,
        is_crude_fallback=crude_fallback,
    )


# ---------------------------------------------------------------------------
# CLI placeholder
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("lcms_identifier: no standalone CLI — "
          "import from procedure_writer.py or use directly")
