# Analysis Public Symbols

> Generated from cdxml-toolkit 0.7.0a2. Curated guidance: [../toolkit-analysis-interfaces.md](../toolkit-analysis-interfaces.md).

## `analysis.deterministic.discover_experiment_files`

- **function**, line 115: `discover_experiment_files(input_dir: str, experiment_name: Optional[str] = None) -> DiscoveryResult` - Discover all files for an experiment.
- **class**, line 50: `DiscoveryResult` - All discovered files for an experiment.
- **method**, line 61: `DiscoveryResult.to_dict() -> dict` - Convert to JSON-serializable dict.
- **function**, line 308: `format_text_report(result: DiscoveryResult) -> str` - Format discovery result as human-readable text.
- **class**, line 36: `LCMSFileRecord` - An LCMS PDF with its classification.
- **property**, line 45: `LCMSFileRecord.filename` - Basename of the file path.

## `analysis.deterministic.lab_book_formatter`

- **function**, line 671: `assemble_output(procedure: str, characterization: str, notes: str) -> str` - Assemble the three sections into final output.
- **function**, line 421: `build_characterization_section(exp, expected: List[ExpectedSpecies], tracking: TrackingAnalysis, purified: PurifiedAnalysis) -> str` - Build the CHARACTERIZATION section with LCMS and NMR data.
- **function**, line 546: `build_notes_section(exp, expected: List[ExpectedSpecies], tracking: TrackingAnalysis, purified: PurifiedAnalysis) -> str` - Build the NOTES section with observations and inferences.
- **function**, line 345: `build_procedure_section(exp, tracking: TrackingAnalysis) -> str` - Build the complete PROCEDURE section.
- **function**, line 136: `build_tracking_narrative(exp, tracking: TrackingAnalysis) -> str` - Build a concise reaction monitoring narrative from multi-LCMS data.
- **function**, line 43: `format_method_name(method_path: str) -> str` - Extract short method name like 'AmF 2 min' from method path.

## `analysis.deterministic.lcms_file_categorizer`

- **class**, line 91: `BatchResult` - Result of batch categorization for one experiment.
- **function**, line 837: `calibrate_sort_keys_hybrid(sorted_groups: List['TrackingGroup'], result: 'BatchResult', run_datetimes: Optional[Dict[str, str]] = None) -> None` - Assign sort keys to tracking files across multiple tracking groups.
- **function**, line 29: `categorize_lcms_file(filename: str) -> Tuple[str, float]` - Categorize an LCMS file and return (category, sort_key).
- **function**, line 707: `categorize_lcms_files_batch(filenames: List[str], experiment_id: Optional[str] = None) -> BatchResult` - Batch-categorize all LCMS files for one experiment.
- **class**, line 81: `FileClassification` - Classification result for one LCMS file.
- **class**, line 61: `FileModifiers` - Metadata stripped from a filename before categorization.
- **class**, line 73: `TrackingGroup` - A group of tracking files sharing a common prefix.

## `analysis.deterministic.lcms_identifier`

- **class**, line 62: `IdentifiedCompound` - A multi-LCMS compound matched to an expected species.
- **class**, line 78: `IdentifiedPeak` - A single-report chromatographic peak matched to an expected species.
- **function**, line 102: `match_ions_to_species(ions: List[Tuple[str, float, int]], expected: List[ExpectedSpecies], tolerance: float = MASS_TOLERANCE) -> Optional[Tuple[ExpectedSpecies, str, float]]` - Match observed ions against expected species adducts.
- **class**, line 86: `PurifiedAnalysis` - Results of purified product LCMS analysis.
- **function**, line 502: `run_purified_analysis(exp, expected: List[ExpectedSpecies]) -> PurifiedAnalysis` - Parse and analyze the purified product LCMS file.
- **function**, line 311: `run_tracking_analysis(exp, expected: List[ExpectedSpecies]) -> TrackingAnalysis` - Analyze tracking LCMS files and identify compounds.
- **function**, line 452: `run_tracking_from_result(analysis: AnalysisResult, expected: List[ExpectedSpecies]) -> TrackingAnalysis` - Identify compounds in a pre-computed AnalysisResult.
- **class**, line 70: `TrackingAnalysis` - Results of multi-LCMS tracking analysis with species identification.

## `analysis.deterministic.mass_resolver`

