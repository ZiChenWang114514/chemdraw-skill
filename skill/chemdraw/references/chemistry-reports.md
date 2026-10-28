# Chemistry reports

These tools answer the questions people ask after a structure is drawn: what are its numbers, how do I write its HRMS line, does the reaction balance, which atom becomes which, how much of everything do I weigh out (for one reaction or a whole SI), what is in this file, and what is it called. They read grounded structures (SMILES, MOL/SDF, CDXML fragments) and never recognize, guess or edit a structure. All compute with RDKit except the name tool, which asks ChemDraw. Exact signatures: [mcp-signatures.md](mcp-signatures.md).

| Question | Tool |
| --- | --- |
| Formula, masses, expected MS peaks, drug-likeness for one or many structures | `molecule_report` |
| Does this reaction conserve atoms and charge? What is missing? Amounts for a given scale? | `check_reaction_balance` |
| How much of each reagent, solvent and product for this reaction, in ChemDraw's own stoichiometry grid that I can type amounts into, and its numbers read back | `stoichiometry_grid`, `cdx.py calc` (needs desktop ChemDraw, except reading back) |
| An HRMS characterization sentence (`HRMS (ESI) m/z calcd for ... [M+Na]+ ...`) | `hrms_line` |
| A whole characterization paragraph (appearance, Rf, mp, rotation, IR, 1H/13C NMR, HRMS) in ACS order, with the peak counts checked | `characterization_text` |
| The experimental-section materials table and procedure sentence for a batch of reactions | `si_materials_tables` |
| Overall yield and cumulative PMI / E-factor of a multi-step route | `route_summary` |
| Which reactant atom does each product atom come from? What bonds change? | `map_reaction_atoms` |
| Give me every structure in this CDXML/SDF as SMILES, InChI or a table | `export_structures` |
| What is the name of this structure? | `structure_to_name` (needs ChemScript or ChemDraw for macOS) |
| What does ChemDraw give for formula, masses, elemental analysis, logP and molar refractivity? | `chemdraw_chemical_properties` (needs ChemScript on Windows; no RDKit substitute) |

All of them accept `output_path` (never overwritten) and return their data inline, so a small result needs no file. Run one as `cdx.py call TOOL --args args.json`.

## Property sheet and MS peaks

```json
{"molecules": [{"smiles": "CC(=O)Oc1ccccc1C(=O)O", "label": "aspirin"},
               {"file": "work/series.cdxml", "all_fragments": true}],
 "output_path": "work/properties.csv"}
```

- Per structure: formula, average and monoisotopic mass, InChI/InChIKey, ESI adduct m/z (`[M+H]+`, `[M+Na]+`, `[M+NH4]+`, `[M+K]+`, `[M+2H]2+`, `[M-H]-`, `[M+Cl]-`, `[M+HCOO]-` and others, electron mass included), the isotope pattern scaled to the tallest peak, Crippen logP, TPSA, hydrogen-bond donors and acceptors, rotatable bonds, QED, stereocentre counts, and Lipinski and Veber results.
- `markdown` is a ready-to-paste table; `output_path` ending in `.csv`, `.md` or `.json` writes that format.
- logP, TPSA and QED are calculated estimates. State them as such; never present them as measured. A charged structure reports its intact ion; a salt reports the whole record (the result warns).
- Compare an observed LCMS peak with the adduct list before concluding anything; one matching peak is not an identification.

## Reaction balance

```json
{"reaction": "CC(=O)O.OCC>>CC(=O)OCC",
 "options": {"scale_mmol": 2.0}}
```

`reaction` can be:

- a reaction string `reactants>agents>products`, structures separated by `.` (a salt written as one species needs the dict form);
- `{"reactants": [...], "agents": [...], "products": [...]}` with structure records that may carry `label`, `coefficient`, `equiv`, `density_g_ml`, `concentration_m` and `isolated_mg`;
- `{"cdxml": "scheme.cdxml", "steps": ["id"]}` to read the reaction steps of a drawn scheme (`render_scheme` writes them, and so do ChemDraw files that store reaction steps; a file with only loose structures or an arrow has none, and the tool says so).

What comes back: `balanced`, the per-side composition, charge, mass balance, atom economy (`main_product` picks the product, the first by default) and, when unbalanced, `missing_from_products` or `missing_from_reactants` as a formula with a common name (`H2O`, `HCl`, ...). When exactly one set of whole-number coefficients balances the reaction, `suggested_coefficients` gives it. Agents are listed but never counted. Isotope-labelled atoms balance as separate species.

