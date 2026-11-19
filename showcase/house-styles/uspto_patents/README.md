# uspto_patents

Drawing house style of US patents and published applications, measured from the page images of pharmaceutical patents (US government works, public domain). Base preset: j_mol_mod.

## Sources

- Hadida-Ruah et al. (Vertex), US 9,732,080 B2, 2017 (Modulators of ATP-binding cassette transporters). US 9,732,080 B2. Licence public domain (US patent).
- Lanman et al. (Amgen), US 10,519,146 B2, 2019 (KRAS G12C inhibitors and methods of using the same). US 10,519,146 B2. Licence public domain (US patent).
- Chaves et al. (Amgen), US 11,236,091 B2, 2022 (Solid state forms). US 11,236,091 B2. Licence public domain (US patent).

## Measurements

- Bond length / atom-label cap height: 3.6 (median of the evidence crops; crop values 2.7 to 4.1)
- Line width / bond length: 0.047 (strokes 2 to 3 px on 51 to 61 px bonds, 0.04 to 0.06)
- Bold wedge width / bond length: 0.2 (wedge wide end in crop 09; the bold ring bonds there are about 0.07 to 0.12, so this value describes wedges)
- Arrow length / bond length: 4.0 (long reagent arrows: crop 06 mean 4.4, crop 07 mean 3.3; the short lettered arrows of crop 05, about 1.5, are a different arrow type)
- Label font: Times New Roman
- Atom label size estimate: 7.5 pt, carried over from the earlier 3.0 ratio and not re-derived (the crops carry no point scale)

## Conventions

- compound_label_face: plain (plain Roman I in crops 01 and 05; example numbers 1-1 plain in crop 03)
- compound_label_color: #000000
- compound_label_italic_suffix: False
- yield_placement: None (no yields on any drawing seen; patents give yields in the example text)
- yield_format: None
- conditions_split: None (letters keyed to a footnote in crop 05; reagent class above and Step n below in crops 06 and 07, with the reagent words straddling the arrow in crop 07 steps 5, 7 and 8; no single rule)
- substrate_layout: None
- abbreviate_groups: None (Me and iPr written as text only in crop 09; not enough agreement)
- aromatic_rings: kekule
- new_bond_color: None
- substrate_colors: None
- highlight_fill: None
- reagent_text_color: #000000
- arrow_style: plain
- show_plus_sign: None

## Signature features

- drawings are black line art on a white page scan, Times serif atom labels, no colour or shading anywhere
- scheme titles centred and underlined (Scheme I, Method 1); a “-continued” heading is centred and plain (crop 07); table captions (TABLE 1, TABLE 5) are centred and plain, not underlined (crops 03, 08)
- general formulas labelled with a plain Roman numeral, I or (I), flush right in the text column at the level of the top of the drawing, not bold
- variable groups as R with superscript numbers (R2, R3) or italic superscript letters (RN, RX); ring atoms E1, E2 and G1 to G4 as bare letters at ring vertices; unspecified rings A and B drawn as an open loop, a circle or a hexagon with the letter inside
- each structure sits in justified two-column body text with line numbers 5, 10, 15 in the gutter

## Evidence crops

- evidence/uspto_patents-01.png: col. 6, formula I and Ar1 definition, Hadida-Ruah et al.
- evidence/uspto_patents-02.png: col. 57, formula (I) and definitions, Lanman et al.
- evidence/uspto_patents-03.png: Table 1, entry 1-1, Lanman et al.
- evidence/uspto_patents-04.png: Table 1, compounds 1 to 5 (fragment), Hadida-Ruah et al.
- evidence/uspto_patents-05.png: Scheme I, Hadida-Ruah et al.
- evidence/uspto_patents-06.png: Method 1, steps 1 to 4, Lanman et al.
- evidence/uspto_patents-07.png: Method 1, steps 5 to 8 (continued), Lanman et al.
- evidence/uspto_patents-08.png: Table 5, Hadida-Ruah et al.
- evidence/uspto_patents-09.png: col. 5, Compound 1 atropisomer P, Chaves et al.

