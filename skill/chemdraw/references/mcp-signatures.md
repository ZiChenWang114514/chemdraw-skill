# MCP Tool Reference

> Generated from the live community registry. Do not edit manually.

Distribution: `cdxml-toolkit-community 0.7.0a3`
Profile: `full (default)`
Tools: `59`

## Extended Tools

### `analyze_lcms_series(files: list[str], output_path: Optional[str] = None, rt_tolerance: float = 0.02, mz_tolerance: float = 0.5, trend_threshold: float = 0.2, ignore_instrument: bool = False) -> dict[str, typing.Any]`

Analyze a chronological series of standard LCMS PDF reports.

### `assemble_lab_book(input_dir: str, experiment: Optional[str] = None, tracking_json: Optional[str] = None, output_path: Optional[str] = None) -> dict[str, typing.Any]`

Assemble a deterministic lab-book entry from experiment files.

### `batch_compare_molecules(pairs: list[dict[str, typing.Any]], fingerprint: str = 'morgan', radius: int = 2, n_bits: int = 2048) -> dict[str, typing.Any]`

Compare up to 256 molecule pairs with one ChemScript bridge session.

### `batch_embed_cdxml_in_office(cdxml_paths: list[str], output_path: str, margin_pt: float = 0) -> dict[str, typing.Any]`

Create PPTX or DOCX containing editable ChemDraw OLE objects.

### `characterization_text(compounds: list[dict], options: dict | None = None, output_path: str | None = None) -> dict`

ACS-style characterization paragraph per compound, in the order of the ACS Style Guide.

Each record is a grounded structure (SMILES, molblock or CDXML/MOL/SDF file, optional label)
with any of: appearance (text), rf ({value, eluent}), mp (number, "112-114" or [low, high]),
optical_rotation ({value, c, solvent, temperature}), ir ({medium, values} or a list), nmr
({"1H": {frequency, solvent, text | peaks}, "13C": {...}, "19F": {...}}), and the HRMS fields
of hrms_line (adduct, adducts, found_mz; "hrms": false leaves HRMS out). NMR peaks are text
such as "7.40-7.30 (m, 5H), 5.11 (s, 2H)" or a list of numbers, strings and
{shift | range, mult, J, n}; the digits you give are printed unchanged and ranges get an en
dash. The paragraph reads: appearance; Rf; mp; [a]D; IR; 1H; 13C; other nuclei; HRMS.
Checks never change a value; they add warnings: the 1H integral against the hydrogens of the
formula, the 13C signal count against the symmetry-distinct carbons, a residual-solvent
signal in a 13C list, an unusual multiplicity code, a wide melting range, a rotation without
c or solvent, and an HRMS error over 5 ppm. Options are those of hrms_line (adducts, mode,
ionization, decimals, electron_mass). Output ends in .txt, .md or .json and is never
overwritten. At most 256 structures.

### `check_reaction_balance(reaction: str | dict, options: dict | None = None, output_path: str | None = None) -> dict`

Check that a reaction conserves atoms and charge, and optionally tabulate its stoichiometry.

reaction is a reaction SMILES string "reactants>agents>products" (structures separated by
'.'), a dict {"reactants": [...], "agents": [...], "products": [...]} of structure records
(smiles, molblock or file; optional label, coefficient, equiv, density_g_ml, concentration_m,
isolated_mg), or {"cdxml": path, "steps": [step ids]} to read the <step> elements of a drawn
scheme. Agents are listed but never counted. Elements are counted with implicit hydrogens;
isotope-labelled atoms are balanced as separate species, and the charge must balance too.
For an unbalanced reaction the result names the missing formula (for example H2O),
and, when exactly one set of whole-number coefficients balances it, suggests them.
Also reports mass balance and atom economy (options main_product, default the first product).
options scale_mmol (amount of the limiting reactant, option limiting = its index, default 0)
adds a stoichiometry table with equivalents, mmol, mass, volume and, for products with
isolated_mg, the percent yield. A failed balance is a finding about the species as drawn:
check the structures against their source before trusting the reaction. Generic atoms
(R groups) are rejected. output_path ends in .json and is never overwritten.

