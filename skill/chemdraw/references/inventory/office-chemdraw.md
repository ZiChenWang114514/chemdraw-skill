# Office Chemdraw Public Symbols

> Generated from cdxml-toolkit 0.8.0. Curated guidance: [../toolkit-office-chemdraw-interfaces.md](../toolkit-office-chemdraw-interfaces.md).

## `chemdraw._chemscript_server`

- **function**, line 193: `cmd_cleanup(args: dict) -> dict` - Clean up a structure file (normalize coordinates, bond lengths).
- **function**, line 269: `cmd_contains_substructure(args: dict) -> dict` - Check if target contains query substructure.
- **function**, line 143: `cmd_convert(args: dict) -> dict` - Convert a file from one format to another.
- **function**, line 312: `cmd_get_formula(args: dict) -> dict` - Get molecular formula for a structure.
- **function**, line 205: `cmd_get_info(args: dict) -> dict` - Get chemical information about a structure file or string.
- **function**, line 300: `cmd_get_name(args: dict) -> dict` - Get IUPAC name for a structure.
- **function**, line 380: `cmd_largest_common_substructure(args: dict) -> dict` - Find the largest common substructure between two molecules.
- **function**, line 330: `cmd_load_reaction(args: dict) -> dict` - Load a reaction and return component information.
- **function**, line 480: `cmd_mimetypes(args: dict) -> dict` - List all supported mimetypes.
- **function**, line 162: `cmd_name_to_cdxml(args: dict) -> dict` - Convert a chemical name to CDXML string.
- **function**, line 407: `cmd_overlay(args: dict) -> dict` - Overlay (2D-align) a molecule onto a reference molecule.
- **function**, line 486: `cmd_ping(args: dict) -> dict` - Health check.
- **function**, line 178: `cmd_smiles_to_cdxml(args: dict) -> dict` - Convert a SMILES string to CDXML.
- **function**, line 437: `cmd_substructure_align(args: dict) -> dict` - Align a query (small molecule) to its substructure match in a target.
- **function**, line 281: `cmd_substructure_search(args: dict) -> dict` - Perform atom-by-atom substructure search.
- **function**, line 320: `cmd_write_data(args: dict) -> dict` - Convert a structure to a specific format string.
- **function**, line 107: `resolve_mime(fmt: str) -> str` - Resolve a short alias or extension to a full mimetype.

## `chemdraw.cdx_converter`

- **function**, line 380: `batch_convert_files(input_paths: list, method: str = 'auto') -> dict` - Convert multiple CDX/CDXML files in a single COM session.
- **function**, line 368: `convert_cdx_to_cdxml(cdx_data: bytes, method: str = 'auto') -> str` - Convert raw CDX bytes to CDXML string.
- **function**, line 374: `convert_cdxml_to_cdx(cdxml_data: str, method: str = 'auto') -> bytes` - Convert CDXML string to raw CDX bytes.
- **function**, line 453: `convert_file(input_path: str, output_path: Optional[str] = None, method: str = 'auto') -> str` - Convert a file between CDX and CDXML. Returns output path.
- **function**, line 80: `sanitise_cdxml(cdxml: str) -> str` - Remove content that makes ChemDraw's strict XML parser reject the file.
- **function**, line 112: `sanitise_cdxml_file(path: str) -> None` - Sanitise a CDXML file in-place.

## `chemdraw.cdxml_to_image`

- **function**, line 107: `batch_render(cdxml_paths: list, png_dpi: int = 300) -> dict` - Render multiple CDXML files to PNG in a single COM session.
- **function**, line 56: `cdxml_to_image(cdxml_path: str, output_path: Optional[str] = None, png_dpi: int = 300) -> str` - Render a CDXML file to PNG or SVG using ChemDraw via COM automation.

## `chemdraw.cdxml_to_image_rdkit`

- **function**, line 157: `cdxml_to_image_rdkit(cdxml_path: str, output_path: Optional[str] = None, width: int = 600, height: int = 400) -> str` - Render a single-molecule CDXML to PNG or SVG using RDKit.
- **function**, line 56: `cdxml_to_rdkit_mol(path: str)` - Read a single-molecule CDXML into one RDKit Mol with its drawn 2D layout.

## `chemdraw.chemscript_bridge`

