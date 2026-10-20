#!/usr/bin/env python3
"""
Procedure Writer — Lab Book Entry Assembler

Takes LCMS PDFs, NMR PDFs, ELN CSV exports, and CDX/RXN structure files for
a single reaction and outputs a polished, copy-paste-ready lab book entry with
three sections:
  PROCEDURE — concise, publication-quality procedure text
  CHARACTERIZATION — LCMS annotations + NMR data
  NOTES — rough observations and inferences

Expected masses for LCMS identification are derived from CDX/RXN structure
files (via ChemScript + RDKit), with fallback to CSV MW values.  Tracking
LCMS analysis is delegated to multi_lcms_analyzer for cross-file compound
matching, trend detection, and area% timelines.

Usage:
    python procedure_writer.py --input-dir path/to/experiment/ --output result.txt
    python procedure_writer.py --input-dir path/to/parent/ --experiment KL-7001-004
    python procedure_writer.py --input-dir path/to/parent/ --experiment KL-7001-004 \\
        --sm-mass 274 --product-mass 459 --output result.txt
"""

import argparse
import json
import os
import re
import sys
from typing import List, Optional, Dict

# --- LCMS tools ---
from ..lcms_analyzer import extract_all_text
from cdxml_toolkit.constants import MIN_SIGNIFICANT_AREA

# --- Mass resolution (split out to mass_resolver.py) ---
from .mass_resolver import (
    ExpectedSpecies,
    extract_expected_masses,
    ADDUCTS, ADDUCT_PRIORITY, MODE_PREFERENCE,
)

# --- LCMS identification (split out to lcms_identifier.py) ---
from .lcms_identifier import (
    IdentifiedCompound, TrackingAnalysis, IdentifiedPeak, PurifiedAnalysis,
    match_ions_to_species, run_tracking_analysis, run_purified_analysis,
    run_tracking_from_result,
)
from .multi_lcms_analyzer import load_analysis_from_json

# --- Output formatting (split out to lab_book_formatter.py) ---
from .lab_book_formatter import (
    SECTION_SEP,
    format_method_name,
    build_procedure_section, build_tracking_narrative,
    build_characterization_section, build_notes_section,
    assemble_output,
)

from .discover_experiment_files import (
    discover_experiment_files,
    DiscoveryResult,
)

# ---------------------------------------------------------------------------
# Data structures & CSV parser — imported from package
# ---------------------------------------------------------------------------

from cdxml_toolkit.perception.eln_csv_parser import (
    ReagentInfo, SolventInfo, ProductInfo, LCMSFileInfo, ExperimentData,
    strip_html, extract_procedure_body, parse_eln_csv,
)

# ---------------------------------------------------------------------------
# File discovery (delegates to discover_experiment_files.py)
# ---------------------------------------------------------------------------

def discover_files(input_dir: str,
                   experiment_name: Optional[str] = None) -> ExperimentData:
    """
    Discover all files for an experiment.

    Delegates file discovery to discover_experiment_files module, then
    parses the CSV and populates an ExperimentData with the results.
    """
    # Run the standalone discovery
    discovery = discover_experiment_files(input_dir, experiment_name)

    # Parse CSV if found
    exp = None
    if discovery.csv_files:
        exp = parse_eln_csv(discovery.csv_files[0])

    if not exp:
        exp = ExperimentData(
            experiment_name=discovery.experiment,
            labbook_name='', procedure_html='', procedure_text='',
            reaction_type='', start_date='',
        )

    # CDX / RXN — take first of each
    if discovery.cdx_files:
        exp.cdx_path = discovery.cdx_files[0]
    if discovery.rxn_files:
        exp.rxn_path = discovery.rxn_files[0]

    # LCMS files
    for lf in discovery.lcms_files:
        exp.lcms_files.append(LCMSFileInfo(
            path=lf.path,
            filename=os.path.basename(lf.path),
            category=lf.category,
            sort_key=lf.sort_key,
            group_prefix=lf.group_prefix,
            method_variant=lf.method_variant,
        ))

    # NMR PDFs
    exp.nmr_pdfs = list(discovery.nmr_files)

    return exp

# ---------------------------------------------------------------------------
# NMR extraction
# ---------------------------------------------------------------------------

