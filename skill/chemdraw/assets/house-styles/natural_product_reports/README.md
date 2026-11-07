# natural_product_reports

House style of Natural Product Reports (RSC), measured from open-access figures. Base preset: rsc.

## Sources

- Williams et al., Nat. Prod. Rep. 2022 (Maleidride biosynthesis: construction of dimeric anhydrides). DOI 10.1039/d2np00041e. Licence CC BY 3.0.
- Miller et al., Nat. Prod. Rep. 2024 (Purine nucleoside antibiotics: recent synthetic advances harnessing chemistry and biology). DOI 10.1039/d3np00051f. Licence CC BY 3.0.
- Wang, Tang et al., Nat. Prod. Rep. 2023 (Dehydroamino acid residues in bioactive natural products). DOI 10.1039/d3np00041a. Licence CC BY 3.0.
- Tepe et al., Nat. Prod. Rep. 2024 (Advances in the total synthesis of bis- and tris-indole alkaloids containing N-heterocyclic linker moieties). DOI 10.1039/d4np00012a. Licence CC BY 3.0.

## Measurements

- Bond length / atom-label cap height: 2.6 (crops 01, 04, 06 give 2.9, about 2.4 and 2.3; all within 0.3)
- Line width / bond length: 0.05 (crops 01, 06 give 0.05 and 0.04; crop 03 about 0.07, rough)
- Bold wedge width / bond length: 0.25 (crop 01 only)
- Arrow length / bond length: 4.8 (crops 01, 03, 04, 06 give 4.35, 4.7, about 4.8 and 5.4; three of four within 0.5)

## Conventions

These apply to reaction schemes (crops 01, 06, 07). A value needs two or more agreeing crops, otherwise it is null.