- **class**, line 314: `ChemScriptBridge` - High-level Python interface to ChemScript via a 32-bit subprocess server.
- **method**, line 528: `ChemScriptBridge.cleanup(input_path: str, output: str = None) -> str` - Clean up a structure file — normalize coordinates, bond lengths, etc.
- **method**, line 446: `ChemScriptBridge.close()` - Shut down the server.
- **method**, line 583: `ChemScriptBridge.contains_substructure(target: str, query: str) -> bool` - Check if target contains query as a substructure.
- **method**, line 472: `ChemScriptBridge.convert_file(input_path: str, output_path: str) -> dict` - Convert a chemistry file between formats.
- **method**, line 559: `ChemScriptBridge.get_formula(source: str) -> str` - Get molecular formula for a structure file or SMILES string.
- **method**, line 569: `ChemScriptBridge.get_info(source: str) -> dict` - Get full chemical info: name, formula, SMILES, InChI, atom/bond count.
- **method**, line 549: `ChemScriptBridge.get_name(source: str) -> str` - Get IUPAC name for a structure file or SMILES string.
- **method**, line 638: `ChemScriptBridge.largest_common_substructure(mol1: str, mol2: str) -> dict` - Find the largest common substructure between two molecules.
- **method**, line 617: `ChemScriptBridge.load_reaction(source: str, include_cdxml: bool = False) -> dict` - Load a reaction file and return component information.
- **method**, line 809: `ChemScriptBridge.mimetypes() -> List[str]` - List all supported mimetypes.
- **method**, line 488: `ChemScriptBridge.name_to_cdxml(name: str, output: str = None) -> str` - Convert a chemical name to CDXML string.
- **method**, line 659: `ChemScriptBridge.overlay(source: str, target: str, source_format: str = None, target_format: str = None) -> Tuple[str, bool]` - Overlay (2D-align) a molecule onto a reference molecule.
- **method**, line 508: `ChemScriptBridge.smiles_to_cdxml(smiles: str, output: str = None) -> str` - Convert a SMILES string to CDXML.
- **method**, line 687: `ChemScriptBridge.substructure_align(query: str, target: str, query_format: str = None, target_format: str = None) -> Optional[List]` - Align a small molecule (query) to its substructure match in a larger molecule (target).
- **method**, line 600: `ChemScriptBridge.substructure_search(target: str, query: str) -> dict` - Perform atom-by-atom substructure search.
- **method**, line 784: `ChemScriptBridge.write_data(source: str, target_format: str, source_format: str = None) -> str` - Convert a structure to a specific format string.
- **function**, line 1110: `shared_bridge()` - The one bridge the naming code shares in this process.

## `chemdraw.chemscript_mac`

- **class**, line 180: `MacChemScript` - Answer ChemScript server commands with ChemDraw for macOS, OPSIN and RDKit.
- **method**, line 202: `MacChemScript.call(cmd: str, args: dict) -> dict` - No public docstring in the audited version.
- **method**, line 199: `MacChemScript.close() -> None` - No public docstring in the audited version.
- **method**, line 677: `MacChemScript.cmd_atoms(args: dict) -> dict` - Atom names (as in substructure maps) and bonds of one structure.
- **method**, line 463: `MacChemScript.cmd_cleanup(args: dict) -> dict` - No public docstring in the audited version.
- **method**, line 534: `MacChemScript.cmd_contains_substructure(args: dict) -> dict` - No public docstring in the audited version.
- **method**, line 430: `MacChemScript.cmd_convert(args: dict) -> dict` - No public docstring in the audited version.
- **method**, line 510: `MacChemScript.cmd_get_formula(args: dict) -> dict` - No public docstring in the audited version.
- **method**, line 471: `MacChemScript.cmd_get_info(args: dict) -> dict` - No public docstring in the audited version.
- **method**, line 500: `MacChemScript.cmd_get_name(args: dict) -> dict` - No public docstring in the audited version.
- **method**, line 517: `MacChemScript.cmd_get_properties(args: dict) -> dict` - Formula, weight, exact mass and elemental analysis from one ChemDraw reading.
- **method**, line 614: `MacChemScript.cmd_largest_common_substructure(args: dict) -> dict` - No public docstring in the audited version.
- **method**, line 583: `MacChemScript.cmd_load_reaction(args: dict) -> dict` - No public docstring in the audited version.
- **method**, line 692: `MacChemScript.cmd_mimetypes(args: dict) -> dict` - No public docstring in the audited version.
- **method**, line 445: `MacChemScript.cmd_name_to_cdxml(args: dict) -> dict` - No public docstring in the audited version.
- **method**, line 637: `MacChemScript.cmd_overlay(args: dict) -> dict` - No public docstring in the audited version.
- **method**, line 427: `MacChemScript.cmd_ping(args: dict) -> dict` - No public docstring in the audited version.
- **method**, line 454: `MacChemScript.cmd_smiles_to_cdxml(args: dict) -> dict` - No public docstring in the audited version.
- **method**, line 662: `MacChemScript.cmd_substructure_align(args: dict) -> dict` - No public docstring in the audited version.
- **method**, line 538: `MacChemScript.cmd_substructure_search(args: dict) -> dict` - No public docstring in the audited version.
- **method**, line 546: `MacChemScript.cmd_write_data(args: dict) -> dict` - No public docstring in the audited version.
- **function**, line 86: `opsin_name_to_smiles(name: str) -> Optional[str]` - Resolve a chemical name offline with OPSIN, or return None.
- **function**, line 157: `rdkit_to_cdxml(mol) -> str` - CDXML for an RDKit molecule, keeping its coordinates and atom order.
- **function**, line 73: `resolve_mime(fmt: str) -> str` - No public docstring in the audited version.
- **function**, line 699: `shared() -> MacChemScript` - The process's MacChemScript, so every ChemScriptBridge drives one ChemDraw.

