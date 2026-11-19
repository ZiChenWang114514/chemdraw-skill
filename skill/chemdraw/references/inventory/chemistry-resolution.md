# Chemistry Resolution Public Symbols

> Generated from cdxml-toolkit 0.7.0a3. Curated guidance: [../toolkit-chemistry-resolution-interfaces.md](../toolkit-chemistry-resolution-interfaces.md).

## `naming.aligned_namer`

- **class**, line 1533: `AlignmentResult` - Result of aligning names for an SM→product pair.
- **property**, line 1553: `AlignmentResult.alignment_quality` - Classify alignment: ALIGNED / SEMI-ALIGNED / UNALIGNED.
- **property**, line 1549: `AlignmentResult.is_aligned` - No public docstring in the audited version.
- **function**, line 238: `chem_token_diff_count(a: str, b: str) -> float` - Token diff count using chemistry-aware tokeniser with soft equivalences.
- **function**, line 425: `extract_parent_ring(parent: str) -> str` - Extract core ring system from a parent name string.
- **function**, line 1708: `find_aligned_name_sequence(smiles_list: List[str], verbose: bool = False, parent_penalty: float = 100.0, timeout: float = 30.0) -> SequenceAlignmentResult` - Pick one IUPAC name per intermediate to minimise parent-ring switches.
- **function**, line 1567: `find_aligned_names(sm_smiles: str, prod_smiles: str, verbose: bool = False, preferred_parent: Optional[str] = None) -> AlignmentResult` - Find aligned name pairs for SM→product that share a naming parent.
- **function**, line 2243: `format_molecular_diff(sm_smiles: str, prod_smiles: str, alignment_result: Optional['AlignmentResult'] = None) -> str` - Plain-text molecular diff: ``fluoro → phenyl``.
- **function**, line 2283: `format_molecular_diff_html(sm_smiles: str, prod_smiles: str, alignment_result: Optional['AlignmentResult'] = None) -> str` - HTML molecular diff with coloured spans.
- **function**, line 1483: `format_name_diff(name1: str, name2: str) -> str` - Plain-text summary of changes between two aligned names.
- **function**, line 1501: `format_name_diff_html(name1: str, name2: str) -> str` - Inline HTML showing the diff between two aligned names.
- **class**, line 1898: `FragmentChange` - One changed fragment in a molecular diff.
- **function**, line 2037: `molecular_diff(sm_smiles: str, prod_smiles: str, min_mcs_ratio: float = 0.4, verbose: bool = False) -> MolecularDiffResult` - Compute molecular-level diff between SM and product using MCS.
- **class**, line 1908: `MolecularDiffResult` - Result of MCS-based molecular diff between SM and product.
- **function**, line 1448: `name_diff(name1: str, name2: str) -> List[Tuple[str, str, str]]` - Token-level diff between two IUPAC names.
- **function**, line 94: `name_similarity(name1: str, name2: str) -> float` - Compute similarity between two names as 1 - normalized Levenshtein.
- **class**, line 1691: `SequenceAlignmentResult` - Result of aligning names across a multi-step synthetic route.
- **property**, line 1704: `SequenceAlignmentResult.is_fully_aligned` - No public docstring in the audited version.

## `naming.mol_builder`