With `scale_mmol` (the limiting reactant, `limiting` index, default the first) you also get a stoichiometry table: equivalents, mmol, mg, mL from a density or molarity, theoretical mass for each product and percent yield from `isolated_mg`.

An unbalanced result is a finding about the species as drawn. After an image reconstruction it often means a misread structure, a lost counterion or a missing by-product; check the structures against the source before treating the gap as chemistry. A balanced result confirms conservation only, not that the reaction works.

## ChemDraw stoichiometry grid

ChemDraw has its own reaction calculator: **Structure > Analyze Stoichiometry** puts an editable grid under a reaction, with formula, MW, equivalents, sample mass, molarity, density, volume and moles for each reactant and reagent, and expected mass, measured mass, purity and percent yield for each product. Typing a mass, volume or equivalents into a cell makes ChemDraw recompute the rest. `stoichiometry_grid` runs that command for you and reads the grid back; the numbers are ChemDraw's, nothing is recomputed outside it.

```json
{"source": "OCc1ccccc1.CC(=O)Cl>CCN(CC)CC.ClCCl>CC(=O)OCc1ccccc1",
 "mode": "analyze", "output_path": "work/acetylation-stoichiometry.cdxml", "options": {"open": true}}
```

- `mode: "analyze"` needs desktop ChemDraw (Windows, or ChemDraw for macOS). `source` is a reaction SMILES `reactants>agents>products` (the agents are drawn above the arrow) or a `.cdxml`/`.cdx` file holding a reaction step. ChemDraw runs the command on a copy in a private window that appears briefly, because the menu command is disabled in a hidden window; the user's own ChemDraw windows are left alone. The grid is saved to `output_path` (`.cdxml`, never overwritten; default `<name>-stoichiometry.cdxml` beside the file, or `reaction-stoichiometry.cdxml`). The source is never changed, and a file that already holds a grid is refused, because running the command again would add a second grid. `options.open: true` then opens the result in the user's ChemDraw for editing.
- `mode: "read"` works on any platform without ChemDraw: `source` is a saved `.cdxml` file, and every grid in it comes back. Use it after the user has typed amounts into the grid and saved.
- Each grid has one row per component with its `role` in the reaction step (`reactant`, `agent` or `product`; a solvent written as text below the arrow is a component too) and one cell per visible column under ChemDraw's own caption (`Formula`, `MW`, `Equivalents`, `Sample Mass`, `Reactant Moles`, `%Yield`, ...). `value` is the stored number (masses in g, amounts in mol, percentages as fractions) and `text` what the grid shows, with units; cells someone typed carry `"edited": true`.
- Only ChemDraw computes the grid. Amounts cannot be pre-filled from outside: values written into the file are not propagated to the other rows, so ask the user to type the amounts into ChemDraw, save, and then read the file back.

`cdx.py calc REACTION|file.cdxml [--output FILE] [--no-open]` does the same from the shell and opens the result in ChemDraw unless `--no-open` is given; `cdx.py calc --read FILE` reads a saved grid back. Both print JSON. For amounts calculated without ChemDraw (default equivalents, concentration, atom economy, PMI), use `si_materials_tables`.

## HRMS characterization lines

```json
{"molecules": [{"smiles": "CC(=O)OCc1ccccc1", "label": "3a", "adduct": "[M+Na]+", "found_mz": 173.0570}],
 "options": {"ionization": "ESI"}}
```

Per structure the result holds the ion formula, the calculated m/z and the line, for example `HRMS (ESI) m/z calcd for C9H10O2Na [M+Na]+ 173.0573, found 173.0570` (the ion formula is in Hill order with the attached ion last). The m/z is the monoisotopic mass plus the adduct atoms minus the electron mass; `options.electron_mass: false` ignores the electron, as some calculators do, so say which convention a journal expects. Defaults: `[M+H]+` (`[M-H]-` with `mode: "negative"`, the molecular ion for `ionization: "EI"`, a charged structure is its own ion). A measured `found_mz` adds the error in ppm; more than 5 ppm is flagged. `output_path` ends in `.txt`, `.md`, `.csv` or `.json`. The numbers are calculated: never write a "found" value the user did not give.

## Characterization paragraphs

```json
{"compounds": [{"label": "3a", "smiles": "CC(=O)OCc1ccccc1", "appearance": "colorless oil",
                "ir": {"medium": "neat", "values": [3034, 1738, 1229]},
                "nmr": {"1H": {"frequency": 400, "solvent": "CDCl3", "text": "7.40-7.30 (m, 5H), 5.11 (s, 2H), 2.10 (s, 3H)"},
                        "13C": {"frequency": 101, "solvent": "CDCl3", "peaks": ["171.0", "136.0", "128.6", "128.3", "128.2", "66.4", "21.1"]}},
                "adduct": "[M+Na]+", "found_mz": 173.0572}],
 "output_path": "work/characterization.txt"}
```

