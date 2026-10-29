# Reviewed Exclusions Public Symbols

> Generated from cdxml-toolkit 0.7.0a3. Curated guidance: [../toolkit-reviewed-exclusions.md](../toolkit-reviewed-exclusions.md).

## `atom_mapping`

- **function**, line 300: `available_methods() -> list` - Methods that can run now: the built-in one plus every installed learned backend.
- **function**, line 32: `hill(counts) -> str` - No public docstring in the audited version.
- **function**, line 583: `map_atoms(left, right, *, resolve_ambiguity: bool = False, method: str = 'auto', compare: bool = False) -> dict` - Map the heavy atoms of products ``right`` onto reactants ``left`` (lists of (label, mol)).
- **function**, line 529: `map_atoms_many(reactions, *, resolve_ambiguity: bool = False, method: str = 'auto', compare: bool = False) -> list[dict]` - Map many reactions at once; ``reactions`` is a list of ``(left, right)`` as in :func:`map_atoms`.

## `catalog.cdxml`

- **function**, line 100: `binary_names(paths: Iterable[Path], names: Iterable[str]) -> set[str]` - Names that occur as standalone ASCII strings in the given binaries.
- **function**, line 112: `build_catalog(observed: dict[str, Any], *, binary_names: set[str], candidates: Iterable[str] = CANDIDATES, fixtures: Optional[list[dict[str, Any]]] = None, verified_on: str = 'unverified') -> dict[str, Any]` - No public docstring in the audited version.
- **function**, line 267: `dump(catalog: dict[str, Any]) -> str` - No public docstring in the audited version.
- **function**, line 244: `extract_live(workdir, *, verified_on: Optional[str] = None) -> dict[str, Any]` - Scan the CDXML ChemDraw installs, plus what it writes for the bundled CDX files and fixtures.
- **function**, line 54: `scan_documents(paths: Iterable[Path]) -> dict[str, Any]` - Collect elements, attributes, nesting and value shapes from CDXML files.
- **function**, line 41: `summarise_values(values: set[str]) -> dict[str, Any]` - Describe the shape of an attribute's observed values without keeping free text.

## `catalog.chemscript`

- **function**, line 87: `build_catalog(reflection: dict[str, Any], docs: dict[str, str], *, verified_on: str = 'unverified', bases: Optional[dict[str, str]] = None) -> dict[str, Any]` - Join a reflection dump (``include_infrastructure`` on) with XML summaries.
- **function**, line 204: `dump(catalog: dict[str, Any]) -> str` - No public docstring in the audited version.
- **function**, line 188: `extract_live(reflection_path, *, verified_on: Optional[str] = None) -> dict[str, Any]` - Read the installed SDK (Windows) and build the catalog; ``reflection_path`` must not exist.
- **function**, line 40: `parse_xml_docs(path) -> dict[str, str]` - Map each ``T:``/``M:``/``P:``/``F:`` key of the SDK's XML docs to its one-line summary.
- **function**, line 175: `read_bases() -> dict[str, str]` - Full name of each exported type's base type, read in-process through Python.NET.

## `catalog.classify`

- **function**, line 185: `all_rows() -> list[dict[str, Any]]` - No public docstring in the audited version.
- **function**, line 159: `classify(catalogs: dict[str, dict[str, Any]], recipes: list[dict[str, Any]], classification: dict[str, Any]) -> list[dict[str, Any]]` - No public docstring in the audited version.
- **function**, line 192: `find_row(rows: Iterable[dict[str, Any]], row_id: str) -> Optional[dict[str, Any]]` - No public docstring in the audited version.
- **function**, line 29: `load_catalog(layer: str) -> dict[str, Any]` - No public docstring in the audited version.
- **function**, line 33: `load_classification() -> dict[str, Any]` - No public docstring in the audited version.
- **function**, line 178: `summarize(rows: Iterable[dict[str, Any]]) -> dict[str, dict[str, int]]` - No public docstring in the audited version.

## `catalog.com`

- **function**, line 212: `dump(catalog: dict[str, Any]) -> str` - No public docstring in the audited version.
- **function**, line 189: `extract_live(*, verified_on: Optional[str] = None) -> dict[str, Any]` - Read the type libraries of the installed ChemDraw (Windows); ChemDraw is not started.
- **function**, line 71: `merge_properties(members: list[dict[str, Any]]) -> list[dict[str, Any]]` - Fold a property's get/put/putref accessors into one ``property`` member, in first-seen order.
- **function**, line 159: `read_typelib(path) -> dict[str, Any]` - Describe every type of the type library at ``path`` (an .exe, .dll, .ocx or .tlb).
- **function**, line 35: `type_name(desc, info) -> str` - Readable name of a TYPEDESC as pythoncom returns it: an int, or ``(vt, inner)``.

## `catalog.menu`

- **function**, line 24: `build_catalog(raw: list[dict[str, Any]], *, verified_on: str = 'unverified') -> dict[str, Any]` - Turn the raw ``[{menu, items: [{caption, command_id}]}]`` walk into the committed shape.
- **function**, line 108: `dump(catalog: dict[str, Any]) -> str` - No public docstring in the audited version.
- **function**, line 82: `extract_live(*, verified_on: Optional[str] = None) -> dict[str, Any]` - Start a private ChemDraw (Windows), read its menus and quit it.
- **function**, line 57: `find_command(catalog: dict[str, Any], caption: str) -> Optional[tuple[str, int]]` - Return ``(menu caption, command id)`` for a menu item caption, ignoring case.

## `catalog.recipes`

- **function**, line 42: `check(recipe: dict[str, Any], results: list[dict[str, Any]]) -> list[str]` - Return one message per expectation the results do not meet.
- **function**, line 56: `declaring_type(catalog: dict[str, Any], type_name: str, member: str) -> Optional[str]` - The type of the ChemScript catalog that declares ``member``, following base types.
- **function**, line 68: `fill_program(program: list[dict[str, Any]], *, fixture: str, out: str) -> list[dict[str, Any]]` - Copy a COM recipe program with ``{fixture}`` and ``{out}`` replaced in every string.
- **function**, line 18: `load() -> list[dict[str, Any]]` - No public docstring in the audited version.
- **function**, line 104: `run(recipe: dict[str, Any]) -> list[str]` - Execute a recipe on the installed ChemDraw and return its failures.

## `catalog.render`

- **function**, line 341: `render_all(catalogs: dict[str, dict[str, Any]] | None = None, recipes: list[dict[str, Any]] | None = None, classification: dict[str, Any] | None = None) -> dict[str, str]` - No public docstring in the audited version.

## `characterization`

