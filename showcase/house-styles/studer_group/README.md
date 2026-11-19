# studer_group

Figure house style of the Studer group (University of Münster), radical chemistry, measured from open-access figures. Base preset: nature.

## Sources

- Studer et al., Nature 2023 (Photocatalytic phosphine-mediated water activation for radical hydrogenation). DOI 10.1038/s41586-023-06141-1. Licence CC BY 4.0.
- Studer et al., Nat. Commun. 2024 (Iron-catalyzed radical Markovnikov hydrohalogenation and hydroazidation of alkenes). DOI 10.1038/s41467-024-51706-x. Licence CC BY 4.0.
- Studer et al., Nat. Commun. 2022 (Decatungstate-catalyzed radical disulfuration through direct C-H functionalization). DOI 10.1038/s41467-022-31617-5. Licence CC BY 4.0.

## Measurements

- Bond length / atom-label cap height: 2.5
- Line width / bond length: 0.05
- Bold wedge width / bond length: not measured
- Arrow length / bond length: 6.9

## Conventions

- compound_label_face: bold
- compound_label_color: #000000
- compound_label_italic_suffix: False
- yield_placement: after_product_label
- yield_separator: , 
- yield_format: {value}%
- conditions_split: None
- substrate_layout: inline_plus
- abbreviate_groups: ['Ph', 'OMe', 'CO2Et', 'Ts', 'Boc', 'PhthN', 'OTBS', 'OAc']
- aromatic_rings: kekule
- new_bond_color: #FF0000
- substrate_colors: None
- highlight_fill: None
- reagent_text_color: #000000
- arrow_style: plain
- show_plus_sign: True

Notes:

- conditions_split: crop 06 has reagents above and solvent, temperature and time below; crop 01 puts the solvent CH3CN above and water and light below; not determined
- new_bond_color: red #FF0000 for the new C-H bond in crops 03, 04 and 06; crop 02 colours only the transferred H labels red (its new C-H bonds are black); the new C-S bond in crop 05 is black; crop 01 has no colour
- bold_width_over_bond_length: wedge in crop 02 is 7 px wide but no bond in that crop could be measured cleanly
- measurement: bond/cap 2.7 (crop 04), 2.5 (crops 03 and 06), 2.25 (crop 05, 45 px over 20 px); 2.5 is the value most crops support; Nature Portfolio figures measured on the 1000 to 2100 px Springer full-size PNGs
- arrow_length_over_bond_length: 6.9 rests on crop 06: arrow 218 px over a bond of about 31 px on the 900 px crop (about 7.0). The px values logged for crop 06 (329 over 48) must be at a larger scale; the ratio is the same. Crop 01 gives about 10 when its bond is inferred from cap height (no bond measured there), so the arrow ratio is approximate
- line_width_over_bond_length: 0.05 is the centre of the spread: 0.042 (crop 03), 0.044 (crop 05), about 0.048 (crop 01, bond inferred), 0.054 (crop 04), 0.06 (crop 06); spread 0.04 to 0.06
- yield_placement: after_product_label in crops 04 and 06; crop 01 has no compound label and sets its yield under the structure
- abbreviate_groups: Me is labelled only in the mechanism crop 03; the scheme crop 06 draws the two methyls of 2a as bare bonds, so Me is left out. Boc, PhthN and OAc are not drawn in any evidence crop and are unverified
- reagent_text_color: black in schemes 01 and 06 and mechanism 02; the navy catalyst name in cycle crop 05 is recorded under catalytic_cycle

## Signature features

- transferred hydrogen atom in pure red #FF0000, with its new C-H bond red in crops 03, 04 and 06 (black in crop 02); the newly introduced X group and its bond in pure blue #0000FF
- thin lines and Helvetica labels; catalyst codes such as PC1 in bold inside the conditions (crop 01), catalyst formulas such as Fe(acac)3 in plain text (crop 06)
- yields as 11, 49% (cis:trans = 9.1:1) with bold label, comma and the ratio in parentheses, italic cis/trans
- panel headings as plain text A. Trapping of ... or bold lowercase Nature panel letters

## Figure types

### reaction_scheme

Conventions:

