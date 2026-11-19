# cell_press_chem: Figure 2A, synthesis of silicon(IV) complex 2 (reaction_scheme)

Source: K. Greb et al., "An isolable, crystalline complex of square-planar silicon(IV)", *Chem* 2021. DOI: [10.1016/j.chempr.2021.05.002](https://doi.org/10.1016/j.chempr.2021.05.002). Licence: CC BY 4.0. The reference crop (`reference.png`) is `evidence/cell_press_chem-02.png` from the house style card. The full-text XML used to check the chemistry is the PMC8367297 record (`D:\workspace\chemdraw-papers\house-cell_press_chem-4`).

Drawing style: the `cell_press_chem` house style (base preset `wiley`, bold compound labels, conditions above and below the arrow, yield on the conditions line as in the crop).

## Figure type and scope

Figure type: `reaction_scheme`. The replica reproduces Figure 2A only: the single arrow from the chlorido silicate [PPh4][1] to the neutral silane 2 with its reagent above the arrow and its conditions and by-products below. Panels B (crystal photograph) and C (X-ray structure) are not reproduced; the crop shows only part of panel A and B/C are outside the crop.

## Structures

| ID | Structure (SMILES in brief.json) | Check |
| --- | --- | --- |
| [PPh4][1] | `Cl[Si-]...` : meso-octaethylcalix[4]pyrrolato chlorido silicate(IV), anion; counterion [PPh4]+ written as the label text | formula C36H48ClN4Si-, RDKit parse ok |
| 2 | `[Si]...` : meso-octaethylcalix[4]pyrrolato silicon(IV), neutral, four Si-N bonds, no axial ligand | formula C36H48N4Si, RDKit parse ok; the paper calls 2 "the neutral silane" |

The crop cuts product 2 off at the right edge, so 2 was drawn from the paper text (neutral square-planar silane, meso-octaethylcalix[4]pyrrole ligand), not from the crop. The by-products NaCl and [PPh4][B(C6F5)4] are written as text lines below the arrow, as in the crop, and are not drawn as structures.

## Conditions and yield

The crop puts "1 eq. Na[B(C6F5)4]" above the arrow and "rt, CH2Cl2, 78 %", "- NaCl" and "- [PPh4][B(C6F5)4]" below. The replica does the same. The paper text describes two operations: metathesis of [PPh4][1] with NaB(C6F5)4 in CH2Cl2 gives the tetramer [Na]4[1]4, and stirring that tetramer in n-hexane for 24 h gives 2 in 78% yield. The figure merges these into one arrow; the replica follows the figure.

## Replay

```
python skill/chemdraw/scripts/cdx.py py skill/chemdraw/assets/house-styles/cell_press_chem/replica/cell_press_chem-02/replay.py NEW_DIR
```

`brief.json` is the final brief (third variant). `rendered.png` is that brief drawn with desktop ChemDraw (1200 px wide). `replay.py` was not run separately; it calls the same `draw_figure` as `cdx.py draw`, which was run on this brief.

## Convention check

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| compound labels bold (`compound_label_face`) | only the compound number is bold (`1` in `[PPh4][1]`, and `2`); `[PPh4]` is regular weight | the whole label `[PPh4][1]` is bold, because the house convention sets every run of a label bold | no (partial) |
| compound label colour black | black | black | yes |
| reagent text colour black | black | black | yes |
| yield format `{value}%` (card) | `78 %` with a space before the percent sign; the card's `{value}%` has no space, so card and crop disagree | `78 %` typed on the conditions line; the `yield` key was not used | no |
| yield placement (reaction_scheme: under the arrow) | yield on the same line as "rt, CH2Cl2" under the arrow | yield typed on that line; the tool cannot put it there (the `yield` key draws its own line) | no (visually similar, but typed text) |
| conditions split: reagent above, rt/solvent/yield below | matches | matches | yes |
| thin arrow (`arrow_style`, crops 02 and 03) | thin arrow with small head | thin arrow (wiley preset); the card's arrow-to-bond ratio was not measured | not verified |
| kekule aromatic rings (`aromatic_rings`) | pyrroles drawn with alternating double bonds | Kekule because the input SMILES is Kekule (no convention is applied by the tool); the left pyrrole is malformed (see Audit) | yes (from the input) |
| abbreviation `Ph` (`abbreviate_groups`) | no phenyl group is drawn as a structure; `PPh4` appears only as text | no phenyl group drawn; the tool abbreviated nothing | not applicable (was marked yes) |
| sans-serif (Arial) labels | Arial | Arial-like sans-serif | yes |
| bold panel letter "A" top left (reaction_scheme signature, crop 02) | bold "A" (B and C are bold too) | not drawn; `title` is accepted and silently ignored | no |
| Si label and Si-N bonds (evidence observation, crop 02) | only the Si label is magenta; the four Si-N bonds are black | Si label black; three Si-N bonds drawn dashed and one as a double line | no |
| components colour-coded red / green / blue (reaction_scheme signature, crop 01) | not in crop 02 | not applicable | n/a |
| new bond colour (`new_bond_color`) | null on the card; no formed bond in crop 02 | black | n/a |
| bond length / cap height 2.12 (`measured`) | not measurable at 258 px crop size | not measured | n/a |
| not on the card: free `+PPh4` text beside the anion; anion in square brackets with `−` outside | present | absent | no |

Corrected count: 5 of the 10 convention rows that could be checked match (label colour, reagent colour, conditions split, Kekule, Arial). Not matched: bold label, yield format, yield placement, panel letter, Si colour. The thin arrow is not verified and the `Ph` abbreviation does not apply. The earlier "8 of 11" cannot be reproduced from this table.

## Differences from the paper

- The bold panel letter "A" at top left is not drawn.
- Only the Si label is magenta in the paper; the four Si-N bonds are black. The replica draws Si black, with three Si-N bonds dashed and the left one as a double line. The paper's bonds are solid single bonds, so neither colour nor bond style matches.
- The chloride sits below-left of Si in the replica; in the crop it sits above-left of Si, joined to Si by a short bond. The replica shows no visible Si-Cl bond. The macrocycle is rotated relative to the crop.
- The layout check still flags two label clashes (fragments 1000 and 1198, Si/N and Cl/N labels near each other). The left pyrrole is malformed: the Si-N bond and a second ring bond cross the pyrrole nitrogen, so the ring does not read as a clean pyrrole.
- The paper shows the counterion as free `+PPh4` text beside the anion and draws the anion in square brackets with `−` outside. The replica has neither (see the convention table).
- In the paper only the compound number is bold; the replica bolds the whole label, including `[PPh4]`.
- Product 2 is drawn in full from the paper text; the crop shows only its left part.
- The step balance check flags the missing Cl (NaCl by-product) on every try. The by-products are shown as text, not drawn, and the check still reports them.
- Panels B and C (crystal photograph and X-ray structure) are not reproduced.
- The yield is typed as `78 %` on the conditions line. The reason given before was wrong: draw_figure does have a `yield` step key, which draws the yield on its own line under the arrow and applies the card's format (giving `78%`, no space). The typed text was used only because the crop shows `78 %`, so the card's format and the crop disagree.

## Tool gaps

- No panel-letter field: `title` is accepted but not drawn, so a bold "A" at the top left cannot be produced.
- No way to colour a specific atom or bond (here the Si label and its bonds). `new_bond_color` colours only bonds formed in the step, and `substrate_colors` colours a whole substrate. `atom_halos` exists but draws a halo around atoms, which is not a coloured label or bond.
- No way to declare an expected by-product in a step (NaCl, [PPh4][B(C6F5)4]). Naming a by-product as text does not satisfy the balance check, so the warning stays on every run.
- No coordinate or orientation control in the brief. RDKit lays out the calix[4]pyrrole around the hypervalent Si centre, and the result depends on SMILES atom order (try 2 versus try 3 changed the clashes). The chloride position (top in the crop) cannot be chosen.
- A render run takes about 4 to 5 minutes on this machine, and the draw_figure tool limit is 300 s. The try-3 combined draw and render run hit the limit and had to be split into a draw call and a separate `cdx.py render` call.
- No free-standing text: labels attach only to species and to the above and below condition lines, so the counterion `+PPh4` beside the anion cannot be drawn.
- No per-run label formatting: `compound_label_face` sets every run of a label, so `[PPh4]` cannot stay regular while `1` is bold.
- No bond-style control. The brief has no key for bond style, and the replica's Si-N bonds came out dashed and double. The draw report does not flag this, and the cause was not found in the renderer (its dative path applies only to explicit DATIVE bonds, and this SMILES has none).
- No charged-bracket option for ions. `ts_bracket` draws a square bracket with a custom superscript (`bracket_type`, `superscript`), so it might give the anion bracket with `−`, but it is documented for transition states and was not tested.
- `_validate` checks only top-level keys as far as read; a by-product key placed in a step would not be reported as unknown.

## Audit

Checked against `reference.png`, `rendered.png` (both zoomed), `brief.json`, the card's conventions and the code in `toolkit/cdxml_toolkit/mcp_runtime/figure_draw.py` and `figure_house.py`.

- Overclaims corrected above: "8 of 11" (now 5 of 10 checkable matches); compound labels bold (only the number is bold in the paper); `Ph` abbreviation (not applicable); the card's Si observation (only the label is magenta, not the bonds); yield reason (the `yield` key exists); "left Si-N bond runs through a pyrrole ring" (understated: the left pyrrole is malformed); missing counterion text, anion bracket and Si-Cl bond (not mentioned before).
- Gaps the replicator listed that hold: `title` is accepted and silently ignored; no by-product declaration; no coordinate control (species keys are id, smiles or name, label, ring_fills, atom_halos, ts_bracket); no per-atom or per-bond colour; no yield-on-conditions-line option.
- Gaps the replicator missed: `yield` key (see above), `atom_halos`, `ts_bracket` for the bracket, free text, per-run label formatting, bond style.
- Card issues (not edited, as only this file was changed): `yield_format` `{value}%` conflicts with the crop's `78 %`; the crop 02 observation of magenta bonds is wrong.
- Not verified here: the 4 to 5 minute render time and the 300 s limit, the arrow-to-bond ratio, line weights, and the label-clash lint (not rerun).
