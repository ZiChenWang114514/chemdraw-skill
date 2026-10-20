"""Analysis — LCMS parsing, species identification, and lab book generation.

Parses Waters MassLynx LCMS PDF reports (standard and manually integrated),
matches peaks across files, identifies compounds by expected mass, and
assembles lab book entries.  Two workflows:

  1. **Agent-driven** (recommended): LLM parses individual files via
     ``parse_report`` / ``parse_manual_report``, reasons about peaks, and
     calls ``process_entries`` with a JSON entry list to produce a lab book
     entry where all numbers are deterministically sourced.

  2. **Deterministic batch**: ``deterministic.procedure_writer`` orchestrates
     mass resolution, multi-file LCMS collation, species identification, and
     output formatting in a single pipeline.

Optional dependency: ``pdfplumber`` (install via
``pip install cdxml-toolkit-community[analysis]``).
"""

# Agent-driven tools (top-level in analysis/)
from .lcms_analyzer import (
    parse_report, parse_manual_report, format_table, format_manual_table,
    LCMSReport, ChromPeak, MassSpectrum,
    ManualLCMSReport, ManualLCMSSample, ManualPeak,
    is_waters_report, is_manual_integration,
)
from .format_procedure_entry import process_entries

# Deterministic pipeline re-exports (from analysis/deterministic/)
from .deterministic import (
    multi_analyze, AnalysisResult,
    categorize_lcms_file, categorize_lcms_files_batch,
    extract_expected_masses, ExpectedSpecies,
    run_tracking_analysis, run_purified_analysis,
    discover_experiment_files, DiscoveryResult,
)
