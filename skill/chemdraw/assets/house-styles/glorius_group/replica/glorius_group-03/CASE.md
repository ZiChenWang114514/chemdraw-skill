# Glorius group: substrate scope, formal [3+2] of isoxazolone 1a with alkenes (Figure 4, top)

Source: Glorius et al., *J. Am. Chem. Soc.* **2025** (cyclic bifunctional reagents enabling a strain-release-driven formal [3+2] cycloaddition). DOI: [10.1021/jacs.4c18080](https://doi.org/10.1021/jacs.4c18080). Licence: CC BY 4.0, reference crop reproduced under that licence. The house style is the `glorius_group` card (`toolkit/cdxml_toolkit/publication/house_styles/glorius_group.json`, `substrate_scope` section); the crop is `evidence/glorius_group-03.png`.

Figure type: `substrate_scope`.

## What is reproduced

Six entries of the alkene scope, from the `Alkenes` section of the panel, drawn with `draw_figure` (`kind: "scope"`, base preset `acs1996`):

| Entry | Structure (SMILES in `brief.json`) | Yield in the paper |
| --- | --- | --- |
| 3a | `CC1(C)N=C(c2ccccc2)CC1C#N` | 69% (70%) |
| 3b | `CC1(C)N=C(c2ccccc2)CC1C(=O)OCc1ccccc1` | 30% (31%) |
| 3d | `CC1(C)N=C(c2ccccc2)CC1C(=O)OCc1cccc(C(F)(F)F)c1` | 32% (36%) |
| 3g | `CCOC(=O)C1CC(c2ccccc2)=NC1(C)C` | 34% (42%) |
| 3h | `CC1(C)N=C(c2ccccc2)CC1C(=O)OC(C(F)(F)F)C(F)(F)F` | 44% (50%) |
| 3i | `C#CCOC(=O)C1CC(c2ccccc2)=NC1(C)C` | 22% (32%) |

The conditions line (`Ir-F (1 mol%), PhCF3 (0.1 M), blue LEDs (λmax = 450 nm), RT, 3 h`) is copied from the top scheme and placed as one line under the title.

The structures were read from the crop and checked with RDKit: all six are 2,2-dimethyl-5-phenyl-3,4-dihydro-2H-pyrrole-3-carboxylates or -carbonitriles, with the C=N next to the phenyl group and the gem-dimethyl carbon next to N. The isoxazolone 1a was read as `CC1(C)C(=O)ON=C1c1ccccc1` (4,4-dimethyl-3-phenylisoxazol-5(4H)-one). Racemic C3; no stereodescriptor is in the crop and none is drawn.

Not reproduced:

- the top scheme (1a + 2 gives 3 with Ir-F above the arrow and PhCF3, blue LEDs, RT, 3 h below); `draw_figure` `scope` has no slot for a general scheme, and the generic alkene 2 and product 3 carry coloured substituent dots that no drawer can place;
- the `[X-ray]` entry, which is an ORTEP-style crystal structure image and not a drawable structure;
- entries 3c (4-I), 3e (2-CH3) and 3f (4-OMe): the crop shows 3b to 3f as one generic benzyl ester with an R list (`R = H, 3b, 30% (31%)` ...), which the tool cannot express; 3b and 3d were drawn as separate compounds to show the R series;
- the `Alkenes` section tab, the dashed separator rule and the `(continued)` heading are not drawn in the house form.

Layout note: the scope packer put the six entries on one page as a 3 x 2 grid. The paper uses a single row (3a, X-ray, the R series, 3g, 3h, 3i).

## Replay

```
python skill/chemdraw/scripts/cdx.py py skill/chemdraw/assets/house-styles/glorius_group/replica/glorius_group-03/replay.py NEW_DIR
```

`replay.py` calls `draw_figure` on `brief.json` offline and writes the scope folder `NEW_DIR/figure.cdxml/` (`page-001.cdxml`, `page-001.manifest.json`) and `validation.json`. `rendered.png` was rendered from `page-001.cdxml` with `cdx.py render` (desktop ChemDraw), then downscaled from 1783 to 1200 px wide. `reference.png` is the crop.

## Convention check

Rows cover every convention the card claims for `substrate_scope`, plus the top-level conventions visible in the crop. "yes" means the replica matches; "partial" means the convention is present in a weaker form (counted as not matched); "no" means absent.

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| scope_layout `grid_with_core` | grid of products under a general scheme, R series as one core with a list | 3 x 2 grid of full structures, no general scheme, no R-series core | partial |
| conditions_position `scheme_on_top` | Ir-F above arrow, PhCF3 / blue LEDs / RT / 3 h below | one text line under the title | no |
| yield_format `{value}%` | `69%`, `(70%)` | `yield: 69% (70%)`; the `yield:` prefix is the field's default label and was not removed (an empty label removes it, see Audit) | partial |
| selectivity_format `{value} d.r.` | not in this crop (no d.r. shown) | not drawn | n/a, excluded from the claim count |
| highlight_fill `#73EDB0` (mint section tab) | mint tab behind `Alkenes` | none | no |
| variation_color `null` | n/a | n/a | n/a |
| signature: general scheme on top with coloured dots marking substituent positions | present | absent | no |
| signature: substrate class as bold italic label on mint tab, dashed separator | `Alkenes` on mint tab, dashed rule | plain text `Alkenes` heading, no rule | no |
| signature: conserved core dark green `#0B5234`, pale grey fill `#DEE2E5` | ring bonds and N dark green, grey ring fill | all black, no fill | no |
| signature: yield line `3a, 69% (70%)`, isolated then NMR yield in parentheses | inline with the bold label | yield on its own line under the label | partial |
| compound_label_face `bold` | bold `3a` | plain `3a` (face 0) | no |
| compound_label_color `#000000` | black | black | yes |
| yield_placement `after_product_label` | `3a, 69% (70%)` | separate line | no |
| yield_separator `", "` | comma | no separator | no |
| aromatic_rings `kekule` | Kekule rings | Kekule rings | yes |
| abbreviate_groups (CN, CO2Et, OEt, CF3) | `CN`, `CO2Et`, `OEt`, `CF3` | expanded: N triple bond, C(=O)OCC, C(F)(F)F | no |
| reagent_text_color `#000000` | black conditions | black conditions | yes |
| arrow_style `plain` | plain arrow in the top scheme | no arrow drawn | no |
| show_plus_sign `true` | `+` between 1a and 2 in the top scheme | no plus drawn | no |
| line width over bond length `0.075` | about 0.078 measured on crop 01; 0.063 on this crop (5 / 80 px) | 0.6 pt over 14.4 pt = 0.042 (base preset) | no |
| bond length over label cap height `2.2` | 2.3 on this crop (80 / 35 px) | about 2.0 estimated (14.4 pt bond over about 7.2 pt Arial cap height, which is 0.716 em at the acs1996 LabelSize of 10 pt; not measured on the render) | partial |

Matched: 3 of 19 claimed rows (rows counted as claimed: 4 figure-type claims, 4 signature features, and 11 top-level or measured conventions; `selectivity_format` and `variation_color` excluded). Partial rows: 4.

## Differences from the paper

- No general scheme on top: the conditions are one text line under the title, not split above and below an arrow.
- The conditions are plain text: `PhCF3` and `λmax` lack the subscripts of the paper, and `Ir-F` is not bold.
- A `Substrate scope` heading is printed above the panel. It is the tool's default title (used because the brief title is empty), and the paper has no such heading.
- Yields are on their own line with a `yield:` prefix instead of `3a, 69% (70%)`. The prefix is the field's default label; it can be removed (see Audit).
- Compound labels are plain, not bold.
- Groups are drawn in full (CN as a nitrile, the esters with ethyl and benzyl groups written out), not as abbreviations.
- Ring bonds and nitrogen are black; the core has no dark green colour and no grey fill.
- The `Alkenes` heading has no mint tab, no bold italic and no dashed separator.
- Only six of the nine structures are drawn; 3c, 3e, 3f and the X-ray entry are omitted.
- Bond length (14.4 pt) and line width (0.6 pt) are the acs1996 base values; the house line width ratio is not applied.

## Tool gaps

- `kind: "scope"` applies only the base preset. The draw report says `style.applied: []` and `skipped: ["house conventions apply to schemes only; the base preset was applied"]`, so none of the `substrate_scope` conventions (label face, yield placement, abbreviations, colours, tabs) reach a scope panel.
- A scope panel has no general-scheme slot above the grid. `conditions` is a single text line; there is no reagent-above/solvent-below split and no arrow.
- No section-heading style for scope groups: `group` becomes a plain text heading. Mint tabs, bold italic headings and dashed separators are not available.
- The `yield` field prints as `label: value`, and the label defaults to the field key. An empty `label` in `fields` prints the bare value (`publication/data.py`, `field_text`), so the prefix can be removed; this render did not do so. The value cannot be placed inline after the compound label, because the label and each field are separate text objects (`publication/layout.py`).
- No `draw_figure` option places coloured substituent dots at variable positions (general scheme, product core). This was checked against the `draw_figure` path only.
- An R-series given as one generic structure with a list of R groups and values (the 3b to 3f block) has no representation; each R variant has to be a separate species.
- Crystal-structure (ORTEP) pictures cannot be drawn; the entry can only be left out or stood in for with a text box.
- Scheme drawing failed in this runtime: `draw_figure` with `kind: "scheme"` returned `worker_crashed` (exit code 143) after about 196 s on three attempts: the house-style 1a + acrylonitrile to 3a scheme, the same without `style`, and a minimal two-substrate ester brief without any conditions. The scope kind worked (5 s without render). Because of this the house scheme conventions (bold labels, `after_product_label` yields, abbreviations, `conditions_split`, `show_plus_sign`) could not be tested on a scheme rendering.
- First attempt with `--render` on the scope brief hit the 300 s tool timeout after writing the pages; a separate `cdx.py render` on the page then succeeded.

- The scope title defaults to `Substrate scope` (`figure_scope.py`: `brief.get("title") or "Substrate scope"`). An empty title cannot suppress the heading, and the paper has none.
- Conditions are a plain string on the scope path, with no subscript, superscript or bold markup, so `PhCF3`, `λmax` and bold `Ir-F` cannot be drawn as in the paper.
- Abbreviated groups (CN, CO2Et, OEt, CF3) cannot be requested on the scope path; the structures are drawn in full.
- Compound-label face is not settable: the scope spec has no label-style key, and the label face comes from the base preset.
- The house bond-length-to-cap-height ratio (2.2) is not settable on the scope path; only the base preset geometry is applied.
- Per-atom and per-bond colour (dark green core, pale grey ring fill, blue or red fragments) has no key in the scope spec or the brief.
- Layout is not controllable: the scope brief takes `width_mm` and `height_mm` only, with no column count, row count or single-row option, so the packer decides the 3 x 2 grid.

## Card observations (not fixed; reported only)

- `substrate_scope.conventions.highlight_fill` is `#73EDB0`, but that colour is the section tab. The tool's `highlight_fill` means a pastel fill behind the product ring, and the crop shows that ring fill as `#DEE2E5`. The card's own top-level note says "no single highlight".
- `selectivity_format` `{value} d.r.` and "d.r. after the yield" are claimed for this figure type, but this crop shows no d.r. value.
- `scope_layout` `grid_with_core` describes "a grid of products", but in the crop 3b to 3f are one generic benzyl ester with an R list, and only 3a, 3g, 3h and 3i (and the X-ray entry) are separate structures.


## Audit

Checked against both images, the card JSON (`toolkit/cdxml_toolkit/publication/house_styles/glorius_group.json`), the toolkit code (`mcp_runtime/figure_scope.py`, `mcp_runtime/figure_draw.py`, `publication/data.py`, `publication/layout.py`, `chemdraw/style_presets.py`) and RDKit. No drawing was rerun.

- Matched count: 3 of 19 holds. The three rows marked yes (compound label colour black, Kekule rings, black conditions text) are visible in both images. The other 16 are not matched: 4 partial and 12 no.
- Overclaim, yield prefix: "cannot be removed" is wrong. An empty field label prints the bare value (`publication/data.py`, `field_text`). The render kept the default label, so the yield row stays partial, but the reason is corrected above.
- Overclaim, cap-height ratio: "about 2.5 (14.4 pt over 8 pt)" was wrong arithmetic. The acs1996 label size is 10 pt and Arial cap height is about 0.716 em, giving about 2.0 against the 2.2 target. Still not matched.
- Undisclosed: the `Substrate scope` heading, the missing subscripts and the non-bold `Ir-F` were not in the table. They are now in Differences and Tool gaps.
- Confirmed: the line-width row (acs1996 BondLength 14.4 pt, LineWidth 0.6 pt, ratio 0.042). The scope path applies only the base preset (`figure_draw.py` reports `style.applied` as empty for scope).
- Confirmed: all six structures parse in RDKit and contain the same 2,2-dimethyl-5-phenyl-3,4-dihydro-2H-pyrrole core. The 3d CF3 is meta, 3h is a hexafluoroisopropyl ester, 3i is a propargyl ester, 3g is an ethyl ester, and 1a is 4,4-dimethyl-3-phenylisoxazol-5(4H)-one. The earlier RDKit claim had no saved check in the folder; this check is the first evidence for it.
- Not verified here: the `worker_crashed` (exit 143, about 196 s) scheme runs, the 300 s render timeout, the 5 s scope timing, and the provenance of `rendered.png` (desktop ChemDraw render, downscaled). No logs are in the folder, so these stay as the replicator reported them.
- Narrowed: the coloured-dot gap was checked only against `draw_figure`, so it no longer claims that no drawer can place dots.
