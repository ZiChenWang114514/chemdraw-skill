# rsc_journals, Scheme 6: representative drug amides (upper reaction only)

Source: M. Freiberg et al., Chem. Sci. 2023, 14, 3462, DOI [10.1039/d3sc00198a](https://doi.org/10.1039/d3sc00198a). Scheme 6 (representative drug amides). Licence: CC BY 3.0, as recorded on the card (`skill/chemdraw/assets/house-styles/rsc_journals/evidence/rsc_journals-03.png`). The citation and licence were taken from the card and were not checked against the article.

Figure type: `reaction_scheme`. The card has no `figure_types` key at all, so no per-figure section exists for this crop; the top-level conventions were used.

Drawing style: `rsc_journals` (base preset `rsc`). Brief: `brief.json` in this folder (try 3 of 3). Rendered with desktop ChemDraw, then downscaled to 1200 px wide for `rendered.png`.

## What is reproduced

The upper reaction of the scheme, on the grey panel: a carboxylic acid R-CO2H with DPDTC (1.05 equiv, neat, 3 to 6 h, 60 °C) gives the S-(2-pyridyl) thioester (drawn in the paper in square brackets as an intermediate), which reacts with a secondary amine R1R2NH in EtOAc (2 M), 60 °C, 3 to 6 h, to the amide. The paper's "1.05 equiv" on the amine is not drawn: the brief has no text above the second arrow.

Structures in the brief, with R groups as generic stand-ins (the crop's R, R1 and R2 are generic labels, so no real structure is implied):

- acid: `OC(=O)*`
- intermediate: `O=C(*)Sc1ccccn1`
- amine: `*N*`
- amide: `O=C(*)N(*)*`

Not reproduced: the lower row (27, 28, 29: sonidegib, imatinib and a tubulin inhibitor with yields, footnotes a and b, and green captions). It is a product-only row with no substrates in the crop, so it does not fit a `draw_figure` step, and the `scope` panel does not give the parenthesised yield after the label or the green captions. The grey panel and the black rule under it are also not drawn.

## Table

Rows are the conventions the card claims for this figure type (top level, non-null or a label rule) and the other conventions visible in the crop. The card-claimed rows are marked "card". Checked by zooming both images; the rendered check used `rendered.png` at 4x and pixel measurements on the 1200 px render.

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| compound label face, bold (card) | upper scheme has no compound numbers, so the convention cannot be tested on this reaction; the lower row labels are plain (the card's own Scheme 6 observation says "plain (not bold)") | no labels drawn | no (not testable here; the card's top-level `bold` conflicts with its own Scheme 6 evidence) |
| compound label colour, black (card) | black numbers on the lower row; none in the upper reaction | no labels drawn | not tested |
| conditions split, reagents above and solvent or conditions below (card) | step 1: DPDTC (1.05 equiv) above; neat, 3-6 h, 60 °C below. Step 2: 1.05 equiv on the amine, no text above the arrow; EtOAc (2 M), 60 °C, 3-6 h below | step 1: same split, but range written "3 to 6 h". Step 2: no text above the arrow, the 1.05 equiv is missing | no |
| abbreviated groups OMe, CF3, OCF3 (card) | not testable: R is generic in the upper reaction; the lower row shows MeO, OMe and F3CO | no groups drawn | not tested |
| Kekule rings (card) | pyridine ring in the thioester drawn with alternating double bonds | pyridine drawn Kekule (checked at 4x) | yes |
| reagent text colour, black (card) | black | black | yes |
| plain arrow (card) | plain solid arrows with filled heads | plain solid arrows with filled heads | yes |
| plus sign between substrates (card, show_plus_sign true) | no plus sign: the amine is stacked above the second arrow | "+" between the thioester and the amine | no |
| new bond red and thicker, #F40405 | C-N bond of the amide red and bold | black | no |
| grey header panel with black rule below | pale grey panel behind the upper reaction; black rule under it | no panel, no rule | no |
| intermediate in square brackets | square brackets around the S-pyridyl thioester | plain structure, no brackets | no |
| amine placed above the arrow | R1R2NH stacked above the second arrow | inline substrate with "+" | no |
| generic labels R1 and R2 | R1 and R2 (superscripted) on the amine and amide N | generic R on every position | no |
| orientation of acid, amide and pyridine | acid: R at left, C=O up, OH to the right; pyridine N at the top of the ring; amide N central, C=O at the right | acid: HO at left, C=O down, R up-right (mirror); pyridine rotated, N at the left; amide mirrored | no |
| amine N-H geometry | N with H drawn below it, R1 up-right, R2 down-right | "NH" written inline, R above and below | no |
| "2 M" unit | M set smaller than the figures around it | M set at normal size | no (no control found in the brief) |
| label font | card says Arial; the `rsc` preset sets label font Helvetica | not separately checked; the two faces are not distinguishable at this resolution | not tested |
| line width / bond length | 2 px / 48 px = 0.042 at the crop scale; a 2 px line is only good to about +/-1 px, so the ratio is good to about +/-50% (card mean 0.046) | `rsc` preset LineWidth 0.45 pt / BondLength 12.2 pt = 0.037. The earlier "0.60 pt" is not in the preset. Pixel check on `rendered.png`: about 1.3 px line on a 36 px bond = 0.036 | approximate only (consistent within the crop's measurement error; not counted) |
| label size / bond length | cap height 29 px, bond 48 px, bond/cap = 1.66 (card mean 1.91) | LabelSize 7 pt, bond 12.2 pt. Pixel check on `rendered.png`: cap height about 15 px, bond about 36 px, bond/cap about 2.4 | no (replica labels smaller relative to bonds) |
| arrow length / bond length | arrow 1: 317 px = 6.6 bonds (card: 317 px). Arrow 2: about 390 px = about 8 bonds (visual estimate from the crop; the replicator did not record it) | arrow 1 about 7.3 bonds (7.5 by pt); arrow 2 about 9.5 bonds (9.8 by pt), measured on `rendered.png` | no |

Counts: `matched` is the number of "yes" rows: 3 of 20 table rows (Kekule rings, reagent text colour, plain arrow). `claimed` is the number of rows whose convention the card claims (8: label face, label colour, conditions split, abbreviated groups, Kekule rings, reagent text colour, plain arrow, plus sign). Of the claimed rows, 3 match (Kekule, reagent colour, plain arrow). The line-width row is approximate and not counted, and the conditions-split row is now "no".

## Differences from the paper

- The bold-versus-plain labelling cannot be checked on the upper reaction, but the lower row in the same crop uses plain labels, which contradicts the card's top-level `compound_label_face: "bold"`.
- The amine's "1.05 equiv" is missing from the replica.
- The new C-N bond is black in the replica; the paper's is red and bold.
- The grey panel and the black rule are missing.
- The thioester intermediate is not in square brackets.
- The amine is an inline substrate with a "+" sign; the paper stacks it above the arrow with no plus, and draws the N-H with H below the N.
- Generic labels are R for all positions; the paper uses R, R1 and R2.
- The acid, the amide and the pyridine ring are mirror-image or rotated relative to the paper (HO on the left, N on the left of the amide, pyridine N on the left).
- The conditions text reads "3 to 6 h" in place of "3-6 h", because the hyphen form renders with the 6 superscripted (see Tool gaps).
- Arrow lengths are longer than in the paper: 7.5 and 9.8 bonds (by the replicator's pt values) against 6.6 and about 8 in the paper.
- Labels are proportionally smaller than in the paper.
- The lower row (27, 28, 29) and its green captions and yields are not drawn.
- The paper file found at `D:\workspace\chemdraw-papers\house-rsc-1\p.pdf` is Cen et al., Chem. Sci. 2024 (DOI 10.1039/d4sc05429f), not Freiberg et al. 2023, so the Scheme 6 source could not be checked against its full text. This was not re-checked in the audit.

## Tool gaps

- `draw_figure` has no option to place square brackets around an unisolated intermediate by default. The double dagger is the default `superscript` of a species-level `ts_bracket`, but that dict also accepts `superscript` and `bracket_type` (`toolkit/cdxml_toolkit/mcp_runtime/figure_draw.py`, `_apply_decorations`). An empty `superscript` may give square brackets without a dagger. This was not run for this crop. A step-level `ts_bracket` given as a dict is silently ignored, since only a species id, a list or a boolean are read.
- A substrate cannot be placed above the arrow. The step `above` and `below` fields are plain strings attached to the arrow (`_step_descriptors`); `substrate_layout` is card-only, and a reagent structure above the arrow is not supported.
- No shaded header panel or horizontal rule can be drawn behind or under a scheme. `highlight_fill` covers ring interiors only. The card key `background_fill` appears in the house-style vocabulary for `graphical_abstract` and `setup_diagram`, but no code applies it (`APPLIED_FIGURE_CONVENTIONS` lists only `mechanism` and `catalytic_cycle`), so even a card entry cannot give this panel.
- Generic groups are drawn only as `R`. There is no numbered R1, R2 label with superscript, and generic atoms are refused by the balance check (the report says the balance could not be checked). Not run in the audit.
- Atom orientation is fixed by the tool's layout. Changing the SMILES atom order did not flip the acid (HO at the left) or the amide (N at the left); no orientation control exists in the brief. Not re-run in the audit.
- Text problem for numeric ranges: a range such as `3-6 h` (ASCII hyphen) renders with the 6 superscripted, and `3–6 h` (en dash) renders as a superscript minus with a subscript 6. The workaround used is `3 to 6 h`. The cause is not confirmed: `text_formatting.py` has no rule that superscripts a digit after a hyphen (its subscript rule needs a letter before the digit), so the effect is probably ChemDraw interpreting "-6" as a charge or count. This was not re-rendered in the audit.
- New-bond colour and weight are card-only (`new_bond_color`, read in `figure_house.py`). The card has it null and the brief has no key for it, so the red bold C-N bond cannot be drawn for this crop even though the crop shows it.
- No arrow-length control in the brief. The brief reads only `kind`, `style`, `species`, `steps`, `max_width`, `layout` and `title`, so arrow length follows the text width, which gives about 7.5 and 9.8 bonds here.
- No bond-length or line-width control in the brief. Both come from the preset (`rsc`: BondLength 12.2 pt, LineWidth 0.45 pt, LabelSize 7 pt).
- The `rsc` preset sets label size to 7 pt, while the card's `atom_label_size_pt_estimate` is 7.9 pt. The house style does not override label size, so the labels come out relatively smaller than in the paper.
- Scope panels cannot place a parenthesised yield after a label (`27 (94%)`) or a coloured caption (green drug names), so the lower row cannot be reproduced with the current tools.
- Missed by the replicator: a label placed beside a substrate (for example the amine's "1.05 equiv") has no place in the brief, so the text was dropped rather than reported.
- Missed by the replicator: step text is plain strings with no run-level formatting. Only automatic formula subscripts and italic nomenclature prefixes are applied (`text_formatting.py`). Small-cap "M" in "2 M" and superscript labels in text cannot be made.
- Missed by the replicator: no control of N-H hydrogen display or placement on a stacked amine. The "NH" is inline here, and the paper draws the H below the N. Not tested, including whether an explicit H in the SMILES changes the drawing.
- Missed by the replicator: the card's label font (Arial) and the `rsc` preset's label font (Helvetica) disagree, and the house style cannot override the font.

## Audit

Audited against both images and the card (`toolkit/cdxml_toolkit/publication/house_styles/rsc_journals.json`). The replicator's "5 of 8" claim mixed denominators: 5 was the count of "yes" rows, which included the line-width row (not a card-claimed convention) and the conditions-split row, which does not hold. The corrected count is 3 of the 8 card-claimed conventions (Kekule rings, reagent text colour, plain arrow). Overclaims corrected in this file: the conditions-split row (step 2 has no text above the arrow, the amine's 1.05 equiv is missing, and the step 1 range differs), the "What is reproduced" paragraph (it described the amine's equiv as reproduced), the line-width row (the stated 0.60 pt is not in the `rsc` preset; the preset gives 0.45 pt, which is consistent with the crop only within its measurement error), the arrow-length row (the paper's second arrow was not recorded), the "figure_types: {}" statement (the card has no such key), and the tool-gap list (the ts_bracket dagger is configurable; the text-tidying cause is unconfirmed; several gaps were missed). Rows were added for the amine N-H geometry, "2 M", and the label font. The generic-label, orientation, balance, and replay checks were not re-run.
