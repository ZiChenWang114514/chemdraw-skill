# OpenStax Chemistry 2015, Figure 12.19: NO2 + CO through a transition state to NO + CO2 (section 12.6 Reaction Mechanisms)

Source: Flowers, Theopold, Langley, Robinson et al., *OpenStax Chemistry* 2015, section 12.6 Reaction Mechanisms, Figure 12.19. The card gives no DOI; the source is the CC BY 4.0 edition named in `house_styles/openstax_chemistry.json`. Reference crop: `evidence/openstax_chemistry-03.png` (copied to `reference.png`).

Licence: CC BY 4.0. Figure number and section are taken from the card; the crop itself carries no caption.

Drawing style: the `openstax_chemistry` house style (base preset `chemdraw_slide`), in `brief.json`.

Figure type: `reaction_scheme` and `mechanism` (the card lists crop 03 under both).

## What is reproduced

The three-panel sequence of the crop, as one plain reaction row: NO2 + CO, then a transition-state structure, then NO + CO2. Two plain arrows, inline plus signs, no conditions and no yields (the crop has none).

The ball-and-stick and space-filling models are not reproduced. Each species is drawn as a line structure. The transition state is a stand-in, `O=[C]ON=O` (formyl nitrite-type connectivity, one radical carbon), not the geometry shown in the crop.

Species and SMILES in `brief.json`:

| Species | SMILES | Note |
| --- | --- | --- |
| NO2 | `[O]N=O` | radical on terminal O (resonance form) |
| CO | `[C-]#[O+]` | charge-separated form |
| TS | `O=[C]ON=O` | stand-in for the activated complex; not a verified TS |
| NO | `[N]=O` | radical |
| CO2 | `O=C=O` | |

All formulas were checked with RDKit (atoms and electron count balance per step; the tool reports `balanced: true` for both steps).

## Build

Three draft runs, all with `--render` through desktop ChemDraw:

1. `max_width` 504 (default): two rows; a 243 pt drawing against a 241.92 pt budget; relayout narrowed the budget to 378 pt, wrapping the route and drawing the TS twice.
2. `max_width` 520: still two rows (sequential layout), but all checks pass.
3. `max_width` 1000: one row; checks pass. This is the final brief and the one rendered in `rendered.png`.

## Replay

```
python skill/chemdraw/scripts/cdx.py py skill/chemdraw/assets/house-styles/openstax_chemistry/replica/openstax_chemistry-03/replay.py NEW_DIR
python skill/chemdraw/scripts/cdx.py render NEW_DIR/figure.cdxml
```

`replay.py` draws `brief.json` offline, so the replay uses the 1000 pt row budget.

