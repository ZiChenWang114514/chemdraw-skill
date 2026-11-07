# List group Figure 4a: cyanosilylation mechanism (partial replica)

Source: B. List et al., "Organocatalytic stereoselective cyanosilylation of small ketones", *Nature* **2022**, DOI [10.1038/s41586-022-04531-5](https://doi.org/10.1038/s41586-022-04531-5). Licence: CC BY 4.0. Reference crop: `evidence/list_group-04.png` (Figure 4a), copied to `reference.png`.

Figure type: `mechanism` (computed mechanism, no curved arrows). The card's `mechanism` section is not applied to this scheme route (`draw_figure` applies `figure_types` only to mechanisms and catalytic cycles); the house style is `list_group` (base preset `nature`).

## What is reproduced

The cyanide-delivery step at the bottom left of Figure 4a, as a surrogate: 2-butanone (`CCC(C)=O`) and TMSCN (`N#C[Si](C)(C)C`) give the bracketed transition state (drawn as the two reactants in one bracket with a double dagger) and then 2-methyl-2-(trimethylsilyloxy)butanenitrile, product 6 (`CCC(C)(C#N)O[Si](C)(C)C`), labelled "6 (−1.5)" as in the paper. The product SMILES has the C8H17NOSi formula of the two reactants; the TS species is their dot-separated pair (C8H17NOSi), so both steps balance.

Drawn with `draw_figure` as a scheme (not `kind: "mechanism"`, which requires an arrow for every electron move and so cannot draw a computed mechanism without arrows). The drawing is in `figure-try3.cdxml` in the scratch folder; `replay.py` regenerates `figure.cdxml` from `brief.json` offline.

The IDPi catalyst, the intermediates INT1, INT1', INT2 and INT2', the top row, the middle row TS1 and TS1', the second product (Z)-53 and the disfavoured red-crossed path are not reproduced (see below).

## Attempts

| try | result |
| --- | --- |
| 1 | `draw` with `--render` exceeded the 300 s tool limit; no file written |
| 2 | `draw` without render exited with code 143 (worker killed), machine heavily loaded |
| 3 | `draw` without render succeeded (about 3 min), `checks_passed` true, readback matched 4 of 4 structures; `cdx.py render` produced the PNG kept as `rendered.png` (downscaled from 1348 to 1200 px wide) |
| 4 | attempted a connected TS as a dative adduct (`CCC(C)=O->[Si](C)(C)(C)C#N`) to replace the dot-separated pair; RDKit rejects it (explicit valence of 5 on Si), so the draw was not completed; the try-3 brief is kept |

## Convention table

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| mechanism.curved_arrow_color (null) | no curved arrows in the crop | no curved arrows | n/a (null convention, nothing to compare) |
| mechanism.curved_arrow_weight (null) | no curved arrows | none | n/a (null convention, nothing to compare) |
| mechanism.show_lone_pairs (false) | no lone pairs drawn | none | yes |
| mechanism.formal_charge_style (circled) | circled charges on the ion-pair atoms (for example on the silyl-oxocarbenium O) | no charged species drawn (neutral surrogate) | no |
| mechanism.intermediate_label_style (bold_number) | bold alphanumeric labels TS0, INT1, TS1', INT2 | only the product carries a bold label; no intermediates | no |
| mechanism.ts_marker (bracket_double_dagger) | square bracket with double dagger at top right | square bracket with double dagger at top right; the bracket encloses two separate molecules, not a bonded TS | yes (glyph and bracket only) |
| mechanism.highlight_fill (null) | light grey boxes behind the ketone at TS1 and TS1' | no fill; the card's null value conflicts with the paper (see Audit) | no |
| signature: TS in square brackets with double dagger | present | present (the same bracket) | yes (glyph and bracket only) |
| signature: free energies in blue #0000FF in parentheses after bold labels | blue energies after the bold labels | energy in parentheses after the bold label, in black | no |
| signature: hydrogen bonds as dashed black lines | dashed H-bonds from the IDPi NH and oxygen to the cyanide | not drawn (no catalyst; dot-separated TS) | no |
| signature: products in purple #800080 | product 6 and (Z)-53 in purple | product 6 in black | no |
| signature: red cross on the disfavoured arrow | red cross on the arrow from the bottom-middle TS back to the TS leading to 6 | no second path | no |
| compound_label_face (bold) | bold | bold (number and energy are one run, so only the number's face is checked) | yes |
| compound_label_color (#000000) | black number | black | yes |
| arrow_style (plain) | plain arrows | plain arrows (length and weight not measured) | yes |
| substrate_layout (null) | the top row writes "IDPi 2 + TMSCN" with a plus; the arrows in the middle and bottom rows carry no plus | inline reactants with a plus drawn between ketone and TMSCN; card show_plus_sign is null, and the code removes "+" only when it is false | no |
| new_bond_color (null) | no coloured bonds | none | n/a (null convention, nothing to compare) |
| abbreviate_groups (tBu, OMe) | TMS and CF3 are abbreviated; no tBu or OMe in the crop | TMS drawn in full | no |

Matched 6 of 18 rows on audit (the replicator claimed 10; see Audit).

## Differences from the paper

- The IDPi catalyst is omitted entirely. The paper's transition states are catalyst-bound, with the steel-blue backbone arcs and H-bonds. The replica's bracketed species is the two reactants side by side, not a complex.
- The energies are copied from the paper but the replica's species are not the paper's species. The product label "6 (−1.5)" is relative to IDPi 2 plus TMSCN at 0.0 in the paper; the replica has no catalyst, so the energy does not describe the replica's pathway.
- Labels are black instead of blue energies after bold labels.
- No intermediates (INT1, INT2), no top row, no middle row, no circled charges, no grey highlight boxes.
- Product 6 is drawn without the purple colour; (Z)-53 is absent.
- No dashed H-bonds and no red-crossed disfavoured path.
- Bond and arrow proportions were not measured against the crop; the bracket line looks heavier relative to the bond than in the paper (visual impression only).
- Product 6 has an unassigned stereocentre in the SMILES; the crop does not show stereo for 6 clearly enough to assign it.

## Tool gaps

- Labels are one plain-text run; a number and its energy cannot take different colours (blue energies).
- A product cannot be coloured (purple); `substrate_colors` covers only substrates.
- The `failed` arrow has no colour option, so the red cross cannot be drawn.
- Interaction lines (dashed H-bonds with distance labels) exist in `cdx.py build` and `acs_builder`, not in `draw_figure` briefs.
- Multi-fragment species in a bracket are laid out as separate pieces; there is no way to draw a connected, H-bonded complex. A dative adduct to a four-coordinate Si is rejected by RDKit, so a connected silyl-activated TS cannot be written this way.
- `kind: "mechanism"` refuses a step without `moves`, so a computed mechanism with TS brackets and energies but no curved arrows has no drawer; the scheme route loses the step-by-step structure.
- The `figure_types.mechanism` conventions (`formal_charge_style`, `intermediate_label_style`, `highlight_fill`) are not applied to a scheme brief, and the report's `skipped` list does not name them.
- No intermediate numbering: bold labels are typed text.
- No catalyst schematic (IDPi with steel-blue backbone arcs and coloured substituent dots).
- Highlight fill applies only to the largest ring of the final product. Species `atom_halos` can put a disc behind the ketone atoms, but not the paper's grey box.
- Operational: `draw_figure` with render exceeded 300 s on the first try and the worker exited with code 143 on the second, under heavy machine load.


## Audit

Checked against `reference.png`, `rendered.png`, `brief.json` and the card `list_group.json`. The replicator's claim of 10 of 18 is overstated.

- **Corrected count: 6 of 18.** Three rows are null in the card (`curved_arrow_color`, `curved_arrow_weight`, `new_bond_color`), so nothing is compared; they are n/a, not matches. `substrate_layout` is not a match: the replica draws a plus sign between the ketone and TMSCN, which the crop's arrows do not carry, and the card leaves `show_plus_sign` null, so the code keeps the plus by default.
- **Bracket rows overstated.** The TS bracket and double dagger are drawn, but the bracket encloses two separate molecules with no interaction, not the H-bonded TS of the paper. Only the glyph and bracket are matched.
- **Label row partly overstated.** The label `6 (-1.5)` is one text run. Only the number's face and colour were checked; the energy colour is a separate, failed signature.
- **Arrow and proportion claims are not measured.** `reference.png` is 900 px wide and `rendered.png` is 1200 px wide, so no bond, arrow or bracket proportion was compared. The paper's grey boxes are present in `reference.png`, but the card's `highlight_fill` is null; the card's own notes record no agreement between crops, so the card value is unresolved for this figure.
- **Mis-stated intro.** The `figure_types` mechanism section is not applied to a scheme route (the `draw_figure` docstring says only mechanisms and catalytic cycles take it).
- **Tool gap overstated.** `atom_halos` is accepted on the scheme path, so a disc behind the ketone atoms can be drawn. The real gap is the shape (a disc, not a box) and the house colour not being applied.
- **Tool gaps missed.** (1) The card's `measured` block (bond length over cap height, line width, bold width, arrow length, Helvetica label font) is parsed in `house_styles.py` but not read by `figure_house.py` or `figure_draw.py`, so proportions follow the base preset only. (2) `show_plus_sign` null cannot be expressed; the code removes "+" only when it is false. (3) Fragments inside one bracketed species are placed by the layout, with no per-fragment position or offset option.
- **Not verified from this folder.** `figure-try3.cdxml` and `figure.cdxml` are absent, so `checks_passed`, the 4 of 4 readback, the 1348 px pre-downscale width, the draw timings and the 300 s and exit-143 failures cannot be checked here. Also not checked: the dashed-interaction claim (present in `cdx.py build` and `acs_builder` but not in `draw_figure`), the "failed arrow has no colour" claim, the mechanism-kind requirement for `moves`, and the claim that the `figure_types` conventions are missing from the skipped list.
