# Xiao et al. 2025: Ni-promoted cascade route to (+)-aglacin B (Scheme 1, retrosynthesis)

Source: Xiao et al., *Beilstein J. Org. Chem.* **2025**, *21*, 197 (Ni-promoted reductive cyclization cascade enables a total synthesis of (+)-aglacin B). DOI: [10.3762/bjoc.21.197](https://doi.org/10.3762/bjoc.21.197).

Licence: CC BY 4.0. Reference crop reproduced under that licence (`reference.png`, evidence crop `beilstein_joc-04.png` of the `beilstein_joc` house style).

Drawing style: the `beilstein_joc` house style in `brief.json` (base preset nature; bold compound labels, reagents above and below the arrow, abbreviated OMe groups, Kekule rings); see `cdx.py styles beilstein_joc`.

Figure type: `retrosynthesis` (card section). The card lists `open_double` retro arrows, dark red disconnection bonds and blue atom numbers for this type; `draw_figure` cannot express any of them, so the replica is a forward route (see below).

## What is reproduced

The whole Scheme 1 route, in forward direction and on one row: 7 + 8 gives 6, 6 gives 5, and 5 gives (+)-aglacin B (2) with Ni, then [H]. Compound labels 2, 5, 6, 7 and 8 are drawn in bold. Stereocentres come from the SMILES in brief.json. RDKit computed the CIP labels from those SMILES (2: 8 S, 8' S, benzylic CH R; 5: CH(Br) S, benzylic CH R; 6: R; 7: the oxazolidinone CH is S). They agree with a manual reading of the paper's wedges and hashes for these centres, but the drawn wedge and hash bonds are not always the paper's (see Audit). The acetal CH(OMe) of 5 is a wavy bond in the paper and is left unspecified.

The paper's compound 2 numbering (C1, C7, C8, C8' in blue; the red disconnection bonds), the bold italic dark red Ni, and the open double retro arrows are not drawn.

| ID | Structure (SMILES in brief.json) | Notes |
| --- | --- | --- |
| 7 | (S)-4-phenyl-3-[(E)-3-(6-bromo-2,3,4-trimethoxyphenyl)acryloyl]oxazolidin-2-one | ring and E-alkene read from the crop; Ph wedge gives S |
| 8 | 3,4,5-trimethoxyphenylmagnesium bromide, `COc1cc([Mg]Br)cc(OC)c1OC` | drawn as a Grignard structure |
| 6 | 3-aryl-3-(3,4,5-trimethoxyphenyl)propan-1-ol with the Ar-Br ring, `COc1cc([C@@H](CCO)c2c(Br)cc(OC)c(OC)c2OC)cc(OC)c1OC` | R; the drawing hashes the bond to the CH2 chain, while the paper hashes the bond to the trimethoxyphenyl |
| 5 | O-allyl methyl acetal with CH(Br) and the aryl bromide, `C=CCOC(OC)[C@@H](Br)[C@H](c1cc(OC)c(OC)c(OC)c1)c1c(Br)cc(OC)c(OC)c1OC` | acetal stereocentre unspecified and drawn as a plain bond (the paper has a wavy bond); CH(Br) S, benzylic CH R |
| 2 | (+)-aglacin B, `COc1cc([C@@H]2c3c(cc(OC)c(OC)c3OC)C[C@@H]3COC[C@H]32)cc(OC)c1OC` | three drawn stereocentres: 8 S, 8' S, benzylic CH R |

The aryl ring pattern of 5, 6 and 7 (Br ortho to the attachment point, CH meta, three OMe) and the ring A pattern of 2 were written from the crop. RDKit only parsed the SMILES, so no RDKit check against the image was made; on inspection the ring of 7 and the trimethoxyphenyl of 8 agree with the crop. Atom mapping shows the bromine of 5 and 6 is at the position that becomes C1 in 2.

## Replay

```
python skill/chemdraw/scripts/cdx.py py skill/chemdraw/assets/house-styles/beilstein_joc/replica/beilstein_joc-04/replay.py NEW_DIR
python skill/chemdraw/scripts/cdx.py render NEW_DIR/figure.cdxml
```

`replay.py` runs `draw_figure` on `brief.json` offline and writes `figure.cdxml` and `validation.json`. `rendered.png` is the final draw (one row), but the file is 1200 px wide, which the stated max_width 900 does not explain. The replay outputs (`figure.cdxml`, `validation.json`) are not stored in this folder, so the checks below cannot be re-read here.

## Balance and checks

The draw report lists `checks_passed: false` with three unbalanced steps. Step 1 (7 + 8 gives 6), step 2 (6 gives 5) and step 3 (5 gives 2) each lack their by-products, because the paper gives no reagents or by-products for the retro arrows 6 from 7 + 8 and 5 from 6, and the tool does not add them. The `lint` check was clean in the final draw; the only earlier issue was a crowded plus sign at the 504 pt width.

## Differences from the paper

- Direction: the paper reads right to left (target 2 on the left, precursors on the right, open double retro arrows). The replica is a forward route, target on the right, with solid arrows.
- Layout: the paper has a single row with the target on the left and precursors stacked on the right (7 above 8 with a plus sign). The replica draws 7 + 8 inline with a plus sign and one row at max_width 900. Stacked substrates (`stacked_plus`) are not applied.
- Arrows: the replica uses solid arrows. The paper uses open double retro arrows, which `draw_figure` does not offer.
- Disconnection bonds: the paper colours the bonds to be formed (C1-C7 and C8-C8') dark red #8A3123. The replica draws them black (`new_bond_color` is null on this card).
- Atom numbers: the paper labels C1, C7, C8, C8' (blue #3839FF) and 7' on the target and intermediate. The replica has no atom number labels.
- Reagents: the paper's Ni is bold italic dark red #8A0004 above the arrow; the replica writes plain black "Ni". The "then [H]" text below the arrow matches.
- Compound 2: the paper's name "(+)-aglacin B" is not drawn; the replica shows only the label 2 in bold. The paper's name is not printed beneath the structure.
- Stereo at the acetal of 5 is left unspecified, but drawn as a plain bond; the paper uses a wavy bond.

## Tool gaps

- No retro arrow: `draw_figure` steps accept only `solid`, `dashed`, `failed`, `reversible` and `resonance`; there is no open double retrosynthetic arrow.
- No retro layout: steps always run from substrates to products left to right; a target-on-left retrosynthesis cannot be drawn without reversing arrows, which would be chemically wrong.
- No disconnection colouring: the card's `disconnection_color` for the retrosynthesis type is not applied; `new_bond_color` is null on the card. The toolkit already colours formed bonds through `new_bond_color` (`mcp_runtime/figure_house.py`), and the retrosynthesis `disconnection_color` key is not wired into it.
- No atom-number labels on a drawn structure (only `show_atom_numbers` on drafts), so the blue C1, C7, C8, C8' labels cannot be placed.
- No styled reagent text: bold italic and dark red reagent text cannot be set per condition line.
- No stacked substrate layout in `draw_figure` for this card (`substrate_layout` inline_plus is the only option the card supplies). The code selects `stacked_plus` only when the house card asks for it, so a brief cannot request it.
- No by-product input for balance: the tool names missing by-products but does not let the brief supply them.

## Audit

Checked against `reference.png`, `rendered.png`, `brief.json` and the `beilstein_joc` card (`publication/house_styles/beilstein_joc.json`, retrosynthesis section). This file has no 13-row convention table, so the earlier "7/13" count is not recorded here. Counting the card and retrosynthesis conventions this figure should follow:

- Matched (6 of 13): bold compound labels; black label colour; reagents above the arrow and text below (the Ni is plain black, not the paper's bold italic dark red); inline plus sign; OMe and Ph abbreviations; Kekule rings.
- Not matched (7 of 13): open double retro arrows (the replica uses solid arrows); target-on-left retro layout; disconnection bonds in #8A3123; blue atom numbers; the paper's stacked 7 over 8 layout; figure width (the card asks for about 700 to 800 px, and `rendered.png` is 1200 px wide); bond-to-label proportions, not measured for this crop (by eye the labels look large relative to the bonds, but that is an estimate, so it is counted as not matched).

Overclaims, corrected above:

- "CIP labels were checked with RDKit against the drawing": RDKit read only the SMILES. The labels are right for the SMILES and agree with a manual reading of the paper for 2 (benzylic CH R, C8 S, C8' S), 5 (CH(Br) S, benzylic CH R), 6 (R) and 7 (S). The drawing itself was not checked.
- "Ring pattern checked by RDKit against the crop": RDKit cannot compare with an image. Only visual agreement was found, for 7 and 8.
- "Stereocentres are drawn from the wedge and hash bonds of the paper": not true of the drawing. Compound 6 hashes the CH2 bond (the paper hashes the aryl bond); the benzylic centres of 2 and 5 are bold where the paper hashes them; 2 is laid out mirrored relative to the paper.
- Acetal of 5 "as the paper's wavy bond indicates": the drawing has a plain bond.
- Replay claims ("checks_passed false", "lint clean", the atom mapping, "max_width 900"): cannot be re-read, because no `validation.json`, `figure.cdxml` or mapping file is in this folder, and the PNG is 1200 px wide.

Corrected matched count: 6 of 13.

Tool gaps the replicator did not list:

- Wedge and hash placement: no option to choose which bond carries a wedge or hash. The tool places them from the SMILES, which is why 6 and 2 differ from the paper.
- Unspecified (wavy) bond style: none.
- Explicit H on stereocentres: the paper shows H on C8 (wedge) and C8' (hash); no option displays them.
- Orientation: no control of the 2D rotation or mirroring of the target.
- Caption text under a structure: the paper's "(+)-aglacin B (2)" line. No caption field is listed in the `draw_figure` brief schema.
- Label size and bond-length ratio: not settable from the brief (`atom_label_size_pt_estimate` is null on the card).