- **function**, line 60: `atoms_mass(mol) -> float` - Sum of the monoisotopic (or labelled-isotope) atom masses, without any electron correction.
- **function**, line 73: `default_adduct(mol, mode: str = 'positive', ionization: str = 'ESI') -> str` - No public docstring in the audited version.
- **function**, line 81: `hrms_entry(mol, adduct: str | None = '[M+H]+', *, ionization: str = 'ESI', decimals: int = 4, found: float | None = None, electron_mass: bool = True) -> dict` - {adduct, ion_formula, charge, calcd_mz, found_mz, error_ppm, line} for one ion of ``mol``.

## `chemistry_diff`

- **function**, line 6: `structural_diff(before: str, after: str, timeout: int = 5) -> dict` - No public docstring in the audited version.

## `chemistry_semantics`

- **function**, line 79: `document_inventory(path)` - No public docstring in the audited version.
- **function**, line 32: `read_fragments(value)` - Top-level CDXML fragments as ``(fragment_id, mol)`` pairs, in document order.
- **function**, line 58: `read_molecules(value)` - No public docstring in the audited version.
- **function**, line 20: `require_supported(mol)` - No public docstring in the audited version.
- **function**, line 10: `semantic_key(mol)` - No public docstring in the audited version.
- **function**, line 83: `validate_document_preserved(source, output)` - No public docstring in the audited version.
- **function**, line 62: `validate_fragment(smiles, xml)` - No public docstring in the audited version.

## `mapping_backends`

- **function**, line 85: `available() -> dict` - No public docstring in the audited version.
- **class**, line 89: `BackendError` - A backend could not run or returned something unusable.
- **function**, line 62: `environment(name: str) -> Path` - No public docstring in the audited version.
- **function**, line 128: `find_base(name: str) -> str | None` - A Python that can host backend ``name``: this one, else python3.N on PATH, else the Windows launcher.
- **function**, line 50: `home() -> Path` - Folder that holds one environment per backend (CHEMDRAW_MAPPER_HOME overrides it).
- **function**, line 181: `install(name: str, *, dry_run: bool = False, log = None) -> dict` - Create ``environment(name)``, install its pinned requirements and check it with a real mapping.
- **function**, line 66: `interpreter(env: Path) -> Path | None` - No public docstring in the audited version.
- **function**, line 73: `python_for(name: str) -> Path | None` - Interpreter that can run backend ``name``: its own environment, else this one if it imports.
- **function**, line 93: `run(name: str, reactions: list, timeout: int = RUN_TIMEOUT) -> list` - Map reaction SMILES with backend ``name``; one dict per reaction (mapped_rxn plus a score).
- **function**, line 219: `status() -> dict` - No public docstring in the audited version.

## `mcp_runtime`

- **function**, line 11: `build_server(*args, **kwargs)` - Build the complete MCP server without importing it during package discovery.

## `mcp_runtime.artifact_safety`

- **function**, line 148: `apply_default_mode(path: str | Path) -> None` - Give a staged file the mode a plain open() would: mkstemp() files are 0600.
- **function**, line 262: `artifact_record(path: str | Path) -> dict[str, Any]` - No public docstring in the audited version.
- **function**, line 275: `artifact_records(paths: Iterable[str | Path]) -> list[dict[str, Any]]` - No public docstring in the audited version.
- **class**, line 18: `OutputExistsError` - An output already exists and the tool will not replace it.
- **property**, line 28: `OutputExistsError.public_message` - No public docstring in the audited version.
- **function**, line 287: `paths_from_value(value: Any) -> list[Path]` - No public docstring in the audited version.
- **function**, line 233: `publish_directory(staged: str | Path, destination: str | Path) -> None` - No public docstring in the audited version.
- **function**, line 179: `publish_file(staged: str | Path, destination: str | Path) -> None` - No public docstring in the audited version.
- **function**, line 217: `publish_files(staged_outputs: Iterable[tuple[Path, Path]]) -> None` - No public docstring in the audited version.
- **function**, line 58: `resolve_destination(*, source: str | Path | None, output_path: str | Path | None, tag: str, suffix: str, base_dir: str | Path | None = None) -> Path` - No public docstring in the audited version.
- **function**, line 90: `resolve_directory_destination(*, source: str | Path, output_dir: str | Path | None, tag: str) -> Path` - No public docstring in the audited version.
- **function**, line 313: `rewrite_paths(value: Any, old_root: str | Path, new_root: str | Path) -> Any` - No public docstring in the audited version.
- **function**, line 332: `stage_validate_publish(destination: str | Path, writer: Callable[[Path], Any], *, validator: Callable[[Path], Any] = validate_artifact) -> tuple[Any, Path]` - No public docstring in the audited version.
- **function**, line 168: `staging_directory(destination: str | Path) -> Iterator[Path]` - No public docstring in the audited version.
- **function**, line 158: `staging_file(destination: str | Path) -> Iterator[Path]` - No public docstring in the audited version.
- **function**, line 112: `validate_artifact(path: str | Path) -> Path` - No public docstring in the audited version.
- **function**, line 32: `validate_input_file(path: str | Path, *, suffixes: tuple[str, ...] | None = None) -> Path` - No public docstring in the audited version.
- **function**, line 305: `with_artifacts(result: dict[str, Any], paths: Iterable[str | Path]) -> dict[str, Any]` - No public docstring in the audited version.

## `mcp_runtime.capabilities`

- **function**, line 37: `get_toolkit_capabilities(detail: str = 'full') -> dict[str, Any]` - Return runtime identity and diagnostics; detail='summary' omits tool signatures.

## `mcp_runtime.chemistry_compare`

- **function**, line 206: `batch_compare_molecules(pairs: list[dict[str, Any]], fingerprint: str = 'morgan', radius: int = 2, n_bits: int = 2048) -> dict[str, Any]` - Compare up to 256 molecule pairs with one ChemScript bridge session.
- **function**, line 145: `compare_molecules(molecule_a: str, molecule_b: str, fingerprint: str = 'morgan', radius: int = 2, n_bits: int = 2048) -> dict[str, Any]` - Compare two molecule representations using ChemScript identity and RDKit Tanimoto fingerprints.

## `mcp_runtime.chemscript_sdk`

- **class**, line 58: `ChemScriptSdkUnavailable` - ChemScript SDK programs need Windows (the .NET SDK) or macOS (its emulation).
- **function**, line 183: `execute_chemscript_sdk(program: list[dict[str, Any]], allow_file_io: bool = False, allow_overwrite: bool = False, allow_unsafe_interop: bool = False, max_items: int = 100) -> dict[str, Any]` - Execute a declarative ChemScript SDK program in an isolated Python.NET process.
- **function**, line 125: `inspect_chemscript_sdk(query: Optional[str] = None, type_name: Optional[str] = None, include_infrastructure: bool = False, offset: int = 0, limit: int = 100, output_path: Optional[str] = None) -> dict[str, Any]` - Catalog every public ChemScript type/member, with filtering or a complete JSON export.

## `mcp_runtime.chemscript_sdk_mac`

