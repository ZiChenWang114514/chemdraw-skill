# JACS Au: graphical abstract (TOC), HAT step of the tagged H-donor (Ravelli et al., 2025)

Source: Ravelli et al., "A decarbonylative strategy to enhance efficiency and regioselectivity in photocatalyzed HAT", *JACS Au* **2025**. DOI: [10.1021/jacsau.5c00530](https://doi.org/10.1021/jacsau.5c00530). Licence: CC BY 4.0 (from the house style card `jacs_au`, evidence crop `jacs_au-09`, graphical abstract (TOC)).

Drawing style: the `jacs_au` house style card, `graphical_abstract` section, with the top-level conventions for arrows and reagent text. Base preset: acs1996.

## What is reproduced

The top path of the TOC only: the tagged H-donor (generic R-CH2-CH2-CH(R)-CHO, the aldehyde being the traceless activating group) goes to the alkyl radical under "HAT, photocatalyst" with a plain black arrow. The crop's R groups are generic circles, so they are drawn as `*` atoms and given the crop's fill colours with atom halos (blue #7CBEF0 on the left R, orange #FFAA73 on the right R, green #26A83E on the CHO carbon). The halos are plain fills: the crop's discs also carry coloured outlines and no letter, while the replica prints R in them. The radical dot is drawn above the radical carbon; the crop shows that carbon as an unlabelled vertex, while the replica also prints H and C on it.

Not reproduced: the activation and fragmentation pathway (grey block arrows), the "Traceless Activating Group" definition box, the grey claims bar with bullets, the lightbulb, the red HAT label, the flag-shaped activating group, the coloured H labels, and the dashed arrow to the C(sp3)-C(sp3) and C(sp3)-C(sp) outcomes. Details are under "Tool gaps".

The brief is `brief.json` (one linear step, two species, halos on the generic atoms). `rendered.png` is the ChemDraw render of the final brief (978 px wide).

OCSR was not run. The crop is a concept drawing with generic R groups and an unlabelled H-donor, so no engine would return a grounded structure; the species follow the crop's own generic connectivity, not a named compound. The balance check reports the step as unchecked (`generic atoms (R groups, *) cannot be balanced`), so the by-products of the real step (CO from the fragmentation and the H passed to the photocatalyst) are not named or drawn.

## Replay

```
python skill/chemdraw/scripts/cdx.py py skill/chemdraw/assets/house-styles/jacs_au/replica/jacs_au-09/replay.py NEW_DIR
python skill/chemdraw/scripts/cdx.py render NEW_DIR/figure.cdxml
```

`replay.py` runs `draw_figure` on `brief.json` offline and writes `figure.cdxml` and `validation.json` into a new folder.

## Brief history

- v1: two species, `*` for the R groups, plain black R labels, no halos. Rendered and checked: the structures and arrow are right, but the R groups are plain and the aldehyde carbon has no colour.
- v2: atom halos added on the R atoms (blue, orange) and on the aldehyde carbon (green), radius 9 and 7. The halos are about one bond length across, a little larger than the crop's discs.
- v3 (final): halo radii 7.5 for the R groups and 8 for the green carbon. The draft readback is `matched` (2 structures, no missing or unexpected), `checks_passed` true.

## Comparison

Rows cover the `graphical_abstract` claims the card makes that are visible in crop 09, and the top-level scheme conventions visible in the crop. The compound label rows are n/a: the crop has no numbered compounds.

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| `graphical_abstract.background_fill` null | white inside a light grey rounded frame | white background, no frame | n/a (null) |
| `graphical_abstract.highlight_fill` #DEE2E3 | grey bar behind the claims list | no bar; the tool's highlight_fill is a fill behind a product ring and was not applied | no |
| `graphical_abstract.variation_color`, `this_work_color` null | none | none | n/a (null) |
| signature: white background | present | present | yes |
| signature: concept scheme reused from Figure 1 | not checkable from this crop alone | a fresh one-step drawing, not the Figure 1 scheme | no |
| signature: claims as italic text in a grey bar with square bullets | present | absent | no |
| signature: key concept in a black box (activating group) | present | absent | no |
| top: `arrow_style` plain | main HAT arrow plain black; activation and fragmentation are thick grey block arrows | main HAT arrow plain black, solid | yes (style only; length and weight not matched, see Audit) |
| top: `reagent_text_color` #000000 | "photocatalyst" black italic, "HAT" bold red | black text, "HAT" not red, not italic | no (the value matches; the bold red HAT and italic photocatalyst are not reproduced) |
| top: `show_plus_sign`, `aromatic_rings`, `substrate_layout`, `new_bond_color` | no plus, no rings, no new-bond colour in this crop | not applicable | n/a |
| R groups as coloured discs (blue #7CBEF0, orange #FFAA73) | blue and orange discs with coloured outlines (blue and red rings), no letter | same fills as atom halos, no outline, R printed inside | no (fills match; outline and letter do not) |
| activating group (TAG) as green flag over C(=O)H, red H | green flag, red aldehyde H | green halo circle on the CHO carbon; no flag; no H drawn | no |
| radical dot on the radical carbon | dot above an unlabelled vertex with no H | dot above a carbon labelled C with an H above it | no |
| H labels coloured (blue, purple, red) | coloured H labels on CH2 and CH | chain H implicit; one black H on the radical carbon | no |
| single left-to-right row, HAT arrow above | HAT sits on the shaft and breaks it, photocatalyst below the arrow; the row runs on to a dashed arrow | HAT and photocatalyst both above the arrow; no dashed arrow | no |

Summary: `claimed` counts the four figure-type rows that are visible in the crop (white background, reuse of Figure 1, the grey claims bar and highlight_fill, the boxed concept) plus the two visible top-level rows (`arrow_style`, `reagent_text_color`), so 6. `matched` counts the rows marked yes among those: white background and the plain main arrow, so 2. The halo, radical and single-row rows are extras, not card claims, and the Audit below corrects their marks.

## Differences from the paper

- The paper's donor is a concept drawing with a green flag for the activating group; the replica draws a plain aldehyde with a green halo on its carbon.
- The paper's coloured H labels (red aldehyde H, blue and purple H on the chain) are all absent: the replica leaves the chain H implicit and prints one black H on the radical carbon, which the crop does not show.
- The paper's HAT label is bold red and the lightbulb sits above it; the replica has plain "HAT" and "photocatalyst" text and no bulb.
- The paper's activation and fragmentation pathway (grey block arrows, the acyl radical losing CO) is not drawn. The replica shows the direct HAT step only, so the mechanism that the TOC is about (traceless loss of the group) is not in the figure.
- The dashed arrow to the two C-C products and their green bond text is not drawn.
- The claims grey bar, the bullets and the "Traceless Activating Group" box are not drawn.
- The R groups are generic `*` atoms, so the balance check is not run and the by-products are not named.

## Tool gaps

- No per-atom colour for hydrogen or element labels. Atom halos are circles behind the atom, not coloured labels, so the red aldehyde H and the blue and purple chain H cannot be reproduced.
- No custom glyph for a structure part. The paper's green flag over the aldehyde has no drawing path; the nearest is a green halo circle.
- No block or coloured arrow styles. `arrow` takes only solid, dashed, failed, reversible and resonance. The thick grey activation and fragmentation arrows, and the dashed arrow to text-only products, cannot be drawn.
- No text-only product outcomes in a step. Products must be structures, so the C(sp3)-C(sp3) and C(sp3)-C(sp) outcome lines cannot be placed next to their arrow.
- No boxed text or boxed structure, no grey bar behind text, no bullet list with square bullets. The TAG definition box and the claims bar cannot be drawn.
- No lightbulb or outlined icon above an arrow.
- No coloured or italic step text. "HAT" (bold red) and "photocatalyst" (italic) come out as plain black text.
- Generic R groups stop the balance check (`generic atoms (R groups, *) cannot be balanced`), so a real step's by-products cannot be named or checked.
- A multi-path concept diagram (a main path plus a bottom activation path, meeting at the fragmentation step) has no layout. The draw_figure layouts are linear, convergent, divergent or catalytic-cycle; a free two-row concept layout is not one of them.

## Structure issues

- The H-donor connectivity is read from a low-resolution concept drawing: a blue R on one end, a CH2-CH2 chain, a CH bearing an orange R and the activating CHO. The blue, purple and red H labels are legible in the crop, but the replica leaves the chain H implicit, colours no H, and uses generic `*` atoms, not a named compound.
- The fragmentation product (CO loss) and the acyl radical of the activation pathway are not drawn; they cannot be grounded from this crop.
- Only the main HAT step is in the brief. The TAG legend structure (`C(=O)H`) is not drawn as its own species, because it is not part of the step and would be an unused species.

## Audit

Checked against reference.png, rendered.png, brief.json and the house card (`toolkit/cdxml_toolkit/publication/house_styles/jacs_au.json`). The measurements are approximate: thicknesses and arrow extents are pixel counts, bond lengths are read by eye from the crop.

Overclaims corrected in the table and text above:

- R groups as coloured discs was `yes`. The crop's discs have coloured outlines and no letter; the replica's halos have no outline and print R.
- The radical dot row was `yes`, and the text said the dot sits on the H-bearing carbon "as in the crop". The crop's radical carbon has no H and no C label; the replica prints both.
- The single-row row with "HAT arrow above" was `yes`. In the crop HAT sits on the shaft and breaks it, and photocatalyst is below the arrow; the replica puts both above. The crop's row also runs on to a dashed arrow.
- The TAG row was `partly`. The replica has no flag and no H, only a green disc on the carbon.
- The reagent_text_color row was `partly`. Black text equals the card value, but the crop's bold red HAT and italic photocatalyst are not reproduced, so it is not counted.
- The text said the purple H labels were not resolvable and that the replica has implicit H only. The crop's H labels are legible, and the replica prints one black H on the radical carbon.

Corrected count: claimed 6, matched 2 (white background, plain arrow style). The white background row stays `yes` as a card signature, although the crop sits inside a light grey frame that the replica lacks. The arrow row is style only: the crop's arrow is about 6 bond lengths long and the replica's about 5, and the crop's HAT interrupts the shaft.

Not checkable from this folder: validation.json and figure.cdxml are absent, so the balance-check wording and "checks_passed true" in the brief history cannot be verified here.

Tool gaps the replicator did not list (checked in the toolkit code):

- Line weight and proportions: the house card's measured geometry (line_width_over_bond_length 0.09, arrow_length_over_bond_length 3.2, label size 9.8) is not read by any drawing code. Geometry always comes from the base acs1996 preset (0.6 pt line on a 14.4 pt bond, a ratio of 0.042). The replica's bond line is about 0.03 of bond length against about 0.08 in the crop, so it is roughly half as heavy.
- Halo outlines: atom_halos draw "Circle Filled" only (figure_draw.py, halo loop), so there is no outline colour or width.
- Label-free placeholders: generic `*` atoms always print R; there is no empty substituent disc.
- Text on the shaft: ArrowContent (render/schema.py) takes only above and below lines, so the crop's HAT-on-shaft layout cannot be drawn.
- Captions: species have no caption field, so the italic "tagged H-donor" and "activation" captions cannot be placed under structures.
- Outer frame: there is no frame or border option for the whole figure.
- Arrow weight: thin, bond and bold exist (figure_house.py, _ARROW_WEIGHTS), but only as the house arrow_style convention, applied to every arrow; there is no per-arrow weight.
- Reagent styling: the house reagent_text_color paints all reagent text one colour; there is no per-line or per-word bold or italic.
- Colour scope: whole-species colour exists (the substrate_colors convention paints a full fragment). Per-atom colour does not, so the H-colour gap is right, but it is narrower than the wording suggests.

