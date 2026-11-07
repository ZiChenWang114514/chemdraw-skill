# Angustmycin C to angustmycin A: one-step AgmF dehydration (Fig. 3)

Source: Miller et al., *Nat. Prod. Rep.* **2024**, purine nucleoside antibiotics review, Fig. 3. DOI: [10.1039/d3np00051f](https://doi.org/10.1039/d3np00051f).

Licence: CC BY 3.0, as recorded on the `natural_product_reports` card. The reference crop is reproduced under that licence.

Drawing style: the `natural_product_reports` house style in `brief.json` (base preset `rsc`, bold compound labels, thin plain arrow, Kekule rings). Figure type: `biosynthesis`.

## What is reproduced

The single enzymatic step at the top of Fig. 3: angustmycin C (21) is converted by AgmF into angustmycin A (3), with the loss of water. The two structures are drawn from the SMILES below, the enzyme name is written above the arrow, and both compound labels are shown with their paper numbers. The title line of the crop is not drawn (see below).

| Compound | SMILES in `brief.json` | Source of structure |
| --- | --- | --- |
| Angustmycin C (21) | `OCC1OC(CO)(n2cnc3c(N)ncnc23)C(O)C1O` | read from the crop; formula C11H15N5O5 (RDKit) |
| Angustmycin A (3) | `C=C1OC(CO)(n2cnc3c(N)ncnc23)C(O)C1O` | read from the crop; formula C11H13N5O4 (RDKit), = 21 minus H2O |

Stereochemistry is not encoded, and this is a gap in the replica. The paper draws stereochemical bonds that are legible at this crop size: a bold wedge from the quaternary carbon to N9, hashed bonds from it to its CH2OH and from the ring to its two OH groups, and in angustmycin C a bold wedge to the blue CH2OH. The replica draws every bond plain. The case does not assign an absolute configuration in the text, but the drawn wedges and hashes should be transcribed as drawn.

No OCSR run was made for this crop; the structures were written from the drawing and checked with RDKit.

## Replay

```
python skill/chemdraw/scripts/cdx.py py skill/chemdraw/assets/house-styles/natural_product_reports/replica/natural_product_reports-04/replay.py NEW_DIR
python skill/chemdraw/scripts/cdx.py render NEW_DIR/figure.cdxml
```

`replay.py` runs `draw_figure` on `brief.json` offline and writes `figure.cdxml` and `validation.json`. Compare the render with `reference.png`; `rendered.png` is the render of the first and only try (ChemDraw, `--render`).

## Comparison

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| compound labels bold (`compound_label_face: bold`) | bold numbers in parentheses; names not bold | whole label bold, including the name | no |
| compound label colour `#000000` | names dark blue, numbers black | all black | no (card value conflicts with crop 04, which shows dark blue names) |
| trivial name italic dark blue `#074383` + bold number in parentheses (biosynthesis signature) | italic dark blue name, bold (21) and (3) | name bold black, number in parentheses bold | no |
| `compound_label_italic_suffix: false` | italic trivial name before the bold number | no italic text anywhere in the label | no (the paper's label has an italic name, so "no italic suffix" does not describe it) |
| `arrow_style: plain` | thin plain arrow | thin plain arrow | yes |
| `aromatic_rings: kekule` | Kekule adenine | Kekule adenine | yes |
| `reagent_text_color: #000000` | enzyme name in bold dark blue | enzyme name in plain black | no (card value is black; `figure_house.py` paints non-black values, so this is a card setting) |
| enzyme name above the arrow (biosynthesis) | AgmF above the arrow | AgmF above the arrow | yes (position only; box, weight and colour differ) |
| enzyme name in a rounded box on the arrow | rounded box around AgmF | plain text, no box | no |
| by-product on a small curved arrow below the arrow (biosynthesis) | H2O on a curved arrow leaving the arrow | H2O as plain text below the arrow, no curved arrow | no |
| by-product position | H2O under the right end of the arrow, beside the curved arrow | H2O centred under the arrow | no |
| atoms changed by the enzyme coloured (biosynthesis, blue in crop 04) | dark blue CH2OH carbon and exocyclic =CH2 | black | no |
| `new_bond_color` (card `null`; red appears only in crop 01) | not applicable to this crop | not applied | n/a |
| `yield_placement: under_arrow` | no yield on this step | no yield given | n/a |
| `abbreviate_groups` (Me, CO2Et) | no such group | none present | n/a |
| `highlight_fill` (null for this figure type) | none | none | n/a |
| connectivity: ring O, C2 with N9 and CH2OH, C3/C4 OH, C5 CH2OH and exocyclic alkene | as drawn | as drawn | yes |
| stereochemistry (wedges and hashes) | bold wedge to N9, hashed bonds to the quaternary CH2OH and to the ring OH groups; bold wedge to the blue CH2OH in angustmycin C | all bonds plain | no |
| adenine orientation | imidazole above the pyrimidine, NH2 at upper right | imidazole below, NH2 at lower right | no |
| title line (bold italic dark blue) | present at the top of the crop | absent from the render; the brief passes it, the saved CDXML is not in this folder | no |
| proportions: label size vs bond length, line weight | cap height about 13 px over a bond about 31 px (ratio about 2.4, rough pixel estimate) | cap height about 19 px over a bond about 50 px (ratio about 2.6, rough) | not confirmed (line weight not measured) |
| arrow length | about 4.8 bond lengths (149 px over about 31 px, rough) | about 5.0 bond lengths (249 px over about 50 px, rough) | roughly similar; not counted |

Count for `result.json`: 10 card conventions claimed for this figure type (the rows for labels, label colour, trivial-name formatting, italic suffix, arrow, Kekule rings, reagent colour, enzyme above the arrow, by-product arrow and changed-atom colour); 3 match (plain arrow, Kekule rings, enzyme above the arrow, by position only). The italic-suffix row no longer counts as a match. `result.json` is not in this folder, so the count is taken from this file.

## Differences from the paper

- The title line "Enzymatic C5'-C6' dehydration to complete angustmycin A biosynthesis" was passed in the brief but does not appear in the saved file or in the render.
- AgmF is plain text above the arrow. The paper puts it in a rounded box on the arrow.
- H2O is plain text below the arrow. The paper draws it on a small curved arrow leaving the arrow; the tool cannot draw that for a step with a missing by-product (see Tool gaps).
- Every atom and bond is black. The paper colours the carbon and exocyclic alkene that the enzyme changes dark blue.
- Labels are bold throughout, black. The paper sets the trivial names in italic dark blue and only the numbers in bold.
- No stereochemistry: the paper's wedges and hashes are omitted (see above).
- The adenine is flipped relative to the paper: the imidazole is below the pyrimidine and NH2 sits at the lower right, where the paper has the imidazole above and NH2 at the upper right.
- H2O sits centred under the arrow; the paper places it under the right end of the arrow.

## Tool gaps

- No curved by-product arrow for a biosynthesis step. `draw_figure` only takes text lines below the arrow. A by-product that is not a product of the step is reported as unbalanced and is not drawn, so the brief keeps `below: ["H2O"]` as text and the report warns: "Step 1 does not balance as drawn: the products lack H2O (water)".
- No rounded enzyme box on the arrow. `above` lines are plain text with no frame option. The toolkit does have a `rounded_rectangle` option, but only for catalytic-cycle figures (`publication/house_styles.py`, lines 65 and 113), not for reagent text.
- No colour for atoms or bonds changed by the enzyme in a biosynthesis step. `new_bond_color` works by atom mapping for formed bonds only, the card leaves it null, and this step changes a bond order (C5-C6 becomes a double bond; C5-H and C6-O are lost) rather than forming a new bond.
- No mixed formatting inside one label at the brief level: the tool cannot set an italic, dark blue name followed by a bold number. The CDXML writer does emit several text runs per label (`cdxml_builder.py`, line 371), so the limit is in the brief keys, not the file format.
- The `title` key is accepted and passed into the scheme descriptor (`mcp_runtime/figure_draw.py`, line 205), but the render shows no title. The claim that the saved CDXML lacks it cites `figure-try1.cdxml`, which is not in this folder, so the saved file was not re-checked here; the cause was not diagnosed.
- Stereochemistry is not a missing tool capability. `cdxml_builder.py` maps bond stereo flags to `WedgeBegin` and `WedgedHashBegin` (lines 148 to 150), and wedges are set from stereo SMILES (lines 716 and 792). The replica omitted the drawn wedges and hashes; it did not hit a tool limit.
- By-product placement: `above` and `below` lines are centred under the arrow, and the brief has no key to place text at an arrow end.
- Structure orientation: the brief keys read in `figure_draw.py` (kind, style, max_width, species, steps, layout, title) include no per-species orientation or rotation key, so the base is laid out by the tool and the replica's adenine is flipped.
- Curved arrows: `figure_draw.py` has a mechanism path with curved electron-pushing moves (around line 749). Whether that path could draw a by-product arrow for a biosynthesis step was not checked.
- Reagent and compound label colours are not a tool gap. The card sets `reagent_text_color` and `compound_label_color` to `#000000`, although crop 04 and the card's own notes show dark-blue text. `figure_house.py` (lines 356 to 365) paints non-black reagent text, so a card change would give the dark-blue enzyme name.

## Audit

Re-checked on 2026-11-07 against `reference.png`, `rendered.png`, `brief.json` and the card `publication/house_styles/natural_product_reports.json`, with zoomed crops and rough pixel measurements.

- The stereochemistry sentence was wrong. The crop shows wedges and hashes on both molecules, and the replica draws none. Stereo is not a missing tool capability (see Tool gaps).
- The italic-suffix row was an overclaim. The paper label has an italic name, so the row is now "no".
- The `reagent_text_color` and `compound_label_color` rows fail against the paper, and the cause is the card's `#000000` values, not the tool.
- The proportions row was "yes (visual only)" with no measurement. Rough estimates give a label-to-bond ratio of about 2.4 in the paper and about 2.6 in the replica, so it is marked not confirmed.
- The arrow-length row was "not checked". Rough estimates give about 4.8 and 5.0 bond lengths, close to the card's 4.9; it is noted but not counted.
- The adenine orientation and the H2O placement differ from the paper and were missing from the table. Both are now rows.
- The count goes from 4 of 10 to 3 of 10: plain arrow, Kekule rings, and enzyme position above the arrow.
- Unverified in this audit: the saved `figure-try1.cdxml` and `validation.json` are not in this folder, so the title-omission and the unbalanced-step warning were checked only through the render and the text of the case.
