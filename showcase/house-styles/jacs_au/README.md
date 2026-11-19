# jacs_au

House style of JACS Au (ACS), measured from open-access (CC BY 4.0) figures. Base preset: acs1996.

## Sources

- Gilmour et al., JACS Au 2025 (Chloroalkylation of unactivated alkenes via a cobalt-mediated radical ligand transfer). DOI 10.1021/jacsau.5c01211. Licence CC BY 4.0.
- Ravelli et al., JACS Au 2025 (A decarbonylative strategy to enhance efficiency and regioselectivity in photocatalyzed HAT). DOI 10.1021/jacsau.5c00530. Licence CC BY 4.0.
- Steffen et al., JACS Au 2025 (Photoactive neutral three-coordinate Cu(I) complexes of anionic N-heterocyclic carbenes). DOI 10.1021/jacsau.5c00357. Licence CC BY 4.0.
- Landfester et al., JACS Au 2025 (Photoactive PFA coating through fluorophilic interactions for continuous flow photochemistry). DOI 10.1021/jacsau.5c00804. Licence CC BY 4.0.

## Measurements

- Bond length / atom-label cap height: 2.06
- Line width / bond length: 0.09
- Bold wedge width / bond length: None
- Arrow length / bond length: 3.2

## Conventions

- compound_label_face: bold
- compound_label_color: #000000
- compound_label_italic_suffix: False
- yield_placement: None
- yield_format: None
- conditions_split: None
- substrate_layout: None
- abbreviate_groups: ['Me', 'Ph', 'tBu', 'CF3', 'NO2', 'CO2Me']
- aromatic_rings: kekule
- new_bond_color: None
- substrate_colors: None
- highlight_fill: None
- reagent_text_color: #000000
- arrow_style: plain
- show_plus_sign: True
- yield_separator: None

Notes: The crops are concept, mechanism and diagram figures; no scope figure was cropped, so yield placement, yield format, conditions split and yield separator are null. substrate_layout is null: crop 02 writes the substrates inline with a plus (panel D), while crop 10 stacks the radical precursor above the alkene with a plus between them, so no two crops agree. new_bond_color is null: only crop 02 draws the newly formed bond (tBu-CH2) in green (#26A83E), and no other crop shows a coloured new bond. reagent_text_color #000000 holds for most reagent text (crops 02 and 05); the exceptions are NaBr in navy (crop 02), the bold red HAT label (crop 09) and the blue Blue LEDs label (crop 08). compound_label_color #000000 holds for crops 05 and 07; C4 is green in crop 03, and crop 04 colours the complex labels C2 to C5 by series. Bold compound labels appear in crops 03 (C4), 05 (t-DCZCB) and 07 (Int-III, CoIII-4(Ag)+, CoIII-5, CoII-6); plain chemical names in crop 03 are not compound labels. Bold intermediate and catalyst-state labels: Int-I and Int-II (crop 01), Int-III and the CoIII and CoII species (crop 07), Ir(III) and Ir(IV) (green) and LnCo (crop 08). arrow_length_over_bond_length 3.2 is the mean of crops 01, 05 and 08 (3.0 to 3.4); crops 02 and 07 give 5.5 and 5.0, so the spread across crops is 3.0 to 5.5. bond_length_over_cap_height 2.06 sits within the 2.0 to 2.2 spread of crops 01, 02, 05, 07 and 08. Halogen atoms drawn as filled discs (Br pink #CC6AE5, Cl blue #4F8EDB) in crops 01, 07, 08, 10, all from one paper. bold_width null: no solid wedge measurable in the cropped regions. measured.label_font is null: no crop measures a font; the Arial label font comes from the acs1996 preset, and the crops read as sans-serif by eye.

## Evidence crops

- evidence/jacs_au-01.png: Figure 1 (A)-(C), Gilmour et al., JACS Au 2025
- evidence/jacs_au-02.png: Figure 1 (A-E), Ravelli et al., JACS Au 2025
- evidence/jacs_au-03.png: Figure 7, Steffen et al., JACS Au 2025
- evidence/jacs_au-04.png: Figure 5 (lower part), Steffen et al., JACS Au 2025
- evidence/jacs_au-05.png: Figure 4, Landfester et al., JACS Au 2025
- evidence/jacs_au-06.png: Figure 1, Landfester et al., JACS Au 2025
- evidence/jacs_au-07.png: Figure 5D (computed mechanism), Gilmour et al., JACS Au 2025
- evidence/jacs_au-08.png: Figure 5A-C, Gilmour et al., JACS Au 2025
- evidence/jacs_au-09.png: Graphical abstract (TOC), Ravelli et al., JACS Au 2025
- evidence/jacs_au-10.png: Graphical abstract (TOC), Gilmour et al., JACS Au 2025

## Figure types

### concept_panel

Conventions:

- panel_label_style: None
- comparison_layout: stacked_rows
- this_work_color: None
- background_fill: #FFFFFF
- highlight_fill: None
- variation_color: None

Signature features:

- multi-panel concept figure: background and prior art first, this work last as its own panel ((C) Our Platform in crop 01, E This work in crop 02)
- bold sans-serif panel titles with the panel letter; crop 01 sets them into a thin grey #B1BDBD frame line, crop 02 as free headings
- abstract substituents as coloured discs (orange #FFAA73, blue #7CBEF0, green) and halogens as filled discs (Br pink #CC6AE5, Cl blue #4F8EDB)
- grey boxes #DEE2E3 hold bullet-point lists with square bullets (crop 02)
- the transferred H atom in red #FE0000 (crop 02)
- radicals drawn as blue orbital lobes on the radical carbon (crop 01)

Crops: evidence/jacs_au-01.png, evidence/jacs_au-02.png

Notes: panel_label_style null: bold (A) in crop 01, bare bold A in crop 02, neither enum value fits. background_fill is white in crops 01 and 02; the #DEE2E3 grey only fills boxes inside the panels (the TAG bullet box and the photocatalyst box in crop 02).

### photophysical_diagram

Conventions:

- energy_unit: eV
- level_style: None
- pathway_colors: ['#213570', '#369134']

Signature features:

- excited-state (triplet) energies along one horizontal eV axis with grey tick labels, unit written '/ eV' at the axis end
- each compound as a vertical bar capped by filled discs, navy #213570; the new compound highlighted in green #369134 with a bold green label
- orbital energies as coloured dots per compound in boxed panels with an 'Energy / eV' axis (crop 04)

Crops: evidence/jacs_au-03.png, evidence/jacs_au-04.png

Notes: No Jablonski diagram was found in the CC BY JACS Au papers checked; both crops are energy-level diagrams from one paper. level_style null: neither bars with connectors nor a curve. pathway_colors are the crop 03 bar and highlight colours; crop 04 colours orbital dots per complex by series (red, orange, green, navy), which is not a pathway palette, so crop 03 alone sets this value.

### setup_diagram

Conventions:

- background_fill: None
- highlight_fill: #FE0000

Signature features:

- flat schematic flow setup left to right: pump circle with chevron, coil reactor as stacked pale pink rings with an LED head and green light, valve as circled x, waste arrow downward (crop 05)
- conditions in plain text under the reactor, product name bold italic
- reactor types as grey tubes with black end fittings; the authors' reactor ('e) This work') drawn with red #FE0000 tubing and photocatalyst disc, its coil outlined in red (crop 06)
- sub-panel letters bold lowercase with a closing parenthesis, a) to e)
- grey bold 'PFA tubing' label, blue bold polymer formula and bold figure heading (crop 06)

