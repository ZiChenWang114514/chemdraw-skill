# cell_press_chem

Reaction-scheme house style of the Cell Press chemistry journals (Chem, Chem Catalysis), measured from open-access CC BY figures. Base preset: wiley.

## Sources

- Goldup et al., Chem 2020 (Synthesis of a mechanically planar chiral rotaxane ligand for enantioselective catalysis). DOI 10.1016/j.chempr.2020.02.006. Licence CC BY 4.0.
- Greb et al., Chem 2021 (An isolable, crystalline complex of square-planar silicon(IV)). DOI 10.1016/j.chempr.2021.05.002. Licence CC BY 4.0.
- Smith et al., Chem Catal. 2025 (Photocatalysis as a mechanistic probe for the Staudinger beta-lactam synthesis). DOI 10.1016/j.checat.2025.101493. Licence CC BY 4.0.

## Measurements

- Bond length / atom-label cap height: 2.12 (crop 03 gives 2.12, crop 04 gives 2.11)
- Line width / bond length: 0.08 (crop 03 gives 0.075, crop 04 gives 0.084)
- Bold wedge width / bond length: 0.17 (crop 03 only)
- Arrow length / bond length: 7.5 (crop 03). Crop 01 gives about 4.9 by cap-height scaling, because its bond cannot be measured; the two crops disagree and the crop 03 value is kept.

## Conventions

Top-level conventions are counted over the reaction-type crops 01 to 04 (schemes and the substrate grid). Mechanism, cycle and energy crops 05 to 08 are read in their figure-type sections only.

