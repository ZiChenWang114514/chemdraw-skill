# baran_group-02: route 29 to 4 (Figure 3 middle band)

## Source

Baran et al., *J. Am. Chem. Soc.* 2024, "Simplified modular access to enantiopure 1,2-aminoalcohols via Ni-electrocatalytic decarboxylative arylation". DOI [10.1021/jacs.3c14119](https://doi.org/10.1021/jacs.3c14119). Licence CC BY 4.0. Evidence crop: `evidence/baran_group-02.png` (Figure 3, middle band; the saved crop is scaled to 0.52 of the full-resolution figure).

## Figure type

`reaction_scheme`. The card has no `figure_types` section, so the top-level conventions apply.

## What is reproduced

The sequential route on the crop, drawn with the `baran_group` house style:

- 29 (4-chloro-3-iodophenol) plus 2-benzyloxyethyl bromide, K2CO3, DMF, 99%, to 12
- 12 to 30 under the electrolytic decarboxylative arylation conditions (11 (cis) 1.5 eq, NiCl2 DME, bpy, AgNO3, nBu4NBF4, DMA; (+)Mg/(-)RVC, 4 F/mol), 65% (dr > 20:1)
- 30 to 31 (TFA/DCM/H2O, then Boc2O), 92%
- 31 to 4 (GSK-656 as the free amine): the three operations (1) nBuLi, B(OMe)3, toluene, 59%; (2) Pd/C, H2; (3) HCl (2 M), 95%, with 33% overall from 29 under the arrow

The teal box behind the target is drawn as a fill on the boron-containing seven-membered ring of 4.

SMILES were read from the crop and checked with RDKit (parse and molecular formula). No RDKit output is stored in the case folder, so that check is unverified. OCSR was not run.

- 29 `Oc1ccc(Cl)c(I)c1`
- BrCH2CH2OBn `BrCCOCc1ccccc1`
- 12 `C(c1ccccc1)OCCOc1ccc(Cl)c(I)c1`
- 30 `CC(C)(C)C1OC(CN1C(=O)OC(C)(C)C)c1cc(OCCOCc2ccccc2)ccc1Cl` (no relative configuration in the SMILES)
- 31 `CC(C)(C)OC(=O)NCC(O)c1cc(OCCOCc2ccccc2)ccc1Cl` (no stereo)
- 4 `NCC1OB2OCCOc3ccc(Cl)c1c23` (free amine, no stereo, no HCl)

## Replica

Rendered with ChemDraw (`rendered.png`, from `brief.json` with `max_width` 1100). The first try at the default `max_width` 504 wrapped the route onto four rows and is not kept. The second try is reported as three rows; rendered.png shows two. The draw report (readback matched, 7 structures, checks passed, native rendered) is claimed but not stored in the case folder, so it is unverified.

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| compound_label_face bold | bold labels 29, 12, 30, 31, 4 | regular weight at this scale (the brief has no label-face field, so the style's bold is not applied) | no |
| compound_label_color #000000 | black | black | yes |
| yield_format {value}% | 99%, 92%, 65%, 33% overall | 99%, 92%, 65%, 33% overall | yes |
| yield_placement (under arrow in multistep) | yields under each arrow | 99%, 92% and 65% under the arrow; 33% overall centred under the arrow, but offset to the lower right in the paper | no (partial) |
| conditions_split (reagents above, solvent below) | step 2 has nBu4NBF4 and DMA above the arrow with the reagents; electrodes and current below | step 2 has DMA above the arrow, as in the paper; the card rule (solvent below) is not followed | no (follows the paper, contradicts the card rule) |
| substrate_layout inline_plus | bromide written above the arrow as a reagent, no plus; Br on the left, OBn on the right | bromide drawn as a substrate with a plus; OBn on the left, Br on the right | no |
| abbreviate_groups (OBn, Boc, tBu shown) | OBn, Boc, tBu | OBn, Boc, tBu | yes |
| aromatic_rings kekule | Kekule rings | not verifiable at this resolution | no (unverified) |
| new_bond_color #8B1A1A | red hashed C-C bond formed in step 2 (aryl to oxazolidine C5) | red colour on the O-CH2 ether bond formed in step 1; the C-C bond formed in step 2 stays black because 11 is text only and atom mapping is incomplete | no |
| highlight_fill #BBF6F4 (teal box behind target) | teal box around the whole of 4 | teal fill inside the 7-membered ring only | no |
| reagent_text_color #000000 | black | black | yes |
| arrow_style plain | plain arrows | plain arrows | yes |
| show_plus_sign | no plus sign in the paper route | plus shown between 29 and the bromide | no |
| signature: light grey panel #EDEDEF | grey background | white page | no |
| signature: navy title bar #0C0C84 with white bold title | plain italic black title on grey, no bar | title key not drawn | no |
| signature: blue lightning bolt on the electrolysis arrow | blue circle with white bolt | absent | no |
| signature: blue bold notes #0C0CFC | "[1.0 mmol]", "[1.8 g scale, Ag-free]", "49% (dr > 20:1)", "[This work] 6 steps" | absent | no |
| signature: compound labels bold, close to atom-label size | bold, near atom-label size | regular weight; size not verified | no |

Matched: 5 of 18 on audit (the replicator claimed 12 of 18; see Audit).

## Differences from the paper

- Layout: the paper is one row. At `max_width` 1100 the replica wraps onto two rows in rendered.png (29 to 31 on the first row, 31 to 4 on the second), so 31 appears twice.
- Stereochemistry is absent. The cis relative configuration of 30 (hashed bond to the aryl, wedge on the tBu carbon) and the configuration of 4 are not in the SMILES.
- 4 is drawn as the free amine. The HCl salt and the "GSK-656 (4)" name are not drawn.
- 11 (cis) is given as text above the arrow, so step 2 is drawn without its carboxylic acid partner (see Tool gaps).
- The second yield (49%, 1.8 g scale, Ag-free) and the blue annotations are omitted.
- The "Commercial" and "Previous" labels, and "[This work] 6 steps", are omitted.
- The above block of step 2 runs through the arrow line. The nBu4NBF4 line is struck through in the render.
- The title given in the brief is not drawn.

## Tool gaps

- draw_figure has no steps-per-row or single-row option. A four-step sequential route gave four rows at `max_width` 504 and three rows at 1100. Only `max_width` is available.
- The above block is centred on the arrow, so a six-line block (step 2) runs through the arrow line.
- Hashed new-bond style (red hashed wedge) is not available. The tool only colours the new bond.
- new_bond_color follows atom mapping, not the paper. It coloured the O-CH2 ether bond in step 1 and left the C-C bond of step 2 black ("atom mapping is incomplete").
- A reagent that is consumed in the transformation but written as text (the carboxylic acid 11, B(OMe)3) makes the step unbalanced in the draw report ("reactants lack C12H22NO3", "reactants lack B"). The draw report flags it and nothing is added. There is no way to declare a text-only partner.
- No electrolysis symbol (blue circle with lightning bolt) on the arrow.
- No per-line colour for conditions or notes (blue annotations).
- No background panel (grey #EDEDEF) and no title bar. The brief title is not drawn.
- The highlight fill covers the largest ring only, not a box behind the whole molecule.
- A multistep sequence on one arrow, with per-step yields, has one yield field. The per-step yields are text only.

## Audit

Checked against reference.png, rendered.png, brief.json and the card toolkit/cdxml_toolkit/publication/house_styles/baran_group.json. A row marked "yes" was tested against the images, and a row that could not be confirmed at this resolution was marked "no".

Overclaims corrected in the table and text:
- Compound labels are regular weight in rendered.png. The brief has no label-face field, so the style's bold is not applied, and the "bold, near atom-label size" signature is not matched either.
- The paper's step 1 bromide is a reagent above the arrow, with no plus sign. The replica draws it as a substrate with a plus, in reversed orientation (OBn on the left). The earlier row "paper: plus between 29 and the bromide" was wrong.
- The paper's step 2 puts DMA above the arrow, which contradicts the card's solvent-below rule. The replica follows the paper, so it does not match the card convention. The "see card_errors" pointer referred to no section in this file and has been removed.
- Yield placement is partial (see table).
- Kekule rings and the red new bond on the step 1 ether bond could not be confirmed on rendered.png. The new_bond_color row stays "no" either way.
- The layout is two rows at max_width 1100, not three.
- The draw report, readback and RDKit checks are not stored in the case folder and are unverified.

Corrected count: 5 of 18 (compound label colour, yield format, abbreviations, reagent text colour, plain arrows). The replicator claimed 12 of 18.

Not in the table, so not claimed and not checked: proportions (bond length, cap height, line width, arrow length against the card's measured ratios). They should not be counted as matched.

Tool gaps the replicator missed:
- The house style's bold label face cannot be set per figure: the brief has no label-face or label-size field.
- A structure cannot be placed above or below the arrow as a reagent, because the above and below fields take text only. This is why step 1 has the bromide as a substrate with a plus.
- Stereo: the brief SMILES carry no stereo and the brief has no wedge or hash field. Whether stereo SMILES would give the paper's hashed bonds was not tested, so this is a probable gap, not a confirmed one.
- The card rules for conditions_split (step 2) and show_plus_sign (step 1) contradict the paper, so applying the card convention cannot reproduce the paper's layout.
