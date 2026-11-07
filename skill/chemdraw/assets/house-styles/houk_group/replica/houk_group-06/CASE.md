# Galeotti, Houk, Bietti et al. 2023: HAT and OH-rebound mechanism (Scheme 2)

Source: Galeotti, Houk, Bietti et al., "Radical and cationic pathways in C(sp3)-H bond oxygenation by dioxiranes", *J. Am. Chem. Soc.* **2023**. DOI: [10.1021/jacs.3c07163](https://doi.org/10.1021/jacs.3c07163).

Licence: CC BY 4.0. Reference crop `reference.png` is `evidence/houk_group-06.png` from the house-style card.

House style: `houk_group` (base preset ACS Document 1996). Figure type: `mechanism` (card). The crop is a one-line scheme with no curved arrows, so the replica uses the scheme drawer (`kind` default), not `kind: "mechanism"`.

## What is reproduced

The one-line mechanism of Scheme 2: R-H plus a dioxirane gives an alkyl radical (HAT step) and a hydroxy alkoxy radical, and the two recombine (OH rebound) to give R-OH and a ketone. The crop uses generic R, R' and R'' groups. The replica uses concrete stand-ins:

- R-H = cyclohexane, `C1CCCCC1` (species 1)
- dioxirane = dimethyldioxirane, `CC1(C)OO1` (species 2)
- alkyl radical `[CH]1CCCCC1` (drawn between the steps, not labelled)
- hydroxy alkoxy radical `OC(C)(C)[O]` (drawn between the steps, not labelled)
- R-OH = cyclohexanol, `OC1CCCCC1` (species 3)
- ketone = acetone, `CC(C)=O` (species 4)

Both steps are atom-balanced (C6H12 + C3H6O2 = C6H11 + C3H7O2; C6H11 + C3H7O2 = C6H12O + C3H6O). The labels 1 to 4 are added by the replica. The crop has no compound labels.

Files: `brief.json` is the final brief (`layout: "linear"`, `max_width: 720`). `rendered.png` is the ChemDraw render of that brief, downscaled from 2495 px to 1200 px wide. `replay.py` is copied from the jacs-au case, with a new docstring; it was not re-run for this case.

## Attempts

1. `figure-1` (first brief, no layout key, `max_width` 504): ChemDraw render written, but the two steps are drawn in one line with the step 1 products repeated as step 2 substrates, and the radical dots are missing.
2. `figure-2` (`layout: "linear"`, `max_width` 720): same single line with repeated substrates, same missing radical dots. This is the saved `rendered.png`.
3. A third try was not made: the remaining gaps (radical dots, step pills, one-row layout) do not respond to brief changes.

The first run without a thread limit failed with OpenBLAS memory errors and a worker crash. Retrying with `OPENBLAS_NUM_THREADS=1` succeeded.

## Convention table

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| arrow_style plain | plain line with open arrowhead | plain line with open arrowhead | yes |
| show_plus_sign true | "+" between substrates and between products | "+" between substrates and products | yes |
| substrate_layout inline_plus | reactants side by side with plus | same | yes |
| reagent_text_color black | step text black | black | yes |
| arrow_length_over_bond_length 6.2 (card) | about 97 px including head (x 166 to 263 in the 765 px crop); the CASE figure of 80 px and 80 / 16 = 5.0 are not reproduced | about 144 px over a bond of about 33 px = 4.2 to 4.4 bond lengths (rendered.png) | no (replica shorter than the card value) |
| no curved arrows (mechanism) | none | none | yes |
| radicals drawn as dots (mechanism signature) | dot on the alkyl carbon and on the O of the hydroxy alkoxy radical | `Radical="Doublet"` is written to the CDXML, but no dot is visible; R• reads as unchanged cyclohexane and the hydroxy alkoxy radical reads as a closed species | no |
| step name in rounded pill on the arrow (mechanism signature) | HAT in pale cyan pill, OH rebound in pale green pill | "HAT" and "OH rebound" as plain text above the arrows | no |
| pill fill #E0FFC3 / #DAFFF7 (mechanism highlight) | two pill fills | not drawn; top-level highlight_fill is null | no |
| one-line route | one row, R-H to ROH in a single line | one line (1200 x 100 px), but step 2 redraws cyclohexane and the hydroxy alkoxy radical as new substrates, so the step 1 products appear twice | no |
| line_width_over_bond_length 0.09 (card) | about 1 px over 16 px = 0.06 (CASE crop figures) | about 2 px over about 33 px = 0.06 | not verified (counted as not matched) |
| bold compound labels (top level) | not shown in this crop | labels 1 to 4 added in bold | n/a |
| bond_length_over_cap_height 2.4 (card) | 16 / 7 = 2.3 (CASE); by my reading the "R" and "O" glyphs are about 11 px tall, so this ratio is not reproduced | digit labels about 8 to 10 px tall on bonds of about 33 px = 3.3 to 4.1 | no |
| abbreviate_groups (Ts, Ph, CF3, tBu) | none in the scheme (generic R, R', R'') | none (methyl and cyclohexyl written out) | n/a |
| yield placement and conditions placement | none in the scheme | none | n/a |

## Differences from the paper

- The paper uses generic R, R' and R'' groups. The replica uses cyclohexane and dimethyldioxirane, so the substituent pattern is concrete.
- The paper has no compound labels. The replica adds bold labels 1 to 4.
- The paper's step names sit in coloured pills. The replica writes them as plain text.
- The paper's radicals carry dots. The replica's radicals are drawn without visible dots, so R• and the hydroxy alkoxy radical read as closed-shell species. The CDXML stores the radical state, but the render does not show it.
- The paper's route is one line. The replica is also one line, but step 2 redraws the step 1 products as its own substrates, so the same two species appear twice in the row.
- The paper draws the two radicals as separate species joined by a plus sign (R• + HO-C(R')(R'')-O•), with no cage, and the replica does the same. An earlier draft called the paper's intermediate caged; the crop does not show that.

## Tool gaps

- Radical dots: `Radical="Doublet"` is written to the CDXML (`cdxml_builder.py`) but not visible in the ChemDraw PNG. Whether the render or the attribute placement drops it was not isolated.
- Step-name pills: `above` text cannot take a rounded, filled background.
- One-row routes: the drawer cannot link a product of one step to a substrate of the next. It redraws the shared species as new substrates in the same line (rendered.png). `layout: "linear"` does not change this.
- Generic R groups: no way to draw R, R' or R'' placeholders from SMILES.
- Arrow length and proportions: the card's `measured` block is never read by the drawing code, so `arrow_length_over_bond_length`, `line_width_over_bond_length`, `bold_width_over_bond_length` and `bond_length_over_cap_height` are all unapplied. The drawn arrow is about 4.2 to 4.4 bond lengths.
- Label size: the drawer takes the ACS 1996 label constants (`ACS_LABEL_SIZE`), not the card's cap-height ratio.
- Runtime: a draw can fail with OpenBLAS memory errors unless `OPENBLAS_NUM_THREADS=1` is set. The toolkit does not set this variable and `replay.py` does not set it either, so a re-run needs the caller to set it.


## Audit

Second-pass audit (2026-11-07) against `reference.png` (765 x 60 px), `rendered.png` (1200 x 100 px), `brief.json` and the card `toolkit/cdxml_toolkit/publication/house_styles/houk_group.json`. Lengths are pixel extents read from the PNGs, accurate to about 10 %. The ChemDraw CDXML was not available, so the radical attribute could only be checked from the PNG and the card code.

- The first draft's "5/9 matched" does not match its own table. The table has 12 judged rows: 5 matched, 6 not matched, 1 not verified (3 further rows are n/a). Corrected count: 5 of 12.
- `rendered.png` is one line, not two rows. The defect is repeated species, not a row split.
- The replica arrow is about 4.2 to 4.4 bond lengths, not 5.0. The reference arrow is about 97 px including its head, not 80 px. The claim that the card value disagrees with the crop is therefore not established by these numbers; the replica is short of the card value either way.
- Label-to-bond proportion was marked n/a but is measurable: about 3.3 to 4.1 in the replica against 2.4 on the card, so it is not matched. The reference "R" and "O" glyphs are about 11 px tall by my reading, not 7 px, so the crop ratio of 2.3 is not reproduced.
- The paper's intermediate is not caged (see Differences).
- The radical row is correctly "no", but the replica's R• reads as ordinary cyclohexane, which is a misrepresentation to flag, not only a missing feature.
- Tool gaps added: the card's `measured` block is never read by the drawing code; labels take the ACS constants; no species reuse across steps; the OpenBLAS variable is not set in the toolkit or in `replay.py`.
- Not verified: the OpenBLAS failure (replay not re-run), the radical attribute in the ChemDraw output, the figure-1 and figure-2 outputs (not in the case folder), and the 2495 px original size.
