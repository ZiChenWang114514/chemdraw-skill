# Reviewed Exclusions Public Symbols

> Generated from cdxml-toolkit 0.7.0a1. Curated guidance: [../toolkit-reviewed-exclusions.md](../toolkit-reviewed-exclusions.md).

## `chemistry_semantics`

- **function**, line 74: `document_inventory(path)` - No public docstring in the audited version.
- **function**, line 32: `read_molecules(value)` - No public docstring in the audited version.
- **function**, line 20: `require_supported(mol)` - No public docstring in the audited version.
- **function**, line 10: `semantic_key(mol)` - No public docstring in the audited version.
- **function**, line 78: `validate_document_preserved(source, output)` - No public docstring in the audited version.
- **function**, line 57: `validate_fragment(smiles, xml)` - No public docstring in the audited version.

## `mcp_runtime`

- **function**, line 5: `build_server(*args, **kwargs)` - Build the complete MCP server without importing it during package discovery.

## `mcp_runtime.artifact_safety`

- **function**, line 229: `artifact_record(path: str | Path) -> dict[str, Any]` - No public docstring in the audited version.
- **function**, line 242: `artifact_records(paths: Iterable[str | Path]) -> list[dict[str, Any]]` - No public docstring in the audited version.
- **function**, line 254: `paths_from_value(value: Any) -> list[Path]` - No public docstring in the audited version.
- **function**, line 200: `publish_directory(staged: str | Path, destination: str | Path) -> None` - No public docstring in the audited version.
- **function**, line 146: `publish_file(staged: str | Path, destination: str | Path) -> None` - No public docstring in the audited version.
- **function**, line 184: `publish_files(staged_outputs: Iterable[tuple[Path, Path]]) -> None` - No public docstring in the audited version.
- **function**, line 44: `resolve_destination(*, source: str | Path | None, output_path: str | Path | None, tag: str, suffix: str, base_dir: str | Path | None = None) -> Path` - No public docstring in the audited version.
- **function**, line 76: `resolve_directory_destination(*, source: str | Path, output_dir: str | Path | None, tag: str) -> Path` - No public docstring in the audited version.
- **function**, line 280: `rewrite_paths(value: Any, old_root: str | Path, new_root: str | Path) -> Any` - No public docstring in the audited version.
- **function**, line 299: `stage_validate_publish(destination: str | Path, writer: Callable[[Path], Any], *, validator: Callable[[Path], Any] = validate_artifact) -> tuple[Any, Path]` - No public docstring in the audited version.
- **function**, line 135: `staging_directory(destination: str | Path) -> Iterator[Path]` - No public docstring in the audited version.
- **function**, line 125: `staging_file(destination: str | Path) -> Iterator[Path]` - No public docstring in the audited version.
- **function**, line 98: `validate_artifact(path: str | Path) -> Path` - No public docstring in the audited version.
- **function**, line 18: `validate_input_file(path: str | Path, *, suffixes: tuple[str, ...] | None = None) -> Path` - No public docstring in the audited version.
- **function**, line 272: `with_artifacts(result: dict[str, Any], paths: Iterable[str | Path]) -> dict[str, Any]` - No public docstring in the audited version.

## `mcp_runtime.capabilities`

- **function**, line 22: `get_toolkit_capabilities() -> dict[str, Any]` - Return versions, profile, tool schema digest, and local capability status.

## `mcp_runtime.chemistry_compare`

- **function**, line 206: `batch_compare_molecules(pairs: list[dict[str, Any]], fingerprint: str = 'morgan', radius: int = 2, n_bits: int = 2048) -> dict[str, Any]` - Compare up to 256 molecule pairs with one ChemScript bridge session.
- **function**, line 145: `compare_molecules(molecule_a: str, molecule_b: str, fingerprint: str = 'morgan', radius: int = 2, n_bits: int = 2048) -> dict[str, Any]` - Compare two molecule representations using ChemScript identity and RDKit Tanimoto fingerprints.

## `mcp_runtime.chemscript_sdk`

