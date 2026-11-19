# RDKit workbench

Use `rdkit_workbench(molecules, operation, options, output_path)` for batch chemical analysis and controlled stereochemical editing. Inputs must be grounded structures; returned candidates can feed drawing tools. It writes JSON with source semantic keys, atom indices, candidates, warnings and truncation flags. It does not modify source files.

## Operations

| Operation | Purpose | Main controls |
|---|---|---|
| inspect | Element/isotope/charge, atom indices, actual CIP labels, potential stereo, enhanced groups, formula and masses | include_molblock emits V3000 |
| set_stereo | Explicitly set selected tetrahedral centers to R, S or unspecified without changing connectivity | one input; configurations maps zero-based atom index strings to targets |
| stereoisomers | Enumerate candidates, usually only unspecified centers | only_unassigned defaults true; max_results 1..128 |
| tautomers | Enumerate bounded tautomer candidates | max_results; inspect status/truncated; not a pH/population model |
| mcs | Chirality-aware maximum common substructure and input atom matches | 2+ inputs, timeout 1..30 seconds |
| r_groups | Decompose a series against an explicitly supplied core | first molecule is the core; report unmatched indices |
| edit_structure | Atom-index graph and stereo edits on one molecule; returns the edited SMILES | `set_atom` `[{"atom": 3, "element": "N", "charge": 0, "h": 1}]`; `set_bond` `[{"atoms": [1, 2], "order": 2}]`; `add_group` `[{"atom": 4, "smiles": "C(F)(F)F"}]`; `remove_atoms` `[5, 6]`; `set_ez` `[{"atoms": [1, 2], "geometry": "E"}]`; `set_stereo` `[{"atom": 1, "label": "R"}]` (`S`, `invert`, `unspecified`); or a combined `ops` list of `{"op": ...}` records |
| edit_smarts | Apply a reaction SMARTS to one molecule and return the first product | `edit_smarts` (or `smarts`) is the reaction SMARTS; an unmatched pattern is an error |
| read_wedges | Set stereocentres from wedges read off a drawing and return CIP labels | `wedges` `[{"atom": 1, "neighbor": 2, "kind": "wedge"}]` (`kind` wedge, hash or plain; `neighbor` an atom index or `"H"`); optional `positions` `{atom index: [x, y]}` from the drawing |
| depict_like | Depict one molecule in the orientation of a reference image, with atom indices | `reference_image` (or `reference_image_path`); optional `image_output_path` (PNG), `annotate_indices` (default true), `size` (default 500) |
| enumerate_markush | Attach R-group fragments to a `[*:n]` core with `molzip` | core is `core_smiles` or the first molecule; `r_groups_by_label` `{"5a": ["[*:1]F", "[*:2]C"]}` (or `r_groups`: one list or string for a single product) |

Options are given in `options` (a flat object); unknown keys are refused. With `operation: "inspect"`, edit keys switch to `edit_structure`, `edit_smarts`/`smarts` to `edit_smarts`, `wedges` to `read_wedges`, `reference_image` to `depict_like` and `r_groups`/`r_groups_by_label` to `enumerate_markush`. `set_stereo` with `configurations` alone (`{"3": "R"}`, zero-based atom index strings to `R`, `S` or `unspecified`) is the checked CIP edit above; with edit keys it runs as `edit_structure`. `max_results` (1..128, default 32) bounds every enumeration.

Example arguments for an already grounded MOL file:

<!-- example: call rdkit_workbench -->
```json
{"molecules":[{"file":"work/verified.mol"}],
 "operation":"inspect","options":{"include_molblock":true},
 "output_path":"work/inspection.json"}
```

Setting one stereocentre with `edit_structure` (L-alanine to D-alanine; atom 1 is the alpha carbon in the order of the SMILES):

<!-- example: call rdkit_workbench -->
```json
{"molecules":[{"smiles":"C[C@H](N)C(=O)O"}],
 "operation":"edit_structure","options":{"set_stereo":[{"atom":1,"label":"R"}]}}
```

Relative paths resolve against the directory `cdx.py` runs in; absolute paths work on every OS (forward slashes are fine on Windows).

First inspect, then select exact atom indices for set_stereo. Inspect its before/after CIP diff and `connectivity_preserved` before drawing. A structural change using another operation still routes through `modify_molecule` and its MCS diff. `set_stereo` rejects enhanced-group inputs because a local R/S edit can alter group meaning. Enumeration is deliberate candidate generation and must not be described as an observed mixture or assigned product.

For same-scaffold figure series, combine `mcs` inspection with `compose_chemical_figure` molecule `align_to` / `alignment_mode: mcs`, and use `grid` for a compound or substrate-scope panel. Explicit reference coordinates override automatic layouts when reproducing a journal conformation.

Limits are enforced: 1..128 input molecules, 1000 atoms per molecule, bounded enumerations, and MCS timeout. Inputs are local; these operations do not upload chemistry. Results use zero-based input atom order. Canonical SMILES may reorder atoms, so never reuse old indices against a canonicalized candidate without reinspection.

Run it with `cdx.py call rdkit_workbench --args args.json`.