- **class**, line 115: `Atom` - No public docstring in the audited version.
- **class**, line 137: `AtomMap` - Atom-to-atom map, keyed like a .NET dictionary (``Keys``, ``map[atom]``).
- **property**, line 148: `AtomMap.Count` - No public docstring in the audited version.
- **property**, line 144: `AtomMap.Keys` - No public docstring in the audited version.
- **class**, line 129: `Bond` - No public docstring in the audited version.
- **class**, line 398: `LargestCommonSubstructure` - No public docstring in the audited version.
- **method**, line 412: `LargestCommonSubstructure.AtomMapM1() -> AtomMap` - No public docstring in the audited version.
- **method**, line 415: `LargestCommonSubstructure.AtomMapM2() -> AtomMap` - No public docstring in the audited version.
- **method**, line 409: `LargestCommonSubstructure.CommonSubstructure() -> Optional[StructureData]` - No public docstring in the audited version.
- **method**, line 404: `LargestCommonSubstructure.Compute(first: StructureData, second: StructureData)` - No public docstring in the audited version.
- **class**, line 472: `MacSdkRuntime` - The program runtime interface of ``ChemScriptRuntime``, for the emulation.
- **method**, line 522: `MacSdkRuntime.catalog() -> tuple[list[dict], list[dict]]` - No public docstring in the audited version.
- **method**, line 510: `MacSdkRuntime.check_member(owner: Any, member: str, operation: str) -> None` - Refuse anything that is not an emulated public member (no Python internals).
- **method**, line 507: `MacSdkRuntime.member_is_interop(reflection_type, member: str) -> bool` - No public docstring in the audited version.
- **method**, line 486: `MacSdkRuntime.python_type(name: str)` - No public docstring in the audited version.
- **method**, line 477: `MacSdkRuntime.reflection_type(name: str) -> _Type` - No public docstring in the audited version.
- **method**, line 489: `MacSdkRuntime.resolve_argument(value: Any, aliases: dict[str, Any], *, unsafe: bool)` - No public docstring in the audited version.
- **class**, line 324: `ReactionData` - No public docstring in the audited version.
- **method**, line 376: `ReactionData.Formula() -> str` - No public docstring in the audited version.
- **method**, line 331: `ReactionData.LoadData(data: str, mimetype: Optional[str] = None)` - No public docstring in the audited version.
- **method**, line 354: `ReactionData.LoadFile(path: str, mimetype: Optional[str] = None)` - No public docstring in the audited version.
- **property**, line 373: `ReactionData.Products` - No public docstring in the audited version.
- **property**, line 369: `ReactionData.Reactants` - No public docstring in the audited version.
- **method**, line 379: `ReactionData.WriteData(mimetype: str = 'chemical/x-mdl-rxn') -> str` - No public docstring in the audited version.
- **method**, line 386: `ReactionData.WriteFile(path: str, mimetype: Optional[str] = None) -> bool` - No public docstring in the audited version.
- **class**, line 161: `StructureData` - No public docstring in the audited version.
- **method**, line 315: `StructureData.AtomByAtomSearch(target: 'StructureData')` - No public docstring in the audited version.
- **property**, line 263: `StructureData.Atoms` - No public docstring in the audited version.
- **property**, line 267: `StructureData.Bonds` - No public docstring in the audited version.
- **method**, line 259: `StructureData.ChemicalName() -> str` - No public docstring in the audited version.
- **method**, line 292: `StructureData.CleanupStructure() -> bool` - No public docstring in the audited version.
- **method**, line 311: `StructureData.ContainsSubstructure(query: 'StructureData') -> bool` - No public docstring in the audited version.
- **property**, line 243: `StructureData.ElementalAnalysis` - No public docstring in the audited version.
- **property**, line 239: `StructureData.ExactMass` - No public docstring in the audited version.
- **method**, line 231: `StructureData.Formula() -> str` - No public docstring in the audited version.
- **property**, line 247: `StructureData.Inchi` - No public docstring in the audited version.
- **method**, line 177: `StructureData.LoadData(data: str, mimetype: Optional[str] = None)` - No public docstring in the audited version.
- **method**, line 189: `StructureData.LoadFile(path: str, mimetype: Optional[str] = None)` - No public docstring in the audited version.
- **method**, line 215: `StructureData.MimeTypes()` - No public docstring in the audited version.
- **method**, line 302: `StructureData.Overlay(target: 'StructureData') -> bool` - No public docstring in the audited version.
- **method**, line 193: `StructureData.ReadFile(path: str, mimetype: Optional[str] = None) -> bool` - No public docstring in the audited version.
- **property**, line 251: `StructureData.TotalCharge` - No public docstring in the audited version.
- **property**, line 235: `StructureData.Weight` - No public docstring in the audited version.
- **method**, line 271: `StructureData.WriteData(mimetype: str = 'text/xml') -> str` - No public docstring in the audited version.
- **method**, line 278: `StructureData.WriteFile(path: str, mimetype: Optional[str] = None) -> bool` - No public docstring in the audited version.

## `mcp_runtime.chemscript_sdk_runtime`

- **function**, line 447: `catalog_sdk(runtime: ChemScriptRuntime, request: dict[str, Any]) -> dict[str, Any]` - No public docstring in the audited version.
- **class**, line 147: `ChemScriptRuntime` - One direct Python.NET session for cataloging and executing an SDK program.
- **method**, line 289: `ChemScriptRuntime.member_is_interop(reflection_type, member: str) -> bool` - No public docstring in the audited version.
- **method**, line 201: `ChemScriptRuntime.python_type(name: str)` - No public docstring in the audited version.
- **method**, line 187: `ChemScriptRuntime.reflection_type(name: str)` - No public docstring in the audited version.
- **method**, line 224: `ChemScriptRuntime.resolve_argument(value: Any, aliases: dict[str, Any], *, unsafe: bool)` - No public docstring in the audited version.
- **method**, line 213: `ChemScriptRuntime.system_python_type(name: str)` - No public docstring in the audited version.
- **function**, line 603: `execute_program(runtime: ChemScriptRuntime, request: dict[str, Any]) -> dict[str, Any]` - No public docstring in the audited version.
- **function**, line 63: `validate_program(program: list[dict[str, Any]], *, allow_file_io: bool = True, allow_unsafe_interop: bool = False) -> list[dict[str, Any]]` - Validate the declarative SDK program without loading Python.NET.

## `mcp_runtime.com_call`

- **function**, line 422: `chemdraw_com_call(program: list[dict[str, Any]], allow_file_io: bool = False, allow_overwrite: bool = False, max_items: int = 100) -> dict[str, Any]` - Run a declarative program over ChemDraw's COM automation objects (Windows, ChemDraw installed).
- **class**, line 66: `ComCallError` - A ChemDraw failure with a stable public code.
- **function**, line 322: `execute_program(application: Any, steps: list[dict[str, Any]], *, max_items: int = 100, allow_overwrite: bool = False, created: Optional[list[Any]] = None) -> dict[str, Any]` - Run validated steps against ``application``; returns results and written files.
- **function**, line 151: `validate_program(program: list[dict[str, Any]], *, allow_file_io: bool = False, allow_overwrite: bool = False) -> list[dict[str, Any]]` - Check the program against the COM catalog and return the steps with their types.

