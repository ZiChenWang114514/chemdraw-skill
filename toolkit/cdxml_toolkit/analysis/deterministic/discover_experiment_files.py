#!/usr/bin/env python3
"""
Experiment File Discovery Tool

Discovers and classifies all files for a chemistry experiment: ELN CSV,
CDX/RXN structure files, LCMS PDFs (with category/sort_key), and NMR PDFs.

Handles two directory layouts:
  1. input_dir IS the experiment directory (contains .csv directly)
  2. input_dir is a parent directory containing experiment subdirectories

Usage:
    python discover_experiment_files.py --input-dir path/to/experiment/ --experiment KL-7001-004
    python discover_experiment_files.py --input-dir path/to/experiment/ --experiment KL-7001-004 --json
    python discover_experiment_files.py --input-dir path/to/experiment/ --experiment KL-7001-004 --json -o files.json
"""

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Tuple

from ..lcms_analyzer import extract_all_text, is_waters_report
from .lcms_file_categorizer import (
    categorize_lcms_file, categorize_lcms_files_batch,
)

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class LCMSFileRecord:
    """An LCMS PDF with its classification."""
    path: str
    category: str       # "tracking", "workup", "purification", "final"
    sort_key: float
    group_prefix: Optional[str] = None     # tracking group prefix (batch categorizer)
    method_variant: Optional[str] = None   # filename-derived method hint (AmB, AmF, etc.)

    @property
    def filename(self) -> str:
        """Basename of the file path."""
        return os.path.basename(self.path)

