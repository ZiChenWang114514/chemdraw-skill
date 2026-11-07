# Nature Portfolio: Table 1 scheme, electrochemical Ni-catalysed coupling of 1a and 2a

Source: Wang et al., *Nat. Commun.* **2025**, *16*, 1108. DOI: [10.1038/s41467-025-56377-w](https://doi.org/10.1038/s41467-025-56377-w).

Licence: CC BY 4.0. The reference crop (`reference.png`) is a copy of `skill/chemdraw/assets/house-styles/nature_portfolio/evidence/nature_portfolio-01.png`.

Drawing style: the `nature_portfolio` house style (base preset `nature`), card `toolkit/cdxml_toolkit/publication/house_styles/nature_portfolio.json`. `brief.json` sets `"style": "nature_portfolio"`.

Figure type: `reaction_scheme`. The card has no `figure_types` section, so the figure-type conventions were read from the top-level conventions and the evidence entry only (see Differences).

## What is reproduced

The whole scheme in the crop: 1a (1-chloropropylbenzene) and 2a (methyl 4-bromobenzoate) give 3a (methyl 4-(1-phenylpropyl)benzoate), with the electrode pair, catalyst and ligand above the arrow and electrolyte, base, solvent, current and time below. The crop shows no yield, so none is drawn. The stereocentre of 3a carries a bold wedge to the ethyl group in the crop; the brief gives the configuration as `CC[C@H]`, which RDKit assigns R. The crop also shows no structure for L1, so L1 is kept as a text label.

| ID | Structure (SMILES in brief.json) |
| --- | --- |
| 1a | `CCC(Cl)c1ccccc1` |
| 2a | `COC(=O)c1ccc(Br)cc1` |
| 3a | `CC[C@H](c1ccccc1)c1ccc(cc1)C(=O)OC` (R) |

The structures were read from the crop by eye (no OCSR run); the three SMILES parse in RDKit and the 3a configuration was checked by hand against the wedge.

## Replay

```
python skill/chemdraw/scripts/cdx.py py skill/chemdraw/assets/house-styles/nature_portfolio/replica/nature_portfolio-01/replay.py NEW_DIR
python skill/chemdraw/scripts/cdx.py render NEW_DIR/figure.cdxml
```

`replay.py` runs `draw_figure` on `brief.json` without network access and writes `figure.cdxml` and `validation.json`. `rendered.png` is the ChemDraw rendering from the first brief (downscaled from 1378 px to 1200 px wide).

## Attempts

1. Brief in this folder (`brief.json`). Rendered; `checks_passed: true`, readback `matched`. One warning: step 1 "does not balance" (BrCl missing), a reductive-coupling artefact (see Tool gaps). Kept as the replica.
2. 1a and 3a written in another SMILES order (`ClC(CC)c1ccccc1`; `c1ccccc1[C@@H](CC)...`, R). Rendered after about 5 min through `cdx.py render`. The product is flipped: the ester sits on the left, Ph and Et on the right, with a bold wedge pointing down to Et. Closer on the wedge type, further on the layout. Not kept.
3. 3a written as `CC[C@@H](c1ccc(cc1)C(=O)OC)c1ccccc1` (R), 1a as in attempt 1. Rendered the same way. The ester is again on the left and the wedge is bold and points down. Not kept.

Attempt 1 keeps the paper's left-to-right order (Ph, stereocentre, aryl, CO2Me) and the ester on the right; attempts 2 and 3 flip that order, so they were not kept. Every attempt's `draw_figure --render` call hit the 300 s tool limit, even though the CDXML was written, and `cdx.py render` on the same CDXML finished later. Renders for attempts 2 and 3 are in the scratch folder only.

## Table

Checked against the crop. Matched 11 of 24 rows after audit (the first count was 13 of 23; see Audit).

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| compound_label_face bold | bold 1a, 2a, 3a | bold | yes |
| compound_label_color #000000 | black | black | yes |
| compound_label_italic_suffix false | no suffix | no suffix | yes |
| yield_placement after_product_label | no yield in this scheme | no yield | no (n/a: the scheme has no yield) |
| conditions_split reagents_above_solvent_below | catalyst, ligand, electrodes above; electrolyte, base, solvent, current and time below | same split, but only because the brief lines are in the paper's order; the tool logs this convention as skipped (figure_house.py 396-397) | no |
| substrate_layout (card null) | 1a + 2a inline | inline with + | yes |
| show_plus_sign (card null) | + between substrates | + drawn | yes |
| abbreviate_groups Et | Et | Et | yes |
| abbreviate_groups Ph | phenyl drawn as rings in 1a and 3a | "Ph" label in 1a and 3a | no |
| CO2Me (not on the card list) | CO2Me in 2a and 3a | ester drawn as C(=O)O-Me | no |
| aromatic_rings kekule | Kekulé | Kekulé | yes |
| substrate_colors #0078B2 (first substrate) | 1a teal | 1a teal | yes |
| second substrate blue #0000FF (card lists one colour) | 2a blue | 2a black | no |
| product skeleton from substrates teal | Ph and CH(Et) teal in 3a | 3a black | no |
| new_bond_color (card null) | new C-C bond red #FF0000 | black | no |
| highlight_fill null | no fill | no fill | yes |
| reagent_text_color #000000 | black | black | yes |
| arrow_style plain | plain | plain | yes |
| bond length / label cap height 2.209 | about 2.2 | about 2.5 from the stated sizes (bond 10.8 pt, label 6 pt); about 2.8 by eye on rendered.png | no |
| line width / bond length 0.062 | about 0.06 (crop 3.5 / 52 = 0.067; the card's three crops range 0.043 to 0.075) | 0.056 (0.6 / 10.8), 10% below 0.062 | no |
| bold width / bond length 0.244 | bold wedge | 0.144 (1.56 / 10.8), hashed bond | no |
| arrow length / bond length 11.1 (card mean of 9.3, 12.7, 11.3) | 9.3 in this crop (484 / 52 px, measured) | about 8.5 (92 / 10.8 pt; 333 / 39 px on rendered.png) | no |
| stereo wedge to Et, bold, pointing up | bold wedge up | hashed bond pointing down; configuration R in both drawings | no |
| molecule orientation (1a, 2a, 3a) | 1a: Et up, Ph lower left, Cl lower right; 2a: Br top, CO2Me lower right; 3a: Et up, Ph lower left | all three flipped vertically (1a: Ph upper left, Et down; 2a: Br lower left, ester upper right; 3a: Ph upper left, Et down); rings also tilted by roughly 12 degrees | no |

## Differences from the paper

- Phenyl groups in 1a and 3a are written as "Ph" labels; the paper draws the rings. The card's abbreviate list includes Ph, so the tool contracts it.
- 2a and 3a show the ester as C(=O)O-Me, not the CO2Me label used in the paper.
- The second substrate (2a) is black, not blue; the product has no teal skeleton and no red new C-C bond.
- The stereocentre is drawn with a hashed bond down to Et; the paper uses a bold wedge up. The configuration is the same (R by CIP and by a hand check of the drawn geometry).
- Orientation: all three molecules are flipped vertically relative to the crop. In 1a and 3a the replica has Ph up and Et down where the paper has Et up and Ph lower left; in 2a the replica has Br lower left and the ester upper right where the paper has Br top and CO2Me lower right.
- Bold wedge width is 0.14 of the bond length against 0.24 in the paper, and label size is about 6 pt against the card's 7.3 pt estimate.
- The arrow is about 8.5 bond lengths long; the paper crop gives 9.3 and the card 11.1.
- The "(+)Pt | Ni foam (-)" electrode line is text, as in the paper.
- The reagent "NiBr2·glyme" is written with a middle dot; the crop has a bullet (•).

## Tool gaps

- substrate_colors colours only the substrates of a step; the substrate-derived part of the product is not coloured, so the teal product skeleton the card describes cannot be reproduced.
- No brief field for the wedge type or direction. The tool drew the stereocentre as a hashed bond pointing down, and the SMILES chirality alone decides which bond is hashed and where it points.
- No way to keep a group drawn as a ring when the card abbreviates it (Ph here).
- Bold wedge width and arrow length are fixed by the nature preset and the label text; the brief cannot set them.
- conditions_split is listed as skipped by the report, so the split is correct only because the brief was written in the paper's order.
- The balance check flags step 1 as missing BrCl. This is a reductive electrochemical coupling (RCl + ArBr + 2 e- gives RAr + Cl- + Br-), and the check has no electron accounting, so the warning is wrong here and nothing is drawn for it.
- `draw_figure --render` returned at the 300 s tool limit in every attempt, although the CDXML was written; `cdx.py render` on the same file finished after about 4 to 5 min. The cause (ChemDraw busy, a lock or a dialog) was not checked.
- The second substrate colour cannot be set. `substrate_colors` in the card is a single list indexed by substrate position (figure_house.py 333-346); with one entry, 2a cannot be blue, and the brief has no per-substrate colour field.
- `new_bond_color` is null in the card, although the card's own evidence entry records a red new C-C bond. The brief has no field for it, and the colouring path (figure_house.py 347-349) runs only when the card sets a value.
- The brief has no rotation or flip field, so the molecules cannot be drawn in the crop's orientation. The lower-level `compose_chemical_figure` manifest accepts molecule `rotation`, `color`, `highlight_bonds` and `bond_displays` (figure_tools.py 900-903), but the brief path does not expose them. This route was not tried.
- Per-label colour is not settable from the brief. The crop colours Br and CO2Me blue; `compose_chemical_figure` text objects accept a `color`, the brief does not.

## Audit

Audited against reference.png, rendered.png, the card, the evidence crop and the toolkit code (figure_house.py, figure_draw.py, report_tools.py, figure_tools.py). The first count was 13 of 23; the corrected count is 11 of 24.

Overclaims found and fixed:
- conditions_split was marked yes. The tool only logs the convention as skipped (figure_house.py 396-397), so the match rests on the order of the brief lines, not on the convention.
- Line width was marked yes. 0.056 is 10% below the card's 0.062. The card's three crops range from 0.043 to 0.075, so the value sits inside the evidence spread but not on the card value; the row is now no.
- The Differences section named only 3a as flipped. 1a and 2a are flipped vertically as well, and the rings are tilted, so the layout is not matched beyond the inline arrangement of the substrates. A row for this was added.
- The bond-to-label ratio of about 2.5 is computed from font size, not from a measured cap height. By eye on rendered.png it is near 2.8. Still not matched.

Checked and holding:
- reference.png is byte-identical to the evidence crop (cmp).
- Teal is about #0078B0 in the crop and the replica's 1a is the same teal, so the 1a row holds. The crop has blue (about #0000F8) on 2a and red on the new bond; the replica has neither.
- Stereocentre: 3a is R in both drawings (CIP from the SMILES, and from the drawn geometry with H in back in the crop and in front in the replica).
- Arrow shaft: 484 px in the crop and 333 px in rendered.png; the bond lengths used (52 px in the crop, about 39 px in the replica) give 9.3 and about 8.5 bond lengths.
- Kekulé rings, bold compound labels, black labels and reagent text, plain arrow, the "+" sign and inline substrates hold.
- Balance: check_reaction_balance compares atoms and charge only (report_tools.py, _balance_one, charge sums at lines 516-520). Electrons are not a term, so the BrCl warning is a false alarm for this reductive coupling, as the replicator said.

Not verifiable from this folder: validation.json, figure.cdxml and the scratch renders are not present. The checks_passed and readback claims, the line and bold widths in pt (0.6 / 10.8, 1.56 / 10.8) and the 300 s timings cannot be checked here.
