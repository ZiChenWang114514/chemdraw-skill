# OpenStax Chemistry: EDTA-metal complex (Figure 19.30)

Source: Flowers, Theopold, Langley, Robinson et al., *OpenStax Chemistry* (2015), section 19.2 Coordination Chemistry of Transition Metals, Figure 19.30. Licence CC BY 4.0, as recorded in the house-style card. The card gives no DOI for this figure.

Drawing style: the `openstax_chemistry` house style (card base preset `chemdraw_slide`). Figure type: `coordination_complex`.

## What is reproduced

The one complex in the crop: a hexadentate EDTA chelate on a metal centre, with two amine N and four carboxylate O donors (six metal-donor bonds) and four O atoms carrying a minus charge. The paper's generic metal M is drawn as Ni. A symbol such as [M] fails RDKit SMILES parsing, so a generic M cannot be drawn. Any RDKit-valid element is accepted (Co or Fe would parse too), so Ni was a choice, not a tool limit.

The brief is a `scope` panel with one structure, because `draw_figure` needs a reaction for a scheme and this crop has no reaction. Its SMILES:

`[Ni]%11%12%13%14%15%16.[O-]%11C(=O)CN%15(CC(=O)[O-]%12)CCN%16(CC(=O)[O-]%13)CC(=O)[O-]%14`

RDKit reads the six metal bonds as dative. No conditions, yield or caption are drawn. The final brief is the second try; the first try differed only in the species id and label, and the layout was the same.

## Attempts

1. Species id `M-EDTA` as the caption. Drawn and rendered; the panel shows the title "Substrate scope" and the caption "M-EDTA".
2. Species id `M` with an empty label, which the tool still captions with the id. Same layout and the same title. This is the final brief in `brief.json`.

No brief field changes the metal geometry, so further brief tries would not help; the layout is set by the 2D coordinates the tool generates from the SMILES.

## Replay

```
python skill/chemdraw/scripts/cdx.py py skill/chemdraw/assets/house-styles/openstax_chemistry/replica/openstax_chemistry-06/replay.py NEW_DIR
```

`replay.py` runs `draw_figure` on `brief.json` without network access and writes `figure.cdxml` and `validation.json` into the new folder. It was not run here; the same brief was drawn with `cdx.py draw` (report `checks_passed` true, readback `matched`, one structure drawn; not verifiable from this folder, which holds no validation.json or figure.cdxml; the readback compares fragment inventory only, not geometry). A draw takes about four minutes and a native render several more.

## Comparison table

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| dative_bond_style `line` | metal-donor bonds drawn as lines (axial plain, equatorial as wedges) | all six metal-donor bonds drawn as plain lines, none as wedges; the plain lines are the tool default, since scope panels never read dative_bond_style | no |
| octahedron: plain axial lines, bold wedges in front, hashed wedges behind | two plain axial lines, two bold and two hashed equatorial wedges | no octahedron; all bonds plain lines; bonds cross and overlap O- labels | no |
| metal and its six donor bonds red-brown #983820 | red-brown | black (`metal_color` is not applied to scope panels) | no |
| ligand in black | black | black (colour only; the CH2 labels are missing) | yes |
| formal charge as plain superscript minus (`formal_charge_style` plain) | O with superscript minus | O- with superscript minus; base preset output, since scope panels never read formal_charge_style | yes (by eye) |
| label font Arial or Helvetica (top level) | plain sans-serif | Arial-like by eye; base preset default, not a house convention applied | yes (by eye) |
| text colour #000000 (top level) | black | black; base preset default | yes (by eye) |
| bond length over cap height 3.35 (top level) | not measured for this crop in the card | not measured; scope panels take the base preset geometry, so the house value cannot be applied | no (unverified) |
| line width over bond length 0.042 (top level) | not measured for this crop in the card | not measured | no (unverified) |
| square brackets with the charge top right (card signature feature) | no brackets in this crop; the bracket rule belongs to crop 04 | no brackets | not applicable |
| arrows and plus signs (top level) | none in this crop | none | not applicable |
| yield, conditions, condensed CH2 labels, layout | no yield or conditions in this crop; ligand CH2 labels; symmetric upright complex | no yield or conditions; no CH2 labels; tilted layout with labels over bonds | no |

