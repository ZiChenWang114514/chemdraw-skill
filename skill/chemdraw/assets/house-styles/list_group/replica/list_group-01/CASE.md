# List group, Nature 2023: asymmetric cyclization of neral to isopiperitenol (Figure 1b)

Source: List et al., "Catalytic asymmetric synthesis of cannabinoids and menthol from neral", *Nature* **2023**. DOI: [10.1038/s41586-023-05747-9](https://doi.org/10.1038/s41586-023-05747-9).

Licence: CC BY 4.0, reference crop `reference.png` reproduced under that licence (the crop is panels a and b of Figure 1; the replica covers panel b only).

Drawing style: the `list_group` house style (`cdx.py styles list_group`), base preset `nature`, figure type `reaction_scheme`.

## What is reproduced

Panel b, the single reaction: neral (Z)-3,7-dimethylocta-2,6-dienal goes to (1R,6S)-trans-isopiperitenol under iIDP catalysis, 76% yield, d.r. > 20:1, e.r. = 99:1. In the replica the catalyst is written above the arrow as text; in the paper it sits in a light teal circle on the arrow line. The selectivity lines are placed under the arrow in the replica; in the paper they sit to the right of the product.

Not reproduced: the 3D transition-state model in square brackets with the double dagger, the teal circle and ring arrow around the catalyst, and the caption "(1R,6S)-trans-isopiperitenol = unnatural enantiomer". The grey outer disc, the teal inner disc and the boxed applications belong to panel a and are outside this replica.

Structures:

| Role | SMILES in brief.json | How it was checked |
| --- | --- | --- |
| neral | `CC(C)=CCC/C(C)=C\C=O` | RDKit CIP: C2=C3 double bond is Z (rechecked in the audit) |
| (1R,6S)-trans-isopiperitenol | `O[C@@H]1C=C(C)CC[C@H]1C(C)=C` | RDKit CIP: CHOH carbon R, isopropenyl-bearing carbon S (rechecked in the audit). Drawing the paper's product from its wedge and hash bonds (OH bold, isopropenyl hashed) gives the same canonical SMILES as this string. |

No OCSR was run; both structures come from the compound names in the paper and the stereo was checked against the crop as above.

## Replay

```
python skill/chemdraw/scripts/cdx.py py skill/chemdraw/assets/house-styles/list_group/replica/list_group-01/replay.py NEW_DIR
python skill/chemdraw/scripts/cdx.py render NEW_DIR/figure.cdxml
```

`replay.py` runs `draw_figure` on `brief.json` offline and writes `figure.cdxml` and `validation.json` to a new directory. `rendered.png` is the ChemDraw render from the third try (the one kept). The first try had the selectivity text missing and the second try the same plus the teal fill; the third try adds the d.r. and e.r. lines under the arrow.

Brief history (three tries, scratch only): try 1 plain yield; try 2 adds a teal `ring_fills` on the product; try 3 adds d.r. and e.r. as `below` lines. The card was not changed.

## Table

Each row is a convention or signature feature of the card, or a visible property of panel b, checked against the paper and against the replica output. The replica's output was read from its CDXML (preset values) and from `rendered.png`.

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| reaction_scheme `yield_format` "{value}% yield" | "76% yield" | "76%" (the figure-type convention is not read by `draw_figure`; the top-level "{value}%" is applied) | no |
| reaction_scheme `selectivity_format` "e.r. = {value}" | "e.r. = 99:1" and "d.r. > 20:1", stacked right of the product | the same text, but as lines under the arrow | no (text matches, placement does not) |
| reaction_scheme `highlight_fill` #CCE6E6 | panel b has no fill behind the product; the #CCE6E6 fill in panel b is the disc behind the catalyst text | #CCE6E6 hexagon on the product, from a per-species `ring_fills` written into brief.json by hand (not read from the card) | no (colour is exact; the fill is on the wrong object and is not in panel b) |
| signature: yield, d.r., e.r. stacked to the right of the product | three lines right of the product, left aligned | "76%" under the product label; d.r. and e.r. under the arrow | no |
| signature: teal #CCE6E6 disc behind the key product | a disc behind the product exists in panel a only | hexagon fill on the product in panel b | no |
| top-level `yield_placement` under_product_label | yield right of the product in panel b | "76%" under the product | no (the card value comes from crops 02 and 03, not crop 01) |
| top-level `yield_format` "{value}%" | "76% yield" | "76%" | no |
| top-level `reagent_text_color` #000000 | black text (catalyst and selectivity lines) | rendered text is #000000 (pixel count) | yes |
| top-level `arrow_style` plain | plain line with a solid head | plain line with a solid "Full" head (CDXML) | yes (head proportions not measured) |
| top-level label font Helvetica | sans-serif, Helvetica-like | CDXML font is Arial (nature preset); the card's `measured.label_font` is stored and not applied by the drawer | no (declared face differs; Arial and Helvetica are close but not the same face) |
| conditions placement (the card's `conditions_split` is reported as skipped by the drawer) | catalyst inside a teal circle on the arrow line; no text above the arrow; selectivity right of the product | "iIDP catalysis" as text above the arrow; selectivity lines below the arrow | no |
| atom label reading | "OH" at the lower-right carbon | "HO" at the lower-left carbon (`draw_figure` gives no label-orientation control) | no |
| abbreviations (`abbreviate_groups` tBu, OMe) | no group abbreviated in panel b | no group present | not applicable (vacuous) |
| stereo wedge and hash on the product (not a card convention) | OH bold wedge, isopropenyl hashed | the same bond types; the paper drawing gives the same canonical SMILES as the replica's SMILES | yes (structure only; the label reading differs, see above) |
| bond length vs label size (`bond_length_over_cap_height` 2.65) | not measured on this crop | 10.8 pt bond and 6 pt Arial label, ratio about 2.5 (from CDXML, cap height taken as 0.716 em) | not checked against the paper |
| line width and bold width (`line_width_over_bond_length` 0.044, `bold_width_over_bond_length` 0.13) | not measured on this crop | 0.60 pt lines (0.056 of the bond) and 1.56 pt bold (0.144), both from the preset | no (card values are not applied) |
| arrow length (`arrow_length_over_bond_length` 5.9) | not measured on this crop | 56.85 pt arrow, 5.3 bond lengths | no (about 10% short of the card value) |

Claimed rows: 10 (the reaction_scheme and top-level convention rows the replicator listed). Matched: 2 (reagent text colour and plain arrow style). The label font row was previously counted as matched and is not. Stereo is checked separately and matches in structure.

## Differences from the paper

- Orientation: the paper's product ring has the methyl at the top and the OH at the lower right; the replica has the methyl at the right and the OH at the bottom.
- Yield: the paper shows "76% yield" to the right of the product, stacked with d.r. and e.r.; the replica shows "76%" under it.
- d.r. and e.r.: the paper stacks them right of the product; the replica puts them under the arrow.
- Catalyst: the paper shows "iIDP" (italic i) and "catalysis" inside a light teal (#CCE6E6) circle with two teal arcs, sitting on the arrow line so that the arrow is interrupted. The replica shows upright text above the arrow, with no circle and no arcs.
- Product fill: panel b of the paper has no fill behind the product. The replica's teal hexagon on the product is an addition taken from the card's signature features, not a feature of panel b.
- Transition state: the paper has a 3D TS model in square brackets with a double dagger; the replica has no TS.
- Caption: the paper has "(1R,6S)-trans-isopiperitenol = unnatural enantiomer" under the product; the replica does not.
- Atom label: the paper reads "OH"; the replica reads "HO".
- Neral: the paper does not label the substrate; the replica does not either.

## Tool gaps

These apply to `draw_figure` unless stated. Gaps the replicator did not list are marked "missed".

- No text block placed to the right of the product for stacked yield, d.r. and e.r. `draw_figure` places the yield under the product and selectivity only as above or below lines. Missed: `compose_chemical_figure` accepts free `text` objects with `position`, `size`, `align` and `color`, so the stacked block and the caption can be placed by hand there.
- Figure-type conventions for `reaction_scheme` (`yield_format`, `selectivity_format`, `highlight_fill`) are not read by `draw_figure`. Only the top-level conventions and the `catalytic_cycle` figure type are applied. The top-level `yield_placement` under_product_label also disagrees with the crop 01 layout (yield right of the product), so the card cannot express panel b as drawn in the paper.
- The yield regex accepts an optional "yield" word and `format_yield` reduces "76% yield" to the number through the top-level template. The brief in this case contains only "76%".
- The figure-type `highlight_fill` is not applied because the top-level value is null, so `add_highlight_fills` does nothing. The only fill is `ring_fills`, which draws a polygon. Missed: `ring_fills` accepts `style: "spline"` with `inset`, and `atom_halos` draws one filled circle per atom with a radius. Both run offline on brief.json (spline gives one closed curve; the halo variant gives six "Circle Filled" ovals). Neither was rendered, so whether they read as a disc is unchecked.
- No circular ring arrow for a single catalysed step. Missed: `compose_chemical_figure` has an `ellipse` object (solid fill, background option), so a teal circle with text inside can be drawn there. A closed curve with arrowheads is not available, because the `curve` object has no arrowhead field.
- No transition-state bracket around a 3D model or a TS image. `ts_bracket` works on a drawn species given as SMILES, so only a 2D stand-in can be bracketed.
- No free-text caption under a product in `draw_figure`. Missed: `compose_chemical_figure` `text` objects as above.
- No grey outer disc or panel behind a scheme in `draw_figure`. Missed: `compose_chemical_figure` `ellipse` with a solid fill and background. The disc is not needed for panel b.
- Missed: the card's `measured` block (`label_font`, `line_width_over_bond_length`, `bold_width_over_bond_length`, `arrow_length_over_bond_length`, `bond_length_over_cap_height`) is stored in the card and never read by the drawing path. Only `base_preset` is used, so the label font, line weights and arrow length are the preset's values.
- Missed: the card's `conditions_split` is reported as skipped ("the brief's above/below lines are kept as given"), so the reagent and solvent split is not applied.
- Missed: no atom-label orientation control, so "OH" cannot be chosen over "HO".

## Audit

Checked against reference.png, rendered.png, brief.json, the card `toolkit/cdxml_toolkit/publication/house_styles/list_group.json` and the drawing source (`figure_house.py`, `figure_draw.py`, `figure_tools.py`, `house_styles.py`).

Corrections made to this file:
- Label font row changed to no: the replica's CDXML declares Arial and the card's Helvetica is not applied.
- Matched count corrected from 3 to 2 of 10 convention rows (reagent colour, plain arrow).
- The product fill row now states that panel b has no product fill; the "background" difference referred to panel a.
- Catalyst description corrected (circle on the arrow line, not a ring around the arrow); added the italic i, the "OH" versus "HO" reading, and the conditions placement.
- The yield parenthetical corrected: the brief contains "76%", not "76% yield".
- Added the measured mismatches: arrow 5.3 bond lengths against the card's 5.9, and line and bold widths of 0.60 pt and 1.56 pt against the card's values of about 0.48 pt and 1.40 pt.
- Tool gaps extended with the `compose_chemical_figure` objects, the spline and halo options, the unapplied card `measured` block, the skipped `conditions_split` and the missing label-orientation control.

Verified: neral is Z (RDKit); the product's CIP labels are (1R,6S) and the paper drawing gives the same canonical SMILES as the replica; #CCE6E6 matches exactly; the text is #000000; the arrow is plain.

Not verified: the appearance of the spline and halo fills (offline runs only, no ChemDraw render in this audit); whether Helvetica and Arial differ visibly at this size; reference line weight (the 900 px source does not resolve it); whether `rendered.png` came from the current brief (not re-rendered).
