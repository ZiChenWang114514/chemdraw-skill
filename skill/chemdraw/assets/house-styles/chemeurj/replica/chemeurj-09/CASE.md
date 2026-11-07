# Chem. Eur. J. (Maes et al.): energy profile of [3+2] addition and N2 extrusion (crop chemeurj-09)

Source: Maes et al., "Iron-Catalysed Carbene Transfer to Isocyanides as a Platform for Heterocycle Synthesis", *Chem. Eur. J.* DOI [10.1002/chem.202203074](https://doi.org/10.1002/chem.202203074). Licence: CC BY 4.0 (from the house-style card). The card cites the year as 2023 and the figure as Figure 1; the downloaded `meta.json` gives *Chemistry* 2022 Dec 20, 29(9). The paper's Figure 1 file (`CHEM-29-0-g001.jpg`) is a different profile (isomerisation and isocyanide approach, starting from `I3`, -22.0 (-25.3)), so the crop's figure number is not confirmed by the downloaded files.

Drawing style: the `chemeurj` house style (`cdx.py styles chemeurj`), base preset Wiley.

Figure type: `energy_profile`.

## What is reproduced

Only the two organic structures that a structure panel can express:

- R2, methyl diazoacetate, `COC(=O)C=[N+]=[N-]` (RDKit: C3H4N2O2), labelled R2;
- N2, `N#N`, labelled N2.

They are placed under the two caption headings of the crop ("[3+2] addition with alpha-diazo ester", "Nitrogen extrusion / carbene formation"). The energy levels are not reproduced, and neither are the iron carbonyl complexes (R1, RC1, TS1, I1, TS1', I1', TS2, I2, I3), the ball-and-stick TS models or the axis.

Values in the crop, for reference (Delta G298 (Delta E), kcal mol-1): R1 0.0 (0.0); RC1 +10.0 (-3.5); TS1 +29.5 (+15.0); I1 +24.6 (+10.4); TS1' +32.0 (+18.3); I1' +28.6 (+11.3); TS2 +33.2 (+19.5); I2 -16.4 (-26.8); I3 -22.0 (-25.3). The grey pathway runs RC1 to TS1' to I1'.

## Status of the render

Not rendered. `rendered.png` was not produced and no visual comparison was possible.

- Attempt 1: brief with a `max_width` key, which the scope brief does not accept. Refused after about 254 s.
- Attempt 2: valid brief with `--render`. `tool_timeout` after 300 s.
- Attempt 3: valid brief without `--render`. `resource_busy` (ChemDraw COM busy for 295 s).
- Attempt 4: valid brief with `--render`. `resource_busy` (295 s).

The table below therefore compares the card with the paper crop only. Nothing in the replica column was checked against a rendering, so every match cell is "no".

## Files

- `reference.png`: copy of the evidence crop.
- `brief.json`: the valid scope brief used in attempts 2 to 4 (`style` `chemeurj`, `kind` `scope`, two species).
- `replay.py`: copy of the JACS Au replay with a changed docstring. Its `draw_figure(brief, out/'figure.cdxml')` call is untested for `kind: scope`, where the output path must be a new folder.

Colour sampling on the crop (not a replica claim): the blue fragments measure around #084078 to #285888, close to the card's navy #004080. The Fe(CO)3 cores and the NO group are black. The grey competing pathway is anti-aliased around #8C8C8C to #9F9F9F, consistent with #808080 within anti-aliasing.

## Convention table

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| energy_profile.energy_unit: kcal/mol | "kcal mol-1" in the header | not drawn (no energy drawer) | no |
| energy_profile.energy_label: delta_G, with DeltaE in parentheses | "DeltaG298 (DeltaE)" header and values | not drawn | no |
| energy_profile.level_style: bars with solid connectors | thick bars, thin solid slanted connectors | not drawn | no |
| energy_profile.pathway_colors: null | grey competing pathway (RC1 to TS1' to I1') against black main pathway | not drawn; card value contradicts the crop | no |
| energy_profile.ts_marker: none | TS1, TS2, TS1' with no double-dagger | not drawn | no |
| signature: thick bars, thin solid connectors (the card's 15-17 px and 3x bond-line figures are not reproduced) | reference.png is 900 x 576 px; level bars are about 2 px thick (e.g. rows 360-361 at R1) and connectors about 1 px, so the card's 15 px figure is not reproduced by this file | not drawn | no |
| signature: bold species name and value next to each bar | bold names; value above bar and name below for 7 of 9 levels (TS1 and I1 have both below the bar) | not drawn | no |
| signature: vertical axis arrow at left with DeltaG label in kcal mol-1 | arrow at left; label is a header above the arrow | not drawn | no |
| signature: second pathway grey #808080 vs black | grey vs black as above | not drawn | no |
| top-level: compound labels bold, black #000000 | bold black labels (R1, RC1, TS1, I2) | not verified; scope panels take only the base preset (scheme-drawing.md) | no |
| top-level: abbreviate_groups includes OMe | methyl ester written "MeO" | not verified | no |
| top-level: substrate colours (card value: substrate_colors null) | ester and N2 fragments blue/navy, Fe core black; the card sets no substrate colour for this case | not applied to scope panels | no |
| top-level: highlight_fill (card value #E6E6E6; null only for the substrate_scope type) | no grey box on this crop | scope panels take no house conventions | no |
| top-level: arrow_style plain | no reaction arrow in this crop (the vertical axis is not a reaction arrow); 'open' head not verified | no reaction arrow drawn | no |

Matched: 0 of 14 claimed; the audit confirms 0 of 14 (see Audit).

## Differences from the paper

- No energy levels, values, bars, connectors, axis or caption text are drawn.
- Only two of the nine species in the profile are drawn (R2 and N2). The iron complexes are omitted.
- The two-structure layout is a scope-style panel with two group headings, not the left-to-right energy diagram.

## Tool gaps

- No energy-profile drawer: no level bars with solid connectors, no energy axis with unit, no DeltaG/DeltaE value pairs or name-and-value placement, no pathway colours for levels. `draw_figure` accepts only `scheme`, `scope` and `mechanism`. Not considered: `compose_chemical_figure` (`toolkit/cdxml_toolkit/mcp_runtime/figure_tools.py`) takes manifest `line`, `text` and `arrow` items at explicit coordinates, so levels, connectors and labels could be placed by hand. Not tried; the weight of a thick bar is untested.
- Scope panels take only the house style's base preset (scheme-drawing.md), so the chemeurj bold labels and substrate colours are not applied to a structure panel.
- Partly unsupported: RDKit rejects the uncharged dative form `[C]#[O]->[Fe-]` and reads `[O]=[N]->[Fe-]` only as `FeNO-`. The charge-separated form `[C-]#[O+]->[Fe-](<-[C-]#[O+])(<-[C-]#[O+])->[N]=O` parses in RDKit 2026.03.5 (checked in the audit), so Fe(CO)3(NO)- can be written as a checked SMILES. The other Fe intermediates were not tried.
- No ball-and-stick 3D model output for TS1 and TS2. Checked: no ball-and-stick path exists; `conformers.py` draws perspective cages only.
- `draw_figure --render` depends on the shared ChemDraw COM resource. In this run it hit the 300 s timeout or `resource_busy` on every render attempt. Not verifiable from this folder (no logs are present).
- The scope brief rejects `max_width` (`SCOPE_KEYS` in `toolkit/cdxml_toolkit/mcp_runtime/figure_scope.py`), while the draw brief accepts it. Confirmed. The scope size key is `width_mm` (60 to 400 mm; `figure_scope.py` line 24 and the `draw_figure` docstring), which was not tried.


## Audit

Checked on 2026-11-07 against `reference.png` (900 x 576 px), `brief.json`, `chemeurj.json` and the toolkit code. No `rendered.png` exists in the folder, so no rendered comparison was made.

Overclaims corrected above:

- The `highlight_fill` row cited `null`. The card's top-level value is `#E6E6E6`; `null` is the value for the `substrate_scope` type.
- The substrate-colour row implied a chemeurj convention. The card sets `substrate_colors` to `null` at top level.
- The thick-bar row gave 15-17 px and "about 3x bond line". `reference.png` shows level bars about 2 px thick and connectors about 1 px, so these figures are not reproduced by this file.
- The iron-complex gap was overstated. RDKit 2026.03.5 parses the charge-separated dative form (see the tool gap). Only the uncharged form fails.
- The energy-drawer gap missed the manifest route through `compose_chemical_figure`.
- The `max_width` gap omitted the `width_mm` alternative for scope briefs.

Confirmed as written:

- All nine energy values and their DeltaE values, the grey RC1 to TS1' to I1' pathway, the absence of grey fills, bold black labels, the `MeO` abbreviation, the absence of double-dagger TS markers, and the bare `N2` and methyl diazoacetate structures.
- The card's citation (Anderson/Maes, Chem. Eur. J. 2023, Figure 1, CC BY 4.0, DOI 10.1002/chem.202203074).
- `draw_figure` accepts `scheme`, `scope` and `mechanism` only (`figure_draw.py` line 84), and the `draw_figure` docstring states that scope panels take only the house style's base preset. The scope report says the same ("house conventions apply to schemes only", `figure_scope.py` line 239).
- No ball-and-stick path exists in the toolkit.
- The colour samples: the grey is near #8C8C8C to #9F9F9F and the blue fragments are dominated by anti-aliased values around #0B457C to #174C82.

Not verifiable from this folder or the repository:

- The timings and `resource_busy` messages (254 s, 300 s, 295 s). No logs are present. `draw_scope` rejects unknown keys before any ChemDraw call, so a 254 s refusal for `max_width` means the time was spent before dispatch; this was not traced.
- `meta.json` and `CHEM-29-0-g001.jpg`, and the statement that the Figure 1 file starts from I3. Neither file is in the folder or found by search in the repository.

Replay: `draw_scope` refuses only an existing target (`figure_scope.py` line 181). `replay.py` passes `out/'figure.cdxml'`, which does not exist yet, so it would not be refused and would create a folder named `figure.cdxml`. It is untested, and the failure mode is silent folder creation, not a refusal.

Corrected matched count: 0 of 14. The audit found no row with a replica, so no row can match.
