# US 10,519,146 B2: Method 1, steps 5 to 8 (Lanman et al., Amgen)

Source: Lanman et al. (Amgen), US 10,519,146 B2, 2019 (KRAS G12C inhibitors and methods of using the same), Method 1, steps 5 to 8 (continued). Evidence crop: `evidence/uspto_patents-07.png` in the `uspto_patents` card.

Licence: public domain (US patent), as stated in the card.

Drawing style: the `uspto_patents` house style (`style` in `brief.json`; base preset `j_mol_mod`). The card's `reaction_scheme` section is the only figure-type section that applies here.

## Figure type

`reaction_scheme`: a linear route of generic structures with reagent text above each arrow and `Step n` below it, no yields, no colour.

## What is reproduced

The four steps shown in the crop as one generic route:

- Step 5: the 3-amino ring (NH2 at C3) to the LG core, "activating agent".
- Step 6: LG to the R4(PG) core, "R4(PG) reagent".
- Step 7: R4(PG) core to the R2(PG) core, "R2(PG) reagent, cross-coupling catalyst".
- Step 8: "(1) R4 deprotection, (2) acylating agent, (3) R2 deprotection" to the acylated final product.

Every generic group is a dummy atom in the SMILES (`*`), so `LG`, `R4(PG)` and `R2(PG)` are all drawn as `R`. The SMILES are in `brief.json` (`Nc1snc2cc(*)c(*)cc12` family, the ring written as a benzo-fused isothiazole with the two ring positions E drawn as plain carbon).

Not reproduced: the `-continued` header, the `R4(PG) = ...` and `R4(acyl) = ...` definitions at the foot of the crop (circle ring placeholders and wavy attachment lines), the `(acyl)` annotation on R4, the `Prot. group` labels, the ring letters E and X, and all superscripts and subscripts.

## Replay

```
python skill/chemdraw/scripts/cdx.py py skill/chemdraw/assets/house-styles/uspto_patents/replica/uspto_patents-07/replay.py NEW_DIR
python skill/chemdraw/scripts/cdx.py render NEW_DIR/figure.cdxml
```

`replay.py` runs `draw_figure` on `brief.json` offline and writes `figure.cdxml` and `validation.json`. `rendered.png` is the ChemDraw render of that brief (version 1, see below); `reference.png` is the crop.

## Attempts

1. `brief.json` (version 1): ring positions E as plain carbon, `max_width` 504. Rendered with ChemDraw. `checks_passed` true, readback matched 8 structures, no layout issues. This is the saved replica. The folder keeps no `figure.cdxml` or `validation.json`, so these check results are not verifiable from it (see Audit).
2. Ring positions E as dummy atoms (drawn as `R`), `max_width` 240. The drawing came out 302 pt wide against the 240 pt budget; the automatic relayout narrowed the row budget to 180 pt and it still failed (`too_wide`), so `checks_passed` is false. Not kept. The `R` labels on ring vertices also read as substituents, not as the crop's E positions.

The brief was not changed further: the remaining differences (intermediates repeated on every row, arrow length, label size, conditions split, superscripts, ring letters) are not controlled by the brief fields, so a third try would not have tested a brief change.