- **function**, line 166: `execute_chemscript_sdk(program: list[dict[str, Any]], allow_file_io: bool = False, allow_overwrite: bool = False, allow_unsafe_interop: bool = False, max_items: int = 100) -> dict[str, Any]` - Execute a declarative ChemScript SDK program in an isolated Python.NET process.
- **function**, line 108: `inspect_chemscript_sdk(query: Optional[str] = None, type_name: Optional[str] = None, include_infrastructure: bool = False, offset: int = 0, limit: int = 100, output_path: Optional[str] = None) -> dict[str, Any]` - Catalog every public ChemScript type/member, with filtering or a complete JSON export.

## `mcp_runtime.chemscript_sdk_runtime`

- **function**, line 447: `catalog_sdk(runtime: ChemScriptRuntime, request: dict[str, Any]) -> dict[str, Any]` - No public docstring in the audited version.
- **class**, line 147: `ChemScriptRuntime` - One direct Python.NET session for cataloging and executing an SDK program.
- **method**, line 289: `ChemScriptRuntime.member_is_interop(reflection_type, member: str) -> bool` - No public docstring in the audited version.
- **method**, line 201: `ChemScriptRuntime.python_type(name: str)` - No public docstring in the audited version.
- **method**, line 187: `ChemScriptRuntime.reflection_type(name: str)` - No public docstring in the audited version.
- **method**, line 224: `ChemScriptRuntime.resolve_argument(value: Any, aliases: dict[str, Any], *, unsafe: bool)` - No public docstring in the audited version.
- **method**, line 213: `ChemScriptRuntime.system_python_type(name: str)` - No public docstring in the audited version.
- **function**, line 575: `execute_program(runtime: ChemScriptRuntime, request: dict[str, Any]) -> dict[str, Any]` - No public docstring in the audited version.
- **function**, line 63: `validate_program(program: list[dict[str, Any]], *, allow_file_io: bool = True, allow_unsafe_interop: bool = False) -> list[dict[str, Any]]` - Validate the declarative SDK program without loading Python.NET.

## `mcp_runtime.codex_config`

- **function**, line 27: `update_config(config_path: str | os.PathLike[str], python_path: str | os.PathLike[str], *, expected_sha256: str | None = None) -> dict` - Update one MCP table while preserving unrelated TOML content and settings.

## `mcp_runtime.decimer_api`

- **function**, line 72: `build_multipart_body(*, filename: str, mime_type: str, image_bytes: bytes, hand_drawn: bool, boundary: str | None = None) -> tuple[str, bytes]` - Encode the multipart fields declared by the live OpenAPI document.
- **class**, line 33: `DecimerAPIError` - Raised when the remote DECIMER service cannot return usable SMILES.
- **method**, line 40: `DecimerAPIError.as_result() -> dict[str, Any]` - No public docstring in the audited version.
- **class**, line 47: `DecimerUploadRefused` - Raised when upload consent is absent or does not match the prepared upload.
- **function**, line 51: `normalize_api_payload(payload: Any) -> dict[str, Any]` - Normalize both the documented string and live list response shapes.
- **function**, line 437: `recognize_image(image_path: str, *, hand_drawn: bool = False, timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS, output_path: str | None = None, confirm_upload: bool = False, approved_sha256: str | None = None, approved_origin: str | None = None) -> dict[str, Any]` - Upload one image to DECIMER and return normalized, validated predictions.
- **function**, line 236: `urlopen(request: Request, *, timeout: int)` - Open a request with redirect checks applied before a redirected upload.

## `mcp_runtime.extended_tools`

