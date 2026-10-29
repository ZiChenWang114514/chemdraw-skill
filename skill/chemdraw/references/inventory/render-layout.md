# Render Layout Public Symbols

> Generated from cdxml-toolkit 0.7.0a3. Curated guidance: [../toolkit-render-layout-interfaces.md](../toolkit-render-layout-interfaces.md).

## `cdxml_builder`

- **function**, line 619: `build_molecule_cdxml(atoms: List[Dict], bonds: List[Dict], start_id: int = 1000) -> str` - Build a CDXML document containing a single molecule fragment.
- **function**, line 663: `build_reaction_cdxml(reactants: List[Dict], products: List[Dict], conditions: Optional[Dict] = None, arrow_y: Optional[float] = None, arrow_tail_x: Optional[float] = None, arrow_head_x: Optional[float] = None, start_id: int = 1000) -> str` - Build a CDXML reaction scheme document.
- **function**, line 90: `element_number(symbol: str) -> int` - Atomic number for *symbol*; 0 only when the symbol is not an element.

## `cdxml_utils`

- **function**, line 319: `arrow_endpoints(arrow: ET.Element) -> Tuple[float, float, float, float]` - Return ``(tail_x, tail_y, head_x, head_y)`` from an arrow element.
- **function**, line 296: `build_id_map(parent: ET.Element) -> Dict[str, ET.Element]` - Build ``{id_string: element}`` map for all descendants with an ``id`` attribute.
- **function**, line 143: `drawn_fragment_bbox(frag: ET.Element) -> Optional[Tuple[float, float, float, float]]` - Box around what a <fragment> draws: its atoms and their labels.
- **function**, line 28: `fragment_bbox(frag: ET.Element) -> Optional[Tuple[float, float, float, float]]` - Atom-only bounding box for a <fragment> element.
- **function**, line 222: `fragment_bbox_with_label_extension(frag: ET.Element) -> Optional[Tuple[float, float, float, float]]` - Atom-only bounding box with hanging-label extension.
- **function**, line 179: `fragment_bottom_has_hanging_label(frag: ET.Element) -> bool` - True if the bottommost atom has a label that hangs below it.
- **function**, line 168: `fragment_centroid(frag: ET.Element) -> Optional[Tuple[float, float]]` - Center point of :func:`fragment_bbox`.
- **function**, line 74: `hydrogens_lead(symbol, hydrogens) -> bool` - Whether ChemDraw writes a lone atom's hydrogens first (H2O, HCl, not OH or NH3).
- **function**, line 99: `label_boxes(frag: ET.Element) -> list` - ``(atom, box)`` for every atom label of a <fragment>, as drawn.
- **function**, line 346: `parse_cdxml(path: str) -> ET.ElementTree` - Parse a CDXML file, returning an :class:`~xml.etree.ElementTree.ElementTree`.
- **function**, line 247: `recompute_text_bbox(t_elem: ET.Element) -> None` - Recompute and set BoundingBox on a ``<t>`` element.
- **function**, line 351: `write_cdxml(tree: ET.ElementTree, path: str) -> None` - Write *tree* to *path*, re-inserting the DOCTYPE declaration.

## `coord_normalizer`

- **function**, line 304: `infer_hydrogens(atoms: List[Dict], bonds: List[Dict]) -> List[Dict]` - For any atom that has no explicit num_hydrogens set, calculate it from the default valence minus the sum of bond orders from bonds.
- **function**, line 142: `normalize_coords(atoms: List[Dict], bonds: List[Dict], center_x: float = 200.0, center_y: float = 300.0, flip_y: bool = True, target_bond_length: float = ACS_BOND_LENGTH_PT, strip_hydrogens: bool = True) -> Tuple[List[Dict], List[Dict]]` - Normalize atom coordinates and return (atoms, bonds) ready for cdxml_builder.
- **function**, line 204: `normalize_molecule(molecule: Dict, center_x: float = 200.0, center_y: float = 300.0, flip_y: bool = True, target_bond_length: float = ACS_BOND_LENGTH_PT, strip_hydrogens: bool = True) -> Dict` - Convenience wrapper: take a molecule dict {"atoms": [...], "bonds": [...]} and return a new dict with normalised coordinates.
- **function**, line 233: `normalize_reaction(reactants: List[Dict], products: List[Dict], reactant_y: float = 300.0, product_y: float = 300.0, reactant_start_x: float = 50.0, product_start_x: float = 350.0, molecule_gap: float = 80.0, flip_y: bool = True, target_bond_length: float = ACS_BOND_LENGTH_PT, strip_hydrogens: bool = True) -> Tuple[List[Dict], List[Dict]]` - Normalize a set of reactant and product molecules for a reaction scheme.
- **function**, line 101: `strip_explicit_hydrogens(atoms: List[Dict], bonds: List[Dict]) -> Tuple[List[Dict], List[Dict]]` - Remove explicit hydrogen atoms from the atom/bond lists.

