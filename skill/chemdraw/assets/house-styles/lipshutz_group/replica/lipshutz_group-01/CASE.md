# lipshutz_group, Figure 3 (amination scope), top reaction: replica

## Source

Iyer, Lipshutz et al., "Ligated Pd-Catalyzed Aminations of Aryl/Heteroaryl Halides with Aliphatic Amines under Sustainable Aqueous Micellar Conditions", *JACS Au* **2024**, *4*, 680. DOI: [10.1021/jacsau.3c00742](https://doi.org/10.1021/jacsau.3c00742).

Licence: CC BY 4.0. The reference crop is `evidence/lipshutz_group-01.png` from the house-style card and is reproduced under that licence.

Figure type: `reaction_scheme`. The card has no `figure_types` section (see card errors), so the conventions tested here are the card's top-level conventions and its signature features.

## What is reproduced

The top reaction of Figure 3: aryl halide + primary amine, with `[Pd(crotyl)Cl]2 (0.25 mol %)`, L1 (2 mol %), KOtBu (2 equiv), 2 wt % Savie/H2O (0.5 M), 10 v/v % THF, 60 °C, and the N-arylated product.

The crop draws a generic aryl `R`/`X` (X = Br, Cl) and a generic amine `HN(R'')(R')`. The brief uses the worked example that the same figure gives as compound 3 (X = Br, 86%, 1 h, lower scope row):

- aryl bromide `Brc1ccc(OC(F)(F)F)cc1` (4-bromo-(trifluoromethoxy)benzene, C7H4BrF3O);
- amine `CCCCN` (n-butylamine, R' = butyl, R'' = H);
- product `CCCCNc1ccc(OC(F)(F)F)cc1` (compound 3, C11H14F3NO), with label 3 and yield 86%.

The SMILES were checked with RDKit (canonical form and molecular formula).

The BippyPhos grey box, the dashed separator and the scope row are not drawn (see Tool gaps).

## Replay

```
python skill/chemdraw/scripts/cdx.py py skill/chemdraw/assets/house-styles/lipshutz_group/replica/lipshutz_group-01/replay.py NEW_DIR
python skill/chemdraw/scripts/cdx.py render NEW_DIR/figure.cdxml
```

`replay.py` runs `draw_figure` on `brief.json` offline and writes `figure.cdxml` and `validation.json`. `rendered.png` is the desktop ChemDraw render, downscaled to 1200 px wide.

Draw report: `style.applied` lists `compound_label_face=bold`, `yield_placement=under_product_label`, `show_plus_sign=true`, `reagent_text_color=#000000`, `substrate_layout=inline_plus` and `abbreviate_groups (2 contracted)`. `style.skipped` lists `conditions_split`, `yield_separator`, `new_bond_color`, `highlight_fill` and `substrate_colors`. `readback` matched (3 structures), `checks_passed` true, native rendered.

## Convention check

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| compound_label_face bold | bold compound numbers (2, 3, 4, 6, 7, 8) | bold `3` | yes |
| compound_label_color #000000 | black | black | yes |
| yield_placement under_product_label | 82% under the number 2 | 86% under the number 3 | yes |
| yield_format {value}% | `X = Br, 82%,a 1.5 h` (condition and footnote mark on the line) | `86%` (bare value; no condition, no footnote) | no |
| conditions_split reagents_above_solvent_below | catalyst and base above, surfactant/H2O and THF/temperature below | same split, supplied in the brief (the tool keeps it as given) | yes |
| substrate_layout inline_plus | ArX + amine on one row | ArBr + amine on one row | yes |
| abbreviate_groups CF3 | F3C-O (CF3 label) | O-CF3 with CF3 label | yes |
| aromatic_rings kekule | alternating double bonds in the rings | same | yes |
| substrate_colors null | black substrates | black substrates | yes |
| highlight_fill null | no fill in this scheme | no fill | yes |
| reagent_text_color #000000 | black | black | yes |
| arrow_style plain | plain arrow | plain arrow | yes |
| show_plus_sign true | "+" between substrates | "+" between substrates | yes |
| signature: surfactant and water below the arrow | 2 wt % Savie/H2O (0.5 M) | 2 wt % Savie/H2O (0.5 M) | yes |
| new_bond_color null (card) | new C-N bond in purple #840CFC | new C-N bond black; the tool skipped the colour because the card value is null | no |
| signature: purple #840CFC marks the new C-N bond | purple bond | black bond | no |
| signature: yield line combines a condition and the yield (X = Br, 82%) | `X = Br, 82%,a 1.5 h` in the scope row | yield only, `86%` | no |

Counted: 13 of 17 convention rows match (the first count of 14 included the yield format row, which does not hold; see Audit). Not counted, because the crop does not allow a measured check: the bond-length to cap-height ratio (2.2), line width (0.055 bond length), arrow length (6.3 bond lengths) and label font (Helvetica). The replica looks similar by eye; these were not measured, and the tool does not apply the card's measured geometry (see Tool gaps). The bold blue italic section headers belong to scope figures, so they do not apply to this scheme.

## Differences from the paper

- Substrates are concrete (4-bromo-(trifluoromethoxy)benzene and n-butylamine) where the paper shows generic `R`, `X` and `HN(R'')(R')`. The product is compound 3, so the scheme is the paper's reaction for that entry, not the generic template.
- The purple new C-N bond of the paper is drawn black. The card's own signature feature asks for purple, but the card's `new_bond_color` is null, so the tool does not colour it.
- The BippyPhos grey box (ligand structure with a bold `L1` label and a Ph/t-Bu structure) and the dashed vertical separator are not drawn. The ligand structure was not transcribed because its SMILES could not be verified from the crop.
- The yield line shows only `86%`. The paper combines the halide and time (`X = Br, 86%,a 1 h`) with a superscript footnote mark `a`. The brief could carry the full line as text (the tool keeps text that is not a bare value), but this drawing uses the bare value, and the footnote mark cannot be drawn.
- The reagent `L1` is plain text here; the paper sets it in bold.
- The tool reports that step 1 does not balance because the products lack HBr. This is named, not drawn. The paper does not draw the HBr by-product either, so the drawing matches the paper; the warning is expected.
- The scope row (2, 3, 4, 6, 7, 8) with its bold italic blue headers and frame is not reproduced. Scope panels take only the base preset, so the house conventions cannot be applied to them.

## Tool gaps

- No drawer for a grey ligand panel (shaded box with a structure and a bold label). The ligand has to be added by hand or by `cdx.py build`. `ring_fills` and `atom_halos` colour rings and atoms only, so they cannot make a panel.
- No drawer for a dashed vertical separator between two schemes.
- The card's measured geometry (`bond_length_over_cap_height`, `line_width_over_bond_length`, `arrow_length_over_bond_length`) is not used by `figure_house.py` or `figure_draw.py`. The scheme takes the base preset's geometry, so the proportions cannot match the card by design.
- No caption text under a structure in a scheme (the paper's `(X = Br, Cl)` and `(R' = Alkyl)` captions). Only scope panels take `footnotes`; a scheme has no footnote field.
- No italic run in a reagent or yield line (the `t` of `tBu` in `KOtBu` is italic in the paper). The reagent path has no bold or italic markup.
- No generic substituents in `draw_figure` (R on an aryl ring, X = Br or Cl, R' and R'' as alkyl or H). Each structure must be a concrete SMILES, so a Markush-style scheme needs the markush tool or a manual drawing.
- `new_bond_color` is taken only from the card. A brief cannot set a bond colour for one figure, so the purple bond of this paper cannot be produced from the brief, and the card value is null.
- The yield line under a product label is drawn as one plain run (face forced to plain, no chemistry formatting). A text yield such as `X = Br, 86%, 1 h` is kept as written, but a superscript footnote mark (`a`) and any bold or italic part cannot be drawn, though the card's signature feature asks for the combined line with a footnote.
- A bold run inside a reagent line (`L1` in bold) is not supported.
- Scope panels ignore the house style (the report says they take only the base preset), so the scope row of this figure cannot be reproduced with the card's conventions.
- Label font: the card's measured `label_font` (Helvetica) is not applied by the tool. The render uses the ChemDraw default sans-serif.
- The first `draw` attempt failed with `worker_out_of_memory` (OpenBLAS allocation). A second attempt with a new output name succeeded. This is a runtime reliability problem, not a drawing capability.

## Audit

Checked by viewing `reference.png` (the full Figure 3 crop), `rendered.png` (the single scheme, 1200 px wide), an enlarged crop of the replica's label and yield, and the card JSON. The drawing code (`figure_house.py`, `figure_draw.py`, `render/renderer.py`) was read, not run. No file other than this one was changed.

Overclaims corrected:

- The `yield_format` row claimed the paper's yield is `82%`. The paper line is `X = Br, 82%,a 1.5 h`, so the format match rests on a misquoted paper value. Changed to no.
- The tool gap "a combined condition-and-yield line cannot be expressed" is wrong as stated. `format_yield` returns text that is not a bare value unchanged, so the full line can be passed. What cannot be drawn is the superscript footnote and any bold or italic part.
- `conditions_split` matches the paper picture, but the draw report lists `conditions_split` as skipped, so the split comes from the brief, not from the house convention. The row stays a match on the picture only.
- The `compound_label_face bold` row holds. The enlarged crop shows a bold `3`.
- The `abbreviate_groups CF3` row holds. The paper's OCF3 sits on the other side of the ring, so the CF3 label extends to the other side, with the same outward convention.
- The `aromatic_rings kekule`, colour, arrow and plus-sign rows hold at this resolution.

Tool gaps the replicator missed: the card's measured geometry is not applied at all; there is no caption field under a scheme structure; there is no italic run; and a scheme has no footnote field.

Card inconsistency, not the replica's fault: the card's own evidence values give a bond-to-cap-height ratio of 79/46 = 1.7, not the stated 2.2, and an arrow of 592/79 = 7.5 bond lengths, not the stated 6.3. The card's measured values need rechecking before any geometry claim is made.

Not verifiable from this folder: `validation.json` is not present, so the readback, `checks_passed` and "native rendered" claims are unchecked. The formulas match the SMILES on hand count (C7H4BrF3O, C11H14F3NO).

Corrected count: 13 of 17 convention rows match.
