# polymer_chemistry replica: crop 05 (Kodger et al., Polym. Chem. 2022, Figure 1)

## Source

- Paper: Kodger et al., Polym. Chem. 2022, "Linear-bottlebrush-linear triblock copolymer towards architecturally tunable soft materials".
- DOI: 10.1039/d2py00841f
- Licence: CC BY 3.0 (from the house-style card).
- Figure: Figure 1, the anionic synthesis of PS-b-bbPDMS-b-PS in three panels (1), (2), (3). Evidence crop: `evidence/polymer_chemistry-05.png`.
- House style: `polymer_chemistry` (base preset `rsc`). Figure type: `polymer`.

## What is reproduced

Only panel (2), first step: the monomer conversion D3 (hexamethylcyclotrisiloxane) to D3V (trivinyl-trimethylcyclotrisiloxane), drawn as one plain solid arrow with no conditions, as in the figure. Both structures are given as SMILES and checked with RDKit (D3 C6H18O3Si3, D3V C9H18O3Si3).

Not reproduced: every other step of the figure. The polymer species (the sec-BuLi/styrene anion with its 60-unit PS block, the living PDMS chains with 4 and 172 units, the end-functionalised chains, the coupled triblock and the grafted bottlebrush) have no SMILES, and an oligomer SMILES would misstate the degree of polymerisation. The reagents that act on them (n-BuLi, ClSiH, CMPDMS, DPE, Pt(0)) are text or structures attached to steps that cannot be drawn, so they are left out too.

