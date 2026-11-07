# Maes et al. 2023: iron-catalysed pyrimidinone scope (Scheme 2, substrate scope, chemeurj)

Source: Maes et al., "Iron-catalysed carbene transfer to isocyanides as a platform for heterocycle synthesis", *Chem. Eur. J.* **2023**. DOI: [10.1002/chem.202203074](https://doi.org/10.1002/chem.202203074). Scheme 2 (the amidine scope part).

Licence: CC BY 4.0, reference crop reproduced under that licence (`reference.png`, copied from `evidence/chemeurj-04.png`).

House style: `chemeurj` (Chemistry - A European Journal, Wiley-VCH; base preset `wiley`). Figure type: `substrate_scope`. The brief is `brief.json` with `"style": "chemeurj"` and `"kind": "scope"`.

## What is reproduced

The amidine part of the scope panel in Scheme 2: six products from the 2-phenylpyrimidin-4(3H)-one family, three from section A and three from section B.

| ID | Structure (SMILES in brief.json) | Yield in the paper | Yield in the replica |
| --- | --- | --- | --- |
| 4aa | `CC(C)(C)Nc1cc(=O)[nH]c(-c2ccccc2)n1` (6-tBuNH, 2-Ph) | 88% (85%b) | 88% (85%b) |
| 4ba | `CC(C)(C)CC(C)(C)Nc1cc(=O)[nH]c(-c2ccccc2)n1` (6-tert-octylNH, 2-Ph) | 86% | 86% |
| 4ca | `CC(C)Nc1cc(=O)[nH]c(-c2ccccc2)n1` (6-iPrNH, 2-Ph) | 71% | 71% |
| 4ab | `COc1ccc(-c2nc(NC(C)(C)C)cc(=O)[nH]2)cc1` (6-tBuNH, 2-p-MeOC6H4) | 84%b | 84%b |
| 4ac | `CC(C)(C)Nc1cc(=O)[nH]c(-c2ccc(C(F)(F)F)cc2)n1` (6-tBuNH, 2-p-CF3C6H4) | 71%b | 71%b |
| 4ae | `Cc1nc(NC(C)(C)C)cc(=O)[nH]1` (6-tBuNH, 2-Me) | 61%b | 61%b |

The structures were read by eye from the crop. RDKit confirmed that each SMILES parses and gives the expected formula. OCSR was not run.

The conditions line is the header of the scheme, condensed to plain text: `Bu4N[Fe(CO)3NO] (5 mol %), DCE, 80 °C, 15 min, 4 Å MS; then amidine 3, 16-20 h`. The paper puts these on two arrows, with the isocyanide 1a-l and diazo ester 2a on the left, and the bracketed intermediate 5aa-la in the middle. None of these are drawn.

Not reproduced: the other 14 entries of the scope, the scheme header structures, the bracketed intermediate, and the footnote text for `b` (not in the crop, so not invented).

## Replay

```
python skill/chemdraw/scripts/cdx.py py skill/chemdraw/assets/house-styles/chemeurj/replica/chemeurj-04/replay.py NEW_DIR
python skill/chemdraw/scripts/cdx.py render NEW_DIR/panel/page-001.cdxml
```

`replay.py` runs `draw_figure` on `brief.json` offline and writes `panel/page-001.cdxml`, `panel/summary.json` and `validation.json` into the new folder. It was checked in this session: one page, six compounds, no errors. No `rendered.png` was produced (see below).

## Render status

No native ChemDraw render was produced. The draw tool reported `native_preview: unavailable` (`resource_busy`, "chemdraw_com remained busy for 175 seconds") on the first try. A retry with `--render` hit the 300-second tool timeout. A later retry, and a direct `cdx.py render` of the single-page file, were stopped because the render did not return. The ChemDraw resource was shared with other jobs running at the same time. The comparison below is therefore based on the CDXML data (fonts, sizes, colours, text) and not on a rendered picture.

## Convention comparison

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| scope_layout grid | section A: 6 columns x 2 rows (12 structures); section B: 6 structure columns x 1 row (8 compounds) | 3 columns, one row per section (6 structures), one page | no |
| yield_format `{value}%` | `88%` and `84%b` under/after the label, footnote letter as superscript | text `yield: 88% (85%b)`; the `yield:` prefix is added from the field key; `b` is plain text | no |
| conditions_position scheme_on_top | reagents above the arrow, solvent and time below, two arrows | one plain text line above the grid; the CDXML has no arrow object | no |
| highlight_fill null | no grey fill | no fill | yes |
| section rule (grey or dashed) | dashed rule between sections A and B | no rule | no |
| section titles bold navy or bold panel letters A/B | bold letters A and B at top left | plain black `A` and `B`, 8 pt, not bold | no |
| footnote letters in brackets or superscript | superscript `b` after the yield | plain `b` after the yield | no |
| reaction header with arrow and bracketed intermediate | 1a-l + 2a -> [5aa-la] -> 3a-i -> 4 | not drawn; scope takes text only | no |
| compound_label_face bold | bold labels | plain labels (`face="0"` on the `4aa` text run) | no |
| abbreviate_groups tBu, Ph, OMe | tBu and Ph written as labels, OMe written as MeO | tBu drawn as skeleton carbons, Ph as a ring, OMe as O-CH3 skeleton; no labels | no |
| variation colour (varied amine part maroon) | varied R groups in maroon | all black | no |
| aromatic_rings kekule | Kekule rings | not verified: explicit double bonds exist in the CDXML (27 `DoublePosition` attributes), but nothing was drawn | not verified |
| yield placement on the label line | `4aa 88% (85%b)`: value on the same line as the bold label | `yield: ...` on its own line, 15.6 pt below the label (CDXML y 197.3 vs 212.9) | no |
| proportions, bond length over label cap height | 2.03 (120 px bond / 59 px cap height, crop 04; house 2.0) | 2.97 from the CDXML (17.0 pt bond / 8.0 pt label, Arial cap about 0.716 em) | no |
| line weight over bond length | 0.05 (6 px / 120 px, crop 04; house 0.04) | 0.044 (0.75 pt / 17.0 pt) | not verified (in range by numbers, not seen) |
| label colour black | `#000000` | labels use colour index 3, but the colour table holds two entries (white, black), so black is not confirmed | not verified |

Counted for the summary: the original count was 11 scored rows, 1 matched, 2 partial. After the audit there are 13 scored rows (the 11 above plus yield placement and proportions): 1 matched (highlight fill, a null convention, so the check is trivial) and 12 no. Three rows are not verified (aromatic, line weight, label colour). The two `partial` marks are corrected to `no`; see the Audit section.

## Differences from the paper

- Layout: the paper's section A is 6 columns x 2 rows (12 structures). Section B is one row of 6 structure columns carrying 8 compounds (the first column stacks 4ab, 4ac and 4ad under one structure). The replica has 3 columns with 3 and 3 entries, one row per section.
- A title "Substrate scope" was added by the tool. The paper has no title.
- Yields carry a `yield:` prefix. The paper shows only the value.
- Compound labels are plain (not bold), and the group letters A and B are plain.
- No dashed rule between sections, no navy section titles, no maroon varied groups.
- The varied substituent text under each entry (p-OMe, p-CF3, p-Cl in section B) is not drawn; the replica has only the compound label and the yield.
- The tBu group is drawn in full (C(CH3)3 skeleton) instead of abbreviated.
- Conditions are a line of text. The paper's reagents sit above the arrow, with solvent and time below.
- Rendering: no picture, so proportions could not be compared by eye. From the CDXML: bond length 17.0 pt, label size 8.0 pt, line width 0.75 pt. The paper's bond length is about 2.0 times the label cap height (120 px / 59 px, crop 04). With Arial cap height about 0.716 of the point size, the replica is about 2.97 times. That is about 46% longer relative to the label than in the paper, a numeric mismatch that the file itself shows. The line weight ratio (0.044 of bond length, against 0.05 in crop 04 and 0.04 in the house file) is within range by the numbers but was not seen.
- The paper's `b` footnote text is not in the crop, so none is provided.

## Tool gaps

For the `kind: "scope"` brief, which is the path this replica used:

- Only the house base preset is applied. Bold labels, bold letters, navy and maroon colours, superscript footnotes and abbreviations are not applied (confirmed in the CDXML: face `0` on labels and letters, no abbreviation text).
- No column-count control. Only `width_mm` and `height_mm` are accepted (`SCOPE_KEYS` in `toolkit/cdxml_toolkit/mcp_runtime/figure_scope.py`).
- No bond length, line width or label size control. `style` takes a preset or house name only, and the panel keeps its own 8 pt text. This is why the bond-to-label ratio cannot be set to the house 2.0. The replicator did not list this one.
- No separator rule, no scheme-style header (arrows, reactant structures, bracketed intermediate), no per-entry text line, no per-entry colour, and no superscript in values (values are plain strings).
- The default title is used when `title` is empty (`brief.get("title") or "Substrate scope"`). A single space gives a blank title, tested offline; that is a workaround, not a switch.

Not a gap:

- The `yield:` prefix can be switched off. A field `{"key": "yield", "label": ""}` gives the bare value `88% (85%b)` (tested offline in the audit).

Toolkit capability not used: `compose_chemical_figure` (`toolkit/cdxml_toolkit/mcp_runtime/figure_tools.py`) takes a manifest with `grid.columns` (1 to 20), text objects with runs (bold, superscript, per-run colour), `line` and `rectangle` objects (colour, dashed), arrows, brackets, molecule `label`, molecule `color` and `highlight_atoms` with `highlight_color`, and a manifest `style` with bond length, font size and line width. The code shows these fields, but none of them was run for this figure.

- Native rendering was unavailable in this session, so the drawing could not be checked by eye.

## Audit

Second pass against `reference.png`, the crop-04 entry in `toolkit/cdxml_toolkit/publication/house_styles/chemeurj.json`, and a fresh offline re-draw of `brief.json` into a scratch folder (it succeeded: one page, six compounds). There is no `rendered.png` and no native render, so no row here is confirmed by eye.

- Confirmed: all six structures and all six yield values agree with the reference crop.
- Overclaim: `scope_layout` and `conditions_position` were marked partial. Both are no. The replica has 3 columns with one row per section, and its CDXML contains no arrow object.
- Overclaim: the reference layout counts. Section A is 6 x 2, not 4 x 3. Section B is 6 structure columns in one row holding 8 compounds (4ab, 4ac, 4ad, 4ae, 4af, 4ag, 4ah, 4ai), not 4 x 1 with 4 entries. The total of 20 compounds, and so "the other 14", is correct.
- Overclaim: "no switch for a bare value". A field with `"label": ""` gives a bare value (tested). Not a gap.
- Overclaim: several tool gaps hold only for the `scope` brief. `compose_chemical_figure` (manifest path) has grid columns, superscript and coloured runs, dashed or coloured lines, arrows, brackets and molecule labels. The replicator did not check that path, and it was not run here.
- Missed row: yield placement. The paper's value sits on the label line. The replica's sits 15.6 pt below it.
- Numeric mismatch: proportions. The replica's bond-to-label ratio is 2.97 against the paper's 2.03. This comes from the numbers, not from the eye.
- Not verified: the "all black" variation colour (labels use colour index 3, and the colour table has two entries), label colour, line weight (in range by numbers), and Kekule rendering.
- Matched: highlight fill. The house value is null and the replica has no graphic objects, so the match is trivial.
- Corrected count: 1 of 13 scored rows matched (the replicator claimed 1 of 11). Three rows are not verified.
