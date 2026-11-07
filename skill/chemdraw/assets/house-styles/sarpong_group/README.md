# sarpong_group

Reaction-scheme house style of the Sarpong group (UC Berkeley), measured from open-access figures. Base preset: nature.

## Sources

- Sarpong et al., Nat. Commun. 2024 (Late-stage benzenoid-to-troponoid skeletal modification of the cephalotanes: total synthesis of harringtonolide). DOI 10.1038/s41467-024-48586-6. Licence CC BY 4.0.
- Sarpong et al., J. Am. Chem. Soc. 2023 (Photo- and metal-mediated deconstructive approaches to cyclic aliphatic amine diversification). DOI 10.1021/jacs.3c01318. Licence CC BY 4.0.
- Sarpong et al., J. Am. Chem. Soc. 2026 (Strategic applications of single-atom skeletal editing in natural product synthesis). DOI 10.1021/jacs.6c04423. Licence CC BY 4.0.
- Sarpong and Hoffmann et al., Angew. Chem. Int. Ed. 2020 (A case for bond-network analysis in the synthesis of bridged polycyclic complex molecules: hetidine and hetisine alkaloids). DOI 10.1002/anie.201909656. Licence CC BY 4.0.

## Measurements

- Bond length / atom-label cap height: 2.9
- Line width / bond length: 0.056
- Bold wedge width / bond length: 0.19
- Arrow length / bond length: 3.7 (measured on crop 03 (134 px arrow over 36 px bond). Crop 07 gives about 2.2 (67 px over 30 px, rough, not re-measured here). Two crops disagree, so the spread is recorded and the value from crop 03, the crop measured on all four ratios, is kept.)

## Conventions

