# dalton_transactions

Figure house style of Dalton Transactions (RSC), measured from CC BY figures. Base preset: rsc.

## Sources

- Martins et al., Dalton Trans. 2025 (Borane-functionalized heteroscorpionate copper complexes as catalysts for azide-alkyne cycloaddition). DOI 10.1039/d5dt01595b. Licence CC BY 3.0.
- Albrecht et al., Dalton Trans. 2023 (Manganese(III) complexes stabilized with N-heterocyclic carbene ligands for alcohol oxidation catalysis). DOI 10.1039/d3dt01013a. Licence CC BY 3.0.
- Albrecht et al., Dalton Trans. 2025 (Ligand modification for tuning activity and selectivity in chemoselective transfer hydrogenation). DOI 10.1039/d5dt01348h. Licence CC BY 3.0.

## Measurements

- Bond length / atom-label cap height: 2.3
- Line width / bond length: 0.07
- Bold wedge width / bond length: None
- Arrow length / bond length: 6.9

## Conventions

- compound_label_face: bold
- compound_label_color: #000000
- compound_label_italic_suffix: False
- yield_placement: after_product_label (crops 04 and 06 both put the yield after the bold product label; crop 04 parenthesises it, crop 06 does not, and the plain form is set; see conventions notes)
- yield_format: None
- conditions_split: reagents_above_solvent_below
- substrate_layout: None
- abbreviate_groups: ['tBu']
- aromatic_rings: kekule
- new_bond_color: None
- substrate_colors: None
- highlight_fill: None
- reagent_text_color: #000000
- arrow_style: plain
- show_plus_sign: None (no two-component scheme in the sample)

## Signature features

- metal precursor written above the arrow as a formula ([Cu(NCMe)4]BF4, [Mn(acac)3]), solvent and temperature below (crops 02, 04)
- heteroatoms coloured by element: donor N blue #0080F8 or #0000F8, B pink #F80080, Cl green, metal coloured (crops 02, 03, 04)
- bold compound numbers with bold letters (2a,b, 1a,b) under each complex (crops 02, 04, 06)
- substituent key in a rounded grey-outlined box (crops 02, 06)

## Figure types

### coordination_complex

Conventions:

- dative_bond_style: line
- metal_color: None
- highlight_fill: None
- formal_charge_style: plain

Signature features:

- metal-ligand bonds as plain lines or hashed wedges, never arrows (crops 01-06)
- metal symbol coloured: Cu brown #804000 (crops 02, 03), Mn purple #800080 (crop 04), Mn orange #F88040 or by oxidation state (crop 05)
- donor N atoms blue (#0080F8 in crops 02, 03; #0000F8 in crop 04), boron pink #F80080 (crops 01-03)
- arene and Cp ligands bonded to the metal by a single line to the ring (crops 01, 06); Cp* drawn with an inner circle (crop 01)
- cationic complexes as a closing half bracket with the counterion at the upper right (crop 06) or a plain + on the metal (crops 02, 03)

Crops: evidence/dalton_transactions-01.png, evidence/dalton_transactions-02.png, evidence/dalton_transactions-03.png, evidence/dalton_transactions-04.png, evidence/dalton_transactions-05.png, evidence/dalton_transactions-06.png. metal_color null: no single metal colour holds across the crops. Cu brown in crops 02 and 03 (sampled #814200 to #833E00, near #804000); Mn purple in crop 04 (near #800080); Cu black in crop 01 and Ru black in crop 06

### reaction_scheme

Conventions:

- yield_format: None
- selectivity_format: None
- highlight_fill: None
- variation_color: #4C7A2C

Signature features:

- metal precursor formula above the arrow, solvent below (crops 02, 04)
- isolated yields in parentheses after the bold label (crop 04)
- variable groups R and Ar in green #4C7A2C (crop 06)

Crops: evidence/dalton_transactions-02.png, evidence/dalton_transactions-04.png, evidence/dalton_transactions-06.png. variation_color rests on crop 06 only

### catalytic_cycle

Conventions:

- cycle_shape: circle
- cycle_arrow_color: #000000
- catalyst_color: None
- center_label: False
- step_names: False
- intermediate_label_style: None
- curved_arrow_color: None
- highlight_fill: None

Signature features:

- cycle drawn as black arcs on an implied circle, intermediates sitting on the circle (crops 03, 05)
- reagents and by-products enter and leave on short curved side arrows (crops 03, 05)
- product boxed in a rounded grey frame with shadow (crop 03)
- secondary interactions as blue dashed lines #0000F8 with a blue text label (crop 03)

Crops: evidence/dalton_transactions-03.png, evidence/dalton_transactions-05.png. intermediate labels are bold roman (I+, II) in crop 03 and bold letters (B, C, D) in crop 05, so null

### structure_panel

Conventions:

- highlight_fill: None
- variation_color: None
- intermediate_label_style: none

Signature features:

- panels headed A: and B: in bold with italic titles, separated by a dashed horizontal rule (crop 01)
- panel A structures annotated in italics with a TOF (950 h-1, 313 h-1, 1920 h-1, 28 h-1) and a reference such as (Refs. 16-18) or (Ref. 20) (crop 01); panel B structures carry a reference only, such as (Ref. 28) (crop 01)
- Our work and This work in italics under the authors' own complexes (crop 01)

Crops: evidence/dalton_transactions-01.png. one crop

## Evidence crops

- evidence/dalton_transactions-01.png: Chart 1, Martins et al., Dalton Trans. 2025
- evidence/dalton_transactions-02.png: Scheme 1, Martins et al., Dalton Trans. 2025
- evidence/dalton_transactions-03.png: Scheme 4, Martins et al., Dalton Trans. 2025
- evidence/dalton_transactions-04.png: Scheme 1, Albrecht et al., Dalton Trans. 2023
- evidence/dalton_transactions-05.png: Scheme 4, Albrecht et al., Dalton Trans. 2023
- evidence/dalton_transactions-06.png: Scheme 1, Albrecht et al., Dalton Trans. 2025
