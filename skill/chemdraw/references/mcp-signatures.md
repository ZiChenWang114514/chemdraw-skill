# MCP Tool Reference

> Generated from the live community registry. Do not edit manually.

Distribution: `cdxml-toolkit-community 0.7.0a1`
Profile: `codex`
Tools: `38`

## Extended Tools

### `analyze_lcms_series(files: list[str], output_path: Optional[str] = None, rt_tolerance: float = 0.02, mz_tolerance: float = 0.5, trend_threshold: float = 0.2, ignore_instrument: bool = False) -> dict[str, typing.Any]`

Analyze a chronological series of standard LCMS PDF reports.

### `assemble_lab_book(input_dir: str, experiment: Optional[str] = None, tracking_json: Optional[str] = None, output_path: Optional[str] = None) -> dict[str, typing.Any]`

Assemble a deterministic lab-book entry from experiment files.

### `batch_compare_molecules(pairs: list[dict[str, typing.Any]], fingerprint: str = 'morgan', radius: int = 2, n_bits: int = 2048) -> dict[str, typing.Any]`

Compare up to 256 molecule pairs with one ChemScript bridge session.

### `batch_embed_cdxml_in_office(cdxml_paths: list[str], output_path: str, margin_pt: float = 0) -> dict[str, typing.Any]`

Create PPTX or DOCX containing editable ChemDraw OLE objects.

### `clean_scheme_layout(input_path: str, output_path: Optional[str] = None, approach: str = 'chemdraw_mimic', render_preview: bool = True) -> dict[str, typing.Any]`

Clean an existing CDXML reaction layout without changing the source file.

### `compare_figure_images(reference_path: str, candidate_path: str, output_path: str) -> dict`

Compare aligned local raster previews without resizing or warping.

Output JSON contains exact pixel equality, normalized mean absolute error,
ink intersection-over-union, and dimensions. Different dimensions explicitly
fail comparison. This evaluates appearance only, never chemical identity.

### `compare_molecules(molecule_a: str, molecule_b: str, fingerprint: str = 'morgan', radius: int = 2, n_bits: int = 2048) -> dict[str, typing.Any]`

Compare two molecule representations using ChemScript identity and RDKit Tanimoto fingerprints.

### `compose_chemical_figure(manifest_path: str, output_path: str) -> dict`

Compose editable CDXML using explicit point coordinates and grounded molecules.

Read the Skill publication-figures reference for the JSON manifest schema.
Supports molecules with exact atom coordinates or template alignment, CIP/
atom labels, highlights, rich text, straight/equilibrium/resonance/retro arrows,
curved electron arrows, brackets and shapes. A template_path preserves native
objects and permits translations/text edits without flattening. Outputs final
CDXML round-trip validation; native rendering and reference comparison are
separate required steps. Never claims journal identity from export success.

### `diagnose_runtime(run_native_probe: bool = False, run_office_probe: bool = False, run_chemscript_probe: bool = False) -> dict[str, typing.Any]`

Report local runtime capabilities; native probes are explicit and temporary.

### `discover_experiment_files(input_dir: str, experiment: Optional[str] = None, output_path: Optional[str] = None) -> dict[str, typing.Any]`

Discover and classify files belonging to one experiment.

### `execute_chemscript_sdk(program: list[dict[str, typing.Any]], allow_file_io: bool = False, allow_overwrite: bool = False, allow_unsafe_interop: bool = False, max_items: int = 100) -> dict[str, typing.Any]`

Execute a declarative ChemScript SDK program in an isolated Python.NET process.

### `fill_office_template(template_path: str, manifest_path: str, output_path: Optional[str] = None) -> dict[str, typing.Any]`

Fill PPTX/DOCX text and editable ChemDraw placeholders from a manifest.

### `get_toolkit_capabilities() -> dict[str, typing.Any]`

Return versions, profile, tool schema digest, and local capability status.

### `inspect_chemdraw_objects_in_office(input_path: str, output_dir: Optional[str] = None, render_previews: bool = True) -> dict[str, typing.Any]`

Inventory editable ChemDraw objects and extract numbered CDXML previews.

