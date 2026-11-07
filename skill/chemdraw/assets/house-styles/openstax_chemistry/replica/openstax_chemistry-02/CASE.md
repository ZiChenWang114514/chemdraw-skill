# OpenStax Chemistry Figure 12.22: catalysed and uncatalysed energy profile (house style replica, not drawn)

Source: Flowers, Theopold, Langley, Robinson et al., *OpenStax Chemistry* (2015), section 12.7 Catalysis, Figure 12.22. DOI not given on the card. Licence: CC BY 4.0. Reference crop: `reference.png` (copy of `evidence/openstax_chemistry-02.png`, byte-identical by SHA-256).

Drawing style: the `openstax_chemistry` house style card (base preset `chemdraw_slide`); figure type `energy_profile`, crop 02.

## What is reproduced

Nothing. The crop is a reaction-coordinate diagram with two smooth curves, axis titles and text labels. It contains no molecules, no reagents and no reaction arrow, so there is no chemistry for `draw_figure` to draw. The brief for this crop (`brief.json`) has `style` set and empty `species` and `steps`. The replicator reports that `cdx.py draw brief.json out.cdxml` refused it with:

- `species: list every structure that is drawn, each with an id and a smiles or a name.`
- `steps: give at least one step with substrates and products.`

These are the messages the `draw_figure` validator (`toolkit/cdxml_toolkit/mcp_runtime/figure_draw.py`) produces for an empty brief. The `cdx.py` run itself was not repeated in the audit.

No `figure.cdxml` or `rendered.png` was produced. `replay.py` is a copy of the JACS Au replay script with a new docstring; it calls `draw_figure` and will hit the same refusal.

The refusal is specific to `draw_figure`, not a general limit. `compose_chemical_figure` (`toolkit/cdxml_toolkit/mcp_runtime/figure_tools.py`) accepts a manifest with only `text`, `arrow`, `line` and `curve` objects and no molecules. An audit probe with one arrow, one line, one four-point Bezier curve and one bold Arial text object was accepted by the tool (`ok: true`) and written as CDXML; the probe was run in the audit session and is not kept in the repository. The replicator did not use this route, because a layout drawn without a brief would invent geometry the brief does not specify. The crop is therefore undrawn because no geometry was specified, not because no tool can draw one. The `scientific plot` operation draws numbered, data-bound axes, which this crop does not have.

## Convention check (card against crop 02)

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| level_style smooth_curve | both curves are smooth, with no straight segments | nothing drawn | no |
| pathway_colors: uncatalysed red | red sampled at #BC2505 (median of the red pixels); the card's crop-02 observation gives #BC2404; the card's conventions field gives #BC4428 (crop 01) | nothing drawn | no |
| pathway_colors: catalysed blue | blue sampled at #4160F5; the card's crop-02 observation gives #4060F4; the card's conventions field gives #8894C8 (crop 01) | nothing drawn | no |
| ts_marker none | no marker on either hump | nothing drawn | no |
| intermediate_label_style none | second, smaller bump on the catalysed curve has no label | nothing drawn | no |
| unnumbered axes with arrowheads; bold axis titles Energy and Extent of reaction in Arial | rotated bold "Energy" on the vertical axis, bold "Extent of reaction" under a thin arrow that is broken around the title, no tick numbers or units | nothing drawn | no |
| Transition state, Reactants and Products as plain text with thin leader lines | "Uncatalyzed pathway" and "Catalyzed pathway" have thin leader lines; "Reactants" and "Products" are unlined; no "Transition state" label in this crop | nothing drawn | no |
| label font Arial or Helvetica | sans-serif, Arial-like | nothing drawn | no |
| reagent_text_color #000000 | labels black | nothing drawn | no |

Claimed: 9 rows. Matched: 0. The Ea double-headed arrows named in the card are not in crop 02 (they are in crop 01), so they are not counted here.

## Differences from the paper

