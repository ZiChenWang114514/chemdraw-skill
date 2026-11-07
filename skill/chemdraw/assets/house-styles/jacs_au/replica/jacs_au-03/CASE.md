# JACS Au: triplet energies of Cu(I) and Ir/Ru sensitizers on an eV axis (Figure 7)

Source: Steffen et al., "Photoactive neutral three-coordinate Cu(I) complexes of anionic N-heterocyclic carbenes", *JACS Au* **2025**. DOI: [10.1021/jacsau.5c00357](https://doi.org/10.1021/jacsau.5c00357). Licence: CC BY 4.0 (from the house style card `jacs_au`, evidence crop `jacs_au-03`, Figure 7).

Drawing style: the `jacs_au` house style card, `photophysical_diagram` section.

## What is reproduced

Nothing. The crop is a triplet-energy bar plot on one horizontal eV axis (ticks 1.7, 2.0, 2.3, 2.6, 2.9 eV). Each sensitizer is a vertical navy bar capped by filled discs, labelled by its complex name ([Cu(dpp)2]+, [Cu(bcp)(xant)]+, [Ru(bpy)3]2+, Ir(ppy)3, Ir(dFppy)3, Ir(p-F-ppy)3). The new complex C4 is a green bar with a bold green label at about 2.7 eV. The crop has no structures and no reaction, so `draw_figure` has nothing to draw. The complex names are not converted to SMILES: metal complexes have no grounded connectivity in the crop, and writing structures for them would be invention.

`brief.json` holds the style and empty species and steps. It was run through `cdx.py draw` (no `--render`) twice. The first run had no result after about 17 minutes and was stopped. The second run ended after 96 s with `worker_crashed` (worker exit code 143, no output). The machine was running many other `cdx.py` workers at the time, so the cause is not confirmed. Neither run showed the tool's own refusal for an empty brief, so no refusal wording is recorded here. `rendered.png` is not produced.

## Replay

```
python skill/chemdraw/scripts/cdx.py draw skill/chemdraw/assets/house-styles/jacs_au/replica/jacs_au-03/brief.json NEW.cdxml
```

`replay.py` calls `draw_figure` in-process with `CHEMDRAW_OFFLINE=1`, outside the `cdx.py` worker, so it does not wait for the ChemDraw lock. For this brief the call returns the two validation errors (species and steps are empty) and writes only `validation.json`. It does not write `figure.cdxml`, although the script prints that path. The same in-process call was run once in the audit: it returned `ok: false` with those two errors in about 2 s. The `cdx.py draw` command above goes through the worker and the ChemDraw lock (see the Audit note).

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| energy_unit `eV`: tick labels and unit '/ eV' at the axis end | "2.9 / eV" at the axis end, grey tick labels | not drawn; no energy-axis drawer | no |
| pathway_colors `#213570` (navy): bars and discs | navy bars with discs at both ends | not drawn | no |
| pathway_colors `#369134` (green): new compound | C4 green bar and bold green label | not drawn | no |
| signature: horizontal eV axis with grey tick labels, unit written '/ eV' at the axis end | present | not drawn | no |
| signature: vertical bars capped by filled discs, navy | present | not drawn | no |
| signature: new compound highlighted in green with bold green label | present (C4) | not drawn | no |
| signature: orbital energies as dots in boxed panels with 'Energy / eV' axis | not in this crop (crop jacs_au-04) | not applicable | n/a |
| observation: labels alternate above and below the axis | not strictly alternating: in energy order the labels run above, below, below, above, below, above, below (three above, four below) | not drawn | no |
| top-level `compound_label_face` bold, black | C4 is bold; the complex names are plain black, not bold, so this crop does not follow the top-level bold rule for its names | not drawn | no |
| top-level `arrow_style` plain, `aromatic_rings` kekule, `show_plus_sign` | no arrows, rings or plus signs in the crop | not applicable | n/a |

The matched count is 0 of 8 claims that apply to this crop. The orbital-panel signature belongs to crop 04 and the scheme-level rows do not apply to this crop, so they are not counted.

## Differences from the paper

- The whole figure is missing. The replica is the empty brief and no PNG, so there is no picture to compare.
- The paper's figure is described here as a plot of triplet energies. Whether they are measured is not checked: the Figure 7 caption is not in this folder. The replica would need those energies. The crop gives only positions, and a pixel estimate from the 666 px image puts them at about 1.80 to 2.75 eV (axis 1.7 to 2.9 eV). These are estimates, not values from the paper, so they were not used.

## Tool gaps

- No energy-level or triplet-bar drawer. `draw_figure` accepts only `kind` scheme, scope or mechanism; catalytic cycles are a scheme layout. `scientific_workflow` `plot` draws only line series: `plot_xy` passes each series to matplotlib `plot` with a linestyle, so it has no markers and no scatter. Stems could be two-point line series; the disc caps cannot be drawn.
- `plot_xy` cannot set tick positions, axis limits, tick label colour or per-series line width. Ticks come from matplotlib's automatic locator, so 1.7, 2.0, ... 2.9 cannot be forced. Its CDXML branch is a fixed 600 x 300 canvas with 8 pt text, and it has no eV unit placement at the axis end beyond the axis title.
- Low-level helper `cdxml_toolkit/scientific/common.py` (`Drawing`) places text and lines at coordinates, so labels and leader lines can be made by a script run with `cdx.py py`. It lacks: bold text (the font face is fixed to plain), centred text (justification is always Left), a per-object line width (the constructor fixes LineWidth 0.6 and BoldWidth 2), and a disc or circle primitive (only closed filled polylines). `chemdraw_object` `add` can also append a text object with props to an existing CDXML; this was not tested for this figure.
- No way to place a label above or below a bar at its energy, alternating, with leader lines, as one call. There is no helper that maps an energy to an x position or avoids label collisions. Coordinates can be set through the low-level helpers above.
- The house card's `photophysical_diagram` conventions (energy_unit, level_style, pathway_colors) are validated by `publication/house_styles.py` but no drawing code reads them. `draw_figure` never reads that section: `apply_figure_type_conventions` runs only for mechanisms (`figure_mechanism.py`) and for catalytic-cycle layouts (`figure_draw.py`). Nothing is reported as skipped for these conventions, for schemes or any other kind.
- An empty brief, run in-process, is refused at once: `draw_figure` returns `ok: false` with the two validation errors in about 2 s. The `cdx.py draw` route is different. `draw_figure` is in `CHEMDRAW_COM_TOOLS`, so the worker takes the `chemdraw_com` mutex (`tool_worker.py`, `native_resource_lock`) before it runs the function, and validation runs only after that. The missing refusal is therefore a wait on the shared lock. This is consistent with the hang, but the cause is not confirmed in a live run. The code's worker timeout is 300 s, so a 17-minute hang is not explained by the code read here, and the 96 s `worker_crashed` (exit 143) is not explained either.

## Audit

Checked against `reference.png` (666 x 316, the same image as `evidence/jacs_au-03.png`) and the toolkit code.

- Matched: 0 of 8 applicable rows. Every applicable row says no and that is correct, because the replica is an empty brief with no image. No row was changed to yes.
- Corrected overclaims: (1) the replay does not write `figure.cdxml` for this brief; (2) `plot` has no scatter or markers; (3) `draw_figure` never reads the `photophysical_diagram` conventions, so nothing is reported as skipped; (4) the paper's labels do not alternate by energy order; (5) an empty brief is refused in-process at once, and the untested part is the worker route, which waits on the ChemDraw lock before validation; (6) "measured" and "1.8 to 2.8 eV" are not supported by the folder (1.80 to 2.75 eV is a pixel estimate); (7) the label-placement gap is narrower than stated.
- Not verifiable from this folder: the 17-minute and 96 s durations and exit 143 (no logs), the Figure 7 caption, and the card hex values. Sampled bar pixels are mixed (navy mode `#213570` with darker `#02205E` cores; green `#54A651` edges with `#228B22` cores), so `#213570` and `#369134` can be neither confirmed nor refuted at this size. They are left as written.
- `replay.py` says `draw_figure` refuses the brief. The in-process run supports that, but this note said no refusal was seen. `replay.py` was not edited (outside the scope of this audit) and its printed `figure.cdxml` path does not exist for this brief.
