# Chem. Eur. J. 2023, Figure 1: substrate scope, R1 = Ph row (house style chemeurj)

Source: Anderson et al., *Chem. Eur. J.* 2023 (Gold-catalyzed cyclization of yndiamides with isoxazoles via alpha-imino gold Fischer carbenes). DOI [10.1002/chem.202302821](https://doi.org/10.1002/chem.202302821). Licence: CC BY 4.0 (from the house card). The crop is `evidence/chemeurj-03.png` and is copied here as `reference.png`.

Figure type: `substrate_scope` (grid). Card: `skill/chemdraw/assets/house-styles/chemeurj/README.md` and `toolkit/cdxml_toolkit/publication/house_styles/chemeurj.json`.

## What is reproduced

The R1 = Ph row of the scope, six products 2h to 2m, with the yields as printed and the bracketed footnote letters kept as text. The brief is `kind: scope`, `style: chemeurj` (base preset wiley, bond length 17 pt), one group heading "R1 = Ph", one field (yield), panel width 180 mm.

Not reproduced: the reaction header (1a plus isoxazole, 2.0 equiv, (ArO)3PAuNTf2 5 mol%, arrow with conditions above and below); the other rows (2b to 2g and 2n to 2s); the section tab and grey rules; the X-ray inset on 2g; the 5b / 5b' side product.

Structures were read by eye from the crop (no OCSR run). Pyrrole numbering as drawn: N-H at the bottom, C5 carries Ph (next to NH), C4 carries the acyl group, C3 and C2 each carry N(n-Bu)Ts. Acyl groups: n-butyl (2h), cyclohexyl (2i), cyclohex-1-en-1-yl (2j), 4-fluorophenyl (2k), 4-cyanophenyl (2l), 4-methoxyphenyl (2m). Product SMILES, for example 2h `CCCCC(=O)c1c(-c2ccccc2)[nH]c(N(CCCC)S(=O)(=O)c2ccc(C)cc2)c1N(CCCC)S(=O)(=O)c1ccc(C)cc1`, all parse in RDKit; they are in `brief.json`.

Yields as printed: 2h 83%, 2i 68%, 2j 59%[c], 2k 68%[c], 2l 47%[c], 2m 38%[a,c]. The footnote texts for a and c are not in the crop and are not drawn.

## Attempts

| try | change | outcome |
| --- | --- | --- |
| v1 | field label "Yield", panel 180 x 90 mm | refused: "Compound 2h exceeds page height" |
| v1 | panel 180 x 120 mm, `--render` | ChemDraw call exceeded the 300 s tool limit (desktop ChemDraw busy with other runs); one retry, same timeout; no PNG |
| v1 | panel 180 x 120 mm, no render | ok: 3 pages of 2 compounds, data binding and chemistry checks passed, readback matched 6 of 6 |
| v2 (final `brief.json`) | field with no label | ok, same packing; yield text reads "yield: 83%" (key name used as prefix) |
| v2 | panel 250 x 110 mm, no render | timed out before reporting; not verified |

`rendered.png` is not present: no native render was obtained. The output for the scope kind is a new folder (`page-001.cdxml`, ...), not one file.

## Replay

`replay.py` is the jacs-au script with a new docstring. It passes a file path as the output, while the scope kind takes a new folder (see the draw_figure signature; figure_scope.py uses the path as a folder name). It was not run on this brief. Replay the scope brief with `cdx.py draw brief.json NEW_FOLDER`.

## Convention check

Rows cover the card's substrate_scope conventions and signature features, plus the top-level conventions visible in the crop. Match: yes, partial, no, or unverified (not checked on a render).

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| scope_layout: grid | six products in one row (R1 = Ph), section tab above | three pages of two products (180 mm panel) | no |
| variation_color: null | sulfonamide N atoms drawn blue in the crop (blue #0080C0 pixels present in crop 03) | black (the scope path sets no colour) | no (the card's substrate_scope says null, but its own notes record blue heteroatoms in crop 03) |
| yield_format: {value}% | 83%, 68%, 59%[c] | "yield: 83%", "yield: 59%[c]" as built (the brief has no label); a field with `"label": ""` prints the bare value (publication/data.py `field_text`), not used and not rendered | partial (value format kept, prefix added as built) |
| selectivity_format: null | no selectivity in this row | not applicable | n/a |
| conditions_position: scheme_on_top | conditions on the arrow of a header above the grid | one plain text line above the panel (brief key `conditions`), no arrow or header | no |
| highlight_fill: null | no grey fill behind products | no fill | yes |
| signature: reaction header with conditions on arrow above grid | header with 1a and isoxazole, arrow, conditions | not drawn (scope kind has no header) | no |
| signature: sections separated by grey #808080 rules | grey rule above each row | no rules | no |
| signature: section titles bold navy #004080 | "R1 = Ph" bold navy on grey tab | "R1 = Ph" plain black text | no |
| signature: footnote letters in brackets after yields | [c], [a,c] | [c], [a,c] as text; legend not drawn | partial |
| compound_label_face: bold | bold labels 2h to 2m | plain labels (face 0) | no |
| compound_label_color: #000000 | black | no colour option in the scope path, so the default text colour applies; not checked on a render | unverified |
| yield placement under compound label, bold navy #004080 | under label, bold navy | under label, plain black | partial |
| abbreviate_groups: Ts, Ph, tBu, OMe | BuTsN, Ph, OMe as labels; CN and F as labels | full rings and chains | no |
| aromatic_rings: kekule | drawn as printed (not resolvable at crop size) | kekule SMILES input | unverified |
| bond length / label cap height 2.0 | about 2.0 measured on the crop (card: 123 px bond, 60 px cap height) | about 3.0 estimated (17 pt bond from the wiley preset; 8 pt Arial label, because the scope path drops the preset's 12 pt label size and the scope brief has no label-size key; cap height about 5.7 pt); not measured on a render | no (estimate) |

Claimed rows: 15 (n/a excluded). Matched (yes): 1.

## Differences from the paper

- No reaction header: the 1a and isoxazole substrates, the arrow, the conditions above and below the arrow, and the 2.0 equiv note are missing.
- One row of six, not a grid: the replica packs two products per page on three pages. The paper row is one line.
- Only the R1 = Ph row (6 of the 18 products 2b to 2s in this panel); the other rows are not drawn.
- Labels plain, not bold; yields plain text with a "yield:" prefix, not bold navy.
- The group heading is plain black text with no grey tab and no grey rules between sections.
- "Substrate scope" is added as a panel title (not in the paper) and repeated on each page, with "R1 = Ph (continued)" on later pages.
- Ph, OMe, CN and F are drawn as rings and BuTsN as full structures; the paper uses abbreviation labels.
- Heteroatoms are black; the paper colours the sulfonamide N atoms blue.
- The footnote legend (a, c) is not in the crop and is not drawn.
- Label size relative to bond length is estimated to differ from the card's 2.0 ratio.

## Tool gaps

- The scope kind has no reaction header: no substrate pair, no arrow with conditions above and below it, no equivalents line. Conditions are a plain text line only.
- The scope kind applies only the base preset. The report says "house conventions apply to schemes only" and `applied` is empty, so bold labels, navy yields, abbreviations and heading styles from the card are not applied.
- A group heading is plain text. There is no tab fill, no bold or colour option for headings, and no horizontal rule between groups.
- The yield field prints its label as a prefix by default ("yield: 83%" when the label defaults to the key). Setting the field label to `""` prints the bare value (figure_scope.py `_fields`; publication/data.py `field_text`). The brief as built does not use this, and it is not rendered, so it is not a gap in the tool.
- The panel title defaults to "Substrate scope", is repeated on every page, and "(continued)" is added to group headings on later pages. An empty title does not suppress it: figure_scope.py uses `brief.get("title") or "Substrate scope"`, so "" falls back to the default. No other brief key removes it.
- Page packing is by measured size and fixed page width. At 180 mm the six products go two per page; a single row of six was not produced. The code accepts width_mm up to 400, and the 250 mm attempt timed out without a result, so a one-row limit has not been shown either way.
- No per-atom or per-group colour for scope structures (heteroatom colouring in the crop).
- No abbreviation labels for Ph, OMe, CN, F, tBu, Ts or N(Bu)Ts in the scope kind.
- No bold label option for scope compound labels.
- Native rendering through desktop ChemDraw was not obtained: two `--render` calls hit the 300 s tool limit while other runs held ChemDraw (the cause is the replicator's account and was not checked).
- Label size is fixed at the layout default of 8 pt in scope panels. The wiley preset's 12 pt label size is dropped (figure_scope.py pops `font_size`), and the scope brief has no label-size key, so the 2.0 bond-to-label ratio cannot be set.
- No face or colour on any scope text. The page text objects carry only text, position and size (publication/layout.py), so the title, conditions, group headings, labels and values cannot be bold, navy or any other colour.
- House conventions are not applied to scope panels. figure_scope.py calls no figure_house step, so there is no hook for bold labels, navy yields, highlight fills, abbreviations or kekule rings; the aromatic_rings row is not enforced by the scope path.


## Audit

Audited against `reference.png`, `brief.json`, the chemeurj card and the toolkit code (`figure_scope.py`, `publication/layout.py`, `publication/data.py`, `chemdraw/style_presets.py`). No output of the replica runs is in this folder, so every statement about rendered output (the attempts rows, the readback, the `yield:` text, the native render) is the replicator's report and is not verified here.

Confirmed: the crop has grey section rules (rows 330 and 476 of `reference.png`), navy pixels (yields and section heading) and blue pixels (sulfonamide N); the yields as printed match; all six SMILES parse in RDKit; the wiley preset gives a 17 pt bond and a 0.75 pt line width (ratio 0.044; the card records 0.04).

Corrected: the crop shows 18 products (2b to 2s), not 12; the bare-value yield gap does not exist (a label of `""` prints the bare value); an empty title is blocked by the code, not merely untested; `conditions_position` is not matched (no arrow or header); the label colour note had no source; the variation_color row cited a non-existent "card errors" section. Added missed gaps: label size is fixed at 8 pt in scope panels, no bold or colour on any scope text, and no house-convention hooks (including no kekule step).

Matched count: 1 of 15 (`highlight_fill`, which matches by absence: card null, no fill in the crop, no fill step in the scope path). The count is the replicator's, but several reasons in the table were wrong or unsupported.

Not checked: the cause given for the ChemDraw timeouts (other runs holding the desktop), and whether the 90 mm attempt used `--render` (the tool-gap list says the first `--render` was refused for panel height; the attempts table does not say).