- yield_format: {value}%
- variation_color: #0000FF
- highlight_fill: None
- selectivity_format: None

Signature features:

- new X group and its bond in blue #0000FF, transferred H in red #FF0000
- catalyst code PC1 in bold inside the conditions (crop 01); catalyst formula Fe(acac)3 in plain text (crop 06)
- gas evolution shown as + H2 followed by an upward arrow (crop 01)

Crops: evidence/studer_group-01.png, evidence/studer_group-06.png.

Notes: blue variation colour and the blue X / red H signatures rest on crop 06 (the only scheme with coloured bonds) and the scope crop 04; crop 01 is greyscale, so it supports only the scheme type, the catalyst code, the yield and the gas features

### substrate_scope

Conventions:

- scope_layout: grid
- variation_color: #0000FF
- yield_format: {value}%
- selectivity_format: dr = {value}
- conditions_position: None
- highlight_fill: None

Signature features:

- centred plain section titles (reaction from secondary radical) set between thin black horizontal rules
- one structure with a generic X stands for several products, listed below it as up to four lines, one per X (3a, 80% (X = Br); 5a, 72% (X = I); 7a, 62% (X = Cl); 8a, 48% (X = N3))
- new C-H bond and H in pure red #FF0000, new C-X bond and X in pure blue #0000FF on every product

Crops: evidence/studer_group-04.png.

Notes: one crop; conditions are in the figure caption, not drawn; no bold blue wedge is drawn (the only blue pixels are the X letters and thin C-X bonds) and no X-ray row is shown

### mechanism

Conventions:

- curved_arrow_color: #000000
- curved_arrow_weight: bond
- show_lone_pairs: False
- formal_charge_style: plain
- intermediate_label_style: bold_letter
- ts_marker: None
- highlight_fill: None

Signature features:

- electron transfer to the photocatalyst as a thin black curved arrow riding over a straight reaction arrow (IrIII to IrII)
- radical cations written with a plain + and a dot above the atom
- radicals as a single dot on the carbon; transferred H in red #FF0000
- intermediates labelled with bold capital letters A, B, C

Crops: evidence/studer_group-02.png, evidence/studer_group-03.png.

Notes: curved arrows are black and as thin as bonds in both crops; bold letters A, B, C in crop 03 only, crop 02 has no intermediate letters, so the letter style rests on one crop (unambiguous)

### catalytic_cycle

Conventions:

- cycle_shape: circle
- cycle_arrow_color: #000000
- catalyst_color: None
- center_label: False
- step_names: True
- curved_arrow_color: #000000
- intermediate_label_style: None
- highlight_fill: #8383DF

Signature features:

- cycle drawn as large black arcs with reagents entering and by-products leaving on smaller curved arrows
- step names beside the arcs: grey #8E8E8E plain (HAT, CPET) in crop 03, bold italic navy #000080 (HAT, SET) in crop 05
- photoexcitation as an orange lightning bolt #FF9C38 with a wavy arrow (crop 05)
- substituent R inside orange #FF8000 discs and sulfur atoms in dark red #800000 (crop 05)

Crops: evidence/studer_group-03.png, evidence/studer_group-05.png.

Notes: step-name colour differs between the two papers; intermediates bold letters in crop 03, bold numbers in crop 05, so the label style is not set; catalyst_color is not set because crop 03 draws the Fe catalyst black and crop 05 draws the photocatalyst label *[W10O32]4- and 1* navy bold while H[W10O32]4- is black; highlight_fill comes from the lavender halo on the reacting C-H of 2a and on the ring carbon of 4 in crop 05 only

## Evidence crops

- evidence/studer_group-01.png: Fig. 2a, Studer et al., Nature 2023
- evidence/studer_group-02.png: Fig. 2b, Studer et al., Nature 2023
- evidence/studer_group-03.png: Fig. 3D, Studer et al., Nat. Commun. 2024
- evidence/studer_group-04.png: Fig. 2 top, Studer et al., Nat. Commun. 2024
- evidence/studer_group-05.png: Fig. 3, Studer et al., Nat. Commun. 2022
- evidence/studer_group-06.png: Fig. 3B, Studer et al., Nat. Commun. 2024
