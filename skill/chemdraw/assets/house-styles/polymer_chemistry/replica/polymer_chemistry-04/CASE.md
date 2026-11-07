# Zuhorn et al., Polym. Chem. 2025: PI-RAFT mechanism (Scheme 1, crop 04)

Source: Zuhorn et al., Polym. Chem. 2025 (Solvent and temperature effects in photoiniferter RAFT polymerisation of PEG methacrylate). DOI: [10.1039/d5py00300h](https://doi.org/10.1039/d5py00300h). Licence: CC BY 3.0, from the `polymer_chemistry` house-style card. Reference crop: `reference.png` (copy of `evidence/polymer_chemistry-04.png`, Scheme 1).

Figure type: `mechanism` (card section `figure_types.mechanism`). Style: `polymer_chemistry` (base preset `rsc`).

## What is reproduced

The three-box PI-RAFT mechanism of the crop, as species and steps only (boxes, colours and the M label are not reproduced; see Audit):

- (a) photoactivation: RAFT agent with the chain Pm, under hv, gives the Z-S-C(=S)-S radical and the Pm radical; the paper draws this step as an equilibrium, and the replica draws it one-way (see Audit). Brief: `brief-a.json` (scheme).
- (b) RAFT equilibrium: RAFT agent with Pn plus Pm radical in equilibrium with the RAFT agent with Pm plus the Pn radical. Brief: `brief.json` and `brief-b.json` (identical; scheme).
- (c) reversible termination: Pm radical plus the Z-S-C(=S)-S radical in equilibrium with the RAFT agent with Pm. Brief: `brief-c.json` (scheme).
- Propagation: the Pn radical adds to methyl methacrylate through one curved one-electron arrow, drawn as one curved one-electron arrow, as in the crop; the product is drawn too, which the crop does not show. Brief: `brief-mech.json` (kind `mechanism`).

`rendered.png` is a 2 x 2 assembly of four native `draw_figure` renders in the crop's panel positions: (a) top left, (b) top right, (c) bottom left, and the propagation step (curved arrow plus product, which the crop does not show) in the bottom right cell. The assembly was made with PIL outside the tool. It is not one drawing, and only the bottom right panel shows a title ("PI-RAFT propagation", from its brief); the other three have none, and none of the paper's box titles are drawn.

Model species (placeholders replaced):

| Paper | Replica | SMILES in brief |
| --- | --- | --- |
| Z (leaving group) | dummy atom `*`, drawn as R | `*SC(=S)SC(C)(C)C(=O)OC` (Pm model) |
| Pm chain | 2-methylpropanoate model | `COC(=O)[C](C)C` (radical) |
| Pn chain | ethyl 2-methylpropanoate model | `CCOC(=O)[C](C)C` (radical) |
| monomer M | methyl methacrylate, not PEG methacrylate | `C=C(C)C(=O)OC` |

The Z-S-C(=S)S radical is `*SC(=S)[S]`. The `*` atoms are drawn as R. draw_figure cannot balance generic atoms and reports "balance could not be checked" on each such step. All other species are checked with RDKit.

## Replay

```
python skill/chemdraw/scripts/cdx.py py skill/chemdraw/assets/house-styles/polymer_chemistry/replica/polymer_chemistry-04/replay.py NEW_DIR
python skill/chemdraw/scripts/cdx.py draw ... --render   (for brief-a, brief-c and brief-mech)
```

`replay.py` draws only `brief.json` (panel b), as in the JACS Au replica. The other panels are drawn with `cdx.py draw` on their briefs.

## Convention check

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| each mechanism step in its own rounded box with a coloured outline (blue, orange, green dashed) | three boxes | no box or frame; the tool has no frame object | no |
| coloured box title above each step ((a) Photoactivation, (b) RAFT Equilibrium, (c) Reversible termination) | blue, orange, green titles | no title on panels (a), (b) or (c) of `rendered.png`; only the propagation panel has a black title | no |
| equilibria drawn with long half-headed double arrows | yes, including the hv step in (a) | (b) and (c) are half-headed `reversible` arrows; (a) is a one-way solid arrow with hv, while the paper's hv step is an equilibrium; arrow length not checked against the card | no |
| radicals drawn as dots | yes | `Radical="Doublet"` is written on the radical nodes, but no dot appears in the native PNG | no |
| monomer addition as a curved arrow from the radical to M | one curved arrow from Pm or Pn to M, with M inside the arc | one curved one-electron arrow from the radical carbon to the CH2 of methyl methacrylate; the paper's head sits on the radical side, so direction and endpoint are unconfirmed | no |
| curved arrow labelled M | "M" under the arrow | no label; the tool has no arrow label | no |
| chains abbreviated Pm and Pn, RAFT group as Z | letters | R for Z; small model esters for Pm and Pn | no |
| `show_lone_pairs` false | none drawn | none drawn | yes |
| `intermediate_label_style` none | none | none | yes |
| `ts_marker` none | none | none | yes |
| `reagent_text_color` #000000 | hv in black | hv in black | yes |
| `arrow_style` plain | no plain arrow in crop 04; the only reagent arrow (hv) is an equilibrium | solid arrow for hv, the wrong arrow type for this step | no |

Matched 4 of 12 conventions after the audit below (the first version claimed 7). Two top-level conventions in the card, `show_plus_sign` and `substrate_layout: inline_plus`, do not appear in crop 04 (the crop draws no reactant pair with a plus), so they are not counted. The card's measured bond-to-cap-height ratio of 2.4 cannot be checked on this crop, because crop 04 has no measured bond length. The replica uses the RSC preset with a 7 pt label on a 12.2 pt bond, which gives a similar ratio, but this is not a check against the crop.

## Differences from the paper

- Layout: the paper has three boxes with titles, and the propagation arrows sit inside (a) and (b). The replica has four separate renders on a grid, and the propagation arrow is in its own cell, not inside (a) or (b).
- No boxes, dashed outlines or coloured titles. The card's colours (#4068A8, #F89040, green dashed) are not applied to anything.
- No radical dots in the native render, although the radical nodes are marked as doublets.
- Z and Pm are replaced by R and by small model esters. Pm and Pn are not distinguished from each other by letter, only by ester group.
- Monomer is methyl methacrylate, not PEG methacrylate.
- Panel (b): in the paper Pm radical sits above the equilibrium arrow and the Pn radical sits below it with the curved arrow. The replica puts both radicals on the left as reactants with a plus sign between them. The `above` field of draw_figure only takes text lines, so the structure cannot be placed above the arrow.
- Panel (c): in the paper the Z radical is above the equilibrium arrow. The replica places it as a reactant on the left, with a plus sign.
- Plus signs are present in the replica (panels a, b and c) and absent from the paper's crop.
- Orientation: the paper draws Z on the left and Pm on the right of the RAFT agent. The tool drew the RAFT agent with the Pm end on the left and the R end on the right. The SMILES does not control which end is on which side.
- The step `hv` is drawn as "hv" in the replica. The crop has the Greek nu, which is hard to check at this scale.
- The propagation panel carries the title "PI-RAFT propagation" from the brief. The paper has no such title.

## Tool gaps

- No frame or box object around a step or a group of steps: no rounded rectangles, no outline colour, no dashed outline, and no coloured title per box. The card's mechanism box conventions therefore cannot be realised. Only the curved-arrow colour and weight are applied by the tools.
- No multi-panel layout in one brief. A figure of several sub-schemes placed on a grid cannot be drawn in one file; each row is a separate call, and the panels were assembled outside the tool.
- Radical dots: draw_figure writes `Radical="Doublet"` on the radical nodes, but the native render shows no dot for the scheme or mechanism briefs.
- Structures above the arrow: draw_figure takes text lines in `above` and `below`. `render_scheme` accepts bare structure IDs there, but draw_figure does not, so the Pm radical and Z radical of the paper cannot sit above the equilibrium arrows.
- A mechanism brief refuses a step without `moves`. An equilibrium with no electron-pushing arrows, as in panels (a), (b) and (c), cannot share a mechanism brief with the curved propagation arrow; those steps have to go in a scheme brief.
- Arrow labels: a curved arrow in a mechanism brief has no text label, so the "M" beside the propagation arrow cannot be drawn.
- Placeholder letters: the Z and P_m letters cannot be written inside a structure. A `*` atom renders as R, and the tool reports that it cannot balance the step.
- Orientation control: there is no field for the drawn direction of a substituent or chain. The RAFT agent came out with the Pm end on the left, reverse to the paper.
- Line weight: the house style applies only the base preset line widths (0.45 pt bonds on a 12.2 pt bond, which is 0.037 of the bond length). The card's measured `line_width_over_bond_length` of 0.09 is not applied, and the replica's bonds look thinner than the crop's.

## Audit

Checked against `reference.png`, `rendered.png` (enlarged), the card `toolkit/cdxml_toolkit/publication/house_styles/polymer_chemistry.json` and the toolkit code (`mcp_runtime/figure_draw.py`, `figure_mechanism.py`, `render/renderer.py`).

Overclaims corrected:

- Equilibria row: the hv step in panel (a) is a one-way solid arrow. The crop draws it as an equilibrium with half heads.
- Arrow style row: crop 04 has no plain arrow. The only reagent arrow is the hv equilibrium, so `plain` is not evidenced here and the replica's solid arrow is the wrong type.
- Monomer addition row: the arc's direction and endpoint are not confirmed. In the crop the arc's head sits at the radical side beside its label and M is inside the arc; the replica's head lands on the CH2 of the monomer, and M is not drawn.
- Titles: `rendered.png` shows one title, not three box titles. The earlier table text "black titles per drawing" was wrong.
- Scope: "reproduced" and "as chemistry only" overstated the fit. Panel (a) has the wrong arrow type, and the RAFT agent is reversed (Pm end on the left), as the Differences section already says.
- Propagation: the replica draws a product that the crop does not show.

Corrected count: 4 of 12. The matches are `show_lone_pairs`, `intermediate_label_style`, `ts_marker` and `reagent_text_color`. Equilibrium, curved-arrow, arrow-style and title rows are not matched.

Tool gaps the replicator did not list:

- Arrow length: the card's `arrow_length_over_bond_length` (7.0) is read by no code path. Arrows are sized from their content, with a minimum of 5 bond lengths (`render/renderer.py`, phase 2), so equilibrium arrows cannot be set to the card's proportion.
- Proportions: `bond_length_over_cap_height` (2.4) and `line_width_over_bond_length` (0.09) are also unread. The house style takes the RSC preset values instead (12.2 pt bond, 7 pt label, 0.45 pt line). The line-weight gap the replicator reported is real.
- Figure-type settings: the card's mechanism colours and arrow weights are applied only when `kind` is "mechanism" (`figure_mechanism.py`). Panels drawn as schemes, which is what panels (a) to (c) are, receive none of them.
- Not a tool gap: `reversible` is available for step (a) in a scheme brief. The replica chose `solid` in `brief-a.json`, so this is an authoring error and should be fixed in that brief.