## `layout.alignment`

- **function**, line 972: `align_product_to_reference(root: ET.Element, ref_cdxml_path: str, verbose: bool = False, timeout: int = 30) -> bool` - Align the product fragment to the best-matching structure in a reference CDXML file.
- **function**, line 120: `compute_rigid_rotation_2d(old_pts: List[Tuple[float, float]], new_pts: List[Tuple[float, float]]) -> Tuple[float, float]` - Compute the optimal 2D rotation from matched point pairs (Kabsch).
- **function**, line 60: `filtered_atom_nodes(frag: ET.Element) -> List[ET.Element]` - Return only real atom <n> nodes from a fragment, filtering out ExternalConnectionPoint, Fragment, and Unspecified pseudo-nodes.
- **function**, line 72: `fragment_centroid(frag: ET.Element) -> Tuple[float, float]` - Compute centroid from direct-child node positions.
- **function**, line 87: `get_visible_carbon_positions(frag: ET.Element) -> List[Tuple[float, float]]` - Extract positions of visible carbon atoms for Kabsch alignment.
- **function**, line 331: `kabsch_align_fragment_to_product(reagent_frag: ET.Element, product_frag: ET.Element, cs_bridge, verbose: bool = False) -> bool` - Align a reagent fragment's orientation to match its substructure in the product using rigid-body Kabsch rotation.
- **function**, line 594: `kabsch_align_to_product(root: ET.Element, cs_bridge = None, verbose: bool = False, frag_ids: Optional[Set[str]] = None) -> List[str]` - Align fragments to product orientation using Kabsch rigid rotation.
- **function**, line 277: `make_abbrev_dummy_copy(frag: ET.Element) -> ET.Element` - Create a deep copy of a fragment with abbreviation nodes replaced by dummy atoms (Iodine, Element=53).
- **function**, line 151: `match_and_compute_rotation(src_positions: List[Tuple[float, float]], tgt_positions: List[Tuple[float, float]]) -> Tuple[float, float, float]` - Match atoms by normalized nearest-neighbor and compute Kabsch rotation.
- **function**, line 1136: `rdkit_align_to_product(root: ET.Element, verbose: bool = False, timeout: int = 30) -> int` - Align all non-product fragments to the product's orientation.
- **function**, line 211: `rotate_fragment_in_place(frag: ET.Element, cos_a: float, sin_a: float, cx: float, cy: float) -> None` - Rotate all coordinates in a fragment around (cx, cy).
- **function**, line 1262: `rxnmapper_align_to_product(root: ET.Element, verbose: bool = False, timeout: int = 120) -> int` - Align non-product fragments using RXNMapper atom maps.
- **function**, line 44: `sp_fragment_to_cdxml(frag: ET.Element) -> str` - Wrap a single <fragment> element in a minimal CDXML document.
- **function**, line 306: `translate_subtree(elem: ET.Element, dx: float, dy: float) -> None` - Recursively shift all p and BoundingBox attributes by (dx, dy).

## `layout.label_anchors`

- **function**, line 6: `preserve_label_anchors(source, output)` - No public docstring in the audited version.

## `layout.reaction_cleanup`

