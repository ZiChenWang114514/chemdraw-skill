# oprd_process

Drawing house style of Organic Process Research & Development (ACS), measured from open-access CC BY figures. Base preset: acs1996.

## Sources

- Guthrie, Gupton et al., Org. Process Res. Dev. 2026 (A concise process to lenacapavir sodium: one-pot sequential Heck/Suzuki-Miyaura couplings). DOI 10.1021/acs.oprd.5c00443. Licence CC BY 4.0.
- Lucas, Opatz et al., Org. Process Res. Dev. 2023 (Short and efficient synthesis of the antituberculosis agent pretomanid from (R)-glycidol). DOI 10.1021/acs.oprd.3c00187. Licence CC BY 4.0.
- Gohain, Malan et al., Org. Process Res. Dev. 2023 (Process development for the manufacture of the antimalarial amodiaquine dihydrochloride dihydrate). DOI 10.1021/acs.oprd.3c00205. Licence CC BY 4.0.

## Measurements

- Bond length / atom-label cap height: 2.0 (crop 03: 2.1; crop 05: 1.9)
- Line width / bond length: 0.085 (crop 03: 0.082; crop 05: 0.088)
- Bold wedge width / bond length: None
- Arrow length / bond length: 8.0 (crop 03: 7.3; crop 05: 9.0; mean 8.2)
- Label font: Arial|Helvetica

## Conventions

- compound_label_face: bold
- compound_label_color: #000000
- compound_label_italic_suffix: None (an italic scale after the bold number appears in crop 03 only)
- yield_placement: under_arrow (under the arrow in crops 01, 03 and 05; crop 04 puts endpoint yields beside the final product, crop 08 an inset table)
- yield_format: {value}% (crops 02, 04, 05 and 08 have no space before the percent sign; crop 01 has one and adds the word yield; crop 03 adds labels)
- conditions_split: reagents_above_solvent_below (solvent and temperature below in crops 01 (panel b), 03, 04 and 06; crops 05 and 08 put all conditions above)
- substrate_layout: None (reagents are written over the arrow; no two-partner layout seen twice)
- abbreviate_groups: ['Boc', 'CF3', 'Me', 'NO2', 'OCF3'] (Boc, CF3 and Me in crops 01, 02 and 03; NO2 in crops 04, 05 and 08; OCF3 in crops 05 and 08; OTBS is in crop 05 only and is removed; SO2Me is written as text in the paper but has no entry in the abbreviation table)
- aromatic_rings: kekule
- new_bond_color: None (no reaction-scheme crop colours formed bonds)
- substrate_colors: None (only crop 02, a graphical abstract, and crop 07, a retrosynthesis, colour building blocks)
- highlight_fill: None
- reagent_text_color: #000000
- arrow_style: plain
- show_plus_sign: False (no plus between co-reactants in crops 01 (panel b), 03, 04, 05, 06 and 08; crop 07 is a retrosynthesis and has plus signs between fragments)

## Signature features

- reagent amounts as equivalents and solvent amounts as volumes (2 V, 4 V HOAc) or mL, temperature and time on the last line under the arrow
- non-isolated intermediates drawn in square brackets, sometimes captioned not isolated
- scale stated on the drawing (50 g scale, 1 kg scale, 5 (100mg) in italics after the bold number)
- yield and purity written as text at the end of a route (Yield 66% Purity 99.3%)
- long arrows, about eight bond lengths, carrying several lines of conditions

## Evidence crops

- evidence/oprd_process-01.png: Scheme 1 (previous Gilead route vs this work), Guthrie, Gupton et al., Org. Process Res. Dev. 2026
- evidence/oprd_process-02.png: Graphical abstract, Guthrie, Gupton et al., Org. Process Res. Dev. 2026
- evidence/oprd_process-03.png: Scheme 3 (Suzuki coupling test), Guthrie, Gupton et al., Org. Process Res. Dev. 2026
- evidence/oprd_process-04.png: Scheme 3 (synthesis of 2-bromo-4-nitroimidazole), Lucas, Opatz et al., Org. Process Res. Dev. 2023
- evidence/oprd_process-05.png: Scheme 2 (literature routes to pretomanid), Lucas, Opatz et al., Org. Process Res. Dev. 2023
- evidence/oprd_process-06.png: Scheme 3 (amodiaquine process), Gohain, Malan et al., Org. Process Res. Dev. 2023
- evidence/oprd_process-07.png: Figure 1 (retrosynthesis of lenacapavir), Guthrie, Gupton et al., Org. Process Res. Dev. 2026
- evidence/oprd_process-08.png: Scheme 7 (optimised three-step route, IY table), Lucas, Opatz et al., Org. Process Res. Dev. 2023

