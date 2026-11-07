# chemeurj-01 replica

## Source

- Anderson et al., Chem. Eur. J. 2023 (Gold-catalyzed cyclization of yndiamides with isoxazoles via alpha-imino gold Fischer carbenes).
- DOI 10.1002/chem.202302821. Licence CC BY 4.0 (from the card).
- Figure: Scheme 1a-b. Crop: `evidence/chemeurj-01.png` in the card folder.

## Figure type

reaction_scheme

## What is reproduced

Panel a only: the gold-catalysed reaction of yndiamide 1 with 2-chloropyridine N-oxide and MeOH (NuH), giving the amide product with the nucleophile on the alpha carbon. The bracketed alpha-oxo gold Fischer carbene under the arrow (labelled "via", with [Au]+) is not reproduced either, and neither is the "Yndiamides" caption under 1. Panel b (the alpha-imino gold Fischer carbene and the isoxazole and benzisoxazole products 2 and 3) is not reproduced, and so is the bulleted summary box.

Structures as drawn (brief.json, Ts variant):

- Substrate: `Cc1ccc(cc1)S(=O)(=O)N(C)C#CN(C)S(=O)(=O)c1ccc(C)cc1`
- Product: `Cc1ccc(cc1)S(=O)(=O)N(C)C(=O)C(OC)N(C)S(=O)(=O)c1ccc(C)cc1`
- Conditions above the arrow: `[Au] cat., 2-chloropyridine N-oxide, MeOH`

## Stand-in choices

- Both EWG groups are drawn as Ts. The paper uses two different EWG groups, so the regiochemistry of the two nitrogens is not tested.
- The R groups on the nitrogens (teal and purple circles in the paper) are drawn as Me.
- NuH is MeOH, so the alpha carbon carries OMe.
- 2-chloropyridine N-oxide is written as conditions text, because the above and below fields only take text lines.
- Files: `rendered.png` is the Ts variant from `brief.json`, rendered by desktop ChemDraw and downscaled from 1905 px to 1200 px wide.
- A CO2Me variant (scratch `brief2.json`) was not rendered. Two render attempts timed out at 300 s under ChemDraw contention. Its no-render draw succeeded, with layout `linear` and no highlight fill, because the product has no aromatic ring. It is not the case brief.

## Convention table

