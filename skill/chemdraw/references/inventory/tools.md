# Tools Public Symbols

> Generated from cdxml-toolkit 0.7.0a1. Curated guidance: [../toolkit-tools.md](../toolkit-tools.md).

## `mcp_server._compat`

- **function**, line 45: `install_legacy_fastmcp_alias() -> None` - Provide the removed FastMCP import path when MCP SDK 2.x is installed.
- **function**, line 19: `sdk_major(version: str | None = None) -> int` - Return a supported MCP SDK major version or raise a clear error.
- **function**, line 14: `sdk_version() -> str` - Return the installed MCP Python SDK distribution version.
- **function**, line 34: `server_class() -> type[Any]` - Return the high-level server class for the installed SDK.

## `mcp_server.server`

- **function**, line 907: `convert_cdx_cdxml(input_path: str, output_path: Optional[str] = None) -> dict` - Convert bidirectionally between CDX (binary) and CDXML (XML) formats.
- **function**, line 359: `draw_molecule(mol_json: dict, output_path: Optional[str] = None) -> dict` - Render a single molecule to a standalone CDXML document.
- **function**, line 1257: `embed_cdxml_in_office(cdxml_path: str, office_path: str, output_path: Optional[str] = None) -> dict` - Embed a CDXML file as an editable ChemDraw OLE object in PPTX or DOCX.
- **function**, line 1168: `extract_cdxml_from_office(file_path: str, output_dir: Optional[str] = None) -> dict` - Extract embedded ChemDraw objects from a PPTX, DOCX, XLS, or XLSX file.
- **async function**, line 754: `extract_structures_from_image(image_path: str, detect_labels: bool = True) -> dict` - Extract chemical structures from an image using DECIMER.
- **function**, line 1039: `format_lab_entry(entries_json: Union[List[dict], dict, str], output_path: Optional[str] = None) -> dict` - Format a list of entry dicts into a structured lab book text entry.
- **function**, line 246: `modify_molecule(mol_json: dict, operation: str, add: Optional[List[dict]] = None, remove: Optional[List[str]] = None, new_smiles: Optional[str] = None, new_name: Optional[str] = None, reaction_name: Optional[str] = None, reagent: Optional[dict] = None, smarts: Optional[str] = None, description: Optional[str] = None) -> dict` - Analyze or transform a molecule with structural verification.
- **function**, line 970: `parse_analysis_file(pdf_path: str, output_path: Optional[str] = None) -> dict` - Parse an LCMS or NMR analysis PDF to extract peaks and data.
- **function**, line 577: `parse_reaction(cdxml: Optional[str] = None, cdx: Optional[str] = None, csv: Optional[str] = None, rxn: Optional[str] = None, input_dir: Optional[str] = None, output_path: Optional[str] = None) -> dict` - Parse reaction files into a semantic JSON descriptor.
- **function**, line 837: `parse_scheme(cdxml_path: str, output_path: Optional[str] = None) -> dict` - Parse a CDXML reaction scheme into a structured description.
- **function**, line 417: `render_scheme(yaml_text: Optional[str] = None, compact_text: Optional[str] = None, json_path: Optional[str] = None, layout: str = 'auto', output_path: Optional[str] = None) -> str` - Render an editable chemical reaction scheme with per-fragment chemical validation.
- **function**, line 1452: `render_to_png(cdxml_path: str, output_path: Optional[str] = None) -> dict` - Render a CDXML file to PNG using ChemDraw COM.
- **function**, line 200: `resolve_name(query: str, use_network: bool = True) -> dict` - Resolve any chemical identifier to a rich molecule descriptor.
- **function**, line 1373: `search_compound(smiles: str, experiment_dir: str, similarity_threshold: float = 0.85) -> dict` - Search for a compound across experiment JSON files by SMILES similarity.
- **function**, line 683: `summarize_reaction(json_path: str, species_fields: Optional[List[str]] = None, top_fields: Optional[List[str]] = None, eln_fields: Optional[List[str]] = None) -> dict` - Return a compact, context-efficient view of a reaction JSON file.
