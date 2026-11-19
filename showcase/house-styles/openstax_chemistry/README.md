# openstax_chemistry

House style of the OpenStax Chemistry textbooks, measured from the CC BY 4.0 first editions of Chemistry (Flowers et al., 2015). Base preset: chemdraw_slide.

## Sources

- Flowers, Theopold, Langley, Robinson et al., OpenStax Chemistry 2015, section 12.7 Catalysis. Licence CC BY 4.0.
- Flowers, Theopold, Langley, Robinson et al., OpenStax Chemistry 2015, section 12.6 Reaction Mechanisms. Licence CC BY 4.0.
- Flowers, Theopold, Langley, Robinson et al., OpenStax Chemistry 2015, section 19.2 Coordination Chemistry of Transition Metals. Licence CC BY 4.0.
- Flowers, Theopold, Langley, Robinson et al., OpenStax Chemistry 2015, section 20.1 Hydrocarbons. Licence CC BY 4.0.
- Flowers, Theopold, Langley, Robinson et al., OpenStax Chemistry 2015, section 20.4 Amines and Amides. Licence CC BY 4.0.

Chemistry 2e, Chemistry: Atoms First 2e and Organic Chemistry are now CC BY-NC-SA 4.0 and were not used.

## Measurements

- Bond length / atom-label cap height: 3.2 (crops 07 and 09; crop 04 gives 3.67, so the spread is 3.2 to 3.67)
- Line width / bond length: 0.049 (crops 07 and 09; crop 04 gives 0.036)
- Bold wedge width / bond length: 0.24 (crop 04 only)
- Arrow length / bond length: 2.5 (crop 09 only)

Pixel measures use an 8-bit luminance threshold of 140 on each crop. The full per-crop values are in the card's evidence list and conventions.notes.

## Conventions

- compound_label_face: None (no compound numbers in any crop; no species-naming convention, see notes)
- compound_label_color: #000000
- compound_label_italic_suffix: None
- yield_placement: None
- yield_format: None
- conditions_split: None
- substrate_layout: inline_plus
- abbreviate_groups: None
- aromatic_rings: None (no aromatic ring in the reaction crops; pyridine elsewhere in the book is drawn Kekule with explicit C and H)
- new_bond_color: None (the new peptide bond is dark red in crop 09 only)
- substrate_colors: None
- highlight_fill: None
- reagent_text_color: #000000
- arrow_style: plain
- show_plus_sign: True

## Signature features

- short plain arrows (about 2.5 bond lengths) with open V heads, not filled (crops 03, 09)
- species never numbered (crops 03, 09); crop 03 gives no species names and crop 09 names only the groups and the process, in plain sans-serif words
- atoms or groups that change drawn in dark red #901800 (crop 09); new bond in the product drawn in the same red
- functional groups framed by dashed lime-green #7CE400 outline boxes with plain side labels (crop 09)
- a curved arrow leaving the main arrow to show the lost by-product (H2O in red) (crop 09)

## Figure types

### reaction_scheme

Conventions:

- yield_format: None
- selectivity_format: None
- highlight_fill: None
- variation_color: #901800

Signature features:

- dashed lime-green #7CE400 outline boxes around functional groups, labels outside the box (crop 09)
- reacting atoms (OH, H), lost H2O and the new peptide bond in dark red #901800 (crop 09)
- process name (Condensation reaction) beside a vertical arrow (crop 09)

Crops: evidence/openstax_chemistry-09.png

Notes: rests on crop 09 alone and is unambiguous there: the changed atoms, the new bond and the lost H2O are all #901800; crop 03 is a mechanism with CPK ball models and is listed under mechanism

### energy_profile

Conventions:

- energy_unit: None
- energy_label: None
- level_style: smooth_curve
- pathway_colors: ['#BC4428', '#8894C8']
- ts_marker: none
- intermediate_label_style: none

Signature features:

- smooth curves on unnumbered axes with arrowheads; axis titles Energy and Extent of reaction in bold Arial
- uncatalyzed path red (#BC4428 in crop 01, #BC2404 in crop 02), catalyzed path blue (#8894C8 in crop 01, #4060F4 in crop 02)
- Ea as vertical double-headed arrows (crop 01 only): the catalysed arrow is red and the uncatalysed arrow black
- Reactants, Products and Transition state as plain text with no leader line; thin leader lines only on the Activation energy labels (crop 01) and on the Uncatalyzed pathway and Catalyzed pathway labels (crop 02)
- a thin reference line at the reactant energy and a double-headed ΔH arrow labelled ΔH < 0 exothermic (crop 01 only)
- the catalysed curve has darker blue (#4D68AF) flat ends at the reactant and product levels (crop 01 only)

Crops: evidence/openstax_chemistry-01.png, evidence/openstax_chemistry-02.png

Notes: no units or energy values on either crop; the red/blue pairing agrees but the exact shades differ between figures; Ea arrows and the Transition state label are in crop 01 only; top-level substrate_layout and show_plus_sign describe reaction schemes and are not applied here, since crop 01 stacks its reactant formulas (H2C=CH2 over H2) with no plus sign

### mechanism

Conventions:

- curved_arrow_color: None
- curved_arrow_weight: None
- show_lone_pairs: None
- formal_charge_style: None
- intermediate_label_style: none
- ts_marker: none
- highlight_fill: None

Signature features:

- elementary steps drawn with space-filling ball models in CPK colours (O red, N blue, C dark grey) with white element letters
- activated complex labelled Transition state in small plain text, no brackets or double dagger

Crops: evidence/openstax_chemistry-03.png

Notes: rests on one crop; the CC BY Chemistry book has no curved-arrow mechanism figures (arrow pushing is in OpenStax Organic Chemistry, which is CC BY-NC-SA and was not used)

### coordination_complex

Conventions:

- dative_bond_style: line
- metal_color: None
- highlight_fill: None
- formal_charge_style: plain

Signature features:

- octahedra drawn with plain axial lines, bold wedges to the front and hashed wedges to the back
- complex ion in square brackets with the charge as a plain superscript at the top right (crop 04); the neutral EDTA chelate in crop 06 has no brackets
- in the EDTA figure the metal and its six donor bonds are red-brown #983820, ligand black

Crops: evidence/openstax_chemistry-04.png, evidence/openstax_chemistry-06.png

Notes: metal_color null: black in crop 04, red-brown in crop 06; the square-bracket rule is from crop 04 only

### stereo_model

Conventions:

- model_style: None
- ts_marker: None
- highlight_fill: None
- variation_color: #983820

Signature features:

- flat wedge-and-hash projections of octahedra with no perspective (crops 04, 05)
- enantiomers drawn as mirror images separated by a vertical dashed mirror line (crop 05)
- cis/trans isomers side by side with cis and trans in italic (crops 04, 08)
- line formula stacked over ball-and-stick and space-filling models of the same molecule (crop 08)
- the groups whose arrangement differs coloured red-brown #983820 (crop 08)

Crops: evidence/openstax_chemistry-04.png, evidence/openstax_chemistry-05.png, evidence/openstax_chemistry-08.png

Notes: model_style null: crops 04 and 05 are flat projections with plain lines, bold and hashed wedges, which no listed style covers; only crop 08 shows ball-and-stick and space-filling models, so perspective_3d would rest on one crop against two. No chair or Newman projections in the CC BY editions' figures checked (chapters 12, 19, 20); variation_color from crop 08 only

### structure_panel

Conventions:

- highlight_fill: None
- variation_color: None
- intermediate_label_style: none

Signature features:

- one molecule shown in several notations side by side (expanded, condensed, skeletal), each captioned underneath in plain Arial (crop 07)
- expanded formulas with every C and H written and bonds at 90 degrees (crop 07)

Crops: evidence/openstax_chemistry-07.png

Notes: rests on crop 07 alone. variation_color null: all black in crop 07. Crop 08 shows three different butenes (1-butene, cis- and trans-2-butene), so it is listed under stereo_model and not here

## Evidence crops

- evidence/openstax_chemistry-01.png: Figure 12.21, Flowers, Theopold, Langley, Robinson et al., OpenStax Chemistry 2015
- evidence/openstax_chemistry-02.png: Figure 12.22, Flowers, Theopold, Langley, Robinson et al., OpenStax Chemistry 2015
- evidence/openstax_chemistry-03.png: Figure 12.19, Flowers, Theopold, Langley, Robinson et al., OpenStax Chemistry 2015
- evidence/openstax_chemistry-04.png: Figure 19.21, Flowers, Theopold, Langley, Robinson et al., OpenStax Chemistry 2015
- evidence/openstax_chemistry-05.png: Figure 19.23, Flowers, Theopold, Langley, Robinson et al., OpenStax Chemistry 2015
- evidence/openstax_chemistry-06.png: Figure 19.30, Flowers, Theopold, Langley, Robinson et al., OpenStax Chemistry 2015
- evidence/openstax_chemistry-07.png: Figure 20.3, Flowers, Theopold, Langley, Robinson et al., OpenStax Chemistry 2015
- evidence/openstax_chemistry-08.png: Figure 20.10, Flowers, Theopold, Langley, Robinson et al., OpenStax Chemistry 2015
- evidence/openstax_chemistry-09.png: Figure 20.20, Flowers, Theopold, Langley, Robinson et al., OpenStax Chemistry 2015
