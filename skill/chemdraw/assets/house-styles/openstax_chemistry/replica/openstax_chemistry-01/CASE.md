# OpenStax Chemistry: Figure 12.21 (reaction-coordinate diagram, ethene + H2 to ethane)

Source: Flowers, Theopold, Langley, Robinson et al., *OpenStax Chemistry* 2015, section 12.7 Catalysis, Figure 12.21. The card has no DOI. Licence: CC BY 4.0 (the reference crop is reproduced under that licence).

Drawing style: the `openstax_chemistry` house style in `brief.json` (base preset `chemdraw_slide`); see `cdx.py styles openstax_chemistry`. Figure type: `energy_profile`.

## What is reproduced

Only the chemistry the crop names: ethene (`C=C`), H2 (`[H][H]`) and ethane (`CC`), drawn as one solid-arrow scheme, ethene + H2 to ethane, with the house style applied only in part (see the table). The crop has no reaction arrow, conditions or yield. The replica draws a reaction arrow although the crop has none, and draws no conditions or yield. The atom balance result is not in this folder (there is no `validation.json` here), so it is not verified here. `checks_passed` is reported false (see Tool gaps).

The energy profile itself is not reproduced. `draw_figure` has no energy-profile drawer, so the two curves, the axes, the Ea arrows, the reference line at the reactant level, the ΔH annotation and all text labels are missing. This replica tests the structures only.

Tries: try 1 (`brief.json`) draws the species from SMILES. Try 2 gave explicit hydrogens on the carbons (`[H]C([H])=C([H])[H]`, `[H]C([H])([H])C([H])([H])[H]`); the replicator reports the output was identical because the explicit hydrogens are normalised to implicit ones. This audit did not re-run it. Try 1 is kept.

`replay.py` redraws `brief.json` offline into a new folder. The script writes `figure.cdxml` and `validation.json` (read from the script; not re-run in this audit). `rendered.png` is the ChemDraw render (1606 x 94 px) downscaled to 1200 x 70 px.