def extract_nmr_data(pdf_path: str) -> List[str]:
    """
    Extract reported NMR data strings from an NMR PDF.

    Searches for patterns like:
        1H NMR (400 MHz, DMSO-d6) delta ...
        13C NMR (101 MHz, DMSO-d6) delta ...
        19F NMR (376 MHz, DMSO-d6) delta ...
    """
    try:
        text = extract_all_text(pdf_path)
    except Exception as e:
        print(f"Warning: Could not read NMR PDF {pdf_path}: {e}",
              file=sys.stderr)
        return []

    results = []

    # Pattern for NMR data strings
    # Match: "1H NMR" or "13C NMR" or "19F NMR" etc., followed by the data
    # The data string continues until a period followed by newline, or
    # until a non-NMR line is encountered.
    nmr_pattern = re.compile(
        r'(\d+[A-Z]\s+NMR\s*'       # nucleus: 1H, 13C, 19F, etc.
        r'\([^)]+\)\s*'              # (400 MHz, solvent)
        r'[\u03b4\u00b4d]\s*'        # delta or delta symbol
        r'.+?)(?=\.\s*$|\.\s*\d+[A-Z]\s+NMR|\Z)',  # capture until end
        re.MULTILINE | re.DOTALL
    )

    seen = set()
    for m in nmr_pattern.finditer(text):
        data_str = m.group(1).strip()
        # Clean up: normalize whitespace, remove line breaks within data
        data_str = re.sub(r'\s+', ' ', data_str)
        # Ensure it ends with a period
        if not data_str.endswith('.'):
            # Find the last closing paren with H count
            last_paren = data_str.rfind(')')
            if last_paren > 0:
                data_str = data_str[:last_paren + 1] + '.'
        # Deduplicate — NMR PDFs often repeat data on each page
        if data_str not in seen:
            seen.add(data_str)
            results.append(data_str)

    return results

# ---------------------------------------------------------------------------
# NMR batch parsing
# ---------------------------------------------------------------------------

def parse_all_nmr(exp: ExperimentData) -> None:
    """Extract NMR data from all NMR PDFs (with cross-file deduplication)."""
    seen = set()
    for pdf_path in exp.nmr_pdfs:
        data = extract_nmr_data(pdf_path)
        new_count = 0
        for d in data:
            if d not in seen:
                seen.add(d)
                exp.nmr_data.append(d)
                new_count += 1
        if new_count:
            print(f"  Found NMR data in {os.path.basename(pdf_path)}: "
                  f"{new_count} entries", file=sys.stderr)
        elif data:
            print(f"  NMR PDF {os.path.basename(pdf_path)}: "
                  f"data already seen (duplicate)", file=sys.stderr)
        else:
            print(f"  NMR PDF {os.path.basename(pdf_path)}: "
                  f"no reported data string found", file=sys.stderr)

# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Procedure Writer — Lab Book Entry Assembler",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("--input-dir", "-i", required=True,
                   help="Directory containing experiment files "
                        "(experiment dir or parent dir)")
    p.add_argument("--experiment", "-e", default=None,
                   help="Experiment name (e.g., KL-7001-004). "
                        "Required if input-dir is the parent directory.")
    p.add_argument("--sm-mass", type=float, default=None,
                   help="Exact mass (MW) of starting material. "
                        "Auto-detected from CSV if not provided.")
    p.add_argument("--product-mass", type=float, default=None,
                   help="Exact mass (MW) of desired product. "
                        "Auto-detected from CSV if not provided.")
    p.add_argument("--predict-byproducts", action="store_true",
                   help="Predict reaction byproducts via FlowER for LCMS "
                        "matching (requires 'flower' conda env; results "
                        "are cached)")
    p.add_argument("--flower-json", default=None,
                   help="Pre-computed FlowER byproduct predictions JSON "
                        "(from run_pipeline Phase 3.15). Adds predicted "
                        "byproducts to expected species for LCMS matching.")
    p.add_argument("--tracking-json", default=None,
                   help="Pre-computed multi-LCMS tracking analysis JSON "
                        "(from multi_lcms_analyzer --json). Skips re-parsing "
                        "tracking PDFs.")
    p.add_argument("--output", "-o", default=None,
                   help="Output file path (default: stdout)")
    p.add_argument("--json-errors", action="store_true",
                   help="Output structured JSON error objects to stderr on "
                        "failure (for agent orchestration)")
    return p


