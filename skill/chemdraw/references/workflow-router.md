# Workflow Router

Load one section matching the user's intent. Exact signatures live only in [mcp-signatures.md](mcp-signatures.md).

## Draw Or Modify A Molecule

For exam or lecture figures with abbreviations, Chinese notes or compound codes, use [ACS 1996 drawings](acs1996-drawings.md) instead.


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
2. Use `render_scheme` for a new reaction ([scheme drawing](scheme-drawing.md) has the compact syntax and the row-width setting) and check its per-fragment `chemistry_validation` status. For exact coordinates, curved arrows, grids or native-template replication, use [publication-figures.md](publication-figures.md).
3. Use `parse_scheme` or `parse_reaction` for an existing CDXML/CDX workflow.
4. Use `clean_scheme_layout`, `merge_reaction_schemes`, or `polish_reaction_scheme` for existing schemes. Explicit and auto-detected sequential plans are checked for linear chemical links; any `force_sequential=true` override requires manual review.
5. Render the resulting CDXML through `render_cdxml_files` and visually inspect all labels, wedges, arrows and plus signs. Cleanup/polish preserves molecular inventory but still needs visual acceptance.

## Recognize An Image

For multi-structure images or publication reconstruction, follow [image-visual-review.md](image-visual-review.md): agent segmentation → DECIMER API → native redraw → actual side-by-side visual review → grounded correction → repeat → structured conditions and final composition.

1. Default to the DECIMER API (`cdx.py decimer CROP.png`), including when local weights are installed, following the upload rule in SKILL.md.
2. Use `extract_structures_from_image` only when the user explicitly requests local or offline recognition. Do not install local models or silently switch to them after an API failure; follow the bounded retry guidance in [decimer-api.md](decimer-api.md).
3. Inspect every candidate and validation warning; never select by position alone.
4. For a complete reaction screenshot, crop and recognize each species as above, then rebuild the reaction with `render_scheme`. No tool assigns reactant, reagent and product roles from an image, so read them from the arrow layout yourself and state any role you could not decide.

## Convert Or Render

1. Convert CDX with `convert_cdx_cdxml`; edit CDXML, not binary CDX.
2. Render one file with `render_to_png` or a collection/PNG/SVG with `render_cdxml_files`. Batch rendering reuses one ChemDraw application session and stops on the first failed export.
3. Require native ChemDraw output for reaction and Office fidelity checks.

## Work With Office

1. Use `inspect_chemdraw_objects_in_office` when object identity, host location, geometry, or selective replacement matters. Use `extract_cdxml_from_office` for simple bulk extraction.
2. Modify and native-render the extracted CDXML. Keep the inspection manifest; replacements refer to its object IDs.
3. Use `replace_chemdraw_objects_in_office` to update selected objects in place. Replacement CDXML paths must remain relative to the replacement manifest; inspect the staged PDF preview when requested. Each object keeps its frame, so act on any warning that a replacement will be distorted. Pass `resize_frames=True` to size each replaced object's frame to its new drawing instead. To let the user edit one object by hand in ChemDraw (Office for macOS has no double-click editing), use `cdx.py office-edit DOCUMENT --object N`, then `cdx.py office-edit DOCUMENT --finish`.
4. Create a new one-object file with `embed_cdxml_in_office`, create a new collection with `batch_embed_cdxml_in_office`, or preserve an existing template through `fill_office_template`. The single-object tool rejects an existing Office target because the upstream builder cannot preserve its content.
5. Verify the OOXML package opens, keeps its OLE relationships and geometry, and contains editable ChemDraw objects rather than flat images.

## Report On Structures Or A Reaction

Details and argument examples: [chemistry reports](chemistry-reports.md).

