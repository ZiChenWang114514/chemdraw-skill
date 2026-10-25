# Chemistry reports

These tools answer the questions people ask after a structure is drawn: what are its numbers, how do I write its HRMS line, does the reaction balance, which atom becomes which, how much of everything do I weigh out (for one reaction or a whole SI), what is in this file, and what is it called. They read grounded structures (SMILES, MOL/SDF, CDXML fragments) and never recognize, guess or edit a structure. All compute with RDKit except the name tool, which asks ChemDraw. Exact signatures: [mcp-signatures.md](mcp-signatures.md).

| Question | Tool |
| --- | --- |
| Formula, masses, expected MS peaks, drug-likeness for one or many structures | `molecule_report` |
| Does this reaction conserve atoms and charge? What is missing? Amounts for a given scale? | `check_reaction_balance` |
| How much of each reagent, solvent and product for this reaction? A page I can draw in and type amounts into; amounts written under the structures of a ChemDraw scheme | `reaction_calculator` (`scheme_output`), `cdx.py calc` |
| An HRMS characterization sentence (`HRMS (ESI) m/z calcd for ... [M+Na]+ ...`) | `hrms_line` |
| The experimental-section materials table and procedure sentence for a batch of reactions | `si_materials_tables` |
| Which reactant atom does each product atom come from? What bonds change? | `map_reaction_atoms` |
| Give me every structure in this CDXML/SDF as SMILES, InChI or a table | `export_structures` |
| What is the name of this structure? | `structure_to_name` (needs ChemScript or ChemDraw for macOS) |

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

## Reaction calculator

`reaction_calculator` turns a reaction into an interactive amounts table and writes it as one standalone HTML page that works offline; `cdx.py calc` serves the same page and adds a ChemDraw canvas to draw on.

```json
{"reaction": {"reactants": [{"smiles": "OCc1ccccc1", "mass_mg": 108.14}, {"smiles": "CC(=O)Cl", "equiv": 1.2}],
              "agents": [{"smiles": "CCN(CC)CC", "equiv": 1.5}, {"smiles": "ClCCl"}],
              "products": [{"smiles": "CC(=O)OCc1ccccc1", "isolated_mg": 120}]},
 "options": {"molarity": 0.2},
 "output_path": "work/acetylation.html"}
```

- `reaction` takes the same forms as `check_reaction_balance`: a reaction string, record lists, or `{"cdxml": ...}`. A record carries one amount: `equiv`, `mmol`, `mass_mg` or `volume_ml`, plus optional `density_g_ml`, `concentration_m` (a stock solution), `purity` and `coefficient`. Products take `isolated_mg` or `yield_percent`.
- `options`: `scale_mmol` (limiting reactant, default 1), `limiting` (reactant index, default 0), `molarity` (of the limiting reagent in the first solvent, default 0.2) and `title`. Common solvents and liquid reagents get a density from a built-in table; others are weighed by mass until a density is typed in.
- The result lists every row with its amounts, the totals (concentration, solvent volume, input mass, atom economy, reaction mass efficiency), `warnings` (for example a yield above 100%), and `assumed`: the rows whose amount is a default (reagents 1 equiv, metal catalysts 5 mol %, the first solvent 0.2 M, further solvents 0 mL). **Say which amounts were assumed rather than presenting them as the user's numbers.**
- In the page every number is editable: type over any equivalents, mmol, mass or volume cell and the rest follow; "Make limiting" re-bases the reaction on another row while keeping all amounts. Species can be added by name, abbreviation, SMILES or formula; the page offers Markdown/TSV copy, a procedure sentence, JSON save/open, undo, print and a dark theme.
- `cdx.py calc [REACTION] [--scale MMOL] [--molarity M] [--offline] [--no-open]` opens the page in the browser from a local server (127.0.0.1, a per-run token in the address, stops a few minutes after the page closes). **Draw in ChemDraw** opens a canvas in ChemDraw (a scheme of the current reaction, or a blank page); after saving it with Ctrl+S, **Load drawing** reads the reaction back and keeps the amounts already typed for structures that are still there. REACTION may be a reaction SMILES, a `.cdxml` file or a JSON record file; with none the page starts empty. `--offline` keeps name lookups local; otherwise a name that is not in the built-in table may be looked up online. The command runs until the page is closed, so start it in the background and give the user the address on its first output line.

The page needs no ChemDraw to calculate; ChemDraw is needed only for the drawing button. Do not invent a molecular weight or a density: when a species is not in the table, ask or take it from the user's data.

### Amounts into a ChemDraw scheme

Add `scheme_output` (a new `.cdxml` path, never overwritten) to `reaction_calculator`, or press **Amounts into scheme** in the `cdx.py calc` page, to write the calculated amounts as text under the drawn structures: `1.00 equiv` / `1.00 mmol` / `108 mg` (`scheme_show` picks any of `equiv`, `mmol`, `mass`, `volume`). Reactants and products get their labels below, agents above the arrow. The source drawing is copied, not modified; structures are matched to rows by their non-isomeric canonical SMILES, and rows with no drawn structure (solvents in a user-drawn file) come back as `unplaced` instead of being guessed onto the canvas. A scheme built from the state also gets the solvent line under the arrow. Check the result with `render_cdxml_files` or in ChemDraw before sending it on.