`characterization_text` writes one paragraph per compound in the order of the ACS Style Guide: appearance; Rf; mp; [α]D; IR; 1H NMR; 13C NMR; other nuclei (`19F`, `31P`, `11B` ...); HRMS (the `hrms_line` sentence; `"hrms": false` leaves it out). Every item is optional, and missing instrument details (frequency, solvent) are left out, never filled in.

- NMR peaks are text (`7.40-7.30 (m, 5H), 7.55 (dd, J = 8.0, 2.0 Hz, 1H)`), a list of numbers or strings, or `{shift | range, mult, J, n}` dicts. The digits you give are printed unchanged (`2.10` stays `2.10`), a range gets an en dash, and `J=7.1` becomes `J = 7.1 Hz`. A peak the parser cannot read is an error that names it.
- The tool reports mismatches as `warnings` and in each compound's `checks`; it never edits a value. Checked: the 1H integral against the hydrogens of the structure (exchangeable OH/NH protons are often missing); the 13C signal count against the symmetry-distinct carbons (quaternary carbons overlap, C-F or C-P coupling adds lines); a residual solvent signal in a 13C list (CDCl3 77.16, DMSO-d6 39.52, CD3OD 49.00, acetone-d6, C6D6, CD2Cl2, CD3CN); an unusual multiplicity code; a melting range wider than 5 °C; a rotation without concentration or solvent; an HRMS error over 5 ppm; a missing found mass.
- Read the warnings with the user before the paragraph goes into a manuscript. **A warning is a question about the data, not a correction: do not add, drop or round a peak to make a check pass.**
- `output_path` ends in `.txt` (one line per compound), `.md` or `.json`, and is never overwritten.

## Materials tables for a batch of reactions

```json
{"reactions": [{"label": "3a", "reaction": "OCc1ccccc1.CC(=O)Cl>CCN(CC)CC.ClCCl>CC(=O)OCc1ccccc1"},
               {"label": "3b", "reaction": {"cdxml": "work/scheme.cdxml"}}],
 "options": {"scale_mmol": 1.0, "molarity": 0.1},
 "output_path": "work/si_materials.html"}
```

