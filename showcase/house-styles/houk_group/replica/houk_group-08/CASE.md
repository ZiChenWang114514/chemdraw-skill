# Houk group (Nat. Commun. 2022): Rh-catalysed cyclisation of an N-allyl bicyclobutane amine (Fig. 1, reaction scheme)

Source: Chen, Wipf, Houk et al., "How mono- and diphosphine ligands alter regioselectivity of the Rh-catalyzed annulative cleavage of bicyclo[1.1.0]butanes", *Nat. Commun.* **2022**. DOI: [10.1038/s41467-022-34837-x](https://doi.org/10.1038/s41467-022-34837-x).

Licence: CC BY 4.0 (from the house-style card). Reference crop reproduced under that licence.

Drawing style: the `houk_group` house style in `brief.json` (base preset ACS Document 1996); see `cdx.py styles houk_group`.

Figure type: `reaction_scheme` (the card's section for this crop).

## What is reproduced

The main scheme at the top of Fig. 1: substrate **1** under catalyst and ligand (written as `cat, L`) in PhMe at 110 °C gives the two products **2** and **3** drawn inline with a plus sign. Conditions are the placeholders printed above and below the arrow. The yields from entry (1) are written under the arrow as a single line (`2 87%, 3 8%`).

The entry table under the scheme (entries (1) and (2), with their catalyst and ligand names and the second row of yields, `2 (<1%)` and `3 (83%)`) is not drawn. Entry (2) is therefore absent.

## Structures

Read by hand from a 2x zoom of the crop. OCSR was not run. Relative stereochemistry comes from the wedge and hash bonds in the crop, converted to SMILES with RDKit from 2D coordinates.

| ID | SMILES in brief.json | Note |
| --- | --- | --- |
| 1 | `O=S(=O)(c1ccc(C)cc1)N(CC=C)C(c1ccccc1)C12CC1C2` | drawn without stereo; the paper shows no stereo on the bicyclobutane |
| 2 | `C=CC[C@]12C[C@H]1CN(S(=O)(=O)c1ccc(C)cc1)[C@@H]2c1ccccc1` | C21H23NO2S; wedge Ph and wedge allyl, cyclopropane hashed. The SMILES encodes one enantiomer of the relative configuration in the drawing; the paper's absolute configuration is not given |
| 3 | `C=C1C[C@@H]2C[C@@H]2CN(S(=O)(=O)c2ccc(C)cc2)[C@@H]1c1ccccc1` | C21H23NO2S; wedge Ph, wedge cyclopropane bond to the apex CH2. Same caveat on absolute configuration |

The step is a 1 to (2 + 3) product mixture. draw_figure reports `Step 1 does not balance as drawn` for it. This is expected for a mixture of isomers and is the tool gap listed below.

## Replay

```
python skill/chemdraw/scripts/cdx.py draw skill/chemdraw/assets/house-styles/houk_group/replica/houk_group-08/brief.json NEW_DIR/figure.cdxml --render
```

`replay.py` in this folder runs `draw_figure` on `brief.json` offline and writes `figure.cdxml` and `validation.json` to a new folder. Compare the PNG with `reference.png`; `rendered.png` is the ChemDraw rendering from the first attempt.

## Convention check

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| compound label face bold | bold numbers 2 and 3 appear only in the yield table under the scheme; the crop has no labels under the structures | bold labels 1, 2, 3 under the structures, which the paper crop does not show | no |
| compound label colour black | black, but only in the yield table; nothing under the structures to compare | black labels under the structures, added by the tool | no |
| abbreviate groups Ts and Ph | Ts and Ph abbreviated | Ts and Ph abbreviated | yes |
| substrate_layout inline_plus (products) | 2 + 3 on one row with a plus | 2 + 3 on one row with a plus | yes |
| show_plus_sign | plus between the products | plus between the products | yes |
| arrow_style plain | plain solid arrow | plain solid arrow | yes |
| reagent_text_color black | black | black | yes |
| conditions split (catalyst above, solvent and temperature below) | `cat, L` above; `PhMe, 110 °C` below | same split | yes |
| long arrow, about six bond lengths (card value 6.2) | rough pixel estimate on reference.png: arrow 215 px, bond roughly 16 to 18 px, so about 11 to 13 bond lengths (the card's 160 px over 14 px was not re-checked) | rough pixel estimate on rendered.png: arrow 207 px, bond roughly 30 px, so about 6 to 7; close to 6.2 but not set by any parameter; the tool has no arrow-length setting | no (the paper's arrow is about twice as long relative to its bonds) |
| catalyst or reagent drawn as a structure above the arrow (card signature, top-level) | text `cat, L`, no structure | text `cat, L` | no (card claim does not hold for this crop) |
| conditions bold | bold text above and below (`cat, L` bold italic) | plain text | no |
| results as rows under the products, numbered by entry | yield rows under each product, aligned with its column, entry numbers (1) and (2) at the left | one line under the arrow | no |
| yield format parenthesised after the label | `2 (87%)`, `3 (8%)` | `2 87%, 3 8%` | no |
| new oxygen red, reaction time green (reaction_scheme) | not in this crop (crop 07 only) | not drawn | n/a |
| bold wedge on a bicyclobutane bond | bold wedge on the bridge bond of substrate 1 | plain bonds | no (not claimed by the card; visible in the paper) |
| stereo wedges and hashed cyclopropane in the products | wedge Ph and allyl on 2; hashed cyclopropane on 2; wedge bond on 3 | same features, checked by eye on 4x crops | yes (by eye only) |

Of the 12 conventions the card claims for this crop, 6 match: Ts and Ph abbreviation, inline plus, plus sign, plain arrow, black reagent text and the conditions split. The 6 that do not match: compound label face bold and compound label colour black (the paper crop has no labels under the structures, so there is nothing to match against), arrow length, catalyst drawn as a structure, yield rows under the products, and parenthesised yield format. The other rows are not claimed by the card for this crop and are reported for completeness.

## Differences from the paper

- The entry table (1) and (2) is omitted. Entry (2), with dppe, the second catalyst and the yields `2 (<1%)` and `3 (83%)`, is not drawn.
- Yields are one line under the arrow. The paper gives them as rows under each product, aligned with its column, and parenthesised.
- The catalyst and ligand are placeholder text (`cat, L`) in both the paper and the replica. The replica writes them in plain type; the paper uses bold italic.
- Conditions are plain, not bold.
- Substrate 1 is drawn with plain bonds. The paper draws the bicyclobutane bridge bond as a bold wedge.
- The arrow is shorter relative to the bonds than in the paper (rough pixel estimate, see the convention table).
- Compound labels 1, 2 and 3 are drawn under the structures and under the substrate. The paper crop has none of these; its only numbered labels are in the yield table below the scheme.
- The SMILES for 2 and 3 fix one enantiomer. The drawing shows relative configuration only.

## Tool gaps

- A single substrate with several products (a product mixture) is treated as a reaction. draw_figure then reports `Step 1 does not balance as drawn`, which is not the case for an isomer mixture. The brief has no way to mark a mixture or a selectivity.
- A step has one `yield` string. Per-product yields cannot be attached to each product's column, and there is no entry-row table (entries (1), (2) with a reagent column and aligned yields).
- The house-style yield conventions (`yield_placement`, `yield_format`) are null on this card, so draw_figure skips yield formatting. The card's own note says the yields are parenthesised after each label; the card does not record the setting, so it is not applied.
- Conditions are plain text. There is no bold or italic run formatting for above and below lines.
- There is no brief field for arrow length relative to bond length, so the card's arrow ratio (6.2) cannot be applied.
- Bond-level bold wedges (for example the bicyclobutane bridge) cannot be specified in the brief. Stereo has to be given as SMILES; wedge input from a 2D molblock is not accepted by draw_figure.
- Render attempts for the second brief failed with `worker_out_of_memory` and then OpenBLAS memory errors while many draw jobs were running at the same time. Attempt 2 (parenthesised yields in the brief) was therefore not rendered and is not verified.

- No way to suppress compound labels under structures for a scheme like this one. The brief gives every species a `label`, and no option to hide it was seen in brief.json. Not checked against the tool source.
- No entry-table construct under a scheme (entry number, reagent line, aligned yields). Only the single `yield` string on the step exists.

## Attempts

1. `brief.json` with the yield as `2 87%, 3 8%`. Rendered; checks passed; readback matched 3 structures; `style.applied` lists bold labels, plus sign, black reagent text and Ts/Ph abbreviation.
2. Yield changed to `2 (87%), 3 (8%)` in the brief (`brief_t2.json`, not kept in the case folder). Failed twice with environment memory errors (see tool gaps). Not verified.


## Audit

Checked on 2026-11-07 by reading reference.png, rendered.png, brief.json and the house-style card, plus 2x to 4x crops of both images. Overclaims corrected in the convention table:

- Compound label face bold and label colour black were marked matched. The paper crop shows no labels under the structures; the bold numbers 2 and 3 appear only in the yield table. The replica's labels under the structures are an addition, so both rows are now not matched.
- The paper's "bold product labels 2 and 3" description was a misreading of the crop and is corrected in the table.
- The arrow row now gives pixel estimates for both images. The paper's arrow is roughly 11 to 13 bond lengths and the replica's roughly 6 to 7. The replica's value is close to the card's 6.2 by coincidence, not because a setting was applied. The verdict stays no, because the paper does not match it.
- Stereo wedges on 2 and 3 were checked by eye and kept as matched, with a note that this is an eye check only.
- Conditions bold was already recorded as no and is confirmed: the paper's "PhMe, 110 °C" is bold and the replica's is plain.
- The bold wedge on the bicyclobutane bridge bond is confirmed. The paper draws it bold, the replica draws plain bonds.
- Corrected count: 6 of the 12 claimed conventions match, not 8.
- Not verified from this folder: the `style.applied` and readback claims in Attempt 1, because validation.json was not kept; the RDKit stereo derivation; the failure messages in Attempt 2.
