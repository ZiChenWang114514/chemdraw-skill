# J. Chem. Educ.: hyperconjugation resonance pairs (Figure 5, middle row)

Source: Elliott et al., "Exploring the interface of hyperconjugation and polarizability", *J. Chem. Educ.* **2026**. DOI: [10.1021/acs.jchemed.6c00708](https://doi.org/10.1021/acs.jchemed.6c00708).

Licence: CC BY 4.0. The reference crop (`reference.png`, Figure 5) is reproduced under that licence.

Figure type: `mechanism` (house style `jchem_educ`, base preset `acs1996`).

Drawing style: the `jchem_educ` card applied through `style` in `brief.json`. The tool applied the curved-arrow colour (`#000000`) and weight (`bond`) from the card's `mechanism` section; the other `mechanism` conventions are listed as skipped guidance in the report.

## What is reproduced

Only the two rows of the paper's Figure 5 that use curved arrows from a heavy-atom bond or lone pair: the negative hyperconjugation pair (trifluoromethoxide, `[O-]C(F)(F)F`, and carbonyl fluoride with fluoride) and the anomeric/negative hyperconjugation pair (trifluoromethanol, `OC(F)(F)F`, and its protonated form with fluoride). Both pairs are drawn with the double-headed resonance arrow, the curved arrows and the caption text under the arrow.

| ID | Structure (SMILES in brief.json) | Check |
| --- | --- | --- |
| tfo | `[O-]C(F)(F)F` | balanced with cof2; two moves: O lone pair to C-O, C-F to F |
| cof2 | `O=C(F)F.[F-]` | balanced; F- drawn as a separate fragment |
| tfoh | `OC(F)(F)F` | balanced with hcf2; same two-move pattern |
| hcf2 | `[OH+]=C(F)F.[F-]` | balanced; OH+ as in the paper |

The tool's report: `balanced: true` for both steps and `readback: matched` with 4 structures. `checks_passed` is false because the two curved arrows in each step pass through a fluorine atom after one automatic re-layout (see Tool gaps).

## Not reproduced

The positive hyperconjugation pair (tert-butyl cation and isobutene with H+), the neutral hyperconjugation pair (acetone and enolate with H+) and the sigma-conjugation pair (ethane and ethene with H+ and H-) are not in `brief.json`. Each of their curved arrows starts on a C-H bond, and the mechanism brief cannot address one (see Tool gaps). A mechanism step also needs at least one move, so these pairs cannot be drawn as structure-only steps in the same brief. The panel is therefore two of the five pairs of Figure 5.

## Replay

```
python skill/chemdraw/scripts/cdx.py py skill/chemdraw/assets/house-styles/jchem_educ/replica/jchem_educ-03/replay.py NEW_DIR
python skill/chemdraw/scripts/cdx.py render NEW_DIR/figure.cdxml
```

`replay.py` runs `draw_figure` on `brief.json` offline and writes `figure.cdxml` and `validation.json`. This folder holds no `validation.json` or `figure.cdxml`, so the run and the report figures cannot be checked from it (see Audit).

## Convention table

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| curved arrow colour (`mechanism.curved_arrow_color`) | black | black, applied by the tool | yes |
| curved arrow weight (`mechanism.curved_arrow_weight` bond) | thin, same as bonds | bond-width, applied by the tool; not measurable at the reference resolution | no (unverified) |
| lone pairs (`show_lone_pairs` false) | not drawn | not drawn | yes |
| formal charge style (`circled`) | circled + and - | plain + and - (the tool lists circled as skipped guidance) | no |
| intermediate labels (`none`) | none | none | yes |
| TS marker (`null`) | none | none | yes |
| highlight fill (`null`) | none | none | yes |
| double-headed arrow joining a resonance pair | yes | yes (`resonance` step arrow); present, but about 10 bond lengths long against about 1.7 in the paper | yes (presence only) |
| square brackets around each pair | yes | no | no |
| curved arrows start on the bond being broken | yes | no: in rendered.png both curved arrows of each step start at the lower F label, not at O or the C-F bond, and the lone-pair head ends at the O label rather than the C-O bond; the other three pairs are absent | no |
| coloured caption under each pair, blue #4C5C98 Arial | yes | black caption set under the arrow, not under each pair | no |
| thin plain arrows with a small filled head (`conventions.arrow_style` plain) | yes | default preset arrows (the tool applies `arrow_style` only when it is `bold`); the resonance arrow is about 10 bond lengths long against about 1.7 in the paper | no |
| Arial labels (`measured.label_font`) | Arial | Arial by eye (ChemDraw default for acs1996; the card's `label_font` is not read by any code); label size not matched | yes (face only) |

Matched 7 of 13 conventions after audit (the claim was 9). Four of the seven are `none` rows that hold trivially. See Audit.

## Differences from the paper

- Three of the five pairs are missing: positive hyperconjugation, neutral hyperconjugation and sigma-conjugation (see Not reproduced).
- Layout: the paper has the pairs in a grid with the upper pairs side by side. The replica stacks the two drawn pairs one above the other on one page.
- No square brackets around each pair.
- Charges are plain + and - rather than circled.
- Captions are black and sit centred under each arrow, not blue under each pair. The two-line caption under the anomeric pair breaks where the paper breaks it.
- The CF3 carbon is drawn as a flat cross (four bonds at 90 degrees). The paper uses wedge and hashed fluorines in perspective. The tool takes no stereo or wedge input from the brief.
- The bond-length to cap-height ratio of the card (2.2) was not applied by the tool. Measured on the images, it is about 2.1 in the reference and about 1.8 in rendered.png, so the replica labels look proportionally larger (indicative only, see Audit).

## Tool gaps

- Curved-arrow endpoints must be heavy atoms or bonds between heavy atoms. Hydrogens are not numbered, and RDKit drops explicit H atoms that have neighbours, so a C-H sigma bond cannot be the start of an arrow. This blocks three of the five pairs in this figure.
- A mechanism step needs at least one move (`Step N needs moves`), so a resonance pair without arrows cannot be in a mechanism brief.
- A scheme or mechanism brief must be one connected route. Three independent resonance pairs in one brief are refused with "not a linear route, a convergent route (arms that merge) or a set of reactions from one starting material", so the structure-only pairs cannot be placed beside the arrowed ones by one call.
- No bracket option around a structure pair. `ts_bracket` wraps a species in a transition-state bracket with a double-dagger superscript, which is not the paper's resonance bracket.
- No circled formal-charge style for mechanism structures.
- No per-element or per-caption colour for mechanism step text. `reagent_text_color` applies to schemes only, and mechanism captions use the `above` / `below` lines centred under the arrow.
- No control over 2D geometry for sp3 centres: the quaternary CF3 carbon comes out as a 90 degree cross, and there is no wedge or hash input for the fluorines.
- Arc routing: both curved arrows in each of the two drawn steps are flagged as passing through a fluorine atom (`arrows.crossings`, `checks_passed` false) after one re-layout that only widened the gaps and raised the loops. The side of each arc cannot be chosen. In the native render the lone-pair arc bulges around the lower fluorine and reads as starting near that fluorine rather than at O.
- Resonance arrow length: the brief has no input for it (only `arrow` and `max_width`), so the double arrow cannot be shortened to the paper's proportion.
- Measured card values are not applied: the `measured` block (bond-length to cap-height 2.2, line width ratio 0.05, bold width 0.24, `label_font`, arrow length ratio 9.2) is stored but no Python code reads it. Only the curved-arrow colour and weight from `figure_types` are applied (`cdxml_toolkit/mcp_runtime/figure_house.py`, `apply_figure_type_conventions`). Label size, line weight and arrow length therefore cannot come from the card.
- Detached ion fragments (the F- on each product) are placed by the tool at upper right, with no position control.
- Arrow endpoints: the render starts both curved arrows of each step at the lower F, not at O or the C-F bond midpoint. Atom 0 of `[O-]C(F)(F)F` is the oxygen, so the move from atom 0 should start at O. The cause was not established in this audit; it may be an index mapping after the re-layout and should be checked against the saved `figure.cdxml`.

## Audit

Checked by eye and by pixel measurement against `reference.png` (the full Figure 5, 626 x 403 px, so the reference resolution is coarse) and `rendered.png` (1145 x 430 px). Corrected matched count: 7 of 13 (the claim was 9). Changes to the table: curved-arrow weight, arrow style and arc endpoints set to no; the double-arrow row now says presence only; the Arial row says face only.

- Caption colour: reference caption pixels are blue (sampled about #4E609E to #54639E, consistent with #4C5C98). `rendered.png` has no saturated pixels, so the caption is black. Row confirmed as no.
- Brackets and charges: the reference has square brackets and circled charges; `rendered.png` has neither. Rows confirmed as no.
- Resonance arrow proportion (not in the table): about 531 px long in `rendered.png` against a C-F bond of about 55 px, roughly 10 bond lengths. In the reference the arrow is about 48 px against a bond of about 28 px, roughly 1.7 bond lengths. The replica arrow is about five times too long relative to the bonds, and the gap between structures is much wider than in the paper.
- Label size: cap height about 30 px against a bond of about 55 px in `rendered.png` (about 0.55 cap height per bond length), against about 13 px and 28 px in the reference (about 0.46). Indicative only, given the reference resolution.
- Curved-arrow endpoints: the claim "yes for the two pairs drawn" in the table contradicted the image. See the table row.
- Line weight: bond strokes are about 2 px in the reference and about 3 px in the render. The curved-arrow weight cannot be compared at reference resolution, so the row is set to no (unverified). The code applies the `bond` weight as the preset LineWidth times 1.0.
- Label face: the glyphs look Arial by eye. The face comes from the acs1996 preset default, not from the card's `label_font`.
- `none` rows (lone pairs, intermediate labels, TS marker, highlight fill): true in both images, but they do not test any convention.
- Unverifiable from this folder: no `validation.json` or `figure.cdxml` is present, so the `balanced: true`, `readback: matched` and `checks_passed: false` statements, and whether `rendered.png` came from this `brief.json`, were not checked. Replay was not run in this audit.