- **function**, line 1915: `apply_reaction(reaction_name: str, substrate: str, reagent: Optional[str] = None) -> Dict[str, Any]` - Apply a named reaction template to transform a substrate.
- **function**, line 741: `assemble_name(parent: str, substituents: List[Dict[str, str]], validate: bool = True, use_network: bool = True) -> Dict[str, Any]` - Assemble an IUPAC name from a parent and substituent list.
- **function**, line 2118: `deprotect(smiles: str) -> Dict[str, Any]` - Remove common protecting groups from a molecule.
- **function**, line 2268: `draw_molecule(mol_json: Dict[str, Any], output_path: Optional[str] = None) -> Dict[str, Any]` - Render a single molecule to a standalone CDXML document.
- **function**, line 1248: `enumerate_names(identifier: str, use_network: bool = True) -> Dict[str, Any]` - Enumerate alternative IUPAC name forms for a molecule.
- **function**, line 665: `get_prefix_form(group: str, use_network: bool = True) -> Dict[str, Any]` - Get the IUPAC substituent prefix form for a chemical group.
- **function**, line 3179: `get_tool_definitions() -> List[Dict[str, Any]]` - Return tool schemas suitable for LLM function calling.
- **function**, line 1866: `list_reactions(category: Optional[str] = None) -> Dict[str, Any]` - List available named reaction templates.
- **function**, line 2615: `modify_molecule(mol_json: Dict[str, Any], operation: str, **kwargs: Any) -> Dict[str, Any]` - Modify a molecule and verify the change with a structural diff.
- **function**, line 854: `modify_name(name: str, operation: str, target: Optional[str] = None, replacement: Optional[str] = None, locant: Optional[str] = None, validate: bool = True, use_network: bool = True) -> Dict[str, Any]` - Modify an IUPAC name by swapping, adding, or removing a substituent.
- **function**, line 1171: `name_to_structure(name: str, output_format: str = 'cdxml') -> Dict[str, Any]` - Convert a chemical name to a structure in the requested format.
- **function**, line 487: `resolve_compound(query: str, use_network: bool = True) -> Dict[str, Any]` - Resolve any chemical identifier to a rich molecule descriptor.
- **function**, line 628: `resolve_to_smiles(query: str, use_network: bool = True) -> Dict[str, Any]` - Resolve a chemical identifier to its canonical SMILES string.
- **function**, line 1133: `validate_name(name: str, use_network: bool = True) -> Dict[str, Any]` - Validate an IUPAC name and return its SMILES if valid.

## `naming.name_decomposer`

- **class**, line 42: `Alternative` - One alternative IUPAC name for the molecule.
- **class**, line 31: `BracketNode` - A parenthesised group in an IUPAC name.
- **function**, line 134: `classify_node(node: BracketNode) -> str` - Quick regex classification of a bracket group.
- **function**, line 814: `construct_yl_form(parent_name: str, locant: str) -> List[str]` - Construct candidate '-yl' substituent forms from a parent name.
- **function**, line 2193: `decompose_name(smiles: str, max_depth: int = -1, verbose: bool = False, timeout: Optional[float] = 30.0, _deadline: Optional[float] = None) -> DecompositionResult` - Main entry point: decompose an IUPAC name into alternatives.
- **function**, line 2604: `decompose_name_with_rgroups(smiles: str, labels = None, verbose: bool = False) -> DecompositionResult` - Decompose a molecule with R-group placeholders using dual-probe consensus.
- **class**, line 54: `DecompositionResult` - No public docstring in the audited version.
- **function**, line 884: `find_prefix_substituents(name: str, verbose: bool = False, skip_single_prefix: bool = False) -> List[BracketNode]` - Detect non-bracketed substituent prefixes in a name.
- **class**, line 1156: `FragmentResult` - Result of splitting a molecule into parent and substituent.
- **function**, line 1421: `generate_alternative(full_name: str, canonical_smiles: str, node: BracketNode, verbose: bool = False, max_depth: int = 0, _deadline: Optional[float] = None) -> List[Alternative]` - Generate alternative names by swapping parent ↔ substituent at one bracket.
- **function**, line 1268: `generate_alternative_from_prefix(full_name: str, canonical_smiles: str, node: BracketNode, verbose: bool = False, max_depth: int = 0, _deadline: Optional[float] = None) -> List[Alternative]` - Generate alternatives for a prefix substituent (no brackets).
- **function**, line 849: `get_locant_via_at_probe(fragment_smiles: str, attach_idx: int) -> Optional[str]` - Add At at attachment point, name via ChemDraw, extract locant.
- **function**, line 752: `get_parent_smiles_from_at_probe(full_name: str, node: BracketNode) -> Optional[Tuple[str, int]]` - Replace bracket group with 'astato', resolve to SMILES, remove the At to get the parent fragment + attachment index.
- **function**, line 772: `get_sub_smiles_from_bracket(node: BracketNode) -> Optional[str]` - Try to resolve the bracket content as a standalone chemical name.
- **function**, line 552: `name_fragment_as_substituent(frag_smiles: str, verbose: bool = False) -> Optional[str]` - Convert a [*]-bearing fragment SMILES to its IUPAC substituent prefix.
- **function**, line 68: `parse_bracket_tree(name: str) -> BracketNode` - Parse parenthesised groups in an IUPAC name into a tree.
- **function**, line 2490: `prepare_rgroup_smiles(smiles: str, labels = None, probe_set = None, label_probe_map = None) -> Tuple[Optional[str], List[RGroupMapping]]` - Replace dummy atoms (*) with halogen probe atoms.
- **class**, line 2466: `RGroupMapping` - Tracks an R-group label and its position in the molecule.
- **function**, line 680: `validate_as_substituent(full_name: str, node: BracketNode, verbose: bool = False) -> bool` - Check if replacing a bracket group with 'astato' gives a valid name.

