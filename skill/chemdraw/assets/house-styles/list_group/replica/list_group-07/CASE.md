# List group: free-energy profile, Figure 4e (energy_profile)

Source: List et al., "Catalytic asymmetric synthesis of cannabinoids and menthol from neral", *Nature* **2023**. DOI: [10.1038/s41586-023-05747-9](https://doi.org/10.1038/s41586-023-05747-9). Licence: CC BY 4.0. The reference crop `reference.png` is `evidence/list_group-07.png`. It shows panel e (the energy profile) in full, the edge of panel f at the right, and above panel e a 2H NMR spectrum in a dashed box with a fragment of panel c at the top right. Only panel e is in scope.

Drawing style: `list_group` house-style card, `figure_types.energy_profile` section (base preset `nature`).

Figure type: `energy_profile`. The card has no drawer for this type.

## What is reproduced

Nothing. The crop has no 2D structures that can be expressed as a `draw_figure` brief:

- the species appear only as labels (`1+ cat.`, `A1`, `TS_AA`, `A`, `TS_AB`, `B`, `TS_BC`, `C1`, `D`, `C2`, `2+ cat.`), so there are no SMILES to write without guessing;
- the catalyst is not drawn as a structure;
- the only structure is the 3D transition-state model `TS_AB` (inset, magnified), which has no 2D drawing or SMILES.

"Not drawn" means the replicator did not draw the figure with `draw_figure`, which has no energy-profile kind. It does not mean the toolkit cannot draw it: `compose_chemical_figure` places text, lines, rectangles and ellipses at explicit coordinates, so the level diagram can be assembled by hand. The gaps that remain are listed under Tool gaps and Audit.

The energy values read from the crop are recorded below so the figure can be redrawn by hand or with a plotting tool. They are not a replica. They were checked against the bar heights in `reference.png`: with the 0.0 level at y = 202 px and 16.25 px per kcal mol-1, every bar sits at its printed value.

| species | label as printed | ΔG (kcal mol-1) as printed |
| --- | --- | --- |
| 1+ cat. | bold navy | 0.0 |
| A1 | bold navy | −5.1 |
| TS_AA | bold navy | −3.7 |
| A | bold navy | −10.0 |
| TS_AB (magnifier) | bold navy, grey magnifier ring | −4.4 |
| B | bold navy | −6.0 |
| TS_BC | bold navy | −4.1 |
| C1 | bold navy | −17.4 |
| D | bold navy | −23.0 |
| C2 | bold navy | −14.2 |
| 2+ cat. | bold navy | −4.9 |
| TS_AB (caption under the 3D model) | black (sampled 0,0,0) | none |

The y axis runs from about +5 to −20 kcal mol-1 with labelled ticks at 0, −5, −10, −15 and −20. The top of the axis (+5) has no label. The y-axis title "Free energy (kcal mol-1)" is set vertically. The x axis is labelled "Reaction coordinate" with no ticks.

Colour check: the core colour of the navy labels is about #00007F to #000080 (sampled; anti-aliasing lightens the edges). This is within six levels of the card's #000086.

## Convention table

The card claims 9 figure-type conventions and signature features for `energy_profile`, plus the top-level compound-label face and colour, which are visible on the species labels. The replica column is "not drawn" for every row because no figure was produced, so no row can match.

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| energy_unit kcal/mol (axis reads "kcal mol-1") | y-axis title uses "kcal mol-1" (the card writes "kcal/mol": same unit, different notation) | not drawn | no (not drawn) |
| energy_label delta_G | y-axis title "Free energy (kcal mol-1)"; values printed without Δ | not drawn | no (paper contradicts the card's delta_G) |
| level_style bars_dashed_connectors | short thick black bars (about 37 px long, about 3 px thick at 900 px width), dashed connectors | not drawn | no (not drawn) |
| pathway_colors null | one pathway, all black bars | not drawn | no (not drawn) |
| ts_marker none | TS labels with no bracket or double dagger | not drawn | no (not drawn) |
| intermediate_label_style bold_letter | bold A, B, C1, C2, D; subscript digits in A1, TS_AA, TS_BC and TS_AB | not drawn | no (not drawn) |
| signature: short thick black bars joined by thin dashed lines | yes | not drawn | no (not drawn) |
| signature: bold navy #000086 labels above, values below each bar | yes for the species labels (core colour about #00007F to #000080, see Colour check); values are black; the TS_AB caption under the inset is black, not navy | not drawn | no (not drawn) |
| signature: y axis "Free energy (kcal mol-1)", x axis "Reaction coordinate" | yes | not drawn | no (not drawn) |
| top-level compound_label_face bold | species labels bold | not drawn | no (not drawn) |
| top-level compound_label_color #000000 | species labels navy, not black; TS_AB caption black | not drawn | no (paper contradicts the top-level colour for this figure type) |

Replica matched: 0 of 11 claimed, and 0 of 11 on audit (nothing drawn).

## Probe result

`brief.json` sets `"kind": "energy_profile"` with the card style `list_group` and empty `species` and `steps`. The replicator reported that `cdx.py draw brief.json <scratch>/figure.cdxml --render` refused it with `tool_business_error`. The case folder keeps no log, so the duration and the error label cannot be checked from here.

The refusal text is the one in `toolkit/cdxml_toolkit/mcp_runtime/figure_draw.py` (`_validate`): "kind 'energy_profile' is not available yet; only 'scheme', 'scope' and 'mechanism' can be drawn." The audit re-ran `replay.py` offline, with output to a temporary folder. Its `validation.json` reports `ok: false` with that kind error, plus errors for the empty species and the empty steps. No `figure.cdxml` or PNG was written, so `rendered` is false.

## Differences from the paper

The paper figure is not reproduced. There is no drawn energy diagram, no species structures, no 3D TS inset and no magnifier ring.

## Tool gaps

- No energy-profile kind in `draw_figure`. It accepts only `scheme`, `scope` and `mechanism`. An energy profile needs a level-diagram kind: one bar per species, dashed connectors, labels above each bar, values below, and axes with the card's titles.
- No picture or 3D model item in the drawing tools, so the TS_AB inset cannot be placed. The inset has no 2D drawing or SMILES.
- The magnifier ring can be drawn with `compose_chemical_figure` (see Audit). The angled dark-teal handle cannot.
- Species label colour in `draw_figure` changes only through a house card's `compound_label_color`, which applies to every compound label of that card. It cannot be set per figure type or per label.

## Audit

Audit of 2026-11-07. The table and notes were checked against `reference.png`, `brief.json`, the card `toolkit/cdxml_toolkit/publication/house_styles/list_group.json` and the toolkit code. Every "no" in the match column stands. Corrections:

Overclaims in the earlier version:

1. "No way to place ... a magnifier ring" was wrong. An `ellipse` item in `compose_chemical_figure` with fill none and a grey hex colour draws the ring. Only the angled handle is missing.
2. "No level-diagram layout" was presented as a tool limit. The primitives exist. The missing pieces are the energy-profile layout and the house conventions.
3. "see card_errors" pointed to nothing. The card has no such field or section, so the reference is removed.
4. "refused after about 257 s" and the `tool_business_error` label could not be verified from the case folder. The timing is removed. The message text is confirmed by the re-run.
5. The crop description omitted the NMR spectrum, the panel c fragment and the top-right edge detail. It is corrected above.
6. The species labels "1 + cat." and "2 + cat." are printed as "1+ cat." and "2+ cat.". The y-axis title is "Free energy (kcal mol-1)", not "Free energy".
7. "Exact hex not measured" is now measured (see Colour check). The navy is consistent with #000086.
8. "Species labels navy" omitted that the TS_AB caption under the 3D inset is black.

Confirmed as stated: no 2D structures to draw, the energy values (checked against bar heights), no energy-profile kind in `draw_figure`, the refusal message (re-run), no `rendered.png`, and the 11 rows marked "no".

Corrected matched count: 0 of 11.

Tool gaps the replicator missed, verified in code:

- `compose_chemical_figure` (`cdx.py call compose_chemical_figure`; manifest schema in `skill/chemdraw/references/publication-figures.md`) draws by coordinates. Its `text` items take runs with bold, subscript, superscript and a colour per run (`toolkit/cdxml_toolkit/mcp_runtime/figure_tools.py`, text helper near line 788). Its `line` items are solid with no arrowhead. `rectangle` items with a solid fill can serve as thick bars. `ellipse` items with fill none draw the magnifier ring. Object fields are near line 905 and the drawing branches near lines 1169 to 1293.
- Gaps inside that composer which the replicator did not list:
  - text cannot be rotated, so the vertical y-axis title has no route;
  - a dashed line without an arrowhead is not possible: style `dashed` sets `LineType` Dashed but keeps the head, and style `line` is solid;
  - there is no per-object line weight, since every line takes the document `LineWidth`, so the thick bars and the thin connectors cannot differ;
  - rectangles and text cannot rotate, and `curve` has no fill, so the angled filled magnifier handle cannot be drawn;
  - there is no picture or embedded-object item, so the 3D TS_AB inset cannot be placed.
- `draw_figure` species label colour is set through the house card's `compound_label_color` (`toolkit/cdxml_toolkit/mcp_runtime/figure_house.py`, lines 278 to 282), which is house-wide, not per label.
- Routes outside the tool list: the `Drawing` class in `toolkit/cdxml_toolkit/scientific/common.py` has dashed lines, per-object colour and filled rectangles, but no drawing tool exposes it for figures. `cdx.py scientific plot` (`toolkit/cdxml_toolkit/scientific/plots.py`, `plot_xy`) draws XY series into a fixed 600 x 300 CDXML layout with no per-point labels, so it is only a coarse fallback.

Card issues, not replica issues: `energy_label` "delta_G" is contradicted by the paper (no Δ on the values), `energy_unit` "kcal/mol" differs in notation from the printed "kcal mol-1", and the top-level `compound_label_color` #000000 contradicts the navy species labels this figure type uses.
