# jmed_chem-01: J. Med. Chem. Scheme 1, top row (11 to 9)

Source: Baldwin, Ward et al., "Discovery of MDI-114215: a potent and selective LIMK inhibitor to treat fragile X syndrome", *J. Med. Chem.* 2025. DOI: [10.1021/acs.jmedchem.4c02694](https://doi.org/10.1021/acs.jmedchem.4c02694). Licence: CC BY 4.0 (from the house-style card). The reference crop is Scheme 1 of that paper.

Figure type: `reaction_scheme`, style `jmed_chem` (base preset acs1996).

## What is reproduced

The top row of Scheme 1: 4-(chlorosulfonyl)benzaldehyde (11) to sulfonamide aldehyde 12 (step a), reductive amination to the benzylamine 13 (step b), and acylation to the amide 9 (step c). Arrows carry only the lower-case letters, there are no conditions on the drawing, compound numbers are bold and centred under each structure, and everything is black. Reagents and conditions were not given in the brief because the paper keeps them in the footnote.

Structures were written from the crop and checked with RDKit (molecular formulas: 11 C7H5ClO3S, 12 C13H11NO3S, 13 C20H20N2O2S, 9 C24H26N2O3S). OCSR was not run. The acyl group of 9 is read from the crop as butanoyl (C(=O)CH2CH2CH3).

| Structure | SMILES |
| --- | --- |
| 11 | `O=Cc1ccc(cc1)S(=O)(=O)Cl` |
| 12 | `O=Cc1ccc(cc1)S(=O)(=O)Nc1ccccc1` |
| 13 | `C(c1ccccc1)NCc1ccc(cc1)S(=O)(=O)Nc1ccccc1` |
| 9 | `CCCC(=O)N(Cc1ccccc1)Cc1ccc(cc1)S(=O)(=O)Nc1ccccc1` |

The brief also contains 14 (`CCCCNCc1ccc(cc1)S(=O)(=O)Nc1ccccc1`) and 10 (`CCCCN(Cc1ccc(cc1)S(=O)(=O)Nc1ccccc1)C(=O)c1ccccc1`), which are used only in the attempted full-scheme layouts. The shipped `brief.json` contains only the top row.

## Attempts

1. Full scheme, five steps (11 to 12, 12 to 13, 12 to 14, 13 to 9, 14 to 10): refused by draw_figure, "The steps are not a linear route, a convergent route (arms that merge) or a set of reactions from one starting material".
2. Divergent test from 12 alone (12 to 13 to 9 and 12 to 14 to 10): refused with the same message.
3. Same brief with `"layout": "divergent"`: refused with the same message.
4. Top row only, default `max_width` 504: drawn, but the row wraps onto three rows (11 to 12 on the first, 12 to 13 on the second, 13 to 9 on the third).
5. Top row, `max_width` 720: drawn, but 9 wraps to a second row.
6. Top row, `max_width` 1000: drawn on one row. This is the shipped replica (`rendered.png`, `brief.json`).

## Replay

```
python skill/chemdraw/scripts/cdx.py py skill/chemdraw/assets/house-styles/jmed_chem/replica/jmed_chem-01/replay.py NEW_DIR
python skill/chemdraw/scripts/cdx.py render NEW_DIR/figure.cdxml
```

`replay.py` reads `brief.json` next to it and writes `figure.cdxml` and `validation.json` into a new folder.

## Convention check

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| lower-case step letter above each arrow, no conditions on the drawing | a, b, b, c, c | a, b, c (top row only), with no footnote to key them | no |
| reagents and conditions in a footnote, not drawn | footnote "Reagents and conditions" | not drawn; scheme kind has no footnote field | no |
| yields not on the drawing | none shown | none drawn | not exercised (the crop has no yields, so nothing was tested) |
| bold compound numbers centred under each structure | 11, 12, 13, 14, 9, 10 bold | 11, 12, 13, 9 bold, centred | yes |
| series written as 87a: R1 = H under the generic structure | not in this crop | not exercised | not exercised |
| black only | black | black | yes |
| Kekule aromatic rings | Kekule | Kekule | yes |
| compound label face bold, colour #000000 | bold, black | bold, black | yes |
| arrows about three bond lengths, filled triangular head | about 2.7 bond lengths (card, measured on the crop; card median 3.0); about 2.4 on reference.png by pixel run | about 4.5 to 5 bond lengths on rendered.png (arrow 101 px, phenyl about 36 px wide); filled head | no |
| bond length over cap height 2.25 (card measured block) | 2.25 (card, measured on the crop) | not measured; no figure.cdxml in the folder | not verified |
| line width 0.07 of bond length (card measured block) | 0.07 (card, measured on the crop) | not measured | not verified |
| abbreviations (card: Boc, CF3) | none in this crop | none drawn | not exercised |
| arrow style plain | plain | plain | yes |
| multistep routes in rows with branch arrows carrying a letter | rows, with a vertical b arrow from 12 to 14 | single row; branch missing | no |
| top-level: substrate_layout inline_plus, plus sign, abbreviated groups | no plus or abbreviated group in this crop | not exercised | not exercised |

Matched 5 of 9 exercised conventions (the first draft said 8 of 10). Not matched: the step letters without their footnote key, the missing footnote, the arrow length, and the branch. Line weight and bond-to-cap proportion were never measured and count as not matched.

## Differences from the paper

- Only the top row (11 to 12 to 13 to 9) is drawn. The lower branch, 12 to 14 (step b, vertical arrow) and 14 to 10 (step c), is missing. The crop shows it, and the tool cannot lay it out (see Tool gaps).
- The "Reagents and conditions: (a) ... (b) ... (c) ..." footnote is not drawn. The scheme kind has no footnote field.
- Reagents (aniline, benzylamine, butylamine, benzoyl and butanoyl donors) are not drawn, as in the paper. Each step is therefore reported as not balanced (three warnings, nothing added).
- The row is drawn at `max_width` 1000 pt to keep four structures on one line. The default 504 pt wraps it into three rows.
- Arrow length was first judged by eye. A pixel measurement of the PNGs (see Audit) shows the replica arrows are about twice the reference's length in bond lengths.
- The acyl group of 9 is read from the crop as butanoyl; it was not checked against the paper's text.

## Tool gaps

- draw_figure cannot lay out a route that branches at an intermediate. 11 to 12 followed by 12 to 13 to 9 and 12 to 14 to 10 is refused with "not a linear route, a convergent route (arms that merge) or a set of reactions from one starting material". The same happens when 12 is the start. The divergent layout only handles single-step products from one starting material.
- The scheme kind has no footnote field. Only the scope kind accepts `footnotes`, so "Reagents and conditions: (a) ..." cannot be drawn.
- Steps whose reagents are not drawn raise a balance warning every time, with no way to mark them as reagent-free by convention. The drawing is not changed, but the warnings are noise for letter-keyed schemes.
- The default row budget (504 pt) at the house bond length (14.4 pt) wraps four structures onto three rows; the card gives no row-width guidance.
- The readback count `structures_drawn` changed for the same four species (6 at 504 pt, 5 at 720 pt, 4 at 1000 pt). Each run reported `missing: []` and `unexpected: 0`, so the readback passed, but the count is not explained.
- Each draw took about 200 to 280 s even though every structure was given as SMILES and no network was needed.
- The house card's measured geometry (arrow_length_over_bond_length 3.0, line_width_over_bond_length 0.07, bond_length_over_cap_height 2.25) is not applied by any drawing path. It is read only by the card loader (publication/house_styles.py) and its test. draw_figure has no arrow length or line width input, and the scheme convention path (figure_house.apply_house_conventions) drops it silently, with no entry in the skipped list.
- The convention arrow_style plain is not read by the drawing code either, so that match rests on inspection of the output.
- The folder has no validation.json or figure.cdxml, although replay.py writes both. The skipped-convention record, the balance warnings and the structures_drawn readback cannot be checked from the folder.

## Audit

Checked on 2026-11-07 by viewing reference.png and rendered.png, measuring them by pixel run (PIL), and reading the toolkit code (figure_draw.py, figure_house.py, publication/house_styles.py). The RDKit formulas in this file were re-run and match.

Overclaims found and corrected in the table:

- Arrow length "about three bond lengths: yes" was not true. The replica arrow is 101 px against a phenyl ring about 36 px wide (bond length about 21 px), about 4.5 to 5 bond lengths. The reference arrow is 48 to 50 px against a ring about 35 px wide, about 2.4 bond lengths. The card median of 3.0 is not reached. The "yes" was an eyeball claim, and the card's measured arrow length is not applied by any code (see tool gaps).
- Step letters "yes" overstated the match. The card defines the letters as keys to the footnote "Reagents and conditions", which is not drawn, so the letters are unkeyed.
- Yields "yes" was vacuous. Neither the crop nor the replica has yields, so nothing was tested.
- Arrow style plain stays matched on inspection (plain line, filled head), but nothing in the toolkit reads the convention.
- Line weight and bond-to-cap proportion were not measured at all. They are now listed as not verified.
- Confirmed on inspection: bold compound numbers (replica labels sit within about 1 px of each structure's bounding box; reference labels within about 5 px), black only (no chroma in either image), Kekule rings, bold label face with colour #000000.
- The attempts log (three rows at 504 pt, 200 to 280 s per draw, readback counts 6, 5 and 4) cannot be verified from this folder, which lacks the validation output.

Corrected matched count: 5 of 9 exercised conventions (was 8 of 10). Matched: compound label face bold, label colour black, black only, Kekule rings, arrow style plain (inspection only).

Tool gaps the replicator missed:

- The card's measured geometry (arrow length 3.0 bond lengths, line width 0.07, bond to cap height 2.25) is not applied by any drawing path, and draw_figure has no arrow length or line width input. The scheme path drops it silently.
- arrow_style is not read by the drawing code.
- The replicator's record of skipped conventions and warnings is not in the folder (no validation.json, no figure.cdxml), so the drawing cannot be audited for stroke widths or arrow geometry beyond the PNG.
