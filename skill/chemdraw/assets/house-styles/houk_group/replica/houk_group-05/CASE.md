# Nat. Commun. 2022: competitive TS panels (Fig. 6), house style houk_group

Source: Chen, Wipf, Houk et al., *Nature Communications* 2022, 13, article 10.1038/s41467-022-34837-x ("How mono- and diphosphine ligands alter regioselectivity of the Rh-catalyzed annulative cleavage of bicyclo[1.1.0]butanes"). Licence: CC BY 4.0 (from the house card). Evidence crop: `evidence/houk_group-05.png` (copied to `reference.png`).

Figure type: `structure_panel` (house card, `figure_types.structure_panel`).

## What is reproduced

The two 2D ChemDraw transition-state panels of Fig. 6: panel a (TS5 and TS5*, rhodium carbenoid formation) and panel b (TS8 and TS8*, olefin insertion). Each is a square-bracketed TS with a double dagger at the top right, a bold TS label, and a ΔΔG‡ value in kcal mol-1 underneath (values 0.0, 2.9, 0.0 and 1.2 as in the crop). The Rh centre is drawn with L and Cl and the forming contacts as dashed or solid lines. Panel titles are included as bold letters with roman text.

Not reproduced: the upper 3D ball-and-stick geometries (CYLview), the Å distances on leader lines, and the grey dashed rule between the panels.

Structures are read by eye from the crop at 3x zoom. The DECIMER OCSR run on the crops returned invalid or unrelated structures (a Pb/Y5 structure for TS5; a P-containing structure for TS8), so OCSR was not used. The organic skeletons are simplified (see Differences). The Rh, L and Cl atoms are not in the SMILES; they are drawn as a separate fragment `[*:3][Rh]Cl`, with L as a dummy label.

Skeletons (Ts and Ph are dummy atoms with labels):

- TS5: `[*:1]N(CC=C)C([*:2])C1CCC1` (cyclobutyl, Rh contact on the ring carbon next to the CH(Ph))
- TS5*: `[*:1]N(CC=C)C([*:2])C1CC1` (cyclopropyl)
- TS8 and TS8*: `[*:1]N1CC2([H])CCC2(CC=C)C1[*:2]` (pyrrolidine fused to cyclobutane, H and Ph wedged)

## Build path and deviation from the brief

The brief asks for `draw_figure`. `draw_figure` has no structure-panel kind and a species cannot be drawn alone (it needs a step), so bracketed TS structures with bold labels and ΔΔG‡ lines below them cannot be expressed there. The replica uses `cdx.py build` (`acs_builder.build_from_spec`) with hand-placed `coords` for each atom, `ts_bracket`, `interaction` and `text` objects. `brief.json` therefore has no `style` key. Its `_note` records the house card and that the build path uses the fixed ACS 1996 base preset and does not apply house conventions. `replay.py` calls `build_from_spec` (not `draw_figure`). The rendered figure is from `cdx.py render` on the built CDXML.

Coordinates: each evidence-crop zoom pixel was scaled by 0.147 pt, so one bond (about 98 zoom px) is about 14.4 pt. Wedges use the RDKit bond index for Ca–Ph (bond 5) and for H–Ch and Ca–Ph in the TS8 skeleton (bonds 3 and 11).

## Replay

```
python skill/chemdraw/scripts/cdx.py py skill/chemdraw/assets/house-styles/houk_group/replica/houk_group-05/replay.py NEW_DIR
python skill/chemdraw/scripts/cdx.py render NEW_DIR/figure.cdxml
```

`replay.py` writes `figure.cdxml` into `NEW_DIR` offline. `rendered.png` is the desktop ChemDraw render of the revised build (the second coordinate set). The first probe render used an earlier set and is not kept.

## Convention check

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| signature: 3D CYLview ball-and-stick geometry above the 2D TS | yes (grey C, Rh, P, Cl) | not drawn (no 3D renderer or geometry input in the tools) | no |
| signature: 2D TS in square brackets with double dagger, forming bonds dashed | yes | brackets and top-right double dagger drawn, but the sides are slanted; TS5 and TS5* contacts dashed to Rh (alkene to Rh solid); TS8 and TS8* dashed contact ends on the L label, not on Rh | partial |
| signature: bold TS label with ΔΔG‡ = x.x kcal mol-1 underneath | yes | bold labels TS5, TS5*, TS8, TS8*; ΔΔG‡ with italic G and superscript double dagger; the ΔΔG line wraps onto a second line in TS5 and TS8 | partial |
| signature: key distances in Å on thin leader lines | yes (2.17 Å etc.) | not drawn (no leader-line distance label used) | no |
| compound labels bold, black | yes | bold TS labels, black | yes |
| abbreviate groups Ts and Ph | yes | Ts and Ph as labels | yes |
| reagent text colour #000000 | yes | L, Cl, Rh and the ΔΔG text black | yes |
| panel letters bold, titles roman, grey dashed rule between panels (visible, not claimed by the card) | yes | letters and titles drawn; no grey rule | partial |
| bond length vs label size (card: bond/cap height 2.4) | about 2.4 | bond about 14 pt, label 10 pt (ACS 1996 preset), cap height about 7.2 pt: ratio about 1.95 | no |
| line weight and bold weight (card: line 0.09, bold 0.22 of bond length) | line 0.09, bold 0.22 of bond | ACS 1996 preset: line 0.6 pt, bold 2 pt on a 14.4 pt bond (about 0.04 and 0.14 of bond) | no |
| aromatic rings kekule | n/a (Ph abbreviated) | n/a | n/a |

## Differences from the paper

