# JACS Au house style, setup diagram: reactor types in flow chemistry (Figure 1, e) This work)

Source: L. Landfester et al., "Photoactive PFA coating through fluorophilic interactions for continuous flow photochemistry", *JACS Au* **2025**. DOI: [10.1021/jacsau.5c00804](https://doi.org/10.1021/jacsau.5c00804). Licence: CC BY 4.0. Reference crop: `reference.png` (copy of `evidence/jacs_au-06.png`, Figure 1).

Card: `jacs_au` (base preset `acs1996`), figure type `setup_diagram`, crop 06.

## What is reproduced

Nothing faithful. The crop is a five-panel schematic of flow reactor types (a) fixed bed, b) slurry, c) coated, d) coil, e) This work) with a title and a photocatalyst. It contains no reaction. Its only chemistry is text: the PFA tubing formula `(CF2CF2)x(CF2CF(OCF3))y`, and the fluorous end groups `F17C8` and `C8F17` on a photocatalyst that is drawn as a red disc with no structure. `draw_figure` has no setup or apparatus drawer, and it cannot write a polymer repeat unit or a fluorous fragment with a defined attachment.

`brief.json` is a tool probe, not a replica. It puts a perfluorooctyl fragment written with a `*` dummy atom and a perfluoro(methyl vinyl ether) species into one step. That step is not a reaction from the paper, and the step could not be balanced. `replay.py` redraws the probe offline. `rendered.png` is absent because the probe drawing does not correspond to the figure and rendering it would be misleading.

## Tool probe result

`cdx.py draw` ran in about two minutes. It accepted the `*` atom and wrote it as a `GenericNickname` labelled `R`, with the balance check reported as "cannot be balanced". The readback was "matched", and `checks_passed` was true. Those checks confirm only that the file round-trips, not that the drawing matches the figure.

## Conventions

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| background_fill null (white background) | white background | no replica drawing exists in this folder (no figure.cdxml, validation.json or rendered.png), so there is nothing to compare | no |
| highlight_fill `#FE0000` on the authors' reactor | red outline on the e) coil and a red photocatalyst disc; no filled region | not drawn; `draw_figure` highlight is a pastel fill behind a product ring, not used here | no |
| reactor types as grey tubes with black end fittings (a, c) | grey tubes with black end caps | not drawn | no |
| authors' reactor 'e) This work' drawn in red | red-outlined coil with a magnifier | not drawn | no |
| sub-panel letters bold lowercase with a closing parenthesis, a) to e) | bold a) to e) under bold titles | not drawn; `draw_figure` has no panel labels | no |

Not visible in this crop, so not scored: the conditions-under-reactor and bold-italic product name (crop 05), and the compound label and arrow conventions of the top-level scheme style (no compounds, arrows or plus signs in the crop).

Matched 0 of 5 conventions. The white background row cannot be scored because no replica drawing exists in this folder; see the Audit below.

## Differences from the paper

- No reactor glyphs: the grey tubes, packed-bed and slurry fills, coil rings, black end fittings, red coil, magnifier and photocatalyst disc with a blue glow are all absent.
- No panel layout: the five sub-panels, their bold titles, the figure heading "Types of reactors in flow chemistry" and the 2 by 2 plus full-width arrangement are absent.
- The polymer formula `(CF2CF2)x(CF2CF(OCF3))y`, the grey bold "PFA tubing" label and the blue bold "Fluorophilic interactions" text are absent. The paper's formula text is blue, and `draw_figure` has no per-line colour or bold for free text.
- The photocatalyst is not defined as a structure in the crop, so no species was drawn for it.

## Tool gaps

- `draw_figure` has no setup or apparatus drawer for reactor tubes, coils, packed beds, magnifiers or glow effects.
- No panel-letter layout: no a) to e) sub-panels with bold titles.
- No polymer repeat-unit bracket with subscript x and y. A `*` dummy atom is accepted but written as a generic `R` label and cannot be balanced, so an open-valence fragment has no faithful route.
- `highlight_fill` applies only as a pastel fill behind the largest ring of a product. The setup card's red outline convention cannot be expressed.
- Free text lines in `above`/`below` take no colour and no bold, so the blue bold formula and grey bold labels cannot be set.
- Figure-type conventions are reported as skipped guidance, so a card's `setup_diagram` section does not change `draw_figure` output.

## Replay

`python -I skill/chemdraw/scripts/cdx.py py skill/chemdraw/assets/house-styles/jacs_au/replica/jacs_au-06/replay.py NEW_DIR` runs the probe offline and writes `figure.cdxml` and `validation.json` in a new folder. The result is a probe drawing, not a replica of the crop.

## Audit

Checked against `reference.png`, `brief.json`, `replay.py`, this file, the card `toolkit/cdxml_toolkit/publication/house_styles/jacs_au.json` (its `setup_diagram` section), and the toolkit code `mcp_runtime/figure_draw.py` and `mcp_runtime/figure_house.py`. No `rendered.png` or drawing output exists in this folder.

- **Background row: not matched.** The reference is white, but the replica side has no drawing to inspect. The default preset is not a convention drawn for this figure, so the row is scored no. Corrected matched count: **0 of 5**.
- **Probe result (`cdx.py draw`, "matched", `checks_passed`, "cannot be balanced"): unverified.** No output or validation file is kept here, so these claims cannot be checked from the case folder.
- **Other "no" rows: confirmed as not matched.** The reference shows grey tubes with black end caps, a red authors' reactor, and bold lowercase panel letters a) to e); none is drawn. Proportions, line weight, label face and colour were never measured on a replica, so none of them can be marked matched.
- **Verified tool facts:** `draw_figure` ignores the card's `setup_diagram` section, because `figure_house.apply_figure_type_conventions` applies only the `mechanism` and `catalytic_cycle` types. `highlight_fill` fills the largest ring of each final product (`figure_house.add_highlight_fills`); the colour comes from the card, so "pastel" is only the default.
- **Overstated gap: "no photocatalyst glow".** `figure_draw.py` has atom halos, a filled oval behind a species atom in a set colour (default `pastel_yellow`). A flat coloured disc behind an atom is possible. A blue glow, or a disc that is not tied to an atom, is not.
- **Gaps the replicator missed:**
  - In `draw_figure`, brackets exist only as `ts_bracket` around a whole species, with a fixed superscript. There is no repeat-unit bracket with subscript x and y. (`figure_tools.py` has its own bracket objects, which the replicator did not check.)
  - No primitive shapes for apparatus: tubes or capsules with end caps, a stacked-ring coil, a sphere or packed-bed fill, a pump chevron, a circled-x valve, an LED bulb, a magnifier, a dashed arrow, or dotted or hatched bands.
  - The only styled text run in `figure_draw.py` is the ts_bracket superscript. The above and below text takes no per-run colour, bold or subscript, so "PFA tubing", the polymer formula and "Fluorophilic interactions" cannot be set as in the paper.
  - No panel layout with lettered sub-panels (already listed above).
