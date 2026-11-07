# sarpong_group-06: Schmidt rearrangement route (Figure 3, panel A)

Source: Sarpong et al., J. Am. Chem. Soc. 2026 (Strategic applications of single-atom skeletal editing in natural product synthesis). DOI [10.1021/jacs.6c04423](https://doi.org/10.1021/jacs.6c04423). Licence: CC BY 4.0. Reference crop: `evidence/sarpong_group-06.png` (copied to `reference.png`).

Drawing style: the `sarpong_group` house style (base preset `nature`), from `brief.json`.

Figure type: `total_synthesis` (card crops 06 and 07).

## What is reproduced

Panel A of the crop only: the Büchi Schmidt ring expansion and the route to (+)-muscopyridine, compounds 11 to 14, with the conditions and yields the panel shows. Panels B, C and D (Schmidt-Aubé, acyloxy nitroso, NMe insertion) are not drawn.

| ID | Structure (SMILES in brief.json) | Read from |
| --- | --- | --- |
| 11 | `C12CCCCCCCCCCC1=CCC2` | cyclopentene fused to a 12-membered carbocycle (10 CH2 in the large ring) |
| 12 | `C12CCCCCCCCCCC(=CCC2)N1` | tetrahydropyridine enamine (NH), macrocycle 13-membered including N |
| 13 | `c12cccc(n1)CCCCCCCCCC2` | 2,6-bridged pyridine, 10 CH2 in the chain |
| 14 | `c12cccc(n1)CC[C@H](C)CCCCCCC2` | the chain carries a CH(Me) stereocentre two CH2 from the pyridine; configuration R as drawn (hashed Me) |

Structures were read by eye from the crop (no OCSR run). RDKit gives C15H26 for 11, C15H27N for 12, C15H23N for 13 and C16H25N for 14, the last matching muscopyridine.

Attempt history: try 1 placed the CH(Me) directly on the pyridine carbon, a misreading of the crop. Try 2 (the file kept here) places it two CH2 further out, as in the crop.

## Replay

```
python skill/chemdraw/scripts/cdx.py py skill/chemdraw/assets/house-styles/sarpong_group/replica/sarpong_group-06/replay.py NEW_DIR
python skill/chemdraw/scripts/cdx.py render NEW_DIR/figure.cdxml
```

`rendered.png` is the ChemDraw native render of `brief.json` (downscaled to 1200 px wide).

## Convention check

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| compound label face | bold numbers 11 to 14 | regular weight in rendered.png | no |
| compound label colour | black | black | yes |
| yield placement | under the arrow | under the arrow | yes |
| yield format | `18%` | `18%` | yes |
| reagents above the arrow | `H2SO4, HN3`; `Pd/C` | same | yes |
| reagent text colour | black | black | yes |
| aromatic rings kekule | pyridine drawn with alternating double bonds, ring bonds crimson | alternating double bonds, bonds black | partial (bond pattern only; not counted) |
| arrow style plain | plain arrows; the 6 steps arrow is double-shafted | all arrows single solid | no (double-shafted arrow not drawn) |
| step count on arrow ("N steps") | `6 steps` over a double-shafted arrow | `6 steps` over a single arrow | no (double shaft not drawn) |
| yield and "(2 steps)" note order | `18%` on the first line, `(2 steps)` below | `(2 steps)` above `18%` | no |
| "prepared in N steps" under the start (grey) | `prepared in 4 steps` under 11 | not drawn | no |
| target name bold italic blue | `(+)-muscopyridine` under 14 | not drawn | no |
| changed atoms or rings crimson #A10E3D | inserted N and the reacting ring bonds crimson | black | no |
| panel header pill with letter badge and title | grey pill, letter A, title `Schmidt rearrangement (Büchi, 1957)` | no pill, no badge, no title in rendered.png | no |
| stereo bond at the stereocentre | hashed Me from the lower right of the ring, pointing right | solid wedge, Me drawn up and to the left, stereocentre on another arc | no (bond type, side and position differ; configuration not verified) |

Corrected count: 5 of 15 table rows match (label colour, yield placement, yield format, reagents above, reagent colour). The kekule row is partial and not counted. The label face, arrow style, step count, note order, grey text, target name, changed-atom colour, header and stereo rows are not matched.

## Differences from the paper

- Layout: the paper uses one row with panel A's four structures; at the default `max_width` 504 the route wraps to two rows. The replica uses `max_width` 760 for one row.
- The paper's double-shafted arrow for "6 steps" is drawn as a single arrow. "(2 steps)" is a note under the single Pd/C arrow, not an arrow of its own.
- The "18%" yield sits below "(2 steps)" in the replica; the paper reverses that order.
- No crimson colouring of the N atom or the ring bonds that change in the Schmidt insertion; no pink halo behind the N atoms.
- No grey "prepared in 4 steps" line under 11 and no bold italic blue "(+)-muscopyridine" name under 14.
- No grey panel pill with the letter A.
- The stereocentre in 14 is drawn with a solid wedge at a different 2D orientation from the paper's hashed bond. The configuration (R) follows the drawing as read.
- Ring shapes are drawn as regular polygons by the tool and differ in proportion from the paper's hand-drawn macrocycles.

## Tool gaps

- No double-shafted "N steps" arrow. `arrow` accepts solid, dashed, failed, reversible or resonance only.
- The step note (for example `(2 steps)`) and the yield are placed in a fixed order; the tool prints the below-arrow lines above the yield, so the paper's order cannot be reproduced.
- No grey text under a starting material ("prepared in N steps"), and no bold italic coloured target name. A compound label is one line in the card's bold face.
- No panel header pill (grey rounded box with a letter badge). The brief has a `title`, but it does not appear in rendered.png, so the header is missing even as plain text. Check whether the tool drops `title` for this card.
- Changed-atom or changed-bond colouring is not applied from the card: `new_bond_color` is null for this card, so the crimson of the paper is not drawn. `atom_halos` could approximate the pink circles behind N, but the brief would have to set them.
- Stereo wedge placement is decided by the tool's 2D layout. The brief cannot choose which bond is hashed or the orientation of the drawing, so the paper's hashed depiction cannot be matched.
- Balance warnings: step 1 reports missing `HN` (the reagent `HN3` is text only and is not counted), step 2 reports missing `H4` (the Pd/C dehydrogenation by-product), step 3 reports missing `CH2` (a multi-step net conversion cannot be balanced in one step). Warnings are informative only; nothing was added to the drawing.

## Audit

Checked the table against reference.png (the full Figure 3 crop; panel A is the top row), rendered.png, the house style JSON and brief.json. Overclaims corrected:

- Kekule row: the bond pattern matches, but the pyridine bonds are black, not crimson. Partial, not counted.
- Label face: the labels in rendered.png look regular weight; the paper's are bold. Not matched.
- Stereo row: the paper's hashed Me points right from the lower right of the ring; the replica has a solid wedge pointing up and left. Not matched. The R configuration was not checked from coordinates.
- Header: the brief's title does not appear in rendered.png, so the replica has no header at all.
- Count: 5 of 15 rows match. The earlier 6 of 15 counted the kekule row.

Other differences found on inspection:

- The NH in 12 is an inline black "HN". The paper stacks N over H, with the H and a pink halo on N in the crimson colour.
- The stereocentre in 14 sits on a different arc of the ring from the paper's position.
- Bond proportions, line weight and label size were not measured, so none of them is counted as matched.
- Balance warnings listed under Tool gaps were not re-run.

Tool gaps the replicator missed:

- Heteroatom label orientation: the card writes NH as one inline string and offers no way to stack N over H or to set the H colour separately.
- Compound label weight and size: the brief has no per-label control, so the bold face in the paper cannot be requested or checked.
- Ring-atom placement: a stereocentre can be placed only through the SMILES. The tool chooses its position on the ring, so the replica cannot match the paper's arc.
