#!/usr/bin/env python3
"""
Lab Book Formatter — Output Section Generation for Procedure Writer

Builds the three sections of a lab book entry:
  PROCEDURE — setup text, tracking narrative, workup, purification, isolation
  CHARACTERIZATION — LCMS annotations (tracking + purified) + NMR data
  NOTES — conversion timeline, unidentified compounds, diagnostics

Also contains formatting helpers for LCMS method names, purity reporting,
UV lambda-max values, and narrative inference from LCMS filenames.

Usage:
    from lab_book_formatter import (
        build_procedure_section, build_characterization_section,
        build_notes_section, assemble_output,
    )
"""

import math
import os
import re
import sys
from typing import List, Optional, Dict

from cdxml_toolkit.constants import MIN_REPORT_AREA_PCT
from .mass_resolver import ExpectedSpecies
from .lcms_identifier import (
    IdentifiedCompound, IdentifiedPeak,
    TrackingAnalysis, PurifiedAnalysis,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SECTION_SEP = "=" * 60

# ---------------------------------------------------------------------------
# Method formatting
# ---------------------------------------------------------------------------

def format_method_name(method_path: str) -> str:
    """Extract short method name like 'AmF 2 min' from method path."""
    basename = os.path.basename(method_path).replace('.olp', '')
    parts = basename.split('_')

    buffer_type = ""
    runtime = ""

    for p in parts:
        pl = p.lower()
        if 'amf' in pl:
            buffer_type = "AmF"
        elif 'amb' in pl or 'ambic' in pl:
            buffer_type = "AmB"
        elif pl == 'fa':
            buffer_type = "FA"
        elif 'tfa' in pl:
            buffer_type = "TFA"

        if 'min' in pl:
            time_str = pl.replace('min', '').replace('p', '.')
            try:
                time_val = float(time_str)
                runtime = f"{round(time_val)} min"
            except ValueError:
                runtime = p

    pieces = [x for x in [buffer_type, runtime] if x]
    return " ".join(pieces) if pieces else basename

# ---------------------------------------------------------------------------
# Tracking narrative helpers
# ---------------------------------------------------------------------------

def _infer_event_from_filename(filename: str) -> Optional[str]:
    """Infer a reaction event from an LCMS filename suffix."""
    name = filename.lower()

    # Additional reagent addition
    m = re.search(r'add\s*(\d+)\s*mg\s*(\w+)', name)
    if m:
        amount = m.group(1)
        reagent = m.group(2).upper()
        return f"Additional {reagent} ({amount} mg) was added"

    if 'addmore' in name:
        return "Additional reagent was added"

    # Quenching
    m = re.search(r'(\d+)\s*ml\s*me', name)
    if m:
        return f"The reaction was quenched with MeOH ({m.group(1)} mL)"

    return None


def _infer_timepoint_desc(filename: str) -> str:
    """Extract a timepoint description from filename for narrative use."""
    name = filename.lower()

    # Remove experiment prefix and extension
    base = os.path.splitext(os.path.basename(name))[0]

    # Extract time patterns
    m = re.search(r'(\d+)\s*min', base)
    if m:
        if 'premix' in base:
            return f"after {m.group(1)} min premixing"
        return f"after {m.group(1)} min"

    m = re.search(r'(\d+)\s*h\b', base)
    if m:
        return f"after {m.group(1)} h"

    if re.search(r'\bON\b', os.path.basename(filename)) or 'overnight' in name:
        return "after overnight stirring"

    if 'beforeadd' in name:
        return "before adding more reagent"

    if 'premix' in name:
        return "after premixing"

    return ""


def _timepoint_for_file(files, file_index: int) -> str:
    """Get timepoint description for a file by index."""
    if file_index < len(files):
        return _infer_timepoint_desc(files[file_index].filename)
    return ""


def build_tracking_narrative(exp, tracking: TrackingAnalysis) -> str:
    """
    Build a concise reaction monitoring narrative from multi-LCMS data.

    Uses identified compound trends and area% timelines to produce
    a paragraph summarizing the conversion story.
    """
    if not tracking.result or not tracking.identified:
        return ""

    # Find SM and product compounds
    sm_ic = None
    dp_ic = None
    for ic in tracking.identified:
        if ic.species.role == "substrate":
            sm_ic = ic
        elif ic.species.role == "product":
            dp_ic = ic

    if not sm_ic and not dp_ic:
        return ""

    events = []
    files = tracking.result.files

    # Check for reagent addition events from filenames
    for lf in exp.lcms_files:
        if lf.category == "tracking":
            event = _infer_event_from_filename(lf.filename)
            if event:
                events.append(event + ".")
                break  # Only report first addition

    # Compute conversion at each timepoint from area% data
    sm_areas = sm_ic.compound.area_pct_by_file if sm_ic else {}
    dp_areas = dp_ic.compound.area_pct_by_file if dp_ic else {}

    prev_conversion = None
    reported_complete = False

    for fi in range(len(files)):
        fe = files[fi]
        is_premix = 'premix' in fe.filename.lower()
        tp = _infer_timepoint_desc(fe.filename)

        sm_area = sm_areas.get(fi)
        dp_area = dp_areas.get(fi)

        # Compute conversion if both SM and DP are tracked
        if sm_ic and dp_ic:
            sa = sm_area if sm_area is not None else 0
            da = dp_area if dp_area is not None else 0
            total = sa + da
            conversion = (da / total * 100) if total > 1.0 else None
        elif sm_ic and sm_area is not None:
            # No product identified — track SM consumption
            conversion = 100 - sm_area if sm_area < 95 else None
        else:
            conversion = None

        if is_premix or conversion is None:
            continue

        if prev_conversion is None:
            if conversion > 0 and tp:
                if conversion >= 95:
                    events.append(
                        f"LCMS {tp} indicated complete consumption "
                        f"of starting material.")
                    reported_complete = True
                else:
                    events.append(
                        f"LCMS {tp} indicated ~{conversion:.0f}% "
                        f"conversion.")
        else:
            delta = conversion - prev_conversion
            if conversion >= 95 and not reported_complete:
                events.append(
                    f"LCMS {tp} indicated complete consumption "
                    f"of starting material.")
                reported_complete = True
            elif reported_complete:
                pass
            elif abs(delta) < 5:
                if not any('did not improve' in e for e in events):
                    events.append(
                        f"Conversion did not improve {tp} "
                        f"(~{conversion:.0f}%).")
            elif delta > 10:
                events.append(
                    f"LCMS {tp} showed ~{conversion:.0f}% conversion.")

        prev_conversion = conversion

    if not events:
        # Fallback: report trends
        parts = []
        if sm_ic:
            parts.append(f"SM {sm_ic.compound.trend}")
        if dp_ic:
            parts.append(f"DP {dp_ic.compound.trend}")
        if parts:
            return "LCMS tracking: " + ", ".join(parts) + "."
        return ""

    return " ".join(events)


# ---------------------------------------------------------------------------
# Workup / purification inference
# ---------------------------------------------------------------------------

def _infer_workup_steps(exp) -> List[str]:
    """Infer workup steps from LCMS filenames."""
    steps = []
    seen = set()

    for lf in exp.lcms_files:
        name = lf.filename.lower()

        if 'eawash' in name and 'ea_wash' not in seen:
            steps.append("washed with EtOAc")
            seen.add('ea_wash')
        elif 'dcmwash' in name and 'dcm_wash' not in seen:
            steps.append("washed with DCM")
            seen.add('dcm_wash')
        elif 'wash' in name and 'rewash' not in name and 'wash' not in seen:
            steps.append("washed")
            seen.add('wash')
        elif 'rewash' in name and 'rewash' not in seen:
            steps.append("re-washed")
            seen.add('rewash')
        elif 'pellet' in name and 'pellet' not in seen:
            steps.append("precipitate collected")
            seen.add('pellet')
        elif 'super' in name and 'super' not in seen:
            steps.append("supernatant separated")
            seen.add('super')

    return steps


def _infer_purification(exp) -> Optional[str]:
    """Infer purification method from LCMS filenames."""
    names = [lf.filename.lower() for lf in exp.lcms_files]
    all_names = " ".join(names)

    methods = []
    if 'nppurif' in all_names or 'np-' in all_names:
        methods.append("normal phase column chromatography")
    if 'c18' in all_names:
        methods.append("reversed phase (C18) column chromatography")
    if 'peakcomb' in all_names:
        methods.append("fractions combined based on LCMS")

    has_purified = any('purified' in n or 'pure' in n for n in names)

    if methods:
        return "Purified by " + " followed by ".join(methods) + "."
    elif has_purified:
        return "Purified (method not specified in LCMS filenames)."

    return None

# ---------------------------------------------------------------------------
# Procedure section
# ---------------------------------------------------------------------------

def _strip_nmr_from_procedure(text: str) -> str:
    """Remove NMR data strings from procedure text.

    NMR data (e.g. '1H NMR (400 MHz, DMSO-d6) δ ...') belongs in
    CHARACTERIZATION, not PROCEDURE.  If the ELN CSV procedure text
    contains NMR data, strip it out to avoid duplication.
    """
    # Pattern matches "1H NMR (...) δ ..." through to the end of the data
    # (terminated by a period + whitespace/newline, or end of string)
    nmr_pattern = re.compile(
        r'\d+[A-Z]\s+NMR\s*\([^)]+\)\s*[\u03b4\u00b4d]\s*.+?'
        r'(?=\.\s*(?:\d+[A-Z]\s+NMR|\n|$)|\Z)',
        re.DOTALL
    )
    cleaned = nmr_pattern.sub('', text)
    # Clean up leftover whitespace / blank lines from removal
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
    return cleaned.strip()


def _procedure_has_tracking(text: str) -> bool:
    keywords = ['lcms', 'tracking', 'conversion', 'consumption of sm',
                'reaction complete', 'indicated', 'lc-ms']
    tl = text.lower()
    return any(kw in tl for kw in keywords)


def _procedure_has_workup(text: str) -> bool:
    keywords = ['was concentrated', 'was quenched', 'was washed',
                'was extracted', 'aqueous', 'was dried', 'workup']
    tl = text.lower()
    return any(kw in tl for kw in keywords)


def _procedure_has_isolation(text: str) -> bool:
    keywords = ['was purified', 'to give', 'to afford',
                'column chromatography', 'chromatography', 'purified by']
    tl = text.lower()
    return any(kw in tl for kw in keywords)


def build_procedure_section(exp, tracking: TrackingAnalysis) -> str:
    """Build the complete PROCEDURE section."""
    parts = []

    # 1. Setup from CSV procedure text
    # Strip NMR data from procedure (it belongs in CHARACTERIZATION)
    setup = exp.procedure_text if exp.procedure_text else ""
    setup = _strip_nmr_from_procedure(setup) if setup else ""

    if setup:
        parts.append(setup)
    else:
        parts.append("[Procedure text not available in CSV.]")

    # 2. Reaction monitoring (only if not already in procedure text)
    if not _procedure_has_tracking(setup):
        narrative = build_tracking_narrative(exp, tracking)
        if narrative:
            parts.append(narrative)

    # 3. Workup (only if not already described)
    if not _procedure_has_workup(setup):
        workup_steps = _infer_workup_steps(exp)
        if workup_steps:
            parts.append("The reaction mixture was " +
                         ", ".join(workup_steps) + ".")

    # 4. Purification (only if not already described)
    if not _procedure_has_isolation(setup):
        purif = _infer_purification(exp)
        if purif:
            parts.append(purif)

    # 5. Product isolation
    if exp.product and not _procedure_has_isolation(setup):
        if exp.product.obtained_mass and exp.product.yield_pct:
            parts.append(
                f"Obtained {exp.product.name} "
                f"({exp.product.obtained_mass}, {exp.product.yield_pct}).")
        elif exp.product.obtained_mass:
            parts.append(
                f"Obtained {exp.product.name} "
                f"({exp.product.obtained_mass}).")

    return "\n\n".join(parts)

# ---------------------------------------------------------------------------
# Characterization section
# ---------------------------------------------------------------------------

def _format_lambda_max(wavelengths: List[float]) -> str:
    """Format UV lambda max values, e.g. 'λmax 218, 254 nm'.

    Uses arithmetic rounding (half-up) rather than Python's default
    banker's rounding, so 222.5 -> 223 not 222.
    """
    if not wavelengths:
        return ""
    wl_strs = [str(math.floor(wl + 0.5)) for wl in sorted(wavelengths)]
    return f"\u03bbmax {', '.join(wl_strs)} nm"


def _format_purity(purified: PurifiedAnalysis) -> str:
    """Format purity from all available detectors."""
    parts = []
    if purified.purity_tac is not None:
        parts.append(f"TAC {purified.purity_tac:.0f}%")
    if purified.purity_220nm is not None:
        parts.append(f"220nm {purified.purity_220nm:.0f}%")
    if purified.purity_254nm is not None:
        parts.append(f"254nm {purified.purity_254nm:.0f}%")
    if not parts:
        return ""
    return "; purity " + ", ".join(parts)


def build_characterization_section(
    exp,
    expected: List[ExpectedSpecies],
    tracking: TrackingAnalysis,
    purified: PurifiedAnalysis,
) -> str:
    """Build the CHARACTERIZATION section with LCMS and NMR data."""
    if not expected:
        return "[Expected species masses not available — cannot annotate LCMS.]"

    lines = []

    # Tracking LCMS — report identified species from multi-LCMS analysis
    # Only include compounds with max area% >= MIN_REPORT_AREA_PCT
    if tracking.result and tracking.identified:
        instrument = tracking.result.instrument
        method = tracking.result.method_short

        # Build annotation from identified compounds
        # Order: SM first, then product, then other reactants
        role_order = {"substrate": 0, "product": 1, "reactant": 2}
        sorted_ic = sorted(
            tracking.identified,
            key=lambda ic: (role_order.get(ic.species.role, 3),
                            ic.compound.canonical_rt))

        parts = []
        for ic in sorted_ic:
            if ic.compound.max_area < MIN_REPORT_AREA_PCT:
                continue
            entry = (f"{ic.species.name} RT {ic.compound.canonical_rt:.2f}, "
                     f"{ic.adduct} {ic.matched_mz:.1f}")
            lm = _format_lambda_max(ic.compound.uv_lambda_max)
            if lm:
                entry += f", {lm}"
            parts.append(entry)

        if parts:
            lines.append(
                f"Reaction tracking LCMS ({instrument}, {method}): "
                + "; ".join(parts))

    # Purified/Crude product LCMS — deduplicate by species (keep highest area)
    # Only include peaks with area% >= MIN_REPORT_AREA_PCT
    _product_label = ("Crude product LCMS" if purified.is_crude_fallback
                      else "Purified product LCMS")
    if purified.report and purified.identified:
        instrument = purified.report.instrument
        method = purified.report.method_short

        best_by_species: Dict[str, IdentifiedPeak] = {}
        for ip in purified.identified:
            area = ip.peak.area_pct or 0
            if area < MIN_REPORT_AREA_PCT:
                continue
            key = ip.species.name
            if key not in best_by_species or (
                    area > (best_by_species[key].peak.area_pct or 0)):
                best_by_species[key] = ip

        parts = []
        for ip in best_by_species.values():
            entry = (f"{ip.species.name} RT {ip.peak.rt:.2f}, "
                     f"{ip.adduct} {ip.matched_mz:.1f}")
            lm = _format_lambda_max(ip.peak.uv_lambda_max)
            if lm:
                entry += f", {lm}"
            parts.append(entry)

        purity_str = _format_purity(purified)

        if parts:
            lines.append(
                f"{_product_label} ({instrument}, {method}): "
                + "; ".join(parts) + purity_str)

    elif purified.report and not purified.identified:
        # No species identified by mass spec — report dominant peak's purity
        # and UV data if the main peak is large enough (likely purified product)
        instrument = purified.report.instrument
        method = purified.report.method_short

        # Find the dominant peak (highest TAC area%)
        best_peak = None
        best_area = 0.0
        for peak in purified.report.peaks:
            area = peak.area_pct or 0
            if area > best_area:
                best_area = area
                best_peak = peak

        if best_peak and best_area >= MIN_REPORT_AREA_PCT:
            entry = f"RT {best_peak.rt:.2f}"
            lm = _format_lambda_max(best_peak.uv_lambda_max)
            if lm:
                entry += f", {lm}"

            # Build purity from the dominant peak directly
            purity_parts = []
            if best_peak.area_pct is not None:
                purity_parts.append(f"TAC {best_peak.area_pct:.0f}%")
            if best_peak.area_pct_220nm is not None:
                purity_parts.append(f"220nm {best_peak.area_pct_220nm:.0f}%")
            if best_peak.area_pct_254nm is not None:
                purity_parts.append(f"254nm {best_peak.area_pct_254nm:.0f}%")
            purity_str = ("; purity " + ", ".join(purity_parts)
                          if purity_parts else "")

            lines.append(
                f"{_product_label} ({instrument}, {method}): "
                f"{entry}{purity_str} [no MS data]")

    # NMR data
    for nmr_str in exp.nmr_data:
        lines.append(nmr_str)

    if not lines:
        return "[No characterization data available.]"

    return "\n\n".join(lines)

# ---------------------------------------------------------------------------
# Notes section
# ---------------------------------------------------------------------------

def build_notes_section(
    exp,
    expected: List[ExpectedSpecies],
    tracking: TrackingAnalysis,
    purified: PurifiedAnalysis,
) -> str:
    """Build the NOTES section with observations and inferences."""
    notes = []

    # Conversion timeline from multi-LCMS tracking data
    if tracking.result and tracking.identified:
        sm_ic = next((ic for ic in tracking.identified
                      if ic.species.role == "substrate"), None)
        dp_ic = next((ic for ic in tracking.identified
                      if ic.species.role == "product"), None)

        if sm_ic or dp_ic:
            for fi, fe in enumerate(tracking.result.files):
                sm_area = (sm_ic.compound.area_pct_by_file.get(fi)
                           if sm_ic else None)
                dp_area = (dp_ic.compound.area_pct_by_file.get(fi)
                           if dp_ic else None)

                # Compute conversion%: 1 - SM/(SM+DP)
                conv_str = None
                if sm_area is not None and dp_area is not None:
                    total = sm_area + dp_area
                    if total > 0:
                        conv = (1.0 - sm_area / total) * 100
                        conv_str = f"conversion {conv:.0f}%"
                elif sm_area is not None and dp_area is None:
                    # No product detected yet
                    conv_str = "conversion 0%"
                elif dp_area is not None and sm_area is None:
                    # No SM detected — full conversion
                    conv_str = "conversion 100%"

                tp = _infer_timepoint_desc(fe.filename)
                if conv_str is not None:
                    notes.append(f"- {fe.filename}: {conv_str}"
                                 f"{' ' + tp if tp else ''}")

    # Unidentified compounds in tracking (only significant ones)
    if tracking.unidentified:
        for c in tracking.unidentified:
            if c.max_area >= MIN_REPORT_AREA_PCT:
                ions_strs = []
                for ic in (c.recurring_ions or c.other_ions)[:3]:
                    mode_str = "ESI+" if ic.mode == "ES+" else "ESI-"
                    ions_strs.append(f"{mode_str} {ic.mean_mz:.1f}")
                ions_str = ", ".join(ions_strs) if ions_strs else "no ions"
                notes.append(
                    f"- Unidentified compound RT {c.canonical_rt:.2f} "
                    f"({c.trend}, max {c.max_area:.1f}%): {ions_str}")

    # Unknown peaks in purified product
    if purified.report and purified.identified:
        identified_rts = {ip.peak.rt for ip in purified.identified}
        for peak in purified.report.peaks:
            if peak.rt not in identified_rts and (peak.area_pct or 0) > 1.0:
                ions_strs = []
                for spec in peak.ms_spectra:
                    if spec.top_ions:
                        mode_str = "ESI+" if spec.mode == "ES+" else "ESI-"
                        ions_strs.append(f"{mode_str} {spec.top_ions[0]:.1f}")
                ions_str = ", ".join(ions_strs) if ions_strs else "no MS"
                _product_type = "crude product" if purified.is_crude_fallback else "purified product"
                notes.append(
                    f"- Unknown peak in {_product_type}: RT {peak.rt:.2f}, "
                    f"{peak.area_pct:.1f}% ({ions_str})")

    # Purified product LCMS source file
    if purified.file_info:
        _product_label = ("Crude product LCMS" if purified.is_crude_fallback
                          else "Purified product LCMS")
        notes.append(f"- {_product_label}: {purified.file_info.filename}")

    # Species source — check if masses came from structure or CSV
    source_files = {sp.source_file for sp in expected if sp.source_file}
    if source_files:
        source = next(iter(source_files))
        notes.append(f"- Expected masses from structure file "
                     f"({os.path.basename(source)})")
    elif expected:
        notes.append("- Expected masses from CSV MW (no CDX/RXN available)")

    # Analysis warnings (method mismatches, outliers, discarded files)
    if tracking.result and tracking.result.warnings:
        for w in tracking.result.warnings:
            notes.append(f"- LCMS analysis: {w}")
    if tracking.result and tracking.result.discarded_files:
        disc_names = [f.filename for f in tracking.result.discarded_files]
        notes.append(
            f"- {len(disc_names)} LCMS file(s) from different instrument/method "
            f"excluded from tracking: {', '.join(disc_names)}")

    # File categorization summary
    categories = {}
    for lf in exp.lcms_files:
        categories.setdefault(lf.category, []).append(lf.filename)
    if categories:
        notes.append(f"- LCMS files: {len(exp.lcms_files)} total "
                     f"({', '.join(f'{len(v)} {k}' for k, v in categories.items())})")

    # Missing data flags
    if not exp.procedure_text:
        notes.append("- Procedure text was empty")
    if not exp.lcms_files:
        notes.append("- No LCMS files found")
    if not exp.nmr_pdfs:
        notes.append("- No NMR PDFs found")
    elif not exp.nmr_data:
        notes.append("- NMR PDFs present but no reported data string found "
                     "— needs manual extraction")
    if exp.product and not exp.product.obtained_mass:
        notes.append("- Yield/mass obtained not recorded in CSV")
    if not expected:
        notes.append("- No expected species masses available")

    return "\n".join(notes) if notes else "No notes."

# ---------------------------------------------------------------------------
# Output assembly
# ---------------------------------------------------------------------------

def assemble_output(procedure: str, characterization: str,
                    notes: str) -> str:
    """Assemble the three sections into final output."""
    parts = [
        SECTION_SEP,
        "PROCEDURE",
        SECTION_SEP,
        "",
        procedure,
        "",
        SECTION_SEP,
        "CHARACTERIZATION",
        SECTION_SEP,
        "",
        characterization,
        "",
        SECTION_SEP,
        "NOTES",
        SECTION_SEP,
        "",
        notes,
    ]
    return "\n".join(parts)

# ---------------------------------------------------------------------------
# CLI placeholder
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("lab_book_formatter: no standalone CLI — "
          "import from procedure_writer.py")
