# Chem. Eur. J. 2022: Au-catalysed oxy-arylation of an alkenol, Scheme 2 (house style `chemeurj`)

Source: Bourissou et al., "Mechanistic insights about the ligand-enabled oxy-arylation/vinylation of alkenes via Au(I)/Au(III) catalysis", *Chem. Eur. J.* **2022**. DOI: [10.1002/chem.202202110](https://doi.org/10.1002/chem.202202110). Scheme 2. Licence: CC BY 4.0 (as recorded on the house-style card). The reference crop is reproduced under that licence.

Drawing style: the `chemeurj` house-style card (base preset `wiley`), `reaction_scheme` section. Card: `skill/chemdraw/assets/house-styles/chemeurj/`. Cards were not edited.

## What is reproduced

The single reaction of Scheme 2: 4-penten-1-ol and iodobenzene give 2-benzyltetrahydrofuran under (P,N)AuCl 1 (5 mol%), AgSbF6 (1.05 eq.), K3PO4 (1 eq.) in CH2Cl2 at 25 °C overnight. The crop shows no yield, so none is drawn.

Structures (SMILES in `brief.json`):

| ID | SMILES | Note |
| --- | --- | --- |
| alkenol | `C=CCCCO` | read from the crop; 4-penten-1-ol |
| aryl iodide | `Ic1ccccc1` | iodobenzene |
| product | `c1ccc(C[C@H]2CCCO2)cc1` | (R)-2-benzyltetrahydrofuran; the R descriptor follows from the bold C2-O bond in the crop, read as toward the viewer; not checked against the paper text |

The brief is `brief.json` (try 1 of 2; try 2 with a reordered product SMILES drew a hashed wedge and placed the grey box over the phenyl label, so it was discarded). `rendered.png` is the ChemDraw render of try 1, downscaled to 1200 px. `replay.py` reruns the brief offline and writes `figure.cdxml` and `validation.json`.

The draw report: `ok`, readback `matched` (3 structures), lint with no issues, native rendered. The report warns that step 1 does not balance because HI is not drawn. The paper does not draw HI either, so this is expected.

## Convention check

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| compound_label_face bold (catalyst number 1 inside the conditions) | bold `1` | plain `1` (no rich text in condition lines) | no |
| compound_label_color #000000 | black | black | yes |
| conditions_split reagents_above_solvent_below | catalyst above; AgSbF6, K3PO4, CH2Cl2 25 °C overnight below | same split | yes |
| substrate_layout inline_plus | alkenol + ArI on one row | same | yes |
| abbreviate_groups includes Ph | phenyl rings drawn in full | iodobenzene and the benzyl phenyl both drawn as `Ph` labels | no |
| aromatic_rings kekule | Kekule phenyl rings | no ring drawn (`Ph` label) | no |
| new_bond_color null (card: no crop marks a formed bond) | the formed C-aryl bond (CH2-Ph, the bond from the aryl to the former terminal alkene carbon) is bold black | no formed bond marked; the bold bond falls on C2-CH2 (stereo) | no |
| substrate_colors null (card) but signature: blue and red fragments, colour carried into product | alkenol blue `#0000FF`, ArI ring red `#FF0000` (I black), product ring bonds and O blue, phenyl red | all black; the tool skips substrate_colors because the card value is null | no |
| highlight_fill `#E6E6E6` on reaction_scheme (card note: fill rests on crop 01 only) | no fill | grey hexagon behind the product | no |
| reagent_text_color #000000 | black | black | yes |
| arrow_style plain | plain arrow | plain arrow | yes |
| show_plus_sign true, plain weight | plain "+" | plain "+" | yes |
| signature: reagents above, additives, solvent, temperature, time stacked below in plain Arial | as in the paper | same | yes |
| signature: substrate fragments coloured, colour carried into the product | blue and red | black | no |
| signature: grey box behind products (crop 01 only) | none in crop 02 | grey hexagon, about one bond length across, added behind the Ph label | no |
| bond length over cap height about 2.0 (card) | 105 px bond, 54 px cap height, ratio 1.94 (crop 02 at 900 px: 42.6 px bond, 21 px cap, ratio 2.03) | about 46 px bond, 24 px H cap height, ratio 1.92 (1200 px render, measured) | yes (within about 5%) |
| arrow length about 7.2 bond lengths (card, crop 02) | 753 px at card scale; 309 px in the 900 px crop, 7.3 bond lengths | 393 px, about 8.5 bond lengths (measured) | no |
| line weight over bond length 0.04 (card) | arrow shaft about 1.8 px in the 900 px crop, 0.042 bond length | arrow shaft about 1.4 px at about 46 px bond, 0.030 bond length | no |
| bold width over bond length 0.19 (card) | bold C2-O and formed C-aryl bonds are uniform bars, 6 to 7 px, 0.14 to 0.16 bond length | one tapered wedge (C2 to CH2); the formed bond is not bold | no |

Claimed rows: 17. Matched rows as claimed: 9. After audit: 8 of 19 rows match (two rows added, see Audit).

## Differences from the paper

- Iodobenzene is drawn as `I-Ph` and the product's benzyl phenyl as `Ph`, where the paper draws full red phenyl rings. The `Ph` abbreviation applies to every phenyl under the chemeurj card.
- A grey `#E6E6E6` hexagon is drawn behind the `Ph` label; the paper's crop has no fill.
- The alkenol, iodobenzene and product fragments are all black; the paper colours the alkenol blue and the aryl iodide ring red, and carries the blue into the product ring bonds and O.
- The stereo bond is drawn as a bold wedge from C2 to the CH2 linker. In the paper it is the bold C2-O bond (a bar of constant width, not a wedge), and the CH2-phenyl bond is also bold.
- The formed C-aryl bond is not bold black as in the paper.
- The catalyst number `1` is plain; the paper sets it bold.
- The exocyclic CH2 runs down-right from C2 in the replica and up-right in the paper; the phenyl hangs straight down from the CH2 in the paper and runs up-right in the replica. The THF ring is placed similarly in both.
- The HI by-product is not drawn (the tool names it as missing and draws nothing). The paper does not draw it either.
- The conditions read `25 °C` in the replica and `25°C` in the paper; the split is the same, the text is not identical.

## Tool gaps

- No brief-level switch to keep full phenyl rings when the house style abbreviates `Ph`; `abbreviate_groups` applies to every scheme under the card.
- No per-species or per-step colour in `draw_figure` briefs. Colour only comes from the card's `substrate_colors`, which is null here, so the blue and red fragments of this crop cannot be drawn.
- No brief option to suppress `highlight_fill` for a scheme whose product is not filled. The fill always goes behind the largest ring of the final product.
- No option to bold one named bond (such as a formed bond) or to bold one character inside a condition line.
- Stereo wedge placement is chosen by the layout. A different product SMILES order gave a hashed wedge and a different ring orientation, so the drawn wedge position cannot be matched to the paper from the brief.
- `new_bond_color` needs the card value set; the tool reports it as "not specified by the card".

## Audit

Second-pass check against `reference.png` (byte-identical to `evidence/chemeurj-02.png`, 900 x 227 px) and `rendered.png` (1200 x 199 px). Numbers come from pixel measurements, so each is accurate to about 1 px.

- Corrected: the arrow row was marked as matched with no measurement. Measured, the replica arrow is 393 px, about 8.5 bond lengths (bond about 46 px), against 7.3 in the paper crop (309 px over a 42.6 px bond) and 7.0 on the card. Now `no`.
- Kept after measurement: bond over cap height is 1.92 in the replica (46 px bond, 24 px H cap) against 2.03 in the paper crop (42.6 px bond, 21 px cap), within about 5%.
- Added and not matched: line weight (arrow shaft 0.030 bond length against 0.042 in the paper crop; card 0.04) and bold width (the paper's bold bonds are constant-width bars of 0.14 to 0.16 bond length; the replica has one tapered wedge and no bold formed bond).
- Matched rows: 8 of 19. They are compound label colour, conditions split, substrate layout, reagent text colour, plain arrow, plain plus sign, stacked conditions in Arial, and bond over cap height. The conditions text differs slightly (`25 °C`).
- Stereo: the paper's C2-O bond is a bar of constant width, so the crop does not show which end is the stereocentre. The `(R)` label assumes that bond points toward the viewer. Under that reading the product is R, and the replica's wedge on the CH2 also reads as R, so the two drawings agree in configuration. This is not checked against the paper text.
- Card conflicts: `figure_types.reaction_scheme` sets `highlight_fill` `#E6E6E6`, and the card's `abbreviate_groups` includes `Ph`, but crop 02 has no fill and draws full phenyl rings. The replica's grey fill and `Ph` labels come from card values that this crop contradicts. The card's own notes say the fill rests on crop 01 only.
- Not checked: `validation.json` is not in this folder, so the draw report (ok, 3 structures matched, lint clean, native render) cannot be verified from here.

Tool gaps the replicator did not list:

- No brief field for arrow length in bond lengths; the arrow came out at about 8.5 bond lengths where the card asks for 7.0.
- No line-width or bold-width control; the replica's arrow shaft is thinner than the card's 0.04 ratio.
- No uniform bold-line bond style. The paper's bold bonds are constant-width bars; the tool offers only tapered and hashed wedges. The bold style itself is missing, not only the choice of which bond to bold.
- No brief control over the 2D direction of an exocyclic substituent. The CH2 and phenyl directions differ from the paper, and this is separate from the wedge placement.
- Card scope: `highlight_fill` and `abbreviate_groups` in `reaction_scheme` apply to every scheme under the card, so this card cannot express "no fill, full phenyl rings" for crop 02.