- compound_label_face: bold
- compound_label_color: #000000
- compound_label_italic_suffix: False. The italic part here is a prefix before the bold number (stereodescriptor in (S,Rmp)-4, crop 01; cis in cis-9, crop 04; syn and anti in syn-1E and anti-1D, crop 05). The schema has no prefix key, so the prefix is recorded in the notes only.
- yield_placement: under_arrow (crops 01 and 02; crop 04 puts the yield under the product label in a grid, and crop 03 shows no yield)
- yield_separator: None
- yield_format: {value}% (crops 01 and 04 have no space; crop 02 writes 78 % with a space, so the majority form is kept)
- conditions_split: None (crop 02 puts the reagent above and rt, solvent and yield below; crop 03 puts catalyst and solvent above and light and time below; crop 01 has no conditions line)
- substrate_layout: None (crop 01 stacks reagents without a plus sign, which neither inline_plus nor stacked_plus describes; crop 03's plus is between products)
- abbreviate_groups: ['Ph']. Ph is contracted in crop 01 (benzyl and P-phenyl labels) and crop 04 (benzoate and cyclopropyl phenyl labels). Crop 03, an author-manuscript figure, draws its N-benzyl phenyl in full. OMe, tBu and CF3 appear as labels only in crop 04, so they are not listed at top level. CN is not drawn in any crop. BzO (crop 07) has no entry in ABBREVIATIONS and cannot be added.
- aromatic_rings: kekule
- new_bond_color: None (dark red only in crop 08, a mechanism figure; core pixels about #890011, one crop)
- substrate_colors: None. Crop 01 colours each component by origin and crop 04 colours fragments of one molecule (benzoate green, cyclopropyl aryl blue). substrate_colors is a list matched to substrates in order, so no list fits. The colouring is in the figure-type signature features.
- highlight_fill: None (the warm grey fill is recorded in the mechanism section)
- reagent_text_color: #000000
- arrow_style: plain. Crops 02 and 03 draw thin arrows; crop 01 draws a heavier shaft (about 3 px) with a large filled head and is the one exception.
- show_plus_sign: None (a plus sign between products appears in crop 03 only)
- figure_sources: crops 03, 05, 06 and 08 come from the PMC author manuscript of the Chem Catalysis paper (NIHMS figures), which keep the authors' artwork; crops 01, 02, 04 and 07 are the journal-published Chem figures.
- base_preset: wiley fixes the bond length (17 pt), the Arial label font and the label size. The measured ratios override the preset's own widths at draw time: its line of 0.75 pt is 0.044 of its bond against the measured 0.08, and its bold width 2.6 pt is 0.15 against the measured 0.17. No preset was checked against the arrow ratio, because presets carry no arrow length.

## Signature features

- panels lettered with a bold sans capital A, B, C (no parentheses) at the top left (crops 02, 05, 06, 07, 08); a plain-weight panel title follows the letter in crops 05, 06 and 08
- compound labels bold with stereo or isomer prefixes in italics, e.g. cis-9, syn-1D, (S)-1 (crops 01, 04, 05)
- warm grey #F0EDE8 fills the small step boxes (ISC, EnT) in crops 05 and 06
- dark red #780001 for mechanistic step names and curved arrows (crop 05); crop 08 uses a dark red panel bullet (about #760809) and a dark red new bond (core #890011), the same family
- sans-serif (Arial or Helvetica) text throughout

## Figure types

### reaction_scheme

Conventions:

- yield_format: {value}%
- selectivity_format: None
- highlight_fill: None
- variation_color: None

Signature features:

- bold panel letter at the top left of each scheme panel (crop 02)
- multistep schemes number the steps (1. AT-CuAAC) with the yield under the arrow (crop 01)
- components colour coded by origin (red #CB181B, green, blue #4068AD) and kept in those colours through the scheme (crop 01)

Crops: evidence/cell_press_chem-01.png, evidence/cell_press_chem-02.png, evidence/cell_press_chem-03.png.

Notes: conditions placement differs between the three crops (see conventions.notes). The yield format is a tie in this section (crop 01 has no space, crop 02 has one); the top-level no-space form is kept. Crop 03 shows no yield.

### substrate_scope

Conventions:

- scope_layout: grid
- variation_color: None
- yield_format: {value}%
- selectivity_format: ({de} de, {ee} ee)
- conditions_position: None
- highlight_fill: None

Signature features:

- bold compound label, then the yield and selectivity below it as 86% (88% de, 57% ee) with italic de and ee (crop 04)
- bold range labels 1b-1j, 2b-2j and 7b-7j under the structures of a single scheme (crop 03)
- fragment colour coding by origin: green ester and enol-ester part #336510, blue aryl group on the cyclopropane #4068AD (crop 04)
- varied position marked by a teal dot #529DBD on the general structure (crop 03)

Crops: evidence/cell_press_chem-03.png, evidence/cell_press_chem-04.png.

Notes: selectivity_format rests on crop 04 alone (one crop, unambiguous; the placeholders are the de and ee values). Crop 03 shows no yield or selectivity; the >20:1 d.r. is written in crop 08, a mechanism figure. scope_layout grid rests on crop 04; crop 03 is a single linear scheme with a range label, which no scope_layout value describes. conditions_position is None: crop 03 puts catalyst and solvent above the arrow and light and time below, while crop 04 gives conditions only in the caption.

### mechanism

Conventions:

- curved_arrow_color: #780001
- curved_arrow_weight: thin
- show_lone_pairs: False
- formal_charge_style: plain
- intermediate_label_style: None
- ts_marker: None
- highlight_fill: #F0EDE8

Signature features:

- dark red curved arrows, thinner than bonds (crops 05, 08)
- step names in dark red #780001 above the arrows and TS names in bold below (crop 05)
- transition state 3 in square brackets with a double dagger and spin multiplicity 3 outside the bracket; intermediates 4 and 5 in square brackets with no mark (crop 08)
- small step boxes (ISC, EnT) filled warm grey #F0EDE8 (crop 05)
- the caption of intermediate 5 is enclosed by a blue #336E90 outline box (crop 08)

Crops: evidence/cell_press_chem-05.png, evidence/cell_press_chem-08.png.

Notes: both crops are from one Chem Catalysis paper. ts_marker and intermediate_label_style are None because the crops disagree: crop 05 writes TS names as plain bold text with no bracket or dagger and letters its species (3A, 3B, 3C); crop 08 brackets its species, puts the dagger on the bracket of 3 only, and numbers them (3, 4, 5). highlight_fill #F0EDE8 rests on crop 05 alone, where it fills the ISC and EnT boxes (577 px). Crop 08 highlights with a blue outline instead; the schema has no key for an outline.

### catalytic_cycle

Conventions:

- cycle_shape: circle
- cycle_arrow_color: #000000
- catalyst_color: None
- center_label: False
- step_names: True
- intermediate_label_style: bold_roman
- curved_arrow_color: None
- highlight_fill: None

Signature features:

- intermediates placed on a circle and joined by thick black curved arrows (crop 07)
- step names in red italics #CB181B beside three of the four arrows (none on the arrow from 7 into I); transition states named in bold, e.g. (TS1) (crop 07)
- intermediates I and II labelled with bold Roman numerals; the third intermediate is unlabelled; empty centre (crop 07)
- photocatalyst cycles drawn as a small side loop of black arcs with the excited states as text labels (crop 05)

Crops: evidence/cell_press_chem-07.png, evidence/cell_press_chem-05.png.

Notes: the full cycle rests on crop 07; crop 05 only shows a small photocatalyst loop. The bold_roman style applies to the labelled intermediates I and II in crop 07.

### energy_profile

Conventions:

- energy_unit: kcal/mol
- energy_label: None
- level_style: smooth_curve
- pathway_colors: ['#000000', '#7A0000', '#0000FE']
- ts_marker: none
- intermediate_label_style: bold_letter

Signature features:

- short blue #116FAF bars at each state joined by smooth black curves; the competing path as a dark red curve
- labels as bold species name with the energy in parentheses, e.g. 3B (-10.4)
- boxed plot with ticks on the left and right edges only (top and bottom edges have none), y axis G_rel (kcal mol-1)
- small EnT box filled warm grey #F0EDE8 beside the vertical EnT arrow
- 1TS-IV and 1TS-V paths drawn as blue #0000FE curves

Crops: evidence/cell_press_chem-06.png.

Notes: rests on one crop. energy_label is None: the axis reads G_rel (relative Gibbs energy, 3A = 0.0), and the schema has no relative-G value; delta_G would misstate the axis. Pathway colours are the black main path, the dark red anti-3TS-I path (darkest pixels #7A0000, antialiased; mode #7C0000) and the blue #0000FE curves (66 exact pixels). Units are written kcal mol-1 (mapped to kcal/mol).

## Evidence crops

- evidence/cell_press_chem-01.png: Scheme 1, Goldup et al., Chem 2020
- evidence/cell_press_chem-02.png: Figure 2A, Greb et al., Chem 2021
- evidence/cell_press_chem-03.png: Figure 3 top, Smith et al., Chem Catal. 2025
- evidence/cell_press_chem-04.png: Figure 3, Goldup et al., Chem 2020
- evidence/cell_press_chem-05.png: Figure 4A, Smith et al., Chem Catal. 2025
- evidence/cell_press_chem-06.png: Figure 4B, Smith et al., Chem Catal. 2025
- evidence/cell_press_chem-07.png: Figure 4A, Goldup et al., Chem 2020
- evidence/cell_press_chem-08.png: Figure 1C, Smith et al., Chem Catal. 2025
