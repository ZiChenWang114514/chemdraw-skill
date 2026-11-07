# glorius_group

Figure house style of the Glorius group (University of Münster), photocatalysis and energy transfer, measured from open-access figures. Base preset: acs1996.

## Sources

- Gutierrez, Glorius et al., J. Am. Chem. Soc. 2024 (gamma-Amino alcohols via energy transfer enabled Brook rearrangement). DOI 10.1021/jacs.4c01667. Licence CC BY 4.0.
- Glorius et al., J. Am. Chem. Soc. 2025 (Cyclic bifunctional reagents enabling a strain-release-driven formal [3+2] cycloaddition). DOI 10.1021/jacs.4c18080. Licence CC BY 4.0.
- Wenger, Glorius et al., J. Am. Chem. Soc. 2025 (Phenothiazine sulfoxides as active photocatalysts for the synthesis of gamma-lactones). DOI 10.1021/jacs.5c01988. Licence CC BY 4.0.
- Glorius et al., Chem. Sci. 2023 (Metal-free photosensitized radical relay 1,4-carboimination across two distinct olefins). DOI 10.1039/d2sc06497a. Licence CC BY 3.0.

## Measurements

- Bond length / atom-label cap height: 2.2
- Line width / bond length: 0.078 (median of crops 01, 03 and 05; per-crop 0.063 to 0.083; the earlier 0.075 was their mean)
- Bold wedge width / bond length: not measured
- Arrow length / bond length: 13.4

## Conventions