## `chemdraw.mac_automation`

- **function**, line 322: `application_info(bundle: Path) -> dict` - No public docstring in the audited version.
- **function**, line 648: `application_pid(bundle_id: str) -> Optional[int]` - Process id of the running application, read without Apple events.
- **function**, line 342: `bundle_identifier(bundle: Optional[Path] = None) -> str` - No public docstring in the audited version.
- **function**, line 335: `checked_bundle_id(bundle_id: object) -> str` - ``bundle_id`` if it is a well-formed bundle identifier; MacAutomationError otherwise.
- **function**, line 1089: `convert_file(source: str | Path, destination: str | Path, *, timeout_seconds: int = 60) -> str` - Convert one file with ChemDraw for macOS (format from the destination extension).
- **function**, line 282: `find_application() -> Optional[Path]` - Return the ChemDraw ``.app`` bundle, honouring ``CHEMDRAW_EXE``.
- **function**, line 313: `find_executable() -> Optional[Path]` - No public docstring in the audited version.
- **function**, line 1095: `flatten_png(path: str | Path, dpi: int = NATIVE_PNG_DPI) -> None` - Composite a transparent native PNG onto white and apply the requested DPI.
- **function**, line 380: `installed_font_families() -> frozenset` - Font family names installed on this Mac, read through CoreText.
- **function**, line 263: `is_macos() -> bool` - No public docstring in the audited version.
- **function**, line 640: `is_running(bundle_id: str) -> bool` - No public docstring in the audited version.
- **function**, line 737: `launch_hidden(bundle_id: str, *, timeout_seconds: float = 60) -> Optional[int]` - Launch an application in the background and hidden; record and return its pid.
- **function**, line 719: `launched_instances() -> dict[int, dict]` - Recorded launches whose process is still alive (stale records are dropped).
- **class**, line 254: `MacAutomationError` - ChemDraw for macOS automation failure with a stable public error code.
- **class**, line 780: `MacChemDrawSession` - Launch ChemDraw once (hidden, in the background) and reuse it for exports.
- **method**, line 918: `MacChemDrawSession.analyze(source: str | Path) -> dict` - ChemDraw's own reading of every structure in ``source``.
- **method**, line 940: `MacChemDrawSession.apply_menu(source: str | Path, destination: str | Path, *commands: tuple[str, str], select_all: bool = True) -> str` - Run ChemDraw menu ``commands`` (``(menu, item)`` pairs) and save the result.
- **method**, line 964: `MacChemDrawSession.clean(source: str | Path, destination: str | Path, *, reaction: bool = False) -> str` - ChemDraw Structure > Clean Up Structure (or Clean Up Reaction).
- **method**, line 1021: `MacChemDrawSession.close() -> None` - No public docstring in the audited version.
- **method**, line 885: `MacChemDrawSession.export(source: str | Path, *destinations: str | Path) -> list[str]` - Open ``source`` and save it to every destination (format from extension).
- **method**, line 979: `MacChemDrawSession.name_to_structure(name: str, destination: str | Path) -> str` - ChemDraw Structure > Convert Name to Structure for one chemical name, as CDXML.
- **method**, line 856: `MacChemDrawSession.run_steps(source: str | Path, steps: Iterable[str], *, timeout_seconds: Optional[float] = None, protect_captions: bool = False) -> list[str]` - Open ``source`` and run ChemDraw steps on it (see ``_STEPS_SCRIPT``).
- **method**, line 936: `MacChemDrawSession.smiles(source: str | Path) -> str` - Return ChemDraw's own SMILES for every structure in ``source``.
- **method**, line 799: `MacChemDrawSession.start() -> None` - No public docstring in the audited version.
- **method**, line 969: `MacChemDrawSession.structure_names(source: str | Path) -> list[str]` - Names from ChemDraw Structure > Convert Structure to Name, in document order.
- **function**, line 1066: `new_captions(source: str | Path, named: str | Path) -> list[str]` - Captions present in ``named`` but not in ``source`` (the names ChemDraw added).
- **function**, line 575: `protect_captions(path: str | Path) -> list[str]` - Mark free captions in a CDXML file as plain text; return their ids.
- **function**, line 274: `query_number(text: str) -> Optional[float]` - A weight or mass from the ``query`` step (AppleScript writes the locale's decimal comma).
- **function**, line 753: `reap_orphans() -> list[int]` - Stop applications the toolkit launched for a process that no longer exists.
- **function**, line 702: `register_launch(pid: int, bundle_id: str, *, owner_pid: Optional[int] = None) -> None` - No public docstring in the audited version.
- **function**, line 602: `release_captions(path: str | Path, ids: Iterable[str]) -> None` - Remove the marks ``protect_captions`` added from a saved CDXML file.
- **function**, line 621: `run_applescript(script: str, args: Iterable[str] = (), *, timeout_seconds: float = 60) -> str` - Run an AppleScript through ``osascript`` and return its stdout.
- **function**, line 770: `save_type_for(path: Path) -> str` - No public docstring in the audited version.
- **function**, line 426: `substitute_missing_fonts(path: str | Path, available: Optional[frozenset] = None) -> dict` - Rename fonts in a CDXML font table that are not installed on this Mac.
- **function**, line 663: `terminate_process(pid: Optional[int], grace_seconds: float = 5) -> None` - SIGTERM ``pid``, then SIGKILL it if it is still alive after the grace period.
- **function**, line 711: `unregister_launch(pid: Optional[int]) -> None` - No public docstring in the audited version.

## `chemdraw.progid`

- **function**, line 121: `dispatch() -> Any` - Attach to a ChemDraw automation instance, starting the application if needed.
- **function**, line 127: `dispatch_ex() -> Any` - Start a dedicated ChemDraw automation instance for one operation.
- **function**, line 133: `get_active() -> Any` - Attach to the ChemDraw instance that is already running.
- **function**, line 89: `local_server_command() -> str | None` - Command line of the first registered ChemDraw automation server.
- **function**, line 83: `registered_progids(progids: Iterable[str] = PROGIDS) -> list[str]` - The subset of ``progids`` that HKCR actually registers.

## `chemdraw.stoichiometry_grid`

- **function**, line 316: `analyze(source: str, output_path: str | None = None, *, open_result: bool = False) -> dict` - Run ChemDraw's Analyze Stoichiometry on a reaction and read the grid it draws.
- **function**, line 298: `open_in_chemdraw(path: Path) -> bool` - Show a saved file in the user's ChemDraw.
- **function**, line 182: `reaction_components(reaction: str) -> list[list[str]]` - Reactant, agent and product records of a reaction SMILES "reactants>agents>products".
- **function**, line 190: `reaction_document(reaction: str, destination: Path) -> Path` - Draw a reaction SMILES "reactants>agents>products" as CDXML, agents above the arrow.
- **function**, line 116: `read_grid(path: str | Path) -> dict` - Every stoichiometry grid in a saved CDXML file, as ChemDraw wrote it.
- **class**, line 49: `StoichiometryGridError` - A failure with a stable public error code.

## `chemdraw.style_presets`

- **function**, line 189: `apply_style_preset(cdxml_text: str, name: str, *, rescale: bool = True) -> str` - Write a preset's settings and fonts onto a CDXML document.
- **function**, line 161: `list_style_presets() -> list[dict]` - All presets, default first, as plain dictionaries.
- **function**, line 166: `style_preset(name: str) -> dict` - One preset by slug, display name or style-sheet name (case-insensitive).
- **function**, line 230: `style_preset_as_manifest_style(name: str) -> dict` - A preset as the ``style`` dictionary of ``compose_chemical_figure``.
- **function**, line 171: `style_preset_bond_length(name: str) -> float` - No public docstring in the audited version.
- **function**, line 148: `style_preset_slug(name: str) -> str` - Slug of a preset named by slug, display name or style-sheet name (any case).

## `chemdraw.style_sheet`

- **function**, line 185: `apply_style_sheet(cdxml_text: str, style: dict, *, rescale: bool = True) -> str` - Write the settings from :func:`read_style_sheet` onto a CDXML document.
- **function**, line 142: `read_style_sheet(path: str | Path) -> dict` - Drawing settings of a ChemDraw style sheet (.cds) or CDX document.
- **class**, line 60: `StyleSheetError` - The file is not a ChemDraw style sheet this module can read.

## `office.doc_from_template`

- **function**, line 540: `create_test_template(output_dir = 'templates')` - Create a minimal 1-slide PPTX template with placeholder text boxes.
- **function**, line 60: `load_manifest(manifest_path)` - Load JSON manifest. Resolve CDXML paths relative to manifest directory.
- **function**, line 176: `pass1_docx(template_path, text_slots, temp_path)` - Replace text placeholders in DOCX template. Save to temp_path.
- **function**, line 156: `pass1_pptx(template_path, text_slots, temp_path)` - Replace text placeholders in PPTX template. Save to temp_path.
- **function**, line 463: `pass2_docx(input_path, output_path, cdxml_slots, ole_items)` - Replace CDXML placeholder paragraphs with OLE objects in DOCX.
- **function**, line 320: `pass2_pptx(input_path, output_path, cdxml_slots, ole_items)` - Replace CDXML placeholder text boxes with OLE objects in PPTX.
- **function**, line 97: `prepare_ole_items(cdxml_slots, margin_pt = 0.0)` - Convert unique CDXML files to OLE data via ChemDraw (COM or macOS).

## `office.emf_preview`

- **function**, line 52: `png_to_emf(path: str | Path) -> bytes` - Return EMF bytes that draw the PNG at ``path`` on a white background.

## `office.emf_vector`

- **function**, line 548: `svg_to_emf(svg: str | Path | bytes) -> bytes` - EMF bytes that draw a ChemDraw SVG export at its physical size.
- **class**, line 79: `UnsupportedSvg` - The SVG uses a feature this converter does not reproduce exactly.

## `office.mac_office`

- **function**, line 83: `application_path(suffix: str) -> Path | None` - The installed Word (.docx) or PowerPoint (.pptx) for macOS, if any.
- **function**, line 92: `export_pdf(source: str | Path, destination: str | Path, *, timeout_seconds: float = PDF_TIMEOUT_SECONDS) -> Path` - Export a .docx (Word) or .pptx (PowerPoint) to PDF with Office for macOS.
- **class**, line 77: `OfficeAutomationError` - No public docstring in the audited version.

## `office.ole_embedder`

- **function**, line 92: `batch_convert(cdxml_paths)` - Open ChemDraw once and convert all CDXML files to CDX + EMF.
- **function**, line 745: `build_docx(items, output_path)` - Create a DOCX with editable ChemDraw OLE objects, one per paragraph.
- **function**, line 348: `build_ole_compound_file(cdx_data)` - Build a CFB file matching the known-good layout from Office COM.
- **function**, line 540: `build_pptx(items, output_path)` - Create a PPTX with one editable ChemDraw OLE object per slide.
- **function**, line 302: `content_size_emu(item, margin_pt = 0.0, scale = 1.02)` - OLE display size for one batch_convert() result.
- **function**, line 214: `get_cdxml_content_size(cdxml_path, margin_pt = 0.0, scale = 1.02)` - Compute OLE display dimensions from CDXML content BoundingBox.

## `office.ole_extractor`

- **function**, line 96: `extract_cdx_from_ole(ole_data: bytes) -> Optional[bytes]` - Extract raw CDX bytes from an OLE compound document.
- **function**, line 327: `extract_from_office(input_path: str, output_dir: Optional[str] = None, output_format: str = 'cdxml', convert_method: str = 'auto') -> List[ExtractedObject]` - Extract all ChemDraw objects from an Office file.
- **class**, line 54: `ExtractedObject` - A single extracted ChemDraw object.
- **function**, line 63: `find_ole_entries(zip_path: str) -> List[str]` - List OLE embedding paths inside a PPTX/DOCX/XLSX ZIP.
- **function**, line 80: `is_chemdraw_ole(ole: olefile.OleFileIO) -> bool` - Check if an OLE container holds a ChemDraw object.
- **function**, line 369: `print_summary(results: List[ExtractedObject], input_path: str) -> None` - Print extraction summary to stdout.

## `office.safe_xml`

- **function**, line 48: `fromstring(data)` - No public docstring in the audited version.
- **function**, line 24: `open_package(path) -> zipfile.ZipFile` - Open a package for reading after checking what it would unpack to.
- **class**, line 20: `UnsafePackage` - The archive is not a plausible Office document and was not read.
