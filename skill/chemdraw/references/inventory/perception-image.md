# Perception Image Public Symbols

> Generated from cdxml-toolkit 0.7.0a1. Curated guidance: [../toolkit-perception-image-interfaces.md](../toolkit-perception-image-interfaces.md).

## `deterministic_pipeline.legacy.eln_cdx_cleanup`

- **function**, line 244: `cleanup_eln_cdx(input_path, output_path = None, scale_factor = 0.5, style_path = None)` - Clean up a reaction scheme exported from Findmolecule ELN.
- **function**, line 379: `cleanup_multiple(input_paths, output_dir = None, scale_factor = 0.5, style_path = None)` - Clean up multiple CDX/CDXML files.
- **function**, line 84: `scale_cdxml_coordinates(input_path, output_path, factor = 0.5)` - Scale all coordinates in a CDXML file by the given factor, centered on the centroid of all node/text positions.

## `deterministic_pipeline.legacy.eln_enrichment`

- **function**, line 758: `enrich_phase_a(root: ET.Element, enrichment: EnrichmentData, merged_text_id: Optional[str], verbose: bool = False) -> None` - Inject equivalents into text labels (modifies root in-place).
- **function**, line 946: `enrich_phase_b(root: ET.Element, enrichment: EnrichmentData, verbose: bool = False) -> None` - Add run arrow and structural eq labels after layout.
- **class**, line 62: `EnrichmentData` - All enrichment info extracted from CSV + scheme matching.
- **function**, line 133: `match_csv_to_scheme(root: ET.Element, csv_path: str, verbose: bool = False) -> EnrichmentData` - Match CSV reagents/solvents/product to scheme elements.
- **class**, line 48: `MatchedReagent` - A CSV reagent matched to a scheme element.
- **function**, line 601: `reposition_reactant_above_arrow(root: ET.Element, csv_path: str, verbose: bool = False) -> bool` - Move a non-substrate reactant from left-of-arrow to above-arrow.

## `deterministic_pipeline.legacy.scheme_aligner`

- **function**, line 210: `align_fragment(ref_mol, tgt_mol, atom_map)` - Align target fragment to reference (product) using GenerateDepictionMatching2DStructure.
- **function**, line 139: `avg_bond_length(atoms_data, mol)` - Average bond length computed from CDXML atom coordinates.
- **function**, line 180: `find_mcs(ref_mol, target_mol, timeout = 30)` - Find MCS. Returns (mcs_result, atom_map [(ref_idx, tgt_idx)]).
- **function**, line 73: `fragment_to_mol(frag_elem)` - Convert a CDXML <fragment> to an RDKit Mol (no conformer set).
- **function**, line 43: `parse_cdxml(path)` - Parse CDXML file. Returns (tree, fragments_dict, reaction_steps).
- **function**, line 153: `rdkit_bond_length()` - RDKit's default 2D depiction bond length (cached).
- **function**, line 307: `save_svg(mol, highlight_atoms, label, out_dir, stem)` - Save a single SVG with highlighted atoms.
- **function**, line 166: `set_cdxml_coords(mol, atoms_data, scale = 1.0)` - Set conformer from CDXML coordinates (y-flipped, optionally scaled).
- **function**, line 256: `write_aligned_coords(frag_elem, mol, atoms_data, scale, original_center)` - Convert aligned RDKit coords back to CDXML space and write to XML.

## `deterministic_pipeline.legacy.scheme_polisher`

- **function**, line 411: `polish_scheme(cdxml_path: str, output_path: str, verbose: bool = False, merge_conditions: bool = False, skip_alignment: bool = False, use_rxnmapper: bool = False) -> Dict` - Polish a CDXML reaction scheme in-place.

## `deterministic_pipeline.legacy.scheme_polisher_v2`

- **function**, line 211: `apply_acs_settings(root: ET.Element)` - Apply ACS Document 1996 settings to the root CDXML element.
- **function**, line 255: `fix_narrow_text(root: ET.Element, verbose: bool = False) -> int` - Fix degenerate narrow text labels from Findmolecule ELN exports.
- **function**, line 162: `normalize_bond_lengths(root: ET.Element, target: float = TARGET_BOND_LENGTH, verbose: bool = False) -> int` - Normalize bond lengths in every fragment to the target length.
- **function**, line 217: `normalize_fonts(root: ET.Element, verbose: bool = False) -> int` - Set all caption text to Arial 10pt Bold (face=96).
- **function**, line 318: `resolve_orphan_reagent_text(root: ET.Element, verbose: bool = False) -> int` - Resolve orphan text labels to their reagent DB display names.
- **function**, line 861: `run_pipeline(input_path: str, output_path: str, merge_conditions: bool = True, approach: str = 'chemdraw_mimic', chemscript_cleanup: bool = True, align_mode: str = 'rdkit', eln_csv: Optional[str] = None, ref_cdxml: Optional[str] = None, verbose: bool = False) -> str` - Run the full COM-free polishing pipeline.