## Figure types

### markush

Conventions:

- r_group_style: superscript_number
- variation_color: None
- table_style: none

Signature features:

- formula label (I) or I flush right in the text column, at the level of the top of the drawing and beyond its right end, plain type
- R groups as R with superscript numbers (R2, R3, R4) or italic superscript letters (RN, RX); ring atoms as E1, E2 or G1 to G4 with subscript numbers, bare letters at ring vertices
- unspecified rings drawn as an open loop with the letter inside (ring A, crop 01), a circle with the letter inside (ring A, crop 02) or a hexagon with the letter inside (ring B, crop 01); substituent position left open by a bond crossing the ring
- attachment points shown by a wavy line across the bond
- variable definitions as running justified text beginning wherein ..., not a table

Crops: evidence/uspto_patents-01.png, evidence/uspto_patents-02.png

Notes: two patents agree on all of these; black only. Ring shape varies within the two crops (loop, circle, hexagon), so all three forms are listed

### structure_panel

Conventions:

- highlight_fill: None
- variation_color: None
- intermediate_label_style: None

Signature features:

- table caption in capitals centred above the table, plain type (TABLE 1, crop 03); the first table page has thick black horizontal rules above and below the header Ex. # / Chemical Structure (crop 03)
- a table fragment with no header shows a single thick rule at its top and no caption (crop 04)
- one example compound per row, example number (1-1, 2, 3) plain at the row start (crop 03) or at the margin (crop 04)
- single structure in body text with no table, caption or example number (crop 09)
- no highlighting of varied substituents; stereo shown by bold wedges with small italic (S) and P descriptors (crop 09)

Crops: evidence/uspto_patents-03.png, evidence/uspto_patents-04.png, evidence/uspto_patents-09.png

Notes: labels are example numbers, so intermediate_label_style is left null. The table caption and header rules rest on crop 03 alone; crop 04 is a fragment from another patent and shows only the top rule; crop 09 has no table, so the table features do not apply to it

### reaction_scheme

Conventions:

- yield_format: None
- selectivity_format: None
- highlight_fill: None
- variation_color: None

Signature features:

- underlined centred title for a scheme (Scheme I, Method 1); a centred, plain “-continued” heading on a continuation page (crop 07)
- generic intermediates with R groups and ring placeholders, ring-atom letters bare at vertices (crops 06, 07); the final generic product of Scheme I is labelled with a plain Roman numeral I (crop 05); Method 1 products (crops 06, 07) carry no numeral
- either lower-case letters beside the arrow keyed to a footnote line a) SOCl2, DMF (cat.), DCM; b) ... or reagent words above the arrow with Step n below (the words may straddle the arrow, crop 07)
- no yields, no colour

Crops: evidence/uspto_patents-05.png, evidence/uspto_patents-06.png, evidence/uspto_patents-07.png

Notes: Roman-numeral labelling seen only for the final formula I in crop 05; intermediates in crops 06 and 07 are unlabelled. The arrow-length spread is recorded in the card's conventions.notes.arrow_length

### sar_table

Conventions:

- table_style: horizontal_rules
- activity_format: binned symbols +, ++, +++ with the bin limits stated under the caption on two legend lines (IC50/EC50 Bins and PercentActivity Bins)
- variation_color: None
- highlight_fill: None

Signature features:

- TABLE 5 caption centred and plain, a thick top rule, then two legend lines: IC50/EC50 Bins: +++ <= 2.0 < ++ <= 5.0 < + and PercentActivity Bins: + <= 25.0 < ++ <= 100.0 < +++
- a rule under the legend block and a heavier rule under the column header row
- centred columns Compd. No., Binned EC50, Binned Max Efficacy; no structures in the table

Crops: evidence/uspto_patents-08.png

Notes: one crop; the second legend line sets the bins for Binned Max Efficacy
