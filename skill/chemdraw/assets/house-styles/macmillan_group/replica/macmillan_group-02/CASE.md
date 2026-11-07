# MacMillan group: oxyalkylation of a vinyl ether by triple radical sorting (top scheme of the scope figure)

Source: MacMillan et al., *J. Am. Chem. Soc.* **2026** (Oxyalkylation of alkenes via triple radical sorting). DOI: [10.1021/jacs.6c03814](https://doi.org/10.1021/jacs.6c03814). Licence: CC BY 4.0. The crop is `evidence/macmillan_group-02.png` (top scheme of the scope figure).

Drawing style: the `macmillan_group` house style (card in `toolkit/cdxml_toolkit/publication/house_styles/macmillan_group.json`, base preset `acs1996`). Figure type: `reaction_scheme`.

## What is reproduced

The overall three-component reaction at the top of the scope figure. Cyclohexyl vinyl ether (`C=COC1CCCCC1`), 2-methoxybenzoic acid (`COc1ccccc1C(=O)O`, benzoyloxy radical source) and the methyl radical source `CC(=O)ON1C(=O)c2ccccc2C1=O` (drawn in full as the N-acyloxyphthalimide) give the oxymethylated product `COc1ccccc1C(=O)OCC(C)OC1CCCCC1` (C17H24O4). The four condition lines sit around the plain arrow in the crop: Ni(acac)2, KTp* and Ir (1), BTTP above it; t-AmOH and 450 nm LEDs, 4h below it. The replica draws all four above the arrow (see the table). The product carries no number and no yield, as in the crop. The step balances only with CO2 and phthalimide (C9H5NO4) as by-products, which the paper also omits and the tool names but does not draw.

The scope rows (compounds 6 to 10, with bold numbers and yields) are not reproduced here. A scope panel takes only the base preset, so the house label and yield conventions cannot be tested through it.

## Iterations

- Try 1 (no decoration): all convention rows as in the table except the grey halo.
- Try 2 (chosen): adds `atom_halos` (grey, radius 9) on the three new-bond atoms of the product (indices 11, 12, 13). It is a stand-in for the grey band behind the new bonds, and its shape differs (see below). Files: `rendered.png` (downscaled from the 1897 px native render to 1200 px wide), `brief.json`.

## Replay

```
python skill/chemdraw/scripts/cdx.py py skill/chemdraw/assets/house-styles/macmillan_group/replica/macmillan_group-02/replay.py NEW_DIR
python skill/chemdraw/scripts/cdx.py render NEW_DIR/figure.cdxml
```

## Convention check

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| substrates side by side, no plus sign (`inline_plus`, `show_plus_sign` false) | three reagents side by side, no plus | same | yes |
| new bonds dark blue (`new_bond_color` #0C549C) | the benzoyloxy-derived C-O bond is blue; the methyl-derived C-Me bond is purple (sampled from the crop, pixels near RGB 80,64,128) | both new bonds blue (CDXML colour #0C549C) | partial: C-Me colour differs |
| reagent text black (`reagent_text_color`) | conditions black | black | yes |
| plain arrow (`arrow_style` plain) | plain arrow | plain arrow | yes |
| kekule aromatic rings (`aromatic_rings` kekule) | alternating double bonds | same | yes |
| abbreviated groups OMe and Me (`abbreviate_groups`) | OMe on the ring, Me on the acyl and the side chain | same | yes |
| arrow length about 5.2 x bond length (`arrow_length_over_bond_length`; the card value is never read by the tool) | 106 px arrow over about 18 px bond (cyclohexane ring in the crop), about 6; the card's 5.2 and the 105 / 20 px note are not reproduced by this file | 212 px arrow over about 38 px bond = 5.6 (ACS preset geometry) | no |
| conditions split (`conditions_split` null in card) | two lines above the arrow (Ni(acac)2, KTp*; Ir (1), BTTP) and two below (t-AmOH; 450 nm LEDs, 4h) | all four lines above; the arrow sits about 2 px under "4h" at 1200 px width | no |
| grey halo behind new bonds (`highlight_fill` null; card notes a halo in crop 02) | grey band along the new bonds, also covering the C1-C2 bond | three grey round discs on the new-bond atoms | partial: shape differs |
| label font Helvetica (`label_font`; the card value is never read by the tool) | sans-serif labels | Arial from the acs1996 preset | no |
| bond / cap height 2.25 (`bond_length_over_cap_height`; the card value is never read by the tool) | not measured in the first draft; by pixel check about 2.0 to 2.2 | replica "O" label 18 px tall over a bond of about 38 px, about 2.1; the earlier "about 2.0" was an estimate, not a measurement | no (unverified) |
| line width 0.055 x bond length (`line_width_over_bond_length`; the card value is never read by the tool) | card value gives about 0.79 pt at a 14.4 pt bond | 0.60 pt (acs1996 preset), 0.042 x bond length | no |
| italic descriptor under each starting material ("alkene nucleophile", blue "benzoyloxy radical source", purple "methyl radical source") | present | absent | no |
| bold italic product caption ("oxymethylated product") | present | absent | no |
| "via triple radical sorting" box and radical intermediate with light-blue and purple curved arrows | present | absent | no |
| "Phth" abbreviation of the phthalimidyl ester | "Me-CO2Phth" | full phthalimide drawn | no |
| missing by-products not drawn (CO2, phthalimide) | not drawn | not drawn; step warning kept | yes |
| product orientation (cyclohexyl ether on the left, 2-methoxybenzoate on the right) | cyclohexyl ether left, aryl ester right | mirror image: 2-methoxybenzoate left, cyclohexyl ether right | no |

Counted rows: 18 visible conventions, 6 matched, 2 partial, 10 not reproduced. Rows that are not in this crop (compound label face, compound label colour, yield placement, catalyst icons) are not counted; the scope rows would test them.

## Differences from the paper

- The italic descriptors under the three starting materials and the bold italic product caption are not drawn.
- The radical-sorting box, the intermediate and the curved arrows of the mechanistic inset are not drawn; the scheme shows only the overall reaction.
- The grey halo is a set of round discs on the three atoms of the new bonds, not a band along the bonds.
- The line weight is thinner than the paper (0.60 pt against about 0.8 pt by the card value).
- Two condition lines belong below the arrow in the crop (t-AmOH; 450 nm LEDs, 4h). The replica draws all four above.
- The arrow spacing is wrong. In the crop the gap between the arrow and the text is about 7 to 8 px at a bond of about 18 px (about 0.4 bond length). In the replica the arrow sits about 2 px under "4h" at a bond of about 38 px (about 0.05 bond length). It does not touch the text, but it is much closer than in the crop.
- The C-Me bond of the product is purple in the crop and blue in the replica.
- The bold 1 in "Ir (1)" is not drawn; condition lines are plain text.
- The product is drawn as a mirror image of the crop: the crop has the cyclohexyl ether on the left and the aryl ester on the right.
- The methyl radical source is drawn as the full N-acyloxyphthalimide, not with the Phth abbreviation.
- The scope rows (compounds 6 to 10) are not reproduced.

## Tool gaps

Checked against the toolkit source (`cdxml_toolkit/mcp_runtime/figure_draw.py`, `figure_house.py`, `figure_tools.py`, `publication/house_styles.py`) and the card.

- The card's `measured` block (`bond_length_over_cap_height`, `line_width_over_bond_length`, `label_font`, `arrow_length_over_bond_length`) is stored but no drawing code reads it. The report neither applies these values nor lists them as skipped. Every house style therefore draws with its base preset (acs1996: 14.4 pt bond, 0.6 pt line, Arial labels, preset arrow geometry).
- No per-structure caption field. The only per-structure text slot is `species.label`, which the renderer treats as the compound-number label. In a house-styled scheme `compound_label_face` forces that text to bold, so a descriptor placed there would come out bold, not italic. `substrate_colors` is null on this card, so descriptors cannot be coloured per structure either.
- Condition lines (`above`, `below`) are plain strings. Bold and italic runs are not supported in a scheme; run formatting exists only in the free-text tool. So "Ir (1)" with a bold 1 cannot be drawn.
- No gap control between the condition block and the arrow. Arrow length cannot be set either: the brief has no arrow-length field and the card value is not read.
- `new_bond_color` is one colour for every formed bond. The crop colours bonds by source (benzoyloxy-derived C-O blue, methyl-derived C-C purple); this cannot be expressed.
- No orientation control. The brief has no field for the left-right order of a product, so the layout engine placed the aryl ester on the left.
- `highlight_fill` fills the largest ring of the final product. It cannot make a band behind bonds that form in a step.
- `atom_halos` draws round discs of a fixed radius only.
- Not a tool gap, but an error in the replica: the brief's `below` field can carry the two lower condition lines, and the replica put all four in `above`. The card's `conditions_split` note ("crop 02 puts all conditions above the arrow") does not match reference.png, which shows two above and two below. The card was not edited.
- The abbreviation list has `PhthN` but not the N-O ester form, so the phthalimidyl ester cannot be abbreviated.
- A mechanistic inset (box, radical intermediate, curved arrows in two colours) cannot be placed inside a scheme brief. A `mechanism` brief takes only the base preset for its house style, so the card's curved-arrow colours are not applied to a figure like this one.
- No `figure_types` block exists for this slug, so the `reaction_scheme` conventions cannot be read from the card. The applied conventions come from the top-level section only.

## Audit

Re-checked against reference.png (775 px wide), rendered.png (1200 px wide), the card and the toolkit source. Corrections to the first draft:

- The C-Me new bond is purple in the crop. The first draft called it blue.
- The crop splits the conditions two above and two below. The first draft's "four lines above" and "all conditions above" were wrong, so the replica's all-above layout is a mismatch, not a partial match.
- The arrow length is 5.6 in the replica against about 6 in the crop by pixel check (106 px over about 18 px). The card's 5.2 is never read by the tool, so "yes (approx.)" is not supported.
- The arrow does not touch "4h" in the replica (about 2 px gap). The defect is the spacing, which is much tighter than in the crop.
- The label font and line width rows: the card values are never read, so the preset Arial and 0.60 pt are what the tool draws. The font row is no, not partial.
- The "about 2.0" label ratio was an estimate. The pixel check gives about 2.1 for the replica, so the row is unverified, not matched.
- The product orientation is mirrored. This was not in the first draft.
- The tool-gap list understated the measured-block gap (no code reads it) and the caption gap (the species label exists but is forced bold). Both are corrected above.

Corrected count: 6 of 18 conventions matched (the first draft said 8 of 17).

Pixel measurements (for reproduction): reference.png has the arrow shaft at rows 46-47, x 253 to 358 (106 px). Its condition text rows are 16-25 and 29-38 above the arrow, and 55-63 and 68-77 below it. The cyclohexane ring gives a bond of about 17 to 18 px. rendered.png has the arrow at row 135, x 635 to 846 (212 px). The "4h" text ends at row 132. The cyclohexane ring gives a bond of about 38 px. The card's evidence numbers (bond 20 px, arrow 105 px) do not match the 18 px bond measured here, so they should be re-checked against the source crop.