## Convention table

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| level_style smooth_curve | smooth curves through the reactant, transition-state and product levels | no curves drawn | no |
| pathway_colors #BC4428 and #8894C8 | uncatalysed red, catalysed light blue (sampled #BC4428 and #8894C8) | not drawn | no |
| ts_marker none | "Transition state" as plain text above the peak, no symbol | not drawn | no |
| bold Energy and Extent of Reaction axis titles | both bold Arial | not drawn | no |
| arrowheads on the axes, no numbers, no units | arrowheads on both axes, no numbers | not drawn | no |
| Ea shown as vertical double arrows in the path colour | uncatalysed Ea arrow black, catalysed Ea arrow red | not drawn | no |
| Transition state, Reactants and Products as plain text (card: thin leader lines on these labels) | Transition state plain with no leader line; reactant and product formulas plain with no leader line; only the two Activation energy labels have leader lines | no text labels | no |
| compound_label_color #000000 | species black | no compound labels drawn; the only text is the two H atoms, black, in Times New Roman | no |
| arrow_style plain, filled head | the crop has no reaction arrow to compare; the axis arrowheads are filled | plain arrow with a filled head (agrees with the card's crop 09 signature, not compared with crop 01) | n/a |
| arrow_length_over_bond_length 2.5 (card value, from crop 09) | no reaction arrow in crop 01 to measure | 150 pt arrow over a 30 pt bond = 5.0; the card value is not applied | no |
| show_plus_sign true | reactants stacked, no plus | plus between ethene and H2 | no |
| substrate_layout inline_plus | H2C=CH2 stacked above H2 | inline with plus | no |
| label_font Arial or Helvetica | sans-serif labels | H atoms and plus in Times New Roman (CDXML font 4 per the replicator; not re-checked) | no |
| intermediate_label_style none | no intermediate in the crop | nothing to label | n/a |
| energy_unit null, energy_label null | no unit, no energy values | no energy axis drawn | n/a |
| reagent_text_color #000000 | no reagent text | none drawn | n/a |
| bond_length_over_cap_height 3.35 | not measurable (null for crop 01) | not measured | n/a |

Matched 0 of 12 checkable conventions. The first count of 1 of 13 rested on the compound colour row, which has no compound labels to compare, so it is now not matched. arrow_style is n/a because crop 01 has no reaction arrow.

## Card observations (reported, card not changed)

- Ea signature: the card says the Ea double arrows are in matching colours. In crop 01 the uncatalysed Ea arrow is black and the catalysed Ea arrow is red, the colour of the uncatalysed path. A zoom on the arrows and the leader lines confirms it.
- Reactant and product signature: the card says they are plain text with thin leader lines. In crop 01 only the two Activation energy labels have leader lines. The reactant and product formulas and the Transition state label have none.
- Missing from the card: a thin black reference line at the reactant energy level, a double-headed ΔH arrow labelled "ΔH < 0 exothermic", and a darker blue (#4C68AC sampled) flat segment at the reactant and product ends of the catalysed curve. The flat-end colour was re-sampled from reference.png in this audit (about #4D68AF at the reactant end and about #4D68AD at the product end).
- The crop 01 observation lists H2C=CH2 at the start and H3C-CH3 at the end but omits the H2 written under H2C=CH2 at the start.
- energy_profile inherits the top-level scheme conventions (`inline_plus`, `show_plus_sign`), but crop 01 stacks its reactant labels with no plus. The card does not say which applies to energy diagrams.
- Confirmed: pathway colours #BC4428 and #8894C8 (re-sampled from reference.png in this audit), bold axis titles, arrowheads on the axes, smooth curves, no units.

## Differences from the paper

- The energy diagram is absent: no curves, axes, Ea arrows, reference line, ΔH annotation, leader lines or text labels. The replica is a scheme of the three species only.
- Reactants: the paper stacks H2C=CH2 above H2 with no plus and no arrow; the replica writes ethene + H2 to ethane inline with a plus and a reaction arrow. The arrow is not in the crop.
- Ethene and ethane are skeletal, with bond ends and no CH2 or CH3 labels. The paper writes H2C=CH2 and H3C-CH3 as condensed text. H2 is drawn as an H-H bond; the paper writes H2 as text.
- Atom labels and the plus are in a serif face (Times New Roman as seen in rendered.png), while the card specifies Arial.
- The arrow is 5 bond lengths long; the card gives 2.5.
- Proportions: the reference crop is 644 x 614 px (close to square). The render is a strip about 17 times wider than tall (1606 x 94 px). The overall shape does not match.
- Line weight is not measured against the card's line_width_over_bond_length (0.042). Not matched until measured.

## Tool gaps

- No energy-profile drawer. `draw_figure` accepts scheme, scope and mechanism briefs only; any other kind is refused at the kind check. Missing: smooth reaction-coordinate curves through reactant, transition-state and product levels; arrowed axes with bold titles; a reference line at the reactant energy; Ea double arrows in path colours; a ΔH double arrow with its label; leader-line callouts. The card's energy_profile conventions are never applied or reported: no code in the toolkit consumes that figure type outside the card loader and its tests.
- No bare reactant list. Each step draws a reaction arrow, so the stacked species list with no arrow and no plus cannot be expressed.
- No condensed-formula labels. Species come from SMILES as skeletal structures, and explicit-H SMILES are normalised to implicit H (the replicator's try 2 gave an identical file).
- House label font not applied, and the cause is wider than the font. The card's `measured` block (label_font, arrow_length_over_bond_length, line_width_over_bond_length, bold_width_over_bond_length, bond_length_over_cap_height) is read by no code path in `mcp_runtime`, `chemdraw/style_presets.py` or `publication/house_styles.py`, so these values are dropped with no entry in either the applied or the skipped list. The brief keys (`BRIEF_KEYS` in `mcp_runtime/figure_draw.py`) include no label-font or arrow-length key either, so the agent cannot set them directly.
- House arrow length not applied. The arrow is 150 pt over a 30 pt bond (ratio 5.0); the card's 2.5 comes from the same unread `measured` block.
- Lint. The stray_plus check reports the plus on id 1008 as not between two species, although the render puts it between ethene and H2. The cause is not established; `checks_passed` is false although the readback matched.
- No control over the aspect of a one-row scheme beyond `max_width`; the output is a 1606 x 94 px strip. There is no canvas or crop-box setting, so the layout cannot be matched to a 644 x 614 px crop.
- Missed by the replicator: no stroke-weight control for curves and no per-segment colour along a path (the dark-blue flat ends at #4C68AC need this).
- Missed by the replicator: no free-text primitive with italic and Greek runs (ΔH), subscript runs in free labels, or multi-line text blocks placed at coordinates. The brief can label species only.

## Audit

Audit on 2026-11-07 by re-reading reference.png (644 x 614), rendered.png (1200 x 70, the downscale of the 1606 x 94 render), CASE.md, brief.json, replay.py, the openstax_chemistry card and the toolkit source. Not re-run: replay.py, so the atom balance, the lint result, the 5.0 arrow ratio and try 2 are reported from the replicator. The `measured` block finding is from grep of the toolkit source.

Overclaims found and corrected in this file:
- Matched count 1 of 13 changed to 0 of 12. The compound colour row was marked as a match, but the replica has no compound labels to compare. The arrow_style row moved to n/a, since crop 01 has no reaction arrow.
- "so none are drawn": the replica draws a reaction arrow; the crop has none.
- "with the house style": applied only in part. The label font and arrow ratio are not applied.
- Transition state row: it said the label has a leader line. The crop shows none on that label; only the two Activation energy labels have leader lines.
- "The atom balance check passes": no validation.json is in this folder, and checks_passed is reported false.
- "checked: it writes figure.cdxml and validation.json": read from the script, not run here.

Confirmed from the images and code: pathway colours #BC4428 and #8894C8; the darker flat ends near #4C68AC; the uncatalysed Ea arrow black and the catalysed red; no plus and no arrow between the stacked reactants in the crop; H2 under H2C=CH2; bold axis titles; no units; the replica's H atoms and plus in a serif face; the card's `measured` values not read by any code.
