# oprd_process-02: graphical abstract route row (lenacapavir sodium)

Source: Guthrie, Gupton et al., *Org. Process Res. Dev.* 2026, DOI [10.1021/acs.oprd.5c00443](https://doi.org/10.1021/acs.oprd.5c00443) (A concise process to lenacapavir sodium: one-pot sequential Heck/Suzuki-Miyaura couplings). Licence CC BY 4.0, as recorded on the `oprd_process` card. Reference crop: `reference.png` (copy of `evidence/oprd_process-02.png`).

Figure type: `process_route`.

## What is reproduced

The route row of the graphical abstract: the aminopyridine `SM` (1 step) to the Boc, K-sulfonamide intermediate `INT`, then (2 steps) to `lenacapavir sodium`. The product carries the tricyclic cyclopropa-cyclopentapyrazole fragment as drawn. The boxed bullet list (3-Step synthesis, 55% overall yield, and so on) and the blue/green/red building-block colouring are not reproduced. Brief: `brief.json` (row budget 860 pt; try 1 at 504 pt wrapped the route onto two rows and is kept only as `figure_try1` in the scratch folder).

Structures were read from the crop by eye and checked with RDKit (`CIP` = S at the stereocentre for all three; formulas as written). OCSR was not run: the default engine uploads to a remote service and the three structures were readable at this resolution.

## Convention table

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| step_label_style numbered (card: "Step n") | "1 step", "2 steps" at arrows; no "Step n" | "1 step", "2 steps" at arrows | no (card wording) |
| step_count_shown | step count shown at each arrow | shown at each arrow (text only; the tool applies no convention here) | yes |
| yield_format "Yield {value}% Purity {purity}%" | none on this crop | none | n/a |
| scale_shown | none on this crop | none | n/a |
| highlight_fill null | none | none | n/a |
| step count at arrows (signature) | "1 step", "2 steps" in bold; the box states "3-Step synthesis" | same text, plain weight; no box | no (text only; bold and the summary count missing) |
| scale on drawing (signature) | none | none | n/a |
| telescoped intermediates in brackets (signature) | none; INT drawn plain | none | n/a |
| route-end Yield and Purity text (signature) | "55% overall yield" in the box only | none | n/a |
| panels a) and b) separated by dashed rule (signature) | single route, no panels | single route | n/a |
| compound_label_face bold | lenacapavir sodium bold | bold | yes |
| compound_label_color #000000 | black | black | yes |
| abbreviate_groups Boc | Boc on the intermediate; SO2Me, Me and CF3 also written as text | Boc only; SO2Me, Me and CF3 drawn as atoms and bonds | partial (Boc only) |
| aromatic_rings kekule | kekule | kekule | yes |
| arrow_style plain | plain | plain | yes |
| reagent_text_color #000000 | step labels black; no other reagent text | step labels black | yes (step labels only) |
| font Arial or Helvetica | Arial-like sans | Arial-like sans | yes |
| show_plus_sign | no plus sign (single substrate per arrow) | none | n/a |
| substrate_colors (card null) | blue (aminopyridine and its bonds), green (indazole), red (tricycle, in the product) | black | no |
| new_bond_color (card null) | tricycle drawn red | black | no |
| formal charge style (not on card) | circled plus on K and Na, circled minus on N | plain + and - | no |
| long arrows, about eight bond lengths (card signature) | both arrows long, several lines of text | arrow length not measured; no brief key sets it | not verified |
| yield placement under arrow | none | none | n/a |
| conditions split | none | none | n/a |
| bond length, line width (measured on crop 03/05 only) | not measured on this crop | not compared | n/a |

Matched: 7 of the 14 rows that make a convention claim (7 yes, 6 no or partial, 1 not verified); the other 11 rows are n/a.

## Differences from the paper

