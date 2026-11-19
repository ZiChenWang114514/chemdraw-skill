# org_lett

House style of Organic Letters (ACS), measured from open-access (CC BY 4.0) figures. Base preset: acs1996.

## Sources

- Oestreich et al., Org. Lett. 2025, 27, 3686 (One-pot sequential alcohol activation and nickel-catalyzed cross-electrophile coupling with chlorosilanes). DOI 10.1021/acs.orglett.5c00830. Licence CC BY 4.0.
- Ma et al., Org. Lett. 2025, 27, 4732 (Transition-metal free photocatalytic synthesis of acylsulfonamides). DOI 10.1021/acs.orglett.5c01129. Licence CC BY 4.0.
- Akiyama et al., Org. Lett. 2025, 27, 6204 (Chiral phosphoric acid-catalyzed enantioselective Pictet-Spengler reaction for CF3-substituted tetrahydro-beta-carbolines). DOI 10.1021/acs.orglett.5c01864. Licence CC BY 4.0.
- Dell'Amico et al., Org. Lett. 2025 (Enantioselective organophotocatalytic alpha-functionalization of aldehydes with N-lactam radicals). DOI 10.1021/acs.orglett.5c02365. Licence CC BY 4.0.

## Measurements

- Bond length / atom-label cap height: 2.2
- Line width / bond length: 0.065
- Bold wedge width / bond length: 0.2
- Arrow length / bond length: 6.5 (median of eight crops, spread 3.3 to 11.0; see Notes below the conventions)

## Conventions

- compound_label_face: bold
- compound_label_color: #000000
- compound_label_italic_suffix: False
- yield_placement: under_product_label
- yield_format: {value}%
- conditions_split: reagents_above_solvent_below
- substrate_layout: inline_plus
- abbreviate_groups: ['Me', 'Ph', 'OMe', 'Bn', 'Boc', 'OAc', 'CF3', 'tBu']
- aromatic_rings: kekule
- new_bond_color: None
- substrate_colors: None
- highlight_fill: None
- reagent_text_color: #000000
- arrow_style: plain
- show_plus_sign: True
- yield_separator: , 

Notes: yield_placement under_product_label in crops 08 and 09 (yield and ee on the line under the bold label); crop 07 writes 7aa: 70% on one line. new_bond_color and substrate_colors null: the blue #0336FF silyl fragment with a thick blue new C-Si bond (crops 03, 06, 07) comes from one paper only; crops 04 and 09 are all black. Reagents above and solvent/temperature below the arrow in crops 01, 04, 06. Light sources written in blue text (Blue LEDs, #0C11FF) in crop 08 only.

Notes on the top-level conventions (where crops disagree, the value kept is the one most crops support):

