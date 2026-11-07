# Natural Product Reports (RSC): maleidride biosynthesis route (Scheme 24)

Source: Williams et al., "Maleidride biosynthesis: construction of dimeric anhydrides", *Nat. Prod. Rep.* **2022**. DOI: [10.1039/d2np00041e](https://doi.org/10.1039/d2np00041e).

Licence: CC BY 3.0. The reference crop is the evidence file `evidence/natural_product_reports-01.png` (Scheme 24) reproduced under that licence.

Drawing style: the `natural_product_reports` card (`kind: journal`, base preset `rsc`), figure type `biosynthesis`.

## What is reproduced

The full oxidative route 108 to 115 in one `draw_figure` call with six steps: RbtB (108 to 112), RbtG (112 to 113), RbtE (113 to 114), RbtU (114 to 13), RbtA (FMO) (13 to 111) and RbtB (111 to 115). Compound numbers are bold. Enzyme names sit above each arrow, and the cofactor lines (Fe²⁺, α-KG, O2) sit below the arrow, followed by the by-products.

Structures were read from the crop by hand and checked with RDKit (formulas: 108 C26H34O7, 115 C26H32O12). No OCSR was run. Ring and side-chain stereocentres are not encoded (see Differences). The E-alkene is encoded.

Layout: the first attempt (`max_width` 504) gave one step per row. The replica uses `max_width` 1100, which gives a 4 + 4 grid: 108, 112, 113, 114 on the first row, and 114, 13, 111, 115 on the second. Structure 114 is drawn twice, once at the end of the first row and once at the start of the second, because the wrap repeats the substrate of the step that opens the new row. The paper uses a folded route: 108, 112 and 113 run across the top, 114 sits in the fold below 113, and 13, 111 and 115 run right to left along the bottom.

## Replay

```
python skill/chemdraw/scripts/cdx.py py skill/chemdraw/assets/house-styles/natural_product_reports/replica/natural_product_reports-01/replay.py NEW_DIR
python skill/chemdraw/scripts/cdx.py render NEW_DIR/figure.cdxml
```

`replay.py` runs `draw_figure` on `brief.json` offline and writes `figure.cdxml` and `validation.json`. `rendered.png` is the 1200 px downscale of the tool's ChemDraw render; `reference.png` is the crop.

## Convention check

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| enzyme name above the arrow (card: bold italic blue) | RbtB, RbtG, RbtE, RbtU, RbtA bold italic blue | plain black text above the arrow | no |
| cofactors (Fe2+, alpha-KG, O2) stacked under the arrow | mixed: stacked in three steps (108 to 112, 112 to 113, 111 to 115), a single horizontal line (Fe2+ alpha-KG O2) in two (113 to 114, 114 to 13); O2 red; block starts at the arrow's left end | every step stacked and centred under the arrow, with succinate and CO2 as a fourth line | no |
| by-products (succinate, CO2) on a small curved side arrow | curved arrow to the right of the cofactors | plain text under the arrow | no |
| O2 in red (reagent text colour) | red | black | no |
| atoms changed by the enzyme coloured red (`variation_color` #D8151F) | new OH and C=O red | all black | no |
| bold compound numbers | bold, set at the lower left under each structure (not centred) | bold, centred under each structure | no |
| compound label colour black | yes | yes | yes |
| arrow style plain | plain arrows | plain arrows | yes |
| conditions split: enzyme above, cofactors below | enzyme above; cofactors below, with succinate and CO2 on a separate curved arrow | enzyme above; cofactors, succinate and CO2 all below | no (by-products sit in the cofactor block; the card's `conditions_split` is null, so the split is the brief's manual above/below lists, not a card convention) |
| Kekule rings, thin lines, sans-serif labels | Kekule rings yes; Arial-like labels; bold wedge bonds on stereocentres | Kekule rings yes; Arial-like labels; no wedges; line weight not measured | no (line weight unverified; paper's bold wedges absent) |
| intermediate numbering in bold | yes | yes | yes |
| abbreviate_groups includes Me | no Me label: the heptyl chain is a zigzag ending in a line | "Me" label drawn at each chain end | no |

Matched 3 of 12 convention rows (compound label colour, arrow style, bold intermediate numbering). The earlier count of 6 did not match the table, which had seven "yes" rows. See the Audit note below.

## Differences from the paper

- Enzyme names are plain black text, not bold italic blue.
- The by-products are text under the arrow, written as one line ("succinate, CO2"). The paper prints "succinate" and "CO2" on two lines at the end of a curved side arrow.
- O2 is black, and no atoms are coloured red. The new hydroxyls, the aldehyde C=O and the carboxylic acid OH are all black.
- The chain ends are labelled "Me" (abbreviate_groups). The paper draws the heptyl chain as a plain zigzag.
- Ring and side-chain stereocentres are not drawn, and the H-atom labels on them are absent. The paper uses bold and hashed wedges and H labels. The replica has no wedges.
- The paper's primed locants (2''', 1'', 6''' and so on) are not drawn, and the plain locant 2 on the ring carbon of 114 is absent.
- Compound numbers sit centred under each structure. In the paper they sit at the lower left.
- Layout: the paper's folded route becomes a 4 + 4 left-to-right grid with 114 drawn twice. No step runs right to left, and the 113 to 114 and 114 to 13 steps are vertical arrows in the paper but horizontal here.
- The FMO step (13 to 111) shows no cofactor below the arrow, as in the paper.

## Tool gaps

- No per-step or per-enzyme text styling (bold, italic, colour) for the above line. `reagent_text_color` paints whole text boxes, so a single run cannot be coloured either.
- No per-character colour for cofactor lines (O2 red). Same cause as above.
- No curved side arrow for by-products. The arrow kinds are solid, dashed, failed, reversible and resonance only.
- Cofactor text cannot take part in the balance check, and the step schema has no agents or by-product field. `_check_balance` in `figure_draw.py` uses only the drawn substrates and products. Each of the six steps differs in formula between substrate and product (five steps gain one O from O2; the FMO step loses H2, 13 C26H34O11 to 111 C26H32O11), so six "does not balance" warnings are expected. The FMO step has no cofactor text, so the cofactor lines are not the cause. The gap is a missing agents or by-products field in the step schema.
- `new_bond_color` is applied only to bonds found by atom mapping, and it is null in this card. More basically, `draw_figure` has no figure-type key, and `apply_figure_type_conventions` is called only for mechanisms and catalytic cycles. The biosynthesis `variation_color`, `enzyme_label_style` and `intermediate_label_style` are therefore never applied, not only the new-bond colour.
- No per-atom label colour. `atom_halos` draws halos, not coloured atom labels, so the red new OH, the red C=O and the red acid OH cannot be drawn.
- The route layout is a row-by-row left-to-right wrap, and every arrow points in reading order. The paper's downward steps and right-to-left bottom row cannot be expressed. The wrap also repeats the substrate of the step that opens a row (114 drawn twice), and there is no row-break connector.
- No key for compound-number anchor (lower left or centred) or for the alignment of the reagent block under the arrow, in either the card or the brief.
- Primed locants (2''', 1''', 6''' and so on), plain numeric locants on ring atoms (2 on 114, 1'' on 13) and H-atom labels are not supported.
- Stereo wedges and hashes are drawn only if the SMILES carries stereo. This replica does not assign stereo.

## Card notes (not edited here)

- `figure_types.biosynthesis.conventions.enzyme_label_style` is null, but its note describes bold italic blue #0704F6 text for crop 01.
- `reagent_text_color` is #000000, but crop 01 prints O2 in red, so the card cannot express the convention its own signature feature describes.
- The `bold compound numbers centred under each structure` feature cites crop 01. In crop 01 (this Scheme 24) the numbers sit at the lower left.

## Audit

Checked against `reference.png` (the crop, 769 px wide), `rendered.png` (1200 px, the downscale of the replica render), `brief.json` and the card. Every "yes" row was re-read against the crop and against the drawn output.

- The first count was wrong. The table had seven "yes" rows, the text said six. After re-checking, three rows match: compound label colour, arrow style and bold intermediate numbering. Four of the former "yes" rows are no: cofactor stacking, compound-number placement, conditions split and the Kekule/thin-line row.
- The phrase "the card lists 12 for this figure type" is removed. The card has no list of 12 conventions for the biosynthesis type; the 12 rows are this table's own.
- The layout is 4 + 4 with 114 drawn twice, not 4 + 2.
- The cause of the balance warnings is corrected. Cofactor text is not read by the balance check at all. The warnings come from the drawn substrate and product formulas (checked with RDKit from the brief SMILES: 108 C26H34O7, 112 C26H34O8, 113 C26H34O9, 114 C26H34O10, 13 C26H34O11, 111 C26H32O11, 115 C26H32O12). The tool was not run to read its warnings, so the count of six is inferred from those formulas.
- Verified: the 108 and 115 formulas; `reagent_text_color` paints whole text boxes; no curved by-product arrow in the tool; the biosynthesis figure-type conventions are not applied by `draw_figure`.
- Not verified and not counted: proportions (bond length against arrow length and label size) and line weight. The replica render is 1200 px wide and the reference is 769 px, so ratios cannot be read reliably from these images. The card's measured ratios are not reproduced here. The yield convention is not tested, because Scheme 24 has no yields.
