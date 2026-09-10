# Workflow Router

Load one section matching the user's intent. Exact signatures live only in [mcp-signatures.md](mcp-signatures.md).

## Draw Or Modify A Molecule

1. Resolve a name with `resolve_name`, or accept user-supplied trusted SMILES.
2. Verify identity, formula, molecular weight, and ambiguity.
3. If no structural change is requested, do not call `modify_molecule(operation="analyze")` merely to authorize drawing; complex naming analysis may be expensive and is limited to 90 seconds.
4. For actual changes, call `modify_molecule` and inspect the MCS diff. For an explicit R/S assignment, `rdkit_workbench(operation="set_stereo")` provides a connectivity-preserving CIP diff; inspect it before drawing.
5. Call `draw_molecule` and require `metadata.chemistry_validation.status=preserved`. Compare source/roundtrip structure signatures and enhanced stereo groups, in addition to E/Z, isotopes and charges.
6. Call `render_to_png` for native compatibility and visual inspection. A successful PNG does not independently prove molecular identity.

## Compare Molecules Or Use ChemScript

1. Use `compare_molecules` for one pair or `batch_compare_molecules` for up to 256 pairs. Exact identity comes from ChemScript InChI when available; inspect both chirality-aware and connectivity-only Tanimoto values.
2. Use `inspect_chemscript_sdk` before any lower-level SDK work. Filter by type or member name; request a JSON output only for a complete audit.
3. Use `execute_chemscript_sdk` with a declarative sequence of SDK operations. Keep file access and replacement disabled unless the task explicitly requires them.
4. Native SWIG pointer/handle calls require a separate explicit option and run only in the isolated SDK process. Prefer the ordinary SDK classes for chemistry work.

## Create Or Edit A Reaction

1. Ground every drawn species.
2. Use `render_scheme` for a new reaction and inspect its per-fragment `chemistry_validation` receipts. For exact coordinates, curved arrows, grids or native-template replication, use [publication-figures.md](publication-figures.md).
3. Use `parse_scheme` or `parse_reaction` for an existing CDXML/CDX workflow.
4. Use `clean_scheme_layout`, `merge_reaction_schemes`, or `polish_reaction_scheme` for existing schemes. Explicit and auto-detected sequential plans are checked for linear chemical links; any `force_sequential=true` override requires manual review.
5. Render the resulting CDXML through `render_cdxml_files` and visually inspect all labels, wedges, arrows and plus signs. Cleanup/polish preserves molecular inventory but still needs visual acceptance.

## Recognize An Image

For multi-structure images or publication reconstruction, follow [image-visual-review.md](image-visual-review.md): agent segmentation → DECIMER → native redraw → actual side-by-side visual review → grounded correction → repeat → structured conditions and final composition. Follow an explicit user preference for DECIMER API over the local default below.

1. Prefer `extract_structures_from_image` when local DECIMER weights are available.
2. Use `extract_structures_via_decimer_api` only after explicit upload authorization and set `confirm_upload=true`.
3. Inspect every candidate and validation warning; never select by position alone.
4. For complete reaction screenshots, use `reaction_image_to_cdxml` only when it appears in the live MCP registry. It remains withheld when structure-role mapping cannot be verified.

## Convert Or Render

1. Convert CDX with `convert_cdx_cdxml`; edit CDXML, not binary CDX.
2. Render one file with `render_to_png` or a collection/PNG/SVG with `render_cdxml_files`. Batch rendering reuses one ChemDraw application session and stops on the first failed export.
3. Require native ChemDraw output for reaction and Office fidelity checks.

## Work With Office

1. Use `inspect_chemdraw_objects_in_office` when object identity, host location, geometry, or selective replacement matters. Use `extract_cdxml_from_office` for simple bulk extraction.
2. Modify and native-render the extracted CDXML. Keep the inspection manifest with its source SHA-256 and stable object IDs.
3. Use `replace_chemdraw_objects_in_office` to update selected objects in place. Replacement CDXML paths must remain relative to the replacement manifest; inspect the staged PDF preview when requested.
4. Create a new one-object file with `embed_cdxml_in_office`, create a new collection with `batch_embed_cdxml_in_office`, or preserve an existing template through `fill_office_template`. The single-object tool rejects an existing Office target because the upstream builder cannot preserve its content.
5. Verify the OOXML package opens, keeps its OLE relationships and geometry, and contains editable ChemDraw objects rather than flat images.

## Analyze Experiments

1. Use `discover_experiment_files` before composing a multi-file workflow.
2. Parse individual LCMS/NMR files with `parse_analysis_file`.
3. Use `analyze_lcms_series` only for at least two supported standard LCMS PDFs.
4. Parse ELN/reaction files with `parse_reaction`; parse SciFinder exports with `parse_scifinder_rdf`. CAS enrichment requires explicit PubChem confirmation and counts a resolution only when a valid field was actually added; inspect `metadata.cas_resolutions` for per-CAS outcomes.
5. Build a lab entry with `format_lab_entry` or a complete experiment entry with `assemble_lab_book`.

## Install Or Upgrade

Read [operations.md](operations.md). Run `scripts/check_prerequisites.ps1` with the requested `-Capabilities` before changing the Skill or MCP configuration. Identify the requested feature set: portable CDXML, native ChemDraw, ChemScript, Office, local DECIMER, or remote HTTP. Keep the main Python 64-bit; configure any legacy 32-bit ChemScript helper separately. Use [agent integration](agent-integration.md) for the current client, and change its configuration only when installation was requested. Restart the agent host and run the matching health-check mode.

## Diagnose Runtime

Read [operations.md](operations.md). Start with `diagnose_runtime()` and load only the native probes needed for the failing capability. Run the full health check before changing client configuration.