- **function**, line 126: `build_adducts(exact_mass: float) -> Dict[str, float]` - Build expected adduct m/z dict from neutral exact mass.
- **function**, line 93: `compute_masses(smiles: str) -> Optional[Tuple[float, float]]` - Compute monoisotopic masses from SMILES.
- **class**, line 80: `ExpectedSpecies` - A chemical species with predicted LCMS adduct masses.
- **function**, line 547: `extract_expected_masses(exp, predict_byproducts = False) -> List[ExpectedSpecies]` - Extract expected species masses from CDX/RXN structure files.
- **function**, line 638: `get_last_flower_predictions() -> List[ExpectedSpecies]` - Return the full FlowER prediction list from the last call to ``extract_expected_masses(predict_byproducts=True)``.

## `analysis.deterministic.multi_lcms_analyzer`

- **class**, line 99: `AnalysisResult` - Complete result of the multi-file LCMS analysis.
- **function**, line 1032: `analyze(files: List[FileEntry], rt_tol: float, mz_tol: float, trend_threshold: float, ignore_instrument: bool, use_run_time: bool = True, max_ion_rank: Optional[int] = None, pick_biggest_group: bool = False) -> List[AnalysisResult]` - Top-level analysis.  Groups files by (instrument, method) and runs peak matching within each group.
- **function**, line 216: `attach_peak_to_compound(compound: Compound, peak: ChromPeak, file_idx: int)` - Add a peak's data to an existing compound.
- **function**, line 162: `check_uv_compatibility(ratio_a: Optional[float], ratio_b: Optional[float]) -> Optional[bool]` - Check if two UV ratios are compatible. Returns True (compatible), False (incompatible), or None (inconclusive).
- **function**, line 334: `cluster_ions(compound: Compound, mz_tol: float, total_files: int, max_ion_rank: Optional[int] = None)` - Group ions within mz_tol, split into recurring vs other.
- **class**, line 69: `Compound` - A matched compound tracked across multiple LCMS files.
- **function**, line 321: `compute_canonical_rt(compound: Compound)` - Set canonical RT by majority vote (mode of rounded values).
- **function**, line 425: `compute_trend(compound: Compound, total_files: int, threshold: float, excluded_files: set = None)` - Determine area% trend: increasing / decreasing / stable.
- **function**, line 533: `compute_uv_consensus(compound: Compound)` - Deduplicate UV lambda-max across all observations.
- **function**, line 147: `compute_uv_ratio(peak: ChromPeak) -> Optional[float]` - Compute area_220nm / area_254nm for a peak. Returns None if either area is missing or zero (inconclusive data). Only returns a meaningful ratio when both areas are present and non-zero.
- **function**, line 199: `create_compound(cid: int, peak: ChromPeak, ratio: Optional[float], file_idx: int) -> Compound` - Create a new Compound from a seed peak.
- **function**, line 538: `detect_outlier_files(files: List[FileEntry]) -> Tuple[set, set]` - Flag files that look like blanks/outliers or have ambiguous timing.
- **function**, line 592: `detect_outlier_files_conservative(files: List[FileEntry], compounds: List[Compound], excluded_files: set, significance_floor: float = 5.0, threshold: float = 0.5) -> set` - Second-pass outlier detection based on multi-species behaviour.
- **function**, line 115: `extract_run_datetime(pdf_path: str) -> Optional[str]` - Extract the acquisition date+time from a MassLynx PDF. Looks for 'Date:DD-Mon-YYYY' and 'Time:HH:MM:SS' in the header. Returns ISO-format string 'YYYY-MM-DD HH:MM:SS' or None.
- **class**, line 47: `FileEntry` - Metadata for one LCMS file in the analysis.
- **function**, line 232: `find_and_match(peak: ChromPeak, ratio: Optional[float], compounds: List[Compound], rt_tol: float, used_ids: set) -> Optional[Compound]` - Find the best matching compound for a peak. Returns the compound or None if no match found.
- **function**, line 889: `format_json_report(result: AnalysisResult) -> str` - Render structured JSON output.
- **function**, line 691: `format_text_report(result: AnalysisResult, min_summary_area: float = 2.0, hide_other_ions: bool = False) -> str` - Render the full text report.
- **class**, line 60: `IonCluster` - A group of m/z values across files that represent the same ion.
- **function**, line 952: `load_analysis_from_json(json_path: str) -> AnalysisResult` - Reconstruct an AnalysisResult from a JSON file produced by format_json_report().
- **function**, line 267: `match_peaks_across_files(files: List[FileEntry], rt_tol: float) -> List[Compound]` - Match peaks across all files and return a list of Compounds. Files must be pre-sorted chronologically.

