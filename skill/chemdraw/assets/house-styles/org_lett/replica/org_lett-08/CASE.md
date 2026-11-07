# Org. Lett. substrate scope: Dell'Amico et al. (Figure 3), crop org_lett-08

Source: Dell'Amico et al., "Enantioselective organophotocatalytic alpha-functionalization of aldehydes with N-lactam radicals", *Org. Lett.* 2025 (DOI: 10.1021/acs.orglett.5c02365). Licence: CC BY 4.0. Reference crop: `reference.png`, a copy of `evidence/org_lett-08.png`.

Drawing style: the `org_lett` house style (card `toolkit/cdxml_toolkit/publication/house_styles/org_lett.json`, figure type `substrate_scope`), requested through `"style": "org_lett"` in `brief.json`. The scope panel applied only the base preset (acs1996, bond length 14.4 pt); the report says "house conventions apply to schemes only".

## What is reproduced

The eight-entry product grid of Figure 3: 4aa, 4ba, 4ca, 4da, 4ea, 4fa, 4ab, 4ac, each with its yield and ee, the two-step conditions as one text line above the grid, and the asterisk footnote. The reaction header (1 + 2 to 4, with the conditions above and below one arrow) is not drawn: the crop does not show structures 1 or 2, and a scope brief cannot draw a header arrow.

| Structure | SMILES (brief.json, S configuration as read from the wedge) | Yield, ee as printed |
| --- | --- | --- |
| 4aa | `CC[C@@H](CO)N1CCCC1=O` | 70%, 89% ee* |
| 4ba | `CC(C)[C@@H](CO)N1CCCC1=O` | 53%, 91% ee* |
| 4ca | `COc1ccc(C[C@@H](CO)N2CCCC2=O)cc1OC` | 48%, 91% ee* |
| 4da | `O=C1CCCN1[C@H](CO)Cc1ccccc1` | 58%, 90% ee |
| 4ea | `C=CCCCCCCCC[C@@H](CO)N1CCCC1=O` | 60%, 90% ee* |
| 4fa | `O=C1CCCN1[C@H](CO)CCOCc1ccccc1` | 53%, 92% ee |
| 4ab | `CC[C@@H](CO)N1CCCCC1=O` | 40%, 86% ee* |
| 4ac | `CC[C@@H](CO)N1CCCCCC1=O` | 11%, 74% ee* |

The SMILES were checked with RDKit (formula, CIP labels). The stereo is my reading of the bold wedge (narrow at the stereocentre, wide at N) in the crop: every product drawn as (S). The paper text was not checked, so the absolute configuration is unverified. The 4ea chain (vinyl plus seven CH2) follows the "7" label in the crop.

## Brief history

- Try 1: `"fields": [{"key": "result"}]` and a `max_width` key. The draw was refused for the unknown key `max_width`; removing it and running with `--render` timed out at 300 s.
- Try 2: drawn without render, then rendered separately. Grid packed 3 + 4 + 1; each value printed as `result: 70%, 89% ee*`.
- Try 3 (final, saved here as `brief.json`): field label changed to a blank string and `width_mm` set to 150. Grid packed 3 + 3 + 2; the value line now starts with a stray colon (`: 70%, 89% ee*`). `--render` timed out again; drawn without render and rendered separately.

## Replay

`replay.py` was copied from the jacs-au case with the docstring changed. It was not run: it writes `figure.cdxml` as one file, but a scope brief writes a folder of pages. Use `python skill/chemdraw/scripts/cdx.py draw brief.json NEW_FOLDER` and then `cdx.py render NEW_FOLDER/page-001.cdxml`. `rendered.png` is the page-001 render of try 3, downscaled to 1200 px wide (226 KB).