def _emit_json_error(error_code: str, detail: str,
                     file: str = None, *, stream=sys.stderr) -> None:
    """Write a structured JSON error to stderr."""
    obj = {"error": error_code, "detail": detail}
    if file:
        obj["file"] = file
    print(json.dumps(obj), file=stream)


def main(argv=None) -> int:
    parser = _build_arg_parser()
    args = parser.parse_args(argv)

    try:
        return _main_inner(args)
    except Exception as e:
        if args.json_errors:
            msg = str(e).lower()
            if "csv" in msg or "parse" in msg:
                code = "csv_parse_failed"
            elif "lcms" in msg or "pdf" in msg:
                code = "lcms_analysis_failed"
            elif "nmr" in msg:
                code = "nmr_extraction_failed"
            elif "mass" in msg or "structure" in msg:
                code = "mass_resolution_failed"
            else:
                code = "procedure_failed"
            _emit_json_error(code, str(e))
        else:
            print(f"ERROR: {e}", file=sys.stderr)
        return 1


def _main_inner(args) -> int:
    print("Procedure Writer — discovering files...", file=sys.stderr)

    # Discover files
    exp = discover_files(args.input_dir, args.experiment)

    print(f"Experiment: {exp.experiment_name}", file=sys.stderr)
    print(f"  CSV procedure: {'yes' if exp.procedure_text else 'no'}",
          file=sys.stderr)
    print(f"  Reactants: {len(exp.reactants)}", file=sys.stderr)
    print(f"  LCMS files: {len(exp.lcms_files)}", file=sys.stderr)
    print(f"  NMR PDFs: {len(exp.nmr_pdfs)}", file=sys.stderr)
    print(f"  CDX: {os.path.basename(exp.cdx_path) if exp.cdx_path else 'none'}",
          file=sys.stderr)
    print(f"  RXN: {os.path.basename(exp.rxn_path) if exp.rxn_path else 'none'}",
          file=sys.stderr)

    # Override masses from CLI if provided
    if args.sm_mass is not None:
        exp.sm_mass = args.sm_mass
    if args.product_mass is not None:
        exp.product_mass = args.product_mass

    if exp.sm_mass:
        print(f"  SM mass (CSV): {exp.sm_mass:.3f}", file=sys.stderr)
    if exp.product_mass:
        print(f"  Product mass (CSV): {exp.product_mass:.3f}", file=sys.stderr)

    # Extract expected masses from CDX/RXN (or CSV fallback)
    print("\nDetermining expected species masses...", file=sys.stderr)
    expected = extract_expected_masses(
        exp, predict_byproducts=args.predict_byproducts)

    # Load pre-computed FlowER byproduct predictions if provided
    if args.flower_json and os.path.isfile(args.flower_json):
        print(f"\nLoading FlowER predictions from "
              f"{os.path.basename(args.flower_json)}...", file=sys.stderr)
        try:
            import json as _json
            with open(args.flower_json, "r", encoding="utf-8") as f:
                flower_data = _json.load(f)
            existing_masses = [s.exact_mass for s in expected]
            from cdxml_toolkit.constants import MASS_TOLERANCE
            n_loaded = 0
            for entry in flower_data:
                em = entry.get("exact_mass", 0)
                # Skip duplicates of existing species
                if any(abs(em - m) < MASS_TOLERANCE for m in existing_masses):
                    continue
                sp = ExpectedSpecies(
                    name=entry.get("name", "BP-?"),
                    role=entry.get("role", "byproduct"),
                    exact_mass=em,
                    smiles=entry.get("smiles", ""),
                    adducts=entry.get("adducts", {}),
                    source_file=args.flower_json,
                )
                expected.append(sp)
                existing_masses.append(em)
                n_loaded += 1
            print(f"  Loaded {n_loaded} byproduct(s) from FlowER JSON",
                  file=sys.stderr)
        except Exception as e:
            print(f"  Warning: Could not load FlowER JSON: {e}",
                  file=sys.stderr)

    for sp in expected:
        mh = sp.adducts.get("[M+H]+", 0)
        mh_neg = sp.adducts.get("[M-H]-", 0)
        print(f"  {sp.name} ({sp.role}): {sp.exact_mass:.3f} Da"
              f"  [M+H]+ {mh:.1f}  [M-H]- {mh_neg:.1f}",
              file=sys.stderr)

    # Run tracking LCMS analysis (multi-LCMS)
    tracking = TrackingAnalysis()
    if args.tracking_json and os.path.isfile(args.tracking_json):
        # Use pre-computed tracking analysis (avoids re-parsing PDFs)
        print(f"\nLoading pre-computed tracking analysis from "
              f"{os.path.basename(args.tracking_json)}...", file=sys.stderr)
        analysis = load_analysis_from_json(args.tracking_json)
        print(f"  {len(analysis.compounds)} compounds, "
              f"{len(analysis.files)} files", file=sys.stderr)
        tracking = run_tracking_from_result(analysis, expected)
        for ic in tracking.identified:
            print(f"  Compound RT {ic.compound.canonical_rt:.2f} -> "
                  f"{ic.species.name} ({ic.adduct} {ic.matched_mz:.1f})",
                  file=sys.stderr)
        if tracking.unidentified:
            n_sig = sum(1 for c in tracking.unidentified if c.max_area > MIN_SIGNIFICANT_AREA)
            print(f"  {len(tracking.unidentified)} unidentified compounds "
                  f"({n_sig} with area > 2%)", file=sys.stderr)
    else:
        tracking_files = [lf for lf in exp.lcms_files
                          if lf.category == "tracking"]
        if tracking_files:
            print(f"\nRunning tracking analysis "
                  f"({len(tracking_files)} files)...", file=sys.stderr)
            tracking = run_tracking_analysis(exp, expected)
            for ic in tracking.identified:
                print(f"  Compound RT {ic.compound.canonical_rt:.2f} -> "
                      f"{ic.species.name} ({ic.adduct} {ic.matched_mz:.1f})",
                      file=sys.stderr)
            if tracking.unidentified:
                n_sig = sum(1 for c in tracking.unidentified if c.max_area > MIN_SIGNIFICANT_AREA)
                print(f"  {len(tracking.unidentified)} unidentified compounds "
                      f"({n_sig} with area > 2%)", file=sys.stderr)

    # Parse purified product LCMS (final files preferred, workup fallback)
    purified = PurifiedAnalysis()
    final_files = [lf for lf in exp.lcms_files if lf.category == "final"]
    workup_files = [lf for lf in exp.lcms_files if lf.category == "workup"]
    if final_files or workup_files:
        print(f"\nAnalyzing purified product LCMS...", file=sys.stderr)
        purified = run_purified_analysis(exp, expected)
        purity_parts = []
        if purified.purity_tac is not None:
            purity_parts.append(f"TAC {purified.purity_tac:.0f}%")
        if purified.purity_220nm is not None:
            purity_parts.append(f"220nm {purified.purity_220nm:.0f}%")
        if purified.purity_254nm is not None:
            purity_parts.append(f"254nm {purified.purity_254nm:.0f}%")
        if purity_parts:
            print(f"  Product purity: {', '.join(purity_parts)}",
                  file=sys.stderr)

    # Extract NMR data
    if exp.nmr_pdfs:
        print(f"\nExtracting NMR data...", file=sys.stderr)
        parse_all_nmr(exp)

    # Build output sections
    print(f"\nAssembling lab book entry...", file=sys.stderr)
    procedure = build_procedure_section(exp, tracking)
    characterization = build_characterization_section(
        exp, expected, tracking, purified)
    notes = build_notes_section(exp, expected, tracking, purified)

    result = assemble_output(procedure, characterization, notes)

    # FlowER byproduct reference CDXML (if predictions were made via
    # --predict-byproducts inline mode)
    if args.predict_byproducts and args.output:
        try:
            from mass_resolver import get_last_flower_predictions
            from experiments.byproduct_prediction.flower_predictor import (
                write_byproducts_cdxml,
            )
            flower_all = get_last_flower_predictions()
            if flower_all:
                base, _ = os.path.splitext(args.output)
                cdxml_path = f"{base}-flower-predictions.cdxml"
                write_byproducts_cdxml(flower_all, cdxml_path)
        except ImportError:
            pass
        except Exception as e:
            print(f"  Warning: Could not write FlowER CDXML: {e}",
                  file=sys.stderr)

    # Output
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(result)
        print(f"\nOutput written to {args.output}", file=sys.stderr)
    else:
        sys.stdout.buffer.write(result.encode('utf-8'))
        sys.stdout.buffer.write(b'\n')

    return 0


if __name__ == "__main__":
    sys.exit(main())
