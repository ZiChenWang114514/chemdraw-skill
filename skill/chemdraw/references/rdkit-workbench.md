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

Example arguments for an already grounded MOL file:

```json
{"molecules":[{"file":"C:/research/verified.mol"}],
 "operation":"inspect","options":{"include_molblock":true},
 "output_path":"C:/research/inspection.json"}
```

First inspect, then select exact atom indices for set_stereo. Inspect its before/after CIP diff and `connectivity_preserved` before drawing. A structural change using another operation still routes through `modify_molecule` and its MCS diff. `set_stereo` rejects enhanced-group inputs because a local R/S edit can alter group meaning. Enumeration is deliberate candidate generation and must not be described as an observed mixture or assigned product.

For same-scaffold figure series, combine `mcs` inspection with `compose_chemical_figure` molecule `align_to` / `alignment_mode: mcs`, and use `grid` for a compound or substrate-scope panel. Explicit reference coordinates override automatic layouts when reproducing a journal conformation.

Limits are enforced: 1..128 input molecules, 1000 atoms per molecule, bounded enumerations, and MCS timeout. Inputs are local; these operations do not upload chemistry. Results use zero-based input atom order. Canonical SMILES may reorder atoms, so never reuse old indices against a canonicalized candidate without reinspection.

Use the full runtime profile (identifier `codex`, supported by any MCP client), or run the [figure CLI](publication-figures.md#immediate-cli-fallback) with the toolkit Python environment.
