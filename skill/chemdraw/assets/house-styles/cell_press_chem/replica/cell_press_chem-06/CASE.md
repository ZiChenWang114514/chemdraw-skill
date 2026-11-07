# cell_press_chem, crop 06: Fig. 4B energy profile

Source: Smith et al., *Chem Catal.* 2025 (Photocatalysis as a mechanistic probe for the Staudinger beta-lactam synthesis). DOI 10.1016/j.checat.2025.101493. Licence CC BY 4.0 (from the card). Per the card's figure_sources note, this crop comes from the PMC author manuscript (NIHMS) and keeps the authors' artwork.

Figure type: `energy_profile` (panel B, "Energy profile and transition state (TS) representations"). Crop size 805 x 598 px.

## What is reproduced

Nothing is drawn. The crop has no molecular structures. The states are term-symbol species labels (3A, anti-3TS-I, 3TS-I, 3B, 3TS-II, 3C, MECP, 1C, 1TS-III, 1TS-IV, 1TS-V, syn-1D, 1A), plus the excitation labels 3Ir(III)* and 1Ir(III) on the energy-transfer (EnT) step. The 3D transition-state panel that the card attaches to this crop is not in the crop. No SMILES were written, since that would mean inventing structures.

`draw` has no energy-profile kind. The trial brief (`brief.json` in this folder: style `cell_press_chem`, kind `energy_profile`, four species labels, no steps) was refused by `cdx.py draw`:

- `kind 'energy_profile' is not available yet; only 'scheme', 'scope' and 'mechanism' can be drawn.`
- `Species 3A needs a smiles or a name.` (and the same for 3TS-I, 3B, 1A)
- `steps: give at least one step with substrates and products.`

The kind refusal is raised in `toolkit/cdxml_toolkit/mcp_runtime/figure_draw.py` (`_validate`), which accepts only the scheme kind. Changing the brief would not change that, so `rendered.png` was not produced. The run took 284 s, which the replicator attributed to lock contention with other `cdx.py draw` processes; that cannot be checked from this folder. `replay.py` is a copy of the jacs-au replay with the docstring changed. It was not re-run, because it calls the same `draw_figure` path.

What this run did not try is `compose_chemical_figure` (a manifest with explicit coordinates, documented in `references/publication-figures.md`). It can place lines, curves, rectangles, ellipses and rich-text labels. See "Tool gaps".

## Convention check against the crop