## `mcp_runtime.decimer_api`

- **function**, line 75: `build_multipart_body(*, filename: str, mime_type: str, image_bytes: bytes, hand_drawn: bool, boundary: str | None = None) -> tuple[str, bytes]` - Encode the multipart fields declared by the live OpenAPI document.
- **class**, line 36: `DecimerAPIError` - Raised when the remote DECIMER service cannot return usable SMILES.
- **method**, line 43: `DecimerAPIError.as_result() -> dict[str, Any]` - No public docstring in the audited version.
- **class**, line 50: `DecimerUploadRefused` - Raised when upload consent is absent or does not match the prepared upload.
- **function**, line 54: `normalize_api_payload(payload: Any) -> dict[str, Any]` - Normalize both the documented string and live list response shapes.
- **function**, line 471: `recognize_image(image_path: str, *, hand_drawn: bool = False, timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS, output_path: str | None = None, confirm_upload: bool = False, approved_sha256: str | None = None, approved_origin: str | None = None) -> dict[str, Any]` - Upload one image to DECIMER and return normalized, validated predictions.
- **function**, line 239: `urlopen(request: Request, *, timeout: int)` - Open a request with redirect checks applied before a redirected upload.

## `mcp_runtime.extended_tools`

- **function**, line 1147: `analyze_lcms_series(files: list[str], output_path: Optional[str] = None, rt_tolerance: float = 0.02, mz_tolerance: float = 0.5, trend_threshold: float = 0.2, ignore_instrument: bool = False) -> dict[str, Any]` - Analyze a chronological series of standard LCMS PDF reports.
- **function**, line 1217: `assemble_lab_book(input_dir: str, experiment: Optional[str] = None, tracking_json: Optional[str] = None, output_path: Optional[str] = None) -> dict[str, Any]` - Assemble a deterministic lab-book entry from experiment files.
- **function**, line 818: `batch_embed_cdxml_in_office(cdxml_paths: list[str], output_path: str, margin_pt: float = 0) -> dict[str, Any]` - Create PPTX or DOCX containing editable ChemDraw OLE objects.
- **function**, line 470: `clean_scheme_layout(input_path: str, output_path: Optional[str] = None, approach: str = 'chemdraw_mimic', render_preview: bool = True) -> dict[str, Any]` - Clean an existing CDXML reaction layout without changing the source file.
- **function**, line 1115: `discover_experiment_files(input_dir: str, experiment: Optional[str] = None, output_path: Optional[str] = None) -> dict[str, Any]` - Discover and classify files belonging to one experiment.
- **function**, line 742: `fill_office_template(template_path: str, manifest_path: str, output_path: Optional[str] = None) -> dict[str, Any]` - Fill PPTX/DOCX text and editable ChemDraw placeholders from a manifest.
- **function**, line 878: `inspect_chemdraw_objects_in_office(input_path: str, output_dir: Optional[str] = None, render_previews: bool = True) -> dict[str, Any]` - Inventory editable ChemDraw objects and extract numbered CDXML previews.
- **function**, line 516: `merge_reaction_schemes(input_paths: list[str], output_path: Optional[str] = None, mode: str = 'auto', equiv_mode: str = 'default', reference_cdxml: Optional[str] = None, allow_adjacent: bool = True, render_preview: bool = True, force_sequential: bool = False) -> dict[str, Any]` - Merge parallel, sequential, or unrelated CDXML reaction schemes.
- **function**, line 1251: `parse_scifinder_rdf(input_path: str, resolve_cas: bool = False, output_path: Optional[str] = None, confirm_pubchem: bool = False) -> dict[str, Any]` - Parse SciFinder RDF and optionally enrich CAS data over the network.
- **function**, line 603: `polish_reaction_scheme(input_path: str, output_path: Optional[str] = None, merge_conditions: bool = True, approach: str = 'chemdraw_mimic', align_mode: str = 'rdkit', eln_csv: Optional[str] = None, reference_cdxml: Optional[str] = None, render_preview: bool = True) -> dict[str, Any]` - Run the audited deterministic polishing pipeline on a CDXML scheme.
- **function**, line 635: `render_cdxml_files(input_paths: list[str], output_dir: Optional[str] = None, format: str = 'png', dpi: int = 300) -> dict[str, Any]` - Render one or more CDXML files through native ChemDraw (COM or macOS).
- **function**, line 984: `replace_chemdraw_objects_in_office(input_path: str, replacements_manifest: str, output_path: Optional[str] = None, render_pdf_preview: bool = True, resize_frames: bool = False) -> dict[str, Any]` - Replace selected ChemDraw OLE contents and previews without moving them.
- **function**, line 1359: `segment_large_scheme(cdxml_path: str, output_path: Optional[str] = None, verbose: bool = False) -> dict[str, Any]` - Segment a disconnected or multi-panel CDXML scheme into logical regions.

## `mcp_runtime.figure_draw`

- **function**, line 260: `draw_figure(brief: dict | str, output_path: str | None = None, render: bool = False) -> dict` - Draw a reaction scheme from a brief and check it, in one call.

## `mcp_runtime.figure_editing`

- **function**, line 4: `apply_crossings(page, crossings)` - No public docstring in the audited version.
- **function**, line 50: `edit_bond_display(node, edit)` - No public docstring in the audited version.

## `mcp_runtime.figure_lint`

- **function**, line 101: `lint_cdxml(cdxml_text: str, max_width: Optional[float] = None) -> List[Dict[str, Any]]` - Return a list of issues; an empty list means the geometry checks passed.

## `mcp_runtime.figure_mechanism`

- **function**, line 644: `draw_mechanism(brief: dict, output_path: str | None, render: bool) -> dict` - Draw a mechanism; called by draw_figure for ``kind: mechanism``.

## `mcp_runtime.figure_scope`

- **function**, line 160: `draw_scope(brief: dict, output_path: str | None, render: bool) -> dict` - Draw a scope panel; called by draw_figure for ``kind: scope``.

## `mcp_runtime.figure_tools`

- **function**, line 606: `compare_figure_images(reference_path: str, candidate_path: str, output_path: str) -> dict` - Compare aligned local raster previews without resizing or warping.
- **function**, line 208: `compose_chemical_figure(manifest_path: str, output_path: str) -> dict` - Compose editable CDXML using explicit point coordinates and grounded molecules.
- **function**, line 72: `rdkit_workbench(molecules: list[dict], operation: str = 'inspect', options: dict | None = None, output_path: str | None = None) -> dict` - Analyze grounded molecules: inspect, stereoisomers, tautomers, mcs, r_groups, set_stereo.

## `mcp_runtime.figure_validation`

