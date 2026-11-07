# Lenacapavir retrosynthesis (Figure 1), house style oprd_process

Source: Guthrie, Gupton et al., "A concise process to lenacapavir sodium: one-pot sequential Heck/Suzuki-Miyaura couplings", *Organic Process Research & Development* **2026**. DOI: [10.1021/acs.oprd.5c00443](https://doi.org/10.1021/acs.oprd.5c00443). Licence: CC BY 4.0 (from the card); the reference crop `reference.png` is reproduced under that licence.

Drawing style: the `oprd_process` house style (base preset ACS Document 1996), figure type `retrosynthesis`. Brief in `brief.json` uses `"style": "oprd_process"`.

## What is reproduced

The retrosynthesis of lenacapavir (left) into Frag C, Frag A, Frag B and Frag D (DMPS) (right), drawn with plus signs between the four fragments. In the paper Frag C, Frag A and Frag B sit on one line and Frag D sits on a second line below Frag A; the replica is one row, so the layout does not match. The three disconnections (amide formation, Suzuki-Miyaura coupling, Sonogashira coupling or Heck alkynylation) are not drawn. Stereochemistry is partly encoded (see below).

| Convention or signature feature | Paper | Replica | Match |
| --- | --- | --- | --- |
| retro_arrow open_double (card) | single open (hollow) block arrow, one head | single thin solid arrow | no |
| disconnection_mark dashed_line | three black dashed lines across the disconnected bonds | none | no |
| disconnection_color #FF0000 (card) | disconnection lines are black, but the disconnected bonds carry thick red stubs (at least the pyridine to alkyne and pyridine to indazole bonds); red also marks Frag C | black, no marks | no |
| disconnection names in bold black | Amide formation, Suzuki-Miyaura coupling, Sonogashira coupling or Heck Alkynylation | none | no |
| fragments coloured red and blue on both sides (card) | lenacapavir side: red Frag C part, blue difluorophenyl and pyridine part, black indazole and SO2Me alkyne. Right side: Frag C red, Frag A blue, Frag B and Frag D black | all black | no |
| fragments named Frag A to Frag D in bold | Frag C, Frag A, Frag B, Frag D (DMPS) in bold | same labels in bold | yes |
| compound_label_face bold | bold labels | bold labels | yes |
| compound_label_color #000000 | black | black | yes |
| show_plus_sign true | plus signs between fragments | plus signs between fragments | yes |
| aromatic_rings kekule | Kekule rings | Kekule rings | yes |
| arrow_style plain (card) | open block arrow for the retro step | thin plain arrow | no |
| abbreviate_groups Boc, OTBS (card) | not used in this figure; CF3, SO2Me and (pin)B written as labels | CF3 and SO2Me drawn as structures, Bpin drawn as ring pinacol ester | no |

## Differences from the paper

- The arrow is a single forward arrow; the paper uses an open single-headed block arrow pointing from lenacapavir to the fragments.
- No disconnection lines, no disconnection names, no red and blue fragment colouring, no red stubs on the disconnected bonds.
- The fragments and lenacapavir are drawn with ChemDraw's own bond geometry, so the crop's compact proportions and the wedged H atoms on Frag C are not reproduced.
- The (S) label beside the Frag A stereocentre is not drawn; the wedge is.
- Frag C is drawn without the cyclopropane stereo the crop shows as wedged H atoms. The stereo was not entered in the SMILES; this is an input choice, not a tool limit.
- The row is wider than the 504 pt budget (738 pt in the render), so the figure would need reflow or a two-row layout to fit a journal column.

## Structures

SMILES were written by hand from the crop, not from OCSR output. CIP assignment of Frag A and the lenacapavir stereocentre was checked with RDKit; the cyclopropane stereocentres of Frag C were not encoded.

- Lenacapavir: `CC(C)(C#Cc1ccc(-c2cc(Cl)c3c(N)nn(CC(F)(F)F)c3c2)c([C@H](Cc2cc(F)cc(F)c2)NC(=O)Cn2nc(C(F)(F)F)c3c2C(F)(F)C2CC32)n1)S(C)(=O)=O`
- Frag C: `O=C(O)Cn1nc(C(F)(F)F)c2c1C(F)(F)C1CC21`
- Frag A: `N[C@@H](Cc1cc(F)cc(F)c1)c1nc(Br)ccc1Br` (S)
- Frag B: `CC1(C)OB(c2ccc(Cl)c3c(N)nn(CC(F)(F)F)c23)OC1(C)C`
- Frag D: `C#CC(C)(C)S(C)(=O)=O`

## Tool run

Draw call: `python skill/chemdraw/scripts/cdx.py draw brief.json figure.cdxml --render` (first try, max_width 504). The result is a linear row (layout `linear`), `readback` matched (5 structures), `native` rendered, `checks_passed` false.

- Lint: `too_wide`, 738 pt against a 504 pt budget; the one automatic relayout narrowed the budget to 378 pt and the drawing stayed 738 pt wide.
- Balance: step 1 reported as unbalanced; the reactants lack `C6H15BBr2O3`. The fragments carry atoms that lenacapavir does not contain (two Br on Frag A, the pinacol boron ester on Frag B), so the step fails in either direction; these are leaving-group atoms of the coupling reactions, which the figure does not draw. Nothing was added to the drawing.
- A second try with `max_width` 760 was queued on the shared ChemDraw lock behind other jobs and was stopped before it finished, so the width result above is the only render.

## Replay

```
python skill/chemdraw/scripts/cdx.py py skill/chemdraw/assets/house-styles/oprd_process/replica/oprd_process-07/replay.py NEW_DIR
python skill/chemdraw/scripts/cdx.py render NEW_DIR/figure.cdxml
```

`replay.py` runs `draw_figure` on `brief.json` offline and writes `figure.cdxml` and `validation.json`. `rendered.png` is a 1200 px downscale of the ChemDraw render.

## Tool gaps

- `draw_figure` has no retrosynthesis kind. The card's `figure_types` colours are applied only for mechanism and catalytic cycles: `apply_figure_type_conventions` runs only for the catalytic-cycle layout (`toolkit/cdxml_toolkit/mcp_runtime/figure_draw.py`, `_draw`). For this linear route the retrosynthesis section is never read, so its conventions are not listed as skipped at all; they are dropped silently. The earlier statement that each one is listed as skipped is not supported.
- No open (hollow) retro arrow: `ARROWS` is `solid`, `dashed`, `failed`, `reversible`, `resonance`; the house `arrow_style` supports only `bold`.
- No disconnection marks. The `ring_fills` and `atom_halos` decorations fill rings or halo atoms; they cannot draw a dashed line across a bond.
- No colour for the disconnected bonds. `new_bond_color` colours bonds formed from substrates into products, so a bond broken by a retro step (lenacapavir to fragments) is never coloured; the card value is null anyway.
- No per-fragment colour. `substrate_colors` paints a whole substrate and the card value is null. `ring_fills` and `atom_halos` give filled rings or halos, not coloured bonds and labels, so the red and blue fragments cannot be drawn as in the paper.
- No balance exemption for a disconnection step. `_check_balance` has no step-level flag, so a correctly drawn disconnection fails it. A retro-direction flag would not fix this, because the fragments carry atoms that lenacapavir lacks and the check fails in either direction.
- Unknown keys inside `steps` and `species` are not validated (only top-level keys are), so a `direction` or `color` key is silently ignored.
- A single step cannot wrap its products. `max_row_width` picks `steps_per_row`, so rows break only between steps; `_relayout` narrows the width budget and widens gaps but does not split one step's products, so the four-product step stays one row.
- No free text beside a structure: only above and below lines; the species label sits below. The italic (S) cannot be placed.
- Abbreviations are limited. `ABBREVIATIONS` has no entry for SO2Me or for Bpin / (pin)B. CF3 has an entry, but it is applied only when the card's `abbreviate_groups` lists it; the card lists only Boc and OTBS, and a brief cannot override this. This gap was missing from the earlier list.

## Audit

The reference crop and the replica render were checked against each match row. The matched count stays 5 of 12, but the layout and colour descriptions were wrong and the first tool-gap claim was not supported by the code.

Overclaims found and corrected above:
- The paper is not one row: Frag D sits on a second line below Frag A.
- The disconnected bonds carry red stubs, so "red marks only Frag C" was wrong.
- Right-hand fragments are not all black: Frag C is red and Frag A is blue.
- The balance failure is not only a direction artefact; a retro-direction flag would not make `checks_passed` true.
- The claim that every retrosynthesis convention is listed as skipped is not supported by the code path (see Tool gaps).
- The card's `retro_arrow: open_double` disagrees with the crop, which shows one hollow head.
- The `arrow_style plain` row is "no" because the paper uses a hollow block arrow; the replica does meet the card's plain value.

Rows that stand but are weaker than stated:
- `show_plus_sign`: three plus signs are present, but Frag D is inline in the replica and below the row in the paper.
- `aromatic_rings kekule`: no code path applies this convention; the rings are Kekule by default. Checked only on the 1200 px downscale.
- The bold-label rows were checked at downscale only; label size was not measured.

Not checkable here: line weight, the bond-length to label ratio (the reference is 900 px wide with no scale bar, the replica 1200 px), the balance numbers, and the width numbers (no `validation.json` is in the folder and the replay was not run).