### `chemdraw_chemical_properties(molecules: list[dict], output_path: str | None = None) -> dict`

Formula, masses, elemental analysis, logP and molar refractivity as ChemDraw computes them.

Records are SMILES/CXSMILES, molblock or file records (CDXML/MOL/SDF), with an optional
label; a CDXML or SDF record with all_fragments=true reports every structure in the file.
Every value is read from ChemDraw's own chemical properties engine (ChemScript StructureData:
Formula, Weight, ExactMass, ElementalAnalysis, PartitionCoefficient and Refractivity);
log_p and molar_refractivity are ChemDraw's ClogP estimates, in its units. Nothing is computed
by RDKit or any other substitute: a property ChemDraw cannot give is null with the reason in
that row's errors, and without ChemScript (Windows) the call fails instead of falling back.
On macOS ChemDraw itself gives the formula, masses and elemental analysis; it has no
scripting access to ClogP or refractivity, so log_p and molar_refractivity are null there.
Use molecule_report for the deterministic RDKit sheet. Generic atoms (R groups, *) are refused.
output_path ends in .csv, .json or .md and is never overwritten. At most 256 structures.

### `chemdraw_com_call(program: list[dict[str, typing.Any]], allow_file_io: bool = False, allow_overwrite: bool = False, max_items: int = 100) -> dict[str, typing.Any]`

Run a declarative program over ChemDraw's COM automation objects (Windows, ChemDraw installed).

program is a list of steps; the root object is the alias "app" (ChemDraw.Application).
Each step has op get, set, call, iterate or release, an optional target alias (default
app), and for get/set/call the member; call takes args, set takes value, and as stores
the result under a new alias. Arguments and values are strings, numbers, booleans, null,
{"constant": "kCDFormatPNG"} (any constant of the ChemDraw type library) or
{"ref": alias}. iterate walks a collection (Count and Item, counted from 1) and reads the
listed members of each item: {"op": "iterate", "target": "atoms", "members": ["Charge"]}.
Every member is checked against the committed COM catalog before ChemDraw starts, with
the result types followed through the program (see the interface-com reference for the
members). Printing, the clipboard, menus, preference changes and Quit are blocked.
Opening, saving or exporting files needs allow_file_io; an existing file is never
replaced unless allow_overwrite is also true (Document.Save and Close with saveChanges
true need it too). Documents the program opens are closed without saving and ChemDraw
is quit afterwards if the tool started it. Object results are reported as their type;
max_items caps the items iterate reads.

### `chemdraw_inventory(layer: str | None = None, query: str | None = None, tier: str | None = None, kind: str | None = None, limit: int = 50) -> dict`

Look up ChemDraw's own interfaces and how far this Skill covers each one.

The catalog lists what ChemDraw 22.2 reports about itself: ChemScript SDK members
(layer chemscript), COM automation objects (com), CDXML elements (cdxml) and menu
commands with their command ids (menu). Every row has a tier: T1 a dedicated tool does
it (tool names it), T2 a generic tool reaches it with a recipe that was run and checked
(recipe, tool), T3 it is documented only (reason says why). Filter by layer, tier, kind
(for example method, property, element, command, enum) and query, a case-insensitive
text found in the row id or its documentation; limit caps the rows returned. The summary
counts every row per layer and tier whatever the filter. Nothing here talks to ChemDraw.

### `chemdraw_object(op: str, input_path: str, selector: str | None = None, tag: str | None = None, props: dict | None = None, children: list | None = None, text: str | None = None, output_path: str | None = None, allow_unknown: bool = False, dry_run: bool = False, verify: bool = True, limit: int = 200) -> dict`

List, read, change, add or delete any object in a CDXML file, without touching the input.