Matched 4 of 7 table rows (ligand colour, charge style, label font and text colour, the last three by eye). The earlier count of 5 of 7 treated dative_bond_style as matched, which the paper column contradicts. The card does not list five conventions for this figure type: coordination_complex has four convention keys (dative_bond_style, metal_color, highlight_fill, formal_charge_style), two of them null in the card, plus three signature features. The bracket feature is left out of the count because the crop does not show it.

## Differences from the paper

- Geometry: the replica has no octahedron. The 2D coordinates come from RDKit, so the two carboxylate O- labels collide with the Ni label and the metal bonds cross the ligand. The figure does not read as a six-coordinate complex.
- Bond styles: the equatorial bonds are plain lines, not bold and hashed wedges.
- Colour: the metal and its six donor bonds are black, not red-brown #983820.
- Metal symbol: Ni in place of the generic M.
- Ligand: the carbons are drawn as skeleton vertices, not as black condensed CH2 labels.
- Extra text: the panel title "Substrate scope" and the caption "M" are added by the tool.
- Overall charge: none is shown, the same as the paper; the drawn fragment carries four minus charges on O and a neutral metal.

## Tool gaps

- No control over metal-complex geometry: no octahedral or specified-angle layout for a metal with six donors, and no coordinates in the brief.
- No wedge or hash style for individual coordination bonds (bold front, hashed back) in the brief or in species records.
- No colour for a metal and its donor bonds: `metal_color` is not implemented, and scope panels take only the base preset (the report says house conventions apply to schemes only).
- No generic metal symbol and no custom atom label text.
- No condensed CH2 labels for chain carbons; `abbreviate_groups` is not applied to scope panels at all (house conventions are read for schemes only), so it cannot help here.
- A scope panel always adds the title "Substrate scope", and an empty title does not remove it; the caption is the species id.
- A single structure with no reaction has no dedicated brief in `draw_figure`; the scope panel is the only route, and it carries the scope title.
- Long runtimes: a draw takes about four minutes and a native render several more, so foreground calls time out (render worker exit 143 at 115 s).
- House measured geometry (bond length over cap height 3.35, line width over bond length 0.042) cannot reach a scope panel, which takes only the base preset; this is why the two geometry rows are unverified.
- The validator checks only the fragment inventory (`_readback` in figure_scope.py), so it passes overlapping labels and crossing bonds; the brief has no way to fix the 2D layout or to check geometry.
- No bracket or charge-frame option for a complex ion: the species keys (id, smiles, name, label, group, values) and the brief keys have no such field.

## Audit

Checked against reference.png, rendered.png, brief.json, the card (openstax_chemistry.json, coordination_complex and structure conventions) and the scope path code (figure_scope.py, figure_draw.py).

- The dative_bond_style row was marked yes. The paper has bold and hashed equatorial wedges, the replica has none, and the plain lines come from the tool default, not from the card value.
- The count was 5 of 7. It is 4 of 7. "The card's five" is not what the card lists.
- The charge style, label font and text colour matches are base-preset output. Scope panels never read the house conventions, so these rows show the defaults happen to agree, not that the house style was applied. They match by eye only.
- "The only element the tool accepts" was false. RDKit rejects [M] but accepts other elements.
- The validation and readback results cannot be checked from this folder. The readback compares fragment inventory only.
- abbreviate_groups is not applied to scope panels at all.
- The bond length and line width rows were never measured. They are now "no (unverified)".
- Layout is not matched. The replica is tilted, the O- labels sit on the Ni-N bonds and the Ni label, and the top and bottom ligand bonds cross the chelate. A dark filled triangle beside the right N and O- label may be a wedge or an overlap; it is not confirmed, and if it is a wedge, "none as wedges" is also wrong.
- Corrected count: 4 of 7 table rows matched, all four by eye or by colour only.
