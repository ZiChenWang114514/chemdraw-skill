# houk_group-07: Scheme 4, row 1 (1,1-dimethylcyclohexane oxidation)

## Source

Galeotti, Houk, Bietti et al., "Radical and cationic pathways in C(sp3)-H bond oxygenation by dioxiranes", *J. Am. Chem. Soc.* **2023**. DOI: [10.1021/jacs.3c07163](https://doi.org/10.1021/jacs.3c07163). Scheme 4 (crop `evidence/houk_group-07.png`). Licence: CC BY 4.0, from the `houk_group` card.

Style: the `houk_group` house style (`style: "houk_group"` in `brief.json`), reaction_scheme figure type, base preset `acs1996`.

## What is reproduced

Only the first row of Scheme 4: 1,1-dimethylcyclohexane (S6) with the two-step conditions (1. 3-ethyl-3-(trifluoromethyl)dioxirane, 48 h; 2. H2CrO4, acetone) giving three ketones, P6-O, P6-O3 and P6-O4, drawn inline with plus signs.

Not reproduced: rows 2 and 3 (S7 and S8, with P7b-OH, P8a-OH and P8b-OH), the % conv. values, the % yield rows, the ring locant numbers, and the dashed panel rules. The dioxirane is given as text, not as a structure.

SMILES checked with RDKit: `CC1(C)CCCCC1` (S6), `CC1(C)CCCCC1=O` (P6-O, 2,2-dimethylcyclohexan-1-one), `CC1(C)CCCC(=O)C1` (P6-O3, 3,3-dimethylcyclohexan-1-one), `CC1(C)CCC(=O)CC1` (P6-O4, 4,4-dimethylcyclohexan-1-one). The structures were read from the crop by hand, not by OCSR.

## Replay

```
python skill/chemdraw/scripts/cdx.py py skill/chemdraw/assets/house-styles/houk_group/replica/houk_group-07/replay.py NEW_DIR
python skill/chemdraw/scripts/cdx.py render NEW_DIR/figure.cdxml
```

`replay.py` runs `draw_figure` on `brief.json` offline and writes `figure.cdxml` and `validation.json`.

## Attempts

| try | brief change | result |
| --- | --- | --- |
| 1 | as in `brief.json` (max_width 504) | drawn and native render done (lint and balance output not kept in this folder); `rendered.png` is this run |
| 2 | max_width 380 (to shorten the arrow) | `draw_figure` stopped by the tool timeout (300 s) while ChemDraw was busy with other draws; no file written |
| 2, retry | same | still queued after about 20 minutes of waiting; the run was stopped, no file written |

The try-2 change was not evaluated. The arrow length is set by the row layout, and narrowing `max_width` was not confirmed to shorten it.

## Convention check

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| compound_label_face bold | bold labels (S6, P6-O, P6-O3, P6-O4) | bold labels | yes |
| compound_label_color #000000 | black | black | yes |
| compound_label_italic_suffix false | no italic suffix | none | yes |
| substrate_layout inline_plus, show_plus_sign | single substrate, products joined by plus signs | products joined by plus signs | yes |
| arrow_style plain | plain solid arrow | plain solid arrow | yes |
| reagent_text_color #000000 | black reagent text | black text | yes |
| arrow length about 6.2 bond lengths (card measurement) | 175 px / 28 px = 6.25 | 193 pt / 14.4 pt = 13.4 (arrow stretched to the row width) | no |
| abbreviate_groups CF3 (dioxirane) | CF3 drawn as an abbreviation in the dioxirane structure | spelled out as "trifluoromethyl" in text | no |
| abbreviate_groups tBu | not in this row | not applicable | n/a |
| aromatic_rings kekule | no aromatic rings | none | n/a |
| new_bond_color / variation_color #FF0000 (new carbonyl O red) | new oxygen red | oxygen black | no |
| reaction time in green #18A800 | "48 hours" green | "48 h" black | no |
| bold step numbers "1." and "2." | bold | plain | no |
| conditions split: step 1 above, step 2 below | step 1 (dioxirane, 48 hours) above, step 2 (H2CrO4, acetone) below | step 1 text and "48 h" above, step 2 text below | no (placement matches; the dioxirane is text and the time reads "48 h" in black) |
| reagent drawn as a structure above the arrow | dioxirane structure | text "3-ethyl-3-(trifluoromethyl)dioxirane" | no |
| yield rows under products (% yield) | 14 / 21 / 11 under P6-O, P6-O3, P6-O4 | no yield row | no |
| % conv. in grey | 49 % conv. | absent | no |
| line width / bond length (card 0.09, measured on crop 01; crop 07 gives 0.07) | 2 / 28 = 0.07 | LineWidth 0.6 pt / 14.4 pt = 0.04 | no |
| bold width / bond length (card 0.22) | 6 / 28 = 0.21 | BoldWidth 2 pt / 14.4 pt = 0.14 | no |
| bond length over label cap height (card 2.4) | 28 / 11 = 2.5 | acs1996 bond 14.4 pt with label size 10 pt (cap height not measured on the render) | not checked |
| ring locant numbers on S6 | 2, 3, 4 | absent | no |
| dashed panel rules between rows | yes | not applicable to one row | n/a |

## Differences from the paper

- Only row 1 of the three-row scheme is drawn. The crop has three substrates and ten products.
- The dioxirane is text, not a structure above the arrow. Because of this the balance check reports that the reactants lack the oxidant (`steps[].missing`); nothing is added to the drawing.
- No yields and no conversion values are drawn, so the "% yield" row under the products is missing.
- The new carbonyl oxygen is black, not red; the reaction time is black, not green; the step numbers are plain, not bold.
- "48 hours" is written "48 h" because the renderer applies `normalize_condition_text` (toolkit `text_formatting.py`) to every condition line; the brief has no switch for it.
- The arrow is about twice as long relative to the bond length as in the paper (13.4 bond lengths against 6.2), because the tool stretches the arrow to fill the row.
- Line and bold widths are the acs1996 preset values, thinner than the card's measured ratios.
- No ring locant numbers on S6.

## Tool gaps

- A reagent drawn as a structure above or below an arrow: `steps[].above` and `below` accept text lines only. The oxidant is therefore reported as a missing reactant.
- Per-product yield rows and per-product conversion values under a multi-product step: a step takes one `yield` string, placed under the arrow or under one product.
- Colour of individual text runs (green reaction time, grey conversion) and of one atom in a product (red new oxygen). `variation_color` in the card is not applied by `draw_figure`.
- Bold step numbers "1." and "2." in the conditions.
- Ring locant numbers drawn on a substrate.
- A multi-row scheme with dashed rules between rows (rows wrap only by `max_width`).
- Arrow length as a fraction of bond length (the card measures 6.2; the tool fills the row).
- Measured line and bold widths from the card are not applied; only the base preset widths are.
- Balance check for a reagent given as text: the oxidant counts as a missing reactant.

## Notes on the render

`rendered.png` was downscaled from the native render (1934 x 280 px) to 1200 x 174 px to meet the size rule. `reference.png` is the evidence crop, unchanged.

## Audit

Checked 2026-11-07 by looking at `reference.png` and `rendered.png` directly, against the `houk_group` card (`toolkit/cdxml_toolkit/publication/house_styles/houk_group.json`).

**Corrected:**
- The conditions split row is now "no". Step 1 above and step 2 below match the paper, but the dioxirane is text, the time is "48 h" and black, and the paper column names a structure and "48 hours".
- Corrected count: 6 matched rows (label face, label colour, no italic suffix, inline plus layout, plain arrow, black reagent text). The earlier 7/17 included the conditions row. The table has 22 rows: 3 are n/a and 1 is not checked, leaving 18 applicable rows, so the denominator should read 6/18.
- The product count is ten (three from S6, four from S7, three from S8), not eight.
- Attempt 1 no longer says "checks passed". No `figure.cdxml` or `validation.json` is in this folder, so the balance claim (C16H26O3 reported missing) cannot be checked here.
- The "48 h" tidy-up is confirmed in code, and the note now names the function.

**Checked and held:** the four SMILES are valid and match the names (C8H16 for S6, C8H14O for the three ketones). The reference has bold labels, black labels and plus signs between products, and the replica matches.

**Not verifiable from this folder:** arrow length, line weight, label size and label-to-bond proportions. No measurement was made on either image, and the replica is a 1200 x 174 px downscale with no native file, so visual comparison is not reliable. The "1934 x 280 native" size is unverified.

**Card issues (outside this case, not edited):**
- The `reaction_scheme` note says "all above in crop 07", but the reference puts step 2 below the arrow.
- The `line_width_over_bond_length` 0.09 comes from crop 01 (9/105). Crop 07 gives 0.07.
- `variation_color` is listed for `reaction_scheme`, but `APPLIED_FIGURE_CONVENTIONS` (`publication/house_styles.py`) applies only `curved_arrow_color`, `curved_arrow_weight` and `cycle_arrow_color`.
- The card's `measured` block is not read by any drawing code.

**Tool gaps the replicator did not list:**
- Condition text is normalised by the renderer (`normalize_condition_text`: "48 hours" to "48 h", "RT" to "rt"), and nothing in the brief turns this off.
- `above` and `below` are plain string lists. There is no per-line bold, colour or run formatting, which covers the bold step numbers, green time and grey conversion together.
- `abbreviate_groups` acts only on species drawn from SMILES (`figure_house._abbreviate`). A text reagent keeps "trifluoromethyl", so CF3 cannot be abbreviated there.
- Per-step annotation rows (a left-hand "% yield" or "% conv." label with values aligned under each product) do not exist. A step takes one `yield` string.
- `new_bond_color` is null on this card, and it colours only bonds that map between drawn species. The new carbonyl oxygen comes from a text reagent, so it cannot be mapped.
- The 300 s timeout and the queue under ChemDraw lock contention were reported by the replicator. They were not checked here.
