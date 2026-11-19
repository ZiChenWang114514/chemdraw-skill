# Natural Product Reports 2024: Dragmacidin B route (Scheme 25, top)

Source: Tepe et al., "Advances in the total synthesis of bis- and tris-indole alkaloids containing N-heterocyclic linker moieties", *Nat. Prod. Rep.* **2024**. DOI: [10.1039/d4np00012a](https://doi.org/10.1039/d4np00012a).

Licence: CC BY 3.0 (from the `natural_product_reports` card). The reference crop `reference.png` is reproduced under that licence.

Drawing style: the `natural_product_reports` house style (base preset `rsc`); figure type `total_synthesis`; see `cdx.py styles natural_product_reports`.

## What is reproduced

The top route of Scheme 25: two steps, with the second step dropping down from 117 to the target on a second row.

- 116 to 117: 1,4-dimethylpiperazine-2,5-dione with NBS, AIBN, CCl4 (1), then 6-bromoindole in DMF (2); 57%.
- 117 to Dragmacidin B (111b): BH3•THF; 25%.

Structures for 116 and 117 are drawn from the crop. Compound 116 is `CN1C(=O)CN(C)C(=O)C1`. Compound 117 is `CN1C(=O)[C@@H](c2c[nH]c3cc(Br)ccc23)N(C)C(=O)[C@@H]1c1c[nH]c2cc(Br)ccc12`. The 3- and 6-stereocentres follow the crop: a bold wedge to one indole and a hashed bond to the other. RDKit assigns the drawn compound as the (3R,6S) diastereomer. The two wedge-consistent tag sets give the same canonical SMILES, so the stereo is unambiguous.

Target 111b is not drawn in the crop, which shows only the name in a box. The replica draws `CN1C[C@@H](c2c[nH]c3cc(Br)ccc23)N(C)C[C@@H]1c1c[nH]c2cc(Br)ccc12`, the amide-reduction product of 117 with the stereo kept. This is an inference from the BH3 step, not a structure read from the figure. It is labelled with the name and number from the crop.

The `brief.json` here uses `max_width` 760. At the default 504 the tool wraps the route and repeats 117 as a substrate on a second row (checked by replaying the brief). The paper does not repeat 117; its second step drops vertically to the target, which the tool cannot draw.

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| compound numbers bold (top level; crops 01, 06, 07) | bold 116 and 117; in the target label only "(111b)" is bold | bold 116 and 117; the whole label "Dragmacidin B (111b)" is bold | partial |
| compound label colour `#000000` | black | black | yes |
| yield format `{value}%` | 57%, 25% | 57%, 25% (format only) | yes |
| yields in bold under the arrow | bold 57% and 25% | plain (CDXML face 96); `yield_format` sets text only | no |
| yield placement `under_arrow` | 57% under the reagent block; 25% beside the vertical shaft of step 2 | both in the condition block under the horizontal arrow | partial |
| numbered reagent lines, 1. above and 2. below, no solvent split | 1. NBS, AIBN, CCl4 above; 2. 6-bromoindole structure, DMF, 57% below | same numbering and split; reagent 2 as text | yes |
| reagent text colour `#000000` | black | black | yes |
| arrow style plain | thin plain arrows, solid head | plain line, full solid head (arrow length differs, see Audit) | yes |
| abbreviate groups Me | Me | Me | yes |
| aromatic rings Kekule | Kekule | Kekule (20 double bonds in the replay CDXML) | yes |
| thin plain lines, Arial-like labels (top level) | thin lines, sans-serif labels | line 0.60 pt on a 12.2 pt bond; Helvetica 7 pt labels | yes |
| final target named with bold number (figure type) | "Dragmacidin B" regular, "(111b)" bold, in a rounded box; no structure | whole label bold; an inferred structure is drawn above it | partial |
| final target in a thin rounded rectangle (figure type) | name in a rounded box | no box | no |
| long routes folded back right to left (figure type) | no right-to-left fold in this crop; step 2 drops down to a second row | single row; no drop | not exercised (layout differs, see Audit) |
| unisolated intermediates in square brackets (figure type) | not present in this crop | not present | not exercised |
| 3,6-stereocentres of 117 as one wedge and one hash | one bold wedge, one hashed bond | one wedge, one hash; RDKit (3R,6S), indolyl groups on opposite faces in 3D (trans) | yes (visible, not a card claim) |
| reagent 2 drawn as a structure below the arrow | 6-bromoindole structure | text "6-bromoindole" | no (visible, not a card claim) |

Claimed: 15 card conventions (figure type total_synthesis plus the top level). Matched after audit: 8 (was 9; compound numbers moved to partial). Partial: 3 (compound numbers, yield placement, target label). No: 2 (bold yields; rounded target box). Not exercised: 2 (folded routes; bracketed intermediates).

## Differences from the paper

- 6-bromoindole is drawn as text. The paper draws the indole structure under the arrow, beside the "2." line.
- Replica yields are plain text. The paper sets them in bold.
- The 25% yield sits under the horizontal arrow in the replica. In the paper, step 2 is a vertical arrow and 25% sits beside its shaft, to the right, with BH3•THF to the left.
- The target is drawn as a structure. The paper shows only the name in a rounded rectangle, with "Dragmacidin B" regular and "(111b)" bold.
- The target structure is the amide-reduction product of 117 (inferred, see above). It is not confirmed against the paper's own structure for 111b.
- Layout: the paper's step 2 drops vertically from 117 to the target on a second row. The replica keeps one row (`max_width` 760), so this drop is not reproduced.
- Balance warnings: step 1 reports the missing C16H8Br2N2 (the NBS-derived by-products) and step 2 reports the missing H4 (reduction hydrogens). Nothing was added to the drawing.

## Tool gaps

- A condition line in a `draw_figure` JSON brief is text only. A reagent such as 6-bromoindole cannot be drawn as a structure below the arrow.
- There is no rounded-rectangle box for a name-only target. A product must be a structure, so a name-only target cannot be drawn in the paper's form.
- There is no bold option for yields. `yield_format` changes the text only.
- There is no way to place a yield beside the arrow shaft. The `yield_placement` options in `house_styles.py` are `under_arrow`, `under_product_label`, `after_product_label` and `after_product_label_parenthesised`; none is beside the shaft.
- Steps run horizontally in a row. The step `arrow` field takes only solid, dashed, failed, reversible or resonance, so there is no downward step arrow and no way to put a product on a second row below its substrate without repeating the substrate.
- The label face is applied to the whole species label. There is no run-level bold, so "(111b)" alone cannot be bold.
- The brief has no arrow-length key (`BRIEF_KEYS`: kind, species, steps, max_width, title, style, layout). The first arrow came out at 80.2 pt, 6.6 bond lengths, against the house value of 4.9.
- The default `max_width` of 504 pt wraps a three-structure route onto a second row that repeats the intermediate (verified by replay). Keeping it on one row needed `max_width` 760.

## Replay

```
python skill/chemdraw/scripts/cdx.py py skill/chemdraw/assets/house-styles/natural_product_reports/replica/natural_product_reports-06/replay.py NEW_DIR
python skill/chemdraw/scripts/cdx.py render NEW_DIR/figure.cdxml
```

`replay.py` runs `draw_figure` on `brief.json` offline and writes `figure.cdxml` and `validation.json`. Compare `rendered.png` (the ChemDraw render, downscaled to 1200 px wide) with `reference.png`.

## Audit

Checked against `reference.png`, `rendered.png`, the replay CDXML and `natural_product_reports.json`. Matched count corrected from 9 to 8 of 15.

Overclaims corrected:

- "The rendered route is one row, as in the crop" was wrong. The crop's step 2 drops vertically from 117 to the target on a second row. The one-row layout is a choice made with `max_width` 760, not a match.
- Compound numbers: the replica bolds the whole target label. The crop bolds only "(111b)".
- Final target: the crop has no structure for 111b, and the structure drawn is an addition. Its name is bold in full, and there is no box. "Partial" overstated this.
- Folded routes: "not present in this crop" holds only for right-to-left folding. The crop's downward second row is a layout feature the replica does not reproduce.
- Arrow length was not in the table. Replica arrow 1 is 80.2 pt, or 6.6 bond lengths, against the card's 4.9. The replicator's own crop measure (190 px over a 35 px bond) gives 5.4. Not matched.

Checked and holding:

- Stereo: RDKit gives (R,S) for 117. A 3D embedding puts the two indolyl groups on opposite faces of the ring, which is trans. This agrees with one wedge and one hash in the crop.
- Line width: 0.60 pt on a 12.2 pt bond is 0.049, against the card's 0.05.
- Labels: Helvetica 7 pt gives a bond-to-cap ratio of about 2.4. The card says 2.6 and the replicator's crop measure is 2.3. Not flagged, but not confirmed either.
- Tool claims: yields have no bold option, conditions are text only, there is no rounded box, and the 504 repeat is real.
- Tool gap correction: `after_product_label_parenthesised` exists. The gap list is still right that no option places a yield beside the shaft.

Not verified: the bold wedge width. The replica's `BoldWidth` is 1.6 pt, or 0.13 of the bond. The card's 0.25 comes from crop 01, not crop 06.