@dataclass
class DiscoveryResult:
    """All discovered files for an experiment."""
    experiment: str
    input_dir: str
    csv_files: List[str] = field(default_factory=list)
    cdx_files: List[str] = field(default_factory=list)
    rxn_files: List[str] = field(default_factory=list)
    lcms_files: List[LCMSFileRecord] = field(default_factory=list)
    nmr_files: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict."""
        return {
            "experiment": self.experiment,
            "input_dir": self.input_dir,
            "files": {
                "csv": self.csv_files,
                "cdx": self.cdx_files,
                "rxn": self.rxn_files,
                "lcms": [
                    {"path": lf.path, "category": lf.category,
                     "sort_key": lf.sort_key,
                     "group_prefix": lf.group_prefix,
                     "method_variant": lf.method_variant}
                    for lf in self.lcms_files
                ],
                "nmr": self.nmr_files,
            },
            "warnings": self.warnings,
        }

# ---------------------------------------------------------------------------
# Core helpers (extracted from procedure_writer.py)
# ---------------------------------------------------------------------------

def _find_files_matching(directory: str, experiment_name: str,
                         extensions: tuple) -> List[str]:
    """Find files matching experiment name prefix in a directory."""
    if not os.path.isdir(directory):
        return []
    prefix = experiment_name.lower()
    matches = []
    for f in os.listdir(directory):
        fl = f.lower()
        if fl.startswith(prefix) and fl.endswith(extensions):
            # Ensure it's not a different experiment (e.g., KL-7001-0040)
            remainder = f[len(experiment_name):]
            if not remainder or remainder[0] in ('-', '.', ' '):
                matches.append(os.path.join(directory, f))
    return sorted(matches)


def _pdf_contains_nmr_data(pdf_path: str) -> bool:
    """Check if a PDF contains NMR data strings (1H NMR, 13C NMR, etc.)."""
    try:
        text = extract_all_text(pdf_path)
        return bool(re.search(r'\d+[A-Z]\s+NMR', text))
    except Exception:
        return False

# ---------------------------------------------------------------------------
# Main discovery logic (extracted from procedure_writer.discover_files)
# ---------------------------------------------------------------------------

def discover_experiment_files(
    input_dir: str,
    experiment_name: Optional[str] = None,
) -> DiscoveryResult:
    """
    Discover all files for an experiment.

    Handles two layouts:
    1. input_dir IS the experiment dir (contains .csv directly)
    2. input_dir is the parent dir (contains experiment subdirs)

    Args:
        input_dir: Path to experiment directory or parent directory.
        experiment_name: Experiment name (e.g. "KL-7001-004"). Required
            if input_dir is the parent directory.

    Returns:
        DiscoveryResult with all found files classified by type.

    Raises:
        SystemExit if no CSV found and no experiment name provided.
    """
    input_dir = os.path.abspath(input_dir)

    # Try to find CSV directly in input_dir
    csv_in_dir = [f for f in os.listdir(input_dir)
                  if f.lower().endswith('.csv')]

    if csv_in_dir and not experiment_name:
        # input_dir IS the experiment dir — infer experiment name from CSV
        csv_path = os.path.join(input_dir, csv_in_dir[0])
        experiment_name = _infer_experiment_from_csv(csv_path)
        if not experiment_name:
            experiment_name = os.path.basename(input_dir)
        parent_dir = os.path.dirname(input_dir)
    elif experiment_name:
        # input_dir is parent, look in experiment subdir
        parent_dir = input_dir
    else:
        # No CSV, no experiment name — list subdirs as candidates
        print("Error: No CSV found and no --experiment specified.",
              file=sys.stderr)
        subdirs = [d for d in os.listdir(input_dir)
                   if os.path.isdir(os.path.join(input_dir, d))
                   and not d.startswith('.')
                   and d not in ('DATA', 'LCMS files')]
        if subdirs:
            print(f"Available experiments: {', '.join(sorted(subdirs))}",
                  file=sys.stderr)
        sys.exit(1)

    result = DiscoveryResult(
        experiment=experiment_name,
        input_dir=input_dir,
    )

    # --- CSV ---
    exp_dir_path = os.path.join(parent_dir, experiment_name)
    csv_path = os.path.join(exp_dir_path, f"{experiment_name}.csv")
    if os.path.isfile(csv_path):
        result.csv_files.append(csv_path)
    elif csv_in_dir:
        # Flat layout: CSV was found directly in input_dir
        result.csv_files.append(os.path.join(input_dir, csv_in_dir[0]))

    # --- CDX / RXN ---
    # Check experiment subdir first, then input_dir itself (flat layout)
    if os.path.isdir(exp_dir_path):
        cdx = _find_files_matching(exp_dir_path, experiment_name, ('.cdx',))
        if cdx:
            result.cdx_files.extend(cdx)
        rxn = _find_files_matching(exp_dir_path, experiment_name, ('.rxn',))
        if rxn:
            result.rxn_files.extend(rxn)

    cdx = _find_files_matching(input_dir, experiment_name, ('.cdx',))
    for f in cdx:
        if f not in result.cdx_files:
            result.cdx_files.append(f)
    rxn = _find_files_matching(input_dir, experiment_name, ('.rxn',))
    for f in rxn:
        if f not in result.rxn_files:
            result.rxn_files.append(f)

    # --- LCMS PDFs ---
    # Search LCMS files dir, experiment dir, input_dir, parent dir
    # NOT DATA directory (DATA is for NMR)
    lcms_dirs = [
        os.path.join(parent_dir, 'LCMS files'),
        os.path.join(input_dir, 'LCMS files'),
        input_dir,
        parent_dir,
    ]
    seen_lcms = set()
    lcms_candidates = []  # (path, filename) — collect all first, then batch

    for d in lcms_dirs:
        for f in _find_files_matching(d, experiment_name, ('.pdf',)):
            fname = os.path.basename(f).lower()
            if fname in seen_lcms:
                continue
            if 'nmr' in fname or 'mnova' in fname:
                continue
            # Content-based check: skip non-standard PDFs (e.g. manually
            # integrated chromatograms) that aren't Waters MassLynx reports
            if not is_waters_report(f):
                continue
            seen_lcms.add(fname)
            lcms_candidates.append((f, os.path.basename(f)))

    # Batch-categorize using context-aware categorizer (resolves ambiguities
    # like tNN purification fractions vs tracking timepoints).
    if lcms_candidates:
        filenames = [fn for _, fn in lcms_candidates]
        path_map = {fn: path for path, fn in lcms_candidates}
        batch = categorize_lcms_files_batch(filenames, experiment_name)

        for fn in filenames:
            if fn in batch.filtered_files:
                continue  # skip special files (-MS, -LC, -UV, etc.)
            fc = batch.files.get(fn)
            if fc is not None:
                result.lcms_files.append(LCMSFileRecord(
                    path=path_map[fn],
                    category=fc.category,
                    sort_key=fc.sort_key,
                    group_prefix=fc.group_prefix,
                    method_variant=(fc.modifiers.method_variant
                                    if fc.modifiers else None),
                ))
            else:
                # Fallback to simple categorizer (shouldn't happen)
                category, sort_key = categorize_lcms_file(fn)
                result.lcms_files.append(LCMSFileRecord(
                    path=path_map[fn],
                    category=category,
                    sort_key=sort_key,
                ))

    # Sort LCMS files chronologically
    result.lcms_files.sort(key=lambda x: x.sort_key)

    # --- NMR PDFs ---
    # Scan DATA directories for PDFs matching experiment name that
    # contain NMR data strings (content-based detection)
    data_dirs = [
        os.path.join(parent_dir, 'DATA'),
        os.path.join(input_dir, 'DATA'),
    ]
    seen_nmr = set()

    for d in data_dirs:
        for f in _find_files_matching(d, experiment_name, ('.pdf',)):
            fname = os.path.basename(f).lower()
            if fname in seen_nmr:
                continue
            if _pdf_contains_nmr_data(f):
                seen_nmr.add(fname)
                result.nmr_files.append(f)

    # --- Warnings ---
    if not result.csv_files:
        result.warnings.append("No CSV file found")
    if not result.lcms_files:
        result.warnings.append("No LCMS PDF files found")
    if not result.cdx_files and not result.rxn_files:
        result.warnings.append("No CDX or RXN structure files found")

    return result


def _infer_experiment_from_csv(csv_path: str) -> Optional[str]:
    """Read the EXPERIENCE_NAME field from a Findmolecule CSV."""
    try:
        import csv as csv_mod
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv_mod.reader(f, delimiter=';', quotechar='"')
            rows = list(reader)
        if len(rows) >= 2:
            headers = rows[0]
            values = rows[1]
            meta = dict(zip(headers, values))
            name = meta.get('EXPERIENCE_NAME', '').strip()
            if name:
                return name
    except Exception:
        pass
    return None

# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------

def format_text_report(result: DiscoveryResult) -> str:
    """Format discovery result as human-readable text."""
    lines = []
    lines.append(f"Experiment: {result.experiment}")
    lines.append(f"Input dir:  {result.input_dir}")
    lines.append("")

    # CSV
    lines.append(f"CSV files ({len(result.csv_files)}):")
    for f in result.csv_files:
        lines.append(f"  {os.path.basename(f)}")
    if not result.csv_files:
        lines.append("  (none)")

    # CDX
    lines.append(f"CDX files ({len(result.cdx_files)}):")
    for f in result.cdx_files:
        lines.append(f"  {os.path.basename(f)}")
    if not result.cdx_files:
        lines.append("  (none)")

    # RXN
    lines.append(f"RXN files ({len(result.rxn_files)}):")
    for f in result.rxn_files:
        lines.append(f"  {os.path.basename(f)}")
    if not result.rxn_files:
        lines.append("  (none)")

    # LCMS
    lines.append(f"LCMS files ({len(result.lcms_files)}):")
    categories: Dict[str, List[LCMSFileRecord]] = {}
    for lf in result.lcms_files:
        categories.setdefault(lf.category, []).append(lf)
    for cat in ("tracking", "workup", "purification", "final"):
        cat_files = categories.get(cat, [])
        if cat_files:
            lines.append(f"  {cat} ({len(cat_files)}):")
            for lf in cat_files:
                lines.append(f"    {os.path.basename(lf.path)}  "
                             f"[sort_key={lf.sort_key}]")
    if not result.lcms_files:
        lines.append("  (none)")

    # NMR
    lines.append(f"NMR files ({len(result.nmr_files)}):")
    for f in result.nmr_files:
        lines.append(f"  {os.path.basename(f)}")
    if not result.nmr_files:
        lines.append("  (none)")

    # Warnings
    if result.warnings:
        lines.append("")
        lines.append("Warnings:")
        for w in result.warnings:
            lines.append(f"  - {w}")

    return "\n".join(lines)

# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Experiment File Discovery Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("--input-dir", "-i", required=True,
                   help="Directory containing experiment files "
                        "(experiment dir or parent dir)")
    p.add_argument("--experiment", "-e", default=None,
                   help="Experiment name (e.g., KL-7001-004). "
                        "Required if input-dir is the parent directory.")
    p.add_argument("--json", "-j", action="store_true",
                   help="Output in JSON format")
    p.add_argument("--output", "-o", default=None,
                   help="Output file path (default: stdout)")
    return p


def main(argv=None) -> int:
    parser = _build_arg_parser()
    args = parser.parse_args(argv)

    result = discover_experiment_files(args.input_dir, args.experiment)

    if args.json:
        output = json.dumps(result.to_dict(), indent=2)
    else:
        output = format_text_report(result)

    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(output)
            f.write('\n')
        print(f"Output written to {args.output}", file=sys.stderr)
    else:
        print(output)

    return 0


if __name__ == '__main__':
    sys.exit(main())
