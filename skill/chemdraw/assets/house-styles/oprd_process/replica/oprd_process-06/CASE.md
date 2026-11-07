# Amodiaquine three-step telescoped process (Scheme 3, Gohain, Malan et al.)

Source: Gohain, Malan et al., "Process development for the manufacture of the antimalarial amodiaquine dihydrochloride dihydrate", *Organic Process Research & Development* **2023**. DOI: [10.1021/acs.oprd.3c00205](https://doi.org/10.1021/acs.oprd.3c00205).

Licence: CC BY 4.0 (from the house-style card). Reference crop: `evidence/oprd_process-06.png`, copied here as `reference.png`.

Drawing style: the `oprd_process` house style in `brief.json` (bold compound labels, reagents above and solvent below the arrow, base preset ACS Document 1996); figure type `process_route`.

## What is reproduced

The whole route in the crop: `13` to `14` (1) paraformaldehyde, 2) diethylamine; solvent below), `14` to the non-isolated aminophenol `15` (aq. HCl), `15` plus 4,7-dichloroquinoline to `3` (2HCl 2H2O in the paper), and `3` to `3` (EtOH:HCl). The structures are drawn close to the paper, but the salt, the layout, reagent 5 (text, not a structure), the bracket shape and the repeated intermediates differ (see below).

Structures used in `brief.json` (checked with RDKit; formulae C8H9NO2, C13H20N2O2, C11H18N2O, C9H5Cl2N, C20H22ClN3O):

| ID | Structure (SMILES in brief.json) | Check |
| --- | --- | --- |
| 13 | `CC(=O)Nc1ccc(O)cc1` | matches the drawing |
| 14 | `CC(=O)Nc1ccc(O)c(CN(CC)CC)c1` | NHAc para to OH, CH2NEt2 ortho to OH |
| 15 | `Nc1ccc(O)c(CN(CC)CC)c1` | free amine from hydrolysis of 14 |
| 3 | `CCN(CC)Cc1cc(Nc2ccnc3cc(Cl)ccc23)ccc1O` | amodiaquine free base; the 2HCl 2H2O salt is not drawn |
| 5 | `Clc1ccc2c(Cl)ccnc2c1` | 4,7-dichloroquinoline, used as text in the final brief (see attempts) |

## Attempts (three tries, as the brief allows)

1. Reagent 5 as a second substrate of step 3 (`["15", "5"]`). `draw_figure` gave a sequential layout: each step on its own row, 14 and 15 and 3 each drawn twice, a "+" between 15 and 5 (the paper has none), and a TS-style bracket around 15 that crosses the H2N and CH2N labels. Readback matched 9 structures; native render OK.
2. Same as 1 with `layout: "linear"` and a smaller bracket lip (`lip_size` 4). The report still says `sequential` (the keyword is ignored here), and the bracket looked the same.
3. Final (`brief.json`, `rendered.png`): reagent 5 written as text above the step-3 arrow, the other steps unchanged. Still one row per step, each intermediate drawn on two rows, so the U shape is lost. Readback matched 8 structures; native render OK, `checks_passed` true.

The `ts_bracket` setting with an empty `superscript` is a workaround. It draws the square bracket without the double dagger, but the feature is meant for transition states.

## Replay

```
python skill/chemdraw/scripts/cdx.py py skill/chemdraw/assets/house-styles/oprd_process/replica/oprd_process-06/replay.py NEW_DIR
python skill/chemdraw/scripts/cdx.py render NEW_DIR/figure.cdxml
```

`replay.py` redraws `brief.json` offline into `figure.cdxml` and `validation.json`. This was run once into a scratch folder and wrote both files. `rendered.png` is the desktop ChemDraw render of attempt 3, downscaled to 1100 px wide.

## Convention table

