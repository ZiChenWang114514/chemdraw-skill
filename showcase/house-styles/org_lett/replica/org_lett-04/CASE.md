# Org. Lett. concept panel: Pictet-Spengler routes to CF3-tetrahydro-beta-carbolines (crop org_lett-04)

Source: Akiyama et al., *Org. Lett.* **2025**, *27*, 6204, "Chiral phosphoric acid-catalyzed enantioselective Pictet-Spengler reaction for CF3-substituted tetrahydro-beta-carbolines". DOI: [10.1021/acs.orglett.5c01864](https://doi.org/10.1021/acs.orglett.5c01864). Licence: CC BY 4.0 (from the house-style card). Reference crop: Scheme 1, `evidence/org_lett-04.png`, copied here as `reference.png`.

Figure type: `concept_panel` (stacked rows of earlier approaches (a), (b) and the present work (c)).

Drawing style: the `org_lett` house style (base preset ACS Document 1996), as set in `brief.json`.

## What is reproduced

- Rendered (`rendered.png`, `draw_figure`, org_lett preset; the card's measured values are not applied, see Audit): the present-work row (c) only. (R)-CPA III (5 mol%), MS4A (100 wt%), DCM (0.2 M), 40 °C, 22–120 h; tryptamine plus 4,4,4-trifluoro-1-(triisopropylsilyl)but-1-yn-3-one gives the 1-CF3 tetrahydro-beta-carboline bearing the TIPS-alkyne; 92%, 91% ee under the product. The stereocentre is drawn with one stereo bond.
- Layout check (`panel_stacked.png`, input `panel_stacked.yaml`, `render_scheme` with `layout: stacked-rows` sections, no house style): all three rows, (a) and (b) included. It reproduces the row order, the reagent/solvent split and the stacked layout. It does not apply the org_lett conventions.
- Not reproduced: the bold serif scheme title above the crop, the panel letters (a), (b), (c), and the bold "Present work:" label.

Structures (read from the crop; no OCSR engine was run). SMILES were parsed by RDKit; CIP descriptors were assigned by RDKit from the wedge and hash bonds as drawn in the crop:

- (a) substrate `FC(F)(F)C1=NCCc2c1[nH]c1ccccc21`, indole `c1ccc2[nH]ccc2c1`; product `FC(F)(F)[C@@]1(c2c[nH]c3ccccc23)NCCc2c1[nH]c1ccccc21` (S as drawn).
- (b) tryptamine `NCCc1c[nH]c2ccccc12` plus ethyl trifluoropyruvate `CCOC(=O)C(=O)C(F)(F)F`; product `CCOC(=O)[C@]1(C(F)(F)F)NCCc2c1[nH]c1ccccc21` (R as drawn).
- (c) tryptamine plus `O=C(C(F)(F)F)C#C[Si](C(C)C)(C(C)C)C(C)C`; product `CC(C)[Si](C#C[C@@]1(C(F)(F)F)NCCc2c1[nH]c1ccccc21)(C(C)C)C(C)C` (R as drawn). `brief.json` stores the same stereocentre in another atom order.

The product descriptors come from the wedge reading of the crop; the paper text was not consulted for them.

## Replay

```
python skill/chemdraw/scripts/cdx.py py skill/chemdraw/assets/house-styles/org_lett/replica/org_lett-04/replay.py NEW_DIR
python skill/chemdraw/scripts/cdx.py render NEW_DIR/figure.cdxml
```

`replay.py` runs `draw_figure` on `brief.json` (the present-work row) offline and writes `figure.cdxml` and `validation.json`. Those two outputs are not kept in this folder, so the CDXML values quoted in the table cannot be re-checked here. The three-row panel is not a `draw_figure` brief: `draw_figure` refuses independent reactions (see Tool gaps). The layout check uses `panel_stacked.yaml` through `cdx.py call render_scheme --args` and then `cdx.py render`.

## Attempts

1. Three-row `draw_figure` brief (rows a, b, c as separate steps): refused with "The steps are not a linear route, a convergent route (arms that merge) or a set of reactions from one starting material, so they cannot be laid out."
2. Row (c) alone, house style: rendered. The first SMILES for the product had the opposite configuration to the crop (RDKit gave S). It was found on re-check against the wedge reading and corrected. This render is not kept.
3. Row (c) alone, corrected stereo: rendered (`rendered.png`, downscaled from the native PNG to 1200 px wide).
4. Three rows via `render_scheme` stacked-rows sections, corrected stereo: rendered (`panel_stacked.png`, downscaled to 1200 px wide).

## Convention table

Rows cover the `concept_panel` conventions and signature features that apply to crop 04, plus the top-level conventions visible in the crop. Crop 04 has no product numbers, so `compound_label_face` (bold) cannot be tested here and is left out. "Replica" describes the rendered output of the row (c) render, or of the layout check where stated.

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| concept_panel panel_label_style: (a), (b), (c) in parentheses at the right end of each row | (a), (b), (c) at the right end | no panel letters in either tool | no |
| concept_panel comparison_layout stacked_rows, present work last | three stacked rows, present work last | `draw_figure` refuses multi-row briefs; `render_scheme` stacks the rows but applies no house style (Attempts 1 and 4) | no |
| concept_panel this_work_color null (black) | all black | all black (default colour; no code path applies the card's concept_panel section, see Audit) | yes |
| concept_panel background_fill null | no fill | no fill (default) | yes |
| concept_panel highlight_fill null | no fill | no fill (default) | yes |
| concept_panel variation_color null | no variation | no variation (default) | yes |
| concept_panel signature: bold "Present work:" above the row | bold sans-serif label above row (c) | not drawn (no bold text-run option) | no |
| yield_placement under the product | "92%, 91% ee" directly under the structure | under the product in the `draw_figure` render (the product has no label, so the line sits under the structure) | yes |
| yield_format and yield_separator | "81%, 86% ee", "92%, 91% ee", "92%, 18% ee" | same text, typed by hand; no tool applies yield_format to this two-value form (the regex matches one bare number only) | yes (text only) |
| conditions_split reagents above, solvent and temperature below | catalyst and MS4A above; solvent and temperature below | same split, but the rendered "22–120 h" shows as "22⁻₁₂₀ h" (see Audit) | no |
| substrate_layout inline_plus, plus sign between substrates | A + B on one line | inline, but the plus sign touches the TIPS isopropyl "Me" label in the render (see Audit) | no |
| abbreviate_groups CF3 | CF3 label | CF3 label in the row (c) render (not in the stacked layout) | yes |
| abbreviate TIPS (drawn in the crop; TIPS and OEt are not on the card list) | TIPS | full Si(iPr)3 with Me labels | no |
| aromatic_rings kekule | Kekule rings | Kekule rings (checked in the render) | yes |
| arrow_style plain | plain arrow | plain arrow | yes |
| show_plus_sign | plus signs between substrates | plus signs | yes |
| new_bond_color null, black | black | black | yes |
| reagent_text_color #000000 | black | black | yes |
| bond length over cap height 2.2 (top-level measured) | 34 : 15 px = 2.3 | LabelSize 10 pt against BondLength 14.4 pt, about 2.0; the card's 9 pt label size is not applied | no |
| line width over bond length 0.065 | 2.5 / 34 px = 0.074 (about 1.06 pt at bond 14.4 pt; the card's 0.065 gives 0.94 pt) | LineWidth 0.60 pt | no |
| bold width over bond length 0.2 | 7 / 34 px = 0.21 (about 3.0 pt at bond 14.4 pt) | BoldWidth 2 pt | no |
| arrow length over bond length (top-level 7.6) | 190 px / 34 px = 5.6 | 104 pt / 14.4 pt = 7.2 (matches the card value, not this crop) | no |

Matched 12 of 22 after audit (the replicator claimed 14); see Audit.

## Differences from the paper

- Only row (c) is drawn with house-style conventions. Rows (a) and (b) appear only in the `render_scheme` layout check, which does not apply the house style.
- The stacked panel has no panel letters, no bold "Present work:" label and no scheme title.
- TIPS is drawn as Si(iPr)3 with explicit methyl groups, not as the TIPS label.
- Stereo: the paper draws a bold wedge to CF3 and a hash to the alkyne in row (c). The replica draws a single stereo bond, a bold wedge to the alkyne (the tool and ChemDraw pick the bond). In the layout check, row (a) shows a wedge to CF3 where the paper shows a wedge to the indole, and row (b) shows a wedge to CF3 where the paper shows a wedge to the ester (the paper hashes CF3 in row (b)).
- Orientation: the replica draws the carboline on the right and the TIPS-alkyne on the left of the stereocentre; the paper draws the opposite way round.
- Line weights and label size follow the ACS 1996 preset, not the card's measurements (see the table).
- The native render shows the condition "22⁻₁₂₀ h" for "22–120 h". The CDXML text is "22–120 h", so the mangling happens at ChemDraw rendering.
- Yield and ee sit under the structure in the `draw_figure` render, as in the paper. In the `render_scheme` layout check they are printed under the arrow instead.
- The condensation is flagged as unbalanced because water is not drawn (the paper does not draw it). No H2O is added.

## Tool gaps

- `draw_figure` refuses independent reactions in one brief (the layout error quoted in Attempts). There is no stacked-rows layout for comparison panels.
- `render_scheme` stacked-rows sections take no `style` argument, so no house conventions reach the stacked panel. In the stacked render, CF3 and CO2Et are not abbreviated, yield text goes under the arrow rather than under the product, and the CF3 fluorine label collides with the indole HN in row (c).
- No panel letters at the right end of a row, and no bold text run above a row.
- `abbreviate_groups` is a fixed list with no custom labels; TIPS (and OEt) cannot be shown as labels.
- The card's `measured` block (label size 9 pt, line width, bold width, arrow length) is stored but no code reads it. The proportions come only from the acs1996 preset, so this is a missing feature, not a mapping slip.
- Stereo bond choice: the tool shows one stereo bond, chosen by ChemDraw; there is no way to request a wedge on one bond and a hash on another.
- No orientation control for the product, so the layout can be mirrored relative to the paper.
- The plus sign can touch a branched substituent (the TIPS methyl); lint reports no overlap.
- Lint did not flag the mangled en-dash condition text.
- Water is not drawn for condensation steps, so each condensation gets a balance warning. There is no per-brief option to mark a by-product as omitted by convention.
- Bold or italic runs inside reagent and condition text: the paper bolds the catalyst numerals ("CPA I", "CPA III") and italicises the stereodescriptor (R). Above-arrow and below-arrow text take no run formatting, so the render is plain.
- A thin black full-width rule between sub-panels (card `concept_panel` signature, crop 03).
- A bold italic caption under the arrow (card `concept_panel` signature, crop 03, "this work").
- Card `concept_panel` conventions have no code path: `apply_figure_type_conventions` is called only for the `mechanism` and `catalytic_cycle` figure types. Panel letters, stacked rows and label style cannot come from the card.
- `yield_format` recognises only one bare number (`_YIELD_VALUE` in `figure_house.py`), so the two-value "92%, 91% ee" form passes through untouched. The card's `selectivity_format` is read by no drawing code.
- Rendering: the shared ChemDraw queue held renders for more than 20 minutes on this run.

## Audit

Checked by hand against `reference.png`, `rendered.png` and `panel_stacked.png` (enlarged crops), against `org_lett.json`, and against `toolkit/cdxml_toolkit/mcp_runtime/figure_house.py`, `figure_draw.py` and `publication/house_styles.py`.

Overclaims corrected:
- The header said "house style applied". Only the acs1996 preset is applied; the card's `measured` block is never read.
- conditions_split was marked matched. The split matches, but the render shows "22⁻₁₂₀ h" for "22–120 h". Now no.
- substrate_layout was marked matched. The plus sign touches the upper-left isopropyl "Me" label in the render. Now no.
- The concept_panel null rows match the paper in output. No code applies the concept_panel card section, so these are default matches, not convention matches.
- yield_format matches in text only: the text is typed by hand and no tool applies the template to this form.
- Differences said row (b) keeps the wedge to the ester. It does not: the stacked render puts the bold wedge on CF3, and the paper puts it on the ester.
- Line width arithmetic: 2.5 / 34 × 14.4 pt = 1.06 pt, not 0.94 pt (0.94 pt is the card's 0.065 value). Arrow: 190 / 34 = 5.6, not 5.5 (the card's crop 04 arrow measurement is 190 px).
- The replay sentence implied that figure.cdxml and validation.json were kept. They are not in this folder, so the LabelSize 10, LineWidth 0.60, BoldWidth 2, 104 pt arrow, balance warning and lint results cannot be checked here.

Checked and correct:
- Stereo configuration. Estimating the wedge and hash geometry from the crops, the paper's (a), (b) and (c) products are S, R and R, matching RDKit's labels for the stated SMILES. The render of row (c) and the stacked rows (a) to (c) give the same descriptors. The replica differs in wedge placement, not in configuration. These are pixel estimates, not an OCSR result.
- CF3 abbreviated in the row (c) render and not in the stacked panel; TIPS drawn as Si(iPr)3; carboline mirrored; the F of CF3 sits on the indole HN in stacked row (c); yields sit under the arrow in the stacked layout, whereas the paper puts them under the product in every row.
- Kekule rings, plain arrow, black colour, no fills and the reagent/solvent split are confirmed in the render.

Not tool gaps:
- `draw_figure` takes a `title` key (`figure_draw.py`). The replica brief omits it, so the missing bold serif title is a choice. Whether the title renders in the paper's face is untested.
- `draw_figure` takes a `layout` key, but only `catalytic-cycle` overrides the route layout, so the stacked-rows gap stands.
