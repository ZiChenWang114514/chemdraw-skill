# Rowett et al.: Figure 2B reaction scheme (wiley_angew, crop 02)

Source: A. Rowett, B. Sweeting, D. M. Heard and C. W. Lennox, *Angew. Chem. Int. Ed.* **2024**, *63*, e202400570. DOI: [10.1002/anie.202400570](https://doi.org/10.1002/anie.202400570).

Licence: CC BY 4.0, reference crop reproduced under that licence. Card: `skill/chemdraw/assets/house-styles/wiley_angew/` (house style `wiley_angew`, base preset `wiley`).

Figure type: `reaction_scheme`. The card has no `figure_types` section, so only its top-level conventions apply (see Differences).

## What is reproduced

The single reaction of Figure 2B: 4-fluoroacetophenone (1a) and benzyl alcohol (2a) give benzyl 4-fluorobenzoate (3a), with the reagent and base above the arrow and solvent and temperature below. The reaction arrow, the bold compound numbers 1a, 2a and 3a, and the inline plus sign are all drawn. No yield appears in the crop and none is drawn. The reagent is the placeholder "Halogenation reagent “X”" from the crop and is not given a structure.

| ID | Structure (SMILES in brief.json) |
| --- | --- |
| 1a | `CC(=O)c1ccc(F)cc1` |
| 2a | `OCc1ccccc1` |
| 3a | `O=C(OCc1ccccc1)c1ccc(F)cc1` |

SMILES were checked with RDKit (formulas C8H7FO, C7H8O, C14H11FO2). They match the structures in the crop. OCSR was not run; the structures are simple and clear in the crop.

## Replay

```
python skill/chemdraw/scripts/cdx.py py skill/chemdraw/assets/house-styles/wiley_angew/replica/wiley_angew-02/replay.py NEW_DIR
python skill/chemdraw/scripts/cdx.py render NEW_DIR/figure.cdxml
```

`brief.json` is the saved brief (attempt 1). `rendered.png` is the desktop ChemDraw rendering of that brief, downscaled to 1200 px wide.

## Attempts

- Attempt 1 (`brief.json`): rendered OK, readback matched (3 structures), `checks_passed` false. The layout is 470 pt wide against a 427 pt budget, and the balance check reports that the products lack CH4.
- Attempt 2 (`max_width` 430): the drawing is still 470 pt. Relayout breaks condition lines only after commas, and the reagent line has none, so the arrow stays long. Not kept. The Audit shows that splitting the reagent into separate lines does narrow it.

## Convention check

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| compound_label_face bold | bold 1a, 2a, 3a | bold 1a, 2a, 3a | yes |
| compound_label_color #000000 | black | black | yes |
| conditions_split reagents above, solvent and temperature below | reagent and base above, solvent and time below | same split | yes |
| substrate_layout inline_plus | 1a + 2a inline | 1a + 2a inline | yes |
| aromatic_rings kekule | Kekule rings | Kekule rings | yes |
| show_plus_sign true | plus sign present (light grey) | plus sign present (black) | presence only: yes; colour no |
| label_font Arial or Helvetica | condition text looks like a humanist sans, not confirmed as Arial | Arial (ACS label font) | no (unverified) |
| arrow_style plain | grey arrow, about as heavy as the bonds, filled head | thin black line (about a third of bond weight), small black head | no |
| reagent_text_color #000000 | "Halogenation reagent “X”" in purple | black | no |
| substrate_colors (null on card, evidence shows red and blue) | 1a red, 2a blue, product acyl red and O-benzyl blue | all black | no |
| abbreviate_groups (null on card, evidence shows Me label) | "Me" label on the ketone | methyl drawn as a bond to a carbon | no |
| yield_format {value}% (no yield in crop) | no yield | none drawn | n/a |

Matched: 6 of the 11 applicable rows (see Audit). The arrow, label font, reagent colour, substrate colours and abbreviation rows do not match. Rows whose card value is null or contradicted by the evidence are counted as not matched, not as claims.

## Differences from the paper

- Colour: the paper colours 1a red and 2a blue, and the product's acyl part red with the ester O and benzyl group blue. The replica is all black, because the card sets no substrate colours.
- Reagent line: the paper sets "Halogenation reagent “X”" in purple. The replica sets it black, as the card says.
- Arrow: the paper uses a grey arrow, about as heavy as the bonds, with a filled head. The replica uses a thin black line with a small black head.
- Text style: the paper sets "(equiv.)" in italics. The replica sets it upright, and the brief has no italic option.
- Plus sign: light grey in the paper, black in the replica. The colour cannot be set (see Tool gaps).
- Methyl: the paper shows the ketone methyl as the label "Me". The replica draws a CH3 bond with a carbon atom.
- Width and spacing: the paper scheme is more compact. The replica is 470 pt wide against a 427 pt budget, so the lint check does not pass. Its arrow is about 11 bond lengths long against about 6 in the crop, because the unbroken reagent line sets the arrow length.
- Balance: the crop equation omits the by-product. The tool names CH4 as missing (C8H7FO + C7H8O = C14H11FO2 + CH4 balances), so `balanced` is false. The crop does not state a by-product; a haloform-type CHX3 pathway would be a guess, not something the source shows.
- Proportions: measured on the supplied PNGs (ink thresholds, about 10% error). Bond to line width is about 0.1 in both. Bond to cap height is about 2 in both. The arrow is the one proportion that differs (see Audit).

## Tool gaps

- Per-substrate colour goes through `substrate_colors`, which colours whole substrates and never products. The product split (acyl part red, O-benzyl part blue) cannot be drawn. The 1a and 2a colours could be drawn by setting `substrate_colors` on the card, which leaves it null.
- `reagent_text_color` colours every above-arrow and below-arrow line, so the purple reagent line cannot be coloured alone. The brief has no per-line colour.
- The plus-sign colour cannot be set (`show_plus_sign` is a boolean).
- `arrow_style` supports only plain or bold. Bold multiplies the line width by 1.5. Arrow colour and a filled head cannot be set.
- The arrow length cannot be set directly. It is the longest condition line plus 10 pt, with a minimum of 5 bond lengths. The card's `measured` block (bond, cap height, arrow length) is not read by the drawing code.
- Condition lines are broken only after commas. A long line without a comma sets the width and cannot be wrapped by the tool; splitting it by hand into separate list entries does work.
- Abbreviations: `Me` is in the table. Setting `abbreviate_groups` to `["Me"]` on the card contracts the one methyl in this scheme (checked in an audit probe). It also raises a `crowded_plus` lint warning, and the tool cannot move the plus sign. A per-atom choice is needed only when several methyls are present.
- Italic runs in condition text are not available. Only the letter labels use italics.
- A placeholder reagent ("X") cannot be drawn as a species, so balance reporting always flags the by-product for such schemes.

## Audit

Second pass on the supplied PNGs and the toolkit code, with probe runs of `draw_figure` on a scratch copy of the brief and card. Only this file was changed. The table, Differences, Attempts, Tool gaps and the matched count were corrected; the replay, brief and images are as they were.

Overclaims found:

- The arrow row was marked partial. It is not matched. The crop's arrow is grey, with a filled head and about the same ink weight as the bonds. The replica's arrow is black, with a small head and about a third of the bond weight. The card's value "plain" is itself contradicted by the Figure 3 evidence, which records a grey filled arrow.
- The label-font row was marked yes without a check. It is unconfirmed. The condition text in the crop looks like a humanist sans rather than Arial.
- The plus-sign row was marked yes. Only the presence matches. The crop's plus is light grey (darkest pixel about 114 of 255) and the replica's is black.
- "A single-step scheme cannot be narrowed" is wrong. In a probe with the reagent split into three list entries, the drawing measured 427.3 pt against a budget of 426.9 pt. It is still 0.4 pt over, so `checks_passed` stays false.
- The abbreviation gap is misdiagnosed. In a probe with `abbreviate_groups` set to `["Me"]` on a copy of the card, one group was contracted. The remaining problem is a `crowded_plus` lint warning, not a missing request.
- The substrate-colour gap mixes two things. The 1a and 2a colours come from a null card setting, not a tool limit. Only the product split is a tool gap.
- The balance note named a haloform-type CHX3 by-product as "the real" one. The crop shows no by-product, so that is a guess. The CH4 flag itself is right.
- "7 of the 9 claimed items" does not match the table, which has 11 applicable rows.
- "More compact" understates the width problem. The replica's arrow is about 11 bond lengths long (418 px over a bond of about 37 px). The crop's arrow is about 6 (257 px over about 42 px).

Corrected matched count: 6 of 11 applicable rows (compound label bold, label colour black, conditions split, inline plus, Kekule rings, plus-sign presence). The replicator claimed 7.

Tool gaps the replicator missed:

- Italic runs in condition text. The crop sets "(equiv.)" in italics, and the brief cannot request it.
- Manual line splitting. Separate list entries narrow the scheme (see above). This is the lever the replicator did not try.
- Arrow length. It cannot be set, and the card's measured arrow ratio is not used by the drawing code.
- `bold` arrows. This is the only arrow-weight option. It was not tested against this crop and may be closer to the crop's weight than `plain` (an inference, not a measurement).
- Crowded-plus lint. Nothing in the brief can fix it when an abbreviation sits next to the plus sign.
- Condition-text font. It is set by the preset, and the card and brief cannot override it.

Card issues (outside this case, not edited): `wiley_angew.json` nulls `substrate_colors` and `abbreviate_groups`, and sets `reagent_text_color` to #000000 and `arrow_style` to plain. Its own evidence records red and blue substrates, Me, NO2 and OMe labels, a purple reagent and a grey filled arrow. Its `arrow_length_over_bond_length` of 8.4 comes from Figure 3; this scheme's arrow is about 6.1.

Method: bond lengths were taken from ring widths (replica about 37 px, crop about 42 px). Line weight came from ink-profile sums across a bond (about 0.10 in both). Arrow length and ink weight came from the longest horizontal ink run and its vertical profile. Colours came from the mean RGB of the plus sign and reagent text.
