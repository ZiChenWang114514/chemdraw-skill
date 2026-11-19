# Nature Portfolio card replica: nature_portfolio-03 (reaction scheme)

Source: Zhao, Jia and Wang, *Nature Communications* 2024, 15, 2415, DOI [10.1038/s41467-024-46576-2](https://doi.org/10.1038/s41467-024-46576-2). Licence: CC BY 4.0. Crop: `evidence/nature_portfolio-03.png` (Fig. 2 header of the paper; the crop also holds two X-ray structures, 2k and 8a, and the top of scope row a).

Card: `toolkit/cdxml_toolkit/publication/house_styles/nature_portfolio.json` (style slug `nature_portfolio`, base preset `nature`). Figure type: `reaction_scheme`.

## What is reproduced

The top-left reaction of the crop: a cyclohexyl aryl ketone is converted to the 3-hydroxyphenyl ketone with CuI (10 mol%), AgOAc (9 mol%), TFA (10.0 equiv), H2O (11.1 equiv), DMSO, 90 °C, O2. Catalysts sit above the arrow; additives, solvent, temperature and O2 sit below.

The X-ray structures, the R = aryl box and the scope rows are not drawn. No compound numbers or yields appear in this scheme, so none are drawn.

| ID | Structure (SMILES in brief.json) | Check |
| --- | --- | --- |
| SM | `O=C(C1CCCCC1)c1ccccc1` (cyclohexyl phenyl ketone, C13H16O) | RDKit canonical form matches the drawn structure |
| P | `O=C(c1ccccc1)c1cccc(O)c1` (3-hydroxybenzophenone, C13H10O2) | RDKit canonical form matches; OH meta to the carbonyl as in the crop |

The paper's R is a generic aryl group (box "R = aryl"). The replica uses phenyl as a stand-in, so the carbonyl substituent reads as Ph in the drawing. This is a substitution of the paper's own R, not a reading of its structure.

## Replay

```
python skill/chemdraw/scripts/cdx.py draw skill/chemdraw/assets/house-styles/nature_portfolio/replica/nature_portfolio-03/brief.json NEW_DIR/figure.cdxml --render
```

`replay.py` runs the same brief through `draw_figure` offline (`python skill/chemdraw/scripts/cdx.py py skill/chemdraw/assets/house-styles/nature_portfolio/replica/nature_portfolio-03/replay.py NEW_DIR`). It was not executed in this pass; the draw above is the one that produced `rendered.png`.

## Comparison

Renders: `rendered.png` (try 1, kept). Try 2 is not in the case folder and was not checked in the audit. Try 2 moved the teal substrate colour onto the carbonyl C and O (not in the crop) and still left the phenol ring black, so try 1 was kept.

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| conditions_split reagents_above_solvent_below | catalysts above (CuI, AgOAc); TFA, H2O, DMSO, 90 °C, O2 below | same split | yes |
| aromatic_rings kekule | phenyl and phenol rings with inner double bonds | Kekulé rings | yes |
| new_bond_color null | no new-bond colour | none | yes |
| highlight_fill null | none | none | yes |
| arrow_style plain | plain solid arrow | plain solid arrow | yes |
| substrate_colors #0078B2 (substrate skeleton teal) | cyclohexyl ring teal in substrate; phenol ring and OH teal in product | cyclohexyl ring teal in substrate; product ring and OH black | no (product half not matched) |
| reagent_text_color #000000 | all black except H2O in the conditions, bold teal | all black, matching the card value; H2O not teal and not bold | no (H2O differs from the paper) |
| arrow length / bond length | about 11.3 (531 / 47 px); card 11.1 | about 11.8 (127.4 / 10.8 pt), from the author's pt values, not pixel-measured on rendered.png | no (not verified; about 4–6% off) |
| line width / bond length | 0.043 (2 / 47 px) in the crop; card mean 0.062 | 0.056 (0.6 / 10.8 pt) | no (about 30% above the crop value; about 10% under the card mean) |
| bond length / label cap height | 2.76 (47 / 17 px) in the crop; card mean 2.209 | about 2.5 (10.8 pt / about 4.3 pt cap at 6 pt) | no |
| atom label size | card estimate 7.3 pt | 6 pt (nature preset LabelSize) | no |
| label font | Arial | Arial (nature preset) | yes (visual check only) |
| subscripts in formula text (H2O, O2) | subscript | subscript | yes |
| conditions centred above and below arrow | centred | centred | yes |
| structure orientation | substrate carbonyl O pointing up, R to the right; product OH hanging below the ring | substrate carbonyl O pointing down, Ph up-left; product carbonyl O down and HO to the left of the ring | no |
| compound_label_face / colour / italic suffix | no compound labels in this scheme | none drawn | not testable |
| yield_placement, yield_format, yield_separator | no yields in this scheme | none drawn | not testable |
| abbreviate_groups (OMe, Ph, Me, Et, tBu, CN) | R is generic in the paper | phenyl stand-in drawn as Ph | not testable |
| substrate_layout null, show_plus_sign null | single substrate, no plus sign | same | not testable |

Testable card conventions: 7 (conditions_split, aromatic_rings, new_bond_color, highlight_fill, arrow_style, substrate_colors, reagent_text_color). Matched in full: 5 (the first five; substrate_colors and reagent_text_color are not matched). Two of the five are matched by absence (new_bond_color and highlight_fill are null in both images).

Visible scheme features checked: 8 (arrow length, line weight, bond/cap ratio, label size, label font, subscripts, centring, orientation). Matched: 3 (label font on visual check only, subscripts, centring). Not matched: arrow length (not verified), line weight, bond/cap ratio, label size, orientation.

## Differences from the paper

- Product colour: the paper colours the phenol ring and its OH teal in the product; the replica leaves them black.
- H2O: the paper sets H2O in the conditions bold and teal; the replica sets it in plain black text.
- Carbonyl substituent: the paper's R is a generic aryl group; the replica uses phenyl.
- Orientation: the paper draws the substrate and product with the carbonyl O up and R to the right; the replica draws the carbonyl O down with Ph up-left, and the product OH to the left of the ring rather than hanging below it.
- Label size: the replica's 6 pt labels look smaller relative to the bonds than in the crop.
- Line weight and arrow length: the replica's line is about 30% heavier than the crop's relative to the bond length, and its arrow length is not verified against the crop's 11.3 bond lengths.
- Balance: the tool warns that step 1 does not balance, because O2 and water are listed only as conditions. The paper draws no by-products either, so the warning is accepted and nothing was added.
- Scope: the X-ray structures (2k, 8a) and scope row a are outside this reaction and are not drawn.

## Tool gaps

- `substrate_colors` colours a whole substrate molecule, and which atoms of it are coloured depends on the mapping heuristic; in try 2 the carbonyl C and O turned teal while the ring did not. There is no way to colour a chosen atom set (for example the cyclohexyl ring only).
- The substrate colour does not follow the substrate skeleton into a product when the ring changes from cyclohexyl to aromatic (the paper colours the phenol ring in the product). The card has no product-side colour field at all, so the teal product ring and OH cannot be requested.
- Above and below condition lines are plain strings; there is no run-level formatting for a bold or coloured word such as H2O.
- No generic R placeholder in a species list: an unnamed R group needs a stand-in SMILES.
- The nature preset gives a 6 pt label; the card's label estimate of 7.3 pt is not applied, and there is no way to set label size from the card. The brief has no label-size key.
- The brief has no orientation or ring-placement key (its keys are style, species, steps and max_width), so the substrate and product cannot be drawn in the paper's orientation.
- A step with reagents listed only as conditions (O2, water) raises the balance warning; there is no flag to mark a step as conditions-only.

## Card observations (for the card owner, not changed here)

- The card has no `figure_types` section, so the reaction_scheme conventions and crop list read from the card do not exist; the conventions above come from the top-level block and the evidence entry only.
- `reagent_text_color` is #000000, but the card's own observation for this crop says the H2O in the conditions is bold teal.
- The card's label estimate (7.3 pt) does not match the nature preset (6 pt) it sits on.
- The card gives the substrate teal as #0078B2 and this crop's observation as #0073AC.

## Audit

Audited against reference.png, rendered.png, brief.json, the card JSON and the house-style schema (`toolkit/cdxml_toolkit/publication/house_styles.py`). Pixel measurement was not possible in the audit runtime (no image library), so line weight and arrow length are judged from the images and the stated numbers only.

Overclaims corrected in the table:

- Arrow length was marked "yes (approx.)"; the replica value comes from the author's pt arithmetic, not from rendered.png. Now "no (not verified)".
- Line width was marked "yes (approx.)"; 0.056 against the crop's 0.043 is about 30% off. Now "no".
- Bond/cap ratio was marked "partial"; 2.5 matches neither the crop (2.76) nor the card (2.209). Now "no".
- Substrate colours was marked "partial"; the product ring and OH are black where the paper has them teal, so the convention is not matched. Now "no".
- Label font is kept as "yes" but flagged as a visual check only.
- The visible-feature count "Matched: 5" was overstated. Corrected to 3 of 8. The card-convention count stays at 5 of 7.

Missed in the first pass: the structure orientation differs from the paper (substrate and product), and the card has no product-side colour field. Both are now in the table, the differences list and the tool gaps.

Not verified in this audit: the try 2 render (not in the folder), and whether the carbonyl C and O are teal in rendered.png at full resolution.
