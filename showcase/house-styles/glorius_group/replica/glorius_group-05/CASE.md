# Wenger, Glorius et al., JACS 2025: photocatalytic cycle of a phenothiazine sulfoxide (Figure 4A, panel "A Proposed Mechanism")

Source: Wenger, Glorius et al., *J. Am. Chem. Soc.* 2025 (Phenothiazine sulfoxides as active photocatalysts for the synthesis of gamma-lactones), Figure 4A. DOI: [10.1021/jacs.5c01988](https://doi.org/10.1021/jacs.5c01988).

Licence: CC BY 4.0 (from the house-style card; reference crop reproduced under that licence).

Drawing style: the `glorius_group` house style (base preset `acs1996`), applied to the catalytic-cycle layout through `catalytic_cycle.cycle_arrow_color`, bold compound labels, black labels and reagent text, plain arrows, abbreviated Ph.

Figure type: `catalytic_cycle`.

## What is reproduced

The three-node photocatalytic loop at the centre of panel A:

- PTH-O, the ground-state sulfoxide photocatalyst, drawn black.
- PTH-O*, the excited state, joined to PTH-O by a reversible arrow labelled `hv` (the paper draws a violet lamp on the equilibrium arrows).
- PTH-O•+, joined to PTH-O* by a SET arrow labelled `2a` and `SET` with `E1/2 = 0.80 V`, and back to PTH-O by a SET arrow labelled `E1/2 = -0.19 V`.

The structure read from the crop is `O=S1c2ccccc2N(c2ccccc2)c2ccccc21` (C18H13NOS, checked with RDKit). The crop draws no charge or excited-state mark on the structure, only in the labels, so PTH-O*, PTH-O•+ and PTH-O share the same neutral graph in `brief.json` and differ by label only. The reagent 2a, `O=C1OOC(=O)C12CCC2` (C6H6O4, checked with RDKit), is in the brief as a substrate of the SET step, but the cycle layout does not draw it (see Tool gaps); the replica shows the name `2a` as text on that arrow instead.

Structures were read by hand from the crop. OCSR was not run for this crop.

## Not reproduced

- The top row (PTH to PTH•+ to PTH2+ via SET or disproportionation, and H2O to PTH-O).
- The lower branch: the reduced 2a species, the ΔG = -18.4 kcal/mol step, the radical intermediates, product 3a and by-product 5 (dashed arrow from 2a). The crop is cut off at the bottom, so the intermediates there are only partly visible and their structures and bonds cannot be written with confidence. For reference, 3a in the crop reads as `O=C1OC(c2ccccc2)CC12CCC2` (C13H14O2), but it is not drawn here.
- The boxed quantum yield (Φrxn = 0.55) in the centre.
- The panel title "A Proposed Mechanism" (dropped by the layout, see Tool gaps).

## Attempts

Try 1 (brief with the title, and 2a only as a substrate of the SET step): ChemDraw render produced, readback `mismatch` (2a missing), title not drawn. Try 2 (current `brief.json`): removed the title, added the text `2a` above the SET arrow. The same readback mismatch remains because the structure of 2a is still not drawn. Two of the three allowed tries used.

## Replay

```
python skill/chemdraw/scripts/cdx.py py skill/chemdraw/assets/house-styles/glorius_group/replica/glorius_group-05/replay.py NEW_DIR
python skill/chemdraw/scripts/cdx.py draw skill/chemdraw/assets/house-styles/glorius_group/replica/glorius_group-05/brief.json NEW_DIR/figure.cdxml --render
```

`replay.py` draws `brief.json` offline into `NEW_DIR` (`figure.cdxml`, `validation.json`); it was run once to check this. `rendered.png` is the desktop ChemDraw render of the same brief (native status `rendered`). Its report shows `checks_passed: false` (readback mismatch and the step 2 balance warning); see below.

## Convention comparison

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| `catalytic_cycle.cycle_shape` circle (card) | loop of curved arcs around the nodes | triangle with straight chord arrows | no |
| `catalytic_cycle.cycle_arrow_color` #000000 | black cycle arrows | black (report `applied`) | yes |
| `catalytic_cycle.catalyst_color` #000000 | PTH-O (the catalyst) in black | PTH-O in black | yes |
| `catalytic_cycle.center_label` (boxed quantum yield) | boxed Φrxn = 0.55 at the centre | not drawn; the layout has no centre box | no |
| `catalytic_cycle.step_names` (SET, bold italic dark red) | SET bold italic dark red | SET as plain black text | no |
| `catalytic_cycle.curved_arrow_color` #000000 | thin black curved arcs | straight black arrows | no |
| `compound_label_face` bold | PTH-O, PTH-O*, PTH-O•+ in bold | bold | yes |
| `compound_label_color` #000000 | black | black | yes |
| label font Arial (measured) | sans serif, Arial-like | sans serif in the PNG; the face name cannot be checked from the folder (no CDXML) | no |
| `arrow_style` plain | plain arrow heads | plain heads | yes |
| `reagent_text_color` #000000 | conditions in black (E1/2 values in dark red) | conditions and 2a in black; E1/2 values also black, not dark red | no |
| `abbreviate_groups` Ph | Ph | Ph | yes |
| `substrate_colors` (card: crops 01 and 02 only) | black structures | black structures; the report says `applied`, but no colour reached the file (see Tool gaps) | no |
| panel title: bold italic with parenthesised capital (card) | "A Proposed Mechanism": bold, upright, no parentheses | no title drawn | no |

Claimed conventions in this table: 14. Matching: 6 (corrected by the Audit below; the replicator counted 8).

Not counted: the bond length to label cap-height ratio and the line width, which were not measured on the replica (the render looks close to the crop by eye); `yield_placement`, `new_bond_color`, `highlight_fill` and `show_plus_sign`, which do not apply to this cycle.

## Differences from the paper

- Shape: a triangle with straight chord arrows; the paper has a loop of curved arcs. PTH-O is at the top, PTH-O* lower right and PTH-O•+ lower left. The paper has PTH-O at the upper right, PTH-O* on the left and PTH-O•+ at the bottom, and its loop runs counter-clockwise on the page; the tool runs clockwise from the first step.
- The violet lamp is replaced by the text `hv`; the equilibrium arrows are drawn as a double-headed arrow.
- SET and the potentials are plain black text, not bold italic dark red.
- 2a is text on the SET arrow, not a drawn structure (the paper draws it as a structure with a curved arrow).
- The boxed quantum yield is absent.
- No panel title.
- The top row and the bottom branch (lower intermediates, ΔG, 3a, 5) are absent, as explained under Not reproduced.
- The radical cation PTH-O•+ and the excited state PTH-O* are drawn as the neutral graph; the charge and excitation are in the labels only, as in the paper.

## Tool gaps

- `catalytic-cycle` draws only the first substrate of each step as a ring node (`_layout_catalytic_cycle` in `toolkit/cdxml_toolkit/render/renderer.py`). A second reactant such as 2a, and any product that is not the next ring node, is silently dropped. The docs in `skill/chemdraw/references/scheme-drawing.md` say entering reactants and departing products are placed on radial in and out arrows; the code does not do this. The report shows it only as readback `mismatch` (`missing: ["R"]`, `checks_passed: false`).
- The `title` key is ignored in the catalytic-cycle layout; the report and the PNG have no title.
- Cycle arrows are straight chords between node positions on a polygon. The tool cannot draw curved cycle arcs (`curved_arrow_color`) or a circular loop; `cycle_shape` is guidance only.
- The layout's direction is fixed: the cycle is placed clockwise from the first step, so the orientation of the paper's loop cannot be chosen.
- No violet lamp or photon symbol on an arrow, no boxed centre label, and no run-level styling (bold italic, colour) for step names or potentials.
- `substrate_colors` is reported as `applied` for this cycle but nothing is coloured. Ring nodes are products of some step and are skipped, and the second substrate 2a is not drawn, so its colour (#0203FE) has nowhere to go; the file's colour table also has no #2C0001. The `applied` entry in the report is therefore misleading for cycles.
- Step 2 is an electron transfer; 2a fragments on reduction. The atom-balance check reports that the products lack `C6H6O4` (the formula of 2a itself). There is no way to write an electron transfer to a fragmenting reagent without naming the reduced species, so this warning is a false positive for this step. The step is still drawn as written.
- Radical cations and excited states cannot be shown as drawn marks on a structure: the brief can carry charged or radical SMILES, but the crop shows the bare graph, so they are left neutral here.

## Card observations (reported only; the card was not edited)

- Top-level signature "panel titles as bold italic text with a parenthesised capital letter, e.g. (A) Reagent synthesis": this crop's title is "A Proposed Mechanism", bold and upright with no parentheses (checked by zooming on the crop's top-left corner). The card's pattern holds for crop 01 only.
- Top-level `substrate_colors` (#2C0001, #0203FE) has no figure-type restriction, but its note says crops 01 and 02 only. Crop 05 shows black structures.
- Top-level `line_width_over_bond_length` 0.075: crop 05 gives 6 / 72 = 0.083 from the card's own `measurements_px`. The median of the three crops with a line width and bond length (01: 0.078, 03: 0.063, 05: 0.083) is 0.078, not 0.075.
- Top-level signature "energy-transfer step drawn as a cyan lamp icon #31BCFA": crop 05 draws the photoexcitation lamp in violet #5828FF, as the `catalytic_cycle` section says. The top-level sentence does not say which step it refers to.

## Audit

Independent check (Haiku 5.5, high) against reference.png, rendered.png, brief.json, the house-style card and the toolkit code. The table above was corrected: the label font and reagent text colour rows are now "no", so the count is 6, not 8.

- **Label font:** the face name is not verifiable from this folder (no figure.cdxml, no font record). The PNG looks sans serif, but "Arial in the ChemDraw render" was not checked. Counted as not matched.
- **Reagent text colour:** the row's own paper column records dark red E1/2 values. The replica draws them black, so the row cannot be "yes".
- **Kept as matched on visual check:** cycle arrows black, PTH-O black, compound labels bold and black, plain arrowheads, Ph abbreviation.
- **Proportions and line weight:** not measured. The replica's bond length was never taken, so the line-width ratio cannot be checked. Shaft thickness alone (about 3 px in reference.png, 2 px in rendered.png, different image widths) does not settle it.
- **"False positive" balance warning (Tool gaps):** overstated. Step 2 lists 2a as a substrate and no product carries its fragment, so the check reports the brief as written. The real gap is that a fragmenting reagent cannot be written into a SET step without naming the reduced species.
- **"Cannot be drawn" charge and radical marks (Tool gaps):** the same section says the brief can carry charged or radical SMILES, so the limit is not shown. Keeping the neutral graph was a choice that follows the crop. Not tested here.
- **Step 2 label placement (not in the replicator's list):** rendered.png puts E1/2 = 0.80 V on the page-top side of the arrow and 2a and SET on the page-bottom side. The paper stacks SET over E1/2 on one side of the arc. The statement that 2a is "text on that arrow" describes the brief, not the page.
- **Evidence not in the folder:** validation.json and figure.cdxml are absent, so the readback mismatch, the "applied" report and the missing #2C0001 colour entry could not be checked here.

Missed tool gaps (checked in the code):

- Above and below condition labels on a cycle are placed radially (outside above, inside below) relative to the cycle centre (toolkit/cdxml_toolkit/render/renderer.py, step 3 of `_layout_catalytic_cycle`), so a page-relative order cannot be chosen.
- skill/chemdraw/references/scheme-drawing.md (line 40) documents a `cycle_radius` parameter (default 120 pt) and curved arrows along the circumference. renderer.py has no `cycle_radius` and draws straight chords.
- The title is stored on the SchemeDescriptor (toolkit/cdxml_toolkit/mcp_runtime/figure_draw.py, line 205), but renderer.py never reads it.
- `substrate_colors` (toolkit/cdxml_toolkit/mcp_runtime/figure_house.py, lines 333-346) appends "applied" whenever the convention is set, even when nothing is painted, and it is not limited to the crops the card's note names.
- The hv equilibrium is a straight double arrow. The paper draws a curved pair, and no option produces that.

The card observations check out against the card's own measurements (6 / 72 = 0.083; the median of 0.078, 0.063 and 0.083 is 0.078).
