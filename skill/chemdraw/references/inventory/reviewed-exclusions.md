# Reviewed Exclusions Public Symbols

> Generated from cdxml-toolkit 0.7.0a3. Curated guidance: [../toolkit-reviewed-exclusions.md](../toolkit-reviewed-exclusions.md).

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

## `mcp_runtime`

- **function**, line 5: `build_server(*args, **kwargs)` - Build the complete MCP server without importing it during package discovery.

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
- **class**, line 362: `LargestCommonSubstructure` - No public docstring in the audited version.
- **method**, line 372: `LargestCommonSubstructure.AtomMapM1() -> AtomMap` - No public docstring in the audited version.
- **method**, line 375: `LargestCommonSubstructure.AtomMapM2() -> AtomMap` - No public docstring in the audited version.
- **method**, line 367: `LargestCommonSubstructure.Compute(first: StructureData, second: StructureData)` - No public docstring in the audited version.
- **class**, line 426: `MacSdkRuntime` - The program runtime interface of ``ChemScriptRuntime``, for the emulation.
- **method**, line 476: `MacSdkRuntime.catalog() -> tuple[list[dict], list[dict]]` - No public docstring in the audited version.
- **method**, line 464: `MacSdkRuntime.check_member(owner: Any, member: str, operation: str) -> None` - Refuse anything that is not an emulated public member (no Python internals).
- **method**, line 461: `MacSdkRuntime.member_is_interop(reflection_type, member: str) -> bool` - No public docstring in the audited version.
- **method**, line 440: `MacSdkRuntime.python_type(name: str)` - No public docstring in the audited version.
- **method**, line 431: `MacSdkRuntime.reflection_type(name: str) -> _Type` - No public docstring in the audited version.
- **method**, line 443: `MacSdkRuntime.resolve_argument(value: Any, aliases: dict[str, Any], *, unsafe: bool)` - No public docstring in the audited version.
- **class**, line 288: `ReactionData` - No public docstring in the audited version.
- **method**, line 340: `ReactionData.Formula() -> str` - No public docstring in the audited version.
- **method**, line 295: `ReactionData.LoadData(data: str, mimetype: Optional[str] = None)` - No public docstring in the audited version.
- **method**, line 318: `ReactionData.LoadFile(path: str, mimetype: Optional[str] = None)` - No public docstring in the audited version.
- **property**, line 337: `ReactionData.Products` - No public docstring in the audited version.
- **property**, line 333: `ReactionData.Reactants` - No public docstring in the audited version.
- **method**, line 343: `ReactionData.WriteData(mimetype: str = 'chemical/x-mdl-rxn') -> str` - No public docstring in the audited version.
- **method**, line 350: `ReactionData.WriteFile(path: str, mimetype: Optional[str] = None) -> bool` - No public docstring in the audited version.
- **class**, line 161: `StructureData` - No public docstring in the audited version.
- **method**, line 279: `StructureData.AtomByAtomSearch(target: 'StructureData')` - No public docstring in the audited version.
- **property**, line 229: `StructureData.Atoms` - No public docstring in the audited version.
- **property**, line 233: `StructureData.Bonds` - No public docstring in the audited version.
- **method**, line 225: `StructureData.ChemicalName() -> str` - No public docstring in the audited version.
- **method**, line 258: `StructureData.CleanupStructure() -> bool` - No public docstring in the audited version.
- **method**, line 275: `StructureData.ContainsSubstructure(query: 'StructureData') -> bool` - No public docstring in the audited version.
- **method**, line 222: `StructureData.Formula() -> str` - No public docstring in the audited version.
- **method**, line 176: `StructureData.LoadData(data: str, mimetype: Optional[str] = None)` - No public docstring in the audited version.
- **method**, line 188: `StructureData.LoadFile(path: str, mimetype: Optional[str] = None)` - No public docstring in the audited version.
- **method**, line 213: `StructureData.MimeTypes()` - No public docstring in the audited version.
- **method**, line 267: `StructureData.Overlay(target: 'StructureData') -> bool` - No public docstring in the audited version.
- **method**, line 192: `StructureData.ReadFile(path: str, mimetype: Optional[str] = None) -> bool` - No public docstring in the audited version.
- **method**, line 237: `StructureData.WriteData(mimetype: str = 'text/xml') -> str` - No public docstring in the audited version.
- **method**, line 244: `StructureData.WriteFile(path: str, mimetype: Optional[str] = None) -> bool` - No public docstring in the audited version.

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

## `mcp_runtime.decimer_api`

