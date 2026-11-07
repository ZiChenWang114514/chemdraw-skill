# USPTO patent: Table 1, example 1-1 (structure panel, not rendered)

Source: Lanman et al. (Amgen), US 10,519,146 B2, 2019 (KRAS G12C inhibitors and methods of using the same), Table 1, entry 1-1. No DOI; the patent number is the identifier. Licence: public domain (US patent), as recorded in the house-style card.

Figure type: `structure_panel` (house-style card, `uspto_patents`, base preset `j_mol_mod`). Crop: `evidence/uspto_patents-03.png`, copied here as `reference.png`.

## What is reproduced

The caption `TABLE 1` and the single example compound of entry 1-1 with its plain example number. The table rules and the header row (Ex. #, Chemical Structure) are not reproduced; no drawer in the toolkit can draw them. The compound is drawn with `kind: "scope"` (one species, no fields), which is the only panel type that takes a structure with a label and a title.

Structure (read from the crop by eye; the DECIMER API, one engine, returned the same canonical SMILES):

- SMILES in brief.json: `C=CC(=O)N1CCN(CC1)c1snc2c(F)c(-c3cc(O)ccc3Br)c(Cl)cc12`
- RDKit canonical: `C=CC(=O)N1CCN(c2snc3c(F)c(-c4cc(O)ccc4Br)c(Cl)cc23)CC1`, C20H16BrClFN3O2S
- Reading: acryloyl piperazine on C3 of a 2,1-benzisothiazole (S bonded to C3, N bonded to C7a), F on C7, Cl on C5, 2-bromo-5-hydroxyphenyl on C6.

## Replica status

Not rendered. Desktop ChemDraw did not return for any file in this session: `cdx.py draw ... --render` (300 s tool timeout), `cdx.py draw` without render (killed after 276 s with worker_crashed, exit 143), and `cdx.py render` on the scope page and on a known-good JACS Au scheme (both killed at the timeout with worker_crashed, exit 143). The scope drawer itself, called directly in the toolkit runtime without render, completed in a few seconds with data binding and chemistry checks passed, so the stall is in the render/worker path. Several ChemDraw.exe processes without window titles were running at the time; they were not stopped. Because no render exists, the comparison below uses the page manifest and the crop measurements, not pixels.

Brief iterations: one brief (brief.json, `kind: scope`, `style: uspto_patents`). No second brief was drawn, because the failures were in the worker and renderer, and the brief has no field that changes 2D orientation, table rules or label position, so a changed brief could not have fixed the differences listed below.

replay.py runs offline and reproduces the draw (checked, exit 0). For `kind: scope` the output path is a folder, so replay.py writes `figure.cdxml/` (page-001.cdxml, manifest, project.json, checks.json) rather than a single file.

## Convention check

Crop measurements are from the card (300 dpi page scan, bond 64 px, cap height 21 px, line 3 px). Replica values come from a fresh offline replay of this case (replay.py, exit 0): page-001.cdxml and page-001.manifest.json give Times New Roman 8 pt for the title and labels, face 0, colour index 3 (black), bond 14.4 pt, line 0.6 pt, title Justification Left at (16, 24). No rendered image of the replica exists, so every replica-side value is from the file, not from pixels.

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| TABLE 1 caption in capitals | `TABLE 1`, plain serif | `TABLE 1`, Times New Roman 8 pt, face 0 | yes (text and case; size see next row) |
| caption size against table text | cap height 22 px against 17 px for the table text (Ex. #, 1-1), about 1.3 times | title 8 pt, the same size as the labels | no (added in audit) |
| caption centred above the table | centred over the rules (centre about x = 490 px, rules span 108 to 874 px) | left-justified at x = 16 pt (`Justification="Left"`) | no |
| thick black rules above and below the header | two thick rules, about 4 px against 2.5 px for bonds | not drawn; scope panels have no rules | no |
| header row Ex. # / Chemical Structure | present | not drawn | no |
| example number plain | `1-1`, plain Roman | `1-1`, face 0 (plain), Times New Roman 8 pt | yes |
| example number at the row start, above the structure | in the Ex. # column, about 215 px left of the structure and about 70 px above its top | below-left of the structure (label at y = 138.7 pt in the regenerated manifest) | no |
| one example compound per row | one structure in a table row | one structure, no table row exists | no (was yes) |
| no highlighting of varied substituents | none | none; the only colour used is index 3 (black), no highlight objects | yes |
| stereo shown by bold wedges, italic (S) and P descriptors | none in this crop | not applicable | n/a |
| black line art, no colour or shading | black only | black only (colour table: index 2 white, index 3 black) | yes |
| Times serif atom labels | Times | Times New Roman (font 1001) | yes |
| bond length over cap height, 3.0 | 3.05 on the card; 3.0 to 3.4 on the crop (depends on the bond measured) | 14.4 pt bond over about 5.3 pt cap height (8 pt estimated from font metrics), about 2.7 | no (was approx; outside the paper range) |
| line width over bond length, 0.047 | 0.047 on the card; about 0.044 to 0.05 on the crop | 0.6 / 14.4 = 0.042 | approx (not counted) |
| bold width over bond length, 0.2 | no bold in this crop | not applied (scope takes the base preset only) | n/a |
| scheme titles centred and underlined | not applicable: this is a table caption, not a scheme title | not applicable | n/a (was no) |
| structure in justified two-column text with margin line numbers 5, 10, 15 | partial margin numbers visible at the right edge; body text outside the crop | no body text, no line numbers | no |
| molecule proportions and orientation | about 7.5 to 8.6 by 9.5 to 10.9 bond lengths (430 by 544 px on the crop; tall; piperazine vertical; acryloyl top-left) | 11.0 by 4.6 bond lengths (158.6 by 65.9 pt from the CDXML atom coordinates; flat) | no |

Counts: 15 convention rows apply (3 n/a excluded: stereo, bold width, scheme title). Matched: 5 (caption text, plain example number, no highlighting, black line art, Times labels). Approx and not counted: 1 (line width over bond length). Not matched: 9. The earlier count of 6 of 15 is withdrawn; see the Audit.

## Differences from the paper

- The table furniture is missing: no thick rules above and below the header, no header row, and no column captions.
- The caption is left-justified, not centred.
- The example number sits below the structure, not above it at the row start.
- The molecule is laid out by RDKit 2D coordinates, so it is flat and wide (10.8 by 4.2 bond lengths), while the paper's drawing is tall (about 7 by 9). The piperazine and acryloyl orientation therefore differ from the paper.
- The margin line numbers and the justified body text of the two-column page are absent.
- The house-style conventions (label face and colour, bold width) are not applied: the scope report states that house conventions apply to schemes only.
- The bond length and line width sit close to the card values (about 2.7 against 3.0 for bond over cap height, 0.042 against 0.047 for line over bond), but this is estimated from font metrics and the manifest, not from a rendered image.

## Tool gaps

- No table furniture: a scope panel cannot draw thick horizontal rules above and below a header row, a header row of column captions, or a structure-only table of rows.
- The scope title is always left-justified at (16 pt, 24 pt); there is no justification or underline option for it.
- Scope panels apply only the house style's base preset; the card's label, colour and bold-width conventions are skipped for structure panels.
- Label placement is fixed (below the structure); there is no option to place the example number above the structure at the row start or in a column.
- No orientation control: species records take SMILES or names only, with no 2D coordinates or orientation option, so the depiction follows RDKit and cannot be matched to a journal's layout.
- No body text, justified two-column text or margin line numbers in any figure type.
- Desktop ChemDraw rendering did not return for any file in this session (worker_crashed, exit 143), including a known-good scheme, and `cdx.py draw` without render also hung for the scope brief while a direct call to the same drawer succeeded in seconds. Native checks could not be run.

## Audit

Audited on 2026-11-07 against reference.png (identical to evidence/uspto_patents-03.png, 900 by 896 px) and an offline replay of this case into a temporary folder. The replay exits 0 and gives the values quoted above. Checks: data_binding and chemistry passed, layout passed (font metrics and bounds only), native_preview not_run. No replica pixels exist, so the replica column is file-based.

Corrections to the table:

- Scheme title row: not applicable, since the paper's caption is a table caption, not a scheme title. It was counted as a failed comparison.
- One compound per row: no. The replica has one structure but no table row, so the row convention is absent.
- Bond over cap height: no. The replica's 2.7 is an estimate from font metrics. On the crop the paper gives about 3.0 (vertical ring bond about 50 px over a 17 px N cap) to 3.4 (piperazine N to N about 114 px over two bonds over the same cap). 2.7 is outside that range, so "approx" overstated it.
- Caption size: added. The paper's TABLE 1 has a cap height of 22 px against 17 px for the table text, about 1.3 times. The replica title is 8 pt, the same as the labels, so the size does not match. The table was not flagging this.

Corrections to the text:

- The example number is not "above the top-left of the structure". It sits in the Ex. # column, about 215 px left of the structure's left edge and about 70 px above its top.
- Replica geometry: the regenerated manifest gives the label at y = 138.7 pt (not 133), and atoms spanning 158.6 by 65.9 pt, 11.0 by 4.6 bond lengths (not 156 by 60 pt, 10.8 by 4.2). The conclusion stands: the replica is flat and wide against the paper's tall layout.
- Font sizes: figure_scope.py pops font_size from the j_mol_mod preset ("the panel keeps its own text size"), so the title and labels are 8 pt where the preset gives LabelSize 10 and CaptionSize 10. The 8 pt value is the panel default, not the house value. "Only the base preset" in Differences and Tool gaps is therefore incomplete.
- Proportions: the paper structure spans about 430 by 544 px on the crop, which is about 7.5 by 9.5 bond lengths at 57 px, or 8.6 by 10.9 at 50 px. "About 7 by 9" is a fair but low estimate.
- Line width over bond length: the crop gives about 0.044 to 0.05 against the card's 0.047, and the replica gives 0.042. Close, but not counted.

Checked and correct: the SMILES reads the image correctly (S bonded to C3 and N, N bonded to C7a, F on C7, Cl on C5, aryl on C6, Br ortho and OH meta on the aryl). The reference shows inner Kekule double bonds. The labels are serif, and no colour or highlight appears.

Tool gaps the replicator missed:

- Caption size is fixed to the label size. The preset's CaptionSize is discarded for scope panels, so the title cannot be set to the paper's larger caption size.
- Label size is fixed at 8 pt. The card estimates 7.5 pt; a bond/cap ratio of 3.0 at a 14.4 pt bond needs about 7.3 pt. There is no per-panel label-size option.
- No pixel comparison is possible here: the render path did not return, so the replica column rests on file values. The render crash is an environment fault, not a drawing gap. This audit did not retry the render and did not reproduce the cdx.py draw hang; the offline replay completed.
