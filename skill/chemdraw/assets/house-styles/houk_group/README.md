# houk_group

Figure house style of Houk group (UCLA), computational organic chemistry, measured from open-access figures. Base preset: acs1996.

## Sources

- Galeotti, Houk, Bietti et al., J. Am. Chem. Soc. 2023 (Radical and cationic pathways in C(sp3)-H bond oxygenation by dioxiranes). DOI 10.1021/jacs.3c07163. Licence CC BY 4.0.
- Chen, Wipf, Houk et al., Nat. Commun. 2022 (How mono- and diphosphine ligands alter regioselectivity of the Rh-catalyzed annulative cleavage of bicyclo[1.1.0]butanes). DOI 10.1038/s41467-022-34837-x. Licence CC BY 4.0.

## Measurements

- Bond length / atom-label cap height: 2.4
- Line width / bond length: 0.09
- Bold wedge width / bond length: 0.22
- Arrow length / bond length: 6.2

Notes:

- bond_length_over_cap_height: Crop values run from 2.0 (crop 02, 85 over 42 px) to 2.6 (crop 05); median 2.37, kept at 2.4. Crop 02 is the outlier.
- line_width_over_bond_length: Crop values run from 0.06 (crop 06) to 0.09 (crops 01 and 02, measured on the originals). Crops 03 to 08 are about one pixel wide over 12 to 28 px bonds, so each has a precision of about 0.04 and all agree with 0.09 within it. Kept at 0.09.
- bold_width_over_bond_length: Crop values run from 0.21 to 0.23 (crops 02, 03, 05, 07, 08); crop 06 gives 0.25 (4 over 16 px). Kept at 0.22.
- arrow_length_over_bond_length: Recorded crop values: 5.0 (crop 06, 80 over 16 px), 6.25 (crop 07, 175 over 28 px) and about 11 (crop 08, 160 over 14 px). The median of the three is 6.25, kept at 6.2. A pixel re-check found longer arrows: crop 07 has three arrows of 228, 227 and 158 px over a 28 px bond, and crop 08 a 215 px arrow. The arrow ratio is unresolved and should be re-measured on the original figures.

## Conventions

