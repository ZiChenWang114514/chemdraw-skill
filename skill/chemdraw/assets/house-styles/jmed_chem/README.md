# jmed_chem

Figure house style of Journal of Medicinal Chemistry (ACS), measured from open-access figures. Base preset: acs1996.

## Sources

- Baldwin, Ward et al., J. Med. Chem. 2025 (Discovery of MDI-114215: a potent and selective LIMK inhibitor to treat fragile X syndrome). DOI 10.1021/acs.jmedchem.4c02694. Licence CC BY 4.0.
- Cottrell et al., J. Med. Chem. 2025 (Discovery of TNG462: a highly potent and selective MTA-cooperative PRMT5 inhibitor). DOI 10.1021/acs.jmedchem.4c03067. Licence CC BY 4.0.

## Measurements

- Bond length / atom-label cap height: 2.25 (seven crops 2.14 to 2.35, median 2.27)
- Line width / bond length: 0.07 (seven crops 0.055 to 0.071, median 0.067)
- Bold wedge width / bond length: None
- Arrow length / bond length: 3.0 (crops 2.7, 3.0 and 4.8; median 3.0)

## Conventions

- compound_label_face: bold (reaction-scheme numbers; structure-panel captions are plain names, see figure_types.structure_panel)
- compound_label_color: #000000
- compound_label_italic_suffix: False
- yield_placement: None (no yields are drawn on the scheme in crops 01 to 03; the footnote lies outside every crop)
- yield_format: None (not on the drawing)
- conditions_split: None (no crop draws reagents or conditions above or below an arrow)
- substrate_layout: inline_plus
- abbreviate_groups: None (under the two-scheme-crop rule: Boc in crop 03 only; CN in scheme crop 02 only, written NC on BMS-986504 in structure-panel crop 04; CF3 in structure-panel crop 04 only). Methyl groups are drawn as plain line ends.
- aromatic_rings: kekule
- new_bond_color: None
- substrate_colors: None
- highlight_fill: None
- reagent_text_color: #000000
- arrow_style: plain
- show_plus_sign: True

## Signature features

- only a lower-case step letter (a, b, c; pairs such as b,c or i,j) above each arrow; reagents, conditions and yields are not drawn on the scheme
- short arrows, about three bond lengths, with a filled triangular head
- bold compound numbers centred under each structure; series given as bold number plus R-group definitions, e.g. 87a: R1 = H, A = C
- multistep routes laid out in rows, branching with vertical and diagonal arrows that also carry only a letter
- black only; no colour, boxes or shading on synthetic schemes

## Figure types

### reaction_scheme

Conventions:

- yield_format: None
- selectivity_format: None
- highlight_fill: None
- variation_color: None

Signature features:

- lower-case letter above the arrow; no reagent, condition or yield text on the drawing
- bold compound number under each structure; series written as 87a: R1 = H, A = C under the generic structure
- black only

Crops: evidence/jmed_chem-01.png, evidence/jmed_chem-02.png

Notes: crops 01 and 02 carry no yields or conditions on the drawing; the footnote text that could carry them lies outside both crops and is not verified. Crop 01 has bold numbers on both branches (14 and 10 on the lower branch).

### total_synthesis

Conventions:

- step_label_style: letter_above_arrow
- step_count_shown: False
- yield_format: None
- highlight_fill: None
- variation_color: None

Signature features:

- convergent route stacked in rows, each arrow carrying only letters (single a, or pairs b,c and i,j) above it
- reagents and yields not drawn on the scheme
- final compound labelled with its code name in bold (TNG462)

Crops: evidence/jmed_chem-03.png

Notes: one crop, greyscale throughout; fragment 88 is black like the rest of the scheme, so no variation colour is shown and the earlier navy #1F1F5C value is withdrawn. Step letters sit above the arrows, as in crops 01 and 02; the footnote key lies outside the crop.

### structure_panel

Conventions:

- highlight_fill: None
- variation_color: None
- intermediate_label_style: None

Signature features:

- drugs and leads in a grid, black only, no highlighted changes
- caption under each structure as plain name, with the compound number bold in parentheses, e.g. LX7101 (3)
- clinical compounds named in plain text larger than atom labels (AMG 193, TNG908)

Crops: evidence/jmed_chem-04.png, evidence/jmed_chem-05.png

Notes: neither panel highlights the changed region. Crop 04 captions carry no compound numbers; the bold numbers come from crop 05, where only the first row of captions is inside the crop (row 2 captions lie below it). Crop 04 writes CF3 on AMG 193 and the nitrile of BMS-986504 as NC. intermediate_label_style null because labels are names with an optional bold number.

### sar_table

Conventions:

- table_style: grid
- activity_format: pIC50 mean ± SD, two decimals (7.48 ± 0.18)
- variation_color: None
- highlight_fill: None

Signature features:

- core structure with R and A drawn above the table
- full black grid on every cell, bold header with merged group headers (Enzymatic pIC50 over LIMK1 and LIMK2)
- bold compound numbers in the first column; R groups drawn as small fragments with a dashed attachment bond
- text values such as Rapid and nd mixed with numbers

Crops: evidence/jmed_chem-06.png, evidence/jmed_chem-07.png

Notes: one paper; in PMC most J. Med. Chem. tables are HTML text and only the core is an image (as in the TNG462 paper). The core with its R and A labels is in crop 07 only (crop 06 shows the table alone). The grid style and the pIC50 format rest on crop 06 alone, since crop 07 shows only the core.

## Evidence crops

- evidence/jmed_chem-01.png: Scheme 1, Baldwin, Ward et al., J. Med. Chem. 2025
- evidence/jmed_chem-02.png: Scheme 5, top two rows, Baldwin, Ward et al., J. Med. Chem. 2025
- evidence/jmed_chem-03.png: Scheme 8 (synthesis of TNG462), Cottrell et al., J. Med. Chem. 2025
- evidence/jmed_chem-04.png: Figure 1, Cottrell et al., J. Med. Chem. 2025
- evidence/jmed_chem-05.png: Figure 1A, Baldwin, Ward et al., J. Med. Chem. 2025
- evidence/jmed_chem-06.png: Table 1 (image version, upper part), Baldwin, Ward et al., J. Med. Chem. 2025
- evidence/jmed_chem-07.png: Table 1 core structure, Baldwin, Ward et al., J. Med. Chem. 2025