### `inspect_chemscript_sdk(query: Optional[str] = None, type_name: Optional[str] = None, include_infrastructure: bool = False, offset: int = 0, limit: int = 100, output_path: Optional[str] = None) -> dict[str, typing.Any]`

Catalog every public ChemScript type/member, with filtering or a complete JSON export.

### `merge_reaction_schemes(input_paths: list[str], output_path: Optional[str] = None, mode: str = 'auto', equiv_mode: str = 'default', reference_cdxml: Optional[str] = None, allow_adjacent: bool = True, render_preview: bool = True, force_sequential: bool = False) -> dict[str, typing.Any]`

Merge parallel, sequential, or unrelated CDXML reaction schemes.

### `parse_scifinder_rdf(input_path: str, resolve_cas: bool = False, output_path: Optional[str] = None, confirm_pubchem: bool = False) -> dict[str, typing.Any]`

Parse SciFinder RDF and optionally enrich CAS data over the network.

### `polish_reaction_scheme(input_path: str, output_path: Optional[str] = None, merge_conditions: bool = True, approach: str = 'chemdraw_mimic', align_mode: str = 'rdkit', eln_csv: Optional[str] = None, reference_cdxml: Optional[str] = None, render_preview: bool = True) -> dict[str, typing.Any]`

Run the audited deterministic polishing pipeline on a CDXML scheme.

### `rdkit_workbench(molecules: list[dict], operation: str = 'inspect', options: dict | None = None, output_path: str | None = None) -> dict`

Analyze grounded molecules: inspect, stereoisomers, tautomers, mcs, r_groups, set_stereo.

Input records accept smiles/CXSMILES, molblock, or file (CDXML/MOL/SDF).
Atom indices are zero-based and refer to each input's atom order. Options:
max_results (1..128), only_unassigned (stereoisomers, default true),
include_molblock, timeout (MCS, 1..30 seconds). R-group decomposition uses
molecules[0] as the explicit core. set_stereo takes configurations={index:
R/S/unspecified} for one molecule, verifies the achieved CIP labels, and emits
a connectivity-preserving diff. Enumeration creates candidate structures,
not predictions of populations, reaction products, or experimental ratios.
Writes provenance, bounded candidate results and truncation status to JSON.

### `render_cdxml_files(input_paths: list[str], output_dir: Optional[str] = None, format: str = 'png', dpi: int = 300) -> dict[str, typing.Any]`

Render one or more CDXML files through native ChemDraw COM.

### `replace_chemdraw_objects_in_office(input_path: str, replacements_manifest: str, output_path: Optional[str] = None, render_pdf_preview: bool = True) -> dict[str, typing.Any]`

Replace selected ChemDraw OLE contents and previews without moving them.

### `segment_large_scheme(cdxml_path: str, output_path: Optional[str] = None, verbose: bool = False) -> dict[str, typing.Any]`

Segment a disconnected or multi-panel CDXML scheme into logical regions.

## Official Tools

### `convert_cdx_cdxml(input_path: str, output_path: Optional[str] = None) -> dict`

Convert bidirectionally between CDX (binary) and CDXML (XML) formats.

    Direction is detected from the file extension:
    - .cdx input  → .cdxml output
    - .cdxml input → .cdx output

    Uses available backends in order: ChemDraw COM (best fidelity, Windows) →
    pycdxml (pure Python, partial support) → OpenBabel.

    ChemDraw COM requires ChemDraw to be installed and closed before running.

    Args:
        input_path:  Path to .cdx or .cdxml file.
        output_path: Output file path. If not given, same directory as input
                     with the swapped extension (e.g. foo.cdx → foo.cdxml).

    Returns:
        Dict with keys: ok, input, output (absolute path to written file).
        Returns {ok: False, error: "..."} if conversion fails.


Safety override: Convert CDX/CDXML through a validated no-overwrite staging file.

### `draw_molecule(mol_json: dict, output_path: Optional[str] = None) -> dict`

