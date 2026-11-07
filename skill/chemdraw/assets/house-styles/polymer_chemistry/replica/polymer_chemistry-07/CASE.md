# Maynard et al., Polym. Chem. 2026: concept figure, this-work reaction (crop polymer_chemistry-07)

Source: Maynard et al., "Biomolecule-polymer conjugates by organometallic bioconjugation and ATRP", *Polym. Chem.* **2026**, DOI [10.1039/d6py00714g](https://doi.org/10.1039/d6py00714g). Figure: Scheme 1 (concept figure, two stacked rows a) and b)).

Licence: CC BY 3.0, reference crop reproduced under that licence.

House style: `polymer_chemistry` (card: `house_styles/polymer_chemistry.json`, figure type `concept_panel`, base preset RSC). Figure type in the card: `concept_panel`.

## What is reproduced

Only part b), "This work": the gold(I) aryl complex bearing a bromo-isobutyryl ketone (graft-from) and the same complex carrying a polymer-bearing aryl (graft-to) react to give the biomolecule-CH2-S-aryl-polymer product, with the claim text "Rapid, efficient, and chemoselective" above the arrow. The two substrates are drawn inline with a plus sign, as the tool requires. The biomolecule and polymer/PEG pills are drawn as `[*]` attachment points, which ChemDraw renders as R groups.

Not reproduced: part a), "Previous work". The draw tool refuses two disconnected reactions in one brief ("The steps are not a linear route, a convergent route (arms that merge) or a set of reactions from one starting material"), so a) was left out. The panel letters, the navy bold italic headers and the second row are therefore absent.

## Structures used

Read from the crop. The gold complex is written as a P-to-Au dative bond with a P+ centre (the crop shows a cation bracket with SbF6-); the SbF6- counterion is not drawn.

| ID | Role | SMILES in brief.json |
| --- | --- | --- |
| AuFrom | graft-from complex | `CN(C)c1ccccc1[P+](C(C)(C)C)(C(C)(C)C)->[Au](Cl)c1ccc(cc1)CC(=O)C(C)(C)Br` |
| AuTo | graft-to complex | `CN(C)c1ccccc1[P+](C(C)(C)C)(C(C)(C)C)->[Au](Cl)c1ccc(cc1)[*]` |
| PB | product, biomolecule-S-aryl-polymer | `[*]CSc1ccc(cc1)[*]` |

The crop has P-adamantyl groups. The first two tries used `C12CC3CC(CC(C3)C1)C2` (1-adamantyl) as drawn in the crop; the layout put the adamantyl cages over the Au and Cl labels (see `draw_v2`, not kept here), so the final brief uses tert-butyl on P. This is a change of the ligand, not of the scheme topology, and it is listed under differences.

Both SMILES were checked by RDKit parse (formal charge +1 on the complex, product neutral).

## Tries

1. Brief with a) and b) as two steps, `draw` with `--render`: refused (disconnected steps).
2. Only b), adamantyl ligands, `--render`: drawn and rendered but cages overlap Au, Cl and P labels.
3. Only b), tert-butyl ligands (kept): drawn, rendered, legible. This is `brief.json` and `rendered.png`.

## Replay

```
python skill/chemdraw/scripts/cdx.py py skill/chemdraw/assets/house-styles/polymer_chemistry/replica/polymer_chemistry-07/replay.py NEW_DIR
python skill/chemdraw/scripts/cdx.py render NEW_DIR/figure.cdxml
```

`replay.py` reproduces the draw from `brief.json` offline. `rendered.png` is the desktop ChemDraw render of try 3, downscaled to 1200 px wide.

## Conventions checked

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| concept_panel: panel_label_style bold_lowercase | bold lowercase a) and b) | no panel letters | no |
| concept_panel: comparison_layout stacked_rows | two stacked rows | one reaction only | no |
| concept_panel: this_work_color #004880 | navy headers | black text, no headers | no |
| concept_panel: a) Previous work / b) This work bold italic navy headers | present | absent (part a not drawn) | no |
| concept_panel: PEG green, ATRP polymer blue, biomolecule grey pills | rounded gradient pills | R groups | no |
| concept_panel: claim text green italic #2A9068 between converging lines | green italic, converging lines | black roman, no lines | no |
| top-level arrow_style plain | plain arrow, about 5 bond lengths long (part a) | plain solid arrow, about 12 bond lengths long | no (audit: style matches, proportions do not) |
| top-level show_plus_sign | no plus sign (two arms merge into one arrow) | plus between the two substrates | no |
| top-level aromatic_rings kekule | Kekule rings | Kekule rings | yes |
| top-level reagent_text_color #000000 | the only text above the arrow is green claim text | black text above arrow (claim text) | no |
| top-level substrate_layout inline_plus | Y-junction merge of two arms | inline plus | no |
| top-level bond length / line width | not comparable (no scale on the crop) | not measured by the replicator; audit estimate: line about 0.04 of the bond length against about 0.06 in the paper crop (card value 0.09) | no |
| top-level Arial labels | Arial-like sans | font name not checked; rendered labels look Arial-like | no (unverified) |

