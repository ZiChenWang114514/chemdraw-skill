# uspto_patents crop 05: Scheme I (Hadida-Ruah et al., US 9,732,080 B2)

Source: Hadida-Ruah et al. (Vertex), "Modulators of ATP-binding cassette transporters", US 9,732,080 B2, 2017, Scheme I. US patent, no DOI. Licence: public domain (US patent), as recorded in the house-style card.

Drawing style: the `uspto_patents` house style (`style` in `brief.json`, base preset `j_mol_mod`). `cdx.py styles uspto_patents` prints the card.

Figure type: `reaction_scheme`.

## What is reproduced

The three-arrow scheme from the crop, reduced to what `draw_figure` can express:

- the starting acid (drawn as 1-phenylcyclopentane-1-carboxylic acid) with arrow a to the acid chloride (SOCl2, DMF (cat.), DCM), an unlabelled intermediate;
- arrow c from the same acid to product I (amide, HNR^NAr^1, HATU, TEA, DCM/DMF), labelled with a plain Roman I;
- the letters a and c above their arrows, the conditions as text under each arrow; the title "Scheme I" is in the brief but is not drawn (see Tool gaps).

Arrow b (HNR^NAr^1, pyr., from the acid chloride to I) is not drawn; see Tool gaps.

Structures are concrete stand-ins for the paper's generic formula. The phenyl ring carries no (R^XX)_X substituents, ring A is a plain cyclopentane, and the amide nitrogen carries a methyl in place of R^N with a phenyl in place of Ar1. Both structures were read from the crop by eye; no OCSR was run.

## Replay

```
python skill/chemdraw/scripts/cdx.py py skill/chemdraw/assets/house-styles/uspto_patents/replica/uspto_patents-05/replay.py NEW_DIR
python skill/chemdraw/scripts/cdx.py render NEW_DIR/figure.cdxml
```

`replay.py` runs `draw_figure` on `brief.json` without network access and writes `figure.cdxml` and `validation.json`. `rendered.png` is the desktop ChemDraw rendering (downscaled to 1200 px wide); compare with `reference.png`.

