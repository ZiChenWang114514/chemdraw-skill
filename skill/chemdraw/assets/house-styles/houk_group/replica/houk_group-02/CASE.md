# Galeotti, Houk, Bietti et al., JACS 2023: energy profile for S3 (Figure 5), first step only

Source: Galeotti, Houk, Bietti et al., "Radical and cationic pathways in C(sp3)-H bond oxygenation by dioxiranes", *J. Am. Chem. Soc.* **2023**. DOI: [10.1021/jacs.3c07163](https://doi.org/10.1021/jacs.3c07163).

Licence: CC BY 4.0, reference crop reproduced under that licence (`reference.png` is `evidence/houk_group-02.png` of the `houk_group` card).

Figure type: `energy_profile` (the crop is the Figure 5 energy profile; the `mechanism` section of the card also lists this crop). The house style is `houk_group` (base preset `acs1996`).

## What is reproduced

The reactant side and the products of the S3 profile, as one scheme: S3 (1-methylbicyclo[4.1.0]heptane, drawn from the crop) with 3-ethyl-3-(trifluoromethyl)dioxirane gives the C2 alcohol P3-OH2 and 1,1,1-trifluorobutan-2-one. The step is balanced (C12H19F3O2 on each side; S3 C8H14, dioxirane C4H5F3O2, P3-OH2 C8H14O, ketone C4H5F3O). Structures are written in `brief.json`:

| ID | SMILES | Source of the structure |
| --- | --- | --- |
| S3 | `CC12CCCCC1C2` | read from the crop (methyl on the cyclopropane bridgehead, cyclopropane fused to a six-membered ring); the ring-position numbers 2 and 5 match the C2 and C5 products in the crop |
| dioxirane | `CCC1(OO1)C(F)(F)F` | drawn in the crop with an ethyl and a CF3 on the dioxirane carbon |
| P3-OH2 | `CC12C(O)CCCC1C2` | OH on the ring carbon next to the methyl-bearing bridgehead; relative stereo not drawn (the crop shows cis and trans) |
| ketone | `CCC(=O)C(F)(F)F` | drawn in the crop as the propanone-CF3 product |

No OCSR was run; the SMILES were parsed with RDKit and their canonical forms and formulas checked; they follow the crop's drawing. The brief has no conditions, because the crop gives none.

Not reproduced: the energy profile itself. The crop's four pathways, the transition states (S3-TS1, S3-TS2, S3-TS3), the intermediates (S3-Int1, S3-Int2), the energy values and the level bars are outside what `draw_figure` can express, so they are not drawn.

## Replay

```
python skill/chemdraw/scripts/cdx.py py skill/chemdraw/assets/house-styles/houk_group/replica/houk_group-02/replay.py NEW_DIR
python skill/chemdraw/scripts/cdx.py render NEW_DIR/figure.cdxml
```

`replay.py` runs `draw_figure` on `brief.json` offline and writes `figure.cdxml` and `validation.json`. `rendered.png` is the desktop ChemDraw render of the same brief (1200 px wide, downscaled from 1450 px).

## Comparison with the card

Convention rows cover every claim the card makes for `energy_profile` and `mechanism`, plus the top-level scheme conventions visible in the crop. Match: `yes`, `partial`, `no`, or `n/a` when the crop does not show the feature (n/a rows are not counted).

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| energy_unit kcal/mol | bare numbers on this crop (unit only on the crop 03 axis) | no energy values drawn | no |
| energy_label delta_G | energy values as bare numbers, no delta-G label on this crop | not drawn | no |
| level_style bars_solid_connectors | short thick level bars joined by thin solid sloped lines | no profile drawn | no |
| pathway_colors (red, blue, orange, green) | four pathways in four colours, connectors black | single black drawing | no |
| energy value above each bar, bold italic, pathway-coloured | yes | not drawn | no |
| structure next to every stationary point | yes, for S3, TS1, Int1, TS2, P3 and Int2 | only S3 and P3-OH2 (2 of 6); the ketone is a product, not a stationary point; no TS or intermediate | no |
| TS partial bonds dashed | dashed forming bonds in the S3-TS1 drawings | not drawn | no |
| spectator fragments in light grey | light grey CF3-C(OH)O fragment in S3-Int1 and S3-TS2 | not drawn | no |
| double slash breaks on long connectors | yes, on the long descents | not drawn | no |
| species labels bold italic in pathway colour | bold italic, coloured (S3-TS1C2trans red, P3-OH2 blue) | bold black S3 and P3-OH2 | partial |
| conformational chair drawings with reacting H coloured | chairs with the reacting H in orange or green | not drawn | no |
| mechanism: formal_charge_style circled | circled plus and minus on S3-Int1 and S3-TS2 | no charges drawn | no |
| mechanism: radicals drawn as dots | dots on the O atoms of the S3-TS1 structures | not drawn | no |
| mechanism: show_lone_pairs false | no lone pairs drawn | no mechanism is drawn, so the row is untested | n/a |
| mechanism: curved_arrow_color and curved_arrow_weight null | no curved arrows on this crop | no mechanism is drawn, so the row is untested | n/a |
| mechanism: ts_marker null | TS names only, no square brackets on this crop | no TS is drawn, so the row is untested | n/a |
| compound_label_face bold | bold italic labels (S3 and P3-OH2 in crop 02, per the species row below) | bold upright on S3 and P3-OH2 (LabelFace 1); no italic | partial |
| compound_label_color #000000 | black on S3; TS and P3 labels in pathway colours (cis-P3-OH2 blue, trans-P3-OH2 red) | black on S3 and P3-OH2 | partial |
| abbreviate_groups includes CF3 | CF3 | CF3 (abbreviated by the tool) | yes |
| show_plus_sign true | plus sign before the ketone | plus signs drawn | yes |
| substrate_layout inline_plus | plus sign between the products; the dioxirane is drawn apart from S3 | plus signs between S3 and the dioxirane and between the products | partial |
| reagent_text_color #000000 | no reagent text on this crop | no reagent text drawn | n/a |
| Me abbreviation on the methyl (top-level, not in card list) | methyl labelled Me | methyl drawn as a bond line with no label | no |
| bond length over cap height 2.4 (card measurement) | crop 02 gives about 2.0 (85 px bond, 42 px cap height); the 2.4 value matches crop 01 (105 px over 43 px) | 14.40 pt bond over a 10 pt Arial label, cap height about 7.2 pt, so about 2.0 | no |
| line weight, line_width_over_bond_length 0.09 (card measurement) | crop 02 gives about 0.09 (8 px line over 85 px bond) | 0.60 pt line over a 14.40 pt bond, 0.042 (acs1996 preset; the house value is not applied) | no |
| arrow_style plain, arrow about 6.2 bond lengths | no reaction arrow on this crop (energy connectors only) | plain arrow of 72 pt, which is 5.0 bond lengths (not about six) | n/a |

Rows counted after audit: 21 (n/a rows not counted). Matched: 2 (yes). Partial: 4. No: 15. The replicator's count was 8 of 24.

## Differences from the paper

- The figure is a one-step scheme, not an energy profile. The paper's content is the four competing pathways, their energies and their transition states, and none of that is drawn.
- The paper shows both cis and trans P3-OH2 as products from separate pathways; the replica draws one alcohol with no stereo and one ketone.
- The methyl groups are bond lines, not "Me" labels.
- The dioxirane is drawn beside S3 with a plus sign, where the paper places it as a separate reagent with no plus sign.
- Labels are bold black; the paper uses bold italic labels in pathway colours.
- The paper's ring-position numbers (2, 5), chair conformers, grey spectator fragments and dashed TS bonds are not drawn.

## Tool gaps

- No energy-profile drawer: no level bars, no sloped connectors, no energy labels with units, no per-pathway colouring of energies or labels, no double-slash break on long connectors.
- No transition-state drawing with dashed forming bonds, and no ring-position number labels on a structure.
- No chair conformer with a coloured reacting H in the draw_figure brief. The conformer templates are documented for the acs_builder path in scheme-drawing.md, but they were not used here.
- No species-level label colour or italic option in `draw_figure`; `compound_label_color` is only the house style's black.
- No Me abbreviation in the house style's `abbreviate_groups`, so the methyl is always a bond line (the card does not list Me).
- No circled-charge or radical-dot placement in a scheme brief; those exist only for `kind: "mechanism"` moves, which need the electron moves stated, and the energy profile has no mechanism brief of its own.
- No drawer for a diastereomer pair from separate pathways; the card's cis and trans products cannot be expressed as one scheme without a stereo SMILES.

## Audit

Second pass by an auditing agent. It re-read `reference.png`, `rendered.png`, `CASE.md`, `brief.json` and `houk_group.json`, and re-ran `replay.py` offline into a scratch directory to read the CDXML. Nothing else in this folder was changed.

**Overclaims corrected.**

- Five of the eight "yes" rows were vacuous. The replica draws no mechanism, no transition state and no reagent text, so `show_lone_pairs`, the curved-arrow rows, `ts_marker` and `reagent_text_color` are now n/a and not counted.
- `compound_label_face` and `compound_label_color` are now partial. The paper's species labels are bold italic (the species row says so), and TS and P3 labels are coloured. The replica's labels are bold upright and black.
- The structure row is now no: only S3 and P3-OH2 are drawn, 2 of the 6 stationary points.
- Bond/cap-height is now no. The CDXML gives `BondLength` 14.40 pt and `LabelSize` 10 pt, so the ratio is about 2.0 against the card's 2.4.
- A line-weight row is added as no. `LineWidth` is 0.60 pt over a 14.40 pt bond (0.042), against the card's 0.09 and the crop's 0.09.
- The arrow is 72 pt, which is 5.0 bond lengths, not "about six". The row stays n/a because crop 02 has no arrow.
- Confirmed as matched: the CF3 abbreviation and the plus signs.
- Confirmed as not matched: the methyl is not labelled Me.

**Corrected count.** 2 matched of 21 counted rows (the replicator claimed 8 of 24).

**Tool gaps the replicator missed.**

- The house `measured` block is never applied. `draw_figure` accepts only `kind`, `species`, `steps`, `max_width`, `title`, `style` and `layout` (`figure_draw.py`, `BRIEF_KEYS`). `figure_house.apply_house_conventions` reads only the preset line width and the figure-type arrow weights. Line width, bold width, bond/cap ratio and arrow length therefore fall back to the acs1996 preset without any entry in `applied` or `skipped`, while the report still says `house: houk_group`. This is a silent gap.
- No brief key sets label size or arrow length, so the bond/cap ratio and the 6.2-bond arrow cannot be reached.
- Substrate layout is `inline` or `stacked_plus` only (`figure_draw.py` line 206). A reagent drawn beside the arrow without a plus sign cannot be expressed, so the replica puts a plus between S3 and the dioxirane.
- Bold width is not controllable either (crop 02 gives 0.22 of the bond length, the replica 0.139).