| convention or signature feature | paper | replica | match |
|---|---|---|---|
| compound label face bold (card) | bold "1" | bold "1" | yes |
| compound label colour #000000 (card) | black | black | yes |
| arrow_style plain (card) | plain arrow with head | plain arrow with head | yes |
| reagent text colour #000000 (card) | generic text black; [Au] and NuH coloured | all text black | partial |
| conditions reagents above arrow (card) | [Au] cat., N-oxide drawn as structure, NuH | three text lines above | partial |
| conditions solvent and time below (card) | none in panel a | none | not exercised |
| yield_format {value}% (reaction_scheme) | no yield in crop 01 | no yield drawn | not exercised |
| substrate_layout inline_plus (card) | one substrate, reagents comma-separated | one substrate | not exercised |
| show_plus_sign true (card) | no plus sign in panel a | no plus sign | not exercised |
| abbreviate_groups Ts, Ph, tBu, OMe (card) | paper uses EWG labels, no OMe | Ts and OMe contracted | not comparable |
| aromatic_rings kekule (card) | panel a has no aromatic ring | Ts rings abbreviated away | not verifiable |
| highlight_fill #E6E6E6 (reaction_scheme convention) | grey box behind panel b products, none in panel a | one stray grey hexagon at upper right, not behind a product | no |
| grey #E6E6E6 box behind products (reaction_scheme signature) | same as above | same as above | no |
| substrate fragments colour-coded and colour kept in product (reaction_scheme signature) | teal and purple circles on the N substituents | none | no |
| new_bond_color null (card) | new C to Nu bond drawn red (about #DD211E) | black | no (the card value is null, so this is a mismatch with the paper, not a card contradiction) |
| substrate_colors null (card) | teal and purple circles on substituents | none | no |
| heteroatom palette colours (card signature) | N blue (about #0080C0) in panel a as well as panel b | N black | no |
| bold sans-serif panel letter (card signature) | "a" at top left | not drawn | no |
| grey #808080 panel rules (card signature) | rule between panels a and b | not drawn | no |

Matched 3 of 19 claimed conventions and signature features. Rows marked partial, not exercised, or not comparable count as not matched. The highlight_fill row and the grey box row describe the same convention and are counted twice.

## Differences from the paper

- The 2-chloropyridine N-oxide is a drawn structure above the arrow in the paper and text in the replica.
- The grey shape at the upper right of the product is a tool artifact. The highlight fill attaches to the largest ring of the final product. When that ring is abbreviated away as Ts, the grey hexagon is left floating. The paper's grey box sits behind the panel b products, not behind panel a.
- The paper colours the N substituents teal and purple, the ring N atoms blue (about #0080C0), the carbonyl O maroon, the Nu label dark purple, the NuH purple, and the new C to Nu bond red. The replica is black throughout.
- The product name "Unnatural amino acid derivatives" in italic navy is absent.
- Only one panel is drawn. The panel letter "a" and the grey panel rule are absent.
- Measured on the PNG files (not the card's pixel values, which were not checked): the replica arrow is 395 px over a carbonyl-to-alpha bond of about 45 px, so about 9 bond lengths. The paper's arrow is about 432 px over a bond of about 31 px, so about 14 bond lengths (card crop 01: 13.0). The replica arrow is shorter relative to its bonds than the paper's, not longer.
- Label size: the replica "1" is about 22 px tall over a 45 px bond (about 0.49, card 0.50). Line width: the replica arrow ink is about 1.3 px over a 45 px bond (about 0.03, card 0.04); the paper's is about 1.4 px over about 31 px (about 0.045). The replica line is probably thinner than the paper's, but this is within the error of downscaling and is not counted as a match.
- Balance check: step 1 is flagged as missing CH4O2 on the reactant side. MeOH is CH4O, so CH4O2 is MeOH plus one oxygen, not MeOH alone; the attribution in the earlier text is wrong. No validation output is saved in this folder, so the check's wording, and the claim that the N-oxide oxygen is unbalanced, cannot be confirmed here. Nothing was added to the drawing.

## Tool gaps

- above and below take text lines only, so a reagent structure such as 2-chloropyridine N-oxide cannot be drawn above the arrow.
- highlight_fill attaches to the largest ring of each final product. There is no option for a grey box behind the product, and when the ring is abbreviated the fill is orphaned.
- Colours for substrates and new bonds are set per substrate or per mapped bond, not per fragment. With substrate_colors and new_bond_color null on the card, the brief cannot colour the N substituents or the new bond.
- The atom-balance check does not recognise a text reagent as a participant, so MeOH written as conditions text is reported as missing.
- draw_figure has no panel letters, panel rules or multi-panel layout. It draws one scheme.
- draw_figure with render timed out at 300 s twice for the CO2Me brief under ChemDraw contention (tool_timeout). The retry budget was spent.
- Not listed above, seen in the images: the bracketed alpha-oxo gold Fischer carbene with a "via" label under the arrow cannot be drawn, because the brief has no bracketed-intermediate element.
- brief.json has no field for heteroatom palette colours on the core. The N atoms in panel a are blue (about #0080C0) in the paper and black in the replica.
- brief.json has no field for R groups drawn as coloured filled circles (teal and purple in the paper). Only Me or an abbreviation is possible.
- brief.json has no per-line colour for conditions text. The paper colours [Au] (bold, navy) and NuH (purple) differently.
- The bond to an abbreviation can land on the wrong end. The OMe bond in rendered.png attaches under the "e" of Me, not at the O, and brief.json has no field to choose the attachment atom.
- The arrow length is not set by any brief.json field (species entries take id, smiles and label only). The arrow comes out at about 9 bond lengths against about 14 in the paper.
- Species entries have no caption field, so the "1: Yndiamides" name and the italic class name under the product cannot be drawn.
- Charges (N-oxide N+ and O-, [Au]+) cannot be drawn on reagent or intermediate structures.

## Audit

Audit of the replica claims, checked against reference.png, rendered.png, CASE.md, brief.json and the card's chemeurj.json.

- The three match rows hold. The reference "1" is bold, the replica "1" is bold, both are black, and the arrow is plain with a head. Corrected count: 3 of 19.
- Overclaims corrected in this file: the heteroatom row (the paper's panel a N atoms are blue, not black, so the row is a no, not "not exercised"); the new bond row (the paper's bond is red, not maroon, and the card value is null, so it is not a card contradiction); the colour bullet (the Nu label is dark purple, the bond is red, the ring N atoms are blue, and the O is maroon); the arrow bullet ("the arrow is long" is wrong, since the replica arrow is about 9 bond lengths against about 14 in the paper); and the balance bullet (MeOH is CH4O, not CH4O2).
- Omissions added: the bracketed via-carbene under the arrow, the "Yndiamides" caption, and the tool gaps listed above.
- Not verifiable from this folder: the 1905 px source and the desktop ChemDraw render, the CO2Me scratch brief2.json and its no-render draw, and the atom-balance output. No validation.json is saved here.
- The highlight_fill row and the grey box row are the same convention counted twice in the denominator.
