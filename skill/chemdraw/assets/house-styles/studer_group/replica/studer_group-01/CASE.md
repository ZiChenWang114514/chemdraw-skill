# Studer group: phosphine water activation (Fig. 2a, reaction scheme)

Source: Studer et al., *Nature* **2023**, Photocatalytic phosphine-mediated water activation for radical hydrogenation. DOI: [10.1038/s41586-023-06141-1](https://doi.org/10.1038/s41586-023-06141-1).

Licence: CC BY 4.0, reference crop reproduced under that licence.

Drawing style: the `studer_group` house style card (base preset `nature`), figure type `reaction_scheme`, crop `evidence/studer_group-01.png`.

## What is reproduced

The single reaction at the top of Fig. 2a: triphenylphosphine (PPh3) is converted into triphenylphosphine oxide with evolution of H2 under photocatalysis (PC1, 455 nm, water as the oxygen and hydrogen source). Conditions are copied from the crop: CH3CN (4.0 ml) with PC1 (2 mol%) above the arrow, H2O (0.15 ml), 455 nm (5 W) and 30 h below. The yield (42%) sits under the product, as in the crop. The crop has no compound labels, so none are drawn.

| ID | Structure (SMILES in brief.json) | Role |
| --- | --- | --- |
| PPh3 | `P(c1ccccc1)(c1ccccc1)c1ccccc1` | substrate, drawn with Ph abbreviations |
| OPPh3 | `O=P(c1ccccc1)(c1ccccc1)c1ccccc1` | product, 42% |
| H2 | `[H][H]` | gaseous by-product, drawn as a bond rather than as the formula |

The stereo wedges and hashes on the P-Ph bonds in the crop (a three-dimensional depiction of the phosphorus centre) are not drawn. The SMILES carry no stereo.

Brief: one version (`brief.json`). The replay was reported as checked with `cdx.py draw` and `--render` (layout linear, readback matched, native render done, checks_passed true). This folder has no `validation.json`, so those checks are not verified here. Water is named in the conditions text only, so the tool reports the step as unbalanced (missing H2O) and draws nothing for it; this is intended, because the crop writes water as a condition, not as a substrate.

## Replay

```
python skill/chemdraw/scripts/cdx.py py skill/chemdraw/assets/house-styles/studer_group/replica/studer_group-01/replay.py NEW_DIR
python skill/chemdraw/scripts/cdx.py render NEW_DIR/figure.cdxml
```

`replay.py` runs `draw_figure` on `brief.json` offline and writes `figure.cdxml` and `validation.json`. Compare `rendered.png` with `reference.png`.

## Convention check

Rows cover the conventions the card claims for `reaction_scheme` and the top-level conventions visible in this crop. Rows marked n/a are not visible in crop 01 and are left out of the count. The match column was re-checked in the Audit below; the first version of this table claimed 9 of 15.

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| yield_format `{value}%` | `42%` | `42%` | yes |
| yield_placement `after_product_label` | 42% under the unlabelled product | 42% under the unlabelled product, tool note "product has no label, yield drawn under it" (a fallback, not the card rule) | no (the rule itself is not exercised; see card errors) |
| conditions split (card: null) | CH3CN above, H2O, light and time below | same split, from the brief's own above and below lists; the card sets no split rule | yes (placement only) |
| abbreviate_groups Ph | Ph | Ph (6 groups contracted) | yes |
| new_bond_color (red) | no new bond in crop 01 (P=O bond is black) | no formed bond; the tool skipped the rule ("no formed bond could be mapped; bonds left black") | no (rule not applied, not tested) |
| reagent_text_color `#000000` | black | black | yes |
| arrow_style plain | plain solid arrow with filled head | plain solid arrow with filled head; head about 20 px long against about 13 px in the crop | yes (style only; head size differs) |
| show_plus_sign | `+` between product and H2 | `+` present | yes |
| line_width_over_bond_length 0.05 | 2 px line; bond length not measured on the crop (card value 42 px is cap height 17 px times 2.5) | 0.6 pt / 10.8 pt = 0.056 from tool numbers; 2 px line on the PNG | no (not confirmed from pixels) |
| label_font Helvetica | sans-serif, Helvetica | Arial (fonttable entry "Arial"; the nature base preset labels are Arial; the card's label_font is never read) | no |
| arrow_length_over_bond_length 6.9 | arrow 425 px, about 10 bond lengths on the PNG (bond about 40 px centre to centre, estimated) | arrow 123.8 pt, 11.5 bond lengths as reported by the tool; about 10 bond lengths on the PNG | no (the card value 6.9 is wrong; see card errors) |
| catalyst code PC1 bold in the conditions | **PC1**, bold | PC with subscript 1, not bold | no |
| gas evolution: `+ H2` followed by an upward arrow | `+ H2` and a plain upward arrow | `+ H-H` (bond drawn), no arrow | no |
| stereo wedges and hashes on P-Ph bonds | bold and hashed wedges | none | no |
| 0.5 mmol note under the substrate | present | absent | no |

Counts: matched 6, claimed 15 (rows marked yes or no; n/a rows excluded). The matched rows are yield_format, conditions split (placement only), abbreviate_groups Ph, reagent_text_color, arrow_style (style only), show_plus_sign. The n/a rows are: compound_label_face and compound_label_color (no label), bond_length_over_cap_height (bond length not measurable in crop 01), substrate_layout, aromatic_rings, substrate_colors, highlight_fill, variation_color, selectivity_format, and the reaction_scheme colour signature for a new X group in blue and transferred H in red (crop 01 has no new bond colour).

## Differences from the paper

- Catalyst code: the paper writes PC1 in bold; the tool writes PC with a subscript 1, because the subscript rule treats the code as a formula. Not bold.
- Gas evolution: the paper shows H2 as a formula with a plain upward arrow; the replica draws H-H as a bond with no arrow.
- Stereo: the paper's wedges and hashes on the P-Ph bonds are not drawn; the replica shows the phosphorus centre flat.
- Substrate and product geometry: in the paper the three P-Ph bonds point left-up (hashed), down (bold wedge) and right-down. The replica's P-Ph bonds point left, up-right and down-right, so the phosphorus centre is drawn at a different orientation even for the plain bonds. The brief has no coordinate input, so this is not controlled.
- Arrowhead: the paper's head is about 13 px long on a 2 px shaft; the replica head is about 20 px long on a 2 px shaft. The head proportion is larger in the replica.
- Scale note: "0.5 mmol" under the substrate is not drawn.
- Arrow: the replica arrow is not clearly longer than the crop arrow relative to the bond length. Pixel estimates give about 10 bond lengths in both (see Audit).
- Water: the paper has it only as a condition (H2O 0.15 ml); the replica does the same, so the step is reported as unbalanced by design.

## Tool gaps

Route note: the gaps below were written for the brief route (`draw_figure` on brief.json). The toolkit's manifest route (`compose_chemical_figure`) takes text objects with runs (bold, subscript), straight arrow objects with start and end points, and molecule objects with explicit `coordinates` and `bond_displays` (WedgeBegin, WedgedHashBegin and others). Gaps marked "brief route only" can be avoided by using the manifest route; the others are missing in both.

- Catalyst codes are subscripted (brief route only): `subscript_matches` in `toolkit/cdxml_toolkit/text_formatting.py` protects only a standalone capital letter plus digits, so "PC1" inside a condition line becomes PC with a subscript 1. The manifest route writes runs as given.
- No bold run inside condition text (brief route only). The manifest route text runs support bold.
- No gas-evolution arrow (brief route only). The manifest route can draw an arrow object with start and end points.
- H2 as a formula (brief route only). The brief draws H-H as a bond; the manifest route can print H with a subscript 2.
- No wedge or hash bond control (brief route only). The manifest route `bond_displays` supports WedgeBegin and WedgedHashBegin.
- No free-text note under a substrate (brief route only). The manifest route `text` object can place one.
- No way to declare a condition-line reagent as a stoichiometric participant, so the balance check reports the water as missing. Not checked for the manifest route.
- Arrow length is set by the width of the condition text (brief route only). The manifest arrow takes start and end points.
- Label font (missing in both routes for the house style): the card says Helvetica, but `figure_house.py` never reads `label_font`, and the nature base preset sets Arial. The brief route cannot set the house label font. The manifest route can override the font through `style.font`.
- Arrowhead size (missing in both): the arrow schema takes `start`, `end`, `style` and `color` only. No head length or width control.
- Substrate geometry on the brief route (missing there): SMILES only, no coordinates or bond angle input. The manifest route accepts coordinates.
- Yield for an unlabelled product (missing in both): the card's `yield_placement` is `after_product_label`, and `figure_house.step_yield` drops the under-arrow yield when the placement is not under_arrow. The under-product position comes from a fallback, not from a declared rule.

## Card errors (reported, card not changed)

- `arrow_length_over_bond_length` is 6.9. The crop gives about 10 bond lengths by pixels (425 px arrow over about 40 px centre-to-centre bond, the bond being an estimate from the card's cap height). The replica gives about 10 by pixels and 11.5 as reported by the tool. The card value 6.9 does not match this crop.
- `yield_placement` is `after_product_label`. It applies only when the product has a compound label. Crop 01 has no label and puts 42% under the structure; the card does not say this.
- `figure_types.reaction_scheme` lists the signature "new X group and its bond in blue, transferred H in red" and crop 01 among its crops. Crop 01 has no coloured bonds, so the colours come from crops 04 and 06 only.
- `conditions_split` is null. The earlier version of this note called this an error. It is deliberate: the card notes say crop 01 has CH3CN above and H2O, light and time below, but crop 06 has the reverse, so the card records "not determined". Not a card error.
- `label_font` is Helvetica in the card, but draw_figure gives Arial through the nature preset and never reads `label_font`. This is a card and tool mismatch.
- `measurements_px.bond_length` for crop 01 is null and `arrow_length` is 460 px in the card's evidence block; the PNG shows the arrow as 425 px (x 158 to 582 on the 900 px reference). The 460 px figure may come from a different scale; it is not checked.

## Audit

Second reader check against `reference.png` and `rendered.png`, using pixel measurements on the two PNGs. No ChemDraw run and no change to any file other than this one.

Overclaims found and corrected in the table above:

1. new_bond_color marked as matched. Crop 01 has no new bond, and the tool logged that the rule was skipped (figure_house.py, "no formed bond could be mapped; bonds left black"). Not matched.
2. label_font Helvetica marked as matched. The output font is Arial (figure_tools.py fonttable entry "Arial"; nature preset label Arial; figure_house.py does not read label_font). The replicator's own note says "Arial-like". Not matched.
3. line_width 0.05 marked as matched. The crop bond length is not measured (card `bond_length` null); the 42 px value is cap height times 2.5. On the PNGs the line is 2 px in both images, the crop bond is about 40 px and the replica bond about 50 px (centre to centre, estimated). That ratio is within the error of a 2 px line. Not confirmed.
4. "The arrow is about 15 percent longer" is not supported. Pixel estimates give about 10.6 bond lengths for the crop (425 px over about 40 px) and about 10 for the replica (504 px over about 50 px). The card value 6.9 is wrong; the replica is not clearly longer. The 11.5 figure cannot be checked from the PNG.
5. Conditions split was treated as a convention. The placement matches the crop, but the card value is null, so no house rule applied; the split is the brief's own input. Kept as a match with that caveat.
6. The earlier card error about conditions_split was wrong (see card errors).
7. The replay checks (checks_passed, readback, native render) are not verifiable here: no validation.json in this folder.
8. Tool gaps: the eight listed gaps were checked against the toolkit. Seven of them (catalyst subscript, bold run, gas arrow, H2 formula, wedge or hash, note, arrow length) hold only for the brief route; the manifest route can do all seven. The balance-check gap was not checked for the manifest route. The replicator's wording did not say which route was meant.
9. Substrate and product geometry (P-Ph bond angles, the hashed and wedged bonds), and the arrowhead proportion, differ from the crop and were not in the first table.

Corrected matched count: 6 of 15 (first version claimed 9).

Missed tool gaps, not in the replicator's list: label font not applied from the house card; no arrowhead size control; no coordinate or bond-angle control on the brief route; no declared rule for the yield under an unlabelled product.
