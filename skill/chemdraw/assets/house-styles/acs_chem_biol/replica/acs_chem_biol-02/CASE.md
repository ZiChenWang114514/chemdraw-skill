# ACS Chem. Biol.: LIMK2 degrader SAR table (Figure 2A), not reproduced

Source: Azeez et al., "Discovery and development of a potent LIMK2 isoform-specific degrader", *ACS Chem. Biol.* 2026. DOI: [10.1021/acschembio.6c00137](https://doi.org/10.1021/acschembio.6c00137). Licence: CC BY 4.0 (from the house-style card). The reference crop is `reference.png`, reproduced under that licence.

Drawing style: the `acs_chem_biol` house style (card `toolkit/cdxml_toolkit/publication/house_styles/acs_chem_biol.json`, base preset ACS Document 1996), figure type `sar_table`.

## What is reproduced

Nothing. The crop is a data table: compound IDs, DSF Tm shifts, SPR K_D values, NanoBRET IC50 values and E3 ligand labels. It contains no structures and no reaction. `draw_figure` draws only species given as a SMILES or a name, and a brief with no species is refused. The structures behind the IDs (21a to 23i, LIMKi3, VH032, CRBN ligands) are not in the crop, so no SMILES was written, guessed or resolved.

Probe: `replay.py`, which calls `draw_figure` directly, with `brief.json` (style `acs_chem_biol`, empty `species` and `steps`, `max_width` 504). It returned `ok: false` with two errors: "species: list every structure that is drawn, each with an id and a smiles or a name." and "steps: give at least one step with substrates and products." No output path was returned, and no render was attempted, so `rendered.png` does not exist.

The crop also contains the top edge of panel C (the ternary complex cartoon), which is not part of the table.

## Replay

`brief.json` is the probe brief. `replay.py` runs it through `draw_figure` and so reproduces the refusal above; it is kept for the day a structure source exists. The text-and-rule check described under Tool gaps was run as a separate manifest and is not part of this case folder.

## Convention table

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| table_style: horizontal_rules | thin horizontal rules under the header and at the section breaks | not drawn | no |
| table_style: no vertical rules | no vertical rules | not drawn | no |
| activity_format: {value} | bare numbers (7.0, 35, 62, 17 in the LIMKi3 row) | not drawn | no |
| variation_color: null | all table text black, no coloured values | not drawn | no |
| highlight_fill: null | no fill behind any row | not drawn | no |
| signature: compound IDs in the first column | 21a to 23i and LIMKi3 in the first column | not drawn | no |
| signature: series headings bold underlined | VHL-C3, VHL-C5 and VHL-C6 as bold underlined headings | not drawn | no |
| signature: two-level bold header, grouped targets above unit-bearing columns | LIMK1 and LIMK2 bold above DSF Tm (°C), SPR K_D (nM), NanoBRET IC50 (nM) | not drawn | no |
| top-level compound_label_color #000000 | black table text | not drawn | no |
| top-level label font Arial or Helvetica | sans-serif table text | not drawn (font not checked) | no |

Matched 0 of 10 rows. No convention was reproduced, because nothing was drawn.

## Differences from the paper

- No table was drawn at all. The paper's table, with its column groups, rules and bold headings, has no counterpart in this replica.
- The `activity_format` and `table_style` conventions were not applied to any output. Nothing else was produced that could carry them.
- The paper's column headings "SPR K_D (nM)" and "NanoBRET IC50 (nM)" are the units the card calls out (the card writes "SPR KD (nM)"); they could not be checked against a rendering.

## Tool gaps

- No SAR or optimisation table drawer in the brief tools. `draw_figure` accepts only the kinds `scheme`, `scope` and `mechanism` (`figure_draw.py`). Reaction, route (linear, convergent, divergent) and catalytic cycle are layouts inside `scheme`. No code reads the `sar_table` or `optimization_table` conventions.
- `publication_figure` has a SAR mode as well as scope (`mode: "sar"`, `references/data-driven-figures.md`). It needs a SMILES for every compound, so it cannot take this table. It is refused here for the same reason as `draw_figure`.
- `draw_figure` refuses a brief with no species. This is correct for that tool, but it does not mean a table with no structures has no input form (see the next point).
- A structure-free table does have an input form: `compose_chemical_figure` (`mcp_runtime/figure_tools.py`) takes a manifest of `text` objects (position, runs with bold, underline, subscript and colour), `line` objects (start, end) and `rectangle` objects, and needs no molecule. A probe manifest with five text objects and one rule composed into an editable CDXML. It was not rendered and has not been compared with the reference by eye, so no visual match is claimed.
- The `publication_figure` scope mode binds each label and value to a structure (`references/data-driven-figures.md`: required `compound_id` and `smiles`, "labels and measurements remain tied to IDs"). This is true of that mode but is not the only route.
- The `sar_table` conventions (`table_style`, `activity_format`, `variation_color`, `highlight_fill`) are listed under `skipped` as guidance (per `references/scheme-drawing.md`), so no brief tool applies them. The card cannot change what a tool draws for this figure type.
- Gaps the first pass missed:
  - `publication_figure` reads flat tables. Spreadsheets with merged or multiple header rows must be flattened first (`references/data-driven-figures.md`). The two-level header (LIMK1 over three columns, LIMK2 over one) and the merged E3 ligand cells spanning two or three rows cannot come through that pipeline.
  - `compose_chemical_figure` has no merged-cell or text-grid primitive. Its `grid` option positions molecule objects only. Each header, cell and rule must be placed by coordinates.
  - No decimal-alignment or column-centring helper. Text `align` is per object (Left, Center, Right), so right-aligned numbers need coordinates computed by hand.
  - Merged E3 ligand cells need a bracket or rule per edge, because the composer draws only straight lines.
- Not checked: `cdx.py build`. `references/acs1996-drawings.md` lists `text` (with `bold`) and `box` objects for the build spec, but the build path was not run here.

## Audit

Date 2026-11-07. Checked the reference crop, this CASE.md, `brief.json` and the house-style card; grepped the toolkit for the refusal messages, the draw kinds and the table paths; re-ran the `draw_figure` probe offline (same two errors, no output path returned); ran a text-and-rule manifest through `compose_chemical_figure` into a temporary folder (`table-probe/table.cdxml`, not rendered).

- Corrected matched count: 0 of 10. No row could be refuted as a match, because nothing was drawn.
- Overclaims corrected in this file:
  1. "A table with values and IDs but no structure has no supported input form" was false. `compose_chemical_figure` accepts text, lines and rectangles with no molecule.
  2. "Not checked: whether cdx.py build can place plain text and horizontal lines" is now partly answered: the composer places text and lines, and the build reference lists text. Neither was rendered.
  3. "No SAR or optimisation table drawer" omitted the SAR mode of `publication_figure`. It is still structure-bound, so the gap stands with the qualification.
  4. The probe was misdescribed. It was `replay.py` calling `draw_figure`, not `cdx.py draw`, and `brief.json` also carries `max_width` 504.
  5. The draw kinds were misstated. The code accepts `scheme`, `scope` and `mechanism`; reaction, route and catalytic cycle are layouts inside `scheme`.
  6. The label-font row was marked "not checked" in the match column; it is now "no" (nothing drawn), with the count unchanged.
- The description of the reference crop holds: IDs in the first column, bare numbers, bold underlined VHL headings, merged E3 ligand cells, no vertical rules, no fill, and the top edge of panel C.
- The reasoning that the table cannot be drawn by the brief tools stands. The claim that no tool could hold the table at all does not.
