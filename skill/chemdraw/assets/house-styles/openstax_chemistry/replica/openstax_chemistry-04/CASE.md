# OpenStax Chemistry: cis and trans [Co(H2O)4Cl2]+ (Figure 19.21)

Source: Flowers, Theopold, Langley, Robinson et al., *OpenStax Chemistry* (2015), section 19.2 Coordination Chemistry of Transition Metals, Figure 19.21. Licence CC BY 4.0. No DOI is recorded on the card. The crop is `skill/chemdraw/assets/house-styles/openstax_chemistry/evidence/openstax_chemistry-04.png` (copied as `reference.png`).

House style: `openstax_chemistry` (card in `toolkit/cdxml_toolkit/publication/house_styles/openstax_chemistry.json`), figure type `coordination_complex` (also `stereo_model`, since the crop is cited under both).

## What is reproduced

Only the ligand set of the complex: one [Co(H2O)4Cl2]+ ion with the Co centre, four aqua ligands and two chloro ligands, drawn in a `kind: "scope"` panel with the title "Isomers of [Co(H2O)4Cl2]+" and the label "cis or trans, stereo not drawn". The cis and trans isomers, the square brackets, the charge placement, the octahedral geometry and the wedges and hashes are not reproduced. `draw_figure` refused the stereo (see Tool gaps).

Structure (checked with RDKit: formula H8Cl2CoO4+, charge +1, no stereo):

`[OH2]->[Co+](<-[OH2])(<-[OH2])(<-[OH2])([Cl])[Cl]`

The intended isomers (the Cl-Co-Cl angle was measured on RDKit ETKDG embeddings: 89.6 degrees for the cis tag, 179.4 degrees for the trans tag; the tool refused both):

- cis: `[OH2]->[Co@OH23+](<-[OH2])(<-[OH2])(<-[OH2])([Cl])[Cl]`
- trans: `[OH2]->[Co@OH21+](<-[OH2])(<-[OH2])(<-[OH2])([Cl])[Cl]`

No OCSR was run; the structure was read from the crop and checked by formula.

## Files

- `brief.json`: the brief that produced the replica (`kind: "scope"`, `style: "openstax_chemistry"`).
- `rendered.png`: native ChemDraw rendering of the panel (471 x 430 px, 21 KB), made with `cdx.py render` on the cdxml that `cdx.py draw` wrote.
- `replay.py`: copy of the jacs-au replay with the docstring changed. The output path is changed to a folder (`panel`), because scope panels take a new folder rather than a `.cdxml` file. The replay was run offline and wrote `panel/page-001.cdxml` and `validation.json`.

## Attempts

1. cis and trans stereo tags, scope panel: refused with `unsupported_stereochemistry: non-tetrahedral center needs a native template`.
2. A typing error in the first non-stereo brief gave five aqua ligands (`[OH2]->[Co+](<-[OH2])` x4 plus the first). The render timed out at 300 s. This is not the chemistry in the crop and is not used.
3. The same wrong brief again: draw written, render stopped with `resource_busy` (chemdraw_com busy for 175 s).
4. Corrected brief (four aqua, two chloro), with `--render`: draw_figure exceeded 300 s.
5. Corrected brief, drawn without `--render` (layout and read-back passed, `readback.status: matched`, one structure), then `cdx.py render` on the cdxml, which succeeded. This is the rendered.png.

## Comparison

Counts cover the figure-type claims that apply to this crop (9 rows, 2 of them n/a). The top-level rows (6 measured or visible items) are listed below the table.

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| coordination_complex: dative_bond_style "line" | Co to the two axial ligands as plain lines; the four equatorial bonds are wedges (two hashed, two bold), so not all bonds are plain | one flat set of single bonds, no dative bonds, no wedges | no |
| coordination_complex: metal_color null | Co black | Co black | yes |
| coordination_complex: highlight_fill null | none | none | n/a (card value null, nothing to match) |
| coordination_complex: formal_charge_style "plain" | plain superscript + at top right of the square bracket | plain superscript style, but on the Co atom and no bracket | no (style matches, placement does not) |
| signature: octahedra, plain axial lines, bold wedges in front, hashed wedges behind | octahedral projection with two hashed and two bold wedges | flat six-bond star around Co, no wedges, no hashes | no |
| signature: complex in square brackets, charge top right | brackets, + at top right | no brackets | no |
| stereo_model: highlight_fill null | none | none | n/a (card value null, nothing to match) |
| stereo_model: model_style "perspective_3d" | flat 2D projection with wedges and hashes | flat 2D, no wedges | no |
| stereo signature: cis and trans side by side, cis and trans in italic | two isomers in titles "Violet, cis form" and "Green, trans form" | one structure, no stereo, plain title | no |

Not counted (not visible in crop 04): coordination signature "metal and donor bonds in red-brown" (crop 06), stereo_model variation_color (crop 08), mirror line (crop 05), line formula stacked over models (crop 08), ts_marker null.

Top-level scheme conventions visible in the crop:

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| compound_label_color #000000 | black | black | yes |
| label font Arial | Arial | Arial-like face on visual check only; the cdxml is not in the case folder, so 'preset font from the cdxml manifest' is unverified | yes (visual only) |
| show_plus_sign | + shown on the complex | + shown, but on Co (presence only) | yes (presence only) |
| bond_length_over_cap_height 3.35 | 55 / 15 = 3.67 on this crop | about 5.3 as stated, but the stated '30 pt over 8 pt' gives 3.75, so 5.3 needs an unstated cap height of 5.7 pt. Pixel check: roughly 6 (bond about 130 to 145 px over a 23 px cap) | no |
| line_width_over_bond_length 0.042 | 2 / 55 = 0.036 on this crop | 1.6 / 30 = 0.053 as stated. Pixel check: about 6 to 7 px of ink on the Cl bond, about 0.05 | no |
| bold_width_over_bond_length 0.24 | 13 / 55 = 0.24 | no bold wedge drawn | no |
| arrow style and arrow length | no arrow in this crop | none | n/a |

