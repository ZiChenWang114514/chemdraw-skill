# Studer et al., Nature 2023: phosphine-mediated water activation, radical mechanism (Fig. 2b, top row)

Source: Studer et al., *Nature* **2023** (Photocatalytic phosphine-mediated water activation for radical hydrogenation). DOI: [10.1038/s41586-023-06141-1](https://doi.org/10.1038/s41586-023-06141-1). Licence: CC BY 4.0. The reference crop `reference.png` is reproduced under that licence.

House style: `studer_group` (`skill/chemdraw/assets/house-styles/studer_group/`), figure type `mechanism`, base preset `nature`.

## What is reproduced

Only the first two steps of the top row of Fig. 2b:

1. Ar3P + Ir(III) gives the phosphine radical cation Ar3P+• and Ir(II) (one-electron oxidation).
2. The radical cation adds water through the oxygen lone pair, giving the hydrated phosphoranyl species [Ar3P(OH2)]+•.

Ar is drawn as phenyl (`P(c1ccccc1)(c1ccccc1)c1ccccc1`), because the tools take SMILES and have no generic Ar label. The Ir centres are drawn as the bare ions `[Ir+3]` and `[Ir+2]`.

The rest of the crop is not drawn: the proton transfer to Ar3P (giving Ar3PH+ and the phosphoranyl radical bearing OH), the hydrogen transfer from the O-H group to the allyl alkene, the alkyl radical, the Ar3P=O by-product, the thiol (ArSH / ArS•) hydrogen-atom-transfer cycle, and the bottom-left saturated product. Each of these needs a hydrogen to be a move end point, which the tool cannot address (see Tool gaps).

## Replay

```
python skill/chemdraw/scripts/cdx.py py skill/chemdraw/assets/house-styles/studer_group/replica/studer_group-02/replay.py NEW_DIR
python skill/chemdraw/scripts/cdx.py render NEW_DIR/figure.cdxml
```

`replay.py` runs `draw_figure` on `brief.json` offline and writes `figure.cdxml` and `validation.json`. `rendered.png` is the native ChemDraw render from the `cdx.py draw --render` run that produced this replica.

## Convention check

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| curved arrows black (`curved_arrow_color`) | black | black | yes (applied by the tool) |
| curved arrows as thin as bonds (`curved_arrow_weight` bond) | thin | thin | yes (applied by the tool; 0.6 pt, the bond default) |
| lone pairs not drawn (`show_lone_pairs` false) | none drawn | none drawn | yes, by absence (not enforced by the tool) |
| formal charges plain (`formal_charge_style` plain) | plain + on P and O | plain + on P and O | yes in the render (not enforced by the tool) |
| intermediates labelled with bold capital letters (`intermediate_label_style` bold_letter) | no letters in this crop | no letters | n/a (neither side has letters) |
| electron transfer as a thin curved arrow over a straight arrow, Ir(III) to Ir(II) | curved arrow from Ir(III) to Ir(II) over the straight arrow | straight arrow present, curved arrow runs from the P atom to Ir3+ | no |
| radical cation written with plain + and a dot above P | `+•` above P | `+` only, no dot in the native render | no |
| radical as a single dot on carbon; transferred H in red #FF0000 | red H labels on the bottom row | not drawn (bottom row absent) | n/a (bottom row not replicated) |
| transferred H and its new bond in red #FF0000 (card: crop 02) | red H labels, bonds black | not drawn | n/a (bottom row not replicated; the card's bond claim is wrong) |
| plain reaction arrow (`arrow_style` plain) | plain straight arrow | plain straight arrow | not verified (arrow_style is not checked for mechanisms) |
| plus sign between substrates (`show_plus_sign` true) | no plus between Ar3P and Ir(III); "+ Ar3P" only as a reagent above the arrow | plus between the substrates of both steps | no |

Matched 4 of 11 conventions after audit (the earlier count of 5 included the arrow-style row, which is not verified; see Audit).

## Differences from the paper

- Scope: two steps of the top row only. The bottom row, the proton and hydrogen transfers, the alkyl radical and the product are missing.
- Ar groups: phenyl instead of the generic Ar label.
- Oxidation states: written as charges (Ir3+, Ir2+), not as Ir(III) and Ir(II).
- Electron transfer arrow: drawn from the phosphorus lone pair to Ir3+, with a warning that P has no unpaired electron for a one-electron arrow. The paper's arrow runs from Ir(III) to Ir(II).
- Layout: step 2 has two substrates, so it starts a new row and repeats the radical cation (the paper draws one row). The arrow of step 2 crosses a phenyl ring of the radical cation (tool relayout reports the crossing).
- Radical cation: the radical dot is not visible in the native render.
- Card claims that disagree with this crop are recorded in the report and not fixed: crop 02 has no intermediate letters, and its transferred H is red but its bonds are black.

## Tool gaps

- Hydrogen atoms cannot be move end points: hydrogens are not numbered and a bond to an implicit H cannot be given as `bond [i, j]`. Proton transfers (Ar3P + H+ from the O-H), hydrogen-atom transfers from O-H to an alkene and from a thiol to a radical cannot be drawn with `moves`.
- A one-electron arrow must start from a radical centre. Single-electron oxidation of a lone pair (Ar3P to Ar3P+•) and an arrow from a metal ion are either flagged or not expressible. No electron-source species type exists for Ir(III) to Ir(II).
- A step needs `moves` and only substrates may be move ends. A co-reagent written above the arrow cannot be a move source, so a reagent-driven step such as the addition of H2O is split into a new row.
- The radical dot on a phosphorus radical cation or phosphoranyl radical is not visible in the native render, although the CDXML carries `Radical="Doublet"`.
- No generic group label (Ar) is available for a structure; only SMILES.
- No per-atom colour on the species (red H, blue X) and no mechanism equivalent of `new_bond_color`.
- No bracket or lower-row layout for a closed hydrogen-atom-transfer cycle with two-electron arrows between ArSH and ArS•.
- No control over arrow paths (the step-2 arrow crosses a ring; the tool only widens gaps and raises loops).

## Audit

Checked against both images and an offline replay of `brief.json`, whose output was kept outside this folder.

- Curved arrow colour and weight are set by the tool from the house style (`mechanism.curved_arrow_color`, `mechanism.curved_arrow_weight`), not by a drawing choice. Both come out at 0.6 pt, the document's default bond width.
- Lone pairs and formal-charge style are not applied by the tool; the replay's style report lists them as not drawn. Those rows hold only because nothing extra is drawn.
- `arrow_style` is not a mechanism convention, and the mechanism path does not check it. The brief's `solid` arrow was not shown to equal the house `plain`, so that row is not verified.
- The layout bullet says the tool reports the step-2 crossing. It does not: the replay gives `arrows.crossings` empty, `lint.issues` empty and `relayout` null. The step-1 arrow also crosses the top phenyl ring of Ar3P in the render.
- "Only SMILES" is incomplete. Species also take `name` and `label`; the label is a caption under the structure, not a group label. Abbreviations apply to schemes only (the style report says so), so the house `Ph` contraction is unavailable here.
- A step with no moves is refused, so the paper's H2O addition (no curved arrow, H2O above the arrow) cannot be drawn. The split into a new row follows from making H2O a substrate.
- Corrected count: 4 of 11 (curved colour, curved weight, lone pairs, charges). The arrow-style row is not verified.

Mismatches inside the two drawn steps that the table does not list:

- H2O is a substrate with a plus sign and its own curved arrow. The paper has it as a reagent above the arrow, with the water hydrogens in red.
- Ir(III) and Ir(II) are charges (Ir3+, Ir2+), not oxidation states.
- Both curved arrows cross phenyl rings. The crossing check tests distance to atom centres only, so ring crossings are not flagged.
- The arrow is about 5 bond lengths (estimated from the render: about 223 px against a ring edge of about 43 px). The tool sets a minimum of 5.0 bond lengths; the house value is 6.9.
- The paper has one row. Here any step with two substrates starts a new row, and the house substrate layout applies to schemes only.

Tool gaps not listed above:

- No colour key anywhere in the mechanism brief, so red H, red reagent text and blue X cannot be set.
- No proportion or font keys (arrow-to-bond ratio, line weight, label font and size). The brief takes only a preset `style`.
- No abbreviation of mechanism species (Ph and the other house groups).
- No superscript oxidation state. A species label can carry text such as Ir(III), but it sits under the structure.
- No radical input: species take SMILES, name or label only. The render shows no radical dot, while the CDXML carries four `Radical="Doublet"` attributes.