- **function**, line 1051: `analyze_lcms_series(files: list[str], output_path: Optional[str] = None, rt_tolerance: float = 0.02, mz_tolerance: float = 0.5, trend_threshold: float = 0.2, ignore_instrument: bool = False) -> dict[str, Any]` - Analyze a chronological series of standard LCMS PDF reports.
- **function**, line 1121: `assemble_lab_book(input_dir: str, experiment: Optional[str] = None, tracking_json: Optional[str] = None, output_path: Optional[str] = None) -> dict[str, Any]` - Assemble a deterministic lab-book entry from experiment files.
- **function**, line 785: `batch_embed_cdxml_in_office(cdxml_paths: list[str], output_path: str, margin_pt: float = 0) -> dict[str, Any]` - Create PPTX or DOCX containing editable ChemDraw OLE objects.
- **function**, line 470: `clean_scheme_layout(input_path: str, output_path: Optional[str] = None, approach: str = 'chemdraw_mimic', render_preview: bool = True) -> dict[str, Any]` - Clean an existing CDXML reaction layout without changing the source file.
- **function**, line 1019: `discover_experiment_files(input_dir: str, experiment: Optional[str] = None, output_path: Optional[str] = None) -> dict[str, Any]` - Discover and classify files belonging to one experiment.
- **function**, line 709: `fill_office_template(template_path: str, manifest_path: str, output_path: Optional[str] = None) -> dict[str, Any]` - Fill PPTX/DOCX text and editable ChemDraw placeholders from a manifest.
- **function**, line 845: `inspect_chemdraw_objects_in_office(input_path: str, output_dir: Optional[str] = None, render_previews: bool = True) -> dict[str, Any]` - Inventory editable ChemDraw objects and extract numbered CDXML previews.
- **function**, line 490: `merge_reaction_schemes(input_paths: list[str], output_path: Optional[str] = None, mode: str = 'auto', equiv_mode: str = 'default', reference_cdxml: Optional[str] = None, allow_adjacent: bool = True, render_preview: bool = True, force_sequential: bool = False) -> dict[str, Any]` - Merge parallel, sequential, or unrelated CDXML reaction schemes.
- **function**, line 1155: `parse_scifinder_rdf(input_path: str, resolve_cas: bool = False, output_path: Optional[str] = None, confirm_pubchem: bool = False) -> dict[str, Any]` - Parse SciFinder RDF and optionally enrich CAS data over the network.
- **function**, line 570: `polish_reaction_scheme(input_path: str, output_path: Optional[str] = None, merge_conditions: bool = True, approach: str = 'chemdraw_mimic', align_mode: str = 'rdkit', eln_csv: Optional[str] = None, reference_cdxml: Optional[str] = None, render_preview: bool = True) -> dict[str, Any]` - Run the audited deterministic polishing pipeline on a CDXML scheme.
- **function**, line 602: `render_cdxml_files(input_paths: list[str], output_dir: Optional[str] = None, format: str = 'png', dpi: int = 300) -> dict[str, Any]` - Render one or more CDXML files through native ChemDraw COM.
- **function**, line 914: `replace_chemdraw_objects_in_office(input_path: str, replacements_manifest: str, output_path: Optional[str] = None, render_pdf_preview: bool = True) -> dict[str, Any]` - Replace selected ChemDraw OLE contents and previews without moving them.
- **function**, line 1263: `segment_large_scheme(cdxml_path: str, output_path: Optional[str] = None, verbose: bool = False) -> dict[str, Any]` - Segment a disconnected or multi-panel CDXML scheme into logical regions.

## `mcp_runtime.figure_tools`

- **function**, line 577: `compare_figure_images(reference_path: str, candidate_path: str, output_path: str) -> dict` - Compare aligned local raster previews without resizing or warping.
- **function**, line 206: `compose_chemical_figure(manifest_path: str, output_path: str) -> dict` - Compose editable CDXML using explicit point coordinates and grounded molecules.
- **function**, line 70: `rdkit_workbench(molecules: list[dict], operation: str = 'inspect', options: dict | None = None, output_path: str | None = None) -> dict` - Analyze grounded molecules: inspect, stereoisomers, tautomers, mcs, r_groups, set_stereo.

## `mcp_runtime.generate_reference`

- **function**, line 33: `manifest(profile: str = 'codex') -> dict` - No public docstring in the audited version.
- **function**, line 59: `render_markdown(profile: str = 'codex') -> str` - No public docstring in the audited version.
- **function**, line 92: `render_reference(profile: str = 'codex') -> str` - Compatibility alias used by ChemDraw Skill catalog checks.

