# ACS Chemical Biology: modified nucleosides, top row of Figure 1B (structure panel)

Source: Sun et al., "Metabolism of epigenetic ribonucleosides leads to nucleolar stress and cytotoxicity", *ACS Chem. Biol.* **2026**. DOI: [10.1021/acschembio.5c00656](https://doi.org/10.1021/acschembio.5c00656). Figure 1B.

Licence: CC BY 4.0, reference crop reproduced under that licence (card `acs_chem_biol`, evidence `acs_chem_biol-03.png`).

Drawing style: the `acs_chem_biol` house style card (`cdx.py styles acs_chem_biol`), brief `"style": "acs_chem_biol"`, base preset ACS Document 1996. Figure type: `structure_panel` and `biomolecule` (the card lists this crop under both).

## What is reproduced

The top row of the crop: six modified nucleosides on a flat ribofuranose and purine or guanine core, with the modification names under each structure: m1A, m6A, i6A, I, m6,6A, m7G. The second row (ac4C, m3C, Psi, D, m5U, acp3U, Um) and the panel D caption at the bottom edge are not drawn.

| ID | Label | SMILES in brief.json (no stereo; the crop draws no wedges) |
| --- | --- | --- |
| m1A | m¹A | `OCC1OC(n2cnc3c(N)[n+](C)cnc32)C(O)C1O` (N1 methyl cation, as drawn) |
| m6A | m⁶A | `OCC1OC(n2cnc3c(NC)ncnc32)C(O)C1O` |
| i6A | i⁶A | `CC(C)=CCNc1ncnc2c1ncn2C1OC(CO)C(O)C1O` |
| I | I | `OCC1OC(n2cnc3c(=O)[nH]cnc32)C(O)C1O` |
| m6,6A | m⁶,⁶A | `OCC1OC(n2cnc3c(N(C)C)ncnc32)C(O)C1O` |
| m7G | m⁷G | `Nc1nc2n(C3OC(CO)C(O)C3O)c[n+](C)c2c(=O)[nH]1` (N7 methyl cation, as drawn) |

All six SMILES were checked with RDKit (parse and formula) before drawing. The structures were read from the crop by eye; OCSR was not run on this 350 px crop.

Tool path: `draw_figure` brief with `"kind": "scope"` (the nearest drawer for a grid of compounds with labels). The scope panel was intended as one page with six structures on one row, but `rendered.png` shows three rows of two. The final output is in `try5` in the scratch folder; `rendered.png` is the native ChemDraw render of that page, cut into three rows at blank gaps so the image is at most 1200 px wide.

Replay: `python skill/chemdraw/scripts/cdx.py py skill/chemdraw/assets/house-styles/acs_chem_biol/replica/acs_chem_biol-03/replay.py NEW_DIR` writes `NEW_DIR/figure.cdxml/page-001.cdxml` (a scope brief writes a folder, not a single file). It was run once offline and gave 6 compounds, 1 page, readback matched. The audit did not re-run it.

## Convention comparison

The table covers the card's claims for `structure_panel` and `biomolecule` that apply to this crop, the top-level conventions that are visible here, and features the card does not record. Status is checked against the images and the toolkit source (see Audit).

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| structure_panel: same core repeated in a grid | six nucleosides on one core | six nucleosides on one core, in three rows of two | yes (grid only; the row layout is below) |
| structure_panel: only the varied group coloured blue (#4C6BFD) | modification drawn blue | all black, no colour (scope drawing skips house conventions) | no |
| structure_panel: short name under each, centred | names centred under each structure, under the ribose | names at the left edge of each cell, not centred (publication/layout.py writes the label at the cell's left edge with no justification) | no |
| structure_panel: highlight_fill null | no fill | no fill | yes |
| structure_panel: intermediate_label_style none | no intermediates in this crop | n/a | n/a |
| structure_panel: R-group key (crop 04 feature) | not in this crop | n/a | n/a |
| biomolecule: sugar_projection null, flat furanose | flat furanose, ring O at top, HO/OH labels | flat furanose, ring O at top, HO/OH labels | yes |
| biomolecule: nucleoside modifications blue on black core | blue modification (also the I C6 oxygen, and ring bonds in Psi and D) | black | no |
| top-level compound_label_color #000000 | black | black | yes |
| top-level label_font Arial | Arial | Arial (the base preset's face; the card is not applied) | yes |
| top-level aromatic_rings kekule | purine C=N double bonds drawn explicitly | same | yes |
| top-level bond_length_over_cap_height 2.0 (card value, measured on crop 05) | not measured on crop 03 (350 px crop too small) | labels at 8 pt (the scope default; the base preset's label size is 10 pt); 14.4 pt bonds over an Arial cap height of 0.716 em at 8 pt give about 2.5 | no |
| top-level line_width_over_bond_length 0.05 and bold_width 0.18 (card values, measured on crop 05) | not measured on crop 03 | the scope path passes no line or bold width for acs1996; the base preset gives 0.6 pt and 2 pt at 14.4 pt bonds (0.042 and 0.14); the card needs about 0.72 pt and 2.6 pt | no |
| layout: one row of six (top row of the crop) | one row | three rows of two in rendered.png | no |
| visible, not on card: superscript locants in names | m¹A, m⁶,⁶A, m⁷G | Unicode superscript digits in the label text | partial |
| visible, not on card: italic i in i⁶A | italic i | upright i | no |
| visible, not on card: N+ with N-methyl (m1A, m7G) | N+ with methyl | N+ with methyl | yes |
| visible, not on card: no panel title | no title | no title (title set to a single space; default "Substrate scope" otherwise) | yes |

Card rows checked: 12 (the nine rows of the first count, plus the bond-to-cap, line and bold ratios from the card's measured block). Matched: 6 (grid, no fill, flat furanose, black labels, Arial, Kekulé). The first count was 6 of 9.

## Differences from the paper

- Colour: the blue modification groups are all black. The house style is not applied to scope panels. The `style.skipped` text ("house conventions apply to schemes only; the base preset was applied") is fixed text in `figure_scope.py`, not a computed result. A scope brief has no way to colour one atom group or bond.
- Name placement: names are at the left edge of each cell, not centred under the ribose as in the crop.
- Text size: labels and atom labels are 8 pt (the scope default, which every style preset leaves unchanged), not the base preset's 10 pt.
- Name markup: superscript locants are Unicode superscript digits; the italic i in i⁶A is upright.
- Structure orientation: the tool chooses the furanose and purine orientation. The paper's purine appears steeper; this is not verified at the 350 px resolution of the crop.
- Stereo: none drawn, as in the crop (no wedges).
- Layout: `rendered.png` shows three rows of two. The crop has one row of six, and its second row is not drawn.
- Bond length and line weight: see the table. The card's ratios come from crop 05 pixel measurements; the crop 03 measurements are all null.

## Tool gaps

- A scope (structure-panel) brief ignores house conventions, and no code path implements `structure_panel` at all. `apply_figure_type_conventions` (figure_house.py) has branches only for `mechanism` and `catalytic_cycle`, and `APPLIED_FIGURE_CONVENTIONS` (publication/house_styles.py) lists only those two. Structure-panel cards cannot be applied through `draw_figure`.
- No per-group or per-bond colour in a scope brief. `substrate_colors` colours whole molecules; `new_bond_color` colours only bonds formed in a step by atom mapping, so the blue modification cannot be drawn.
- Empty `title` falls back to "Substrate scope" (`brief.get("title") or "Substrate scope"` in figure_scope.py). Only a whitespace title suppresses it. There is no option to omit the title.
- Scope labels are left-aligned at the cell edge; the scope brief has no centring option.
- No italic or superscript markup in scope compound labels; the labels are written as plain text.
- No text-size option in a scope brief. The size is 8 pt for every style preset, because `_write_inputs` pops `font_size` from the preset.
- No line or bold width for the default preset in a scope brief: `_write_inputs` writes the preset's line and bold values only for non-default presets, so acs1996 scope drawings take the compose defaults.
- `width_mm` is capped at 400 mm (figure_scope.py, validation error above 400). The replicator's stated reason is not shown: the 400 mm draw wrapped to three rows of two (the layout wraps at page width in publication/layout.py `create_pages`), so the cap was not shown to be the limit for six structures on one row.
- No control over structure orientation (ring rotation) in a scope panel.
- Native rendering was unreliable in the replicator's run (`resource_busy` after 175 s, then a timeout). Not verified in this audit.

Missed by the replicator: the lower-level `compose_chemical_figure` manifest (mcp_runtime/figure_tools.py) already accepts several of these, so a centred, italic or superscript, per-bond-coloured or rotated drawing is possible there, though not through `draw_figure` scope. Specifically:
- Text objects take `align` (Left, Center, Right) and `runs`, with per-run italic (face bit 2), superscript (bit 64) and colour.
- Molecule objects take `highlight_bonds` (sets the colour of the bonds given by index, with no halo) and a molecule-level `color`. `highlight_atoms` colours atom labels but also adds a filled halo circle, which does not match the paper's look.
- Molecule objects take `rotation` and explicit `coordinates`, so the orientation can be set.

These manifest options were read in the source only and have not been run for this case.

## Audit

Audit on 2026-11-07 by reading `reference.png`, `rendered.png`, this file, `brief.json`, the house card and the toolkit source. No drawing or replay was run, and no other file in the case folder was changed.

- Overclaims corrected: the name row was "partial" and is now "no" (left-aligned, not centred). The layout claim "one row of six, as in the crop" is contradicted by `rendered.png`, which shows three rows of two. The bond-to-cap row was "not checked" and is now "no": the scope path draws labels at 8 pt, which gives about 2.5 against the card's 2.0. The line and bold rows were not measured and are now "no": the scope path does not set them for acs1996.
- The claim that 400 mm is needed for six structures on one row is not supported by the render (see Tool gaps).
- Not verified in this audit: the replay, the `try5` output, the RDKit checks of the six SMILES, the first `resource_busy` render and the timeout, and the purine orientation of the paper.
- Corrected count: 6 of 12 card rows matched (the first count was 6 of 9).