Card claims for `energy_profile` are 6 conventions plus 4 signature features (10 items). The replica column is "not drawn" for all of them, so the replica matches 0 of 10. The match column records whether the crop agrees with the card, checked against `reference.png` by pixel sampling and by eye.

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| `energy_unit` kcal/mol | y-axis title `G_rel (kcal mol-1)`; the card's note records the kcal mol-1 to kcal/mol mapping | not drawn | yes (notation differs) |
| `energy_label` delta_G | y-axis reads G with subscript rel (relative Gibbs energy), not delta G | not drawn | no, card error |
| `level_style` smooth_curve | black smooth curves join the level bars | not drawn | yes |
| `pathway_colors` #000000, #7A0000 | main path black; competing anti-3TS-I path dark red (curve core #720000 to #7C0000, consistent with #7A0000); the 1TS-IV and 1TS-V curves are pure blue #0000FE, a third colour the card does not list | not drawn | partial (card list incomplete) |
| `ts_marker` none | TS levels are blue bars with bold names; no brackets or double dagger. The same blue bars mark every level (3A, 3B, 1C, 1A), so the bar does not single out TS states | not drawn | yes |
| `intermediate_label_style` bold_letter | bold species names with superscript spin (3A, 1C, syn-1D); MECP is a red label, not a species name | not drawn | yes |
| signature: short blue #116FAF bars joined by smooth black curves, competing dark red curve | bars use #116FAF (38 pixels exact, antialiased range #0D6CAE to #1571B0); curves are smooth; the competing curve is dark red | not drawn | yes (the blue pathway in the row above is extra) |
| signature: bold name with energy in parentheses, e.g. 3B (-10.4) | present, unicode minus; MECP (-12.7) is the exception, a red label | not drawn | yes |
| signature: boxed plot with ticks on all sides | box with top and bottom edges (rows 40 and 591-592) and left and right edges (columns 90 and 793). Ticks sit outside the left edge every 2 kcal mol-1, longer at every 10; outside the right edge only at every 10; none on the top or bottom edge (pixel scan) | not drawn | no, card error |
| signature: 3D TS structures beside the plot on warm grey #F0EDE8 | no 3D structures in this crop; #F0EDE8 appears only as the EnT box fill | not drawn | no, card error (the crop does not contain them) |
| top level: bold panel letter "B" with plain-weight title | bold B, plain title "Energy profile and transition state (TS) representations" (the card's signature list cites crop 06 for this) | not drawn | yes |
| top level: sans-serif text | Arial-like text (by eye) | not drawn | yes (by eye) |
| top level: warm grey #F0EDE8 small step box | EnT box fill is exactly #F0EDE8 (the card's signature list cites crop 06 for this) | not drawn | yes |
| top level: dark red #780001 step names | EnT and MECP labels in dark red; the exact hex was not measured on the labels | not drawn | partial (hex not measured) |
| top level: italic stereo prefix | italic "anti" in anti-3TS-I (the card cites crops 01, 04, 05 for this, not 06) | not drawn | yes (by eye) |

Crop agreement with the card, for the 10 items: 6 agree outright (`energy_unit`, `level_style`, `ts_marker`, `intermediate_label_style`, the blue-bar signature, the bold-name signature), 1 agrees only in part (`pathway_colors`), and 3 disagree (`energy_label`, tick placement, 3D structures).

The top-level rows are not part of the 10-item count. They are recorded as checks on this crop, because the card's signature list cites crop 06 for the bold panel letter and the warm-grey box.

## Differences from the paper

The whole figure is missing from the replica. There is no plot, no axis, no level bars, no curves, no labels. The brief could only express species; the figure is an energy diagram.

## Tool gaps

Checked against the toolkit source (`toolkit/cdxml_toolkit/mcp_runtime/figure_tools.py`). `draw_figure` cannot draw this figure. `compose_chemical_figure` can, with explicit coordinates, so several gaps in the first draft are not gaps.

Real gaps:

- No energy-profile kind in `draw_figure` (see above). The card's `energy_profile` conventions (`energy_unit`, `energy_label`, `level_style`, `pathway_colors`, `ts_marker`, `intermediate_label_style`) are guidance only: `cdx.py styles` prints them and the draw result lists them as skipped. No tool applies them.
- No energy-to-page mapping layer. Nothing converts kcal/mol to page points, draws a frame and ticks from a range and step, places level bars at given energies, or builds a smooth curve through the sequence of levels. Every coordinate and Bezier control point would be computed by hand.
- Text cannot be rotated (text items take position, align, size, runs and colour only), so the vertical axis title `G_rel (kcal mol-1)` cannot be placed as drawn.
- Line, arrow and curve objects take the page LineWidth (root `LineWidth`, default 0.6). There is no per-object weight, so heavier level bars and lighter curves or leader lines cannot be set separately.
- No picture or image object in a manifest. The kinds are molecule, text, arrow/line, curve/electron_arrow, symbol, rectangle/ellipse/bracket, ts_bracket, orbital and interaction. The 3D conformer panel cannot be placed, and molecules are drawn in 2D only.
- A rectangle or ellipse takes one `color` for both outline and fill. A fill colour that differs from the outline cannot be set (not a problem for an unoutlined warm-grey box).

Items the first draft listed as missing that the manifest does have:

- Smooth connecting curve: `curve` item with four cubic Bezier points (`points`) and a colour.
- Level bar: `line` item with a colour, placed at a computed y.
- Second coloured pathway curve: any `curve` or `line` takes its own colour.
- Species label with bold name and parenthetical energy: `text` with `runs` (bold, italic, subscript, superscript, colour).
- Vertical excitation arrow with a two-line label and a small filled box: `line` with a style (dashed is available), `text`, and `rectangle` with `fill_type` solid.
- Filled dot marker (the MECP point on the 3C curve): `ellipse` with `fill_type` solid.
- Boxed frame: unfilled `rectangle`. Ticks: short `line` items. Numeric tick labels: `text`.
- Subscript in the axis title: a rich-text run with `subscript`.

## Audit

Checked by the auditor against `reference.png` (pixel sampling with numpy, plus visual inspection). No `rendered.png` exists, so only the reference was compared.

Overclaims corrected above:

1. `pathway_colors` was marked "yes". The crop uses a third colour, pure blue #0000FE, on the 1TS-IV and 1TS-V curves (66 exact pixels, x 608-654, y 253-271). The card lists only black and dark red, so the row is now partial. The dark red curve core (#720000 to #7C0000) is consistent with #7A0000.
2. The top-level rows were excluded as "not claimed for this figure type". The card's signature list cites crop 06 for the bold panel letter and the warm-grey box, so they are claims about this crop. Now checked: the EnT box fill is exactly #F0EDE8.
3. The boxed-plot description said ticks on the left and right edges only. That is right in substance but incomplete: the left edge has minor ticks every 2 kcal mol-1 as well as major ticks every 10, and the right edge has major ticks only. The "checked at 4x zoom" note could not be reproduced here; the check was a pixel scan of the frame.
4. The first draft's tool-gap list said there was no smooth-curve, level-bar, second-curve, species-label, excitation-arrow, filled-box or plot-frame primitive. These exist in `compose_chemical_figure` (see Tool gaps). The first draft did not try that route, so "no further brief tries" does not rule it out. The accurate statement is that `draw_figure` cannot draw an energy profile and no tool applies the card's energy conventions; a hand-built drawing with `compose_chemical_figure` is possible but was not attempted.
5. The species list omitted anti-3TS-I (9.8), which has a leader line to its bar. Corrected above.
6. The "card error" verdicts on `energy_label`, tick placement and 3D structures hold. The 3D panel is absent from the crop, so the card's attribution of it to this crop is wrong.
7. Not verifiable from this folder: the 284 s run time and the claim that about 120 other `cdx.py draw` processes held the lock. They are kept as reported and are not used in any table row.

Counts: replica 0 of 10 (nothing drawn). Crop against card: 6 agree outright, 1 partly, 3 disagree.