## `mcp_runtime.install_decimer_models`

- **function**, line 35: `download(url: str, destination: Path, proxy: str | None) -> None` - No public docstring in the audited version.
- **function**, line 45: `file_hash(path: Path, algorithm: str) -> str` - No public docstring in the audited version.
- **function**, line 116: `install_model(model: dict[str, str], target: Path, *, proxy: str | None, downloader = download) -> dict[str, str]` - No public docstring in the audited version.
- **function**, line 53: `md5(path: Path) -> str` - No public docstring in the audited version.
- **function**, line 61: `safe_extract(archive: Path, destination: Path) -> None` - No public docstring in the audited version.
- **function**, line 74: `select_models(keys: list[str] | None) -> list[dict[str, str]]` - No public docstring in the audited version.
- **function**, line 57: `sha256(path: Path) -> str` - No public docstring in the audited version.

## `mcp_runtime.mcp_compat`

- **function**, line 45: `install_legacy_fastmcp_alias() -> None` - Provide the legacy FastMCP import expected by the core MCP module.
- **function**, line 19: `sdk_major(version: str | None = None) -> int` - Return a supported MCP SDK major version or raise a clear error.
- **function**, line 14: `sdk_version() -> str` - Return the installed MCP Python SDK distribution version.
- **function**, line 34: `server_class() -> type[Any]` - Return the high-level server class for the installed SDK.

## `mcp_runtime.mcp_server`

- **class**, line 489: `ApiKeyMiddleware` - Require a bearer token without placing it in logs or worker environments.
- **function**, line 686: `build_http_app(args: argparse.Namespace, *, environ = None)` - No public docstring in the audited version.
- **function**, line 626: `build_server(*, profile: str | None = None, **server_settings)` - No public docstring in the audited version.
- **function**, line 654: `parse_args(argv: list[str] | None = None) -> argparse.Namespace` - No public docstring in the audited version.
- **function**, line 553: `resolve_http_configuration(*, host: str, port: int, allowed_hosts: list[str], allowed_origins: list[str], environ: typing.Mapping[str, str] | None = None, api_key_env: str = 'CHEMDRAW_MCP_HTTP_API_KEY') -> dict[str, typing.Any]` - Validate remote HTTP exposure and return non-secret server settings.
- **function**, line 724: `run_streamable_http(args: argparse.Namespace) -> None` - No public docstring in the audited version.

## `mcp_runtime.native_io`

- **function**, line 124: `ascii_input_directory(source: str | Path, *, suffixes: Sequence[str] = ('.cdxml', '.cdx', '.csv', '.rxn')) -> Iterator[tuple[Path, dict[str, str]]]` - No public docstring in the audited version.
- **function**, line 108: `ascii_inputs(sources: Sequence[str | Path]) -> Iterator[list[Path]]` - No public docstring in the audited version.
- **function**, line 91: `ascii_workspace(prefix: str = 'cdx-') -> Iterator[Path]` - No public docstring in the audited version.
- **function**, line 350: `batch_convert_cdxml(sources: Sequence[str | Path], batch_convert: Callable[[list[str]], Any]) -> list[dict[str, Any]]` - No public docstring in the audited version.
- **function**, line 207: `bridge_file(source: str | Path, destination: str | Path, operation: Callable[[Path, Path], Any], *, output_kind: str | None = None, preserve_source_context: bool = False) -> Any` - No public docstring in the audited version.
- **function**, line 379: `convert_cdx_bytes_to_cdxml(cdx_data: bytes, converter: Callable[..., Any]) -> str` - No public docstring in the audited version.
- **class**, line 18: `NativeIOError` - Native automation failure with a stable public error code.
- **function**, line 442: `rewrite_json_paths(path: str | Path, replacements: dict[str, str]) -> None` - No public docstring in the audited version.
- **function**, line 150: `validate_native_output(path: str | Path, kind: str | None = None) -> Path` - No public docstring in the audited version.
- **function**, line 400: `write_shadow_manifest(manifest: str | Path, workspace: str | Path) -> tuple[Path, list[Path]]` - No public docstring in the audited version.

