# cell_press_chem-07 replica

## Source

- Citation: Goldup et al., Chem 2020, "Synthesis of a mechanically planar chiral rotaxane ligand for enantioselective catalysis". Figure 4A (catalytic cycle).
- DOI: 10.1016/j.chempr.2020.02.006
- Licence: CC BY 4.0 (from the house-style card).
- Evidence crop: `evidence/cell_press_chem-07.png` (copied as `reference.png`).

## Figure type

`catalytic_cycle` (card `figure_types.catalytic_cycle`; the card lists crop 07 as the full-cycle source).

## What is reproduced

The four-node catalytic cycle: [AuCu(6)]2+ to I (substrate 7 enters), I to II (rearrangement), II to III (addition of styrene 8, TS1), III to [AuCu(6)]2+ with release of 9 (cyclisation, TS2). Node labels I and II, step names, the catalyst label, and the arrangement of the nodes on a circle with an empty centre.

What is not reproduced:

- The catalyst is simplified. The paper draws the full Au/Cu rotaxane ligand (6) on every node. The replica uses the bare `[Au+]` with the paper's label `[AuCu(6)]2+`, so the ligand and the Cu centre are absent from the structures.
- Substrate 7, substrate 8 and product 9 are not drawn in the output file. The replica report lists them as missing from the saved file (readback mismatch). The step arrows show only the cycle nodes.
- Intermediate I is drawn as a sigma-acetylide (`CC(C)(C#[C][Au])OC(=O)c1ccccc1`). The paper shows a pi-complex of Au(I) with the terminal alkyne, which keeps the alkyne H. Because of this, steps 1 and 2 are flagged as not balancing (H), and nothing was added to the drawing.

## Structures used

| label in brief | SMILES | note |
| --- | --- | --- |
| Cat, label `[AuCu(6)]2+` | `[Au+]` | simplified catalyst (see above) |
| 7 | `C#CC(C)(C)OC(=O)c1ccccc1` | not drawn in the output file |
| 8 | `C=Cc1ccccc1` | styrene, not drawn in the output file |
| I | `CC(C)(C#[C][Au])OC(=O)c1ccccc1` | sigma-acetylide stand-in for the pi-complex |
| II | `CC(C)=C([CH]=[Au+])OC(=O)c1ccccc1` | gold carbene, read from the crop |
| III | `CC(C)=C(OC(=O)c1ccccc1)[CH]([Au])C[CH+]c1ccccc1` | read from the crop (Au on the carbon, benzylic cation), unlabelled as in the paper |
| 9 | `CC(C)=C(OC(=O)c1ccccc1)C1CC1c1ccccc1` | not drawn in the output file |

## Convention and signature table

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| cycle_shape: circle | four nodes on a circle | nodes placed around a circle but the figure reads as a rhombus with straight sides | no |
| cycle_arrow_color: #000000 | black cycle arrows | black arrows | yes |
| center_label: false (empty centre) | empty centre | empty centre | yes |
| step_names: true | step names beside each arrow | step names beside three of four arrows (rearrangement, addition of styrene (TS1), cyclisation (TS2)); the Cat to I arrow has none, and the paper's 7 arrow has none either; roman black, not red italic | no |
| intermediate_label_style: bold_roman | I and II bold, third node unlabelled | I and II bold roman, third node unlabelled | yes |
| signature: intermediates joined by thick black curved arrows | thick curved arrows | thin straight arrows (tool draws straight lines) | no |
| signature: step names red italics #CB181B, TS names bold | red italic step names, TS names red italic | black roman step names, TS names with subscript, no colour | no |
| signature: intermediates on a circle with an empty centre | yes | yes, with a diamond-like spacing | no |

Matched 3 of 8 after audit (the replicator claimed 4; the step_names row is demoted, see Audit).

Top-level scheme conventions visible in the crop:

| convention | paper | replica | match |
| --- | --- | --- | --- |
| compound_label_face: bold | bold I, II, [AuCu(6)]2+ | bold I, II, [AuCu(6)]2+ | yes |
| compound_label_color: #000000 | black labels | black labels | yes |
| reagent_text_color: #000000 | step names red (#CB181B) in the figure | black text | no |
| abbreviate_groups (Ph) | Ph and BzO | Ph contracted to a label; the benzoate is drawn as O, C=O and a Ph label, with no BzO | no |
| aromatic_rings: kekule | rings drawn with inner double bonds | no ring is drawn at all; every phenyl is a Ph label | no |