## `deterministic_pipeline.scheme_reader_audit`

- **function**, line 367: `audit_showcase(showcase_dir: str, use_chemscript: bool = False, verbose: bool = False, render: bool = False) -> AuditReport` - Run quality audit on all showcase CDXMLs in a directory.
- **class**, line 148: `AuditReport` - Aggregate quality report across all audited files.
- **method**, line 159: `AuditReport.to_dict() -> dict` - No public docstring in the audited version.
- **class**, line 95: `FileAuditResult` - Quality audit result for one CDXML file.
- **property**, line 123: `FileAuditResult.detail_line` - One-line summary for terminal output.

## `deterministic_pipeline.scheme_reader_verify`

- **function**, line 107: `batch_enrich_schemes(descs: list, verbose: bool = False) -> list` - Batch ML enrichment for multiple SchemeDescriptions.
- **function**, line 75: `enrich_scheme(desc: SchemeDescription, verbose: bool = False) -> dict` - Generate ML enrichment for all steps in a scheme.
- **function**, line 887: `generate_report(results: List[dict], output_path: str, title: str = 'Scheme Reader Verification Report') -> None` - Generate the HTML report from a list of result dicts.

## `image.reaction_from_image`

- **function**, line 775: `build_reaction_scheme(structures: List[Dict], reactant_indices: List[int], product_indices: List[int], conditions_above: List[str], conditions_below: List[str], verbose: bool = False, expanded_above: Optional['ExpandedItems'] = None, expanded_below: Optional['ExpandedItems'] = None) -> str` - Assemble a CDXML reaction scheme from extracted structures + descriptor.
- **function**, line 1171: `build_reaction_scheme_chemscript(structures: List[Dict], cs_fragments: Dict[int, Tuple[str, float, float, float, float]], reactant_indices: List[int], product_indices: List[int], conditions_above: List[str], conditions_below: List[str], verbose: bool = False, expanded_above: Optional['ExpandedItems'] = None, expanded_below: Optional['ExpandedItems'] = None) -> str` - Assemble a CDXML reaction scheme using ChemScript-cleaned fragment XML.
- **function**, line 1391: `reaction_from_image(image_path: str, descriptor: Dict, page: int = 0, segment: bool = True, hand_drawn: bool = False, verbose: bool = False, merge_gap: Optional[int] = None, cleanup: bool = False, expand: bool = False) -> str` - Full pipeline: image + reaction descriptor → CDXML reaction scheme.
- **function**, line 1511: `reaction_from_image_to_json(image_path: str, descriptor: Dict, output_path: Optional[str] = None, page: int = 0, segment: bool = True, hand_drawn: bool = False, verbose: bool = False, merge_gap: Optional[int] = None, use_network: bool = True) -> 'ReactionDescriptor'` - Full pipeline: image + reaction descriptor → ReactionDescriptor JSON.
- **function**, line 89: `resolve_abbreviation(text: str) -> str` - Look up text in the reagent database.

## `image.structure_from_image`

- **function**, line 732: `enrich_with_mass_data(results: List[Dict]) -> None` - Add formula, mw, exact_mass, and adducts to each extracted structure.
- **function**, line 1150: `extract_structures_from_image(image_path: str, page: int = 0, segment: bool = True, hand_drawn: bool = False, verbose: bool = False, merge_gap: Optional[int] = None, detect_labels: bool = True) -> Dict` - Extract all chemical structures from an image using DECIMER.
- **function**, line 254: `load_image(path: str, page: int = 0) -> 'np.ndarray'` - Load an image from a PNG/JPG file or from a specific page of a PDF.
- **function**, line 688: `normalize_for_cdxml(atoms: List[Dict], bonds: List[Dict], center_x: float = 200.0, center_y: float = 300.0) -> Tuple[List[Dict], List[Dict]]` - Scale + flip-y + centre coordinates for CDXML output (ACS 1996, 14.40 pt bonds). RDKit coords are Angstroms, y-up. CDXML is points, y-down.
- **function**, line 1373: `results_to_cdxml(results: List[Dict]) -> str` - Convert extracted structures to a CDXML document (multiple molecules on one page).
- **function**, line 1485: `results_to_cdxml_chemscript(results: List[Dict], verbose: bool = False) -> str` - Convert extracted structures to CDXML using ChemScript for cleanup.
- **function**, line 388: `segment_structures(bgr: 'np.ndarray', merge_gap: Optional[int] = None) -> List[Tuple['np.ndarray', Tuple[int, int, int, int]]]` - Detect chemical structure regions in a BGR image.
- **function**, line 615: `smiles_to_coords(smiles: str, offset_index: int = 0) -> Optional[Dict]` - Convert a SMILES string to 2D atom/bond data using RDKit.