1. `molecule_report` for formula, masses, expected ESI adduct m/z, isotope pattern, logP/TPSA and Lipinski/Veber checks of grounded structures, including every fragment of a CDXML file (`all_fragments`).
2. `check_reaction_balance` to test that a reaction string, record lists or the steps of a drawn scheme conserve atoms and charge. It names a missing by-product, suggests whole-number coefficients, reports atom economy, and with `scale_mmol` returns an equivalents/mass/volume/yield table. After an image reconstruction, an unbalanced reaction points to a misread species; resolve that before reporting.
3. `export_structures` to list every structure of a CDXML/MOL/SDF/SMILES file as SMILES, InChI and InChIKey (CSV, JSON, SMI, SDF or Markdown). Use it as an independent read-back of a saved drawing.
4. `reaction_calculator` for a reaction equivalents calculator: a standalone HTML page with editable equiv/mmol/mass/volume per species, solvent concentration, theoretical and isolated yield, atom economy and RME. For a page the user can draw in, run `cdx.py calc` in the background (add `--offline` to keep name lookups local) and give the user the printed address; the page can open ChemDraw and read the saved drawing back. Say which amounts are defaults (`assumed`). `scheme_output` (or the page's "Amounts into scheme" button) writes the amounts as text under the structures of a new CDXML copy.
5. `hrms_line` for `HRMS (ESI) m/z calcd for ... [M+Na]+ ...` characterization sentences (ppm error when a found value is given). `characterization_text` for a whole ACS paragraph (appearance, Rf, mp, [α]D, IR, 1H/13C/other NMR, HRMS) with the peak counts checked and mismatches reported, never corrected. `route_summary` for the overall yield and cumulative PMI (process mass intensity; E-factor = PMI - 1) of a multi-step route from per-step yields and masses (or calculator reactions), with a lower-bound warning when a solvent has no known mass. `si_materials_tables` for the materials table, HRMS line and procedure sentence of up to 100 reactions at once (Markdown, CSV, printable HTML or JSON); `map_atoms: true` adds each reaction's bond changes; `reagent_safety: true` adds GHS reminders per reagent from a built-in table (species not in it are reported as not listed, and the table never replaces the supplier SDS).
6. `map_reaction_atoms` for which reactant atom each product atom comes from and which bonds change. `method` is `auto` (installed LocalMapper or RXNMapper, else the built-in substructure method), `mcs`, `rxnmapper` or `localmapper`; the learned mappers come from `cdx.py install-mappers`, and `compare: true` shows where methods disagree. Pass several reactions as one list: a learned mapper loads once instead of once per reaction. `template` adds the reaction-centre SMARTS, `classify` names the reaction type from the structures (or says unclassified), `map_numbers_into_scheme` writes the map numbers into a copy of the drawing. Read RXNMapper's `confidence`, report `ambiguous` and `incomplete` as they are and never present a tie-break as the true mapping.
7. `structure_to_name` for a name of a drawn or supplied structure, from ChemDraw's own engine (ChemScript on Windows, ChemDraw for macOS). Report a name as confirmed only when `roundtrip.status` is `same`; without ChemScript or ChemDraw the tool cannot run and no name may be invented.

## Analyze Experiments

1. Use `discover_experiment_files` before composing a multi-file workflow.
2. Parse individual LCMS/NMR files with `parse_analysis_file`.
3. Use `analyze_lcms_series` only for at least two supported standard LCMS PDFs.
4. Parse ELN/reaction files with `parse_reaction`; parse SciFinder exports with `parse_scifinder_rdf`. CAS enrichment requires explicit PubChem confirmation and counts a resolution only when a valid field was actually added; inspect `metadata.cas_resolutions` for per-CAS outcomes.
5. Build a lab entry with `format_lab_entry` or a complete experiment entry with `assemble_lab_book`.

## Install Or Upgrade

Read [operations.md](operations.md). Run `cdx.py doctor` first; when it reports `"runtime": "missing"`, follow the install commands it prints. Identify the requested feature set: portable CDXML, native ChemDraw, ChemScript, Office, local DECIMER, or remote HTTP. Keep the main Python 64-bit; configure any legacy 32-bit ChemScript helper separately. Change the runtime only when installation was requested, then rerun `cdx.py doctor` with the matching probes.

## Diagnose Runtime

Read [operations.md](operations.md). Start with `cdx.py doctor` and add only the probe needed for the failing capability (`--native`, `--office`, `--chemscript`). When `runtime_matches_skill` is false, rebuild the runtime as `runtime_hint` says before trusting tool names or signatures.

## Substrate scope, SAR, or hand-edited publication updates

Read [data-driven figures](data-driven-figures.md). Use `publication_figure` to create, update, or check a project. Keep the original project directory and supply hand-edited CDXML separately; unresolved identity or concurrent-edit conflicts produce drafts only.
