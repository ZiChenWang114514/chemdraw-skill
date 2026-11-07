# Galeotti, Houk, Bietti et al. 2023: S8 oxidation pathway (Figure 7, energy profile)

Source: Galeotti, Houk, Bietti et al., "Radical and cationic pathways in C(sp3)-H bond oxygenation by dioxiranes", *J. Am. Chem. Soc.* **2023**. DOI: [10.1021/jacs.3c07163](https://doi.org/10.1021/jacs.3c07163).

Licence: CC BY 4.0. The reference crop (`reference.png`) is reproduced under that licence.

Drawing style: the `houk_group` house style in `brief.json` (base preset ACS Document 1996). The card's `energy_profile` section is the figure type that applies to this crop.

## What is reproduced

Only the chemistry of the crop that `draw_figure` can express: the oxidation of the substrate S8 by 3-ethyl-3-(trifluoromethyl)dioxirane to the C4 alcohol P8a-OH and the ketone 1,1,1-trifluorobutan-2-one, drawn as one scheme with the house style applied.

Not reproduced: the energy axis, the level bars and connectors, the ΔG values, the pathway colours, the transition-state structures (S8-TS1eq, S8-TS1ax, S8-TS2, S8-TS2'), the radical and zwitterion intermediates (S8-Int1), the P8b-OH bridged product and the P8c-OH stereoisomer. The `draw_figure` tool has no energy-profile drawer.

Structures read from the crop and checked with RDKit (formulas C12H22 + C4H5F3O2 gives C12H22O + C4H5F3O, balanced):

- S8: `CC(C)(C)C1CCC2(CC2)CC1` (tBu para to the spiro cyclopropane; the reacting CH2 is next to the spiro carbon, labelled 4 in the paper)
- dioxirane: `CCC1(C(F)(F)F)OO1`
- P8a-OH: `CC(C)(C)C1CCC2(CC2)C(O)C1` (OH on the carbon next to the spiro carbon; no stereo is shown in the crop, so none is drawn)
- ketone: `CCC(=O)C(F)(F)F`

## Replay

```
python skill/chemdraw/scripts/cdx.py py skill/chemdraw/assets/house-styles/houk_group/replica/houk_group-01/replay.py NEW_DIR
python skill/chemdraw/scripts/cdx.py render NEW_DIR/figure.cdxml
```

`replay.py` runs `draw_figure` on `brief.json` offline and writes `figure.cdxml` and `validation.json`. The replay was re-run on 2026-11-07: ok, readback matched, 4 structures drawn, house `houk_group` applied. Two of the applied entries (`show_plus_sign=true`, `substrate_layout=inline_plus`) change nothing in the drawing; see Audit. `rendered.png` was made from the same drawing with `cdx.py render` (the `draw --render` call itself crashed once, see below).

## Comparison

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| energy_unit kcal/mol (energy_profile) | bare numbers, no unit in this crop | no energy axis | no |
| energy_label delta_G (energy_profile) | no ΔG label in this crop | none | no |
| level_style bars_solid_connectors | thick level bars with thin solid sloped connectors | not drawable | no |
| pathway_colors red and blue | red and blue energy and species labels | black only | no |
| energy value above each bar | yes, bold italic and coloured | none | no |
| competing pathways told apart by coloured labels, connectors black | yes | none | no |
| a structure next to every stationary point | yes | only the scheme | no |
| TS partial bonds dashed | yes (S8-TS1eq, S8-TS1ax, S8-TS2) | no TS drawn | no |
| spectator fragments in light grey | yes (S8-Int1, S8-TS2') | none | no |
| double slash breaks on long descending connectors | yes | none | no |
| stage names between double-headed arrows (crop 03 only) | not in this crop | none | no |
| mechanism formal_charge_style circled | yes, circled plus and minus | no charged species | no |
| radicals drawn as dots | yes, on S8-TS1eq | no radical species | no |
| compound_label_face bold | bold italic labels | bold labels | no (italic missing) |
| compound_label_color #000000 | red and blue labels | black | no |
| abbreviate_groups tBu and CF3 | tBu and CF3 | tBu and CF3 | yes |
| substrate_layout inline_plus with show_plus_sign | paper: an inline plus only in the P8c-OH + ketone row; P8a-OH and its ketone are stacked; no inline reactant pair | replica: inline plus between substrates and between products (the plus signs come from the default layout) | no (partly) |
| bond_length_over_cap_height 2.4 | 2.4 (105 px over 43 px) | about 2.0 (BondLength 14.40 pt over LabelSize 10 pt, Arial cap height about 0.72 em) | no |
| line_width_over_bond_length 0.09 | about 0.09 (9 px over 105 px) | 0.042 (LineWidth 0.60 pt over BondLength 14.40 pt) | no |
| arrow_style plain | no reaction arrow in this crop | solid arrow, 72 pt long = 5.0 bond lengths (CDXML Head3D to Tail3D over BondLength 14.40); house arrow_length_over_bond_length is 6.2 | no (not comparable with the crop; length 5.0 vs 6.2) |

Matched 1 of 20 claimed conventions after audit (the replicator claimed 2; see Audit).

## Differences from the paper

- The paper is an energy diagram; the replica is one reaction scheme. The layout, the energy levels and the structures beside each level are missing.
- Compound labels: the paper uses bold italic labels in pathway colours; the replica uses bold black labels, following the card's top-level label rule.
- The OH of P8a-OH is drawn below C4 in the paper (H to its right, red OH) in a perspective chair; the replica draws it to the left in a flat ring. The tool chooses the orientation.
- The reacting C-H is not marked with the red 4 label of the paper, and the blue and red H labels on C4 are not drawn.
- The ring is drawn with the tool's own geometry; the line weights are the acs1996 ones (see the table).
- P8b-OH and P8c-OH are not drawn, and S8-TS1eq and the other transition states are not drawn.

## Tool gaps

- No energy-profile drawer: `draw_figure` accepts only the kinds scheme, scope and mechanism. Level bars, sloped connectors, energy values with a unit above each level, pathway-coloured values and labels, double-slash breaks on long connectors, and a structure beside each level cannot be drawn.
- Figure-type conventions, scoped to the kind: for kind scheme, `draw_figure` applies the top-level conventions and, only for a catalytic-cycle layout, the catalytic_cycle figure-type conventions. The energy_profile conventions are neither applied nor listed under skipped. For kind mechanism, `figure_mechanism` applies the mechanism conventions (curved_arrow_color, curved_arrow_weight) and lists the rest as skipped.
- The card's `measured` block (bond_length_over_cap_height, line_width_over_bond_length, bold_width_over_bond_length, arrow_length_over_bond_length, label_font) is stored and read by no code path. It is not applied, and the report's skipped list does not name it, so a reader of the validation report cannot see that it was dropped. The drawing keeps the acs1996 line widths (0.60 pt over a 14.40 pt bond) and 10 pt labels.
- Arrow length: the scheme brief has no arrow-length key (its keys are kind, species, steps, max_width, title, style, layout). The replica arrow is 5.0 bond lengths; the house value is 6.2.
- Per-atom colour: a figure cannot colour one atom. The card's `new_bond_color` colours formed bonds in product structures (RDKit maps the atoms and the bond is painted; the new O atom itself is not separately coloured). It is null on this card because red appears only in crop 07, and the brief has no per-figure override. `atom_halos` only adds halos. So the red new oxygen is blocked by the card setting and the missing override, not by the absence of any colour mechanism.
- No per-label colour or italic option for compound labels. The card's `compound_label_italic_suffix` is reported as "not applied yet", and there is no per-label option.
- Atom annotations: species accept only id, smiles or name, label, ring_fills, atom_halos and ts_bracket. There is no way to place a small atom number (the red 4) or a coloured H label on a given atom.
- Label placement and rich text: there is no position control for species labels, and a label is a plain string, so italic, subscript and dagger markup (for example S8-TS1eq) cannot be written.
- Structures above or below a scheme arrow: `above` and `below` take text lines only. Reagents drawn as structures above the arrow (a house signature feature of reaction_scheme) cannot be drawn in a scheme brief.
- Curved arrows between species are available only in kind mechanism. The dioxirane-to-S8 curved arrow of the paper cannot be drawn in a scheme brief.
- No dashed partial (forming or breaking) bond in a species or scheme brief; `ts_bracket` wraps a species in brackets but draws no partial bonds.
- No grey shading for spectator fragments inside one structure (`substrate_colors` colours whole substrates).
- No circled formal-charge option in the scheme brief, and figure_mechanism has no circled-charge or radical-dot option, so the card's formal_charge_style is not applied. Radical dots were not tested with a radical SMILES.
- Runtime: `cdx.py draw ... --render` crashed once (worker_crashed, exit 143, after 295 s) on the first try, as the replicator reported. Not re-tested in this audit.

## Audit

Checked on 2026-11-07 by re-reading the reference, the replica image, the card and the toolkit code, and by re-running `replay.py` into a scratch folder outside this case folder. The re-run gave ok, readback matched, 4 structures and no warnings. The formulas (C12H22 + C4H5F3O2 giving C12H22O + C4H5F3O) were re-checked by hand and balance.

- Overclaim: the `substrate_layout inline_plus` row was marked as a match. The paper has an inline plus only in the P8c-OH row; P8a-OH and its ketone are stacked, and the paper has no inline reactant pair. The row is now "no (partly)".
- Overclaim: `validation.json` lists `show_plus_sign=true` and `substrate_layout=inline_plus` as applied, but the code only records those names and changes nothing for them. The other applied entries do change the drawing: `compound_label_face=bold` (label face 1 on S8 and P8a-OH) and `abbreviate_groups (4 contracted)`.
- Overclaim: the tool-gap claim that energy_profile and mechanism figure-type conventions are neither applied nor listed under skipped holds for kind scheme only. For kind mechanism they are applied or listed. The gap is now scoped.
- Overclaim: the new-oxygen colour was stated as impossible. The card's `new_bond_color` mechanism exists; it is blocked by the card's null value and the lack of a per-figure override.
- Error: the paper's P8a-OH hydroxyl is drawn below C4, not on the right.
- Under-reported: the arrow row gave no length check. The replica arrow is 72 pt, 5.0 bond lengths, against the house 6.2.
- Missed gaps added: the arrow-length key, the silently dropped `measured` block, atom annotations, label rich text and position, structures above or below the arrow, curved arrows in a scheme brief, and the unscoped figure-type skipped report.
- The `rendered.png` and the `cdx.py render` step were not re-run in this audit; the rendered image was checked only by eye.
- Corrected matched count: 1 of 20 (abbreviate_groups). The compound_label_face row reads "no" against the paper's bold italic labels, though the card's top-level field is bold and is applied.
