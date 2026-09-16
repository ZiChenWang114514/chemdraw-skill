# Saved-file figure validation

Use for final CDXML checks and, especially, bridges, charged symbols and stereo-sensitive edits. This CLI uses the existing registered isolated workers for native saving; it does not add an unlocked COM path.

Run `python -m cdxml_toolkit.mcp_runtime.figure_tools validate_figure --arguments check.json`.

The JSON arguments are `input_path`, a new `output_dir`, optional `native` (default false), and optional `cross_reader` (default false, requires native). Paths should be absolute. The output directory retains `report.json`, saved native files and any extracted native fragments used for direct reader comparison.

- Basic: XML object/reference checks, source hash, molecule inventory, connectivity, formal charge and specified stereo.
- Native: CDXML -> CDX -> CDXML through locked workers. Compare inventories and distinguish changes from unavailable checks; the source is untouched.
- Cross-reader: read saved native CDXML fragments directly with ChemScript and RDKit; no MOL intermediate. Record pairing or atom-mapping ambiguity rather than inventing an assignment. Tetrahedral CIP changes are not automatically spatial inversions when connectivity changes.
- Visual: the report does not claim visual review. Render with `render_cdxml_files`, then actually inspect the PNG/SVG against the reference.

`ok=true` means the diagnostic directory was written, not that all checks passed. Read `native.status`, its comparison, `cross_reader.status`, and `source_identity`. `not_run`, `failed`, `unavailable`, `unresolved`, `changed` and `preserved` describe different outcomes. Native failure leaves a valid diagnostic report, not an accepted chemistry result. Molecular inventory equality proves reader consistency only.

For structural corrections, `modify_molecule.diff` retains legacy fields and adds `status`, `method`, `reason`, `atom_mapping`, `atom_changes`, `bond_changes`, and `stereo_changes`. Mapped stereo checks cover tetrahedral CIP and bond stereo; unclassified semantic differences, including enhanced-group distinctions, remain partial. `completed` means the stated comparison completed; `partial` and `not_completed` cannot authorize a no-change claim. Null mapping or an empty legacy list is not independent evidence of equivalence. MCS execution is bounded; symmetric mappings stay explicit.

Timing and token reports are optional user deliverables. Keep host-specific accounting outside runtime health responses, distinguish repeated/cached inputs and outputs, and state the exact cutoff and unavailable third-party usage.