## `analysis.deterministic.procedure_writer`

- **function**, line 77: `discover_files(input_dir: str, experiment_name: Optional[str] = None) -> ExperimentData` - Discover all files for an experiment.
- **function**, line 126: `extract_nmr_data(pdf_path: str) -> List[str]` - Extract reported NMR data strings from an NMR PDF.
- **function**, line 178: `parse_all_nmr(exp: ExperimentData) -> None` - Extract NMR data from all NMR PDFs (with cross-file deduplication).

## `analysis.format_procedure_entry`

- **function**, line 421: `process_entries(entries: List[dict]) -> str` - Process all entries in order, return the formatted lab book entry.

## `analysis.lcms_analyzer`

- **function**, line 1009: `analyze_reaction_progress(reports: List[LCMSReport], sm_mass: float, product_mass: float) -> str` - Analyze reaction progress across multiple timepoints. Returns notes section.
- **class**, line 58: `ChromPeak` - A single integrated peak from the UV chromatogram.
- **function**, line 91: `extract_all_text(pdf_path: str) -> str` - Extract all text from all pages of a PDF.
- **function**, line 936: `format_annotation(report: LCMSReport, sm_mass: float, product_mass: float) -> str` - Format section (1): LCMS annotation line. Template: [Instrument], [Method short], SM RT = X.XX min, ESI+/- XXX.X; DP RT = X.XX min, ESI+/- XXX.X
- **function**, line 1080: `format_basic_report(report: LCMSReport) -> str` - Format a single LCMS file report without species identification.
- **function**, line 811: `format_manual_table(report: ManualLCMSReport) -> str` - Format a manual integration report as markdown for LLM consumption.
- **function**, line 990: `format_peak_summary(report: LCMSReport, sm_mass: float, product_mass: float) -> str` - Format a summary of all peaks with identification.
- **function**, line 1145: `format_table(report: LCMSReport) -> str` - Format an LCMS report as a markdown table for LLM consumption.
- **function**, line 849: `identify_peak(peak: ChromPeak, sm_mass: float, product_mass: float, tolerance: float = 1.5) -> Optional[str]` - Try to identify a peak as SM, product, or unknown based on ESI mass data.
- **function**, line 660: `is_manual_integration(pdf_path: str) -> bool` - Check if this PDF is a MassLynx manual integration export.
- **function**, line 548: `is_waters_report(pdf_path: str) -> bool` - Quick content-based check: is this PDF a standard Waters MassLynx report?
- **class**, line 75: `LCMSReport` - Parsed contents of one MassLynx PDF report.
- **class**, line 651: `ManualLCMSReport` - Parsed contents of a manually integrated MassLynx PDF.
- **class**, line 642: `ManualLCMSSample` - One chromatogram section from a manual integration PDF.
- **class**, line 632: `ManualPeak` - A peak from a manually integrated chromatogram.
- **class**, line 52: `MassSpectrum` - ESI+ or ESI- spectrum for a single chromatographic peak.
- **function**, line 153: `method_basename(method_path: str) -> str` - Return the method filename without directory and extension, lowercased.
- **function**, line 268: `parse_all_peak_tables(text: str) -> Tuple[List[ChromPeak], Dict[Tuple[int, float], str]]` - Parse all UV peak integration tables (TAC, 220nm, 254nm). Returns (peaks, id_map) where id_map maps (raw_num, rt) -> string peak_id.
- **function**, line 162: `parse_header(text: str) -> dict` - Extract header fields from the report text.
- **function**, line 679: `parse_manual_report(pdf_path: str) -> ManualLCMSReport` - Parse a manually integrated MassLynx PDF.
- **function**, line 106: `parse_method_short(method_path: str) -> str` - Extract a short method description from the full MassLynx method path.
- **function**, line 576: `parse_report(pdf_path: str) -> LCMSReport` - Parse a complete MassLynx PDF report.

## `analysis.parse_analysis_file`

- **function**, line 34: `parse_analysis_file(pdf_path: str) -> Dict[str, Any]` - Detect and parse an LCMS or NMR PDF report.
