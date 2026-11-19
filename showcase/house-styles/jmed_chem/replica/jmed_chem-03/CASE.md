# jmed_chem-03: TNG462 final fragment coupling (Scheme 8, last row)

Source: Cottrell et al., "Discovery of TNG462: a highly potent and selective MTA-cooperative PRMT5 inhibitor", *J. Med. Chem.* 2025. DOI: [10.1021/acs.jmedchem.4c03067](https://doi.org/10.1021/acs.jmedchem.4c03067). Licence: CC BY 4.0. Reference crop: `evidence/jmed_chem-03.png` (Scheme 8, synthesis of TNG462).

Drawing style: the `jmed_chem` house style card (base preset `acs1996`), `style: "jmed_chem"` in `brief.json`.

Figure type: `total_synthesis`.

## What is reproduced

The bottom row of Scheme 8 only: acid **88** plus amine **92** give TNG462 under the step letters m and n, drawn as one arrow with "m, n" above it. The rows above (synthesis of 86, 87, 88, 89, 90, 91 and 92) and the BF3K reagent are not drawn. The Boc-protected amide is not drawn as an intermediate, because the crop draws only one arrow.

| Structure | SMILES (in brief.json) |
| --- | --- |
| 88 | `CCc1cc(NC(=O)C(=O)O)cnc1N(C(=O)OC(C)(C)C)C(=O)OC(C)(C)C` |
| 92 | `CC1CCC(c2ccc3sc(C4CCN(C)CC4)nc3c2)NC1` (no stereo, see below) |
| TNG462 | `Nc1ncc(NC(=O)C(=O)N2CC(C)CCC2c2ccc3sc(C4CCN(C)CC4)nc3c2)cc1CC` (no stereo, see below) |

The SMILES were checked with RDKit (formulas C19H27N3O7 for 88, C19H27N3S for 92, C28H36N6O2S for TNG462). They were read from the crop by hand. No OCSR was run.

## Replay

```
python skill/chemdraw/scripts/cdx.py py skill/chemdraw/assets/house-styles/jmed_chem/replica/jmed_chem-03/replay.py NEW_DIR
python skill/chemdraw/scripts/cdx.py render NEW_DIR/figure.cdxml
```

## Result

Two draws were run. The first used the default row budget of 504 pt and reported the drawing as 544 pt wide. The second raised `max_width` to 544 and cleared that warning. The second draw is the saved `brief.json`. It passed the layout and readback checks (3 structures matched, fragment round trip preserved). One warning remains (see Tool gaps).

## Convention table

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| compound labels bold (88, 92, TNG462) | bold | bold | yes |
| compound labels black | black | black | yes |
| step letters only, above the arrow (m, n) | "m, n" above the arrow | "m, n" above the arrow | yes |
| step count not shown | none | none | yes |
| reagents and conditions only in the footnote, not on the drawing | no reagents on the drawing; the crop has no footnote to check | no reagents on the drawing | no (footnote not in the crop; card conditions_split is "all_above", which contradicts the footnote rule) |
| yield placement and format (null) | none drawn | none drawn | yes |
| highlight_fill (null) | none | none | yes |
| Boc abbreviated | Boc | Boc | yes |
| inline_plus substrate layout (88 + 92) | 88 + 92 | 88 + 92 | yes |
| show_plus_sign | plus between partners | plus between partners | yes |
| reagent text colour black | no reagent text drawn in either image | none drawn | no (nothing to check) |
| plain solid arrow | plain, head style not checked at crop resolution | plain, head style not checked | no (card says filled triangular head; not verified) |
| Kekule aromatic rings | not checked at crop resolution | not checked at this resolution | no (not verified) |
| final compound labelled with its code name in bold (TNG462) | bold TNG462 | bold TNG462 | yes |
| fragment 88 coloured navy #1F1F5C in the last row (variation_color) | black (the crop has no coloured pixels at all) | black | no (the card's navy claim is wrong for this crop) |
| stereo wedges and hashes on 92 and TNG462 | drawn | not drawn | no |

Matched 10 of 16 on audit. The replicator claimed 14. Rows that are not matched: reagents in footnote (no footnote in the crop), reagent colour (no reagent text), plain arrow head and Kekule rings (not verified), navy fragment (the card is wrong for this crop), and stereo (not drawn).

## Differences from the paper

- Stereochemistry is missing. The paper draws the methyl and the aryl bond on the piperidine of 92 with wedge and hash marks, and the same ring in TNG462. The wedge and hash bonds are visible in the reference crop, so "could not be read" is not a valid reason. The replica is drawn without stereo, and no attempt to draw these bonds is recorded. The SMILES are therefore constitution-only and must not be taken as the drug's configuration.
- The other rows of Scheme 8 are not drawn, and neither is the Boc-protected amide between the two steps.
- Only the letter pair "m, n" is drawn. The paper's footnote reagents are not reproduced, as the card asks.
- Line weight and the bond-length to label-size ratio were not measured against the crop, so those are not claimed as matches.

## Tool gaps

- Fragment-level colour is not a tool gap for this case. The reference crop has no coloured pixels, so fragment 88 is black. The card's total_synthesis `variation_color` (#1F1F5C) is wrong for this crop and should not be applied here. The card needs correcting, not the tool. A fragment-colour capability may still be useful for other schemes, but it is not needed for this one.
- Two-stage arrow: "m, n" on one arrow stands for an amide coupling followed by Boc removal. The tool reports the step as unbalanced (it names C10H18O5 as missing) and draws nothing for it. The reference draws no by-products either, so the real gap is only the balance warning on a combined step.
- Row budget: `max_width` had to be raised to 544 pt in the brief. This is a brief parameter, not a missing capability, so it is listed here only for reference.
- Missed by the replicator: wedge and hash bonds on rings (stereo on 92 and TNG462). The replicator did not test whether the tool can draw them. This is the most important gap for this scheme and needs a check before it is recorded as a limit.
- Missed by the replicator: the card's `conditions_split` is "all_above", while its signature features say reagents go only in the footnote. This is a card inconsistency, not a tool gap.

## Audit

Audited against reference.png and rendered.png. The bottom labels (88, 92, TNG462) are bold and black in both images. The reference crop has no coloured pixels, so fragment 88 is black there, and the card's navy #1F1F5C does not match the crop. The table's yes rows for the labels, step letters, plus sign, Boc, inline layout, highlight and yield are supported. The reagent colour, Kekule, arrow-head and footnote rows were overclaimed and are now marked no. The stereo excuse is not supported because the wedge and hash bonds are visible in the reference. Corrected count: 10 of 16. Still open: whether the tool can draw ring wedge and hash bonds, and a card fix for the navy colour and the conditions_split conflict.