- **function**, line 49: `compare_inventories(a, b)` - No public docstring in the audited version.
- **function**, line 16: `inspect_document(path)` - No public docstring in the audited version.
- **function**, line 78: `validate_figure(input_path: str, output_dir: str, native: bool = False, cross_reader: bool = False) -> dict` - Write a diagnostic directory without changing the source. CLI-only operation.

## `mcp_runtime.generate_reference`

- **function**, line 32: `manifest(profile: str = 'full') -> dict` - No public docstring in the audited version.
- **function**, line 57: `render_markdown(profile: str = 'full') -> str` - No public docstring in the audited version.
- **function**, line 90: `render_reference(profile: str = 'full') -> str` - Signature reference used by the Skill's catalog checks.

## `mcp_runtime.install_decimer_models`

- **function**, line 35: `download(url: str, destination: Path, proxy: str | None) -> None` - No public docstring in the audited version.
- **function**, line 45: `file_hash(path: Path, algorithm: str) -> str` - No public docstring in the audited version.
- **function**, line 116: `install_model(model: dict[str, str], target: Path, *, proxy: str | None, downloader = download) -> dict[str, str]` - No public docstring in the audited version.
- **function**, line 53: `md5(path: Path) -> str` - No public docstring in the audited version.
- **function**, line 61: `safe_extract(archive: Path, destination: Path) -> None` - No public docstring in the audited version.
- **function**, line 74: `select_models(keys: list[str] | None) -> list[dict[str, str]]` - No public docstring in the audited version.
- **function**, line 57: `sha256(path: Path) -> str` - No public docstring in the audited version.

## `mcp_runtime.markush_tools`

- **function**, line 30: `markush_compile(spec_path: str, output_dir: str, layout_path: str | None = None, render: bool = True) -> dict` - Compile a spec into markush.cxsmiles, markush.mol (V3000), markush.cdxml and a native PNG.
- **function**, line 73: `markush_detect(image_path: str, output_dir: str) -> dict` - Find text boxes, bonds and ring circles in a clean Markush drawing.
- **function**, line 62: `markush_enumerate(spec_path: str, count: int = 5, seed: int = 0) -> dict` - Sample concrete members from the definition values of a spec (SMILES).
- **function**, line 23: `markush_validate(spec_path: str) -> dict` - Check a markush.json spec; every error says what to change.

## `mcp_runtime.mcp_compat`

- **function**, line 45: `install_legacy_fastmcp_alias() -> None` - Provide the legacy FastMCP import expected by the core MCP module.
- **function**, line 19: `sdk_major(version: str | None = None) -> int` - Return a supported MCP SDK major version or raise a clear error.
- **function**, line 14: `sdk_version() -> str` - Return the installed MCP Python SDK distribution version.
- **function**, line 34: `server_class() -> type[Any]` - Return the high-level server class for the installed SDK.

## `mcp_runtime.mcp_server`

- **class**, line 546: `ApiKeyMiddleware` - Require a bearer token without placing it in logs or worker environments.
- **function**, line 744: `build_http_app(args: argparse.Namespace, *, environ = None)` - No public docstring in the audited version.
- **function**, line 683: `build_server(*, profile: str | None = None, **server_settings)` - No public docstring in the audited version.
- **function**, line 712: `parse_args(argv: list[str] | None = None) -> argparse.Namespace` - No public docstring in the audited version.
- **function**, line 610: `resolve_http_configuration(*, host: str, port: int, allowed_hosts: list[str], allowed_origins: list[str], environ: typing.Mapping[str, str] | None = None, api_key_env: str = 'CHEMDRAW_MCP_HTTP_API_KEY') -> dict[str, typing.Any]` - Validate remote HTTP exposure and return non-secret server settings.
- **function**, line 782: `run_streamable_http(args: argparse.Namespace) -> None` - No public docstring in the audited version.

## `mcp_runtime.native_io`

- **function**, line 153: `ascii_input_directory(source: str | Path, *, suffixes: Sequence[str] = ('.cdxml', '.cdx', '.csv', '.rxn')) -> Iterator[tuple[Path, dict[str, str]]]` - No public docstring in the audited version.
- **function**, line 136: `ascii_inputs(sources: Sequence[str | Path]) -> Iterator[list[Path]]` - No public docstring in the audited version.
- **function**, line 119: `ascii_workspace(prefix: str = 'cdx-') -> Iterator[Path]` - No public docstring in the audited version.
- **function**, line 386: `batch_convert_cdxml(sources: Sequence[str | Path], batch_convert: Callable[[list[str]], Any]) -> list[dict[str, Any]]` - No public docstring in the audited version.
- **function**, line 257: `bridge_file(source: str | Path, destination: str | Path, operation: Callable[[Path, Path], Any], *, output_kind: str | None = None, preserve_source_context: bool = False) -> Any` - No public docstring in the audited version.
- **function**, line 415: `convert_cdx_bytes_to_cdxml(cdx_data: bytes, converter: Callable[..., Any]) -> str` - No public docstring in the audited version.
- **class**, line 20: `NativeIOError` - Native automation failure with a stable public error code.
- **function**, line 33: `normalize_cdxml_staging(path: Path) -> None` - Normalize a staged copy for native use; the source document is never changed.
- **function**, line 478: `rewrite_json_paths(path: str | Path, replacements: dict[str, str]) -> None` - No public docstring in the audited version.
- **function**, line 180: `validate_native_output(path: str | Path, kind: str | None = None) -> Path` - No public docstring in the audited version.
- **function**, line 436: `write_shadow_manifest(manifest: str | Path, workspace: str | Path) -> tuple[Path, list[Path]]` - No public docstring in the audited version.

## `mcp_runtime.native_renderer`

- **class**, line 36: `NativeRenderError` - ChemDraw rendering failure with a stable public error code.
- **class**, line 109: `NativeRenderSession` - Lazily acquire and reuse one ChemDraw application for native exports.
- **method**, line 184: `NativeRenderSession.render(source: str | Path, destination: str | Path, dpi: int = 300) -> str` - No public docstring in the audited version.
- **function**, line 255: `render_cdxml(source: str | Path, destination: str | Path, *, dpi: int = 300, timeout_seconds: int = 30) -> str` - No public docstring in the audited version.
- **function**, line 31: `renderer_name() -> str` - The native renderer on this platform, as written in render receipts.

## `mcp_runtime.object_tools`

- **function**, line 228: `chemdraw_inventory(layer: str | None = None, query: str | None = None, tier: str | None = None, kind: str | None = None, limit: int = 50) -> dict` - Look up ChemDraw's own interfaces and how far this Skill covers each one.
- **function**, line 75: `chemdraw_object(op: str, input_path: str, selector: str | None = None, tag: str | None = None, props: dict | None = None, children: list | None = None, text: str | None = None, output_path: str | None = None, allow_unknown: bool = False, dry_run: bool = False, verify: bool = True, limit: int = 200) -> dict` - List, read, change, add or delete any object in a CDXML file, without touching the input.

