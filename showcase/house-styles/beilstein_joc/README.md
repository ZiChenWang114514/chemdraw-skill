# beilstein_joc

Reaction-scheme house style of the Beilstein Journal of Organic Chemistry, measured from open-access figures. Base preset: nature.

## Sources

- Beller et al., Beilstein J. Org. Chem. 2025 (Pd-catalyzed dehydrogenative arylation of arylhydrazines to access non-symmetric azobenzenes). DOI 10.3762/bjoc.21.170. Licence CC BY 4.0.
- Gandeepan et al., Beilstein J. Org. Chem. 2025 (Palladium-catalyzed regioselective C1-selective nitration of carbazoles). DOI 10.3762/bjoc.21.190. Licence CC BY 4.0.
- Xiao et al., Beilstein J. Org. Chem. 2025 (Ni-promoted reductive cyclization cascade enables a total synthesis of (+)-aglacin B). DOI 10.3762/bjoc.21.197. Licence CC BY 4.0.
- Chusov et al., Beilstein J. Org. Chem. 2025 (Influence of the cation in hypophosphite-mediated catalyst-free reductive amination). DOI 10.3762/bjoc.21.130. Licence CC BY 4.0.

## Measurements

- Bond length / atom-label cap height: 2.2
- Line width / bond length: 0.068
- Bold wedge width / bond length: 0.16
- Arrow length / bond length: 6.4

Only crops 02 and 05 carry measurements and they disagree; each value is the mean of the two crops. The spread is recorded in conventions.notes.measured.

## Conventions

