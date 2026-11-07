# Besenius et al.: organocatalytic ROP of N-acylated 1,4-oxazepan-7-ones (Scheme 1)

Source: Besenius et al., "1,4-Oxazepan-7-one trifluoroacetate: a modular monomer precursor for functional and biodegradable poly(amino esters)", *Polym. Chem.* **2025**. DOI: [10.1039/d5py00522a](https://doi.org/10.1039/d5py00522a).

Licence: CC BY 3.0 (from the house-style card); the reference crop is reproduced under that licence.

Drawing style: the `polymer_chemistry` house style in `brief.json` (base preset `rsc`). The crop is listed under the `polymer` and `reaction_scheme` figure types of the card.

## What is reproduced

The organocatalytic ring-opening polymerisation step of Scheme 1. An N-acyl 1,4-oxazepan-7-one is opened by benzyl alcohol with DBU and a thiourea co-catalyst (DCM, RT). The product is drawn as a three-unit poly(amino ester) chain with a benzyl ester end (BnO) and a hydroxyl end (OH).

Simplifications made to fit `draw_figure`:

- R = Me stands in for the four R groups of the scheme. The crop lists CH2CH2SMe, Me, allyl and an n-alkyl chain as wavy-bond fragments; Me is one of them.
- The product is a trimer. The paper draws one repeat unit in round brackets with a subscript n; `draw_figure` has no polymer kind, so neither the brackets nor the n are drawn.
- DBU and the thiourea are text ("DBU / thiourea") above the arrow, not structures.

| ID | Role | SMILES |
| --- | --- | --- |
| M | monomer, R = Me stand-in | `CC(=O)N1CCOC(=O)CC1` |
| P3 | three repeat units, BnO and OH ends | `c1ccccc1COC(=O)CCN(C(C)=O)CCOC(=O)CCN(C(C)=O)CCOC(=O)CCN(C(C)=O)CCO` |

The drawing reads back as the same two structures (readback `matched`). The step is flagged as unbalanced: the drawn reactant side is one monomer, and the tool reports the missing C21H30N2O7, which is two more monomers plus BnOH. That is the polymerisation stoichiometry (3 M + BnOH gives P3 with no by-product), not a missing by-product, and nothing was added to the drawing for it. The catalysts are not part of the balance.

## Replay

```
python skill/chemdraw/scripts/cdx.py py skill/chemdraw/assets/house-styles/polymer_chemistry/replica/polymer_chemistry-01/replay.py NEW_DIR
python skill/chemdraw/scripts/cdx.py render NEW_DIR/figure.cdxml
```

`replay.py` runs `draw_figure` on `brief.json` offline and writes `figure.cdxml` and `validation.json`. `rendered.png` is the desktop ChemDraw rendering of the same brief, downscaled to 1200 px wide.

## Conventions

Rows marked n/a are not visible in this crop and are excluded from the counts. Counted: 15 claims, 6 matched (after the audit below; the original count was 13 claims, 6 matched).

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| polymer: repeat unit in round brackets, subscript n at lower right | round brackets with n (crop 01) | three units, no brackets, no n | no |
| polymer: end groups drawn on both sides (BnO and OH) | BnO on the left, terminal H after the bracket on the right | both ends drawn, but mirrored: OH on the left, BnO on the right | yes (both ends drawn; order reversed) |
| polymer: block colours PS red, PDMS blue, pendants magenta (crop 05) | not in crop 01 | not drawn | n/a |
| polymer: monomer colours carried into the polymer (crop 03) | not in crop 01 | not drawn | n/a |
| reaction_scheme: organocatalysts drawn as structures above the arrow, slash between | DBU and thiourea structures with a slash | text "DBU / thiourea" | no |
| reaction_scheme: substituent options as R = list of wavy fragments under the product | four wavy R fragments under the product | not drawn; Me on monomer and product | no |
| reaction_scheme: no yields on polymerisation schemes | no yield | no yield | yes |
| reaction_scheme: bracketed step numbers [1], [2] (crop 02) | not in crop 01 | not drawn | n/a |
| reaction_scheme: bold panel letters (crops 02, 03) | not in crop 01 | not drawn | n/a |
| scheme: conditions split, reagents above and solvent below | catalysts above; BnOH, DCM, RT below | catalysts above; BnOH, DCM, rt below | yes (layout only; catalysts as text is the separate row above) |
| scheme: substrate_layout inline_plus | one substrate | one substrate | n/a |
| scheme: abbreviate_groups CF3 | CF3 on the thiourea (visible in crop 01) | thiourea is text; no CF3 drawn | no |
| scheme: aromatic_rings kekule | Kekule benzyl ring | Kekule benzyl ring | yes |
| scheme: reagent_text_color #000000 | black text | black text | yes |
| scheme: conditions text RT in capitals | RT | rt (the tool rewrites RT to rt; seen in the CDXML) | no |
| scheme: arrow_style plain | plain arrow | plain arrow | yes |
| scheme: show_plus_sign | no plus sign (one substrate) | no plus sign | n/a |
| measured: bond length over cap height 2.4 | card: 23 px over 9 px (2.6); on reference.png the bond is about 24 to 25 px and the B cap about 14 px (about 1.8) | 12.2 pt bond; cap about 5.0 pt from font metrics for 7 pt Helvetica (2.4 by calculation); rendered B cap about 14 px against a bond of about 34 px (about 2.4) | no |
| measured: line width over bond length 0.09 | card: about 2.5 px over 23 px, 0.11; reference arrow line about 2 px over about 24 px, about 0.08 | bonds 0.45 pt (document LineWidth, no bond override); arrow 0.60 pt; bond 0.45 over 12.2 pt, about 0.04 | no |
| measured: arrow length over bond length, median 7 | 440 px over 23 px, about 19 | 64 pt over 12.2 pt, about 5.3 | no |
| measured: label font Arial | Arial-like labels | Helvetica (CDXML font 4; Arial is font 3 in the file but unused) | no |
| compound label face and colour | no compound numbers in crop 01 | none drawn | n/a |

## Differences from the paper

- The catalysts are text above the arrow, not structures, so the slash between two structures becomes "DBU / thiourea". The thiourea is not named in the crop; the text is a stand-in.
- The monomer R is Me, not the crop's wavy-bond R list. The R list under the product is not drawn.
- The product is a three-unit chain with explicit ends. The paper's round brackets across the backbone and the subscript n are missing.
- The crop prints "RT"; the rendering prints "rt", because the tool normalises it.
- Labels are Helvetica in the rendering; the card and the crop use Arial.
- Strokes are lighter than the crop. Bonds are 0.45 pt against a 12.2 pt bond (about 0.04), where the crop is about 0.09 to 0.11. The arrow line is 0.60 pt.
- The product is mirrored relative to the paper: the rendering has OH at the left and BnO at the right, where the paper has BnO at the left.
- The arrow is about 5.3 bond lengths long; the crop arrow is about 19.
- The first brief labelled the monomer "M". The crop has no label, so the label was removed in the final brief.

## Tool gaps

- `draw_figure` accepts only `kind` scheme, scope or mechanism. There is no polymer kind, so repeat-unit brackets, a subscript n and a degree of polymerisation cannot be drawn.
- `above` and `below` take text lines only. Catalyst structures cannot be placed above the arrow, so the DBU and thiourea pair with its slash cannot be drawn.
- There is no wavy-bond or variable-R attachment, so the R list under the product cannot be drawn.
- The tool rewrites "RT" as "rt"; there is no option to keep the printed form.
- The house-style label font (Arial) and the line width over bond length are not applied. Only the base preset `rsc` is applied (bond 12.2 pt; label font Helvetica).
- Label size is fixed by the preset (LabelSize 7). No brief key sets it, so the ratio of bond length to label cap height cannot be tuned to the card.
- Scheme bonds take the document LineWidth (0.45 pt). The card's line_width_over_bond_length is applied only to mechanism curved arrows (`figure_house.py`).
- The validation report's style section lists applied and skipped items, but label font, line width and arrow length appear in neither list, so they are dropped silently.
- The arrow length follows the layout (here about 5.3 bond lengths), and no argument sets it.
- A polymerisation written as one monomer going to an oligomer is flagged as unbalanced. There is no n-mer notation.
- One `--render` attempt stopped at the 300 second tool timeout and left a lock folder in the scratch directory. A second attempt under a new name rendered. This is a process issue, not a drawing capability.

## Audit

Checked against `reference.png`, `rendered.png`, `polymer_chemistry.json` and an offline replay of `brief.json` (run into the scratch directory; its `figure.cdxml` and `validation.json` were read there, and nothing else was written). Image measurements are pixel counts from the two PNGs as supplied, antialiasing included, so each is about +/- 1 px.

Overclaims corrected:

- End groups: the table said BnO on the left. The rendering and the CDXML have OH on the left and BnO on the right. The row stays yes because both ends are drawn, but the mirror is now stated.
- Bond length over cap height 2.4 was marked matched. That value is a font-metric calculation (7 pt Helvetica cap of about 5 pt), not a measurement of the image. On the images, the paper's B cap is about 14 px against a bond of about 24 to 25 px (about 1.8); the rendering's B cap is about 14 px against about 34 px (about 2.4). The card's own 9 px cap does not reproduce from `reference.png`, so the card's 2.4 is also doubtful. The row is now no.
- Line width: bonds are 0.45 pt (document LineWidth; bonds carry no override). 0.60 pt is the arrow line only. The row stays no with corrected numbers.
- Conditions split was marked no while its own cells are identical. The layout matches (reagents above, solvent below); the failure is the catalysts-as-text row. The row is now yes.
- CF3 abbreviation was n/a although CF3 groups are visible on the thiourea in crop 01. The row is now no.
- RT in capitals was not listed. Added as no (the CDXML has `rt`).

Confirmed as stated: Kekule benzyl ring (ring bonds alternate between single and double in the CDXML); no yields; reagent text black (all text uses colour index 0, #000000); solid arrow head as in the paper, though the arrow line is about half the paper's weight; arrow about 5.3 bond lengths (64.2 pt over 12.2 pt); label font Helvetica, not Arial; readback matched; the step is unbalanced as stated and nothing was added to the drawing.

Corrected count: 15 claims, 6 matched (was 13 claims, 6 matched). The matched rows are end groups (both ends drawn), no yields, Kekule ring, black reagent text, plain solid arrow head and conditions split.

Proportions: `reference.png` is 783 by 260 px (about 3:1, with the R list under the product); `rendered.png` is 1200 by 160 px (about 7.5:1). The missing R list explains part of this. The paper's arrow is about 16 to 19 bond lengths against 5.3 here.

Tool gaps the replicator missed:

- Label size and face come from the preset (LabelSize 7; LabelFont 4, Helvetica). No brief key sets label size, so the bond to label ratio cannot be tuned. Arial (font 3) is in the file's font table but is not used.
- Bond line width is not set for schemes (bonds use the document 0.45 pt). The card's line width over bond length is applied only to mechanism curved arrows.
- The validation report omits label font, line width and arrow length from both its applied and skipped lists.
- The brief has no figure aspect or height control, so overall proportion cannot be set.
- The product's reading direction came out with OH at the left, although the SMILES starts at BnO. The cause was not checked; the brief does not choose it.
