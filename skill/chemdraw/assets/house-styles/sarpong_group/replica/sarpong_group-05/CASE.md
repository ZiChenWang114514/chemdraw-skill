# sarpong_group-05: substrate-scope panel, Figure 3 (scope of reaction), Sarpong et al., JACS 2023

Source: Sarpong et al., "Photo- and Metal-Mediated Deconstructive Approaches to Cyclic Aliphatic Amine Diversification", *J. Am. Chem. Soc.* **2023**, *145*, 11245-11257, DOI [10.1021/jacs.3c01318](https://doi.org/10.1021/jacs.3c01318). Licence: CC BY 4.0 (from the `sarpong_group` card). Reference crop: `reference.png` (copy of `evidence/sarpong_group-05.png`, 776 x 855 px).

Figure type: `substrate_scope` (card section). Style: `sarpong_group` (base preset `nature`).

## What is reproduced

The eight substrate-product pairs visible in the crop: 1a/3a (86%), 1b/3b (62%), 1c/3c (43%, 75% BRSM), an unlabelled 4-methyl piperidine pair, 1i/3i (72%), 1j/3j (67%), 1k/3k (52%) and an unlabelled 6,7-dimethoxy tetrahydroisoquinoline pair. Brief: `brief.json`, kind `scope`, title "Scope of reaction", 16 entries (substrate, then product, for each pair), yields on the products only. No conditions are drawn because none are visible in the crop.

Structures were read by hand from the crop and checked only as parseable SMILES in RDKit; they were not overlaid on the crop. Ring-opened products follow the drawn regiochemistry: C2-N cleavage with the former C2 as the aldehyde for 3a, 3b, 3c and 3k; for the 3-substituted pair (3i, 3j) the substituent sits on the carbon next to the NHPiv chain. The bottom row has no visible labels (cut off in the crop), so no labels are assigned to those two pairs.

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| scope_layout `grid` (substrate left, product right in each cell) | four rows of two pairs; substrate left, product right in each pair | entries flow across four columns in input order (substrate and product not kept together) | no |
| variation_color `#800567` on the new CHO | the new CHO is black in the crop; no magenta on any structure. The magenta in the crop is the title only | black | yes (matches the crop; the card's magenta is not in the crop) |
| yield_format `{value}%` and placement | label and yield on one line under the structure, for example `3a: 86%`, with `3c: 43%` and `(75% BRSM)` on the next line | same values and `{value}%` format, but label and yield on separate lines | no |
| conditions_position `scheme_on_top` | none visible in crop | none drawn | no (not visible, so not matched) |
| highlight_fill null | no filled highlight | no filled highlight | yes |
| each cell pairs substrate (left) with product (right) | paired | listed separately | no |
| bold label and yield under the product | bold labels; yield is plain, after a colon, on the label line | plain labels, label and yield on separate lines, dash under substrates | no |
| section title over violet `#C385DB` rule | bold italic title in magenta-plum (about `#7E0467`), violet `#C385DB` rules on both sides, dashed violet divider below | plain title, no rule, no divider | no |
| compound_label_face `bold` (top level) | bold | plain | no |
| compound_label_color `#000000` | black | black | yes |
| abbreviate_groups OMe, Boc, tBu | `Piv` and `MeO` text | skeletal pivaloyl and OMe bonds | no |
| aromatic_rings `kekule` | Kekule rings (inner double-bond lines) | Kekule rings (inner double-bond lines) | yes |
| structure orientation (added in audit) | N-acyl ring drawn with the N at the bottom and `Piv` directly below it; NH chains run up to the right | rings and chains drawn in other orientations; `Piv` on the lower left | no |
| dashed column divider (added in audit) | dashed violet vertical line between the left and right pair columns | none | no |
| footnote letters `a` on 3i and 3j (added in audit) | superscript `a` on the labels | not drawn | no |

Matched 4 of 12 claimed conventions after audit: highlight_fill, variation_color (matches the crop), compound_label_color and aromatic_rings. yield_format is not matched once placement is counted, and conditions_position is not matched because no conditions are visible. The three added rows are not counted in the 12. The house conventions are not applied to a scope panel (see Tool gaps).

## Replay

```
python skill/chemdraw/scripts/cdx.py py skill/chemdraw/assets/house-styles/sarpong_group/replica/sarpong_group-05/replay.py NEW_DIR
python skill/chemdraw/scripts/cdx.py render NEW_DIR/figure.cdxml/page-001.cdxml
```

`replay.py` runs `draw_figure` on `brief.json` offline. The scope output is a folder (`page-001.cdxml`, `page-002.cdxml`), so the `figure.cdxml` name is only a folder name. `rendered.png` is the desktop ChemDraw render of page 1 (15 entries), downscaled to 1200 px wide. Page 2 holds the last product (`p7`) alone because the page height was set to 240 mm. The draw with `--render` exceeded the 300 s tool limit, so the drawing was run without render and the page was rendered separately with `cdx.py render`. (The page-2 output and the timings are session reports; no output folder is in this case folder, so they were not re-checked.)

## Differences from the paper

- No pairing: the paper keeps each substrate with its product in a two-column block. The replica flows all 16 structures across four columns in input order, so a substrate and its product are often in different cells.
- Dashes: the substrates show a dash (no value) where the paper shows nothing under the structure.
- Labels: the two unlabelled pairs appear in the drawn panel with the internal ids `s3`, `p3` and `s7` in place of labels. The labels are cut off in the crop, so the correct labels are unknown.
- Labels are plain, not bold, and the yield is on its own line rather than after the label. The paper uses bold labels for compounds and writes the yield after a colon.
- N-pivaloyl is drawn as a skeleton; the paper writes `Piv`. Methoxy is drawn as skeletal bonds; the paper writes `MeO`.
- The new CHO is black, and so is every other atom in the crop. The earlier note that the paper colours it magenta was wrong: the magenta in the crop is the title.
- The title is plain black text with no violet rule and no dashed divider. The paper has a bold italic magenta-plum title over violet rules.
- Footnote letters `a` on 3i and 3j are not drawn; the footnote text is not in the crop.
- Orientation differs: the replica does not follow the paper's orientation for the N-acyl rings and chains.
- Entry spacing and structure size are not measured against the paper; bond and label size follow the `nature` base preset only. Proportions and line weight are therefore not claimed as matched.

## Tool gaps

- No paired-cell scope layout: the card's `scope_layout` key is not read by the scope path (`figure_scope.py` does not use it, and no layout code reads it). `publication/layout.py` packs entries in input order, wrapping by width, and starts a new row for each `group`. Giving each pair its own group might put the substrate and the product side by side, but this was not tested, and each group name would be drawn as a heading.
- An 8-reaction scheme cannot stand in for the grid: `draw_figure` refuses unconnected reactions ("The steps are not a linear route, a convergent route (arms that merge) or a set of reactions from one starting material, so they cannot be laid out."). Pairs drawn as separate steps fail.
- House conventions do not reach scope panels: `figure_scope.py` does not import `figure_house`, the report hard-codes `applied: []` and the note "house conventions apply to schemes only; the base preset was applied". Bold labels, the variation colour, the abbreviations and the title rule are all lost.
- A missing `label` falls back to the internal species id in the drawn panel (`s3`, `p3`, `s7`): `publication/data.py` uses `row label or compound id`.
- A missing value is drawn as a dash under the entry (`publication/data.py` writes `—` for an empty value). There is no option to leave the value blank.
- The `abbreviate_groups` list has no `Piv` (pivaloyl) entry, and the card's `OMe` does not reproduce the `MeO` spelling in the crop. Abbreviations are applied only on schemes.
- Yield placement: the layout writes the label, then each field, on separate lines. There is no option for `label: value` on one line.
- Orientation: `SPECIES_KEYS` in `figure_scope.py` is `id`, `smiles`, `name`, `label`, `group`, `values`. No per-entry orientation or rotation exists, so the crop's ring and chain orientation cannot be set.
- Title: the scope title is a plain text object at the top-left margin (`publication/layout.py`). No face, italic, colour or rule option exists.
- Column divider: no line object is available to the scope kind, so the dashed divider cannot be drawn.
- Footnote letters on labels or values: `SPECIES_KEYS` has no footnote key, and `footnotes` are page-level text lines at the bottom only. A superscript `a` on 3i and 3j cannot be drawn.
- Margins and gaps are fixed in `publication/layout.py` (16 pt margin, 12 pt gap) and cannot be set from the brief.
- Timing (session report, not re-run here): `draw_figure` with `--render` exceeded 300 s; the unrendered draw took about 3 minutes, and rendering the page took about 10 minutes on a shared ChemDraw.

## Audit

Second pass on this case: `reference.png`, `rendered.png`, `brief.json`, the card `toolkit/cdxml_toolkit/publication/house_styles/sarpong_group.json`, and the toolkit code paths named above. Pixel sampling of the crop: all structure and label pixels are neutral black; the only magenta is in the title row (y 6 to 25 px); the rules and dashed divider are about `#C385DB`.

Overclaims corrected in the table and text:

- The new CHO is not magenta in the crop. The replica's black CHO matches the crop, so the variation_color row is now a match against the crop. The card's `#800567` matches the title colour, not a variation colour.
- The yield row was counted as a match on values and format alone. The crop places the label and the yield on one line, and the replica does not, so it is not matched.
- "One column" was wrong. The rendered page shows four columns in input order. The pairing gap stands.
- Conditions were counted as "not checkable"; they are not matched.
- Two differences were missing from the first version: the structure orientation and the dashed column divider. They are now in the table and the differences list.

Card issues noticed, not edited (outside this case folder): the `substrate_scope` signature example "3b 66%" does not match the crop (62%); the card's `variation_color` `#800567` is the title colour; the card's `OMe` does not match the crop's `MeO`.

Not verified here: the 300 s and 10 minute timings, the contents of `page-002.cdxml`, and the 3i and 3j regiochemistry (checked by eye only).
