# Sarpong group, Nat. Commun. 2024, Figure 1C (biosynthesis vs chemical synthesis): mechanism replica, stand-in chemistry

Source: Sarpong et al., *Nat. Commun.* **2024** (Late-stage benzenoid-to-troponoid skeletal modification of the cephalotanes: total synthesis of harringtonolide). DOI: [10.1038/s41467-024-48586-6](https://doi.org/10.1038/s41467-024-48586-6). Licence: CC BY 4.0. Reference crop: `evidence/sarpong_group-02.png` (Figure 1C), copied here as `reference.png`.

Drawing style: the `sarpong_group` house style (card `figure_types.mechanism`, base preset `nature`), applied through `cdx.py draw` / `draw_figure` with `kind: "mechanism"`.

## What is reproduced

The reproduced part is one row of structures with curved electron-pushing arrows, drawn in the house curved-arrow colour and weight. The crop's two-row layout (the biosynthesis row over the chemical synthesis row, with a return arrow and right-to-left steps) is not reproduced.

The chemistry is not the paper's. The cephalotane cage and the Approach A and B intermediates (`8` to `12`) are not drawn. The cage is bridged and stereo-dense, the crop is too small to read it reliably, and no OCSR was run on it, so no SMILES was written for it. The replica uses a stand-in addition-elimination mechanism instead:

| species | SMILES in brief.json | role |
| --- | --- | --- |
| 1 | `O=C(Cl)c1ccccc1` | benzoyl chloride (electrophile) |
| hydroxide | `[OH-]` | nucleophile |
| 2 | `[O-]C(O)(Cl)c1ccccc1` | tetrahedral intermediate |
| 3 | `OC(=O)c1ccccc1` | benzoic acid |
| Cl- | `[Cl-]` | leaving group |

Step 1 is hydroxide addition to the C=O (lone pair to carbon, C=O pi bond to oxygen). Step 2 is collapse of the tetrahedral intermediate (O- to C=O, C-Cl bond to chloride). Atom and charge balance pass for both steps (`balanced: true`, `missing: null`). The moves are textbook electron pushing and were not taken from the paper.

The layout variant that was rendered (`brief.json`) lists the hydroxide first in step 1, so its arrow runs from the left. The first layout (hydroxide on the right) rendered with a long arc crossing the substrate label; it is not kept.

Rendering: desktop ChemDraw, `cdx.py render` on the `figure.cdxml` from the draw run. `rendered.png` is that render, downscaled to 1200 px wide. The validation in the draw report: `ok: true`, `readback: matched`, `checks_passed: false` (see Differences).

## Replay

```
python skill/chemdraw/scripts/cdx.py py skill/chemdraw/assets/house-styles/sarpong_group/replica/sarpong_group-02/replay.py NEW_DIR
python skill/chemdraw/scripts/cdx.py render NEW_DIR/figure.cdxml
```

`replay.py` runs `draw_figure` on `brief.json` offline and writes `figure.cdxml` and `validation.json`. Compare the render with `reference.png`; `rendered.png` is the render made for this case.

## Convention match

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| mechanism.curved_arrow_color `#800000` | dark red curved arrows | `#800000` on all four arrows (applied) | yes |
| mechanism.curved_arrow_weight `thin` | arrows thinner than the bonds | thin (applied) | yes |
| mechanism.show_lone_pairs `false` | no lone pairs drawn | none drawn | yes |
| mechanism.formal_charge_style `plain` | no charged atom is drawn in crop 02 | plain O- and Cl- | not checkable (nothing to compare in crop 02) |
| mechanism.intermediate_label_style `bold_number` | intermediates numbered in bold | plain numbers `1`, `2`, `3` (the house label rule is skipped for mechanisms) | no |
| mechanism.ts_marker `null` | no TS drawn | no TS drawn | not checkable (no TS in the replica) |
| mechanism.highlight_fill `null` | no filled highlight | none | yes |
| signature: dark red curved arrows thinner than bonds, drawn over the structures | arrows over the cage | thin arrows, but on structure 2 the arrows cross the Cl, O- and OH labels (see Audit) | no |
| signature: intermediates in tall square brackets, dashed reaction arrows between them | brackets around `9` and the Approach A and B intermediates; solid and grey block arrows between steps | no brackets; solid arrows | no |
| signature: teal dot `#0C5C60` on the reacting carbon | teal dot on the carbon of the `8` and `R1-H` steps | no dot | no |
| signature: dashed grey frame around the pathway with an underlined bullet title | no dashed frame in the crop; underlined plum and navy headings are present | none | no |
| top-level compound_label_face `bold` | labels read as bold | plain labels | no |
| top-level compound_label_color `#000000` | black labels | black | yes |
| top-level aromatic_rings `kekule` | Kekule ring bonds | Kekule (alternating double bonds) | yes |
| top-level arrow_style `plain` | thick grey block arrows between the route steps | thin plain arrows | no |
| top-level reagent_text_color `#000000` | -CO2 in plum, [O] and HO in red (not black) | no reagent text drawn; the tool does not apply this to mechanisms | no |
| top-level yield_placement / yield_format | no yields in the crop | no yields | not checkable |
| top-level conditions_split | -CO2 and [O] above the arrows, none below | no conditions drawn (mechanism steps accept above and below text, not used) | not checked |
| top-level abbreviate_groups `OMe`, `Boc`, `tBu` | `Me` labels only | no such groups | not checkable |

Matched 6 of 14 convention and signature items (the rows marked yes or no), not the 8 first claimed: the signature arrows row and the reagent text colour row were yes and are now no. The rows marked not checkable or not checked are left out of the count.

## Differences from the paper

- The structures are a stand-in (benzoyl chloride, hydroxide, Cl-, benzoic acid), not the cephalotane intermediates `8` to `12`. The crop's step 1 to step 2 pattern is kept only as a layout of addition and collapse.
- Intermediates are not in square brackets, and the arrows between them are solid, not dashed.
- No teal dot marks the reacting carbon.
- No dashed grey pathway frame and no underlined heading. The paper's headings "biosynthesis; net C=O deletion" (plum) and "chemical synthesis; single-atom insertion" (navy) are not drawn.
- The paper's thick grey block arrows (between the route steps, and "or") are drawn as thin black arrows.
- Compound labels are plain numbers; the paper's are bold.
- The `[O]`, `-CO2` and `LG` labels, the blue `R1` and `R2` groups and the bold front bonds of the cage are not drawn.
- `checks_passed` is `false` in all four layouts tried, for the same reason: the arrow that leaves the tetrahedral intermediate (step 2) passes through the intermediate's own O- and OH atoms. The warning says to move the species apart or reorder them. The layout re-try only widened the gaps, and the arrows still cross the substituents. In the rendered picture the arrows overlap the Cl and O- labels of structure `2`.

## Tool gaps

- Mechanism briefs have no square brackets around intermediates. Species `ts_bracket` is documented for schemes only, and was not tested with `kind: "mechanism"`.
- Mechanism arrows are `solid`, `reversible` or `resonance` only. Dashed reaction arrows (allowed for schemes) and thick grey block arrows are not available for mechanisms.
- No per-atom accent such as a teal dot. `atom_halos` exists for species in `draw_figure`, but was not tested for `kind: "mechanism"`.
- House label conventions (bold compound labels, bold intermediate numbers) are skipped for mechanisms ("apply to schemes only"), so `intermediate_label_style: bold_number` cannot be reproduced by the tool.
- No heading or title with underline and per-heading colour for a mechanism block.
- No dashed or grey frame around a pathway, and no bold (heavy) bonds for the near face of a cage.
- Layout: when the substrate of a step is a tetrahedral carbon with substituents, the arrow to a leaving group or to the O- passes through that substrate's own atoms, and the single relayout (wider gaps, higher loops) does not clear it. The report then has `checks_passed: false`.
- Run behaviour: `cdx.py draw` on this brief (no `--render`) returned no output for more than 20 minutes and was stopped. The same brief through `cdx.py py replay.py` completed in seconds, and `cdx.py render` on the resulting file worked. The draw entry point was not diagnosed further.

## Audit

Checked by eye on `reference.png` and `rendered.png`, by pixel sampling, and against the toolkit code (`toolkit/cdxml_toolkit/mcp_runtime/figure_mechanism.py`, `figure_house.py`). Corrected count: 6 of 14 (first claimed 8).

Overclaims corrected in the table and text:
- Signature arrows marked yes: in the render the arrowheads and shafts cross the Cl, O- and OH labels of structure 2, the defect the draw report already flags (`checks_passed: false`). Only the weight part holds.
- Reagent text colour marked yes: the replica draws no reagent text, so nothing was compared. The crop's reagent text is coloured (-CO2 plum, [O] and HO red), not black. `figure_house.py` does not apply `reagent_text_color` to mechanisms.
- Conditions marked not checkable: the crop has -CO2 and [O] above the arrows, and mechanism steps accept above and below text, so this was checkable and was not checked.
- Formal charges marked "too small to read": crop 02 has no charged atom.
- Dashed frame row: crop 02 has no dashed frame. The row stays no only because the underlined headings are missing.
- Layout: the "What is reproduced" section claimed the crop's layout. The crop has two rows, a return arrow and right-to-left steps; the replica is one row of left-to-right steps.

Kept as matched after checking: curved arrow colour (sampled red about 120 to 125 with green and blue at 0 in both images, consistent with #800000 after resampling; no exact hex check possible); curved arrow weight (visibly thinner than the bonds in the render); black labels; no fill; Kekule rings. Lone pairs are not drawn anywhere by the mechanism path, so that match is by absence only.

Tool gaps the replicator missed or understated (checked in code):
- Mechanism arrows are solid, reversible or resonance only (`MECH_ARROWS`), and always run left to right (head = tail + arrow length). Approach B's right-to-left steps, the return arrow from the lower row to structure 8 and the grey bracket joining 11 and 12 to the lower row cannot be drawn. Rows stack with no connector.
- `ts_bracket` and `atom_halos` are scheme-only. The mechanism species keys are `id`, `smiles`, `name`, `label`. The "not tested" wording above should read "not implemented for mechanisms".
- Only `curved_arrow_color` and `curved_arrow_weight` are applied to mechanisms. `reagent_text_color`, `compound_label_face`, `arrow_style`, abbreviations and yield placement are skipped as "apply to schemes only". So coloured reagent text and bold compound labels cannot be drawn.
- No per-bond width. The heavy front bonds of the cage cannot be drawn, because the house style sets one line width. This feature was missing from the table.
- The arrow-crossing check reports the crossing, but the one re-layout only widens gaps and cannot reroute an arrow, so `checks_passed` stays false.

Other notes:
- The replicator's reported tool gaps list was empty, but this file lists eight gaps. The structured report should carry them.
- The case folder has no `figure.cdxml` or `validation.json`, so the `ok`, `readback` and `checks_passed` claims cannot be checked from the folder.
- Card errors (`sarpong_group.json`, not edited): top-level `reagent_text_color` black, `arrow_style` plain and `abbreviate_groups` (no `Me`, though the crop uses `Me`) are contradicted by crop 02. The card's proportion values (2.9, 0.056, 0.19, 3.7) come from crop 03; crop 02's measurements are null, so proportions and label face (Helvetica) are unverified here, and no claim is made about them.