Render a single molecule to a standalone CDXML document.

    Takes a molecule dict (at minimum {"smiles": "..."}) and generates a
    self-contained CDXML string with 2D coordinates in ACS Document 1996 style
    (BondLength=14.40, Arial 10pt). Optionally places a text label below the
    structure using the "label", "name", or "iupac_name" field (in that order).

    IMPORTANT: Do NOT construct {"smiles": "..."} with hand-edited SMILES.
    Always get mol_json from another tool (resolve_name, modify_molecule,
    parse_reaction, etc.). If you need to edit a SMILES, use
    modify_molecule(operation="set_smiles") first — it gives you an MCS diff
    to verify the edit was correct before drawing.

    Args:
        mol_json: Molecule dict with at least {"smiles": "..."}. Optional display
                  fields: "label" (used verbatim), "name", "iupac_name".
                  Should come from another tool's output, not hand-constructed.
        output_path: If given, also write CDXML to this file path.

    Returns:
        Dict with keys: ok, cdxml (CDXML document string), and output_path if
        a path was specified. Returns {ok: False, error: "..."} on failure.


Safety override: Draw a molecule through a validated no-overwrite staging file.

### `embed_cdxml_in_office(cdxml_path: str, office_path: str, output_path: str | None = None) -> dict`

Embed a CDXML file as an editable ChemDraw OLE object in PPTX or DOCX.

    Converts CDXML → CDX + EMF preview via ChemDraw COM, builds a CFB OLE
    compound file, and injects it into a PPTX slide or DOCX paragraph as a
    double-clickable, editable ChemDraw object.

    Requires: ChemDraw COM (Windows, ChemDraw 16+), python-pptx or python-docx.
    ChemDraw must be installed and closed before calling this tool.

    The output format (.pptx or .docx) is detected from office_path extension.
    If office_path does not exist, a new file is created.

    Args:
        cdxml_path:   Path to the CDXML file to embed.
        office_path:  Path to the target .pptx or .docx file. Created if it
                      does not exist.
        output_path:  Output file path. If not given, writes to office_path
                      (modifies in place via temp file).

    Returns:
        Dict with keys: ok, input_cdxml, output (absolute path to written
        Office file), format ("pptx" or "docx"), num_objects_embedded.
        Returns {ok: False, error: "..."} if embedding fails.


Safety override: Create a new validated PPTX or DOCX and reject all existing targets.

### `extract_cdxml_from_office(file_path: str, output_dir: Optional[str] = None) -> dict`

Extract embedded ChemDraw objects from a PPTX, DOCX, XLS, or XLSX file.

    Office files (PPTX/DOCX/XLSX) are ZIP archives that may contain ChemDraw OLE
    objects as binary blobs. XLS files are OLE2 compound documents with embedded
    ChemDraw objects stored in MBD* sub-storages. This tool extracts every
    ChemDraw object, converts it to CDXML, and writes the files to output_dir.

    Requires: olefile. CDX→CDXML conversion uses available backends.

    Args:
        file_path:  Path to a .pptx, .docx, .xlsx, or .xls file.
        output_dir: Directory for extracted CDXML files. Default: a folder
                    named "<basename>_chemdraw/" next to the input file.

    Returns:
        Dict with keys: ok, input, output_dir, objects (list of: source_path,
        cdxml_output, cdx_output, error for each extracted object).
        Returns {ok: False, error: "..."} if extraction fails entirely.


Safety override: Extract every object transactionally; publish nothing on partial failure.

### `extract_structures_from_image(image_path: str, detect_labels: bool = True) -> dict`

Extract chemical structures from an image using DECIMER.

    Takes a PNG, JPG, or PDF image and returns SMILES + confidence scores +
    bounding boxes for every detected chemical structure. Segments the image
    into individual structure regions automatically. Optionally detects nearby
    text labels via OCR.

    DECIMER models download on first run (~570 MB to ~/.data/DECIMER-V2/).
    Requires: DECIMER, opencv-python, and optionally pytesseract/easyocr.

    The returned SMILES should be passed through resolve_name or modify_molecule
    to verify and enrich — DECIMER SMILES may not be canonical and can have
    low confidence for complex structures.

    Args:
        image_path:    Path to PNG, JPG, or PDF file.
        detect_labels: Attempt OCR detection of text labels near structures.
                       Requires pytesseract or easyocr; labels are null without
                       an OCR library. Default True.

    Returns:
        Dict with keys: ok, image_path, structures (list of: smiles, confidence
        in [0,1], bbox [x0,y0,x1,y1], label or null). Returns {ok: False,
        error: "..."} if DECIMER is not installed or extraction fails.