## `mcp_runtime.native_renderer`

- **class**, line 11: `NativeRenderError` - ChemDraw rendering failure with a stable public error code.
- **class**, line 79: `NativeRenderSession` - Lazily acquire and reuse one ChemDraw application for native exports.
- **method**, line 142: `NativeRenderSession.render(source: str | Path, destination: str | Path, dpi: int = 300) -> str` - No public docstring in the audited version.
- **function**, line 189: `render_cdxml(source: str | Path, destination: str | Path, *, dpi: int = 300, timeout_seconds: int = 30) -> str` - No public docstring in the audited version.

## `mcp_runtime.office_objects`

- **function**, line 24: `com_apartment()` - Initialize COM for the current worker thread and release it symmetrically.
- **function**, line 435: `load_replacement_manifest(manifest_path: str | Path, *, source_sha256: str, objects: list[dict[str, Any]]) -> list[dict[str, Any]]` - No public docstring in the audited version.
- **function**, line 535: `render_office_pdf(office_path: str | Path, output_path: str | Path) -> None` - No public docstring in the audited version.
- **function**, line 502: `rewrite_office_package(input_path: str | Path, output_path: str | Path, replacement_parts: dict[str, dict[str, bytes]]) -> None` - No public docstring in the audited version.
- **function**, line 259: `scan_office_objects(input_path: str | Path) -> tuple[str, list[dict[str, Any]]]` - No public docstring in the audited version.
- **function**, line 43: `sha256_file(path: str | Path) -> str` - No public docstring in the audited version.
- **function**, line 583: `validate_pdf(path: str | Path) -> None` - No public docstring in the audited version.
- **function**, line 383: `write_inspection(input_path: str | Path, output_dir: str | Path, *, render_previews: bool) -> dict[str, Any]` - No public docstring in the audited version.

## `mcp_runtime.official_overrides`

- **function**, line 234: `convert_cdx_cdxml(input_path: str, output_path: Optional[str] = None) -> dict` - Convert CDX/CDXML through a validated no-overwrite staging file.
- **function**, line 74: `draw_molecule(mol_json: dict, output_path: Optional[str] = None) -> dict` - Draw a molecule through a validated no-overwrite staging file.
- **function**, line 406: `embed_cdxml_in_office(cdxml_path: str, office_path: str, output_path: str | None = None) -> dict` - Create a new validated PPTX or DOCX and reject all existing targets.
- **function**, line 299: `extract_cdxml_from_office(file_path: str, output_dir: Optional[str] = None) -> dict` - Extract every object transactionally; publish nothing on partial failure.
- **function**, line 281: `format_lab_entry(entries_json: Union[list[dict], dict, str], output_path: Optional[str] = None) -> dict` - Format a lab entry and atomically publish verified text.
- **function**, line 263: `parse_analysis_file(pdf_path: str, output_path: Optional[str] = None) -> dict` - Parse an analysis file and atomically publish verified JSON.
- **function**, line 142: `parse_reaction(cdxml: Optional[str] = None, cdx: Optional[str] = None, csv: Optional[str] = None, rxn: Optional[str] = None, input_dir: Optional[str] = None, output_path: Optional[str] = None) -> dict` - Parse a reaction and atomically publish its JSON descriptor.
- **function**, line 219: `parse_scheme(cdxml_path: str, output_path: Optional[str] = None) -> dict` - Parse a scheme and atomically publish its JSON descriptor.
- **function**, line 108: `render_scheme(yaml_text: Optional[str] = None, compact_text: Optional[str] = None, json_path: Optional[str] = None, layout: str = 'auto', output_path: Optional[str] = None) -> str` - Render a scheme through a validated no-overwrite staging file.
- **function**, line 451: `render_to_png(cdxml_path: str, output_path: Optional[str] = None) -> dict` - Render CDXML to a validated PNG through a staging file.

## `mcp_runtime.process_control`

