# Sarpong and Hoffmann, Angew. Chem. Int. Ed. 2020: hetidine core cyclization scheme (Scheme 1)

Source: Sarpong and Hoffmann et al., "A case for bond-network analysis in the synthesis of bridged polycyclic complex molecules: hetidine and hetisine alkaloids", *Angew. Chem. Int. Ed.* **2020**, DOI [10.1002/anie.201909656](https://doi.org/10.1002/anie.201909656). Licence: CC BY 4.0, as recorded on the `sarpong_group` house-style card (not re-checked against the article page). Reference crop: `evidence/sarpong_group-07.png` (copied to `reference.png`).

Drawing style: the `sarpong_group` house style (`brief.json`, `"style": "sarpong_group"`), total_synthesis figure type.

## What is reproduced

The whole of Scheme 1: five structures (3, the N-Boc intermediate after SOCl2, 4, 5 and the boxed final core) and four arrows (SOCl2; "4 steps"; SiO2; "1) Rh/H2, 2) K2CO3"). Compound labels 3, 4 and 5 are drawn; the unlabelled intermediate and final structure are drawn without labels, as in the paper. The paper's blue bond and ring-letter marks (E, B, F, C), the box around the final structure and the cage depiction are not reproduced.

Structures are typed in by hand from the crop (see the table in the structure notes below). OCSR (DECIMER API, `cdx.py ocsr`) was run on each cropped structure, but it returned invalid or mercury-containing SMILES for 4 of 5 and only a partial ring system for 4, so none of its output is used.

Renders: `figure_r1.cdxml` (try 1, `max_width` 504, two rows) and try 2 (`max_width` 720, one row; this is `rendered.png`, from `brief.json`). Try 1 was not kept.

## Replay

```
python skill/chemdraw/scripts/cdx.py py skill/chemdraw/assets/house-styles/sarpong_group/replica/sarpong_group-07/replay.py NEW_DIR
python skill/chemdraw/scripts/cdx.py render NEW_DIR/figure.cdxml
```

## Convention check

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| step_label_style none (no a/b/c step labels) | none | none | yes |
| step_count_shown: "N steps" on the arrow | "4 steps" over the arrow | "4 steps" over the arrow | yes |
| yield_format and yield under the arrow | no yields in this crop | none drawn | no (card claim not visible in this crop) |
| highlight_fill none | no fill | no fill | yes |
| variation_color #A10E3D (card figure-type value) | changed bonds are blue #2758A5, not crimson | no colour drawn | no |
| reagents above each arrow | SOCl2, 4 steps, SiO2, 1) Rh/H2 | same | yes |
| second reagent below the arrow (conditions split) | 2) K2CO3 below | 2) K2CO3 below | yes |
| "prepared in N steps" under the start | not in crop | not drawn | no (card claim not visible in this crop) |
| target name bold italic blue under the final structure | not in crop | not drawn | no (card claim not visible in this crop) |
| changed atoms or new bonds in blue (Angew) | blue bonds E, B, F, C and blue ring letters | none | no |
| compound labels bold, black | bold 3, 4, 5 | bold 3, 4, 5 | yes |
| atom labels (Me, N, O, OH, Boc, OMe) in bold | bold | regular weight | no |
| arrow_style plain | plain arrows, shaft about 2 px | plain arrows, shaft 1 px; the "4 steps" and "1) Rh/H2" arrows are horizontal, not angled as in the paper | yes (style only) |
| aromatic_rings kekule | Kekule arene in 3, 4 and 5 | Kekule | yes |
| abbreviate_groups OMe, Boc (and Me as drawn in the paper) | OMe, Boc, Me | OMe and Boc as text; the methyls are bare stubs with no "Me" label | no |
| reagent text colour black | black | black | yes |
| bold heavy front bonds on caged polycycles | bold front bonds in the cage | plain bonds, cage overlaps | no |
| dark red curved arrows, intermediate brackets | none in this crop | not drawn | n/a (not in crop) |
| arrow length over bond length (card 3.7) | about 2.2 (67 px arrow over a ring bond of about 30 px) | about 5.4 (100 px arrow over a ring bond of about 18.5 px) | no |

Corrected count: 9 of 18 table rows match (the n/a row is excluded). The earlier "9 of 15" cannot be reproduced from this table, which had 10 yes rows out of 16 and no list of 15 conventions. See the Audit note.

## Differences from the paper

- Layout: the paper stacks the scheme as one row, then a second row of 4 and 5 with the boxed final structure. The replica is a single row of four arrows. Structures are much smaller than in the paper, and the cage bonds overlap in 3, the N-Boc intermediate, 4 and 5 and in the final structure, so the 3D cage is not legible.
- Colour: the blue C-N, C-C and ring bonds marked E, B, F and C and the blue ring letters are absent.
- Box: the final structure is boxed in the paper; the replica has no box.
- Condensed step: the "4 steps" arrow is drawn as one arrow between the N-Boc intermediate and 4 without the reagents of the four steps.
- Unlabelled structures: the intermediate and the final structure carry no label, as in the paper, but the paper's 3 is labelled as 3 at a bottom-right position and the replica places it below the left structure.
- Label clash: in 3, the NH and OH labels overlap (draw_figure lint: "Two atom labels of fragment 1000 run into each other").
- The final structure's OH carbon is drawn with stereochemistry-free bonds; the paper's final structure also has no stereo marks in this crop.

