# oprd_process-03: Suzuki coupling test, Scheme 3 (Guthrie, Gupton et al., 2026)

Source: Guthrie, Gupton et al., "A concise process to lenacapavir sodium: one-pot sequential Heck/Suzuki-Miyaura couplings", *Org. Process Res. Dev.* 2026. DOI: [10.1021/acs.oprd.5c00443](https://doi.org/10.1021/acs.oprd.5c00443). Licence: CC BY 4.0 (as recorded on the house-style card). The reference crop is reproduced as `reference.png` under that licence.

Drawing style: the `oprd_process` house style (base preset ACS Document 1996), figure type `reaction_scheme`, crop `evidence/oprd_process-03.png`. See `brief.json`.

## What is reproduced

Part of Scheme 3, the Suzuki coupling test. Boc-protected pyridyl bromide 5 (100 mg) is drawn as the substrate, with two product arms: 7 (NR2 = NHMs, A%: ~40 %) and 9 (NR2 = NH2, IY 52 %). Each product has its own arrow from a vertical bracket (layout `divergent`). The conditions are copied from the crop, but they are repeated above and below each arrow. The crop has them once, on a common stem before the bracket. The replica draws no stem, so the substrate is not connected to the bracket, and the branch labels are not drawn.

The coupling partner, written as "Frag B-DiMs" for 7 and "Frag B" for 9 on the branch arms of the crop, is not drawn and not placed. The paper gives it only as a label, and no structure was read from the crop. The steps therefore show up as unbalanced in the report (see below).

## Structures

Read from the crop by hand (no OCSR run). Formulas checked with RDKit: 5 C24H27BrF2N2O4S, 7 C34H35ClF5N5O6S2, 9 C33H33ClF5N5O4S.

| ID | SMILES |
| --- | --- |
| 5 | `CC(C)(C)OC(=O)NC(Cc1cc(F)cc(F)c1)c1nc(C#CC(C)(C)S(C)(=O)=O)ccc1Br` |
| 7 | `CC(C)(C)OC(=O)NC(Cc1cc(F)cc(F)c1)c1nc(C#CC(C)(C)S(C)(=O)=O)ccc1-c1ccc(Cl)c2c(NS(C)(=O)=O)nn(CC(F)(F)F)c12` |
| 9 | `CC(C)(C)OC(=O)NC(Cc1cc(F)cc(F)c1)c1nc(C#CC(C)(C)S(C)(=O)=O)ccc1-c1ccc(Cl)c2c(N)nn(CC(F)(F)F)c12` |

The stereocentre on the NHBoc carbon is a solid wedge from the carbon to the NH in the crop. The replica draws a plain bond and the SMILES has no configuration, so the stereochemistry is not reproduced.

## Brief history

- Try 1 (`brief-v1`, not kept in the case folder): solvent given as one line "1,4-Dioxane (2 mL), water (0.3 mL)", substrate label "5", yield "A%: ~40 %". Rendered; the "~40" came out with subscript digits ("~₄₀"), and the solvent line wrapped at the comma.
- Try 2 (final, `brief.json`): solvent split into two lines as in the crop, substrate label "5 (100mg)", yield "A%: ~ 40 %" (space after the tilde). Rendered. The readback and lint results are not in the case folder and were not re-checked in the audit below.
- No third try: the remaining differences need tool changes, not brief changes.

## Convention checks

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| yield_format `{value}%` (reaction_scheme) | "A%: ~40 %", "IY: 52 %" (label, space before %) | "A%: ~ 40 %" (space after the tilde), "IY: 52 %" upright | no |
| selectivity_format null | no selectivity shown | none | yes |
| highlight_fill null | none | none | yes |
| variation_color null | none | none | yes |
| reagents with mol % and eq above arrow; solvent volumes, time and temperature below (conditions placement) | Pd(dppf)Cl2 (5 mol %), K2CO3 (6 eq) above the common stem; 1,4-dioxane (2 mL), water (0.3 mL), 16 h, 110 °C below it, once for both products | the same lines repeated above and below each branch arrow; no common stem | no |
| bold compound number followed by italic scale `5 (100mg)` | bold 5, italic (100mg) | bold 5 (100mg), whole label bold | no |
| inset yield table under product | not in this crop (crop 08) | not drawn | n/a |
| compound_label_face bold | bold | bold | yes |
| compound_label_color #000000 | black | black | yes |
| compound_label_italic_suffix false | italic scale present in the crop | not applied | no |
| yield_placement under_arrow | yield as the last line under the arrow | yield last line of the lower block | yes |
| conditions_split reagents above, solvent below | split is right on each arrow; the shared-stem placement is recorded in the row above | split as stated, repeated per arrow | yes |
| abbreviate_groups Boc | Boc | Boc, contracted in 5, 7 and 9 | yes |
| abbreviate_groups OTBS | not in this crop | not drawn | n/a |
| SO2Me written as text | `SO2Me` | drawn as S(=O)(=O)CH3 | no |
| CF3 written as text (on CH2) | `CF3` | drawn as explicit F3C | no |
| aromatic_rings kekule | Kekulé rings | Kekulé rings | yes |
| arrow_style plain | plain | plain | yes |
| arrow about eight bond lengths | reference stem (no head) 162 px = 6.4 bonds; reference branch arrows 102 px = 4.0 bonds (bond 25.5 px, measured on reference.png). Paper 622 / 85 = 7.3 refers to the stem | replica branch arrows 276 px = about 7 to 8 bonds (bond length estimated from glyph height) | no |
| bond length / cap height 2.0 | reference 25.5 / 11.5 px = 2.2 (measured on the PNG) | replica about 2.0 (estimated from glyph height; not measured on the cdxml) | approx. |
| line width 0.085 | reference shaft ink 2.2 px over a 25.5 px bond = 0.086 | replica shaft ink about 1.4 px over a bond of about 37 px = about 0.04 | no |
| label font Arial | sans-serif, Arial-like glyphs | font name not visible in the PNG | not verified (counted as no) |
| show_plus_sign true | no plus sign (one substrate) | none | n/a |
| new_bond_color, substrate_colors null | black | black | yes |
| reagent_text_color #000000 | black | black | yes |

Rows that the table cannot show, found on audit:

| feature | paper | replica | match |
| --- | --- | --- | --- |
| common stem from the substrate to the bracket | plain stem from 5 to the bracket, no head | none; no dark pixels between the substrate and the bracket | no |
| branch labels "Frag B-DiMs" and "Frag B" on the branch arms | bold, on the arm before the arrowhead | absent | no |
| compound numbers 7 and 9 | bold, above each branch arrow, above the NR2 line | bold, under each product structure | no |
| methyls on the gem-dimethyl carbon | written as "Me" labels | drawn as bonds | no |
| yield line face | "IY: 52 %" in italic, "A%: ~40 %" upright | both upright | no |
| stereocentre on the NHBoc carbon | solid wedge | plain bond | no |

Claimed conventions that were checked: 19. Matched: 12 after the audit (14 before). The arrow-length and line-width rows, which the first count left out, are both no, so the count would be 12 of 21 if they were included. Not applicable and approximate rows are left out of the count, as before.

## Differences from the paper

- The coupling partner (Frag B-DiMs, Frag B) is not drawn, and the branch labels at the divergence point are not placed. Both steps are reported as unbalanced: the missing reactant formulas are C10H8ClF3N3O2S (step 1) and C9H6ClF3N3 (step 2). Nothing was added to the drawing.
- The paper states Pd(dppf)Cl2 and K2CO3 once, on the common stem before the bracket. The replica repeats them above both branch arrows, and the replica has no common stem at all.
- The paper writes the scale in italics, `5 (100mg)`; the replica sets the whole label in bold.
- The paper writes the yield "IY: 52 %" in italics; the replica sets it upright.
- The paper places 7 and 9 above their branch arrows; the replica places them under the product structures.
- SO2Me and CF3 are drawn as structures, and the methyls are drawn as bonds, not as "Me" labels; the paper writes all three as text.
- The NR2 variable is drawn as two explicit products (NHMs for 7, NH2 for 9); the NR2 line is kept above each arrow as in the paper.
- The yield text is written "A%: ~ 40 %" with a space; the paper has "~40". Without the space the tool subscripts the digits.
- The stereocentre is not specified and its wedge is lost (see above).
- The replica's branch arrows are about twice as long as the reference branch arrows, relative to the bond length.

## Tool gaps

- Divergent layout has no shared stem: the replica draws no connection from the substrate to the bracket, and conditions common to all branches cannot be drawn once on that stem, so they are repeated per branch.
- No branch label: text placed on a divergence arm (here "Frag B-DiMs", "Frag B") cannot be attached to a branch arrow. The coupling partner has no structure in the brief, so the balance check cannot pass for these steps.
- Branch arm length: the reference arms are short (about 4 bond lengths) because the label sits between the bracket and the arrowhead. The replica's arrows are about 7 to 8 bond lengths. Whether the layout can set a shorter branch arm was not tested.
- Label placement: compound numbers are placed under the product in the replica, not above the branch arrow as in the crop. Whether the tool can anchor a compound number to the arrow was not tested.
- The `compound_label_italic_suffix` convention is not applied, so a scale in italics after the bold number cannot be reproduced.
- Per-run italic is not available for the yield line either: "IY: 52 %" is italic in the crop.
- Yield and condition tidying turns digits after "~" into subscript formula digits ("~40" becomes "~" + subscript 40). The replica avoids this with a space; the tool should exempt yield text.
- Abbreviation: the card's `abbreviate_groups` lists only Boc and OTBS, so SO2Me, CF3 and Me were never sent to the tool for contraction. Whether the tool contracts them when listed was not tested. The replica's SO2Me and CF3 failures therefore come from the card's list, not only from the tool.
- Stereo: the SMILES has no configuration, so the wedge is lost. Whether the tool renders a wedge from stereo in the SMILES was not tested.
- Line weight: the replica's bond and arrow lines are about half the card's ratio to bond length (about 0.04 against 0.085, estimated on the PNG). Whether the preset can be changed per figure was not tested.
- No variable substituent: a Markush-like family (NR2 = NHMs / NH2) cannot be expressed on one structure; each product is drawn separately.

## Audit

Reviewed against `reference.png` (900 x 230 px) and `rendered.png` (1200 x 777 px), using pixel runs and ink integration. Replica bond lengths are estimated from the glyph height and the preset bond/cap ratio (about 10 % uncertainty), so the replica ratios are approximate. The card (`toolkit/cdxml_toolkit/publication/house_styles/oprd_process.json`) is internally inconsistent in one place: `compound_label_italic_suffix` is false, while its signature features call for the italic scale. Its `abbreviate_groups` omits SO2Me, CF3 and Me.

Corrections to the first version:
- "The whole of Scheme 3" and "two branch arrows from one substrate" were overclaims: the replica has no connection from the substrate to the bracket and no branch labels.
- The conditions row "same lines, same placement" was wrong: the crop places the conditions once on a common stem.
- "The stereocentre ... is drawn as a plain bond in the crop" was wrong: the crop has a solid wedge.
- "Arrow about eight bond lengths" was marked approximate, but the reference branch arrows are about 4 bond lengths.
- The line-width row was "not measured"; the PNG shows the replica line about half the card ratio.
- "Label font Arial" was marked matched; the PNG cannot confirm the font name.
- The yield "IY" face, the compound-number position, the Me labels and the wedge were not in the first table.

Corrected matched count: 12 of 19 counted rows (was 14).
