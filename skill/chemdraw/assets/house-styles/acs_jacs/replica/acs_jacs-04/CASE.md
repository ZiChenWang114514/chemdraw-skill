# JACS Au 2024: Pd-catalysed amination, top reaction of the figure (acs_jacs-04)

Source: K. S. Iyer, R. D. Kavthe, R. M. Lammert, J. R. Yirak, B. H. Lipshutz, "Ligated Pd-Catalyzed Aminations of Aryl/Heteroaryl Halides with Aliphatic Amines under Sustainable Aqueous Micellar Conditions", *JACS Au* **2024**, *4*, 680-689. DOI: [10.1021/jacsau.3c00742](https://doi.org/10.1021/jacsau.3c00742).

Licence: CC BY 4.0 (from the house-style card). Reference crop `reference.png` is `evidence/acs_jacs-04.png` copied unchanged.

Drawing style: the `acs_jacs` house style (base preset ACS Document 1996). The card has no `figure_types` section, so only its top-level conventions were applied.

Figure type: `reaction_scheme`.

## What is reproduced

The top reaction of the crop: an aryl halide plus a secondary amine, with the Pd/BippyPhos catalyst and ligand above the arrow and base, aqueous micellar medium, solvent and temperature below, giving the N-aryl product. The crop is generic (R, R', R''). The replica draws one concrete example from the crop's bottom panel, compound 12 (X = Br, 91%), because `draw_figure` cannot take R-group placeholders.

| Species | SMILES | Source |
| --- | --- | --- |
| ArBr | `COc1cccc(Br)c1` | read from the bottom panel of the crop (compound 12 aryl bromide) |
| amine | `Fc1ccc(cc1)C(c1ccc(F)cc1)N1CCNCC1` | read from compound 12 |
| 12 | `COc1cccc(c1)N1CCN(CC1)C(c1ccc(F)cc1)c1ccc(F)cc1` | read from the bottom panel of the crop |

All three SMILES were checked with RDKit (valid, formulas C7H7BrO, C17H18F2N2, C24H24F2N2O). OCSR was not run; the structures are simple enough to read directly from the crop.

## Replay

```
python skill/chemdraw/scripts/cdx.py py skill/chemdraw/assets/house-styles/acs_jacs/replica/acs_jacs-04/replay.py NEW_DIR
python skill/chemdraw/scripts/cdx.py render NEW_DIR/figure.cdxml
```

`brief.json` is the final brief (v2). `rendered.png` is the desktop ChemDraw render of that brief, downscaled to 1200 px wide.

## Convention table

Card conventions for the top-level scheme (`acs_jacs.json`), with the visible features of the crop and the replica.

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| compound_label_face: bold | bold "12" | bold "12" | yes |
| compound_label_color: #000000 | black | black | yes |
| compound_label_italic_suffix: false | no suffix | no suffix | yes |
| yield_format: "{value}%" | "91%" | "91%" | yes |
| yield placement (card: null) | "91%" on a second line under the label "12", with "X = Br, 45 min" | "91%" under the arrow | no (card does not set it) |
| conditions_split: reagents above, solvent below | catalyst and ligand above; KOtBu (a base reagent), aqueous medium, THF, 60 °C and time below | same as the crop: KOtBu below | no (the card rule puts reagents above; the tool does not enforce it, figure_house.py:396-397 keeps the brief lines as given; the replica matches the crop, not the card) |
| substrate_layout: inline_plus | inline A + B | inline A + B | yes |
| abbreviate_groups: OMe | OMe label | OMe label | yes |
| aromatic_rings: kekule | Kekule rings in the crop | Kekule rings | yes |
| reagent_text_color: #000000 | one word, "ocean", in blue | all black | no (card claims black; crop has one blue word) |
| KOtBu italic t (not in card) | italic t | upright t | no |
| arrow_style: plain | plain arrow | plain arrow | yes |
| show_plus_sign: true | inline plus | inline plus | yes |
| new_bond_color (card: null) | new C-N bond purple | black | no (card does not set it) |
| bond length and line width relative to cap height | 27 px bond, 12 px cap height, 1.5 px line (card measurement) | acs1996 preset geometry | no (the drawing code never reads the card measured values; see Audit) |

Claimed by the card (non-null): 11. Matched: 9 (conditions_split does not match the card rule; reagent_text_color does not match the crop).

## Differences from the paper

- The crop is a generic scheme (R, R', R'') above a boxed panel of two products (12 and 24). The replica draws only the concrete example 12; the boxed panel, the second product 24 and its "from fenofibrate" note are not drawn.
- The crop's conditions contain the placeholder "time". The replica uses "45 min", the value the crop gives for compound 12.
- Yield: the crop puts "91%" on a second line under the label, after "X = Br, 45 min". The replica puts "91%" under the arrow, which is what the default placement gives.
- The new C-N bond is black in the replica and purple in the crop; the single word "ocean" is black, not blue.
- The substrates are unlabelled, as in the crop; the replica shows no bold substrate labels.
- The step does not balance as drawn: HBr is reported as a missing by-product because the base (KOtBu) is in the conditions, not the reaction. The tool names it and does not draw it.
- The layout width is 517 pt for the v1 brief against a 504 pt budget (one relayout only widened the gaps); v2 (no substrate labels) was rendered but its draw report was not returned (see tool gaps).

## Tool gaps

- No way to draw generic R, R', R'' placeholders in a `draw_figure` brief, so a general scheme cannot be reproduced; only concrete examples can.
- No product note line under a compound label (the "X = Br, 91%, 45 min" line): the note text has no field. The yield placement value `under_product_label` exists in the house-style schema (`publication/house_styles.py`), but the card sets it to null and the brief has no per-figure override, so it was not tried.
- No per-word colour inside a condition line ("ocean" in blue).
- No way to declare a base or salt by-product (KOtBu, KBr); a step with a base in the conditions reports a missing HBr and `checks_passed` is false.
- No boxed panel or framed region below a scheme, and no two-panel composition of a scheme over a product panel.
- Bond length, line width and arrow length cannot be set from the brief, and the card measured values are stored but never applied by the drawing code, so the geometry rows cannot match by design.
- No per-figure override of a card convention: the purple new C-N bond can only come from the card (`new_bond_color`), which applies to every figure in that style, and the card leaves it null.
- No per-bond colour in the brief (decorations cover `ring_fills` and `atom_halos` only).
- No run-level italic in condition text (the italic t of KOtBu); condition lines are plain strings.
- The conditions split rule is not enforced: above and below lines are kept as given, so the tool cannot check a reagent against the card.
- `cdx.py draw ... --render` exceeded the 300 s draw_figure timeout on v2: the CDXML was written but the PNG was not. `cdx.py render` on the same CDXML then succeeded. The draw_figure timeout does not leave a report behind.

## Audit

Checked on 2026-11-07 against reference.png, rendered.png, the card (`toolkit/cdxml_toolkit/publication/house_styles/acs_jacs.json`), `toolkit/cdxml_toolkit/mcp_runtime/figure_house.py` and `toolkit/cdxml_toolkit/publication/house_styles.py`. The table and tool gaps above were corrected where the images or the code disagreed with them.

Overclaims:
- The count of 10 of 11 was too high; the matched count is 9 of 11. The conditions split is not enforced by the tool (figure_house.py:396-397 keeps the brief lines as given), and the replica places the base KOtBu below, as the crop does, which the card rule (reagents above) does not.
- The bond length and line width row ("same ACS-derived geometry") is not supported. The drawing code does not read the card `measured` values, so the replica uses the acs1996 preset. A rough pixel check on the downscaled images (low precision) gives: the crop arrow is about 277 px with a cap height of about 13 px (about 21 cap heights); the replica arrow is about 344 px with a cap height of about 16 px (about 21 cap heights), so arrow length relative to text roughly agrees. The arrow line is about 2.2 px wide in the crop (about 0.17 of cap height) and about 1.3 px in the replica (about 0.08), so the replica line looks thinner relative to the text. This is not conclusive, but it does not support the claim.
- The abbreviations row covers OMe only; the crop italic t in KOtBu is not reproduced.
- The tool-gap bullet saying `under_product_label` "would be needed" is wrong in part: the value exists in the schema. The gap is that the card sets it to null and the brief cannot override it, and the note text has no field.
- The yield_format match covers the format "91%" only; the placement differs (see the yield row).
- Not verifiable from this folder: `figure.cdxml` and `validation.json` are not here, so the `checks_passed false` claim for the KOtBu step and the v2 layout status cannot be confirmed.

Confirmed by the images: bold black compound label "12", Kekule rings, plain arrow, inline plus, OMe label; the crop has one blue word ("ocean") and the replica has none.

Corrected matched count: 9 of 11.

Tool gaps the replicator missed: bond length, line width and arrow length are not settable from the brief, and the card measured values are not applied; no per-figure override of card conventions (purple new bond); no per-bond colour; no run-level italic in condition text; the tool does not check the conditions split rule.
