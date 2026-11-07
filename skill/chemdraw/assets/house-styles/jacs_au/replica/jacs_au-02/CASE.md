# JACS Au house style: panel D of Ravelli et al. 2025 (aldehyde decarbonylation)

Source: Ravelli et al., "A decarbonylative strategy to enhance efficiency and regioselectivity in photocatalyzed HAT", *JACS Au* **2025**. DOI: [10.1021/jacsau.5c00530](https://doi.org/10.1021/jacsau.5c00530). Licence: CC BY 4.0 (as recorded on the `jacs_au` card). Crop: `evidence/jacs_au-02.png`, Figure 1 (A-E).

Figure type: `concept_panel` (card section). Reference copy: `reference.png`. Final brief: `brief.json`. Rendered output: `rendered.png` (desktop ChemDraw, `draw_figure` with `style: jacs_au`).

## What is reproduced

Panel D only, the two aldehyde decarbonylation reactions, drawn as one scheme:

- `CC(C)(C)C=O` + 4-methylphenylacetylene (`Cc1ccc(cc1)C#C`), DTBP (2 equiv.), MeCN, 110 °C, 12 h, gives `CC(C)(C)/C=C/c1ccc(C)cc1`.
- `CC(C)(C)C=O` + N-phenylmethacrylamide (`C=C(C)C(=O)Nc1ccccc1`), 4CzIPN, NaBr, (CH3)2CO/H2O, 18 h, ambient temperature, gives `CC(CC(C)(C)C)C(=O)Nc1ccccc1`.

Conditions are copied from the crop. The crop shows no yields, so none are drawn. The grey bullet boxes, the panel letter and title, the light-bulb symbol and the other panels (A-C, E) are not drawn.

| ID | SMILES | Source |
| --- | --- | --- |
| aldehyde | `CC(C)(C)C=O` | read by eye from the crop (tBu-CHO); not OCSR-checked |
| alkyne | `Cc1ccc(cc1)C#C` | read by eye; RDKit canonical `C#Cc1ccc(C)cc1` |
| alkene | `CC(C)(C)/C=C/c1ccc(C)cc1` | crop draws a wavy bond (E/Z mixture); E is written because the tool refuses an unspecified double bond |
| acrylamide | `C=C(C)C(=O)Nc1ccccc1` | read by eye |
| amide | `CC(CC(C)(C)C)C(=O)Nc1ccccc1` | read by eye; RDKit checked, C14H21NO |

RDKit parses all five SMILES. The by-product CO is not drawn, as in the paper.

## Draw attempts

1. Two independent steps with separate aldehyde ids: refused, "not a linear route, a convergent route or a set of reactions from one starting material".
2. One shared aldehyde (divergent layout), alkene without stereo: refused, `chemical_semantics_changed` (the tool re-reads the alkene as E).
3. Same with the alkene as E: drawn, but 4CzIPN and NaBr were placed one line too low (both below the arrow). Brief error, corrected below.
4. Final brief (`brief.json`): as 3, with 4CzIPN and NaBr above the arrow, as in the crop. Drawn and rendered (`rendered.png`). Readback still reports the two co-reactants missing, so `checks_passed` is false.

## Convention check

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| comparison_layout: stacked_rows | two reactions stacked; the aldehyde is drawn again in each row | one aldehyde on the left, two arrows joined by a vertical line (divergent layout) | no |
| background_fill `#DEE2E3` | white page; the grey is only behind the bullet lists | white page, no fill | no |
| signature: bold panel letter and title | bold "D" and title "Aldehyde as alkyl radical precursors via decarbonylation" | not drawn | no |
| signature: grey boxes with square-bullet lists | square marker left of each row, italic dash-bullet claims at right | not drawn | no |
| signature: coloured substituent discs, red H | not in panel D (panels A and E) | not drawn | n/a |
| compound_label_face bold, compound_label_color `#000000` | no compound numbers in panel D | no labels | n/a |
| substrate_layout inline_plus | aldehyde + alkyne and aldehyde + acrylamide, inline | co-reactants not drawn | no |
| show_plus_sign true | plus sign between substrates | no plus sign | no |
| abbreviate_groups: tBu | tBu on both aldehydes and on both products | tBu | yes |
| abbreviate_groups: Me | Me on the aryl ring and on the acrylamide carbon | Me | yes |
| abbreviate_groups: Ph | amide written as a condensed CONHPh label | N with H below and a bond to Ph (skeletal, not condensed) | no |
| aromatic_rings kekule | kekule | kekule | yes |
| reagent_text_color `#000000` | black, except NaBr in navy bold italic | all black | partial |
| arrow_style plain | plain arrows | plain arrows | yes |
| new_bond_color null | the new tBu-CH2 bond of the amide is green | all black | no (card sets null; result.json is not in the case folder) |
| bond length : cap height = 2.06 | 60 : 30 px in the crop | not measured | unverified |
| line width = 0.09 bond length | 6 px in the crop | not measured | unverified |
| arrow length = 3.2 bond length | 330 : 60 px in the crop (5.5) | not measured | unverified |
| label font Arial | Arial (judged by eye) | ChemDraw ACS label font; no font record in the case | unverified |

Claimed items (non-n/a rows): 18 (17 table rows plus conditions placement). Matched after audit: 5 (tBu, Me, kekule, arrow style, conditions placement). See Audit.

## Differences from the paper

- Layout: the paper repeats the aldehyde in each row. The divergent layout draws it once.
- Co-reactants: the alkyne and the acrylamide are not drawn, so there are no plus signs. The readback reports them missing.
- Alkene: the paper's E/Z mixture (wavy bond) is drawn as E.
- Green new bond (tBu-CH2) in the paper, black in the replica.
- NaBr is navy bold italic in the paper, black in the replica.
- No panel letter or title, no grey bullet boxes, no light-bulb symbol above the 4CzIPN arrow.
- Balance warnings: the tool reports that both steps lack CO. The paper does not draw CO either, so this is a convention difference, not an error in the figure.
- Bond length, line width and arrow length were not measured on the replica.

## Tool gaps

- The divergent layout drops the second substrate of each step (readback: `alk`, `acr` missing).
- Two reactions with different co-reactants on one shared aldehyde cannot be drawn as stacked rows that each repeat the aldehyde. Independent steps are refused.
- An unspecified or wavy alkene cannot be drawn; the tool rewrites it as E and refuses the layout.
- No light-source symbol above an arrow.
- No panel letter or title element, no framed or shaded box, no bullet-list annotations.
- One text colour per figure (`reagent_text_color`); a single reagent (NaBr) cannot be coloured.

## Audit

Checked against reference.png (Figure 1 A-E; panel D enlarged) and rendered.png. The earlier count of 7 is withdrawn.

- Ph: the paper writes the amide as a condensed CONHPh label. The replica draws N, a separate H and a bond to Ph. Changed to no.
- Label font: no font record exists in the case, so Arial is judged by eye only. Changed to unverified.
- Count: 17 table rows plus conditions placement give 18. The matched rows are tBu, Me, kekule, arrow style and conditions placement, so 5/18.
- Proportions, line weight and arrow length stay unverified. reference.png is downscaled from the 5-panel figure, and the rough bond/cap-height estimate (about 1.7 to 2.2) cannot confirm 2.06.
- reagent_text_color stays partial. The replica is all black; the NaBr colour in the paper was not re-measured.
- Not in the folder and not checked: result.json (cited for new_bond_color), validation.json and the checks_passed readback.

Tool gaps the replicator did not list:

- A condensed group label such as CONHPh cannot be drawn. Only skeletal N and H with a bond to Ph is available.
- Per-bond colour is not exposed. The green new C-C bond in the paper cannot be drawn, because new_bond_color is null on the card.
- Ring substituent orientation is not controllable. The paper places the para-Me at the lower left; the replica places it at the upper right.

## Replay

    python skill/chemdraw/scripts/cdx.py py skill/chemdraw/assets/house-styles/jacs_au/replica/jacs_au-02/replay.py NEW_DIR
    python skill/chemdraw/scripts/cdx.py render NEW_DIR/figure.cdxml

`replay.py` runs `draw_figure` on `brief.json` and writes `figure.cdxml` and `validation.json` to a new folder.
