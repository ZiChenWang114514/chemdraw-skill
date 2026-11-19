# ACS Chem. Biol.: CuAAC click assembly of LIMK PROTACs (Figure 1C, left part)

Source: Azeez et al., "Discovery and development of a potent LIMK2 isoform-specific degrader", *ACS Chem. Biol.* 2026. DOI: [10.1021/acschembio.6c00137](https://doi.org/10.1021/acschembio.6c00137). Licence: CC BY 4.0 (from the house-style card). The reference crop is `reference.png`, reproduced under that licence. The full panel was read from the paper's Figure 1 image (`cb6c00137_0001.jpg`) to resolve the structures.

Drawing style: the `acs_chem_biol` house style (card `toolkit/cdxml_toolkit/publication/house_styles/acs_chem_biol.json`, base preset ACS Document 1996), figure types `reaction_scheme` and `biomolecule`.

## What is reproduced

One of the three CuAAC arms of the reaction in the crop: the PD-alkyne (1-[2-methyl-3-(prop-2-ynyloxy)phenyl]dihydrouracil) plus the LIMKi3 azide gives the PD click PROTAC, drawn as a single step with the CuAAC arrow above.

The crop shows three E3 alkynes (PD, Thal, VH032) stacked on the left, one LIMKi3 azide, a thick arrow labelled "CuAAC – click reaction" and one product, cut off at the right edge of `reference.png`; the other products are not in the crop. This replica draws only the PD arm. The Thal and VH032 arms are not drawn.

Structures (SMILES in `brief.json`):

| ID | Structure | How it was read |
| --- | --- | --- |
| PD | `C#CCOc1cccc(N2CCC(=O)NC2=O)c1C` | read from the figure: 1-aryl dihydrouracil, aryl = 2-methyl-3-propargyloxyphenyl |
| LIMKi3N3 | `[N-]=[N+]=NCCC(=O)Nc1ncc(s1)-c1cc(C(F)F)nn1-c1c(Cl)cccc1Cl` | LIMKi3 core read from the figure (2,6-dichlorophenyl pyrazole with CHF2, 5-thiazolyl, 2-amide). The paper text says the solvent-exposed isobutyramide is the exit vector, so the azide replaces the isobutyramide. The figure shows N3-(CH2)n-C(=O); the replica uses n = 2 (3-azidopropanamide). |
| PDP | `C(c1cn(CCC(=O)Nc2ncc(s2)-c2cc(C(F)F)nn2-c2c(Cl)cccc2Cl)nn1)Oc1cccc(N2CCC(=O)NC2=O)c1C` | click product of PD and LIMKi3N3, 1,4-triazole (alkyne CH2 on C4, azide CH2 on N1) |

All SMILES were checked with RDKit (formulae and stereocentres) before drawing.


## Replay

`brief.json` is the single-step brief. `replay.py` runs `draw_figure` on it offline and writes `figure.cdxml` and `validation.json`. `rendered.png` was drawn from the same brief with `cdx.py draw ... --render`.

The brief uses the brief-level styling options: `abbreviate: ["N3"]` draws the azide as an N3 label, `bond_colors` colours the two linker bonds between the azide and the amide carbonyl, and the condition text sits in `below`.

## Convention table

Card conventions claimed for crop 06 (`reaction_scheme`, `biomolecule`, and top-level), checked against the crop and the replica.

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| reaction_scheme: step name at the arrow | "CuAAC – click reaction" below the arrow | same text below the arrow | yes |
| reaction_scheme: variation_color #D2107A | linker (CH2)n in pink, close to #EE3E77; #D2107A not present | linker bonds in #EE3E77 | no (card value not seen in this crop) |
| biomolecule: PROTAC linkers with variable (CH2)n in pink #EE3E77, two ligands in black | ligands black, (CH2)n pink | ligands black, fixed CH2CH2 linker in #EE3E77 | partly (colour yes, variable n no) |
| top-level aromatic_rings kekule | kekule rings | kekule rings | yes |
| top-level reagent_text_color #000000 | black reagent text | black reagent text | yes |
| top-level compound_label_color #000000 | black compound names | black names | yes |
| top-level arrow_style plain | thick tapered block arrow (card notes crop 06 as the exception) | plain thin arrow | no |
| azide written as N3 | N3 label | N3 label | yes |

Matched 5 of 8 (partial counted as no).

## Differences from the paper

- Only one of the three CuAAC arms is drawn; the paper stacks the PD, Thal and VH032 alkynes on the left with one LIMKi3 azide.
- The paper uses a thick block arrow; the replica uses the card's plain arrow.
- Compound names are bold in the paper and plain in the replica (the card leaves `compound_label_face` null).
- The PD label sits above its structure in the paper and below it in the replica.
- The paper's light-blue rounded group boxes ("E3 alkynes", "LIMKi3 azides") and the rounded panel frame are not drawn.
- The linker is drawn with a fixed length (n = 2) instead of a variable (CH2)n.
- The en dash in "CuAAC – click reaction" renders as a raised minus-like glyph.
- The "+" between reagents is regular weight in the replica and bold in the paper.

## Tool gaps

- No layout for several reagents stacked on the left with one shared partner and several products, as in the paper; a multi-step brief with one shared azide takes the divergent layout and drops the alkynes.
- No way to write a variable repeat unit (CH2)n with a bracket and subscript n on a bond.
- No per-figure bold arrow when the card says `plain`, and no per-species bold compound label when the card leaves the face null.
- No label-position field per species (above or below the structure).
- No grouping boxes around a set of species with a caption, and no bold "+" sign.
- The en dash in condition text renders as a raised minus-like glyph.