- **function**, line 75: `build_multipart_body(*, filename: str, mime_type: str, image_bytes: bytes, hand_drawn: bool, boundary: str | None = None) -> tuple[str, bytes]` - Encode the multipart fields declared by the live OpenAPI document.
- **class**, line 36: `DecimerAPIError` - Raised when the remote DECIMER service cannot return usable SMILES.
- **method**, line 43: `DecimerAPIError.as_result() -> dict[str, Any]` - No public docstring in the audited version.
- **class**, line 50: `DecimerUploadRefused` - Raised when upload consent is absent or does not match the prepared upload.
- **function**, line 54: `normalize_api_payload(payload: Any) -> dict[str, Any]` - Normalize both the documented string and live list response shapes.
- **function**, line 471: `recognize_image(image_path: str, *, hand_drawn: bool = False, timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS, output_path: str | None = None, confirm_upload: bool = False, approved_sha256: str | None = None, approved_origin: str | None = None) -> dict[str, Any]` - Upload one image to DECIMER and return normalized, validated predictions.
- **function**, line 239: `urlopen(request: Request, *, timeout: int)` - Open a request with redirect checks applied before a redirected upload.

## `mcp_runtime.extended_tools`

- **function**, line 1114: `analyze_lcms_series(files: list[str], output_path: Optional[str] = None, rt_tolerance: float = 0.02, mz_tolerance: float = 0.5, trend_threshold: float = 0.2, ignore_instrument: bool = False) -> dict[str, Any]` - Analyze a chronological series of standard LCMS PDF reports.
- **function**, line 1184: `assemble_lab_book(input_dir: str, experiment: Optional[str] = None, tracking_json: Optional[str] = None, output_path: Optional[str] = None) -> dict[str, Any]` - Assemble a deterministic lab-book entry from experiment files.
- **function**, line 785: `batch_embed_cdxml_in_office(cdxml_paths: list[str], output_path: str, margin_pt: float = 0) -> dict[str, Any]` - Create PPTX or DOCX containing editable ChemDraw OLE objects.
- **function**, line 470: `clean_scheme_layout(input_path: str, output_path: Optional[str] = None, approach: str = 'chemdraw_mimic', render_preview: bool = True) -> dict[str, Any]` - Clean an existing CDXML reaction layout without changing the source file.
- **function**, line 1082: `discover_experiment_files(input_dir: str, experiment: Optional[str] = None, output_path: Optional[str] = None) -> dict[str, Any]` - Discover and classify files belonging to one experiment.
- **function**, line 709: `fill_office_template(template_path: str, manifest_path: str, output_path: Optional[str] = None) -> dict[str, Any]` - Fill PPTX/DOCX text and editable ChemDraw placeholders from a manifest.
- **function**, line 845: `inspect_chemdraw_objects_in_office(input_path: str, output_dir: Optional[str] = None, render_previews: bool = True) -> dict[str, Any]` - Inventory editable ChemDraw objects and extract numbered CDXML previews.
- **function**, line 490: `merge_reaction_schemes(input_paths: list[str], output_path: Optional[str] = None, mode: str = 'auto', equiv_mode: str = 'default', reference_cdxml: Optional[str] = None, allow_adjacent: bool = True, render_preview: bool = True, force_sequential: bool = False) -> dict[str, Any]` - Merge parallel, sequential, or unrelated CDXML reaction schemes.
- **function**, line 1218: `parse_scifinder_rdf(input_path: str, resolve_cas: bool = False, output_path: Optional[str] = None, confirm_pubchem: bool = False) -> dict[str, Any]` - Parse SciFinder RDF and optionally enrich CAS data over the network.
- **function**, line 570: `polish_reaction_scheme(input_path: str, output_path: Optional[str] = None, merge_conditions: bool = True, approach: str = 'chemdraw_mimic', align_mode: str = 'rdkit', eln_csv: Optional[str] = None, reference_cdxml: Optional[str] = None, render_preview: bool = True) -> dict[str, Any]` - Run the audited deterministic polishing pipeline on a CDXML scheme.
- **function**, line 602: `render_cdxml_files(input_paths: list[str], output_dir: Optional[str] = None, format: str = 'png', dpi: int = 300) -> dict[str, Any]` - Render one or more CDXML files through native ChemDraw (COM or macOS).
- **function**, line 951: `replace_chemdraw_objects_in_office(input_path: str, replacements_manifest: str, output_path: Optional[str] = None, render_pdf_preview: bool = True, resize_frames: bool = False) -> dict[str, Any]` - Replace selected ChemDraw OLE contents and previews without moving them.
- **function**, line 1326: `segment_large_scheme(cdxml_path: str, output_path: Optional[str] = None, verbose: bool = False) -> dict[str, Any]` - Segment a disconnected or multi-panel CDXML scheme into logical regions.

