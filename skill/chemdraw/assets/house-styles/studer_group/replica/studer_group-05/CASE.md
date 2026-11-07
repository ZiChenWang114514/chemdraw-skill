# studer_group-05: decatungstate radical disulfuration, visible part of Fig. 3

## Source

Studer et al., *Nat. Commun.* **2022**, decatungstate-catalyzed radical disulfuration through direct C-H functionalization. DOI: [10.1038/s41467-022-31617-5](https://doi.org/10.1038/s41467-022-31617-5). Licence: CC BY 4.0. Reference crop: `evidence/studer_group-05.png` (Fig. 3, top part of the figure). The full figure also shows the tetrabutylammonium decatungstate cluster (TBADT 1) below the crop; the crop cuts it off.

House style: `studer_group` (base preset `nature`).

## Figure type

`catalytic_cycle` (card figure type). The crop is a cycle with a radical chain attached, so the replica is judged against the cycle conventions and the top-level scheme conventions.

## What is reproduced

The organic half of the figure, as a sequential scheme:

- `2a` (cyclohexane) to `2a'` (cyclohexyl radical), with "TBADT (cat.)" and "hν" above the arrow;
- `2a'` + `3` (`[*]SSSS[*]`, R-S-S-S-S-R) to `4` (cyclohexyl-S-S-R) plus the radical `rss` (`[*]S[S]`, R-S-S•), labelled "radical substitution".

Not reproduced: the catalyst cycle (the 1*, H[W10O32]4- and [W10O32]4- species, the HAT and SET arcs, the proton transfer, Na2S2O8 with HNaSO4 and NaSO4•), the lightning bolt and wavy arrow, the homo-coupling arrow from `rss` back to `3`, and the TBADT cluster.

## Structures

| ID | Replica SMILES (brief.json) | Reading of the crop |
| --- | --- | --- |
| 2a | `C1CCCCC1` | cyclohexane, read directly from the crop |
| 2a' | `[CH]1CCCCC1` | cyclohexyl radical; the crop shows the radical orbital |
| 3 | `[*]SSSS[*]` | R-S-S-S-S-R, R is the orange disc; `[*]` is a generic R, not a specific group |
| 4 | `C1CCC(CC1)SS[*]` | cyclohexyl-S-S-R; R as above |
| rss | `[*]S[S]` | R-S-S• radical; `[*]` as above |

No OCSR was run on this crop: the structures are simple and the R group is generic, so a reader would only confirm what is in the crop. All SMILES were checked against the crop by eye.

## Replay

```
python skill/chemdraw/scripts/cdx.py py skill/chemdraw/assets/house-styles/studer_group/replica/studer_group-05/replay.py NEW_DIR
python skill/chemdraw/scripts/cdx.py render NEW_DIR/figure.cdxml
```

`rendered.png` is the desktop ChemDraw render of `brief.json`, downscaled from 1493 px to 1200 px wide. It is the third run of the brief; runs 1 and 2 are described under Run log.

## Convention table

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| cycle_shape circle | circle of large black arcs | no cycle; steps in one row (sequential layout) | no |
| cycle_arrow_color #000000 | black | black plain arrows only, no cycle arrows | no |
| catalyst_color #000000 | TBADT cluster drawn as a black structure (not in crop) | "TBADT (cat.)" as black text, no structure | no |
| center_label false | no centre label (there is no cycle, so the convention is not tested) | none | no |
| step_names true | HAT, SET, proton transfer, radical substitution, homo coupling | "radical substitution" only | no |
| curved_arrow_color #000000 | black curved arcs | no curved arrows | no |
| step names bold italic navy #000080 (signature) | bold italic navy | plain black text | no |
| lightning bolt #FFFF00 with wavy arrow (signature) | yellow bolt with wavy arrow | "hν" as text | no |
| R in orange #FF8000 discs, S in dark red #800000 (signature) | orange discs, dark red S | plain "R" letters, black S | no |
| compound labels bold | bold 2a, 3, 4 | bold 2a, 3, 4 | yes |
| compound label colour #000000 | black | black | yes |
| 2a' with a prime, upright | 2a' upright | 2a′ upright | yes |
| inline plus between substrates | "+" between 2a' and 3, and between 4 and rss | "+" in both places | yes |
| arrow_style plain | plain straight arrows, filled heads | plain straight arrows, filled heads | yes (plain only; the earlier "open heads" wording was wrong for both) |
| reagent_text_color #000000 | Na2S2O8 is black, but the catalyst name ([W10O32]4-, 1*) is navy bold and the step names are navy | "TBADT (cat.)" and "hν" as black text; Na2S2O8 not drawn | no |
| highlight_fill null | lavender #8080FF halos on the reacting C-H of 2a and on the ring carbon bonded to S in 4 | none | no |
| new_bond_color #FF0000 (top level) | the formed C-S bond is black in this crop, so the card's red rule does not describe this crop | red rule not applied; formed bonds not mapped (generic R), drawn black | no (the black result is the crop's outcome, not the convention) |
| line width / bond length 0.05 | thin lines, about 0.044 from 2 px over 45 px (a 900 px crop, so the 2 px reading is about +/-0.5 px) | 0.6 / 10.8 = 0.056, the nature preset values, not the card's measured 0.05 | no |
| bond length / cap height 2.5 (top level) | 45 / 20 = 2.25 (card note 2.3) | about 2.5 from LabelSize 6 pt and BondLength 10.8 pt, not pixel-measured | no |
| label font Helvetica | sans-serif, Helvetica-like | Arial (nature preset) | no |

Counts: 5 of 20 rows match after the audit (see Audit). Rows 1 to 9 are the catalytic_cycle figure-type claims (0 matches; the replica is not a cycle). Rows 10 to 20 are top-level scheme conventions visible in the crop (5 matches: compound label face, compound label colour, 2a' prime, inline plus, plain arrow style).

## Differences from the paper

- Layout: the paper is a closed cycle around the catalyst with the substrate branch at the top right. The replica is a single row, so the cycle is lost.
- Catalyst: TBADT is named as text, not drawn. The cluster is absent.
- Radical: the paper draws the cyclohexyl radical with a single-electron orbital and the R-S-S• radical with a dot. The replica draws plain structures; the radical flag is stored in the CDXML but no dot appears in the render.
- Colour: the orange R discs, dark red S atoms and the lavender halos on the reacting C-H in 2a and on the ring carbon bonded to S in 4 are not drawn. The replica uses black throughout. The explicit bold H on the reacting carbon of 2a is also missing: the replica's 2a is a plain hexagon.
- Step names: "HAT", "SET" and "proton transfer" are missing; "radical substitution" is plain black text, not bold italic navy.
- Radical chain: the homo-coupling arrow from the R-S-S• radical back to 3 is missing, so the replica is not closed.
- Geometry: the paper draws 3 as a zig-zag chain with the S atoms staggered; the replica draws it as a vertical zig-zag. The paper's 4 has the ring at the left; the replica has the ring at the bottom.
- Font: Arial (nature preset) in place of Helvetica in the draw_figure output.
- Balance: step 1 (2a to 2a') does not balance without the catalytic H-acceptor, which the cycle would draw. The tool named the missing H and did not draw it.

## Tool gaps

- Catalytic-cycle layout in draw_figure needs every catalyst state as a species with a SMILES or a curated name. The polyoxometalate states ([W10O32]4-, H[W10O32]4-, 1*) and TBADT cannot be written without a verified SMILES, and no name lookup for TBADT was tried. No SMILES was guessed. Not tried: compose_chemical_figure (toolkit/cdxml_toolkit/mcp_runtime/figure_tools.py) takes explicit point coordinates and text items, so catalyst states could be plain text labels placed on a circle, with no SMILES.
- A loop of steps with no catalyst species is refused with the default layout: "The steps form a cycle: a product feeds back into its own route." The homo-coupling return (rss + rss to 3) therefore cannot be drawn in this brief. The catalytic-cycle layout was not tried with this crop's species.
- Generic R atoms (`[*]`) are not balanced and not atom-mapped ("generic atoms (R groups, *) cannot be balanced"), so `new_bond_color` is skipped and the formed C-S bond stays black. The card's red new-bond rule cannot be tested here.
- R groups are drawn as plain R letters, not in an orange disc. atom_halos (figure_draw.py) accepts a hex colour and a radius, so an orange disc behind the R atom is possible; this was not tried. The halo is drawn as an opaque filled oval, not the reference's shaded disc, and no translucent option was found.
- A radical flag (`Radical="Doublet"`) is saved in the CDXML for 2a' and rss, but no radical dot or orbital appears in the render. draw_figure has no orbital item. compose_chemical_figure has orbital items (orbital_type) and a native Electron symbol, so a radical orbital or dot there is possible; not tried.
- Photoexcitation in draw_figure: there is no symbol, and step arrows are only solid, dashed, failed, reversible or resonance, so the lightning bolt (yellow) and wavy arrow cannot be drawn there. compose_chemical_figure has curve items with explicit points and a colour, so a bolt and a wavy arrow could be drawn as custom curves (no bolt primitive exists); not tried. "hν" is text only.
- Step-name styling (bold italic navy, grey) cannot be set on above or below lines in draw_figure; its brief takes plain text only. compose_chemical_figure text items take runs with bold, italic, underline and a colour per run, so bold italic navy step names are possible there; not tried.
- The card's measured block (bond_length_over_cap_height 2.5, line_width_over_bond_length 0.05, arrow_length_over_bond_length 6.9, label_font Helvetica) is never read by the draw path. Only the card loader in publication/house_styles.py touches it. The geometry comes from the base preset (nature: BondLength 10.8, LineWidth 0.6, LabelSize 6), and the arrow length is neither applied nor reported as skipped.
- The nature base preset sets Arial, not Helvetica, and draw_figure cannot override the font. compose_chemical_figure accepts a style "font" field (for example Helvetica); this gap is specific to draw_figure, and the option was not tried.
- draw_figure step arrows are straight only. The curved HAT and SET arcs of the cycle, and the curved homo-coupling return, cannot be drawn in the scheme layout. Curved arrows exist only as electron-pushing moves between atoms in a mechanism brief (figure_mechanism.py) or as electron_arrow and curve items in compose_chemical_figure.
- No control of molecule orientation or the zig-zag direction of multi-sulfur chains.
- ChemDraw contention: the first render attempt returned `resource_busy` (chemdraw_com busy for 295 s). Parallel runs that share the one ChemDraw COM instance will collide.

## Run log

- run 1 (brief with a homo-coupling step back to 3): refused, "The steps form a cycle: a product feeds back into its own route" (no render).
- run 2 (two steps, the brief in this folder): `resource_busy`, chemdraw_com remained busy for 295 s.
- run 3 (same brief as run 2, retried once): ok, `checks_passed: true`, readback matched (5 structures), native rendered; warnings for the step 1 balance and the generic-atom balance. This is the brief in this folder.

## Audit

Second, independent pass. Checked: `reference.png` and `rendered.png` (enlarged crops of both), this CASE.md, `brief.json`, `replay.py`, the card `toolkit/cdxml_toolkit/publication/house_styles/studer_group.json`, and the draw path in the toolkit (`mcp_runtime/figure_draw.py`, `figure_house.py`, `figure_tools.py`, `chemdraw/style_presets.py`, `render/route_graph.py`, `mcp_runtime/report_tools.py`).

Overclaims corrected in the table:

- center_label: a convention about the centre of a cycle is not tested by a sequential row. Now no.
- arrow_style: both paper and replica use filled arrowheads, so "open heads" was wrong. The row still matches on plain straight arrows.
- reagent_text_color: Na2S2O8 is black in the crop, but the catalyst name is navy bold and the step names are navy. The replica's black catalyst text does not match. Now no.
- highlight_fill: the crop has lavender halos on the reacting C-H of 2a and on the ring carbon bonded to S in 4. The card value null does not describe this crop, and the replica draws none. Now no.
- new_bond_color: the black result matches the crop only because the crop is black. The red rule was not applied and could not be applied (generic R atoms). Now no.
- line width: the replica uses the nature preset values (0.6 / 10.8 = 0.056), not the card's measured 0.05. The paper's own reading (0.044) differs from the replica by more than the row admitted. Now no.
- Counts: 10 of 20 becomes 5 of 20. The catalytic-cycle rows are 0 of 9.

Verified as stated: compound labels are bold and black (zoomed), 2a' has an upright prime, the inline plus appears twice (the second joins products 4 and rss, which the card's substrate rule does not cover, but the crop shows it), bond to cap height is not matched (45 / 20 = 2.25 from this crop), label font is Arial in the replica, the step-arrow shaft is plain.

Verified in code: the generic-atom balance refusal (`report_tools.py`), the cycle refusal (`route_graph.py`), the five straight step-arrow types only (`figure_draw.py`), the nature preset values (`style_presets.py`), the card's `measured` block is not read by the draw path, and `atom_halos` accepts hex colours (`figure_draw.py`).

Tool gaps the replicator missed, mostly because only `draw_figure` was tried: `compose_chemical_figure` (`figure_tools.py`) takes explicit coordinates, text runs with bold, italic and colour, a style `font`, orbital items, curve and electron-arrow items, and symbol items. Those cover the Helvetica, step-name styling, radical orbital, catalyst-as-text and curved-arc gaps, in principle. None of this was tried, so the gaps are "draw_figure only", not "toolkit cannot".

Not verifiable from this folder: `rendered.png` is 1200 px wide, consistent with the claim, but the 1493 px source, the `validation.json`, the `figure.cdxml` (0.6 / 10.8 values), the run log, and the `resource_busy` timing are not in the folder. Those statements rest on the replicator's own report.

Overall: the replica is a sequential scheme, not the paper's catalytic cycle. The figure-type rows are not matched, and the honest match count is 5 of 20.
