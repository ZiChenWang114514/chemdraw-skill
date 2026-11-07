# US 9,732,080 B2: Table 5, binned EC50 and maximum efficacy (SAR table, not drawn)

Source: Hadida-Ruah et al. (Vertex), US 9,732,080 B2, 2017 (Modulators of ATP-binding cassette transporters), Table 5. Licence: public domain (US patent), as the card states. Evidence crop: `evidence/uspto_patents-08.png`.

Card: `uspto_patents` (base preset `j_mol_mod`), figure type `sar_table`.

## What is reproduced

Nothing is drawn. The crop has no chemical structures. Above the caption it holds three cut-off lines of running body text, which are not part of the table. The table itself is text only: a TABLE 5 caption, a two-line bin legend, three centred columns (Compd. No., Binned EC50, Binned Max Efficacy) and 15 compound numbers, each with a binned activity symbol (+, ++, +++). `draw_figure` has no table kind. Its kinds are scheme, scope and mechanism (any other kind is refused), and each needs structures. Route, convergent, divergent and catalytic-cycle are layouts of the scheme kind, not kinds. `publication_figure` in SAR mode also needs a structure for each row. With no structures to draw, the brief in this folder is empty and no `rendered.png` was produced.

Attempt: `brief.json` (style `uspto_patents`, empty species and steps) was run with `cdx.py draw` without `--render`. The call returned `resource_busy` after 295 s (`chemdraw_com` lock), while another `cdx.py draw` job was running on the same ChemDraw. No figure was written, and the call gave no content-based refusal. The retry was not run: a second `cdx.py` call with an empty brief would only repeat the lock wait and would test nothing about the card.

`replay.py` calls `draw_figure` in-process, so it does not take the `chemdraw_com` lock and does not repeat the lock wait. It should be refused at once by the brief check, which names the missing species and steps in `validation.json`. It is kept so this folder matches the other replica folders.

## Comparison

| convention or signature feature | paper | replica | matched |
| --- | --- | --- | --- |
| Table style: horizontal rules only, no vertical rules (`table_style`) | yes | not drawn | not assessed |
| TABLE 5 caption centred above the table | yes | not drawn | not assessed |
| Thick top rule above the legend | yes | not drawn | not assessed |
| Legend line IC50/EC50 Bins: +++ <= 2.0 < ++ <= 5.0 < + (card) | yes | not drawn | not assessed |
| Binned symbols +, ++, +++ (`activity_format`) | yes | not drawn | not assessed |
| Columns Compd. No., Binned EC50, Binned Max Efficacy, centred | yes | not drawn | not assessed |
| Top-level: Times serif labels, black only, no colour | yes | not drawn | not assessed |
| Legend line 2: PercentActivity Bins (not on card) | yes | not drawn | not assessed |
| Rule under the column header row (card names only the top rule) | yes | not drawn | not assessed |

The first seven rows are what the card claims for this figure type and its top-level conventions; the last two are visible in the crop and missing from the card. Matched: 0 of 7 claimed. Nothing was drawn, so every match cell reads "not assessed". The zero means no row was checked, not that a convention was tested and failed.

## Card notes (not changed)

- Legend: the crop has two legend lines, `IC50/EC50 Bins: +++ <= 2.0 < ++ <= 5.0 < +` and `PercentActivity Bins: + <= 25.0 < ++ <= 100.0 < +++`. The second line sets the bins for the Binned Max Efficacy column. The card's signature feature names only the first line.
- Rules: the crop shows a thick top rule, a further rule under the legend block, and a heavier rule under the column header row. The card names only the top rule.
- Table end: the crop stops after row 15 with no bottom rule visible, so the card cannot say whether the table has one.
- Caption: `TABLE 5` is not underlined. The top-level "scheme titles centred and underlined" rule applies to schemes, so it does not carry over to table captions.

## Differences from the paper

- The whole table is missing: caption, legends, rules, headers, the 15 rows and the binned symbols.
- No vertical rules or cell borders would need to be checked, since none are drawn.

## Tool gaps

- No text-only results table: a drawer for a caption, bin legend lines, horizontal rules, centred column headers and rows of binned symbols (`+`, `++`, `+++`) does not exist in the `draw_figure` kinds or in `publication_figure`.
- `publication_figure` SAR mode needs a structure for each row. A table of values with compound numbers only cannot be expressed.
- `draw_figure` with an empty species list takes the `chemdraw_com` lock before it returns, so a structure-free brief is not refused quickly. Here it ended in `resource_busy` after 295 s.
- `cdx.py build` could place this table by hand in principle: `text` centres column heads and symbols (Justification Center), and a solid `interaction` line with `clip_margin` 0 gives a horizontal rule. Not run here.
- Line weight: `interaction` and `box` take no width, and the document header sets `LineWidth` 0.6 for every object (`skill/chemdraw/scripts/acs_builder.py`). The reference needs a thick top rule, a lighter rule under the legend block and a thick header rule, which the builder cannot tell apart.
- No underline in text markup: `TOK` accepts only i, b, bi, sub and sup. Underlined titles (the card's scheme and method titles) need a separate line object.
- The card's `sar_table` conventions (`table_style`, `activity_format`) are guidance only: `APPLIED_FIGURE_CONVENTIONS` in `toolkit/cdxml_toolkit/publication/house_styles.py` covers only mechanism and catalytic_cycle, so no tool applies a table style.

## Replay

```
python skill/chemdraw/scripts/cdx.py py skill/chemdraw/assets/house-styles/uspto_patents/replica/uspto_patents-08/replay.py NEW_DIR
```

This draws nothing useful. It exists only so the folder layout matches the other replicas.

## Audit

Reviewed against reference.png (900 x 676) and the card. Nothing was drawn, so no row is matched. Corrected matched count: 0 of 7 claimed (0 of 9 rows), and every row is not assessed rather than failed.

The paper column holds up against the crop: horizontal rules only, a centred TABLE 5 caption that is not underlined, a thick rule under the caption, both legend lines as written, centred column heads, serif labels in black, 15 rows and no bottom rule.

Overclaims corrected above:
- The match column read "no", which reports a failed comparison that never happened.
- `draw_figure` has three kinds, not seven.
- `replay.py` does not repeat the lock wait, because it calls the function in-process.
- The running body text above the caption was left out.

Not verified: the 295 s wait and the other running `cdx.py draw` job. Nothing in this folder records them. The lock path is confirmed in code: `draw_figure` is in `CHEMDRAW_COM_TOOLS` (`toolkit/cdxml_toolkit/mcp_runtime/tool_registry.py`), so the worker takes the lock before the brief check refuses an empty species list. The `publication_figure` structure requirement is also confirmed (`toolkit/cdxml_toolkit/publication/data.py` rejects an empty or invalid structure).