- **function**, line 427: `approach_arrow_driven(page, step, id_map, arrow, verbose = False)` - Arrow-centric layout: - Arrow stays at a fixed reasonable length (70pt ≈ ~1 inch) - Reactants right-aligned to arrow tail with gap - Products left-aligned to arrow head with gap - Vertical centering on arrow midpoint
- **function**, line 363: `approach_bbox_center(page, step, id_map, arrow, verbose = False)` - Simple centroid-based layout: - All molecules vertically centered on arrow y - Uniform horizontal gaps between reactants, arrow, products - Above/below text centered over arrow
- **function**, line 665: `approach_chemdraw_mimic(page, step, id_map, arrow, verbose = False)` - Emulates ChemDraw's Clean Up Reaction behaviour: - Arrow length ≈ 1.5× bond length (BondLength from doc) - Molecules placed so nearest atom is ~1 bond length from arrow tip - Above-arrow objects stacked: structures first, then text - Below-arrow objects similarly stacked - Everything vertically centered on a common y-line - Separate above-arrow fragments from above-arrow text labels
- **function**, line 554: `approach_compact(page, step, id_map, arrow, verbose = False)` - Compact layout for space-constrained output: - Minimal gaps (5pt) - Short arrow (45pt) - Tight vertical stacking
- **function**, line 608: `approach_golden_ratio(page, step, id_map, arrow, verbose = False)` - Golden ratio aesthetics: - Arrow length = φ × average molecule width - Gaps = average molecule width / φ - Pleasing visual proportions
- **function**, line 483: `approach_proportional(page, step, id_map, arrow, verbose = False)` - Proportional spacing: - Arrow length = 0.6× the average molecule width - Gaps scale with molecule size - Looks balanced for both small and large molecules
- **function**, line 1050: `run_cleanup(input_path: str, output_path: str, approach: str = 'chemdraw_mimic', verbose: bool = False) -> dict` - Run one cleanup approach on a CDXML file.

## `layout.scheme_merger`

- **function**, line 1074: `adjacent_place(trees: List[ET.ElementTree], *, log = None) -> ET.ElementTree` - Place multiple independent schemes side by side on one page.
- **function**, line 846: `auto_detect(schemes: List[ParsedScheme], log = None) -> MergePlan` - Analyze N schemes and determine merge strategy.
- **function**, line 791: `classify_pair(ps_a: ParsedScheme, ps_b: ParsedScheme) -> str` - Classify the relationship between two parsed schemes.
- **class**, line 70: `EquivInfo` - Equiv value for one reagent in one scheme.
- **function**, line 968: `execute_merge_plan(schemes: List[ParsedScheme], plan: MergePlan, *, equiv_mode: str = 'default', ref_cdxml: str = None, allow_adjacent: bool = True, log = None) -> ET.ElementTree` - Execute a merge plan: parallel within groups, sequential between.
- **class**, line 814: `MergePlan` - Result of auto-detection: how to merge N schemes.
- **method**, line 823: `MergePlan.describe() -> str` - Human-readable summary of the merge plan.
- **function**, line 1164: `parallel_merge(schemes: List[ParsedScheme], *, equiv_mode: str = 'default', strict: bool = True, log = None) -> ET.ElementTree` - Merge schemes for the same reaction into one with stacked run arrows.
- **function**, line 229: `parse_scheme(path: str, log = None) -> ParsedScheme` - Parse an ELN-enriched CDXML scheme file.
- **class**, line 77: `ParsedScheme` - A parsed ELN-enriched CDXML scheme with all metadata extracted.
- **method**, line 130: `ParsedScheme.get_product_smiles_set() -> set` - Set of canonical SMILES for product fragments.
- **method**, line 121: `ParsedScheme.get_reactant_smiles_set() -> set` - Set of canonical SMILES for reactant fragments.
- **class**, line 62: `RunArrowData` - Data extracted from one run arrow (mass/yield for one run).
- **function**, line 1465: `sequential_merge(schemes: List[ParsedScheme], *, ref_cdxml: str = None, log = None) -> ET.ElementTree` - Merge schemes where step N product = step N+1 starting material.

## `render.auto_layout`

- **function**, line 31: `auto_layout(reaction_json_path: str, include_equiv: bool = True) -> SchemeDescriptor` - Generate a default SchemeDescriptor from reaction_parser output.
- **function**, line 146: `auto_layout_to_cdxml(reaction_json_path: str, output_path: Optional[str] = None, include_equiv: bool = True) -> str` - Generate and render a scheme from reaction_parser JSON.

## `render.compact_parser`

- **function**, line 294: `parse_compact(text: str) -> SchemeDescriptor` - Parse compact syntax text into a :class:`SchemeDescriptor`.
- **function**, line 651: `parse_compact_file(path: str) -> SchemeDescriptor` - Read a file and parse it as compact syntax.
- **class**, line 32: `ParseError` - Syntax or semantic error with optional line number.

## `render.parser`