op is list, get, set, add or delete. selector picks elements: steps joined by ">" of
tag#id[Attr=value] (for example "fragment > n[Element=8]", "b#5", "*[id=6]"); the first step
matches anywhere, later steps match direct children. list without a selector counts the
elements by tag; with one it describes up to limit matches. get needs a selector and
returns the attributes and children count of each match. set changes the attributes in
props ({name: value}, null removes one) on every match; an attribute the ChemDraw catalog
does not list for that element is refused unless the element already carries it or
allow_unknown is true, and integer/number/list values are checked. add appends a new tag
to the one element that selector matches, with props, optional text and nested children
[{tag, props, text, children}]; an id is assigned when the element type has one. delete
removes the matched objects with their contents and refuses objects that other objects
still point at (a bond's atoms, a bracket's members). Every other element, attribute and
comment of the file is kept as read, in order, including ones this tool does not know.
Changes are written to a new CDXML (output_path, or a fresh name beside the input);
an existing file is never replaced. dry_run reports the changes and writes nothing.
verify (default true) re-reads what would be written and checks the element count, that
objects outside the edit are unchanged and that no duplicate id or dangling reference
appeared; a failed check writes nothing. The edit is structural: render the result
with ChemDraw before treating it as a final figure.

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

### `draw_figure(brief: dict | str, output_path: str | None = None, render: bool = False) -> dict`

Draw a reaction scheme from a brief and check it, in one call.

brief is an object (or its JSON text) the caller writes from the user's request:
species [{id, smiles or name, label?}], steps [{substrates [ids], products [ids],
above [lines], below [lines], yield, arrow solid|dashed|failed|reversible|resonance}],
optional max_width (points, default 504, the width of a double-column ACS page) and
title; kind defaults to "scheme" and style to "acs1996". The steps may form a linear
route, a convergent route (arms that merge) or one starting material with several
products, in any order; the report names the layout used, and steps that fit none of
these are refused. Only the conditions in the brief are drawn; a
step without any is reported, never filled in. Structures given as SMILES are used
as they are; names go through the curated reagent table and, when the network is
allowed, PubChem; a name that cannot be resolved stops the run. Each step is checked
for atom balance (a missing by-product is named, not drawn), the layout is measured
for overlaps, tiny text and width, and one automatic re-layout is tried if that
fails; the report says what changed and what still fails. The saved file is read back
and its structures compared with the brief. render=True also renders a PNG with
ChemDraw and returns its path; without ChemDraw the report says native: not_run. The
file is never written over an existing one: without output_path a fresh name is made
in the temp directory, and an existing output_path is refused.

kind "scope" draws a substrate-scope panel instead: species [{id, smiles or name,
label?, group?, values {field: text}}], optional fields [{key, label?, unit?}] (default:
the keys used in values), conditions, footnotes, title, width_mm and height_mm. The
structures are packed onto as many editable pages as needed, grouped in first-seen
order, each label and value bound to its structure; a missing value is drawn as a
dash and listed in the notes. output_path is then a new folder (page-001.cdxml, ...;
PNGs in png/ with render=True) and the report lists the pages.

kind "mechanism" draws the structures of a mechanism with the curved arrows the brief
lists: species [{id, smiles or name, label?}] and steps [{substrates, products, above?,
below?, arrow?, moves [{from, to, electrons?}]}] drawn in the order given. A move runs
from {species, atom} or {species, bond [i, j]} to the same kind of end, in species that
are substrates of the step; atoms are numbered from 0 in SMILES order (the report lists
them) and electrons is 2 (full head, default) or 1 (half head). Nothing is inferred: a
step without moves is refused, a two-electron arrow that starts on an atom without a lone
pair or charge is drawn and flagged, and the arrows are checked for passing through
another atom (one automatic re-layout). A step with one substrate and one product
continues the same row with the intermediate drawn once; any other step starts a new
row, with its substrates drawn again. show_atom_numbers=true prints the atom numbers on a
draft so the moves can be checked.

### `execute_chemscript_sdk(program: list[dict[str, typing.Any]], allow_file_io: bool = False, allow_overwrite: bool = False, allow_unsafe_interop: bool = False, max_items: int = 100) -> dict[str, typing.Any]`

Execute a declarative ChemScript SDK program in an isolated Python.NET process.

