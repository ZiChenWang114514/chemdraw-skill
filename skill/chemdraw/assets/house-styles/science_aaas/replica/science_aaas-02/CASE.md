# Science Advances: TIPS-alkynoate amidation with an amine (Fig. 4, header scheme)

Source: Choudhary, Zhang and Lin, *Sci. Adv.* **2024**, *10*, eadp7544. DOI: [10.1126/sciadv.adp7544](https://doi.org/10.1126/sciadv.adp7544). Licence: CC BY 4.0 (per the house-style card). The reference crop is reproduced under that licence.

House style: `science_aaas` (`toolkit/cdxml_toolkit/publication/house_styles/science_aaas.json`, base preset `nature`).

## What is reproduced

The header reaction of Fig. 4 (scope of bioactive amines): ethyl 3-(triisopropylsilyl)propiolate (1) plus an amine (2) in PBS buffer (pH 7.0) / EtOH (4:1), 40 °C, 48 hours, giving the amide (3). The paper keeps the amine generic (R). `draw_figure` needs concrete structures, so the representative amine is the first scope entry shown in the crop, 3ae (Boc-lysine tert-butyl ester, 2ae), and the yield is that entry's 88%. The six-entry scope rows below the header are a different figure kind (scope panel) and are not drawn here.

| ID | Structure (SMILES in brief.json) | Check |
| --- | --- | --- |
| 1 | `CCOC(=O)C#C[Si](C(C)C)(C(C)C)C(C)C` | RDKit formula C14H26O2Si |
| 2ae | `CC(C)(C)OC(=O)[C@H](CCCCN)NC(=O)OC(C)(C)C` | RDKit CIP S (L-lysine), read as the amine in the 3ae row |
| 3ae | `CC(C)(C)OC(=O)[C@H](CCCCNC(=O)C#C[Si](C(C)C)(C(C)C)C(C)C)NC(=O)OC(C)(C)C` | RDKit CIP S; readback matched, 3 structures drawn |

## Replay

```
python skill/chemdraw/scripts/cdx.py py skill/chemdraw/assets/house-styles/science_aaas/replica/science_aaas-02/replay.py NEW_DIR
python skill/chemdraw/scripts/cdx.py render NEW_DIR/figure.cdxml
```

`brief.json` is the input; `reference.png` is the crop; `rendered.png` is the desktop ChemDraw render downscaled to 1200 px wide.

## Convention check

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| compound labels bold | bold numbers (1, 2, 3ae) | bold labels (report: `compound_label_face=bold`) | yes |
| compound label colour black, no italic suffix | black, plain suffix | black, `3ae` without italic suffix | yes |
| yield after product label, `88%`, separator `, ` | `3ae, 88%` | `3ae, 88%` | yes |
| incoming component blue in reagents and products | blue amine fragment in 2 and in 3 | whole amine 2ae blue (Boc and tBu ester included); product 3ae all black | no |
| reagent text black | black | conditions and solvent black; the `2ae` label appears blue in rendered.png, and the card's `compound_label_color` is black, so the code does not paint labels | no |
| plain arrow | plain | plain | yes |
| solvent above the arrow, temperature and time below | solvent above, `40 °C, 48 hours` below | same placement | yes |
| `A + B` inline with `+` | inline | inline | yes |
| abbreviate `TIPS` | `TIPS` | `Si(iPr)3` drawn in full | no |
| abbreviate `OEt` | `OEt` | ethyl drawn in full | no |
| abbreviate `NHBoc`, `O-tBu` | `NHBoc`, `O^tBu` | drawn in full | no |
| new C-N amide bond red and bold (`#F40405`) | red, bold | black, regular weight (`new_bond_color` null in card) | no |
| time unit `hours` kept | `48 hours` | `48 h` (rewritten by the tool) | no |
| kekule rings | not present in this scheme | not present | not exercised |
| abbreviate `OMe`, `CF3` | not present in this scheme | `abbreviate_groups (0 contracted)` | not exercised |
| bond length, line width, arrow length ratios | measured in the crop (47 px bond, 2 px line, 721 px arrow) | not reported; figure.cdxml and validation.json are not in this folder | not verified |

Claimed rows checked: 14. Matched: 6 after audit (the original table had 7 `yes` rows, not 8). Not exercised rows are not counted. See Audit.

## Differences from the paper

- The generic amine R is replaced by the lysine derivative 3ae (2ae in the scheme) so the tools have concrete structures. The paper's header shows R.
- Abbreviations are spelled out: TIPS as Si(iPr)3, OEt as the ethyl group, NHBoc and O-tBu as full structures.
- The incoming amine is coloured blue as a whole species, so the Boc and tert-butyl ester of 2ae are blue too. The paper colours only the amine fragment, and it also colours the amine fragment in the product. The product 3ae is drawn all black.
- The new amide C-N bond is black and regular weight. The paper draws it red and bold.
- The time reads `48 h`, not `48 hours`.
- The ethanol by-product of the ethyl ester is not drawn. The tool reports the step as not balanced and names ethanol. The paper also omits it, so the warning is correct and the drawing matches the paper on this point.
- Only the header reaction is drawn, and the scope rows below it are omitted.

## Tool gaps

- `draw_figure` contracts only the card's `abbreviate_groups` (here OMe and CF3). A brief has no field to request a particular abbreviation such as TIPS, OEt, NHBoc or O-tBu.
- `substrate_colors` colours whole species. There is no way to colour only the incoming fragment of a substrate, nor to colour the matching fragment of the product.
- A new-bond colour exists (`new_bond_color` in `figure_house.py`); the card sets it to null, so the red colour is not applied. What is missing is a bold option for the bond (see Audit).
- The tool rewrites `hours` to `h` in conditions. The brief cannot keep the unit as written.
- The report gives no arrow length or line width, so the measured ratios cannot be checked from the report.
- The card has no `figure_types` section, so no reaction_scheme-specific conventions are applied. The report's `style.applied` list shows only the top-level conventions.

## Card observations

- The `science_aaas` card has no `figure_types` section and no `crops` list, so the reaction_scheme entry this replica was asked to check is not defined in the card. The top-level conventions were used.
- `abbreviate_groups` lists only OMe and CF3, but the evidence observations for `science_aaas-01` and `-02` say TIPS, OEt, NHBoc and OtBu are abbreviated.
- `new_bond_color` is null, but `science_aaas-01` records a red new C-N bond (`#F40405`), and this crop (`science_aaas-02`) shows the same red bold bond.
- The README lists "solvent above or below" as unsettled. This crop puts the solvent above and temperature and time below, which matches `science_aaas-01`.
- `bold_width_over_bond_length` is null in the card, but `science_aaas-02` records `bold_width` 20 px against a 47 px bond (about 0.43).

## Audit

Checked against reference.png, rendered.png, CASE.md, brief.json, the card JSON, and the toolkit code (`mcp_runtime/figure_house.py`, `figure_draw.py`, `publication/house_styles.py`, `text_formatting.py`).

- Matched count: the original table had 7 `yes` rows, not 8. The `2ae` label and the reagent row were also wrong, so the corrected count is 6 of 14 (bond ratio row counted as not verified).
- Reagent text black: marked no, because the `2ae` label appears blue at render size.
- Bond, line and arrow ratios: never measured. The report, figure.cdxml and validation.json are absent from this folder, so the report-based claims (label face, abbreviation count, style applied list) cannot be checked from files.
- Tool gap "no new-bond colour option" is wrong: `figure_house.py` applies the card's `new_bond_color` through `_color_new_bonds`. The card value is null, so this is a card setting. The real gap is the bold width of the new bond, which no option provides.
- NHBoc is already in `ABBREVIATIONS` (`publication/house_styles.py`), so adding it to the card's `abbreviate_groups` would work. TIPS, OEt and O-tBu have no table entry, so they need code changes, not only a brief field.
- Hours rewrite: confirmed. `normalize_condition_text` (`text_formatting.py`) runs on scheme conditions in `render/renderer.py`, with no brief or card bypass.
- Card arithmetic: `arrow_length_over_bond_length` is 12.82 in the card, but the crop gives 721/47, about 15.3. `line_width_over_bond_length` is 0.052 in the card, but 2/47 is about 0.043.
- Missed tool gaps: no bold bond option; no per-fragment colour of the product (substrate colour paints whole species, `figure_house.py:333-346`); no per-species compound-label colour (label colour is global, `figure_house.py:278-282`); no way to keep a drug name after the yield on the label line; `draw_figure` returns no arrow length or line width in the report.