- compound_label_face: bold
- compound_label_color: #000000
- compound_label_italic_suffix: False
- yield_placement: under_arrow (crops 06, 07; the 25% yield in crop 06 sits beside the shaft under the BH3-THF label, the one exception)
- yield_format: {value}%
- conditions_split: None (biosynthetic steps put the enzyme above and cofactors below (crop 01); synthetic steps number all reagents above and below without a solvent split (crops 06, 07))
- substrate_layout: None
- abbreviate_groups: None (Me appears only in crop 06 and CO2Et only in crop 07; crop 01 draws the heptyl chain as a plain zigzag)
- aromatic_rings: kekule
- new_bond_color: None (the red #D8151F on newly installed oxygen atoms appears only in crop 01; it is recorded under biosynthesis)
- substrate_colors: None
- highlight_fill: None
- reagent_text_color: #000000 (crops 01, 06, 07; the blue enzyme names of biosynthesis crops are a separate style)
- arrow_style: plain
- show_plus_sign: None (no two-substrate step in the reaction-scheme crops)

## Signature features

- bold compound numbers under each structure, at the lower left in crop 01 (crops 01, 06, 07); after the trivial name in crops 05 and 08
- yields in bold under the arrow (crops 06, 07); numbered reagent lines 1. ..., 2. ... only where one arrow carries two operations (crops 06, 07)
- final natural-product target named and numbered inside a thin rounded rectangle, e.g. Dragmacidin B (111b) (crop 06; the final compound of crop 07 is not boxed)
- intermediates that are not isolated drawn in square brackets (crop 07)
- thin plain lines, Kekule rings, Arial-like sans-serif labels

## Figure types

### biosynthesis

Conventions:

- enzyme_label_style: boxed (crops 03, 04: dark-blue rounded box; crop 01 sets the enzyme names in bold italic blue above the arrow)
- highlight_fill: None
- variation_color: #074383 (crops 03, 04; crop 01 colours the new oxygen atoms red #D8151F, so the spread is recorded here)
- intermediate_label_style: bold_number

Signature features:

- enzyme name above the reaction arrow, in a dark-blue rounded box in crops 03 and 04 and in bold italic blue text without a box in crop 01
- cofactors (Fe2+, alpha-KG, O2) written under the arrow, stacked in three steps and on one line in two (crop 01); by-products (succinate and CO2 in crop 01, H2O in crop 04) leave on a small curved arrow (crops 01, 04)
- atoms changed by the enzyme coloured: red #D8151F for the new oxygen atoms in crop 01, dark blue in crops 03 and 04 (added sugar, new exocyclic alkene)
- intermediates labelled with bold numbers (crop 01); in crops 03 and 04 the trivial name of the changed compound is in italic dark blue #074383 (crop 03: compound 44 only; crop 04: both compound names), with the number in parentheses after it

Crops: evidence/natural_product_reports-01.png, evidence/natural_product_reports-03.png, evidence/natural_product_reports-04.png

Notes: enzyme_label_style boxed: crops 03 and 04 (dark-blue rounded box with blue text); crop 01, from another paper, sets the enzyme names in bold italic blue above the arrow with no box. variation_color takes the value shared by most crops: #074383 in crops 03 and 04 (one paper); crop 01 (another paper) colours the new oxygen atoms red #D8151F. The drawing tools do not apply biosynthesis conventions.

### biomolecule

Conventions:

- sugar_projection: None
- peptide_style: None
- highlight_fill: None
- variation_color: None

Signature features:

- sugars as chairs (crop 03) or Haworth-like furanoses with bold front bonds (crop 04)
- ribosomal peptides as chains of grey circles with three-letter codes, modified residues coloured magenta #FB1AE0 and blue, thioether bridges as coloured lines (crop 05)
- nonribosomal lipopeptides as full skeletal structures with the dehydro residue in red #FC332F (crop 08)

Crops: evidence/natural_product_reports-03.png, evidence/natural_product_reports-04.png, evidence/natural_product_reports-05.png, evidence/natural_product_reports-08.png

Notes: sugar_projection and peptide_style vary with the molecule; both forms occur, so None. variation_color None: the coloured atoms differ by purpose and crop (dark blue added sugar in crops 03 and 04, magenta modified residues in crop 05, red dehydro residue in crop 08), so no value is shared by most crops.

### structure_panel

Conventions:

- highlight_fill: #C9C9FD
- variation_color: None
- intermediate_label_style: bold_number

Signature features:

- core families in thin black outlined boxes, one box per family, with bold headings for maleidrides and nonadrides and regular headings for octadrides and heptadrides; italic sub-class lines (head-to-head, head-to-tail, head-to-side) where a family has one (crop 02)
- monomer-derived bonds drawn bold (the anhydride C=C and the adjacent ring bonds) while the rest of each ring is plain (crop 02)
- a lavender #C9C9FD fill sits behind the maleidride and nonadride groups only; the octadride and heptadride boxes stand on white (crop 02)
- each natural product: name with a bold number, organism in italic under it, activity in plain text below (crops 05, 08)

Crops: evidence/natural_product_reports-02.png, evidence/natural_product_reports-05.png, evidence/natural_product_reports-08.png

Notes: highlight_fill rests on crop 02 only (exact flat pixels #C9C9FD in that crop); crops 05 and 08 have no fill. intermediate_label_style bold_number rests on the bold compound numbers of crops 05 and 08; crop 02 has no numbers. variation_color None: crop 08 colours the dehydro residue red #FC332F and crop 05 colours modified residues magenta, so no value is shared by most crops.

### total_synthesis

Conventions:

- step_label_style: numbered
- step_count_shown: None
- yield_format: {value}%
- highlight_fill: None
- variation_color: None

Signature features:

- two-operation arrows number each operation 1. ..., 2. ... (crops 06, 07); single-reagent arrows carry unnumbered reagent text (crops 06, 07); yields in bold under the arrow (crops 06, 07)
- final target in a thin rounded rectangle with its name and bold number (crop 06 only; the final compound of crop 07 is not boxed)
- long route folded into a U, with one arrow running right to left (crop 07); unisolated intermediates in square brackets (crop 07)

Crops: evidence/natural_product_reports-06.png, evidence/natural_product_reports-07.png

Notes: two crops from one review.

## Evidence crops

- evidence/natural_product_reports-01.png: Scheme 24, Williams et al., Nat. Prod. Rep. 2022
- evidence/natural_product_reports-02.png: Fig. 1a, Williams et al., Nat. Prod. Rep. 2022
- evidence/natural_product_reports-03.png: Fig. 6, Miller et al., Nat. Prod. Rep. 2024
- evidence/natural_product_reports-04.png: Fig. 3, Miller et al., Nat. Prod. Rep. 2024
- evidence/natural_product_reports-05.png: Fig. 5, Wang, Tang et al., Nat. Prod. Rep. 2023
- evidence/natural_product_reports-06.png: Scheme 25, Tepe et al., Nat. Prod. Rep. 2024
- evidence/natural_product_reports-07.png: Scheme 10, Tepe et al., Nat. Prod. Rep. 2024
- evidence/natural_product_reports-08.png: Fig. 14, Wang, Tang et al., Nat. Prod. Rep. 2023
