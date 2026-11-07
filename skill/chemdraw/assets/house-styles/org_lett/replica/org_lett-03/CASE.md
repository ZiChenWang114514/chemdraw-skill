# Org. Lett. Scheme 1 (alcohol activation and C(sp3)–Si bond construction): concept panel replica, not rendered

Source: K. Oestreich et al., *Org. Lett.* **2025**, *27*, 3686 (One-pot sequential alcohol activation and nickel-catalyzed cross-electrophile coupling with chlorosilanes). DOI: [10.1021/acs.orglett.5c00830](https://doi.org/10.1021/acs.orglett.5c00830). Licence: CC BY 4.0. Reference crop: `reference.png` (Scheme 1 of the article).

Drawing style: the `org_lett` house style card (`cdx.py styles org_lett`), base preset ACS Document 1996; figure type `concept_panel`.

## Status

The replica is **not rendered**. `brief.json` was submitted to `cdx.py draw`, but the run never reached the drawing step: every run queued on the shared ChemDraw automation mutex (`chemdraw_com`) and ended with `resource_busy` after 295 s, or was killed by the foreground timeout while waiting. Several other replica runs were using ChemDraw at the same time. No `figure.cdxml` or `rendered.png` was produced, so nothing below has been checked against a drawing.

## What is reproduced

Intended scope: the top panel of the crop, "Reactions Between Alcohols and Chlorosilanes". One alcohol R–CH2CH2–OH and one chlorosilane Cl–SiR'3 give the alkoxysilane (left arrow, "traditional alcohol protection" / "established") and the alkylsilane (right arrow, "deoxygenative silylation" / "unexplored"). In `brief.json`, R is `*` and R'3 is three `*` atoms on Si, because the card's generic labels cannot be entered as species.

The bottom panel, "General Strategies for the Construction of C(sp3)–Si Bonds" (four rows, "this work" last), is not in `brief.json`. It was drafted in scratch as three single-arrow steps with the same product. The tool's layout rules for steps that share a product (convergent or divergent) are not stacked rows, so this panel would need a different route. This is the panel that carries most of the `concept_panel` conventions, so the replica covers only part of the figure.

## Stand-ins in the brief

| Crop label | Brief SMILES | Note |
| --- | --- | --- |
| R–CH2CH2–OH | `*CCO` | `*` stands for R |
| Cl–SiR'3 | `Cl[Si](*)(*)*` | `*` stands for R' |
| R–CH2CH2–O–SiR'3 | `*CCO[Si](*)(*)*` | |
| R–CH2CH2–SiR'3 | `*CC[Si](*)(*)*` | |

Dummy atoms are used because the species fields take SMILES only. Whether they render as `R` or as `*` was not checked.

## Convention check

The card claims the conventions below for `concept_panel`, plus the top-level scheme conventions visible in the crop. "not checked" means the replica has no drawing to compare against. "n/a" means the feature is absent from this crop.

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| comparison_layout: stacked rows | two stacked sub-panels; the bottom panel has four rows with "this work" last | top panel only (no bottom panel drawn) | no |
| panel_label_style: parenthesised lowercase (a), (b) | not used in this crop; sub-panels have bold italic titles | not drawn | n/a |
| this_work_color: null | "this work" in black; the silyl fragment in blue #0336FF | not drawn; draw_figure has no per-label colour for this | no (not drawn) |
| background_fill: null | white | not drawn | no (not drawn) |
| highlight_fill: null | none | not drawn | no (not drawn) |
| variation_color: null | none | not drawn | n/a |
| signature: previous approaches and this work as stacked rows, this work last | as above | not drawn | no |
| signature: "this work" as bold italic text under the arrow, no coloured box | bold italic "this work" under the bottom arrow | no bold italic run in below lines (draw_figure `below` takes text lines) | no (not drawn) |
| signature: sub-panels separated by a thin black full-width rule | rule under the top panel | no separator object in draw_figure | no |
| top level: arrow_style plain | plain arrows | solid arrows | no (not drawn) |
| top level: substrate_layout inline_plus, show_plus_sign | stacked: alcohol above, "+", Cl–SiR'3 below, between the two arrows | inline, as the card specifies; not rendered | no |
| top level: reagent line placement (added in audit) | name above the arrow; status word ("established", "unexplored") below the arrow; both italic | both lines in the brief's `above` list | no |
| top level: product captions (added in audit) | "alkoxysilanes (silyl ethers)" and "alkylsilanes" under the products, plain type | not in brief | no |
| top level: reagent_text_color #000000 | reagents and conditions in black | not drawn | no (not drawn) |
| top level: Arial labels | sans-serif labels, Arial-like at this resolution | not drawn | no (not drawn) |

Testable rows: 13 (two are n/a; two of the rows were added in the audit below). Matched: 0. The rows checked against a drawing: none, because no drawing exists in this folder.

## Differences from the paper

- Nothing has been drawn, so no visual comparison exists. The figure in the paper is a two-panel layout; the replica would contain only the top-panel reaction, if it drew at all.
- Generic labels R, R', X, M, `C(sp3)`, `SiR'3` are replaced by dummy atoms or Br/Cl stand-ins.
- The bottom panel, the sub-panel titles (bold italic), the thin separator rule, and the dashed separator between the two first rows are missing.
- All colour (blue silyl group, blue thick new C–Si bond) is missing; the card sets `new_bond_color` and `substrate_colors` to null, so no colour is expected from the house style.

## Tool gaps

- Shared ChemDraw automation (`chemdraw_com` mutex) blocked every draw for more than 5 minutes while other runs were active. This blocked the replica; it is an operating constraint, not a drawing capability.
- Species accept SMILES only: no generic group labels (R, R', X, M). Whether dummy atoms render as the letter `R` in ChemDraw is not verified.
- `draw_figure` lays out steps by its own rules (linear, sequential, convergent, divergent, catalytic cycle). Independent reactions with a shared product cannot be stacked as rows.
- No sub-panel title, panel letter, full-width rule or dashed separator line in `draw_figure`; these would need the manifest route (`compose_chemical_figure` has `text` and `line` objects) without the house style conventions.
- Below-arrow text lines do not take bold or italic runs, so "this work" under the arrow cannot be set in bold italic through the brief.

## Replay

`replay.py` runs `draw_figure` on `brief.json` offline and writes `figure.cdxml` and `validation.json` into a new folder given as argument. It has not been run successfully for this case.

## Audit

Checked against `reference.png` (829 x 535), `brief.json`, the `org_lett` card and the toolkit source. There is no `rendered.png` or `figure.cdxml` in this folder, so no replica image was compared. The brief was checked offline with the toolkit's own validator (`_validate` in `figure_draw.py`); no ChemDraw call was made and no file was written.

Overclaims and errors in the text above:

- The paper's substrate layout is stacked, not inline: the alcohol sits above a "+", with Cl–SiR'3 below it, between the two arrows. The card's `inline_plus` does not match this crop.
- The status says the run "never reached the drawing step" because of the mutex. The brief also fails `draw_figure`'s own validator before any ChemDraw step. Both steps take the alcohol and the chlorosilane as substrates, and the route classifier accepts only one shared substrate (divergent). The error is "The steps are not a linear route, a convergent route ... so they cannot be laid out." Even with a free mutex, this brief returns an error and no CDXML.
- "Species accept SMILES only" is wrong. Names are accepted (curated table, or PubChem when the network is allowed). An unresolved name stops the run. The real limit is that generic labels cannot be resolved.
- "Whether dummy atoms render as R is unverified" can be answered from source. `renderer.py` (about lines 527 to 574) writes every element-0 atom as a generic nickname with display text "R", so each `*` reads R, including the three on Si. R', X, M and the subscript 3 cannot be produced. This is from reading the source, not from a render.
- "Claimed (testable) rows: 10" was wrong: the table had 11 rows that were not n/a.
- "Br/Cl stand-ins" describes nothing in `brief.json`, which has no Br.
- "not checked" is not a match status when nothing was drawn. Those rows are now "no (not drawn)".
- The table omitted two paper features: the status word below each arrow, and the product captions. Both rows are added above.

Corrected matched count: 0 of 13 testable rows (two n/a). No row matches.

Tool gaps the replicator missed (verified in source, not run):

- Topology: two steps that share both substrates are refused by the validator. The top panel has this topology, with arrows leaving a central reagent pair in opposite directions. `draw_figure` lays out left-to-right routes; the only right-to-left handling found is the alternating row direction in multi-row schemes (`renderer.py` about line 1482).
- Labels: every dummy atom is drawn as "R". There is no R', X, M, subscript or prime in generic labels.
- Colour: the brief has no colour key (`BRIEF_KEYS`: kind, species, steps, max_width, title, style, layout). Colour comes only from the card's `new_bond_color` and `substrate_colors` (both null for org_lett) and from ring or halo fills, which are fills, not text colour. The blue SiR'3 groups and the blue new bond cannot be set on this style.
- Figure type: the brief has no `figure_type` key. `draw_figure` calls the figure-type step only for catalytic cycles (`figure_draw.py` line 638) and mechanisms, so the card's `concept_panel` conventions are never applied to a scheme.
- Title: the brief's `title` key is accepted, but no code in `render/renderer.py` reads it. It probably draws nothing (not run).
- Product captions: a species `label` is drawn under its structure, but the org_lett card sets `compound_label_face` to bold, and `figure_house.py` (about lines 262 to 276) applies that face to these labels. The captions would come out bold; the crop's captions are plain.
- Manifest route: `compose_chemical_figure` text runs take bold, italic and colour per run (`figure_tools.py` about lines 806 to 815), and line objects take `style: "dashed"` (about line 1173). The bold italic "this work" label and a dashed separator can therefore be built there, but not from the brief and not with the house style applied. A full-width solid rule is also available as a line object.

A fix that needs no tool change: put "established" and "unexplored" in the step's `below` list, not `above`. This does not clear the validator refusal above.
