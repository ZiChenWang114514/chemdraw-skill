# Organic Letters: alcohol activation and Ni-catalysed coupling with a chlorosilane (Table 1, top scheme)

Source: Oestreich et al., *Org. Lett.* **2025**, *27*, 3686 (One-pot sequential alcohol activation and nickel-catalyzed cross-electrophile coupling with chlorosilanes). DOI: [10.1021/acs.orglett.5c00830](https://doi.org/10.1021/acs.orglett.5c00830).

Licence: CC BY 4.0. Reference crop `reference.png` is reproduced from Table 1 (PDF page 2, 300 dpi) under that licence.

Drawing style: the `org_lett` house style (`brief.json` `"style": "org_lett"`; base preset ACS Document 1996); see `cdx.py styles org_lett`.

Figure type: `optimization_table` (the card's crop 01 entry).

## What is reproduced

Only the reaction scheme above Table 1: alcohol 1a and chlorosilane 2a give 3aa, with the reagents and conditions written above and below the arrow. The replica keeps the same condition lines on the same sides as the paper, but not its line breaks, its italic "then", its colours or its layout (see Differences).

The optimization table itself (13 entries, variations from the standard conditions, the yield column with footnotes a to d, the reagent key grey box) is not drawn. draw_figure has no table drawer.

## Structures

| ID | SMILES in brief.json | Note |
| --- | --- | --- |
| 1a | `O=C(OCCCO)c1ccc(cc1)S(=O)(=O)N(CCC)CCC` | R is truncated: the paper's wavy bond at the end of R is capped with H (R = ArCO2CH2-). Generic atoms are refused, so the R group cannot be drawn as in the paper. The chain length of 1a is not checked against the paper's R key at this resolution. |
| 2a | `C=C[Si](C)(C)Cl` | vinyl-SiMe2Cl, read from the paper's drawing. |
| 3aa | `O=C(OCCC[Si](C)(C)C=C)c1ccc(cc1)S(=O)(=O)N(CCC)CCC` | Product with the same truncated R; the Si is attached to the terminal CH2 of 1a. |

Each SMILES was read from the crop by eye (no OCSR run). RDKit validation was not run on this machine because the runtime RDKit did not expose rdMolDescriptors in the check call. The original report says draw_figure read back all three structures as drawn (`readback: matched`), but `validation.json` is not in this case folder, so that read-back could not be re-checked.

## Replay

```
python skill/chemdraw/scripts/cdx.py py skill/chemdraw/assets/house-styles/org_lett/replica/org_lett-01/replay.py NEW_DIR
python skill/chemdraw/scripts/cdx.py render NEW_DIR/figure.cdxml
```

`replay.py` runs `draw_figure` on `brief.json` offline and writes `figure.cdxml` and `validation.json`.

## Convention checks

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| compound_label_face bold | 1a, 2a, 3aa bold | bold | yes |
| compound_label_color #000000 | black | black | yes |
| reagent_text_color #000000 | condition text black | condition text black | yes |
| show_plus_sign | 2a shown as a reagent under the arrow, no plus | plus between 1a and 2a (2a is a substrate) | no |
| abbreviate_groups Me | Si-Me groups written Me; the N-propyl groups are written (n-Pr)2N in the R key, not as Me | Me on Si and on the propyl ends of 1a and 3aa | no (propyl ends differ) |
| aromatic_rings kekule | kekule ring | kekule ring | yes |
| arrow_style plain | plain arrow | plain arrow | yes (arrow length and line weight were not measured against the card) |
| substrate_layout inline_plus | 2a under the arrow, left of the conditions, no plus | inline with 1a | no |
| conditions_split reagents_above_solvent_below | the card rule does not describe this scheme; the paper splits by step. Above: POP, TBAB, Barton's base; NMP (0.1 M), r.t. for 1 h; then (italic). Below: NiBr2·diglyme, n-Bu2phen, Mn; r.t. for 23 h | same lines on the same sides; the reagent/solvent split is not applied (style report: skipped) | no against the card rule; the sides match the paper |
| conditions text and line breaks | 3 lines above (POP, TBAB, Barton's base on one line), 2 below; "then" italic | 5 lines above and 3 below (automatic relayout broke lines after commas); r.t. becomes rt; "then" roman | no |
| silyl fragment colour | 2a and 3aa SiMe2(vinyl) group in blue-grey, solid #5178A1 in reference.png (measured) | black | no |
| optimization table: scheme above the table body, three horizontal rules | scheme above the table with rules | table not drawn | no |

Matched: 5 of 12 checked rows (label face, label colour, reagent text colour, kekule, plain arrow). The other seven rows are not reproduced. The table rows are counted as not reproduced.

## Differences from the paper

- R: the wavy bond is replaced by H, so 1a and 3aa are truncated analogues of the paper's compounds.
- Orientation: the paper reads R to OH from left to right, with the alcohol at the right; the replica writes HO on the left.
- 2a: the paper draws the chlorosilane as a reagent under the arrow; the replica draws it as a second substrate joined by a plus.
- Colour: the paper draws the SiMe2(vinyl) group of 2a and 3aa in blue-grey (measured solid #5178A1 in reference.png); the replica draws it black.
- Bond to OH: the paper's bond from the alcohol carbon to OH appears bold in the crop; the replica draws a normal bond. This was judged by eye, not measured.
- Condition text: r.t. becomes rt because draw_figure normalises condition lines; the paper writes r.t. The paper's "then" is italic; the replica's is roman.
- Conditions: the lines and their sides match the paper. The paper's split is by step (first step above, second below), which the card's reagents_above_solvent_below rule does not describe.
- Line breaks: the replica has five lines above and three below; the paper has three above (POP, TBAB, Barton's base on one line) and two below, with 2a set under the arrow.
- The optimization table, its footnotes and the reagent key box (POP, TBAB, Barton's base, the phen ligand family) are not drawn.

## Tool gaps

- No optimization-table drawer: horizontal rules, column headers with footnote superscripts, bare number cells, parenthesised isolated yields, footnote letters.
- No boxed reagent key (grey background, several structures with R-group labels).
- No substrate placed under the arrow without a plus. draw_figure has a `stacked_plus` substrate layout (substrates stacked in a column with a plus), but the org_lett card selects `inline_plus`, so every substrate is drawn inline with a plus.
- No generic atoms or wavy bonds, so the R group of the paper cannot be drawn; the truncation is the only option.
- Colour is not applied: the house style supports substrate colours and a new-bond colour, but the org_lett card sets both to null. The card's `#0336FF` is not the colour of this crop (measured #5178A1), so the blue silyl fragment is missing.
- conditions_split is listed as skipped in the style report: the brief's above and below lines are kept as given.
- Condition text has no italic option in the draw_figure brief, so "then" and "r.t." cannot be set in italic there.
- The brief has no option to keep a condition line whole: when the width check fails, the relayout breaks lines after commas.
- Condition text is normalised (r.t. becomes rt) with no switch to keep journal punctuation.
- The draw_figure brief has no per-bond bold option, so the bold bond to OH cannot be drawn.
- Balance: draw_figure names a missing by-product and does not draw it, but it still draws the step (rendered.png shows the arrow and product). The first-step by-product (ClHO) is a brief-level decision: the brief lists no balanced by-product for the two-stage route. The earlier claim that draw_figure "draws nothing" for this step was wrong. The report that names ClHO is not in this folder, so it could not be re-checked.
- Layout: the first draft was 518 pt wide (budget 504 pt) and a + sign was crowded. One automatic relayout did not clear either issue (checks_passed false), and rendered.png is that relayout output. So the delivered figure does not pass the layout checks.

## Audit

Audited against reference.png, rendered.png, brief.json and the org_lett card, with pixel measurements of the blue-grey silyl colour and visual zoom checks of the labels and reagents.

Overclaims corrected in this file:

- Matched count: 6 of 10 is now 5 of 12. The Me row, the conditions row and the silyl colour are not matched.
- Me row: the paper does not write the propyl ends as Me; its R key writes (n-Pr)2N.
- Line breaks: the replica has five lines above and three below, not four and two. The paper has three lines above and two below, plus 2a under the arrow.
- Conditions: the earlier note that the paper's NMP/Ni split is "not reproduced" was wrong. The brief gives that split and the output matches it; only the card rule (reagents above, solvent below) is not what this paper does.
- Balance: draw_figure does draw the step (a missing by-product is named, not drawn). The claim that it "draws nothing" was wrong.
- Substrate layout: draw_figure does have a stacked_plus layout; the gap is the inline_plus choice of this card plus the lack of a no-plus substrate under the arrow.
- Silyl colour was missing from the earlier comparison entirely. The paper's silyl fragment is blue-grey.
- Layout: the rendered output fails the layout checks; this was stated but the earlier table did not reflect it.

Tool gaps missed by the replicator: colour is available through the house style but blocked by the card's null values; no italic option for condition text; no way to keep a condition line whole; no per-bond bold option.

Card issues for this figure (org_lett.json):

- `show_plus_sign: true` and `substrate_layout: inline_plus` conflict with this scheme, where 2a sits under the arrow with no plus (the card's crop 01 observations do not record this placement).
- `substrate_colors` and `new_bond_color` are null, yet this paper's Table 1 (crop 01, same DOI as crops 03, 06, 07) draws the silyl fragment in blue-grey. The card's `#0336FF` is not this crop's colour.
- `arrow_length_over_bond_length: 7.6` disagrees with the card's own crop 01 measurements (172 px arrow over 35 px bond, about 4.9).

Not verified: bold label face, kekule rings and the bold bond to OH were judged visually at 1200 px and 900 px and not measured against the card; the validation.json read-back and the ClHO balance report are not in this folder; the chain length of R was not checked against the paper's R key.
