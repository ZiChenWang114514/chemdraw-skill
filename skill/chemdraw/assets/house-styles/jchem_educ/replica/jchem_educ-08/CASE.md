# Deufel, van Gemmeren et al., J. Chem. Educ. 2024: Figure 2 (More O-Ferrall-Jencks square), stand-in only

Source: Deufel, van Gemmeren et al., "Deuteration of arenes via Pd-catalyzed C-H activation: a lesson in nondirected C-H activation", *J. Chem. Educ.* **2024**. DOI: [10.1021/acs.jchemed.4c00270](https://doi.org/10.1021/acs.jchemed.4c00270). Figure 2 (crop `evidence/jchem_educ-08.png`, as recorded in the house-style card).

Licence: CC BY 4.0 (from the card); reference crop reproduced under that licence.

Drawing style: the `jchem_educ` house style in `brief.json` (base preset ACS Document 1996). The card has no drawer for a concept panel; `draw_figure` applies only the bold compound-label convention, which this figure does not use.

## What is reproduced

Very little. The figure is a More O-Ferrall-Jencks square: two axes ("C-H bond order" along the top, "C-M bond order" down the right side), a red diagonal double-headed arrow, two dark ellipses labelled AMLA / CMD and BIES / eCMD, corner dots, a grey, a teal and a pink legend box, and a dashed legend frame at the bottom. Its only chemistry is three generic labels: **H** over **Ar** (top right), **B** over **H** joined to **[M]** over **Ar** by a dashed arc (bottom left). Ar, M and B are generic placeholders in the paper; no SMILES can be read from them, so OCSR was not run.

What `draw_figure` can express is a single two-species step. The stand-in drawn here is:

- `c1ccccc1` (benzene) as the H-Ar placeholder;
- `[Pd]c1ccccc1` (phenylpalladium) as the [M]-Ar placeholder, with Pd chosen only to make an M-Ar bond;
- a dashed arrow with the text "generic H-Ar / [M]-Ar (Ar, M generic in paper)".

This is not a chemical claim from the paper. The step is unbalanced as drawn (the tool warns that Pd is missing from the reactants), and the rendered figure reads as a reaction that the paper does not show.

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| card, concept_panel: `panel_label_style` none | no panel letters | no concept panel is drawn, so there are no letters to omit; the match is vacuous | no |
| card, concept_panel: colour-filled legend boxes grey #C4CECD, teal #80D8D8, pink #F8C0CC, each with a bold title line | three boxes, measured fills #C2CCCD, #80DADB, #F8C2CF; bold title lines | not drawn (no filled text box in the tools) | no |
| card, concept_panel: category names in dark navy #003454 ellipses with white text | BIES / eCMD ellipse #023554 (navy); AMLA / CMD ellipse #2D3D3D (dark slate, not navy); white text in both | not drawn (no ellipse primitive) | no |
| card, concept_panel: take-home statements in blue #0000FC under small structures | none on this crop (they are on crop 09) | not drawn | n/a |
| top level: label font Arial or Helvetica | sans-serif labels | "Pd" and the caption in Arial (CDXML font id 3 for labels and captions, checked in a scratch replay); label size and colour not compared | yes (font face only) |
| top level: `arrow_style` plain (thin line, small filled head) | no reaction arrow; the only arrow is the red double-headed diagonal | dashed arrow (my stand-in choice) | no |
| top level: generic stacked labels (H over Ar, B over H, [M] over Ar, bold H) | stacked two-line labels with bold H | benzene ring and one-line text | no |
| top level: `aromatic_rings` kekule | no ring drawn on this crop | Kekule benzene (stand-in) | n/a |
| top level: `compound_label_face` bold | no compound numbers on this crop | none | n/a |

Claimed by the card for concept_panel: 4 items (the first row plus the three signature features). Matched: 0 after audit (see the Audit note). The take-home item is on the card's list but belongs to crop 09, so it is not counted as matched here.

## Differences from the paper

- The square is absent: no axes, no axis titles, no diagonal red double-headed arrow, no corner dots, no ellipses.
- The top-right key (x = system in this study; filled dot = completely stepwise), the x marker inside the square, and the two dot-and-text entries inside the dashed legend frame are absent.
- The three legend boxes and the dashed legend frame are absent, with their bold titles and coloured fills.
- The generic labels H-Ar, B-H and [M]-Ar are replaced by benzene and phenylpalladium. The dashed B...M arc is not drawn.
- The step arrow is dashed; the paper has no reaction arrow here.
- The red and navy colouring is not reproduced, so the colour conventions cannot be compared.
- The stand-in step does not balance (Pd missing), and the drawing implies a reaction the paper does not show.

## Tool gaps

`draw_figure` was the only route the replicator used. The gaps below are corrected by the audit: the code was read in `toolkit/cdxml_toolkit/mcp_runtime/`, and the composer route was not run against this figure.

- `draw_figure` has no concept-panel kind: `figure_draw.py` rejects every kind except `scheme`, `scope` and `mechanism`. This gap holds.
- The manifest composer `compose_chemical_figure` (`figure_tools.py`) already takes `ellipse` (solid fill, colour, dashed option), `rectangle` (fill type, dashed, background), arrows in the `resonance` style (double-headed, any colour) and free `text` items (per-run colour and bold, multi-line). Filled ellipses with white centred text, a dashed legend frame, a coloured double-headed diagonal arrow and filled boxes with a bold title line can therefore be built there, one hand-placed item each. Corner dots can be small ellipses. The claim that these primitives are missing holds only for `draw_figure`.
- Generic labels (Ar, M, B) and a stacked two-line label (H over Ar) can be free text items in the composer. The `draw_figure` species `label` field was not tested for a label with no structure.
- No dashed curved bond or arc: `curve` items take points and colour only, with no dash option. This gap holds on both routes.
- No house-style drawer: a house card is applied inside `draw_figure` only to schemes, scope panels and mechanisms, and the composer's `style` takes only a built-in preset. A card's concept-panel conventions cannot be applied through either route. This gap holds.

## Replay

```
python skill/chemdraw/scripts/cdx.py py skill/chemdraw/assets/house-styles/jchem_educ/replica/jchem_educ-08/replay.py NEW_DIR
```

`replay.py` runs `draw_figure` on `brief.json` offline and writes `figure.cdxml` and `validation.json`. It was not run for this case before the audit; the audit ran it once into a scratch directory (see the Audit note), with `PYTHONPATH` pointing at the repository toolkit because the installed package lacks `mcp_runtime`. `rendered.png` came from a direct `cdx.py draw ... --render` call with the same brief.

## Audit

Audit date 2026-11-07. Checked against `reference.png`, `rendered.png`, `brief.json`, the `jchem_educ` card and the toolkit code.

- Overclaim corrected: the `panel_label_style` row was marked matched. No concept panel is drawn, so the match is vacuous. It is now no, and the concept-panel count is 0 of 4 (not 1).
- Verified: the Arial label row. The replay CDXML uses Arial (font id 3) for labels and captions. Size and colour are not compared, because the card leaves `atom_label_size_pt_estimate` null.
- Verified: the arrow is dashed, not plain; the square, ellipses, legend boxes and dashed frame are absent; `draw_figure` warns that Pd is missing from the reactants (`balanced: false`), and nothing was added to balance it.
- Verified from `reference.png`: the legend fills are about #C2CCCD, #80DADB and #F8C2CF, and the ellipses are #023554 (BIES / eCMD) and #2D3D3D (AMLA / CMD). These match the card's observations, but they describe the paper, not a replica match.
- Not comparable: proportions and line weight. The card's measurements for crop 08 are null, and the replica's bond length has no counterpart in the reference crop, so no proportion row can be checked.
- Tool gaps were overstated for the toolkit as a whole; see Tool gaps.
- The replica's caption "(Ar, M generic in paper)" is internal wording that would appear on a published figure. It must not be used in a final figure.