Crops: evidence/jacs_au-05.png, evidence/jacs_au-06.png

Notes: Both crops from one paper; highlight_fill rests on crop 06 only, where the PFA tubing bars and the photocatalyst disc are filled #FE0000 and the coil is outlined; crop 05 has no highlight. No electrochemical cell figure was cropped.

### graphical_abstract

Conventions:

- background_fill: None
- highlight_fill: #DEE2E3
- variation_color: None
- this_work_color: None

Signature features:

- white background, concept scheme reused from Figure 1 rather than a new illustration (compare crop 02 panel C, same paper)
- claims as italic text in a grey bar #DEE2E3 with square bullets (crop 09)
- key concept boxed or circled: black box defining the activating group (crop 09); circle with a beige #DED7A3 shadow and gold-brown #705100 italic title (crop 10)
- catalysts as interlocking circular arrows, halogens as coloured discs (crop 10)
- R groups as coloured discs, light blue #7CBEF0 and orange #FFAA73, a green #26A83E activating-group flag, and thick light grey block arrows for activation and fragmentation (crop 09)

Crops: evidence/jacs_au-09.png, evidence/jacs_au-10.png

Notes: highlight_fill from crop 09 only: the grey claims bar. Crop 10 has no grey fill, which matches this note.

### energy_profile

Conventions:

- energy_unit: kcal/mol
- energy_label: delta_G
- level_style: smooth_curve
- pathway_colors: ['#889897']
- ts_marker: bracket_double_dagger
- intermediate_label_style: None

Signature features:

- one smooth thick grey #889897 curve through all stationary points; the branch is a second grey curve labelled 'barrierless' in italics
- stationary points as small black dots with plain values (-13.9) beside them, 'complex' in grey italics under the value
- no y axis: an up arrow with italic ΔG (kcal·mol-1) at the top right
- transition states drawn in square brackets with double dagger and radical dot
- species drawn along the curve, halogens as pink #CC6AE5 and blue #4F8EDB discs; photoexcitation as a dashed vertical arrow from a navy bulb disc
- blue omega annotations beside the radical species (ω 2.63 eV and 1.07 eV) and a boxed ΔrG = -4.9 side reaction with a 3D structure inset (crop 07)

Crops: evidence/jacs_au-07.png

Notes: One crop, unambiguous. Only one intermediate is named (bold Int-III), so intermediate_label_style is null.

### catalytic_cycle

Conventions:

- cycle_shape: circle
- cycle_arrow_color: #000000
- catalyst_color: None
- center_label: True
- step_names: True
- intermediate_label_style: None
- curved_arrow_color: None
- highlight_fill: None

Signature features:

- two touching circular cycles, photoredox (black arcs) and cobalt (dark maroon arcs)
- cycle name bold italic in the centre of each cycle
- catalyst states in grey square brackets, oxidation states as bold superscript roman numerals, IrIV green
- light step marked by a navy disc with a bulb and blue bold italic 'Blue LEDs'
- grey arc for the competing radical chain; step name RLT bold italic maroon

Crops: evidence/jacs_au-08.png

Notes: Bonus type; one crop. cycle_arrow_color is the photoredox arc colour (black). The cobalt-cycle arcs are dark maroon (about #200008 at the darkest pixels) and the radical-chain arc is grey, so curved_arrow_color stays null.
