# wiley_angew-01: top reaction of Figure 3 (Angewandte 2024)

Source: Rowett, Sweeting, Heard and Lennox, *Angew. Chem. Int. Ed.* **2024**, *63*, e202400570. DOI: [10.1002/anie.202400570](https://doi.org/10.1002/anie.202400570).

Licence: CC BY 4.0, reference crop reproduced under that licence.

House style: `wiley_angew` card (base preset `wiley`). The card has no `figure_types` section, so the top-level conventions were used.

## What is reproduced

The reaction at the top of Figure 3 only: the methyl ketone **1** and the alcohol **2** give the ester **3** under I2 (3 equiv.), DBU (4 equiv.) in DCM (0.1 M) from 0 °C to rt over 16 h. The substrate scope below the line is not drawn.

The paper draws generic groups (a red circle on the ketone, a blue circle on the alcohol). The replica uses the R = NO2 case, which is product 3b in the scope (93%):

| ID | Structure (SMILES in brief.json) |
| --- | --- |
| 1 | `CC(=O)c1ccc(cc1)[N+](=O)[O-]` (4-nitroacetophenone) |
| 2 | `OCc1ccccc1` (benzyl alcohol) |
| 3 | `O=C(OCc1ccccc1)c1ccc(cc1)[N+](=O)[O-]` (benzyl 4-nitrobenzoate) |

All three SMILES were checked with RDKit (C8H7NO3, C7H8O, C14H11NO4). The yield is not drawn because the top reaction has none.

Brief: `brief.json` (style `wiley_angew`, one step, above = reagents, below = solvent and temperature, `max_width` 504). Render: `rendered.png` (native ChemDraw, try 1). Try 2 with `max_width` 378 gave an identical layout, so it is not kept.

## Replay

```
python skill/chemdraw/scripts/cdx.py py skill/chemdraw/assets/house-styles/wiley_angew/replica/wiley_angew-01/replay.py NEW_DIR
python skill/chemdraw/scripts/cdx.py render NEW_DIR/figure.cdxml
```

## Convention table

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| compound_label_face bold | bold 1, 2, 3 | bold 1, 2, 3 (CDXML face 1) | yes |
| compound_label_color #000000 | black | black | yes |
| conditions_split reagents above, solvent and temperature below | I2 and DBU above; DCM (0.1 M) and 0 °C to rt, 16 h below. Paper prints one line per side | same split, but each side wraps to two lines. The split is kept as the brief gives it (the card's split is not applied) | yes (split only) |
| substrate_layout inline_plus | 1 + 2 (2 carries "(1 equiv.)" in the paper) | 1 + 2 (no "(1 equiv.)") | yes (layout only) |
| aromatic_rings kekule | Kekule rings | Kekule rings | yes |
| new_bond_color null (black) | new C-O bond black | new C-O bond black, but every bond is black, so this row does not test the convention | yes (trivially) |
| arrow_style plain | grey arrow, shaft about 5 px at 300 dpi, head about 27 px wide, 360 px long (8.4 bond lengths) | black arrow, 0.60 pt shaft (about 1.5 px in the render), 100.6 pt long (5.9 bond lengths) | no |
| show_plus_sign true | plus present, light grey | plus present, black | no (colour) |
| label font Arial or Helvetica | humanist sans (Myriad-like letterforms), not Arial or Helvetica by eye | Arial (CDXML font 3) | no (the card's label_font is not read by any code, and the paper face is not confirmed) |
| abbreviate_groups null | NO2 and Me drawn as labels (crop 01 observations) | N(+)(=O)O(-) and bond-line Me | no |
| substrate_colors null | red ketone part, blue alcohol part | black | no |
| reagent_text_color #000000 | I2 in purple, rest black | all black | no (I2 colour) |

Matched: 6 of 12 (rows 1-6). Rows 7-12 do not match (6). The earlier count of 9 counted the partial rows 7, 8 and 9 as matches. Yield placement and highlight fill are not visible in the top reaction and are not counted.

## Differences from the paper

- Groups: the paper draws generic red and blue groups; the replica uses the 4-nitrophenyl and phenyl instances. The NO2 group is drawn as a charged N(+)(=O)O(-) rather than a label.
- Colour: the ketone fragment is red (#CB1C01) and the alcohol fragment blue (#031993) in the paper; the replica is all black. The I2 is purple in the paper and black in the replica.
- The paper's alcohol carries "(1 equiv.)" under the label `2`; the replica has only the bold label.
- Arrow and plus sign are grey in the paper and black in the replica. The replica arrow is also thinner (0.60 pt shaft against about 5 px in the paper) and shorter (5.9 bond lengths against 8.4).
- Bond weight: bonds carry no line width of their own and inherit the document default of 0.75 pt. With a 17 pt bond that is 0.044 of the bond length; the card measures 0.09 and the paper's bonds are 4 px on 43 px (0.093). The replica's lines are about half the paper's weight. Bond length against label cap height is about 2.0 in the replica (17 pt against a cap height of about 8.6 pt) and 2.05 in the paper (43 px against 21 px): close, but not a measured match.
- The paper's yield (93%, product 3b) is not in the top reaction, so none is drawn.
- Balance: the replica's step reports a missing CH4 on the product side. The ketone methyl leaves as the iodoform by-product (haloform-type cleavage), which the paper does not draw either. The tool names the gap and does not add it.

## Tool gaps

- No brief field sets colour on a species, a bond or a line of conditions text. Substrate colours and the purple I2 come only from the card (`substrate_colors`, `reagent_text_color`), and the card sets them to null or black. `ring_fills` and `atom_halos` exist, but they make fills and halos, not coloured bonds or text.
- `abbreviate_groups` comes only from the card (null here), so NO2 and Me labels cannot be requested per figure.
- No field for a note attached to one structure, such as "(1 equiv.)" under substrate `2`.
- No convention for a grey arrow or grey plus sign. The brief accepts only `solid`, `dashed`, `failed`, `reversible` and `resonance` for arrows. The card's `arrow_style` "plain" is not read by the code (only "bold" is), and it is dropped without a "skipped" entry.
- No field sets bond or line weight, arrow length, arrow shaft width or plus size. The card's measured proportions (`bond_length_over_cap_height`, `line_width_over_bond_length`, `arrow_length_over_bond_length`) are not read by any code path, so a house style cannot enforce them.
- No font field: the card's `label_font` is not read, and labels take the preset's Arial.
- The automatic re-layout breaks condition lines after a comma when the row is too wide (validation.json: "broke condition lines longer than 16 characters after a comma") and sets the arrow to the shorter line length. The brief's "I2 (3 equiv.), DBU (4 equiv.)" therefore wraps to two lines, and the arrow shrinks to 5.9 bond lengths. There is no way to keep a condition line whole or to set the arrow length.
- `max_width` does not force a narrower layout: the re-layout sets its own budget (378 pt here, from validation.json), so the replicator's max_width gap is a symptom of this re-layout.
- `conditions_split` is not applied: the code logs "the brief's above/below lines are kept as given", so the split depends on how the brief author writes it.
- The step balance check flags the iodoform by-product (CH4) with no way to mark it as intentionally omitted, so the warning stays.

## Structure notes

Structures are given by name in the paper (generic R), so OCSR was not run. The three SMILES are written from the scope product 3b and the scheme's connectivity.

## Audit

Checked against `reference.png` and `rendered.png` (both viewed and measured in pixels), a fresh replay of `brief.json` into a temporary folder (its `figure.cdxml` and `validation.json`; nothing was written to the case folder), and the card `wiley_angew.json`.

- Count: the earlier claim was 9 of 12, with the partial rows 7 and 8 and the font row 9 counted as matches. Corrected to 6 of 12 (rows 1-6).
- Row 3 (conditions split): the split holds, but the card's split is not applied by the tool and each side wraps to two lines where the paper prints one. Counted on the split only.
- Row 6 (new bond black): holds only trivially, since every bond is black.
- Row 7 (arrow): not matched. Grey against black; the paper's shaft is about 5 px at 300 dpi against 0.60 pt (about 1.5 px) in the replica; the paper's arrow is 360 px (8.4 bond lengths) against 100.6 pt (5.9 bond lengths); the head is smaller in the replica.
- Row 8 (plus): colour not matched (light grey against black).
- Row 9 (label font): not confirmed. The paper's letterforms look like a humanist sans, and no code reads the card's `label_font`.
- Unlisted proportions: bond weight is about half the paper's (see Differences). The "by eye similar in length" claim is withdrawn. Bond-to-cap-height is close (2.0 against 2.05) but was not measured on the replica.
- Card against paper: `abbreviate_groups` null, `substrate_colors` null and `reagent_text_color` #000000 are the card's own values, yet the card's observations for crop 01 record NO2, OMe and Me labels, red and blue fragments and a purple I2. The replica agrees with the card only because it is unstyled, so the three "no" rows measure replica against paper, and the card's values conflict with its own evidence. The card was not edited (outside this audit's scope).
- Tool gaps the replicator missed: the re-layout breaking condition lines and shortening the arrow; the card's measured proportions not being read by any code; the card's `arrow_style` "plain" and `label_font` silently ignored; `conditions_split` only logged as kept as given.
