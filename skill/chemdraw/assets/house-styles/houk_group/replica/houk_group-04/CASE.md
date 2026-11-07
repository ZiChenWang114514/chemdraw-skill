# Chen, Wipf, Houk et al., Nat. Commun. 2022, Fig. 2: Rh-catalysed annulative cleavage of bicyclo[1.1.0]butanes (partial replica)

Source: Chen, Wipf, Houk et al., "How mono- and diphosphine ligands alter regioselectivity of the Rh-catalyzed annulative cleavage of bicyclo[1.1.0]butanes", *Nature Communications* **2022**. DOI: [10.1038/s41467-022-34837-x](https://doi.org/10.1038/s41467-022-34837-x).

Licence: CC BY 4.0. The reference crop (`reference.png`) is the evidence crop `evidence/houk_group-04.png` of the `houk_group` card, reproduced under that licence.

Figure type: `catalytic_cycle` (house style `houk_group`, base preset `acs1996`), read from the card's `figure_types.catalytic_cycle` section.

## What is reproduced

Only the first entry of the cycle: substrate I (N-allyl-N-(bicyclo[1.1.0]butylmethyl)-Ts-amide) and Rh(I)Ln give the endo oxidative addition intermediate IV, in one scheme step with the step name "endo oxidative addition". The intermediates II and III are not drawn, so I to IV is collapsed into one arrow.

The two mirrored catalytic loops, the other intermediates (II, III, V to XII), the pathways A to F, the curved electron-move arrows and the products VII and XI are not drawn. `draw_figure` cannot express them (see Tool gaps), so the replica is a partial one and does not reproduce the figure's cycle.

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| cycle_shape `open_arc` (two mirrored open-arc loops around a central entry) | two mirrored loops, entry at I | one linear scheme step, no loop | no |
| pathway colours red, green, blue; solid for one manifold, dashed for the other | red, green and blue arcs; A to C solid, D to F dashed | no arcs; a single black solid arrow | no |
| `intermediate_label_style` bold_roman | bold roman I to XII | bold roman I and IV (only two intermediates drawn); the bold comes from compound_label_face, because the tool does not apply intermediate_label_style | yes |
| step names bold black along the arcs | "Reductive Elimination", "Olefin Insertion", "Rearrangement" in bold; "Endo Oxidative Addition" in bold (Endo bold italic) | "endo oxidative addition" in lower-case plain text above the arrow | no |
| path letters bold italic (path A to F) | "path A" to "path F" in bold italic | not drawn | no |
| compound_label_face bold, compound_label_color #000000 (top level) | bold black roman compound labels; Rh(I)Ln, a reagent above the arrow, in regular weight with an n subscript | I and IV bold black; Rh(I)Ln also bold black, no subscript | partly |
| abbreviate_groups Ts (top level) | Ts on the sulfonamide N | Ts | yes |
| arrow_style plain (top level) | plain solid arrows | plain solid arrow | yes |
| reagent_text_color #000000 (top level) | black | black | yes |

Matched 4 of 9 claimed conventions after audit (the first draft said 5; see Audit). Not counted: `show_plus_sign` and `substrate_layout: inline_plus` (no plus sign in the crop; the replica's "+ Rh" is not a paper feature), arrow length (the crop does have straight plain arrows; see Audit), and the card's null values (`cycle_arrow_color`, `catalyst_color`, `curved_arrow_color`, `highlight_fill`).

## Differences from the paper

- Scope: one step of a cycle with about twelve intermediates and six pathways. The replica is one arrow and two species drawn with the Rh atom.
- Rh(I)Ln is drawn as a bare `[Rh]` atom. The paper's ligand set (Lm, drawn as a subscript on Rh) is not drawn, and "Rh(I)Ln" is typed as a bold text label, so the n subscript is lost and the label is bold, where the paper sets Rh(I)Ln in regular weight.
- In IV the Rh is placed across the cyclobutane ring as a rhodabicyclo[1.1.1] unit (Rh bonded to the two former bridgehead carbons). The paper draws RhLm bonded to one carbon of the bicyclobutane frame with the small curved arrows of that step. I read this structure from the 800 px crop at low resolution; it was not checked against the SI, which is not in the chemdraw-papers folder.
- The step name is plain text, not bold, and in lower case with no italic; the paper sets it as bold "Endo Oxidative Addition" with "Endo" in bold italic. The arrow is a single black arrow where the paper has coloured arcs.
- Substrate I is drawn as a bicyclo[1.1.0]butane with a CH2 to N(Ts)(allyl). This matches the paper's I (X = NTs) as read from the figure.
- The house-style colour values (red #FF1D1E, green #38996E, blue #382DFF in the card) could not be checked on the 800 px crop: the saturated-pixel sample found only anti-aliased red (#983038, #C06870) and no clean green or blue, so the hex values are unverified here.

## Tool gaps

- The `catalytic-cycle` layout draws one closed loop of at least three steps on one circle. It has no open-arc shape, and it cannot draw two mirrored loops that share a central entry species.
- Arrow colour is set per cycle, not per step: `catalytic_cycle.cycle_arrow_color` is one value. A step's arrow in the brief can be solid, dashed, failed, reversible or resonance, but it has no colour, so the red, green and blue pathways cannot be drawn.
- Text in `above`, `below` and step names has no bold, italic or bold-italic formatting, so the bold step names and bold italic path letters ("path A") cannot be set.
- Labels have no subscripts: "Rh(I)Ln" loses the n subscript.
- Organometallic ligand sets (Lm, Ln) and eta-2 alkene coordination to Rh are not drawn; only a bare Rh atom with bonds was used.
- Small curved electron-move arrows inside intermediates (in IV, VIII and XII) come only from `kind: "mechanism"`, which cannot be combined with a catalytic-cycle layout in one brief.
- Arrow length has no control. The arrow length is set by the content width with a minimum of 5 bond lengths (`render/renderer.py`), so the card value `arrow_length_over_bond_length` 6.2 cannot be set. The replica arrow is 8.2 bond lengths.
- The house measurements (`measured`: line width 0.09 and bold width 0.22 of the bond, bond over cap height 2.4) are not applied. The drawing keeps the acs1996 preset: LineWidth 0.6 pt and BoldWidth 2 pt on a 14.4 pt bond. Only curved mechanism arrows take a weight.
- No free text. The brief takes text only as species labels and as above or below lines on an arrow, so stage names, "via" labels and path names away from an arrow cannot be drawn.
- No rotated text. Above and below lines are horizontal, so the paper's text running along diagonal arcs cannot be placed.
- No curved step arrow. `arrow` allows solid, dashed, failed, reversible and resonance only, so one step cannot be an arc.
- No per-label face. `compound_label_face` applies to every species label, so a reagent such as Rh(I)Ln cannot be regular while compound labels are bold.
- The card's catalytic-cycle conventions `cycle_shape`, `step_names` and `intermediate_label_style` are listed as skipped; only `cycle_arrow_color` is applied (`publication/house_styles.py`, `APPLIED_FIGURE_CONVENTIONS`).
- Subscripts are digit-only in the text formatter (`text_formatting.py`, `build_formatted_s_xml`), and the above and below lines are written as plain runs, so "n" or "m" subscripts cannot be drawn in any label.

## Run notes

- `draw_figure` with `render=true` returned `worker_out_of_memory` on the first attempt (OpenBLAS allocation error). The second, identical attempt succeeded and gave `native.status: rendered`, `readback: matched` (3 structures, 0 missing, 0 unexpected), `checks_passed: true`, no lint issues and balanced steps.
- No brief iterations were made after the render: the mismatch is in the figure type (a cycle that the layout cannot draw), not in the brief parameters.
- `rendered.png` is the 1200 px downscale of the ChemDraw PNG (1576 px wide); `replay.py` redraws the brief offline.

## Replay

```
python skill/chemdraw/scripts/cdx.py py skill/chemdraw/assets/house-styles/houk_group/replica/houk_group-04/replay.py NEW_DIR
python skill/chemdraw/scripts/cdx.py render NEW_DIR/figure.cdxml
```


## Audit

Second pass against reference.png, rendered.png, the CDXML from replay.py (run offline into a scratch folder; nothing else in this folder was changed) and the houk_group card.

Overclaims corrected:

- Compound labels: I and IV are bold, as in the paper. Rh(I)Ln is bold in the replica and regular in the paper, so the row is partly matched, not matched.
- Arrow length: "the crop has no straight arrow to compare" is wrong. The paper crop has plain straight arrows: the III to IV arrow is about 2.6 bond lengths (bond 12 px) and the red top arrow about 8.5. The replica arrow is 8.2 bond lengths (118.1 pt on a 14.4 pt bond). The card's 6.2 comes from one scheme crop (crop 07); its other arrow ratios are 5.0 and 11.4, so the convention is loose. Still not counted.
- Step name: the paper's step reads "Endo Oxidative Addition" in bold with "Endo" in bold italic. The replica is lower-case plain text, which was not disclosed.
- intermediate_label_style: the bold roman labels are real on the page, but the tool does not apply this style. The bold comes from compound_label_face.

Measured on the replayed CDXML and not in the first draft (all not matched):

- Bond over cap height: 14.4 pt bond over about 7.2 pt cap height (Arial 10 pt) gives about 2.0; the card has 2.4 (5 px cap over 12 px bond in the crop).
- Line width over bond: 0.6 pt over 14.4 pt gives 0.042; the card has 0.09.
- Bold width over bond: 2 pt over 14.4 pt gives 0.14; the card has 0.22.

Corrected matched count: 4 of 9 (abbreviated Ts, plain arrow, black reagent text, bold roman labels I and IV). The first draft said 5.

Not checked: the colours (the crop has no clean green or blue pixels, as disclosed); the worker_out_of_memory first attempt; the paper's IV drawing, which places Rh on one bridgehead carbon while the replica bridges both (disclosed).
