# Lucas, Opatz et al., Org. Process Res. Dev. 2023: pretomanid three-step route with IY table (Scheme 7)

Source: Lucas, Opatz et al., "Short and efficient synthesis of the antituberculosis agent pretomanid from (R)-glycidol", *Org. Process Res. Dev.* 2023. DOI: [10.1021/acs.oprd.3c00187](https://doi.org/10.1021/acs.oprd.3c00187). Licence: CC BY 4.0 (from the house-style card). Reference crop: `reference.png` (copy of `skill/chemdraw/assets/house-styles/oprd_process/evidence/oprd_process-08.png`).

Drawing style: the `oprd_process` house style, figure type `reaction_scheme` (base preset ACS Document 1996). Brief: `brief.json` (style `oprd_process`, max_width 760). Replay: `replay.py`.

## What is reproduced

The text of Scheme 7 and its five structures are present (the layout, reagent placement, stereo depiction and IY table differ, see Audit): 7 plus a glycidyl ether gives 8 (step 1, DIPEA/toluene or K2CO3/H2O); 8 gives 9 (step 2, p-OCF3-BnBr, NaH, NaI, toluene/NMP); 9 gives 1 (step 3, (1) deprotection, (2) cyclisation). The IY table is written under the product block. The four protecting groups of the paper (PMBz, Tr, Bz, TBS) are the IY row labels; the drawn structures use one representative group (TBS) for 8, 9 and the epoxide, because the crop shows a generic OR. The compound numbers are copied from the crop (8, 21-23; 9, 24-26; 1).

Structures were read by eye from the crop at 827 px; OCSR was not run. SMILES in `brief.json`:

| ID | SMILES | Notes |
| --- | --- | --- |
| 7 | `O=[N+]([O-])c1c[nH]c(Br)n1` | 2-bromo-4-nitroimidazole, regiochemistry as drawn |
| epoxide | `CC(C)(C)[Si](C)(C)OC[C@@H]1CO1` | TBS glycidyl ether, stereo mapped from 8 (see below) |
| 8 | `O[C@@H](Cn1cc([N+](=O)[O-])nc1Br)CO[Si](C)(C)C(C)(C)C` | (S); R = TBS representative |
| 9 | `O(Cc1ccc(OC(F)(F)F)cc1)[C@@H](Cn1cc([N+](=O)[O-])nc1Br)CO[Si](C)(C)C(C)(C)C` | (S); Ar = 4-(trifluoromethoxy)phenyl, as in 1 |
| 1 | `O=[N+]([O-])c1cn2c(n1)OC[C@@H](OCc1ccc(OC(F)(F)F)cc1)C2` | (S), pretomanid |

Stereo: the configuration of 1 was set to (S), the configuration of pretomanid, and checked with RDKit CIP. 8 and 9 carry the same spatial arrangement at the stereocentre (the O atom is retained through steps 2 and 3, and the CIP priority order is unchanged), so they are (S) as well. The epoxide was built from 8 by ring closure at the same stereocentre, which gives (S). These assignments were not read off the crop; the crop wedges were not decoded at this resolution.

## Replica

Rendered with desktop ChemDraw (`rendered.png`, downscaled from 2627 px to 1200 px). The report says `checks_passed: true`, readback `matched` for 6 structures, and `native.rendered`. Balance warnings for steps 2 and 3 are expected: p-OCF3-BnBr and the silyl by-product are text reagents and are not drawn (see Tool gaps).

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| compound label face bold | bold 7, 8, 9, 1 | bold on 8, 9, 1; 7 cannot be resolved at this scale | no (unverified) |
| compound label colour black | black | black | yes |
| aromatic rings Kekule | Kekule imidazole and aryl rings | Kekule | yes |
| plus sign between substrates | no plus sign; epoxide drawn above the arrow as a reagent | "+" between 7 and the epoxide, epoxide as substrate | no |
| arrow style plain | plain arrows | plain arrows | yes |
| reagent text colour black | black | black | yes |
| reagents above, solvent below (conditions split) | all conditions written above the arrow, none below | all conditions above; the tool skips the reagents_above_solvent_below split (see Audit) | no (convention not shown) |
| yield format `{value}%` | `40%`, `36%`, `34%`, `31%` | `40%`, `36%`, `34%`, `31%` | yes |
| yield placement under arrow (card) | IY table under product 1 | IY table under the arrow | no |
| abbreviate groups Boc, OTBS, NO2 (card) | OR and Ar as generic labels, no OTBS; NO2 drawn as O2N | OTBS (representative TBS); NO2 drawn as N+/O- bonds | no |
| mol % and eq above arrow, solvent volumes, time and temperature below (card signature) | not in this crop | not drawn | not shown |
| scale in italics after bold number (card signature) | not in this crop | not drawn | not shown |
| inset yield table under product, IY over 3 steps (card signature) | present, under product | present, under arrow | no (placement only partly matches) |
| numbered step labels (1) (2) on one arrow | (1) deprotection, (2) cyclisation | same text | yes |
| arrow length about 8 bond lengths (top-level signature) | long arrows | not measured | not shown |

Matched after audit: 6 of 15 table rows (see Audit). The earlier claim of 8 of 13 did not match the table, which had 9 rows marked yes. Rows marked "not shown" count as not matched.

## Differences from the paper

- Layout: the paper draws two rows, 7 to 8 to 9 left to right on the top row, then 9 to 1 right to left on the bottom row. The replica uses the sequential layout, one row per step, all arrows left to right (`layout: "sequential"`). Route direction and row grouping cannot be set.
- Epoxide: the paper writes the glycidyl ether above the arrow as a reagent structure. The replica puts it on the left as a substrate with a plus sign.
- Protecting groups: the paper uses generic OR and Ar. The replica uses TBS (drawn as OTBS) and 4-(trifluoromethoxy)benzyl.
- Nitro group: the paper writes O2N as a label. The replica draws the charged N+ and O- bonds because NO2 is not in the card's abbreviate list.
- Stereo bonds: the replica draws a hashed bond on 8 and 1 and a bold wedge on 9 and the epoxide. The claim that the paper uses bold wedges on all four was not decoded at this resolution and is unverified (see Audit).
- IY table: the paper sets the table under product 1 with two columns (PMBz 40% / Tr 36%, Bz 34% / TBS 31%) and a bold heading. The replica writes it as centred plain lines under the arrow.
- Compound 9 is labelled 9, 24-26 with a bold number, as in the paper; the scale and mol % are absent from this crop and from the replica.
- Byproducts: the p-OCF3-BnBr reagent (C8H5F3O) and the silyl by-product of step 3 (C6H15BrSi) are not drawn. Step 2 and step 3 are flagged as not balancing as drawn; the paper also does not draw them.

## Tool gaps

- No structure-as-reagent above an arrow: `above` takes text lines only, so the epoxide cannot be placed above the arrow.
- No inset table under a product: the IY table can only be written as below-arrow lines. The card's `under_product_label` and `after_product_label` placements exist, but they take one yield per product and cannot hold four labelled values.
- No route row control: the sequential layout wraps one row per step; the paper's serpentine route (second row running right to left) cannot be requested. Tried max_width 504 (three rows, the same sequential layout) and 760 (three rows, one step per row).
- No generic R or Ar placeholder was tested; the TBS representative was used instead, which forces the OTBS abbreviation on the drawing.
- No wedge style control: draw_figure chose hashed bonds on 8 and 1 for the given SMILES.
- No bold or tabular text in below lines: the IY heading and the two-column row alignment cannot be reproduced.
- Byproduct and reagent-text balance warnings persist when reagents are given as text; no way to mark a text reagent as intentionally undrawn.

## Card observations (not fixed; see result.json card_errors)

- Reaction scheme signature 1 (mol % and eq above, volumes, time and temperature below) and signature 2 (scale in italics after the bold number) do not appear in crop 08.
- The top-level abbreviate_groups note says OTBS appears in crop 08; the crop shows OR and Ar, and no OTBS.
- The card's abbreviate list omits NO2, which the crop draws as O2N.
- The card's top-level yield_placement is under_arrow, while the reaction_scheme signature for this crop is an inset table under the product; the two conflict for crop 08.

## Audit

Checked against reference.png and rendered.png, the card in toolkit/cdxml_toolkit/publication/house_styles/oprd_process.json, and the tool code in toolkit/cdxml_toolkit/mcp_runtime/figure_house.py and figure_draw.py.

Overclaims corrected above:
- Plus sign: the paper has no "+" between 7 and the glycidyl ether. The epoxide sits above the arrow as a reagent, so the paper column was wrong and the row does not match.
- Conditions split: figure_house.py lists reagents_above_solvent_below as skipped ("the brief's above/below lines are kept as given"). Crop 08 has no solvent line below the arrow, so the convention is not shown.
- Abbreviations: the paper draws NO2 as O2N. The card omits NO2 from abbreviate_groups, and the replica draws N+/O- bonds. This is a second mismatch beyond OTBS.
- Compound label face: bold looks right for 8, 9 and 1, but compound 7 cannot be resolved at this scale in either image.
- Count: the earlier text said 8 of 13 while its table had 9 rows marked yes. The corrected count is 6 of 15 rows.
- Stereo: the Differences section describes the paper's wedge style on 8, 9, 1 and the epoxide, but the same file says the wedges were not decoded. Hashed bonds on 8 and 1 are visible in rendered.png; the paper's style on those bonds is not confirmed.
- "The whole of Scheme 7" overstated the match; the layout, reagent placement, stereo depiction and IY table all differ.
- The Replica section cites result.json (checks_passed, readback matched, native.rendered) and card_errors. Neither file is in this folder, so those claims cannot be checked here.

Checked and correct: RDKit rdCIPLabeler gives S for the epoxide, 8, 9 and 1 in brief.json, as the CASE states. This confirms the SMILES are internally consistent, not that they match the paper's drawn wedges.

Tool gaps the replicator missed:
- Arrow length has no direct setting. The arrow length follows the longest condition line (figure_draw.py _relayout), so the card's about-eight-bond-lengths signature cannot be requested.
- The card's reagents_above_solvent_below split is skipped by the tool, so the solvent-below convention cannot be applied even where a paper uses it.
- No per-bond wedge or hash control. Species fields are id, smiles or name, label, ring_fills, atom_halos and ts_bracket only.
- No generic group label. Species take a SMILES or a name that resolves to a real molecule, so generic OR and Ar cannot be drawn as labels. This follows from the brief schema and was not tested.
- NO2 abbreviation exists in the tool (house_styles.py) but is missing from this card. This is a card fix, not a tool gap.
- One yield per step. A labelled multi-value table such as IY over 3 steps has no field.
