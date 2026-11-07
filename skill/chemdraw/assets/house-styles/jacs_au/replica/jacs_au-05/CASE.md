# JACS Au: photochemical dimerisation of VCZ to t-DCZCB in continuous flow (Figure 4, flow setup)

Source: Landfester et al., *JACS Au* **2025** (Photoactive PFA coating through fluorophilic interactions for continuous flow photochemistry). DOI: [10.1021/jacsau.5c00804](https://doi.org/10.1021/jacsau.5c00804). Licence: CC BY 4.0 (from the house-style card); reference crop reproduced under that licence.

Crop: `evidence/jacs_au-05.png` (copied to `reference.png`, 661 x 185 px), Figure 4 of the paper.

Figure type: `setup_diagram` (card section `setup_diagram`, crops 05 and 06).

Drawing style: the `jacs_au` house style (base preset ACS Document 1996), applied through `brief.json` (`"style": "jacs_au"`). The report lists applied: bold compound labels, black reagent text, `show_plus_sign`. Skipped by the card (null): yield placement and format, conditions split, new-bond colour, highlight fill, substrate colours.

## What is reproduced

Only the chemistry of the flow setup. The schematic (syringe-type pump, coil reactor with LED head, valve, waste line) cannot be drawn with `draw_figure`, so the replica is the reaction it serves: VCZ (9-vinylcarbazole) to t-DCZCB (trans-1,2-bis(9-carbazolyl)cyclobutane) with the two conditions printed in the crop, as a scheme. The yield is not shown in the crop and is not drawn.

| ID | SMILES in brief.json | Source of structure |
| --- | --- | --- |
| VCZ | `C=Cn1c2ccccc2c2ccccc21` | read from the crop, name matches; checked with RDKit (C14H11N) |
| t-DCZCB | `c1ccc2c(c1)c1ccccc1n2[C@@H]1CC[C@H]1n1c2ccccc2c2ccccc21` | read from the crop and name; RDKit CIP (R,R), N atoms on opposite faces of the ring (trans). The cis isomer is (R,S), a meso form |

OCSR was not run; the structures are simple and were read directly from the crop and the name. One enantiomer is drawn, (R,R) as read back from the depiction. The crop draws the same wedge and hash pair with no rel label, so the image alone does not settle absolute versus relative configuration.

## Brief versions

- `brief.json` (final, used for `rendered.png`): two VCZ substrates (`VCZ`, `VCZ2`, identical SMILES) giving the 2 VCZ to 1 product dimerisation. Balance check passed, no warnings, readback matched.
- First try (not kept as a file in this folder): one VCZ, as drawn in the crop. The report warned `Step 1 does not balance as drawn: the reactants lack C14H11N` and drew it anyway. The figure in the crop shows one VCZ, so this is a faithful picture of the crop but an unbalanced equation.

## Replay

```
python skill/chemdraw/scripts/cdx.py py skill/chemdraw/assets/house-styles/jacs_au/replica/jacs_au-05/replay.py NEW_DIR
python skill/chemdraw/scripts/cdx.py render NEW_DIR/figure.cdxml
```

`replay.py` runs `draw_figure` on `brief.json` offline and writes `figure.cdxml` and `validation.json`. Compare the PNG with `reference.png`; `rendered.png` is the desktop ChemDraw rendering, downscaled to 1200 px wide.

## Convention comparison

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| setup_diagram: flat flow schematic, pump, coil, valve, waste (signature 1) | pump circle with chevron, coil as stacked rings with LED head, valve as circled X, waste arrow down | not drawn; no drawer for flow hardware | no |
| setup_diagram: coil reactor as stacked rings with LED head (signature 2) | stacked rings, pink-red with green light, black LED head | not drawn | no |
| setup_diagram: conditions as plain text under the reactor (signature 3) | 1:5 v/v Acetone:MeCN and 525 nm LED Lamp, 25 °C, plain text under the coil | same two lines, plain text under the arrow (the reactor is absent) | partial |
| setup_diagram: product name bold italic (signature 4) | t-DCZCB, bold italic | t-DCZCB, bold; italic t- prefix not applied | partial |
| compound_label_face bold | VCZ and t-DCZCB bold | bold | yes |
| compound_label_color #000000 | black | black | yes |
| reagent_text_color #000000 | conditions black | black | yes |
| arrow_style plain | plain arrow with head | plain arrow with head | yes |
| aromatic_rings kekule | carbazole rings with alternating double bonds | kekule | yes |
| stereo: bold wedge and hashed bond on the cyclobutane | bold wedge to the left N, hash to the right N | bold wedge to the left N, hash to the right N (depiction only; see Audit) | yes |
| label_font Arial | Arial-like sans | Arial, set by the toolkit's ACS label font constant; not measured in the render | yes |
| bond length / cap height 2.06 (card), crop 05 measures 20 / 9 px | 2.06 (card) | about 2.1 (VCZ cap about 21 px over a 45 px bond in rendered.png; threshold-dependent) | not confirmed |
| arrow length / bond length 3.2 (card), crop 05 measures 60 / 20 px | 3.2 (card) | about 7.3 (arrow 328 px over a 45 px bond in rendered.png) | no |
| line width / bond length 0.09 (card), crop 05 measures 2 / 20 px | 0.09 (card) | about 0.04 (effective line width 1.7 px over a 45 px bond in rendered.png) | no |
| substrate_layout inline_plus | one substrate in the crop | two VCZ joined by a plus sign | n/a (stoichiometry, see below) |

Counted rows: 14 scored, 7 matched, 2 partial, 4 no, 1 not confirmed. The substrate_layout row is excluded as not comparable (see Audit). Excluded: the highlight fill (#FE0000) and sub-panel letters belong to crop 06, not crop 05; background_fill and yield are null in the card and make no claim here.

## Differences from the paper

- The flow setup is absent. The replica shows the reaction only; the pump, coil reactor with LED, valve and waste line are not drawn.
- The crop shows one VCZ. The replica shows two VCZ with a plus sign, to balance the dimerisation. The one-VCZ version is available by using a single species in `substrates`, but the tool then flags the step as unbalanced.
- The product is drawn as one enantiomer (R,R). The crop shows a trans wedge and hash pattern; the tools cannot leave the drawing unspecified as a racemate or a relative configuration.
- The italic t- prefix in "t-DCZCB" is not applied; the label is bold roman.
- The arrow is a plain scheme arrow; in the paper the arrow is the flow outlet to a waste line. Its length is about 7 bond lengths against about 3 on the card, and its line weight is thinner than the card's measured value.
- The card's measured geometry (bond/cap, line width, arrow length) is not applied by the renderer, so these proportions come from the base preset.
- The paper's conditions sit under the coil, to the left of the outlet arrow; the replica places them under the arrow.

## Tool gaps

- No drawer for flow or photochemistry hardware: pump, coil reactor with LED head, valve (circled X), waste outlet and the flow lines. `setup_diagram` has no drawer in `draw_figure`, `render_scheme` or the brief kinds.
- Compound labels take plain text only: no italic or bold-italic segment inside a label (here the italic t- prefix).
- Stoichiometric coefficients (2 VCZ to 1 product) cannot be written; a dimerisation needs duplicate species, which draws two structures and a plus sign. A single-substrate dimerisation is drawn with an unbalanced-step warning, not refused.
- No racemate or relative-configuration notation: a racemic trans compound has to be drawn as one enantiomer.
- House-style measured geometry is read but not applied: `measured` (bond_length_over_cap_height, line_width_over_bond_length, arrow_length_over_bond_length) is loaded into HouseStyle and no drawing code reads it. Drawings take the base preset's geometry (acs1996: BondLength 14.4, LineWidth 0.6, a line-to-bond ratio of about 0.04). The brief has no arrow length or line width key (BRIEF_KEYS: kind, species, steps, max_width, title, style, layout), so no brief can reach the card's 0.09 line ratio or 3.2 arrow ratio.
- Reagent text is always attached to the arrow (step keys: substrates, products, above, below, yield, arrow). It cannot sit under another object, such as a reactor, or be left-aligned.
- Only kinds scheme, scope and mechanism are drawn; any other kind is refused with "is not available yet".

## Audit

Checked by the auditor against reference.png and rendered.png (ratios only, since the images are 661 and 1200 px wide), brief.json, the card jacs_au.json, and RDKit.

- The table left the arrow and bond proportions as "not measured" and kept them out of the count. Measured in rendered.png, the arrow is about 7.3 bond lengths against 3.2 on the card, and the line-to-bond ratio is about 0.04 against 0.09. Both rows are now "no". The cause is a tool gap (see Tool gaps), not a drawing slip.
- The bond/cap row is about 2.1 in the render, close to 2.06, but the cap height depends on the threshold, so it is "not confirmed".
- The label font row was supported only by the preset, not by a checked render. It is kept as "yes" with that evidence stated.
- The stereo note said the crop shows relative configuration only. The crop draws the same wedge and hash pair with no rel label, so this is not supported. The depiction reads back as (R,R) in a 2D check of the wedge pattern, which matches the SMILES. The trans relation is correct: the cis isomer would be meso (R,S). The stereo row stays "yes" for the depiction only.
- Corrected count: 7 of 14 scored rows match, not 7 of 11. The substrate_layout row (inline_plus) is not comparable: the card's convention is inline_plus, which the replica uses, but the crop has one VCZ and the replica has two.
- The first-round claim "label face bold" and the colour rows hold on the render.
