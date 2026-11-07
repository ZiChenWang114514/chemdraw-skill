# Organic Letters: two-step, one-pot alcohol to alkylsilane (abstract graphic, crop 06)

Source: Oestreich et al., *Org. Lett.* **2025**, *27*, 3686 (One-pot sequential alcohol activation and nickel-catalyzed cross-electrophile coupling with chlorosilanes). DOI: [10.1021/acs.orglett.5c00830](https://doi.org/10.1021/acs.orglett.5c00830).

Licence: CC BY 4.0. Reference crop `reference.png` is the abstract graphic (PDF page 1, 300 dpi) reproduced under that licence.

Drawing style: the `org_lett` house style (`brief.json` `"style": "org_lett"`; base preset ACS Document 1996); see `cdx.py styles org_lett`.

Figure type: `graphical_abstract` (the card's crop 06 entry, the single-line TOC scheme).

## What is reproduced

The whole single-line scheme: alcohol to bromide (bracketed intermediate) to alkylsilane, with both sets of conditions above and below the arrows and the yield line under the product. The pale blue abstract band is not drawn: the card says it belongs to the journal's abstract box, not to the graphic.

## Structures (stand-ins, not the paper's compounds)

The paper's R is a generic alkyl group and SiR3 a generic silyl group. draw_figure refuses dummy or generic atoms, so the replica uses a concrete stand-in with the same R-CH2CH2-X skeleton:

| ID | SMILES in brief.json | Note |
| --- | --- | --- |
| alc | `CCCCCCO` | hexan-1-ol: R = n-Bu stand-in for the paper's R-CH2CH2OH |
| int | `CCCCCCBr` | bromide, drawn in square brackets (`ts_bracket` with an empty superscript) |
| prod | `CCCCCC[Si](C)(C)C` | SiMe3 stand-in for SiR3; the Cl-SiR3 reagent is written as text only |

SMILES were chosen to follow the scheme's skeleton; they were not read from OCSR. The brief uses `max_width` 760 (the default 504 wrapped the route onto two rows and drew the bracketed intermediate twice).

## Replay

```
python skill/chemdraw/scripts/cdx.py py skill/chemdraw/assets/house-styles/org_lett/replica/org_lett-06/replay.py NEW_DIR
python skill/chemdraw/scripts/cdx.py render NEW_DIR/figure.cdxml
```

`replay.py` runs `draw_figure` on `brief.json` offline and writes `figure.cdxml` and `validation.json`. `rendered.png` is the desktop ChemDraw render of the second brief (downscaled to 1200 px wide).

## Convention checks

Claimed rows are the card's `graphical_abstract` claims for crop 06 and the top-level conventions that are visible in this crop. The visible features the card does not claim follow them.

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| graphical_abstract crop 06: one-line scheme | one line, two steps | one line, two steps (`max_width` 760); proportions and orientation differ (see Audit) | yes (topology only) |
| graphical_abstract crop 06: reacting group red #FF0000 | OH red | OH black | no |
| graphical_abstract crop 06: introduced group blue #0080FF | SiR3 blue | SiMe3 black | no |
| graphical_abstract crop 06: "48 examples, up to 98% yield" under product | two lines: "48 examples" / "up to 98% yield" | one line, comma after "examples" | no (line break and comma both differ; the card's comma wording is not the paper's print) |
| top-level yield_placement under_product_label | yield line under the product | yield line under the product | yes |
| top-level yield_format "{value}%" | phrase, not a bare value | phrase kept verbatim | no (the phrase is not a value; the tool keeps it as given) |
| top-level conditions_split reagents above, solvent/temperature below | reagents above; NMP and r.t. below | reagents above; NMP and rt below | yes |
| top-level reagent_text_color #000000 | "Mn" in blue, other reagent text black | all black | no (the card's blanket claim does not hold for "Mn") |
| top-level arrow_style plain | plain arrows | plain arrows | yes |
| visible, not claimed: intermediate in square brackets | bracket around the bromide | square bracket present | partly (shape matches; strokes cross the Br and Me labels and the overlap check fails) |
| visible, not claimed: bold italic "two-step/one-pot" under the bracket | present | absent | no |
| visible, not claimed: bold bonds at the reacting heteroatom (C-O, C-Br, C-Si) | bold | normal width | no |
| visible, not claimed: new C-Si bond blue | blue | black (card null) | no |
| visible, not claimed: "r.t." wording | r.t. | rt (tool normalises it) | no |
| visible, not claimed: scheme proportions | about 725 x 185 px in reference.png (about 3.9:1) | about 1190 x 165 px in rendered.png (about 7.2:1) | no |
| visible, not claimed: orientation | R on the left, OH on the right; product R-CH2CH2-SiR3 with SiR3 on the right | HO on the left, Me on the right; Me3Si on the left of the product | no |
| visible, not claimed: red and blue colour | about 185 red and 380 blue pixels in reference.png | none in rendered.png | no |

Matched: 4 of 9 claimed rows (graphical_abstract scheme line, yield placement, conditions split, arrow style). The "48 examples" row is not matched: the paper sets two lines with no comma, the replica one line with a comma.

## Differences from the paper

- R and SiR3 are stand-ins (hexyl, SiMe3). The paper's generic groups cannot be drawn; the replica shows Me and Me3Si where the paper has R and SiR3.
- The reacting heteroatom bonds are normal width, not bold, and the group colours (red OH, blue SiR3, blue new C-Si bond) are not drawn. The paper's colours are per group, which the tool cannot assign.
- "Mn" is black; the paper sets it in blue.
- The "two-step/one-pot" caption under the bracket is absent.
- Conditions use "rt" (tool normalisation) rather than the paper's "r.t.".
- The yield line is one line; the paper breaks it after "48 examples".
- The pale blue abstract band is not reproduced (journal layout, outside the graphic).

## Tool gaps

- No per-atom or per-bond colour from the brief: `substrate_colors` paints whole substrate fragments, so the red OH cannot be drawn. A `new_bond_color` path exists (atom-mapped formed bonds) but it is only a house convention, which org_lett sets to null, so a brief cannot switch it on. Whether that path could colour the C-Si bond here is unverified; the Cl-SiR3 partner is text only, so the formed bond may have no mapped source atom.
- No per-run colour inside condition text: `reagent_text_color` is one colour for all reagent lines, so the blue "Mn" cannot be written.
- No bold-bond option for an individual bond. Bold width exists only for reaction arrows, through the house `arrow_style` "bold" (1.5 times the line width), not for bonds.
- No caption under a bracketed intermediate: `ts_bracket` takes `superscript`, `bracket_type` and `lip_size` (hook length), but no line under the bracket, so the bold italic "two-step/one-pot" line cannot be placed.
- The bracket margin is fixed (5 pt beyond the atom coordinates of the fragment, not its label extents), so strokes cross terminal labels such as Br and Me; `lint` reports this overlap after relayout and `checks_passed` stays false.
- No orientation control: the brief has no key to mirror or flip a structure, so the replica's HO sits at the left where the paper has R.
- No aspect-ratio control: `gap_scale` is internal and is widened only when lint finds an overlap; `max_width` is the only size input, so a single row cannot be made as wide-to-tall as the paper's (about 3.9:1).
- Generic atoms (R, SiR3 as dummy atoms) are refused, so the paper's generic groups cannot be drawn.
- Condition text is normalised (`r.t.` becomes `rt`) and cannot be kept as written.
- A yield text is set on one line only; there is no two-line centred option for "48 examples" over "up to 98% yield".
- Balance: each step is reported as unbalanced (missing Br and C3H9Si) because the Cl-SiR3 and Mn reagents are text, not species; the warnings name the missing species and nothing is added to the drawing.

## Audit

Checked against `reference.png`, `rendered.png`, `brief.json`, `org_lett.json` and the toolkit source (`mcp_runtime/figure_draw.py`, `figure_house.py`, `text_formatting.py`). A fresh offline replay of `replay.py` into a temporary folder gave `checks_passed: false`, one lint overlap (fragment 1035 with text 1120) after one relayout, and two balance warnings (missing Br and C3H9Si), as this note says.

Corrections made in this table:

- The "48 examples" row was marked matched. The paper prints two lines with no comma, so the row is now no, and the count is 4 of 9, not 5. The card's crop 06 wording ("48 examples, up to 98% yield") differs from the paper; `org_lett.json` was not edited.
- The one-line scheme row is kept for topology only. Proportions (about 3.9:1 in the paper, about 7.2:1 here) and orientation do not match.
- The bracket row is partly, not matched: the overlap check fails and the strokes cross Br and Me.
- The tool-gap list said nothing colours a new bond and that `ts_bracket` takes only a superscript. Both are corrected above. Bold width applies to reaction arrows, not to bonds.

Matched with limits:

- Yield placement: the yield sits under the product in both. The card's convention is written around a bold compound label, which crop 06 does not have.
- Conditions split and arrow style agree on placement and plain arrows. The wording (r.t. against rt) does not match, as listed above.

Not verified: line weight (no row claims it, and `rendered.png` is downscaled), the arrow-to-bond ratio of 7.6 (estimated by eye only), and label size relative to bonds.
