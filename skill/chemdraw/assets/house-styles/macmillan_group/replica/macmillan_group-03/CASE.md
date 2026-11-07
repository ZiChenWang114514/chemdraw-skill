# MacMillan group, JACS 2026: gram-scale scheme (oxyalkylation of alkenes)

Source: MacMillan et al., *J. Am. Chem. Soc.* 2026, DOI [10.1021/jacs.6c03814](https://doi.org/10.1021/jacs.6c03814) (Oxyalkylation of alkenes via triple radical sorting). Licence: CC BY 4.0, reference crop reproduced under that licence.

Figure type: `reaction_scheme` (the "Gram-Scale Reaction" panel under the scope figure).

Drawing style: the `macmillan_group` house style (base preset `acs1996`), read from `toolkit/cdxml_toolkit/publication/house_styles/macmillan_group.json`. The card's `figure_types` object is empty, so the top-level conventions were used for this crop (see Differences).

## What is reproduced

The one-step gram-scale reaction at the bottom of the figure: N-Cbz-4-methylenepiperidine (4) with 2-methoxybenzoic acid and the N-acetoxyphthalimide reagent (printed as Me-CO2Phth) under Ir, light and Ni conditions, 4 mmol scale, giving 5.

| ID | SMILES (in `brief.json`) | How it was read |
| --- | --- | --- |
| 4 | `C=C1CCN(CC1)C(=O)OCc1ccccc1` | from the crop |
| ArCO2H | `COc1ccccc1C(=O)O` | from the crop, unlabelled |
| MeCO2Phth | `CC(=O)ON1C(=O)c2ccccc2C1=O` | printed as Me-CO2Phth; drawn as the full N-acyloxyphthalimide |
| 5 | `COc1ccccc1C(=O)OCC1(C)CCN(CC1)C(=O)OCc1ccccc1` | the crop shows Ar; 2-methoxyphenyl is assumed (see below) |

RDKit parses all four SMILES. The product formula is C23H27NO5 (MW 397.47). The scale check is 1.01 g / 397.5 g/mol = 2.54 mmol, which is 63.5% of 4 mmol and rounds to the printed 64%, so Ar = 2-methoxyphenyl is consistent with the figure.

Reproduced: the single step, the three substrates side by side with no plus sign, the catalyst line above the arrow (as text), the "4 mmol scale" line below, bold compound numbers, and the yield on the product label line.

Not reproduced: the "Gram-Scale Reaction" heading box, the grey rounded callout with "1.01 g", "64% yield" and "Reaction is readily scalable", the footnote mark b, the Ir, light-bulb and Ni icons, and the generic Ar label.

## Replay

`replay.py` runs `draw_figure` on `brief.json` with `CHEMDRAW_OFFLINE=1` and writes `figure.cdxml` and `validation.json` to a new folder. Compare the PNG with `reference.png`; `rendered.png` is the desktop ChemDraw render of the first (and only) brief run, downscaled to 1200 px wide.

```
python skill/chemdraw/scripts/cdx.py py skill/chemdraw/assets/house-styles/macmillan_group/replica/macmillan_group-03/replay.py NEW_DIR
```

Brief runs: one run with `--render` (report: `checks_passed` true, readback `matched`, 4 structures, native rendered, one balance warning). No second try was made. The remaining differences come from the card and the tools (icons, colours, callout box, label size), not from the brief, so a different brief could not close them.

## Convention check

Rows marked n/a are not claimed by the card for this crop (`conditions_split` is null and "not determined"; the italic descriptor is not in this crop).

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| `compound_label_face: bold` | 4 and 5 bold | 4 and 5 bold | yes |
| `compound_label_color: #000000` | black | black | yes |
| `yield_placement: after_product_label` and the yield signature line | yield in a grey rounded box beside the product, not on the label line | `5, 64% yield` on the label line | no |
| `yield_format` `{value}% yield`, `yield_separator` `", "` | `64% yield` with footnote b, inside the box | `64% yield` joined with `, ` | partial |
| `substrate_layout: inline_plus`, `show_plus_sign: false`, signature "substrates side by side with no plus sign" | three substrates in a row, no plus signs | same | yes |
| `abbreviate_groups` (Boc, Cbz, Me, Et, TMS, OMe) | Cbz, OMe, Me abbreviated | Cbz, OMe, Me abbreviated | yes |
| `aromatic_rings: kekule` | kekule benzene rings | kekule | yes |
| `new_bond_color: #0C549C` and signature "new bonds drawn in dark blue" | CH2-O bond dark blue; C-Me bond purple | both new bonds dark blue (#0C549C) | partial |
| `substrate_colors: null` | none | none | yes |
| `highlight_fill: null` (card: grey halo in crop 02 only) | grey halo behind the new C-CH2 bond | no halo | no |
| `reagent_text_color: #000000` | "4 mmol scale" in blue | black | no |
| `arrow_style: plain` | plain thin arrow | plain thin arrow | yes |
| signature "catalyst icons (PC, Ir, Ni discs, light bulb) on or before the arrow" | Ir, bulb and Ni icons on the arrow | text "Ir, light, Ni" above the arrow | partial |
| signature "italic descriptor text under starting materials" | none in this crop | none | n/a |
| `measured.bond_length_over_cap_height: 2.25` | about 2.2 (card px values) | 14.4 pt bond over about 7.2 pt Arial cap height = 2.0 | no |
| `measured.line_width_over_bond_length: 0.055` | about 0.06 (card px values) | 0.60 pt over 14.4 pt = 0.042 | no |
| `measured.arrow_length_over_bond_length: 5.2` | about 5.2 (card px values) | 72 pt over 14.4 pt = 5.0 (preset value, not the card's measurement) | no |
| `measured.label_font: Helvetica` | sans-serif, Helvetica-like | Arial (preset font); the card's font is not applied | no |

Counts: 17 claimed rows, 7 match (rows marked yes). The card's px values for this crop were not re-measured; they match the values the card gives for crop 02, which may be a copy.

## Differences from the paper

- Product Ar: the crop shows a generic Ar on the ester; the replica draws 2-methoxyphenyl with OMe, supported by the mass check above.
- Reagent: the paper prints Me-CO2Phth as text; the replica draws the full N-acetoxyphthalimide structure.
- Catalyst icons (Ir disc, light bulb, Ni disc) are replaced by the text "Ir, light, Ni".
- The "4 mmol scale" line is black; the paper prints it in blue.
- The methyl bond is dark blue; the paper colours it purple and the CH2-O bond dark blue.
- Yield: "5, 64% yield" sits on the label line; the paper has a grey rounded callout with 1.01 g, 64% yield (footnote b) and "Reaction is readily scalable". The callout is not drawn.
- No grey halo behind the new C-CH2 bond.
- No "Gram-Scale Reaction" heading box or rules.
- Labels are about 10 pt Arial on the acs1996 preset, so label size relative to the bond is about 2.0 against the card's 2.25, and the line weight (0.6 pt) is thinner than the card's measured 0.055 ratio (0.79 pt at this bond length).
- The step is reported as unbalanced by the tool (missing C9H5NO4, phthalimide plus CO2, from the N-acyloxyphthalimide). The paper draws no by-products, and nothing was added to the drawing.

## Tool gaps

- No catalyst icons or pictograms (disc, bulb) above or on the arrow; reagent lines are text only.
- `reagent_text_color` applies to all text; there is no per-line colour, so the blue scale line cannot be drawn.
- `new_bond_color` is one colour for every formed bond; a second colour for the methyl bond (purple) is not possible.
- No halo or highlight behind formed bonds (`highlight_fill` only fills the largest ring of the final product).
- No callout box, rounded grey box or footnote superscript on the product.
- No section heading box with rules for a scheme panel.
- No generic group label (Ar, R) in a product slot; a structure must be given, so the Ar label cannot be reproduced.
- No condensed reagent text (Me-CO2Phth) in a substrate slot; the abbreviation list has PhthN but no Phth ester form.
- Measured proportions are not applied: the card's `label_font` (Helvetica), `bond_length_over_cap_height` (2.25) and `line_width_over_bond_length` (0.055) are not set by the tool, which keeps the acs1996 Arial 10 pt labels and 0.6 pt lines.
- `conditions_split` `reagents_above_solvent_below` (catalysts above, scale below) is listed as not applied; the replica keeps the brief's own split.

## Audit

Checked against reference.png and rendered.png (reference is 775 by 196 px, so the card's px ratios cannot be checked from this file).

- Confirmed: bold 4 and 5, black labels, inline substrates with no plus sign, Cbz/OMe/Me abbreviations, kekule rings on 2-methoxybenzoic acid, black substrates, plain arrow.
- Corrected: `label_font` and `arrow_length_over_bond_length` were marked matched but are not. The label font is the preset Arial, and the replica's own gap list says the card's font is not applied. The 5.0 arrow ratio comes from the preset, not the card's 5.2, and the card's crop 03 px values are copies of crop 02.
- Count corrected from 9 to 7 of 17.
- Not verifiable from the folder: validation.json and the figure.cdxml output of the one run are not present, so the "checks_passed" and "matched" report is unconfirmed.
- Product: the paper draws a generic Ar on the ester; the replica draws a 2-methoxyphenyl ester. The mass check (1.01 g, 64%) fits that choice but does not confirm the source's Ar, so the replica adds a structure the crop does not show.
- Missed tool gaps: the condensed reagent "Me-CO2Phth" has a bond dash between Me and CO2 that no text slot can draw; the grey halo is an ellipse, not a rectangle highlight.
