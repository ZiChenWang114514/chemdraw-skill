# Polymer Chemistry (RSC): Figure 1a, monomer synthesis (reaction_scheme)

Source: Besenius et al., *Polym. Chem.* 2025, "1,4-Oxazepan-7-one trifluoroacetate: a modular monomer precursor for functional and biodegradable poly(amino esters)". DOI: [10.1039/d5py00522a](https://doi.org/10.1039/d5py00522a). Licence: CC BY 3.0 (from the house-style card). Reference crop reproduced under that licence.

Drawing style: the `polymer_chemistry` house style (`reaction_scheme` figure type; base preset `rsc`).

## What is reproduced

Row a) of Figure 1: 4-piperidone to the N-Boc piperidone (P_Boc, drawn as PBoc), ring expansion with mCPBA to OxPBoc, and TFA/DCM deprotection to the ammonium trifluoroacetate OxPTFA. Only the mCPBA arrow is drawn. Conditions follow the figure's wording, with the changes listed under Differences. No yields are shown in the paper for this row.

| ID | Structure (SMILES in brief.json) | RDKit check |
| --- | --- | --- |
| 4-piperidone | `O=C1CCNCC1` | C5H9NO |
| PBoc | `CC(C)(C)OC(=O)N1CCC(=O)CC1` | C10H17NO3 |
| OxPBoc | `CC(C)(C)OC(=O)N1CCOC(=O)CC1` | C10H17NO4 |
| OxPTFA | `O=C1CC[NH2+]CCO1.[O-]C(=O)C(F)(F)F` (ammonium lactone with trifluoroacetate) | C7H10F3NO4 (salt) |

The lactone ring (1,4-oxazepan-7-one) follows the paper's name and drawing: O1 bonded to the carbonyl C7, N4 bears the Boc group in OxPBoc and is protonated in OxPTFA.

## Replay

```
python skill/chemdraw/scripts/cdx.py py skill/chemdraw/assets/house-styles/polymer_chemistry/replica/polymer_chemistry-02/replay.py NEW_DIR
python skill/chemdraw/scripts/cdx.py render NEW_DIR/figure.cdxml
```

`replay.py` runs `draw_figure` on `brief.json` offline. It was not run for this case, because the final drawing came from `cdx.py draw brief.json ... --render` with the brief saved here. `rendered.png` is the ChemDraw render, downscaled to 1200 px wide.