## Structure notes

Typed SMILES (my reading of the crop; not checked against the SI or the author's files):

- 3: `CC1(CNC(=O)OC(C)(C)C)CCCC2(CC=C)C(O)c3c(CCC12)cc(OC)cc3` (C26H39NO4)
- N-Boc intermediate (after SOCl2, N to former C-OH bond): `CC1(CN2C(=O)OC(C)(C)C)CCCC3(CC=C)C2c2c(CCC13)cc(OC)cc2`
- 4: `CC12CCCC3(CC=O)C4N(C1)C(=O)OC45C=CC(=O)C=C5CCC23` (C20H23NO4)
- 5 (C8-C9 Michael bond, drawn as a single bond): `CC12CCCC3(C6C=O)C4N(C1)C(=O)OC45C=CC(=O)CC56CCC23` (C20H23NO4)
- Final: `CC12CCCC3(C6C7O)C4N(C1)C(=O)OC45CC7C(=O)CC56CCC23` (C20H25NO4). Assumed reading: Rh/H2 reduces the enone C=C and K2CO3 triggers an intramolecular aldol between the aldehyde and the ring CH2 alpha to the ketone. The paper's text is not checked for this.

RDKit parses all five. The drawing report marks steps 1, 2 and 4 as not atom-balanced (missing H2O, O and H2), which is expected for SOCl2, the condensed "4 steps" and the reduction; nothing was added to the drawing.

## Tool gaps

- No per-bond colour in `draw_figure` (new bonds blue, changed bonds crimson). The card's new-bond colour is null, so the house style cannot mark E, B, F and C.
- No ring-letter labels (A-F) on structures.
- No boxed-structure option for a final product.
- Caged polycycles: the automatic 2D layout overlaps bonds and cannot be given coordinates or a bold-front-bond style in `draw_figure`.
- Condensed multi-step arrows ("4 steps", reagent sequences) cannot be marked as schematic, so balance checks fail on those arrows.
- Layout: only a single sequential row or the catalytic-cycle layout; no two-row or staggered scheme layout beyond `max_width`.
- Label clash avoidance: no control over label placement in crowded polycycles (3's NH and OH overlap).

## Audit

Second pass against `reference.png` (the paper crop) and `rendered.png`, with pixel measurements of arrow and bond lengths. Corrections to the table and text above:

- The "9 of 15" count was not reproducible from the table (10 yes rows out of 16). The count is corrected above.
- "abbreviate OMe, Boc" was marked yes, but the paper labels the methyls "Me" and the replica leaves them as bare stubs. Now no.
- Atom labels (Me, N, O, OH, Boc) are bold in the paper and regular weight in the replica. Compound labels 3, 4 and 5 are bold in both, so that row stays yes.
- Proportions: the arrows are about 2.5 times too long relative to the bonds (about 5.4 bond lengths in the replica, about 2.2 in the paper crop). The card's 3.7 is not reproduced by this scheme. The replica arrow shafts are 1 px against about 2 px in the paper.
- Line weight is not refuted: bond width relative to bond length is similar in both images.
- Layout is not matched: the paper has two rows, with the "4 steps" and "1) Rh/H2" arrows angled down-left and the boxed product on the second row. The replica has one horizontal row.
- Orientation: all five structures are mirror-flipped or rotated relative to the paper (Me on the left in the paper and on the right in the replica; the ketone of 4 on the right in the paper and on the left in the replica). The typed SMILES parse and their formulas match the values in this file, but the drawing does not use the paper's orientation.
- The "Differences" section understates the cage problem. In 3 a cage bond crosses the aromatic ring and the Boc carbonyl bond runs through NH and OH. The CH2CHO side chain of 4 is not legible.
- The differences list omits the paper's blue ring letters A and D on 3 and the small carbon numbers 8 and 9 on 4.
- Colour: the replica has no colour at all, so the "no" rows for colour are correct.
- Yield and the "prepared in N steps" and target-name rows are not in this crop. They are marked no, which means not matched, not that they were checked and found wrong.

Tool gaps the replicator missed:

- No small atom-number labels (8 and 9 on 4) and no blue ring-letter labels (A and D on 3).
- No "Me" abbreviation for terminal methyl groups, so the methyls are bare stubs.
- No font-weight control for atom labels (the paper's atom labels are bold).
- No control of arrow angle, arrow shaft weight, or structure orientation (mirror or rotation).
- No per-bond bold width for an individual bond (distinct from the cage front-bond gap).
