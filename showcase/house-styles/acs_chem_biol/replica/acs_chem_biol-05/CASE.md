# acs_chem_biol replica: crop 05 (Bridge et al., ACS Chem. Biol. 2026, Figure 1)

## Source

- Paper: Bridge et al., ACS Chem. Biol. 2026, "Enzymatic bromination of native peptides for late-stage structural diversification via Suzuki-Miyaura coupling"
- DOI: 10.1021/acschembio.6c00269
- Figure: Figure 1 (crop `evidence/acs_chem_biol-05.png`, 718 x 973 px)
- Licence: CC BY 4.0 (from the house-style card)
- Figure type: `reaction_scheme` (with `biomolecule`)

## What is reproduced

Only the bottom row of the crop, "this work", which is the 4V-catalysed halogenation of a tryptophan residue in a peptide. The reaction is drawn as one step, the Trp-containing substrate to the 7-halo-Trp product, with `4V` above the arrow.

The brief uses:

- substrate `CN[C@@H](Cc1c[nH]c2ccccc12)C(=O)NC` (L-Trp, S centre confirmed with RDKit);
- product `CN[C@@H](Cc1c[nH]c2c(Br)cccc12)C(=O)NC` (7-bromo, same centre);
- above the arrow: `4V`; no conditions below, no yield (none is shown in this row of the crop).

Not reproduced: the two literature rows above it (wild-type RebH and RebH 4V on bioactive molecules, with citations Yeh, et al. 2005 and Payne, et al. 2015), the grey row bars and the bold row title, the italic caption, and the grey-bead peptide backbone.

## Changes made to the paper's structures

- The peptide chain is replaced by N-methyl caps (`NHMe` on the N-terminus and `C(=O)NHMe` on the C-terminus). The grey bead repeats `( )n` and `( )m` are not drawn.
- The halogen is Br. The paper's key reads "= Cl or Br"; the Br choice follows the paper title.
- The grey-purple dot at C7 is drawn as a Br atom label inside a grey-purple halo (`atom_halos`, colour `#B0A0BA`, sampled from the crop). The paper shows no letters.

## Render history

- Try 1 (`figure-try1`): plain Br label, no halo. Rendered, layout checks passed.
- Try 2 (final, `brief.json` and `rendered.png`): Br in a grey-purple halo of radius 9 pt. Closer in colour, but the halo is about 18 pt across, about 2.4 label cap heights; the paper's dot is about 1.1 cap heights (see Audit).
- Try 3 was started with radius 5 pt to match the dot size. ChemDraw did not return a render within the session (shared desktop ChemDraw queue), and the run was stopped. No file from it is kept.

The draw report for the final brief has `checks_passed: true`, `readback: matched`, `native: rendered`, and one warning: step 1 does not balance because no bromide source is in the drawn reactants. The crop shows only `4V` above the arrow, so no NaBr was added.