### `format_lab_entry(entries_json: Union[list[dict], dict, str], output_path: Optional[str] = None) -> dict`

Format a list of entry dicts into a structured lab book text entry.

    Takes a list of typed entry dicts (or a JSON string) and produces a
    formatted lab book entry.  The tool re-parses LCMS PDFs to fill in
    exact numbers — you only provide peak identifications (name, approximate
    RT, ion) as search keys.

    IMPORTANT: Do NOT write free-form LCMS text.  Use the structured entry
    types below.  The tool will look up the actual RT, area%, m/z, and UV
    from the PDF.

    Entry types and their required fields:

      {"type": "text", "content": "Procedure paragraph or section header..."}

      {"type": "lcms-species",
       "file": "path/to/report.pdf",
       "label": "t = 0 min",
       "peaks": [
         {"name": "Product",  "rt": 1.02, "ion": {"mode": "ES-", "mz": 444.1}},
         {"name": "SM",       "rt": 0.65, "ion": {"mode": "ES+", "mz": 275.1}},
         {"name": "TPPO",     "rt": 1.02, "ion": {"mode": "ES+", "mz": 279.1}}
       ]}

      {"type": "lcms-areas",
       "file": "path/to/report.pdf",
       "label": "t = 10 min",
       "peaks": [
         {"name": "Product",     "rt": 1.03, "compound_related": true},
         {"name": "Byproduct",   "rt": 1.26, "compound_related": false}
       ]}

      {"type": "lcms-species",
       "file": "path/to/report.pdf",
       "label": "Purified product",
       "peaks": [
         {"name": "Product", "rt": 1.01, "ion": {"mode": "ES-", "mz": 444.2},
          "purity": true, "detector": "220nm"}
       ]}

      {"type": "lcms-manual",
       "file": "path/to/manual_integration.pdf",
       "label": "Manual LC",
       "peaks": [
         {"name": "Product", "rt": 1.01, "compound_related": true}
       ]}

      {"type": "nmr", "content": "1H NMR (400 MHz, DMSO-d6): ..."}

    Workflow: First call parse_analysis_file on each PDF to see peaks/masses.
    Then build entries referencing those PDFs with approximate RT and ion as
    search keys.  This tool re-reads the PDF and fills in exact numbers.

    Args:
        entries_json: List of entry dicts, or a JSON string, or {"entries": [...]}.
        output_path:  If given, write the formatted text to this file and return
                      {ok, output_path, size} instead of {ok, text}.

    Returns:
        Dict with keys: ok, text (formatted lab book entry string).
        When output_path is provided, returns {ok, output_path, size} instead.


Safety override: Format a lab entry and atomically publish verified text.

### `modify_molecule(mol_json: dict, operation: str, add: Optional[List[dict]] = None, remove: Optional[List[str]] = None, new_smiles: Optional[str] = None, new_name: Optional[str] = None, reaction_name: Optional[str] = None, reagent: Optional[dict] = None, smarts: Optional[str] = None, description: Optional[str] = None) -> dict`

