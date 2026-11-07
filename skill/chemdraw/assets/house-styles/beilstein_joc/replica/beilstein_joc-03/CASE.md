# Beilstein JOC: Pd catalytic cycle for C1 nitration of carbazole (Figure 2)

Source: Gandeepan et al., "Palladium-catalyzed regioselective C1-selective nitration of carbazoles", *Beilstein J. Org. Chem.* **2025**, *21*, 190. DOI: [10.3762/bjoc.21.190](https://doi.org/10.3762/bjoc.21.190). Figure 2 (catalytic cycle). Licence: CC BY 4.0, reference crop reproduced under that licence.

Drawing style: the `beilstein_joc` house style (card `toolkit/cdxml_toolkit/publication/house_styles/beilstein_joc.json`, base preset `nature`), figure type `catalytic_cycle`. Tool: `cdx.py draw` with `layout: "catalytic-cycle"`.

## What is reproduced

The Pd(II) cycle of the paper: `PdX2` (7, X = NO3) binds 1a to give 8, C-H palladation with loss of HNO3 gives the palladacycle 9, and nitration with HNO3 releases 2a and regenerates 7. The Pd2(dba)3 activation arrow at the top, the Ag salts, the external substrate and product structures (1a, 2a) and the external HNO3 are not drawn; see Tool gaps.

Structures (SMILES in `brief.json`; read from the figure by eye, not OCSR; all parse in RDKit):

| ID | Structure | Note |
| --- | --- | --- |
| 7 | `O=[N+]([O-])O[Pd]O[N+](=O)[O-]` | Pd(NO3)2 |
| 8 | `O=[N+]([O-])O[Pd](O[N+](=O)[O-])<-n1ccccc1N1c2ccccc2c2ccccc21` | 1a coordinated through pyridine N (dative) |
| 9 | `O=[N+]([O-])O[Pd]1<-n2ccccc2N2c3ccccc3c3cccc1c32` | palladacycle at carbazole C1, pyridine N dative, O-bound nitrate |
| 1a | `c1ccc2c(c1)c1ccccc1n2-c1ccccn1` | 9-(pyridin-2-yl)carbazole (in brief, not drawn) |
| 2a | `O=[N+]([O-])c1cccc2c3ccccc3n(-c3ccccn3)c12` | 1-nitro product (in brief, not drawn) |

Rendered result (`rendered.png`, 871 x 688 px, from `cdx.py draw brief.json --render`, see Replay): a three-node loop 7 -> 8 -> 9 -> 7 with black straight arrows, bold labels 7, 8, 9, light blue ring fills on the carbazole and pyridine of 8 and 9, Kekule rings, Arial-like labels.

Matched rows: 7 of 18 after audit (see table and Audit below). The replicator claimed 9.

## Convention table

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| catalytic_cycle.cycle_shape: circle | round loop through 7, 8, 9 and 2a | three nodes on a triangle, straight chords | no |
| catalytic_cycle.cycle_arrow_color: #000000 | black cycle arrows | black (pixels are pure #000000) | yes |
| catalytic_cycle.catalyst_color: #8B0542 | maroon Pd centre arrows | no centre graphic | no |
| catalytic_cycle.center_label: true | shaded sphere labelled Pd at centre | not drawn (tool does not place a centre label) | no |
| catalytic_cycle.step_names: false | no step names | none | yes |
| catalytic_cycle.intermediate_label_style: bold_number | bold 7, 8, 9 | bold 7, 8, 9 (from compound_label_face; the tool does not apply intermediate_label_style, see Audit) | yes |
| catalytic_cycle.curved_arrow_color: null | black curved arrows | straight chord arrows | no |
| catalytic_cycle.highlight_fill: #BEDAFF | blue rings on carbazole and pyridine | same blue on the rings of 8 and 9 (ring_fills); 1a and 2a not drawn | partial, counted as no |
| signature: black curved arrows on a circle | yes | straight arrows | no |
| signature: substrates enter and HNO3 leaves on short tangent arrows | 1a enters, HNO3 leaves from 8, HNO3 enters at 9 | 1a, 2a and HNO3 not drawn | no |
| signature: shaded sphere Pd with two maroon circular arrows | yes | no | no |
| signature: bold Arabic numbers under each intermediate, no step names | yes | yes | duplicate of the two rows above, not counted |
| top-level: compound_label_face bold | bold labels | bold labels | yes |
| top-level: compound_label_color #000000 | black | black | yes |
| top-level: label_font Arial | Arial-like sans serif | Arial-like sans serif (the PNG cannot confirm Arial, see Audit) | no (not verified) |
| top-level: aromatic_rings kekule | Kekule rings | Kekule rings (renderer default; the tool does not apply the card value) | yes |
| top-level: arrow_style plain | plain arrows, filled heads | plain arrows, filled heads (renderer default; the tool acts only on bold) | yes |
| top-level: reagent_text_color #000000 | NO2, NO3 and HNO3 text in red | black | no |

Counts: matched 7 after audit (the replicator claimed 9; see Audit).

## Differences from the paper

- The cycle is a triangle of three straight chord arrows, not a circle with curved arrows. The tool lays the cycle out on a polygon and does not curve the arrows.
- The external species are missing: 1a enters at 7 -> 8, HNO3 leaves at 8 and re-enters at 9, 2a leaves at 9. The draw report records them as missing from the saved file (readback `mismatch`, `checks_passed` false). The rendered figure shows only 7, 8 and 9.
- The centre Pd sphere with maroon circular arrows is not drawn.
- The Pd2(dba)3 + 2 AgNO3 activation arrow from the top is not drawn.
- Element colours in the text (red NO2, NO3, HNO3) are not drawn; all text is black.
- The 8 structure is crowded: the pyridine dative bond and the two nitrate ligands sit on top of the carbazole N in the rendered output. The same overlap appeared with three different SMILES orders, so it comes from the tool's 2D coordinates for dative metal complexes, not from the SMILES.
- Step 9 + HNO3 -> 2a + 7 is kept as drawn in the paper. The atom balance check flags it (nitration needs a second HNO3 and gives H2O), so the figure is a simplified reagent scheme, not a balanced equation.

## Tool gaps

- `catalytic-cycle` layout draws only the cycle intermediates. Substrates, products and by-products that enter or leave the loop (1a, 2a, HNO3 here) are dropped, so readback reports them missing even though the steps are balanced in the brief. Entering and leaving structures need radial in/out arrows.
- Cycle arrows are straight chords. There is no curved-arrow option for `layout: "catalytic-cycle"` (the card's curved arrows and `curved_arrow_color` cannot be applied; only `cycle_arrow_color` is applied).
- No centre label or centre graphic (shaded sphere with circular arrows), so `center_label` and `catalyst_color` cannot be expressed in the brief.
- Cycle shape is a regular polygon with one vertex per step; `cycle_shape: circle` and the cycle radius cannot be set in the brief.
- Per-atom or per-group text colour (red NO2, NO3, HNO3) is not expressible; `reagent_text_color` is not applied to structures and the brief has no per-atom colour.
- Pre-catalyst activation (Pd2(dba)3 + 2 AgNO3 -> 7, with Ag by-product) cannot be entered as an arrow into the cycle.
- Dative metal coordination with two covalent nitrate ligands gives overlapping atoms in 8 (2D layout, no way to set coordinates from the brief).
- `highlight_fill` for `catalytic_cycle` is guidance only (listed under `skipped`); ring fills must be given per species with `ring_fills`.
- Operational: the first draw_figure attempt for a brief timed out at 300 s (the tool's limit, likely ChemDraw contention); a retry with the same brief succeeded.

## Replay

```
python skill/chemdraw/scripts/cdx.py py skill/chemdraw/assets/house-styles/beilstein_joc/replica/beilstein_joc-03/replay.py NEW_DIR
python skill/chemdraw/scripts/cdx.py render NEW_DIR/figure.cdxml
```

`replay.py` runs `draw_figure` on `brief.json` offline and writes `figure.cdxml` and `validation.json`. Not executed for this case; the rendered result above came from `cdx.py draw brief.json <out> --render`.


## Audit

Second pass against `reference.png`, `rendered.png`, `brief.json`, the card and the toolkit code (`figure_house.py`, `figure_draw.py`, `house_styles.py`, `style_presets.py`). Result: 7 of 18 rows match, not 9.

Changes to the table:

- The signature row for bold numbers repeats the `intermediate_label_style` row and is not counted again.
- `label_font`: the PNG cannot tell Arial from Helvetica. The face comes from the `nature` base preset (label Arial), not from the card's `label_font`, which no code path applies. Not counted.
- For `catalytic_cycle`, the tool applies only `cycle_arrow_color` (`apply_figure_type_conventions`). `intermediate_label_style`, `step_names`, `cycle_shape`, `center_label`, `catalyst_color`, `curved_arrow_color` and `highlight_fill` are reported as skipped guidance. The bold numbers come from `compound_label_face`. The absence of step names is trivial because nothing is drawn.
- `arrow_style` plain and `aromatic_rings` kekule have no code path (only bold arrows and circle rings are acted on). They match the reference only because the renderer default does.

Checked and holding: cycle arrows and bonds are pure #000000 in `rendered.png`; the ring fill is #BEDAFF in the reference and #BED9FF (rounding) in the rendered image, about 32,000 px each; labels 7, 8 and 9 are bold and black.

Errors or unsupported statements in this file:

- The count of 9 included one duplicate row and one unverified row.
- Line 21 gave the render source as `draw_figure`; the Replay section gives `cdx.py draw --render`. The Rendered line now uses the second, which is the source stated in Replay. Confirm which one produced the image.
- The readback result (`mismatch`, `checks_passed` false) and the 300 s timeout are not in this folder (no `validation.json`). They are unverified here.
- Proportions: the drawn ratios come from the `nature` preset (LineWidth 0.6 and BoldWidth 1.56 over BondLength 10.8 pt, so 0.056 and 0.144). The card's measured ratios are 0.068 and 0.2. Not matched.
- The card's signature says figures are about 700 to 800 px wide; `rendered.png` is 871 px wide.
- The card's `reagent_text_color` is #000000, but its own crop 02 and this reference use red for NO2, NO3 and HNO3 (about 1,740 red pixels in the reference, none in the replica). The card value is wrong for this figure.

Differences and tool gaps the replicator missed:

- The reference scaffold bonds and N atoms are dark blue (about 5,400 px near RGB 0, 65, 129; the card records blue bonds #255A90 in crop 02). The replica is all black. The brief has no per-bond or outline colour; `ring_fills` set the fill only.
- The reference draws the palladium species as text (Pd with superscript II, X = NO3) and the nitrates as NO3 text. The replica draws explicit Pd-O-N(+)O(-) structures with no superscript. `abbreviate_groups` comes from the card (OMe, tBu, Ph, CO2Me), so the brief cannot add NO3 or NO2.
- `draw_figure` records `reagent_text_color=#000000` as applied even though it paints nothing, so the draw report overstates what was applied.