## `rdkit_utils`

- **function**, line 723: `avg_bond_length_from_atoms(atoms_data: List[dict], mol) -> float` - Average bond length computed from CDXML atom coordinates.
- **function**, line 534: `cleanup_fragment_rdkit(frag_elem: ET.Element, verbose: bool = False) -> bool` - Clean up a single fragment's 2D geometry using RDKit.
- **function**, line 111: `frag_to_mol(frag_elem: ET.Element)` - Convert a CDXML <fragment> to an RDKit Mol with atom metadata.
- **function**, line 508: `frag_to_molblock(frag_elem: ET.Element) -> Optional[str]` - Convert a CDXML <fragment> to a MOL block string (with CDXML coords).
- **function**, line 452: `frag_to_mw(frag_elem: ET.Element) -> Optional[float]` - Compute molecular weight from a CDXML <fragment>.
- **function**, line 273: `frag_to_smiles(frag_elem: ET.Element) -> Optional[str]` - Convert a CDXML <fragment> to a canonical SMILES string.
- **function**, line 393: `frag_to_smiles_chemscript(frag_elem: ET.Element) -> Optional[str]` - Convert a CDXML ``<fragment>`` to SMILES using ChemScript.
- **function**, line 290: `frag_to_smiles_resolved(frag_elem: ET.Element) -> Optional[str]` - Convert a CDXML <fragment> to SMILES, resolving abbreviation groups.
- **function**, line 253: `keep_stereo_or_restore(frag_elem: ET.Element, snapshot, mol, atoms_data: List[dict]) -> bool` - After atoms of *frag_elem* moved, redraw its wedges and compare the molecule with *mol* (read before the move).  If the chemistry changed, restore the attributes in *snapshot* (taken before the move) and return False: the re-layout is abandoned.
- **function**, line 708: `rdkit_default_bond_length() -> float` - RDKit's default 2D depiction bond length (cached).
- **function**, line 209: `rewrite_wedges(frag_elem: ET.Element, mol, atoms_data: List[dict]) -> None` - Redraw wedge and hash bonds of *frag_elem* from *mol*'s stereo.
- **function**, line 728: `set_cdxml_conformer(mol, atoms_data: List[dict], scale: float = 1.0)` - Set conformer from CDXML coordinates (y-flipped, scaled to RDKit space).
- **function**, line 248: `snapshot_attributes(frag_elem: ET.Element) -> List[Tuple[ET.Element, Dict[str, str]]]` - Attributes of every element under *frag_elem*, for :func:`keep_stereo_or_restore`.

## `resolve.cas_resolver`

- **function**, line 361: `resolve_batch(cas_list: List[str], include_coords: bool = False, delay: float = REQUEST_DELAY) -> List[Dict[str, Any]]` - Resolve a list of CAS numbers with rate limiting.
- **function**, line 106: `resolve_cas(cas: str, include_coords: bool = False) -> Optional[Dict[str, Any]]` - Resolve a single CAS number via PubChem PUG REST.
- **function**, line 406: `resolve_name_to_smiles(name: str) -> Optional[str]` - Resolve a chemical name to a canonical SMILES via PubChem PUG REST.

## `resolve.condensed_formula`

