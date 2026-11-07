# Maynard et al.: ATRP from an aryl iodide initiator and gold oxidative addition (Figure 2a)

Source: Maynard et al., "Biomolecule-polymer conjugates synthesized by a combination of organometallic bioconjugation and atom transfer radical polymerization", *Polym. Chem.* **2026**. DOI: [10.1039/d6py00714g](https://doi.org/10.1039/d6py00714g).

Licence: CC BY 3.0 (per the house-style card). Reference crop reproduced under that licence.

House style: `polymer_chemistry` (base preset RSC). Figure type: `reaction_scheme`; the crop also shows polymer conventions (repeat bracket, end groups, R list).

## What is reproduced

The two-step scheme in Figure 2a: (1) ATRP of a methacrylate (CuCl, Bpy, MeOH, 25 °C, 20 min) from an aryl iodide initiator with a tertiary C-Br; (2) oxidative addition of the aryl iodide end group to MeDalPhos·AuCl with AgSbF6 in DCM, giving the cationic Au(III) polymer reagent with an SbF6 counterion. Both steps are drawn in one row (brief `max_width` 1400).

Choices made for the replica:

- Monomer R: the R box lists three options. 2-hydroxyethyl methacrylate (`C=C(C)C(=O)OCCO`) is used; the box is not drawn.
- Polymer: an explicit three-unit chain with the initiator fragment at one end and Br at the other.
- Monomer and MeDalPhos·AuCl are drawn as in-line substrates. The paper draws them above the arrows.
- Au(III) product: P->Au and N->Au are dative; Au-Cl and Au-aryl are plain bonds; N is drawn as N+ and the complex is +1, with SbF6- as a separate product.
- Structures were read from the crop and the paper text. No OCSR was run. The MeDalPhos and Au(III) SMILES were checked with RDKit (formula, charge, dative bonds parse).

| Structure | SMILES in brief.json |
| --- | --- |
| Initiator | `Ic1ccc(OCCNC(=O)C(C)(C)Br)cc1` |
| Monomer (R = CH2CH2OH) | `C=C(C)C(=O)OCCO` |
| Aryl iodide polymer (3 units) | `Ic1ccc(OCCNC(=O)C(C)(C)CC(C)(C(=O)OCCO)CC(C)(C(=O)OCCO)CC(C)(C(=O)OCCO)Br)cc1` |
| MeDalPhos·AuCl | `CN(C)c1ccccc1P(C23CC4CC(CC(C4)C2)C3)(C56CC7CC(CC(C7)C5)C6)->[Au]Cl` |
| Au(III) polymer cation | `C[N+]1(C)c2ccccc2P(C34CC5CC(CC(C5)C3)C4)(C67CC8CC(CC(C8)C6)C7)->[Au]1(Cl)c9ccc(OCCNC(=O)C(C)(C)CC(C)(C(=O)OCCO)CC(C)(C(=O)OCCO)CC(C)(C(=O)OCCO)Br)cc9` |
| SbF6- | `F[Sb-](F)(F)(F)(F)F` |

## Convention table

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| conditions_split: reagents above, solvent and temperature below | CuCl, Bpy and AgSbF6 above; MeOH, 25 °C, 20 min and DCM below | same split | yes |
| substrate_layout: inline_plus (card) | monomer and MeDalPhos·AuCl drawn above the arrows, not in line | in line with plus signs | no |
| aromatic_rings: kekule | kekule rings | kekule rings (not verified at render size) | no |
| reagent_text_color #000000 | black text | black text | yes |
| arrow_style: plain | plain arrows | plain arrows | yes |
| show_plus_sign: true (card) | no plus signs between reactants in this crop | plus signs drawn between reactants | no |
| yield placement and format: none on polymerisation schemes | no yields | no yields | yes |
| compound labels: none in this crop | no compound numbers | none | yes |
| polymer: repeat unit in round brackets with subscript n | round bracket with n at lower right | explicit trimer, no bracket, no n | no |
| polymer: end groups drawn explicitly | initiator fragment and Br | initiator fragment and Br | yes |
| polymer: R options as wavy-bond list, boxed | box with three R options | not drawn | no |
| reaction_scheme: catalyst structures above the arrow, separated by a slash | MeDalPhos·AuCl drawn above the second arrow | drawn in line as a substrate | no |
| reaction_scheme: bold panel letter a) | bold a) at top left | not drawn (title "a)" did not render) | no |

