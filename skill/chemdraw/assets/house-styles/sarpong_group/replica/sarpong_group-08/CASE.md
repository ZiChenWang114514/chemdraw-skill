# sarpong_group-08: hetisine skeleton and bond-network analysis (Figure 6)

Source: Sarpong and Hoffmann et al., *Angew. Chem. Int. Ed.* **2020** (A case for bond-network analysis in the synthesis of bridged polycyclic complex molecules: hetidine and hetisine alkaloids). DOI: [10.1002/anie.201909656](https://doi.org/10.1002/anie.201909656). Licence: CC BY 4.0 (from the house-style card). Reference crop: `reference.png` (copy of `evidence/sarpong_group-08.png`, Figure 6).

Figure type: `retrosynthesis` (bond-network analysis; no retro arrows in the crop).

Card: `skill/chemdraw/assets/house-styles/sarpong_group/README.md` and `toolkit/cdxml_toolkit/publication/house_styles/sarpong_group.json` (`figure_types.retrosynthesis`).

## What is reproduced

Compound 14 (the hetisine skeleton, heptacyclic C20 framework with the N bridge, C17 exocyclic methylene and C18 methyl) and compound 14a (the same skeleton, which the paper marks with five strategic bonds). Both are drawn as one `kind: "scope"` panel with the title "hetisine skeleton" and labels 14 and 14a. The bottom row of the crop (two more structures, compound labels cut off by the crop edge) is not reproduced.

Structure source: the SMILES was built from the numbered skeleton in the figure (atisane bicyclo[2.2.2]octane, C20-N bridge, C14-C20 and N-C6 bonds of the hetisine type), not from OCSR. RDKit gives `C=C1CC23CC4C5C6(C)CCCC57C(C2CC1CC37)N4C6` as C20H27N, 21 heavy atoms (20 C + N), 7 rings (ring sizes 5, 5, 5, 6, 6, 6, 6). This is consistent with a heptacyclic C20 skeleton, but it does not show that the connectivity equals the figure's. The label-to-atom mapping is in the scratch folder only, so the drawn bonds could not be checked against the figure's numbering from this case folder. The replica is also left-right reversed relative to the paper (C4 methyl on the right, exocyclic CH2 on the left).

Strategic bonds in 14a: red #EA3735 for C8-C9, C8-C14 and C10-C20; green #42B54F for C9-C10 and C14-C20 (five bonds in total). Re-checked against the enlarged reference crop during the audit. They are not drawn in the replica (see the gaps below).

## Replay

```
python skill/chemdraw/scripts/cdx.py py skill/chemdraw/assets/house-styles/sarpong_group/replica/sarpong_group-08/replay.py NEW_DIR
python skill/chemdraw/scripts/cdx.py render NEW_DIR/figure.cdxml/page-001.cdxml
```

`replay.py` runs `draw_figure` on `brief.json` offline and writes `figure.cdxml/` (page-001.cdxml, manifest, checks). `rendered.png` is the desktop ChemDraw render of the same page (881 x 376 px, about 22 KB). `draw --render` in one call timed out at 300 s on the first try; the draw without render followed by `cdx.py render` succeeded.

## Convention table

Only conventions the card claims for `retrosynthesis`, the top-level conventions visible in the crop, and the measured bond-to-label ratio are listed. Rows marked n/a have nothing in the paper or the replica to check, so they are not counted.

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| retro_arrow: none | no arrows between 14 and 14a | no arrow | yes |
| disconnection_mark: colored_bond | strategic bonds coloured | bonds all black | no |
| disconnection_color: #EA3735 | red bonds C8-C9, C8-C14, C10-C20 | none | no |
| highlight_fill: null | no fill in the crop | no fill | n/a |
| step_count_shown: false | no step counts in the crop | none | n/a |
| signature: strategic bonds thick red #EA3735 and green #42B54F | red and green bonds in 14a | not drawn | no |
| signature: ring letters A-G in blue | blue ring letters in 14 | not drawn | no |
| signature: carbon numbers in small black digits | 1-20 in 14, 9/10/14/20 in 14a | not drawn | no |
| compound_label_color: #000000 | black labels | black labels | yes |
| compound_label_face: bold | "14" and "14a" bold | plain weight (scope path) | no |
| signature: heavy bonds near face of caged polycycle | even weight in 14; the heavy strokes are the coloured bonds of 14a | one line weight | no |
| bond_length_over_cap_height: 2.9 (card) | about 2.6-3.0 (bonds 34-39 px, bold label cap 13 px) | about 2.0 (bond about 45 px, label digits 23 px) | no |

Matched 2 of 10 applicable rows (retro_arrow, compound_label_color). The earlier count of 4 of 11 counted the two n/a rows as matches. Line weight relative to bond length (card 0.056) measured about 0.06-0.07 in both images; that is within pixel error, so it is not counted as matched. Font was not measured.

## Differences from the paper

- Only compounds 14 and 14a are drawn, side by side in one row. The paper's 2 x 2 layout has two lower structures (compound labels cut off in the crop), which are not reproduced.
- Strategic bonds: 14a looks identical to 14. The red and green bonds of the bond-network analysis are the content of this figure and are missing.
- No ring letters A-G and no carbon numbers 1-20 (and 9, 10, 14, 20 in 14a) are drawn.
- Labels: the paper's compound labels are bold; the scope panel draws them in plain weight. The title "hetisine skeleton" is plain; the paper's title is bold.
- The C4 methyl is a plain line; the paper labels it with a bold "Me". Me is not in the card's `abbreviate_groups` (OMe, Boc, tBu), so this is also a card gap.
- The N atom is plain; in the paper it is bold.
- Font: the replica digits look like Arial; the card's measured label font is Helvetica. Arial and Helvetica are nearly identical at this resolution, so this is not a decisive difference.
- Line weight: the replica's bonds are one even weight. In the paper's 14 the black bonds also look even; the heavy strokes in this crop are the coloured bonds of 14a. The card's near-face bold signature does not appear in this crop, so the earlier wording "some heavier bonds in the cage" is not supported.
- Geometry: the 2D layout comes from the SMILES, not from the paper's perspective, and the left-right orientation is reversed. Near the top centre of 14 two bonds run close together and read as a double line. The readback only compared drawn bond orders with the SMILES. It does not show that the drawing reproduces the paper's skeleton, so the conclusion "layout, not chemistry" is not established.
- Proportions (pixel measurement of both PNGs, approximate, plus or minus 1 px): reference bonds 34-39 px, bold compound label "14" cap height 13 px, so bond/cap about 2.6-3.0 (card 2.9). Replica bond about 45 px, "14" digit height 23 px, so bond/cap about 2.0. The replica's labels are about 1.4 times too large relative to the bonds.
- Label placement: in the paper, "14" and "14a" sit directly under each structure, about 20 px below it. In the replica, the labels sit at the bottom corners of the canvas, about 50 px below the structure, and "14" lies left of the structure's footprint.
- Title position: the replica title starts at the canvas's left edge; the paper's title sits over the left structure.
- Rendering artefact: near the centre of 14 (about x 245-290, y 210-230 in `rendered.png`), some crossing bonds appear as short broken dashes. The paper does not show this. The cause was not checked.

## Tool gaps

Gaps below are for `draw_figure` brief kinds unless noted. The toolkit's manifest route `compose_chemical_figure` (`toolkit/cdxml_toolkit/mcp_runtime/figure_tools.py`) covers several of them, so they are gaps of the `draw_figure` path, not of the toolkit.

- No per-bond colour in `draw_figure` for a structure without a reaction step. `new_bond_color` colours only bonds formed in a step (needs `steps` and atom mapping). `ring_fills` and `atom_halos` colour rings and atoms, not bonds. `compose_chemical_figure` molecule items take `highlight_bonds` with `highlight_color`, which sets the bond colour; this route was not used.
- No ring-letter annotation field in any `draw_figure` brief kind. `compose_chemical_figure` can place text items with a colour, but positions must be given by hand.
- No atom-number labels in `draw_figure` outside `kind: "mechanism"` (`show_atom_numbers` is for checking mechanism moves on a draft). `compose_chemical_figure` has `atom_numbers`, but it prints RDKit 0-based atom indices, not the paper's numbering, so an index map is needed.
- Scope panels skip house conventions: the report says "house conventions apply to schemes only", so bold labels and house abbreviations are not applied. `applied` is empty.
- No bold or heavy bond option in `draw_figure` for the near face of a caged polycycle. `compose_chemical_figure` has `bond_displays` with `Bold` per bond index.
- No 2D coordinate input in `draw_figure`; the depiction is an automatic layout. `compose_chemical_figure` takes explicit `coordinates` and `preserve_coordinates`. The perspective of the paper's drawing is not a parameter in either route.
- Scope panels keep their own text size: `figure_scope.py` pops `font_size` from the preset, and `SCOPE_KEYS` has no label-size key. This is why the replica's labels are about 1.4 times too large relative to the bonds.
- Scope labels have no position key (`SCOPE_KEYS` has none), so they land at the bottom corners of the panel instead of under each structure.
- Scope layout is a single grid: no 2 x 2 arrangement with free offsets or mixed panel sizes.
- Scope title is plain text; no bold title option (`SCOPE_KEYS` has no weight key).
- Bold text runs exist only in the `compose_chemical_figure` text items (`runs` with a bold flag); scope labels have no weight key.
- `max_width` is rejected for `kind: "scope"` (`Unknown brief keys: ['max_width']`); the scope panel takes `width_mm`/`height_mm`.

## Audit

Checked in this audit: `reference.png`, `rendered.png`, `brief.json`, this file, the card `toolkit/cdxml_toolkit/publication/house_styles/sarpong_group.json`, and the toolkit source for tool gaps (`figure_scope.py`, `figure_tools.py`). Measurements are from PNG thresholding and 3-5x enlargements, approximate to about 1 px.

Overclaims corrected:

1. Two n/a rows (highlight_fill, step_count_shown) were counted as matches. Corrected count: 2 of 10 applicable rows. The earlier 4 of 11 is not supported.
2. The paper's "heavier front bonds in the cage" is not visible in 14; the heavy strokes are the coloured bonds of 14a.
3. "The readback matched ... so this is layout, not chemistry" and "the drawn bonds match the figure's visible connectivity" are not established. The readback compares drawn bonds with the SMILES only; the numbering map is outside this folder. RDKit gives C20H27N and 7 rings (5, 5, 5, 6, 6, 6, 6), which is consistent with the skeleton but not proof of it.
4. Four listed tool gaps (per-bond colour, 2D coordinates, bold bonds, atom numbers) hold for `draw_figure` only. `compose_chemical_figure` offers them (see the Tool gaps section).

Checked and correct: the five strategic bonds and their colours; retro_arrow none; black compound labels; the title and compound labels plain in the replica but bold in the paper; "Me" and N plain in the replica; no ring letters, atom numbers or coloured bonds in the replica.

Missed by the replicator: the label-to-bond ratio (about 2.0 against the card's 2.9); label placement; the left-right reversal; the crossing-bond dashes; the scope label size fixed in code.