## `mcp_runtime.figure_editing`

- **function**, line 4: `apply_crossings(page, crossings)` - No public docstring in the audited version.
- **function**, line 50: `edit_bond_display(node, edit)` - No public docstring in the audited version.

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

- **class**, line 526: `ApiKeyMiddleware` - Require a bearer token without placing it in logs or worker environments.
- **function**, line 724: `build_http_app(args: argparse.Namespace, *, environ = None)` - No public docstring in the audited version.
- **function**, line 663: `build_server(*, profile: str | None = None, **server_settings)` - No public docstring in the audited version.
- **function**, line 692: `parse_args(argv: list[str] | None = None) -> argparse.Namespace` - No public docstring in the audited version.
- **function**, line 590: `resolve_http_configuration(*, host: str, port: int, allowed_hosts: list[str], allowed_origins: list[str], environ: typing.Mapping[str, str] | None = None, api_key_env: str = 'CHEMDRAW_MCP_HTTP_API_KEY') -> dict[str, typing.Any]` - Validate remote HTTP exposure and return non-secret server settings.
- **function**, line 762: `run_streamable_http(args: argparse.Namespace) -> None` - No public docstring in the audited version.

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

- **class**, line 27: `NativeRenderError` - ChemDraw rendering failure with a stable public error code.
- **class**, line 95: `NativeRenderSession` - Lazily acquire and reuse one ChemDraw application for native exports.
- **method**, line 170: `NativeRenderSession.render(source: str | Path, destination: str | Path, dpi: int = 300) -> str` - No public docstring in the audited version.
- **function**, line 241: `render_cdxml(source: str | Path, destination: str | Path, *, dpi: int = 300, timeout_seconds: int = 30) -> str` - No public docstring in the audited version.
- **function**, line 22: `renderer_name() -> str` - The native renderer on this platform, as written in render receipts.

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

- **function**, line 552: `check_reaction_balance(reaction: str | dict, options: dict | None = None, output_path: str | None = None) -> dict` - Check that a reaction conserves atoms and charge, and optionally tabulate its stoichiometry.
- **function**, line 623: `export_structures(source: str | list, options: dict | None = None, output_path: str | None = None) -> dict` - Export every structure in a file or list as SMILES, InChI, InChIKey, formula and mass.
- **function**, line 287: `molecule_report(molecules: list[dict], output_path: str | None = None) -> dict` - Property sheet for grounded molecules: formula, masses, MS adducts, drug-likeness.
- **function**, line 443: `signs(species)` - No public docstring in the audited version.

## `mcp_runtime.resource_lock`

- **function**, line 46: `native_resource_lock(resource_class: str | None, timeout_seconds: int) -> Iterator[None]` - Serialize ChemDraw automation across workers in the current user session.
- **class**, line 34: `ResourceBusyError` - Raised when an exclusive native resource cannot be acquired in time.

## `mcp_runtime.runtime_diagnostics`

- **function**, line 507: `diagnose_runtime(run_native_probe: bool = False, run_office_probe: bool = False, run_chemscript_probe: bool = False) -> dict[str, Any]` - Report local runtime capabilities; native probes are explicit and temporary.

## `mcp_runtime.runtime_discovery`

- **class**, line 28: `Discovery` - No public docstring in the audited version.
- **method**, line 32: `Discovery.to_dict() -> dict[str, str]` - No public docstring in the audited version.
- **function**, line 299: `find_chemdraw(explicit: str | None = None) -> Discovery` - Find ChemDraw from explicit, environment, the macOS application, COM, then common paths.
- **function**, line 144: `find_python(explicit: str | None = None) -> Discovery` - Find and probe Python using explicit, environment, then implicit paths.
- **function**, line 185: `find_skill_root(explicit: str | None = None) -> Discovery` - No public docstring in the audited version.

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

## `mcp_runtime.tool_registry`

- **function**, line 132: `build_registry(profile: str | None = None) -> dict[str, ToolSpec]` - No public docstring in the audited version.
- **function**, line 124: `normalize_profile(profile: str | None = None) -> str` - Return the canonical profile name; None means CHEMDRAW_MCP_PROFILE or the default.
- **class**, line 28: `ToolSpec` - No public docstring in the audited version.

## `mcp_runtime.tool_worker`

- **function**, line 30: `worker_log_dir() -> Path` - Folder of ``worker-<id>.log`` files (``cdx.py doctor --paths`` prints it).

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