## `perception.compound_search`

- **function**, line 73: `search_compound(smiles: str, experiment_dir: str, similarity_threshold: float = 0.85) -> Dict[str, Any]` - Search for a molecule (by SMILES) across all experiments in a directory.

## `perception.eln_csv_parser`

- **class**, line 66: `ExperimentData` - No public docstring in the audited version.
- **function**, line 107: `extract_procedure_body(full_text: str) -> str` - Extract the procedure portion, cutting off literature references.
- **class**, line 55: `LCMSFileInfo` - No public docstring in the audited version.
- **function**, line 126: `parse_eln_csv(csv_path: str) -> Optional[ExperimentData]` - Parse a Findmolecule ELN CSV export.
- **class**, line 46: `ProductInfo` - No public docstring in the audited version.
- **class**, line 27: `ReagentInfo` - No public docstring in the audited version.
- **class**, line 39: `SolventInfo` - No public docstring in the audited version.
- **function**, line 89: `strip_html(html_str: str) -> str` - Strip HTML tags and convert to plain text.

## `perception.rdf_parser`

- **class**, line 29: `Atom` - A single atom from a V3000 MOL block.
- **class**, line 40: `Bond` - A single bond from a V3000 MOL block.
- **class**, line 57: `Molecule` - A molecule parsed from a $MOL block.
- **function**, line 207: `parse_rdf(filepath: str) -> List[Reaction]` - Parse a SciFinder .rdf file and return a list of Reaction objects.
- **function**, line 117: `parse_v3000_mol(lines: List[str]) -> tuple` - Parse a V3000 MOL block into atoms, bonds, and stereo collections.
- **class**, line 102: `Reaction` - A complete parsed reaction record from an RDF file.
- **function**, line 504: `reaction_to_dict(rxn: Reaction) -> Dict[str, Any]` - Convert a Reaction dataclass to a clean dictionary for JSON output.
- **class**, line 88: `ReactionVariation` - One experimental variation of a reaction (SciFinder VAR block).
- **class**, line 69: `ReagentEntry` - A reagent, catalyst, or solvent identified by CAS in $DTYPE/$DATUM.
- **class**, line 80: `Reference` - A literature reference from the reaction record.
- **function**, line 475: `resolve_cas_numbers(reaction: Reaction) -> None` - Resolve all CAS numbers in the reaction using cas_resolver. Populates name, MW, formula, SMILES for reagents/catalysts/solvents.
- **class**, line 50: `StereoCollection` - Stereo collection from V3000 (ABS, REL, RAC).

## `perception.reactant_heuristic`

- **function**, line 839: `classify_from_cdxml(cdxml_path: str, mcs_threshold: float = 0.3, use_rxnmapper: bool = False) -> Dict[str, Any]` - Parse a CDXML reaction file and classify all reagents.
- **function**, line 958: `classify_from_smiles(reagent_smiles: List[str], product_smiles: str, reagent_names: Optional[List[str]] = None, mcs_threshold: float = 0.3, use_rxnmapper: bool = True) -> Dict[str, Any]` - Classify reagents given as SMILES strings.
- **function**, line 714: `classify_reagents(reagents: List[ReagentInfo], product_smiles: str, mcs_threshold: float = 0.3, use_rxnmapper: bool = True) -> List[ReagentInfo]` - Classify each reagent using a two-tier strategy.
- **function**, line 461: `mcs_ratio(reagent_smiles: str, product_smiles: str) -> Optional[float]` - Compute MCS heavy-atom ratio: MCS_atoms / reagent_heavy_atoms.
- **class**, line 33: `ReagentInfo` - Information about a single reagent being classified.
- **function**, line 397: `role_lookup(smiles: Optional[str], name: Optional[str]) -> Optional[Tuple[str, str]]` - Tier 1 classification.  Returns (role, method) or None.

