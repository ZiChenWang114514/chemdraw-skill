# Dalton Transactions: ligand and Ru(II) complex synthesis (Scheme 1, one R entry)

Source: Albrecht et al., "Ligand modification for tuning activity and selectivity in chemoselective transfer hydrogenation", *Dalton Trans.* **2025**. DOI: [10.1039/d5dt01348h](https://doi.org/10.1039/d5dt01348h). Licence: CC BY 3.0, reference crop reproduced under that licence.

House style: `dalton_transactions` (base preset `rsc`), see `cdx.py styles dalton_transactions`.

Figure type: `coordination_complex` and `reaction_scheme` (the card lists crop 06 under both).

## What is reproduced

The three-step route at the top of Scheme 1, for the R = Ph entry only (ligand 1a, pyridinium 2a, Ru complex 3a):

1. 4-(Boc-amino)pyridin-3-amine plus PhCOCl gives `1a`. Step conditions are not given in the crop and are not drawn.
2. `1a` plus MeOTf gives the N-methylpyridinium `2a`, 78% (counterion not drawn).
3. `2a` plus [RuCl2(cym)]2 gives the Ru(II) complex `3a`, 65% (PF6 salt).

Structures as SMILES in `brief.json`:

- SM: `CC(C)(C)OC(=O)Nc1ccncc1N`
- 1a: `CC(C)(C)OC(=O)Nc1ccncc1NC(=O)c1ccccc1`
- 2a: `C[n+]1ccc(N)c(NC(=O)c2ccccc2)c1`
- 3a: `Cc1ccc(C(C)C)cc1.[Ru]1[NH]c2cc[n+](C)cc2[N]1C(=O)c1ccccc1` (p-cymene written as a separate fragment, see below)

The variable R / Ar series (a to g), the substituent key box, the 2a to 2f and 3a to 3e yield columns and the anion labels (X = PF6 or OTf) are not drawn. The structures were read from the crop and checked against the stated compound names by hand; no OCSR run was needed.

## Replay

```
python skill/chemdraw/scripts/cdx.py py skill/chemdraw/assets/house-styles/dalton_transactions/replica/dalton_transactions-06/replay.py NEW_DIR
python skill/chemdraw/scripts/cdx.py render NEW_DIR/figure.cdxml
```

`rendered.png` is the third try (`figure-t3`, desktop ChemDraw, downscaled to 1200 px wide). `reference.png` is the crop.

## Tries

- Try 1 (`figure-t1`, max_width 504): cymene linked to Ru by a dative arrow (`->`) from the ring atom. Wrong: the crop has a plain line from the arene to Ru, not an arrow.
- Try 2 (`brief-v2.json`, `figure-t2`, max_width 900): same dative arrow, drawn on one row. Not kept.
- Try 3 (`brief-v3.json`, saved here as `brief.json`): cymene as a separate fragment, so the plain line is gone and the arene floats free of Ru. Labels are bold and the metal precursor sits above the arrow. The route wrapped to two rows.

Tries were capped at three. Remaining problems are listed below.

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| metal-ligand bonds as plain lines, never arrows (coordination_complex) | Ru-N bonds plain lines | Ru-N bonds plain lines | yes |
| arene bonded to the metal by one line to the ring (coordination_complex, crop 06) | one line from the cymene ring to Ru | cymene detached, no bond to Ru | no |
| cationic complex as a closing half bracket with counterion at upper right (coordination_complex, crop 06) | bracket with PF6 at upper right | no bracket, no PF6 | no |
| variable groups R and Ar in green #4C7A2C (reaction_scheme, crop 06) | R and Ar green | R = Ph, black | no |
| bold compound numbers with bold letters (top level, crop 06) | bold 1a, 2a, 3a | bold 1a, 2a, 3a | yes |
| substituent key in rounded grey-outlined box (top level, crop 06) | a to g box | not drawn | no |
| compound_label_color #000000 | black | black | yes |
| arrow_style plain | plain arrows | plain arrows | yes |
| reagent_text_color #000000 | black | black | yes |
| aromatic_rings kekule | pyridine rings kekule; p-cymene drawn with an inner delocalisation circle | p-cymene drawn kekule (pyridines kekule too) | no |
| conditions_split reagents above, solvent below | reagents above; nothing under any arrow (yields sit beside the product labels) | reagents above; yield text under each arrow | no |
| abbreviate_groups tBu | BocNH on the starting material and 1a; no tBu label in the crop | full O-tBu carbamate, tBu written out | no |

Matched 5 of 12 after audit (the first write claimed 8; see Audit). The metal and N colour rules are not claimed here: the card scopes them to other crops, and crop 06 shows Ru and N in black.

## Differences from the paper

- Layout: the paper draws the route in one row of four structures; the replica wraps the route to two rows.
- Arene: the paper draws the p-cymene ring as bonded to Ru by one line. The replica writes cymene as a separate fragment and does not bond it, so the complex is not what the paper draws.
- Counterion: the paper shows the cationic complex inside a bracket with PF6 at upper right. The replica has no bracket and no counterion.
- Yields: the paper shows yields as a column beside the bold labels (78%, 65% and the other entries). The replica puts one yield under each arrow.
- Variable groups: only R = Ph is drawn. No green R or Ar labels.
- Ring labels: alpha, beta, gamma and alpha' in red italics are not drawn.
- Overlap: in `2a` the NH2 label sits on top of the benzamide carbonyl O (lint overlap in the rendered PNG).
- Orientation: the paper draws the pyridinium with N-Me at the bottom; the replica draws N-Me at the right.
- Ligand NH and N-acyl donor: the paper binds Ru through NH and the N-acyl nitrogen; the replica draws the same two Ru-N bonds, but the Ru is drawn without its arene partner.

## Tool gaps

- No eta6-arene attachment in a brief: the η6 ring cannot be bonded to a metal by a single line. The brief species record has no field for a multi-attachment node, although `scheme-drawing.md` mentions one for organometallics (not tried in this run).
- No brackets and counterions for a cationic complex: there is no option to wrap a complex in a closing half bracket with a charge and counterion at upper right.
- No variable-group label: an R or Ar label that is coloured green (or any colour) and marks a series entry cannot be written into a brief species.
- No substituent key box: a rounded grey-outlined legend of a to g is not a brief option.
- Yield column: a per-product yield column beside the bold labels is not expressible; `yield` takes one value per step, placed under the arrow.
- Red italic ring-position labels (alpha, beta, gamma): no atom-label option for text beside specific ring atoms.
- Layout: a complex written as a dot-separated fragment makes the route wrap to two rows at `max_width` 504.

## Audit

Re-checked against `reference.png` (zoomed) and `rendered.png`, and against the toolkit code in `toolkit/cdxml_toolkit`. Three rows moved from yes to no, which leaves 5 of 12.

- Kekule row: the p-cymene ring in crop 06 has an inner delocalisation circle (zoomed). The replica draws it kekule. The pyridines are kekule in both.
- tBu row: crop 06 never writes tBu. The starting material and 1a both read BocNH / BocHN, so the paper abbreviates the whole Boc group. The paper column "tBuO carbamate" was wrong.
- Conditions row: crop 06 has no text under any arrow. The replica puts yield text under the arrows, a value the paper never places there, so the split is not reproduced.

Rows that still match: Ru-N bonds as plain lines, bold compound numbers, label colour #000000, plain arrows, reagent text #000000.

Corrections to the tool gaps above:

- Bracket: `ts_bracket` already draws a bracket pair with a custom superscript (`figure_draw.py`, fields superscript and bracket_type), so the top-right PF6 position exists. What is missing is a single closing half bracket. Whether `bracket_type` accepts a half-bracket value was not tested.
- Yield column: `yield_placement` set to `after_product_label` (or `after_product_label_parenthesised`) appends a plain run after the bold product label in `figure_house.py`, which is the crop's "2a 78%" form. The card sets `yield_placement` to null, so this is a card setting, not a tool gap.
- Boc: the abbreviation table in `publication/house_styles.py` has NHBoc (BocHN) and Boc entries that would give the crop's labels. The card lists only tBu, so this is a card setting, not a tool gap.
- Aromatic circle: `figure_house.py` skips `aromatic_rings=circle` ("rings are drawn as Kekule structures"). The setting is house-wide, so the cymene circle cannot be drawn while the pyridines stay kekule. This is a real gap.
- Variable-group colour: the card's `variation_color` is declared in `publication/house_styles.py`, but no drawing code reads it. The green R and Ar labels cannot come from the card either. This is a real gap.

Gaps the replicator missed (the `draw_figure` docstring lists no key for them):

- Arrow length per step: the step keys are substrates, products, above, below, yield, arrow and ts_bracket. Step 3 of the crop is about twice the length of steps 1 and 2 (about 91 px against 47 px in the crop). The replica's arrows are all equal.
- Label or atom nudge: no offset key, so the NH2 on 2a cannot be moved off the carbonyl O.
- Orientation: no per-structure orientation key. The crop's starting material has the ring N at the bottom; the replica's has it at top right.