## Convention check

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| underlined, centred scheme title (Scheme I) | underlined and centred above the scheme | `title` is given in the brief but no layout draws it; no underline | no |
| generic groups and ring placeholders on intermediates (R^XX, R^N, Ar1, ring A loop) | drawn | not drawn; concrete phenyl, cyclopentane and N-methyl stand-ins | no |
| lower-case letters beside arrows | a, b, c beside three arrows | a and c above their arrows (a is not beside the vertical arrow); b not drawn | partial |
| reagents keyed to the letters in a footnote line under the scheme | full footnote a) ... b) ... c) ... | no footnote line; reagents set as text under each arrow | no |
| final product labelled with plain Roman I | plain I under the product | plain I under the product | yes |
| no yields | none | none | yes |
| no colour, black line art | black | black | yes |
| compound label face plain, colour #000000 | plain | plain, black | yes |
| Kekule aromatic rings (top-level) | Kekule | Kekule | yes |
| plain arrow style | plain solid arrowheads | solid heads, the tool default (the card's arrow_style is not read; only the bold option is coded) | yes (output only) |
| reagent text colour #000000 | black | black | yes |
| Times serif atom labels | Times | serif face from the ACS default label font (the card's label_font is not read) | yes (face only) |
| arrow length 4.0 bond lengths (card value, from crop 06) | short lettered arrows, about 1.3 bond lengths (85 px over 65 px in this crop) | arrows about 12 bond lengths (estimated from the render), set by the length of the condition text | no |
| bond length 3.0 cap heights (card value) | about 3.1 (65 px over 21 px) | about 2 to 2.5 by eye; not measured | no |
| single layout: vertical arrow down, arrow right, a third arrow from empty space | triangle; arrow b starts from nothing | divergent layout: vertical trunk with two horizontal arrows, no arrowhead on the trunk, no third arrow; no triangle layout exists in the tool | no |
| line weight 0.047 of bond length (card value) | 3 px over 62 px on the paper | not applied; not measured on the replica | no |
| atom label size 7.5 pt (card estimate) | labels look larger than the paper relative to the bonds | not applied; ACS default label size | no |
| no overlapping bonds | none | N-methyl bond of I runs into the upper phenyl ring | no |

Matched 8 of 18 rows (see the Audit note).

## Differences from the paper

- Structures: the paper's generic formula (R^XX substituents on the phenyl, ring A as an open loop, R^N and Ar1 on the amide N) is replaced by concrete stand-ins. The acid chloride is drawn as a concrete structure; the paper draws it generic and unlabelled.
- Arrow b is missing. The paper draws it as a short diagonal arrow with no drawn start; the replica cannot draw a product from two steps (see Tool gaps).
- Title: the paper underlines "Scheme I"; the replica has no visible title.
- Footnote: the paper gives the reagents once in a footnote keyed to a, b and c. The replica puts each reagent set under its arrow, and it puts the amine as text ("HNRᴺAr¹" with Unicode superscripts).
- Arrows: the paper's arrows are short (about 1.3 bond lengths); the replica's arrows are long and sized to the text under them.
- Bond length: the replica uses the j_mol_mod preset bond length; the card's measured proportion of bond to label height is not applied, so labels look large by comparison.
- The N-methyl bond of product I runs into the upper phenyl ring (visible in rendered.png). The lint step did not flag it because it does not test a molecule's bonds against its own rings (see Tool gaps).

## Tool gaps

- Scheme title: the `title` key is stored on the scheme descriptor, but no drawing code under `render/` reads it, so no layout draws it (the render has no "Scheme I"). No underline option for titles.
- Footnote line: a reaction scheme has no footnote field (only scope panels take `footnotes`), so a letter-keyed footnote under the scheme cannot be drawn.
- Arrow length: the house style's `arrow_length_over_bond_length` is not applied; arrow length follows the condition text. No option for a short lettered arrow.
- Bond length: the house style's measured `bond_length_over_cap_height` is not applied; the base preset bond length is used.
- Generic groups: no variable-group labels (R^XX with an X subscript, R^N, Ar1) and no ring placeholder (a loop or circle with A inside). Concrete SMILES only.
- Superscripts in condition text: Unicode superscripts (U+1D3A, U+00B9) render correctly in this run. The caret syntax was not tested in this case (the brief has no caret), so whether it prints literally is unverified.
- Two-step product: a product made by two steps is refused ("Species I is produced by more than one step"), so the AC to I step (arrow b) cannot be expressed with the triangle. A floating arrow with no drawn start is not supported either.
- Overlap check: the lint step reported no issues although the N-methyl bond crosses the upper phenyl ring in the render. `figure_lint.py` pairs separate objects (fragments, arrows, labels) and does not test a fragment's own bonds against its own rings, so this miss is a tool gap. `validation.json` is not in this folder, so the lint result itself is unverified here.
- Balance: the amine and SOCl2 are text conditions, so both steps report `balanced: false` (missing Cl, missing C7H7N). Correct for this drawing, but the warnings are noise for a scheme whose reagents sit in text. `validation.json` is not in this folder, so the balance values are unverified here.
- Card measurements: `line_width_over_bond_length`, `bold_width_over_bond_length`, `label_font`, `atom_label_size_pt_estimate`, `bond_length_over_cap_height` and `arrow_length_over_bond_length` are not read by any code under `toolkit/cdxml_toolkit`. Only the convention keys (label face and colour, reagent colour, yield, conditions, aromatic rings and similar) are applied. So line weight, label size and label font cannot follow the card; the replica named only the arrow and bond length.
- Layouts: the layout set is linear, sequential, serpentine, divergent, stacked-rows, convergent and catalytic-cycle. None draws the paper's triangle (arrow down, arrow right, third arrow from empty space), so this layout cannot be reached from the brief.
- Step and product labels: a step's `above` and `below` lists are the only text placement, so a letter cannot sit beside a short vertical arrow, and there is no position field for a product label.
- Arrow style and size: the card's `arrow_style` is not read (only `bold` has a code path), and arrowhead size and line width cannot be set from the brief.

## Audit

Checked against `reference.png`, `rendered.png`, `brief.json`, the card and the code paths named above. Corrections made in this pass:

- The scope section listed the title "Scheme I" as drawn. It is not drawn.
- The letters a and c sit above their arrows, not beside them.
- The layout row is no, not partial: the tool has no triangle layout, and the drawn layout differs from the paper.
- The Times and plain-arrow rows match on output only. The house style does not set either (the face is the ACS default and the arrow is the tool default), so they are marked as such.
- The caret superscript syntax, the lint result and the balance result were not verified in this case; `validation.json` is not in the folder.
- Three rows were missing from the table (line weight, label size, N-methyl overlap). They are added and marked no.
- Matched count: 8 of 18. Of the eight matched rows, two (compound label face and colour, reagent text colour) come from the house style; the other six match by the tool's defaults.
- Not measured: line weight, label size and arrowhead size. The estimates are by eye.
