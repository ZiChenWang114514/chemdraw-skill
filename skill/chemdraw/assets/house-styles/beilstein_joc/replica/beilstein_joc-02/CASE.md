# beilstein_joc-02: substrate-scope panel, Scheme 3 (top), Gandeepan et al. 2025

Source: Gandeepan et al., "Palladium-catalyzed regioselective C1-selective nitration of carbazoles", *Beilstein J. Org. Chem.* **2025**, DOI [10.3762/bjoc.21.190](https://doi.org/10.3762/bjoc.21.190). Licence: CC BY 4.0 (from the `beilstein_joc` card). Reference crop: `reference.png` (copy of `evidence/beilstein_joc-02.png`).

Figure type: `substrate_scope` (card section). Style: `beilstein_joc` (base preset `nature`).

## What is reproduced

The three-entry product grid of the scope scheme: 2a (69%), 2j (60%) and 2k (55%), with the conditions line from the top of the scheme. Brief: `brief.json`, kind `scope`, one row of three compounds with their yields.

| ID | Product SMILES in brief.json | Reading from the crop |
| --- | --- | --- |
| 2a | `[O-][N+](=O)c1cccc2c1n(-c1ccccn1)c1ccccc12` | unsubstituted carbazole core, NO2 at C1 next to the N-fusion carbon, N-(2-pyridyl) |
| 2j | `[O-][N+](=O)c1cc(OC)cc2c1n(-c1ccccn1)c1ccc(OC)cc12` | MeO at C3 and C6, read from the drawing, not checked against the SI |
| 2k | `[O-][N+](=O)c1cc(C(C)(C)C)cc2c1n(-c1ccccn1)c1ccc(C(C)(C)C)cc12` | t-Bu at C3 and C6, read from the drawing |

All three SMILES parse in RDKit and give C17H11N3O2, C19H15N3O4 and C25H27N3O2 (rechecked). The paper text is not in the case folder, so the claim that it names the C1-nitration products and the 2-Ph, 2-OMe and 2-Cl substrates cannot be checked here. As written it does not fit 2j, which is drawn with two OMe groups, so the 2-OMe name cannot be this compound. The 3,6-substitution pattern for 2j and 2k is a reading of the crop: reference.png shows two MeO groups on 2j and two t-Bu groups on 2k, and the drawn positions agree with that reading, but nothing outside the crop confirms them.

The general reaction above the grey rule (substrate 1 with R1 and R2, the Pd2(dba)3 / AgNO3 / 1,4-dioxane / 120 °C / 24 h conditions) is not part of the scope brief. The scope kind has no place for it. It was drawn separately as a scheme with dummy atoms (see Tool gaps).

## Replay

`replay.py` is the jacs-au script with only its docstring changed. It runs offline and writes a folder named `figure.cdxml` (the scope output is a folder, so the name is misleading) that contains `page-001.cdxml`. The replayed page size (15981 bytes) is not checked: the case folder has no page-001.cdxml to compare.

```
python skill/chemdraw/scripts/cdx.py py skill/chemdraw/assets/house-styles/beilstein_joc/replica/beilstein_joc-02/replay.py NEW_DIR
python skill/chemdraw/scripts/cdx.py render NEW_DIR/figure.cdxml/page-001.cdxml
```

`rendered.png` is a 1200 x 611 px render of the scope page. The 1389 px native width is not in the folder and is not checked. The reference crop is 798 x 440 px (checked).

## Differences from the paper

- No general reaction header. The paper has the general reaction (1 to 2) with a catalyst line above the arrow and AgNO3 and solvent below, then a full-width thin grey rule. The replica has only one line of conditions above the grid.
- Extra heading: the replica draws `Substrate scope` above the conditions line. The paper has no such heading. It is the tool default in figure_scope.py (`brief.get("title") or "Substrate scope"`), and an empty title falls back to it, so it cannot be removed.
- Conditions are one plain line: `Pd2(dba)3 (10 mol %), AgNO3 (1.2 equiv), 1,4-dioxane, 120 °C, 24 h`. The paper splits them over the arrow and sets the formula digits as subscripts; the replica leaves them plain.
- Labels are plain and on their own line, with the yield on the line below (`2a` / `69%`). The paper has bold labels with the yield on the same line (bold `2a`: 69%).
- No footnote. The paper marks 2k with a superscript a after 55%; the footnote text is not in the crop, so nothing was added.
- tert-Butyl is drawn as a skeleton (C(CH3)3), not as the italic-t abbreviation `t-Bu`. Methoxy groups are skeletal OMe bonds, not `MeO` or `OMe` labels.
- Nitro is drawn as N(+)(=O)O(-) with charges; the paper writes it as a red NO2 label.
- Colours are absent. The paper draws the carbazole and pyridine core with blue bonds and light-blue ring fill (#BEDAFF), and the NO2 label in red. The card records these as author choices and sets `variation_color` and `highlight_fill` to null for this figure type, so the replica follows the card and not the paper.
- The new C-NO2 bond is black. The card's note that it is dark red (#800000) could not be confirmed at this crop size, so it is not claimed either way.
- The skeleton orientation differs: the paper shows the N-pyridyl pointing down, the replica pointing up and left.
- Width: the delivered rendered.png is 1200 px wide (the 1389 px native width is not checked), against about 798 px in the paper. The card asks for figures about 700 to 800 px wide, so the replica is outside that range either way.
- Bond to label ratio: the paper is about 2.5 (bond over text cap height, crop 02, card measurement). Measured on rendered.png, the bond is about 35 px (RDKit geometry against the ink extent of 2a, roughly plus or minus 10 percent) and the conditions cap height is 21 px, so the ratio is about 1.7. The labels are relatively large, more than the earlier preset estimate of 1.9 suggested. Label size against figure width is about the same as the paper's (cap 21 of 1200 px against 14 of 798 px).

## Convention table

Rows are the conventions the card claims for `substrate_scope` plus the top-level scheme conventions visible in this crop. 17 rows, 4 match after the audit (the first draft said 5).

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| scope_layout grid (entries in a grid under one header) | three entries on one shared baseline | not on one baseline: the 2a label sits about 75 px higher than the 2j and 2k labels, because each label is placed under its own structure | no |
| conditions_position scheme_on_top (general reaction above the grid) | general reaction 1 to 2 above the rule | conditions line only, no general reaction | no |
| full-width thin grey rule between header and grid | present | absent | no |
| label and yield on one line (`2a: 69%`) | one line | two lines | no |
| compound_label_face bold | bold labels | plain labels | no |
| yield_format `{value}%` | 69%, 60%, 55% | 69%, 60%, 55% | yes |
| footnote as superscript a after the yield | 55% with superscript a | not drawn | no |
| tBu written t-Bu with italic t | t-Bu | skeletal tBu | no |
| abbreviate_groups (OMe, tBu) | MeO, OMe, t-Bu labels | skeletal bonds | no |
| aromatic_rings kekule | Kekule rings | Kekule rings (visual check only) | yes |
| reagent_text_color #000000 | black conditions text | black (darkest conditions pixel is 0,0,0) | yes |
| Arial-like sans-serif text | Arial-like | sans-serif that looks like Arial (visual only; font not identified) | yes |
| arrow_style plain (scheme arrow) | plain arrow | no arrow | no |
| conditions_split reagents above, solvent below | catalyst above, AgNO3 and solvent below | one line above, no split | no |
| variation_color null (card) | red NO2, blue scaffold (card says null) | black | no |
| highlight_fill null (substrate_scope) | light-blue ring fill #BEDAFF | none | no |
| figure about 700 to 800 px wide | about 798 px | 1200 px delivered (1389 px native not checked) | no |

## Tool gaps

- Scope panels apply no house conventions. The report says `applied: []` and `house conventions apply to schemes only`. The same style on a scheme does apply bold labels and other conventions, so the scope path is the gap.
- A scope brief has no slot for a general reaction above the grid, and no full-width rule under a header.
- A scope value cannot share a line with its label. With an empty field label the yield sits under the label, and there is no superscript footnote marker on a value (footnotes are only text lines under the panel).
- Conditions text is drawn as given. Formula digits are not turned into subscripts on this path, although the scheme path does that.
- No per-compound or per-substituent colour for scope species. `substrate_colors` and `highlight_fill` are scheme conventions only.
- R-group placeholders: a scheme with `[*]` atoms is accepted with a warning that the balance is not checked (`generic atoms (R groups, *) cannot be balanced`). The brief cannot label R1 and R2 as variables, and the balance check is skipped.
- The replay script writes scope output to a path named `figure.cdxml`, which the tool creates as a folder. The scheme replay pattern does not carry over to scope.
- Runtime: one `draw` with `--render` on the scope brief ran past the 300 s tool limit (`tool_timeout`), and a second attempt ended as `worker_crashed` (exit 143) after about 96 s. The same brief drew offline in about 112 s, and a separate `render` of its page took about 5 min. A scheme with `[*]` atoms drawn with `CHEMDRAW_OFFLINE=1` finished in about 48 s; its ChemDraw render did not return within about 17 min and was stopped, so that scheme has no PNG and is not part of the replica files. The timings come from the replicator's own runs; the folder has no logs, so they are not checked here.

- Title cannot be removed: an empty title falls back to `Substrate scope` (figure_scope.py). The scope brief has no way to drop the heading. The replicator did not list this.
- Label and yield baselines: publication/layout.py places each label under its own structure (molecule bottom plus 2.6 times the font size), so structures of different heights give labels on different baselines. There is no common-baseline option. The replicator did not list this.
- Orientation: coordinates come from RDKit Compute2DCoords. publication/layout.py has a `core_by_group` option that aligns each group to a reference compound, but figure_scope.py does not expose it (SCOPE_KEYS has no such key). That is the route to one core orientation across 2a, 2j and 2k, and it was not listed.
- Units: a field unit is appended with a space (field_text in publication/data.py), so the unit key gives `69 %`, not `69%`. The value has to carry the percent sign itself.

## Structure issues

- The 2j and 2k substitution positions (C3 and C6) are read from the crop and are not confirmed against the paper. The paper text is not in the folder, so the earlier claim that it was checked is withdrawn.
- The footnote text for 2k is not in the crop and is not drawn.
- All three product SMILES are in `brief.json` and were parsed by RDKit. Nothing comes from OCSR output.

## Audit

Checked against reference.png, rendered.png, brief.json, the house-style card (toolkit/cdxml_toolkit/publication/house_styles/beilstein_joc.json) and the toolkit code (figure_scope.py, figure_draw.py, publication/layout.py, publication/data.py). Pixel measurements are from rendered.png (1200 x 611) and reference.png (798 x 440).

Overclaims corrected:
- The scope_layout row was marked matched. The three entries are not on one baseline: the 2a label is at about y 440 to 470 px, the 2j and 2k labels at about y 515 to 540 px, and the yields at about y 495 to 525 px and 565 to 600 px. The reference has all three labels on one line. The row is now no.
- The count of 5 matched was wrong. It is 4 of 17 (yield format, Kekule rings, black conditions text, Arial-like face). Kekule and the font were checked by eye only.
- The two null rows (variation_color, highlight_fill) are no because the match column compares against the paper. The replica follows the card (no colour), not the paper.
- The unlisted heading "Substrate scope" is drawn above the conditions line. The Differences section said there was only the conditions line.
- The bond to label ratio of about 1.9 came from preset values. Measured, it is about 1.7, so the labels are relatively larger than the preset estimate said.
- The claims about the paper text (named 2-Ph, 2-OMe and 2-Cl substrates, and that the paper text was checked) cannot be checked from this folder. The 2-OMe name does not fit 2j as drawn (two OMe groups). Withdrawn as checked.
- The 1389 px native width, the 15981 byte page size and the runtime timings cannot be checked here: the folder has no native render, no page file and no logs. The delivered rendered.png is 1200 px wide.

Confirmed: replay.py differs from the jacs-au original only in its docstring; the scope path applies no house conventions (hard-coded report text in figure_scope.py); yields sit under the label; conditions are plain text; a scheme with [*] atoms gets a balance warning (figure_draw.py); the output path is a folder holding page-001.cdxml; the three product formulas match RDKit; the replica has no colour (zero coloured pixels in rendered.png); the reference is 798 x 440 px.

Tool gaps the replicator missed: the heading cannot be removed; labels sit on each structure's bottom, with no common baseline; orientation cannot be set from the brief although core_by_group exists in publication/layout.py; a unit adds a space. See Tool gaps above.