## `perception.reaction_parser`

- **function**, line 419: `extract_conditions_from_text(text: str) -> List[str]` - Extract condition tokens (temperature, time, atmosphere) from text.
- **function**, line 1852: `parse_reaction(cdxml: Optional[str] = None, cdx: Optional[str] = None, csv: Optional[str] = None, rxn: Optional[str] = None, input_dir: Optional[str] = None, experiment: Optional[str] = None, use_rxnmapper: bool = False, use_rxn_insight: bool = True, use_network: bool = True, verbose: bool = False) -> ReactionDescriptor` - Parse reaction from ELN files and return a ReactionDescriptor.
- **function**, line 285: `reaction_summary(json_path: str, species_fields: Optional[List[str]] = None, top_fields: Optional[List[str]] = None, eln_fields: Optional[List[str]] = None) -> dict` - Load a reaction JSON and return a slim summary for LLM context.
- **class**, line 109: `ReactionDescriptor` - Complete parsed reaction description.
- **method**, line 143: `ReactionDescriptor.from_dict(d: dict) -> 'ReactionDescriptor'` - No public docstring in the audited version.
- **method**, line 171: `ReactionDescriptor.from_json(path: str) -> 'ReactionDescriptor'` - No public docstring in the audited version.
- **method**, line 182: `ReactionDescriptor.get_dp() -> Optional[SpeciesDescriptor]` - Return the desired product species, or None.
- **method**, line 189: `ReactionDescriptor.get_expected_species() -> List[dict]` - Return ExpectedSpecies-compatible dicts for LCMS matching.
- **method**, line 175: `ReactionDescriptor.get_sm() -> Optional[SpeciesDescriptor]` - Return the starting material species, or None.
- **method**, line 228: `ReactionDescriptor.summary(species_fields: Optional[List[str]] = None, top_fields: Optional[List[str]] = None, eln_fields: Optional[List[str]] = None) -> dict` - Return a slim summary dict for LLM context.
- **method**, line 125: `ReactionDescriptor.to_dict() -> dict` - No public docstring in the audited version.
- **method**, line 165: `ReactionDescriptor.to_json(path: str, pretty: bool = True) -> None` - No public docstring in the audited version.
- **class**, line 54: `SpeciesDescriptor` - A single chemical species in the reaction.
- **method**, line 102: `SpeciesDescriptor.to_dict() -> dict` - No public docstring in the audited version.
- **function**, line 367: `split_condition_text(text: str) -> List[str]` - Split a merged condition text block into individual chemical tokens.

## `perception.scheme_reader`

- **function**, line 2654: `read_scheme(cdxml_path: str, use_network: bool = True, use_chemscript: bool = False, verbose: bool = False, segment: bool = False, _scheme_filter: Optional[Set[str]] = None) -> SchemeDescription` - Read a CDXML reaction scheme and return a structured description.
- **class**, line 116: `SchemeDescription` - Complete structured description of a reaction scheme.
- **method**, line 173: `SchemeDescription.from_dict(d: dict) -> 'SchemeDescription'` - No public docstring in the audited version.
- **method**, line 168: `SchemeDescription.from_json(path: str) -> 'SchemeDescription'` - No public docstring in the audited version.
- **method**, line 137: `SchemeDescription.to_dict() -> dict` - No public docstring in the audited version.
- **method**, line 162: `SchemeDescription.to_json(path: str, pretty: bool = True) -> None` - No public docstring in the audited version.
- **method**, line 203: `SchemeDescription.to_scheme_descriptor() -> 'SchemeDescriptor'` - Convert to a DSL SchemeDescriptor for round-trip rendering.
- **class**, line 101: `ScopeEntry` - One entry in a substrate scope table.
- **method**, line 111: `ScopeEntry.to_dict() -> dict` - No public docstring in the audited version.
- **class**, line 56: `SpeciesRecord` - One chemical entity identified in the scheme.
- **method**, line 75: `SpeciesRecord.to_dict() -> dict` - No public docstring in the audited version.
- **class**, line 81: `StepRecord` - One reaction step extracted from the scheme.
- **method**, line 94: `StepRecord.to_dict() -> dict` - No public docstring in the audited version.

## `perception.scheme_refine`

