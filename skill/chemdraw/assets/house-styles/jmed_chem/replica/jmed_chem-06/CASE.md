# J. Med. Chem.: SAR table, LIMK1/LIMK2 activities (Table 1, upper part)

Source: Baldwin, Ward et al., "Discovery of MDI-114215: a potent and selective LIMK inhibitor to treat fragile X syndrome", *J. Med. Chem.* **2025**. DOI: [10.1021/acs.jmedchem.4c02694](https://doi.org/10.1021/acs.jmedchem.4c02694).

Licence: CC BY 4.0, reference crop reproduced under that licence (`evidence/jmed_chem-06.png`).

Drawing style: the `jmed_chem` house style in `brief.json` (`style`), base preset ACS Document 1996; figure type `sar_table` on the card.

## What is reproduced

The six rows of the table in the crop: compounds 57, 71, 72, 73, 74 and 75, each with its R group, A (C or N), cLogD, LIMK1 and LIMK2 pIC50 (mean ± SD), microsomal CLint (human, rat), Caco-2 Papp A:B and efflux ratio ER. All values are copied from the crop, in the same text as the paper.

The R groups are drawn as structures: H, F, NH2, a morpholin-4-yl group, a 2-hydroxyethylamino group and a 2-methoxyethylamino group. The core and the A position are not drawn: the core is in crop 07 (a separate replica), and A is given as a text field.

The tool used is `kind: "scope"` (substrate-scope panel), the nearest drawer in `draw_figure`. `draw_figure` has no table kind, so the grid, the header row and the merged group headers are not drawn.

| SMILES in brief (R fragment, attachment as `*`) | compound | R in crop |
| --- | --- | --- |
| `*[H]` | 57 | H |
| `*F` | 71 | F |
| `*N` | 72 | NH2 |
| `*N1CCOCC1` | 73 | morpholin-4-yl |
| `*NCCO` | 74 | NH-CH2CH2OH |
| `*NCCOC` | 75 | NH-CH2CH2OMe |

The `*` marks the attachment point to the core. These SMILES are fragment depictions for the drawing only; they are not compounds.

## Build

Draw run with `cdx.py draw brief.json <out>`; one run wrote two pages (see Differences). `rendered.png` joins try-3 pages 1 and 2 vertically, downscaled to 1200 px wide and quantised to 16 grey levels to fit 250 KB.

Attempt log: try 1 with `[H]` for 57 failed with `unsupported_radical`; try 2 (`*[H]`) timed out at 300 s under concurrent ChemDraw load; try 3 (same brief) drew six compounds on two pages and rendered both pages through desktop ChemDraw.

`replay.py` is the scope-kind variant of the jacs-au script: it writes the panel into a `panel/` subfolder, because `draw_figure` writes a folder for scope panels. It was not re-run for this case; `brief.json` is the one used for try 3.

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| table_style: grid (black rules on every cell) | full grid, rules between all rows and columns | no rules; each compound is a block of "Field: value" lines | no |
| signature: full black grid on every cell | grid | no grid | no |
| signature: core structure with R and A drawn above the table | core image above the table | not drawn (core is in crop 07; scope kind has no core layout) | no |
| signature: bold header with merged group headers (Enzymatic pIC50 over LIMK1 and LIMK2) | bold header row; "Enzymatic pIC50" merged over LIMK1, LIMK2 | no header row; each value is prefixed by its field name, e.g. "LIMK1 pIC50: 7.48 ± 0.18" | no |
| signature: bold compound numbers in the first column | bold 57 to 75 | plain 57 to 75 above each structure | no |
| signature: R groups drawn as small fragments with a dashed attachment bond | fragments with dashed bonds | R label with solid bond ("R-H", "R-F", "R-NH2"); morpholine and ethanolamine drawn as full rings and chains with a solid "R" bond | no |
| signature: text values such as Rapid and nd mixed with numbers | "Rapid" and "nd" in the number columns | "Rapid" and "nd" on the same field lines, with no columns | no |
| activity_format: pIC50 mean ± SD, two decimals (7.48 ± 0.18) | 7.48 ± 0.18, 6.80 ± 0.01 | 7.48 ± 0.18, 6.80 ± 0.01 [c] | yes |
| variation_color: None | black | black | no (not verifiable here, see Audit) |
| highlight_fill: None | none | none | no (not verifiable here, see Audit) |
| compound_label_face: bold (top level) | bold numbers | plain numbers | no |
| compound_label_color: #000000 (top level) | black | black | no (not verifiable here, see Audit) |
| black only, no colour, boxes or shading (top level) | black | black | no (not verifiable here, see Audit) |
| bond_length_over_cap_height 2.25 (top level; crop 06 measures 60 / 28 = 2.14) | 2.14 on the crop | not measured on the render | no |

Rows in the table: 14. Matched (yes) after audit: 1 (activity_format). The first count was 13 claimed rows and 6 matched; see Audit.

Visible but not claimed by the card for this figure type: superscript footnote letters on headers and values (a, b on the LIMK headers, c on 6.80) are superscripts in the paper; the replica gives "[c]" as text and no a or b. Abbreviate_groups (Boc, CF3) is not visible in this crop, so it is not counted.

## Differences from the paper

- Layout: the paper is one ruled table with a header row and six rows of columns. The replica is a substrate-scope panel: one block per compound, with the R structure above its values, split over two pages of three compounds (57, 71, 72 on page 1; 73, 74, 75 on page 2). `rendered.png` joins the two pages.
- Title: the panel prints "Substrate scope" above each page, which is not in the paper. Setting `"title": ""` did not remove it.
- Header: no column headers and no merged group header. Field names appear as prefixes, "cLogD: 4.09", "LIMK2 pIC50: 7.85 ± 0.24", so units and group names repeat on every row.
- Compound numbers are plain, not bold.
- A is shown as the text "A: C" or "A: N", not as a column.
- R groups: 57, 71 and 72 are drawn as "R-H", "R-F" and "R-NH2" with a solid bond and an "R" label, where the paper shows a bare H, F or NH2 on the core. 73, 74 and 75 are drawn as full ring or chain structures, not as fragments with a dashed attachment bond. The attachment point is the "R" label, not a dashed bond.
- Footnote marker c is "[c]" in text, not a superscript; the a and b markers of the headers are not drawn.
- Values, units in the field names (µL/min/mg, ×10⁻⁶ cm/s) and decimal places match the paper. Black only, as in the paper.

## Tool gaps

- No table kind: `draw_figure` has no ruled grid, no bold header row, no merged group header and no bold first column. The scope kind is the nearest drawer and does not lay values out in columns.
- Scope panels print each value with its field name as a prefix ("cLogD: 4.09"); there is no option to print the bare value under a column header.
- The title "Substrate scope" is printed by default and repeated on each page; `"title": ""` does not suppress it.
- Scope compound labels are plain; there is no bold-label option for scope panels (also noted for chemeurj).
- No attachment-point drawing: the `*` in a SMILES is drawn as an "R" label on a solid bond; there is no dashed attachment bond.
- A bare hydrogen cannot be drawn as an R group: `[H]` is refused with `unsupported_radical` ("radical export is not yet validated"); `*[H]` is accepted and drawn as "R-H".
- No core-with-variable-positions layout: the core and the A and R positions above the table (crop 07) cannot be expressed in a scope panel.
- Superscript footnote markers on headers and values: the fields accept text only, so "c" is written as "[c]" and header superscripts cannot be drawn.
- Pagination: the scope kind packs three compounds per 180 mm page, so the six rows split across two pages. There is no option for a single row of six compounds in this layout.
- Run time: under concurrent ChemDraw load a scope draw took up to 300 s and timed out; the successful try reported 7.2 s for the draw itself (summary.json) once ChemDraw was free.
## Audit

A second reader checked the table against reference.png, rendered.png, brief.json, jmed_chem.json and the toolkit source (figure_scope.py, publication/layout.py, publication/data.py, mcp_runtime/figure_draw.py). The values of all six compounds (A, cLogD, LIMK1, LIMK2, human and rat CLint, Papp, ER) match the crop.

Table corrections:

- The table has 14 rows, not 13. Only activity_format survives; the partial row is a no, since no structure has a dashed attachment bond and 73 to 75 are full structures.
- Text values: the replica has no number columns, so Rapid and nd are not in the same positions as in the paper; the values sit on the same field lines.
- The four colour rows (variation_color, highlight_fill, compound_label_color, black only) are not verifiable here. rendered.png is a 16-entry greyscale PNG (every palette entry has equal R, G and B), and no CDXML or colour render is in this folder. Re-score them from the native file if one is produced.
- Not in the Differences list: in 74 and 75 the H sits above N in the replica and below N in the paper; the morpholine orientation differs (paper: N upper left, O lower right; replica: O left, N right); the pIC50, CLint and Papp subscripts are plain text.

Tool-gap statements that are wrong or incomplete:

- Bare values are possible: a field with label "" prints its value without a prefix (publication/data.py field_text). What is missing is column headers, not the bare-value option.
- Pagination is set by the brief: width_mm (60 to 400) and height_mm (60 to 500) are accepted, and create_pages starts a new page when the next compound does not fit the page height. The 150 mm height is a likely cause of the split, not only the 180 mm width. Other sizes were not tested.
- The title is a bug, not a missing option: brief.get("title") or "Substrate scope" in figure_scope.py (_write_inputs) treats "" as absent. Conditions and footnotes also repeat on every page.
- House conventions are dropped for scope panels; the report says so only in its style field, not in warnings.

Tool gaps the replicator missed: font size and bond length cannot be set in a scope brief (SCOPE_KEYS has neither, and _write_inputs drops font_size from the preset), so the card's bond-to-cap-height ratio cannot be drawn; no subscript or superscript runs in scope text (figure_draw.py already writes a superscript run for the transition-state mark); no per-cell alignment; no control of structure orientation or hydrogen placement, although publication/layout.py accepts a reference core per group (core_by_group) that scope briefs do not pass.

Not verifiable from this folder: summary.json (the 7.2 s draw time), the try-2 timeout, and the desktop ChemDraw render. None of these run outputs is present.

Corrected matched count: 1 of 14.
