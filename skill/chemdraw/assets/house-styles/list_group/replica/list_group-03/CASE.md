# List et al., Nature 2024: substrate scope of the ring expansion (Figure 3, products 3b-3f)

Source: List et al., "Catalytic asymmetric cationic shifts of aliphatic hydrocarbons", *Nature* **2024**, DOI: [10.1038/s41586-023-06826-7](https://doi.org/10.1038/s41586-023-06826-7). The citation is taken from the house-style card ("List et al."); the full author list was not checked against the paper.

Licence: CC BY 4.0 (from the card). Reference crop: `evidence/list_group-03.png`, copied here as `reference.png`.

Drawing style: `list_group` house style (`cdx.py styles list_group`), figure type `substrate_scope`. Base preset applied by the tool: `nature`, bond length 10.8 pt.

## What is reproduced

Six entries of the scope grid under the "Five- to six-membered ring expansion" heading: 3b (n-decyl), 3a (n-hexyl), 3c (n-butyl), 3d (n-propyl), 3e (ethyl) and 3f (isopentyl). Each has its yield and e.r. as printed in the crop. Not drawn: the 1 to 3 reaction arrow, the catalyst panel, the OsO4/TMEDA step, the X-ray structure of 7, 3g (93%, 99:1 e.r., readable in the crop; the reason it was left out is not recorded), and rows 3h, 3i, 3j and 3k. The values for 3h to 3k are cut off at the bottom edge of the crop and cannot be read.

Structures (product core `CC1=CCCC[C@]1(C)R` with R as listed; SMILES are in `brief.json`):

| ID | R | SMILES | CIP (RDKit) |
| --- | --- | --- | --- |
| 3b | n-C10H21 | `CCCCCCCCCC[C@@]1(C)CCCC=C1C` | S |
| 3a | n-C6H13 | `CCCCCC[C@@]1(C)CCCC=C1C` | S |
| 3c | n-C4H9 | `CCCC[C@@]1(C)CCCC=C1C` | S |
| 3d | n-C3H7 | `CCC[C@@]1(C)CCCC=C1C` | S |
| 3e | C2H5 | `CC[C@@]1(C)CCCC=C1C` | S |
| 3f | CH2CH2CH(CH3)2 | `CC1=CCCC[C@]1(C)CCC(C)C` | R |

The 3f label is R although the drawn arrangement is the same as in the other five. For 3f the isopentyl chain outranks the ring CH2 in CIP priority, so the descriptor flips. Stereo was read from the drawing: a hashed methyl and a bold wedged chain on the quaternary carbon, which gives S for the n-alkyl products. This wedge and hash reading was not checked against the SI and is the main uncertainty in the stereo.

OCSR was not run. The structures were read by eye from zoomed crops and checked with RDKit (formula and CIP labels). The chain lengths were counted from the drawn zigzags.

## Replay

```
python skill/chemdraw/scripts/cdx.py py skill/chemdraw/assets/house-styles/list_group/replica/list_group-03/replay.py NEW_DIR
python skill/chemdraw/scripts/cdx.py render NEW_DIR/pages/page-001.cdxml
```

`replay.py` runs `draw_figure` on `brief.json` offline and writes `pages/` and `validation.json` into a new directory. `rendered.png` is a downscaled copy of the native ChemDraw render of the same page.

## Attempts

1. The first brief had the wrong stereo tag for 3b, 3a, 3c, 3d and 3e (a hand-written `[C@]` gives R). An RDKit CIP check caught it before the figure was kept. The draw started with it was stopped.
2. Draw with `--render` on brief v1 (separate yield and e.r. fields with units): `draw_figure` exceeded 300 s (`tool_timeout`). Draw without render succeeded, and `cdx.py render` of that page succeeded; that output was not kept.
3. Brief v2 (kept as `brief.json`): values pre-formatted as `93%, 97.5:2.5 e.r.`, one field with an empty label, title `""`, width 260 mm. The first draw returned `resource_busy` (`chemdraw_com` busy for 295 s). The retry succeeded, and the native render of that page is `rendered.png`.

## Differences from the paper

- Layout: the paper shows five products in one row, ring on the left and chain running right, then a second row. The replica puts all six in one row, ring on the right and chain running left.
- Stereo depiction: the paper draws a hashed methyl up-right and a bold wedge down-right. The replica draws a bold wedge on the methyl pointing down and a plain chain. The RDKit readback reports the same stereo, but the depiction is different.
- Labels: the paper's compound labels are bold; the replica's are plain. The scope tool did not apply the house conventions (`style.applied` is empty; `skipped`: "house conventions apply to schemes only").
- Yield and e.r.: the paper has "93%, 97.5:2.5 e.r." on one line under a bold label. The replica has the same text on one line, in plain type.
- Title: the paper has no title. The replica shows an automatic "Substrate scope" heading; setting `title` to `""` did not remove it.
- Category title: the paper's "Five- to six-membered ring expansion" is left-aligned plain text with no rules. The replica's is left-aligned plain text with no rules.
- Conditions: the paper has them in the scheme, split: '(S,S)-IDPi 2d (5 mol%)' above the arrow and 'CHCl3, RT, 24 h' below it, with CHCl3 subscripted and 2d bold. The replica has them as one plain line above the panel.
- Grid: the paper has five entries in the first row; the replica has one row of six.
- Omitted: the reaction header, catalyst panel, OsO4 step, X-ray structure, 3g (readable: 93%, 99:1 e.r.; no reason recorded), and rows 3h to 3k (values unreadable).

## Tool gaps

- Scope panels ignore the house-style conventions (bold labels, label colour, yield placement and format, `reagent_text_color`). Only the base preset is applied. Scheme briefs get these conventions, so a scope panel with house conventions cannot be drawn with `draw_figure`.
- No option to suppress the automatic "Substrate scope" title.
- No option for group headings: a centred heading or thin grey rules under it cannot be requested.
- Unit formatting adds a space before the unit (`93 %`); a pre-formatted value is needed to get `93%`.
- The tool chooses each structure's depiction. Ring orientation, the side the chain sits on, and which bond carries the wedge cannot be set, so the replica does not match the paper's per-structure drawing.
- Footnote superscripts on compound labels (paper: `3k^a`) cannot be expressed in the scope species record.
- Scope conditions are a single line. The scheme's reagents-above and solvent-below split (`conditions_split`) cannot be expressed in a scope panel.
- Operational: `draw_figure` with `render: true` exceeded its 300 s limit once, and `chemdraw_com` returned `resource_busy` once; both cleared on retry.

## Card observations (not fixed here)

These are reported in `result.json` as `card_errors`. The card was not edited.

- `substrate_scope` signature "bold number, comma, yield on one line, e.r. on the next": in crop 03 the bold label is alone on its line, and yield and e.r. share the next line, separated by a comma.
- `substrate_scope` "thin grey horizontal rules with centred category titles": crop 03 shows a left-aligned title and no rules.
- `substrate_scope` "footnote letters as superscripts after the yield": crop 03 puts the footnote on the compound label (`3k^a`).
- Top-level signature "label, yield and e.r. stacked under products: '6, 91%' then '98:2 e.r.'" conflicts with `yield_placement: under_product_label` and with crop 03, where the label stands alone.
- Top-level IDPi signature (steel-blue arcs, blue and gold dots): crop 03's catalyst is black and grey; no blue or gold pixels are present.
- `highlight_fill: null` for `substrate_scope`: crop 03 has a grey #F7F7F7 band behind the top scheme and catalyst (the card's own notes record it). It is not a fill behind a product.
- `abbreviate_groups` lists `tBu` and `OMe` only. Crop 03 uses `OBn` (3j) and abbreviates tBu in the catalyst; `OBn` is not on the list.

## Conventions checked

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| compound label face bold | bold | plain | no |
| compound label colour #000000 | black | black (default; the tool did not apply it) | yes (appearance only) |
| yield under product label (order) | yes | yes | yes |
| label and yield horizontal alignment | centred in each product's cell (for 3b, about x 75 px, under the chain rather than the ring) | left-aligned at the cell edge | no |
| yield format `{value}%` | `93%` | `93%` (pre-formatted string; the tool's own unit formatting would insert a space) | yes (output text only) |
| e.r. format `{value} e.r.` | `97.5:2.5 e.r.` | `97.5:2.5 e.r.` | yes |
| yield and e.r. on one line after label | `93%, 97.5:2.5 e.r.` | `93%, 97.5:2.5 e.r.` | yes |
| grid layout | 5 in row 1; 2 in row 2, beside the OsO4 step and 7; 4 in row 3 | one row of six | no |
| conditions placement | reagent above the arrow; CHCl3, RT, 24 h below it | one plain line above the panel | no |
| conditions text: italic (S,S), bold 2d, subscript 3 in CHCl3 | yes | none | no |
| variation colour null | no colour | no colour | yes |
| highlight fill null (no fill behind products) | no product fill; the grey #F7F7F7 band (value 247) sits behind the scheme only | no fill | yes (products); the scheme band is not reproduced |
| reagent text colour #000000 | black | black | yes |
| structure orientation and stereo bond choice | ring left, chain right; hashed methyl and bold chain on 3b, 3a, 3f and 3g | ring right, chain left; bold methyl wedge on all six | no |
| group title left-aligned, plain, no rules | left-aligned, plain, no rules | left-aligned, plain, no rules | yes (the card's centred-with-rules signature is not in crop 03) |
| footnote superscript on compound label (card claim) | `3k^a` on label | not reproduced | no |
| bond length to label size (house value 2.65) | bond about 20 px over a bold label ascender about 8 px: about 2.5 | bond about 19 px over a plain label ascender about 11 px: about 1.7 | no (native pixels, about 10 % uncertainty) |
| line weight (house value 0.044 of bond) | about 1 px on a 20 px bond; cannot be resolved at this resolution | about 1 px; similar | not verified (counted as not matched) |
| aromatic rings kekule | no aromatic ring in 3b-3f | none drawn | not applicable (removed from count) |
| IDPi catalyst blue and gold (card claim) | black and grey; no #456A98 or #DEC27D pixels | no catalyst in the panel | not applicable (removed from count) |

Matched 9 of 18 applicable rows. The earlier "9 of 15" and "9 of 16" were wrong: the table had 17 applicable rows, and two more rows (conditions text, structure orientation) are now counted.

## Audit

Second audit, by eye on reference.png and rendered.png, with pixel measurements at native resolution. ChemDraw was not run. The CIP labels were re-derived by hand from the drawn wedges: reference 3b S and 3f R, replica 3b S and 3f R, which agrees with brief.json.

Corrections made above:
- Matched count: 9 of 18 applicable rows, not 9 of 15 or 9 of 16.
- Label and yield alignment: the paper centres them in each product's cell, not under the ring. Still not matched.
- Conditions: the old text said the paper has all conditions above the arrow. It splits them, and the subscript and bold 2d were missing from the list.
- Bond ratio: the rough "about 2.0" is replaced by measured values, about 2.5 for the paper and about 1.7 for the replica. The replica's labels are relatively larger, as the earlier audit said.
- 3g was readable in the crop (93%, 99:1 e.r.) and was left out without a reason. It is now listed as omitted.
- Stereo: the paper draws a hashed methyl and a bold chain on 3b, 3a, 3f and 3g. The replica draws a bold methyl wedge on all six. The RDKit readback match is a CIP match, not a depiction match.
- Card observations, rechecked: the band is value 247 and sits behind the scheme only. No #456A98 or #DEC27D pixels are present; the roughly 250 bluish pixels are anti-aliasing. All card observations in this file stand.

Tool gaps the replicator missed:
- No bond-length or line-width key in a scope brief. The scope keys in mcp_runtime/figure_scope.py are kind, species, fields, conditions, footnotes, title, style, width_mm and height_mm. The label-to-bond ratio cannot be matched.
- Label and yield horizontal alignment (centred in the cell) cannot be set.
- No columns-per-row control. width_mm packs one row of six; the paper's layout is 5, then 2 beside the step, then 4.
- A scope panel cannot carry a scheme header, an arrow or a step label (OsO4, TMEDA). The paper's arrow and structure 7 cannot be drawn on the same figure, so the omission is a tool limit, not a choice.
- The conditions field is plain text. There is no italic, no bold run and no subscript (CHCl3, italic (S,S), bold 2d).
- The footnotes key takes plain text lines. It cannot place a superscript letter on a compound label (already listed above).
