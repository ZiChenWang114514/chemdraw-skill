# Sci. Adv. amide formation in PBS/EtOH (Fig. 3 header, reaction scheme)

Source: Choudhary, Zhang and Lin, *Sci. Adv.* **2024**, *10*, eadp7544. DOI: [10.1126/sciadv.adp7544](https://doi.org/10.1126/sciadv.adp7544). Licence: CC BY 4.0 (from the house-style card). The reference crop is `reference.png` (Fig. 3, scope of amine).

Figure type: `reaction_scheme` (the header row of the figure, above the scope rows). The card `toolkit/cdxml_toolkit/publication/house_styles/science_aaas.json` has no `figure_types` section, so the figure type and the reaction-scheme conventions come from the top-level card conventions and the observations of this crop.

## What is reproduced

The header reaction only: ethyl 3-(triisopropylsilyl)propiolate (`1`) plus an amine (`2`) in PBS buffer (pH 7.0) / EtOH (4:1), 40 °C, 48 hours, giving the propiolamide (`3`). Solvent is above the arrow and temperature and time below, as in the paper.

Structures read from the crop and checked with RDKit (formulas C14H26O2Si, C7H9N, C19H29NOSi):

| ID | SMILES (in brief.json) | Note |
| --- | --- | --- |
| 1 | `CCOC(=O)C#C[Si](C(C)C)(C(C)C)C(C)C` | TIPS drawn in full, not as the paper's TIPS label |
| 2 | `NCc1ccccc1` | benzylamine stands in for the generic R (see below) |
| 3 | `O=C(NCc1ccccc1)C#C[Si](C(C)C)(C(C)C)C(C)C` | the N-benzyl case, compound 3a of the scope |

The generic amine `H2N-CH2-R` cannot be drawn with `draw_figure` (every species needs a concrete SMILES), so R is phenyl, which is the first scope entry (3a). The scope rows (3a to 3g), the CCDC X-ray inset and the yields are not reproduced; the scheme type does not include them.

Run: `draw_figure` with `style: "science_aaas"` (base preset `nature`), `brief.json` (copied here from the scratch folder); rendered with desktop ChemDraw (`rendered.png`, downscaled from 1629 px to 1200 px wide). `replay.py` reruns the draw offline and was checked to write `figure.cdxml` and `validation.json`.

## Convention check

Claimed = conventions the card states for this figure, or observations in the card about this crop (19 rows). Matched = rows that agree with the paper crop.

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| compound_label_face bold | bold `1`, `2`, `3` | the code sets face 1 on the labels, but in `rendered.png` the labels look regular weight; not confirmed by the image | no |
| compound_label_color #000000 | black | black | yes |
| yield placement / format (`after_product_label`, `{value}%`) | no yield in the header (yields only in scope rows) | no yield drawn | not tested |
| conditions placement (solvent above, temperature and time below) | above and below | above and below | yes |
| conditions wording (`40 °C, 48 hours`) | "48 hours" | "48 h" (the tool tidies condition text) | no |
| substrate_colors: amine blue #0B0AED, ester black | amine blue, ester black | amine blue, ester black | yes |
| amine atoms in the product blue (observations) | amine part of `3` blue | `3` black | no |
| new C–N bond red #F40405, thicker (observations; card `new_bond_color` null) | red, thicker | black | no |
| abbreviate_groups OMe, CF3 | no OMe or CF3 in the header | none | not tested |
| TIPS and OEt abbreviated (observations) | `TIPS`, `OEt` | full triisopropylsilyl and full ethyl ester | no |
| Kekulé rings | no ring in the header crop (the Kekulé evidence is in the scope rows, not drawn) | a phenyl ring, not checked against a Kekulé reference | no |
| reagent_text_color #000000 | black | black | yes |
| arrow_style plain | plain | plain | yes |
| A + B inline with `+` (observations) | inline `+` | inline `+` | yes |
| bond line width / bond length (card 0.052) | 0.043 (2 px / 47 px in the crop) | 0.056 (0.6 pt / 10.8 pt), about 30% heavier than the crop | no |
| arrow length / bond length (card 12.82) | 15.5 (727 px / 47 px in the crop) | 11.1 (120.3 pt / 10.8 pt) | no |
| atom label size (card 8 pt estimate) | about 8 pt | 6 pt (`LabelSize` 6 from the nature base) | no |
| label font Arial | Arial | ChemDraw font id 3, not checked as Arial; the card's `label_font` is not read by the house code (fixed ACS font) | no |
| bond length / cap height (card 1.935) | about 1.9 | not measured on the replica; the card value is not read by the house code | no |

Matched: 6 of 19 claimed (the replicator reported 9). See the Audit note below.

## Differences from the paper

- Compound `1` keeps the full TIPS group and the full OEt ester; the paper abbreviates both.
- Amine `2` is benzylamine (R = phenyl) instead of the generic R of the paper.
- The amine is blue in the reactant but the product `3` is drawn black; the paper colours the amine part of the product blue as well.
- The C–N bond formed is black; the paper draws it red and thicker.
- The carbonyl oxygen points down in the replica and up in the paper, for the amide `3` and also for the ester `1` (the replica's ester C=O points down too).
- The paper's reagent text reads "PBS buffer (pH = 7.0)". The brief writes "pH 7.0", so the wording differs from the paper; this comes from the brief, not from the tool.
- The arrow is shorter than in the paper (11 bond lengths against 15.5 in the crop).
- Labels are 6 pt in the replica; the paper labels are about 8 pt.
- The ethanol by-product is not drawn. The tool flags step 1 as not balanced (C2H6O missing from the products). The paper does not draw it either, so this warning is expected here and nothing was added.
- The scope rows, yields, CCDC inset and the compound 3a-3g labels are not drawn.

## Tool gaps

- No control of the atom-label size. The card's `atom_label_size_pt_estimate` (8 pt) is not applied; the nature base gives 6 pt.
- No control of the arrow length in bond lengths. The card's `arrow_length_over_bond_length` (12.82) is not applied; the arrow is 11.1 bond lengths here.
- `substrate_colors` colours only the drawn substrates. There is no way to colour the atoms that came from a substrate inside a product (the card's observation that the amine is blue in the product).
- `new_bond_color` is supported by the house code (`figure_house.py` colours the formed bond when the card sets it), but the card leaves it null, so the red bond is not drawn. What is really missing is a weight for a new bond: no field sets a heavier line for the formed bond, so the red bold C–N bond cannot be reproduced even with the colour set.
- The abbreviation vocabulary is fixed. TIPS and OEt cannot be contracted, so the TIPS silyl group and the ethyl ester are drawn in full.
- A generic substituent (R or a variable group) cannot be written in a brief; every species needs a SMILES.
- No way to mark a by-product as deliberately not drawn. Every condensation that loses a small molecule gets an unbalanced-step warning, even where the paper omits the by-product on purpose.
- Condition text is rewritten by the tool ("hours" becomes "h"). There is no switch to keep the paper's wording.
- Orientation of the carbonyl and the placement of substituents are left to the layout engine; the card has no convention for them. This applies to the ester `1` as well as the amide `3`.
- The card's `label_font` (Arial) is not read by the house code; labels use a fixed ACS font id, so the label face cannot be set from the card.
- The card's `bond_length_over_cap_height` (1.935) is not read, so the bond-to-label proportion cannot be fixed by a house style.
- The compound-label face (`compound_label_face`) is applied in code, but the replica's labels are not visibly bold in `rendered.png`. Whether the bold reaches ChemDraw is not confirmed.
- The bond geometry is not controllable: the alkyne of `1` runs horizontally in the replica and rises toward the carbonyl in the paper, and the layout engine picks the angles.

## Audit

Audit by a second reviewer, run after the first replica. The first table overstated the match. Corrections:

- Compound-label bold, Kekulé rings and bond line width were marked "yes" without support. The bold labels are not visible in the image, the header has no ring to compare, and the line width is about 30% heavier than the crop (0.056 against 0.043). All three are now "no".
- The label font and the bond-length-to-cap-height ratio were marked "not verified" or "not measured". They are not read by the house code, so they are "no".
- The new-bond colour gap was misdescribed: the colour can be set through `new_bond_color`; the missing part is the weight of the new bond.
- The line-width ratio of the card (0.052) does not match the crop's own pixel measures either (2 px / 47 px = 0.043 in Fig. 3 and Fig. 4; 3 px / 43 px = 0.070 in the bromination figure).
- The paper's reagent text is "pH = 7.0", not "pH 7.0".

Corrected count: 6 of 19 claimed match (conditions placement, colour of the compound labels, substrate colours for the reactants, reagent text colour, plain arrow, inline "+"). The replicator reported 9.