## `mcp_runtime.office_objects`

- **function**, line 26: `com_apartment()` - Initialize COM for the current worker thread and release it symmetrically.
- **function**, line 514: `emf_frame_size(data: bytes) -> tuple[int, int] | None` - Width and height of an EMF picture frame in 0.01 mm, or None if not an EMF.
- **function**, line 443: `load_replacement_manifest(manifest_path: str | Path, *, source_sha256: str, objects: list[dict[str, Any]]) -> list[dict[str, Any]]` - No public docstring in the audited version.
- **function**, line 637: `render_office_pdf(office_path: str | Path, output_path: str | Path) -> None` - No public docstring in the audited version.
- **function**, line 550: `resize_ole_frame(xml: bytes, relationship_id: str, scale_x: float, scale_y: float) -> bytes` - Scale the frame of the OLE object ``relationship_id`` in a slide or document part.
- **function**, line 591: `rewrite_office_package(input_path: str | Path, output_path: str | Path, replacement_parts: dict[str, dict[str, bytes]]) -> None` - Write a copy of an Office package with replaced OLE objects and previews.
- **function**, line 267: `scan_office_objects(input_path: str | Path) -> tuple[str, list[dict[str, Any]]]` - No public docstring in the audited version.
- **function**, line 51: `sha256_file(path: str | Path) -> str` - No public docstring in the audited version.
- **function**, line 690: `validate_pdf(path: str | Path) -> None` - No public docstring in the audited version.
- **function**, line 391: `write_inspection(input_path: str | Path, output_dir: str | Path, *, render_previews: bool) -> dict[str, Any]` - No public docstring in the audited version.

## `mcp_runtime.official_overrides`

- **function**, line 234: `convert_cdx_cdxml(input_path: str, output_path: Optional[str] = None) -> dict` - Convert CDX/CDXML through a validated no-overwrite staging file.
- **function**, line 74: `draw_molecule(mol_json: dict, output_path: Optional[str] = None) -> dict` - Draw a molecule through a validated no-overwrite staging file.
- **function**, line 408: `embed_cdxml_in_office(cdxml_path: str, office_path: str, output_path: str | None = None) -> dict` - Create a new validated PPTX or DOCX and reject all existing targets.
- **function**, line 299: `extract_cdxml_from_office(file_path: str, output_dir: Optional[str] = None) -> dict` - Extract every object transactionally; publish nothing on partial failure.
- **function**, line 281: `format_lab_entry(entries_json: Union[list[dict], dict, str], output_path: Optional[str] = None) -> dict` - Format a lab entry and atomically publish verified text.
- **function**, line 263: `parse_analysis_file(pdf_path: str, output_path: Optional[str] = None) -> dict` - Parse an analysis file and atomically publish verified JSON.
- **function**, line 142: `parse_reaction(cdxml: Optional[str] = None, cdx: Optional[str] = None, csv: Optional[str] = None, rxn: Optional[str] = None, input_dir: Optional[str] = None, output_path: Optional[str] = None) -> dict` - Parse a reaction and atomically publish its JSON descriptor.
- **function**, line 219: `parse_scheme(cdxml_path: str, output_path: Optional[str] = None) -> dict` - Parse a scheme and atomically publish its JSON descriptor.
- **function**, line 108: `render_scheme(yaml_text: Optional[str] = None, compact_text: Optional[str] = None, json_path: Optional[str] = None, layout: str = 'auto', output_path: Optional[str] = None) -> str` - Render a scheme through a validated no-overwrite staging file.
- **function**, line 453: `render_to_png(cdxml_path: str, output_path: Optional[str] = None) -> dict` - Render CDXML to a validated PNG through a staging file.

## `mcp_runtime.process_control`

- **function**, line 295: `cleanup_automation_processes(before: dict[int, dict[str, Any]], after: dict[int, dict[str, Any]], *, stage_pid: int, terminate: bool = True, deadline: float | None = None) -> dict[str, Any]` - No public docstring in the audited version.
- **function**, line 119: `pid_is_running(pid: int) -> bool` - No public docstring in the audited version.
- **function**, line 216: `snapshot_automation_processes(timeout_seconds: float = 5) -> dict[int, dict[str, Any]]` - No public docstring in the audited version.
- **function**, line 92: `terminate_pid(pid: int, timeout_seconds: float = 10) -> bool` - No public docstring in the audited version.

## `mcp_runtime.publication_figure`

- **function**, line 32: `publication_figure(operation: str, spec_path: str, output_dir: str) -> dict` - Create, update, or check editable substrate-scope and SAR figure projects.

## `mcp_runtime.remote_tools`

- **function**, line 10: `extract_structures_via_decimer_api(image_path: str, hand_drawn: bool = False, output_path: Optional[str] = None, timeout_seconds: int = 600, confirm_upload: bool = False, approved_sha256: Optional[str] = None, approved_origin: Optional[str] = None) -> dict[str, Any]` - Default image-recognition tool: use the remote DECIMER API.

## `mcp_runtime.report_tools`

- **function**, line 1582: `characterization_text(compounds: list[dict], options: dict | None = None, output_path: str | None = None) -> dict` - ACS-style characterization paragraph per compound, in the order of the ACS Style Guide.
- **function**, line 568: `check_reaction_balance(reaction: str | dict, options: dict | None = None, output_path: str | None = None) -> dict` - Check that a reaction conserves atoms and charge, and optionally tabulate its stoichiometry.
- **function**, line 853: `chemdraw_chemical_properties(molecules: list[dict], output_path: str | None = None) -> dict` - Formula, masses, elemental analysis, logP and molar refractivity as ChemDraw computes them.
- **function**, line 630: `export_structures(source: str | list, options: dict | None = None, output_path: str | None = None) -> dict` - Export every structure in a file or list as SMILES, InChI, InChIKey, formula and mass.
- **function**, line 996: `hrms_line(molecules: list[dict], options: dict | None = None, output_path: str | None = None) -> dict` - HRMS characterization lines: "HRMS (ESI) m/z calcd for C9H10O2Na [M+Na]+ 173.0573, found 173.0570".
- **function**, line 1498: `map_reaction_atoms(reaction: str | dict | list, options: dict | None = None, output_path: str | None = None) -> dict` - Map each product atom to the reactant atom it comes from (atom-to-atom mapping).
- **function**, line 290: `molecule_report(molecules: list[dict], output_path: str | None = None) -> dict` - Property sheet for grounded molecules: formula, masses, MS adducts, drug-likeness.
- **function**, line 1278: `route_summary(steps: list, options: dict | None = None, output_path: str | None = None) -> dict` - Overall yield and cumulative process mass intensity (PMI) of a synthetic route.
- **function**, line 1142: `si_materials_tables(reactions: list, options: dict | None = None, output_path: str | None = None) -> dict` - Materials tables for a batch of reactions, ready for a Supporting Information file.
- **function**, line 446: `signs(species)` - No public docstring in the audited version.
- **function**, line 961: `stoichiometry_grid(source: str, mode: str = 'analyze', output_path: str | None = None, options: dict | None = None) -> dict` - ChemDraw's own stoichiometry grid (Structure > Analyze Stoichiometry), drawn or read back.
- **function**, line 723: `structure_to_name(molecules: list[dict], options: dict | None = None, output_path: str | None = None) -> dict` - Name grounded structures with ChemDraw's own structure-to-name engine and check each name.

