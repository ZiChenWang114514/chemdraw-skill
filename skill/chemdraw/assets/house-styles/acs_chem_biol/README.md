# acs_chem_biol

House style of ACS Chemical Biology, measured from open-access figures. Base preset: acs1996.

## Sources

- Bridge et al., ACS Chem. Biol. 2026 (Enzymatic bromination of native peptides for late-stage structural diversification via Suzuki-Miyaura coupling). DOI 10.1021/acschembio.6c00269. Licence CC BY 4.0.
- Azeez et al., ACS Chem. Biol. 2026 (Discovery and development of a potent LIMK2 isoform-specific degrader). DOI 10.1021/acschembio.6c00137. Licence CC BY 4.0.
- Sun et al., ACS Chem. Biol. 2026 (Metabolism of epigenetic ribonucleosides leads to nucleolar stress and cytotoxicity). DOI 10.1021/acschembio.5c00656. Licence CC BY 4.0.

## Measurements

- Bond length / atom-label cap height: 2.0
- Line width / bond length: 0.05
- Bold wedge width / bond length: 0.18
- Arrow length / bond length: 3.0 (crop 05 about 3.2, crop 01 about 2.6; the earlier 4.2 used a 105 px arrow that crop 05 does not show)

## Conventions

- compound_label_face: None (molecules are named (LIMKi3, VH032, 4V) rather than numbered in the crops; crop 06 sets names in bold, but it is the only scheme crop that names compounds, so no two scheme crops agree)
- compound_label_color: #000000
- compound_label_italic_suffix: None
- yield_placement: None (only crop 01 gives yields, under the product; the two-crop rule keeps it null)
- yield_format: None (the reaction_scheme section carries it from crop 01)
- conditions_split: None (crop 01 splits one step and not the next, so it does not agree with itself)
- substrate_layout: None
- abbreviate_groups: None
- aromatic_rings: kekule
- new_bond_color: None
- substrate_colors: None
- highlight_fill: None
- reagent_text_color: #000000
- arrow_style: plain (crops 01 and 05; crop 06 uses a thick tapered block arrow)
- show_plus_sign: None

## Signature features

- chemistry embedded in multi-panel figures with bold uppercase or lowercase panel letters (crops 02, 03)
- the installed group drawn as a filled coloured circle defined in a key instead of an atom label: grey-purple halogen dot (crops 01, 05), magenta aryl dot (crop 01)
- grey title bars with bold black text separate scheme rows (crop 05)
- step names in italic over a thin grey rule above the arrow (crop 01)

## Figure types

### biomolecule

Conventions:

- sugar_projection: None
- peptide_style: None (crop 01 labels the beads with one-letter codes; crop 05, from the same paper, draws unlabelled beads)
- highlight_fill: None
- variation_color: #4C6BFD (crops 03 and 04 agree)

Signature features:

- peptides as rows of circles: in crop 01 the residues carry one-letter codes, grey R and cyan #7FD0D4 W; in crop 05 the beads are unlabelled grey circles; the modified Trp carries a coloured dot (crop 01)
- PROTAC linkers drawn with the variable (CH2)n segment in pink #EE3E77, the two ligands in black (crop 06)
- nucleoside modifications in blue #4C6BFD on a mostly black core (crops 03, 04); in crop 03 the core atoms or bonds a modification changes are blue too (N1 of m1A, N7 of m7G, C6 oxygen of I, ring bonds of Psi and D)

Crops: evidence/acs_chem_biol-01.png, evidence/acs_chem_biol-03.png, evidence/acs_chem_biol-04.png, evidence/acs_chem_biol-05.png, evidence/acs_chem_biol-06.png

Notes: peptide_style is null because the crops disagree. Ribose drawn as a flat furanose rather than Haworth or chair, so sugar_projection null.

### structure_panel

Conventions:

- highlight_fill: None
- variation_color: #4C6BFD
- intermediate_label_style: none

Signature features:

- same core repeated in a grid with a short name under each; the varied group is coloured blue, and where a modification changes the core, the affected core atoms or bonds are blue too (crop 03)
- R-group key in a thin grey rectangle: R = followed by blue fragments with names (crop 04)

Crops: evidence/acs_chem_biol-03.png, evidence/acs_chem_biol-04.png

Notes: both crops from one paper; the R-group key is in crop 04 only

### sar_table

Conventions:

- table_style: horizontal_rules
- activity_format: {value}
- variation_color: None
- highlight_fill: None

Signature features:

- no structures in the table; compound IDs (21a, 23d) in the first column, series headings bold underlined (VHL-C3)
- two-level bold header with grouped targets (LIMK1, LIMK2) above unit-bearing columns such as SPR KD (nM)
- thin horizontal rules at the header and section breaks, no vertical rules

Crops: evidence/acs_chem_biol-02.png

Notes: one crop; activities as bare numbers with units in the header

### reaction_scheme

Conventions:

- yield_format: {value}% isolated yield
- selectivity_format: None
- highlight_fill: None
- variation_color: None (the three scheme crops use three colours for their variable groups: magenta aryl in crop 01, grey-purple halogen in crops 01 and 05, pink linker in crop 06)

Signature features:

- on-peptide reactions shown on bead peptides (crop 01); the new substituent drawn as a coloured dot defined beside the arrow, magenta for an aryl group and grey-purple for a halogen (crops 01, 05)
- enzyme or catalyst name above the arrow, concentrations stacked (10 uM 4V, 10 mM NaBr) (crop 01)
- step titles in italic above a thin grey rule over each arrow (crop 01)

Crops: evidence/acs_chem_biol-01.png, evidence/acs_chem_biol-05.png, evidence/acs_chem_biol-06.png

Notes: yield_format from crop 01 only, the only scheme with yields. Sampled colours: magenta about #D21579, pink about #F64883.

## Evidence crops

- evidence/acs_chem_biol-01.png: Figure 4b, Bridge et al., ACS Chem. Biol. 2026
- evidence/acs_chem_biol-02.png: Figure 2A, Azeez et al., ACS Chem. Biol. 2026
- evidence/acs_chem_biol-03.png: Figure 1B, Sun et al., ACS Chem. Biol. 2026
- evidence/acs_chem_biol-04.png: Figure 1D, Sun et al., ACS Chem. Biol. 2026
- evidence/acs_chem_biol-05.png: Figure 1, Bridge et al., ACS Chem. Biol. 2026
- evidence/acs_chem_biol-06.png: Figure 1C, Azeez et al., ACS Chem. Biol. 2026
