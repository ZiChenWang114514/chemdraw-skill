# baran_group

Reaction-scheme house style of the Baran group (Scripps Research), measured from open-access figures. Base preset: acs1996.

## Sources

- Baran et al., J. Am. Chem. Soc. 2024 (Simplified modular access to enantiopure 1,2-aminoalcohols via Ni-electrocatalytic decarboxylative arylation). DOI 10.1021/jacs.3c14119. Licence CC BY 4.0.
- Baran et al., Nature 2026 (C-glycoside synthesis through radical cross-coupling of glycohydrazides). DOI 10.1038/s41586-026-10807-x. Licence CC BY 4.0.

## Measurements

- Bond length / atom-label cap height: 2.2
- Line width / bond length: 0.07
- Bold wedge width / bond length: 0.2
- Arrow length / bond length: 5.7

## Conventions (top-level, reaction schemes)

- compound_label_face: bold
- compound_label_color: #000000
- compound_label_italic_suffix: False
- yield_placement: None. Crop 02 puts the multistep yields under the arrow; crop 03, a product panel, puts its yield under the product label; crop 01 shows no yield.
- yield_format: {value}%
- conditions_split: None. Crop 01 puts NMP below the arrow; crop 02 puts DMA above it.
- substrate_layout: None. Only crop 01 shows a plus between two substrates.
- abbreviate_groups: CO2Me, OBn, Boc, Cbz, tBu, PhthN, OMe
- aromatic_rings: kekule
- new_bond_color: #8A0108 (dark red in both reaction-scheme crops, 01 and 02). The Nature product panel (crop 03) uses purple.
- substrate_colors: None
- highlight_fill: None (the teal box in crop 02 is recorded under reaction_scheme)
- reagent_text_color: #000000
- arrow_style: plain
- show_plus_sign: None (only crop 01 shows a plus)

## Figure types

- reaction_scheme (crops 01 and 02): yield_format {value}%; highlight_fill #BBF6F4. The highlight rests on crop 02 alone: a teal box behind the target product 4.
- substrate_scope (crop 03): scope_layout grid; yield_format {value}%. One crop: a grid of approved-drug structures, each with its yield under the product label.

## Signature features

- light grey panel background #EDEDEF behind the reaction schemes (crops 01 and 02); the product panel (crop 03) is on white
- thin navy top edge #00007E on the grey panel (crop 01 only); no navy title bar and no white panel title in any crop
- blue circle with white lightning bolt on the arrow for electrolysis (crops 01 and 02; circle #0B17FF)
- scale and comparison notes in bold blue #0B17FF (crop 02); the blue "Chiral auxiliary" note in crop 01 is regular weight
- compound labels bold and large, close to atom-label size (crops 01 and 02; crop 01 compound cap height 31 px against 36 px for atom labels)

## Evidence crops

- evidence/baran_group-01.png: Figure 2A, Baran et al., J. Am. Chem. Soc. 2024
- evidence/baran_group-02.png: Figure 3 middle band, Baran et al., J. Am. Chem. Soc. 2024
- evidence/baran_group-03.png: Figure 2b first row, Baran et al., Nature 2026