## Convention and signature check

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| polymer: repeat unit in round brackets, DP subscript lower right (30, 60, 4, 172) | round brackets with DP subscripts | no polymer drawn | no |
| polymer: end groups drawn explicitly on both sides (n-Bu, SiMe2H, sec-Bu, CMPDMS and DPE caps) | yes, on panels (1) and (2) | not drawn | no |
| polymer: block colour coding (PS red #C80000, PDMS blue #0050D0, magenta #F800F8 pendant dots) | yes, red PS, blue grafts, magenta dots on the backbone | not drawn, black only | no |
| polymer: monomer colours carried into polymer segments | not in this crop (the monomers are black) | black | n/a |
| polymer: no highlight fill and no variation colour | none | none | n/a |
| compound labels plain text under the structure, subscript 3 (compound_label_face null) | D3 and D3V, plain, subscript 3 | D₃ and D₃V, plain, subscript 3 | yes for plain text and subscript 3 only; the card face is null and the font is not verified |
| arrow style plain, solid, no head decoration | plain solid arrow | plain solid arrow | yes |
| no conditions drawn when the figure gives none | none above or below | none (the brief has no above or below lines) | yes |
| arrow length about 7 bond lengths (card median) | about 2.2 bond lengths (67 px over a 30 px Si-O bond, measured on reference.png) | about 5.0 bond lengths (254 px over a 51 px bond, measured on rendered.png) | no |
| structure drawing: ring orientation, Me and vinyl placement | D3 with six methyls; D3V with three vinyls and three methyls, one vinyl and one methyl per Si; pointy-top ring (bond directions about 30 degrees mod 60) | same atom counts and one vinyl and one methyl per Si, but the ring is rotated about 15 degrees (bond directions about 45 degrees mod 60) and the substituents point in different directions | no |
| label font Arial (card) | sans-serif | RSC preset font, not checked against Arial | not verified |
| bond length over cap height 2.4 (card) | about 2.2 (30 px bond over about 14 px cap height) | about 2.7 (51 px bond over about 19 px cap height) | no (the two differ by about 20%, and neither is clearly 2.4) |
| line width over bond length 0.09 (card) | about 0.04 (arrow shaft about 1.3 px over a 30 px bond) | about 0.04 (arrow shaft about 2.0 px over a 51 px bond) | no (both about half the card value) |
| substrate_layout inline plus, show_plus_sign, kekule rings, CF3 abbreviation | not present in this step | not present | n/a |
| catalysts or initiators as structures above the arrow | n-BuLi and sec-BuLi appear as text in this crop | not present | n/a |

## Differences from the paper

- The replica is one step of nine. The panel's polymer chemistry (living anionic chains, end functionalisation, halogen exchange, coupling, hydrosilylation grafting) is absent, and so is the panel (1) and (3) structure of the final triblock.
- No repeat-unit brackets, DP subscripts, wavy cartoon chains, colour coding by block, or grouping brackets with (1), (2), (3).
- The paper's D3 to D3V arrow has no reagent, and the drawn structures do not balance: the replica reports the reactants as short by C3 (three methyls turned into three vinyl groups). The replica keeps the arrow exactly as drawn and does not add a reagent, so the warning stays in the report.
- Compound labels are the figure's own text, D₃ and D₃V. The first attempt used D3 and D3V with no subscript; the second attempt (the saved brief) matches the figure's subscript.
- Proportions were first judged by eye. The Audit below measured them in pixels, and the arrow length, line width, cap height and ring orientation do not match either the paper or the card.

## Tool gaps

- No polymer drawer: `draw_figure` has no kind for polymers, so repeat units cannot be drawn in round brackets with a DP or n subscript at the lower right of the bracket.
- No way to draw a polymer end group or a polymer chain whose length is only a degree of polymerisation; every species needs a SMILES, and placeholders such as Pm or Z (used in the mechanism crop) are not accepted.
- No wavy or cartoon chain primitive. The figure's red PS, blue PDMS graft and black backbone chains, with curly ends, cannot be drawn.
- Colour per block or per segment of a product is not supported for polymers; `substrate_colors` colours substrates only.
- No vertical grouping brackets with step numbers (1), (2), (3) placed beside a multi-row scheme, and no elbow arrow that returns a product to an earlier row.
- No way to record that a source arrow omits a reagent on purpose; the balance check names the missing C3 correctly, but the report has no field for an acknowledged omission.

## Files

- `reference.png`: the evidence crop, identical to `evidence/polymer_chemistry-05.png`. It is the whole of Figure 1 (783 x 1304 px), not the single step; the D3 to D3V arrow sits at about x 198 to 265, y 484 to 496 in it.
- `brief.json`: the brief that was drawn (second attempt, subscript labels).
- `rendered.png`: the ChemDraw render of that brief, 843 x 280 px, 19.8 KB.
- `replay.py`: offline replay of the brief with `draw_figure`.

## Audit

Re-checked against `reference.png`, `rendered.png`, `brief.json`, the card at `toolkit/cdxml_toolkit/publication/house_styles/polymer_chemistry.json` and RDKit. Pixel values come from connected-component centres and ink profiles, so they are good to about 10%. The paper values refer to the D3 to D3V step inside the full Figure 1 image.

Overclaims corrected in the table:

- Arrow length: the paper arrow is about 2.2 bond lengths, not 8, and the replica arrow is about 5.0, not 8. Neither meets the card median of 7.
- Structure drawing: the replica ring is rotated about 15 degrees from the paper ring, and the methyl and vinyl directions on each Si differ. Only the atom counts and the one-vinyl-one-methyl-per-Si pattern match.
- Line width and bond length over cap height were marked not measured. Measured, the line-to-bond ratio is about 0.04 on both the paper and the replica against the card's 0.09, and bond over cap height is about 2.2 on the paper and about 2.7 on the replica against the card's 2.4.
- Compound labels: plain text and subscript 3 match. The card's compound_label_face is null, so there is no house value to match, and Arial is unverified. The label sits about 1.0 bond below the lowest atom on the paper and about 0.65 bond below it on the replica.

Corrected matched count: 3 of 12 (compound labels, arrow style, no conditions), down from 5. Arrow style (solid, filled head, no decoration) and the absence of conditions do match.

Layout differences not in the table: the arrow-to-structure gaps are about 0.3 and 0.4 bond on the paper and about 1.8 and 1.2 bonds on the replica.

Tool gaps the replicator missed:

- No ring-orientation or substituent-direction control. The brief in `brief.json` carries only SMILES, so the ring comes out rotated and the methyl and vinyl directions differ from the paper.
- No arrow-length or arrow-to-structure gap setting. The brief has only `steps` and `max_width`, and the replica arrow comes out at about 5 bond lengths, not the card's 7.
- No bond-length, line-width, cap-height or label-gap setting, so the card's 2.4 and 0.09 ratios cannot be requested for a figure.
- No label-font selection in the brief, so the card's Arial cannot be requested.

Checked and correct: the D3 and D3V formulas (C6H18O3Si3 and C9H18O3Si3, RDKit) and the C3 imbalance they imply; the polymer rows marked no; the card's red and blue values are close to the paper's pixels (about #C20109 and #0952CC against #C80000 and #0050D0). The seven gaps the replicator listed are real.
