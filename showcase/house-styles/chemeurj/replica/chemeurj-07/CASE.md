# chemeurj-07: Au(I)/Au(III) catalytic cycle, Scheme 1 (Bourissou et al. 2022)

Source: Bourissou et al., *Chem. Eur. J.* 2022, "Mechanistic insights about the ligand-enabled oxy-arylation/vinylation of alkenes via Au(I)/Au(III) catalysis". DOI [10.1002/chem.202202110](https://doi.org/10.1002/chem.202202110). Scheme 1, evidence crop `evidence/chemeurj-07.png`. Licence: CC BY 4.0 (from the house-style card).

Figure type: `catalytic_cycle` (house style `chemeurj`, base preset `wiley`).

Drawing style: the `chemeurj` house style in `brief.json`, with `"layout": "catalytic-cycle"`.

## What is reproduced

The five-step cycle for R = Ph (compound **2**) with pent-4-en-1-ol:

1. `cat` + PhI, oxidative addition, to the Au(III) species `OA`.
2. `OA` + Ag+ (iodide abstraction) to `2` (bold label).
3. `2` + alkenol, coordination, to the alkene complex `Pi`.
4. `Pi` to `Cyc` (pi-activation, anti-addition: the ring oxygen adds to the internal alkene carbon).
5. `Cyc` to `cat` + 2-benzyltetrahydrofuran (reductive elimination).

Step names are drawn as plain black text beside the arrows. The R = vinyl variant (**2v**) and the generic R of the crop are not drawn. The incoming and departing species are not drawn as structures (see Tool gaps).

Tries: two. Try 1 gave the cycle without reagent text. Try 2 adds `PhI`, `Ag+`, `alkenol` and the product name as text on the steps, because the tool does not draw the radial species. `rendered.png` is the try 2 render. Both tries have readback `mismatch` (four species missing) and `checks_passed: false`.

## Structures

Read by eye from the crop (OCSR not run). The ligand is 2-(di-1-adamantylphosphino)-N,N-dimethylaniline, drawn as P and N chelating Au. The crop writes it as `Ad2P` and `(P,N)`. Alkenol is pent-4-en-1-ol: the chain and the five-membered ring product in the crop both fit this. The crop's generic R is replaced by Ph, the compound-2 case. Byproducts AgI and H+ are not drawn, as in the crop. The brief's warnings name them.

Per-step atom balance (tool report): step 1 and step 3 and step 5 balance; step 2 lacks AgI and step 4 lacks H, both expected.

## Convention table

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| `cycle_shape: circle` | nodes on a circle, chords drawn as arcs | nodes on a regular pentagon, straight chords | no |
| `cycle_arrow_color: #000000` | thin black arcs | black straight chords (colour only; the shape is the row above) | yes |
| `curved_arrow_color: #000000` | black curved arrows (cycle arcs, incoming and outgoing arrows) | no curved arrows drawn | no |
| `catalyst_color: null` | no colour | no colour | yes |
| `center_label: null` | no centre label; catalyst box in the centre | no centre box | yes for the label, no for the box |
| `intermediate_label_style` (notes: bold compound numbers) | bold **2**; **2v** with an "R = Ph / R = vinyl" legend | bold **2**; **2v** and the legend omitted | yes for the bold label; legend missing |
| signature: black arcs around a circle | arcs | straight chords | no |
| signature: incoming and leaving species on short curved arrows touching the arc | R–I, Ag+, alkenol in; product out | none drawn (text only in try 2) | no |
| signature: framed catalyst box with black outline | black rounded frame at centre | no frame | no |
| `compound_label_face: bold` | bold | bold | yes |
| `compound_label_color: #000000` | black | black | yes |
| label font Arial | Arial-like sans face | not inspected: no figure.cdxml in the case folder; toolkit default is Arial | no (unverified) |
| `aromatic_rings: kekule` | kekule benzene rings | kekule | yes |
| `highlight_fill` (none in crop 07) | no fill | no fill | yes |
| `arrow_style: plain` | plain arrows | plain reaction arrows (dative bonds carry arrowheads, see Differences) | yes |
| `reagent_text_color: #000000` | black step names; reagent names alkenol (blue) and R–I (red) | all text black, including alkenol and PhI | no |
| `new_bond_color: null` | no marked bond | none | yes (null) |
| `substrate_colors` (top level null) | red R–I and blue alkenol, blue carried into the THF ring | black throughout | no |
| palette: navy #004080, blue #0080C0, maroon, purple | pure red and pure blue in crop 07 | black throughout | no |
| `abbreviate_groups` (Ph) | only "R" and "Ph" in the caption; no Ph drawn | Ph drawn as a label on Au | n/a |
| `show_plus_sign: true` | circled plus charges (⊕) on each Au and on Ag | plain "+" text; no circled charges | no |
| ligand abbreviation `Ad2P`, `(P,N)Au+` on nodes | abbreviated node labels, full ligand only in centre | full adamantyl cages on every node | no |

Counts: the first pass claimed 10 of the 15 counted rows matched. The audit gives 7 of 15: `curved_arrow_color`, `reagent_text_color` and the label font are now no. The 15 counted rows are the non-null card values for this figure type and the visible top-level conventions (cycle shape, cycle and curved arrow colour, intermediate label, three catalytic-cycle signature features, compound label face and colour, font, kekule rings, highlight fill, arrow style, reagent text colour, palette). Rows with a null card value (`catalyst_color`, `center_label`, `new_bond_color`, `substrate_colors`) and rows marked n/a (`abbreviate_groups`, `show_plus_sign`) are listed for completeness and not counted.

## Differences from the paper

- Layout: the paper draws a circle with arc arrows. The replica draws a pentagon with straight chords.
- Nodes: the paper uses `(P,N)Au+` labels, with the ligand only in the centre box. The replica draws the full ligand on every node, which dominates the figure.
- Coordination bonds: the crop draws Au–P and Au–N as plain lines. The replica uses dative SMILES, which ChemDraw draws with arrowheads.
- Labels: "Au+" overlaps "Ph" in the oxidative addition node and "Au2+" overlaps "Ph" in node 2. The same Ph/Au overlap also appears in the Pi and Cyc nodes (see Audit).
- Incoming and leaving species: PhI, Ag+, the alkenol and the product are missing from the drawing as structures. The paper draws them on radial arrows. Try 2 gives the names as step text.
- Colour: no red or blue for the incoming partners, and no blue carried into the THF product.
- Stereo: the crop marks the THF C2 with a wedge or hash bond in the product and in the left intermediate. The replica has no stereo. The configuration is not stated in the crop, and the ligand is achiral, so none was invented.
- Step names: the crop places oxidative addition, coordination, π-activation and reductive elimination inside the circle, and alkenol outside it (read from the crop). The replica places the first four outside and alkenol inside, so coordination and alkenol are swapped relative to the paper. The cause is the brief assignment (see Tool gaps).
- Compound 2v and the R = vinyl series are not drawn.

## Tool gaps

- Second substrates (PhI, Ag+, alkenol) and the non-ring product (2-benzyltetrahydrofuran) are never drawn. `_layout_catalytic_cycle` in `toolkit/cdxml_toolkit/render/renderer.py` takes only `step.substrates[0]` of each step as a ring node. Each step's first product appears as the next ring node, so only the non-ring product is missing. Readback reports the missing species. `references/scheme-drawing.md` (line 40) describes curved arrows along the circumference, radial in and out arrows and a `cycle_radius` option. None of these are implemented: no `cycle_radius` key is read anywhere in the toolkit.
- Cycle arrows are straight chords between node boxes. Arc arrows along the circumference are not available. `kind: "mechanism"` has curved arrows, but they are electron-pushing moves between atoms of substrates in rows, not free arcs, so it cannot draw the cycle.
- Nodes sit on a regular n-gon with radius max(90, 32n) pt, so five steps give a pentagon, not a circle. No brief key sets the radius (`gap_scale` is internal and changes only on re-layout).
- No centre element: no catalyst frame or centre label option for a cycle.
- House-card conventions are mostly not drawn for cycles. `figure_house.apply_figure_type_conventions` applies only `cycle_arrow_color` for `catalytic_cycle`. The other card conventions (`cycle_shape`, `catalyst_color`, `center_label`, `step_names`, `intermediate_label_style`, `curved_arrow_color`, `highlight_fill`) are reported as skipped guidance. The "yes" rows for curved arrows and label style therefore did not come from the tool.
- Colour: species decorations (`ring_fills`, `atom_halos`) are applied in every layout (`_apply_decorations` in `toolkit/cdxml_toolkit/mcp_runtime/figure_draw.py`), so a cycle node can get a filled ring or a halo. They do not colour atoms or bonds, and they cannot reach text-only species (PhI, Ag+, alkenol) or the non-ring product. `substrate_colors` is null on this card and not applied to cycles.
- Charges and dative bonds: `formal_charge_style: "circled"` and `dative_bond_style: "line"` appear in `toolkit/cdxml_toolkit/publication/house_styles.py` as allowed values, but no drawing code reads them. The circled-plus charges and plain-line coordination bonds of the crop are not available. Dative SMILES bonds are drawn with arrowheads. Writing the bond as a plain single bond with explicit charges was not tried.
- `abbreviate_groups` only takes the fixed `ABBREVIATIONS` table in `publication/house_styles.py`. It has no Ad, Ad2P or (P,N) entry, so catalytic nodes show full adamantyl cages.
- Step-name placement is radial and fixed by side, not by screen position. In `_layout_catalytic_cycle`, `above` lines go radially outside each arrow and `below` lines go radially inside, falling back to outside when the interior is tight (`_place_radial_text`). Inside placement therefore exists: put the name in `below`. The replica's coordination and alkenol swap follows from the brief, which put coordination in `above` and alkenol in `below`. Not tested: a brief with oxidative addition, π-activation and reductive elimination in `below`, alkenol in `above` and coordination in `below` would be expected to match the crop's placement.
- Lint: `figure_lint.lint_cdxml` checks each fragment, with its labels in its box, against the other objects. It does not check labels against each other inside one fragment, so the Ph and Au overlaps inside each node pass. No text-on-structure check exists for cycle nodes.
- Timing: `draw_figure` takes about 160 s without a render. A `--render` call did not finish within a 300 s foreground call and succeeded when run in the background (about 5 min). Not re-measured in the audit.

## Replay

```
python skill/chemdraw/scripts/cdx.py py skill/chemdraw/assets/house-styles/chemeurj/replica/chemeurj-07/replay.py NEW_DIR
python skill/chemdraw/scripts/cdx.py render NEW_DIR/figure.cdxml
```

`replay.py` runs `draw_figure` on `brief.json` without network access. The brief is the try 2 brief. It was run through `cdx.py draw` with `--render`, not through `replay.py`.

## Audit

Audited on 2026-11-07 from reference.png, rendered.png, brief.json, the chemeurj card and the toolkit code named above. Only this file was changed.

- Overclaim, curved arrows: the table matched curved_arrow_color because the colour is black on black. The replica draws no curved arrows, so the row is now no. The tool also skips this convention for cycles.
- Overclaim, reagent text colour: the crop colours alkenol blue and R–I red. All replica text is black. The row is now no.
- Overclaim, label font: the case folder has no figure.cdxml, validation.json or other output, so the Arial face was not checked. The row is now no (unverified).
- Overclaim, plus sign: the crop has circled plus charges on the Au centres and on Ag. The replica uses plain "+". The row is now no. Drawing circled charges for cycles is not implemented.
- Overclaim, overlaps: in rendered.png, Ph touches Au in four nodes (oxidative addition, node 2, Pi and Cyc), not two. Read at normal size, not measured.
- Overclaim, step names: "no option places them inside the circle" is wrong, because `below` lines go inside. The replica's "alkenol" sits inside the ring, so "step names sit outside each arrow" is also wrong for that line.
- Overclaim, species drawing: first products are drawn as the next ring node. Only the non-ring product is missing.
- Overclaim, colour: species decorations exist (ring_fills, atom_halos). They do not colour bonds or atoms, but they are not "no per-fragment colour" either.
- Not verified: the 160 s and 5 min timings, the readback and checks_passed results, and the per-step atom balance. The case folder has no validation.json to check them.
- Corrected count: 7 of 15 counted rows match, not 10.
- Missed tool gaps: the house-card conventions for cycles are skipped by the tool; circled charges and plain-line dative bonds are vocabulary only; `below` already places text inside the ring, so step-name placement is set by brief assignment.