## Convention check

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| grid layout, 4 + 4 products under one scheme | 4 per row, 2 rows | 3 + 2 + 3 per the page packer | no |
| conditions above and below one arrow, scheme on top (`conditions_position` scheme_on_top) | 1 + 2 to 4 arrow with conditions above and below | one plain text paragraph above the grid that wraps to two lines and splits "Blue LEDs" mid-word, no arrow, no 1 + 2 row | no |
| compound label face bold (`compound_label_face` bold) | bold labels | plain labels (base preset; house style not applied to scope) | no |
| yield and ee on the line under the label, "yield, ee" | `70%, 89% ee*` | `: 70%, 89% ee*` (stray leading colon from the field label; left-aligned, not centred under the label) | no |
| yield format `{value}%` | 70% | 70% | yes |
| selectivity format `{value}% ee` | 89% ee | 89% ee | yes |
| asterisk footnote explanation centred under the grid | centred line | left-aligned line at the bottom | no |
| abbreviate_groups (MeO, OMe) | MeO and OMe labels | O-Me written out as ether chains | no |
| aromatic rings kekule | kekule | the only ring in the paper is 4ca; Ph and Bn are abbreviations there but full rings here | no |
| substrate colours and variation colour null (all black structures) | all black | all black | yes |
| blue text for light source (Blue LEDs, #0C11FF) | blue | black | no |
| solid (bold) wedge at the stereocentre to N | bold wedge on the stereocentre to N bond, narrow at the stereocentre | wedge on the substituent bond (ethyl in 4aa, chain in 4ea); N bond plain; N sits to the left of the stereocentre, the paper has it below | no |
| arrow_style plain and show_plus_sign | one plain arrow with a plus between 1 and 2 | no arrow in the scope panel | no |

## Differences from the paper

- Grid: 3 + 2 + 3 instead of 4 + 4. The page packer has no column or row count; `width_mm` changes the packing without fixing it to the crop.
- Labels are plain, not bold; values carry a stray leading colon from the field label.
- The two-step conditions are one plain paragraph above the grid (two wrapped lines); the scheme arrow, the 1 + 2 reactant row and the "4" product are not drawn.
- The footnote is left-aligned at the foot of the page, not centred under the grid.
- MeO and OMe on 4ca are drawn out as O-Me ether chains, not as abbreviation labels.
- The Blue LEDs text is black; the crop has it in blue.
- Ring orientation differs from the crop for several entries (the lactam ring and the benzyl or ethyl arm are drawn in other positions); the stereocentre wedges are present.
- Structures 1 and 2 are not drawn: they are not visible in the crop.

## Tool gaps

- The scope kind takes only the base preset: `style.skipped` reads "house conventions apply to schemes only". Card conventions for scope figures (bold labels, abbreviations, yield placement, centred footnote) therefore cannot be tested through `draw_figure` at all.
- No way to combine a scheme header (reactants, one arrow with conditions above and below, one product) with a scope grid in one panel.
- No grid control: no column count or row count, so 4 + 4 cannot be requested directly.
- The field label defaults to the field key ("result:"); a blank label leaves a leading colon. A field-level value format (for example the yield and ee joined by ", ") is not available.
- No per-span text colour in the conditions or footnote text, so the blue Blue LEDs cannot be drawn.
- No footnote alignment option (centred under the grid).
- No abbreviation pass for scope structures (MeO, OMe).
- Runtime: `draw_figure` took 220 to 300 s on this machine; `--render` timed out at 300 s on two of three tries. Drawing without `--render` and then running `cdx.py render` on the page worked.
- The scope kind rejects the `max_width` key that the scheme brief accepts.

## Audit

Second-agent audit against `reference.png`, `rendered.png`, `brief.json` and the card `org_lett.json`. One of the four matched rows (kekule) was an overclaim, and two partial rows are no; the corrected count is below.

- Matched count: 3 of 13 rows (yield format `{value}%`, selectivity format `{value}% ee`, substrate colours all black). The earlier 4 included kekule. The paper draws one ring (4ca) and writes Ph and Bn as abbreviations; the replica draws full rings for them.
- The yield line and the wedge row were marked partial; both are no. The yield line has the stray colon and is not centred under the label. The wedge sits on the substituent bond, and the N bond is plain.
- Grid packing in `rendered.png` is 3 + 2 + 3 (row 2 holds 4da and 4ea), not 3 + 3 + 2.
- `brief.json` sets the field label to one space (`" "`), not a blank string. The colon remains because the separator is still written.
- The 4ea chain has eight CH2 between the alkene CH and the stereocentre (RDKit on the SMILES; the reference bracket "7" plus one CH2). The "vinyl plus seven CH2" wording undercounts. The drawing matches the SMILES.
- Gaps the replicator did not list: (a) the scope kind always draws a title, and a blank title falls back to "Substrate scope" (`toolkit/cdxml_toolkit/mcp_runtime/figure_scope.py`, line 140), so it cannot be removed; (b) `SCOPE_KEYS` (line 24) takes only `width_mm` and `height_mm`, so the house bond length, line width and label size cannot be set; (c) no control over which bond carries the wedge or over ring orientation (the paper has N below the stereocentre); (d) conditions are one string with no explicit line break, and they wrap mid-word ("Blue LED" / "s 573 mW"); (e) labels and values are left-aligned at a fixed offset, not centred under each structure; (f) Ph, Bn and BnO are not abbreviated, only MeO and OMe are in the list.
- Not checked: proportions and line weight were not measured numerically. The stereo labels (all S) agree with RDKit on the SMILES; the paper's absolute configuration is unverified. The render timeout was not reproduced.
