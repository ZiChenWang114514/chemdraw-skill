# Data-driven publication figures

Use for substrate-scope panels, full-structure SAR panels, or updating a generated
figure after editing it in ChemDraw. The runtime must include `publication_figure`.
Use the existing figure composer for arbitrary schemes and mechanisms instead.

## Start from structures and a table

Ask for the table, trusted structure source and desired display fields when these
are not already supplied. CSV is portable; XLSX requires the runtime's
`publication` extra (`openpyxl`). Formula cells need values cached by Excel; this
workflow never calculates them. Simple decimal, percentage (including `0.0%`), scientific and quoted-unit numeric formats preserve their displayed precision and units; unsupported numeric formats produce a cell-specific error. Prefer explicit text for percentages, inequalities,
ranges and units. Blank measurements are displayed as an em dash, never zero.

Minimal specification:

```json
{
  "mode": "scope",
  "table": "results.csv",
  "group_column": "series",
  "fields": [
    {"column": "yield", "label": "Yield"},
    {"column": "ee", "label": "ee"}
  ],
  "conditions": "Shared reaction conditions supplied by the researcher",
  "footnotes": ["a: isolated yield"],
  "native_render": true
}
```

Required table fields are `compound_id` and `smiles` by default. Optional `label`
is the displayed compound number, independent of the stable ID. `id_column`,
`label_column` and `group_column` select other headers. Select `sheet` explicitly
for a multi-sheet XLSX. `fields` choose the exact measurement columns and optional
display `label` and `unit`; do not append a unit already present in the cell.
`label` is reserved and must not also be a measurement column.

Structure alternatives:

- `structure: {"format":"mol", "column":"structure_file"}`: paths in the table
  are relative to the table directory.
- `structure: {"format":"sdf", "file":"library.sdf", "id_property":"compound_id"}`:
  exactly one SDF record must match each table ID.
- `structure: {"format":"smiles", "column":"smiles"}`: trusted SMILES/CXSMILES.
  Old CX coordinates and wedge directives are discarded when generating a new
  layout; chemical identity and enhanced stereo groups are retained and checked.

Other specification paths are relative to the specification file. Duplicate IDs,
invalid structures and missing or ambiguous SDF matches are errors with row context.

## Substrate scope

Use `mode: "scope"`. Select yields, ee/dr, conditions and footnotes from the actual
data. Rows are grouped in first-occurrence order; order within a group follows the
table. Labels and measurements remain tied to IDs during pagination.

## Full-structure SAR

Use `mode: "sar"` with fields such as `{"column":"IC50","label":"IC50","unit":"nM"}`.
All compounds retain their complete structures. R-group decomposition tables and
inferred potency/selectivity are outside this workflow. `core_by_group` maps a
group name to a reference compound ID; otherwise the first structure is used.
Groups without a usable common core carry a warning and independent depictions.

## Layout

`style` accepts `width_mm`, `height_mm`, `font_size`, `bond_length`, and `font`.
Defaults are 180 by 240 mm, 8 pt Arial text and 14.4 pt bonds: design defaults,
not a universal journal specification. Rows wrap or paginate at fixed text/bond
sizes. Each page is a separate native editable CDXML. An oversized structure is
reported rather than silently shrunk. Native exports may crop surrounding whitespace;
assess final reproduction size when inserting them into a manuscript.

## ChemDraw editing and incremental updates

Keep the generated project directory unchanged. Save hand-edited pages separately,
then supply them through `edited_pages`; keys are **zero-based page indices**.

```json
{
  "project_path": "previous/project.json",
  "table": "updated-results.csv",
  "edited_pages": {"0": "hand-edited-page.cdxml"},
  "native_render": true
}
```

The saved import and display choices are reused. Existing objects are locked:
data-only edits preserve native position, font and annotations. New compounds are
placed on new pages, keeping existing pages stable. To change grouping, display
fields, global style, title, conditions or footnotes, create a new layout explicitly.

Supply a trusted replacement structure under the same ID. Common-core coordinates
are retained; symmetric mappings require `atom_maps: {"compound-id":[[old,new],...]}`
using zero-based atoms from the **edited CDXML readback** and incoming normalized
structure, respectively. Inspect both structures first. The update records the
mapped atoms and old/new identities; it does not invent a replacement structure.

The baseline input, baseline displayed content and edited figure are compared
separately. Manual-only text or structure changes remain visible and are recorded.
Concurrent changes to the same value/structure, an ambiguous object match, or a
deleted group whose row still exists produce a conflict. Remove a row to request
deletion; deletion versus a manual content edit also requires resolution.

Resolve a conflict by correcting the incoming data or edited page, or supplying
an explicit atom map, then rerun against the original baseline into a new directory.
Conflict output contains `conflicts.json` and viewable `draft/` pages, not an accepted
new `project.json`. Do not use a draft as a completed revision.

## Execute and inspect

The MCP signature is generated in [mcp-tools.md](mcp-tools.md).
The equivalent CLI is:

```console
python -m cdxml_toolkit.mcp_runtime.publication_figure create --spec figure.json --output new-project
python -m cdxml_toolkit.mcp_runtime.publication_figure update --spec update.json --output new-revision
python -m cdxml_toolkit.mcp_runtime.publication_figure check --spec check.json --output new-check
```

`check` needs `project_path` and optional `edited_pages`, and writes a new report;
it never changes the source project. Output includes pages, `project.json`, raw input
snapshots, normalized `data.json`, `changes.json`, `checks.json`, and native `png/`
and `svg/` previews when available. Preserve the complete directory for later updates.

Review data binding, reader consistency, layout and native preview independently.
Native previews start at `rendered_pending_visual_review`; open and inspect them.
Report overlaps and out-of-page objects by page and compound ID. Locked objects
are not automatically moved. Font geometry is conservative, not pixel-perfect
collision proof. `unresolved_chemistry` records known disagreements and persists
across updates; never remove it merely to obtain a pass.

The [runnable examples](../examples/publication/run_examples.py) create both 48-row
layouts. Structures are sourced from existing editable examples and intentionally
reused; all measurements are illustrative, not experimental findings.

## Reconstructing a real literature panel

Read the article figure and its caption together with the supporting data. For
spreadsheets with merged or multiple header rows, prepare a flat import table and
record each source worksheet/cell and its original number format. Keep residual
activity distinct from percent inhibition, and label comparator targets separately.
Copy missing measurements as missing; preserve interference and solubility notes.

When crystal chemical-component dictionaries and the drawn figure use different
tautomers, preserve both source records and route the figure-specific correction
through `modify_molecule`, retaining its diff. A successful reader round trip does
not prove agreement with the source image. Inspect all final native pages against
the article before reporting a reconstruction as reviewed.