### `export_structures(source: str | list, options: dict | None = None, output_path: str | None = None) -> dict`

Export every structure in a file or list as SMILES, InChI, InChIKey, formula and mass.

source is a path to a CDXML, MOL, SDF or SMILES (.smi) file, or a list of structure records
(smiles, molblock or file; optional label). A CDXML file contributes each top-level fragment
in document order with its CDXML fragment id; SDF titles and SMILES-file names become
labels. Binary CDX needs convert_cdx_cdxml first, and Office files need
extract_cdxml_from_office. Structures with generic atoms (R groups) are listed with their
SMILES but without InChI, and the result says so. option include_molblock adds a MOL block per
structure. output_path ends in .csv, .json, .smi, .sdf or .md and is never overwritten.
At most 2000 structures. Identity comes from the structure as stored; nothing is recognised or edited.

### `fill_office_template(template_path: str, manifest_path: str, output_path: Optional[str] = None) -> dict[str, typing.Any]`

Fill PPTX/DOCX text and editable ChemDraw placeholders from a manifest.

### `get_toolkit_capabilities(detail: str = 'full') -> dict[str, typing.Any]`

Return runtime identity and diagnostics; detail='summary' omits tool signatures.

### `hrms_line(molecules: list[dict], options: dict | None = None, output_path: str | None = None) -> dict`

HRMS characterization lines: "HRMS (ESI) m/z calcd for C9H10O2Na [M+Na]+ 173.0573, found 173.0570".

Each record is a grounded structure (SMILES, molblock or CDXML/MOL/SDF file, optional label).
The ion formula and calculated m/z come from the monoisotopic mass of the structure plus the
atoms the adduct adds or removes, with the electron mass included (options.electron_mass=false
ignores it, as some calculators do). A record may carry adduct or adducts (default [M+H]+, or
[M-H]- with options.mode "negative", or the molecular ion for ionization "EI"; a charged
structure is its own ion) and found_mz: a number for its first adduct or {adduct: number}. A
measured value adds ", found ..." and the error in ppm; more than 5 ppm is flagged. Options:
adducts, mode (positive or negative), ionization (ESI, APCI, EI, ESI-TOF and similar labels),
decimals (default 4), electron_mass. Supported adducts: [M+H]+, [M+Na]+, [M+K]+, [M+NH4]+,
[M+Li]+, [M+2H]2+, [M+H-H2O]+, [M-H]-, [M-2H]2-, [M+Cl]-, [M+Br]-, [M+HCOO]-,
[M+CH3COO]- and the EI molecular ion M+. . Output ends in .txt, .md, .csv or .json and is
never overwritten. At most 256 structures. The values are calculated, never measured.

### `inspect_chemdraw_objects_in_office(input_path: str, output_dir: Optional[str] = None, render_previews: bool = True) -> dict[str, typing.Any]`

Inventory editable ChemDraw objects and extract numbered CDXML previews.

### `inspect_chemscript_sdk(query: Optional[str] = None, type_name: Optional[str] = None, include_infrastructure: bool = False, offset: int = 0, limit: int = 100, output_path: Optional[str] = None) -> dict[str, typing.Any]`

Catalog every public ChemScript type/member, with filtering or a complete JSON export.

### `map_reaction_atoms(reaction: str | dict | list, options: dict | None = None, output_path: str | None = None) -> dict`

Map each product atom to the reactant atom it comes from (atom-to-atom mapping).

