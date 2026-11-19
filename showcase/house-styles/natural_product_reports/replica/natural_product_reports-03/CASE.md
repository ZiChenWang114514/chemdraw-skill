# Nat. Prod. Rep. 2024: 3'-O-glucosyl metabolite to nucleocidin (NucGS step, Fig. 6)

Source: J. Miller et al., "Purine nucleoside antibiotics: recent synthetic advances harnessing chemistry and biology", *Natural Product Reports* **2024**. DOI: [10.1039/d3np00051f](https://doi.org/10.1039/d3np00051f).

Licence: CC BY 3.0 (from the house-style card); reference crop reproduced under that licence.

Drawing style: the `natural_product_reports` house style in `brief.json` (bold compound numbers, black labels, Kekule rings, plain arrow; base preset RSC); see `cdx.py styles natural_product_reports`.

Figure type: `biosynthesis` (the enzyme step) with `biomolecule` (the sugar and nucleoside structures). The card lists this crop under both.

## What is reproduced

The one-step enzymatic conversion at the centre of the crop: 3'-O-glucosylated metabolite (44) to nucleocidin (45) with NucGS above a long plain arrow. Both structures are drawn with bold numbers under them. The step is drawn as a single-substrate, single-product scheme.

Structures were read from the crop by eye (OCSR not run). `44` is nucleocidin with a glucopyranose on O-3'; `45` is nucleocidin. RDKit gives `45` = `C10H13FN6O6S`, consistent with nucleocidin, and `44` = `C16H23FN6O11S`.

| ID | SMILES in brief.json | Note |
| --- | --- | --- |
| 44 | `NS(=O)(=O)OCC1(F)OC(n2cnc3c(N)ncnc32)C(O)C1OC1OC(CO)C(O)C(O)C1O` | no stereo descriptors written |
| 45 | `NS(=O)(=O)OCC1(F)OC(n2cnc3c(N)ncnc32)C(O)C1O` | no stereo descriptors written |

Not reproduced: the blue glucose and its colour, the title line, the compound-name captions, the enzyme box, the sugar chair and the orientation of the ring (see below).

## Replay

```
python skill/chemdraw/scripts/cdx.py py skill/chemdraw/assets/house-styles/natural_product_reports/replica/natural_product_reports-03/replay.py NEW_DIR
python skill/chemdraw/scripts/cdx.py render NEW_DIR/figure.cdxml
```

`replay.py` runs `draw_figure` on `brief.json` offline and writes `figure.cdxml` and `validation.json`. Compare `rendered.png` with `reference.png`.

## Convention check

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| compound_label_face bold (numbers 44, 45) | bold | bold | yes |
| compound_label_color #000000 | black numbers | black | yes |
| aromatic_rings kekule (adenine) | Kekule | Kekule | yes |
| arrow_style plain | plain solid arrow | plain solid arrow | yes |
| reagent_text_color #000000 | enzyme text blue and bold, inside a rounded box | black text, no box; the card colour is applied (validation `style.applied`) | no |
| line width over bond length 0.05 and Arial labels | thin lines, Arial-like (not measured for this crop; a rough read of about 2 px over a 29 px bond gives about 0.07) | 0.6 pt over 12.2 pt bond (0.049), Arial | no |
| arrow length about 4.9 bond lengths | long arrow; visual estimate, and about 4.7 bond lengths by pixels (136 px over a 29 px bond), not measured for this crop | 61.0 pt / 12.2 pt = 5.0 | no |
| biosynthesis: enzyme name above the arrow | NucGS above the arrow | NucGS above the arrow | yes |
| biosynthesis: enzyme in a dark-blue rounded box | blue outline, black text | no box | no |
| biosynthesis: changed atoms coloured, variation_color #D8151F | changed sugar dark blue #074383, no red | all black | no |
| biosynthesis: intermediates labelled with bold numbers | bold 44 and 45 | bold 44 and 45 | yes |
| biosynthesis: italic dark-blue trivial name with bold number in parentheses | "3'-O-glucosylated metabolite" dark blue italic, "(44)" bold; "Nucleocidin (45)" italic black | numbers only, no names | no |
| biomolecule: sugar as a chair (crop 03) | sugar drawn as a chair-like pyranose | flat hexagon | no |
| biomolecule: variation_color #FC332F | changed sugar dark blue #074383 | all black | no |

The table covers the claims the card makes for these two figure types that apply to this crop, plus the top-level scheme conventions that are visible. Rows that the card does not claim for crop 03 (cofactors stacked below the arrow, by-products on a curved arrow, yield format, abbreviated groups) are left out because the crop has none of them.

## Differences from the paper

- Layout: the paper puts the glucose lower-left under the aglycone and the ring orientation keeps the ribose hydroxyls pointing down. The replica puts the glucose above the aglycone and draws the hydroxyls upward, so the molecules are a different shape on the page. The crop is 790 x 226 px (3.5:1) and the replica is 3.2:1.
- Colour: the transferred glucose is black. In the paper it is dark blue (#074383), the one colour that marks the enzymatic change.
- Sugar: the paper draws a chair-like pyranose. The replica draws a flat hexagon.
- Enzyme label: plain black "NucGS". The paper has a blue outline box.
- Compound names: the paper has an italic caption under each structure ("3'-O-glucosylated metabolite" in dark blue, "Nucleocidin" in black), with the bold number in parentheses. The replica shows only the bold numbers.
- Title: the paper has a dark-blue bold title line. The brief's `title` key was accepted but no title was drawn (see tool gaps).
- By-product: the paper shows no released glucose. The replica does not draw one either, and the tool reports the step as unbalanced (missing `C6H10O5`, the glucosyl unit). This is a faithful reading of the figure and is not corrected in the drawing.
- Stereochemistry: no wedges or hashes are legible at this size, so the SMILES carry no stereo descriptors.

## Tool gaps

- The brief has no `figure_type` key. The biosynthesis and biomolecule conventions (variation colour, enzyme box, dark-blue names) are never applied to a scheme, and the report does not list them as skipped.
- Per-fragment colour: `substrate_colors` colours a whole substrate. There is no way to colour the transferred glucose only.
- Enzyme box: `above` and `below` take text lines. A rounded box with a coloured outline cannot be drawn.
- Compound captions: a species `label` is one string. An italic name followed by a bold number in parentheses cannot be drawn, and the name cannot be coloured separately.
- Title: the brief's `title` is accepted for a scheme, but the rendered CDXML contains no title text (checked in `figure-try2.cdxml`).
- By-products: a released molecule can only be drawn as a product, which adds a structure the paper does not show. There is no text-only or curved-leaving-arrow by-product, so a step like this stays unbalanced.
- Sugar conformer: no species option sets a chair or other 3D-like ring projection in `draw_figure`. A flat pyranose is always drawn.
- Orientation: no per-species rotation or substituent-direction option, so the ring cannot be turned to match the paper.

## Attempts

- Try 1: the scheme as above. Rendered; `checks_passed` true; `lint` clean; `readback` matched (2 structures). One warning, the unbalanced step.
- Try 2: same brief with a `title` added. Rendered; the title does not appear. Warning unchanged.
- No third try. The remaining differences (orientation, colour, enzyme box, captions, chair) cannot be changed from the brief.

## Audit

Checked by eye and by pixel sampling against `reference.png` and `rendered.png`, and by re-running `replay.py` into a scratch folder outside this case. Only this file was changed.

Overclaims, now corrected in the table:
- Reagent colour: the paper's enzyme name is blue and bold, not black. The replica's black comes from the card's `reagent_text_color`, which the replay applies. Row set to no.
- Line width: the paper's line width was never measured for this crop. The 0.05 in the card comes from crop 01. A rough read gives about 2 px on a 29 px bond (about 0.07), which does not confirm 0.05. Row set to no.
- Arrow length: the paper value is a visual estimate. Pixels give about 4.7 bond lengths (136 px over 29 px), close to the card's 4.9 but never measured for this crop. Row set to no.

Wrong statements in the body:
- Stereochemistry: the paper has stereo marks. The C4'-F and C3'-O bonds and the C2'-OH bond are hashed, the C1'-N9 and C5'-CH2 bonds are bold wedges, and the glucose has bold wedge bonds. The reason given ("no wedges or hashes are legible") is wrong. The replica has no stereo because the SMILES in `brief.json` carry none. A probe with a stereo SMILES gave `WedgedHashBegin` bonds, so this is a transcription gap, not a tool limit.
- Orientation: the replica is a vertical mirror of the paper's scaffold (paper: ribose O at the top and glucose lower-left; replica: ribose O at the bottom and glucose above), not only a changed sugar orientation.
- Title: confirmed absent from the replay's CDXML. `figure-try2.cdxml` is not in this folder, so that earlier check could not be repeated from the file itself.

Confirmed: bold compound numbers (on zoom, replica 44 and 45 are bold), black label colour, Kekule rings, plain arrow, enzyme name above the arrow, bold intermediate numbers, the two formulas in the Structures section (RDKit), the by-product warning, and that the biosynthesis conventions do not appear in the replay's `skipped` list.

Corrected matched count: 6 of 14 (label face, label colour, Kekule rings, plain arrow, enzyme name above the arrow, bold intermediate numbers). The replicator's 8 included line width and arrow length, now no. The reagent row was already partial and is now no.

Tool gaps the replicator missed:
- Condition lines are plain strings with no bold, italic or colour. A bold blue enzyme name cannot be drawn even if a box existed, and the card's `reagent_text_color` is applied to the enzyme label with no per-step override.
- Arrow length has no brief key. The layout sets it from the longest condition line (the code says so), so the 5.0 here is incidental.
- Bond length and line width have no brief key. They come only from the style preset, so the paper's proportions cannot be requested.
- Title styling: the title is dropped and there is no bold or colour option.
- Stereo: the brief has no stereo field. Stereo enters only through the SMILES, so the transcription has to carry it.
- Species `ring_fills` and `atom_halos` exist. They give fills or halos, not coloured bonds or labels, so they cannot colour the glucose dark blue. The report should have named them and said why they fail.