## HRMS characterization lines

```json
{"molecules": [{"smiles": "CC(=O)OCc1ccccc1", "label": "3a", "adduct": "[M+Na]+", "found_mz": 173.0570}],
 "options": {"ionization": "ESI"}}
```

Per structure the result holds the ion formula, the calculated m/z and the line, for example `HRMS (ESI) m/z calcd for C9H10O2Na [M+Na]+ 173.0573, found 173.0570` (the ion formula is in Hill order with the attached ion last). The m/z is the monoisotopic mass plus the adduct atoms minus the electron mass; `options.electron_mass: false` ignores the electron, as some calculators do, so say which convention a journal expects. Defaults: `[M+H]+` (`[M-H]-` with `mode: "negative"`, the molecular ion for `ionization: "EI"`, a charged structure is its own ion). A measured `found_mz` adds the error in ppm; more than 5 ppm is flagged. `output_path` ends in `.txt`, `.md`, `.csv` or `.json`. The numbers are calculated: never write a "found" value the user did not give.

## Materials tables for a batch of reactions

```json
{"reactions": [{"label": "3a", "reaction": "OCc1ccccc1.CC(=O)Cl>CCN(CC)CC.ClCCl>CC(=O)OCc1ccccc1"},
               {"label": "3b", "reaction": {"cdxml": "work/scheme.cdxml"}}],
 "options": {"scale_mmol": 1.0, "molarity": 0.1},
 "output_path": "work/si_materials.html"}
```

Up to 100 reactions per call; each entry is a reaction string, a record, `{"cdxml": path}` (one table per reaction step, labelled `<file>, step N`) or `{"label", "reaction", "options"}`. Options are those of `reaction_calculator` plus `hrms` (default true, the first product's HRMS line), `adduct` and `ionization`. Each table lists material, role, MW, equiv, mmol, mass and volume, the concentration, atom economy and reaction mass efficiency, the product's isolated mass and yield and its HRMS line, and a procedure sentence. A reaction that cannot be read is reported with its error while the rest continue. `output_path` ends in `.md`, `.csv` (long format, one row per material), `.html` (printable, no external loads) or `.json`. **Amounts the user did not give are assumed defaults, listed per reaction in `warnings`; say so.**

## Atom mapping

```json
{"reaction": "CC(=O)O.OCC>>CC(=O)OCC", "options": {"method": "auto", "compare": false, "include_agents": false},
 "output_path": "work/mapping.svg"}
```

`map_reaction_atoms` pairs product heavy atoms with reactant atoms. Hydrogens are not mapped, and the result is bookkeeping, not a mechanism: pericyclic reactions and rearrangements can be mapped differently from the textbook arrows. Three `method` values:

- `mcs` (built in, nothing to install): repeated maximum-common-substructure matching (rings stay rings unless nothing else is left), keeping the pairing with the fewest unmapped product atoms, then the fewest bond changes. It lists atoms with several equally good sources instead of guessing.
- `localmapper` and `rxnmapper` (optional learned mappers, run locally, nothing is uploaded): LocalMapper is trained on human-corrected reaction-centre labels; RXNMapper reads atom pairing from a transformer's attention. Both decide every atom. RXNMapper returns a `confidence` (a warning is added below 0.8; it is often low for cross-couplings and olefinations) and LocalMapper a `confident` flag: read them before trusting the map.
- `auto` (default): LocalMapper, then RXNMapper, then `mcs`; a mapper that fails falls back with a warning. `available_methods` in the result lists what is installed. Naming an uninstalled mapper is an error that points to the install command.

Install the learned mappers once with `cdx.py install-mappers` (or `rxnmapper` / `localmapper` alone; `--dry-run` shows the plan, `--status` what is installed), or with `scripts/install.py --runtime --mapping --apply`. Each gets its own environment beside the runtime, so their pinned PyTorch stacks never disturb it: several hundred MB each, about 30 s of start-up per call, and LocalMapper needs Python 3.10 to 3.12 (a suitable interpreter is found, or fetched through `uv` when present). `compare: true` runs every installed method and adds a `comparison` with the product atoms they disagree on; where the methods differ, show the user both and let them decide.

- `mapped_reaction` is the reaction SMILES with atom map numbers; `map` is the per-atom table; `bond_changes` lists formed, broken and order-changed bonds; `unmapped_reactant_atoms` are the leaving groups.
- `status`: `complete`; `incomplete` when product atoms have no source in the reactants (a reagent may be missing, try `include_agents`, or the reaction is unbalanced); `ambiguous` (`mcs` only) when product atoms could come from several reactant atoms at the same cost. Ambiguous atoms are left unmapped and listed with their candidates; `resolve_ambiguity: true` accepts a fixed tie-break and warns. **Do not present a tie-break as the true mapping, and do not resolve an ambiguity silently.**
- `output_path` ends in `.json`, `.smi` (the mapped reaction SMILES) or `.svg` (a picture); at most 120 heavy atoms per side.

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
