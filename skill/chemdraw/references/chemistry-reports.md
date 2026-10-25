# Chemistry reports

Three deterministic tools answer the questions people ask after a structure is drawn: what are its numbers, does the reaction balance, and what is in this file. They read grounded structures (SMILES, MOL/SDF, CDXML fragments), compute with RDKit and never recognize, guess or edit a structure. Exact signatures: [mcp-signatures.md](mcp-signatures.md).

| Question | Tool |
| --- | --- |
| Formula, masses, expected MS peaks, drug-likeness for one or many structures | `molecule_report` |
| Does this reaction conserve atoms and charge? What is missing? Amounts for a given scale? | `check_reaction_balance` |
| Give me every structure in this CDXML/SDF as SMILES, InChI or a table | `export_structures` |

All three accept `output_path` (never overwritten) and return their data inline, so a small result needs no file. Run one as `cdx.py call TOOL --args args.json`.

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

## Export every structure in a file

```json
{"source": "work/scheme.cdxml", "output_path": "work/structures.csv"}
```

`source` is a CDXML, MOL, SDF or `.smi` path, or a list of structure records. CDXML yields each top-level fragment in document order with its fragment id; SDF titles and `.smi` names become labels. Output formats by extension: `.csv`, `.json`, `.smi`, `.sdf` (with SMILES, InChIKey and formula as properties), `.md`. `options.include_molblock` adds a MOL block per structure.

Structures with R groups or other generic atoms are listed without an InChI and the result says so. Binary CDX needs `convert_cdx_cdxml`, Office files need `extract_cdxml_from_office`. Because the fragments come from the saved file, this also works as a read-back: export, then compare with the SMILES the drawing was built from.

Limits: 256 structures for `molecule_report` and `check_reaction_balance`, 2000 for `export_structures`, 1000 atoms per structure.
