# J. Chem. Educ. 2024: Deuteration of watermelon ketone 1 (Figure 3, top reaction)

Source: Deufel, van Gemmeren et al., "Deuteration of Arenes via Pd-Catalyzed C-H Activation: A Lesson in Nondirected C-H Activation, Isotopic Labeling, and NMR Characterization", *J. Chem. Educ.* **2024**, *101*, 3410-3417. DOI: [10.1021/acs.jchemed.4c00270](https://doi.org/10.1021/acs.jchemed.4c00270).

Licence: CC BY 4.0. The reference crop (`reference.png`) is the house-style evidence crop `evidence/jchem_educ-01.png` reproduced under that licence.

Drawing style: the `jchem_educ` house style (base preset ACS Document 1996) from `brief.json`; see `cdx.py styles jchem_educ`.

Figure type: `reaction_scheme`.

## What is reproduced

The top reaction of Figure 3 only: watermelon ketone 1 (`Cc1ccc2OCC(=O)COc2c1`, C10H10O3, checked with RDKit) to the deuterated product 1-dx, with the conditions above the arrow (L1, L2, Pd(OAc)2) and below it (HFIP, D2O). The product is drawn with the same skeleton as 1, labelled 1-dx, because the positions and extent of deuteration are not defined in the figure (see below).

The bottom reaction (4-tert-butylphenol 2 to 2-dx) is not drawn. draw_figure takes one connected scheme per brief, and the two rows share no species, so the second row would need its own file.

The structures were read by eye from the crop and checked with RDKit; OCSR was not run. The caption's catalyst loadings (L1 20 mol %, L2 30 mol %, Pd(OAc)2 10 mol %), HFIP:D2O ratio, 1 M, 80 °C and 18 h are not in the crop and are not drawn.

## Replay

```
python skill/chemdraw/scripts/cdx.py py skill/chemdraw/assets/house-styles/jchem_educ/replica/jchem_educ-01/replay.py NEW_DIR
python skill/chemdraw/scripts/cdx.py render NEW_DIR/figure.cdxml
```

`replay.py` runs `draw_figure` on `brief.json` offline and writes `figure.cdxml` and `validation.json`. Compare the PNG with `reference.png`; `rendered.png` is the ChemDraw rendering of this run, downscaled to 1200 px wide.

## Convention table

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| compound labels bold (`compound_label_face`) | bold 1 and 1-dx | bold 1 and 1-dx | yes |
| compound label colour black (`compound_label_color`) | black | black | yes |
| italic isotopologue suffix (`compound_label_italic_suffix`) | italic d and x in 1-dx | 1-dx, all upright bold | no |
| plain thin arrow with small filled head (`arrow_style` plain) | yes | yes | yes |
| arrow about 9.2 bond lengths (`arrow_length_over_bond_length`) | 282 px over 30.5 px bond in the crop | 85.2 pt arrow over 14.4 pt bond, 5.9 bond lengths (CDXML; the render agrees) | no |
| conditions above the arrow in plain Arial | L1, L2, Pd(OAc)2 above, heavier type by eye, L1 and L2 coloured | same text, plain face, black | no |
| solvent and reagent below the arrow | HFIP structure and bold D2O below | text "HFIP, D2O" below | no (no structure, D2O not bold) |
| ligand colours L1 teal #005474, L2 orange #D87C5C | teal and orange | black | no |
| Pd(OAc)2 in metal-salt grey | grey | black | no |
| HFIP drawn inline as a light grey structure | yes | text only | no |
| Kekule aromatic rings (`aromatic_rings` kekule) | yes | yes | yes |
| no yield on the arrow (`yield_placement` null) | none | none | yes |

The table has 12 rows: the conventions and signature features the card claims for the reaction_scheme figure type that appear in this crop. Five match (bold labels, black labels, plain arrow style, Kekule rings, no yield). The other seven do not match, including the two partial rows. See the Audit section for the checks.

## Differences from the paper

- Product 1-dx is drawn with the same skeleton as 1. The paper marks the deuterium sites with a blue bond-crossing line and a D_X label; draw_figure cannot draw that marker, and the positions are not stated, so no deuterium atoms were placed.
- L1 and L2 are not coloured teal and orange, and Pd(OAc)2 is not grey, because the house style leaves reagent text colour null and draw_figure applies one colour to the whole condition line.
- HFIP is written as text, not drawn as the light grey structure in the conditions.
- D2O is not bold in the replica (it is bold in the paper).
- The italic d in the label 1-dx is upright.
- Only the top reaction is drawn; the bottom reaction is not in this file.
- The layout is a single row with the conditions above and below the arrow. It does not match the crop's arrangement: the HFIP structure is missing, and the arrow is too short for the molecules (5.9 bond lengths against 9.2 in the crop). The ring orientation and methyl position match by eye: the methyl is para to one ring oxygen and meta to the other, as in the SMILES.

## Tool gaps

These are gaps of `draw_figure`. The toolkit has more; see the last paragraph.

- `compound_label_italic_suffix` is listed under `style.skipped` ("not applied yet"), so no italic suffix on labels such as 1-dx.
- No per-run text colour and no bold run inside `above` or `below` lines. The ligand colours (L1 teal, L2 orange), the grey Pd(OAc)2 and the bold D2O cannot be reproduced. `reagent_text_color` is null on this card, so the house style does not apply colour either, although the card's signature features list the ligand colours. The card contradicts itself here.
- `above` and `below` take text lines only. A structure such as HFIP cannot be drawn inline in the conditions in draw_figure.
- No deuterium-site marker: nothing draws a bond-crossing line with a D_X label on a species, and the extent of deuteration (the x in dx) cannot be expressed as a SMILES without inventing positions.
- Two reactions that share no species cannot be placed in one draw_figure scheme (the docs say steps that fit none of the layouts are refused), so a two-row figure needs two files or a manual composition step.
- Card values silently not applied (not in `style.skipped`): `arrow_length_over_bond_length` (9.2), the measured line width (0.05 bond length) and bond length over cap height (2.2) are not read by any code path. Here the arrow is set by the layout (5.9 bond lengths), the line is the preset 0.60 pt (0.72 pt wanted) and the bond is 14.4 pt (about 2.0 cap heights).

Other toolkit path: `compose_chemical_figure` (manifest; `toolkit/cdxml_toolkit/mcp_runtime/figure_tools.py`, see `skill/chemdraw/references/publication-figures.md`) has text runs with bold, italic, subscript, superscript and per-run colour, coloured `line` and `arrow` items with explicit start and end points, and molecules placed by position on one page. With it, the italic suffix, coloured ligand names, bold D2O, a blue D-marker line, an explicit 9.2-bond arrow and a two-row page are possible with hand-placed coordinates. Whether a molecule can take a grey colour for the HFIP structure was not checked, and the extent of deuteration still has to be given.

## Audit

Checked against `reference.png`, `rendered.png`, the card in `toolkit/cdxml_toolkit/publication/house_styles/jchem_educ.json`, and a fresh replay of `brief.json` into a temporary folder (its `figure.cdxml` was read for bond lengths, arrow geometry, bond orders and run formatting). No other file in the case folder was changed.

- Overclaim: the arrow length was marked "not measured". It is measurable and does not match: 85.2 pt over a 14.4 pt bond is 5.9 bond lengths, against 9.2 in the crop (282 px over 30.5 px). `rendered.png` agrees (arrow 335 px at about 3.93 px per pt).
- Overclaim: the layout was said to match the crop's arrangement. It does not: the HFIP structure is missing and the arrow is too short for the molecules.
- Overstatement: the two partial rows were counted as not matched, but they also fail on weight and structure, so the table now marks them "no".
- Miscount: the table has 12 rows, not 11.
- Overstatement: the tool-gap list reads as a toolkit limit. Several items are draw_figure limits only; `compose_chemical_figure` has bold, italic and coloured runs, coloured lines and multi-row pages.
- Missed gap: the card's arrow length, line width and bond-to-cap-height values are silently ignored by draw_figure.
- Not matched on line weight: 0.60 pt (0.042 bond) against the card's 0.05 bond. The arrow style key itself matches.

Confirmed: bold labels (both labels face 1), black labels, plain arrow shaft with a filled full head, Kekule rings (8 double bonds in CDXML: 3 per benzene ring and 1 per ketone, for both structures), no yield, and the SMILES formula C10H10O3 (RDKit). The Pd(OAc)2 in the crop is grey (darkest pixels about #6B6B6B) and is black in the replica.

Corrected matched count: 5 of 12 rows. The same five rows match as the replicator claimed; the "11" was a miscount of the table's 12 rows.