Analyze or transform a molecule with structural verification.

    IMPORTANT: This is the ONLY correct way to modify a molecule. Never edit
    SMILES strings yourself and pass them directly to draw_molecule — always
    go through modify_molecule so you get an MCS-based structural diff to
    verify the change was correct.

    Takes a molecule dict (at minimum {"smiles": "..."}) and applies one of 6
    operations. Returns the modified molecule with a structural diff showing
    exactly what atoms/bonds were added, removed, or changed.

    Operations:
        "analyze"      — Inspect without modifying: functional groups, IUPAC
                         names, formula, MW, prefix form. No extra kwargs needed.
        "name_surgery" — Modify via IUPAC name: add/remove substituents.
                         Pass add=[{"locant": "2", "prefix": "fluoro"}] and/or
                         remove=["methyl"] kwargs.
        "smarts"       — Apply a SMARTS reaction transform. Pass smarts=
                         "reaction SMILES" (e.g. "[c:1][F]>>[c:1][Cl]") or
                         reaction_name= from list_reactions output.
        "set_smiles"   — Use when you have edited a SMILES and want to verify
                         the change. Pass the original mol_json and new_smiles=.
                         The MCS diff will confirm exactly what was added/removed.
                         Do NOT generate SMILES from scratch — use resolve_name.
        "set_name"     — Set the display name. Pass new_name=.
        "reaction"     — Apply a named template from list_reactions. Pass
                         reaction_name= and optionally reagent={"smiles": ...}
                         for binary reactions (coupling, etc.).

    Args:
        mol_json: Source molecule dict with at least {"smiles": "..."}.
        operation: One of: "analyze", "name_surgery", "smarts", "set_smiles",
                   "set_name", "reaction".
        add: For "name_surgery" — list of {"locant": str, "prefix": str} dicts.
        remove: For "name_surgery" — list of prefix strings to remove.
        new_smiles: For "set_smiles" — validated SMILES string.
        new_name: For "set_name" — new display name string.
        reaction_name: For "smarts"/"reaction" — template name.
        reagent: For "reaction" — dict with "smiles" key for the second reagent.
        smarts: For "smarts" — reaction SMARTS string.
        description: For "set_smiles" — optional context note.

    Returns:
        For "analyze": ok, input_smiles, canonical_name, alternative_names,
        functional_groups, prefix_form, bracket_tree, formula, mw.
        For modifications: ok, input_smiles, output_smiles, input_name,
        output_name, aligned_names, diff (atoms_added, atoms_removed,
        atoms_changed, mcs_smarts, delta_formula, delta_mw), formula, mw.

### `parse_analysis_file(pdf_path: str, output_path: Optional[str] = None) -> dict`

Parse an LCMS or NMR analysis PDF to extract peaks and data.

    Supports Waters LCMS reports and MestReNova NMR PDFs. Returns structured
    peak data for LCMS species identification or NMR characterisation.

    This module is under active development. If unavailable, the tool returns
    a graceful error rather than crashing.

    Args:
        pdf_path:    Path to an LCMS or NMR PDF report.
        output_path: If given, write the parsed data as JSON to this file and
                     return {ok, output_path, size} instead of the full dict.

    Returns:
        For LCMS: dict with retention_times, peak_areas, masses, UV traces.
        For NMR: dict with chemical_shifts, multiplicities, integrations.
        When output_path is provided, returns {ok, output_path, size}.
        Returns {ok: False, error: "..."} if module unavailable or parse fails.


Safety override: Parse an analysis file and atomically publish verified JSON.

### `parse_reaction(cdxml: Optional[str] = None, cdx: Optional[str] = None, csv: Optional[str] = None, rxn: Optional[str] = None, input_dir: Optional[str] = None, output_path: Optional[str] = None) -> dict`

Parse reaction files into a semantic JSON descriptor.

    Extracts every species with canonical SMILES, role classification (using
    Schneider fingerprint scoring for reactant/reagent binary, plus curated
    database for semantic roles like base/solvent/catalyst), display names,
    equivalents, mass data, and adducts. Produces a single JSON source of truth
    suitable for summarize_reaction, render_scheme, or LCMS analysis.

    Provide at least one file path. Multiple may be combined (e.g. cdxml + csv)
    to merge structural data with ELN metadata.

    Args:
        cdxml:       Path to a .cdxml reaction file.
        cdx:         Path to a .cdx reaction file (converted internally).
        csv:         Path to a Findmolecule ELN CSV export.
        rxn:         Path to a .rxn file.
        input_dir:   Directory containing experiment files (auto-discovers
                     cdxml/cdx/csv/rxn by experiment ID).
        output_path: If given, write the result JSON to this file and return
                     {ok, output_path} instead of the full dict.

    Returns:
        Reaction descriptor dict with keys: version, experiment, input_files,
        reaction_smiles, reaction_class, species (list with role, smiles,
        formula, mw, etc.), conditions, and eln_data.
        When output_path is provided, returns {ok, output_path} instead.


