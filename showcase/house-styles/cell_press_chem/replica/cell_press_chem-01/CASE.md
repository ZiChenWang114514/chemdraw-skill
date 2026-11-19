# cell_press_chem-01: CuAAC step of Scheme 1, Goldup et al., Chem 2020

Source: M. Goldup et al., "Synthesis of a mechanically planar chiral rotaxane ligand for enantioselective catalysis", *Chem* 2020. DOI: [10.1016/j.chempr.2020.02.006](https://doi.org/10.1016/j.chempr.2020.02.006).

Licence: CC BY 4.0. The reference crop is reproduced under that licence (evidence crop `evidence/cell_press_chem-01.png`, Scheme 1 of the paper, a low-resolution web image).

Drawing style: the `cell_press_chem` house style card (`cdx.py styles cell_press_chem`), base preset `wiley`, applied through `draw_figure` with `"style": "cell_press_chem"`.

Figure type: `reaction_scheme`.

## What is reproduced

Step 1 of the scheme only: the azide (S)-1 and the alkyne-phosphonium 2 give a 1,4-disubstituted triazole with the yield 71% under the arrow, with the step name "1. AT-CuAAC" above the arrow. The macrocycle 3 is not drawn, so the product is a model triazole and the compound label reads "4 (model)".

| Species | SMILES in brief.json | Check |
| --- | --- | --- |
| (S)-1 | `CC(C)OC(=O)[C@H](Cc1ccccc1)N=[N+]=[N-]` | RDKit CIP: S |
| 2 | `C#CC[P+]([BH3-])(c1ccccc1)c1ccccc1` | RDKit: C15H16BP |
| model triazole | `[BH3-][P+](Cc1cn([C@H](Cc2ccccc2)C(=O)OC(C)C)nn1)(c1ccccc1)c1ccccc1` | CIP at the N-CH centre: R by hand (see Audit), not S as first recorded; 1,4-regiochemistry as in the paper (CH2P at C4, C5-H) |

The three structures were read by eye from the 741 px crop. OCSR was not run, because the macrocycle could not be read reliably at this resolution and the drawn structures are the simple ones.

## Convention table

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| yield under the arrow, format `{value}%` | 71% under the arrow | 71% under the arrow | yes |
| step name numbered above the arrow ("1. AT-CuAAC") | "1. AT-CuAAC" above the arrow | same text, typed in the brief (the tool does not number steps) | yes |
| conditions split: step name above, yield below | "1. AT-CuAAC" above, 71% below | same split | not counted: repeats the yield and step-name rows; the card's conditions_split is null |
| compound labels bold, colour #000000 | bold labels | bold labels, black | yes |
| abbreviated groups (Ph) | Ph | Ph | yes |
| reagent text colour #000000 | black | black | yes |
| sans-serif text (Arial) | sans-serif | Arial in the wiley preset | yes |
| stereo prefix italic in compound labels, e.g. (S)-1 | (S)-1 | (S)-1, whole label bold and upright | no |
| components coloured by origin (red, green, blue) through the scheme | 1 and 2 red, the macrocycle green, blue and red | all black | no |
| heavy arrow with a large filled head (house card notes, crop 01) | heavy shaft, large head | thin arrow | no |
| reagents stacked in a column, no plus sign (house card notes, crop 01) | 1 above 2, no plus | 1 and 2 side by side with "+" | no |
| line weight over bond length (card 0.08) | 0.08 (card, crop 03) | about 0.05 on rendered.png: stroke about 2.2 to 2.5 px on a 43 px bond; the wiley preset gives 0.75 over 17 = 0.044 | no |
| arrow head size | head 18 px long, 10 px wide on a 103 px arrow, about 1.8 cap heights (crop 01) | head 14 px long, 8 px wide on a 218 px arrow, about 0.7 cap heights | no |
| arrow length over bond length (card 7.5) | 7.5 (card, crop 03) | about 5.0 (218 px over about 43 px) | no |
| arrow length over cap height (crop 01) | 10.3 | 10.4 (218 px over 21 px) | yes |
| bond length over cap height (card 2.12) | 2.12 (card, crop 03) | about 2.0 to 2.1 (43 px over 21 to 22 px) | yes, within measurement error |
| stereocentre of the model triazole | (S)-1 has a wedge to CH2Ph and reads S | hashed bond to CH2Ph on the same 2D layout, reads R; the brief SMILES encodes R | no |
| azide | N3 as a label with subscript 3 | N=N+=N- drawn out; the central N-N bond renders as a dash with two dots | no |

Matched 6 of 11 rows after audit. The conditions split row repeats the yield and step-name rows and is not counted. The step numbering row counts as matched only because the number was typed in the brief.

Measured on rendered.png (see Audit): bond over cap height about 2.0 to 2.1 against the card's 2.12, and arrow over bond length about 5.0 against the card's 7.5. The reference crop has no measurable bond length (`bond_length: null` in the card), so the reference side of the bond ratios comes from the card's crop 03.

## Differences from the paper

- The macrocycle 3 is not drawn. The paper's product 4 is the macrocyclic phosphine oxide with the (S,Rmp) and (S,Smp) diastereomers; the replica product is the model triazole with the N-CH(Bn)CO2iPr fragment and the CH2P(BH3)Ph2 group only.
- The paper's product shows the phosphine oxide; the replica keeps the BH3 adduct from 2, because draw_figure checks atom balance and the borane has to be carried through the step.
- Steps 2 (alkylation to 5), 3 (reduction) and 4 ([Au(SMe2)Cl]) are not drawn.
- Labels: the paper's labels 1, 2, 3, 4 and the stereodescriptors (S,Rmp)-4 and (S,Smp)-4 are not reproduced; the replica label is "4 (model)".
- Colour coding by origin is absent (all black); the arrow is thin, not heavy; the reagents are side by side with "+", not stacked without plus signs.
- Stereodescriptors in the paper are italic; the replica label is bold upright text.
- Layout: the paper stacks the two reagents in a column on the left and shows two product diastereomers (top and bottom); the replica is one row of three structures.

## Tool gaps

- Per-species colour: draw_figure has no colour field for a species. `substrate_colors` colours the i-th substrate of a step, and the card leaves it null, so colour by origin (red for 1 and 2, green and blue inside the macrocycle) cannot be produced from the brief.
- Heavy arrow: `arrow_style: bold` exists in the tool, but the card's `arrow_style` is null, so it is not applied. There is no arrow head size control.
- Stacked reagents without plus signs: `substrate_layout: stacked_plus` always draws the "+" between the stacked substrates. No option removes it.
- Italic stereo prefix: a compound label is a single text run in the brief, so the italic stereodescriptor cannot be set.
- Macrocycle with a mechanically planar chiral ring (3, and the (S,Rmp)/(S,Smp) products): not reproduced. The ring cannot be written from the 741 px crop with confidence, and no OCSR result was used.
- Multi-step routes with reagents at each step: the replay covers one step only, because steps 2 to 4 need the macrocycle.
- Card measurements are not applied: draw_figure never reads the card's `measured` block (bond length, line width, bold width, arrow length). The wiley preset values (LineWidth 0.75, BondLength 17) are used as they are, so the line weight and bond-based arrow length cannot be set to the card's ratios from the brief.
- Arrow length and shaft weight: there is no field for either. The arrow length follows the layout, and the head size is fixed by the preset.
- Subscripts, superscripts, italic runs and atom annotations: a label is one text run, so "(S,Rmp)-4" and the italic letters g, h, i, j beside atoms cannot be written.
- Stereo check: the brief has no CIP or stereo assertion, and draw_figure draws the stereocentre from the SMILES without comparing it with the reactant. The inverted model product drew without any warning.
- Layout: route layouts come only from classify_route (linear, convergent, divergent, catalytic-cycle). Two products stacked vertically in one step cannot be requested.
- Azide: the charged azide drawn from SMILES renders its central bond as a dash with two dots. The cause was not diagnosed in this audit, and no option was found for it.

## Replay

```
python skill/chemdraw/scripts/cdx.py py skill/chemdraw/assets/house-styles/cell_press_chem/replica/cell_press_chem-01/replay.py NEW_DIR
python skill/chemdraw/scripts/cdx.py render NEW_DIR/figure.cdxml
```

`rendered.png` is the desktop ChemDraw rendering of the brief (1200 px wide, downscaled from the 1947 px render). `reference.png` is the evidence crop.

## Audit

Checked on 2026-11-07 against reference.png (741 by 352 px) and rendered.png (1200 by 310 px). Ratios are pixel counts from those images, good to about 5 percent. brief.json and the other files in this folder were not edited.

- Stereocentre (stated under "What is reproduced"): the brief product SMILES is R, not S. In the azide SMILES, the `[C@H]` neighbours are C(=O), H, CH2, N with `@`, which reads S. In the product SMILES, `n([C@H](Cc2ccccc2)C(=O)...)`, the neighbours are N, H, CH2, C(=O) with `@`. Swapping N and C(=O) flips the parity, so the centre is R. The same method reads L-alanine (`N[C@@H](C)C(=O)O`) as S. RDKit is not installed in the audit environment, so this is a hand check. The drawing agrees: the hashed CH2 bond sits on the same 2D layout as the wedge in (S)-1, which reads R. CuAAC does not change this centre, so brief.json needs the product SMILES corrected to the S enantiomer and the replay rerun.
- Overclaim: the conditions split row repeats the yield and step-name rows, and the card's conditions_split is null. Corrected count: 6 of 11 rows.
- Overclaim: the proportions were not "not checkable". Bond over cap height is about 2.0 to 2.1 (43 px over 21 to 22 px), within about 5 percent of the card's 2.12, so it matches. Arrow over cap height is 10.4 against 10.3 in crop 01, so it matches. Arrow over bond length is about 5.0 against the card's 7.5, so it does not match. Line over bond length is about 0.05 against 0.08, so it does not match.
- Arrow head: the reference head is about 1.8 cap heights long and the replica head about 0.7, so the arrow reads lighter. This is not matched, and the tool gap is real.
- Card: the wiley preset is not "closest on the three ratios" for line weight (0.044 against 0.08). The card's arrow over bond (7.5, crop 03) and arrow over cap (10.3, crop 01) imply a bond over cap ratio of about 1.4 for crop 01, against 2.12 from crop 03. The card mixes two schemes.
- Crop size: the reference is 741 by 352 px, not 690 px.
- Unlisted visual difference: the reference writes the azide as N3 with a subscript, and the replica draws the charged azide with a dash-and-dot central bond (rendered.png, x 0 to 80, y 85 to 135).

Corrected matched rows: yield under the arrow and its format, the step name above the arrow (typed text, not a tool feature), bold compound labels, Ph, black reagent text, and Arial. The conditions split row is not counted.
