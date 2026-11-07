# Beilstein JOC: hypophosphite reductive amination, carbonyl to iminium (Scheme 5, top row)

Source: Chusov et al., "Influence of the cation in hypophosphite-mediated catalyst-free reductive amination", *Beilstein J. Org. Chem.* **2025**, *21*. DOI: [10.3762/bjoc.21.130](https://doi.org/10.3762/bjoc.21.130). Licence: CC BY 4.0 (from the house-style card). Reference crop: `reference.png` (copy of `evidence/beilstein_joc-07.png`).

Figure type: `mechanism` (card figure_types section; one crop).

Drawing style: the `beilstein_joc` house style in `brief.json` (base preset nature; the card's curved-arrow colour and weight are applied; the scheme-only conventions are skipped by the tool).

## What is reproduced

The top row of the paper's figure: butan-2-one and a secondary amine give the carbinolamine (with H3PO2 printed above the arrow, as in the paper), which loses water to the iminium ion. Both steps are equilibria (double-headed arrows, as in the paper's top row).

The paper's top row has no curved arrows. The replica adds two curved-arrow steps (nitrogen attack on the carbonyl carbon; C-O bond to oxygen, then nitrogen lone pair into the C-N bond) so that the tool has moves to draw. These arrows are the replica's own, not copied from the crop. The crop's curved arrows are all in the lower cycle (hydride and proton moves involving P-H and O-H), which the replica does not draw.

The R groups are replaced by concrete alkyls: the ketone is butan-2-one (R = CH3 on the carbonyl, CH2 chain as ethyl) and the amine is dimethylamine (the paper's R2NH with R = CH3).

| ID | Structure (SMILES in brief.json) | Check |
| --- | --- | --- |
| K | `CCC(C)=O` (C4H8O) | RDKit canonical form matches; stands for R-CH2-C(=O)-R with R = CH3 |
| A | `CNC` (C2H7N) | dimethylamine; the paper's R2NH with R = CH3 |
| H+ | `[H+]` | added so that step 1 balances (K + A + H+ = C6H16NO+, the same formula as HP) |
| HP | `CCC(C)([OH2+])N(C)C` (C6H16NO+) | protonated carbinolamine; the paper draws the hemiaminal with an N+-H ammonium instead (see differences) |
| I | `CCC(C)=[N+](C)C` (C6H14N+) | iminium ion, no label (the paper labels no intermediates in this figure) |
| W | `O` (H2O) | water; HP = I + W balances (C6H14N+ + H2O = C6H16NO+) |

## Replay

```
python skill/chemdraw/scripts/cdx.py py skill/chemdraw/assets/house-styles/beilstein_joc/replica/beilstein_joc-07/replay.py NEW_DIR
python skill/chemdraw/scripts/cdx.py render NEW_DIR/figure.cdxml
```

`replay.py` runs `draw_figure` on `brief.json` offline and writes `figure.cdxml` and `validation.json`. `rendered.png` is the desktop ChemDraw render of the try-3 brief, downscaled from 1509 to 1200 px wide.

Tries: try 1 drew an `I` label on the iminium and no H3PO2 text. try 2 changed only the row width (max_width 400); the drawing did not change. try 3 removed the intermediate label and added H3PO2 above the first arrow. The first run of try 3 timed out inside the tool (300 s); the retry with a new output name succeeded and is the rendered result. The brief in this folder is the try-3 brief.

## Convention table

Claimed rows are the card's non-null mechanism conventions and signature features, plus the top-level scheme conventions visible in this crop. ts_marker and highlight_fill are null; compound labels, yields, abbreviations and aromatic-ring style are not visible in this crop, so none are counted.

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| curved_arrow_color `#000000` | black curved arrows (in the lower cycle only) | black (applied by the tool) | yes |
| curved_arrow_weight `thin` | thin arrows (lower cycle) | 0.45 pt, 0.75 of the 0.6 pt bond width (applied by the tool); the paper's ratio was not measured against a bond in this crop | no (not verified) |
| show_lone_pairs `false` | no lone pairs drawn | none drawn (renderer default; the tool lists this card rule as not drawn) | yes |
| formal_charge_style `plain` | plain superscript + on the iminium N and the H+ | plain superscript + on N, OH2 and H (renderer default; not applied by the tool) | yes |
| intermediate_label_style `none` | no intermediate labels | no label (try 3; renderer default, not applied by the tool) | yes |
| signature: small black curved arrows, thinner than bonds | yes (lower cycle) | no: the top-row arrows are the replica's own additions, not the paper's; thinness against bonds is unverified | no |
| signature: fragments colour coded, carbonyl red `#FC0000`, amine blue `#0000FC` | red carbonyl part, blue amine part (both colours present in the crop pixels) | all black | no |
| signature: phosphorus reagents in grey rounded boxes with drop shadow | yes (cycle) | not drawn: the hydride steps are not expressible | no |
| top level: inline_plus substrate layout | ketone + amine inline | ketone + amine + H+ inline (visual only; the tool skips substrate layout for mechanisms) | yes |
| top level: show_plus_sign true | plus between the substrates | plus between the substrates | yes |
| top level: reagent_text_color `#000000` | H3PO2 in black | H3PO2 in black (visual only; the tool skips reagent colour for mechanisms) | yes |
| top level: conditions_split, reagents above | H3PO2 above the first arrow | H3PO2 above the first arrow (visual only; the tool skips conditions_split for mechanisms) | yes |
| top level: arrow_style `plain` | equilibrium arrows in the top row, plain curved arrows in the cycle | equilibrium arrows (as the paper's top row) | no (not counted: the card's plain value is for single reaction arrows, and the tool skips arrow_style for mechanisms) |

Matched 8 of 13 claimed rows after audit (the first count was 10; see Audit).

## Differences from the paper

- Scope: only the top row (ketone, amine, carbinolamine, iminium, water) is drawn. The hypophosphite steps (P-H hydride transfer to the iminium carbon, release of the phosphorus acid), the phosphorus boxes with drop shadow, the cycle arrows and the final amine product are not reproduced.
- Curved arrows: the paper's top row has none; the replica's two curved-arrow steps are added to show the electron moves the tool needs. They do not appear in the crop.
- R groups: the paper uses R on every position; the replica uses CH3 and CH2CH3 because the brief takes SMILES only.
- Fragment colours: the paper colours the carbonyl part red and the amine part blue; the replica is all black.
- Hemiaminal: the paper draws the carbinolamine as an N+-H ammonium with OH; the replica draws the oxygen as protonated OH2+ on a tertiary nitrogen, which avoids an N-H move in the drawing but not the proton transfers the product needs (see Audit).
- Extra H+: the replica adds H+ as a substrate of step 1 for atom and charge balance; the paper shows no separate proton.
- Proton transfers (N-H to O in step 1, and the alpha-C-H in the enamine tautomer shown in the paper's top right) are not drawn; the tool cannot address H atoms as arrow ends.

## Tool gaps

- Hydrogen atoms bonded to heavy atoms cannot be arrow ends (a bare H+ species can; see Audit). The SMILES is grounded with implicit hydrogens and atom numbering skips H, so a P-H hydride donor (hypophosphite to iminium) and any N-H or C-H proton transfer cannot be expressed as a curved arrow.
- No fragment colouring in a mechanism brief. `substrate_colors` applies to schemes only (the tool lists it as skipped for mechanisms); mechanism species have no per-atom or per-substructure colour option.
- No generic R label. Species are SMILES or names only, so R groups become concrete alkyls. Not tested: whether a dummy atom would draw as R.
- No grey rounded box with drop shadow around a species or reagent, in schemes or mechanisms.
- No circular cycle layout for a mechanism brief. The catalytic-cycle layout is for schemes; a mechanism runs in rows, so a closed loop of hydride and proton steps cannot be drawn as a circle with curved arrows.
- draw_figure timed out once at 300 s on this 2-step mechanism; the retry with a new output name finished.

## Audit

Second pass. `reference.png` is byte-identical to `evidence/beilstein_joc-07.png`. The species formulas and canonical SMILES check out with RDKit. The replay was rerun into a scratch folder, not this one. Its `validation.json` lists lone pairs, formal charge and intermediate labels as "guidance ... not drawn by the tool", and lists the reaction-scheme conventions as skipped for mechanisms.

Overclaims corrected:
- The count goes from 10 to 8. The curved-arrow weight and arrow-signature rows are not verified: no bond in crop 07 was measured, the paper's curved arrows measure about 1.3 px at 741 px wide, and the replica's top-row arrows are not in the paper.
- Lone pairs, formal charge, intermediate label, inline layout, plus sign, reagent colour and conditions placement are visual matches only. The tool does not apply them to mechanisms.
- The arrow_style row cited "card_errors", which does not exist in this case.
- "So that the step has heavy-atom moves only" is wrong. Step 1 as drawn (N lone pair to C, C=O pi to O) gives an N+ / O- zwitterion. The drawn HP (neutral N, OH2+) also needs an N-H to O and an H+ to O proton transfer, and neither is drawn. The H+ substrate is in no arrow. The balance check is formula-only; the tool's report says it "does not decide whether the mechanism is chemically right".
- Proportions are not matched and are not in the table. The CDXML has bond length 10.8 pt, Arial 6 pt labels, bond width 0.6 pt and an equilibrium arrow of 54 pt. That gives bond to cap height about 2.5 (card 2.25), line to bond 0.056 (card 0.068) and arrow 5.0 bond lengths (card 6.4). The tool applies only the nature preset.
- The paper's "-H2O" label under the second equilibrium arrow is missing and is not listed under Differences. Mechanism steps accept "below" text, so it could be drawn.

Tool gaps, corrected:
- Confirmed: RDKit removes hydrogens bonded to heavy atoms ("CC[H]" parses to 2 atoms), so N-H, C-H and P-H moves cannot be drawn.
- Wrong: a bare H+ species is addressable. A scratch test with an arrow from K atom 4 (O) to P atom 0 (H+) passed the checks and the readback. The proton-addition arrow can be drawn.
- Partly wrong: the top-row equilibria do not need curved arrows. figure_draw.py lists "reversible" among the scheme arrows (not tested). The mechanism-kind gap stands.
- Partly wrong: layout "catalytic-cycle" exists for scheme routes (figure_draw.py `_route_layout`), so a circular loop with plain arrows is possible. A curved-arrow cycle is still not possible.
- The species "label" key draws a compound label under the structure, not an R group. Scheme atom_halos draw coloured halos, not coloured bonds and text.
- Confirmed: there is no grey box or drop-shadow option (no shadow or rounded-box code found).
