# Sarpong group, JACS 2023: flavin photocatalytic cycle (Figure 2B, proposed mechanism)

Source: Sarpong et al., *J. Am. Chem. Soc.* **2023** (Photo- and metal-mediated deconstructive approaches to cyclic aliphatic amine diversification). DOI: [10.1021/jacs.3c01318](https://doi.org/10.1021/jacs.3c01318).

Licence: CC BY 4.0, as recorded in the `sarpong_group` card. Reference crop: `evidence/sarpong_group-04.png` (copied here as `reference.png`).

Figure type: `catalytic_cycle` (card: `figure_types.catalytic_cycle`). Style: `sarpong_group` (base preset `nature`, bond length 10.8 pt in the report).

## What is reproduced

The three-step photocatalytic loop of the flavin: oxidised flavin `2.A` is excited to `2.B*`, `2.B*` is reduced by `1a` to the semiquinone anion `2.C`, and `2.C` is reoxidised by S2O8²⁻ back to `2.A`. The R group on N10 is drawn as the generic `R` (SMILES dummy atom). Compound labels are bold. The side species are written as text on the arrows (see the tool gaps below).

Structures (SMILES in `brief.json`; checked with RDKit, formula C12H9*N4O2 for the flavin core):

| ID | Structure | Check |
| --- | --- | --- |
| 2.A | `CC1=CC2=C(C=C1C)N(*)C3=NC(=O)NC(=O)C3=N2` | neutral, no radical |
| 2.B* | `CC1=CC2=C(C=C1C)N(*)C3=C(C(=O)NC(=O)[N]3)[N]2` | neutral, two radical centres (N1 and N5) |
| 2.C | `CC1=CC2=C(C=C1C)N(*)C3=C(C(=O)NC(=O)[N-]3)[N]2` | charge -1, one radical (N5) |

The radicals in 2.B* and 2.C are written as bracket `[N]` atoms in a Kekulé form. Written as aromatic SMILES, RDKit dropped them, so the Kekulé form is the one used.

Side species, not drawn as structures: `1a` (N-pivaloyl piperidine), `1a_ox` (its radical cation), S2O8²⁻, SO4²⁻, SO4•⁻. They appear as the text `+ 1a`, `− 1a_ox`, `+ S2O8²⁻` and `− SO4²⁻ + SO4•⁻` on the cycle arrows.

## Replay

```
python skill/chemdraw/scripts/cdx.py py skill/chemdraw/assets/house-styles/sarpong_group/replica/sarpong_group-04/replay.py NEW_DIR
python skill/chemdraw/scripts/cdx.py render NEW_DIR/figure.cdxml
```

`replay.py` runs `draw_figure` on `brief.json` offline and writes `figure.cdxml` and `validation.json`. The replay was run once and returned `checks_passed: true`, readback `matched`.

## Brief iterations

Three briefs were tried, all with `"style": "sarpong_group"` and `"layout": "catalytic-cycle"`:

1. Full figure: the cycle plus the off-cycle branch `1a_ox` to `1.A` to `1.B` (with H2O) and `1.B` ⇌ `3a`, and all side species as structures. The tool closed the loop through `1.A`, `1.B` and back to `2.A`. The reversible arrow ended on `2.A`, `3a` and the side species were dropped, and the readback was `mismatch`.
2. Cycle only, side species as structures (`1a`, `1a_ox`, S2O8²⁻, SO4²⁻, SO4•⁻). The rendered figure had the three-structure cycle only; readback `mismatch` on five side species (`1a`, `1aox`, `S2O8`, `SO4`, `SO4r`).
3. Cycle only, side species as text on the arrows. Readback `matched` (3 structures), checks passed. This is the rendered brief kept here as `brief.json`.

The brief was not changed after try 3.

## Convention table

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| catalytic_cycle.cycle_shape `open_arc` | three curved black arcs around a ring | three straight chord arrows (a triangle) | no |
| catalytic_cycle.cycle_arrow_color `#000000` | black cycle arrows | black cycle arrows | yes |
| catalytic_cycle.center_label `True` | bold italic purple `Proposed Mechanism` in the centre | no centre label | no |
| catalytic_cycle.step_names `False` | no step names | no step names | yes |
| catalytic_cycle.intermediate_label_style `bold_number` | bold labels `2.A`, `2.B*`, `2.C`, with `Fl_Ox` and `Fl_sq•` captions under the structures | bold `2.A`, `2.B*`, `2.C`, no `Fl` captions | yes for the bold labels; the `Fl` captions are missing |
| catalytic_cycle.catalyst_color, curved_arrow_color, highlight_fill (null) | nothing coloured or filled | nothing coloured or filled | n/a (null in card, not counted) |
| signature: black arcs form the cycle, side inputs and outputs on small curved arrows | black arcs, side arrows curved | black straight chords, side species as text | no |
| signature: bold italic purple `Proposed Mechanism` in the centre | present | absent | no |
| signature: blue lightbulb in a blue `#092DFF` ring at the excitation step | present | absent (no excitation symbol) | no |
| signature: radical dots in blue | blue dots on 2.B* and 2.C | no dots visible in the PNG (CDXML has `Radical="Doublet"` on 3 atoms) | no |
| compound_label_face `bold` | bold labels | bold labels | yes |
| compound_label_color `#000000` | black | black | yes |
| compound_label_italic_suffix `false` | no italic suffix | no italic suffix | yes |
| arrow_style `plain` | plain arrows | plain arrows | yes |
| aromatic_rings `kekule` | benzo ring drawn with alternating double bonds | benzo ring Kekulé | yes |
| reagent_text_color `#000000` | black text | black text | yes |
| conditions_split `reagents_above_solvent_below` (audit row, not counted) | reagent `1a` is a structure beside the arrow; no conditions text on the arrows | `+ 1a` below and `− 1a_ox` above on step 2; the step-3 pair is stacked in reverse and sits at the upper left, away from its arrow | no |
| abbreviate_groups `Me` on the two aromatic methyls (audit row, not counted) | `Me` text | bare line stubs; the card lists OMe, Boc and tBu only | no |
| measured bond_length_over_cap_height 2.9 (audit row, not counted) | not measured on the crop | not verified; a rough pixel estimate gives about 2.7 in the replica and about 3 in the reference | not verified, not claimed |
| not visible in this crop: dark red `#800000` curved arrows, square brackets around intermediates, bold heavy bonds | none in the crop | none in the replica | not counted |

Count: 9 of the 15 counted rows match. Those 15 are 3 catalytic-cycle type rows that match (cycle arrow colour, no step names, bold labels), 6 top-level rows that match (label face, label colour, no italic suffix, plain arrows, Kekulé rings, black reagent text), and 6 rows that do not (cycle shape, centre label, and the 4 signature features). The null row is not counted, and 0 of the 4 signature features match. The three audit rows are not counted.

## Differences from the paper

- The cycle is a triangle of straight arrows. The paper's cycle is a ring of curved arcs, with `2.A` at the top, `2.B*` on the right and `2.C` on the left. The arrangement of the three intermediates is similar; the arrows are not.
- `1a` and `1a_ox` are structures in the paper and text here. S2O8²⁻, SO4²⁻ and SO4•⁻ are text in the paper too, on curved arrows, so for those the replica only loses the curved arrows.
- The blue radical dots on `2.B*` and `2.C` are absent from the rendered PNG.
- The blue lightbulb in a blue ring at the excitation step is absent. Step 1 has no label.
- The purple `Proposed Mechanism` heading in the centre is absent.
- The off-cycle branch `1a_ox` → `1.A` → `1.B` ⇌ `3a` (H2O step) is omitted.
- The green highlight on one bond of `1.B` is not reproduced, because `1.B` is omitted.
- The labels `+ 1a` and `− 1a_ox` are conditions-style text. The paper does not have them; the reagents are drawn as structures there.
- The text labels for step 3 sit at the upper left of the cycle, away from the arrow they describe.
- Proportions were not verified. A rough pixel estimate gives a bond of about 49 px and a bold `2.A` cap height of about 18 px in the replica (ratio about 2.7). The reference gives a bond of about 40 to 46 px and a cap height of about 13 to 14 px (ratio about 3). The replica labels may be large relative to the bonds. Not claimed.

## Tool gaps

- Catalytic-cycle layout draws only `substrates[0]` of each step on the ring (`_layout_catalytic_cycle` in `toolkit/cdxml_toolkit/render/renderer.py`). The other reactants and products are dropped from the drawing, and the readback reports them as missing. `scheme-drawing.md` describes entering reactants and departing products on radial arrows; in the code they only become text labels.
- Cycle arrows are straight chords between intermediates. `scheme-drawing.md` says curved arrows along the circumference; the output has no curvature, and no `open_arc` option exists.
- No centre label for a catalytic cycle. The card's `center_label` is reported as skipped guidance.
- No excitation symbol (lightbulb in a ring) for a photochemical step; only text above or below the arrow is possible.
- Radical dots: not visible in the rendered PNG, although the CDXML carries `Radical="Doublet"` on three atoms. There is no option to colour them.
- An off-cycle branch cannot be attached to a catalytic cycle. In try 1 the tool forced `1.A` and `1.B` into the loop and dropped `3a`.
- Balance cannot be checked when a generic `R` atom (`*`) is present. The report says "generic atoms (R groups, *) cannot be balanced" for every step, so the steps are not verified. No option treats `R` as a placeholder for checking.
- Subscript in compound labels is not supported: `1a_ox` appears with a literal underscore in try 1.
- Radial condition labels are placed by the layout, not next to their arrow: in try 3 the step-3 labels sit at the upper left, away from the arrow. The above and below lines are also stacked in reverse order on both steps: the PNG shows `− 1a_ox` above and `+ 1a` below on step 2, and `− SO4²⁻ + SO4•⁻` above and `+ S2O8²⁻` below on step 3, while `brief.json` has the opposite. `validation.json` reports the lines as kept as given, and the PNG was not re-rendered in this audit.
- `cdx.py draw --render` can take more than 2.5 minutes under contention. A run with an outer 170 s timeout was killed (`worker_crashed`, exit 143) and succeeded when rerun with no outer timeout.
- The house card's measured fields (`bond_length_over_cap_height`, `arrow_length_over_bond_length`, `label_font`, `line_width_over_bond_length`, `bold_width_over_bond_length`) are stored by `house_styles.py` but not applied. `validation.json` lists them neither as applied nor as skipped, so nothing reports that they were ignored. The output uses Arial (the card says Helvetica). The step-2 arrow is about 2.5 bond lengths long (124 px for a 49 px bond in the PNG), against the card's 3.7.
- No multi-line compound label, so the `Fl_Ox` and `Fl_sq•` captions the paper sets above the bold labels cannot be drawn.
- The abbreviation list is fixed to OMe, Boc and tBu. `Me` is not contracted, so the paper's `Me` text becomes bare stubs. The card does not list `Me`, but the paper uses it.

## Audit

Audited 2026-11-07 by reading both PNGs, measuring pixels, and re-running `replay.py` into a temporary folder. The re-run gave `checks_passed: true`, readback `matched`, `Radical="Doublet"` on 3 atoms, and balance warnings for all three steps. The code references in the tool gaps check out: `toolkit/cdxml_toolkit/render/renderer.py` line 2773 uses `substrates[0]`, and `skill/chemdraw/references/scheme-drawing.md` line 40 describes radial arrows.

Overclaims corrected above:
- The count sentence did not match the table. Three of the nine matches are catalytic-cycle type rows, not the four signature features and six top-level rows it described.
- The Differences bullet said S2O8²⁻, SO4²⁻ and SO4•⁻ are text instead of the paper's structures. They are text in the paper too. Only `1a` and `1a_ox` are structures there.
- The proportion comparison was not measured. It is now marked as not claimed, with a rough estimate that suggests the replica labels may be large relative to the bonds.
- Conditions placement was not reported. The above and below labels are swapped on both steps in the PNG, and the reagent `+ 1a` sits below the arrow.
- The intermediate-label row was marked yes without the caveat that the paper's `Fl` captions are missing. Now stated.

Checks that held: bold black labels, black arrows, no step names, Kekulé benzo rings and black reagent text match the PNG. The rendered PNG has no blue or purple pixels, which is consistent with no radical dots, no lightbulb and no centre label.

Corrected matched count: 9 of 15 counted rows (the number is unchanged; the rows that match are the bold, black, plain, Kekulé and no-step-name rows, and 0 of 4 signature features match).

Tool gaps the replicator missed: the house card's measured geometry is silently dropped; the label font is Arial, not Helvetica; there is no multi-line compound label for the `Fl` captions; `Me` is not abbreviated; the above and below labels are stacked in reverse; and conditions placement breaks the reagents-above convention.