## Figure types

### process_route

Conventions:

- step_label_style: None (numbered only in panel a of crop 01)
- step_count_shown: None (crop 02 only)
- yield_format: {value}% yield
- scale_shown: None (crop 04 only)
- highlight_fill: None

Signature features:

- step count at the arrows, '1 step' and '2 steps' in bold (crop 02), with a boxed '3-Step synthesis' summary there
- step labels 'step 1' to 'step 4' under the arrows in panel a of crop 01 (panel b is unlabelled)
- scale on the drawing as plain-text route headers: 50 g scale and 1 kg scale (crop 04 only)
- telescoped intermediates in square brackets, usually numbered in bold (crops 01 and 06); crop 04 adds a 'not isolated' caption
- route endpoints carry yield text: '> 75 % yield' under the final arrow (crop 01), or a text block beside the final product with 'Yield 42%' and 'Purity 98.2%' (crop 04)
- overall yields as '(Overall:57%)' (crop 04) or '70 % overall yield from Frag A' (crop 01)
- old and new process stacked as panels a) Previous work and b) This work separated by a dashed rule (crop 01 only)

Crops: evidence/oprd_process-01.png, evidence/oprd_process-02.png, evidence/oprd_process-04.png, evidence/oprd_process-06.png

Notes: step labels are numbered only in panel a of crop 01, so the value is null. Crop 04 numbers its reagent lines (1. 2.) inside one arrow; crop 06 numbers reagents (1) 2)) and has no step labels. The yield format '{value}% yield' follows crops 01 and 02; crop 04 writes 'Yield {value}% Purity {purity}%' and is the only crop with purity; crop 06 has no yield text.

### reaction_scheme

Conventions:

- yield_format: {value}%
- selectivity_format: None
- highlight_fill: None
- variation_color: None

Signature features:

- reagents with mol % and eq above the arrow; solvent with volumes, time and temperature below
- bold compound number followed by the scale in italics, 5 (100mg)
- inset yield table under the product (IY over 3 steps, one line per protecting group)

Crops: evidence/oprd_process-03.png, evidence/oprd_process-08.png

Notes: each signature rests on one crop: conditions and scale on crop 03, the inset yield table on crop 08. Crop 08 writes its conditions as text above the arrow with no equivalents, volumes, times or temperatures. Crop 03 gives IY labels at the arrow, not a table. Black text in both.

### total_synthesis

Conventions:

- step_label_style: none
- step_count_shown: False
- yield_format: {value}%
- highlight_fill: None
- variation_color: None

Signature features:

- literature routes headed by authors in bold (Read & Fairlamb:, Zhai et al.:)
- yield alone under each arrow, reagents above
- rows wrap with downward arrows at the right edge

Crops: evidence/oprd_process-05.png

Notes: one crop, unambiguous.

### retrosynthesis

Conventions:

- retro_arrow: None (single-headed open block arrow in crop 07; the schema offers only open_double and none)
- disconnection_mark: dashed_line
- disconnection_color: #FF0000 (red stubs on the cut bonds; sampled #FB0000)
- highlight_fill: None
- step_count_shown: False

Signature features:

- disconnected bonds crossed by black dashed lines with red stubs, each named in bold black text (Amide formation, Suzuki-Miyaura coupling, Sonogashira coupling or Heck alkynylation)
- fragments coloured red and blue on both sides of the arrow (red #FF0000 for Frag C, blue #0000FF for Frag A)
- fragments named Frag A to Frag D in bold

Crops: evidence/oprd_process-07.png

Notes: one crop. The dashed disconnection lines are black; the colour is on the stubs at the cut bonds, not on the dashed lines.

### graphical_abstract

Conventions: none (no schema convention is shown clearly enough to add a value)

Signature features:

- route summary with '1 step' and '2 steps' in bold above the arrows
- boxed bullet list under the route (3-Step synthesis, 55% overall yield, No chromatography, Residual Pd < 4.2 ppm)
- building blocks coloured blue, green and red so each can be followed into the product

Crops: evidence/oprd_process-02.png

Notes: one crop, unambiguous. Flat sampled colours are listed in the crop 02 evidence entry of the card.