- The step labels are plain text; the paper sets "2 steps" (and "1 step") in bold. The tool has no bold control for step labels.
- The paper puts the route inside a boxed bullet list; draw_figure cannot draw a box or bullets. The box also carries the "3-Step synthesis" count, which the replica omits.
- The paper colours the starting material blue (bonds and text), the indazole green and the tricycle red in the product. Card `substrate_colors` and `new_bond_color` are null, so every bond stays black.
- Stereo wedges: the SM NH2 is a solid bold wedge in the paper and hashed in the render. The product stereocentre has a solid wedge to NH in the paper and a hashed bond to CH2 in the render. The intermediate's hashed bond to CH2 matches.
- The cyclopropane in the tricyclic fragment is drawn with a bold wedge in the paper; the SMILES leaves its configuration undefined and the render shows no stereo there.
- Charges: the paper circles the charges on K, N and Na; the render writes plain + and -. The card sets no formal charge style.
- Counterions K and Na are separate labels in both. The paper's product label is bold and so is the render's.
- Abbreviations: the paper writes SO2Me (several times), Me (the two methyls on the quaternary carbon) and CF3 (indazole and tricycle) as text; the render draws them as atoms and bonds.
- Balance: step 1 and step 2 both report as unbalanced (Boc, the salt counterions and the tricycle acid partner are not in the drawing). Nothing was added; the paper shows no reagents, so no by-products are drawn.

## Tool gaps

- No way to colour a building block through the route. Card `substrate_colors` paints a starting material's whole drawing by position, but skips any substrate that a step makes (`figure_house.py`, `made`), so the intermediate and product never take a building-block colour. `new_bond_color` colours only bonds formed in a step. Its atom mapping is computed inside the tool (`map_reaction_atoms`, MCS), so the brief does not need to supply one; the earlier stated cause was wrong. Species `ring_fills` and `atom_halos` exist, but they draw fills, not coloured bonds or atoms.
- No bold control for arbitrary text under or above arrows (step labels). `build_formatted_s_xml` writes italic, subscript and formula runs only.
- No boxed text panel or bullet list attached to a route. The brief keys are kind, species, steps, max_width, title, style and layout.
- Default `max_width` 504 pt wraps a three-structure route to two rows; the crop is one row. Not verified by this audit (no RDKit runtime in the audit session, so draw_figure was not run).
- Not listed before:
  - Abbreviations: SO2Me is not in the ABBREVIATIONS table (`house_styles.py`). Me and CF3 are in it, but `abbreviate_groups` comes only from the card (Boc, OTBS), and the brief cannot change it.
  - Charge style: `formal_charge_style` "circled" is accepted by the card schema for mechanism and coordination figures (`house_styles.py`), but `APPLIED_FIGURE_CONVENTIONS` applies only arrow colour and weight, so no path draws circled charges, including schemes. CirclePlus and CircleMinus exist only as native symbol objects in `figure_tools.py`.
  - Arrow length: no brief key. Length follows the longest condition line (`figure_draw.py`, relayout). The card signature "long arrows, about eight bond lengths" cannot be set directly.
  - Wedge type: species accept id, smiles or name, label, ring_fills, atom_halos and ts_bracket. No key chooses a solid or hashed wedge.

## Replay

`replay.py` runs offline and writes `figure.cdxml` and `validation.json` (checks_passed true, readback matched). The replay reports 3 structures in readback; the draw report from the render run reported 4. Not resolved. `validation.json` is not in this folder, and the audit did not re-run `replay.py`.

## Audit (2026-11-07)

- Overclaims corrected: "step count at arrows (signature)" was marked yes, but the paper's step labels are bold and the box carries the count, so it is no. "abbreviate_groups Boc" gave the paper as Boc only; the paper also abbreviates SO2Me, Me and CF3, so it is partial. "reagent_text_color" was n/a, but the step labels are black in both, so it is yes. The reason given for the colour gap (atom mapping not in the brief) was wrong. The Differences list did not record the circled charges, the stereo wedge differences or the abbreviations.
- Count: the original claim of 8 of 20 did not reconcile with the table, which has 23 rows. Corrected: 7 of the 14 rows that make a claim (7 of 25 rows including the two rows added here).
- Not verified by this audit: the 504 pt wrap, the 3-versus-4 structure count, the `validation.json` result, the RDKit CIP check, and the proportions and line weight (not measured; the table did not claim them).
