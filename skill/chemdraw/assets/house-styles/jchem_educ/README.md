# jchem_educ

Teaching-figure house style of the Journal of Chemical Education (ACS), measured from CC BY articles. Base preset: acs1996.

## Sources

- Deufel, van Gemmeren et al., J. Chem. Educ. 2024 (Deuteration of arenes via Pd-catalyzed C-H activation: a lesson in nondirected C-H activation). DOI 10.1021/acs.jchemed.4c00270. Licence CC BY 4.0.
- Birchall, Clark, Biagini et al., J. Chem. Educ. 2021 (Himic anhydride: a retro Diels-Alder reaction for the organic laboratory and an accompanying NMR study). DOI 10.1021/acs.jchemed.1c00661. Licence CC BY 4.0.
- Elliott et al., J. Chem. Educ. 2026 (Exploring the interface of hyperconjugation and polarizability). DOI 10.1021/acs.jchemed.6c00708. Licence CC BY 4.0.
- Elliott et al., J. Chem. Educ. 2026 (Rethinking the nature and extent of inductive effects in organic compounds). DOI 10.1021/acs.jchemed.6c00141. Licence CC BY 4.0.

## Measurements

- Bond length / atom-label cap height: 2.2. Crops 01, 03 and 06 give 2.14 to 2.28; crop 02 gives 2.46 (spread 2.1 to 2.5).
- Line width / bond length: 0.05. Crops give 0.047 to 0.054.
- Bold wedge width / bond length: 0.24. Crops 02 and 03 give 0.22 and 0.25.
- Arrow length / bond length: 9.2. No majority across crops: the single plain arrow in crop 01 measures 9.25, the equilibrium pair in crop 02 measures 5.4, and the resonance arrow in crop 03 measures 1.6. The value kept is the single plain reaction arrow.

## Conventions

- compound_label_face: None (bold numbers in crop 01 only among the reaction-scheme crops; crop 02 has names, not numbers)
- compound_label_color: #000000
- compound_label_italic_suffix: None (italic d suffix in crop 01 only among the reaction-scheme crops)
- yield_placement: None (no crop shows a yield; the earlier 72% note was wrong)
- yield_format: None
- conditions_split: None (reagents above and HFIP and D2O below in crop 01 only)
- substrate_layout: None (inline plus in crop 02 only)
- abbreviate_groups: None (tBu and CF3 in crop 01 only)
- aromatic_rings: None (Kekule rings in crop 01 only)
- new_bond_color: None
- substrate_colors: None
- highlight_fill: None
- reagent_text_color: None (ligand colours in crop 01 only)
- arrow_style: plain (thin, not bold; crops 01 and 02 agree)
- show_plus_sign: None (plus sign in crop 02 only)

## Signature features

- thin plain line arrows, not bold (crops 01, 02); crop 02 uses paired equilibrium arrows for a reversible step
- reaction name above the arrow in plain Arial (crop 02); reagents above the arrow with the ligand names in bold (crop 01)
- ligand names in bold, coloured L1 teal #005474 and L2 orange #D87C5C (crop 01)
- bold compound numbers with the isotopologue suffix in italic, as 1-dx and 2-dx (crop 01)
- endo/exo prefixes in italic in the plain name labels under the structures (crop 02)

## Figure types

### reaction_scheme

Conventions:

- yield_format: None
- selectivity_format: None
- highlight_fill: None
- variation_color: None

Signature features:

- thin single-line arrow for reactions, about 9 bond lengths long in crop 01; equilibrium half-arrows for reversible steps, about 5 bond lengths long in crop 02
- reaction name above the arrow in plain Arial (crop 02); reagents above and solvent below the arrow, with the ligand names in bold (crop 01)
- ligand names in bold, coloured L1 teal #005474 and L2 orange #D87C5C, with Pd(OAc)2 in black (crop 01)
- auxiliary structure (HFIP) drawn below the arrow in light grey, with D2O in bold (crop 01)

Crops: evidence/jchem_educ-01.png, evidence/jchem_educ-02.png

Notes: no yields on either crop's arrows; the solvent, ligand and HFIP features rest on crop 01 alone; the arrow length spread (5.4 to 9.2 bond lengths) is recorded under the top-level measured notes

### mechanism

Conventions:

- curved_arrow_color: #000000
- curved_arrow_weight: bond
- show_lone_pairs: False
- formal_charge_style: circled
- intermediate_label_style: none
- ts_marker: None
- highlight_fill: None

