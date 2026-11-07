# US 9,732,080 B2: generic formula I and the Ar1 definition (markush)

Source: Hadida-Ruah et al. (Vertex), US 9,732,080 B2, 2017, "Modulators of ATP-binding cassette transporters", col. 6 (formula I and the Ar1 definition). The patent number is used as the citation because the card gives no DOI.

Licence: public domain (US patent), as stated on the card. `reference.png` is a copy of `evidence/uspto_patents-01.png`.

Drawing style: the `uspto_patents` house-style card, figure type `markush`. The card's base preset is `j_mol_mod`, which is what `draw_figure` applied (the report says house conventions apply to schemes only). Of the preset, only the bond length (14.4 pt) and line width (0.6 pt) were applied; the label size is not the preset's (see Differences).

## What is reproduced

A generic formula I panel: a quaternary carbon bearing a meta-substituted phenyl (ring B placeholder), a spiro ring A placeholder, and a C(=O)N amide carrying two variable groups (Ar1 and RN). Below it, the line "or a pharmaceutically acceptable salt thereof, wherein:" and the Ar1 definition as an indole fragment.

The generic parts are stand-ins, not structures from the paper:

- ring A is drawn as cyclopropane (`C1CC1`); the paper draws an open loop with the letter A inside;
- ring B is drawn as a benzene ring with the substituent as `*`; the paper draws a hexagon with the letter B and the substituent (R^xX)_x;
- R^N and the Ar1 group on the amide nitrogen are `*` placeholders; the paper writes R^N and Ar^1 with superscripts;
- the Ar1 fragment is an indole with `*` at C5 (G3 in the paper's numbering). The paper leaves the substituent position open across the G2 to G3 edge with a wavy line; `draw_figure` cannot draw that, so the position was chosen here. The compose route has a `Wavy` bond display that was not tried (see Tool gaps).

SMILES, checked in RDKit (the canonical form equals the input): formula I `O=C(N(*)*)C1(CC1)c1cccc(*)c1`; Ar1 `*c1ccc2[nH]ccc2c1`. OCSR was not run: the crop carries variable groups that OCSR cannot read, so the stand-in SMILES are not read from the image. The RDKit check was not repeated in the audit; the draw's own chemistry readback passed (`rdkit_readback_consistency`).

## Render status

Not rendered. Two `cdx.py draw ... --render` runs (the first run and one retry, on the first brief) exceeded the 300 s draw limit. Five `ChemDraw.exe` processes were running at the time and were left alone. The final brief was drawn without rendering, and `replay.py` in this folder reproduces the panel without rendering. No `rendered.png` was made.

The `match` column below reflects the unrendered CDXML and its manifest (text strings, node types, bond orders, font, colour index). It is not an image comparison. Rows marked "not confirmed" need a visual check once ChemDraw can render. The audit re-read the manifest (see Audit); it did not render.

## Brief iterations

1. First draft: a default title "Substrate scope" appeared on the panel, and the Ar1 entry had no label, so its id "Ar1" was printed under the indole.
2. Title set to a single space (removes the default title, leaves an empty text object), and the Ar1 group heading given its colon.
3. Label of the Ar1 entry set to a single space (removes the auto-label). This is the final brief, `brief.json` in this folder. The empty text object is left for this label too, not only for the title.

## Replay

```
python skill/chemdraw/scripts/cdx.py py skill/chemdraw/assets/house-styles/uspto_patents/replica/uspto_patents-01/replay.py NEW_DIR
```

`replay.py` is the jacs-au replay with two changes: the docstring, and the output is the folder `panel`, because the brief has `kind: "scope"` (a scope brief writes a folder of pages, not one `.cdxml` file). Verified: it writes `panel/page-001.cdxml`, `validation.json`, and the manifest reports `checks_passed: true`. The audit re-ran it into a temporary folder (not this folder) and got the same result.

## Convention and signature check

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| formula label I flush right, at the top of the drawing | plain I at the top right of the text column, above and beyond the right end of the drawing | I printed under the structure as a compound label (text at x 22, y 139, below the drawing) | no |
| compound label face plain | plain Roman I | label text with face 0 (plain) in the CDXML; not seen on an image | not confirmed (manifest only) |
| label and line colour black | black only | text colour index 3, but the colour table has two entries, so index 3 is outside it; black is not established | no (colour reference undefined) |
| Times serif labels | Times | font 1001, Times New Roman in the CDXML font table; not seen on an image | not confirmed (manifest only) |
| R groups as R with superscript numbers or italic superscript letters (RN, RX) | R^N italic superscript; (R^xX)_x | every variable is a plain R node with no superscript | no |
| ring atoms as E1, E2 or G1 to G4 with subscript numbers | G1 to G4 with small locants 2 and 3 | no ring labels | no |
| unspecified ring as an open loop or circle with a letter inside | ring A open loop with A; ring B a hexagon with B | cyclopropane triangle, no letter | no |
| substituent position left open by a bond crossing the ring | bond crossing the G2 to G3 edge | R node on a ring atom | no |
| attachment shown by a wavy line | wavy line to Ar1 | R node; no Display="Wavy" in the CDXML | no |
| variable definitions as running justified text beginning "wherein" | the sentence "or a pharmaceutically acceptable salt thereof, wherein:" followed by "Ar^1 is:" on its own line | conditions line and "Ar1 is:" as text with Justification="Left"; the line begins "or a pharmaceutically" | no |
| aromatic rings Kekule | Kekule | 8 double bonds in the CDXML (C=O plus alternating ring bonds); not seen on an image | not confirmed (manifest only) |
| no colour or shading | none | no coloured shapes, but the text colour index is undefined (see above) | not confirmed |
| line width to bond length 0.047 | 0.047 (3 px over 62 px) | 0.6 / 14.4 = 0.042 (CDXML LineWidth 0.6, BondLength 14.4), about 11 percent thinner than the house value | no |
| label size to bond length | cap height 21 px, bond 62 px (ratio about 3.0); house label estimate 7.5 pt | CDXML label 8.0 pt, bond 14.4 pt; ratio about 2.7 to cap height (estimated); 8.0 pt is the scope panel's own size, not the preset's 10 pt | no |
| indole NH drawn with H stacked above N (added in audit) | H above N | the text "NH" set inline (CDXML label "NH") | no |
| locants 2 and 3 on the indole ring (added in audit) | plain 2 and 3 on C2 and C3 | none; draw_figure has no per-atom text | no |
| superscript 1 on Ar^1 in the group heading (added in audit) | "Ar^1 is:" | "Ar1 is:" as plain text | no |
| semicolon after the Ar1 structure (added in audit) | ";" at the right end of the fragment | none | no |

Claimed: 5 signature features (the card's `markush` list). Matched: 0. The partial "wherein" line is counted as no.

Corrected count (audit): 0 of 18 rows confirmed on an image. Four rows are manifest only (face, Times, Kekule, no colour), and the other 14 are no. The earlier table had four "yes" rows; none of them has image evidence.

## Differences from the paper

- Layout: the paper puts the formula label I flush right above the drawing; the replica puts I under the structure.
- Variable groups: every variable is a plain R node, so R^N, (R^xX)_x, Ar^1, E and G labels with superscripts or subscripts are lost.
- Ring A is a cyclopropane triangle rather than an open loop with the letter A.
- Ring B has no letter, and the substituent is a plain `*` on a meta position.
- Ar1 has no wavy attachment line, and the attachment position is chosen (C5), not left open.
- The indole NH is an inline "NH" label, not H stacked over N; locants 2 and 3 and the closing semicolon are missing.
- The conditions line is left-aligned; the paper's running text is justified.
- Line width and bond length are the j_mol_mod preset (0.6 pt and 14.4 pt). The house line width is 0.047 of the bond length, about 0.68 pt at 14.4 pt, so the replica is thinner.
- The label size is not the preset's. `figure_scope.py` removes the preset's font size and keeps the panel's own text size, so the labels are 8.0 pt, not the preset's 10 pt and not the house estimate of 7.5 pt. A scope brief takes only a preset name in `style`, so the house line width and label size cannot be set from the brief.
- The paper's line numbers and two-column layout are not in this crop and were not drawn.

## Tool gaps

Checked against the toolkit sources in the audit. The `draw_figure` limits are real; some capabilities that the earlier text called absent exist on other routes but were not tried here.

- `draw_figure` has no `markush` kind (its `kind` accepts scheme, scope and mechanism only). Variable labels with superscripts or subscripts, labelled rings and wavy bonds cannot be written in a scope brief.
- A `*` in a SMILES becomes a plain `R` generic nickname (four GenericNickname nodes, text "R"): no per-atom text, no superscripts or subscripts. Scope `group` and `conditions` are plain strings, so run-level superscripts are not available there either.
- Labelled rings: overstated in the earlier text. `markush_compile` has a `variable_ring` kind (a circle with a letter at its centre, drawn by `markush/cdxml_writer.py`). `compose_chemical_figure` has `ellipse` and `curve` graphics plus `text` objects, so a circle and the letter A could be overlaid. Neither was tried. The ring A loop is therefore a possible route, not an absent capability.
- Wavy bond: overstated in the earlier text. `compose_chemical_figure` molecule objects accept `bond_displays` with `Wavy`, and `chemdraw_object` bond-display edits accept `Wavy` (`figure_editing.edit_bond_display`). Neither was tried. The markush route has no wavy display.
- Bond crossing a ring edge for an open substituent: not drawn by any route checked here. `crossings` sets the depth of crossing bonds; it does not create a substituent position.
- Flush-right label above the drawing: the gap is real for the scope panel, which labels only below. `compose_chemical_figure` text objects accept `align: Right` and a position, so the formula label could be placed there. Not tried.
- Scope panels apply only the base preset; the house figure-type conventions are not applied to scope output (the draw report's `style.applied` is empty and says so).
- A scope brief with no title adds "Substrate scope" (`figure_scope.py` line 140). A single-space title is truthy, so the default is suppressed, and an empty text object is left at the top of the drawing (CDXML id 1002).
- An unlabelled scope compound is printed with its species id unless a single space is given as its label. Not re-checked in the audit.
- Free text lines have no justification: text objects accept `align` Left, Center or Right only.
- Text colour index 3 with a two-entry colour table is a defect, not an unknown. Every text run in the scope output carries `color="3"`, and the colour table has two entries, so the index is outside the table. The black label colour is not established by the file.
- `--render` exceeded the 300 s draw limit on two runs; no native PNG was produced. Not re-tested in the audit.
- The markush spec route (`markush_compile`, see `skill/chemdraw/references/markush.md`) takes superscript and subscript labels (`^{...}`, `_{...}`), variable-position groups such as `(R^{B})_{q}`, variable-ring circles and arc bonds. It is not on the `draw_figure` path this brief uses and was not tested here. It has no wavy display.
- Gaps the earlier list missed: the NH label is inline rather than stacked (no stacked-H option on the scope path; the markush spec has an `h` atom option, untested); there is no per-atom locant text on the scope path; the group heading cannot carry a superscript; no trailing punctuation can follow a structure in a scope panel; the empty text object also appears for the Ar1 label, not only for the title.

## Audit

Audit date: 2026-11-07. Inputs: `reference.png` (the only image in this folder; there is no `rendered.png` and no `panel` folder here), `CASE.md`, `brief.json`, `replay.py`, the card `toolkit/cdxml_toolkit/publication/house_styles/uspto_patents.json`, and the toolkit sources named above.

- The replay was re-run without rendering into a temporary folder. It wrote `panel/page-001.cdxml` and `validation.json`, `checks_passed: true`, native preview `not_run`. The manifest was read from that run; no image was produced, so no row is confirmed visually.
- Overclaims corrected in this file: (1) the "yes" rows for face, Times, Kekule and no colour rested on the manifest only, now "not confirmed"; (2) line width and label size were marked "close" but do not meet the house values (0.042 against 0.047; 8.0 pt against a 7.5 pt estimate with a 2.7 against 3.0 ratio), now "no"; (3) "label sizes are the base preset" was wrong, since the label size is the scope panel's own 8.0 pt; (4) the colour row said "not confirmed" when the file's colour index 3 is outside its two-entry colour table, now "no"; (5) "no way to draw a loop" and "no wavy attachment bond" were overstated, since other routes exist (untested); (6) the summary "Matched: 0" sat beside four "yes" rows, which is now resolved by the corrected count.
- Missing rows added: stacked NH, locants 2 and 3, superscript in the group heading, trailing semicolon.
- Corrected matched count: 0 of 18 table rows on an image; 0 of the 5 markush signature features.
- Still needed before any row can be marked matched: a native render of `panel/page-001.cdxml` and a visual comparison with `reference.png`. The render limit (300 s) and the five running `ChemDraw.exe` processes were not re-examined.