Counting used here: "claimed" counts the rows where the card or the paper gives a feature that applies to this crop (rows marked n/a are left out); "matched" counts the rows marked yes. Partial rows do not count as matched.

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| bold compound labels (13, 14, 15, 5, 3) | bold | 13, 14, 15 and 3 bold; reagent 5 is plain text in the replica, not bold and not a structure | partial |
| compound label colour black | black | black | yes |
| reagents above, solvent below the arrow (conditions_split) | "1) Paraformaldehyde / 2) Diethylamine" above, "Solvent" below | same lines | yes |
| plain arrows (arrow_style plain) | plain | plain | yes |
| Kekule aromatic rings | Kekule | Kekule | yes |
| non-isolated intermediate in square brackets | 15 in brackets with a bold label; no "not isolated" caption | narrow box with top and bottom edges, drawn with an empty-superscript `ts_bracket`; lines cross the H2N and CH2N labels; drawn twice; no caption | partial |
| long arrows (about eight bond lengths) with several lines of conditions | step 1 arrow with 3 lines of conditions; length not measured | step 1 arrow with 3 lines; length not measured; draw_figure has no arrow-length setting | not verified |
| reagent 5 drawn as a structure beside the final arrow, no plus sign | 5 as a structure at the arrow, no plus | 5 named as text above the arrow (attempt 3) | no |
| U-shaped route, second row right to left, downward connector from 15 | U shape | four stacked rows, all left to right | no |
| each intermediate drawn once, route continuous | 14 and 15 drawn once each; 3 drawn twice (the step 3 product, which is also the step 4 substrate, and the final 3) | 14 and 15 each drawn on two rows; 3 drawn on three rows | no |
| salt text 2HCl 2H2O beside product 3 | text beside 3 | free base, no salt text | no |
| step 4 product shown as the same salt-form 3 | 3 to 3 (same salt) | identical free base to free base | no |
| bond length against label size, line width | not measured for this crop (card measurements null) | ACS 1996 geometry, bond length 14.4 pt; not compared with the paper | unverified |
| step numbers (step 1, 2 ...), step count shown | none | none | n/a (the card lists numbered steps for process_route; this crop has none) |
| scale on the drawing | none | none | n/a |
| yield and purity at the route end, yield under the arrow | none | none | n/a |
| plus sign (show_plus_sign) | no plus in the crop | no plus (attempt 3) | n/a (not tested by this route) |

Matched 4 of 13 claimed (the first count was 5; the bold-label row overstated reagent 5, see Audit).

## Differences from the paper

- Layout: the paper is a U. The route runs along the top, drops from the bracket at the right edge, and returns right to left in the second row, where the arrow ends at the left-hand `3`. The replica is four stacked rows, all left to right, with the arrows not connected.
- Intermediates: the replica draws 14 and 15 twice each (as product of one row and substrate of the next) and 3 three times (product of step 3, and substrate and product of step 4). The paper draws 14 and 15 once each, and 3 twice: the step 3 product, which is also the step 4 substrate, and the final 3.
- Reagent 5: the paper draws 4,7-dichloroquinoline as a structure beside the arrow. The replica writes its name above the arrow (attempt 3). Attempt 1 drew it as a structure, but with a plus sign and a repeated 15.
- Salt: the paper writes 2HCl 2H2O beside both 3 structures. The replica draws the free base only.
- Step 4: the paper shows the same salt-form 3 on both sides of EtOH:HCl. The replica draws identical free bases; the tool reports the step as balanced because nothing changes.
- Bracket: the paper's square brackets are open-sided and clean around 15. The replica's bracket is a narrow box with top and bottom edges that crosses the H2N and CH2N labels; the empty-superscript workaround is not a real intermediate bracket.
- Balance: steps 1 to 3 are reported as unbalanced because formaldehyde, water, acetic acid and HCl are by-products that are named but not drawn. The paper does not draw them either.
- The replica numbers only the compounds, as the paper does. It has no step labels, which is what the paper shows, although the card claims numbered steps for this type.

## Tool gaps

