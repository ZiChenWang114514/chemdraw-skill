# OpenStax Chemistry: condensation of two amino acids to a dipeptide (Figure 20.20)

Source: Flowers, Theopold, Langley, Robinson et al., *OpenStax Chemistry* (2015), section 20.4 Amines and Amides, Figure 20.20. No DOI is listed on the card. Licence: CC BY 4.0. The reference crop is `evidence/openstax_chemistry-09.png`, copied here as `reference.png`.

Drawing style: the `openstax_chemistry` house style card, `reaction_scheme` figure type (crop 09 is one of its two listed crops). Base preset `chemdraw_slide`.

## What is reproduced

Only the top row of the figure: the condensation of two amino acids (both drawn with a generic R group) to the dipeptide, with H2O as the by-product. The brief is `brief.json`. R groups are `*` dummy atoms, drawn as R. The species are unlabelled in the brief; the captions "Amino acid" are attached as labels (see differences). The second row of the crop (the dipeptide again with dashed amino and carboxyl frames, the red peptide bond, the "Peptide bond" and "Polypeptide chain" labels) is not drawn.

Two drawings were made. Try 1 had no captions and was 385 pt wide against a 242 pt budget. Try 2 (the saved `rendered.png`) adds the captions and sets `max_width` to 420. Both wrote structures that read back as matched (4 of 4), but neither passed the layout check (389 pt wide against a 202 pt budget in try 2) and the balance check could not run because of the R groups, so `checks_passed` is false.

Structures (`brief.json`): `NC(*)C(=O)O` (both amino acids), `NC(*)C(=O)NC(*)C(=O)O` (dipeptide), `O` (water). These were checked with RDKit; all are valid and the dipeptide is the peptide-bond condensation product of the two amino acids.

Replay: `python skill/chemdraw/scripts/cdx.py py skill/chemdraw/assets/house-styles/openstax_chemistry/replica/openstax_chemistry-09/replay.py NEW_DIR`, then `python skill/chemdraw/scripts/cdx.py render NEW_DIR/figure.cdxml`.

## Convention table

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| substrate_layout inline_plus | two amino acids side by side, "+" between | same | yes |
| show_plus_sign true | "+" between the reactants | "+" between the reactants, and a second "+" before H2O (not in the crop); show_plus_sign=false deletes every "+", so the product plus cannot be dropped alone | no |
| arrow_style plain (solid arrow with a head) | plain solid arrow (vertical) | horizontal arrow; head size and line weight not measured; no house arrow style is applied by the code (only "bold" is handled) | no (not verified) |
| arrow_length_over_bond_length 2.5 | vertical arrow about 2.5 bond lengths | horizontal arrow about 9 to 10 bond lengths by eye (layout-dependent) | no |
| bond_length_over_cap_height 3.35 | bond 55 px, cap height about 17 px | not measured; labels look large relative to bonds | not checked |
| line_width_over_bond_length 0.042 | about 2.5 px at 55 px bond | not measured | not checked |
| label_font Arial or Helvetica | sans-serif labels | serif (Times-like) labels from the chemdraw_slide preset; the house font is not applied | no |
| compound_label_color #000000 | black for N, C, O and R; the reacting OH and H and the H2O label are red #901800 | all black | no |
| reagent_text_color #000000 | "Condensation reaction" in black | black | yes |
| species named in plain words, not numbered | "Amino acid" captions above each reactant | "Amino acid" captions below each reactant | partial |
| process name beside a vertical arrow | "Condensation reaction" in two lines to the left of a vertical arrow | one line above a horizontal arrow | partial |
| variation_color #901800 on the reacting OH and H, the new peptide bond and the lost H2O | red | all black | no |
| dashed lime-green #7CE400 frames around amino and carboxyl groups | dashed lime frames with plain side labels | no frames, no side labels | no |
| curved arrow carrying H2O away in red | curved red arrow off the main arrow | none; H2O drawn as a plain product | no |

Matched 2 of 14 claimed items after audit (rows 1 and 9). The replicator counted 4 of 14; rows 3 and 8 were overclaims (see Audit). Bond and line measures are not counted because they were not measured.

## Differences from the paper

- Layout: the paper stacks the product in a second row under a vertical arrow. The tool lays the route out left to right on one row.
- Captions: the paper puts "Amino acid" above each reactant; the replica puts them below, as labels.
- Colour: the paper shows the reacting OH and H, the lost H2O and the new peptide bond in dark red #901800. The replica is all black, because the card leaves `new_bond_color` null and no other colour is applied.
- Frames and side labels: the paper has dashed lime-green frames around the amino and carboxyl groups, with "Amino group" and "Carboxyl group" beside them. Neither is drawn.
- By-product: the paper draws H2O as a red curved arrow leaving the main arrow. The replica lists H2O as a plain product after a "+".
- Hydrogens and abbreviations: the paper draws the N-H hydrogens, the O-H hydrogen and the alpha-C hydrogen explicitly. The replica shows NH2 and HO/OH as abbreviations and has no alpha-C hydrogen.
- Orientation: the paper draws each amino acid with the amino group on the left (H2N-CH(R)-COOH), and the dipeptide the same way. The replica mirrors both (HOOC on the left, NH2 on the right).
- Font: the paper uses sans-serif labels. The replica's labels look serif, and the card's label_font is never read (see Tool gaps).
- Arrow length: the paper's arrow is about 2.5 bond lengths (vertical). The replica's horizontal arrow is much longer.
- Second row: the crop's lower row (the dipeptide again with frames, the red peptide bond, "Peptide bond" and "Polypeptide chain") is not drawn.