## Convention table

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| substrate_layout `inline_plus` (A + B on one line) | `NO2 + CO` inline | `NO2 + CO` inline | yes |
| show_plus_sign `true` | plus between substrates and between products | plus signs present | yes |
| arrow_style `plain` (thin shaft) | thin plain shafts | thin plain shafts | yes (shaft only; the base preset sets it, the style's arrow_style is not applied by code) |
| arrow head (card: filled head) | open V head | filled-looking head | no (card wrong for crop 03) |
| arrow length about 2.5 bond lengths | not checkable on crop 03 (ball models); the card's ratio is 2.5 | 150 pt arrow on a 30 pt bond, 5.0 bond lengths in the saved file | no (twice the style ratio) |
| mechanism: space-filling CPK ball models | O red, N blue, C dark grey | line structures, no atom colours | no (tool gap) |
| mechanism: white element letters in the balls | white letters in spheres | black letters, no spheres | no (tool gap) |
| mechanism: TS labelled "Transition state", small plain text | text under the activated complex | not drawn; a species `label` does place text 14 pt under the species, but the replica does not set it | no (not drawn; the stated tool gap is wrong, see Audit) |
| mechanism: no brackets or double dagger on the TS | no brackets | none | yes |
| label face: house `label_font` Arial or Helvetica | sans-serif element letters and label text | atom and species labels in Times New Roman 16 pt plain (font 4); the header declares Arial 12 pt | no (not applied; see Audit) |
| bond line width about 0.042 of bond length (card measured) | not checkable on crop 03 (no line bonds) | 1.6 pt bond on a 30 pt bond = 0.053 | no (about 27 % heavier than the card's ratio) |
| reaction_scheme: changed atoms and new bond in #901800 | none in crop 03 (CPK colours instead) | none | n/a (card claim not in crop 03) |
| reaction_scheme: dashed lime-green #7CE400 boxes around functional groups | none in crop 03 | none | n/a (card claim from crop 09) |
| reaction_scheme: "Condensation reaction" beside a vertical arrow | none in crop 03 | none | n/a (card claim from crop 09) |
| species named in plain Arial words, never numbered | no species names in crop 03 | no names | n/a (card claim not in crop 03) |

Matched: 4 of the 11 rows that apply to crop 03 (rows 1, 2, 3 and 9 of the table, plus the new label face and line width rows, which do not match). Row 3 is the shaft only; row 9 is an absence (no brackets). The n/a rows are not in crop 03. See Audit.

## Differences from the paper

- Ball models: the paper draws every species as a space-filling model in CPK colours with white element letters. The replica draws line structures, so the atom-colour convention is missing entirely.
- Transition state: the paper shows an activated complex with the N bonded to two O and a C-O chain. The replica uses a formyl-nitrite stand-in. The "Transition state" label is missing under the structure; it cannot be placed there (see Tool gaps).
- Layout: the paper is one row. The default width wrapped the route into two rows and duplicated the TS; a 1000 pt budget was needed for a single row.
- Electron marks and charges: the crop shows none, while the replica draws charges on CO and an N-O radical state. The render shows no radical dots.
- Arrow head: the paper uses an open V head; the replica uses a filled head.

## Tool gaps

- No space-filling or ball-and-stick atom rendering in `draw_figure`: atoms cannot be given CPK colours, white element letters or sphere geometry.
- A label cannot be placed under a species. `above` and `below` attach to the arrow, so the "Transition state" label lands under the arrow, not under the TS.
- No way to draw an activated complex with partial (dashed) bonds or a true TS geometry. The replica needs a closed SMILES stand-in.
- The automatic re-layout narrows the row budget instead of trying a wider one. A drawing 1 pt over budget wraps the route into two rows and duplicates the TS in the second row.
- Radical state is not shown in the render; this crop shows no electron marks either, so the difference is only in what the saved file records.


## Audit

Checked: both PNGs enlarged at the arrow heads and labels; the saved CDXML from replaying `brief.json` offline into a scratch folder (no ChemDraw render, so the render was not reproduced); the toolkit code for the style, label, arrow and relayout paths. No other file in the case folder was changed.

Overclaims corrected in the table:

- Arrow length: the replica arrow is 150 pt on a 30 pt bond, 5.0 bond lengths, twice the style's 2.5. "From the style" was wrong and "not checkable" hid it. Row is now no.
- Label face: atom and species labels are Times New Roman 16 pt plain (font 4), the header's CaptionFont and CaptionSize, not the Arial 12 pt LabelFont it declares. No code reads the style's `label_font`, and the style report does not list it as skipped.
- Line width: 1.6 pt bonds on 30 pt bonds is 0.053 of bond length, against 0.042 on the card. Crop 03 has no line bonds, so the crop itself cannot check it.
- Arrow style: the style's `arrow_style` is not applied by code (it is in neither the applied nor the skipped list). The thin shaft comes from the base preset.
- Arrow head: confirmed no. The replica head is solid (`ArrowheadType="Solid"`), crop 03 has an open V.
- Matched count: "3 of 12, rows 1, 2 and 8" contradicts the table, where row 8 is no and the yes rows are 1, 2, 3 and 9. Corrected: 4 of 11 applicable rows. Rows 10 to 13 are not in crop 03 (it uses CPK colours, has no dashed boxes, no condensation text, no species names) and are excluded. The card's reaction_scheme crop list includes crop 03 while its own notes say crop 03 uses CPK instead, so the card is internally inconsistent.
- Label colour: black matches the style value (`compound_label_color` #000000), but the crop's element letters are white (row 7), so it is not counted.

Tool gaps, corrected:

1. "No label under a species" is refuted. A species `label` is drawn 14 pt below the structure. A test replay with `label: "Transition state"` on the TS put the text centred under the TS fragment (centre x 615.6 pt, 14 pt below its bottom edge). It is Times New Roman 16 pt, so face and size still fail, but the placement is possible.
2. "No CPK colours or sphere geometry" is partly refuted. `atom_halos` draws coloured filled discs behind atoms and `substrate_colors` colours atoms. Still missing: shaded spheres, per-atom white letters, and bonds hidden behind spheres.
3. Partial or dashed bonds: true for the `draw_figure` brief, but crop 03 shows no partial bonds, so this gap is not needed for this crop.
4. Relayout: true. The budget is multiplied by 0.75 (`RELAYOUT_WIDTH_FACTOR`), so a 1 pt overrun costs about a quarter of the row budget.
5. Radical state: not a capability gap. The saved file carries `Radical="Doublet"` on three atoms (NO2 oxygen, TS carbon, NO nitrogen), and rendered.png shows no dot. Charges (O+ and C-) are visible in the render, so "only in what the saved file records" is wrong for charges. The replica adds charges and radicals that crop 03 does not show.

Gaps the replicator missed:

- Label face and size: atom and species labels take the header's caption font and size. No brief option changes this.
- House measured geometry (arrow length ratio, bond line width, label font) is loaded from the card and never applied, and the style report does not list it as skipped, so output can silently differ from the card.
- No single-shaft open-V arrow head in `draw_figure`: solid arrows are always `Solid`. The only Angle head is the `retro` style of `compose_chemical_figure`, which doubles the shaft.

The Differences and Tool gaps sections above are superseded where they conflict with this note.
