# Chem. Eur. J. 2023: Au-catalysed yndiamide cyclisation, catalytic cycle (Scheme 3a), layout probe

Source: Anderson et al., *Chem. Eur. J.* 2023 (gold-catalysed cyclisation of yndiamides with isoxazoles via alpha-imino gold Fischer carbenes), Scheme 3a. DOI: [10.1002/chem.202302821](https://doi.org/10.1002/chem.202302821).

Licence: CC BY 4.0 (from the house-style card; reference crop reproduced under that licence).

Drawing style: the `chemeurj` house style (base preset `wiley`, applied to the catalytic-cycle layout through `catalytic_cycle.cycle_arrow_color`, bold compound labels, plain arrows, Arial labels).

Figure type: `catalytic_cycle`.

## What the target shows (not reproduced)

The bullets below describe the paper's Scheme 3a, which is the target. The chemistry is not reproduced. Of the target's features, the probe matches only the bold black Arial labels and the black plain arrows.

- The scheme is an open loop of thin black curved arrows around the gold cycle, with the H3P-Au+ catalyst at the top right, intermediates Int1 to Int8 in bold, transition-state names (TS1 to TS6, TSflip) on grey tabs with relative energies in parentheses, products 2, 4 and 5 on grey boxes, and Au drawn in orange.
- The probe in `brief.json` is a four-step closed loop of placeholder C4H6 isomers (`C#CCC`, `CC#CC`, `C=CC=C`, `C1=CCC1`) labelled Int1 to Int4. These are not the paper's structures. The probe exists only to see what `draw_figure` does with `layout: "catalytic-cycle"` under this card. `rendered.png` shows that probe, not the figure in the paper.

## Why the chemistry was not reproduced

- OCSR (`cdx.py ocsr`, decimer-api, `provenance: model_prediction`) on the crop returned one phthalic-acid SMILES, `Cc1cc(C)c(C(=O)O)c(C(=O)O)c1`, with ten candidates. It does not segment multi-structure schemes, so it cannot supply the structures.
- The protecting group on every nitrogen is shown only as the abbreviation PG. Its identity is not in the crop, so the ynediamide, products 2, 4 and 5 and the pyrrole intermediates cannot be written without guessing.
- Int1 to Int8 contain gold-carbon bonds, a carbene centre and zwitterionic N+ atoms. At the crop's resolution the bonding and charges are not readable with the confidence the brief requires, so no SMILES were written for them.
- The isoxazole reagent on the Int2 and Int3 arrows is drawn, but its ring substitution is not clear enough at this size to write as a SMILES.

## Convention comparison

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| `catalytic_cycle.cycle_shape`: circle (card) | open loop of curved arrows, not a circle | four-node closed diamond with straight arrows | no |
| `catalytic_cycle.cycle_arrow_color` #000000 | black cycle arrows | black (applied by the tool, report `applied`) | yes |
| `catalytic_cycle.curved_arrow_color` #000000 | thin black curved arrows | black but straight; the tool draws no curved cycle arrows | no |
| signature: black arcs around a circle (card) | open loop of arcs, crop 05 is not a circle | straight segments | no |
| signature: incoming and leaving species on short curved black arrows | catalyst and ynediamide enter, products leave on curved arrows | no reagents or products drawn in the probe, so no radial arrows | no |
| `intermediate_label_style` (card null; crop uses bold Int1 to Int8) | bold Int1 to Int8 | bold Int1 to Int4 | not counted (card null) |
| `compound_label_face` bold | bold | bold | yes |
| `compound_label_color` #000000 | black | black | yes |
| `label_font` Arial | Arial | Arial bold in the render | yes |
| `arrow_style` plain | plain arrows | plain | yes |
| `highlight_fill` #E6E6E6 (top-level; crop 05 uses it on TS tabs and product boxes) | grey #E6E6E6 tabs and boxes | not applied (`catalytic_cycle` section does not carry it; no grey shape is drawn) | no |

Card conventions in this table: 8 (the card-sourced rows). Matching: 5. The earlier count of 6 of 10 is corrected in the Audit note.

Not claimed by the card for `catalytic_cycle` (null) and so not counted: `catalyst_color` (paper Au in orange), `center_label`, `step_names`, `yield_placement`, `new_bond_color`, `substrate_colors`.

## Differences from the paper

- Cycle shape: the paper has an open loop with four curved sides and an exit to products 2, 4 and 5. The probe is a closed four-node diamond with straight arrows.
- Arrows: the paper's cycle arrows are thin and curved; the tool draws straight lines.
- Transition states: the paper names TS1 to TS6, TSflip and TS3 on grey tabs with relative energies in parentheses. Nothing like this is drawn; the tool has no free-text tab or box on a cycle.
- Catalyst: the paper's H3P-Au+ sits outside the loop with a curved arrow into Int1. The probe has no catalyst.
- Colour: the paper colours Au orange and uses grey fills. The probe has no coloured atoms or fills.
- Structures: none of the paper's structures are drawn. The C4H6 placeholders are only there to exercise the layout.
- Labels: the paper's Int numbering runs Int1 to Int8 with primes (Int7') and bold compound numbers for products. The probe has Int1 to Int4 only.