- compound_label_face: bold
- compound_label_color: #000000
- compound_label_italic_suffix: False
- yield_placement: None (crop 07: a % yield row under the product labels (14, 21, 11 under P6-O, P6-O3, P6-O4), with % conv. in grey above it; crop 08: numbered entry rows (1) and (2) under the scheme, each product followed by its yield in parentheses. The two crops do not share one pattern, so null.)
- yield_format: None (crop 07 gives bare values under a % yield row label; crop 08 gives (87%) after the product. No single template, so null.)
- conditions_split: None (crop 07: step 1 (dioxirane, 48 hours) above the arrow and step 2 (H2CrO4, acetone) below it; crop 08: cat, L above and PhMe, 110 °C below. No single rule, so null.)
- substrate_layout: inline_plus
- abbreviate_groups: ['Ts', 'Ph', 'CF3', 'tBu'] (Ts and Ph in crops 03, 05 and 08; CF3 in crops 01, 02 and 07 (written F3C in crop 07); tBu in crops 01 and 07. Me is labelled in crop 02 only, so it is not listed; add it once a second crop shows it.)
- aromatic_rings: kekule
- new_bond_color: None (red new oxygen (dark red #861212) appears in crop 07 only, so null at top level; the reaction_scheme variation_color carries it.)
- substrate_colors: None
- highlight_fill: None
- reagent_text_color: #000000
- arrow_style: plain
- show_plus_sign: True

Notes:

- compound_labels: Bold black labels: crop 07 (P6-O, P6-O3, P6-O4 under the structures), crop 03 (bold numbers 4, 6, 7 and TS5) and crop 05 (bold TS labels). Crop 08 has no labels under its structures. Energy-profile species labels in crops 01 and 02 are bold italic in pathway colours and are recorded under energy_profile.

## Signature features

- product mixtures drawn inline with plus signs; yields set out as a row under the products (crop 07) or as numbered entry rows (1) and (2) under the scheme, each yield in parentheses after its product (crop 08)
- bold black compound labels under each structure (crop 07: P6-O, P6-O3, P6-O4)
- long plain arrows, about six bond lengths (median of the scheme crops, see notes), with the oxidant drawn as a structure above the arrow (crop 07) or the catalyst as bold italic text above it (crop 08)
- single colour accents on the scheme: the new oxygen atom in dark red #861212 and the reaction time in green #4E9845 (crop 07)

## Figure types

### energy_profile

Conventions:

- energy_unit: kcal/mol
- energy_label: delta_G
- level_style: bars_solid_connectors
- pathway_colors: ['#FF0000', '#3A4694', '#FF6000', '#18A000']
- ts_marker: None
- intermediate_label_style: None

Signature features:

- short thick horizontal level bars joined by thin solid sloped lines (all three crops)
- energy value above each bar; in JACS crops bold italic and coloured by pathway, in the Nat. Commun. crop plain black
- competing pathways told apart by coloured labels and numbers (red #FF0000, blue #3A4694, orange #FF6000, green #18A000) while the connector lines stay black
- species labels in bold italic and the pathway colour in crops 01 and 02 (S8-TS1ax red, P8c-OH blue); bold upright black numbers and TS labels in crop 03
- a structure drawing next to every stationary point, TS partial bonds dashed, spectator fragments in light grey
- double slash breaks on long descending connectors
- stage names in bold upright, not italic, between double-headed arrows along the bottom (crop 03)

Crops: evidence/houk_group-01.png, evidence/houk_group-02.png, evidence/houk_group-03.png

Notes: energy_unit and energy_label rest on crop 03 alone, where the axis title reads ΔGsol (kcal mol-1). Crops 01 and 02 print bare energy numbers with no unit or delta-G label, which is an absence rather than a different unit. Blue in pathway_colors is the flat fill of crop 01 (#3A4694); crop 02 is darker (#202A67). ts_marker null: brackets with double dagger in crop 03 only, while crops 01 and 02 name TS without brackets. Labels are bold numbers or TS5 in crop 03 and bold italic names (S8-TS1ax) in crops 01 and 02.

### catalytic_cycle

Conventions:

- cycle_shape: open_arc
- cycle_arrow_color: None
- catalyst_color: None
- center_label: False
- step_names: True
- intermediate_label_style: bold_roman
- curved_arrow_color: None
- highlight_fill: None

Signature features:

- two mirrored loops of open arcs leaving a central catalyst-substrate complex
- each pathway its own colour (red #FF1D1E, green #38996E, blue #382DFF), solid for one manifold and dashed for the competing one
- bold roman intermediate labels I to XII
- step names in bold black along the arcs, path letters in bold italic (path A)

Crops: evidence/houk_group-04.png

Notes: one crop; arrow colour varies by pathway so cycle_arrow_color is null

### structure_panel

Conventions:

- highlight_fill: None
- variation_color: None
- intermediate_label_style: None

Signature features:

- 3D ball-and-stick TS geometry (CYLview style, grey C, orange P, green Cl) above a 2D ChemDraw drawing of the same TS
- 2D TS in square brackets with a double dagger, forming bonds dashed
- bold TS label (TS5, TS5*) with ΔΔG‡ = x.x kcal mol-1 underneath
- key distances in Å on thin leader lines

Crops: evidence/houk_group-05.png

Notes: one crop

### mechanism

Conventions:

- curved_arrow_color: None
- curved_arrow_weight: None
- show_lone_pairs: False
- formal_charge_style: circled
- intermediate_label_style: None
- ts_marker: None
- highlight_fill: None

Signature features:

- step names written in rounded pastel pills on the arrow (HAT pale cyan #DAFFF7, OH rebound pale green #E0FFC3)
- radicals drawn as dots, no curved arrows
- charges circled (crops 01, 02)

Crops: evidence/houk_group-06.png, evidence/houk_group-01.png, evidence/houk_group-02.png

Notes: Pill fills from crop 06 only: HAT pill pale cyan (about #DAFFF7), OH rebound pill pale green (#E0FFC3). Two pill colours cannot share one highlight_fill, so it is null; crop 02 has no pills. Circled charges from crops 01 and 02.

### reaction_scheme

Conventions:

- yield_format: None
- selectivity_format: None
- highlight_fill: None
- variation_color: #861212

Signature features:

- reagent drawn as a structure above the arrow, with bold step numbers 1. and 2. (crop 07; step 1 above the arrow, step 2 below it)
- conditions in bold: cat, L bold italic above the arrow and PhMe, 110 °C bold below (crop 08)
- new oxygen in dark red #861212 and reaction time in green #4E9845 (crop 07)
- results as rows under the products, % conv. in grey and % yield in black (crop 07)

Crops: evidence/houk_group-07.png, evidence/houk_group-08.png

Notes: variation_color rests on crop 07 alone, where the new carbonyl oxygen atoms are dark red. Crop 08 has no structure reagent and no step numbers. The red new atom is in crop 07 only.

## Evidence crops

- evidence/houk_group-01.png: Figure 7 (energy profile for S8), Galeotti, Houk, Bietti et al., J. Am. Chem. Soc. 2023
- evidence/houk_group-02.png: Figure 5 (energy profile for S3), Galeotti, Houk, Bietti et al., J. Am. Chem. Soc. 2023
- evidence/houk_group-03.png: Fig. 4, Chen, Wipf, Houk et al., Nat. Commun. 2022
- evidence/houk_group-04.png: Fig. 2, Chen, Wipf, Houk et al., Nat. Commun. 2022
- evidence/houk_group-05.png: Fig. 6, Chen, Wipf, Houk et al., Nat. Commun. 2022
- evidence/houk_group-06.png: Scheme 2, Galeotti, Houk, Bietti et al., J. Am. Chem. Soc. 2023
- evidence/houk_group-07.png: Scheme 4, Galeotti, Houk, Bietti et al., J. Am. Chem. Soc. 2023
- evidence/houk_group-08.png: Fig. 1, Chen, Wipf, Houk et al., Nat. Commun. 2022
