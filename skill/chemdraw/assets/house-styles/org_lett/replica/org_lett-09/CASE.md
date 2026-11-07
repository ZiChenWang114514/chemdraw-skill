# org_lett-09: Akiyama et al., Scheme 3 (derivatization of 4ac), fan from 7

Source: Akiyama et al., *Org. Lett.* **2025**, *27*, 6204 (chiral phosphoric acid-catalyzed enantioselective Pictet-Spengler reaction for CF3-substituted tetrahydro-beta-carbolines), Scheme 3. DOI: [10.1021/acs.orglett.5c01864](https://doi.org/10.1021/acs.orglett.5c01864).

Licence: CC BY 4.0 (from the house-style card). The reference crop is reproduced under that licence.

Drawing style: the `org_lett` house style (`"style": "org_lett"` in `brief.json`; base preset ACS Document 1996). Figure type: `derivatization`.

## What is reproduced

Only the fan from the terminal alkyne 7 to its three derivatives: 9 (Sonogashira coupling with Ph-I, 87%, 91% ee), 8 (Lindlar hydrogenation, 84%, 90% ee) and 10 (Pd/C hydrogenation, 93%, 91% ee). Conditions and yields are copied from the scheme. Each derivative has its bold number with the yield and ee line under it.

Not reproduced:

- the TBAF step from 4ac to 7 (98%, 91% ee), and the "91% ee" line under 4ac;
- the 4ac to 6 route (1) Boc2O, Et3N; 2) TBAF; 85%, 91% ee, "(2 steps)");
- the radial arrangement of the paper (see Differences).

The full scheme could not be drawn in one brief (Attempt 1 below), so the brief carries the fan from 7 only.

Structures (SMILES in `brief.json`; RDKit CIP label at C1 is R for each):

| ID | SMILES | Note |
| --- | --- | --- |
| 7 | `FC(F)(F)[C@]1(C#C)NCCc2c1[nH]c1ccccc21` | starting material of the fan |
| 9 | `FC(F)(F)[C@]1(C#Cc2ccccc2)NCCc2c1[nH]c1ccccc21` | Sonogashira product |
| 8 | `FC(F)(F)[C@]1(C=C)NCCc2c1[nH]c1ccccc21` | vinyl product |
| 10 | `FC(F)(F)[C@]1(CC)NCCc2c1[nH]c1ccccc21` | ethyl product |

Not in the brief, written and checked for later use (full scheme): 4ac `FC(F)(F)[C@]1(C#C[Si](C(C)C)(C(C)C)C(C)C)NCCc2c1[nH]c1ccccc21` (CIP R, C23H31F3N2Si) and 6 `FC(F)(F)[C@]1(C#C)NCCc2c1n(C(=O)OC(C)(C)C)c1ccccc21` (CIP R, C19H19F3N2O2). Ph-I is `Ic1ccccc1`; the H2 and the Pd/Lindlar reagents are text.

Stereo: the crop draws a bold wedge on the CF3 bond and a hashed bond to the alkyne at C1, with the ring NH up. Reading these wedges gives R, which agrees with the RDKit CIP labels above. The absolute configuration is my reading of the crop; it has not been checked against the paper's SI.

OCSR: `cdx.py ocsr` (decimer-api) returned `CC(C)(C)C#C[C@]1(O)NCCc2c1[nH]c1ccccc21`, which reads TIPS as tBu and CF3 as OH. It was not used. The SMILES above were written by hand and checked with RDKit.

## Attempts

1. Full scheme (4ac to 7 by TBAF; 4ac to 6 by the two-step route; 7 to 9, 8 and 10). `draw` stopped with: "The steps are not a linear route, a convergent route (arms that merge) or a set of reactions from one starting material, so they cannot be laid out." No drawing was made.
2. Fan from 7 only (`brief.json`, saved as `brief2.json` in the scratch folder and copied here). Layout `divergent`; checks passed; lint clean; readback matched 4 structures. Rendered with desktop ChemDraw; `rendered.png` is that render downscaled to 1200 px. The tool reports that steps 1 to 3 "do not balance as drawn" (C6H4, H2 and H4 missing). This is because Ph-I and H2 are text reagents, not species; nothing was added to the drawing.

Replay: `cdx.py py replay.py NEW_DIR` runs offline from `brief.json` and reproduced `layout: divergent`, `checks_passed: true`, `readback: matched`.