reaction is a reaction SMILES "reactants>agents>products", {"reactants": [...], "products": [...]}
of structure records, or {"cdxml": path, "steps": [step id]} (one reaction step). A list of
these (at most 100, each optionally {"label": "3a", "reaction": ...}; a drawing with several
steps gives one entry per step) maps them all in one pass: a learned mapper loads its model on
every call, so this takes about as long as one reaction. The answer then holds "reactions", one
entry per reaction with the fields below (or ok false and an error), and output_path ends in
.json or .smi (one mapped reaction per line). Hydrogens are
not mapped. Methods (option method): "mcs" is built in and needs nothing installed; it pairs
atoms by repeated maximum-common-substructure matching, keeps the pairing with the fewest
unmapped product atoms and then the fewest bond changes, and lists product atoms with more
than one equally good source as ambiguous instead of deciding. "rxnmapper" and "localmapper"
are learned mappers that run locally and need the one-time download made by
`cdx.py install-mappers`; they decide every atom, and RXNMapper also returns a confidence
(LocalMapper a confident flag) that you should read before trusting the map. "auto" (default)
uses LocalMapper, then RXNMapper, then "mcs", and falls back with a warning if a mapper fails.
Option compare runs every installed method and adds a "comparison" with the product atoms they
disagree on. This is bookkeeping, not a mechanism: pericyclic reactions and rearrangements can
be mapped differently from the textbook arrows. The result holds the mapped reaction SMILES,
a per-atom table, the bond changes (formed, broken, order changed), reactant atoms with no
product counterpart (leaving groups), product atoms without a source (status "incomplete"),
and, for "mcs", product atoms that could come from more than one reactant atom (status
"ambiguous"; left unmapped, never decided silently). Other options: resolve_ambiguity
(default false, "mcs" only) accepts a fixed tie-break for them, with a warning; include_agents
(default false) also offers the agent structures as atom sources. Option template adds
"template": the reaction centre as a reaction SMARTS (the atoms whose bonds change, their
neighbours and the leaving atoms, written by element with maps renumbered from 1) and whether
it reproduces the drawn products. Option classify adds "reaction_class": the name of the
generic template (amide coupling, esterification, Suzuki-type coupling, aryl amination,
reductive amination, Boc deprotection, ...) that makes the drawn products from the drawn
structures, every template that fits, and null with a note when none does; it reads the
structures only, never the conditions. Option map_numbers_into_scheme (one drawn reaction,
{"cdxml": path}) is the path of a new .cdxml: a copy of the drawing with each map number
written beside its atom on both sides, never overwriting a file. output_path ends in .json,
.smi (the mapped reaction SMILES) or .svg (a picture) and is never overwritten. At most 120
heavy atoms per side.

### `markush_compile(spec_path: str, output_dir: str, layout_path: str | None = None, render: bool = True) -> dict`

Compile a spec into markush.cxsmiles, markush.mol (V3000), markush.cdxml and a native PNG.

``layout_path`` holds coordinates (for example from the image workflow) so the
drawing follows the source figure; without it RDKit coordinates are used.
``output_dir`` must not exist yet.

### `markush_detect(image_path: str, output_dir: str) -> dict`

Find text boxes, bonds and ring circles in a clean Markush drawing.