Matched: 6 of 13 conventions after audit (the first draft claimed 7; see Audit). The abbreviate_groups convention (CF3) is not present in this crop and is not counted.

## Brief iterations

1. `max_width` 900: the scheme laid out sequentially in two rows (step 2 under step 1). Checks passed; balance warnings for C12H20O6 (step 1) and F6Sb (step 2).
2. `max_width` 1400 and `title` "a)" (final, saved as brief.json): one row, readback matched (6 structures), checks passed. The title did not produce a visible "a)" label. Further tries would change only `max_width`, so the brief was not changed again.

## Differences from the paper

- Layout: the paper is one row with the monomer and MeDalPhos·AuCl above the arrows; the replica is one row with the monomer and gold complex as in-line substrates.
- Plus signs: the paper has none in this scheme; the replica draws plus signs between the substrates.
- Polymer: the paper shows one repeat unit in round brackets with n at the lower right and a boxed R list; the replica shows an explicit trimer with no brackets, no n, and no R box.
- Monomer R: the paper leaves R general; the replica uses HEMA.
- Panel letter: the paper has a bold a) at top left; the replica has none.
- Charges: the paper shows a circled plus and a circled minus; the replica shows N+ and Sb- without circles.
- Mass balance: step 1 lacks the two monomer units implied by the trimer (C12H20O6 warning); step 2 lacks the Ag/I by-product and the F6Sb from AgSbF6 (F6Sb warning). These are expected from the representation and were not corrected.
- Compound labels: none in the paper crop and none in the replica.

## Tool gaps

- No bracketed repeat unit with a subscript n or DP in `draw_figure`; repeat units must be written as explicit oligomers.
- No structures above or below the arrow: `above` and `below` take text lines only, so the monomer and the MeDalPhos·AuCl reagent cannot sit above the arrow as in the paper.
- No R-group option box and no wavy-bond substituent list.
- No panel-letter support: `title` does not render a visible bold "a)" label.
- No circled charge symbols on ions.
- No row control: `max_width` changed the layout from two rows to one row here, but there is no explicit steps-per-row option in `draw_figure`.

## Replay

```
python skill/chemdraw/scripts/cdx.py py skill/chemdraw/assets/house-styles/polymer_chemistry/replica/polymer_chemistry-06/replay.py NEW_DIR
python skill/chemdraw/scripts/cdx.py render NEW_DIR/figure.cdxml
```

`replay.py` runs `draw_figure` on `brief.json` offline and writes `figure.cdxml` and `validation.json`. `rendered.png` is the second-try rendering (downscaled to 1200 px wide); `reference.png` is the crop.

## Audit

Checked against reference.png, rendered.png (downscaled, so line weight, label size and ring bond pattern cannot be measured reliably), brief.json and the polymer_chemistry card.

Overclaims found:

- aromatic_rings kekule was marked "yes" without evidence. The rings in rendered.png could not be confirmed as Kekule at this size, so the row is now "no (not verified)" and the count drops from 7 to 6.
- The Choices bullet says P->Au and N->Au are both dative. In the Au(III) cation SMILES in brief.json the N to Au link is a plain bond (the ring-closure digit has no "->"); only P->Au is dative. The Choices bullet was not edited and still states the wrong bonding, so it should be corrected to match brief.json.

Rows that held up on inspection: conditions split (CuCl, Bpy and AgSbF6 above; MeOH, 25 °C, 20 min and DCM below), black reagent text, plain arrows, no yields, no compound labels, explicit initiator and Br end groups. The "no" rows are correct, including plus signs, which the paper does not draw in this scheme and the replica does.

Not checked, so not counted as matched: arrow length (card: 7 bond lengths; paper 155 px over 22 px bond), line width (card: 0.09 bond length), reagent label face (card: Arial) and the proportion of reagent text height to bond length (card: 2.4). Neither image is at a resolution that settles these.

Tool gaps the replicator missed:

- CASE.md does not say whether draw_figure can set arrow length to about 7 bond lengths or line width to about 0.09 bond length. The card requires both and the replica did not test either.
- Subscripts in reagent text (AgSbF6 in the paper) were not tested. The replica writes AgSbF6 and CuCl as plain text, and this is not established as either supported or missing.
- max_width changed the layout from two rows to one (900 gave two, 1400 gave one). That is row control by width only, so the replicator's gap about steps-per-row is accurate.
