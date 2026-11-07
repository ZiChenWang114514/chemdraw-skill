# OpenStax Chemistry Figure 20.3: an alkane in three notations (house style replica, partial, not rendered)

Source: Flowers, Theopold, Langley, Robinson et al., *OpenStax Chemistry* (2015), section 20.1 Hydrocarbons, Figure 20.3. DOI not given on the card. Licence: CC BY 4.0. Reference crop: `reference.png` (copy of `evidence/openstax_chemistry-07.png`).

Drawing style: the `openstax_chemistry` card (base preset `chemdraw_slide`), figure type `structure_panel`, crop 07. The brief names the house style, but a scope panel takes only the base preset, so no house convention is applied to the drawing.

## What is reproduced

Only the skeletal structure of the molecule, captioned "Skeletal structure" underneath in Arial. The molecule is 3-ethyl-2-methylhexane (C9H20), SMILES `CCCC(CC)C(C)C`, checked with RDKit. The structure was read by eye from the crop: a six-carbon chain with a methyl on the second carbon and an ethyl on the third, which agrees with the crop's condensed formula CH3-CH(CH3)-CH(CH2CH3)-CH2-CH2-CH3. The molecule's name is not printed in the figure. OCSR was not run.

Not reproduced: the expanded formula (every C and H written, bonds at 90 degrees) and the condensed formula (text). draw_figure cannot draw either; see Tool gaps.

The drawing is `kind: scope` with one species and no values (`brief.json`). It was drawn as an unrendered draft (see Attempts).

## Convention check (card against crop 07)

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| structure_panel: one molecule in several notations side by side | expanded, condensed and skeletal of one alkane side by side | skeletal only | no |
| each notation captioned underneath in plain Arial | three captions, "Expanded formula", "Condensed formula", "Skeletal structure", in Arial, each centred under its structure on one shared baseline | one caption, "Skeletal structure", Arial 8 pt (CDXML font 1001), left-justified at x 22 pt under the left part of the structure (structure spans x 32 to 162 pt); the text is about 60 percent of the crop's size relative to the bond (see bond/cap row) | no |
| expanded formula with every C and H written | 9 C and 20 H drawn | not drawn; the explicit H atoms of the SMILES are dropped when the structure is grounded | no |
| bonds at 90 degrees in the expanded formula | all bonds horizontal or vertical | not drawn; skeletal zigzag has 120 degree angles | no |
| skeletal structure drawn as a plain zigzag | straight six-carbon zigzag at about 30 degree bonds, one methyl straight up at C2, ethyl straight down at C3, no atom labels | 120 degree angles and no atom labels, but the chain bonds are at about 18 and 42 degrees, the C2 end is a V of two methyls at the top, and the ethyl runs to the right; the principal chain is not drawn straight | no |
| condensed formula as plain text | CH3-CH(CH3)-CH(CH2CH3)-CH2-CH2-CH3 in Arial with stacked CH2 and CH3 | not drawn; no text item in a scope panel | no |
| compound label colour #000000 | black | black (CDXML colour is black; the house style is not applied, so this is the default) | yes |
| label font Arial or Helvetica | Arial-like | Arial (face only; the size is covered by the caption row) | yes |
| species named, not numbered | captions name the notation, no numbers | caption names the notation, no number; the molecule is not named in either figure, and the card's naming convention is for reaction crops, so the convention is not shown | no |
| variation colour (card null) | all black, no coloured groups | all black | yes |
| line width / bond length 0.042 (top level) | card value 0.042; card measurement 2.5 px over 55 px (0.045); crop pixels give a line about 2 px over a bond about 38.5 px (about 0.05) | 1.6 pt over 30 pt (0.053), in the same range as the crop pixels | no (against the card value only) |
| bond length / cap height 3.35 (top level) | crop pixels: bond about 38.5 px over cap height about 12 px (about 3.2); card measurement 55 over 17 px | no atom labels; the only text is the caption, and 8 pt Arial (cap height about 0.72 em) over a 30 pt bond gives about 5.2, so the text is about 40 percent smaller relative to the bond than in the crop | no |
| arrow length 2.5 bond lengths (top level) | no arrow in crop 07 | no arrow | n/a |

