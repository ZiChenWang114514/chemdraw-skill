# RSC house style replica: Pd-catalysed annulation of a 2-vinylbenzoic acid with an alkyne (entry 3a)

Source: Cen et al., "Edge Article", *Chem. Sci.* **2024**, DOI: [10.1039/d4sc05429f](https://doi.org/10.1039/d4sc05429f). Licence: CC BY 3.0 (from the card `rsc_journals.json`); the reference crop is reproduced under that licence.

Figure: Table 2, the scope table header (reaction scheme 1 + 2 to 3, with conditions) and the first scope entry 3a. Crop: `skill/chemdraw/assets/house-styles/rsc_journals/evidence/rsc_journals-01.png` (copied here as `reference.png`).

Drawing style: `rsc_journals` house style (base preset `rsc`); `brief.json` sets `"style": "rsc_journals"`.

Figure type: `reaction_scheme`. The card has no `figure_types` section, so only its top-level conventions could be checked.

## What is reproduced

The header reaction for the entry 3a, with the Ar and R of the generic scheme set to phenyl (the 3a entry of the same table):

- 1 = 2-(1-phenylvinyl)benzoic acid, `OC(=O)c1ccccc1C(=C)c1ccccc1`
- 2 = phenylacetylene, `C#Cc1ccccc1`
- 3a = 1,3-diphenylnaphthalene, `c1(-c2ccccc2)cc(-c2ccccc2)cc2ccccc12`

Above the arrow: PdCl2 (5 mol%), Piv2O (1.4 equiv); DMAP (1.0 equiv), TFP (10 mol%); LiBr (0.5 equiv). Below: Dioxane, 160 °C. Yield 77% (84%).

The structures were read from the crop (the first row of the table draws 3a with two phenyl groups). No OCSR run was needed. The three SMILES were checked with RDKit (C15H12O2, C8H6, C22H16). Ar and R are not expressible as generic groups in `draw_figure`, so the replica is one concrete entry. The rest of the table (3b to 3s) is not drawn.

## Brief iterations

- Try 1 (`brief.json` variant with `"yield": "77% (84%)"` on the step): the tool places the yield under the arrow, below the conditions. Rendered; this is not how the paper places it.
- Try 2 (final, `brief.json`): the yield is typed into the product label (`"label": "3a, 77% (84%)"`) and the step carries no `yield` key. The tool's yield placement is `null` in the card, so this is a text workaround. Rendered as `rendered.png`.

Try 2 passed the layout and readback checks (`readback` matched, 3 structures; `checks_passed` true) and has one balance warning (see below). The try 1 report was not saved, so only its render is kept (`figure-try1.png` in the scratch folder).

Reproduction: `replay.py` runs `draw_figure` on `brief.json` offline and writes `figure.cdxml` and `validation.json`. It was run once in the scratch folder and reported `checks_passed: true`.

## Convention table

Card conventions (top level, all 15 keys), then the visible scheme features.

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| compound label face: bold | "3a," bold; "77% (84%)" regular | whole line bold (yield typed into the label) | no |
| compound label colour #000000 | black | black | yes |
| compound label italic suffix: off | upright "a" | upright "3a" | yes |
| yield placement (card null; observed: after the product label) | "3a, 77% (84%)" on the product label line | typed into the label text (try 2), so the yield is bold; the tool default would put it under the arrow | no |
| yield format (card null; observed "77% (84%)") | 77% (84%), plain | 77% (84%) typed in the label, bold | no (characters match, weight does not) |
| conditions split: reagents above, solvent and temperature below | three lines above, "Dioxane, 160 °C" below | same | yes |
| substrate layout: inline A + B | 1 + 2 inline | inline with plus sign | yes |
| abbreviate groups (OMe, CF3, OCF3) | no such group in 3a | none drawn | not exercised |
| aromatic rings: Kekule | Kekule | Kekule | yes |
| new bond colour (card null; observed magenta) | 3a: 3-phenyl ring and new ring bonds magenta | black | no |
| substrate colours (card null; observed navy and magenta) | header 1 navy (with Ar), header 2 magenta (with R); 3a naphthalene and 1-phenyl navy | all black | no |
| highlight fill (null) | none | none | yes |
| reagent text colour #000000 | black | black | yes |
| arrow style: plain | plain arrow | plain arrow | yes |
| show plus sign | "+" between 1 and 2 | "+" present | yes |
| arrow length / bond length (about 11.9 in the crop) | 452 / 38 px = 11.9 | 140 / 12.2 pt = 11.5 (pixel estimate about 11) | not established |
| line width / bond length (about 0.05) | 2 / 38 px = 0.053 | 0.6 / 12.2 pt = 0.049 | not established (cannot be resolved at this scale) |
| label size relative to bond (crop: about 7.9 pt) | about 7.9 pt | 7 pt (rsc preset LabelSize) | no, about 11% smaller by point size and about 20 to 25% by cap height to bond in pixels |
| label font: Arial | Arial | Helvetica (font 4 in the rsc preset) | close, not identical |
| product orientation (1-aryl at top) | aryl at top of the right ring | aryl at lower left of the naphthalene | no |

## Differences from the paper

- Ar and R are concrete phenyl groups; the paper draws the generic Ar and R and the scope entries.
- Colour: the paper colours the acid-derived part navy (header 1 and the naphthalene of 3a) and the alkyne-derived part magenta (header 2, the 3-phenyl ring of 3a and the new ring bonds). The replica is black because the card gives no colour for substrates or new bonds and the brief has no colour keys.
- Yield: printed in the label text, not by a placement convention, so the whole label line is bold. In the crop only "3a," is bold and "77% (84%)" is regular, so this is a visible difference.
- Label size: the rsc preset draws atom and compound labels at 7 pt; the crop suggests about 7.9 pt.
- Orientation: the tool chose the naphthalene orientation; the paper's 1-aryl sits at the top of the right-hand ring.
- Scope panel (3b to 3s), the generic Ar and R, and the abbreviations OMe, OPh, SMe, CF3, OCF3 and CO2Me of the other entries are not drawn.
- The step does not balance as drawn: the warning says the products lack CH2O2 (by atom count this is CO2 plus H2, consistent with a decarboxylative oxidative annulation). The tool names the missing by-products and does not draw them, so no CO2 or H2 appears on the arrow.

## Tool gaps

- The brief has no colour keys for species or bonds (`BRIEF_KEYS` is `kind`, `species`, `steps`, `max_width`, `title`, `style`, `layout`). Substrate and new-bond colours can come only from the card, which is `null` here.
- The rsc card leaves yield placement null (`after_product_label` and `yield_separator` are not set), so the paper's "3a, 77% (84%)" can only be typed as label text. The code does support this placement (see the Audit).
- No way to draw a by-product (CO2, H2 or an oxidant) on a step; a non-balancing step is reported and not drawn.
- No way to control the orientation of a structure or of a ring in the layout.
- The rsc preset's label size (7 pt) does not match the card's measured estimate (7.9 pt).
- Generic substituents (Ar, R) cannot be expressed in a `draw_figure` species; each entry must be concrete.

## Audit

Checked by opening both images, measuring them in pixels, and reading brief.json, the card and the toolkit code (`figure_draw.py`, `figure_house.py`, `house_styles.py`). Where unsure, a row was marked not matched. Only this file was edited.

**Overclaims corrected above**

- "3a is drawn all navy" was false. The 3-phenyl ring and the new ring bonds are magenta, and header 2 is magenta with its R label magenta; header 1 and its Ar are navy.
- The compound label and yield rows were marked matched. The yield run is regular in the paper and bold in the replica, and it is not hard to judge at this size.
- "No yield placement after the product label" is a card-data gap, not a tool gap. `figure_house.py` implements `after_product_label`, `after_product_label_parenthesised` and `yield_separator`, which write the yield as a separate plain run. Six other cards already use them. Setting these in the rsc card (not done here) would likely fix the bold yield.
- Arrow/bond and line width were marked matched without support. In pixels the replica arrow is about 11 bond lengths (445 px arrow, bond about 40 px). The reference is about 13 (277 px arrow, bond about 21 px in the downscaled image). Line width cannot be resolved at this scale.
- The label size gap is larger than 11% by cap height to bond length: the replica's cap is about 16 px against a bond of about 40 px, the reference's about 11 px against about 21 px.
- reference.png is the whole top of Table 2 (rows 3b to 3s included), not only the header and 3a crop. The "not drawn" statement is correct.
- The following cannot be checked because the case folder has no validation.json, figure-try1.png or run log: checks_passed, readback, worker_crashed after 107 s, the RDKit check, and font 4 of the preset.

**Corrected count:** 9 of 15 card conventions, not 11. Matched: label colour, italic suffix, conditions split, inline substrate layout, Kekule rings, highlight fill (nothing drawn in either), reagent text colour, plain arrow, plus sign. Not matched: label face (yield run), yield placement, yield format, abbreviations (not exercised), new bond colour, substrate colours.

**Tool gaps the replicator missed**

- The card's `measured` block (atom_label_size_pt_estimate 7.9, label_font Arial, bond/cap, line and arrow ratios) is read by no draw code. The label stays at the preset's 7 pt and Helvetica, so this is a tool gap as well as a card issue.
- A species label is one string and takes one face, so a bold number and a plain yield cannot be written in the brief. Only the after_product_label path writes a separate run.
- Product fragments cannot be coloured by origin. `substrate_colors` paints only substrates that are not products, and `new_bond_color` paints only formed bonds. The alkyne-derived phenyl of 3a stays black even with the card set.
- No arrow-length or bond-length key exists in the brief (BRIEF_KEYS and the step keys list none).
- No atom-level text labels (such as Ar or R on a structure). A species takes id, smiles, name, label and the ring_fills, atom_halos or ts_bracket decorations only.
