# Studer group: radical probe with Fe-H hydrogen atom transfer, Fig. 3B

Source: Studer et al., *Nat. Commun.* **2024**, "Iron-catalyzed radical Markovnikov hydrohalogenation and hydroazidation of alkenes". DOI: [10.1038/s41467-024-51706-x](https://doi.org/10.1038/s41467-024-51706-x).

Licence: CC BY 4.0. The reference crop (`reference.png`) is reproduced under that licence.

Drawing style: the `studer_group` house style in `brief.json` (base preset `nature`; bold compound labels, yield after the product label, inline plus, abbreviated groups, red new bond); see `cdx.py styles studer_group`.

## What is reproduced

Panel B, the radical-probe scheme: diene **10** and bromide **2a** (1.2 equiv) with Fe(acac)3 (10 mol %) and PhSiH3 (1.0 equiv) in MeOH at rt for 48 h give **11** in 49% yield (cis:trans = 9.1:1). The reagents are above the arrow, the solvent, temperature and time below it, as in the paper. The panel heading "C. Hydroazidation of a-pinene" at the foot of the crop belongs to the next panel and is not drawn.

Structures were read from the crop and checked with RDKit (no OCSR run):

- 10 = `CCOC(=O)C(CC=C)(CC=C)C(=O)OCC` (C13H20O4)
- 2a = `COC(=O)C(C)(C)Br` (C5H9BrO2)
- 11 = `CCOC(=O)C1(C(=O)OCC)CC(C)C(CBr)C1` (C13H21BrO4); the generic X of the paper is drawn as Br, and the cis:trans mixture is not drawn, as in the paper.

Brief tries: v1 used the bare label `2a`; v2 used a dummy atom `[*]` for X; v3 (submitted) adds the `(1.2 eq.)` annotation to 2a. v2 was rejected because the dummy atom is drawn as R and blocks the atom mapping, so no bond is coloured.

## Replay

```
python skill/chemdraw/scripts/cdx.py py skill/chemdraw/assets/house-styles/studer_group/replica/studer_group-06/replay.py NEW_DIR
python skill/chemdraw/scripts/cdx.py render NEW_DIR/figure.cdxml
```

`replay.py` runs `draw_figure` on `brief.json` offline and writes `figure.cdxml` and `validation.json`. `rendered.png` is the desktop ChemDraw rendering of the submitted brief, downscaled to 1200 px wide.

## Comparison

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| compound_label_face bold | 10, 2a and 11 bold | 10 and 11 bold; the 2a label is bold in full, so "(1.2 eq.)" is bold too (paper: regular) | no |
| compound_label_color #000000 | black | black | yes |
| yield_placement after_product_label, separator ", " | `11, 49% (...)` on the label line | same | yes |
| yield_format {value}% | 49% | 49% | yes |
| substrate_layout inline_plus | 10 + 2a on one row | same | yes |
| abbreviate_groups Me | the two methyls on 2a are bare bonds with no label | both methyls labelled Me | no |
| abbreviate_groups OMe | OMe written as one label, no bond between O and Me | O and Me joined by a visible bond (the OMe pattern excludes ester oxygens) | no |
| abbreviate_groups CO2Et (left-hand ester) | left ester spelled EtO2C on 10 and 11 | both esters spelled CO2Et on 10 and 11 | no |
| reagent_text_color #000000 | black | black | yes |
| arrow_style plain | plain arrow | plain arrow | yes |
| show_plus_sign true | + between 10 and 2a | same | yes |
| substrate_colors null, highlight_fill null | none | none | yes |
| conditions split (crop 06: reagents above, solvent, temperature and time below) | Fe(acac)3 and PhSiH3 above; MeOH, rt, 48 h below | same | yes |
| arrow_length_over_bond_length 6.9 | crop arrow 218 px over bond about 31 px = about 7.0 | arrow 292 px over bond about 42 px = about 6.9 | yes |
| bond_length_over_cap_height 2.5 | bond about 31 px over cap about 12 px = about 2.6 | bond about 42 px over cap about 16 to 17 px = about 2.5 | yes |
| line_width_over_bond_length 0.05 | about 1.8 px over bond 31 px = about 0.06 | about 2.3 px over bond 42 px = about 0.055 | yes |
| label_font Helvetica | Helvetica-like sans | CDXML LabelFont 3, Helvetica-like in the render | yes |
| new bond red #FF0000 on the transferred H | red C-H bond on the methyl; ring C-C bond black | red on the ring-closing C-C bond; the H is not drawn | no |
| variation_color #0000FF on the new C-X bond | blue C-X bond | C-Br bond black | no |
| yield cis:trans italic | italic *cis:trans* | plain text | no |

Claimed conventions: 20. Matched after audit: 13 (the replicator claimed 16; see Audit).

## Differences from the paper

- Ring orientation: the paper has the quaternary C(CO2Et)2 carbon at the top apex; the replica rotates the ring so the quaternary carbon sits on the right and the CH2Br arm points left.
- New-bond colour: `draw_figure` coloured every bond formed in the atom mapping. The ring-closing C-C bond between the two ring CH carbons is red, which the paper draws black. The transferred hydrogen of the methyl group is not drawn at all, so the red C-H bond of the paper is missing.
- X: drawn as Br, not as a generic X. The C-Br bond is black, not blue.
- Yield text: "(cis:trans = 9.1:1)" is plain; the paper sets cis and trans in italic.
- Label 2a: the replica bolds the whole label "2a (1.2 eq.)"; the paper bolds only "2a" and sets "(1.2 eq.)" in regular weight.
- Left-hand ester on 10 is spelled CO2Et; the paper spells it EtO2C.
- The step does not balance as drawn: the tool names the missing fragment C5H8O2 (the 2a radical remainder, plus the H from PhSiH3, which is not a species in the brief). The paper does not draw by-products either, so nothing was added.

## Tool gaps

- `new_bond_color` applies to every bond the atom mapping finds as formed; there is no way to colour only the transferred H or only the new C-X bond, so a ring-closing C-C bond turns red here.
- Explicit hydrogens are removed when the SMILES is read, so a transferred H cannot be drawn or coloured, and hydrogens are not mapped.
- `figure_types.reaction_scheme.conventions.variation_color` is not applied by `draw_figure` (the report's `applied` list has no blue colour).
- A generic atom (`[*]`) is drawn as "R", not "X", and makes the atom mapping fail, so `new_bond_color` is skipped for the whole step ("no formed bond could be mapped").
- No mixed-weight substrate labels: a substrate label is one string and its face applies to every run, so "2a" cannot be bold with a regular "(1.2 eq.)"; compound_label_italic_suffix is skipped ("not applied yet" in figure_house.py). The yield path does give mixed weight: the rendered 11 label is a bold "11" followed by regular text.
- No italic run inside yield text, so *cis:trans* cannot be set in italic.
- No control of product ring orientation or apex position.
- The left-hand ester spelling is the known right-flowing spelling; it needs Clean Up Structure on the file to match the paper.

## Audit

Re-checked by pixel measurement and zoomed crops of reference.png and rendered.png, and by reading the toolkit code (house_styles.py, figure_house.py). Corrected matched count: 13 of 20 (the replicator claimed 16). Rows changed: compound_label_face, abbreviate_groups Me, abbreviate_groups OMe (and CO2Et scope widened to 10 and 11), and the two cited pixel rows. The rows kept as yes (label colour, yield placement convention, yield format, inline plus, reagent colour, arrow style, plus sign, substrate colours, conditions split, arrow ratio, bond/cap ratio, line width, label font) rest on the image; the ratios are rough (about 1 px error on a 12 to 17 px cap height).

Overclaims:
- The two methyls of 2a are bare bonds in the paper. The replica labels them Me, so the Me row is false. The house-style Me entry does not describe this paper.
- The paper writes OMe as one label with no bond to O. The replica draws a bond from O to Me. The OMe pattern in toolkit/cdxml_toolkit/publication/house_styles.py excludes ester oxygen, so this methyl ester is never contracted.
- The 2a label is bold in full in the replica; the paper bolds only "2a".
- The quoted pixel values (329 px arrow, 48 px bond, 19 px cap, 3 px line) do not occur in this image. reference.png is byte-identical to evidence/studer_group-06.png, 900 px wide, with an arrow of 218 px and a bond of about 31 px. The ratios are close enough to stand, but the pixel values should not be cited as measured.
- The tool-gap bullet "no mixed-weight label runs" is too broad (corrected above).
- The C5H8O2 note says "plus the H from PhSiH3". The balance is: 10 + 2a is C18H29BrO6 in the brief, 11 is C13H21BrO4, so the difference C5H8O2 is the 2a radical remainder C5H9O2 less the H that PhSiH3 supplies and the brief omits. The sign is wrong, not the species.

Differences not listed in the case:
- Compound 10: the paper has the quaternary carbon at the top with both allyl chains going down. The replica has the quaternary carbon mid-left, one allyl chain pointing up and esters left and upper right.
- Compound 2a: the paper has Br at upper left, two bare methyls going down and the C=O up right. The replica has Me up left, Br lower left, and a different rotation.
- Both esters on 11 are CO2Et in the replica (paper: EtO2C left, CO2Et right).
- The yield label is centred under the whole product in the paper (centre at the product centre). In the replica it sits about 27 px (on the 1200 px render) right of the product centre.
- The product constitution is correct: 3-methyl and 4-CH2Br on the cyclopentane-1,1-diester, as in the paper (stereochemistry not drawn in either).

Tool gaps the replicator missed:
- Ester OMe is excluded from OMe contraction by the SMARTS in house_styles.py.
- abbreviate_groups is global: Me matches every CH3, so a terminal methyl cannot be left as a bare bond under a house style that lists Me.
- No orientation or apex control for any structure (10, 2a and 11), not only 11. No rotation option was found in figure_draw.py or figure_house.py.
- variation_color is declared for reaction_scheme in house_styles.py, but nothing in figure_draw.py or figure_house.py applies it (confirmed by grep).
- The yield label has no horizontal centring under the product, and format_yield returns a plain string, so no italic run is possible in yield text.
- Ester spelling follows the layout direction (the abbreviation table has separate left and right spellings); no per-group override was found, so EtO2C on the left cannot be forced.