## Tool gaps

- No top-to-bottom reaction layout (reactants above, product below, a vertical arrow). `draw_figure` only lays out horizontal rows and wraps them.
- No dashed outline frame around a substructure, and no way to put a plain side label next to a structure. Only above and below conditions lines are available.
- No caption placed above a structure. A species `label` sits below the structure.
- Colour of the reacting atoms and lost groups is not available. `new_bond_color` does colour formed bonds through atom mapping (`figure_house._color_new_bonds`), but the card leaves it null. The `reaction_scheme` `variation_color` (#901800) is informational: no code path applies it (`APPLIED_FIGURE_CONVENTIONS` lists only mechanism and catalytic cycle). `atom_halos` puts a filled coloured disc behind atoms, which marks atoms but does not recolour their labels. `substrate_colors` colours whole substrates. So the red OH, H and H2O labels cannot be reproduced.
- No curved by-product arrow leaving a reaction arrow. A by-product must be a plain product (the `kind: "mechanism"` curved arrows only draw electron moves).
- Generic R groups (`*`) cannot be balanced, so the step balance and `checks_passed` cannot be confirmed. Nothing in the brief can mark an R group as balanced.
- A single-step scheme cannot wrap onto a narrower row. The layout check reports the drawing 389 pt wide against a 202 pt budget, and the one automatic re-layout narrowed the budget without changing the drawing.
- `label_font` from the card is never read by the code. The drawing header hard-codes the label font (`ACS_LABEL_FONT = "3"` in `constants.py`). The serif face is visible in `rendered.png`; its cause (the chemdraw_slide preset) was not traced.
- Measured geometry is not applied. The card's `measured` block (bond-to-cap ratio, line width, arrow length, bold width) is stored and validated, but no drawing code reads it, so a measured value could not be reproduced even if it were taken.
- No hydrogen display option. No brief key controls explicit N-H or O-H hydrogens. The NH2 and HO/OH abbreviations are not set by the house style (`abbreviate_groups` is null), and whether explicit `[H]` in a SMILES survives was not tested.
- No orientation control. Neither the brief nor the card has a key for mirroring a structure, so the amino group cannot be put on the left as in the paper.
- The product plus cannot be dropped alone. `show_plus_sign` true only adds an applied-label entry; `show_plus_sign` false removes every "+" text on the page, including the reactant plus.
- No support for the "Peptide bond" and "Polypeptide chain" annotations with arrows.

## Card observations (not changed)

- `reaction_scheme.signature_features` and `figure_types.reaction_scheme.conventions.variation_color` (#901800) say the red applies to the reacting atoms, the lost H2O and the new bond. The top-level `new_bond_color` is null, so no tool applies that red; the card does not say whether the red applies to atoms or bonds.
- `measured.label_font` says Arial or Helvetica. No code path reads it; the drawing header uses a hard-coded label font (`ACS_LABEL_FONT = "3"`). The cause of the serif look was not traced.
- `reaction_scheme.conventions.variation_color` is never applied (see Tool gaps), and the `measured` block is never applied either.
- `measured.arrow_length_over_bond_length` 2.5 comes from the vertical arrow in crop 09; it has no direct meaning for a horizontal scheme.

## Audit

Checked against `reference.png`, `rendered.png`, this card and the toolkit code (`toolkit/cdxml_toolkit/mcp_runtime/figure_house.py`, `figure_draw.py`, `constants.py`, `publication/house_styles.py`). Not re-run: `replay.py`, the readback and `checks_passed`; the balance statement is taken from the earlier run.

- Overclaims: the `arrow_style` and `compound_label_color` rows were marked yes. The replica arrow is horizontal, its head and line weight were never measured, and no code applies a house arrow style. The reference's OH, H and H2O labels are red, so a black-only comparison covers just the unchanged atoms. The `show_plus_sign` row was marked partial but is a mismatch: the replica adds a product plus that the paper does not show.
- Corrected count: 2 of 14 (`substrate_layout` inline_plus and `reagent_text_color`). The `reagent_text_color` match is for colour only; the font differs.
- Measurements from the images: the reference's vertical arrow is about 125 px at its 900 px image width (the card gives 138 px at native size). The rendered horizontal arrow is about 331 px at its 1200 px image width. A 2.5-bond arrow would need bonds about 130 px long, far longer than any bond in the rendered scheme, so the arrow-ratio row is a mismatch. Bond and line measures were not taken.
- Missed differences: the amino acids and the dipeptide are mirrored (carboxyl on the left, amine on the right; the paper has the amine on the left), and the replica abbreviates NH2 and HO/OH where the paper draws explicit hydrogens.
- Missed tool gaps: the card's measured geometry is never applied; the reaction-scheme variation colour is never applied; there is no orientation or explicit-hydrogen control; the product plus cannot be dropped alone.