## Convention table

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| bracketed step numbers [1], [2], [3] to the left of the reagent stack | yes | not drawn (no tool for step numbers) | no |
| panel letters a) and b) | yes | not drawn; only row a) reproduced | no |
| compound names as plain subscripted text (`OxP` with subscript `Boc`) | yes | plain `PBoc`, `OxPBoc`, `OxPTFA`; no subscript | no |
| CF3 abbreviated (top-level `abbreviate_groups`) | yes | CF3 abbreviated on the trifluoroacetate | yes |
| Boc abbreviated under N (card notes: "Boc only in crop 02") | yes | expanded tert-butyl carbamate | no |
| reagents above the arrow, solvent and temperature below | yes | Boc2O and K2CO3 above; THF/H2O and rt, 16 h below (placement matches; the tool reports conditions_split as not applied, so the split was set by hand in the brief) | yes |
| plain arrow (`arrow_style` plain) | yes | plain solid straight arrows; the paper's mCPBA arrow [2] is curved and is drawn straight | yes (style only) |
| reagent text black (`reagent_text_color` #000000) | yes | black | yes |
| no yields on this row (`yield_placement` null) | none in row a) | none drawn | yes |
| bond length over label cap height about 2.4 | 25 / 10 px = 2.5 | by pixel count on rendered.png the bond is about 30 px and the cap height about 11 px, a ratio of about 2.7; the 2.4 of the earlier draft came from an assumed 7 pt label, not from the image | no |
| line width over bond length 0.09 | 2.5 / 25 px = 0.10 | bond line 0.45 pt over 12.2 pt = 0.04 | no |
| arrow length about 4.3 bond lengths (crop 02 measured) | 107 / 25 px = 4.3 | by pixel count the step 1 arrow is 141 px over a 30 px bond, about 4.7; the 61 / 12.2 pt figure is in the tool's units and was not checked against the image | no (approximate, about 9 percent longer) |
| circled plus and minus on the ammonium and carboxylate | yes | plus on NH2 shown; carboxylate minus not circled | no |
| trifluoroacetate beside the ring (lower right of the ammonium) | yes | stacked above the ring | no |
| second alternative arrow [2'] (OXONE, phosphate buffer, 18 h) | yes | not drawn: a second step to the same product is refused | no |

Matched 5 of 15 conventions after audit (the replicator claimed 7; see Audit).

## Differences from the paper

- Step numbers [1] to [3] and the panel letter a) are not drawn.
- The OXONE alternative (step [2'], phosphate buffer, RT, 18 h) is omitted. The tool refuses a second step producing the same species (`Species OxPBoc is produced by more than one step.`), so only the mCPBA route is drawn.
- Row b) (acylation of OxPTFA with four acyl chlorides) is not reproduced in this case.
- Compound names are plain text with no subscript. `OxP_Boc` would show the underscore literally, so the label was changed to `OxPBoc`.
- The paper's "RT" is drawn as "rt" because the condition tidy-up lowercases it.
- The paper's "TFA/DCM (1/1 v/v)" is drawn as "(1/1 v/v)" with the second 1 subscripted, as if it were a formula.
- The Boc group on N is drawn in full, not as the abbreviation the paper uses.
- The trifluoroacetate counterion is stacked above the ring, not set beside it at lower right.
- Bond lines are thinner than in the crop (0.45 pt against a 12.2 pt bond).
- The mCPBA step [2] is a curved arrow in the paper and a straight arrow here.
- mCPBA is set upright; the paper has an italic m.
- The charges on the ammonium and carboxylate are plain superscript signs, not circled plus and minus.
- The RT of steps 1 and 3 is drawn as rt, and the second 1 in 1/1 is subscripted.
- The paper's row is on one line. The default `max_width` of 504 wrapped the third step onto a second row; `max_width` 720 keeps the row on one line.
- The by-products of each step (for example CO2 and t-BuOH from Boc chemistry) are not drawn; the tool reported balance warnings and added nothing.

## Tool gaps

- Compound labels cannot carry subscripts. `OxP_Boc` renders as literal text with an underscore; the tool has no subscript markup for labels.
- Two alternative steps to the same product (a split arrow) cannot be drawn; the tool refuses a species made by more than one step.
- Step numbers in brackets placed to the left of the reagent stack, and panel letters, have no drawing option.
- The `conditions_split` convention is reported as not applied, so the reagent/solvent split comes only from the brief's own above and below lists.
- The condition tidy-up forces "rt" and subscripts a digit after a slash ("1/1" becomes "1/1" with a subscript), so the paper's exact condition text cannot be kept.
- Only the abbreviations listed in `abbreviate_groups` are applied; Boc is not in that list, so it is drawn in full.
- The counterion of a salt is drawn stacked above the cation; there is no option to set it beside the ring.
- Bond line weight follows the base preset (rsc), not the card's measured 0.09 ratio.
- Row layout: a route wider than `max_width` wraps onto a second row, and nothing in the style chooses the width of a single-row scheme.
- The draw with `--render` took about 3 to 5 minutes per run.
- Primed step labels such as [2'] have no drawing option; the replica has no step label at all.
- Circled charge symbols (a plus or minus inside a circle) on atoms: only plain superscript signs are drawn.
- Curved reaction arrows (an arc from one structure to the next, with reagent text above and below the arc): only straight arrows appear in this case.
- Italic letters inside reagent text (the italic m in mCPBA) and the registered mark in OXONE: not shown in this case, and the case does not say whether the tool can draw them.

## Audit

Checked by reading reference.png and rendered.png at 3x zoom and by pixel counts (threshold 128 to 160) on both images. The replicator's claim of 7 of 15 is overstated; the corrected count is 5 of 15.

- Overclaim: the bond-to-cap-height row was marked matched on an assumed 7 pt label. Pixel count gives about 2.7 in the replica (bond about 30 px, cap height about 11 px) against 2.5 in the reference. Marked no.
- Overclaim: the arrow-length row was marked "yes (close)". Pixel count gives about 4.7 bond lengths in the replica against 4.3 in the reference. Marked no.
- Overclaim: the intro said conditions were copied from the figure. RT is drawn as rt and the second 1 in 1/1 is subscripted. Corrected in the intro and in Differences.
- Kept as matched, with a limit: the plain-arrow row matches arrow style only. The paper's mCPBA arrow is curved and is drawn straight.
- Confirmed matched: CF3 abbreviation, reagent placement above and below the arrow, plain arrow style, reagent text pure black (RGB 0,0,0, no colour in the image), no yields.
- Confirmed not matched: step numbers, panel letters, compound subscripts, Boc abbreviation, circled charges, counterion placement, the OXONE route, and bond line weight (stroke about 1.2 px on a 30 px bond, ratio about 0.04 against 0.09).
- Tool gaps added: primed step labels, circled charge symbols, curved reaction arrows, and italic or registered-mark glyphs in reagent text.
- Not checked: render timings, the balance warnings, the command lines, and whether rendered.png came from the ChemDraw engine. No cdxml file is in the case folder.