## `mcp_runtime.resource_lock`

- **function**, line 46: `native_resource_lock(resource_class: str | None, timeout_seconds: int) -> Iterator[None]` - Serialize ChemDraw automation across workers in the current user session.
- **class**, line 34: `ResourceBusyError` - Raised when an exclusive native resource cannot be acquired in time.

## `mcp_runtime.runtime_diagnostics`

- **function**, line 521: `diagnose_runtime(run_native_probe: bool = False, run_office_probe: bool = False, run_chemscript_probe: bool = False) -> dict[str, Any]` - Report local runtime capabilities; native probes are explicit and temporary.

## `mcp_runtime.runtime_discovery`

- **class**, line 28: `Discovery` - No public docstring in the audited version.
- **method**, line 32: `Discovery.to_dict() -> dict[str, str]` - No public docstring in the audited version.
- **function**, line 299: `find_chemdraw(explicit: str | None = None) -> Discovery` - Find ChemDraw from explicit, environment, the macOS application, COM, then common paths.
- **function**, line 144: `find_python(explicit: str | None = None) -> Discovery` - Find and probe Python using explicit, environment, then implicit paths.
- **function**, line 185: `find_skill_root(explicit: str | None = None) -> Discovery` - No public docstring in the audited version.

## `mcp_runtime.scientific_tool`

- **function**, line 21: `scientific_workflow(operation: str, spec_path: str, output_path: str) -> dict[str, Any]` - Draw or analyse a scientific figure from a JSON spec file: tlc, apparatus, mechanism, nmr or plot.

## `mcp_runtime.structure_fidelity`

- **function**, line 219: `repair_and_validate_drawn_cdxml(smiles: str, path: str | Path, *, repair_stereo: bool = True) -> dict[str, object]` - Repair missing wedge bonds and verify CDXML against the source SMILES.
- **class**, line 9: `StructureFidelityError` - Generated CDXML does not preserve the requested molecular structure.

## `mcp_runtime.telemetry`

- **function**, line 38: `configure_tools(names: Iterable[str]) -> None` - Set the finite tool-label vocabulary used by exported metrics.
- **function**, line 106: `health_snapshot(*, tool_count: int) -> dict` - Return process health without input, output, filename, or molecule data.
- **function**, line 100: `native_active_finished() -> None` - No public docstring in the audited version.
- **function**, line 94: `native_active_started() -> None` - No public docstring in the audited version.
- **function**, line 88: `native_wait_finished() -> None` - No public docstring in the audited version.
- **function**, line 82: `native_wait_started() -> None` - No public docstring in the audited version.
- **function**, line 136: `render_prometheus() -> str` - Render the current process metrics using the Prometheus text format.
- **function**, line 217: `reset_for_tests() -> None` - No public docstring in the audited version.
- **function**, line 56: `worker_finished(tool: str, *, duration_seconds: float, ok: bool, error_code: str | None) -> None` - No public docstring in the audited version.
- **function**, line 49: `worker_started(tool: str) -> None` - No public docstring in the audited version.

## `mcp_runtime.temp_compat`

- **function**, line 47: `ensure_usable_mkdtemp(is_usable: Optional[Callable[[], bool]] = None) -> bool` - Replace ``tempfile.mkdtemp`` when its folders are unusable. Returns True when it was replaced.
- **function**, line 19: `mkdtemp_is_usable() -> bool` - Whether a folder made by ``tempfile.mkdtemp`` accepts a file.

## `mcp_runtime.tool_registry`

- **function**, line 149: `build_registry(profile: str | None = None) -> dict[str, ToolSpec]` - No public docstring in the audited version.
- **function**, line 141: `normalize_profile(profile: str | None = None) -> str` - Return the canonical profile name; None means CHEMDRAW_MCP_PROFILE or the default.
- **class**, line 32: `ToolSpec` - No public docstring in the audited version.

## `mcp_runtime.tool_worker`

- **function**, line 30: `worker_log_dir() -> Path` - Folder of ``worker-<id>.log`` files (``cdx.py doctor --paths`` prints it).

## `model.document`

- **function**, line 30: `catalog_index() -> dict[str, dict[str, dict[str, Any]]]` - Catalog elements as ``{element: {attribute: {kind, values?}}}``.
- **class**, line 72: `Document` - A parsed CDXML file; ``prologue`` is the text before the root element.
- **method**, line 236: `Document.add(parent: ET.Element, tag: str, props: Optional[dict[str, Any]] = None, *, children: Optional[list[dict[str, Any]]] = None, text: Optional[str] = None, allow_unknown: bool = False) -> ET.Element` - Append a new element (and nested ``children``) to ``parent``; ids are assigned.
- **method**, line 154: `Document.check() -> list[dict[str, Any]]` - Structural problems: duplicate ids and references to objects that do not exist.
- **method**, line 274: `Document.delete(element: ET.Element) -> int` - Remove ``element`` and its subtree; refuse the root and objects other objects point at.
- **method**, line 137: `Document.describe(element: ET.Element, parents: Optional[dict[int, ET.Element]] = None) -> dict[str, Any]` - No public docstring in the audited version.
- **method**, line 297: `Document.dump_bytes() -> bytes` - No public docstring in the audited version.
- **method**, line 290: `Document.dumps() -> str` - No public docstring in the audited version.
- **method**, line 81: `Document.elements() -> Iterable[ET.Element]` - No public docstring in the audited version.
- **method**, line 91: `Document.ids() -> set[str]` - No public docstring in the audited version.
- **method**, line 232: `Document.next_id() -> int` - No public docstring in the audited version.
- **method**, line 84: `Document.parent_map() -> dict[int, ET.Element]` - ``{id(child): parent}`` for the whole tree; rebuild it after an edit.
- **method**, line 88: `Document.parent_of(element: ET.Element, parents: Optional[dict[int, ET.Element]] = None) -> Optional[ET.Element]` - No public docstring in the audited version.
- **method**, line 128: `Document.path_of(element: ET.Element, parents: Optional[dict[int, ET.Element]] = None) -> str` - No public docstring in the audited version.
- **method**, line 94: `Document.select(selector: str) -> list[ET.Element]` - Elements matching ``step > step ...``; a step is ``tag#id[Attr=value]...``.
- **method**, line 208: `Document.set_properties(element: ET.Element, props: dict[str, Any], *, allow_unknown: bool = False) -> dict[str, tuple]` - Set, replace or (with ``None``) remove attributes; returns ``{name: (old, new)}``.
- **function**, line 319: `load(path: str | Path) -> Document` - No public docstring in the audited version.
- **function**, line 301: `parse(source: str | bytes) -> Document` - Parse CDXML text or bytes; the root must be ``CDXML``.

