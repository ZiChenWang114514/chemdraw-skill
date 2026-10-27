# Workflow Router

Load one section matching the user's intent. Exact signatures live only in [mcp-signatures.md](mcp-signatures.md); `cdx.py sig TOOL` prints one. Run a tool named below as `python <skill>/scripts/cdx.py call TOOL --args ARGS.json` (a file holding the arguments as a JSON object; `--json '{...}'` also works in bash). `cdx.py render` and `cdx.py draw` are shortcuts for rendering and for `draw_figure`.

## Draw Or Modify A Molecule

For exam or lecture figures with abbreviations, Chinese notes or compound codes, use [ACS 1996 drawings](acs1996-drawings.md) instead.


1. Resolve a name with `resolve_name`, or accept user-supplied trusted SMILES.
2. Verify identity, formula, molecular weight, and ambiguity.
3. If no structural change is requested, do not call `modify_molecule(operation="analyze")` merely to authorize drawing; complex naming analysis may be expensive and is limited to 90 seconds.
4. For actual changes, call `modify_molecule` and inspect the MCS diff. For an explicit R/S assignment, `rdkit_workbench(operation="set_stereo")` provides a connectivity-preserving CIP diff; inspect it before drawing.
5. Call `draw_molecule` and require `metadata.chemistry_validation.status=preserved`. Compare source/roundtrip structure signatures and enhanced stereo groups, in addition to E/Z, isotopes and charges.
6. Run `cdx.py render FILE.cdxml` (the `render_to_png` tool) for native compatibility and visual inspection. A successful PNG does not independently prove molecular identity.

## Compare Molecules Or Use ChemScript

1. Use `compare_molecules` for one pair or `batch_compare_molecules` for up to 256 pairs. Exact identity comes from ChemScript InChI when available; inspect both chirality-aware and connectivity-only Tanimoto values.
2. Use `inspect_chemscript_sdk` before any lower-level SDK work. Filter by type or member name; request a JSON output only for a complete audit.
3. Use `execute_chemscript_sdk` with a declarative sequence of SDK operations. Keep file access and replacement disabled unless the task explicitly requires them.
4. Native SWIG pointer/handle calls require a separate explicit option and run only in the isolated SDK process. Prefer the ordinary SDK classes for chemistry work.

## Create Or Edit A Reaction

1. Ground every drawn species.
2. For a new reaction, route, substrate-scope panel or a mechanism with curved arrows, read [scheme drawing](scheme-drawing.md) and run `cdx.py draw brief.json out.cdxml --render` (`draw_figure`; `kind: mechanism` for curved arrows). `render_scheme` takes the compact syntax and the row-width setting; check its per-fragment `chemistry_validation` status. For exact coordinates, grids or native-template replication, use [publication-figures.md](publication-figures.md).
3. Use `parse_scheme` or `parse_reaction` for an existing CDXML/CDX workflow.
4. Use `clean_scheme_layout`, `merge_reaction_schemes`, or `polish_reaction_scheme` for existing schemes. Explicit and auto-detected sequential plans are checked for linear chemical links; any `force_sequential=true` override requires manual review.
5. Render the resulting CDXML with `cdx.py render` (`render_cdxml_files`) and visually inspect all labels, wedges, arrows and plus signs. Cleanup/polish preserves molecular inventory but still needs visual acceptance.

## Recognize An Image

For multi-structure images or publication reconstruction, follow [image-visual-review.md](image-visual-review.md): agent segmentation → DECIMER API → native redraw → actual side-by-side visual review → grounded correction → repeat → structured conditions and final composition.

1. Default to the DECIMER API (`cdx.py decimer CROP.png`), including when local weights are installed, following the upload rule in SKILL.md.
2. Use `extract_structures_from_image` only when the user explicitly requests local or offline recognition. Do not install local models or silently switch to them after an API failure; follow the bounded retry guidance in [decimer-api.md](decimer-api.md).
3. Inspect every candidate and validation warning; never select by position alone.
4. For a complete reaction screenshot, crop and recognize each species as above, then rebuild the reaction with `render_scheme`. No tool assigns reactant, reagent and product roles from an image, so read them from the arrow layout yourself and state any role you could not decide.

## Convert Or Render

1. Convert CDX with `convert_cdx_cdxml`; edit CDXML, not binary CDX.
2. Render with `cdx.py render A.cdxml [B.cdxml ...]` (PNG next to each file; `--out-dir` and `--replace` are described in [agent integration](agent-integration.md#command-reference)); use the `render_cdxml_files` tool for SVG or a collection. Batch rendering reuses one ChemDraw application session and stops on the first failed export.
3. Require native ChemDraw output for reaction and Office fidelity checks.

## Inspect Or Edit CDXML Objects

For any object other than the molecules and schemes the drawing tools produce (text, shapes, tables, bioshapes, plasmid maps, annotations, chemical properties), or to change one attribute of an existing file:

1. Find the element in [interface-cdxml-model.md](interface-cdxml-model.md) (or `chemdraw_inventory(layer="cdxml", query=...)`); the page lists the attributes seen in real ChemDraw documents.
2. `chemdraw_object(op="list", input_path=...)` counts elements by tag; add a `selector` such as `fragment > n[Element=8]` to describe matches, and `get` for full attributes.
3. `set`, `add` and `delete` write a new CDXML (never the input) and keep every element, attribute and comment they do not touch, in order. Use `dry_run` first on a large selector. An attribute the catalog does not list is refused unless `allow_unknown` is set; delete refuses an object that a bond, bracket or graphic still points at.
4. The result is a structural edit. ChemDraw draws an atom's saved label text as it is, so changing `Charge`, `Element` or `NumHydrogens` on a labelled atom does not change what is drawn (the result warns about it); edit the label's `s` text as well. Render the result with `render_to_png`, look at the image, and compare molecules with `compare_molecules` when atoms or bonds changed.

## Drive ChemDraw Through COM

For a ChemDraw object or measurement no dedicated tool covers (document or selection formula and masses, atom and bond properties, ChemDraw's own Clean Up), and only on Windows with ChemDraw installed (`chemdraw_com_call` does not exist on macOS):

1. Find the member in [interface-com.md](interface-com.md) (or `chemdraw_inventory(layer="com", query=...)`). Start from a T2 member's recipe in [recipes-chemdraw.md](recipes-chemdraw.md); a T3 member is reachable but untested, so say so in the answer.
2. `chemdraw_com_call(program=[...])` takes steps `get`, `set`, `call`, `iterate` and `release` on the root alias `app`; `as` names an object result so later steps can use it, and constants are written `{"constant": "kCDFormatPNG"}`. Every member is checked against the catalog before ChemDraw starts.
3. Opening or saving a file needs `allow_file_io`; replacing an existing file also needs `allow_overwrite`. Documents the program opens are closed unsaved and ChemDraw is quit afterwards if the tool started it. Printing, the clipboard, menu commands, preference changes and `Quit` are refused.
4. Values are ChemDraw's own, read from the whole document or collection the program names; check them against the molecule you expect. Render a saved result with `render_to_png` and look at it before reporting a change.

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
8. `chemdraw_chemical_properties` (Windows with ChemScript only) when the answer must be ChemDraw's own value (as the Chemical Properties window shows it): formula, average and exact mass, elemental analysis, ClogP logP and molar refractivity. A property ChemDraw cannot give comes back null with the reason in `errors`; do not fill it from `molecule_report` and call it ChemDraw's. NMR prediction and the other menu commands are not opened as tools (see [interface-menu.md](interface-menu.md)); say they were not run.

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