Claimed: 9 rows (the card's structure_panel signature features and its top-level colour, font, naming, line width and bond/cap measurements). The skeletal zigzag, condensed formula and variation colour rows are visible in the crop but are not card claims, so they are not counted. Matched: 2 (colour, label face). Both are default values, not applied house conventions. Not matched: 7 (structure_panel, captions, expanded formula, 90 degree bonds, line width, bond/cap ratio, species naming). See Audit.

## Differences from the paper

- Two of the three notations are missing. The panel shows the skeletal structure only.
- The tool adds a "Substrate scope" heading above the panel. The paper has no heading.
- Bonds are 1.6 pt wide on a 30 pt bond (0.053). The crop's bonds are about 2 px on about 38.5 px (about 0.05), so the weight is close to the crop's. It is the card's 0.042 value that differs, and that value rests on a bond length the crop does not show.
- The caption is left-justified under the left part of the structure. In the crop the three captions share one baseline and each is centred under its structure.
- The replica's zigzag is tilted (bonds at about 18 and 42 degrees; the crop uses about 30 degrees). The replica structure is about 2.3 bond lengths tall; the crop's skeletal structure is about 3.0.
- The caption "Skeletal structure" matches the paper's wording, but the panel has no second or third caption to compare.
- Nothing was rendered natively, so the look (antialiasing, label rendering) has not been compared. The comparison here uses the CDXML regenerated for this audit (see Audit).

## Attempts

1. Two species: the expanded formula from explicit-H SMILES and the skeletal structure. The `--render` run exceeded the 300 s tool limit, and the retry with `--render` exceeded its 290 s limit. An unrendered draft of the same brief completed. Its CDXML has 18 atoms and 16 bonds, which is two 9-carbon skeletons, so the expanded entry was drawn as a second copy of the skeletal structure. The expanded formula was dropped.
2. One species, skeletal only, and `title: ""`. The unrendered draft completed on the third call; the call before it timed out while ChemDraw was busy. The "Substrate scope" heading is still present: `figure_scope.py` uses `brief.get("title") or "Substrate scope"`, so an empty title falls back to it. A single space as the title removes the heading (see Audit). This is the drawing that `brief.json` describes.

No `rendered.png` was produced.

## Tool gaps

- No structure-panel kind. `kind: scope` is the nearest. It adds a title ("Substrate scope"); an empty title does not remove it, but a single-space title does. It also packs compounds in a grid rather than a notation row.
- Explicit hydrogens are removed when a SMILES is drawn, so an expanded formula with every C and H cannot be drawn from SMILES. draw_figure has no option to keep explicit hydrogens. Confirmed by a probe: a 9-carbon SMILES written with explicit [H] atoms drew 9 atoms and 8 bonds.
- No control over bond angles or orientation. The chain angle is fixed at 120 degrees by the preset, and the layout chooses the orientation and principal chain (the replica's bonds are tilted off the 30 degree lattice; the crop's are not). The scope keys (species, fields, conditions, footnotes, title, width_mm, height_mm) include nothing for either, so the 90 degree geometry of the expanded formula cannot be requested.
- No text-only item in a scope panel, so the condensed formula cannot be drawn as the typeset text in the crop. The publication_figure manifest has text objects, but no panel-level way to place them from draw_figure.
- House conventions are not applied to scope panels ("house conventions apply to schemes only"), so the line width of the card (0.042 of the bond length) cannot be set. The preset gives 1.6 pt on a 30 pt bond. The scope panel also keeps its own text size (`figure_scope.py`: "The panel keeps its own text size"), so the caption size cannot be set from the brief.
- Caption placement: the caption is always left-justified at a fixed offset, so there is no way to centre a caption under its structure or to put all captions on one baseline.
- Native rendering was unavailable in this session: two `--render` calls timed out, and ChemDraw processes from other runs were open. The tool gave no way to wait for the lock.

## Card issues (not fixed here)

- The structure_panel signature "one molecule shown in several notations side by side" fits crop 07. The card's own observation text for crop 08 describes three different butene isomers with notations stacked in columns, which does not fit that feature. Crop 08 was not opened for this replica.
- The card's crop 07 measurements do not match the crop. A connected-component scan of `reference.png` (dark threshold 140) gives carbon glyphs about 38.5 px apart, bonds about 2 px wide and cap height about 12 px. The card's `bond_length: 55` and `cap_height: 17` are therefore not the crop's values, and `line_width: 2.5` over 55 px is not what the crop shows either. The bond/cap ratio (about 3.2) is close to the card's 3.35, so the ratio may be right while the absolute values are not. The card's 0.042 line-width ratio rests on the same wrong bond length.

## Audit

Checked against `reference.png`, `brief.json`, the card JSON and a draft regenerated offline from `brief.json` with `replay.py`: `replay_audit_fresh/figure.cdxml/page-001.cdxml`. Two probes (single-space title; explicit-H SMILES) are in `audit_probe/out_075349`. Nothing was rendered natively.

- Overclaims: the rows marked yes for the zigzag and species naming were wrong, the caption row was marked partial when it is a no, and the bond/cap row was marked not measured when the caption text can be measured against it (about 40 percent off). The zigzag is tilted and the principal chain is not straight; the caption is off-centre and about 60 percent of the crop's relative size; the naming convention is not shown.
- Matched count: 2 of the 9 counted rows (colour, label face), both default values rather than house conventions.
- The line-weight "heavier" claim is not supported by the crop's pixels.
- Tool gap "title key cannot suppress the heading" is wrong for a single-space title.
- Confirmed: explicit H dropped; the 1.6 pt / 30 pt preset; Arial 8 pt caption; black colour; empty title falls back to "Substrate scope".
- Missed tool gaps: no control of orientation or principal-chain choice; no control of caption size or justification/position in a scope panel.
- Not verifiable from this folder: the attempt timings, the 18-atom two-species draft, and the `--render` timeouts. No logs or CDXML for those attempts are present, and no `rendered.png` exists.
