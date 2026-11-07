# jmed_chem replica: Scheme 5, top row, series a (87a to 57)

Source: Baldwin, Ward et al., "Discovery of MDI-114215: a potent and selective LIMK inhibitor to treat fragile X syndrome", *J. Med. Chem.* 2025. DOI: [10.1021/acs.jmedchem.4c02694](https://doi.org/10.1021/acs.jmedchem.4c02694). Licence: CC BY 4.0. Reference crop: `evidence/jmed_chem-02.png` (copied as `reference.png`).

Style: `jmed_chem` house style (base preset `acs1996`), figure type `reaction_scheme`.

## What is reproduced

The first row of the scheme, series a only: benzaldehyde (`87a`) is converted by step a into the secondary amine `88a` (`C1CC1CNCc1ccccc1`), and step b gives the benzamide `57` (`O=C(c1ccc(cc1)S(=O)(=O)Nc1ccccc1)N(CC1CC1)Cc1ccccc1`). Only the letters a and b are drawn above the arrows, as in the paper. The series b members (`87b`, `88b`, `71`) are not drawn, and neither is the second row of the scheme. The generic structures are drawn with concrete members (`R1 = H, A = C`), so the series definitions are not shown.

The brief is `brief.json`; the render is `rendered.png` (downscaled from the 2143 px ChemDraw PNG to 1200 px wide).

## Convention check

Rows were checked against both PNGs at higher zoom and against the toolkit source. Measurements on the 1200 px render are approximate (about plus or minus 10 percent).

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| compound numbers bold, black | bold 87a, 88a, 57 under each structure | bold Arial 87a, 88a, 57 under each structure | yes |
| only a lower-case step letter above each arrow | a above step 1, b above step 2 | a, b above the arrows | yes |
| reagents and conditions in a footnote, not on the drawing | the footnote is outside the crop; the letters are the only key | letters drawn, but no footnote; a reaction_scheme brief has no footnotes field (only scope panels do), so the key a, b cannot be given | no |
| yields not on the drawing | no yields in the crop, so this cannot be tested | none drawn | not tested |
| series written as 87a: R1 = H, A = C under the generic structure | bold number, then a plain R-group line under each structure | no series line; only the a member is drawn | no |
| plain arrow with filled triangular head | filled head | filled head | yes |
| arrow length about 3 bond lengths (card 3.0) | about 2.5 on a rough measure of reference.png (arrow about 43 px at 900 px, bonds about 17 to 19 px); card gives 2.7 to 3.0 | arrow about 168 px against bonds about 34 px in rendered.png, about 5 | no |
| multistep route laid out in a row | one row, three structures | one row at max_width 600; at the default 504 the second step wrapped to a second row. The 600 pt width is wider than the 504 pt double-column default; the journal scheme width is not known, so the width is unverified | yes (one row) |
| Kekule aromatic rings | Kekule | Kekule | yes |
| Arial or Helvetica labels | Arial-like | acs1996 Arial, bold for compound numbers | yes |
| black only, no colour or shading | black | black | yes |
| bond length / cap height 2.25 | card 2.25 (paper 85 px over 37 px) | acs1996 preset: 14.4 pt bond over 10 pt Arial, cap height about 7.2 pt, ratio about 2.0; render: about 34 px bond over a 16 px digit, about 2.1 | no |
| line width / bond length 0.07 | card 0.07 (paper 6 px over 86 px) | acs1996 preset: 0.6 pt over 14.4 pt, 0.042; render: arrow shaft ink about 1.2 px over about 34 px bonds, about 0.035; reference shaft about 1.0 to 1.4 px over bonds of about 17 to 19 px | no |
| vertical or diagonal branch arrows | none in this row | not drawn | n/a |
| plus sign between partners | none in this row | not drawn | n/a |
| Boc and CF3 abbreviated | none in this row | not drawn | n/a |

Matched 7 of 12 testable conventions (the yields row is not testable, and the three rows marked n/a are excluded). The earlier claim of 10 of 12 is not supported; see the Audit section below.

## Differences from the paper

- The series b members (87b, 88b, 71) are missing. The generic structure with A = N and R1 = F cannot be drawn in the same figure as the a members, and two disjoint routes in one brief are refused by the tool (see Tool gaps).
- The second row of the scheme (89a to 92) is not drawn.
- The generic ring atom A and the substituent R1 are not drawn as variables. The replica benzaldehyde is an unsubstituted benzene ring, and the ring in the paper has the A position drawn as a labelled vertex.
- The arrows are about 5 bond lengths long, where the paper uses about 2.5 to 3.
- The line-to-bond and label-to-bond ratios differ from the paper (see the table): the replica lines are about half as heavy relative to the bonds, and the labels are slightly larger relative to the bonds.
- The amine reactant for step a and the acid reactant for step b are not in the crop, so the tool reports both steps as not balanced (missing C4H9N and C13H9NO3S). Nothing was added to the drawing, which matches the paper, where these reagents are not drawn. This run record is not in the case folder, so the message is not checked here.
- The scheme footnote with the reagents and conditions is not in the crop, so no footnote is drawn, and the tool cannot draw one for a reaction_scheme.

## Tool gaps

- Generic structures: species take a SMILES or a name only. There is no way to draw a variable ring atom (A = C or N) or an R group (R1 = H or F) as one structure labelled with a series. The replica must pick one concrete member per structure. Wildcard or SMARTS atoms were not tested.
- Two disjoint routes in one brief are refused with "The steps are not a linear route, a convergent route (arms that merge) or a set of reactions from one starting material, so they cannot be laid out" (render/route_graph.py). The series a and b pair from one row cannot be drawn together.
- House-style geometry is stored but never applied, and nothing is reported as skipped. `jmed_chem.json` has a `measured` block (arrow_length_over_bond_length 3.0, line_width_over_bond_length 0.07, bond_length_over_cap_height 2.25). No code in the toolkit reads that block, and `style.skipped` does not list it. The house docstring says invalid cards are never silently skipped, but these values are silently dropped.
- Arrow length cannot be set from the brief. The keys are kind, species, steps, max_width, title, style and layout. Without a value in the brief, the arrows come out about 5 bond lengths long.
- Line width and label size cannot be set from the brief either. The drawing uses the acs1996 preset (line 0.6 pt over a 14.4 pt bond, label 10 pt), so the line and cap-height ratios of the card are not reproduced.
- Footnotes: a reaction_scheme brief has no footnotes field. The house convention puts the reagents in a footnote ("Reagents and conditions: (a) ...; (b) ..."), so the letters above the arrows have no key. Only the scope kind takes footnotes.
- Labels: the species label is a single plain string (render/schema.py, StructureRef.label: str). The series line (bold 87a, then plain "R1 = H, A = C") needs mixed bold and plain runs, and R1 needs a superscript. Neither can be expressed in a label. The replicator test with a longer label was not run.
- Atom labels: species accept no text label on a ring vertex or a substituent position. The A ring vertex and the R1 substituent in the paper cannot be placed.
- Default max_width 504 wraps a three-structure row with two arrows. The brief needed max_width 600 to keep one row, which is wider than the double-column default, so the journal width is a separate open question.
- ChemDraw COM returned resource_busy after 295 seconds on the first linear attempt; the retry succeeded. This is a runtime issue, not a figure issue. No log is in the case folder, so it is not checked here.

## Replay

```
python skill/chemdraw/scripts/cdx.py py skill/chemdraw/assets/house-styles/jmed_chem/replica/jmed_chem-02/replay.py NEW_DIR
python skill/chemdraw/scripts/cdx.py render NEW_DIR/figure.cdxml
```

`replay.py` runs `draw_figure` on `brief.json` and writes `figure.cdxml` and `validation.json` in a new folder.

## Audit

An audit on this case corrected the table above. The original claims that did not hold:

- The count of 10 of 12 did not match its own table. The table had 9 "yes" rows out of 11 scored rows, and the two measurable rows (bond/cap and line/bond) were excluded as "not measured". The preset and card values differ on both, so they are "no", not unknown. The corrected count is 7 of 12 testable rows.
- The footnote row was marked as a match, but no footnote is drawn and the tool has no footnote field for a reaction scheme.
- The yields rows were marked as matches, but the source crop has no yields, so they test nothing.
- The arrow numbers "295 px against about 55 px" do not match rendered.png, which measures about 168 px against about 34 px (about 5 bond lengths). The conclusion (arrows about twice the length in the paper) stands.
- The house card measured values are never read by code, a silent drop that the first draft did not report. This is added to Tool gaps.
- The 600 pt width is wider than the 504 pt double-column default. The journal width is not in the case, so this is unverified.
- Not checked from this folder: the resource_busy event and the "both steps not balanced" message. No validation.json, log or run record is in the folder. Running the replay would regenerate validation.json.