## Convention table

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| derivatization_layout: radial | 7 at top middle; arrows right (to 9), down (to 8) and diagonal (to 10) | three horizontal arrows off a vertical bus line from 7 | no |
| yield_format `{value}%`, with ee text | `87%, 91% ee` under 9 | `87%, 91% ee` under 9 (the text is kept as given; the template is not applied to it) | yes |
| highlight_fill: null | none | none | yes |
| variation_color: null | all black | all black | yes |
| signature: parent top left, arrows right, down and diagonal to each derivative | the fan leaves 7 (top middle), not the top-left 4ac | the fan leaves 7 (left of the bus); all arrows horizontal | no |
| signature: reagents beside each arrow | reagents beside each arrow: the Lindlar reagents sit to the right of a vertical arrow, the H2 Pd/C reagent above a diagonal arrow, the Ph-I and CuI lines beside the horizontal arrow | every reagent sits above a horizontal arrow; no arrow in the replica is vertical or diagonal | no |
| signature: "1) 2)" two-step labels | on the 4ac to 6 route | not drawn (route omitted) | no |
| signature: bold number with yield, ee below each derivative | bold 9, 8, 10 with yield, ee | bold 9, 8, 10 with yield, ee | yes |
| signature: "(2 steps)" in parentheses | under 6 | not drawn (6 omitted) | no |
| signature: all black, no colour or boxes | yes | yes | yes |
| compound_label_face: bold | bold | bold | yes |
| compound_label_color: #000000 | black | black | yes |
| yield_placement: under_product_label | yield line under the bold label | same | yes |
| yield_separator: ", " | `87%, 91% ee` | same | yes |
| conditions_split: reagents above, solvent below | CuI, Et3N and PdCl2(PPh3)2 above; Ph-I below | same; the split comes from the brief (the tool keeps the brief's lines, it does not apply the card rule) | yes |
| abbreviate_groups: Ph, CF3 | Ph on the alkyne of 9; CF3 written as F3C (F, subscript 3, then C) | Ph on the alkyne of 9; CF3 written as CF3 (C first) in 7, 9, 8 and 10 | no |
| abbreviate_groups: Me | no Me label on the ethyl of 10 | Me label on the terminal CH3 of the ethyl of 10 | no |
| aromatic_rings: kekule | kekule | kekule | yes |
| arrow_style: plain | plain arrows | plain arrows | yes |
| reagent_text_color: #000000 | black | black | yes |
| new_bond_color: null; substrate_colors: null | black | black | yes |
| measured line width, 0.065 of bond | about 0.067 (2 px over 30 px) | 0.60 pt over 14.4 pt = 0.042 | no |
| measured bold width, 0.2 of bond | about 0.2 (6 px over 30 px) | 2 pt over 14.4 pt = 0.14 | no |
| measured label size, 9 pt | cap height 13 px over a 30 px bond (the crop has no pt scale, so 9 pt is not checked) | 10 pt (acs1996 LabelSize, not the card value) | no |
| measured arrow length, 7.6 bonds (card mean) | 3.3 bonds in this crop (100 px over 30 px) | 72 pt over 14.4 pt = 5.0 bonds | no |

Counts: 25 rows, 14 match (the first draft said 16; see Audit). The `substrate_layout` and `show_plus_sign` conventions are not counted: no step in this figure has two substrates.

## Differences from the paper

- Scope: only the fan from 7 (three derivatives). The TBAF step, 4ac, 6, the 4ac to 6 route and the ee line under 4ac are missing.
- Layout: the paper's radial arrangement (9 to the right, 8 straight down, 10 diagonal) is replaced by three horizontal arrows on a vertical bus. Rows are stacked, so 8 and 10 sit lower than in the paper.
- Orientation: the paper draws the tetrahydro-beta-carboline with the indole on the left and the piperidine NH at top right. The replica mirrors the scaffold: the indole is on the right and the piperidine on the left.
- Stereo depiction: the paper uses a CF3 wedge and an alkyne hash in 7 and 4ac; in 9 the alkyne is hashed; in 8 the CF3 is a wedge and the vinyl a hash; in 10 the CF3 is a wedge and the ethyl a hash. The replica puts the wedge on the alkyne in 7 and 9 (CF3 plain), a hash on the CF3 bond in 8 (vinyl plain), and a wedge on the ethyl bond in 10 (CF3 plain). The configuration reads back as R for 7, 9, 8 and 10 (toolkit `read_molecules` plus RDKit CIP), so the depiction differs but the stereochemistry does not.
- Labels: ChemDraw writes the piperidine NH as "HN" in this orientation; the paper writes "NH". The indole NH is also "HN" with the H beside the N, where the paper stacks the H under the N. The CF3 group is written "CF3" where the paper writes "F3C".
- Me label: the terminal CH3 of the ethyl in 10 is labelled Me; the paper draws a plain chain end.
- Proportions: the replica uses the acs1996 values (bond 14.4 pt, line 0.6 pt, bold 2 pt, label 10 pt). The card's measured values (line 0.94 pt, bold 2.9 pt, label 9 pt) are not applied. Replica arrows are 72 pt (5 bonds), longer than the 3.3 bonds in this crop.
- Yield text: the yields and ee values match. "(2 steps)" is missing because 6 is omitted.

## Tool gaps

- `draw_figure` refuses a route that combines a chain (4ac to 7) with a fan from 7 and a second branch from 4ac (the error is quoted in Attempt 1). The full scheme cannot be drawn in one brief.
- No radial (hub-and-spoke) layout. `derivatization_layout: radial` is not applied and not listed in `style.skipped`. The divergent layout stacks product rows on a vertical bus.
- The brief cannot name a figure type, so the `figure_types.derivatization` conventions are never applied.
- The card's measured proportions (line 0.065, bold 0.2, label 9 pt, arrow 7.6 bonds) are not applied. Only the base preset values are used, and `style.applied` does not list them.
- A yield or ee line cannot be placed under a starting material (the "91% ee" under 4ac). Yield lines attach only to the product of a step.
- The tool chooses the wedge and hash bonds itself. The crop's CF3 wedge and alkyne hash cannot be requested, so the stereo bond differs from the paper in each derivative.
- No control of ring orientation or 2D coordinates in `draw_figure`.
- `abbreviate_groups` labels the terminal CH3 of an ethyl group as Me, which the crop does not do.
- No control of label orientation; the piperidine NH and the indole NH are written HN, and the CF3 group is written CF3 (the paper writes F3C). No brief field sets the written form of an abbreviation.
- The card's `yield_format`, `yield_separator` and `conditions_split` rules are not applied by the tool. The matching rows for yield text and reagent split reflect strings typed into `brief.json`, not tool output.
- Reagents given as text are not counted in the balance check, so steps with Ph-I or H2 are reported as "does not balance" even when the drawing is correct.
- The written form of an abbreviation cannot be chosen. The paper writes CF3 as F3C; the brief has no field for this.
- The stacked NH of the indole (H under N) cannot be requested; the tool writes HN with the H beside the N.
- The angle of each arrow and the side on which its reagents sit cannot be set per step. Every arrow in this figure is horizontal, so no reagent is beside a vertical or diagonal arrow as in the paper.
- The card's text rules (`yield_format`, `yield_separator`, `conditions_split`) are not enforced. The output shows only what the brief text says.

## Audit

Checked by eye at 2x zoom of `reference.png` and `rendered.png`. Pixel measurements were not repeated, and the toolkit was not run.

Overclaims corrected in the table:

- Row "signature: reagents beside each arrow" was marked matched. The paper's column already says "beside", but the replica puts every reagent above a horizontal arrow, and the paper has a vertical arrow (Lindlar, reagent to its right) and a diagonal arrow (H2 Pd/C). Now marked no.
- Row "abbreviate_groups: Ph, CF3" was marked matched. The paper writes the group as F3C, and the replica writes CF3 in 7, 9, 8 and 10. Now marked no.
- Rows "yield_format", "yield_separator" and "conditions_split" stay matched, but only on the rendered text. The strings were typed into `brief.json`, and the tool does not apply the card's rules.

Corrected matched count: 14 of 25 (was 16).

Checked and not refuted: highlight and variation colour (none), all-black drawing, bold compound numbers, label colour, yield placement under the bold number, kekule rings, plain arrows, reagent colour, and blank substrate colours. The stereo reading (R for 7 in both the paper's wedges and the replica's) also holds. The "no" rows for line width, bold width, label size and arrow length were not re-measured. They stay "no" because the stated values differ from the card, and the paper's proportions were not measured to a tolerance.