- compound_label_face: bold
- compound_label_color: #000000
- compound_label_italic_suffix: False
- yield_placement: None (yields sit under the arrow in one crop only (06: 18%, 62%, 98%, 64%); crops 03 and 07 show no yields; the scope crop 05 puts yields under the product (substrate_scope section), so null.)
- yield_format: {value}%
- conditions_split: reagents_above_solvent_below
- substrate_layout: None (only one-component steps in the crops)
- abbreviate_groups: ['Me', 'OMe'] (Me in crops 01, 02, 03, 05, 06, 07 and 08; OMe in crops 03, 05 and 07 (written MeO where the group sits on the right, the house reading in house_styles.ABBREVIATIONS). Boc is in crop 07 only, so it is not listed at top level (2+ crops rule). tBu is in no crop and was dropped. Piv (crops 04, 05) and Teoc (crop 06) are not in house_styles.ABBREVIATIONS, so they cannot be listed.)
- aromatic_rings: kekule
- new_bond_color: None (colour marks changed atoms, bonds or rings (crop 01 dark red, crop 06 crimson), strategic bonds (crop 08 red and green) or new bonds (crop 07 blue); the colour differs between papers, so null.)
- substrate_colors: None
- highlight_fill: None (one crop (01) has a flat #CCCCCC box behind a molecule (structure_panel section); no other crop does, so null here.)
- reagent_text_color: #000000
- arrow_style: plain (plain single shafts in crops 02, 06 and 07; the condensed-sequence arrows ('N steps') in crop 06 are drawn with a double shaft, which the enum cannot express; crop 03 draws its arrows between intermediates dashed.)
- show_plus_sign: None (no two-component scheme seen)

## Signature features

- bold heavy bonds (about 3x line width) on the near face of caged polycycles, plain thin bonds behind (not in crop 08)
- atoms or bonds that change in the key step coloured: dark red #800000 (Nat. Commun.), crimson #A10E3D (JACS 2026 review)
- condensed sequences as an arrow labelled 'N steps' above the arrow in crop 06 (below it in crop 07), yield below

## Evidence crops

- evidence/sarpong_group-01.png: Figure 1A, Sarpong et al., Nat. Commun. 2024
- evidence/sarpong_group-02.png: Figure 1C, Sarpong et al., Nat. Commun. 2024
- evidence/sarpong_group-03.png: Figure 2B, Sarpong et al., Nat. Commun. 2024
- evidence/sarpong_group-04.png: Figure 2B (proposed mechanism), Sarpong et al., J. Am. Chem. Soc. 2023
- evidence/sarpong_group-05.png: Figure 3 (scope of reaction), Sarpong et al., J. Am. Chem. Soc. 2023
- evidence/sarpong_group-06.png: Figure 3, Sarpong et al., J. Am. Chem. Soc. 2026
- evidence/sarpong_group-07.png: Scheme 1, Sarpong and Hoffmann et al., Angew. Chem. Int. Ed. 2020
- evidence/sarpong_group-08.png: Figure 6, Sarpong and Hoffmann et al., Angew. Chem. Int. Ed. 2020

## Figure types

### structure_panel

Conventions:

- highlight_fill: #CCCCCC
- variation_color: #800000
- intermediate_label_style: bold_number

Signature features:

- family members side by side, differing atoms in dark red #800000
- name with bold number in parentheses, step count below in bold italic teal #0C5C61
- core skeleton in a thin grey frame with grey ring letters A-E

Crops: evidence/sarpong_group-01.png

Notes: one crop (01); unambiguous. highlight_fill is the flat #CCCCCC grey box behind the common intermediate at the right edge of the crop (one crop).

### mechanism

Conventions:

- curved_arrow_color: #800000
- curved_arrow_weight: thin
- show_lone_pairs: False
- formal_charge_style: plain
- intermediate_label_style: bold_number
- ts_marker: None
- highlight_fill: None

Signature features:

- dark red #800000 curved arrows thinner than bonds, drawn over the cage
- intermediates in tall square brackets; one pair can enclose several species (crop 03: 21 to 22', 22 inside), 20 and the product not bracketed
- dashed reaction arrows between them (crop 03; crop 02 uses solid arrows)
- teal dot #0C5C60 on the reacting carbon
- dashed grey frame around the pathway with an underlined bullet title

Crops: evidence/sarpong_group-02.png, evidence/sarpong_group-03.png

Notes: no double-dagger transition-state marks on the structures. Crop 03 has energy-profile labels TS1 (11.7) and TS2-C (10.1) at its bottom edge; they belong to the energy profile, not the mechanism. formal_charge_style plain comes from crop 03 only (N2+ and the BF3 anion on 21); crop 02 has no charged atom.

### catalytic_cycle

Conventions:

- cycle_shape: circle
- cycle_arrow_color: #000000
- catalyst_color: None
- center_label: True
- step_names: False
- intermediate_label_style: bold_letter
- curved_arrow_color: None
- highlight_fill: None

Signature features:

- black arcs form the cycle; side inputs and outputs on small curved arrows
- bold italic purple #752ED6 'Proposed Mechanism' in the centre
- blue lightbulb in a blue #092DFF ring at the excitation step
- radical dots in blue

Crops: evidence/sarpong_group-04.png

Notes: one crop (JACS 2023, crop 04). cycle_shape circle: a closed ring of black arcs, broken where the side arrows enter and leave. intermediate_label_style bold_letter is the nearest value: the labels are bold number.letter (2.A, 2.B*, 1.B) and no enum value covers number.letter.

### substrate_scope

Conventions:

- scope_layout: grid
- variation_color: None
- yield_format: {value}%
- selectivity_format: None
- conditions_position: None
- highlight_fill: None

Signature features:

- each cell pairs substrate (left) with product (right)
- bold label and yield (e.g. '3b: 62%', label and yield on one line) under the product
- section title over a violet #C385DB rule

Crops: evidence/sarpong_group-05.png

Notes: one crop; no selectivity values. No conditions appear in the crop, so conditions_position is null. No variation colour: the crop has no magenta below the title and the new CHO is black; the magenta is the title colour only.

### total_synthesis

Conventions:

- step_label_style: none
- step_count_shown: True
- yield_format: {value}%
- highlight_fill: None
- variation_color: None

Signature features:

- reagents above each arrow and the yield below it where shown (crop 06); 'N steps' on the arrow for condensed sequences
- 'prepared in N steps' in small grey text under the start (crop 06 only)
- target name in bold italic black under the final structure (crop 06 only)
- changed atoms in crimson #A10E3D (crop 06, review) or new bonds in blue #2758A5 (crop 07, Angew)

Crops: evidence/sarpong_group-06.png, evidence/sarpong_group-07.png

Notes: variation_color null: crop 06 colours changed atoms crimson and crop 07 colours new bonds blue, so the colour differs between papers. Yield under the arrow in crop 06 only (crop 07 shows none). 'N steps' sits above the arrow in crop 06 and below it in crop 07. The prepared-in and target-name features are crop 06 only; crop 07 has neither, and the target names in crop 06 are black, not blue.

### retrosynthesis

Conventions:

- retro_arrow: none
- disconnection_mark: colored_bond
- disconnection_color: #EA3735
- highlight_fill: None
- step_count_shown: False

Signature features:

- strategic bonds as thick red #EA3735 and green #42B54F bonds on the skeleton instead of retro arrows; the crop does not say what green marks
- ring letters in blue and carbon numbers in small black digits

Crops: evidence/sarpong_group-08.png

Notes: one crop; bond-network analysis; no open retro arrows. disconnection_color covers the red bonds only; green bonds (14a and the lower-right structure) also appear, with no rule given in the figure.
