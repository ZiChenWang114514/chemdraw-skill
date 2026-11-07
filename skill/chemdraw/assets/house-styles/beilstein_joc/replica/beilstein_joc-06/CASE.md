# Beilstein JOC: free-energy diagram of the hypophosphite reductive amination (Figure 2, top)

Source: E. Chusov et al., "Influence of the cation in hypophosphite-mediated catalyst-free reductive amination", *Beilstein J. Org. Chem.* **2025**, *21*, 130 (DOI [10.3762/bjoc.21.130](https://doi.org/10.3762/bjoc.21.130)). The DOI and the figure caption ("Reaction profile and DFT energies of intermediates and transition states", M062X/6-311+G(d,p), model reaction of dimethylamine and benzaldehyde promoted by hypophosphorous acid) were checked against the article XML in `D:\workspace\chemdraw-papers\house-beilstein_joc-4`.

Licence: CC BY 4.0, © the authors; the reference crop is reproduced under that licence.

Drawing style: the `beilstein_joc` house style (card `toolkit/cdxml_toolkit/publication/house_styles/beilstein_joc.json`, `energy_profile` section), base preset `nature`.

## What is reproduced

Nothing is drawn. The crop is only the energy plot: bars, dashed connectors and energy labels, with no chemical structure. The structure boxes under the plot are in the full Figure 2 of the paper, not in this crop (the crop stops above them). `draw_figure` has no drawer for this plot, so no replica image was made (`rendered: false`). The manifest tool `compose_chemical_figure` could draw it from explicit coordinates; that route was not tried for this case.

The probe in `brief.json` asks `draw_figure` for `kind: "energy_profile"`. `replay.py` re-runs it and the tool refuses the brief with `kind 'energy_profile' is not available yet; only 'scheme', 'scope' and 'mechanism' can be drawn.` No `figure.cdxml` is written.

Values read from the crop (kcal/mol, delta G as printed):

| State | Colour | Value | State | Colour | Value |
| --- | --- | --- | --- | --- | --- |
| Step_1 | blue | 0.0 | Step_2' | orange | 30.9 |
| Step_2 | blue | -2.6 | TS2→3'' | red | 32.1 |
| TS2→3 | blue | 8.9 | Step_3'' | red | 3.3 |
| Step_3 | blue | 6.2 | | | |
| Step_4 | blue | 0.9 | | | |
| TS3→4 | blue | 43.8 | | | |
| TS4→5 | blue | 28.5 | | | |
| Step_5 | blue | -26.8 | | | |

Pathway colours sampled from the crop pixels: blue about #0000FF, orange about #FF7F00, red #FF0000.

## Convention check (card claims against the crop)

The replica column is "not drawn" everywhere, so the match column is "not reproduced". The crop column records what the crop itself shows.

| convention or signature feature | paper (crop 06) | replica | match |
| --- | --- | --- | --- |
| energy_unit kcal/mol | y-axis title "Gibbs Free Energy (kcal/mol)"; bare values | not drawn | not reproduced (crop agrees) |
| energy_label delta_G | no ΔG symbol on any value; only the axis title | not drawn | not reproduced (card value wrong: the crop shows no delta G) |
| level_style bars_dashed_connectors | short thick bars, thin dashed connectors in pathway colour | not drawn | not reproduced (crop agrees) |
| pathway_colors blue, orange, red | blue main, orange and red side paths; sampled pixels within a few units of the card | not drawn | not reproduced (crop agrees) |
| ts_marker none | TS states named with subscript arrow; no brackets, no double dagger | not drawn | not reproduced (crop agrees) |
| intermediate_label_style none | every state carries a name (Step_1 etc.), no numbering | not drawn | not reproduced (ambiguous: names are on every state; 'none' fits only as 'no numbering') |
| signature: short thick bars joined by thin dashed pathway-coloured lines | yes | not drawn | not reproduced (crop agrees) |
| signature: energy values italic above each bar; state names bold, pathway colour, below | values italic and above their bars; but the Step_3 name sits above its bar, between 6.2 and the bar, not below | not drawn | not reproduced (crop partly disagrees) |
| signature: y axis titled Gibbs Free Energy (kcal/mol) in italics; x axis an arrow without ticks | yes | not drawn | not reproduced (crop agrees) |
| signature: state structures in coloured boxes under the plot, grouped in dashed rounded frames | not in crop; the 'square-cornered' remark cannot be checked here | not drawn | not reproduced (not in crop, unverifiable) |
| top-level compound_label_face bold | state names are bold | not drawn | not reproduced (crop agrees) |
| top-level label_font Arial-like sans-serif | sans-serif throughout | not drawn | not reproduced (crop agrees) |

Claimed: 10 energy-profile items (6 conventions, 4 signature features) plus 2 top-level items that the crop shows. Matched in the replica: 0 (nothing is drawn). Against the crop alone, 6 of the 10 energy-profile claims hold, 1 holds only in part (the values and name-placement signature), 1 is wrong (energy_label), 1 is ambiguous (intermediate_label_style), and 1 cannot be checked on this crop (structure boxes). Both top-level items hold.

## Differences from the paper

- The whole figure is missing: no bars, connectors, labels or axes are drawn.
- The paper's structure panel under the plot (boxes for Step_1 to Step_5, TS and side states, in frames) is not reproduced; it is not in crop 06.
- The black × marks on the orange and red connectors near Step_1 are not reproduced, and the caption does not explain them.
- The primes on side-pathway states (Step_2', TS2→3'', Step_3'') are not reproduced.

## Tool gaps

- `draw_figure` has no `energy_profile` kind; it accepts only `scheme`, `scope` and `mechanism`. Confirmed by re-running `replay.py`.
- Not a gap: thick level bars can be drawn as `rectangle` objects with `fill_type` `solid`; dashed connectors in a chosen colour are `interaction` objects with `style` `dashed` (code read, not tested); numeric labels are `text` objects; italic and subscript runs are supported. These are in `compose_chemical_figure` (manifest route), which the replicator did not try.
- Not a gap: a dashed rounded frame is a `rectangle` with `dashed` true and `round_edge` true, and a coloured box is a `rectangle` with a fill. Tested: the output CDXML carries `LineType="Dashed"` and `RectangleType="RoundEdge"`.
- Real gaps: `text` has no rotation field, so the vertical y-axis title cannot be set; there is no per-object line width (bar thickness must come from rectangles); `line` or `arrow` with `style` `dashed` gets an arrowhead (use `interaction` for a plain dashed connector); the composer gives no visual check (`native_render` not run), so proportions are unverified; every position is hand-placed.
- Infrastructure note, not verified in the audit: the claimed stall of `cdx.py draw` under load was not reproduced.

## Replay

```
python skill/chemdraw/scripts/cdx.py py skill/chemdraw/assets/house-styles/beilstein_joc/replica/beilstein_joc-06/replay.py NEW_DIR
```

`replay.py` writes `validation.json` with the refusal and no CDXML.


## Audit

Checked against reference.png (enlarged crops), the card, and the toolkit code. Tests were run only in a temporary folder.

- Overclaims corrected: energy_label is wrong (no ΔG in the crop); the 'state names below' signature fails for Step_3; 'see card errors' pointed to a section that did not exist; 'square-cornered' cannot be checked from the crop; 'no drawer, so no replica' overstated the options.
- Replicator's tool gaps: the draw_figure refusal is real. Gaps 2 and 4 are largely wrong (see Tool gaps). Gap 3 is partly wrong: numeric axis labels and italic runs are possible; the real missing piece is text rotation.
- Corrected counts: matched in the replica 0 (nothing drawn). Against the crop, 6 of 10 energy-profile claims hold, 1 partly, 1 wrong, 1 ambiguous, 1 unverifiable.
