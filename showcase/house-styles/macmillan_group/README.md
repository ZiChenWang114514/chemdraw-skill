# macmillan_group

Reaction-scheme house style of the MacMillan group (Princeton University), measured from open-access figures. Base preset: acs1996. The card's measured values are recorded for reference; the drawing code uses the acs1996 preset and does not read them.

## Sources

- MacMillan et al., J. Am. Chem. Soc. 2026 (A general photoredox platform for the hydroarylation of olefins). DOI 10.1021/jacs.6c14333. Licence CC BY 4.0.
- MacMillan et al., J. Am. Chem. Soc. 2026 (Oxyalkylation of alkenes via triple radical sorting). DOI 10.1021/jacs.6c03814. Licence CC BY 4.0.

## Measurements

- Bond length / atom-label cap height: 2.25 (crop 01 2.30, crop 02 2.22)
- Line width / bond length: 0.055 (crop 01 0.054, crop 02 0.060)
- Bold wedge width / bond length: None
- Arrow length / bond length: 5.2 (crop 02 about 5.25; crop 03 arrow measures 132 px, its bond not re-measured)
- Label font: Helvetica (near-identical face to Arial; informational, the drawing code uses the preset's Arial)

## Conventions

- compound_label_face: bold
- compound_label_color: #000000
- compound_label_italic_suffix: False
- yield_placement: after_product_label (number and yield on one line, e.g. "6, 76% yield")
- yield_format: {value}% yield
- conditions_split: reagents_above_solvent_below (crop 02: catalysts above the arrow, t-AmOH and 450 nm LEDs, 4h below; crop 03: catalyst icons above, scale below)
- substrate_layout: inline_plus
- abbreviate_groups: ['Boc', 'Cbz', 'Me', 'Et', 'TMS', 'OMe'] (Ar is drawn in crops 02 and 03 but is not in the abbreviation table)
- aromatic_rings: kekule
- new_bond_color: #024F8B (new C-O bond; crop 02 #00508D, crop 03 #024F8A). The new C-Me bond from the methyl radical source is purple (#58428A) and is not covered by this value.
- substrate_colors: None (crop 02 colours the source labels, not the structures)
- highlight_fill: #D5D5D5 (grey halo behind the new bonds in crops 02 and 03)
- reagent_text_color: None (crop 02 conditions are black, crop 03 scale line is blue; the crops disagree)
- arrow_style: plain
- show_plus_sign: False

## Signature features

- yield line such as 6, 76% yield with bold number, comma and the word yield (crops 01, 02)
- new C-O bond and transferred D drawn in dark blue; the new C-Me bond from the methyl radical source is purple (crops 02, 03; transferred D in crop 01)
- substrates placed side by side with no plus sign (crops 01, 02, 03)
- italic descriptor text under starting materials (crops 01, 02)

## Figure types

- reaction_scheme (crops 02, 03): catalyst icons (Ir, light bulb, Ni discs) above the arrow in the gram-scale scheme (crop 03 only; crop 02 names the catalysts in text)
- substrate_scope (crops 01, 02): grid layout; substrate pairs joined by a light-blue curved double-headed arrow (crop 01 only)

## Evidence crops

- evidence/macmillan_group-01.png: Scope figure, unactivated alkenes rows, MacMillan et al., J. Am. Chem. Soc. 2026 (substrate_scope)
- evidence/macmillan_group-02.png: Scope figure, top scheme, MacMillan et al., J. Am. Chem. Soc. 2026 (reaction_scheme and substrate_scope)
- evidence/macmillan_group-03.png: Scope figure, gram-scale scheme, MacMillan et al., J. Am. Chem. Soc. 2026 (reaction_scheme)
