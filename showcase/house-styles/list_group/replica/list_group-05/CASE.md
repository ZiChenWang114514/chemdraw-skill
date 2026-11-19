# List group Figure 4e (crop 05): cationic-shift catalytic cycle, top half

Source: List et al., *Nature* 2024, "Catalytic asymmetric cationic shifts of aliphatic hydrocarbons", DOI [10.1038/s41586-023-06826-7](https://doi.org/10.1038/s41586-023-06826-7). Figure 4e. Licence CC BY 4.0 (from the `list_group` card). Reference crop: `reference.png` (copy of `evidence/list_group-05.png`).

Drawing style: the `list_group` house style (base preset `nature`), figure type `catalytic_cycle`.

## What is reproduced

A four-node part of the cycle in the paper's arrangement: 1a′ at the top, I on the right, II at the bottom, IV on the left. The steps are protonation of 1a′ to I, ring expansion I to II, a [1,2]-n-hexyl shift between II and IV (reversible), and deprotonation from IV, each with its step name in plain text.

Not reproduced: the IDPi/HX catalyst, the released product 3a″ and its −HX arrow, the H+ that leaves, the square brackets around intermediates, the curved cycle arcs, the side branches (III, 3a′, 4a′, 5a′, 6a′), the red 13C labels and the coloured carbon markers.

## Structures

Read from the crop, which is low resolution. SMILES are in `brief.json`:

- 1a′ `CCCCCC/C([13CH3])=C1\CCCC1C`. The alkene geometry was not readable. The toolkit refused the unspecified alkene (see Tool gaps), so the E/Z given here is arbitrary and is not evidence for the paper's geometry.
- I `[13CH3][C+](CCCCCC)C1CCCC1C`, II `[13CH3]C1(CCCCCC)CCC[CH+]C1C`, IV `[13CH3][C+]1CCCCC1(C)CCCCCC`. The ring positions of the methyl groups and the hexyl migration are inferred from the crop and are approximate.
- RDKit (via `cdx.py py`): 1a′ is C14H26, I, II and IV are C14H27+ (so I is 1a′ + H+, and II and IV are isomers of I), and 3a″ `[13CH3]C1=CCCCC1(C)CCCCCC` is C14H26 (IV − H+).

## Result

The `draw_figure` run wrote a file, but the readback did not match the brief (`checks_passed` false): the saved file lacks the catalyst and product structures. `rendered.png` is therefore an incomplete drawing of the cycle, not a full replica.

## Convention table

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| compound_label_face bold | bold I, II, IV, 1a′ (IV checked at zoom) | bold labels (IV checked at zoom) | yes |
| compound_label_color #000000 | black | black | yes |
| reagent_text_color #000000 | black step names | black | yes |
| arrow_style plain | plain arrows; the reversible step is an equilibrium pair | plain arrows; equilibrium pair | not verified (head size and shaft weight not measured), not counted |
| abbreviate_groups tBu, OMe | no tBu or OMe in this crop; the paper writes n-hexyl as nHex, which the card list does not include | full n-hexyl chains | not matched |
| cycle_shape open_arc | large open black arcs, gap at the catalyst | closed quadrilateral of straight arrows | not matched |
| cycle_arrow_color #000000 | black | black | yes |
| catalyst_color #457898 | no catalyst steel-blue pixels in the crop (26 px within 20 of #457898); arcs read black | no catalyst drawn | not matched |
| center_label False | empty centre | empty centre | yes |
| step_names True | plain text beside arrows | plain text beside arrows | yes |
| intermediate_label_style bold_roman | bold I, II, IV in square brackets | bold I, II, IV, no brackets | not matched (no brackets) |
| highlight_fill none | light grey (#F9F9F9) fill inside the II bracket | no fill | not matched |
| signature: large black arcs, curved substrate and product arrows | arcs | straight arrows | not matched |
| signature: step names in plain text | plain text | plain text | yes |
| signature: catalyst drawn schematically | IDPi drawn as arcs and dots | none | not matched |
| signature: bracketed intermediates, bold roman labels | I, II, IV in brackets | no brackets | not matched |

Matched: 6 of the 12 convention rows (compound_label_face, compound_label_color, reagent_text_color, cycle_arrow_color, center_label, step_names). arrow_style is not verified and is not counted. Signature features: 1 of 4 card features (plain step names). The earlier "7 of 11" and "1 of 3" did not match the earlier table, which had 8 "yes" rows.

## Differences from the paper

- The top node is 1a′, where the paper has the IDPi catalyst (2d = HX). The Deprotonation arrow therefore ends on 1a′, the substrate, where brief.json has 3a″ and H+ (see Audit).
- The cycle is a quadrilateral of straight arrows, not open arcs.
- Missing: the catalyst, the product 3a″ with its −HX arrow, the H+, the intermediate brackets, the curved arrows and the side branches.
- The n-hexyl chains are drawn in full, where the paper uses nHex.
- The 13C labels are black, not red. The carbon markers are absent.
- The arrows are longer than in the crop, relative to the structures. This was judged by eye, not measured.

## Tool gaps

- The `catalytic-cycle` layout drew straight segments between intermediates, not the curved arcs along the circumference that `scheme-drawing.md` describes (`figure_try2.png`).
- No catalyst node. A species with no SMILES cannot be given. A bare `[H+]` and a phosphoric-acid stand-in were both dropped from the saved file (readback reports them missing).
- A product that leaves the loop is not kept. In the first two working drafts the 3a″ structure was dropped from the saved file (readback reports it missing). A single-product variant was not completed (ChemDraw busy, then timeout).
- A species that is the substrate of two steps is drawn twice (IV appeared twice in a run with a second step from IV).
- Intermediate brackets: the documented bracket is the transition-state bracket with a double dagger (`ts_bracket`). No option to bracket an intermediate with no dagger was found. Not tested with an empty superscript.
- An alkene with no specified geometry is refused. The round-trip added E/Z and the run stopped with `chemical_semantics_changed`.
- The `abbreviate_groups` list is fixed and has no nHex or nPen.
- There is no per-atom colour for 13C labels or carbon markers. `atom_halos` could approximate the dots; not tried here.
- ChemDraw: the first run stopped with `resource_busy` after 295 s. A retry hit `tool_timeout` at 300 s, so a fourth draft was never produced.

## Replay

    python skill/chemdraw/scripts/cdx.py py skill/chemdraw/assets/house-styles/list_group/replica/list_group-05/replay.py NEW_DIR
    python skill/chemdraw/scripts/cdx.py render NEW_DIR/figure.cdxml

`replay.py` redraws `brief.json` offline. It does not change the readback result above.

## Audit

Second-pass audit of the table above, checked against reference.png, rendered.png, brief.json, the list_group card and the toolkit code.

Overclaims corrected:

- The tally was not supported by the table. The old table had 8 "yes" rows, and its two signature rows were both "no". The old "1 of 3" signature count does not match the card, which lists 4 signature features.
- highlight_fill was wrong. reference.png has a light grey (#F9F9F9) fill inside the II bracket, confirmed by pixel sampling and zoom. The card's null entry means no agreement between crops, not "none".
- arrow_style is not verified, because head size and shaft weight were not measured.
- Proportions and line weight were not measured. A rough reading of reference.png gives an arrow of about 5.6 bond lengths (card 5.9). The claim that the replica arrows are longer than the paper's is therefore not confirmed.
- The Deprotonation arrow from IV ends on 1a′, the substrate alkene. brief.json says IV gives 3a″ and H+. The drawn cycle therefore reads as IV regenerating the starting alkene. This is a chemistry error in the figure, not only missing catalyst turnover.
- Colour: reference.png has lavender (#8080BE, about 650 px) and teal (#408080, about 530 px) carbon dots and a red 13C label. rendered.png has no coloured pixels at all.
- The catalyst row cites steel-blue #457898 for this crop, but the arcs read black and only 26 pixels fall within 20 of #457898.
- The case folder has no figure.cdxml or validation.json, so the readback result (checks_passed false) cannot be checked from here.
- The brief carries an arbitrary alkene E/Z for 1a′. The CASE discloses this, but the saved figure then depicts a geometry the source does not give. Invented stereo should not be in brief.json.
- Layout: the paper has the catalyst at top centre and 1a′ at top right. The replica puts 1a′ at top centre, so "the paper's arrangement" is approximate.

Tool gaps: corrections and additions.

- Corrected: the "no per-atom colour" gap overstates it. atom_halos (figure_draw.py, species level) draws filled coloured circles on chosen RDKit atom indices, so the carbon dots are reachable in principle (untested). What is missing is a per-atom text colour for the 13C label.
- Corrected: ts_bracket takes a superscript option (figure_draw.py, default double dagger). An empty superscript is the likely route to an intermediate bracket. This is untested, so it is not a confirmed gap.
- Confirmed: abbreviate_groups is a fixed list (publication/house_styles.py, ABBREVIATIONS) with no nHex or nPen.
- Confirmed: the catalytic-cycle layout draws straight segments. scheme-drawing.md (line 40) says curved arcs along the circumference.
- Missed: no counterion field, so the X⊖ on I, II and IV cannot be drawn.
- Missed: no stereo bond depiction without stereo in the SMILES. The reference has a wedged nHex and a hashed methyl on II and IV, and the brief has no stereo for those centres.
- Missed: no species-level background box. ring_fills shade rings only, so the grey fill behind II cannot be drawn.
- The ChemDraw timings (295 s and 300 s) cannot be checked from the case folder.
