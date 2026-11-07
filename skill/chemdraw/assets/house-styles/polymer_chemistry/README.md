# polymer_chemistry

Figure house style of Polymer Chemistry (RSC), measured from CC BY figures. Base preset: rsc.

## Sources

- Besenius et al., Polym. Chem. 2025 (1,4-Oxazepan-7-one trifluoroacetate: a modular monomer precursor for functional and biodegradable poly(amino esters)). DOI 10.1039/d5py00522a. Licence CC BY 3.0.
- Konkolewicz et al., Polym. Chem. 2026 (Vinyl ether maleic acid block copolymers for tunable lipid nanodiscs). DOI 10.1039/d5py00767d. Licence CC BY 3.0.
- Zuhorn et al., Polym. Chem. 2025 (Solvent and temperature effects in photoiniferter RAFT polymerisation of PEG methacrylate). DOI 10.1039/d5py00300h. Licence CC BY 3.0.
- Kodger et al., Polym. Chem. 2022 (Linear-bottlebrush-linear triblock copolymer towards architecturally tunable soft materials). DOI 10.1039/d2py00841f. Licence CC BY 3.0.
- Maynard et al., Polym. Chem. 2026 (Biomolecule-polymer conjugates by organometallic bioconjugation and ATRP). DOI 10.1039/d6py00714g. Licence CC BY 3.0.

## Measurements

- Bond length / atom-label cap height: 2.2 (median; crop 01 about 1.6, crop 02 2.5, crop 06 2.2)
- Line width / bond length: 0.10 (median; crop 01 0.11, crop 02 0.10, crop 06 0.07)
- Bold wedge width / bond length: None
- Arrow length / bond length: 7.0 (median; crop 01 19, crop 02 4.3, crop 06 7.0)

The short step arrows in crop 05 and the concept arrow in crop 07 are not reaction-arrow measurements and are not in the medians.

## Conventions

- compound_label_face: None (plain subscripted names in crop 02, bold black names (VEMA-block-AA) in crop 03; most polymer schemes carry no compound numbers)
- compound_label_color: None
- compound_label_italic_suffix: None
- yield_placement: None (polymerisation schemes give no yields; the only yields are in the caption of crop 02)
- yield_format: None
- conditions_split: reagents_above_solvent_below (crop 03 has no solvent below the arrow; see notes)
- substrate_layout: inline_plus (crop 06 places its monomer and Au reagent above the arrows; see notes)
- abbreviate_groups: ['CF3'] (CF3 in crops 01 and 02; Boc only in crop 02, below the two-crop threshold)
- aromatic_rings: kekule
- new_bond_color: None
- substrate_colors: None (monomer colour coding only in crop 03)
- highlight_fill: None
- reagent_text_color: #000000
- arrow_style: plain
- show_plus_sign: True (crop 06 has no plus because its monomer sits above the arrow; see notes)

Top-level conventions describe reaction schemes: crops 01, 02, 03, 05 and 06. The mechanism (crop 04) and the concept panel (crop 07) are outside them.

## Signature features

- organocatalysts drawn as full structures above the arrow, with the initiator BnOH, solvent and temperature as text below (crop 01); the Au catalyst drawn above the arrow with AgSbF6 and solvent as text below (crop 06)
- polymers drawn as one repeat unit in round brackets with a plain subscript n (m and n in the block copolymers) or the degree of polymerisation (30, 60) at the lower right (crops 01, 03, 05, 06)
- variable side chains given as an R = list of wavy-bond fragments under the product (crops 01, 06; boxed in 06)
- monomers and the matching segments of the product coloured the same in block-copolymer schemes (crop 03)
- compound names such as OxP with subscript Boc written as plain text, not bold numbers (crop 02)

## Figure types

### polymer

Conventions:

- repeat_bracket: round
- highlight_fill: None
- variation_color: None

Signature features:

- repeat unit in round brackets crossing the backbone bonds, with n (m and n in block copolymers) or the DP as a subscript at the lower right of the closing bracket (crops 01, 03, 05, 06)
- end groups drawn explicitly on both sides (BnO and OH, n-Bu and SiMe2H, initiator and Br) (crops 01, 05, 06)
- block copolymer cartoons: PS blocks red #C80000, PDMS grafts and the end-capped pre-polymer blue #0050D0 wavy chains, the soft PDMS backbone black, functional pendants as magenta #F800F8 dots (crop 05)
- monomer colours carried into the polymer segments: maleic anhydride blue #1010F8, vinyl ether red #F80000, butyl acrylate magenta #F810F8, RAFT end group olive #98A030 (crop 03)

Crops: evidence/polymer_chemistry-01.png, evidence/polymer_chemistry-03.png, evidence/polymer_chemistry-05.png, evidence/polymer_chemistry-06.png. variation_color left null: colour coding marks blocks, not substrate variation

### reaction_scheme

Conventions:

- yield_format: None
- selectivity_format: None
- highlight_fill: None
- variation_color: None

Signature features:

- organocatalysts drawn as structures above the arrow, two catalysts separated by a slash (crop 01)
- bracketed step numbers [1], [2] to the left of the reagent stack (crop 02)
- rows marked with bold panel letters a) b) (crop 02) or A B C (crop 03)
- substituent options listed as R = with wavy-bond fragments, boxed in crop 06

Crops: evidence/polymer_chemistry-01.png, evidence/polymer_chemistry-02.png, evidence/polymer_chemistry-03.png, evidence/polymer_chemistry-06.png. no yields on polymerisation schemes

### mechanism

Conventions:

- curved_arrow_color: None
- curved_arrow_weight: None
- show_lone_pairs: False
- formal_charge_style: None
- intermediate_label_style: none
- ts_marker: none
- highlight_fill: None

Signature features:

- each mechanistic step in its own rounded rectangle with a coloured outline and a matching coloured title above: blue #4068A8, orange #F89040, green dashed (crop 04)
- equilibria drawn with long half-headed double arrows; radicals as dots; monomer addition as a curved arrow labelled M (crop 04)
- chains abbreviated as Pm and Pn, the RAFT agent Z group as Z (crop 04)

Crops: evidence/polymer_chemistry-04.png. one crop; the propagation step carries one curved arrow from the radical to M, and the equilibria are half-headed arrows

### concept_panel

Conventions:

- panel_label_style: bold_lowercase
- comparison_layout: stacked_rows
- this_work_color: #004880
- background_fill: None
- highlight_fill: None
- variation_color: None

Signature features:

- a) Previous work and b) This work as bold italic navy #004880 headers, stacked (crop 07)
- macromolecules and biomolecules as rounded pills: PEG green, ATRP Polymer blue, Biomolecule grey, each with a gradient (crop 07)
- claim text in green italics #2A9068 between converging graft-from and graft-to lines (crop 07)

Crops: evidence/polymer_chemistry-07.png. one crop

## Evidence crops

- evidence/polymer_chemistry-01.png: Scheme 1, Besenius et al., Polym. Chem. 2025
- evidence/polymer_chemistry-02.png: Figure 1, Besenius et al., Polym. Chem. 2025
- evidence/polymer_chemistry-03.png: Scheme 1, Konkolewicz et al., Polym. Chem. 2026
- evidence/polymer_chemistry-04.png: Scheme 1, Zuhorn et al., Polym. Chem. 2025
- evidence/polymer_chemistry-05.png: Figure 1, Kodger et al., Polym. Chem. 2022
- evidence/polymer_chemistry-06.png: Figure 2a, Maynard et al., Polym. Chem. 2026
- evidence/polymer_chemistry-07.png: Scheme 1, Maynard et al., Polym. Chem. 2026
