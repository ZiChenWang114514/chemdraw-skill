# JACS Au: frontier orbital energies of Cu(I) complexes C2-C5 (Figure 5, lower part)

Source: M. Steffen et al., "Photoactive Neutral Three-Coordinate Cu(I) Complexes of Anionic N-Heterocyclic Carbenes", *JACS Au* **2025**, *5*, 2792-2801. DOI: [10.1021/jacsau.5c00357](https://doi.org/10.1021/jacsau.5c00357). Licence: CC BY 4.0 (from the `jacs_au` card; reference crop reproduced under that licence).

Drawing style: the `jacs_au` house style card (`photophysical_diagram` figure type, crop `evidence/jacs_au-04.png`). Base preset ACS Document 1996.

## What is reproduced

Nothing is drawn. The crop is a plot, not a scheme: two stacked boxed panels of orbital energies in eV (top "unoccupied", bottom "occupied") with one dot per orbital for each complex C2 (red), C3 (orange), C4 (green) and C5 (navy). It has no molecular structures, no reaction arrows and no compound labels other than the four complex names. There is no chemistry in the crop that `draw_figure` could take as a species list, so `brief.json` holds no species and no steps. Running it returns a refusal at once (see Replay), and no `rendered.png` was produced.

The complex structures (Cu(I) with an anionic NHC and a dipyridylamine N,N-ligand, methyl groups at the 4,4-positions in C3-C5) are shown in the paper's earlier figures, not in this crop. They were not redrawn here, because the crop does not show them and no SMILES was read from the paper for this replica.

## Reference values (read from the crop, not measured from the paper)

| Panel | Series | Points read from the crop |
| --- | --- | --- |
| unoccupied (top, box edges about -0.9 and -1.9 eV; ticks every 0.2 eV, labelled -1.0, -1.4, -1.8) | C2 / C3 / C4 / C5 | 2 dots each (LUMO and LUMO+1) |
| occupied (bottom, axis -5.6 to -6.6 eV) | C2 / C3 / C4 / C5 | 4 dots each (HOMO to HOMO-3) |

The quoted paper text gives the HOMO shifts relative to C2 as 0.00, +0.07, +0.12 and +0.07 eV for C2 to C5. The paper is not in this folder, so the quote is unverified. Pixel readings of this crop (200 px per eV in both boxes, about +/-0.01 eV) give HOMO shifts of about +0.05, +0.06 and +0.05 eV, and LUMO shifts of about +0.07, +0.12 and +0.08 eV. The quoted values agree with the LUMO readings, not the HOMO readings, so the orbital label needs checking against the paper. These numbers are not drawn.

## Convention table (card claims for `photophysical_diagram` plus the visible top-level conventions)

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| `energy_unit` eV, axis title "Energy / eV" | "Energy / eV", bold, rotated, at the left edge, centred on the gap between the two boxes (about y 202 to 321 px of the 534 px crop) | not drawn (no energy-level drawer) | no |
| `level_style` null (card) | dots, one per orbital, no bars or connectors | not drawn | no |
| `pathway_colors` `#213570`, `#369134` | crop 04 uses red, orange, green and navy series colours (sampled dots: red about `#FA0107`, orange about `#FDA601`, green about `#268821`, navy about `#020096`); the two card colours are the crop 03 bar and highlight colours | not drawn | no (the card's colours are the crop 03 colours, not crop 04's) |
| orbital energies as coloured dots per compound in boxed panels (crop 04 signature feature) | yes, two boxed panels | not drawn | no |
| "Energy / eV" axis labelled in the crop | yes | not drawn | no |
| top-level `compound_label_face` bold | complex names C2-C5 bold | not drawn | no (no drawer) |
| top-level `compound_label_color` `#000000` | complex names coloured by series (red, orange, green, navy) | not drawn | no (the card says black; the crop shows the series colours) |
| top-level `arrow_style` plain, `show_plus_sign` | no arrows and no plus signs in the crop | not applicable | n/a |
| top-level `aromatic_rings` kekule, `abbreviate_groups` | no structures in the crop | not applicable | n/a |
| `reagent_text_color` #000000 | no reagent text | not applicable | n/a |

Count: the card claims 3 signature features for `photophysical_diagram`, of which 1 applies to crop 04 (the orbital dot panels, not replicated). The crop-03 features (eV triplet axis, navy bars and green new compound) do not apply to crop 04.

## Differences from the paper

- The whole crop is not reproduced. The figure is an orbital energy plot, and no drawer in the toolkit produces it.
- The top panel's edge carries partial green marks cut off by the crop boundary; they belong to the part of Figure 5 above the crop and are not reproduced.
- The complex structures from the paper are not drawn, so there is no chemistry to compare.

## Tool gaps

- No energy-level or orbital-diagram drawer. `draw_figure` takes the kinds `scheme` (default), `scope` and `mechanism`. The catalytic cycle is a layout of a scheme (`layout="catalytic-cycle"`), not a kind. Nothing in the toolkit draws a numeric axis with ticks, a dot series or a plot.
- `cdx.py build` (`acs_builder.py`) has primitives: `text` (size, bold, colour), `box` (rectangle, square with `round: false`), `arrow`, `label_box`, and an `interaction` line (solid or dashed). Boxed panels can therefore be drawn by giving coordinates by hand. What is missing is a layout layer: no panel stacking or relative placement, no tick or axis generator, no rotated text (`text` has no rotation argument), and no filled-dot object outside molecule drawing.
- No energy-axis option: an axis range from numeric values, ticks every 0.2 eV with labels every 0.4 eV, ticks mirrored on both sides of each box (present in the reference), rotated tick labels and the "Energy / eV" title.
- No dot-series option: one column of coloured dots per compound, one series colour per column, and a bold coloured column label. Text colour exists in `text`; the dot series does not.
- Panel titles are not placed per box. In the reference "unoccupied" is below the top box and "occupied" is above the bottom box, in the gap between them. The x labels C2 to C5 sit under the bottom box only.
- The empty-brief hang recorded earlier was not reproduced (see Replay). `draw_figure` refuses an empty species or steps list at validation.

## Replay

```
python skill/chemdraw/scripts/cdx.py py skill/chemdraw/assets/house-styles/jacs_au/replica/jacs_au-04/replay.py NEW_DIR
```

On 2026-11-07 the replay returned at once: it wrote `validation.json` with the two refusals (no species, no steps) in about 3 s. `cdx.py draw` on the same brief also refused, in about 2 s, with the same two errors. The earlier hang (no output for over 150 s, `worker_crashed`, exit 143) could not be reproduced. The replay is kept only so the case matches the other replica folders.

## Audit

Checked on 2026-11-07 against `reference.png` (666 x 534 px), by pixel measurement and by eye.

- Matched count: 0. The table has 10 rows, not 5: 7 "no" and 3 "n/a", and no "yes". The replica draws nothing, so nothing can match. The "0/5" figure is not in this file.
- Corrected: the top box runs from about -0.9 to -1.9 eV (edges at y 34 and 235 px, ticks at 0.2 eV steps), not -1.0 to -1.8. The bottom box (-5.6 to -6.6 eV) is correct.
- Corrected: "unoccupied" sits below the top box, but "occupied" sits above the bottom box, in the gap. "Titles set below each box" was wrong.
- Corrected: "Energy / eV" is centred on the gap between the boxes, not left of the top box.
- Corrected: the "see card_errors" pointers referred to nothing. The card has no such field, so the colour mismatches are now stated directly.
- Corrected: the empty-brief hang was not reproduced. Refusals came back in 0.02 s (direct call), 1.9 s (`cdx.py draw`) and 3 s (`replay.py`).
- Overclaimed gap: "no boxed-panel primitive". `acs_builder.py` has `box`, `text`, lines and arrows, placed by coordinates. What is missing is a plot or layout layer.
- Unverified here: the paper HOMO shifts (the paper is not in this folder; the crop's LUMO readings match the quoted values and the HOMO readings do not), and the methyl positions in C3 to C5.
- Measured for the record: dots 11 px in diameter; box edges 2 px (the top box's lower edge 1 px); ticks about 6 px outside both sides of each box; dot colours red (249, 5, 5), orange (251, 165, 5), green (33, 138, 33), navy (4, 3, 138), within a few units of the sampled values in the table.
- Tool gaps missed by the replicator: rotated text, numeric axis and tick generation, a filled-dot object outside molecule drawing, per-box title placement, and the fact that the primitives for boxes and text already exist.
