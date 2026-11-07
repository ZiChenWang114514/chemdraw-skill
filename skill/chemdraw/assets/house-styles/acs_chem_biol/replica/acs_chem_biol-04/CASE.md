# Sun et al. 2026, Figure 1D: N6-substituted adenosines (structure panel replica)

Source: Sun et al., *ACS Chem. Biol.* 2026, Figure 1D, DOI [10.1021/acschembio.5c00656](https://doi.org/10.1021/acschembio.5c00656). Licence: CC BY 4.0 (from the house-style card); the reference crop is reproduced under that licence.

Figure type: `structure_panel` (with the `biomolecule` convention for the nucleoside). Style: `acs_chem_biol` (base preset acs1996).

## What is reproduced

The adenosine core with four N6 substituents, as one scope-kind panel with the name under each structure: m⁶A (N6-methyl), CPA (N6-cyclopentyl), Bz⁶A (N6-benzyl) and i⁶A (N6-isopentenyl). The ribose is a flat furanose with no stereo marks, as in the crop.

Not reproduced: the grey R-group key box, the blue colour of the varied group, and the other entries of the key. The crop is 275 x 153 px, so the names of the remaining entries were not legible and were not guessed.

| ID | SMILES in brief.json | Name in panel |
| --- | --- | --- |
| m6A | `CNc1ncnc2c1ncn2C1OC(CO)C(O)C1O` | m⁶A |
| CPA | `C1CCC(C1)Nc1ncnc2c1ncn2C1OC(CO)C(O)C1O` | CPA |
| Bz6A | `C(Nc1ncnc2c1ncn2C1OC(CO)C(O)C1O)c1ccccc1` | Bz⁶A |
| i6A | `CC(C)=CCNc1ncnc2c1ncn2C1OC(CO)C(O)C1O` | i⁶A |

The SMILES were checked with RDKit (formulas C11H15N5O4, C15H21N5O4, C17H19N5O4 and C15H21N5O4). They carry no stereo because the crop shows none.

## Replay

```
python skill/chemdraw/scripts/cdx.py py skill/chemdraw/assets/house-styles/acs_chem_biol/replica/acs_chem_biol-04/replay.py NEW_DIR
python skill/chemdraw/scripts/cdx.py render NEW_DIR/panel/page-001.cdxml
```

`replay.py` runs `draw_figure` on `brief.json` offline and writes `NEW_DIR/panel/` (the scope folder) and `validation.json`. `rendered.png` is the desktop ChemDraw render of the one-page panel, downscaled to 1100 px wide.

## Convention check

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| structure_panel: same core repeated in a grid, short name under each | 1D crop: one core with an R-group key (the grid and centred names are Figure 1B) | four full structures in one row, names under each (left-anchored, not centred) | no |
| structure_panel: only the varied group coloured blue (`variation_color` #4C6BFD) | blue R on a black core | all black | no |
| structure_panel: R-group key in a thin grey rectangle with blue fragments and names | grey-outlined box with R = and names | not drawn (no frame or key object) | no |
| biomolecule: nucleoside modifications in blue #4C6BFD on a black core | blue modification | black | no |
| biomolecule: ribose as a flat furanose (`sugar_projection` null) | flat furanose, OH groups as labels | flat furanose, OH labels | yes |
| top-level: compound label colour #000000 | black names | black names | yes |
| top-level: label font Arial or Helvetica | sans-serif names | Arial claimed; no font readout in the case folder | no |
| top-level: aromatic rings kekule | alternating double bonds in the purine | alternating double bonds in the purine and the benzyl ring | yes |
| top-level: no yield or conditions in this figure type | none | none | n/a |

Matched 5 of 8 claimed conventions. After audit: 3 of 8 (see Audit).

## Differences from the paper

- Colour: the varied group and the nucleoside modification are black. The paper draws them in blue #4C6BFD. No tool colours one substituent in a scope or structure panel.
- Key: no grey-outlined R-group box, no "R =" prefix and no list of R groups with names. The paper shows the core once and lists the substituents in the key; the replica repeats the whole nucleoside for each entry.
- Entries: four names, not the full set in the crop.
- Names: in the 1D crop the names sit in the R-group key, not under the structures (centred names are a Figure 1B feature). Here the names are left-anchored, and the CPA name sits lower than the other three (manifest y 147 pt against 133 pt).
- Scale: base preset acs1996, bond length 14.4 pt, panel 260 x 90 mm (aspect about 2.9:1, against about 1.8:1 for the 275 x 153 px crop). The card's bond_length_over_cap_height is 2.0 (not null), but the replica's cap height was never measured, so the ratio is not checked.
- Superscript notation is Unicode (m⁶A) rather than ChemDraw subscript and superscript runs.

## Tool gaps

- No per-substituent colour in `kind: "scope"` or `draw_figure`. The card's `variation_color` (#4C6BFD) and the blue nucleoside convention cannot be applied, so the scope panel takes only the base preset.
- No frame, rectangle or key-list object, so the R-group key box cannot be drawn.
- An empty `title` falls back to "Substrate scope" (`toolkit/cdxml_toolkit/mcp_runtime/figure_scope.py` line 140, `brief.get("title") or "Substrate scope"`). A single blank space suppresses it; the blank title should be an explicit option.
- Scope labels are not placed on one baseline or centred under each structure; CPA sat lower in this run.
- `draw_figure` with `kind: "scope"` was slow or hung in this session: at 120 x 80 mm the first two `--render` attempts exceeded 300 s, a 120 x 80 mm run without render exceeded 150 s, and the same panel at 180 x 100 mm and then 260 x 90 mm wrote its files in about 4 s without render. A native render worker crashed once and succeeded on retry. Five ChemDraw.exe processes were running during the session.
- The default packing at 120 x 80 mm split four entries over three pages. Panel size needs to be chosen by hand.

## Audit

Checked against reference.png (the Figure 1D crop), rendered.png, brief.json, the card acs_chem_biol.json and the toolkit code. Each "yes" row was tested against the crop, not the paper figure named in the row.

Overclaims corrected above:
- Grid row: the paper column describes Figure 1B. The 1D crop has one core with an R-group key and no grid. The row's own text says the names are not centred, so it is not a match.
- Arial row: the case folder has no CDXML, font readout or manifest, and the glyphs cannot be confirmed as Arial at this resolution. Treated as not matched.
- Names and Scale bullets: the centred-name claim comes from 1B, not 1D. The card's bond_length_over_cap_height is 2.0, not null.
- "What is reproduced" describes the output as the 1D panel. The output is a different composition (four full molecules in a row against one core plus key), which the Differences key bullet states but the reproduction claim does not.
- The panel size of 260 x 90 mm is in brief.json but not in the case text. Aspect ratio differs from the crop.
- Line weight, bond proportions and label size against the crop: there are no measurements in the folder (the crop's px measurements are null in the card). Not matched by default.
- Tool timing claims (300 s runs, five ChemDraw.exe processes, the render worker crash): no logs are in the folder. Unverified.

Corrected matched count: 3 of 8. Flat furanose, black labels and kekule aromatic rings hold at this resolution. The kekule rows were checked in the render only: the purine shows inner double bonds, and the benzyl ring is assumed from the same render.

Tool gaps the replicator missed (verified in the toolkit):
- No `structure_panel` kind. draw_figure accepts only scheme, scope and mechanism (`toolkit/cdxml_toolkit/mcp_runtime/figure_draw.py` line 84), so the card's structure_panel conventions (variation_color, highlight_fill) have no drawer. The replicator's gap wording says "kind scope or draw_figure"; the colour gap is scope-specific, since scheme and mechanism take card colours and per-atom halos or ring fills.
- `scope_layout: grid_with_core` is in the schema (`toolkit/cdxml_toolkit/publication/house_styles.py` line 74, allowed for substrate_scope) but no code draws it. The scope drawer applies only the house style's base preset (figure_draw.py docstring). The core-once-plus-R-key layout of 1D cannot be produced.
- Scope labels are plain strings (`figure_scope.py` `_text`, written to table.csv). There is no superscript, subscript, italic or bold run, so m⁶A has to be Unicode. This is listed as a difference, not as a tool gap.
- The scope spec has no label alignment or baseline option (spec keys at `figure_scope.py` lines 136 to 146), so the baseline and centring gap has no workaround beyond the packing.
- The blank-title workaround is confirmed: a single space is truthy in `brief.get("title") or "Substrate scope"` (`figure_scope.py` line 140).