Top-level matches: 3 of 6 applicable (colour, font, plus sign; font and plus sign are weak, see Audit). Figure-type matches: 1 of 7 applicable (the earlier 4 of 9 counted two null rows as matches).

## Differences from the paper

- One structure instead of the cis and trans pair. The paper's titles "Violet, *cis* form" and "Green, *trans* form" are replaced by a placeholder label, "cis or trans, stereo not drawn", which is not in the paper.
- A title "Isomers of [Co(H2O)4Cl2]+" is added, because the scope panel needs one.
- Ligands: the paper writes H2O with a subscript 2. The rendered panel mixes "H2O" (two ligands) and "OH2" (two ligands), since ChemDraw chooses the orientation of the label.
- The complex has no square brackets and the + sits on the Co atom, not at the top right of a bracket.
- The geometry is a flat star, not an octahedron. The paper's two axial Cl or H2O lines, bold and hashed wedges are missing.
- The bonds are heavier relative to the labels than in the crop (see top-level rows).
- The house-style conventions are not applied to a scope panel: the tool reports "house conventions apply to schemes only; the base preset was applied", so the replica uses the chemdraw_slide base preset alone.

## Tool gaps

The refusals below are real. Two gaps the replicator listed are overstated, and some gaps are missing; see Audit.

- Octahedral stereo is refused by `draw_figure` (brief path): `unsupported_stereochemistry: non-tetrahedral center needs a native template`, raised in `chemistry_semantics.require_supported`. A cis or trans [M(L)4X2] stereo tag cannot be encoded through the brief path.
- Partly wrong: `compose_chemical_figure` (manifest path) accepts molecules with explicit coordinates and `bond_displays` (WedgeBegin, WedgedHashBegin, Bold, Dash) on any bond, including Co to ligand bonds. There is no octahedral template, so the six positions must be placed by hand.
- Scope panels skip house-style conventions: the scope path reports "house conventions apply to schemes only; the base preset was applied".
- A scope panel always has a title: `brief.get("title") or "Substrate scope"`, so an empty title also falls back to the default. The manifest path has no default title and can omit it.
- Partly wrong: square brackets are possible on the manifest path. The `bracket` object draws the pair, and superscript text runs give the top-right charge. `ts_bracket` is not needed. The bracket's own `label` is plain text placed at its bottom right.
- No ligand label control on molecule objects: the molecule fields have no per-atom label override. Text runs can write H2O with a subscript, but ChemDraw still draws the atom's own label.
- `draw_figure --render` timed out twice and returned `resource_busy` once. The cause (ChemDraw contention from other sessions) is not verified. `compose_chemical_figure` returns `native_render: not_run` and needs a separate render.

## Audit

Checked against reference.png, rendered.png, brief.json, the house card and the toolkit source. Pixel figures are rough (grey threshold 128).

Overclaims corrected:
- The `dative_bond_style "line"` row described the paper as plain lines to every ligand. The four equatorial bonds are wedges, so the row is now "no". The replica has no dative bonds.
- The two `highlight_fill null` rows counted "none = none". The card value is null, so there is nothing to match; they are now n/a. Figure-type matches are 1 of 7 applicable, not 4 of 9. The only real figure-type match is metal colour (black, crop 04).
- The replica star has six bonds, not five.
- The formal-charge row: the style (plain superscript) matches; the placement does not. It stays "no".
- The bond/cap and line/bond derivations cannot be checked from this folder: `panel/`, `validation.json` and the cdxml are not here. The stated "30 pt over 8 pt" gives 3.75, not 5.3. Pixel estimates are about 6 (bond over cap height) and about 0.05 (line over bond), both still outside the targets, so the "no" verdicts stand.
- "Preset font, from the cdxml manifest" cannot be checked here. Visually the labels are Arial-like.
- show_plus_sign matches on presence only; the plus sign sits on Co, not on a bracket.
- The Cl-Co-Cl angles are close but not exact: RDKit ETKDG (seed 42) gives 88.6 and 178.0 degrees, against 89.6 and 179.4 stated, and no seed is recorded. The SMILES parse, and the octahedral tags give cis and trans geometry.
- The cause of the render timeouts ("ChemDraw contention") is not verified.

Corrected count: figure-type 1 of 7 applicable; top-level 3 of 6 applicable, with font and plus sign weak.

Gaps the replicator did not list:
- `compose_chemical_figure` has no stereo check on its path (by code reading, no `require_supported` call), so an octahedral tag in a manifest SMILES may be dropped without an error. Not tested.
- The compose `style` object takes bond_length, line_width, bold_width, hash_spacing and font_size. The card's measured ratios can be set there by hand; neither drawing path applies the card automatically. Not tested end to end.
- Dative bonds are written from the ligand to Co (the RDKit begin atom is the O). WedgeBegin or WedgedHashBegin therefore taper at the ligand. A wedge with its narrow end on Co needs WedgeEnd or WedgedHashEnd on those bonds. Not checked visually.