## `publication.data`

- **function**, line 146: `field_text(record, field)` - No public docstring in the audited version.
- **function**, line 83: `load_records(spec, base)` - No public docstring in the audited version.
- **function**, line 15: `local_path(base, value)` - No public docstring in the audited version.
- **function**, line 11: `sha256(path)` - No public docstring in the audited version.
- **function**, line 36: `table_rows(path, sheet = None)` - No public docstring in the audited version.
- **function**, line 155: `write_json(path, value)` - No public docstring in the audited version.

## `publication.layout`

- **function**, line 197: `bounds(node, style)` - No public docstring in the audited version.
- **function**, line 219: `check_pages(project, roots, spec)` - No public docstring in the audited version.
- **function**, line 111: `create_pages(records, spec, stage, start_index = 0)` - No public docstring in the audited version.
- **function**, line 25: `font_for(style, size = None)` - No public docstring in the audited version.
- **function**, line 53: `fragment_mol(fragment)` - No public docstring in the audited version.
- **function**, line 64: `molecule_coordinates(mol, bond_length, reference = None)` - No public docstring in the audited version.
- **function**, line 60: `node_text(node)` - No public docstring in the audited version.
- **function**, line 215: `overlap(a, b)` - No public docstring in the audited version.
- **function**, line 84: `prepare(records, spec)` - No public docstring in the audited version.
- **function**, line 15: `style_settings(spec)` - No public docstring in the audited version.
- **function**, line 36: `text_width(value, style, size = None)` - No public docstring in the audited version.
- **function**, line 41: `wrap(value, width, style)` - No public docstring in the audited version.

## `publication.update`

- **function**, line 37: `match_objects(group, record)` - No public docstring in the audited version.
- **function**, line 16: `matching_group(root, record)` - No public docstring in the audited version.
- **function**, line 56: `replace_text(node, old, new)` - Preserve unchanged rich runs; single-run labels retain all their style.
- **function**, line 86: `replacement_fragment(old_fragment, new_smiles, atom_map, stage, root, cid)` - No public docstring in the audited version.
- **function**, line 151: `update_pages(base_project, base_dir, records, spec, spec_dir, stage)` - No public docstring in the audited version.

## `reaction_calculator.annotate`

- **function**, line 17: `key(mol_or_smiles) -> str | None` - No public docstring in the audited version.
- **function**, line 44: `read_fragments_from_text(text: str)` - (id, mol) of each top-level fragment of CDXML text.

## `reaction_calculator.engine`

- **function**, line 63: `compute(state: dict) -> dict` - Amounts of every row from the limiting row and the quantity fixed on each row.

## `reaction_calculator.hazards`

- **function**, line 133: `entries() -> list[dict]` - No public docstring in the audited version.
- **function**, line 153: `for_rows(rows: list[dict]) -> list[dict]` - A safety item per reactant, reagent, catalyst and solvent row: the entry, or ``listed: False``.
- **function**, line 168: `lines(items: list[dict]) -> list[str]` - Text lines for a table footer: the heading, one line per listed species, the species not listed.
- **function**, line 122: `lookup(smiles: str) -> dict | None` - The entry for a structure (stereo and drawing coordinates ignored), or None when it is not listed.
- **function**, line 137: `summary(entry: dict) -> str` - One line: signal word, pictograms, statements, boiling and flash point, note.

## `reaction_calculator.library`

- **function**, line 100: `by_name(text: str) -> dict | None` - The library entry for a name or common abbreviation (case-insensitive).
- **function**, line 90: `by_smiles(smiles: str) -> dict | None` - The library entry for a structure, matched on canonical SMILES (stereo and isotopes ignored).
- **function**, line 105: `entries() -> list[dict]` - Every entry once.

## `reaction_calculator.materials`

- **function**, line 120: `csv_text(entries: list[dict]) -> str` - No public docstring in the audited version.
- **function**, line 162: `html_text(entries: list[dict]) -> str` - No public docstring in the audited version.
- **function**, line 103: `markdown(entries: list[dict]) -> str` - No public docstring in the audited version.
- **function**, line 42: `procedure(rows: list[dict], limiting: str, totals: dict) -> str` - One sentence in the usual experimental style, from computed rows.
- **function**, line 19: `trim(value, digits: int = 3) -> str` - Significant digits without trailing zeros: 1.00 -> 1, 94.2 -> 94.2.
- **function**, line 27: `volume_phrase(ml: float) -> str` - No public docstring in the audited version.

## `reaction_calculator.state`

- **function**, line 69: `build_state(sides: dict, options: dict | None = None) -> dict` - Rows for one reaction; ``sides`` maps reactants, agents and products to species dicts.

## `reaction_templates`

- **function**, line 105: `classify(reactants, agents, products) -> dict` - Name the reaction by the generic template that makes the drawn products from its structures.
- **function**, line 171: `reaction_center(mapped_reaction: str) -> dict` - The reaction centre of an atom-mapped reaction SMILES as a reaction SMARTS.
- **function**, line 223: `reproduces(smarts, reactants, products) -> bool | None` - Whether the template run on ``reactants`` (list of mols) makes one of ``products``; None if it cannot run.
- **function**, line 335: `write_map_numbers(text: str, numbers: dict) -> tuple[str, list]` - (CDXML text with the map numbers added, warnings).

## `route_metrics`

- **function**, line 57: `summarize(raw) -> dict` - No public docstring in the audited version.

## `spectral_text`

- **function**, line 258: `describe(record: dict, mol, label: str) -> dict` - The paragraph (without HRMS) of one compound, with the checks that were run and their warnings.
- **function**, line 147: `distinct_carbons(mol) -> int` - Carbons that differ by symmetry (what a decoupled 13C spectrum can show at most).
- **function**, line 115: `format_peak(peak: dict) -> str` - No public docstring in the audited version.
- **function**, line 123: `format_peaks(peaks) -> str` - No public docstring in the audited version.
- **function**, line 143: `formula_hydrogens(mol) -> int` - No public docstring in the audited version.
- **function**, line 127: `known_multiplicity(mult: str) -> bool` - No public docstring in the audited version.
- **function**, line 92: `normalize_peaks(items, decimals: int) -> list[dict]` - Peaks given as text, numbers or dicts -> the dicts :func:`parse_peaks` returns.
- **function**, line 132: `nucleus_ok(name: str) -> bool` - No public docstring in the audited version.
- **function**, line 66: `parse_peaks(text: str) -> list[dict]` - Peaks of an NMR list such as ``7.40-7.30 (m, 5H), 5.11 (s, 2H)`` as dicts.