Matched 1 of 11 claimed conventions for this crop (aromatic_rings kekule). The table has 13 rows; rows 1 to 11 are the claimed conventions and rows 12 and 13 are not counted. See Audit.

## Differences from the paper

- Part a) (Previous work) is not drawn; the panel letters a) and b), and the bold italic navy headers "Previous work" and "This work", are not drawn.
- Two substrates are joined inline with "+", while the paper merges two arms into one arrow with a Y-junction and "Graft from" / "Graft to" labels.
- The claim text "Rapid, efficient, and chemoselective" is black roman, not green italic (#2A9068).
- The adamantyl groups on P are tert-butyl groups in the replica. This changes a reagent's structure, not only its drawing.
- The biomolecule, PEG and ATRP-polymer pills (grey, green and blue, with gradients) are R groups.
- Au-Cl and Au-aryl bonds: the paper's dashed Au...C aryl contact is drawn as a solid bond in the replica (dative line from P only).
- The graft-from linker is a CH2 plus a carbonyl; in the paper the linker is drawn with a wavy bond between the aryl and the CH2 (the carbonyl follows the CH2). The replica uses a plain bond.
- The SbF6- counterion and the bracket on the cation are not drawn.
- The wavy attachment bonds on the aryl (variable linkage) are drawn as plain bonds.
- Bond length and line width were not compared with the crop (no measurement scale in the crop or the card for this figure type).

## Tool gaps

- No rounded pill or gradient box for macromolecules and biomolecules; `[*]` dummy atoms render as plain R.
- A brief cannot hold two disconnected reactions (one brief was refused), so stacked rows a) and b) cannot be drawn by a single draw_figure brief; the tool only accepts linear, convergent, divergent or catalytic-cycle layouts.
- No panel letters, no per-text bold/italic/colour for headers or claim text.
- No Y-junction merge of two independent substrates without a plus sign; the convergent layout needs arms that are steps.
- No cation bracket with an ion-pair counterion (SbF6-) beside the complex.
- No wavy attachment bond to a substituent on an aryl ring.
- Bulky P-ligands (adamantyl) overlap the Au and Cl labels in the default layout.
- No dotted or dashed style for a single bond: the paper's Au...aryl contact is dotted and the replica draws it solid. The brief has dashed arrows only.
- No circled charge symbols (plus or minus in circles); charges are superscripts only.
- No free text beside a connector line that has no arrow (the "Graft from" and "Graft to" labels on the merge stems).
- No direct arrow length setting; the arrow length follows the longest condition line, so one long line of claim text gives a long arrow.
- No line weight or arrowhead size field in the brief; the only width set in figure_draw is for bold arrows, from the preset LineWidth, so the card's measured line width is not applied.

## Audit

Checked against reference.png and rendered.png with zoomed crops and pixel profiles. Lengths are read off the drawn rings and lines, so treat the ratios as rough (about 15 percent).

- Arrow style was marked as matched. The style matches (one solid arrow with a filled head), but the replica arrow is about 12 bond lengths long against about 5 for the paper's part a) arrow, so the row is changed to no.
- Kekule rings were checked in both images and are confirmed as matched.
- Corrected count: 1 of 11 claimed conventions (kekule only).
- Line weight: the replica line is about 0.04 of the bond length (about 1.4 px ink against a bond of about 33 px) and the paper crop is about 0.06 (about 1.8 px against about 30 px). Card value 0.09. Changed to no.
- Arial labels: the font name in the CDXML was not checked. The labels look Arial-like, so the "no" is unverified rather than shown false.
- The wavy bond in the paper sits between the aryl and the CH2, not the carbonyl; corrected above.
- Not re-run in this audit: the RDKit parse of the two SMILES, replay.py, and the ChemDraw render.
- The adamantyl to tert-butyl change alters a reagent, so the replica is not the paper's compound. The change is disclosed under Differences but does not count toward any match.