Safety override: Parse a reaction and atomically publish its JSON descriptor.

### `parse_scheme(cdxml_path: str, output_path: Optional[str] = None) -> dict`

Parse a CDXML reaction scheme into a structured description.

    Reads a CDXML file containing a reaction scheme (single- or multi-step) and
    returns a structured JSON with a species registry, reaction graph, topology
    classification, and a natural language narrative suitable for LLM reasoning.

    Uses two strategies in order: step-attribute path (reads <scheme><step>
    attributes if present) then geometry-based fallback (spatial arrow detection).
    Text labels near arrows are classified as "chemical", "condition_ref",
    "footnote", "yield", "compound_label", "citation", or "bioactivity".

    Args:
        cdxml_path:  Path to a CDXML file containing a reaction scheme.
        output_path: If given, write the result JSON to this file and return
                     {ok, output_path, size} instead of the full dict.

    Returns:
        Dict with keys: source_file, species (dict of species records with
        smiles, name, formula, mw, role, text_category), steps (list with
        reactant/product/reagent species IDs and conditions), topology
        (linear/parallel/convergent/divergent), content_type, narrative
        (human-readable summary), and optionally sub_schemes for multi-panel
        files. When output_path is provided, returns {ok, output_path, size}.


Safety override: Parse a scheme and atomically publish its JSON descriptor.

### `render_scheme(yaml_text: Optional[str] = None, compact_text: Optional[str] = None, json_path: Optional[str] = None, layout: str = 'auto', output_path: Optional[str] = None) -> str`

Render an editable chemical reaction scheme with per-fragment chemical validation.

    Accepts exactly ONE of: yaml_text, compact_text, or json_path.
    Call with NO arguments to see the full YAML schema reference.

    - yaml_text:  Write YAML with structures (ID + SMILES) and steps
                  (substrates, products, above/below arrow).
    - json_path:  Path to reaction JSON from parse_reaction (auto-layout).

    IMPORTANT: Every SMILES in the YAML must come from a tool — resolve_name,
    modify_molecule, parse_reaction, extract_structures_from_image, etc.
    Never write SMILES from built-in chemistry knowledge or from reading an
    image with vision. Always call the appropriate tool first, then use the
    SMILES from its output in your YAML.

    Place all atom-contributing substrates on the center line when appropriate.
    Catalysts and conditions may go above/below arrows. Sequential steps can
    share intermediates; spatial position does not determine chemical identity.

    Args:
        yaml_text:    YAML scheme descriptor string.
        compact_text: Compact DSL syntax string.
        json_path:    Path to a reaction JSON file.
        layout:       Layout for json_path: "auto", "landscape", "portrait".
        output_path:  If given, write the CDXML to this file and return
                      {ok, output_path, size} instead of the raw CDXML string.

    Returns:
        CDXML string (when output_path is None), or {ok, output_path, size}
        when output_path is provided, or YAML schema reference if called with
        no arguments.


Safety override: Render a scheme through a validated no-overwrite staging file.

### `render_to_png(cdxml_path: str, output_path: Optional[str] = None) -> dict`

Render a CDXML file to PNG using ChemDraw COM.

    Uses ChemDraw's native rendering engine (via COM automation) at 300 DPI
    with a solid white background. ChemDraw must be installed (Professional
    16+) and closed before calling this tool.

    This tool uses ChemDraw COM exclusively — no RDKit fallback. For a
    quick preview without ChemDraw, use draw_molecule which returns CDXML
    that can be opened directly.

    Args:
        cdxml_path:  Path to the CDXML file to render.
        output_path: Output PNG path. If not given, writes to the same
                     directory as the input with a .png extension.

    Returns:
        Dict with keys: ok, input, output (absolute path to PNG file).
        Returns {ok: False, error: "..."} if ChemDraw COM is unavailable
        or rendering fails.


Safety override: Render CDXML to a validated PNG through a staging file.

### `resolve_name(query: str, use_network: bool = True) -> dict`

