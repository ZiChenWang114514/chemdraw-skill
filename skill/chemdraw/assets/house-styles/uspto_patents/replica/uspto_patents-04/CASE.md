# uspto_patents replica: crop 04 (structure panel, Table 1 compounds 1 to 5)

## Source

- Hadida-Ruah et al. (Vertex), US 9,732,080 B2, 2017 (Modulators of ATP-binding cassette transporters), Table 1.
- Licence (from the house-style card): public domain (US patent).
- The card's evidence entry for this crop says "compounds 1 to 8". The crop image shows five compounds, so the replica follows the image (see Differences).

## Figure type

structure_panel (the card lists crops 03, 04 and 09 for this type).

## What is reproduced

The five example compounds of the panel, one per row, drawn with the house-style base preset through `cdx.py draw` with `kind: "scope"`. The table caption, header rules and the number column are not reproduced, because the scope kind cannot express them.

Structures (read by eye from the crop, parsed with RDKit; no OCSR run):

- 1: `O=C(Nc1ccc2cc[nH]c2n1)C1(CC1)c1ccc2OCOc2c1`
- 2: `COc1ccc(cc1)C1(CC1)C(=O)Nc1ccc2[nH]c(cc2n1)C(C)(C)C`
- 3: `COc1ccc(cc1)C1(CC1)C(=O)Nc1cnc2[nH]c(cc2c1)C(C)(C)C`
- 4: `COc1cccc(c1)C1(CC1)C(=O)Nc1ccc2[nH]c(cc2n1)C(C)(C)C`
- 5: `COc1cccc(c1)C1(CC1)C(=O)Nc1cnc2[nH]c(cc2c1)C(C)(C)C`

## Convention table

| convention or signature feature | paper | replica | match |
|---|---|---|---|
| TABLE 1 caption, centred above the table | caption is in crop 03, not in crop 04 | none; the brief title " " suppresses the default title | no |
| Thick rules above and below the header row | one thick top rule in crop 04 | no rules | no |
| One compound per row | yes | yes, one per row, but split 4 + 1 over two pages | yes |
| Example number at the right margin | yes | left margin, x about 22 pt | no |
| Single column of five rows | yes | no, two columns on two pages | no |
| No highlighting of the varied ring | yes | yes, no fill | yes |
| Stereo bold wedges with small (S) / P descriptors | not present in these five compounds | n/a | n/a (not counted) |
| Base preset j_mol_mod (top level) | not verifiable: a patent scan carries no ChemDraw preset | preset j_mol_mod is applied (style.preset); house conventions are not applied (style.applied is empty) | no |
| Bond length about 3.0 x cap height | 62 px bond, 21 px cap (2.95) on the 2560 px scan | 14.4 pt bond; estimated cap about 5.3 pt at 8.0 pt Times, ratio about 2.7 (estimate, not rendered). A rough pixel check on reference.png gives about 3.4 (bond about 58 px, capital N about 17 px), so the gap is not smaller than stated | no |
| Line width 0.047 x bond length | 3 px on a 62 px bond = 0.048; at 300 dpi 3 px is 0.72 pt, not 0.6 pt | 0.6 pt on a 14.4 pt bond = 0.042; the 0.047 target gives 0.68 pt | no |
| Times New Roman atom labels | yes | Times New Roman (font 1001) | yes |
| Atom label size about 7.5 pt | 7.5 pt estimate | 8.0 pt (LabelSize) | no |
| Kekule aromatic rings | yes | yes; page 1 has 32 Order-2 bonds (28 aromatic C=C from four rings of 7 each, plus 4 amide C=O), consistent with Kekule. The earlier figure of 16 was wrong | yes |
| Black only, plain label face | yes | not established. Atom labels use colour index 3, but the file's colortable has two entries (white, black), so index 3 is not defined in it. Atom labels use face 96 (Formula), not 0; face 0 applies only to the example numbers | no |

Matched 4 of 13 counted conventions (the stereo row is excluded; the earlier count of 7 of 14 counted a 14th row that does not exist and kept three rows that do not hold). See the Audit.

## Differences from the paper

- Layout: the paper stacks five rows in one column with the number at the right margin. The replica at 90 x 240 mm puts four compounds on page 1 and one on page 2. Column count follows the panel width; a narrower brief to get one column was not tested.
- Caption and rules: none drawn. The scope kind adds "Substrate scope" as a title when the brief title is empty; a single space suppresses it.
- Number placement: example numbers sit at the left margin, not the right.
- Bond to cap ratio: about 2.7 in the replica (estimated from LabelSize 8.0 pt) against 2.95 in the paper. Bond length is 14.4 pt against about 14.9 pt in the paper (62 px at 300 dpi), within about 3 percent.
- Not rendered: no native ChemDraw image was produced, so the comparison is from CDXML attributes and estimates, not from pixels.
- Structures were read by eye. The positions of the pyridine nitrogen and the methoxy groups were not checked by OCSR.

## Tool gaps