- conditions_split: Crops 02 and 04 put reagents above the arrow and solvent and temperature below. Crops 01 and 06 are two-step schemes that split by step (crop 01: NMP and r.t. 1 h above, NiBr2 diglyme, n-Bu2phen, Mn and r.t. 23 h below), so the rule holds for single-step schemes only.
- substrate_layout: Inline in crops 02, 04 and 05. Crop 03 shows the general alcohol and chlorosilane pair stacked, with the plus sign between them. Crop 01 places the chlorosilane 2a under the start of the arrow as a reagent, with no plus sign.
- show_plus_sign: Plus sign shown in crops 02, 04, 05 and 08. Crop 01 has none because 2a is a reagent under the arrow.
- yield_placement: under_product_label in crops 06 (under the product), 08, 09 and 10: yield and ee on the line under the label. Crop 04 has no product label and sets '92%, 18% ee' directly under the structure. Crop 07 writes 'label: yield' on the label line (7aa: 70%).
- yield_format: {value}% in crops 04, 06, 07, 08 and 09. Crop 10 writes '24 % Yield' on its own line under the label; the majority form is kept.
- yield_separator: ', ' between yield and ee in crops 04 and 08 ('92%, 18% ee', '70%, 89% ee'). Crop 07's colon sits between the label and a yield with no ee, so it is a label separator, not this one.
- reagent_text_color: Black in crops 01, 02 and 04 and in most of crop 06. Exceptions: the introduced reagent Mn in crop 06 is blue, and the light source (Blue LEDs) in crop 08 is blue. Black is kept as the majority colour.
- arrow_length_over_bond_length: Crops disagree widely: 3.3 (crop 09), 4.9 (01), 5.6 (04), 6.25 (06), 6.7 (02), 9.0 (03), 10.3 (07), 11.0 (08). The median of these eight, 6.5, is kept; 7.6 lies within one unit of crop 02 only.
- abbreviate_groups: Me is labelled on silicon (crop 01) and on aryl and alkyl ends (crop 07); the terminal CH3 of ethyl and methyl groups stays skeletal (crops 09 and 10). OMe is labelled in crops 07 and 08; crop 02 draws the methoxy group skeletally. TIPS and OEt are labelled in crop 04 but are not in the abbreviation table, so they cannot be listed.
- substrate_colors: Null. Crop 02 (Ma et al.) colours 1a slate and 2a dark red; crops 03, 06 and 07 (Oestreich et al.) colour the silyl fragment blue. No colour list is shared across papers.
- new_bond_color: Null. The blue new C-Si bond in crops 03, 06 and 07 comes from one paper (Oestreich et al.); crops 04 and 09 are all black.

## Evidence crops

- evidence/org_lett-01.png: Table 1 (PDF page 2, 300 dpi), Oestreich et al., Org. Lett. 2025, 27, 3686
- evidence/org_lett-02.png: Table 1 (PDF page 1, 300 dpi), Ma et al., Org. Lett. 2025, 27, 4732
- evidence/org_lett-03.png: Scheme 1, Oestreich et al., Org. Lett. 2025, 27, 3686
- evidence/org_lett-04.png: Scheme 1, Akiyama et al., Org. Lett. 2025, 27, 6204
- evidence/org_lett-05.png: Graphical abstract (TOC), Dell'Amico et al., Org. Lett. 2025
- evidence/org_lett-06.png: Abstract graphic (PDF page 1, 300 dpi), Oestreich et al., Org. Lett. 2025, 27, 3686
- evidence/org_lett-07.png: Scheme 4 (top rows), Oestreich et al., Org. Lett. 2025, 27, 3686
- evidence/org_lett-08.png: Figure 3 (reaction scope), Dell'Amico et al., Org. Lett. 2025
- evidence/org_lett-09.png: Scheme 3 (derivatization of 4ac), Akiyama et al., Org. Lett. 2025, 27, 6204
- evidence/org_lett-10.png: Figure 5 (telescoped flow synthesis), Dell'Amico et al., Org. Lett. 2025

## Figure types

### optimization_table

Conventions:

- table_style: none
- entry_highlight: none
- footnote_style: superscript_letters
- yield_format: {value}
- selectivity_format: None

Signature features:

