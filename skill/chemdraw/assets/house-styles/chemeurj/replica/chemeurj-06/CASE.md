# Maes et al. 2023: Fe-catalysed carbene transfer to isocyanides (Scheme 5, catalytic cycle)

Source: Maes et al., *Chem. Eur. J.* 2023, "Iron-catalysed carbene transfer to isocyanides as a platform for heterocycle synthesis". DOI: [10.1002/chem.202203074](https://doi.org/10.1002/chem.202203074). Licence: CC BY 4.0 (from the `chemeurj` house-style card). Reference crop: Scheme 5, copied to `reference.png`.

Drawing style: the `chemeurj` house style (Chem. Eur. J., base preset `wiley`) applied through `draw_figure` with `layout: "catalytic-cycle"`; see `brief.json`.

Figure type: `catalytic_cycle`.

## What is reproduced

The four-step main loop of the cycle, starting from [Fe]:

1. [Fe] + isocyanide gives A (isocyanide bound to Fe).
2. A + diazo ester gives B (Fe carbene with the isocyanide still bound), with loss of N2.
3. B gives C (ketenimine bound to Fe).
4. C gives [Fe] and product 5.

Substitutions: the paper's generic R is drawn as methyl and EWG is drawn as CO2Me (methyl diazoacetate). The paper states EWG = CO2R, COR or CN, so this is one representative instance.

SMILES used (`brief.json`):

| ID | SMILES |
| --- | --- |
| [Fe] | `[Fe]` |
| isocyanide | `[C-]#[N+]C` |
| diazo ester | `COC(=O)C=[N+]=[N-]` |
| A | `[C-]#[N+]C->[Fe]` |
| B | `COC(=O)C=[Fe]<-[C-]#[N+]C` |
| C | `COC(=O)C=C(=NC)->[Fe]` |
| 5 | `COC(=O)C=C=NC` |
| N2 | `N#N` |

Not drawn: the second route from [Fe] through the carbene D (`COC(=O)C=[Fe]`) to B (step II) and to C (step III), the two straight arrows inside the cycle, the grey framed pathway boxes I, II and III, and the legend box.

What the render actually shows: four intermediates ([Fe], A, B, C) at the corners of a diamond, joined by four straight arrows. The isocyanide, the diazo ester, N2 and product 5 are not drawn (see Tool gaps).

## Attempts

1. Full seven-step brief with D: refused, `Species N2 is produced by more than one step.` (N2 used as by-product of two steps under one id).
2. Same brief with one N2 id per step: refused, `Species B is produced by more than one step.` (B is the product of the A + diazo step and of the D + isocyanide step; C likewise).
3. Four-step main loop with `--render`: accepted (`ok: true`), `balanced: True` for all steps, native render reported as succeeded in the original run (not reproduced in the audit). This is `brief.json` and `rendered.png`. Readback reports `mismatch`: ICN, DZ, P5 and N2a not drawn, and `checks_passed` is false. The offline replay reproduces the readback and reports `native: not_run`.

## Replay

```
python skill/chemdraw/scripts/cdx.py py skill/chemdraw/assets/house-styles/chemeurj/replica/chemeurj-06/replay.py NEW_DIR
python skill/chemdraw/scripts/cdx.py render NEW_DIR/figure.cdxml
```

`replay.py` runs `draw_figure` on `brief.json` offline and writes `figure.cdxml` and `validation.json`. Compare the render with `reference.png`.

## Card conventions checked

Applied by the tool (from the report's `style.applied`): `compound_label_face=bold`, `show_plus_sign`, `reagent_text_color`, `substrate_layout=inline_plus`, `catalytic_cycle.cycle_arrow_color=#000000`.

Skipped by the tool: `conditions_split`, `yield_placement`, `yield_separator`, `new_bond_color`, `substrate_colors`, `catalytic_cycle.cycle_shape=circle` and `catalytic_cycle.curved_arrow_color`.

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| catalytic_cycle.cycle_shape "circle" | circle of four heavy black arcs around [Fe] | four straight arrows in a diamond | no |
| catalytic_cycle.cycle_arrow_color "#000000" | black | black | yes |
| catalytic_cycle.curved_arrow_color "#000000" | black curved arcs | black straight arrows, no curvature (skipped as guidance) | no |
| signature: black arcs around a circle | yes | no, straight arrows | no |
| signature: incoming and leaving species on short curved arrows touching the cycle | isocyanide and diazo enter, N2 and 5 leave | none drawn (readback: ICN, DZ, P5, N2a missing) | no |
| signature: framed legend or catalyst box, black outline, grey drop shadow | "EWG = CO2R, COR, CN" box with grey shadow | not drawn | no |
| top-level compound_label_face "bold" | bold letters and bold 5 | bold A, B, C (face 1 in the CDXML); 5 not drawn | yes (A to C only) |
| top-level compound_label_color "#000000" | 5 black; A to D grey | A, B, C black | no |
| top-level highlight_fill (none in this crop) | no fill | no fill, but the replica draws no filled element, so the row tests nothing | no (not testable) |
| top-level substrate_colors null | EWG blue and N-R maroon in the isocyanide, the diazo ester and 5 | all black | no |
| top-level arrow_style "plain" | heavy arcs, not plain thin arrows | thin plain arrows | no |
| intermediate_label_style (null in card; notes say grey bold letters A to D) | grey bold capital letters | bold black letters | no (not a card claim) |

Conditions, yields, selectivity, substrate layout, abbreviations and aromatic rings do not occur in this crop and are not counted.

## Differences from the paper

- Shape: the paper's cycle is a circle of heavy curved arcs. The replica is a diamond of thin straight arrows.
- Missing species: the paper shows the isocyanide and the diazo ester entering the cycle, N2 and product 5 leaving it. None of these is drawn in the replica.
- Missing intermediate D and steps II and III: the paper's second route (Fe carbene D, then B and C) is not drawn.
- Labels: the paper writes [Fe] in brackets and intermediates A to D in grey bold capitals. The replica writes Fe plain and A to C in black bold.
- Colour: the paper colours the EWG blue and the N-R fragment maroon, and keeps the colours in product 5. The replica is all black.
- Pathway boxes and legend: the paper's I, II and III boxes and the EWG legend box, each with a grey shadow, are not drawn.
- Ligand bonds: the paper's Fe-ligand bonds are plain or dashed. The replica draws them as dative arrows, which reads differently.
- Arrow weight: the paper's cycle arcs are heavy, about 9.5 px in the crop. The replica's arrows are thin.

## Tool gaps

- `draw_figure` refuses any species that is the product of more than one step (`Species B is produced by more than one step.`). A cycle in which two steps feed the same intermediate (here B and C, via D) cannot be drawn.
- A by-product shared by two steps must get a separate id for each step (`Species N2 is produced by more than one step.`).
- The `catalytic-cycle` layout draws straight arrows in a loop, not a circle of curved arcs. `cycle_shape` and `curved_arrow_color` are listed as skipped guidance. There is no arc option, and no option for heavy cycle arrows.
- The layout's documentation (`skill/chemdraw/references/scheme-drawing.md`, catalytic-cycle bullet) promises entering reactants and departing products on radial in/out arrows, a `cycle_radius` parameter (default 120 pt) and curved arrows along the circumference. None of these is implemented (no `cycle_radius` in the code). The cause of the four missing species is in `_layout_catalytic_cycle` (`toolkit/cdxml_toolkit/render/renderer.py`): it draws only `substrates[0]` of each step as a ring node and never builds other substrates or off-ring products. They are dropped silently; the only signal is the readback mismatch.
- `[Fe]` with brackets cannot be expressed as the atom label. A species `label` of `[Fe]` would be placed as a caption under the ring node, not on the atom.
- No per-label colour for the grey intermediate letters in a catalytic cycle.
- Fragment colouring (`substrate_colors`) paints whole species, not fragments, so the blue EWG and maroon N-R parts of one intermediate cannot be coloured separately. It paints only substrates that are not products, and the cycle layout draws none of the entering reagents. The card sets `substrate_colors` to null, so the tool skips it for that reason, not because of the layout.
- No framed pathway boxes with numerals (I, II, III) and no framed legend box with a drop shadow.
- Dative bonds render as arrows; the paper's Fe-ligand bonds are plain or dashed. The `multi_attachments` code in `cdxml_toolkit/mcp_runtime/figure_tools.py` accepts `bond_display` (default Dash) and `bond_order` (default dative), but `draw_figure` does not expose it.
- Cycle ring nodes are the first substrate of each step, so the order of a step's substrates decides which species sits on the ring. A reagent listed first would become a ring node without a warning.
- Cycle arrows take no weight option. `curved_arrow_weight` exists only for mechanisms, and `_arrow_kind` maps only reversible and resonance onto the cycle arrows.
- The four ring nodes sit at 0, 90, 180 and 270 degrees on a circle and are joined by chords, so the cycle is a diamond whatever the card says.

## Structure issues

- A: wrong structure, not a readability issue. The SMILES `[C-]#[N+]C->[Fe]` puts the dative bond on the N-methyl carbon, so Fe is bonded to CH3, and the isocyanide carbon that should bind Fe is free. The drawing is faithful to that SMILES (fragment round trip preserved), so the error is in `brief.json`. The paper's Fe-C-N-R unit is not reproduced.
- C: the connectivity matches the SMILES (MeO2C-CH=C(=N-Me)->Fe, checked in the CDXML: the CH sits between the ester and the central carbon). The drawing is hard to read at this size and the Fe-ligand arrow is not clear, so treat C as not reproduced.
- Not drawn: D, the diazo ester, the isocyanide, N2 and product 5, so the reaction-level chemistry of the cycle is not shown.

## Audit

Checked against `reference.png`, `rendered.png`, `brief.json`, the CDXML from an offline replay of `brief.json` (temporary folder, not this folder), and the toolkit code.

- Overclaim: the count. The table had 3 of 11 matched. The `highlight_fill` row tests nothing, because the replica draws no filled element. Corrected count: 2 of 11 (cycle_arrow_color; compound_label_face on A to C; the 5 label is not drawn).
- Overclaim: species A. The SMILES puts the Fe bond on the N-methyl carbon, not the isocyanide carbon. This is a chemistry error in `brief.json`, not a readability point.
- Understated: the radial in/out arrows, curved cycle arcs and `cycle_radius` are documented in `scheme-drawing.md` but not implemented. The reason for the missing reagents and products is now stated.
- Unverified: "native render succeeded" for attempt 3 was not reproduced (the replay reports `native: not_run`). `checks_passed` false is now stated.
- Confirmed: the four-step loop, the readback mismatch (ICN, DZ, P5, N2a), the straight chord arrows, the bold A to C labels, the black cycle arrows, the grey intermediate letters and blue or maroon colouring in the paper, and the missing I to III boxes and legend.