1. The scope kind applies only the base preset. The card's structure_panel conventions (caption, header rules, number side, label size) have no parameter. The evidence JSON reports style applied [] and skipped house conventions.
2. An empty title falls back to "Substrate scope" (figure_scope.py line 140, `brief.get("title") or "Substrate scope"`). Only a whitespace title suppresses it, and there is no explicit no-title option.
3. No single-column control. Column count follows the panel width.
4. No control of the example-number side. Labels are placed at the left margin.
5. No table drawing: no caption, no header row, no ruled lines.
6. Label size is fixed by the base preset (8.0 pt). The card estimate is 7.5 pt, and the card value is not passed to scope.
7. `--render` did not return within the 300 s tool limit in two attempts (desktop ChemDraw busy), so there is no native preview and no rendered.png.
8. Run time without render varied from about 7 s to about 5 min, close to the 300 s tool limit.

## Attempts

| try | brief | call | result |
|---|---|---|---|
| 1 | brief.json v1: 80 x 110 mm, title "" | draw scope, no render | ok, 4 pages (2, 1, 1, 1); title "Substrate scope" added |
| 2 | brief_v2.json: 90 x 240 mm, title " " | draw scope, --render | timed out at 300 s (ChemDraw busy) |
| 3 | brief_v2.json | draw scope, --render, retry | timed out at 300 s |
| 4 | brief_v2.json | draw scope, no render | ok, 2 pages (4 + 1), checks passed, readback 5/5, lint clean |
| 5 | brief_v2.json | draw scope, no render, retry | ok, 2 pages (4 + 1) |

The case brief.json is brief_v2.json. replay.py redraws it offline into a new output folder (`replay.py NEW_OUTPUT_DIRECTORY`). rendered.png was not produced.

## Audit

Checked against reference.png, brief.json, the house-style card (`toolkit/cdxml_toolkit/publication/house_styles/uspto_patents.json`) and the replica CDXML. The audit redrew brief.json offline into a temporary folder (`replay_audit/panel`): 2 pages, 4 + 1 compounds, readback 5/5, as the attempts table says. No rendered image exists, so no visual claim below is verified by pixels.

Overclaims corrected in the table above:

- Count: "7 of 14" is now 4 of 13. The stereo row is excluded, which leaves 13 counted rows, and three of the seven former "yes" rows do not hold.
- Base preset "yes": a patent scan carries no ChemDraw preset, so the comparison is not possible. The style record shows house conventions were not applied (style.applied is empty), so the preset alone is not house style.
- Line width "yes": at 300 dpi, 3 px is 0.72 pt, not 0.6 pt. The replica's 0.6 pt on a 14.4 pt bond is 0.042 of the bond length, not 0.047 (0.047 gives 0.68 pt).
- Black, plain face "yes": the replica CDXML colortable has two entries (white, black). Atom labels use colour index 3, which that table does not define, so black is not established. Atom labels use face 96 (ChemDraw Formula style), not 0; face 0 is used only for the example numbers.
- Kekule "16 double bonds": page 1 has 32 Order-2 bonds (28 aromatic C=C from four rings of 7 each, plus 4 amide C=O). Kekule still matches; the count was wrong.
- Bond to cap ratio: a rough pixel check on reference.png (900 px wide) gives about 3.4, not 2.95. The replica's estimated 2.7 is therefore further from the paper than the CASE implies. Still "no".
- The attempts row "checks passed, readback 5/5, lint clean": the validator checks data binding, RDKit consistency, readback and lint only. None of these compares the card's conventions, so "checks passed" says nothing about house-style match.

Rows that hold: one compound per row (on each page, with the layout gap in its own row); no highlighting (no fill in either page's CDXML); Times New Roman (font 1001 is "Times New Roman" in the font table; not rendered); Kekule (count corrected above).

The caption row is "no" but the caption is not in crop 04 at all (it is in crop 03), so that row is not a fault of the replica for this crop. The thick rule above the structures is present in the reference, as the CASE says. The reference also has a second column of small numerals at about x 898 px beside the example numbers. Their meaning is not established from the crop and the CASE does not mention them.

Tool gaps the replicator missed:

- Colour defect in the toolkit: the scope output writes atom labels with colour index 3 against a two-entry colortable (white, black). This is a bug in the output, not only a missing parameter.
- No way to set atom labels to a plain face; scope writes face 96 (Formula).
- Line width is fixed by the preset at 0.6 pt. The card's line_width_over_bond_length (0.047) and bond_length_over_cap_height (3.0) are neither passed nor enforced.
- Aromatic display (Kekule) comes from the default; the card's aromatic_rings setting is not passed.
- The card's colour fields (compound_label_color, reagent_text_color) are not passed to the drawing.
- No measurement or reference-comparison step. Every match claim can only come from CDXML attributes and estimates, so pixel-level house-style checks are impossible with these tools.
- The validation output (checks, lint, readback) has no house-convention check, so a "passed" result can be read as a style match when it is not.
- Pagination: the page size fixes the split (4 + 1 at 90 x 240 mm); there is no option to keep all rows on one page or to set a page height independently of the brief.