- reaction scheme drawn above the table body; table text in the journal serif (Times-like), scheme text in Arial
- no rules: a filled light grey header band (#E6E6E6) over the column heads, with no horizontal rules and no vertical lines (crops 01, 02)
- yield column header carries the footnote letter and unit, yield^b (%); cells give bare numbers, isolated yield in parentheses with its own letter, 94 (91^c)
- footnote letters are italic superscripts attached to entries or cells (7^c, ND^d)
- the best entry is not bold, shaded or boxed in either table; in crop 01 it is entry 1 'none' of a variation-from-standard table
- in crop 01 reagent structures sit in a grey box #F1F2F1 between scheme and table

Crops: evidence/org_lett-01.png, evidence/org_lett-02.png

Notes: Crops 01 and 02 agree: no highlighted best entry, no rules, header row filled #E6E6E6. table_style is none because the value set has no band option. selectivity_format null: no ee column in these crops. Org. Lett. tables are typeset text, so they were cropped from the article PDF.

### concept_panel

Conventions:

- panel_label_style: parenthesised_lowercase
- comparison_layout: stacked_rows
- this_work_color: None
- background_fill: None
- highlight_fill: None
- variation_color: None

Signature features:

- previous approaches and this work as stacked rows, this work last
- this work flagged by text only: bold italic 'this work' under the arrow (crop 03) or bold 'Present work:' above the row (crop 04); no coloured box
- panel letters in parentheses (a), (b), (c) at the right end of each row in crop 04; crop 03 uses bold italic sub-panel titles instead
- sub-panels separated by a thin black full-width rule (crop 03)

Crops: evidence/org_lett-03.png, evidence/org_lett-04.png

Notes: panel_label_style rests on crop 04. this_work_color null: black in crop 04, the method's blue silyl colour in crop 03. Crop 04 writes yield and ee directly under each structure as '81%, 86% ee'. This section takes no yield or selectivity convention, so that format is recorded in the top-level notes (yield_format, yield_separator).

### graphical_abstract

Conventions:

- background_fill: None
- highlight_fill: #DFB3FE
- variation_color: None
- this_work_color: None

Signature features:

- light source as a blue #0B0DFE ring with a lamp icon sitting on the reaction arrow (crop 05)
- catalysts as two interlocking arc arrows in mint #55FFA9 and dark green #066A34 around a bold PC (crop 05)
- key ring filled lilac #DFB3FE (crop 05)
- check-mark bullets with bold dark green #066A34 claims (crop 05)
- crop 06: a one-line scheme with the reacting group red #FF0000 and the introduced group blue #0080FF, '48 examples, up to 98% yield' under the product

Crops: evidence/org_lett-05.png, evidence/org_lett-06.png

Notes: Two TOC styles: free-form graphic (crop 05) and a single scheme (crop 06). highlight_fill rests on crop 05 only. The blue band in crop 06 is the journal's abstract box, not part of the graphic. draw_figure reads only the top-level highlight_fill, so the lilac ring is reproduced per species rather than from this section.

### substrate_scope

Conventions:

- scope_layout: grid
- variation_color: None
- yield_format: {value}%
- selectivity_format: {value}% ee
- conditions_position: scheme_on_top
- highlight_fill: None

Signature features:

- one reaction arrow with conditions above and below, products in a grid underneath
- bold product label with 'yield, ee' on the line beneath (70%, 89% ee) or label: yield on one line (7aa: 70%)
- crop 07: generic substrate as a dark green #036500 pill with red #FF0305 OH, introduced group blue #0336FF, italic 'from Drug' line above each label
- footnote marker as an asterisk with its explanation centred under the grid (crop 08)

Crops: evidence/org_lett-07.png, evidence/org_lett-08.png

Notes: variation_color null: blue in crop 07, black structures in crop 08. selectivity_format from crop 08. conditions_position: crop 08 has one arrow with the conditions above and below it and 1 + 2 reactants; the reactant row is not recorded in this card.

### derivatization

Conventions:

- derivatization_layout: radial
- yield_format: {value}%
- highlight_fill: None
- variation_color: None

Signature features:

- parent 4ac top left: an arrow to the right gives 7 (top middle) and an arrow down gives 6; 7 is the hub, with arrows leaving it to the right (to 9), down (to 8) and diagonally down-right (to 10)
- reagents written beside each arrow, two steps as 1) 2)
- bold compound number with 'yield, ee' below every derivative, (2 steps) in parentheses
- all black, no colour or boxes

Crops: evidence/org_lett-09.png

Notes: One crop (Akiyama et al., Scheme 3). Radial kept: the arrows fan out from 7, the middle hub.

### setup_diagram

Conventions:

- background_fill: #D7FFF6
- highlight_fill: None

Signature features:

- telescoped flow route split into horizontal pastel bands, mint #D7FFF6, light blue #C0EFFF and lilac #DBD4FE, each with a bold coloured title
- coil reactors drawn as stacked rings with residence time and temperature in bold italic
- reagent feeds in dashed boxes joining the line at small T-pieces

Crops: evidence/org_lett-10.png

Notes: Bonus type; one crop; background_fill is the first band.