- The whole figure is absent. No curve, axis, label or colour is reproduced.
- Colours: the crop-02 values in the card's observations (#BC2404, #4060F4) are within a few units of the sampled crop (#BC2505, #4160F5). The card's conventions field holds the crop-01 values (#BC4428, #8894C8), which differ more; see Card issues.
- Axes, measured from `reference.png` (650 x 567 px): the L-shaped plot frame is a vertical line at x of about 85 px from y of about 7 to 519, with a baseline at y of about 519 from x of about 85 to 613, and neither has an arrowhead. The energy axis is a separate arrow to the left of the frame, at x of about 53 px, running from y of about 518 up to y of about 9 with its head at the top. The extent-of-reaction arrow lies below the frame at y of about 551, from x of about 86 to 615, with its head at the right end.
- Line weight: the axes are about 2 px; the two curves are about 5 to 6 px thick (measured at the uncatalysed peak).

## Tool gaps

- `draw_figure` needs at least one structure and one reaction step, so it refuses a figure with no molecules. This applies to `draw_figure` only; `compose_chemical_figure` accepts an objects-only manifest (see What is reproduced).
- No energy-profile object: no kind builds a reaction-coordinate figure from levels, curves and labels. Axes and leader lines can be built from `arrow` and `line` objects, but nothing places a leader line against a named level or label.
- Figure-type conventions such as pathway colours are listed as skipped guidance in `scheme-drawing.md` for all figure types (its examples include energy units), not only for schemes and mechanisms. No tool applies them automatically to a curve. A `curve` object takes a `color`, so a colour can be set by hand per curve.
- `text` objects have no rotation field (the allowed fields are position, text, runs, size, align and color). The rotated "Energy" title cannot be set from the manifest.
- Each `curve` object is exactly one cubic Bezier (four points). The two-hump catalysed path needs several joined curve objects, and nothing enforces matching tangents at the joins.
- Line weight is per manifest, not per object: `compose_chemical_figure`'s `line_width` sets one `LineWidth` for every arrow, line and curve. The crop needs the curves about 2.5 to 3 times the width of the axes, so one width cannot reproduce both.
- Arrowhead size is not a spec field: the probe output used constant HeadSize and ArrowheadWidth values, and the `arrow` fields are only start, end, style and color.
- Ea double-headed arrows have a route: the `resonance` arrow style sets `ArrowheadTail` to Full in the code, giving arrowheads at both ends (not rendered in this audit). Crop 02 has none, so this does not block this crop.
- Nothing links a curve to a named level, label or leader line; objects are placed by coordinates only.
- `scientific plot` draws numbered, data-bound axes. This was not re-checked beyond the code.

## Card issues (not fixed here)

- Leader lines: the card says Reactants and Products have thin leader lines. In crop 02 only the two pathway labels have them.
- Transition state: the card lists a Transition state label under energy_profile. Crop 02 has none (it is in crop 01).
- Ea arrows: the card lists Ea double-headed arrows under energy_profile, but they are in crop 01 only; crop 02 has none.
- Colours: `figure_types.energy_profile.conventions.pathway_colors` holds the crop-01 values (#BC4428, #8894C8). The crop-02 values (#BC2404, #4060F4) appear only in the observations and signature features. The card's own notes say the shades differ between figures.

## Audit

Second-pass audit by Haiku 5.5 on 2026-11-07. Only this file was edited.

- Overclaims corrected:
  - "The card names the energy profile as having no drawer." The card has no such statement; the line is removed.
  - "Nothing reproduced" was presented as forced by the tools. `compose_chemical_figure` takes objects without molecules; the figure was left undrawn by choice (see What is reproduced).
  - Pathway colour citation: the card's conventions field gives #BC4428 and #8894C8, not #BC2404 and #4060F4 as the table said.
  - Axis geometry: the energy axis is a separate arrow outside the L-shaped frame, not the frame itself; the extent arrow is broken around its title, not "bold-flanked".
  - "Pathway colours for schemes and mechanisms only" is not what `scheme-drawing.md` says; it lists them as skipped for all figure types.
  - "No tool applies them to a curve" is true only of automatic application; `curve` objects take a colour.
  - "Ea double-headed arrows" have a drawing route: the `resonance` arrow style.
- Checked and confirmed: the red and blue colour samples; the `draw_figure` refusal messages; no rotation field on `text`; `reference.png` is byte-identical to `evidence/openstax_chemistry-02.png`; the three card issues about leader lines, Transition state and Ea arrows.
- Corrected matched count: 0 of 9. Nothing is drawn, so no row can be a match.
- Tool gaps the replicator missed: one line width per manifest (not per object); one cubic Bezier per curve object with no join constraint; no arrowhead size control; and objects-only composition through `compose_chemical_figure`, which the replicator's gap list did not mention.
- Not checked: the `cdx.py draw` run itself; native rendering (no `rendered.png`); `scientific plot` beyond the code.