- `draw_figure` lays out a multi-step chain as one row per step (layout `sequential`) and draws each intermediate again on each row. There is no option for a continuous row that draws each compound once. A `layout: "linear"` key in the brief is accepted but reported as `sequential`. Any other `layout` value is ignored without a warning: `_route_layout` only recognises `catalytic-cycle` and `cycle`, and `_validate` does not check the value.
- No serpentine or U-shaped wrap with a downward connector. The renderer has a serpentine wrap (`_layout_serpentine` in `cdxml_toolkit/render/renderer.py`, selected by `scheme.wrap`), but `draw_figure`'s `_scheme` never sets it and the brief schema (`BRIEF_KEYS`) has no wrap key.
- No square bracket for a non-isolated intermediate, and no "not isolated" caption. The only bracket is `ts_bracket` (transition state, with a double dagger option), and `lip_size` made no visible change. Its lines run through neighbouring labels.
- No text annotation attached to a species, so a salt or hydrate such as "2HCl 2H2O" cannot be written beside a structure. A dot-separated SMILES was not tested; it would probably draw HCl and water as separate structures.
- No way to place a reagent structure beside an arrow without a plus sign. Giving the reagent as a second substrate adds a plus and starts a new row. Giving it as text loses the structure.
- No step-number labels for process routes (step 1, step 2 ...). Only the reagent text lines can carry numbers.
- No way to show a salt form of the same compound distinct from the free base, except by a second species with the same SMILES; the salt-form arrow then reads as "no change".

- Bracket box: the `ts_bracket` box is the bounding box of the fragment's atom positions, padded by 5 pt across and 4 pt up and down (`cdxml_toolkit/mcp_runtime/figure_draw.py`, the ts_bracket block near line 503). Substituent labels such as H2N and CH2N lie outside that box, so the bracket crosses them. This is the cause of the crossings; `lip_size` only sets the width of that box, which is why 4 and 5 look the same.
- House measurements are not applied: the card's `measured` block (bond length, line width, arrow length 8 bond lengths) is copied into the house style object, but no drawing code reads it. The renderer sets arrow length from content with a minimum of 5 bond lengths (`cdxml_toolkit/render/renderer.py`, around line 1663), and no brief key sets it.
- No bold or caption field: the step keys (`substrates`, `products`, `above`, `below`, `yield`, `arrow`, `ts_bracket`) take plain text lines only, so a bold reagent number under a reagent structure, or a caption under a bracket, cannot be written.

## Audit

Checked on `reference.png` (771 x 370), `rendered.png` (1100 x 981), zoomed crops of both, and the toolkit source (`cdxml_toolkit/mcp_runtime/figure_draw.py`, `figure_house.py`, `render/renderer.py`, `render/route_graph.py`). The house card is `toolkit/cdxml_toolkit/publication/house_styles/oprd_process.json`.

Overclaims corrected:

- Bold labels: reagent 5 is plain text in the replica ("5 (4,7-dichloroquinoline)"), not a bold label under a structure. The row is partial, and the count drops from 5 to 4.
- Long arrows: no length was measured on either image, so the row is "not verified", not partial.
- Structure sentence: the salt, the layout, reagent 5, the bracket shape and the repeated intermediates all differ, not only the salt and the layout.
- Intermediates: the replica repeats 14 and 15 twice each and 3 three times. The paper draws 3 twice, so the paper column was also wrong.
- Bracket: the replica's bracket is a narrow box with top and bottom edges, not the paper's open square brackets.
- Step-number row cited `card_errors`, which is not in this folder; the reference is now given in plain words.

Confirmed on inspection: label colour black (both); reagent lines above the arrow and "Solvent" below (both); plain arrows with solid barbed heads (both); Kekule rings (inner double bonds on ring 13 in the reference and on ring 14 in the replica).

Not verifiable from the images: the label font (both look Arial-like, not measured); bond length against label size and line width (the card's measurements are null for this crop and neither image was measured); the readback and checks_passed claims in Attempts (replay not run); the balance claims in Differences.

Corrected matched count: 4 of 13 claimed.

Tool gaps the replicator missed: the bracket box is padded from atom positions (the cause of the label crossings); house `measured` values are never read, so arrow length, line width and bond length cannot be set from the card; unknown `layout` values are silently ignored; step keys have no bold or caption field.
