# Smith et al., Chem Catal. 2025: photocatalytic Staudinger mechanism, Figure 4A (partial replica)

Source: Smith et al., "Photocatalysis as a mechanistic probe for the Staudinger beta-lactam synthesis", *Chem Catal.* **2025**. DOI: [10.1016/j.checat.2025.101493](https://doi.org/10.1016/j.checat.2025.101493). Licence: CC BY 4.0 (from the house-style card). The reference crop is `evidence/cell_press_chem-05.png`, the top panel (Figure 4A, mechanistic overview) of the figure.

Figure type: `mechanism` (card section), drawn here with `kind` scheme because a mechanism brief needs atom-level electron moves that a hydrogen-atom transfer cannot express (see Tool gaps).

## What is reproduced

The main line of the mechanism, from the enone to the C-N rotamer pair: 1A to the triplet diradical 3A (hv, Ir(III) photocatalyst, EnT), 3A to the 1,4-diradical 3B (1,5-HAT, 3TS-I), and 3B to 3C (C-N rotation, 3TS-II, t1/2 = 351 fs from MD). The step labels 1,5-HAT, 3TS-I, C-N rotation, 3TS-II and t1/2 = 351 fs from MD are copied from the crop. The 1A to 3A arrow has no label in the crop; the replica's "hv, Ir(III) photocatalyst (EnT)" label was added and is not in the crop. Structures are written from the crop and checked with RDKit (`C10H15NO2` for 1A, 3A and 3B, which are isomers).

Not reproduced: the photocatalyst cycle (1Ir(III), 1Ir(III)*, 3Ir(III)*, EnT and ISC arcs), the ISC steps to the zwitterion 1C, the cyclization to syn-1D (2I), the minor and side paths (anti-1D, 1B, 1E, 1F, 1G, 1TS-III to 1TS-V), and the energy profile in panel B. The zwitterion and product connectivity are not read reliably at the crop's resolution, so they are left out rather than guessed. The SMILES in `brief.json` are:

- 1A: `CCC(=O)N(C)C1=CCCCC1=O`
- 3A: `CCC(=O)N(C)[C]1[CH]CCCC1=O` (two radical centres on the enone alpha and beta carbons)
- 3B and 3C: `C[CH]C(=O)N(C)[C]1CCCCC1=O`

3C is the rotamer of 3B; the two are drawn with identical SMILES because the tool draws constitution, not conformation.

Drawing style: `style: cell_press_chem` in `brief.json` (base preset wiley, bond length 17 pt; bold compound labels, black reagent text). Rendered with desktop ChemDraw via `cdx.py draw ... --render`, with `max_width` 900 so the three steps fit one row as in the crop. The first try at `max_width` 504 wrapped onto three rows (`figure_try1` in the scratch folder, not kept here).

## Replay

```
python skill/chemdraw/scripts/cdx.py py skill/chemdraw/assets/house-styles/cell_press_chem/replica/cell_press_chem-05/replay.py NEW_DIR
python skill/chemdraw/scripts/cdx.py render NEW_DIR/figure.cdxml
```

`replay.py` runs `draw_figure` on `brief.json` offline and writes `figure.cdxml` and `validation.json`. `reference.png` is the crop; `rendered.png` is the ChemDraw render (downscaled to 1200 px wide).

## Convention and signature check

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| compound_label_face bold (1A, 3A, 3B, 3C) | bold | bold | yes |
| compound_label_color #000000 | black | black | yes |
| sans-serif label text (Arial) | Arial-like | Arial | yes |
| reagent_text_color #000000 (hv, EnT, 1,5-HAT, 3TS-I) | 1,5-HAT dark red; 3TS-I bold black; no text above the 1A to 3A arrow | 1,5-HAT and 3TS-I black; an added "hv, Ir(III) photocatalyst (EnT)" label above the 1A to 3A arrow | no |
| mechanism.show_lone_pairs false | none drawn | none drawn | yes |
| mechanism.intermediate_label_style bold_number (3A, 3B, 3C) | bold, with a superscript spin prefix (triplet 3 on 3A, 3B, 3C) | bold, no spin prefix | no |
| equilibrium arrow for the rotamer step (3B and 3C) | double-headed arrow | reversible arrow | yes |
| mechanism.curved_arrow_color #780001 | dark red curved arrows | none drawn | no |
| mechanism.curved_arrow_weight thin | thin curved arrows | none drawn | no |
| mechanism.ts_marker bracket_double_dagger | 3TS-I and 3TS-II as text, no bracket in crop 05 | TS names as plain text | no |
| mechanism.highlight_fill #F0EDE8 (step boxes) | warm grey ISC and EnT boxes | not drawn | no |
| step names dark red #780001 above arrows | 1,5-HAT and C-N rotation in dark red | black text | no |
| TS names bold below arrows | 3TS-I, 3TS-II bold in the crop | plain | no |
| spin multiplicity superscript on intermediates (3A, 1C) | spin label in the crop | not drawn; radicals drawn as dots | no |
| radical centres drawn as dots | bare dots on carbon, no H label (3A, 3B); 3C has its own dot position | explicit H labels ("CH" with dot on 3A, "H" with dot on 3B and 3C); 3C drawn identical to 3B | no |
| catalytic_cycle.cycle_arrow_color (photocatalyst loop) | black arcs | not drawn | no |

Matched 5 of 16 claimed conventions (rows 1, 2, 3, 5 and 7); see Audit.

## Differences from the paper

- Scope: the crop shows the whole mechanistic overview, including the photocatalyst loop, ISC steps, zwitterion, product and minor paths. The replica has only the main line from 1A to 3C.
- Arrows: the paper's 1,5-HAT and cyclization arrows are curved dark red arrows. The replica uses straight scheme arrows.
- Colour: step names (1,5-HAT, C-N rotation) and TS names are black; the paper uses dark red for the step names and bold black for the TS names.
- Labels: the paper writes a superscript spin prefix on 3A, 3B, 3C, 3TS-I and 3TS-II, and "1A (1I)" for the enone; the replica writes none of these prefixes and no alternate number.
- Orientation: the crop draws the carbonyl above the ring on 1A, 3A, 3B and 3C; the replica draws it below. The molecules are the same 2D graph, but the layout differs.
- Italics: the crop sets t1/2 in italics; the replica sets it upright.
- Rotamer: 3C has the same SMILES as 3B; the paper draws a different rotamer.
- Layout: the paper runs the main line on one row with the energy profile beneath; the replica is one row for 1A, 3A and 3B and a second row for the rotamer pair.
- Label style: no text or label colours beyond black are available for the scheme text, so the labels are plain black.

## Tool gaps

- `kind: "scheme"` does not apply the `figure_types.mechanism` conventions (curved-arrow colour and weight, step-name colour, TS markers); the report lists them as skipped. A mechanism brief applies only the base preset.
- `kind: "mechanism"` cannot draw the 1,5-HAT. Its move endpoints are heavy-atom indices or bonds between heavy atoms, so the transferred hydrogen has no endpoint for a fishhook from the C-H bond.
- Triplet state: 3A was written as two radical centres without a triplet state, and the brief has no field to set one (the spin superscript on 3A is also not drawn). Whether the drawing layer accepts a triplet radical state was not tested.
- No colour or bold for text above or below arrows, so dark red step names and bold TS names cannot be drawn.
- No warm grey filled step boxes (ISC, EnT) and no arrow-with-box annotation for photocatalysts.
- The photocatalyst loop (EnT and ISC arcs between 1Ir(III), 3Ir(III)* and 1Ir(III)*) needs a closed catalytic cycle of at least three steps with arcs and excited-state labels; the catalytic-cycle layout does not draw it from this brief.
- Conformers (rotamers of the same constitution, such as 3B and 3C) cannot be drawn distinctly.
- The ts_bracket option is available on species, but the crop shows TS names as text, so it was not used for 3TS-I.

## Audit

Checked by reading reference.png and rendered.png (enlarged crops), the house-style card (`toolkit/cdxml_toolkit/publication/house_styles/cell_press_chem.json`, since the path given in the task is not in this checkout), and the drawing code (`toolkit/cdxml_toolkit/mcp_runtime/figure_draw.py`, `figure_mechanism.py`, `figure_house.py`).

Overclaims corrected above:
- reagent_text_color: 1,5-HAT is dark red in the crop, not black. The crop has no text above the 1A to 3A arrow; that step runs through the photocatalyst loop (EnT in a box in the loop, hv at its lower left). The "hv, Ir(III) photocatalyst (EnT)" label was added, which contradicts "copied from the crop".
- intermediate_label_style: the crop labels carry a superscript spin prefix (3A, 3B, 3C and 1A (1I)); the replica does not.
- radical dots: the crop uses bare dots on carbon; the replica writes explicit H labels ("CH" on 3A, "H" on 3B and 3C). 3C is drawn identically to 3B, so its dot placement does not match the crop's rotamer.
- The ts_marker row is internally inconsistent: the paper and replica columns both have no bracket, so it matches crop 05 and mismatches only the card's bracket_double_dagger. It stays "no" against the card.
- "Rendered with desktop ChemDraw" and the 504 px first try could not be checked here.

Kept as yes, not refuted: compound labels bold; label colour black; Arial-like face (judged by glyph shape, not measured); no lone pairs drawn (a vacuous match); the equilibrium arrow is a double line with heads on both ends, like the crop, but was not measured. The RDKit check was not rerun; C10H15NO2 for 1A, 3A and 3B was counted by hand and is correct.

Not measurable at these resolutions: proportions, line weight, and label-to-bond ratios. The crops are 900 and 1200 px wide and label boxes could not be separated cleanly from line work, so no proportion is claimed either way.

Corrected count: 5 of 16.

Tool gaps the replicator missed (checked in code):
- `energy_profile` is not a drawable kind: `figure_draw.py` rejects any kind other than scheme, scope and mechanism, so panel B cannot be drawn.
- No wavy arrow: `ARROWS` is solid, dashed, failed, reversible and resonance, so the hv arrow of the loop cannot be drawn.
- No italic or superscript runs in compound labels or above/below text, so t1/2 (italic t), the spin prefixes and "1A (1I)" cannot be written with formatting.
- No orientation field on species (keys: id, smiles, name, label, ring_fills, atom_halos, ts_bracket), so the crop's carbonyl-up layout cannot be requested.
- Radical carbons get explicit H labels in the replica. The cause was not traced in code; the brief has no switch to suppress it.
- The mechanism-convention gap is real: `apply_figure_type_conventions` is called for "mechanism" only in `figure_mechanism.py` and for "catalytic_cycle" in `figure_draw.py`.

Scope, not a tool gap: `scheme` supports dashed arrows, so the two ISC steps (3A to 1A, 3B to 1B) could have been drawn but were left out.