Up to 100 reactions per call; each entry is a reaction string, a record, `{"cdxml": path}` (one table per reaction step, labelled `<file>, step N`) or `{"label", "reaction", "options"}`. A record may fix its own amount with one of `equiv`, `mmol`, `mass_mg` or `volume_ml`, plus optional `name`, `role`, `density_g_ml`, `concentration_m` (a stock solution) and `purity`; products take `isolated_mg` or `yield_percent`. Options: `scale_mmol` (limiting reactant, default 1), `limiting` (reactant index, default 0), `molarity` (of the limiting reagent in the first solvent, default 0.2), `hrms` (default true, the first product's HRMS line), `adduct` and `ionization`, and `map_atoms` (default false) with `map_method` (default `auto`) to add a "Bond changes" line from atom mapping; every reaction goes to the mapper in one call (see Atom mapping), and `reagent_safety` (default false) adds a "Safety reminders" block (GHS pictograms, H-statements, boiling and flash point per reactant, reagent and solvent, with the species not in the table listed as not listed) and a `hazards` CSV column. The safety data come from an offline table of about fifty common solvents and reagents; **a species that is not in it is "not listed", never "safe"**, and the table is a reminder, not a substitute for the supplier's SDS. Common solvents and liquid reagents get a density from a built-in table; do not invent a molecular weight or a density for the others. Each table lists material, role, MW, equiv, mmol, mass and volume, the concentration, atom economy and reaction mass efficiency, the product's isolated mass and yield and its HRMS line, and a procedure sentence. A reaction that cannot be read is reported with its error while the rest continue. `output_path` ends in `.md`, `.csv` (long format, one row per material), `.html` (printable, no external loads) or `.json`. **Amounts the user did not give are assumed defaults, listed per reaction in `warnings`; say so.**

## Route summary: overall yield and cumulative PMI

```json
{"steps": [{"label": "1", "yield_percent": 80, "input_mg": 1000, "product_mg": 200, "used_mg": 100},
           {"label": "2", "yield_percent": 50, "input_mg": 500, "product_mg": 40}],
 "output_path": "work/route.md"}
```

Steps are listed in the order they are run; the last one makes the final product. A step feeds the next one unless `into` names a later step by label, which makes the route convergent. Up to 100 steps per call.

- **Overall yield** is the product of the step yields along the longest linear sequence (`longest_sequence`), as usual for a convergent route.
- **Cumulative PMI** is the mass put into every step over the mass of the final product. Each step is scaled to make exactly the amount of product the next step uses: `scale = scale_next x used_mg / product_mg`. `used_mg` is read from the next step's reaction by matching the structure of the intermediate, or given explicitly; the tool asks for it rather than assuming it. E-factor is PMI - 1.
- A step is `{label, yield_percent, input_mg, product_mg, used_mg, into}` or `{label, reaction, options}` where `reaction` is anything `si_materials_tables` accepts and the numbers come from the same computation. Put work-up and purification solvents into `input_mg` if they should count: only the solvents of the reaction itself are included.
- A missing yield or mass gives `null` for that figure plus a warning, never a guess. If a solvent has no known mass (no density) the PMI is flagged `lower_bound`. **Say so when quoting the number.**
- `output_path` ends in `.md`, `.csv` (one row per step), or `.json`, and is never overwritten.

## Atom mapping

```json
{"reaction": "CC(=O)O.OCC>>CC(=O)OCC", "options": {"method": "auto", "compare": false, "include_agents": false},
 "output_path": "work/mapping.svg"}
```

`map_reaction_atoms` pairs product heavy atoms with reactant atoms. Hydrogens are not mapped, and the result is bookkeeping, not a mechanism: pericyclic reactions and rearrangements can be mapped differently from the textbook arrows. Three `method` values:

- `mcs` (built in, nothing to install): repeated maximum-common-substructure matching (rings stay rings unless nothing else is left), keeping the pairing with the fewest unmapped product atoms, then the fewest bond changes. It lists atoms with several equally good sources instead of guessing.
- `localmapper` and `rxnmapper` (optional learned mappers, run locally, nothing is uploaded): LocalMapper is trained on human-corrected reaction-centre labels; RXNMapper reads atom pairing from a transformer's attention. Both decide every atom. RXNMapper returns a `confidence` (a warning is added below 0.8; it is often low for cross-couplings and olefinations) and LocalMapper a `confident` flag: read them before trusting the map.
- `auto` (default): LocalMapper, then RXNMapper, then `mcs`; a mapper that fails falls back with a warning. `available_methods` in the result lists what is installed. Naming an uninstalled mapper is an error that points to the install command.

Install the learned mappers once with `cdx.py install-mappers` (or `rxnmapper` / `localmapper` alone; `--dry-run` shows the plan, `--status` what is installed), or with `scripts/install.py --runtime --mapping --apply`. Each gets its own environment beside the runtime, so their pinned PyTorch stacks never disturb it: several hundred MB each, and LocalMapper needs Python 3.10 to 3.12 (a suitable interpreter is found, or fetched through `uv` when present). `compare: true` runs every installed method and adds a `comparison` with the product atoms they disagree on; where the methods differ, show the user both and let them decide.

Measured on a laptop CPU (a 43-atom peptide coupling and larger): `mcs` takes under 0.3 s up to 94 product atoms, including symmetric chains and a ring with several equivalent sources. Each learned-mapper call starts its own process and loads its model, which costs 10 to 35 s (the first RXNMapper call after installing was the slowest). So give several reactions as one list: `"reaction": [...]` (at most 100 entries, each a reaction or `{"label", "reaction"}`; a drawing with several steps gives one entry per step) reaches each mapper in a single call and answers with `reactions`, one entry per reaction (`ok: false` and an `error` for one that fails, such as one over the size limit, while the rest continue). Four reactions took about 15 s as one list and 55 to 60 s as four separate calls. A list takes `.json` or `.smi` output (one mapped reaction per line), not `.svg`, and the options apply to the whole list.

- `mapped_reaction` is the reaction SMILES with atom map numbers; `map` is the per-atom table; `bond_changes` lists formed, broken and order-changed bonds; `unmapped_reactant_atoms` are the leaving groups.
- `status`: `complete`; `incomplete` when product atoms have no source in the reactants (a reagent may be missing, try `include_agents`, or the reaction is unbalanced); `ambiguous` (`mcs` only) when product atoms could come from several reactant atoms at the same cost. Ambiguous atoms are left unmapped and listed with their candidates; `resolve_ambiguity: true` accepts a fixed tie-break and warns. **Do not present a tie-break as the true mapping, and do not resolve an ambiguity silently.**
- `output_path` ends in `.json`, `.smi` (the mapped reaction SMILES) or `.svg` (a picture); at most 120 heavy atoms per side.

### What the mapping can be used for

Three options build on a finished mapping (they also work on each entry of a list):

- `template: true` adds `template`: the **reaction centre** as a reaction SMARTS. It keeps the atoms whose bonds or charge change, their neighbours and the unmapped atoms next to them (leaving groups, new atoms), writes the changing atoms by element and the unchanged neighbours as any atom, and numbers the maps from 1, so it fits other substituents. `reproduces` says whether running it on the drawn reactants gives the drawn products. With an `ambiguous` or `incomplete` mapping the differing atoms are unmapped, so the template may be missing (`smarts: null` with a note) or incomplete; resolve the ambiguity first.
- `classify: true` adds `reaction_class`: the first of 19 generic templates (amide formation or coupling, sulfonamide, ester formation, esterification, anhydride acylation, Suzuki-type coupling, aryl amination, N- and O-alkylation, reductive amination, carbonyl reduction, alcohol oxidation, ester hydrolysis, Boc deprotection, nitro reduction, C=C hydrogenation, azide-alkyne cycloaddition, Diels-Alder) that makes the drawn products from the drawn structures, with `matches` (every template that fits and the species it used). Reagents drawn as agents can take part. It reads structures only, never conditions, so "Aryl amination (SNAr or Pd/Cu-catalysed C-N coupling)" is a label for the bond change, not a claim about the catalyst. No fitting template gives `name: null` and "unclassified"; say so, do not name a reaction type yourself. Salt or tautomer forms of the products are not matched.
- `map_numbers_into_scheme: "work/scheme-mapped.cdxml"` (one drawn reaction, `{"cdxml": path}`) writes a copy of the drawing with each map number as a small label beside its atom on both sides, placed in the free space around atoms, bonds and text. The original is untouched and the file is never overwritten; `scheme_path` in the answer names it. Check the picture (`render_cdxml_files`) when an atom label such as H2N is crowded.

## Export every structure in a file

```json
{"source": "work/scheme.cdxml", "output_path": "work/structures.csv"}
```

`source` is a CDXML, MOL, SDF or `.smi` path, or a list of structure records. CDXML yields each top-level fragment in document order with its fragment id; SDF titles and `.smi` names become labels. Output formats by extension: `.csv`, `.json`, `.smi`, `.sdf` (with SMILES, InChIKey and formula as properties), `.md`. `options.include_molblock` adds a MOL block per structure.

Structures with R groups or other generic atoms are listed without an InChI and the result says so. Binary CDX needs `convert_cdx_cdxml`, Office files need `extract_cdxml_from_office`. Because the fragments come from the saved file, this also works as a read-back: export, then compare with the SMILES the drawing was built from.

## Structure to name

```json
{"molecules": [{"smiles": "O=C(O)[C@@H]1CCCN1", "label": "L-proline"}]}
```

The name is produced by ChemDraw's own "Convert Structure to Name" engine (ChemScript on Windows, ChemDraw for macOS on a Mac); this toolkit does not generate or guess names, and nothing is uploaded. There is no offline fallback: on a host without ChemScript or ChemDraw the tool fails with a message saying so, and the name must come from the user or a published source.

Each name is checked by default: ChemDraw parses it back into a structure and the result is compared with your input by InChIKey, component by component. Read `roundtrip.status`:

| Status | Meaning |
| --- | --- |
| `same` | The name describes exactly the input, stereochemistry and charges included. Safe to report as confirmed. |
| `same_connectivity` | Same skeleton, but a stereo, charge or isotope layer differs. Do not report; inspect the difference. |
| `different` | The name describes another structure. Do not use it. |
| `unparseable` | ChemDraw could not read its own name back. Report the name as unverified. |
| `skipped` | `verify` was false, there was no name, or no InChI could be made for the comparison. |

ChemDraw writes its own style of name (for example `isobutyl`, `phenethyl` and `tert-butyl` in place of the current IUPAC preferred forms); say so when a strict IUPAC name is required. Enhanced (and/or) stereo groups cannot be expressed in a name and produce a warning. One structure that ChemDraw cannot name is reported with its error and does not stop the others. `all_fragments` names every structure of a CDXML or SDF file; `output_path` writes `.csv`, `.json` or `.md`. On macOS each name drives the real ChemDraw application, so a long list takes minutes.

Limits: 256 structures for `molecule_report`, `check_reaction_balance` and `structure_to_name`, 2000 for `export_structures`, 1000 atoms per structure.
