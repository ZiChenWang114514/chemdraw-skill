# list_group

Reaction-scheme house style of the List group (MPI für Kohlenforschung), measured from open-access figures. Base preset: nature.

## Sources

- List et al., Nature 2023 (Catalytic asymmetric synthesis of cannabinoids and menthol from neral). DOI 10.1038/s41586-023-05747-9. Licence CC BY 4.0.
- List et al., Nature 2022 (Organocatalytic stereoselective cyanosilylation of small ketones). DOI 10.1038/s41586-022-04531-5. Licence CC BY 4.0.
- List et al., Nature 2024 (Catalytic asymmetric cationic shifts of aliphatic hydrocarbons). DOI 10.1038/s41586-023-06826-7. Licence CC BY 4.0.

## Measurements

- Bond length / atom-label cap height: 2.65
- Line width / bond length: 0.044
- Bold wedge width / bond length: 0.13
- Arrow length / bond length: 5.9

## Conventions

- compound_label_face: bold
- compound_label_color: #000000 (scheme compounds; energy-profile species labels are navy, see energy_profile)
- compound_label_italic_suffix: False
- yield_placement: None (not set: no two crops agree. Crop 01 stacks yield and d.r./e.r. to the right of the product; crop 02 puts the yield on the label line, '6, 91%'; crop 03 puts the label alone with yield and e.r. on the next line)
- yield_format: {value}% (crops 02 and 03; crop 01 writes '{value}% yield', set in reaction_scheme)
- conditions_split: reagents_above_solvent_below
- substrate_layout: None (only one-component schemes in the crops)
- abbreviate_groups: CF3, TMS (both meet the two-crop rule: CF3 in crops 02 and 04, TMS in crops 02, 04 and 06)
- aromatic_rings: kekule
- new_bond_color: None (no new-bond colouring)
- substrate_colors: None
- highlight_fill: None (teal #CCE6E6 disc in crop 01; grey background panels in crop 03, #F0F0F0 behind the scheme and #F7F7F7 behind the catalyst; no agreement)
- reagent_text_color: #000000
- arrow_style: plain
- show_plus_sign: None (not seen)

Notes:

- yield_format: crop 01 writes '{value}% yield'; the reaction_scheme section carries that value.
- abbreviate_groups: one-crop groups are not set at top level. tBu (crop 03), OMe (crop 02), OBn (crop 03), CN (crop 02) and TBSO (crop 02) each appear in one crop. nHex (crop 05) and C2F5 (crop 02) are not in the abbreviation table. OTMS in crop 02 reads through TMS.
- catalyst_arc_colour: steel-blue #457898 in crops 04 and 06; black in crops 03 and 05. Not a top-level feature; see figure_types.
- compound_label_color: energy-profile species labels are navy (crop 07), recorded in the energy_profile signature features, because that section has no compound-label colour key.

## Signature features

- catalyst and reagent above the arrow; solvent with molarity, temperature and time below, e.g. 'Toluene (0.2 M)' over 'T (°C), 24 h'
- product label with yield and e.r. stacked below it, e.g. '6, 91%' then '98:2 e.r.' (crop 02); crop 03 sets the label alone on one line and yield and e.r. on the next
- catalyst aryl variants 2 to 5 drawn with a blue #456A98 dot above and a gold #DEC27D dot below (crop 02)
- light teal #CCE6E6 disc behind the key product in overview figures (crop 01)

## Evidence crops

- evidence/list_group-01.png: Figure 1a,b, List et al., Nature 2023
- evidence/list_group-02.png: Figure 2 top, List et al., Nature 2022
- evidence/list_group-03.png: Figure 3, List et al., Nature 2024
- evidence/list_group-04.png: Figure 4a, List et al., Nature 2022
- evidence/list_group-05.png: Figure 4e, List et al., Nature 2024
- evidence/list_group-06.png: Figure 4d, List et al., Nature 2022
- evidence/list_group-07.png: Figure 4e, List et al., Nature 2023

## Figure types

### reaction_scheme

Conventions:

- yield_format: {value}% yield
- selectivity_format: e.r. = {value}
- highlight_fill: #CCE6E6
- variation_color: None

Signature features:

- yield, d.r. and e.r. stacked to the right of the product: '76% yield', 'd.r. > 20:1', 'e.r. = 99:1'
- teal #CCE6E6 disc behind the key product, inside a grey #ECECEC backing around the overview scheme

Crops: evidence/list_group-01.png

Notes: one crop (crop 01); the yield format, the teal disc and the grey backing are read from that single unambiguous crop. The section value overrides the top-level yield format.

### substrate_scope

Conventions:

- scope_layout: grid
- variation_color: None
- yield_format: {value}%
- selectivity_format: {value} e.r.
- conditions_position: scheme_on_top
- highlight_fill: None

Signature features:

- bold number centred under the structure; yield and e.r. on the lines below (crop 02: yield on the label line, '6, 91%', then e.r.; crop 03: label alone, then yield and e.r. on one line)
- category titles centred between thin grey horizontal rules, e.g. 'Aliphatic ketones' (crop 02); crop 03 has a left-aligned plain title and no rules
- footnote letters as superscripts after the yield (crop 02) or on the compound label (crop 03, 3k^a)

Crops: evidence/list_group-02.png, evidence/list_group-03.png

Notes: both crops agree on the e.r. format ('{value} e.r.'). highlight_fill stays null: the grey panel in crop 03 is a two-tone background (#F0F0F0 behind the scheme, #F7F7F7 behind the catalyst), not a highlight, and crop 02 has none.

### mechanism

Conventions:

- curved_arrow_color: None
- curved_arrow_weight: None
- show_lone_pairs: False
- formal_charge_style: circled
- intermediate_label_style: bold_number
- ts_marker: bracket_double_dagger
- highlight_fill: #EFEFEF

Signature features:

- TSs in square brackets with a double dagger at top right
- free energies in blue #0000FF in parentheses after bold labels
- hydrogen bonds as dashed black lines
- products in purple #800080, disfavoured path marked with a red cross
- IDPi catalyst drawn with steel-blue #457898 backbone arcs; no substituent dots in this crop

Crops: evidence/list_group-04.png

Notes: computed mechanism without curved arrows (crop 04, one crop). Grey #EFEFEF highlight boxes sit behind the ketone at the TS1 and TS1' positions. Labels are bold prefix plus number (TS0, INT1, TS1', INT2); the schema has no bold alphanumeric value, so bold_number is the nearest, and this is a schema limit.

### catalytic_cycle

Conventions:

- cycle_shape: open_arc
- cycle_arrow_color: #000000
- catalyst_color: None
- center_label: False
- step_names: True
- intermediate_label_style: bold_roman
- curved_arrow_color: None
- highlight_fill: #F9F9F9

Signature features:

- large black arcs; substrates enter and products leave on short curved arrows
- step names in plain text, on grey boxes (#E7E7E7) in crop 06
- catalyst drawn schematically; backbone arcs steel-blue #457898 in crop 06 but black in crop 05
- bracketed intermediates with bold roman labels I-IV (crop 05)

Crops: evidence/list_group-05.png, evidence/list_group-06.png

Notes: roman labels in crop 05 only. catalyst_color is left unset because the two crops disagree (crop 06 steel-blue, crop 05 black). highlight_fill #F9F9F9 is the grey box behind intermediate II in crop 05 (one crop); the crop 06 step-name boxes are #E7E7E7 label backgrounds and are not set here.

### energy_profile

Conventions:

- energy_unit: kcal/mol
- energy_label: None
- level_style: bars_dashed_connectors
- pathway_colors: None
- ts_marker: none
- intermediate_label_style: bold_letter

Signature features:

- short thick black bars joined by thin dashed lines
- bold navy #000086 species labels above, values below each bar
- y axis 'Free energy (kcal mol-1)', x axis 'Reaction coordinate'

Crops: evidence/list_group-07.png

Notes: one crop (crop 07). energy_label is left unset: the y axis reads 'Free energy (kcal mol-1)' and the species values carry no delta symbol, and the schema has no value for an unlabelled energy.
