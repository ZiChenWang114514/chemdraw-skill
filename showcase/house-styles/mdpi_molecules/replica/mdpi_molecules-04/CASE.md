# Molecules (MDPI): proposed Ni catalytic cycle, Scheme 6 (left cycle)

Source: Wu et al., Molecules 2024 (Nickel-catalyzed reductive cyanation of aryl halides and epoxides with cyanogen bromide), Scheme 6. DOI [10.3390/molecules29246016](https://doi.org/10.3390/molecules29246016). Licence CC BY 4.0, as recorded on the house-style card. `reference.png` is a copy of `evidence/mdpi_molecules-04.png`.

Figure type: `catalytic_cycle` of the `mdpi_molecules` card (house style on the acs1996 base preset, `layout: "catalytic-cycle"`).

## What is reproduced

The left-hand nickel cycle of Scheme 6, as one closed loop of five steps:

- A (Ni) with ArX (1) gives B (Ar-Ni-Br), the oxidative addition;
- B with Zn gives C (Ar-Ni), reduction by zinc;
- C with BrCN gives D (Ni bearing CN, Br and Ar);
- D gives ArCN (2) and E (NiBr), reductive elimination;
- E with Zn gives A again.

The right-hand manganese cycle (F to I), the epoxide 3 and bromohydrin 6 side path and the rearrangement to isocyanate 4 are not drawn. The card's catalytic-cycle section describes one circle; the crop has two cycles side by side. See Tool gaps.

Structures: the crop writes Ar generically and the R group of 3, 4 and 6 is not reproduced. Ar is written as phenyl because the tool needs a concrete SMILES. The metals are bare atoms with no ligands:

| Species | SMILES |
| --- | --- |
| A | `[Ni]` |
| 1 (ArX, text only) | `Brc1ccccc1` |
| B | `Br[Ni]c1ccccc1` |
| C | `[Ni]c1ccccc1` |
| BrCN | `BrC#N` |
| D | `N#C[Ni](Br)c1ccccc1` |
| 2 (ArCN, text only) | `N#Cc1ccccc1` |
| E | `Br[Ni]` |

All five steps pass the atom balance check. Zinc is `[Zn]` and the zinc by-product is `Br[Zn]`, both listed as species. Conditions are the labels on the arrows as the crop gives them: Ar-X (1), Zn, BrCN, Zn(II) and the product labels; no solvent or temperature appears in the crop.

Build: `brief.json` in this folder, drawn with `cdx.py draw brief.json <new>.cdxml --render`. `replay.py` redraws it offline. The result was rendered with desktop ChemDraw (`rendered.png`, downscaled to 1200 px wide).

The report has `checks_passed: false` because the readback finds seven species from the brief missing from the drawing (the reagents, the by-product and the product 2). This is the catalytic-cycle layout limit listed under Tool gaps, not a layout failure.

## Convention and signature check

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| cycle_shape circle | intermediates on a circle, arrows as arcs | intermediates on a regular pentagon, straight chords | no |
| cycle_arrow_color #000000 | black cycle arrows | black cycle arrows | yes |
| curved_arrow_color #000000 | thin black arcs | no curved arrows; the tool applies curved_arrow_color only to mechanisms | no |
| center_label false | no centre label | no centre label | yes |
| step_names false | no step names | no step names | yes |
| intermediate_label_style bold_letter | bold capital letters under each species | bold capital letters A to E under each species (bold comes from compound_label_face; the tool skips this key) | yes |
| signature: thin black arcs with small arrowheads | arcs with small arrowheads | straight chords with arrowheads | no |
| signature: reagents enter on short curved arrows | Ar-X (1), Zn, BrCN on curved arrows; Zn(II) leaves on one | text labels on the chord arrows, no curved arrows and no structures | no |
| signature: intermediate letters bold blue #0000FF | letters A to E in blue | letters in black | no |
| top-level compound_label_color #000000 | black compound labels (conflicts with the blue letters above) | black | yes |
| top-level compound_label_face bold | bold labels (compound numbers 1 and 2 bold) | only the letters A to E are bold; Ar-X (1) and PhCN (2) are plain text | no |
| top-level new_bond_color #FF0000 | no red bonds in the cycle; all bonds black | bonds formed in B and D shown red | no |
| top-level reagent_text_color #000000 | black reagent text | black reagent text | yes |
| top-level arrow_style plain | plain arrows | plain arrows | yes |
| top-level conditions_split reagents_above_solvent_below | reagents above the arrow, the zinc by-product below | the tool skips this rule ("kept as given"); labels are placed radially, outside or inside the ring; BrCN is above in the brief but drawn below its arrow; on step 2 the reagent Zn sits lower than its by-product Zn(II) | no |
| top-level compound labels slightly smaller than atom labels | labels about 0.85 of atom-label cap height | labels bold, size not measured | not measured |

Matched: 7 of 16 rows after the audit below (the first pass said 8 of 16).

## Differences from the paper

- Layout: the paper draws a circle of curved arrows, with the intermediates at the points of that circle. The replica is a regular pentagon with straight arrows.
- Ar is phenyl in the replica and generic Ar in the paper. The paper's product is written Ar-CN, the replica PhCN.
- Reagents ArX (1), Zn, BrCN and the by-product Zn(II) are text labels on the arrows. In the paper they are structures or symbols on curved arrows. Product 2 is text, not a bold compound label.
- Oxidation states (Ni0, NiII, NiI, NiIII in superscript roman numerals) are absent; the metal atoms are bare Ni.
- Letters A to E are black in the replica and bold blue in the paper.
- Bonds formed in B and D are red in the replica (Ni-Br, Ni-Ar and the Ni-CN carbon bond); all bonds are black in the paper.
- The right-hand Mn cycle, the epoxide and bromohydrin 6 path and the rearrangement to 4 are omitted.
- The paper's frame is not drawn.

## Tool gaps

- The catalytic-cycle layout takes only the first substrate of each step as a ring structure (`_layout_catalytic_cycle` in `toolkit/cdxml_toolkit/render/renderer.py` uses `step.substrates[0]`). Other substrates, the species leaving the loop and the zinc by-product are not drawn as structures, so the readback lists them as missing. The guide says entering reactants and departing products go on radial in and out arrows; that is not what the code draws.
- Cycle arrows are straight chords between neighbouring intermediates. There is no circle layout and no curved arrow along the circumference, although the guide describes curved arrows.
- Only the cycle arrow colour is applied from the card. The bold blue intermediate letters, the curved reagent arrows and the bold product labels cannot be set.
- Oxidation-state superscripts on metal atoms (roman numerals) cannot be written for a species.
- `new_bond_color` cannot be turned off for a catalytic-cycle figure. It is applied to every bond the atom mapping finds as formed in a cycle step, which colours Ni bonds red where the paper has none.
- One closed loop per figure. No second cycle, no side path from an epoxide to a bromohydrin and no rearrangement arrow.
- Radial text labels can sit far from their arrow (Ar-X (1) and PhCN (2) appear at the corners of the figure).

## Audit

Second pass against `reference.png`, `rendered.png`, the card, and the drawing code (`figure_house.py`, `renderer.py` `_layout_catalytic_cycle`).

Overclaims corrected in the table:

- compound_label_face: no. Only the intermediate letters are bold. The compound numbers 1 and 2 are plain text in the replica and bold in the paper.
- conditions_split: no. `figure_house.py` records this rule as skipped ("the brief's above/below lines are kept as given"), and labels are placed radially, outside or inside the ring. BrCN is above in the brief but is drawn below its arrow. On step 2 the reagent Zn sits lower than its by-product Zn(II).
- curved_arrow_color: no, not partial. There are no curved arrows, and the tool applies curved_arrow_color only to mechanisms.
- signature thin black arcs: no, not partial. The cycle arrows are straight chords.
- intermediate_label_style: kept as yes for the look of the letters (bold, capital, under each species). The tool skips this key; the bold comes from compound_label_face.
- compound_label_color: changed to yes. The replica's compound labels are black, as the card states. The conflict with the blue letters is a separate row.

Matched count after the audit: 7 of 16 (was 8). The compound-label size row stays not measured.

Tool gaps the first pass missed or got wrong:

- conditions_split is not implemented. Above and below cannot follow the card rule; placement is radial only.
- compound_label_color paints every compound label one colour, so numbered compounds (black in the paper) and intermediate letters (blue) cannot differ. The first pass said there was no way to colour the letters; that is only partly true.
- No generic Ar. Every species needs a concrete SMILES, so the paper's Ar is drawn as Ph and the product becomes PhCN where the paper has Ar-CN. The card's abbreviation list holds Ph, not Ar.
- Brief labels are plain strings, so superscripts (Zn^II, Ni^I) cannot be entered in a catalytic-cycle brief. `figure_tools` has superscript text runs, but the cycle layout does not take them.
- The grey frame (#BDBDBD) around the paper's panel has no card key and no drawing support.
- The brief species `ZnBr2` has the SMILES `Br[Zn]`, which is ZnBr. The id should be corrected if the readback or a label uses it.

Not verified here: `checks_passed: false` and the seven missing structures. No validation.json is in this folder and replay.py was not run. The atom counts of all five steps balance by hand.
