# JACS Au: photoredox and Co-catalyzed cycles, Figure 5A (Gilmour et al., 2025)

Source: Gilmour et al., "Chloroalkylation of unactivated alkenes via a cobalt-mediated radical ligand transfer", *JACS Au* **2025**. DOI: [10.1021/jacsau.5c01211](https://doi.org/10.1021/jacsau.5c01211). Licence: CC BY 4.0 (from the house style card `jacs_au`, evidence crop `jacs_au-08`, Figure 5A-C).

Drawing style: the `jacs_au` house style card, `catalytic_cycle` section, with the top-level conventions for compound labels, plain arrows and reagent text. Base preset: acs1996.

## What is reproduced

Only the photoredox loop of panel A (the left cycle): Ir(III) to Ir(III)* under blue LEDs, Ir(III)* to Ir(IV) with the FG-CH2Br / Ag+ step, and Ir(IV) back to Ir(III) with the Co-catalyzed turnover named as text. The metal centres are the crop's oxidation-state labels. They are drawn as bare `[Ir]` atoms (no ligands, no charge), because the crop shows no structure for them. The label carries the oxidation state. The Co cycle (LnCo^n+1 Cl, LnCo^n, LiCl, RLT), the radical chain, the ATRA product and the substrate structures are not drawn.

The brief is `brief.json` (layout `catalytic-cycle`, three species, three steps). `rendered.png` is the ChemDraw render of the final brief (1200 px wide, downscaled from the 1288 px render).

## Replay

```
python skill/chemdraw/scripts/cdx.py py skill/chemdraw/assets/house-styles/jacs_au/replica/jacs_au-08/replay.py NEW_DIR
python skill/chemdraw/scripts/cdx.py render NEW_DIR/figure.cdxml
```

`replay.py` runs `draw_figure` on `brief.json` offline and writes `figure.cdxml` and `validation.json` into a new folder.

## Brief history

- v1: three `[Ir]` nodes with labels, layout `catalytic-cycle`. Rendered as a triangle. Hyphen in "FG-CH2Br" became a superscript minus.
- v2: added a `title` and an unknown `cycle_radius` key. The key is refused (`Unknown brief keys`), so no run; the `title` is accepted but not drawn.
- v3 (final): en dash in "FG–CH2Br", "hν" written as `hv` in the output. The unknown key and title were removed.

## Comparison

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| `cycle_shape` circle: two touching circular cycles | two touching circles (photoredox and Co) | one triangle with straight edges | no |
| `center_label` true: cycle name in the centre | "Photoredox cycle" and "Co-catalyzed cycle", bold italic | no centre label | no |
| `step_names` true: steps named | Blue LEDs, FG-CH2Br / Ag+, RLT, ATRA | only Blue LEDs, FG–CH2Br, Ag+ and Co-catalyzed cycle as text; no RLT | no |
| signature: two touching circular cycles, photoredox black and Co dark maroon | present | one loop; no Co cycle | no |
| signature: cycle name bold italic in the centre of each cycle | present | absent | no |
| signature: catalyst states in grey square brackets | Ir(III), Ir(III)*, Ir(IV), LnCo species in grey brackets | no brackets; `draw_figure` brackets only transition states (double dagger), and the manifest bracket object is not used | no |
| signature: oxidation states as bold superscript roman numerals; IrIV green | superscript roman numerals, IrIV green | "(III)" and "(IV)" on the baseline in bold, inside the compound label; no superscript, no green | no |
| signature: light step as navy disc with bulb and blue bold italic "Blue LEDs" | present | plain text "hv, blue LEDs" beside the arrow; no disc, no bulb, not blue or italic | no |
| signature: grey arc for the competing radical chain | present | absent | no |
| `compound_label_face` bold, `#000000` | bold black state labels, element symbol included | only the oxidation-state line is bold; the element symbol "Ir" is regular weight | no |
| `reagent_text_color` `#000000` | black reagent text ("FG-CH2Br, Ag+", "Li Cl") | black text on the one reagent label drawn ("FG–CH2Br, Ag+"); "Li Cl" is not drawn | yes |
| `arrow_style` plain | plain black arrows | plain black straight arrows (not curved) | yes |
| `show_plus_sign`, `aromatic_rings` | no plus sign or rings in panel A | not applicable | n/a |

Matched count: 0 of 8 claims the card makes for `catalytic_cycle` (cycle_shape, center_label, step_names and the five signature features). Two of the three applicable top-level conventions match (reagent text colour, plain arrows); the compound label face does not, because the element symbol is not bold (see Audit).

## Differences from the paper

- The paper draws two touching cycles with curved arcs. The replica draws one triangle with straight arrows. Curvature and the shared-catalyst geometry are both lost.
- The paper shows Ir oxidation states as superscript roman numerals inside grey square brackets. The replica shows them as a bold compound label under the element symbol "Ir", which is drawn twice (once as the atom, once as the label).
- The excited state Ir(III)* and the Ir(IV) species are not structures; they are `[Ir]` placeholders. The replica makes no chemical claim about them.
- The FG radical, the Ag and AgBr by-product and the LiCl turnover are not drawn. The balance check reports every step as balanced, because the brief lists only the `[Ir]` placeholders and no FG-CH2Br, Ag+ or AgBr species; it cannot detect the missing by-products.
- The "Co-catalyzed cycle" label sits at the far left, away from its arrow, and "hv, blue LEDs" sits at the right edge, offset from its arrow. "FG–CH2Br, Ag+" sits directly under its own arrow.
- "hν" is written as ν in the CDXML text (checked by an offline replay of brief.json), but rendered.png shows "hv". The loss happens at rendering, not in the drawing step.
- The title "A) Proposed catalytic cycle" is not drawn.

## Tool gaps

Scope: `draw_figure` (the brief tool) unless stated. The manifest tool `compose_chemical_figure` is a separate, hand-placed path (`skill/chemdraw/references/publication-figures.md`, "Text, arrows and graphics").

- Cycle geometry: the catalytic-cycle layout draws straight chords between nodes; a three-node cycle is a triangle. `cycle_shape: circle` and `catalytic_cycle.curved_arrow_color` are not applied. The style report lists `cycle_shape`, `center_label` and `step_names` as guidance only.
- The manifest path can place an `ellipse` and cubic Bezier `curve` objects, and an `electron_arrow` gives a curved arrow with a solid head. Circles and curved arrows can therefore be drawn by hand, but nothing links them to species or to a layout, so the figure is not generated from the brief.
- One closed loop per brief in `draw_figure`. Two cycles that share a species need hand placement in the manifest path.
- No cycle-centre label in `draw_figure`. A manifest `text` object with bold italic runs can place one.
- No grey square brackets tied to a species role. `draw_figure`'s `ts_bracket` is for transition states (double dagger). The manifest `bracket` object takes a colour and a label, so grey brackets are possible by hand.
- No superscript and no per-species colour on `draw_figure` labels; species labels are plain strings. Manifest `text` runs support `superscript` and a per-run `color`.
- No bulb pictogram for the light source. A solid `ellipse` gives the navy disc only.
- Step text in `draw_figure`: v1 turned the hyphen in "FG-CH2Br" into a superscript minus. v3 uses an en dash, so this was not re-tested with a hyphen. The Greek nu is stored as ν in the CDXML (offline replay); the rendered image shows "hv", so the loss is at rendering (font glyph availability), not in drawing.
- Step text placement: `draw_figure` does not place step text at the arrow midpoint. In the replay the Co-catalyzed label landed at the left edge. The manifest `text` object takes explicit coordinates.
- Metal species: a label such as LnCo^(n+1) can be written with subscript and superscript runs in the manifest path without a grounded structure. What is missing is the grounded structure that the policy requires, not a drawing capability. A bare `[Ir]` is a placeholder.
- Title: `title` is accepted by `draw_figure` and passed to the layout (`toolkit/cdxml_toolkit/mcp_runtime/figure_draw.py`, line 205), but no renderer reads it. This is a bug, not a missing option.
- Documentation mismatch, missed in the first report: `skill/chemdraw/references/scheme-drawing.md` line 40 documents a `cycle_radius` parameter (default 120 pt) and curved arrows along the circumference. Neither exists in the code.
- Balance: every step reports `balanced: true` and `missing: null` in the offline replay. The brief holds only `[Ir]` placeholders, so this check does not test the real chemistry.

## Structure issues

- Metal centres: `[Ir]` placeholders only; the crop gives no ligands, charges or geometry for Ir(III), Ir(III)* or Ir(IV).
- Substrates: FG-CH2Br and the Ag+ reagent are not drawn, because FG is a generic group in the paper and no SMILES is grounded for it.
- Co cycle: LnCo^n+1 Cl, LnCo^n and LiCl are not drawn; the crop gives only the labels.

## Card observations

- `catalytic_cycle.cycle_arrow_color` and `curved_arrow_color` are null on the card, but the crop shows black photoredox arcs and dark maroon Co-cycle arcs. The card could record these values.
- The top-level notes list "Int-I, Int-II, Int-III, CoII-2" as bold black labels in crop 08. Crop 08 has none of these names; its bold labels are the catalyst states Ir(III), Ir(IV), Ir(III)* and LnCo species.

## Audit

Checked by re-reading reference.png and rendered.png (the latter enlarged), replaying brief.json offline into a temporary folder, and reading the toolkit source and `publication-figures.md`.

Overclaims corrected:

- Compound label face: only the "(III)" and "(IV)" line is bold; the element symbol is regular weight, while the reference's Ir is bold. The row is now "no", and the top-level count falls from three to two.
- Tool gaps: the first list said grey brackets, superscript, per-species colour, a light-source disc, metal labels and curved arrows cannot be drawn. The manifest path supports coloured bracket objects, text runs with superscript and colour, filled ellipses and Bezier curves. The gaps are now stated for `draw_figure`, with the hand-placement caveat.
- Text placement: "FG–CH2Br, Ag+" sits beside its own arrow; only the Co-catalyzed label is at the far left.
- Greek nu: the CDXML holds ν; the loss is at rendering.
- Arrow style: arrowheads are solid and swept in both images, so the "plain" row stands.
- Reagent colour: holds for the one reagent label drawn, which is weak evidence; "Li Cl" is not in the replica.

Corrected counts: catalytic-cycle claims 0 of 8 (unchanged). Top-level applicable conventions 2 of 3 (reagent text colour and plain arrows). Corrected matched count: 2.

Not verified: native ChemDraw rendering (the replay reported native `not_run`); proportions, line weight and yield layout were not measured, and the table makes no claim on them. The v1 hyphen behaviour was not reproduced.