- compound_label_face: bold
- compound_label_color: #000000
- compound_label_italic_suffix: False
- yield_placement: after_product_label (after the product label in both scope crops (01, 02); in the total-synthesis scheme (05) the yield is under the arrow in parentheses. Two agreeing crops (01, 02) hold the value; crop 05 is the exception and is recorded under total_synthesis.)
- yield_separator: None (no single separator: crop 02 uses a colon (2a: 69%); crop 01 uses a comma in R = ... rows (3c R = OCF3, 69%) and a space for single compounds (3m 43%).)
- yield_format: {value}% ({value}% in the product labels of the scope crops (01, 02); the step yield in the multistep scheme (05) is ({value}%) and is recorded under reaction_scheme and total_synthesis.)
- conditions_split: None (Crops 01 and 02 put the base or AgNO3 below the arrow with the solvent (Cs2CO3 and H2O in 01; AgNO3 in 02); only crop 05 puts all reagents above and the solvent below. Two agreeing crops are needed, so null.)
- substrate_layout: None (Crop 01 (1a + 2b-q) is inline_plus; crop 04 (retrosynthesis, 7 over 8 with a plus) is stacked_plus. Crops 02 and 05 show a single substrate. The crops disagree, so null.)
- abbreviate_groups: ['OMe', 'tBu', 'Ph', 'CO2Me']
- aromatic_rings: kekule
- new_bond_color: None (Dark red new bonds appear in crop 02 (C-NO2 bond, #800000, Gandeepan et al.), crop 04 (bonds to be formed, #8A3123) and crop 05 (two new C-C bonds of 13, dark red on thin lines, Xiao et al.). The hex differs between papers; author choice, not a journal rule.)
- substrate_colors: None
- highlight_fill: None (light blue ring fill #BEDAFF in crops 02 and 03 only (one paper); the substrate_scope and catalytic_cycle sections carry the same fill.)
- reagent_text_color: None (Author colouring: NO2, NO3 and HNO3 in red in crops 02 and 03; Ni in dark red in crop 04 (#8A0004); reagent text black in crops 01 and 05. The journal sets no colour, so null.)
- arrow_style: plain (plain in crops 01, 02 and 05. Crop 07 (a mechanism, Scheme 5 of Chusov et al.) uses equilibrium double arrows in its top row; mechanism figures are outside this top-level convention.)
- show_plus_sign: True
- base_preset: nature is closest on the three ratios; the journal does not redraw author figures, so ratios vary between papers (bond/cap 1.95 in crop 05, 2.48 in crop 02).

## Signature features

- scope figures open with the general reaction on top, separated from the product grid by a full-width thin grey rule (crops 01, 02)
- product yield on the label line: bold label then plain yield, e.g. 2a: 69% (crop 02) or 3m 43% (crop 01)
- tert-butyl written t-Bu with an italic t (crops 01, 02)
- in multistep schemes the step yield sits in parentheses as the last line under the conditions, e.g. (30%) (crop 05)
- sans-serif (Arial-like) text throughout (crops 01 to 07)

## Figure types

### reaction_scheme

Conventions:

- yield_format: ({value}%)
- selectivity_format: None
- highlight_fill: None
- variation_color: None

Signature features:

- catalyst above the arrow; base and additives each on their own line below, with solvent, temperature and time on one line (crops 01, 02)
- step yield in parentheses as the last line under the conditions (crop 05)

Crops: evidence/beilstein_joc-01.png, evidence/beilstein_joc-05.png.

Notes: colours are chosen by the authors; the journal imposes no palette. yield_format rests on crop 05 (step yield in parentheses). Crop 01 product yields are {value}% on the product labels and are recorded under substrate_scope, so the scheme-level format is not {value}%.

### substrate_scope

Conventions:

- scope_layout: grid
- variation_color: None
- yield_format: {value}%
- selectivity_format: None
- conditions_position: scheme_on_top
- highlight_fill: #BEDAFF

Signature features:

- general reaction on top, a full-width thin grey rule, then the product grid (crops 01, 02)
- label and yield on one line under each product: bold 2a then : 69% (crop 02); crop 01 writes bold 3m, a space and 43% for single compounds and R = OCF3, 69% (comma) in R = ... rows
- products sharing one core listed as R = ... rows under a single drawing (crop 01)
- footnotes as superscript a after the yield

Crops: evidence/beilstein_joc-01.png, evidence/beilstein_joc-02.png.

Notes: variation colours differ (purple Ph and dark red C-Br in crop 01; dark red bond and red NO2 in crop 02), and crop 02 also draws the core bonds in blue #255A90, so variation_color is null. highlight_fill #BEDAFF rests on crop 02 alone (light blue ring fill over each product core, unambiguous there); crop 01 has no ring fill, so the fill is one paper's choice.

### catalytic_cycle

Conventions:

- cycle_shape: circle
- cycle_arrow_color: #000000
- catalyst_color: #8B0542
- center_label: True
- step_names: False
- intermediate_label_style: bold_number
- curved_arrow_color: #000000
- highlight_fill: #BEDAFF

Signature features:

- black curved arrows on a circle; substrates enter and by-products (HNO3) leave on short tangent arrows
- shaded sphere labelled Pd with two maroon #8B0542 circular arrows at the centre of the cycle
- intermediates numbered with bold Arabic numbers under each structure; no step names

Crops: evidence/beilstein_joc-03.png.

Notes: rests on one crop; the cycle in crop 07 also uses black arrows but puts key species in grey rounded boxes instead of a centre label

### mechanism

Conventions:

- curved_arrow_color: #000000
- curved_arrow_weight: thin
- show_lone_pairs: False
- formal_charge_style: plain
- intermediate_label_style: none
- ts_marker: None
- highlight_fill: None

Signature features:

- fragments colour coded through the mechanism: carbonyl part red #FC0000, amine part blue #0000FC
- small black curved arrows, thinner than bonds
- phosphorus reagents in grey rounded boxes with a drop shadow

Crops: evidence/beilstein_joc-07.png.

Notes: rests on one crop. The top row of crop 07 uses equilibrium double arrows; plain curved arrows appear only in the lower cycle, which is not drawn.

### energy_profile

Conventions:

- energy_unit: kcal/mol
- energy_label: None
- level_style: bars_dashed_connectors
- pathway_colors: ['#0000FF', '#FF7F00', '#FF0000']
- ts_marker: none
- intermediate_label_style: none

Signature features:

- short thick horizontal bars joined by thin dashed lines in the pathway colour
- energy values in italics above each bar; state names (Step_1, TS2->3) in bold pathway colour below
- y axis titled Gibbs Free Energy (kcal/mol) in italics; x axis an arrow without ticks

Crops: evidence/beilstein_joc-06.png.

Notes: rests on one crop; transition states named TS with arrow subscripts, no double dagger. energy_label is null: the values carry no delta-G symbol, only the y-axis title Gibbs Free Energy (kcal/mol). intermediate_label_style none refers to numbered intermediates; every state carries a name (Step_1, Step_2', TS2->3'', Step_3'' and so on), which the enum does not express. Side-pathway states carry prime marks; two black x marks sit on the orange and red connectors near Step_1. Step_3 is the one state name that sits above its bar; the others are below.

### retrosynthesis

Conventions:

- retro_arrow: open_double
- disconnection_mark: colored_bond
- disconnection_color: #8A3123
- highlight_fill: None
- step_count_shown: False

Signature features:

- open double retrosynthetic arrows with the key reagent (bold italic Ni, dark red #8A0004) above
- bonds to be formed in dark red #8A3123, atom numbers in blue #3839FF

Crops: evidence/beilstein_joc-04.png.

Notes: rests on one crop

### total_synthesis

Conventions:

- step_label_style: none
- step_count_shown: False
- yield_format: ({value}%)
- highlight_fill: None
- variation_color: None

Signature features:

- each step written in full above and below its arrow, yield in parentheses as the last line
- target named with its number in parentheses, (+)-aglacin B (2), only the number bold
- X-ray ball-and-stick model linked to the structure by a triple-bar sign, italic caption

Crops: evidence/beilstein_joc-05.png.

Notes: rests on one crop. The two new C-C bonds of 13 are drawn in dark red (crop 05), the same author colouring as the bonds to be formed in the retrosynthesis (crop 04); total_synthesis has no new_bond_color key, so this is recorded here.

## Evidence crops

- evidence/beilstein_joc-01.png: Scheme 1, Beller et al., Beilstein J. Org. Chem. 2025
- evidence/beilstein_joc-02.png: Scheme 3 top, Gandeepan et al., Beilstein J. Org. Chem. 2025
- evidence/beilstein_joc-03.png: Figure 2, Gandeepan et al., Beilstein J. Org. Chem. 2025
- evidence/beilstein_joc-04.png: Scheme 1, Xiao et al., Beilstein J. Org. Chem. 2025
- evidence/beilstein_joc-05.png: Scheme 3, Xiao et al., Beilstein J. Org. Chem. 2025
- evidence/beilstein_joc-06.png: Figure 2 top, Chusov et al., Beilstein J. Org. Chem. 2025
- evidence/beilstein_joc-07.png: Scheme 5, Chusov et al., Beilstein J. Org. Chem. 2025
