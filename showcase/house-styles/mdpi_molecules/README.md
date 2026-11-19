# mdpi_molecules

Reaction-scheme house style of Molecules (MDPI), measured from open-access figures. Base preset: acs1996.

## Sources

- Wu et al., Molecules 2024 (Nickel-catalyzed reductive cyanation of aryl halides and epoxides with cyanogen bromide). DOI 10.3390/molecules29246016. Licence CC BY 4.0.
- Wünsch et al., Molecules 2025 (Structure-activity relationship studies of tetracyclic pyrrolocarbazoles inhibiting heterotetrameric CK2). DOI 10.3390/molecules30010063. Licence CC BY 4.0.
- Sun et al., Molecules 2024 (Isolation and structure elucidation of new metabolites from the Mariana-Trench-associated fungus Aspergillus sp. SY2601). DOI 10.3390/molecules29020459. Licence CC BY 4.0.

## Measurements

- Bond length / atom-label cap height: 2.0 (crop 02 gives 2.07, crop 06 gives 2.02; crop 03 gives 1.75)
- Line width / bond length: 0.042 (crop 06 gives 0.042, crop 03 gives 0.040; crop 02 gives 0.076)
- Bold wedge width / bond length: 0.13 (midpoint of crop 03 at 0.12 and crop 06 at 0.15; no majority between the two)
- Arrow length / bond length: None

## Conventions

- compound_label_face: bold
- compound_label_color: #000000
- compound_label_italic_suffix: False
- yield_placement: None (only crop 03 gives yields: the yield follows the label after a comma with the halide in parentheses ("2b, 89% (X = I)"), and a second yield for the other halide stacks under the first (2e: 90% (X = I) over 47% (X = Br)); one scheme crop only, so yield_placement stays null)
- yield_format: None (only crop 03 gives yields, so the two-crop rule is not met; the substrate_scope section keeps {value}%)
- conditions_split: reagents_above_solvent_below (crop 03 catalyst above, reductant/solvent/temperature below; crop 01 catalyst above, reductant below; crop 02 uses step letters)
- substrate_layout: inline_plus
- abbreviate_groups: None (null: Ph is written in one scheme crop only (03, the N-phenyl of 2d'; crop 01 writes the aryl as Ar); CO2Et is written in one scheme crop only (02) and in the SAR table (05, not a scheme); the two-crop rule is not met)
- aromatic_rings: kekule
- new_bond_color: #FF0000
- substrate_colors: None
- highlight_fill: None (teal #BBFDF4 section bars in crop 01 only)
- reagent_text_color: None (null: crop 01 writes the metal reductant (Zn or Mn) in maroon (about #74002E) with Ni in black; crop 03 writes its Zn reagent in black; the crops disagree)
- arrow_style: plain
- show_plus_sign: True

## Signature features

- introduced group written as a bold blue #0000FF label (CN) on a red #FF0000 bold new bond (crops 01, 03)
- methoxy on the trimethoxyphenyl written as H3CO / OCH3 rather than MeO (crops 02, 05); crop 03 writes the para-methoxy of 2g as MeO
- compound labels bold, slightly smaller than atom labels (cap height about 0.85 of atom labels)

## Figure types

### reaction_scheme

Conventions:

- yield_format: None
- selectivity_format: None
- highlight_fill: None
- variation_color: #0000FF

Signature features:

- introduced group in bold blue #0000FF, new bond red #FF0000
- thin grey #BDBDBD frame around the scheme in crop 01

Crops: evidence/mdpi_molecules-01.png.

Notes: one crop; frame and teal section bars are author choices

### total_synthesis

Conventions:

- step_label_style: letter_above_arrow
- step_count_shown: False
- yield_format: None
- highlight_fill: None
- variation_color: None

Signature features:

- step letters (a), (b), (c) in parentheses above each arrow, reagents in the caption
- plain black structures, bold compound labels with ": R = H" variations

Crops: evidence/mdpi_molecules-02.png.

Notes: one crop (02); the step letters sit above each arrow, which is letter_above_arrow

### substrate_scope

Conventions:

- scope_layout: grid
- variation_color: #0000FF
- yield_format: {value}%
- selectivity_format: None
- conditions_position: both
- highlight_fill: None

Signature features:

- header reaction above a six-column grid, conditions repeated in the caption
- label then yield on one line: "2b, 89% (X = I)"
- a second yield for the other halide stacked under the first (2e, 2w, 2a')
- new C-CN bond red #FF0000 in every product, CN label bold blue #0000FF
- thin grey #BDBDBD frame around the scheme (top and bottom edges in crop 03)
- full-width black rule under the header reaction
- bold-italic note after the compound number on some entries (2f', from cholesterol, 32%; 2g', from DL-Menthol, 81%; 2i', CF102 intermediate, 75%; 2j', Fulvestrant intermediate, 67%)

Crops: evidence/mdpi_molecules-03.png.

Notes: one crop; the crop is cut at the left edge, so the six-column count is not confirmed (at least five columns are visible); yield_format {value}% leaves out the halide qualifier (X = I) or (X = Br) that every yield carries

### catalytic_cycle

Conventions:

- cycle_shape: circle
- cycle_arrow_color: #000000
- catalyst_color: None
- center_label: False
- step_names: False
- intermediate_label_style: bold_letter
- curved_arrow_color: #000000

Signature features:

- intermediates named by bold blue #0000FF capital letters below each species
- thin black arcs with small arrowheads; reagents enter on short curved arrows

Crops: evidence/mdpi_molecules-04.png.

Notes: one crop (04); two circular cycles side by side, Ni (A to E) and Mn (F to I), with an epoxide side path (3 to 6) and a rearrangement to 4

### sar_table

Conventions:

- table_style: horizontal_rules
- activity_format: {mean} ± {sd}
- variation_color: None
- highlight_fill: None

Signature features:

- three black horizontal rules, no vertical rules
- core structures drawn above the table with R and R' positions
- cyclic or N-heteroaryl R groups drawn as small structures in the R column (rows 15 to 17); other R groups written as text (OEt, NHCH3, NHCH2C6H5, NH(CH2)2-indol-3-yl)

Crops: evidence/mdpi_molecules-05.png.

Notes: one crop; typeset MDPI table (serif body text); activity_format applies to the KD′ column only (mean ± SD in nM); the Ki column holds single values in µM and the test-concentration column is in µM

### structure_panel

Conventions:

- highlight_fill: None
- variation_color: None
- intermediate_label_style: bold_number

Signature features:

- grid of black natural-product structures, no colour
- bold numbers under each structure; a scaffold carrying several R groups shares one caption, e.g. "25. R = alpha-OH; 26. R = beta-OH"

Crops: evidence/mdpi_molecules-06.png.

Notes: one crop

## Evidence crops

- evidence/mdpi_molecules-01.png: Scheme 1, Wu et al., Molecules 2024
- evidence/mdpi_molecules-02.png: Scheme 1, Wünsch et al., Molecules 2025
- evidence/mdpi_molecules-03.png: Scheme 2, Wu et al., Molecules 2024
- evidence/mdpi_molecules-04.png: Scheme 6, Wu et al., Molecules 2024
- evidence/mdpi_molecules-05.png: Table 1, Wünsch et al., Molecules 2025
- evidence/mdpi_molecules-06.png: Figure 1, Sun et al., Molecules 2024
