# ACS Chemical Biology: enzymatic C7 bromination and Suzuki-Miyaura coupling of a Trp peptide (Figure 4b, reaction part)

Source: Bridge et al., "Enzymatic bromination of native peptides for late-stage structural diversification via Suzuki-Miyaura coupling", *ACS Chem. Biol.* **2026**. DOI: [10.1021/acschembio.6c00269](https://doi.org/10.1021/acschembio.6c00269).

Licence: CC BY 4.0, © the authors 2026; reference crop reproduced under that licence (`reference.png`, copied from `evidence/acs_chem_biol-01.png`).

Drawing style: the `acs_chem_biol` house card (base preset ACS Document 1996). Figure type: `biomolecule` and `reaction_scheme` (the crop is listed under both).

## What is reproduced

The two-step reaction row of the figure: the 4V-catalysed bromination (24 h, r.t., 44%) and the Pd-catalysed Suzuki-Miyaura coupling with a 3-(trifluoromethyl)phenylboronic acid (45 °C, 4 h, 81%). The peptide is simplified to a single capped tryptophan residue, Ac-Trp-OMe, because `draw_figure` cannot draw a one-letter bead chain. The bromine and the aryl group are drawn as atoms, not as the coloured dots of the paper.

The paper's peptide is (RW)3 with the modified Trp at the right end. Structures were read from the crop by eye and checked with RDKit (formulae C14H16N2O3, C14H15BrN2O3, C7H6BF3O2 and C21H19F3N2O3); OCSR was not run. The bromine is on C7 (the position next to the indole NH, read from the position of the dot in the crop). The CF3 is on the meta position of the aryl ring.

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| aromatic rings drawn Kekulé (`aromatic_rings: kekule`) | benzene rings with alternating double bonds (inner bond lines visible on the indole and aryl rings at the crop's size) | Kekulé rings; the tool does not apply the card value, Kekulé is the preset default | yes |
| plain arrows (`arrow_style: plain`) | plain arrows | plain arrows; the preset default, the tool applies only `bold` | yes |
| reagent text black (`reagent_text_color`) | black | black; the preset default, the tool only logs `reagent_text_color=#000000` | yes |
| step 1 conditions: reagents above, time below | "10 µM 4V / 10 mM NaBr / cofactor regen. system" above, "24 h, r.t." below, yield under the product | same split as typed in the brief (the card's `conditions_split` is null, so the split is not a card convention), but the tool prints "24 h, rt" and puts "44%" in the same block below the arrow | no |
| step 2 conditions: all above | "Pd(OAc)2, DMG / 1:1 EtOH: H2O / 45°C, 4 h, 500 rpm" above | all above (placement only); the tool breaks "45 °C, 4 h, 500 rpm" onto two lines and the spacing follows the brief | yes (placement only) |
| enzyme or catalyst name above arrow, concentrations stacked (reaction_scheme) | 4V and NaBr stacked above the arrow, "cofactor regen. / system" wrapped | stacked above the arrow, "cofactor regen. system" on one line | yes (stacking only) |
| no numbered compound labels (compound_label_face null) | no labels in the crop | no labels | yes |
| yield under the product, "{value}% isolated yield" (reaction_scheme yield_format and yield_placement) | "44% isolated yield" and "81% isolated yield" under each product | "44%" and "81%" under the arrow; yield_format not applied (top-level value null, reaction_scheme figure_types ignored) | no |
| new substituent as a coloured dot, `variation_color` #D2107A (reaction_scheme) | grey-purple dot = Br, magenta dot = aryl | Br and aryl drawn as atoms in black | no |
| bead peptide, one-letter residues (biomolecule `peptide_style: one_letter`) | (RW)3 as grey R and cyan W beads | capped Trp drawn as a skeleton | no |
| Trp in cyan #7FD0D4, other residues light grey | cyan W, grey R | no beads | no |
| modified Trp carries a coloured dot (biomolecule) | grey dot on the indole ring | Br atom on the ring | no |
| step titles in italic over a thin grey rule above each arrow | "4V-catalyzed bromination", "Suzuki-Miyaura coupling" | not drawn | no |
| coloured dot defined in a key beside the arrow | "= Br" and "= aryl" key | not drawn | no |
| substrate concentration under the starting material | "1 mM" | not drawn | no |
| boronic acid drawn below the arrow | B(OH)2 reagent below the arrow, aryl dot on it | drawn as a left-hand substrate with "+" | no |
| arrow length over bond length (`arrow_length_over_bond_length` 4.2, measured on crop 05) | step arrows about 3 bond lengths (both arrows 37 px; bonds about 12 to 14 px at the 575 px crop width, read by eye) | 7.9 bond lengths (step 1) and 5.0 (step 2), from the replay CDXML | no |
| bond, line and bold widths (`line_width_over_bond_length` 0.05, `bold_width_over_bond_length` 0.18, measured on crop 05) | not measurable at the crop's resolution | LineWidth 0.60 pt on a 14.4 pt bond (0.042), BoldWidth 2 pt (0.14); the card's measured values are not read by the tool | no |
| label font Arial (`label_font` Arial or Helvetica) | sans-serif labels, consistent with Arial | Arial in the CDXML font table, LabelSize 10 pt (the size itself is not checked against the crop) | yes |
| abbreviations as printed in the crop | "r.t.", "EtOH: H2O", "45°C" | "rt" (the condition text is always normalised, so "r.t." becomes "rt"); the other spacing follows the brief | no |
| wrap of above-arrow condition lines | "cofactor regen." / "system" on two lines | one line; the tool breaks a line only in the automatic re-layout, at a comma | no |
| row fits `max_width` (480 pt budget) | not applicable | 502 pt on replay (505 pt in the replicator's run); `checks_passed` false | no |

Matched 6 of the 16 conventions in the replicator's own table (rows 1 to 3, 5 to 7; row 4 is refuted). The earlier "7 of 18" is not supported: the table has 16 rows and the text counted 11 misses, which does not add up. The rows added in the audit (rows 17 to 22) bring the table to 22 rows with 7 matches; the only new match is the label font. The misses in the original table are the yield placement and format, the coloured-dot substituents (Br and aryl), the peptide beads and their colours (two rows), the modified-Trp dot, the step titles and grey rules, the key, the substrate concentration, the reagent position, and the one-line split of step 1. Each miss is a tool gap listed below, except the yield format, which the tool skips because the card gives no top-level value.

## Replay

```
python skill/chemdraw/scripts/cdx.py py skill/chemdraw/assets/house-styles/acs_chem_biol/replica/acs_chem_biol-01/replay.py NEW_DIR
python skill/chemdraw/scripts/cdx.py render NEW_DIR/figure.cdxml
```

`replay.py` runs `draw_figure` on `brief.json` without network access and writes `figure.cdxml` and `validation.json`. `rendered.png` is the desktop ChemDraw render of the second brief try, downscaled to 1200 px wide. The case folder holds neither `figure.cdxml` nor `validation.json`; they exist only in the output folder of a replay.

## Brief tries

Try 1 used `max_width` 504 and "24 h, rt". The row came out 505 pt wide and the lint check failed. Try 2 (the saved brief) used `max_width` 480 and "24 h, r.t.", which the tool prints as "24 h, rt". The replicator's run reports 505 pt for try 2; a fresh replay of the saved brief gives 502 pt (529 pt before the one automatic re-layout). Either way the row is over the 480 pt budget. Both tries are readback-matched with five structures. Native drawing is on file only for try 2 (`rendered.png`); the replay itself runs without ChemDraw and reports native status `not_run`, and no native check of try 1 is in the folder. `checks_passed` is false in both: the width check fails because the three-structure Suzuki row cannot be narrowed by `max_width`. Changing the brief further would only alter the row budget, not the row content, so the replica stops at two tries.

## Differences from the paper

- The peptide is a single capped Trp (Ac-Trp-OMe), not the (RW)3 bead chain, and the bead colours are absent.
- The bromine and the 3-CF3-phenyl are drawn as atoms in black, not as grey-purple and magenta dots.
- Yields sit under the arrow as plain "44%" and "81%", not as "44% isolated yield" under each product.
- The step titles (italic, over grey rules) are absent.
- The boronic acid is drawn as a left-hand substrate with "+", not below the arrow.
- The "1 mM" substrate concentration is absent.
- The step arrows are longer than the crop's: about 7.9 and 5.0 bond lengths against about 3 in the crop.
- The crop is cut at both edges, so the left-hand fragment of another panel and the right edge of the last product are not reproduced.
- The tool prints "rt" for the crop's "r.t." (both tries), so the time spelling differs.
- "cofactor regen. system" is one line here and wraps to two lines in the crop.
- The arrow of the second step sits directly under the "500 rpm" line instead of clear of it.

## Tool gaps

- No bead or one-letter peptide renderer: a peptide has to be given as a full SMILES, so the chain cannot be drawn as beads with coloured residues.
- No substituent as a coloured dot, and no key that defines a dot beside an arrow. The crop's key also draws a wavy bond to the aryl ring, and the Trp chain ends in a small filled square (an attachment point); the tool has neither.
- No yield placement under an unnumbered product (`under_product_label` needs a compound number).
- No step title in italic over a thin grey rule above an arrow.
- No reagent drawn below the arrow as a structure; `below` takes text lines only.
- No substrate concentration label under a starting material.
- `draw_figure` applies only the top-level card conventions, and the `figure_types` section only for catalytic cycles (`figure_draw._draw`). The reaction_scheme yield_format and variation_color are not listed in `style.skipped` at all; the report lists only null top-level keys, such as "yield_format: not specified by the card". They are dropped without a report.
- A three-structure row can exceed `max_width` and the re-layout does not fix it (502 pt on replay against 480 pt; 505 pt in the replicator's run); `checks_passed` stays false.
- The arrow length follows the widest condition line. The card's arrow ratio and its measured geometry (bond, line and bold widths) are not read by `figure_draw.py` or `figure_house.py`, and the report does not say so.
- The condition text is always normalised: `normalize_condition_text` (`text_formatting.py`) rewrites "r.t." to "rt". The rewrite is not recorded in the report, and no house-card switch for it was found.
- No line-break control for above-arrow text: a line stays whole unless the automatic re-layout breaks it at a comma, so the crop's wrap of "cofactor regen. system" cannot be drawn.
- The balance check names a missing Br (the bromine source, NaBr, is not in the brief) and lists BBrH2O2 as a missing Suzuki by-product. Both are reported, not drawn.

## Audit

Checked against `reference.png`, `rendered.png`, `brief.json`, the `acs_chem_biol` card, and a fresh replay of `brief.json` (no ChemDraw run).

- The "7 of 18" count is not supported. The table has 16 rows; 6 of them match, and the text's "11 misses" is wrong.
- Row 4 (step 1 split) is refuted. The split is typed in the brief, the card's `conditions_split` is null, and the printed text reads "rt".
- Rows 1 to 3 match the crop, but the tool applies none of them: Kekulé, plain arrows and black text are preset defaults, and the code only logs `reagent_text_color=#000000`.
- Row 5 and row 6 match placement only. Line breaks, the "rt" spelling and the wrap of "cofactor regen. system" differ from the crop.
- The tool-gap claim that `style.skipped` lists the reaction_scheme yield_format and variation_color is false. The replay's `style.skipped` lists only null top-level keys.
- The width is 502 pt on replay, not 505 pt. The width failure and `checks_passed` false are confirmed.
- "Draw natively" is not supported by anything in the folder: the replay reports native `not_run`, there is no native run for try 1, and the provenance of `rendered.png` was not checked.
- Proportions and line widths were missing from the original table. The step arrows are 5.0 and 7.9 bond lengths against about 3 in the crop, so the arrow row is a miss.
- Confirmed as stated: readback matches five structures; the step 1 yield is drawn below the arrow, not under the product; the beads, coloured dots, step titles, key, substrate concentration and reagent position are absent; the balance warnings name Br and BBrH2O2.

Corrected matched count: 6 of the 16 conventions in the replicator's table, and 7 of 22 rows once the audit rows are added.
