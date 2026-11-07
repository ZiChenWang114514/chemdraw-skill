# ACS organic journals: Scheme 2 header reaction (silyl enol ether azidation)

## Source

Qing et al., *Org. Lett.* 2024, 26, 9215. DOI: [10.1021/acs.orglett.4c03212](https://doi.org/10.1021/acs.orglett.4c03212). Licence: CC BY 4.0 (from the `acs_jacs` card). Reference crop: `evidence/acs_jacs-02.png` (copied here as `reference.png`), Scheme 2, "optimized reaction conditions" header and scope panel.

Drawing style: the `acs_jacs` house style in `brief.json` (base preset ACS Document 1996, bold compound labels, reagents above and solvent and conditions below, inline plus sign, Kekule rings).

Figure type: `reaction_scheme`. The card has no `figure_types` key at all, so only the top-level conventions of the card apply to this crop.

## What is reproduced

The header reaction of Scheme 2: silyl enol ether **6** and trimethylsilyl azide **2** give the azido ketone **7** with PhI(OAc)2 (2 equiv) and residual H2O in DMSO, air, rt, 30 min.

- The generic aryl group Ar of the paper is drawn as phenyl (Ar = Ph). In the header the paper draws Ar as a filled pale-red disc with no label (the open circle labelled Ar belongs to the scope panel). The tools cannot express either, so the substituent is a stand-in and not a claim about the paper's scope.
- No yield is drawn: the header has none. The per-entry yields (7a to 7ac) and the 7a to 7ac scope panel are not reproduced.
- The blue header rules and italic section captions are not drawn.

SMILES in `brief.json`: `C=C(O[Si](C)(C)C)c1ccccc1` (6), `C[Si](C)(C)N=[N+]=[N-]` (2), `[N-]=[N+]=NCC(=O)c1ccccc1` (7). All three were checked with RDKit and each matches the drawn structure.

## Replay

```
python skill/chemdraw/scripts/cdx.py py skill/chemdraw/assets/house-styles/acs_jacs/replica/acs_jacs-02/replay.py NEW_DIR
python skill/chemdraw/scripts/cdx.py render NEW_DIR/figure.cdxml
```

`replay.py` runs `draw_figure` on `brief.json` offline and writes `figure.cdxml` and `validation.json`. `rendered.png` is the desktop ChemDraw render (downscaled to 1200 px wide, white background).

## Comparison

Claimed conventions are the card's top-level conventions with a non-null value (11). "Visible" marks whether the header shows the convention at all.

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| compound_label_face: bold | 6, 2 and 7 bold | 6, 2 and 7 bold | yes |
| compound_label_color: #000000 | black | black | yes |
| compound_label_italic_suffix: false | no suffix on labels | no suffix | not visible |
| yield_format: "{value}%" | no yield in the header | no yield drawn | not visible |
| conditions_split: reagents above, solvent below | PhI(OAc)2 (2 equiv), residual H2O above; DMSO, air, rt, 30 min below | same split | yes |
| substrate_layout: inline_plus | 6 + 2 on one line | 6 + 2 on one line | yes |
| abbreviate_groups: OMe | no OMe, but the header uses TMS, N3 and OTMS labels | no labels; Si(CH3)3 and N=N+=N- drawn out in full | no (house abbreviation style visibly fails) |
| aromatic_rings: kekule | rings drawn with inner double bonds | Kekule rings | yes |
| reagent_text_color: #000000 | black | black | yes |
| arrow_style: plain | plain solid arrow | plain solid arrow | yes |
| show_plus_sign: true | plus between 6 and 2 | plus shown | yes |
| substrate_colors: null | core of 6 dark red (#800000), TMS-N3 dark blue (#004080) | all black | no (card null, see card errors) |
| new_bond_color: null | no coloured new bond in the header | black | n/a (card null, not counted) |
| highlight_fill: null | none | none | n/a (card null, not counted) |
| measured.arrow_length_over_bond_length: 7.0 | 410 / 37 px = 11.1 for this crop | 11.5 (CDXML arrow 165.1 pt / bond 14.4 pt) | no (card value is from crop 01) |
| measured.line_width_over_bond_length: 0.055 | 2 / 37 px = 0.054 | 0.60 / 14.4 pt = 0.042 | no |
| measured.bond_length_over_cap_height: 2.2 | 37 / 17 px = 2.2 | not measured on the render | not checked |
| label font Arial or Helvetica | Arial-like | Arial-like; LabelFont 3 not checked (no CDXML in the case folder) | yes, by eye only |
| TMS and N3 as label abbreviations | TMS and N3 labels, OTMS label on 6 | drawn as Si(CH3)3 and N=N+=N- skeletons | no |
| carbonyl O orientation in 7 | O drawn above the carbonyl | O drawn below the carbonyl | no |
| generic Ar substituent | filled pale-red disc with no label in the header (open Ar circle only in the scope panel) | phenyl ring | no (stand-in) |
| orientation of 6 and 7 | Ar at left of 6 and 7, OTMS above the alkene carbon, N3 at right of 7 | phenyl at upper right of 6, O-Si at lower left; 7 mirrored, N3 at left and phenyl at right | no |
| blue header rules and italic captions | present | absent | no |

Counts: 11 claimed conventions, 8 match on inspection. The 3 rows that are not visible or fail (italic suffix, yield format, abbreviate_groups) are not counted as matches. Outside the 11 claimed conventions the replica also fails on orientation, substrate colour, the Ar placeholder, TMS and N3 labels and scheme decoration, so the 8/11 headline overstates how close the figure is to the paper.

## Differences from the paper

- Ar is drawn as phenyl. The paper's filled header disc and the open-circle Ar of the scope panel are not reproducible with the tools.
- TMS and N3 are drawn as full atoms. The paper uses the labels TMS, N3 and OTMS.
- Reagent 2 and the azide of 7 are drawn in charged N=N+=N- form, not with an N3 label.
- Colours are absent: the core of 6 is black (paper dark red), TMS-N3 is black (paper dark blue).
- The carbonyl O of 7 points down, the paper points it up.
- Orientation: the replica mirrors 6 and 7 against the paper (the paper has Ar at left and N3 at right of 7; the replica has N3 at left and phenyl at right).
- The header rules and italic blue captions are absent.
- Measured geometry is a little lighter than the crop: line width 0.042 of the bond against 0.054 in the paper.
- The yield and the scope panel of the crop are not reproduced.

## Tool gaps

- Group abbreviations come only from the card's `abbreviate_groups`. TMS, N3 and OTMS cannot be shown as labels, and the brief has no per-species label or abbreviation field.
- The brief cannot colour a species or a substituent. Substrate colours depend on the card's `substrate_colors`, which is null for this style, so the dark red and dark blue of the paper cannot be drawn.
- The generic Ar group: `draw_figure` has no open-circle placeholder with an Ar label.
- No control over the orientation of the carbonyl O (automatic layout).
- No control over the orientation or mirroring of whole species, and no arrow length control in the brief, so the card's arrow ratio cannot be applied even when it is correct.
- No scheme-level decoration: no header rules and no italic blue caption above or below the scheme.
- The card's `measured` geometry (line width, bond to cap height) is not applied; only the base preset geometry is used.
- The balance check flags step 1: the products lack C6H18Si2 (the hexamethyldisiloxane by-product), and the oxidant PhI(OAc)2 is not drawn. The paper omits both, so the warning is correct but not fixable from the brief.

## Card errors (reported, not fixed)

- `measured.arrow_length_over_bond_length` is 7.0, but this crop gives 11.1 (410 / 37 px). 7.0 matches only `acs_jacs-01`.
- `abbreviate_groups` is `["OMe"]`, but the observations for this crop list TMS, N3, Ph, Me and MeO2C labels, and the scope uses OTMS. The card does not contract the groups the crop uses.
- `substrate_colors` is null, but the observations for this crop record dark red substrate cores (#800000) and dark blue azide and TMS (#004080).
- `yield_placement` is null, but the observations describe yields after the bold label with a comma (7e, 73%). The header has no yield, so this is not tested here, but the card contradicts itself.
- `figure_types` is absent from the card, so the `reaction_scheme` figure type has no conventions and the crop is not listed under any figure type.

## Audit

Reviewed by re-reading `reference.png` and `rendered.png` (rendered at 1200 px, zoomed for inspection) against each comparison row.

- Overclaims corrected: the abbreviation row was marked "not visible", but the paper header visibly uses TMS, N3 and OTMS labels and the replica spells them out, so it is a failure. The paper's substituent is a filled disc, not an open circle. The `figure_types` key is absent, not an empty object. The two null rows (new_bond_color, highlight_fill) were marked "yes" but are not tests, so they are now n/a. The LabelFont 3 claim cannot be checked from this folder.
- Confirmed as matched on inspection: bold labels 6, 2 and 7 (black), conditions split, inline plus, Kekule rings, black reagent text, plain arrow, plus sign. These are 8 rows, so the count stays at 8 of 11 claimed conventions, with 3 rows not visible or failing.
- Missed by the replicator and added to the table: the mirror and rotation of 6 and 7 against the paper (the largest visible layout difference).
- Not verified: the measured line width (0.042) and the arrow ratio (11.5) come from CDXML that is not in this folder. By eye on the 1200 px render the arrow is roughly 10 to 11 bond lengths, so the card's 7.0 is still wrong, but the exact replica value was not re-measured.
- Tool gaps added: species orientation and mirroring, and arrow length. The other gaps listed by the replicator stand.
