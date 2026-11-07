# Polymer Chemistry: RAFT copolymerisation, block extension and hydrolysis (Scheme 1, rows A to C; crop 03)

Source: Konkolewicz et al., *Polym. Chem.* **2026**, "Vinyl ether maleic acid block copolymers for tunable lipid nanodiscs". DOI: [10.1039/d5py00767d](https://doi.org/10.1039/d5py00767d).

Licence: CC BY 3.0 (as recorded in the house-style card `polymer_chemistry`). Reference crop reproduced under that licence.

Drawing style: the `polymer_chemistry` house style (base preset `rsc`); figure types `reaction_scheme` and `polymer`.

## What is reproduced

Scheme 1, rows A to C, as drawn in the paper:

- Row A: RAFT agent (dodecyl trithiocarbonate with a 2-propanoic acid leaving group), maleic anhydride and butyl vinyl ether, AIBN, 4 hours, 65 °C, giving the RAFT adduct drawn as one monomer-unit representative. The paper also uses dodecyl vinyl ether, which is not drawn.
- Row B: that adduct with n-butyl acrylate, AIBN and 65 °C above the first arrow, 12 hours below it, then NaOH and 50 °C, 12 hours, giving the carboxylate block copolymer.
- Row C: the same adduct with tert-butyl acrylate, AIBN and 65 °C above the first arrow, 12 hours below it, then NaOH and 50 °C, 12 hours, giving the product with the tert-butyl ester retained.

Each polymer is drawn as one representative unit per monomer (no repeat brackets, no n). The paper's rows B and C carry round brackets with m and n subscripts, and the paper's bold row letters, monomer colour coding, bold product names and the R = list are not drawn (see the table).

The five steps cannot be one `draw_figure` brief: the tool refuses a route with several starting materials feeding a shared intermediate, and it refuses two-step branches from one starting material. Each row is therefore drawn from its own brief, and the three renders are stacked into `rendered.png`.

## Structures

| ID | SMILES (in brief files) | Note |
| --- | --- | --- |
| CTA | `CCCCCCCCCCCCSC(=S)SC(C)C(=O)O` | RAFT agent read from row A; C16H30O2S3 |
| MA | `O=C1C=CC(=O)O1` | maleic anhydride; C4H2O3 |
| BuVE | `C=COCCCC` | butyl vinyl ether; the paper also uses dodecyl vinyl ether (not drawn) |
| PA | `OC(=O)C(C)CC(OCCCC)C1C(=O)OC(=O)C1SC(=S)SCCCCCCCCCCCC` | row A adduct, R = C4H9 only; C26H44O6S3 |
| BuA | `C=CC(=O)OCCCC` | n-butyl acrylate |
| PB | `OC(=O)C(C)CC(OCCCC)C1C(=O)OC(=O)C1CC(C(=O)OCCCC)SC(=S)SCCCCCCCCCCCC` | row B block extension, one BuA unit; C33H56O8S3 |
| PBh | `OC(=O)C(C)CC(OCCCC)C(C(=O)[O-])C(C(=O)[O-])CC(C(=O)[O-])SC(=S)SCCCCCCCCCCCC` | row B after NaOH; ring opened, ester hydrolysed; drawn as carboxylate anions without Na+ |
| tBA | `C=CC(=O)OC(C)(C)C` | tert-butyl acrylate |
| PC | `OC(=O)C(C)CC(OCCCC)C1C(=O)OC(=O)C1CC(C(=O)OC(C)(C)C)SC(=S)SCCCCCCCCCCCC` | row C block extension; C33H56O8S3 |
| PCh | `OC(=O)C(C)CC(OCCCC)C(C(=O)[O-])C(C(=O)[O-])CC(C(=O)OC(C)(C)C)SC(=S)SCCCCCCCCCCCC` | row C after NaOH; tert-butyl ester kept |

All SMILES were checked with RDKit (formulas above). Row A balances: CTA + MA + BuVE gives C26H44O6S3, and the draw report says balanced. The row B and C hydrolysis steps do not balance as drawn: the tool reports missing O on the reactant side, because NaOH, water and butanol are not in the brief and nothing is added to the drawing.

## Files

- `brief.json`: the full five-step brief. It is refused by `draw_figure` (kept to show the refusal).
- `brief_rowA.json`, `brief_rowB.json`, `brief_rowC.json`: the three briefs that were drawn. Their condition text is "4 hours, 65 °C" (row A), and "12 hours, 65 °C" with "50 °C, 12 hours" (rows B and C).
- `replay.py`: draws the three row briefs offline into a new folder. It ran successfully through `cdx.py py`. No replay output is in this case folder.
- `reference.png`: copy of the crop.
- `rendered.png`: the three ChemDraw renders (rows A, B and C) stacked by hand into one 1200 px image. Its condition labels do not match the briefs (see Audit), and no CDXML source for it is in this folder.

## Replication

```
python skill/chemdraw/scripts/cdx.py py skill/chemdraw/assets/house-styles/polymer_chemistry/replica/polymer_chemistry-03/replay.py NEW_DIR
```

## Convention table

Claimed rows are the card's conventions for this crop (top level and the `polymer` / `reaction_scheme` sections). Unclaimed rows are visible in the crop but the card does not claim them for crop 03. The match column is the reviewer's check against `reference.png` and `rendered.png`.

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| arrow style plain (top level) | plain arrows | plain arrows (style applied) | yes |
| reagents above arrow, conditions below (conditions_split) | row A: AIBN above, "4 hours 65 °C" below. Rows B and C: AIBN and 65 °C above the first arrow, "12 hours" below; NaOH above, "50 °C 12 hours" below | row A: AIBN above, "12 h, 65 °C" below (wrong time). Rows B and C: 65 °C below the AIBN arrow and "50 °C, 12 h" below NaOH. The brief places 65 °C below, so rows B and C differ from the paper | no |
| inline plus between substrates (substrate_layout) | "+" inline in rows A, B and C | "+" inline | yes |
| plus sign shown, bold (show_plus_sign) | bold plus; strokes look heavier than the replica's at zoom | regular weight; `show_plus_sign=true` only records the setting and sets no weight | no |
| reagent text black (reagent_text_color) | black | black in colour; the paper sets reagent and condition text in bold, the replica in regular weight | yes (colour only) |
| end groups drawn explicitly (polymer) | RAFT dodecyl trithiocarbonate and CH(CH3)COOH end; R = C4H9 / C12H25 on the ether oxygen | same RAFT ends drawn; R drawn as C4H9 only, no list | yes (RAFT ends only) |
| repeat unit in round brackets with n or m subscript (polymer) | round brackets crossing the backbone with m and n subscripts in rows B and C | one unit each, no brackets, no subscript | no |
| monomer colours carried into product segments (polymer, crop 03) | CTA olive, MA blue, VE red, BA magenta | all black | no |
| bold uppercase row letters A, B, C (reaction_scheme, crop 03) | bold A, B, C | not drawn | no |
| bold dark-red product labels (top-level observations, crop 03) | VEMA-block-AA and VEMA-block-tBA/AA | not drawn | no |
| AIBN as text above the arrow | AIBN above arrow | AIBN above arrow | yes (not claimed as a structure) |
| carboxylate anions on ring-opened and ester-hydrolysed product | COO- marks in rows B and C | COO- marks | yes (not claimed) |
| R = list under the product, wavy-bond fragments (not claimed for crop 03) | R = C4H9, C12H25 under row A product | R = C4H9 only, no list | not claimed |
| yield placement and format | no yields in crop 03 | none | not applicable |
| bond length to cap height 2.4 (top level) | not measured for crop 03 in the card | not compared | not measured |
| arrow shaft weight (top level, card line width 0.09 of bond length) | shaft about 2 to 3 px at the 725 px reference width | shaft about 1 px at the 1200 px render width, about three to four times thinner relative to page width | not verified (replica looks thinner) |

Claimed: 10. Matched: 4 (arrow style, inline plus, reagent text colour, RAFT end groups). The earlier count of 6 is withdrawn; see Audit.

## Differences from the paper

- Repeat units: each polymer is one monomer unit per monomer, with no round brackets and no n or m subscripts. The paper's rows B and C draw round brackets crossing the backbone with m and n subscripts.
- Row A: the paper draws both butyl and dodecyl vinyl ether as reagents, and the product carries R = C4H9, C12H25. The replica draws only butyl vinyl ether and R = C4H9, so the row A stoichiometry is not the paper's.
- Colours: the paper colours the CTA olive, maleic anhydride blue, vinyl ether red and butyl acrylate magenta, and keeps the colours in the polymer. The replica is all black.
- Row letters: the paper marks the rows with bold A, B, C; the replica has no row letters, and the three rows are separate drawings.
- Product names: the paper labels the products VEMA-block-AA and VEMA-block-tBA/AA in bold dark red; the replica has no labels.
- Conditions: the paper puts AIBN and 65 °C above the first arrow in rows B and C, with "12 hours" below. The replica puts 65 °C below. The paper writes "hours" in full, and the replica's rendered.png writes "h". The paper sets reagent and condition text in bold; the replica's is regular weight.
- Plus signs: the paper's plus signs look heavier than the replica's regular-weight plus.
- Hydrolysis: NaOH is text only. Na+, water and butanol are not drawn, so the hydrolysis steps are unbalanced in the replica; the paper shows no by-products either.
- Layout: the paper draws the three rows as one scheme with the row A product feeding rows B and C; the replica draws three separate renders stacked by hand.

## Tool gaps

- `draw_figure` refuses a set of steps in which two or more starting materials feed one shared intermediate (row A product into rows B and C). The message is "The steps are not a linear route, a convergent route (arms that merge) or a set of reactions from one starting material".
- `draw_figure` refuses a divergent set in which each branch has two steps from one starting material (PA to PB to PBh and PA to PC to PCh). Only one-step divergence is accepted.
- No repeat-unit notation: round brackets crossing the backbone with an n or m subscript at the lower right. The card's `polymer.repeat_bracket: round` is recorded as skipped guidance.
- No R = list with wavy-bond fragments under the product.
- No monomer or segment colouring: the card leaves `substrate_colors` null, so the style does not apply it, and the brief has no per-species or per-atom colour field (only ring_fills and atom_halos).
- No bold panel letters for stacked rows.
- No free product label (for example a bold dark-red name under the product); labels are compound numbers only.
- Hydrolysis steps: NaOH cannot be given as a species, so the step reports missing O and no by-products are drawn; `checks_passed` is false.
- Width: at the RSC bond length (12.2 pt) every row exceeds the 504 pt budget (735 pt and 690 pt reported). The one automatic re-layout narrowed the budget and the rows wrapped, but `checks_passed` stayed false for all three.
- No tool composes several rows into one figure; the stacked `rendered.png` was built by hand from three renders.
- No face (bold) control for reagent and condition text. `compound_label_face` applies only to compound numbers, and `reagent_text_color` paints colour only, so the paper's bold conditions cannot be drawn.
- No weight control for the plus sign. `show_plus_sign: true` only adds `show_plus_sign=true` to the applied list, so the paper's heavier plus cannot be drawn.
- The draw report lists `show_plus_sign=true` and `reagent_text_color=#000000` under applied, although neither changes weight or face (for black text the colour step does nothing at all). The applied list overstates what the style does.
- Arrow shaft weight was not tested. The toolkit defines arrow weights thin, bond and bold, so a heavier shaft may be possible; this is unverified.

Not a tool gap: the conditions split. `split_conditions` keeps the brief's above and below lines as given, so 65 °C could have been placed above the arrow in rows B and C. The error is in the brief.

## Card observations

- The `polymer.repeat_bracket: round` convention and the round-bracket signature are listed for crops 01, 05 and 06, and the `polymer` section also lists crop 03. Crop 03 does draw round brackets with m and n subscripts in rows B and C, so the card's crop 03 coverage is right and the replica's omission is a real gap.
- The card describes `conditions_split` as "solvent below", but crop 03 puts no solvent below the arrow. It puts time and temperature below, and in rows B and C it puts AIBN and 65 °C above the arrow, which the card's wording does not describe.

## Audit

Checked against `reference.png`, `rendered.png` and the brief files, using zoomed crops of the arrow labels, plus signs and the row B and C products.

Overclaims corrected in the table:

- Conditions split marked "yes" with the evidence "same split as the brief". That check was circular. The paper puts 65 °C above the arrow with AIBN in rows B and C, and the replica puts it below. Marked "no".
- Plus sign marked "yes" although the table itself records a bold plus in the paper. The replica's plus is regular weight. Marked "no".
- Reagent text marked "yes" without a face check. Colour matches; the paper's reagent and condition text is bold and the replica's is not. Marked "yes (colour only)".
- End groups marked "yes" with the R variable omitted. The RAFT ends match; the R = C4H9 / C12H25 variable does not. Marked "yes (RAFT ends only)".
- The paper column for repeat units said "no brackets". The paper's rows B and C do have round brackets with m and n subscripts. The verdict "no" stands; the description was wrong.
- The rendered row A label reads "12 h, 65 °C". The brief and the paper both say 4 hours, so the rendered drawing has a wrong reaction time. The rendered labels in rows B and C use "h" where the briefs say "hours". The toolkit has no rule that I could find that turns "hours" into "h", so this is not explained by the tool, and no source file for `rendered.png` is in this folder.
- The earlier text said row A was "4 h" in the replica. The rendered image does not show that.

Corrected matched count: 4 of 10 claimed rows (arrow style, inline plus, reagent text colour, RAFT end groups). The earlier count of 6 is withdrawn.

Other checks: the yield row is not applicable (no yields in crop 03). The bond-to-cap-height ratio was not measured and is not claimed. Arrow length relative to figure width matches between the reference (about 9.7 percent) and the render (about 9.7 percent), but the row A arrow sits further right in the render. Arrow shaft weight looks thinner in the render and is recorded as not verified.