- 3D geometries (top halves of both panels) are absent; the 2D halves are the only part drawn.
- The Å distances and leader lines are absent.
- The grey dashed separator rule is absent.
- The skeletons are simplified. TS5 is drawn as a cyclobutane with a single Rh contact; the crop shows a four-vertex ring with a dashed diagonal, which I could not read unambiguously. TS5* is drawn as a cyclopropane with the Rh contact on one ring carbon. The Rh contacts are drawn as interaction lines, not as bonds.
- TS8 and TS8* have the same 2D skeleton. The crop shows them as diastereomers (allyl and Rh orientation differ); this difference is not reproduced.
- Wedges: the Ph wedge and the ring H wedge are set, but the absolute configuration was not checked against the paper's SI.
- The ΔΔG line breaks in two of four labels: after "0.0" in TS5 and after "kcal" in TS8. TS5* and TS8* stay on one line. The text object's width is not controllable in the build spec. A non-breaking space did not stop this.
- Ts–N bonds are very short, and the "Ts" label crowds the N.
- The bracket sides render as slanted lines, not vertical, in the build output.
- L and Cl labels sit on the Rh bonds in TS5 and TS8, and in TS8 the right bracket crosses the L and Cl labels.

## Tool gaps

- `draw_figure` has no structure-panel or TS-panel kind. A species cannot be drawn without a step, so a bracketed TS with labels and ΔΔG‡ lines cannot be expressed there. Only `cdx.py build` can do it, and that path has no house-style conventions.
- No 3D ball-and-stick (CYLview-style) geometry input or renderer.
- No atom-to-metal forming bond with a dashed partial-bond type in the species model. The build `interaction` object is an endpoint-clipped line not attached to atoms, so it does not move with the structure.
- Wedge bonds in `build` need RDKit bond indices. The spec has no atom-pair form for `displays`.
- Text objects have no width or wrap control; the ΔΔG‡ line wraps unpredictably.
- No leader-line distance label (Å on a thin line with an offset anchor).
- The `ts_bracket` renders with slanted sides in the `build` output (verify the bracket geometry in ChemDraw).
- OCSR (DECIMER) gives nonsense for organometallic TS drawings with Rh, L and Cl; reading by eye is the only route in this case.
- Desktop ChemDraw render was queued behind other jobs for several minutes.

## Notes

- The card's `figure_types.structure_panel` says "one crop" and lists four signature features; these are the four rows above that name the card's claims. The crop agrees with the card on brackets, double dagger, dashed forming bonds, bold TS labels and the ΔΔG‡ line below.
- The card's Rh colour ("blue Rh" in the 3D observation) was not checked at pixel level, so no card error is reported for it.

## Audit

Audited against reference.png, rendered.png, brief.json, replay.py, CASE.md and houk_group.json (house card and the ACS 1996 preset in `toolkit/cdxml_toolkit/chemdraw/style_presets.py`).

Corrections to the convention table:

- Bracket and contact row (was yes, now partial): the bracket sides are slanted in the render. The TS8 and TS8* forming contacts end on the L dummy atom, not on Rh. In brief.json the contact endpoint (185.12, 206.15) is the L atom, and Rh sits at (192.46, 198.8). The rendered dashed line runs into the L label.
- ΔΔG row (was yes, now partial): the line wraps in TS5 and TS8, as the table row itself says.
- Bond length vs label size (was partial, "about 2.0 by eye", now no): the ratio is computed, not judged by eye. Bond about 13.97 pt (brief coordinates 49.24 to 63.21), label size 10 pt, Arial cap height about 0.716 em, so bond over cap height is about 1.95 against the card's 2.4.
- Line and bold weight (added, no): the preset draws lines at 0.6 pt and bold at 2 pt. The card gives about 1.3 pt and 3.2 pt on a 14.4 pt bond.
- Matched count: 3 of the 8 applicable rows (bold black compound labels, Ts and Ph abbreviations, black reagent text). The replica claimed 5 of 7.

Other overclaims:

- "What is reproduced" lists TS8 and TS8* as reproduced. The two 2D drawings are identical in brief.json: every TS8* coordinate is the TS8 coordinate shifted by 105.01 pt, with the same wedges. The diastereomer difference the crop shows is absent from panel b. The Differences section discloses this, but the reproduced claim does not.
- The rendered TS8 "Ph" label touches the bold "TS8" label. The rendered TS5 "Ts" shows a dot in place of the Ts-N bond, while TS5* shows a bond. Neither is in Differences.
- The panel a title reaches the right edge of the render (1132 px wide).
- Checked and correct: the wedge keys. With explicit H kept, as the builder does (removeHs = False), RDKit bond 3 is C-H and bond 11 is C-Ph in the TS8 skeleton. TS5 bond 5 is C-Ph.

Tool gaps corrected or missed:

- The `draw_figure` claim is overstated. Its species entries accept a `ts_bracket` flag, but only inside a reaction step (`figure_draw.py` lines 328-349 and 705-707). The real gap is narrower: no standalone species, and no bold label or ΔΔG line under the bracket.
- Missed: `interaction` endpoints are raw coordinates, not atom references, so an endpoint can land on the wrong atom without an error. This is how the TS8 contact ended on L. L is also a bonded dummy atom, so its label sits on the contact point.
- Missed: molecule objects in the brief have no per-object label size, line width or bold width. The preset fixes the bond-to-label ratio and the line weight at values that differ from the house card.
- Missed: `ts_bracket` takes a hand-set box with no fit to the structure and no clearance from nearby labels. The right bracket crosses Cl and L.
- Missed: the brief types used here (text, molecule, interaction, ts_bracket) have no plain rule object, so the grey separator was dropped.
- Missed: no overlap check was reported on the build output. The Ph/TS8 touch and the bracket-through-label collisions are visible at zoom.