## Differences from the paper

- Catalyst: the Au/Cu rotaxane ligand is replaced by a bare `[Au+]`. The paper's structures are much larger and the nodes differ in size.
- Missing structures: 7, 8 and 9 are absent from the output (readback mismatch, see Tool gaps).
- Arrows: straight thin arrows instead of thick curved arrows along the circle.
- Colour: no red step names, no red italic TS names, no orange Au or blue Cu, no green/blue fragment colours.
- Text: step names in roman, TS labels with subscript numerals (TS1, TS2), not bold italic red.
- Layout: the replica is 460 pt wide per the run report (not checkable from this folder, which holds no figure.cdxml or validation.json). The brief sets max_width 504 pt; no 427 pt budget exists in the toolkit code, so the "above budget" statement is unsupported.
- Intermediate I: sigma-acetylide instead of the pi-complex; H balance warnings follow.
- Rendering: the first run took 290 s and the second run exceeded 300 s; the third run succeeded. The render used the desktop ChemDraw path.

## Tool gaps

- Curved arrows along the cycle circumference: the catalytic-cycle layout draws straight arrows; the brief has no option for the curved thick cycle arrows.
- Entering and leaving reactants (7, 8 and product 9 on radial in/out arrows): the cause is not a readback bug. The cycle layout (renderer.py `_layout_catalytic_cycle`) places only `substrates[0]` of each step as a ring node, draws chord arrows between ring nodes and radial text only; there is no code for second substrates, products or radial in/out arrows. It does this silently.
- Step-name style: no brief field for step-name colour or italic style, or for bold TS names; these are guidance only (skipped).
- Metal pi-complexes: no way to write an Au(I)-alkyne pi-complex (dative bond to a triple bond fails RDKit valence), so the alkyne intermediate has to be a sigma-acetylide stand-in.
- Large catalysts: the rotaxane ligand is out of scope for SMILES input; the replica needs a placeholder structure with a label.
- Documentation mismatch: `references/scheme-drawing.md` (line 40) mentions `cycle_radius` (default 120 pt) and curved arrows along the circumference. The draw_figure docstring does not mention cycle_radius, the brief rejects it as an unknown key, and the code sets the radius to max(90, 32 x steps) x gap_scale (128 pt for four steps) with straight chord arrows.
- Render time: the render path timed out twice in this run (290 s and more than 300 s) before succeeding on a third try.

## Audit

Checked against reference.png, rendered.png, the card (cell_press_chem.json) and the toolkit code (renderer.py `_layout_catalytic_cycle`, figure_draw.py, figure_house.py, house_styles.py).

- Count: 3 of 8 in the convention table (cycle_arrow_color, center_label, intermediate_label_style) and 2 of 5 in the scheme table (compound_label_face, compound_label_color). The replicator claimed 4 of 8. step_names is demoted: the names sit beside three of four arrows, and their style differs.
- Only `cycle_arrow_color` is applied to catalytic cycles (`APPLIED_FIGURE_CONVENTIONS`). center_label, step_names, intermediate_label_style and cycle_shape are reported as skipped guidance, so the replica's match on those rows comes from the layout and brief text, not from the house convention. The I and II stems measure about 4 px on an 18 px cap height, which reads as bold; that is a visual match only.
- Ring positions are fixed at -90 degrees plus 360/n steps, so four nodes always sit at top, right, bottom and left: a diamond, not a circle.
- Not checkable from this folder: there is no figure.cdxml, validation.json or render log, so the run times, the 460 pt width, the H-balance warnings and the readback result are unverified.
- Toolkit documentation overclaims: `references/scheme-drawing.md` line 40 promises curved arrows along the circumference and a cycle_radius option. The code draws straight chords and has neither.

Tool gaps the replicator missed:

1. Silent ring-node choice: each step's first listed substrate becomes its ring node. Step 1 therefore draws the catalyst Au+ as a node, and the brief order decides which species is drawn, with no warning.
2. No cycle shape or start-angle control, so a four-node cycle can only be a diamond.
3. No weight or curvature option for cycle arrows; `curved_arrow_weight` exists only for mechanisms.
4. BzO cannot be contracted: `ABBREVIATIONS` has no benzoyloxy entry and the card's abbreviate_groups lists only Ph, OMe, tBu, CF3 and CN.
5. No step-name colour, italic or bold for catalytic cycles, because the tool applies only cycle_arrow_color to them.