## Tool gaps

- The `catalytic-cycle` layout draws the loop as straight arrows between nodes placed on a polygon. It cannot draw an open loop, arcs along the cycle, or curved cycle arrows, so `cycle_shape` and `curved_arrow_color` on the card cannot be applied.
- `catalytic_cycle.cycle_arrow_color` is applied, but `curved_arrow_color` for catalytic-cycle arrows is only guidance and is not drawn.
- No free-text tab or box with a fill (grey #E6E6E6) behind transition-state names and relative energies, and no navy bold text style for TS labels.
- No per-atom colouring of a metal such as Au in a species (the `substrate_colors` convention applies to scheme substrates only).
- No text placeholder for a protecting group (PG) or other undefined group on a species; the SMILES must use a real atom or a fragment.
- OCSR does not segment a multi-structure scheme into structures; it returns one wrong structure with ten candidates.
- The first `draw --render` call waited 295 seconds on the `chemdraw_com` resource and returned `resource_busy`; the retry succeeded. This is an operational note, not a drawing gap.

## Replay

```
python skill/chemdraw/scripts/cdx.py py skill/chemdraw/assets/house-styles/chemeurj/replica/chemeurj-05/replay.py NEW_DIR
```

`replay.py` draws `brief.json` offline into `NEW_DIR`. It was run once to check that it reproduces the probe without ChemDraw; `figure.cdxml` and `validation.json` were written to a scratch folder.

## Audit

Checked against reference.png, rendered.png, brief.json, chemeurj.json and the toolkit code. replay.py was re-run offline into a scratch folder.

- Corrected count: 5 of 8 card conventions match, not 6 of 10. The table has 11 rows, and the intermediate_label_style row has no card value (card null), so it is not counted.
- Verified matches: cycle_arrow_color black (the replay report lists `catalytic_cycle.cycle_arrow_color=#000000` as applied); bold black labels; Arial (font table in the CDXML); plain arrows (no bold applied).
- Verified non-matches: cycle_shape (straight-sided polygon, not an open loop or circle); curved_arrow_color (reported as skipped, guidance only); highlight_fill.
- The highlight_fill reason is incomplete. `add_highlight_fills` (figure_house.py, line 76) fills only final products, as a ring fill, and a closed cycle has no final products. The row's conclusion stands, but the tool does have a grey fill; it just cannot reach a cycle.
- The replay reproduces the probe offline (checks_passed true, readback matched). The case folder holds no figure.cdxml or validation.json, so the earlier scratch outputs could not be checked directly.
- Not verifiable from the folder: the 295 s resource_busy wait and the ten OCSR candidates. Both are operational notes, not drawing gaps, so they do not belong in the tool gap list.
- Missed tool gaps, confirmed by probe or code:
  - The cycle layout draws only substrates[0] of each step. A second substrate (water, in a probe) is not drawn and the report gives checks_passed false. Reagents or catalysts entering the loop (H3P-Au+, the isoxazole) cannot be drawn. Dashed step arrows exist, but off-loop reagents cannot be attached.
  - No exit arrows for products leaving the loop (2, 4 and 5 in the paper). In a probe, an exit product with the same structure as a ring species was not drawn, yet readback reported matched, because readback compares structures, not labels. A distinct exit product would be reported missing (from the `_readback` code; not run).
  - A non-closed path forced to layout catalytic-cycle is not refused: it returns ok true with checks_passed false and one species dropped (probe run).
  - Atom colour: `atom_halos` paints a coloured circle behind an atom and `ring_fills` colours a ring. Neither colours the atom symbol, so orange Au text remains a gap, though an orange halo behind Au is possible.
  - `ts_bracket` draws square brackets with a double dagger, not a name tab, so the TS-tab gap stands.
- Proportions and line weight appear in no table row. From the CDXML, LabelSize 12 on BondLength 17 gives a cap height of about 8.6 pt, a ratio of 2.0 to the bond, as the card states. The arrow LineWidth is 0.60 pt (0.035 of the bond), close to the card's 0.04.