Resolve any chemical identifier to a rich molecule descriptor.

    Converts a name, abbreviation, condensed formula, or CAS number into a
    structured molecule dict with SMILES, formula, MW, exact mass, IUPAC name,
    reagent role, and display text. Uses a 4-tier resolution chain: curated
    reagent DB → condensed formula parser → ChemScript IUPAC → PubChem.

    Do NOT hand-construct SMILES — use this tool instead. The returned dict can
    be passed directly to modify_molecule, draw_molecule, or used to build a
    render_scheme input.

    Args:
        query: Chemical identifier — common name, IUPAC name, abbreviation,
               condensed formula (e.g. "PhB(OH)2"), or CAS number. Examples:
               "aspirin", "Cs2CO3", "2-chloropyridine", "534-17-8", "Et3N".
        use_network: Allow PubChem lookup (requires internet). Default True.

    Returns:
        Dict with keys: ok, name, smiles, formula, mw, exact_mass, iupac_name,
        source (which tier resolved it), role (if in reagent DB), display_text,
        prefix_form (IUPAC substituent prefix, if applicable).
        Returns {ok: False, error: "..."} if unresolvable.

### `search_compound(smiles: str, experiment_dir: str, similarity_threshold: float = 0.85) -> dict`

Search for a compound across experiment JSON files by SMILES similarity.

    Scans a directory of reaction JSON files (from parse_reaction) and returns
    exact matches and structurally similar compounds above the given Tanimoto
    threshold. Useful for finding related experiments, checking if a compound
    has been made before, or tracing a compound through a multi-step synthesis.

    This module is under active development. If unavailable, the tool returns
    a graceful error rather than crashing.

    Args:
        smiles:               SMILES string of the compound to search for.
                              Use resolve_name to get a validated SMILES first.
        experiment_dir:       Directory containing reaction JSON files to search.
        similarity_threshold: Tanimoto similarity cutoff (0–1). Default 0.85.

    Returns:
        Dict with keys: ok, query_smiles, exact_matches (list), similar_matches
        (list with similarity scores), total_files_searched.
        Returns {ok: False, error: "..."} if module unavailable or search fails.

### `summarize_reaction(json_path: str, species_fields: Optional[List[str]] = None, top_fields: Optional[List[str]] = None, eln_fields: Optional[List[str]] = None) -> dict`

Return a compact, context-efficient view of a reaction JSON file.

    The full reaction JSON can be 3,000+ tokens with geometry data. This tool
    returns only the fields you need for a given task, making it practical for
    LLM reasoning without burning context.

    Default fields (when no arguments given):
      species:   id, name, role, role_detail, smiles, display_text, formula, mw
      top-level: experiment, conditions
      eln_data:  product_yield, reaction_type

    Pass ["*"] for any field set to get all fields (equivalent to loading the
    full JSON). Request specific fields by name for task-focused summaries.

    Args:
        json_path:      Path to a reaction JSON file from parse_reaction.
        species_fields: Species fields to include. Available: id, name, role,
                        role_detail, smiles, smiles_neutral, is_sm, is_dp,
                        is_substrate, is_solvent, exact_mass, exact_mass_full,
                        mw, formula, adducts, source, source_id, csv_equiv,
                        csv_mass, csv_name, csv_volume, csv_supplier,
                        display_text, original_geometry. Pass ["*"] for all.
        top_fields:     Top-level fields. Available: version, experiment,
                        input_files, reaction_smiles, reaction_class,
                        reaction_name, classification_confidence, warnings,
                        metadata, conditions. Pass ["*"] for all.
        eln_fields:     ELN data fields. Available: sm_mass, product_obtained,
                        product_yield, procedure_text, procedure_plain,
                        reaction_type, start_date, labbook_name, solvents,
                        solvent_details. Pass ["*"] for all.

    Returns:
        Compact dict with requested fields for each species and top-level keys.

## Remote Tools

### `extract_structures_via_decimer_api(image_path: str, hand_drawn: bool = False, output_path: Optional[str] = None, timeout_seconds: int = 600, confirm_upload: bool = False, approved_sha256: Optional[str] = None, approved_origin: Optional[str] = None) -> dict[str, typing.Any]`

Upload an image to DECIMER only when confirm_upload is explicitly true.
