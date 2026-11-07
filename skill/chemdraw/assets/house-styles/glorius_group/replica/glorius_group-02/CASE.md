# Glorius group, Figure 1E: general reaction and concept panel (crop 02)

Source: Gutierrez, Glorius et al., "gamma-Amino alcohols via energy transfer enabled Brook rearrangement", *J. Am. Chem. Soc.* 2024. DOI: [10.1021/jacs.4c01667](https://doi.org/10.1021/jacs.4c01667). Licence: CC BY 4.0. Reference crop: Figure 1E (`reference.png`, copy of `evidence/glorius_group-02.png`).

Drawing style: the `glorius_group` house style (base preset ACS Document 1996), figure type `reaction_scheme` for the dashed general reaction and `mechanism` for the concept panel. Card: `toolkit/cdxml_toolkit/publication/house_styles/glorius_group.json`.

## What is reproduced

1. The general reaction in the dashed box (`brief.json`, `rendered.png`): alkene 1 plus oxime carbonate 2 give imine ether 3 under light and EnT. The generic groups are instantiated: Ar = Ph (as in the concept panel above it), R = CH3, R' = CH3 (Si bears Me, R' and Me, so R' is drawn as Me). Structures were read by eye from the 3x zoomed crop and written as SMILES. RDKit gives C3H6 (1), C18H21NO3Si (2) and C20H27NOSi (3); with CO2 as a by-product the step balances (C21 to C21, H27 to H27).
2. The concept panel above (`brief_top.json`, `rendered_top.png`, separate draft, not the main replica): oxime carbonate 2 fragments to the iminyl radical Ph2C=N•, CO2 and the O-centred radical 2' (`•O-CH2-SiMe2R'`); then the Brook step to the C-centred radical 2'' (`•CH2-O-SiMe2R'`). This draft has a tool defect (see Differences and Tool gaps): the radical centres are drawn as closed-shell.

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| compound_label_face bold | labels 1, 2, 3 bold | bold | no (not verifiable: the labels are clipped at the bottom edge of reference.png) |
| compound_label_color #000000 | black | black | no (not verifiable: the labels are clipped in reference.png) |
| compound_label_italic_suffix false | no suffix | no suffix | yes |
| substrate_layout inline_plus | 1 + 2 on one line | 1 + 2 on one line | yes |
| show_plus_sign true | "+" between 1 and 2 | "+" between 1 and 2 | yes |
| reagent_text_color #000000 | symbols only, no text | "hv, EnT" in black | partial |
| arrow_style plain | plain line arrow | plain arrow | yes |
| conditions_split reagents_above_solvent_below | nothing below the arrow | all conditions above, none below | yes |
| abbreviate_groups (Ph, Me) | Me and Ph in the top panel; Ar and R in the bottom | Me and Ph as labels; Ar and R not expressible | partial |
| aromatic_rings kekule | kekule rings in the top panel | rings are abbreviated as Ph, not visible | no |
| yield_placement, yield_format | no yield in the crop | no yield | n/a |
| new_bond_color null | no new-bond colour; the formed C-C bond is bold black | no colour; bond not bold | no (colour matches, but the formed bond is bold in the paper and not in the replica) |
| substrate_colors #2C0001, #0203FE | alkene 1 black; reagent 2 split: Ar and N dark red, O-CH2-SiMe2R' blue | whole reagent 2 blue; alkene 1 dark red; product black | no |
| highlight_fill null (reaction_scheme) | mint dot #92F2C4 on the reacting CH2 of 2 and of 3 | none | no |
| variation_color #0203FE | variable silyl part blue | whole reagent 2 blue | partial |
| dashed rectangle around a sub-scheme | dashed box around 1 + 2 to 3 | none | no |
| bond length / label cap height 2.2 | bond 90 px, cap 41 px in crop 01; crop 02 not measured | 14.4 pt bond, 10 pt label (about 2.0) | no (crop 02 has no bond or cap measurement in brief.json, so 2.2 is from crop 01 only; the replica's own figures give 14.4 / (10 x 0.716) = 2.0) |
| line width / bond length 0.075 | about 0.08 (crop 01 measurement) | 0.6 pt / 14.4 pt = 0.042 | no |
| arrow length / bond length 13.4 (median) | not measured in crop 02 | 72 pt / 14.4 pt = 5.0 | no |
| energy-transfer lamp #31BCFA with circled EnT (mechanism) | lamp icon and circled EnT with circular arrow on the arrow | "hv, EnT" text only | no |
| straight arrows, no curved arrows (mechanism) | straight arrows for the radical steps | straight arrows | yes (arrow type only; the paper's Brook step is vertical, the replica's is horizontal; the top panel's chemistry is wrong, see Audit) |
| italic captions under radical structures (mechanism) | "Persistent radical", "Transient radical" in italic under the structures | no captions | no |
| Brook rearrangement bold italic navy label | bold italic navy #01027F | plain black text | no |
| mint dot on the migrating CH2 (mechanism) | mint dot #92F2C4 on the CH2 of 2' and 2'' | none | no |

Counted rows: 23 claimed (yield rows excluded as not in the crop); 6 match after audit (the replicator claimed 10). Partial rows count as not matched. The six matches are: compound_label_italic_suffix, substrate_layout, show_plus_sign, arrow_style, conditions_split, and straight arrows (arrow type only).

## Replay

```
python skill/chemdraw/scripts/cdx.py py skill/chemdraw/assets/house-styles/glorius_group/replica/glorius_group-02/replay.py NEW_DIR
python skill/chemdraw/scripts/cdx.py render NEW_DIR/figure.cdxml
```

`replay.py` draws `brief.json` offline. `brief_top.json` is not wired into a replay script; it was drawn with `cdx.py draw`.

## Differences from the paper

- Ar and R are not generic here: Ar = Ph, R = CH3, R' = CH3. The paper's R' is a variable and the tool cannot draw R, Ar or R' as labels, so the replica shows concrete compounds.
- The dashed box around the general reaction is not drawn.
- The lamp icon and the circled EnT with its circular arrow are replaced by the text "hv, EnT" above the arrow. The tool wrote "hν" as "hv".
- Colours: the paper colours the Ar/N part of reagent 2 dark red and the O-CH2-SiMe2R' part blue; the replica colours all of reagent 2 blue and the alkene dark red (the paper's alkene is black). The product 3 is black in the replica; the paper has Ar/N dark red and O-Si blue.
- The new C-C bond in product 3 is bold in the paper and not in the replica.
- The mint dot (#92F2C4) on the reacting CH2 is not drawn in the bottom reaction, and the product's Ar/N and O-Si colours are missing.
- The paper's general reaction omits the CO2 by-product. draw_figure reports "Step 1 does not balance as drawn" (CO2 missing) and does not add it. The replica keeps the paper's form, so the warning stays.
- The paper's arrow is about 13 bond lengths in the card median; the replica arrow is 5 bond lengths (72 pt). Line width is 0.042 of bond length in the replica against about 0.08 in the paper.
- Top panel (rendered_top.png): no captions, no lamp icon, no mint dots, no navy bold italic Brook label, arrows plain. The 2' and 2'' radicals are drawn closed-shell (see Tool gaps), so the chemistry shown differs from the paper: the iminyl radical loses its dot, and the 2'' radical becomes CH3-O-Si(CH3)3 (an implicit H is added).

## Tool gaps

- Colour inside one molecule: `substrate_colors` colours whole substrate molecules. The card's fragment colours (Ar/N dark red, silyl part blue within one reagent) cannot be expressed, and product colours are not offered.
- Condition symbols: no lamp icon (cyan #31BCFA) and no circled EnT with a circular arrow on the arrow. Above and below accept only text lines.
- Frame: no dashed rectangle around a sub-scheme or a reagent.
- Atom or bond highlight: `highlight_fill` fills the product ring only. A mint dot on one CH2 or on a single bond is not available.
- Formed bond emphasis: `new_bond_color` is colour only; a bold formed bond is not offered.
- Generic groups: R, Ar and R' cannot be drawn as labels in `draw_figure` SMILES species (only in `cdx.py build` specs).
- Line width and arrow length from the card measurements are not applied: the house style keeps the acs1996 line width (0.6 pt) and the default arrow (72 pt).
- Text formatting: above and below text lines are plain; bold italic navy labels and italic captions under radical structures are not available.
- Arrow direction: a vertical step (the Brook step drawn downward between two radicals) can only be drawn as a horizontal row in the scheme layout.
- Radical SMILES in the scheme path: `[N]=C(Ph)2`, `[O]C[Si](C)(C)C` and `[CH2]O[Si](C)(C)C` are drawn closed-shell (radical dot missing; the last one gains an H and becomes CH3-O-Si(CH3)3). The readback reports "matched" for these three structures, so the readback does not detect the change. The scheme-drawing reference says radical state is preserved and shown; this run did not show it.
- Text normalisation: "hν" is written as "hv".

## Notes

- OCSR was not run; the structures were read by eye from the crop and checked with RDKit (formulas above).
- The bottom replica was drawn once (try 1). The concept-panel draft was drawn once (try 2). Brief changes were not used to chase the radical or colour gaps, since these are tool-side.

## Audit

Checked against `reference.png`, `rendered.png` and `rendered_top.png` by zoomed inspection and pixel colour sampling. Overclaims corrected in the table above:

- Label face and label colour: the compound labels are clipped at the bottom edge of `reference.png`, so bold face and black colour cannot be confirmed. Counted as not matched.
- Formed bond: the C-C bond next to the mint-dot CH2 in product 3 is visibly bold in `reference.png`; the replica bond is not. The "colour only" match did not cover this.
- Bond/cap ratio 2.2: no bond or cap measurement exists for crop 02 (both are null in `brief.json`). The replica's own dimensions give about 2.0.
- Arrow length: the paper's arrow in crop 02 is not measured, so the 13.4 card median cannot be checked against this crop either. Still not matched.
- Bottom colours (not claimed as a gap in the table): the paper's alkene 1 "R" and bonds are black (#000000 sampled); the replica's alkene is dark red (#1B0000). Reagent 2 in the paper has dark red Ar/N and blue O-CH2-SiMe2R'; the replica's whole reagent is blue (#0000FE).
- Top panel: the CO2 is drawn as O=O in `rendered_top.png` (next to Ph2C=N), although `brief_top.json` gives O=C=O. The carbon is missing. This error is not reported above. The top reagent is dark red throughout (#210000); in the paper the iminyl part is dark red and the silyl fragment is blue.

Corrected count: 6 of 23 rows match (was 10).

Tool gaps the replicator missed:

- CO2 species `O=C=O` is rendered as O=O in the top panel (carbon dropped). A readback check should catch this.
- Colour within one molecule also affects the top-panel reagent: the rearranging fragment cannot be coloured blue while the iminyl part stays dark red.
- Measurement gap, not a tool gap: crop 02 has no bond-length or cap-height measurement in `brief.json`, so the 2.2 and 13.4 card values cannot be checked for this crop.
