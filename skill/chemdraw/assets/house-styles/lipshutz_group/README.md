# lipshutz_group

Reaction-scheme house style of the Lipshutz group (University of California, Santa Barbara), measured from open-access figures. Base preset: acs1996.

## Sources

- Iyer, Lipshutz et al., JACS Au 2024, 4, 680. DOI 10.1021/jacsau.3c00742. Licence CC BY 4.0.
- Freiberg, Lipshutz et al., Chem. Sci. 2023, 14, 3462. DOI 10.1039/d3sc00198a. Licence CC BY 3.0.
- Lipshutz et al., J. Am. Chem. Soc. 2023 (Introducing Savie: a biodegradable surfactant). DOI 10.1021/jacs.2c13444. Licence CC BY 4.0.

## Measurements

- Bond length / atom-label cap height: 2.2
- Line width / bond length: 0.055
- Bold wedge width / bond length: None
- Arrow length / bond length: 6.3

## Conventions

- compound_label_face: bold
- compound_label_color: #000000
- compound_label_italic_suffix: False
- yield_placement: under_product_label
- yield_format: {value}%
- conditions_split: reagents_above_solvent_below
- substrate_layout: inline_plus
- abbreviate_groups: ['OMe', 'CF3', 'Boc', 'NO2', 'Ph', 't-Bu', 'Cbz']
- aromatic_rings: kekule
- new_bond_color: None (purple #7F07FF in crop 01; red in crop 03 with the incoming amine purple; the crops disagree, so the value stays null)
- substrate_colors: None
- highlight_fill: None (pale cyan ellipses #D5FFFE behind the changing group in crop 02 only; see the reaction_scheme figure type below)
- reagent_text_color: #000000
- arrow_style: plain
- show_plus_sign: True

Notes:

- yield_format: the yield line carries a per-scheme prefix before the value (X = Br, 82% in crop 01; Savie: 95% in crop 03). The prefix is scheme text, not part of the template, so the format stays {value}%.
- surfactant_spacing: 2 wt % with a space in crops 01 and 03; 2 wt% with no space in crop 02 (Scheme 8).

## Signature features

- surfactant and water written below the arrow, e.g. 2 wt % Savie/H2O or 2 wt % TPGS-750-M / H2O [0.5 M]
- purple #7F07FF marks the new C-N bond in crop 01 or the incoming amine fragment in crop 03 (where the new bond is red)
- yield line combines a condition and the yield, e.g. X = Br, 82% or Savie: 95%
- bold italic blue section headers in scope figures

## Figure types

- reaction_scheme (crop 02): highlight_fill #D5FFFE, the flat-pixel mode of the cyan ellipses. Read from one crop, which is unambiguous for this figure type. Signature features: one-pot three-step sequence with reagent above and conditions below each arrow; pale cyan ellipses behind the changing group; yellow step ovals.
- substrate_scope (crops 01 and 03): no convention values recorded, because the crops do not agree on a layout (crop 03 shows its products in one row). Signature features: yield line under each bold product number, prefixed by the condition or surfactant; bold italic blue section headers (crop 01 only); purple new C-N bond in crop 01, red new bond in crop 03 with the incoming amine purple.

## Evidence crops

- evidence/lipshutz_group-01.png: Figure 3, amination scope, Iyer, Lipshutz et al., JACS Au 2024, 4, 680
- evidence/lipshutz_group-02.png: Scheme 8, Freiberg, Lipshutz et al., Chem. Sci. 2023, 14, 3462
- evidence/lipshutz_group-03.png: Figure 5B, aminations, Lipshutz et al., J. Am. Chem. Soc. 2023
