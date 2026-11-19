# Glorius group (JACS 2024): reagent synthesis panel (A), Figure 2A

Source: Gutierrez, Glorius et al., *J. Am. Chem. Soc.* 2024 (gamma-Amino alcohols via energy transfer enabled Brook rearrangement), Figure 2A. DOI: [10.1021/jacs.4c01667](https://doi.org/10.1021/jacs.4c01667). Licence: CC BY 4.0 (from the house-style card).

Reference crop: `reference.png` (copy of `evidence/glorius_group-01.png`).

Figure type: `reaction_scheme`. House style: `glorius_group` (base preset `acs1996`).

## What is reproduced

Panel (A), reagent synthesis, as two rows:

- S1 to S3: (i) NaOAc, NaI, DMF, reflux, 12 h above the arrow; (ii) LiAlH4, Et2O, reflux, 1 h below it.
- S3 to 2: (i) triphosgene, Na2CO3, CH2Cl2, 0 °C–rt, 12 h above; (ii) S5, pyridine, CH2Cl2 (0.3 M), 0 °C–rt, 12 h below.

The conditions are copied from the crop. As in the paper, the intermediate of each two-step sequence is not drawn. The row break is produced by the layout (the drawing wraps after S3). No yields appear in this panel, so none are drawn.

Not reproduced: the panel title "(A) Reagent synthesis" with its dashed rule, the dashed box around S5, and the structure of S5 (named in the conditions only).

Structures (SMILES in `brief.json`), read by eye from the crop; no OCSR was run, and RDKit parses all three:

- S1: `ClC[Si](C)(C)[*]`
- S3: `OC[Si](C)(C)[*]`
- 2: `c1ccc(cc1)C(=NOC(=O)OC[Si](C)(C)[*])c1ccccc1`

`[*]` stands for the variable group R. The two aryl groups (Ar) of 2 are drawn as phenyl, a stand-in for the paper's unspecified Ar.

## Replay

```
python skill/chemdraw/scripts/cdx.py py skill/chemdraw/assets/house-styles/glorius_group/replica/glorius_group-01/replay.py NEW_DIR
python skill/chemdraw/scripts/cdx.py render NEW_DIR/figure.cdxml
```

`rendered.png` is the native ChemDraw render of the final brief (attempt 2, `max_width` 440). Attempt 1 (`max_width` 300) was refused by the layout lint (too wide, condition lines broken, `checks_passed` false) and is not kept here.

## Convention table

Rows marked `n/a` are features the crop does not show, so they are not counted. Every other row is counted; `matched` counts the `yes` rows. The Audit section at the end re-checks each row against the images, the CDXML written by the replay and pixel measurements.

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| compound labels bold (S1, S3, 2) | bold | bold (CDXML `face="1"`) | yes |
| compound label colour `#000000` | black | black (CDXML `color="0"`) | yes |
| yield placement `after_product_label`, `{value}%` | no yield in panel | none drawn | n/a |
| conditions split `reagents_above_solvent_below` | (i) above, DMF and reagents in (i); (ii) below, Et2O | (i) above, (ii) below, from the brief; each condition line broken into two lines by the layout lint; card rule skipped | no |
| `substrate_layout` `inline_plus` | no two-substrate step in panel | none drawn | n/a |
| abbreviation `Me` | Me | Me | yes |
| aryl written as Ar (generic) | Ar on S5 and 2 | Ph (stand-in) | no |
| `aromatic_rings` `kekule` | no drawn ring | none drawn | n/a |
| `substrate_colors` (first `#2C0001`, second `#0203FE`) | S1 and S3 entirely blue | S1 entirely `#2C0001` (colour index 10, pixels about (33,0,0)); S3 black | no |
| `highlight_fill` null | none | none | yes |
| `reagent_text_color` `#000000` | black | black (CDXML `color="0"`) | yes |
| `arrow_style` plain | plain, full head | plain, full solid head | yes |
| `show_plus_sign` true | no plus sign in panel | none drawn | n/a |
| `variation_color` `#0203FE` | variable part blue | absent from the colour table; no blue pixel in rendered.png | no |
| signature: variable group blue | S1, S3 and Si(Me)2R of 2 blue | black, except S1 dark red | no |
| signature: aryl/oxime part dark red-brown | Ar of S5 and 2 dark red-brown (pixels about (32,0,0) to (43,4,4)) | black Ph | no |
| signature: (i) and (ii) above and below one long arrow | yes, both rows | yes, both rows | yes |
| signature: dashed rectangle around S5 | present | absent | no |
| panel title "(A) Reagent synthesis", bold italic, dashed rule | present | absent | no |
| two rows, S3 at the end of row 1 and start of row 2 | two rows | two rows; gap between the arrows about 6.6 bond lengths against about 4.5 in the reference (structure matches, spacing does not) | yes |
| bond length to cap height about 2.2 | about 2.2 (reference.png: bond about 21.4 px, cap about 9.8 px) | 14.4 pt bond, 10 pt Arial, cap about 7.2 pt: ratio 2.0 | no |
| arrow length about 13.4 bond lengths | 19.2 (row 1, 412 px over 21.4 px) and about 22 (row 2, 470 px) | 212 pt and 217 pt arrows: 14.7 and 15.1 bond lengths | no |
| line width over bond length about 0.075 (card) | about 0.08 (arrow about 1.8 px over 21.4 px bond) | `LineWidth` 0.6 pt over 14.4 pt bond = 0.042 | no |
| "S5" typeset plain, bold in conditions | bold S5 | S with subscript 5 (face 32), not bold | no |
| condition typography: "0 °C – rt" (spaced dash, tight degree sign) | spaced dash, "0°C" | "0 °C–rt" (no spaces around the dash) | no |

Testable rows: 21 (4 `n/a`). Matches: 8 (compound labels bold, label colour, Me, highlight, reagent text colour, arrow style, (i)/(ii) placement, two-row structure).

## Differences from the paper

- Colour: in the paper S1 and S3 are blue all over (Cl or HO, the CH2, Si, both Me and R). In the replica S1 is dark red (the tool applied `#2C0001` to the first substrate), S3 is black. In 2 the paper has the aryl (Ar) groups in dark red-brown and the Si(Me)2R part in blue, with the O and CH2 black; the replica is all black, with Ph in place of Ar.
- Aryl groups: the paper writes Ar; the replica writes Ph.
- S5: the paper shows the structure in a dashed box with a bold label; the replica does not draw S5 at all.
- Panel title and dashed rule of panel (A) are absent.
- Conditions: the paper keeps each condition line whole; the replica breaks lines after commas (the layout lint re-flowed them to fit the row budget).
- S5 in the conditions: the paper bolds it; the replica writes it as S with a subscript 5 (the formula-digit rule).
- Label to bond proportion is not close: the replica is about 2.0 (14.4 pt bond, 10 pt Arial, cap height about 7.2 pt) and the reference is about 2.2. Arrow length is not close either: 14.7 and 15.1 bond lengths in the replica against about 19 and 22 in the reference.
- Bold compound labels, black label and reagent colour, the arrowhead style, the (i)/(ii) above and below placement and the two-row structure agree with the paper. The line weight, the row spacing and the degree and dash typography do not.

## Tool gaps

- `substrate_colors` colours whole substrates by position, and the report lists it as applied. In the saved file only S1 (first substrate) is coloured; S3 in the second step stays black.
- No fragment-level or atom-level colour in the brief, so a variable group can not be coloured separately from the rest of the molecule, and the aryl/oxime part of 2 can not be dark red while the rest is black.
- `variation_color` is not used by `draw_figure` (not in the report's applied list).
- `conditions_split` is skipped; the report says the brief's above/below lines are kept as given.
- No bold italic "(A)" run or dashed horizontal rule is known to be available. The brief accepts a `title` key (`BRIEF_KEYS` in `toolkit/cdxml_toolkit/mcp_runtime/figure_draw.py`), so the panel title is untested rather than a confirmed gap.
- No dashed frame around a reagent; S5 is not drawn because the brief places structures only as steps' substrates or products (a free reagent panel was not tested).
- No Ar label: only `[*]` (drawn as R) worked as a generic group, and Ar is not in `abbreviate_groups`. No alias field for a custom label was found.
- Step balance can not be checked when a dummy atom is present ("generic atoms (R groups, *) cannot be balanced"), so the report never confirms the two steps.
- Condition text is re-typeset: formula digits become subscripts, so S5 becomes S with subscript 5, and a bold label can not be placed inside a condition line.
- Layout lint re-flows condition lines after commas whenever a row is too wide. No option keeps each condition line whole while still wrapping rows.
- The two-row layout comes only from the row budget (`max_width`); there is no explicit row break.
- No line-width control: the `acs1996` preset fixes `LineWidth` at 0.6 pt, so the line-to-bond ratio is 0.042 against about 0.08 in the reference. No brief key sets it.
- No arrow-length control: the arrows come out at 14.7 and 15.1 bond lengths; no brief key sets arrow length.
- No row-spacing control: the gap between rows is an internal `gap_scale`, not a brief key.
- No bond-length control in the brief: the 14.4 pt bond comes from the preset, so the bond-to-cap ratio of 2.0 can not be set to the card's 2.2 from the brief.
- No typography control for conditions: a bold compound label inside a condition line, a spaced en dash and the tight degree sign are not reachable from the brief. Condition strings get automatic subscripts only.
- The card's `conditions_split` value does not describe this crop, where DMF is in step (i) above with the reagents. The card's `substrate_colors` order (first substrate `#2C0001`) does not match this crop, where S1 is blue.

## Structure issues

- R is a dummy atom, while the paper's R is an unspecified group; the replica depicts one placeholder meaning.
- The two aryl groups of 2 are phenyl, a specific compound in place of the paper's unspecified Ar.
- S5 structure is not drawn.
- The yield field is empty in this panel; nothing to check.

## Audit

Checked by re-running `replay.py` into a temporary folder (nothing written in this folder), reading the `figure.cdxml` it produced, and measuring `reference.png` and `rendered.png` pixel by pixel.

Overclaims corrected:

- Testable count: the earlier table held 17 counted rows and one `approx` row, not 18. The table now has 21 counted rows and 4 `n/a` rows.
- The `approx` bond-to-cap row is a mismatch (2.0 against 2.2) and is now `no`.
- The arrow-length row said "not measured". It was measured: 14.7 and 15.1 bond lengths against about 19 and 22 in the reference. Now `no`.
- Line width was missing from the table. Measured 0.042 against about 0.08. Added as `no`.
- "Label to bond proportion is close" is not accurate. See the Differences section.
- "O-CH2-SiMe2R of 2 blue" is not accurate. Only the Si, the two Me and the R are blue; the O and CH2 are black.
- "plain arrows agree" holds for the arrowhead only; the line weight does not match.
- "two rows" holds for the structure; the row spacing does not. Kept as `yes` for the structure only.
- The "(i)/(ii) split" is matched only for placement above and below. The card's `reagents_above_solvent_below` name is wrong for this crop.
- The tool gap "no panel title ... (`title` key not tested)" is untested, not a confirmed gap, because `BRIEF_KEYS` includes `title`.

Corrected matched count: 8 of 21 counted rows (the earlier figure was 8 of 18). The eight `yes` rows hold, but the two-row row holds for structure only, not for spacing.

Confirmed from the CDXML and pixels: colour index 10 is `#2C0001` and no `#0203FE` appears in the colour table; S1 atoms and bonds use colour 10 and S3 uses colour 0; the compound labels use face 1 (bold); the "S5" run in the conditions is a subscript 5 (face 32), not bold; in `reference.png` S1, S3 and the Si(Me)2R part of 2 are blue (about 2400 saturated blue pixels) while `rendered.png` contains no blue pixel.

Not verified: the origin of `rendered.png` (my own replay reported native status `not_run`, although arrow and line sizes in the CDXML agree with the render); the RDKit parse of the three SMILES; the spacing of the en dash in `0 °C – rt`, read from a 3x zoom of a 900 px crop (medium confidence).