- **function**, line 925: `analyze_bond_changes(mapped_rxn: str) -> Dict[str, list]` - Analyze bond changes from an atom-mapped reaction SMILES.
- **function**, line 391: `apply_corrections(desc: SchemeDescription, corrections: Dict[str, Any]) -> SchemeDescription` - Apply LLM corrections to a SchemeDescription.
- **function**, line 1013: `describe_transformation(changes: Dict[str, list], max_changes: int = 5) -> str` - Generate a chemical English description from bond-change analysis.
- **function**, line 54: `enrich_aligned_names(desc: SchemeDescription, verbose: bool = False) -> int` - Replace canonical IUPAC names with aligned alternatives per step.
- **function**, line 1073: `generate_llm_narrative(desc: SchemeDescription, ml_enrichment: Optional[Dict[int, Dict]] = None) -> str` - Generate a chemist-quality natural language narrative.
- **function**, line 298: `generate_prompt(desc: SchemeDescription, image_path: Optional[str] = None) -> str` - Generate a structured prompt for LLM refinement.
- **function**, line 455: `load_corrections_file(path: str) -> Dict[str, Dict[str, Any]]` - Load a corrections file mapping source filenames to corrections.
- **function**, line 468: `refine_scheme(desc: SchemeDescription, corrections: Optional[Dict[str, Any]] = None) -> SchemeDescription` - Refine a scheme description.

## `perception.scheme_segmenter`

- **function**, line 506: `classify_scheme_complexity(cdxml_path: str) -> str` - Classify a CDXML file's complexity for mode selection.
- **class**, line 41: `SchemeSegment` - One independent sub-scheme identified within a CDXML file.
- **method**, line 51: `SchemeSegment.to_dict() -> dict` - No public docstring in the audited version.
- **function**, line 291: `segment_scheme(cdxml_path: str, verbose: bool = False) -> SegmentationResult` - Detect independent sub-schemes within a CDXML file.
- **class**, line 58: `SegmentationResult` - Result of segmenting a CDXML file.
- **property**, line 71: `SegmentationResult.num_segments` - No public docstring in the audited version.
- **method**, line 74: `SegmentationResult.to_dict() -> dict` - No public docstring in the audited version.

## `perception.spatial_assignment`

- **class**, line 49: `ArrowVector` - Fully characterised arrow with direction, type, and spatial metadata.
- **function**, line 975: `assign_elements(arrows: List[ArrowVector], page: ET.Element, layout: Optional[LayoutPattern] = None) -> Tuple[List[RawStep], List[AssignmentResult]]` - Assign all fragments and texts on the page to arrows.
- **class**, line 90: `AssignmentResult` - Single element-to-arrow assignment with confidence.
- **function**, line 211: `build_arrow_vector(arrow: ET.Element) -> ArrowVector` - Build an :class:`ArrowVector` from a CDXML ``<arrow>`` or ``<graphic>`` element.
- **function**, line 243: `build_arrow_vectors(page: ET.Element) -> List[ArrowVector]` - Find all arrows on the page and build ArrowVector objects.
- **function**, line 469: `classify_layout(arrows: List[ArrowVector]) -> LayoutPattern` - Classify the scheme layout pattern from arrow geometry.
- **function**, line 347: `cluster_arrows_into_rows(arrows: List[ArrowVector], gap_threshold: Optional[float] = None) -> List[List[ArrowVector]]` - Cluster arrows into horizontal rows by y-coordinate.
- **function**, line 274: `collect_fragments(page: ET.Element) -> List[FragmentInfo]` - Collect all fragments on the page with spatial metadata.
- **function**, line 294: `collect_texts(page: ET.Element) -> List[TextInfo]` - Collect all free text elements on the page with positions.
- **class**, line 73: `FragmentInfo` - Spatial metadata for a CDXML fragment.
- **class**, line 63: `LayoutPattern` - No public docstring in the audited version.
- **function**, line 168: `point_to_segment_distance(point: Tuple[float, float], seg_start: Tuple[float, float], seg_end: Tuple[float, float]) -> float` - Shortest distance from *point* to the line segment [seg_start, seg_end].
- **function**, line 124: `project_onto_arrow(point: Tuple[float, float], tail: Tuple[float, float], head: Tuple[float, float]) -> Tuple[float, float]` - Project *point* into the arrow-relative coordinate system.
- **class**, line 100: `RawStep` - One reaction step derived from spatial assignment.
- **class**, line 82: `TextInfo` - Spatial metadata for a CDXML text element.