Writes graph.json (pixel geometry with T# text-box and v# bond-end ids),
marks.png (the ids drawn on the image) and labels.png (one enlarged row per
text box, for transcription).  No chemistry is guessed here.

### `markush_enumerate(spec_path: str, count: int = 5, seed: int = 0) -> dict`

Sample concrete members from the definition values of a spec (SMILES).

### `markush_validate(spec_path: str) -> dict`

Check a markush.json spec; every error says what to change.

### `merge_reaction_schemes(input_paths: list[str], output_path: Optional[str] = None, mode: str = 'auto', equiv_mode: str = 'default', reference_cdxml: Optional[str] = None, allow_adjacent: bool = True, render_preview: bool = True, force_sequential: bool = False) -> dict[str, typing.Any]`

Merge parallel, sequential, or unrelated CDXML reaction schemes.

A parallel merge (repeat runs of one reaction) draws the first input's
conditions and adds each run's mass and yield as run arrows; a warning names
any run whose own conditions are therefore not drawn.

### `molecule_report(molecules: list[dict], output_path: str | None = None) -> dict`

Property sheet for grounded molecules: formula, masses, MS adducts, drug-likeness.

Each record is a SMILES/CXSMILES, molblock or file (CDXML/MOL/SDF) record with an optional
label; a bare SMILES string also works. A CDXML or SDF record with all_fragments=true
contributes every structure in the file. Reports formula, average and monoisotopic mass,
InChI/InChIKey, ESI adduct m/z values (positive and negative mode, electron mass included),
the isotope pattern scaled to the tallest peak, Crippen logP, TPSA, H-bond donors and
acceptors, rotatable bonds, QED, stereocentre counts and Lipinski/Veber rule results.
Descriptors are computed by RDKit from the structure as given; logP and TPSA are
calculated estimates, not measurements, and generic atoms (R groups) are rejected.
output_path ends in .json, .csv or .md and is never overwritten. At most 256 structures.

### `parse_scifinder_rdf(input_path: str, resolve_cas: bool = False, output_path: Optional[str] = None, confirm_pubchem: bool = False) -> dict[str, typing.Any]`

Parse SciFinder RDF and optionally enrich CAS data over the network.

### `polish_reaction_scheme(input_path: str, output_path: Optional[str] = None, merge_conditions: bool = True, approach: str = 'chemdraw_mimic', align_mode: str = 'rdkit', eln_csv: Optional[str] = None, reference_cdxml: Optional[str] = None, render_preview: bool = True) -> dict[str, typing.Any]`

Run the audited deterministic polishing pipeline on a CDXML scheme.

### `publication_figure(operation: str, spec_path: str, output_dir: str) -> dict`

Create, update, or check editable substrate-scope and SAR figure projects.

operation is create, update, or check. spec_path is a local JSON file naming
the CSV/XLSX table, structure source, fields and style. Updates/checks name a
project_path and optionally edited_pages (zero-based page index to CDXML).
Output is a new directory. Conflicts produce only a draft and conflict report,
never a new accepted project. Native PNG/SVG rendering defaults on, through
isolated locked workers; native failure is reported as pending validation.
This checks reader consistency and data binding, not experimental chemistry.

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

Render one or more CDXML files through native ChemDraw (COM or macOS).

### `replace_chemdraw_objects_in_office(input_path: str, replacements_manifest: str, output_path: Optional[str] = None, render_pdf_preview: bool = True, resize_frames: bool = False) -> dict[str, typing.Any]`

Replace selected ChemDraw OLE contents and previews without moving them.

With ``resize_frames``, each frame grows or shrinks with its drawing, as
Office does after an object is edited in ChemDraw; its top-left corner
stays in place. Otherwise frames keep their size.

### `route_summary(steps: list, options: dict | None = None, output_path: str | None = None) -> dict`

Overall yield and cumulative process mass intensity (PMI) of a synthetic route.

steps are listed in the order they are run; the last one makes the final product. A step is a
reaction as in si_materials_tables (a reaction SMILES, {"reactants": ..., "products": ...}
records, {"cdxml": path} or {"label": "2", "reaction": ..., "options": {...}}, whose amounts,
isolated mass or yield are computed as in si_materials_tables) or just numbers: {"label": "2",
"yield_percent": 85, "input_mg": 1500, "product_mg": 340, "used_mg": 300}. input_mg is
everything put into the step (reagents, catalysts, solvents), product_mg the isolated mass of
its product; a reaction takes both from that computation (a solvent with no density has no mass
and makes the PMI a lower bound), and either can be given on the step to override. A step
feeds the next one; "into": "<later step label>" makes the route convergent. used_mg is the
mass of a step's product that the step it feeds consumes: it is read from the structures when
both steps are reactions and the product is drawn as a reactant of the next, and is otherwise
required once the masses are given. Overall yield is the product of the step yields along the
longest linear sequence. Cumulative PMI is the mass put into all steps over the mass of the
final product, each step scaled so that it makes exactly what the next one uses (scale);
E-factor is PMI - 1. Work-up, extraction and purification solvents count only if you include
them in input_mg; a missing number is reported in warnings, never assumed. output_path ends in
.md, .csv or .json and is never overwritten. At most 100 steps.

### `scientific_workflow(operation: str, spec_path: str, output_path: str) -> dict[str, typing.Any]`

Draw or analyse a scientific figure from a JSON spec file: tlc, apparatus, mechanism, nmr or plot.

tlc, apparatus and mechanism write one editable .cdxml at output_path; nmr and plot write
a new directory (figures, the full data as CSV and a JSON analysis with the source file's
SHA-256). Relative file names inside the spec resolve against the spec's folder. The spec
formats are in the scientific workflows reference (examples for each operation ship with
the toolkit). Nothing is recognised or invented: peaks and integrals come from the supplied
processed spectrum, plots from the supplied columns. Output is written to a staging
location and published only when the workflow succeeds; an existing output_path is never
replaced.

### `segment_large_scheme(cdxml_path: str, output_path: Optional[str] = None, verbose: bool = False) -> dict[str, typing.Any]`

Segment a disconnected or multi-panel CDXML scheme into logical regions.

### `si_materials_tables(reactions: list, options: dict | None = None, output_path: str | None = None) -> dict`

Materials tables for a batch of reactions, ready for a Supporting Information file.

reactions is a list; each entry is a reaction SMILES "reactants>agents>products", a record
{"reactants": [...], "agents": [...], "products": [...]}, {"cdxml": path} (one reaction per
reaction step in the drawing) or {"label": "3a", "reaction": <any of these>, "options": {...}}.
A record may fix its own amount with one of equiv, mmol, mass_mg or volume_ml (solvents:
volume_ml) and may carry name, role (agents: solvent, reagent or catalyst), density_g_ml,
concentration_m (a stock solution), purity (percent) and, for a product, isolated_mg or
yield_percent; amounts nobody fixed get defaults (reactants by their coefficients, reagents
1 equiv, metal catalysts 0.05 equiv, a 0.2 M solvent). Per-reaction options override the
call's options. Options: scale_mmol (limiting reactant, default 1),
limiting, molarity (default 0.2 of the limiting reagent in the first solvent), hrms (default
true: add the calculated HRMS line of the first product), adduct (default [M+H]+) and
ionization (default ESI). map_atoms (default false) adds each reaction's bond changes from
atom mapping: all reactions go to the mapper in one call, so a learned mapper loads once;
map_method (default auto, see map_reaction_atoms) picks the method. A reaction that cannot be
mapped only loses that line, with a warning. reagent_safety (default false) adds, per
reaction, "safety": the GHS pictograms, H-statements, boiling and flash point of each reactant,
reagent and solvent from a built-in table of common reagents (a reminder, not a substitute for
the supplier SDS); a species that is not in the table is reported as not listed, never guessed.
Per reaction the result holds the amounts table, concentration, atom economy and reaction mass
efficiency, the first product's formula, isolated mass and yield, its HRMS line and a procedure
sentence; "assumed" lists the amounts nobody gave (shown in warnings). A reaction that cannot be
read is reported with its error and the others continue. output_path ends in .md, .csv, .html
or .json and is never overwritten. At most 100 reactions. Amounts and HRMS values are
calculated; nothing here is a measurement.

### `stoichiometry_grid(source: str, mode: str = 'analyze', output_path: str | None = None, options: dict | None = None) -> dict`

ChemDraw's own stoichiometry grid (Structure > Analyze Stoichiometry), drawn or read back.

mode "analyze" (Windows or macOS with desktop ChemDraw): source is a reaction SMILES
"reactants>agents>products" (agents are drawn above the arrow) or a .cdxml/.cdx file holding
a reaction. ChemDraw runs the command on a copy in a private window that it shows briefly
(the command is disabled in a hidden one), and the result is saved to output_path (.cdxml,
never overwritten; default "<name>-stoichiometry.cdxml" beside the file or
"reaction-stoichiometry.cdxml"). The source is never changed, and a file that already holds a
grid is refused. options.open (default false) then opens the result in the user's ChemDraw,
where typing a mass, volume or equivalents into the grid makes ChemDraw recompute the rest.
mode "read" (any platform, no ChemDraw): source is a saved .cdxml file; every grid in it is
read back, for example after someone typed amounts into it and saved.
Each grid lists one row per component with its role in the reaction step (reactant, agent or
product) and one cell per visible column under ChemDraw's own caption (Formula, MW,
Equivalents, Sample Mass, Reactant Moles, %Yield, ...): value is the stored number (masses in
g, amounts in mol, percentages as fractions) and text what the grid shows, with units;
cells someone typed are marked edited. Nothing is computed outside ChemDraw.