- **function**, line 62: `parse_yaml(source: Union[str, Path]) -> SchemeDescriptor` - Parse a YAML file or string into a SchemeDescriptor.
- **class**, line 57: `SchemeParseError` - Raised when YAML content is invalid or violates schema rules.

## `render.renderer`

- **function**, line 2588: `render(scheme: SchemeDescriptor, yaml_dir: Optional[str] = None) -> str` - Render a scheme and retain per-fragment output-derived validation receipts.
- **function**, line 2610: `render_to_file(scheme: SchemeDescriptor, output_path: str, yaml_dir: Optional[str] = None) -> None` - Render and write to a file.
- **function**, line 2576: `render_with(build) -> str` - Build page content with ``build(ids) -> inner_xml`` and wrap it like a rendered scheme.
- **class**, line 146: `ResolvedFragment` - A structure that has been resolved to atom/bond data + XML.
- **class**, line 161: `ResolvedStep` - A step with all structures resolved and laid out.

## `render.route_graph`

- **function**, line 48: `classify_route(steps: list[StepDescriptor]) -> tuple[str, list[int]]` - Return ``(kind, order)``: kind is linear, convergent or divergent, order the step indices to draw.
- **function**, line 69: `convergent_sections(steps: list[StepDescriptor]) -> list[list[StepDescriptor]]` - Rows of a convergent route: each arm first, then the merge row (with any chain after it).

## `render.schema`

- **class**, line 26: `ArrowContent` - Content placed above or below an arrow.
- **class**, line 46: `RunArrowEntry` - A single run (one scale) of a reaction step.
- **class**, line 79: `SchemeDescriptor` - Complete scheme description.
- **class**, line 71: `SectionDescriptor` - A section in a stacked-rows layout.
- **class**, line 33: `StepDescriptor` - A single reaction step.
- **class**, line 54: `StepRunArrows` - Run arrows for a specific step (may have multiple scales).
- **class**, line 15: `StructureRef` - Reference to a chemical structure — resolved later by the renderer.

## `render.scheme_maker`

- **function**, line 293: `build_scheme(input_path: str, output: Optional[str] = None, approach: str = 'chemdraw_mimic', align_mode: str = 'rdkit', run_arrow: bool = True, verbose: bool = False) -> str` - Build a CDXML reaction scheme from a reaction JSON file.

## `render.scheme_yaml_writer`

- **function**, line 1089: `build_merged_scheme_yaml_dict(json_paths: List[str], layout: str = 'auto', include_run_arrows: bool = True, use_eln_labels: bool = False) -> Dict[str, Any]` - Build a combined YAML dict from multiple reaction JSONs.
- **function**, line 131: `build_scheme_yaml_dict(json_path: str, layout: str = 'auto', include_run_arrows: bool = True, use_eln_labels: bool = False) -> Dict[str, Any]` - Read reaction JSON and return the YAML dict (without writing to disk).
- **class**, line 487: `MergePlan` - How to combine N reaction JSONs into a merged scheme.
- **method**, line 493: `MergePlan.describe() -> str` - No public docstring in the audited version.
- **class**, line 470: `ReactionSummary` - Extracted summary of one reaction JSON for merge classification.
- **function**, line 1356: `write_merged_scheme_yaml(json_paths: List[str], output_path: str, layout: str = 'auto', include_run_arrows: bool = True, use_eln_labels: bool = False) -> str` - Read multiple reaction JSONs, detect relationships, write merged YAML.
- **function**, line 78: `write_scheme_yaml(json_path: str, output_path: str, layout: str = 'auto', include_run_arrows: bool = True, use_eln_labels: bool = False) -> str` - Read reaction JSON, make layout decisions, write YAML file.

## `text_formatting`

- **function**, line 163: `build_formatted_s_xml(text: str, font: str = '3', size: str = '10', color: str = '0', italic_font: str | None = None) -> str` - Build one or more CDXML ``<s>`` elements with correct chemical styling.
- **function**, line 97: `needs_subscript(text: str) -> bool` - Determine whether *text* contains chemical-formula digits that should be rendered as subscripts in ChemDraw.
- **function**, line 79: `normalize_condition_text(text: str) -> str` - Write temperatures, room temperature and times the way papers do.
- **function**, line 139: `split_italic_prefix(text: str) -> Tuple[str, str]` - Split *text* into ``(italic_prefix, remainder)`` if it starts with a recognised chemistry italic prefix (see :data:`ITALIC_PREFIXES`).
