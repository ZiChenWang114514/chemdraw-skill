# Zobernig et al.: hydrogenation of vinylarenes (Table 2 scheme), wiley_angew replica

Source: Zobernig et al., *Chem. Eur. J.* **2024**, *30*, e202302455. DOI: [10.1002/chem.202302455](https://doi.org/10.1002/chem.202302455).

Licence: CC BY 4.0. Reference crop reproduced under that licence (`reference.png`, from `evidence/wiley_angew-03.png`).

Drawing style: the `wiley_angew` house style card (top-level conventions; the card has no `figure_types` section, so `reaction_scheme` conventions are the top-level ones). Base preset `wiley`.

## What is reproduced

The top reaction of the figure only: a vinylarene is hydrogenated to the ethylarene under catalyst `2` (0.25 - 0.5 mol%), KOtBu (2.5 - 5 mol%), toluene, 100 °C, 20 bar H2, 18 h. The generic `R` of the paper is replaced by phenyl, so the drawn pair is styrene to ethylbenzene, which is entry 3a of the scope (yield >99). The yield is written as `> 99%`; the footnote letters b and c are not drawn.

Not reproduced: the 15-entry scope grid (3a-3o), the substituted entries, the red colouring, and the footnote superscripts.

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| compound label face bold (card: `bold`) | `3a` bold | `3a` bold | yes |
| compound label colour `#000000` | black | black | yes |
| yield format `{value}%` | `>99 (89)` with footnote letters | `>` then subscripted `99` and `%` (`>₉₉%`); the card template is not applied to a value with a leading `>` (see Audit) | no |
| yield placement (card: null) | yield on the line below the product label | yield under the arrow, in the conditions block | no |
| conditions split `reagents_above_solvent_below` | catalyst above, KOtBu and toluene/temperature/H2/time below | catalyst above, KOtBu and solvent line below, as typed in `brief.json`; the drawing code skips this convention and keeps the brief's lines as given | no |
| aromatic rings Kekule | Kekule | Kekule (visual check only) | yes |
| reagent text colour `#000000` | black | black (visual check only) | yes |
| arrow style plain | black plain arrow | black arrow with a solid head, as in the crop; the code does not apply `arrow_style`, and `plain` is not defined on the card | no |
| font Arial or Helvetica | sans-serif | Arial-like sans-serif by eye; the code does not apply `label_font`, and the font name was not checked | no |
| bond length about 2.1 times cap height (card, measured) | about 2.1 (46 px bond, 21 px cap height) | not measured on the render | no |
| line width about 0.09 of bond (card, measured) | about 0.09 | not measured; the render is a 1200 px copy of a 2085 px crop, so line weight cannot be compared | no |
| arrow length 8.4 bonds (card) | 560 px / 46 px = 12.2 bonds by the card's own crop numbers | not measured | no |
| new bond colour (card: null; crop shows red) | hydrogenated bonds red | black | no |
| substrate colour (card: null; crop shows red) | substrate C=C red | black | no |
| highlight fill (card: null) | none | none | yes |
| substrate layout `inline_plus`, plus sign | single substrate, no plus sign drawn | single substrate | n/a |
| abbreviate groups (card: null) | `R`, `Me` as line | not applicable (no abbreviation drawn) | n/a |
| catalyst label bold (visible, not in card) | `2` bold | `2` plain | no |

Count: 4 of 11 claimed conventions match after audit (the replicator claimed 7). Claimed = conventions with a non-null card value that this crop shows: label face, label colour, yield format, conditions split, Kekule, reagent colour, arrow style, font, bond/cap ratio, line width, arrow length. Matched: label face, label colour, Kekule, reagent colour. Conditions split, arrow style and font were marked matched before the audit; see Audit.

## Differences from the paper

- The substrate is styrene, not the generic `R`-vinyl of the paper.
- The hydrogenated bonds are black; the paper colours them red, and the substrate's C=C is also red.
- The yield is subscripted and sits under the arrow, not on the line under the product label as in the paper.
- The catalyst `2` is plain, not bold.
- The paper's footnote letters (b, c) and the yield in brackets (89) are not drawn.
- The scope entries 3b-3o are not drawn.
- Line weight was not measured on either image; the render is a 1200 px copy of the 2085 px crop, so any visual comparison of line thickness is unreliable.
- The H2 balance warning is expected from the chemistry: the paper names H2 only in the conditions. H2 was not added as a species, since that would draw a reagent the paper does not show. Not checked in this folder: no `validation.json` is present, so the warning itself was not seen.

## Tool gaps

- No way to colour the bonds changed by hydrogenation. `new_bond_color` works from atom mapping of heavy-atom bonds (`figure_house.py`, `_color_new_bonds`); a hydrogenation adds only H, so the red ethyl bonds cannot be produced and the code leaves them black.
- Yield text: `>99%` is rendered as `>` followed by subscripted `99`. The cause is not fully confirmed. `format_yield` in `figure_house.py` only fills the template for a bare number (regex `_YIELD_VALUE`), so a `>` prefix leaves the text unchanged and the card's `{value}%` is never applied to it. The subscripting of `99` is a separate formula-digit rule that acts on the text. A `> 99%` retry did not finish in this session, so no workaround is confirmed.
- The `applied` report may overstate yield formatting: in the house branch (lines 291-294) `yield_format` is appended to `applied` whenever a yield and a template exist, without checking that `format_yield` changed the text. A `>99%` yield is therefore reported as formatted when it is not.
- No per-text formatting in `above` and `below` lines (bold catalyst number, superscript footnotes) and no per-line placement of the yield under the product label.
- No way to mark a gas (H2) as stated only in conditions, so the balance check always warns for hydrogenations.
- No generic `R` placeholder on a species; species need SMILES. A dummy-atom placeholder was not tested.
- The card's `measured` values (`bond_length_over_cap_height` 2.1, `line_width_over_bond_length` 0.09, `arrow_length_over_bond_length` 8.4, `label_font`) are stored by `house_styles.py` but no drawing code reads them. The wiley preset widths and lengths apply, and the card cannot set them.
- `conditions_split: reagents_above_solvent_below` is skipped by the code (`figure_house.py`, "the brief's above/below lines are kept as given"). The card cannot move a reagent above or below the arrow; the placement depends entirely on how the brief is written.
- `arrow_style` and `label_font` are not applied by the code either, so those card conventions have no effect on the drawing.
- Scope panels take only the base preset (per the tool documentation), so the card's bold labels and yield conventions would not reach a scope grid. Not tested here.
- Render time: `--render` waited more than 20 minutes on the ChemDraw lock during this run (other jobs were holding ChemDraw); the first render completed, the second did not finish.

## Replay

```
python skill/chemdraw/scripts/cdx.py py skill/chemdraw/assets/house-styles/wiley_angew/replica/wiley_angew-03/replay.py NEW_DIR
python skill/chemdraw/scripts/cdx.py render NEW_DIR/figure.cdxml
```

`replay.py` runs `draw_figure` on `brief.json` offline and writes `figure.cdxml` and `validation.json`. Compare `rendered.png` (1200 px wide copy of the first render) with `reference.png`.

## Audit

Both images and the card were checked; the toolkit code was read for each convention claimed. Corrections made above:

- Conditions split was marked matched. The layout matches only because `brief.json` lists the lines by hand; `figure_house.py` skips this convention. KOtBu, a reagent, sits below the arrow, which the card's reagents-above rule does not allow.
- Arrow style and font were marked matched on a visual check only. The code applies neither, and "plain" is not defined on the card. Both are now not matched.
- "Line widths look thinner" was an impression from a downscaled copy (1200 px against 2085 px). It is not a measurement and is now stated as unmeasured.
- The yield failure has a cause the first draft did not name: the card template does not apply to a `>` prefix at all, so the subscript rule is only part of the problem.
- The H2 balance warning is asserted but no `validation.json` is in this folder, so it is unchecked.
- Left as stated: the yield format, yield placement, bond/cap ratio, arrow length, and the new-bond and substrate colour rows are not matched, and the label face, label colour, Kekule and reagent colour rows match by eye.