Signature features:

- each resonance or hyperconjugation pair enclosed in square brackets joined by a double-headed arrow
- curved arrows black, same weight as bonds, full arrowheads, starting on the bond being broken
- charges as circled + and - signs; lone pairs not drawn
- a coloured caption under each pair naming the effect, blue #4C5C98 Arial

Crops: evidence/jchem_educ-03.png

Notes: rests on one crop; the circled charge also appears in crop 04. No transition states drawn

### stereo_model

Conventions:

- model_style: perspective_3d
- ts_marker: None
- highlight_fill: None
- variation_color: None

Signature features:

- orbitals drawn as outlined lobes on the skeletal model; the interacting bond lobe shaded grey (crop 04)
- each sp3 carbon of the chain carries one bold wedge H and one hashed H, and the left terminal carbon also has a plain H; bonds of interest labelled a and b in orange-red (crop 05)
- explanations as plain text joined to the model by thin leader lines (crop 04 only)

Crops: evidence/jchem_educ-04.png, evidence/jchem_educ-05.png

Notes: model_style and the leader-line feature rest on crop 04 alone. Crop 05 is a planar zigzag with wedge and hash bonds, not a perspective model, and has no text or leader lines. No CC BY J. Chem. Educ. article found in Europe PMC with a chair, Newman, Fischer, Zimmerman-Traxler or Felkin-Anh drawing; only perspective wedge/hash models are evidenced

### assignment_panel

Conventions:

- numbering_style: none
- shift_color: #E43800
- highlight_fill: #ECECEC

Signature features:

- chemical shifts written straight onto the skeleton next to each carbon in orange #E43800, no atom numbers (crop 06)
- deuterium percentages per position in bold teal #006C88, structure on a light grey #ECECEC box (crop 07)
- position letters X and A in teal with a teal dot on carbon A (crop 07)

Crops: evidence/jchem_educ-06.png, evidence/jchem_educ-07.png

Notes: shift_color from crop 06; crop 07 uses teal for %D values, so the colour varies by article. highlight_fill #ECECEC rests on crop 07 alone (the grey box behind the structure). Crop 07 shows no yield and no DTot values, and its lack of atom numbers agrees with numbering_style none

### concept_panel

Conventions:

- panel_label_style: none
- comparison_layout: None
- this_work_color: None
- background_fill: None
- highlight_fill: None
- variation_color: None

Signature features:

- diagram with colour-filled legend boxes: grey #C2CCCD, teal #80DADB, pink #F8C2CF, each with a bold title line whose colour differs by box (crop 08)
- category names in white text on ellipses: AMLA / CMD in dark slate #2D3D3D, BIES / eCMD in navy #023554 (crop 08)
- small structures with black italic captions underneath (crop 09)
- partial charges written in red (δ−, δ+, δδ+) on the structures, and bond-dipole arrows in blue, double-headed with crossing ticks (crop 09)
- take-home statements in blue #0000FC plain text as footnote lines below the panel (crop 09)

Crops: evidence/jchem_educ-08.png, evidence/jchem_educ-09.png

Notes: neither crop has panel letters; layouts differ (square diagram vs side-by-side pair). The legend title lines are dark slate, navy and red in crop 08, one per box

## Evidence crops

- evidence/jchem_educ-01.png: Figure 3 (reaction rows), Deufel, van Gemmeren et al., J. Chem. Educ. 2024
- evidence/jchem_educ-02.png: Scheme 1, Birchall, Clark, Biagini et al., J. Chem. Educ. 2021
- evidence/jchem_educ-03.png: Figure 5, Elliott et al., J. Chem. Educ. 2026
- evidence/jchem_educ-04.png: Figure 3, Elliott et al., J. Chem. Educ. 2026
- evidence/jchem_educ-05.png: Figure 15 (structure only), Elliott et al., J. Chem. Educ. 2026
- evidence/jchem_educ-06.png: Figure 4, Elliott et al., J. Chem. Educ. 2026
- evidence/jchem_educ-07.png: Figure 4 (structure box), Deufel, van Gemmeren et al., J. Chem. Educ. 2024
- evidence/jchem_educ-08.png: Figure 2, Deufel, van Gemmeren et al., J. Chem. Educ. 2024
- evidence/jchem_educ-09.png: Figure 16, Elliott et al., J. Chem. Educ. 2026