- compound_label_face: bold
- compound_label_color: #000000
- compound_label_italic_suffix: False
- yield_placement: after_product_label
- yield_separator: , 
- yield_format: {value}%
- conditions_split: None (No value. Crop 01 splits the conditions by step: the reagents and DMF sit above step (i) and Et2O is below step (ii). Crop 03 puts all its conditions above the arrow. The crops disagree, so no value is set.)
- substrate_layout: inline_plus
- abbreviate_groups: ['Ph', 'Me', 'Et', 'CO2Et', 'CO2Me', 'OMe', 'Boc', 'OTBS', 'CF3', 'CN'] (Me is labelled on silicon (SiMe2 in crops 01 and 02). Gem-dimethyl groups on carbon rings are drawn as bare bonds with no label (crops 03 and 04).)
- aromatic_rings: kekule
- new_bond_color: None (red new C-C bonds #F82D30 only in the Chem. Sci. mechanism crop (06); not seen in the JACS crops)
- substrate_colors: ['#2C0001', '#0203FE'] (Reaction-scheme convention: crops 01 and 02 (same paper) only; not applied to the scope, mechanism, catalytic-cycle or energy-profile crops. #2C0001 is the aryl/oxime part (the aryl groups of product 2 in crop 01 and of reagent 2 in crop 02); #0203FE is the silyl part (S1 and S3 in crop 01, the O-CH2-Si unit of reagent 2 in crop 02). Alkene 1 stays black.)
- highlight_fill: None (No single highlight. Crop 02 marks the reacting CH2 with mint dots (flat shades #9BF5C8 and #89EDC7; #92F2C4 lies between them). These are atom halos, not ring fills. Crop 03 fills the product core ring with #DEE2E5. The highlight_fill key fills product rings, so the scheme and mechanism sections record the dots as a signature and leave the key unset.)
- reagent_text_color: #000000
- arrow_style: plain
- show_plus_sign: True

## Signature features

- panel titles in crop 01 are bold italic with a parenthesised capital letter, e.g. (A) Reagent synthesis, above a dashed horizontal rule; the other crops differ: crop 04 bold italic without a letter, crop 05 bold upright without parentheses, crop 06 regular weight with parenthesised letters under a solid rule
- energy-transfer step in the concept panel (crop 02) drawn as a cyan lamp icon #41ABE7 on the arrow next to a circled EnT with a circular arrow
- the two reagent fragments colour-coded: oxime/aryl part in very dark red-brown #2C0001, silyl part in blue #0203FE
- multistep conditions as numbered lines (i), (ii) split above and below one long arrow
- atom labels and compound labels in bold Arial-like sans serif; yields as 3a, 69% (70%) with NMR yield in parentheses

## Figure types

### reaction_scheme

Conventions:

- yield_format: None
- variation_color: #0203FE
- highlight_fill: None
- selectivity_format: None

Signature features:

- silyl reagents S1 and S3 blue (#0203FE) throughout, including Cl or HO, CH2, Si, Me and R; in reagent 2 and product 2 the blue starts at the O-CH2 of the carbonate; aryl/oxime part dark red-brown #2C0001
- two-step sequences written as (i) and (ii) lines, one above and one below a single long arrow
- dashed rectangle drawn around one box: the reagent S5 in crop 01, or the whole general reaction (1 + 2 to 3) in crop 02
- mint dots #92F2C4 on the reacting CH2 of reagent 2 and of product 3 (crop 02), drawn on the atom rather than as a ring fill

Crops: evidence/glorius_group-01.png, evidence/glorius_group-02.png.

Notes: variation colour agrees in crops 01 and 02 (same paper); yield_format is null because neither crop shows a yield (the yield format is in substrate_scope, crop 03); the conditions split by step is in crop 01 only.

### substrate_scope

Conventions:

- scope_layout: grid_with_core
- conditions_position: scheme_on_top
- yield_format: {value}%
- selectivity_format: None
- highlight_fill: #DEE2E5
- variation_color: None

Signature features:

- general scheme on top with coloured dots marking the substituent positions, then one row of products: 3a, the X-ray entry, 3b to 3f drawn once as a core with an R list, then 3g, 3h and 3i
- substrate classes introduced by bold italic labels on mint tabs #73EDB0 at the left of dashed horizontal separators
- conserved product core drawn in dark green #0B5234 with a pale grey fill #DEE2E5 inside the ring
- yield line 3a, 69% (70%) with isolated yield then NMR yield in parentheses

Crops: evidence/glorius_group-03.png.

Notes: one crop; the conventions are unambiguous in it. selectivity_format is null because no d.r. is shown. highlight_fill is the product core ring fill (#DEE2E5), the key the tool applies; the mint section tabs (#73EDB0) are signature features, not a highlight. scope_layout is kept as grid_with_core, the nearest value, but crop 03 is one row with one shared 3b to 3f core, not a two-dimensional grid.

### mechanism

Conventions:

- curved_arrow_color: None
- curved_arrow_weight: None
- intermediate_label_style: None
- highlight_fill: None

Signature features:

- energy transfer drawn as lamp icon #41ABE7 plus a circled EnT with a circular arrow on the reaction arrow (crop 02); in the Chem. Sci. figure as the word EnT above the arrow with -CO2 below (crop 06)
- radicals named by italic captions under the structure: persistent and transient in crop 02; persistent (ambiphilic) and transient (nucleophilic) in crop 06. In crop 02 the short-lived and stabilised radicals 2' and 2'' have roman captions beside the structures
- newly formed C-C bonds in red #F82D30 (crop 06)
- radical steps shown with straight reaction arrows, no electron-pushing curved arrows
- mint dots #92F2C4 on the migrating CH2 of the Brook rearrangement (crop 02), drawn on the atom, not as a ring fill

Crops: evidence/glorius_group-02.png, evidence/glorius_group-06.png.

Notes: no curved electron-pushing arrows in either crop, so arrow colour and weight are not set; crop 06 mixes bold letters (A, B) with IM1 and IM2; crop 02 labels its intermediates 2' and 2''; no single intermediate label style, so it is not set

### catalytic_cycle

Conventions:

- cycle_shape: circle
- cycle_arrow_color: #000000
- catalyst_color: #000000
- center_label: True
- step_names: True
- curved_arrow_color: #000000
- intermediate_label_style: None
- highlight_fill: None

Signature features:

- cycle closed by black curved arrows with substrates entering and leaving on side arcs
- step names (SET) in bold italic dark red #7E2228 beside the arcs, with E1/2 values in dark red below
- boxed centre label giving the quantum yield (Phi rxn = 0.55)
- violet lamp icon #6331BC on a pair of equilibrium arrows for photoexcitation of the catalyst

Crops: evidence/glorius_group-05.png.

Notes: one crop

### energy_profile

Conventions:

- energy_unit: kcal/mol
- energy_label: delta_G
- level_style: bars_solid_connectors
- pathway_colors: ['#000000', '#859795']
- ts_marker: none
- intermediate_label_style: None

Signature features:

- main pathway as black bars and solid connectors; competing pathway as grey #859795 bars with dashed connectors
- each level labelled with bold species name with superscript multiplicity (3TS-1, 3IM-1) above two values: dG and (dE) in parentheses
- vertical axis drawn as a bare upward arrow labelled dG (dE) in kcal/mol, no tick marks
- stage brackets under the x axis with italic names (Isoxazolone ring contraction, Olefin insertion into azirine)
- inset boxes with thin grey frames for competing transition states; spin densities on pink #EB659D circles
- pale grey ring fill #DEE2E5 on the isoxazolone 1a ring and the product 13a ring; dark green #244E41 bonds on the 13a core; a double-slash break mark on the connector from MECP-2 to 13a

Crops: evidence/glorius_group-04.png.

Notes: one crop; transition states are named TS in the label, not marked with a double dagger

## Evidence crops

- evidence/glorius_group-01.png: Figure 2A, Gutierrez, Glorius et al., J. Am. Chem. Soc. 2024
- evidence/glorius_group-02.png: Figure 1E, Gutierrez, Glorius et al., J. Am. Chem. Soc. 2024
- evidence/glorius_group-03.png: Figure 4 top, Glorius et al., J. Am. Chem. Soc. 2025
- evidence/glorius_group-04.png: Figure 3, Glorius et al., J. Am. Chem. Soc. 2025
- evidence/glorius_group-05.png: Figure 4A, Wenger, Glorius et al., J. Am. Chem. Soc. 2025
- evidence/glorius_group-06.png: Fig. 1E, Glorius et al., Chem. Sci. 2023
