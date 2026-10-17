# Saved-file figure validation

Use for the final CDXML, and always for bridges, charge symbols and stereo-sensitive edits. Native saving goes through the locked worker.

```bash
cdx.py py -m cdxml_toolkit.mcp_runtime.figure_tools validate_figure --arguments check.json
```

Arguments: `input_path`, a new `output_dir`, optional `native` (default false) and `cross_reader` (default false; needs `native`). Use absolute paths. The output folder holds `report.json` and the saved native files.

- **Basic:** XML references, molecule inventory, connectivity, formal charge, specified stereo.
- **Native:** CDXML → CDX → CDXML, then the inventories are compared. The source is untouched.
- **Cross-reader:** saved fragments read directly by ChemScript and RDKit (no MOL step).

`ok=true` only means the report was written. Read `native.status`, `cross_reader.status` and `source_identity`; the values `not_run`, `failed`, `unavailable`, `unresolved`, `changed` and `preserved` mean different things. The report does not cover appearance: render with `cdx.py render` and look at the PNG.

For structural corrections, `modify_molecule.diff` gives `status`, `atom_changes`, `bond_changes` and `stereo_changes`. Only `completed` supports a "no change" statement; `partial`, `not_completed` or a null mapping do not.

For reader disagreement, hydrogen loss on abbreviations and version-specific stereo handling, see [stereo diagnosis](stereo-reconstruction.md).