- **function**, line 232: `cleanup_automation_processes(before: dict[int, dict[str, Any]], after: dict[int, dict[str, Any]], *, stage_pid: int, terminate: bool = True, deadline: float | None = None) -> dict[str, Any]` - No public docstring in the audited version.
- **function**, line 104: `pid_is_running(pid: int) -> bool` - No public docstring in the audited version.
- **function**, line 155: `snapshot_automation_processes(timeout_seconds: float = 5) -> dict[int, dict[str, Any]]` - No public docstring in the audited version.
- **function**, line 83: `terminate_pid(pid: int, timeout_seconds: float = 10) -> bool` - No public docstring in the audited version.

## `mcp_runtime.remote_tools`

- **function**, line 10: `extract_structures_via_decimer_api(image_path: str, hand_drawn: bool = False, output_path: Optional[str] = None, timeout_seconds: int = 600, confirm_upload: bool = False, approved_sha256: Optional[str] = None, approved_origin: Optional[str] = None) -> dict[str, Any]` - Upload an image to DECIMER only when confirm_upload is explicitly true.

## `mcp_runtime.resource_lock`

- **function**, line 25: `native_resource_lock(resource_class: str | None, timeout_seconds: int) -> Iterator[None]` - Serialize ChemDraw COM calls across workers in the current user session.
- **class**, line 13: `ResourceBusyError` - Raised when an exclusive native resource cannot be acquired in time.

## `mcp_runtime.runtime_diagnostics`

- **function**, line 451: `diagnose_runtime(run_native_probe: bool = False, run_office_probe: bool = False, run_chemscript_probe: bool = False) -> dict[str, Any]` - Report local runtime capabilities; native probes are explicit and temporary.

## `mcp_runtime.runtime_discovery`

- **class**, line 27: `Discovery` - No public docstring in the audited version.
- **method**, line 31: `Discovery.to_dict() -> dict[str, str]` - No public docstring in the audited version.
- **function**, line 299: `find_chemdraw(explicit: str | None = None) -> Discovery` - Find ChemDraw.exe from explicit, environment, COM, then common paths.
- **function**, line 143: `find_python(explicit: str | None = None) -> Discovery` - Find and probe Python using explicit, environment, then implicit paths.
- **function**, line 184: `find_skill_root(explicit: str | None = None) -> Discovery` - No public docstring in the audited version.

## `mcp_runtime.structure_fidelity`

- **function**, line 219: `repair_and_validate_drawn_cdxml(smiles: str, path: str | Path, *, repair_stereo: bool = True) -> dict[str, object]` - Repair missing wedge bonds and verify CDXML against the source SMILES.
- **class**, line 9: `StructureFidelityError` - Generated CDXML does not preserve the requested molecular structure.

## `mcp_runtime.telemetry`

- **function**, line 37: `configure_tools(names: Iterable[str]) -> None` - Set the finite tool-label vocabulary used by exported metrics.
- **function**, line 105: `health_snapshot(*, tool_count: int) -> dict` - Return process health without input, output, filename, or molecule data.
- **function**, line 99: `native_active_finished() -> None` - No public docstring in the audited version.
- **function**, line 93: `native_active_started() -> None` - No public docstring in the audited version.
- **function**, line 87: `native_wait_finished() -> None` - No public docstring in the audited version.
- **function**, line 81: `native_wait_started() -> None` - No public docstring in the audited version.
- **function**, line 135: `render_prometheus() -> str` - Render the current process metrics using the Prometheus text format.
- **function**, line 216: `reset_for_tests() -> None` - No public docstring in the audited version.
- **function**, line 55: `worker_finished(tool: str, *, duration_seconds: float, ok: bool, error_code: str | None) -> None` - No public docstring in the audited version.
- **function**, line 48: `worker_started(tool: str) -> None` - No public docstring in the audited version.

## `mcp_runtime.tool_registry`

- **function**, line 99: `build_registry(profile: str | None = None) -> dict[str, ToolSpec]` - No public docstring in the audited version.
- **class**, line 24: `ToolSpec` - No public docstring in the audited version.
