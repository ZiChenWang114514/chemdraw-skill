# Office Chemdraw Public Symbols

> Generated from cdxml-toolkit 0.7.0a3. Curated guidance: [../toolkit-office-chemdraw-interfaces.md](../toolkit-office-chemdraw-interfaces.md).

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

- **function**, line 334: `batch_convert_files(input_paths: list, method: str = 'auto') -> dict` - Convert multiple CDX/CDXML files in a single COM session.
- **function**, line 322: `convert_cdx_to_cdxml(cdx_data: bytes, method: str = 'auto') -> str` - Convert raw CDX bytes to CDXML string.
- **function**, line 328: `convert_cdxml_to_cdx(cdxml_data: str, method: str = 'auto') -> bytes` - Convert CDXML string to raw CDX bytes.
- **function**, line 396: `convert_file(input_path: str, output_path: Optional[str] = None, method: str = 'auto') -> str` - Convert a file between CDX and CDXML. Returns output path.
- **function**, line 67: `sanitise_cdxml(cdxml: str) -> str` - Remove content that makes ChemDraw's strict XML parser reject the file.
- **function**, line 99: `sanitise_cdxml_file(path: str) -> None` - Sanitise a CDXML file in-place.

## `chemdraw.cdxml_to_image`

- **function**, line 109: `batch_render(cdxml_paths: list, png_dpi: int = 300) -> dict` - Render multiple CDXML files to PNG in a single COM session.
- **function**, line 48: `cdxml_to_image(cdxml_path: str, output_path: Optional[str] = None, png_dpi: int = 300) -> str` - Render a CDXML file to PNG or SVG using ChemDraw via COM automation.

## `chemdraw.cdxml_to_image_rdkit`

- **function**, line 225: `cdxml_to_image_rdkit(cdxml_path: str, output_path: Optional[str] = None, width: int = 600, height: int = 400) -> str` - Render a single-molecule CDXML to PNG or SVG using RDKit.

## `chemdraw.chemscript_bridge`

- **class**, line 291: `ChemScriptBridge` - High-level Python interface to ChemScript via a 32-bit subprocess server.
- **method**, line 444: `ChemScriptBridge.cleanup(input_path: str, output: str = None) -> str` - Clean up a structure file — normalize coordinates, bond lengths, etc.
- **method**, line 364: `ChemScriptBridge.close()` - Shut down the server.
- **method**, line 499: `ChemScriptBridge.contains_substructure(target: str, query: str) -> bool` - Check if target contains query as a substructure.
- **method**, line 388: `ChemScriptBridge.convert_file(input_path: str, output_path: str) -> dict` - Convert a chemistry file between formats.
- **method**, line 475: `ChemScriptBridge.get_formula(source: str) -> str` - Get molecular formula for a structure file or SMILES string.
- **method**, line 485: `ChemScriptBridge.get_info(source: str) -> dict` - Get full chemical info: name, formula, SMILES, InChI, atom/bond count.
- **method**, line 465: `ChemScriptBridge.get_name(source: str) -> str` - Get IUPAC name for a structure file or SMILES string.
- **method**, line 554: `ChemScriptBridge.largest_common_substructure(mol1: str, mol2: str) -> dict` - Find the largest common substructure between two molecules.
- **method**, line 533: `ChemScriptBridge.load_reaction(source: str, include_cdxml: bool = False) -> dict` - Load a reaction file and return component information.
- **method**, line 725: `ChemScriptBridge.mimetypes() -> List[str]` - List all supported mimetypes.
- **method**, line 404: `ChemScriptBridge.name_to_cdxml(name: str, output: str = None) -> str` - Convert a chemical name to CDXML string.
- **method**, line 575: `ChemScriptBridge.overlay(source: str, target: str, source_format: str = None, target_format: str = None) -> Tuple[str, bool]` - Overlay (2D-align) a molecule onto a reference molecule.
- **method**, line 424: `ChemScriptBridge.smiles_to_cdxml(smiles: str, output: str = None) -> str` - Convert a SMILES string to CDXML.
- **method**, line 603: `ChemScriptBridge.substructure_align(query: str, target: str, query_format: str = None, target_format: str = None) -> Optional[List]` - Align a small molecule (query) to its substructure match in a larger molecule (target).
- **method**, line 516: `ChemScriptBridge.substructure_search(target: str, query: str) -> dict` - Perform atom-by-atom substructure search.
- **method**, line 700: `ChemScriptBridge.write_data(source: str, target_format: str, source_format: str = None) -> str` - Convert a structure to a specific format string.

## `office.doc_from_template`

- **function**, line 535: `create_test_template(output_dir = 'templates')` - Create a minimal 1-slide PPTX template with placeholder text boxes.
- **function**, line 58: `load_manifest(manifest_path)` - Load JSON manifest. Resolve CDXML paths relative to manifest directory.
- **function**, line 174: `pass1_docx(template_path, text_slots, temp_path)` - Replace text placeholders in DOCX template. Save to temp_path.
- **function**, line 154: `pass1_pptx(template_path, text_slots, temp_path)` - Replace text placeholders in PPTX template. Save to temp_path.
- **function**, line 458: `pass2_docx(input_path, output_path, cdxml_slots, ole_items)` - Replace CDXML placeholder paragraphs with OLE objects in DOCX.
- **function**, line 315: `pass2_pptx(input_path, output_path, cdxml_slots, ole_items)` - Replace CDXML placeholder text boxes with OLE objects in PPTX.
- **function**, line 95: `prepare_ole_items(cdxml_slots, margin_pt = 0.0)` - Convert unique CDXML files to OLE data via ChemDraw COM.

## `office.ole_embedder`

- **function**, line 87: `batch_convert(cdxml_paths)` - Open ChemDraw once and convert all CDXML files to CDX + EMF.
- **function**, line 638: `build_docx(items, output_path)` - Create a DOCX with editable ChemDraw OLE objects, one per paragraph.
- **function**, line 300: `build_ole_compound_file(cdx_data)` - Build a CFB file matching the known-good layout from Office COM.
- **function**, line 439: `build_pptx(items, output_path)` - Create a PPTX with one editable ChemDraw OLE object per slide.
- **function**, line 254: `content_size_emu(item, margin_pt = 0.0, scale = 1.02)` - OLE display size for one batch_convert() result.
- **function**, line 166: `get_cdxml_content_size(cdxml_path, margin_pt = 0.0, scale = 1.02)` - Compute OLE display dimensions from CDXML content BoundingBox.

## `office.ole_extractor`

- **function**, line 93: `extract_cdx_from_ole(ole_data: bytes) -> Optional[bytes]` - Extract raw CDX bytes from an OLE compound document.
- **function**, line 262: `extract_from_office(input_path: str, output_dir: Optional[str] = None, output_format: str = 'cdxml', convert_method: str = 'auto') -> List[ExtractedObject]` - Extract all ChemDraw objects from an Office file.
- **class**, line 51: `ExtractedObject` - A single extracted ChemDraw object.
- **function**, line 60: `find_ole_entries(zip_path: str) -> List[str]` - List OLE embedding paths inside a PPTX/DOCX/XLSX ZIP.
- **function**, line 77: `is_chemdraw_ole(ole: olefile.OleFileIO) -> bool` - Check if an OLE container holds a ChemDraw object.
- **function**, line 304: `print_summary(results: List[ExtractedObject], input_path: str) -> None` - Print extraction summary to stdout.
