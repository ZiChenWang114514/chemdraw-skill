# Cell Press Chem house style: Figure 3 (top) scheme, crop 03

Source: K. Smith et al., "Photocatalysis as a mechanistic probe for the Staudinger beta-lactam synthesis", *Chem Catalysis* **2025**. DOI: [10.1016/j.checat.2025.101493](https://doi.org/10.1016/j.checat.2025.101493). Figure 3, top scheme. Licence: CC BY 4.0 (from the house-style card). The crop comes from the PMC author manuscript (NIHMS figure), so the artwork is the authors'.

Figure type: `reaction_scheme` (card also lists this crop under `substrate_scope`).

Drawing style: the `cell_press_chem` house style (base preset `wiley`, bond length 17.0 pt in the report), compound labels bold black, reagent text black.

## What is reproduced

The whole top scheme: the substrate class 1b-1j (N-benzyl enaminone amide with a varied group) under Ir(dFppy)3 (1 mol%), EtOAc (0.1 M), blue LED (440 nm), r.t., 16 h, giving the spiro beta-lactam 2b-2j and the hydroxy lactam 7b-7j. The varied group is drawn as a methyl (SMILES below) with a teal circle (`#529DBD`, `atom_halos`) on the methyl carbon. No yield is drawn because the crop shows none.

| Species | SMILES in brief.json (R = Me as stand-in for the teal dot) | Note |
| --- | --- | --- |
| 1b-1j | `O=C1CCCC=C1N(Cc1ccccc1)C(=O)CC` | RDKit formula C16H19NO2 |
| 2b-2j | `O=C1CCCCC12C(C)C(=O)N2Cc1ccccc1` | same formula; stereo not encoded |
| 7b-7j | `OC12CCCC=C1N(Cc1ccccc1)C(=O)C2C` | same formula; stereo not encoded |

Structures were read from the crop by hand (OCSR was not run); RDKit confirms the three SMILES parse and share one formula. The offline replay (`replay.py`) reproduces the drawing and its report (see Audit).

## Comparison with the paper (audited)

Each row was checked against the two images and, where possible, by pixel measurement (`reference.png` is 900 by 132 px, `rendered.png` is 1200 by 269 px). The rows added in the audit are at the bottom of the table.

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| compound labels bold, black | bold `1b-1j`, `2b-2j`, `7b-7j`, black | bold, black (font face 1, colour 0 in the CDXML) | yes |
| reagent text black | black | black | yes |
| catalyst and solvent above the arrow, light and time below | `Ir(dFppy)3 (1 mol%)` / `EtOAc (0.1 M)` above; `Blue LED (440 nm)` / `r.t., 16 h` below | same four lines in the same places; the wording differs (see the `r.t.` row) | yes (placement only) |
| plus sign between the two products | `+` between 2b-2j and 7b-7j | `+` drawn between them on one row | yes |
| thin arrow with small filled head | shaft about 0.09 of a bond length thick (1.4 px at 900 px), about 7.5 bond lengths long | shaft 0.6 pt (about 0.035 of a bond length), 6.9 bond lengths long; head size not measured | no (weight and length differ) |
| varied position marked by a teal dot (`#529DBD`) | teal dot at the chain end of 1b (lower right), on C3 of 2 (upper right) and on C3 of 7 (upper left) | colour exact; the dot on 2 is in the same place; the dots on 1b and 7 are mirrored or rotated; dot diameter about 0.6 of a bond length (paper about 0.57); the radius is fixed in points, not scaled with the preset | no (positions of 1b and 7 differ) |
| sans-serif label text | Arial-like | Arial (font 3 in the CDXML) | yes |
| range labels bold, e.g. `1b-1j` | bold | bold | yes |
| substrate scope as a grid (card `scope_layout: grid`) | one scheme with a range label, not a grid | one scheme | no |
| yield and selectivity written with each label (card `substrate_scope` signature) | none in this crop | none | not applicable to this crop (not counted) |
| abbreviate `Ph` (card `abbreviate_groups`) | benzyl drawn with a full phenyl ring | `Ph` abbreviation on all three N-benzyl groups | no |
| `r.t.` as written | `r.t., 16 h` | `rt, 16 h` (the renderer rewrites the text) | no |
| hashed and bold wedges for relative configuration on 2 and 7 | hashed and bold bonds at the ring fusion and C3 | no stereo drawn | no |
| full-width black rule under the scheme | present, about one pixel thick, full width | absent | no |
| proportions (added in audit) | 900 by 132 px, about 6.8 to 1; a bond is about 1.8 percent of the width | 1200 by 269 px, about 4.5 to 1; a bond is about 3.3 percent of the width (estimated from the CDXML) | no |
| bond line weight (added in audit) | about 0.08 of a bond length (card measurement) | 0.75 pt, about 0.044 of a bond length (wiley preset value) | no |
| 2D orientation of 1b, 2 and 7 (added in audit) | 1b: chain and amide to the right of the enaminone; 2: ketone at the top next to the spiro carbon, N-benzyl hangs down to the right; 7: teal dot up and to the left of C3 | 1b mirrored; 2: ketone at the bottom, N-benzyl to the left; 7: teal dot down and to the right of C3 | no |

Audited count: 6 of 13 applicable rows match (the yield row does not apply to this crop). The earlier "8 of 11" cannot be reproduced from this table, which has 14 rows; it counted the arrow and the teal dot as matches. The proportion, line-weight and orientation rows were not in the earlier table and do not match either. The label size is close to the paper (cap height about 0.5 of a bond length against about 0.46 in the paper), within the error of a pixel estimate, so it is not counted.

## Differences from the paper

- Varied group: the teal dot is a methyl with a teal circle, so the substrate is drawn as a propanamide. This is a stand-in, not a variable group.
- Stereo: 2 and 7 are drawn without the hashed and bold bonds. The relative configuration was not read reliably from the 900 px crop, so it was not encoded. SMILES stereo tags would draw wedge and hash bonds (see tool gaps), so the missing stereo is a choice in the brief, not a limit of the tools.
- Benzyl groups: the paper draws the phenyl ring; the replica uses `Ph`.
- Ring layout: the paper draws the cyclohexanone of 2 with the ketone at the top, next to the spiro carbon; the replica puts the ketone at the bottom. The 1b chain and amide are mirrored, and the N-benzyl groups of 2 and 7 point in different directions. The cyclohexene of 7 is also drawn differently.
- Arrow and bonds: the replica arrow shaft and bond lines are thinner relative to the bond length than the paper's (see the table), and the arrow is about 8 percent shorter in bond lengths.
- Proportions: the paper's scheme is a flatter strip (about 6.8 to 1); the replica is taller (about 4.5 to 1) because its bonds and text are large relative to the scheme width.
- Conditions: `r.t.` becomes `rt`.
- Black rule under the scheme is not drawn.
- No yield or selectivity is shown, as in the crop.

## Tool gaps (audited)

- `abbreviate_groups` from the card contracts every terminal phenyl to `Ph` (`figure_house.py`, `ABBREVIATIONS` in `publication/house_styles.py`). The brief has no per-figure switch, and `style` takes either one house style or one preset, so the phenyl ring cannot be kept under the house style.
- Conditions text is tidied: `normalize_condition_text` in `text_formatting.py` runs on every arrow line in `render/renderer.py`, so `r.t.` becomes `rt` with no option to keep the wording.
- A single step with two isomeric products is reported as unbalanced ("the reactants lack C16H19NO2") because `figure_draw._check_balance` adds the product formulas together. The drawing is still correct: the replay's readback matches all three structures.
- No placeholder for a variable group (R, or a dot). An `atom_halos` circle on a real atom approximates the teal dot. The halo radius is in points (default 8.0, `figure_draw.py`) and is not scaled with the preset bond length.
- Stereo (corrected): the earlier claim that the brief cannot carry wedge or hash layout is wrong. SMILES stereo tags are turned into wedge and hash bonds. A test in a temporary folder with @ and @@ tags on C3 and the ring fusion gave `WedgeBegin` and `WedgedHashBegin` bonds in the CDXML. The 2D coordinates come from RDKit (`Compute2DCoords` and `WedgeMolBonds` in `cdxml_builder.py`), not from ChemDraw. The real gap is narrower: the brief cannot choose which bond is wedged or hashed, cannot set the 2D layout, and cannot make the wedge placement match the paper.
- No option to draw a full-width rule under a scheme (`BRIEF_KEYS` in `figure_draw.py` has no such key).
- Missed: the card's measured ratios (`line_width_over_bond_length` 0.08, `bold_width_over_bond_length` 0.17, `arrow_length_over_bond_length` 7.5) are stored in `cell_press_chem.json`, but no code reads them. Line weight and arrow length come from the wiley preset and the layout.
- Missed: no bond length, spacing or aspect setting in the brief. The bond length comes from the preset and the width from `max_width`, so the ratio of bond to scheme width cannot be set. `gap_scale` exists inside `_relayout` but is not exposed.
- Missed: no 2D orientation or mirror control per species. This is why 1b, 2 and 7 differ from the paper.
- Missed: no arrow length or arrow weight setting for one figure.

## Replay

```
python skill/chemdraw/scripts/cdx.py py skill/chemdraw/assets/house-styles/cell_press_chem/replica/cell_press_chem-03/replay.py NEW_DIR
python skill/chemdraw/scripts/cdx.py render NEW_DIR/figure.cdxml
```

`replay.py` runs `draw_figure` on `brief.json` offline and writes `figure.cdxml` and `validation.json`. `reference.png` is the crop; `rendered.png` is the desktop ChemDraw rendering from this brief (downscaled to 1200 px wide). The audit re-ran the replay offline and got the same balance warning, the same three contracted groups and the same readback. ChemDraw was not run in the audit, so `rendered.png` was not compared with a new render.

## Audit

Audited 2026-11-07 by a second agent. The table, the counts, the differences and the tool gaps above were corrected. No other file in this folder was changed.

Overclaims found in the earlier version:

1. "8 of 11 match" cannot be reproduced. The table had 14 rows, and the count included the arrow and the teal dot as matches. Corrected: 6 of 13 applicable rows match.
2. "Thin arrow with small filled head" was marked as matching. The shaft is about 0.035 of a bond length against about 0.09 in the paper, and the arrow is 6.9 against 7.5 bond lengths.
3. "Varied position ... approximate" was counted as a match. The dots on 1b and 7 are mirrored or rotated relative to the paper.
4. The stereo tool gap was stated too strongly. SMILES stereo tags do produce wedge and hash bonds (tested); the gap is control over which bonds are wedged and over the 2D layout. The layout comes from RDKit, not ChemDraw.
5. The paper's ketone position on 2 was described as lower left. In the crop it is at the top, next to the spiro carbon.
6. Not listed before: proportions (about 4.5 to 1 against about 6.8 to 1), bond line weight (about 0.044 against about 0.08 of a bond length), 2D orientation of 1b, 2 and 7, and the direction of the N-benzyl groups. All differ from the paper.

Measurements behind the audit: reference arrow shaft thickness 1.44 px (median over 80 columns); reference rule 0.88 px, full width; teal colour exactly #529DBD in both images; reference bond length about 16 px, from the card's measured 26.5 px on the 1500 px original scaled by 0.6, and consistent with the ring bonds in a 3x enlarged view; replica bond 17 pt and arrow 117 pt from the replay CDXML.
