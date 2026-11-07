# Beilstein JOC: Ni-promoted cascade to (+)-aglacin B, top route of Scheme 3

Source: Xiao et al., "Ni-promoted reductive cyclization cascade enables a total synthesis of (+)-aglacin B", *Beilstein J. Org. Chem.* **2025**, *21*, 197. DOI: [10.3762/bjoc.21.197](https://doi.org/10.3762/bjoc.21.197). Licence: CC BY 4.0. Reference crop (Scheme 3) reproduced under that licence.

Drawing style: the `beilstein_joc` house style card (`cdx.py styles beilstein_joc`), base preset `nature`. Figure type: `total_synthesis` (the card also lists this crop under `reaction_scheme`).

## What is reproduced

The top row of the crop, a two-step route with conditions and step yields:

- `5` to `13`: NiCl2, Zn, ethyl crotonate, pyridine above the arrow; DMA, rt, 4 h and (30%) below.
- `13` to `(+)-aglacin B (2)`: BF3·Et2O, Et3SiH above; CH2Cl2, rt, 1 h and (58%) below.

The structures were read by hand from 4 to 6 times zoomed crops and checked with RDKit (no OCSR run). SMILES in `brief.json`:

- `5`: `COc1cc([C@@H]2c3c(cc(OC)c(OC)c3OC)/C(Br)=C/COC(OC)[C@@H]2Br)cc(OC)c1OC`
- `13`: `COc1cc([C@H]2c3c(cc(OC)c(OC)c3OC)C[C@@H]3CO[C@H](OC)[C@H]32)cc(OC)c1OC`
- `2`: `COc1cc([C@H]2c3c(cc(OC)c(OC)c3OC)C[C@@H]3COC[C@H]32)cc(OC)c1OC`

Stereo was taken from the drawn wedges and hashes. The vinyl bromide alkene is E as drawn in the nine-membered ring (ring CH2 trans to the aryl carbon across the C=C).

Not reproduced: the lower row (the `5a` conformer with blue H labels and bold ring bonds, and the arrow to the cyclised structure) and the X-ray ball-and-stick panel with its triple-bar link and italic caption. The draw tools have no conformer or crystal-structure rendering.

## Build

Brief v1 (`brief.json`, `max_width` 720) drew the route with ChemDraw in one call. A second brief wrote the two ring-fusion H atoms of `13` and `2` explicitly, to show the H labels. That build timed out once, then rendered, but the H labels did not appear (ChemDraw folded them into the wedges) and the layout of `5` became crowded, so v1 is the saved replica. `rendered.png` is v1, downscaled to 1200 px wide.

`replay.py` is the jacs-au replay with a new docstring. It was not re-run in this pass.

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| total_synthesis: no step labels, no step count | no step numbers | none | yes |
| total_synthesis: yield_format `({value}%)`, yield as last line under conditions | (30%) and (58%), last line under the arrow | (30%) and (58%), last line under the arrow (typed as a text line, not the tool's yield field) | yes |
| total_synthesis: each step written in full above and below the arrow | yes | yes | yes |
| reaction_scheme: catalyst and reagents above, base, solvent, temperature, time below, one item per line | NiCl2, Zn / ethyl crotonate / pyridine above; DMA, rt, 4 h below | same | yes |
| total_synthesis: target named with its number in parentheses, only the number bold | (+)-aglacin B plain, (**2**) bold | whole label bold | no |
| total_synthesis: X-ray ball-and-stick model, triple-bar link, italic caption | present | not drawn | no |
| top-level yield_placement `after_product_label` (card) against crop 05 | yield under the arrow | yield under the arrow (only because the text was placed by hand) | no |
| reaction_scheme yield_format `{value}%` (card) against crop 05 | `(30%)` | `(30%)` typed by hand | no |
| compound_label_face bold | 5 and 13 bold | 5 and 13 at regular weight; only the target label is bold | no |
| compound_label_color `#000000` | black | black | yes |
| compound_label_italic_suffix false | no italic suffix | none | yes |
| reagent_text_color `#000000` | black | black | yes |
| conditions_split reagents above, solvent below | yes | yes | yes |
| arrow_style plain | plain shaft and head | plain | yes |
| aromatic_rings kekule | Kekule rings | Kekule rings | yes |
| abbreviate_groups includes OMe | OMe; left-hand groups written MeO | OMe everywhere | no |
| label_font Arial | sans-serif, Arial-like | sans-serif; typeface not confirmed from the raster | no (not verified) |
| new_bond_color null | two bonds of 13 drawn dark red | black | no |
| highlight_fill null | none | none | yes |
| bond_length_over_cap_height 2.25 (card), 2.0 for crop 05 | 19.5 px / 10 px = 1.95 | 10.8 pt bond / about 4.3 pt cap (6 pt label, estimated) = about 2.5 | no |
| line_width_over_bond_length 0.068 | 1.3 / 19.5 = 0.067 | 0.6 / 10.8 = 0.056 | no |
| bold_width_over_bond_length 0.2 | 4 / 19.5 = 0.205 | 1.56 / 10.8 = 0.144 | no |
| arrow_length_over_bond_length 6.4 (card), 4.6 for crop 05 | 89 / 19.5 = 4.6 | 60.4 / 10.8 = 5.6 | no |
| orientation of the fused tetralin | aryl ring left, furan right in 13 and 2 | mirror image layout, furan left | no |
| stereo depiction at C2 and C3 | H labels drawn, wedge and hash on the H | no H labels; wedges on C-C bonds; acetal OMe of 13 drawn as a bold wedge (hashed in the paper) | no |

Matched 10 of 25 rows on audit (the first draft claimed 13 of 24). The table has 25 rows; there is no row 26. The draw tool compares structures with CX stereo (readback `matched`), so the wedge differences are depiction, not a different molecule.

## Differences from the paper

- Layout: the paper draws the tetralin with the methoxy aryl ring on the left and the furan on the right, and the pendant trimethoxyphenyl hanging below C4. The replica mirrors the tetralin (furan on the left).
- Compound label: the paper bolds only the number in `(+)-aglacin B (2)`; the replica bolds the whole label.
- H atoms: the paper labels the two ring-fusion H atoms of 13 and 2 (wedge up at C2, hash down at C3). The replica has no H labels. Its wedges sit on the neighbouring C-C bonds, and the acetal OMe of 13 is a bold wedge where the paper uses a hash.
- Colour: the paper draws two bonds of the new ring in 13 in dark red. The replica is all black.
- Yields: the paper puts (30%) and (58%) under the arrow in parentheses. The tool would place a yield after the product label under this card's top-level setting, so the yields were typed as conditions lines.
- Line and bold widths, arrow length and the bond-to-cap-height ratio: the replica uses the `nature` preset geometry, so its lines are thinner, the wedges narrower, the arrows longer relative to the bond, and the labels smaller relative to the bond than in the paper.
- By-products: the paper draws none in this scheme, so this is not a difference. The earlier draft listed H2 and CH2O as missing; that was wrong and is removed.
- Bottom row: the `5a` conformer and the X-ray panel are not drawn.

## Tool gaps

- Per-figure-type yield placement: the card puts yields under the arrow in parentheses for total_synthesis, but `draw_figure` applies the top-level `after_product_label` rule. The under-arrow parenthesised form can only be written as typed text lines.
- Mixed-weight compound labels: a label cannot bold only the number, so `(+)-aglacin B (2)` comes out fully bold.
- Explicit H labels on stereocentres: the tool strips explicit `[H]` atoms from the drawing, so H labels at ring fusions cannot be shown; the wedge moves to a neighbouring bond.
- Bond-level colours: there is no brief key for colouring specific bonds (the red bonds in 13), and `new_bond_color` only applies from atom mapping when the card sets it.
- Orientation: no control of the 2D orientation of fused polycycles; the mirror layout of the tetralin cannot be requested.
- House-style measured ratios: bond-to-cap-height, line, bold width and arrow-to-bond ratios are not applied from the card, only the base preset.
- Abbreviation direction: left-hand groups are written OMe rather than MeO (already documented for CO2Me and MeO2C).
- Conformer and crystal depictions: no tool for the `5a` perspective-style conformer with bold ring bonds, the X-ray ball-and-stick model, or the triple-bar link with an italic caption.

## Audit

Audited against reference.png and rendered.png by a second pass that tried to refute each match row. Corrections:

- Compound label weight: the paper bolds 5 and 13; in rendered.png only the target label is bold. The 5 and 13 labels look regular weight at print scale. Row 9 changed to no.
- Label font: the raster does not confirm the typeface, so the Arial row is marked not verified and no longer counted.
- Count: 10 of 25 rows match on audit (was 13 of 24 claimed). Rows 1 to 4 and 10 to 15 and 19 hold; row 2 (yield format) holds visually only because the yields are typed text lines, not produced by the card.
- Replica-side numbers (10.8 pt bond, about 4.3 pt cap, 0.6 pt line, 60.4 pt arrow) are not measured from rendered.png. The cap height is labelled as estimated, and the other values are unsourced. The ratio rows stay no, but these numbers should not be read as measured.
- The "readback matched" claim (stereo unchanged) was not re-run in this audit and is unverified. The mirrored tetralin requires the wedges to be flipped to keep the same molecule; this is also unverified.
- The by-product difference was not a paper difference (fixed above).

Tool gaps the replicator missed:

- Compound label weight is not applied to 5 and 13 in draw_figure, so the card's compound_label_face bold rule is not met by the tool even for plain labels.
- Bond wedge versus hash choice per bond is not exposed: the acetal OMe of 13 cannot be drawn hashed as in the paper.
