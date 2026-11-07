# jchem_educ crop 04: tert-butyl cation as a perspective model (Figure 3)

Source: Elliott et al., "Exploring the interface of hyperconjugation and polarizability", *J. Chem. Educ.* 2026, Figure 3. DOI: [10.1021/acs.jchemed.6c00708](https://doi.org/10.1021/acs.jchemed.6c00708).

Licence: CC BY 4.0 (from the house-style card). The reference crop is reproduced under that licence.

Figure type: `stereo_model` (card section `stereo_model`, crop `evidence/jchem_educ-04.png`).

Drawing style: the `jchem_educ` house style (base preset `acs1996`) applied through `draw_figure` with `kind: "scope"`. Scope panels take only the base preset, so the card's conventions are mostly not applied (see below).

## What is reproduced

Only the chemistry: the tert-butyl cation, `C[C+](C)C` (C4H9+, charge +1; checked with RDKit). It is drawn as one planar skeletal structure in a scope panel with its compound label. The perspective model, the outlined empty p-orbital lobes, the shaded C-H bond lobe, the explicit hydrogens with wedge and hash bonds, and the four plain-text explanations with leader arrows are not reproduced, because `draw_figure` has no drawer for them.

No render exists. `draw_figure` with `--render` exceeded the 300 s tool limit on both attempts, and the run without render also exceeded it after writing `page-001.cdxml` (4.6 s). At the time about eight ChemDraw.exe processes were running on the machine. The comparison below uses the draft CDXML values and the crop, not a rendered picture, so the appearance judgements are inferred from those values and are not visual checks.

## Comparison

Counting: rows marked "not claimed (null)" or "not in this crop" are excluded from `claimed`. Rows that could not be measured are counted as claimed and not matched.

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| `model_style: perspective_3d` | perspective model of the cation with the three methyl groups in depth | planar skeleton; methyls are bond ends with no 3D depiction | no |
| `ts_marker`, `highlight_fill`, `variation_color` (null) | none | none | not claimed (null) |
| orbitals drawn as outlined lobes on the skeleton | two white outlined p-orbital lobes on the cationic carbon | no orbital objects | no |
| interacting C-H bond lobe shaded grey | grey shaded lobe on the H of one methyl | not drawn | no |
| every hydrogen shown with a bold wedge or hashed bond | wedge and hash bonds to the methyl groups and to the shaded H | no hydrogens drawn; bonds are plain | no |
| bonds of interest labelled a and b in orange-red | not in crop 04 (crop 05 only) | none | not in this crop |
| explanations as plain text joined by thin leader lines | four explanations, each with a curved leader arrow | no free text or arrows in a scope panel | no |
| label font Arial or Helvetica | Arial-like sans serif | Arial (family). The 8 pt size and `LabelFont` 1001 come from a draft CDXML that is not in this folder; the family follows from the code defaults (`publication/layout.py` font `Arial`, scope text size 8 pt) | yes (family only, output not checked) |
| `compound_label_color` #000000 (black text) | no compound label on this crop; the black text is atom labels (H3C, C, H) | `tBu+` is an added label, black by default: `apply_house_conventions` skips #000000, so no colour is set (colortable entry not checked) | no (not a valid comparison) |
| circled formal charge (card `mechanism`, noted as also in crop 04) | circled plus sign on the cation | superscript plus on C (`Charge="1"`), no circle | no |
| `arrow_style: plain` (thin arrows, small filled head) | thin curved leader arrows with small filled heads | no arrows | no |
| `bond_length_over_cap_height` 2.2 | not measured for crop 04 (card null); pixel estimate from `reference.png` about 1.4 (bond about 27 px, cap height about 19 px) | bond 14.4 pt over Arial 8 pt cap height of about 5.7 pt, about 2.5 (14% above the card's 2.2) | no |
| `line_width_over_bond_length` 0.05 | not measured for crop 04 (card null) | 0.6 / 14.4 = 0.04 (17% below 0.05; 0.6 pt is the preset value, not a measurement) | no |
| `bold_width_over_bond_length` 0.24 | not measured; no bold bond in the replica | `BoldWidth` 2 pt, 0.14 of the bond length (base preset value; card value not applied) | no |
| `compound_label_face: bold` | no compound number on this crop | label `tBu+` drawn plain (face 0); scope panels do not apply the bold face | no |
| `aromatic_rings: kekule` | no ring | no ring | not applicable |
| chemistry: tert-butyl cation | C(CH3)3+ | `C[C+](C)C`, same connectivity and charge; skeleton only, no H labels | yes (not a card convention) |

## Differences from the paper

- Depiction: the paper shows a perspective model; the replica is a planar skeleton in the ACS 1996 geometry, so the 3D view of the lobes is lost.
- Hydrogens: the paper labels the methyl groups as H3C and draws the H atoms with wedge and hash bonds. The replica shows no hydrogens.
- Orbitals: the paper has an empty p orbital and a shaded C-H bond lobe; the replica has none of them, so the central teaching point of the figure is absent.
- Explanations: the four text callouts and their leader arrows are absent.
- Charge: the paper uses a circled plus; the replica shows a plain superscript plus.
- Title and label: the scope panel adds a title, "Substrate scope", when the brief gives an empty title, and adds the id "tBu+" as a compound label. The paper has neither.
- Label face: the card's bold compound label is not applied; the label is plain.
- Bond weights: the replica uses the base preset's bold width (2 pt), not the card's 0.24 measure.

## Tool gaps

- No perspective 3D drawer in `draw_figure`: a model with explicit H labels on each carbon, wedge and hash bonds in perspective, and no 3D projection. Scope and scheme kinds are planar ACS skeletal drawings.
- No orbital lobes in `draw_figure`: the `orbital` object is not in a `draw_figure` brief. It does exist in `compose_chemical_figure` (`toolkit/cdxml_toolkit/mcp_runtime/figure_tools.py`, object kind `orbital`, default `orbital_type` `pShaded`; other types not checked), which the replicator did not try.
- No free-text callouts with leader arrows in `draw_figure`: the scope kind takes only title, conditions and footnotes. `compose_chemical_figure` has `text` (with `runs`) and `arrow` or `curve` objects, so callouts are possible there.
- No circled-charge style for a scope panel: charges are drawn as superscripts; the circled style is listed only as skipped guidance for mechanism briefs. `compose_chemical_figure` has a `symbol` object with `CirclePlus` (`figure_tools.py`), placed by its `start` and `end` coordinates.
- No option to suppress the compound label: a species without a `label` takes its `id` ("tBu+"); a brief `label` of "" was not tested to completion because the render attempt timed out.
- No option to suppress the panel title: an empty `title` is replaced by "Substrate scope" (verified in the draft CDXML).
- Scope panels take only the base preset, so `compound_label_face: bold`, the measured bold width and the circled charge of the card are not applied.
- `abbreviate_groups` (including tBu) is a scheme option; it was not tested for a bare cation in a scope panel.
- Native render: `draw_figure --render` timed out (300 s) twice; the run without render also timed out after writing its file. The native PNG was not produced (`native: not_run`).
- No perspective depiction in any tool: `compose_chemical_figure` takes explicit 2D coordinates per atom, so the 3D view of the model has to be computed by hand. Wedge and hash bonds are available there through `bond_displays` (`WedgeBegin`, `WedgedHashBegin`, `Bold`, `Dash`; `publication-figures.md`).
- No per-bond display and no per-atom label override in a `draw_figure` brief (no wedge, hash, bold or dash option). `compose_chemical_figure` covers the bond display.
- House-card measurements are not applied by any path: `publication/house_styles.py` loads the `measured` block (`bond_length_over_cap_height`, `line_width_over_bond_length`, `bold_width_over_bond_length`, `arrow_length_over_bond_length`, `label_font`), and no drawing code reads it, for schemes, mechanisms or scopes. `compose_chemical_figure` accepts `bond_length`, `line_width`, `bold_width` and `font` in its manifest `style`, so the card values can be set by hand there.
- Stereo-model conventions are not applied by any path: `apply_figure_type_conventions` (`figure_house.py`) is called only for `mechanism` and `catalytic_cycle`, so the card's `stereo_model` entries (`model_style`, `ts_marker`, `highlight_fill`, `variation_color`) are never applied or reported.
- No image comparison was run: `compare_figure_images` in `figure_tools.py` compares a reference with a candidate image and could check a render once one exists.

`replay.py` was copied from the JACS Au case with only the docstring changed. It was not run, because the same timeouts would apply. Its output path is untested for a scope brief, where the tool expects a new folder.


## Audit

Audited against `reference.png` (no `rendered.png` exists in this folder), `CASE.md`, `brief.json`, the `jchem_educ` card and the toolkit source. No other file was changed.

Overclaims corrected in the table and tool gaps above:

- Label font: the 8 pt size and `LabelFont` 1001 cite a draft CDXML that is not in the folder, so they are unverified. The Arial family matches through the code defaults, so the family-only match stands.
- Compound label colour: not a valid comparison. The convention is for compound numbers and the crop has none. The only black text in the replica is the added `tBu+` label, and `apply_house_conventions` skips #000000, so no colour is applied.
- Bond length over cap height: the replicator's own figure, about 2.5, is 14% above the card's 2.2. A pixel estimate on `reference.png` gives about 1.4 for crop 04 itself (bond about 27 px, cap height about 19 px, roughly +-10%), so the crop does not show 2.2 either. This is a no, not "not assessed".
- Line width over bond length: 0.04 against 0.05, a no. The 0.6 pt value is the preset, not a measurement.
- Orbital, callout and circled-charge gaps were stated as existing "only in the build spec". That is true for `draw_figure` only. `compose_chemical_figure` has `orbital`, `text`, `arrow`, `curve` and `symbol` (`CirclePlus`) objects, and `bond_displays`.
- Chemistry: the connectivity and charge are right, but no H labels are drawn, so the match is for the skeleton only.
- The replicator's count of 2 of 12 does not match the table, which has 13 applicable convention rows (`aromatic_rings` excluded).

Corrected count: 1 of 13 applicable convention rows matched (label font family, on the spec). Chemistry is not a card convention and is not counted.

Not verifiable from this folder: the draft `page-001.cdxml` values (`LabelFont` 1001, colour table, `Charge`, `BoldWidth`, the "Substrate scope" title and the `tBu+` label), the `draw_figure --render` timeouts, and the appearance judgements (no render). The code confirms the acs1996 `BoldWidth` of 2 pt, the default title "Substrate scope" (`figure_scope.py`), the id fallback for a blank label (`publication/data.py`), and that scope panels apply only the base preset.

`replay.py` passes `out/'figure.cdxml'` as the output of a scope brief. `draw_scope` treats `output_path` as a new folder (`figure_scope.py`), so the replay would create a folder with that name. The replay was not run.