## Convention and signature check

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| yield_placement and yield_format null: no yields | no yields | no yields | yes |
| highlight_fill, variation_color and new_bond_color null: no colour | black only | black only | yes |
| black line art on a white page, no colour (signature feature 1) | black | black | yes |
| arrow_style plain | plain arrows, no bold | plain solid arrows | yes |
| reagent_text_color #000000 | black text | black text | yes |
| aromatic_rings kekule | alternating double bonds in the rings | alternating double bonds | yes |
| reagent class above and Step n below (reaction_scheme feature 3, second form) | "Step n" is below the arrow in all four steps, but the reagent words straddle the arrow in steps 5, 7 and 8: "activating" above and "agent" below (step 5); "R2 (PG) reagent," above and "cross-coupling catalyst" below (step 7); "(1) R4 deprotection" above and "(2)", "(3)" below (step 8). Only step 6 is entirely above. | every reagent line above the arrow and "Step n" below | no |
| underlined centred title (reaction_scheme feature 1) | plain, centred, not underlined "-continued" line; no scheme title | no title | no |
| generic intermediates with R groups and ring placeholders (reaction_scheme feature 2) | R groups and ring letters E and X on ring vertices | R on substituents; ring positions plain carbon (no letter) | no |
| final generic product labelled with a plain Roman numeral (reaction_scheme feature 3, first form) | no numeral on the final product | no numeral | yes (both absent) |
| variable groups as R with superscript numbers (top-level feature 4) | R2 and R4 with superscripts; LG and PG labels | R with no superscripts; "R4(PG) reagent" in plain text | no |
| ring placeholders as a loop or circle with the letter inside (top-level feature 4) | letters E and X on ring vertices; circles only in the definitions, not drawn | no letters on ring vertices | no |
| arrow_length_over_bond_length 4.0 | about 2.2 to 3.9 bond lengths (arrows 107, 161, 188 and 188 px against a bond of about 48 px centre to centre, measured in audit; the card's 62 px bond does not fit this crop) | about 5.4 to 8.4 bond lengths (296 to 462 px against a bond of about 55 px in rendered.png, measured in audit) | no |
| bond_length_over_cap_height 3.0 | about 3.2 (bond about 48 px, capital N about 15 px tall in evidence crop 07, measured in audit; the card's 62 px and 21 px do not fit this crop, but its ratio is near 3.0) | about 2.0 (bond about 55 px, capital N about 27 px tall in rendered.png, measured in audit; the earlier 2.2 was an estimate) | no |
| route layout: each intermediate drawn once, product starts the next row (snake layout, crop 06 note) | intermediate drawn once; arrow ends at the row edge and the next row starts with the product | intermediate drawn again at the start of each row | no |
| line_width_over_bond_length 0.047 | bonds about 3 px over about 48 px (about 0.06) in audit, which neither confirms nor refutes 0.047 at this threshold | 0.6 pt over 14.4 pt = 0.042 (not measured on rendered.png) | not checked |
| compound_label_face and compound_label_color | no compound labels in the crop | no labels | not checked (none to test) |

Matched 7 of 15 claimed rows after audit: rows 1 to 6 and row 10 (row 7 was refuted; row 10 was mis-marked). The two rows marked not checked are excluded from the count.

## Differences from the paper

- Labels: every generic group is `R`. `LG`, `PG`, `E`, `X`, the `(acyl)` annotation, `Prot. group`, and all superscripts and reagent subscripts are lost. The subscript in `NH2` survives because it is generated from the SMILES.
- Ring positions: the crop's E positions are drawn as plain carbon in version 1, which says CH at those positions. The crop does not say whether E is C or N. The attempt with dummy atoms there (version 2) prints `R` on the ring vertex instead, which reads as a substituent.
- Route layout: each step is a separate row and each row repeats its starting structure. The crop draws each intermediate once, with the arrow ending at the row edge and the product starting the next row.
- Arrows: about 5 to 8 bond lengths long, against about 2.2 to 3.9 in the crop (see row 13).
- Orientation: the replica turns the bicyclic core the other way. Its benzo ring is on the left with the `R` groups pointing left, and the isothiazole is on the right with `NH2` at the bottom right. The crop has the isothiazole on the left, `H2N` on top and the `X` groups on the right.
- Final product: the replica draws a carbonyl O on the 3-position substituent with `R` on the carbon. The crop shows only the `(acyl) R4` label on that bond, with no O drawn.
- Label order: the crop writes `H2N`; the replica writes `NH2`, which comes from the SMILES.
- Label size: in the replica the capital height is about 0.49 of the bond length; in the crop it is about 0.31 (measured in audit), so labels are about 1.6 times too large. Reagent text is set at the same 10 pt and is too large by the same ratio. The card's `atom_label_size_pt_estimate` (7.5 pt) is not applied.
- Conditions: in the crop, reagent text straddles the arrow in steps 5, 7 and 8 (see row 7); step 6 is above only. The replica puts every reagent line above the arrow and `Step n` below, so steps 5, 7 and 8 are split wrongly. In step 8 the crop has `(1)` above and `(2)`, `(3)` below; the replica has all three above.
- Omitted: the `-continued` header, the `R4(PG) =` and `R4(acyl) =` definitions, the `(acyl)` annotation, and the `Prot. group` labels.
- Not checked: atom balance. The tool cannot balance generic atoms, so each step carries a warning instead of a check.

## Tool gaps

- Generic labels: every dummy atom is drawn as `R`. There is no way to draw `E`, `X`, `LG`, `PG`, `A` or `L` on a ring vertex or substituent.
- Text: no superscript or subscript in reagent text or in free labels (`R4(PG)` is plain). Atom labels generated from SMILES do get a subscript (`NH2` in rendered.png).
- Balance: `draw_figure` returns `balanced: null` for every step of a generic scheme ("generic atoms (R groups, *) cannot be balanced"), so the route balance is not checked.
- Layout: the sequential layout repeats each intermediate on each row. There is no continuation layout in which the arrow ends at the row edge and the next row starts with the product. Narrowing `max_width` only wraps steps (version 2 still failed the width check).
- Arrow length: not a brief field and not applied by the house style (`style.applied` lists only `compound_label_face` and `reagent_text_color`). Arrow length in the output is set by the text width.
- Measured proportions: the card's `measured` values (bond/cap-height 3.0, arrow 4.0 bond lengths, bold width, line width) are not applied. A grep finds no code that reads the `measured` block in `figure_house.py` or `figure_draw.py`; only the base preset `j_mol_mod` is used (label 10 pt, bond 14.4 pt, line 0.6 pt).
- Orientation: no brief key sets the orientation of the fused core or the side that substituents point to. `BRIEF_KEYS` in `figure_draw.py` is `kind`, `species`, `steps`, `max_width`, `title`, `style` and `layout`.
- Text size: the only size control is the style preset. Reagent text and atom labels cannot be sized separately.
- Label order: a written order such as `H2N` cannot be chosen; a SMILES amine comes out as `NH2`.
- Unspecified ring atoms: the options are carbon or a dummy atom drawn as `R`, so the crop's `E` positions are forced to CH or to `R`.
- Conditions placement: all `above` lines go above the arrow and all `below` lines below it. A centred reagent block that straddles the arrow cannot be written.
- Definitions: no drawer for a block of `R = ...` definitions with circle ring placeholders, wavy attachment lines or the `(acyl)` annotation.
- Ring placeholders: a ring vertex cannot be marked with a letter (E, A, G1), a circle, or a wavy attachment bond.

## Audit

Checked against `reference.png` (same md5 as `evidence/uspto_patents-07.png`) and `rendered.png`, with pixel measurements on both. Evidence crop: bond about 48 px centre to centre, capital N about 15 px tall, arrows 107, 161, 188 and 188 px. Replica: bond about 55 px, capital N about 27 px, arrows 333, 296, 462 and 388 px.

Changes made in this audit:

- Row 7 changed from yes to no. Reagent words straddle the arrow in steps 5, 7 and 8, so "same form" does not hold.
- Row 10 changed from no to yes. The crop and the replica both have no product numeral.
- Rows 13 and 14 keep the "no" verdict, but their numbers now come from the crop's own pixels. The 62 px bond and 21 px cap height that the card gives for this crop do not reproduce; the card's bond-to-cap ratio of about 3 does.
- The "no superscript or subscript" tool gap was too broad. The `NH2` label in rendered.png gets an automatic subscript.
- Attempt 1 (`checks_passed`, readback of 8 structures, balance nulls) and attempt 2 (302 pt, `checks_passed` false) cannot be verified from this folder, which keeps no `figure.cdxml` or `validation.json`.
- Unlisted differences added: orientation of the core, the carbonyl O on the final product, and label order.
- The card's observation for crop 07 (`uspto_patents.json`, evidence entry for US 10,519,146 steps 5 to 8) says the (1) to (3) block sits above Step 8. In the crop, (2) and (3) are below the arrow.

Corrected count: 7 of 15 claimed rows (rows 1 to 6 and row 10).