## Convention check

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| Single step with the catalyst name above the arrow (card: enzyme or catalyst name above arrow) | `4V` above a plain arrow | `4V` above a plain arrow | yes |
| arrow_style `plain` | thin plain arrow | thin plain arrow | yes |
| aromatic_rings `kekule` | benzene and pyrrole rings with inner double-bond lines | same | yes |
| reagent_text_color `#000000` | black `4V` | black `4V` | yes |
| arrow_length_over_bond_length 4.2 (card measurement, 105 px / 25 px) | card says 4.2, but the crop arrow is about 80 px, so the card value is not reproduced (see Audit) | 5.0 (72 pt / 14.4 pt); not applied by the tool; about 2.2 times the paper's arrow in label-height units | no |
| bond_length_over_cap_height 2.0 | not measured (card null); the card's cap height (12.5 px) is not in the crop, whose 4V cap is 18 px | 14.4 pt bond, 10 pt label: about 1.9 from the rendered image (50 px / 26 px) | not measured |
| line_width_over_bond_length 0.05 | card 0.05; crop shaft is about 0.11 of the 4V cap height (see Audit) | 0.60 / 14.40 = 0.042; shaft about 0.07 of the 4V cap height | no |
| label_font Arial or Helvetica | sans-serif; 4V width/height 1.67 | Arial in the toolkit template; 4V width/height 1.65 | yes |
| variation_color `#D2107A` (card, reaction_scheme) | grey-purple dot, about `#B0A0BA`; no magenta in crop 05 | grey-purple halo `#B0A0BA` around Br | no (card value comes from crop 01) |
| installed group as a bare coloured dot defined by a key (card signature) | bare dot at C7, no letters; key "= Cl or Br" sits in row 1 | Br letters inside the halo; no key | no |
| coloured dot on the modified Trp (card, biomolecule) | yes, at C7 | yes, at C7, but as a labelled halo, not a dot | no (position only) |
| yield_format `{value}% isolated yield` | no yield in this row | none drawn | not shown |
| stacked concentrations above arrow (card, crop 01) | not in crop 05 | none | not shown |
| italic step title over grey rule (card, crop 01) | not in crop 05 (grey row bars instead) | none | not shown |
| peptide_style `one_letter` (card, biomolecule) | grey unlabelled beads, no letters | N-methyl caps; no beads | no |
| Trp cyan `#7FD0D4` (card, biomolecule) | Trp is an ordinary indole, no cyan | ordinary indole | no |
| grey title bar with bold black title (card, crop 05) | grey bar, bold "this work: RebH 4V-catalyzed peptide functionalization" | not drawn | no |
| italic caption under the scheme | "sequence-tolerant Trp halogenation in peptides" | not drawn | no |
| solid bold wedge at the Trp alpha carbon | solid wedge to the CH2 | hashed wedge (tool choice; configuration S in both) | no |
| indole orientation, NH at lower right | benzo ring upper right, NH lower right | same | yes |
| H stacked under the amide and amine N | yes | yes | yes |

## Differences from the paper

- Peptide: the grey beads and `( )n` / `( )m` repeat markers are missing. The N- and C-terminal groups are methyl caps, so this is a small-molecule model of the Trp residue, not the peptide.
- Halogen: the paper's dot is a generic "Cl or Br" placeholder; the replica prints Br as text inside a halo.
- Arrow: about 2.2 times longer than the paper's arrow relative to label height (see Audit).
- Stereo bond: the paper's solid wedge is drawn hashed.
- Layout: no grey title bar, no caption, and no row structure. The scheme is one linear row.
- Bromide: the crop shows no halide source, so the step is flagged as unbalanced by the tool; the drawn conditions match the crop.

## Tool gaps (partly wrong or incomplete; see Audit)

- No bare coloured dot as a substituent: `atom_halos` adds a disc behind the atom, but the element label is still printed. A substituent placeholder that is drawn as a dot, with no text, is not available in `draw_figure`.
- No size control for the halo: the radius is in points, and the minimum tested value (9 pt) gives a disc about 1.25 bond lengths across. A 5 pt value was queued but did not render in the session.
- No peptide or bead cartoon: grey circles with `( )n` and italic `n`, `m` repeat markers cannot be expressed, so the chain had to be replaced by caps.
- No scheme or row title bars (grey fill, bold text) and no caption text under a scheme.
- Arrow length: `arrow_length_over_bond_length` (card value 4.2) is not applied by the house style; the report's `applied` lists only `reagent_text_color`, and `skipped` does not name it either.
- Wedge display: `draw_figure` chooses the stereo bond display itself and drew the Trp alpha bond as hashed; there is no per-bond display field in the brief.
- Generic halogen: there is no way to write "Cl or Br" as a variable, so the replica has to pick one halogen.
- Multi-row figures: one brief draws one reaction, so the three-row crop cannot be reproduced as a single file.
- Balance: a reagent that the crop does not show (here a bromide source) cannot be marked as "given elsewhere"; the tool reports the imbalance and does not add it.

## Audit

Checked against `reference.png`, `rendered.png`, `brief.json`, the card `acs_chem_biol.json` and the toolkit code. No ChemDraw run was made. Pixel values come from the two PNG files in this folder. Ratios use the "4V" cap height as the unit, because the "4V" width-to-height ratio is the same in both images (1.67 paper, 1.65 replica).

Measured:

- Paper crop (718 x 973): both arrows are about 80 px long (top 79 px, bottom 79 to 81 px). "4V" cap height 18 px. Grey-purple dot 20 px across. Shaft ink about 1.9 px.
- Rendered (1200 x 187): arrow 254 px, dot 63 px, "4V" cap height 26 px, shaft ink about 1.8 px. Scale is about 3.5 px per pt (from the 72 pt arrow and 18 pt dot), so the 14.4 pt bond is about 50 px and bond/cap is about 1.9.
- In label-height units: arrow 4.4 in the paper and 9.8 in the replica (replica about 2.2 times longer). Dot 1.1 in the paper and 2.4 in the replica (about 2.2 times larger). Shaft 0.11 in the paper and 0.07 in the replica (replica about 35 percent thinner). These ratios do not depend on the bond length.
- Dot colour: paper (176, 161, 184), replica (176, 160, 185). Colour matches.
- The card's crop-05 values (arrow 105 px, bond 25 px, cap 12.5 px) cannot be reproduced from this file. No bond length was measured in the paper, so every ratio that uses it (5.0 against 4.2; 1.25 against 0.8 bond lengths) is unverified. A halo radius of about 4 pt would match the paper's dot in label-height units (CASE used 9 pt).
- Confirmed: H stacked under both N atoms in both images (separate bands); indole orientation (benzo ring upper right, NH lower right); "4V" above a plain arrow; black reagent text.

Table changes made above: the bare-dot row (partial to no), the Trp dot row (yes to no, position only), the bond/cap row (replica value corrected to about 1.9), the line-width row (approx to no), the label-font row (not verified to yes, font name Arial in the toolkit template) and the arrow row (basis corrected, magnitude about 2.2 times, not 19 percent).

Overclaims in the earlier text:

- "about 19 percent longer" understated the arrow error. In label-height units it is about 2.2 times.
- "1.25 bond lengths" against "0.8 bond lengths" rests on a 25 px bond that is not in the file. The halo is about 2.2 times the paper's dot in label-height units.
- "4/12 conventions matched" does not appear in this file. The table has 21 rows, and 7 were "yes" before this audit. After the audit 7 remain "yes" (4V above arrow, plain arrow, kekule rings, black reagent text, label font, indole orientation, stacked H), so the count is 7 of 21.
- Two "no" rows (variation colour, no cyan on Trp) are "no" only against the card, whose values for those conventions come from crop 01. Against the paper both match, which would give 9 of 21. The table mixes the two standards. The card's values for those two conventions do not apply to crop 05.
- The draw-report claims (`checks_passed: true`, `readback: matched`, `native: rendered`, one warning) cannot be checked here. No `validation.json` or report is in this folder.
- The Trp S configuration was not re-checked in this audit.

Tool gaps the replicator missed or got wrong (from reading code, not run):

- `compose_chemical_figure` (`toolkit/cdxml_toolkit/mcp_runtime/figure_tools.py`, function at line 608, listed in `FIGURE_TOOLS` at line 1504) takes explicit coordinates and these objects: `molecule` (with `bond_displays` for WedgeBegin, WedgedHashBegin, Bold, Dash and others, `atom_halos` and `label`), `text` (with `runs` for rich text), `arrow` (start and end, so arrow length is exact), `ellipse` and `rectangle` (`fill_type` Solid, `background`, `round_edge`; the fill colour key was not verified). It also takes a `style` object that overrides `bond_length`, `line_width`, `bold_width` and `hash_spacing`. This covers the per-bond display gap, exact arrow length, halo size (an ellipse of exact diameter), the bead cartoon (filled grey ellipses with italic n and m runs), grey title bars and captions, and line-width control. Several rows in one file look possible through its `grid` and object keys.
- `draw_figure`'s brief `title` key is stored in the scheme descriptor (`toolkit/cdxml_toolkit/mcp_runtime/figure_draw.py` line 205), but no code in `render/` or `layout/` reads it. A title is probably dropped without warning.
- None of the card's measured values (`bond_length_over_cap_height`, `line_width_over_bond_length`, `bold_width_over_bond_length`, `arrow_length_over_bond_length`, `label_font`) is read by any drawing code. `draw_figure` takes its 0.6 pt line and 14.4 pt bond from the acs1996 preset, so the card's line width is not enforced. The line-width row should say so.
- The replicator is right that the arrow length is not named in the report. The skipped list covers only null convention keys (`figure_house.py`).
- A "Cl or Br" key can be written as a `text` object. The molecule still needs one halogen.