- **function**, line 617: `resolve_condensed_formula(formula: str) -> Optional[str]` - Parse a condensed structural formula to canonical SMILES.
- **function**, line 81: `tokenize(formula: str) -> List[Tuple[str, Any]]` - Tokenize a condensed structural formula.

## `resolve.jre_manager`

- **function**, line 229: `ensure_java_on_path(download: bool = True) -> bool` - Discover Java and expose its executable directory to subprocesses.
- **function**, line 203: `get_java(download: bool = True) -> Optional[str]` - Return Java from the system, a verified installation, or an approved download.
- **function**, line 110: `install_jre_archive(archive_path: str | os.PathLike[str], *, expected_sha256: str | None = None, source: str = 'local') -> Optional[str]` - Verify and install a JRE ZIP without modifying an existing installation.

## `resolve.network_policy`

- **function**, line 15: `network_allowed() -> bool` - No public docstring in the audited version.
- **function**, line 19: `offline_reason(what: str) -> str` - No public docstring in the audited version.

## `resolve.opsin_call`

- **function**, line 15: `py2opsin_private(py2opsin: Callable[..., Any], name: str) -> Any` - No public docstring in the audited version.

## `resolve.reagent_db`

- **function**, line 363: `get_reagent_db() -> ReagentDB` - Return the shared ReagentDB singleton (loaded on first call).
- **class**, line 57: `ReagentDB` - In-memory reagent database with two-tier lookup.
- **method**, line 260: `ReagentDB.display_for_name(name: str) -> Optional[str]` - Return display string for a name/alias, or None if unknown.
- **method**, line 306: `ReagentDB.display_for_smiles(smiles: str) -> Optional[str]` - Return display string for a SMILES, or None if unknown.
- **method**, line 278: `ReagentDB.entry_for_name(name: str) -> Optional[dict]` - Return the full entry dict for a name/alias, or None.
- **method**, line 325: `ReagentDB.entry_for_smiles(smiles: str) -> Optional[dict]` - Return the curated (tier-1) entry for a SMILES, or None.
- **method**, line 192: `ReagentDB.entry_smiles(entry: dict) -> Optional[str]` - No public docstring in the audited version.
- **method**, line 237: `ReagentDB.lookup_name(name: str, tiers: Tuple[str, ...] = ('primary', 'secondary')) -> Optional[Tuple[dict, str]]` - Return ``(entry, tier)`` for a name, or None.
- **method**, line 335: `ReagentDB.resolve_display(name: str) -> str` - Return the display string for *name*, or *name* itself if unknown.
- **method**, line 270: `ReagentDB.role_for_name(name: str) -> Optional[str]` - Return role string for a name/alias, or None.
- **method**, line 317: `ReagentDB.role_for_smiles(smiles: str) -> Optional[str]` - Return role string for a SMILES, or None.
- **method**, line 344: `ReagentDB.smiles_role_display(smiles: str) -> Optional[Tuple[str, str]]` - Return (role, display) for a SMILES, matching the old ROLE_BY_SMILES dict interface.

## `resolve.reagent_quality`

- **function**, line 102: `build_secondary_quarantine(secondary: dict) -> dict` - Return the quarantine document for the secondary table.
- **function**, line 45: `nonmetal_radical_atoms(mol) -> List[str]` - Symbols of main-group atoms that carry unpaired electrons.
- **function**, line 64: `same_formula(a: str, b: str) -> bool` - Compare two molecular formulae element by element (D and T count as H).
- **function**, line 51: `unspecified_stereocentres(mol) -> int` - No public docstring in the audited version.

## `resolve.superatom_table`

- **function**, line 135: `get_abbrev_label(node) -> Optional[str]` - Extract the visible abbreviation label text from a CDXML node.
- **function**, line 78: `get_superatom_table() -> Dict[str, str]` - Return the label → SMILES lookup table (singleton, built on first call).
- **function**, line 95: `lookup_mw(label: str) -> Optional[float]` - Look up a superatom label and return its standalone MW, or None.
- **function**, line 90: `lookup_smiles(label: str) -> Optional[str]` - Look up a superatom label and return its SMILES, or None.