### `structure_to_name(molecules: list[dict], options: dict | None = None, output_path: str | None = None) -> dict`

Name grounded structures with ChemDraw's own structure-to-name engine and check each name.

Records are SMILES/CXSMILES, molblock or file records (CDXML/MOL/SDF), with an optional
label; a CDXML or SDF record with all_fragments=true names every structure in the file.
The name is the one ChemDraw's "Convert Structure to Name" produces (ChemScript on Windows,
ChemDraw for macOS on a Mac); it is not generated or guessed by this toolkit, and no
structure leaves the machine. With the default option verify=true each name is parsed
back to a structure by ChemDraw and compared with the input by InChIKey, component by
component: roundtrip.status is same, same_connectivity (stereo, charge or isotope layers
differ), different, unparseable or skipped. Report a name as confirmed only when the status
is same. Enhanced (and/or) stereo groups cannot be expressed in a name and are warned about.
One structure that ChemDraw cannot name is reported with its error and does not stop the others.
Needs ChemScript (Windows) or ChemDraw for macOS, like compare_molecules; there is no
offline fallback. output_path ends in .csv, .json or .md and is never overwritten.
At most 256 structures.

## Official Tools

### `convert_cdx_cdxml(input_path: str, output_path: Optional[str] = None) -> dict`

