# chemeurj

Reaction-scheme house style of Chemistry - A European Journal (Wiley-VCH), measured from open-access figures. Base preset: wiley.

## Sources

- Anderson et al., Chem. Eur. J. 2023 (Gold-catalyzed cyclization of yndiamides with isoxazoles via alpha-imino gold Fischer carbenes). DOI 10.1002/chem.202302821. Licence CC BY 4.0.
- Bourissou et al., Chem. Eur. J. 2022 (Mechanistic insights about the ligand-enabled oxy-arylation/vinylation of alkenes via Au(I)/Au(III) catalysis). DOI 10.1002/chem.202202110. Licence CC BY 4.0.
- Maes et al., Chem. Eur. J. 2023 (Iron-catalysed carbene transfer to isocyanides as a platform for heterocycle synthesis). DOI 10.1002/chem.202203074. Licence CC BY 4.0.

## Measurements

- Bond length / atom-label cap height: 2.0
- Line width / bond length: 0.04
- Bold wedge width / bond length: 0.19
- Arrow length / bond length: 7.0

## Conventions

- compound_label_face: bold
- compound_label_color: #000000
- compound_label_italic_suffix: False
- yield_placement: None (under the compound label in bold navy #004080 in crop 03, after the label as "4aa, 88%" in crop 04; differs between papers)
- yield_format: {value}%
- conditions_split: reagents_above_solvent_below
- substrate_layout: inline_plus
- abbreviate_groups: ['Ts', 'tBu', 'OMe'] (Ph removed: crop 02 draws both phenyl rings in full, while Ph is abbreviated only in scope crops 03 and 04. OMe is the ether group (crops 03, 04); crop 09 writes a methyl ester as MeO-C(=O) in an energy profile, whereas scope crop 03 writes esters as CO2Me.)
- aromatic_rings: kekule
- new_bond_color: None (crop 01 draws the new C to Nu bond red (about #DD211E); crops 02 and 07 (one paper, Bourissou et al.) draw the new C to aryl bond black and bold. The crops disagree, so null.)
- substrate_colors: None (two pairs, one per paper: blue and red in Bourissou et al. (crop 02 alkenol and aryl iodide; crop 07 the same pair), maroon and blue or navy in Maes et al. (crops 04 and 06). No pair is shared between the papers, so null.)
- highlight_fill: None (null at top level: among the reaction figures only crop 01 shows the fill (grey #E6E6E6 behind the panel b products, none in panel a) and crop 02 has none, so there is no 2+ agreement. The fill also appears in crop 05 (transition-state labels and product boxes) and crop 08 (starting-material group), which are cycle and energy figures; see the figure_types sections.)
- reagent_text_color: #000000
- arrow_style: plain
- show_plus_sign: True

## Signature features

- ChemDraw palette colours for heteroatoms or fragments: navy #004080, blue #0080C0, maroon #800000, purple #800040
- light grey #E6E6E6 boxes behind products (crop 01 panel b, crop 05), behind transition-state labels (crop 05) and behind the starting-material group (crop 08)
- bold sans-serif panel letters a, b, c at the top left of each panel, panels separated by grey #808080 rules
- substrate fragments coloured and the colour carried into the product (blue/red in crops 02 and 07, maroon with blue or navy in crops 04 and 06)

## Figure types

### reaction_scheme

Conventions:

- yield_format: None
- selectivity_format: None
- highlight_fill: #E6E6E6
- variation_color: None

Signature features:

- reagents above the arrow and additives, solvent, temperature, time stacked below in plain Arial (crop 02)
- substrate fragments colour-coded and the colours kept in the product
- grey #E6E6E6 box behind the panel b products in crop 01 (panel a has none)

Crops: evidence/chemeurj-01.png, evidence/chemeurj-02.png.

Notes: highlight_fill rests on crop 01 only: grey boxes behind the two panel b products (2 and 3); panel a and crop 02 have no fill. yield_format is null because neither reaction-scheme crop (01, 02) prints a yield; the {value}% format comes from the scope crops 03 and 04 at top level.

### substrate_scope

Conventions:

- scope_layout: grid
- variation_color: None
- yield_format: {value}%
- selectivity_format: None
- conditions_position: scheme_on_top
- highlight_fill: None

Signature features:

- reaction header with conditions on the arrow above a grid of products, sections separated by grey #808080 rules (crop 03) or a dashed rule (crop 04)
- section titles in bold navy #004080 (crop 03) or bold panel letters A/B (crop 04)
- footnote letters in square brackets or superscript after yields
- section titles on light grey #F5F5F5 tabs (crop 03)

Crops: evidence/chemeurj-03.png, evidence/chemeurj-04.png.

Notes: variation colour differs and stays null: crop 03 draws the varied R1 and R2 groups black, with the sulfonamide nitrogens blue (scaffold atoms, not the varied part); crop 04 draws the varied amine part maroon (about #6C0000 to #800000 on the stroke).

### catalytic_cycle

Conventions:

- cycle_shape: None
- cycle_arrow_color: #000000
- catalyst_color: None
- highlight_fill: #E6E6E6
- center_label: None
- step_names: True
- intermediate_label_style: None
- curved_arrow_color: #000000

Signature features:

- cycle drawn with black arcs around a circle (crops 06, 07); crop 05 is an open loop
- incoming and leaving species on short curved black arrows touching the cycle arc
- framed legend or catalyst box with black outline, in crop 06 with a grey drop shadow
- grey #E6E6E6 tabs behind transition-state labels and product boxes (crop 05)

Crops: evidence/chemeurj-05.png, evidence/chemeurj-06.png, evidence/chemeurj-07.png.

Notes: intermediate labels differ and stay null: Int1 to Int8 in bold (crop 05), grey bold capital letters A to D (crop 06), bold compound numbers 2 and 2v (crop 07). Catalyst colour differs and stays null: Au orange in crop 05, black in crops 06 and 07. Cycle shape differs and stays null: crop 05 is an open loop, crops 06 and 07 are circles. Step names: plain black beside the arrows in crop 07 only (crops 05 and 06 have none). Grey #E6E6E6 fill: crop 05 only (transition-state tabs and product boxes); crops 06 and 07 have no fill (crop 06 has grey drop shadows on its pathway boxes). The catalyst sits centred in a black-framed box in crop 07 only.

### energy_profile

Conventions:

- energy_unit: kcal/mol
- energy_label: delta_G
- level_style: bars_solid_connectors
- pathway_colors: None
- ts_marker: none
- intermediate_label_style: None

Signature features:

- thick horizontal level bars (15-17 px, about 3x the bond line) joined by thinner solid slanted lines
- bold species name stacked over its energy value beside each bar, above the bar for most levels and below for some (crops 08, 09)
- vertical axis arrow at left with DeltaG label in kcal mol-1
- second pathway in a contrasting colour: blue #0080BF vs maroon #800000 (crop 08), grey #808080 vs black (crop 09)

Crops: evidence/chemeurj-08.png, evidence/chemeurj-09.png.

Notes: transition states carry no double dagger: crop 08 TS1minor, TS2minor, TS1major, TS2major and TS_Interconv; crop 09 TS1, TS2 and TS1'. Crop 08 reads DeltaG_sol (solvation-corrected) on the axis and crop 09 reads DeltaG298 with DeltaE in parentheses; delta_G is the nearest value. Pathway colours differ between the two crops (crop 08 blue minor and maroon major; crop 09 grey competing and black main), so pathway_colors is null.

## Evidence crops

- evidence/chemeurj-01.png: Scheme 1a-b, Anderson et al., Chem. Eur. J. 2023
- evidence/chemeurj-02.png: Scheme 2, Bourissou et al., Chem. Eur. J. 2022
- evidence/chemeurj-03.png: Figure 1, Anderson et al., Chem. Eur. J. 2023
- evidence/chemeurj-04.png: Scheme 2, Maes et al., Chem. Eur. J. 2023
- evidence/chemeurj-05.png: Scheme 3a, Anderson et al., Chem. Eur. J. 2023
- evidence/chemeurj-06.png: Scheme 5, Maes et al., Chem. Eur. J. 2023
- evidence/chemeurj-07.png: Scheme 1, Bourissou et al., Chem. Eur. J. 2022
- evidence/chemeurj-08.png: Scheme 3b, Anderson et al., Chem. Eur. J. 2023
- evidence/chemeurj-09.png: Figure 1, Maes et al., Chem. Eur. J. 2023
