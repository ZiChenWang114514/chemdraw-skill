# MacMillan group: photoredox hydroarylation of unactivated alkenes (scope, entry 1)

Source: MacMillan et al., "A general photoredox platform for the hydroarylation of olefins", *J. Am. Chem. Soc.* **2026**. DOI: [10.1021/jacs.6c14333](https://doi.org/10.1021/jacs.6c14333). Licence: CC BY 4.0. The crop is the scope figure, unactivated alkenes rows (`evidence/macmillan_group-01.png`).

Drawing style: the `macmillan_group` house style (base preset ACS Document 1996). The card has no `figure_types` section, so only its top-level conventions apply.

Figure type: the brief asks for `reaction_scheme`. The crop is really a substrate-scope row: each entry is a pair of substrates joined by a light-blue double-headed link arrow, with the product number and yield below. The product is not drawn in the crop.

## What is reproduced

Entry 1 only: pent-4-en-1-ol and 2-bromobenzothiazole give the hydroarylation product `OCCCCCc1nc2ccccc2s1` (compound 1, 61% yield), drawn as a single step with a plain arrow. The product structure is not in the crop. It follows the regiochemistry the paper shows for entries 21-24 (aryl on the terminal carbon, H on the internal carbon).

Entries 2 (`C1=CC2CCC1C2` with `Brc1nc2ccccc2s1`, product `C1(c2nc3ccccc3s2)CC2CCC1C2`, 62%) and 4 (`C=C1CCC(=O)CC1`, product `O=C1CCC(Cc2nc3ccccc3s2)CC1`, 74%) were in the first brief, which draw_figure refused (see Tool gaps). They are not in the rendered replica.

The entry 1 SMILES were checked with RDKit: the alkene `OCCCC=C` (C5H10O), the bromide `Brc1nc2ccccc2s1` (C7H4BrNS) and the product `OCCCCCc1nc2ccccc2s1` (C12H15NOS). The product formula equals alkene + benzothiazolyl + H.

## Replay

```
python skill/chemdraw/scripts/cdx.py py skill/chemdraw/assets/house-styles/macmillan_group/replica/macmillan_group-01/replay.py NEW_DIR
python skill/chemdraw/scripts/cdx.py render NEW_DIR/figure.cdxml
```

`replay.py` redraws `brief.json` offline and writes `figure.cdxml` and `validation.json`. `rendered.png` is the desktop ChemDraw rendering from the draw call (downscaled to 1200 px wide). `reference.png` is the crop.

## Convention check

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| compound_label_face bold | bold `1` | bold `1` | yes |
| compound_label_color #000000 | black | black | yes |
| yield_placement after_product_label | `1, 61% yield` centred under the substrate pair (no product in crop) | `1, 61% yield` under the product | no |
| yield_format `{value}% yield` | `61% yield` with footnote `a` | `61% yield`, no footnote | yes (text only) |
| yield_separator `, ` | comma and space | comma and space | yes |
| substrate_layout inline_plus with show_plus_sign false | substrates side by side, no plus, joined by the light-blue link arrow | substrates side by side, no plus, no link arrow, black reaction arrow after them | no |
| aromatic_rings kekule | benzothiazole drawn with alternating double bonds | same | yes |
| new_bond_color #0C549C | no formed bond in crop 01 (the card notes read #0C2484 for crop 01) | new bond set to #0C549C in the CDXML colour table; style report lists it as applied | no (nothing in the crop to match) |
| arrow_style plain (product arrow) | no product arrow in crop | plain black arrow | no (an addition, not a match) |
| light-blue curved double-headed link arrow between substrates | present on every row | absent | no |
| italic descriptor under starting materials (`mono-substituted-alkene`) | present under entry 1, blue italic | absent | no |
| proportions: line width 0.055 of bond length, bond about 2.25 cap heights (card) | 2.5 px line, 46 px bond, 20 px cap in crop 01 | LineWidth 0.60 pt over BondLength 14.40 pt (0.042); Arial 10 pt, cap about 7.2 pt, bond about 2.0 cap heights | no |
| label font Helvetica (card) | Helvetica-like sans | Arial (font id 3, ACS constant); not applied from the card, not reported as skipped | no (visually close) |
| catalyst icons on or before the arrow | absent in crop 01 (present in the paper header) | absent | n/a (absent on both sides; not counted) |

Claimed 12, matched 9. Audit: 5 of 13 applicable rows hold (see Audit).

## Differences from the paper

- The crop has no product and no reaction arrow. The replica draws the product `OCCCCCc1nc2ccccc2s1` and a plain arrow. The product is inferred from the regiochemistry, not copied from a drawing of compound 1.
- The light-blue double-headed link arrow between the two substrates is not drawn.
- The italic descriptor `mono-substituted-alkene` is not drawn.
- The yield superscript `a` is not drawn.
- The catalyst icons in the paper's header are not drawn; the brief gives no conditions.
- Only entry 1 is drawn. Entries 2 and 4 were not rendered, and entry 3 (deuterium label) was not attempted.
- Bond length, line weight and label size were not tuned to the crop's proportions; the table gives the measured mismatch.
- The reaction is not atom-balanced as drawn (an H-atom donor and a bromide by-product are missing). draw_figure warns and adds nothing.

## Tool gaps

- draw_figure refuses several independent reactions in one brief ("not a linear route, a convergent route or a set of reactions from one starting material"), so a multi-entry row of substrate pairs cannot be drawn in one call.
- No glyph for a substrate pair joined by a light-blue curved double-headed arrow with no product.
- No catalyst icon glyphs (PC, Ir, Ni discs, light bulb); conditions are text only.
- No placement for italic descriptor text under the starting materials; the step `below` line goes under the arrow.
- The `scope` kind lays out product compounds with their values and cannot draw substrate pairs.
- The yield field has no footnote superscript (not tested).
- No atom-balance model for an H-atom source and a halide by-product; the tool only warns.

## Audit

Checked on 2026-11-07 against reference.png, rendered.png, CASE.md, brief.json and the card macmillan_group.json. A fresh offline replay of replay.py was run into a temporary folder (not into this folder) to read figure.cdxml and validation.json.

Overclaims in the table above:

- New-bond colour: crop 01 has no formed bond, so nothing in the paper was matched. The card notes read #0C2484 for crop 01, not #0C549C. The `#0C539C` "median of blue pixels" was not reproducible; the CDXML holds #0C549C, which the style report lists as applied. Not a match.
- Yield placement: in the crop the line sits centred under the substrate pair, and the replica puts it under the product. Not a match.
- Arrow style: the crop has no product arrow, so the replica's black arrow is an addition, not a match.
- Substrate layout: no plus sign is right, but the paper joins the pair with the light-blue link arrow and the replica has none.
- Yield format: the text matches; footnote `a` is missing.
- Catalyst icons: absent on both sides, so the row is not applicable. It had been marked "no".
- Kekule: the drawing is kekule (9 C=C bonds in the CDXML), but the style report neither applies nor skips aromatic_rings, so the card did not enforce it.
- Proportions and label font were not in the table. The card's `measured` values are stored by publication/house_styles.py but no drawing code reads them. LineWidth is 0.60 pt over BondLength 14.40 pt (0.042), against 2.5/46 = 0.054 in the crop. Arial 10 pt gives bond/cap about 2.0, against 46/20 = 2.3. The card says Helvetica; the drawing uses Arial.
- Not checked and not supported by the folder: "regiochemistry the paper shows for entries 21-24" (not in the crop); rendered.png as a desktop ChemDraw render (replay.py does not request native rendering, and an offline run reports native not_run); the #0C549C paper page.

Corrected count: 5 of 13 applicable rows hold (compound label face, compound label colour, yield format text, yield separator, kekule rings). The 13 are the 11 original rows without the catalyst icons row, plus the proportion and label-font rows. The replicator claimed 9 of 12.

Tool gaps the replicator did not list:

- A transferred H or D cannot be coloured blue. `_color_new_bonds` in toolkit/cdxml_toolkit/mcp_runtime/figure_house.py colours only formed heavy-atom bonds.
- The card's measured proportions and label font are not applied (figure_draw.py uses the preset LineWidth; constants.py fixes the label font and size).
- Scheme arrows have no colour and no curved link option. `arrow` takes solid, dashed, failed, reversible or resonance, and reversible is a straight black double arrow.
- Above and below text is a plain string with no italic or colour, so the blue italic descriptor cannot be styled even once a placement exists.
- The yield is a plain string, so footnote superscripts cannot be drawn.
- The brief gives one label string per species, so a regular-weight racemic prefix with a bold number (as in (±)-2 and (±)-6) has no way to be set.
- The card's grey rounded yield box (crop 03) has no field.
- Not a gap but missed: atom_halos (colour and radius) could draw the grey halo of crop 02.