Convert bidirectionally between CDX (binary) and CDXML (XML) formats.

Direction is detected from the file extension:
- .cdx input  → .cdxml output
- .cdxml input → .cdx output

Uses available backends in order: ChemDraw (best fidelity; COM on Windows,
AppleScript on macOS) → pycdxml (pure Python, partial support) → OpenBabel.

On Windows ChemDraw COM drives a dedicated automation instance, so an open
ChemDraw window is neither reused nor required to be closed. On macOS the
toolkit drives a hidden ChemDraw for macOS instance.

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

Converts CDXML → CDX + EMF preview via ChemDraw, builds a CFB OLE
compound file, and injects it into a PPTX slide or DOCX paragraph as a
double-clickable, editable ChemDraw object.

Requires: ChemDraw COM (Windows, ChemDraw 16+, dedicated automation instance) or
ChemDraw for macOS (vector EMF preview from its SVG export), plus python-pptx or python-docx.

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
                     reaction_name= (a template name; see "reaction").
    "set_smiles"   — Use when you have edited a SMILES and want to verify
                     the change. Pass the original mol_json and new_smiles=.
                     The MCS diff will confirm exactly what was added/removed.
                     Do NOT generate SMILES from scratch — use resolve_name.
    "set_name"     — Set the display name. Pass new_name=.
    "reaction"     — Apply a named template. Pass reaction_name= and
                     optionally reagent={"smiles": ...} for binary reactions
                     (coupling, etc.). Template names come from the Python
                     API cdxml_toolkit.naming.mol_builder.list_reactions()
                     (not a tool); an operation that names a template, such
                     as "suzuki", is also matched to it.

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

Render a CDXML file to PNG using ChemDraw.

Uses ChemDraw's native rendering engine (COM automation on Windows,
AppleScript on macOS) at 300 DPI with a solid white background.
ChemDraw Professional 16+ must be installed and activated; a dedicated
automation instance is used, so an open ChemDraw window may stay open.

This tool uses ChemDraw only — no RDKit fallback. For a
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

Default image-recognition tool: use the remote DECIMER API.

For image-recognition tasks, pass confirm_upload=true for task images and
relevant crops without a separate upload-confirmation question. Respect
explicit local/offline or no-upload requests. The false value remains
available for an explicitly requested no-upload preflight.
Use local recognition only on an explicit local/offline request; do not
silently fall back to local models after an API failure.
