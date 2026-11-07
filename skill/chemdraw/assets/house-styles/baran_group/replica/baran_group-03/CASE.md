# Baran group, Nature 2026: C-glycoside products 1, 2, 30 (Figure 2b, first row)

Source: Baran et al., *Nature* **2026** (C-glycoside synthesis through radical cross-coupling of glycohydrazides). DOI: [10.1038/s41586-026-10807-x](https://doi.org/10.1038/s41586-026-10807-x).

Licence: CC BY 4.0. The reference crop is `evidence/baran_group-03.png` of the `baran_group` card. The card lists it as Figure 2b, first row.

Figure type: `reaction_scheme` (as assigned for this crop). The card has no `figure_types` section, so the scheme conventions are the top-level `conventions`.

## What is reproduced

The crop shows three products (1 dapagliflozin, 2 empagliflozin, 30 canagliflozin) under an "Approved drug" header, each with a yield line. The crop has no reaction, so the replica draws the step that forms product 1 from the same paper: glucosyl hydrazide 25 and aryl iodide 26 give 1. The conditions are the boxed entry of Figure 2a (Ni(dme)Cl2 20 mol %, L1 20 mol %, TMG 3 equiv, DMSO 0.1 M, 70 °C). The yield, 88%, is the value printed for 1 in the crop. The structures of 25 and 26 come from the sibling panel of the figure and were not read from crop 03.

Structures used (SMILES in `brief.json`):

- 25: `OC[C@H]1O[C@@H](NNS(=O)(=O)c2ccc(C)cc2)[C@H](O)[C@@H](O)[C@@H]1O` (β-glucosyl hydrazide, β assumed from the β-selectivity of 1; not read from the figure).
- 26: `CCOc1ccc(Cc2cc(I)ccc2Cl)cc1`
- 1: `CCOc1ccc(Cc2cc([C@@H]3O[C@H](CO)[C@@H](O)[C@H](O)[C@H]3O)ccc2Cl)cc1` (RDKit: C21H25ClO6, MW 408.9, matching dapagliflozin).

Not reproduced: the product row itself (2 and 30 and their "Approved drug" header and "[Previous]" lines), the other rows of Figure 2b, and the ligand L1 structure (named only).

Brief: `brief.json` (the `max_width` 420 try; the layout did not change between 504 and 420, see below). Replay: `replay.py`.

## Tries

1. `kind: "scope"` with the three products 1, 2, 30 and their yields. The report says the house conventions apply to schemes only, and the base preset was applied. Native rendering returned `resource_busy` after 175 s and was not retried. It is not kept as a case file.
2. `reaction_scheme` for 25 + 26 → 1 with `max_width` 504. Rendered (`try2.png`). The layout check reported 612 pt against the 504 pt budget. The step warning says the step does not balance: the products lack C7H9IN2O2S. Nothing was added to the drawing.
3. Same brief with `max_width` 420. The first render timed out at 300 s. The retry rendered. The layout is still 612 pt against 420 pt. The atom-balance warning is unchanged. This is the `rendered.png` kept here.

## Comparison

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| compound_label_face: bold | bold numbers `1`, `2` and `30` | mixed: `25` and `26` have heavier strokes (about 3 px), the product label `1` has regular strokes (about 2 px, as the regular `Cl` label). The report says bold was applied to all | no |
| compound_label_color: #000000 | black | black | yes |
| yield_format: {value}% | `88%` | `88%` | yes |
| yield placement (card: null) | under the product label, with `(β:α > 19:1, from ArI)` | above the arrow, after the conditions | no |
| conditions_split: reagents above, solvent below | catalyst and base above, solvent and temperature below (Fig. 2a) | `Ni(dme)Cl2`, `L1`, `TMG` above, `DMSO (0.1 M), 70 °C` below | yes |
| substrate_layout: inline_plus | no reaction in the crop, nothing to compare | 25 + 26 inline | not verifiable (not counted) |
| abbreviate_groups | `OEt` is abbreviated on product 1 in the crop | `OEt` drawn expanded as O–CH2–CH3; `OEt` is not in the card's `abbreviate_groups` list or in the tool's ABBREVIATIONS table | no |
| aromatic_rings: kekule | Kekulé rings | Kekulé rings | yes |
| new_bond_color: #8B1A1A | purple (card note: "redrawn to journal style") | dark red bond to the aryl ring | no |
| highlight_fill: #BBF6F4 | no highlight box | teal fill on the sugar ring of 1 | no |
| reagent_text_color: #000000 | black | black | yes |
| arrow_style: plain | no arrow in the crop | plain arrow | not verifiable (not counted) |
| show_plus_sign: true | no reaction in the crop | plus sign between 25 and 26 | not verifiable (not counted) |
| signature: light grey panel #EDEDEF | crop background is white | background is pure white, no #EDEDEF pixels; the card says every scheme panel has the grey panel | no |
| signature: navy title bar #0C0C84 | absent in the crop | absent (no navy pixels); the card says every scheme panel has the title bar | no |
| signature: blue lightning bolt on the arrow | not electrolysis, so the card's feature does not apply | none drawn | n/a (not counted) |
| signature: blue bold notes #0C0CFC | no scale or comparison notes in the crop | none drawn | n/a (not counted) |
| signature: bold, large compound labels | bold labels, close to atom-label size | labels are not uniformly bold (see row 1) and are not large | no |
| measured: bond_length_over_cap_height 2.2 | 12.5 px / 6 px = 2.1 | about 2.0 by eye (cap height 14 px); bond length not measured precisely | not verified (not counted) |
| measured: line_width_over_bond_length 0.07 | 1 px / 12.5 px = 0.08 | not measured | not verified (not counted) |

Corrected count: 5 of 13 applicable rows match (label colour, yield format, conditions split, Kekulé rings, reagent text). The replicator's 12 of 17 is overstated, see the Audit note. Rows marked "not verifiable" or "n/a" are not counted.

## Differences from the paper

- The crop is a three-product panel with no arrow. The replica is a single coupling step from the same paper, using the Figure 2a conditions. The step is therefore not part of the crop.
- Bond colour: the paper's new C–C bond is purple. The replica uses the card's dark red.
- The product ring has a teal highlight box in the replica. The crop has none.
- Compound labels are mixed in the replica: `25` and `26` look heavier than `1`, and none of them matches the bold, large labels of the crop.
- `OEt` on product 1 is abbreviated in the crop and drawn expanded in the replica.
- Yield: the paper places 88% under the product label with a β:α note. The replica places it above the arrow.
- The "Approved drug" header, the "[Previous]" lines and the footnote superscripts are not drawn.
- The by-product is not drawn. The paper does not give its structure in the crop, and the atom-balance check flags the omission.
- The layout is 612 pt wide in the replica, against the 504 pt default and the 420 pt budget, so it is wider than the paper's panel.

## Tool gaps

- Scope panels take no house conventions. The report says "house conventions apply to schemes only", so the crop's product-panel layout cannot carry the card at all.
- `new_bond_color` and `highlight_fill` cannot be set per figure type or switched off in a brief. The teal product highlight appears whenever the card has `highlight_fill`, even where the crop has none.
- No yield placement under a product label in a single-step scheme. Only above or below the arrow is available.
- `max_width` is not enforced: the figure is 612 pt at both 504 and 420, and the tool reports only a warning.
- For a step whose by-product the brief does not name, the balance check flags it and nothing is added. There is no field to declare a by-product that the source does not show.
- Bold compound labels are reported as applied, but the render shows mixed weight. `figure_house` appends `compound_label_face=bold` to the applied list whenever the convention is set. It does not check that a label was found (`_label_of` can return None silently), and it does not read the render back.
- Missed by the replicator: the abbreviation table (`publication/house_styles.py`, `ABBREVIATIONS`) has no `OEt` entry, and a brief cannot add groups, so `OEt` cannot be abbreviated.
- Missed by the replicator: the card's `measured` block (bond/cap ratio 2.2, line width 0.07, bold width 0.2, label font Helvetica, arrow length 5.7) is stored and validated, but no drawing code reads it. The drawing uses the acs1996 base, and labels use Arial (`constants.py`).
- Missed by the replicator: no toolkit code draws the grey panel or the navy title bar (a case-insensitive search for `EDEDEF` and `0C0C84` finds nothing), and no brief field requests them.
- Missed by the replicator: `max_width` gets one relayout pass (`figure_draw._relayout`: narrow once, break condition lines once), and whatever is still too wide is returned as a warning.
- ChemDraw native rendering: `resource_busy` after 175 s (scope try), and a 300 s timeout on try 3 that passed on retry.

## Audit

Checked by the auditor against `reference.png`, `rendered.png`, `CASE.md`, `brief.json`, the card and the toolkit code. Colour and background were checked by pixel count. Label weight was checked by comparing stroke widths against the regular `Cl` label in the same render.

- Overclaims corrected in the table:
  - The compound-label row said all three labels were regular. `25` and `26` are heavier than `1`. The face is mixed, and the tool reports bold as applied anyway.
  - The abbreviation row said the crop has no abbreviated groups. The crop shows `OEt`, and the replica draws it expanded.
  - The substrate-layout, arrow and plus-sign rows were counted as matches against features the crop does not contain. They are now not verifiable.
  - The grey-panel and navy-title-bar rows matched the crop's absence of these features. The card says every scheme panel carries them, and the replica has neither. They are now no.
  - The lightning-bolt and blue-notes rows describe conditional features that do not apply to this step or to this replica. They are now n/a.
- Corrected count: 5 of 13 applicable rows (label colour, yield format, conditions split, Kekulé rings, reagent text), against the claimed 12 of 17.
- Not verified from this folder: the bond/cap proportion (about 2.0 by eye against 2.2), the line weight, and the 612 pt layout. The folder has no tool report, no `figure.cdxml` and no `try2.png`, so the pt figures cannot be checked here. The rendered image is 1200 × 178 px.
- Tool gaps the replicator did not list: the `OEt` abbreviation gap, the unused `measured` block, the unverified bold `applied` report, the one-pass relayout, and the missing grey-panel and title-bar support (listed above under Tool gaps).
