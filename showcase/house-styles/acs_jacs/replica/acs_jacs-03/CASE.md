# Qing et al.: isotope-labelling row of Scheme 3 (control experiments)

Source: Qing et al., *Org. Lett.* **2024**, *26*, 9215. DOI: [10.1021/acs.orglett.4c03212](https://doi.org/10.1021/acs.orglett.4c03212). Licence: CC BY 4.0 (from the `acs_jacs` card). The reference crop `reference.png` is reproduced under that licence.

Drawing style: the `acs_jacs` house style (bold compound labels, Kekule rings, inline plus, reagents above and conditions below; base preset ACS Document 1996). The card has no `figure_types` section, so the top-level conventions are the only ones applied. The card's `measured` block is stored, but no drawing code reads it, so the geometry comes from the base preset alone.

Figure type: `reaction_scheme` (one reaction row of a two-row control-experiment scheme).

## What is reproduced

The lower row of the crop only: 4-bromophenyl isocyanide (**1a**) and TMS-N3 (**2**) with H2 18O (2.0 equiv) under the optimized conditions, giving [18O]-**3a** (68%). The structures are read from the crop and the scheme text:

| ID | SMILES in brief.json | Note |
| --- | --- | --- |
| 1a | `[C-]#[N+]c1ccc(Br)cc1` | 4-bromophenyl isocyanide; the crop shows an "NC" group |
| 2 | `C[Si](C)(C)N=[N+]=[N-]` | TMS-N3; the crop shows a "TMS-N3" label |
| [18O]-3a | `[18O]=C(N=[N+]=[N-])Nc1ccc(Br)cc1` | 4-bromophenyl carbamoyl azide with the isotope on the carbonyl O, as the caption and H2 18O reagent indicate |

The crop cuts off at the right edge, so the bromine on the product is only partly visible. It is taken from 1a (para-bromo, carried through the reaction). RDKit gives C7H5BrN4O for the labelled product, and the drawn structures match the brief (readback `matched`, 3 structures).

The top row (radical trapping, TEMPO, 1a + 2 giving 3a) is not drawn; see "Tool gaps".

## Replay

```
python skill/chemdraw/scripts/cdx.py py skill/chemdraw/assets/house-styles/acs_jacs/replica/acs_jacs-03/replay.py NEW_DIR
python skill/chemdraw/scripts/cdx.py render NEW_DIR/figure.cdxml
```

`replay.py` runs `draw_figure` on `brief.json` offline and writes `figure.cdxml` and `validation.json`. `rendered.png` is the ChemDraw rendering from the `draw` run with `--render` (1200 px wide copy); the audit did not re-render it.

## Convention table

`brief.json` draws the lower row. Claimed is the 15 card conventions plus the 4 measured values the card gives (bond over cap height, line width, label font, arrow length). The last two rows are visible in the crop but not claimed by the card, so they are not counted. Each "match" was checked against the reference crop, the rendered PNG and the drawn `figure.cdxml` (regenerated offline in a temporary folder).

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| compound_label_face bold | "1a", "2" and "[18O]-3a" bold | bold (CDXML face 1 on all three labels) | yes |
| compound_label_color #000000 | black labels | black | yes |
| compound_label_italic_suffix false | roman "3a" | roman | yes |
| yield_placement (card null; crop shows after the label) | "68%" after the product label, after a comma, italic grey-blue | "68%" is a second line of the below-arrow conditions text, in one text object with "optimized conditions" | no |
| yield_format {value}% | "68%" | "68%" | yes |
| conditions_split reagents_above_solvent_below | H2 18O above; optimized conditions below | same split (the yield also sits in the below block) | yes |
| substrate_layout inline_plus | 1a + 2 | 1a + 2 | yes |
| abbreviate_groups OMe (card) | no OMe in this row; NC, N3 and TMS appear as labels | nothing abbreviated: TMS drawn as Si(CH3)3, azide as N=N=N with charges, isocyanide as C(-)#N(+) | no |
| aromatic_rings kekule | Kekule rings | Kekule rings (11 double bonds in the CDXML: three per benzene ring, C=O, two per azide) | yes |
| new_bond_color null (card) | new C-N3 bond black and bold; the C-NH bond red | every bond thin and black | no |
| substrate_colors null (card) | substrate cores dark red, TMS-N3 dark blue; product core dark red, product N3 dark blue | all black (no coloured pixels in rendered.png) | no |
| highlight_fill null | none | none | yes |
| reagent_text_color #000000 | H2 and conditions black roman; 18O green; "optimized conditions" italic blue-grey | all black, roman | no |
| arrow_style plain | thin plain arrow | plain arrow, full solid head, 0.60 pt | yes |
| show_plus_sign true | plus between 1a and 2 | plus between 1a and 2 | yes |
| label_font Arial or Helvetica | sans-serif, Arial-like | Arial (font table). This comes from the acs1996 preset; the code does not read the card's measured label_font | yes |
| measured bond_length_over_cap_height 2.2 | 39 / 17 px, about 2.3 | 14.4 pt bond over 7.2 pt cap (10 pt Arial), 2.0; the replica's labels are about 15% larger relative to the bonds | no |
| measured line_width_over_bond_length 0.055 | 2 / 39 px, about 0.051 | 0.60 / 14.4 pt, 0.042 (not set by the tool) | no |
| measured arrow_length_over_bond_length 7.0 | 230 / 39 px (card evidence), about 5.9 | 104 / 14.4 pt, 7.2 | no |
| section header in italic blue between blue rules | present above the row | absent | no |
| note under product ("without TEMPO: 85%; with TEMPO: 0%") | present | absent | no |

Matched: 11 of 19 claimed. The new-bond row that was previously marked yes is withdrawn, because the paper's new bonds are not uniformly black. The label font matches, but only through the base preset.

Note on the yield row: a variant with the yield written into the product label (`[18O]-3a, 68%`, no `yield` field) is closer to the crop. It was checked with `draw` without `--render` (checks passed) but could not be rendered because the ChemDraw render lock was held by other runs. The audit did not re-check it. The card's own route to the same result (`yield_placement` set to `after_product_label` with `yield_separator`) is implemented in the code but was not tested, since the card is unchanged.

## Differences from the paper

- The figure is one row. The paper has two rows (radical trapping above, isotope experiments below) with a blue section header and rule for each.
- The isocyanide is drawn with formal charges (C-, N+) and the azide as N-=N+=N. The paper writes "NC" and "N3" as labels.
- TMS-N3 is drawn as a full trimethylsilyl azide, not as the "TMS-N3" label.
- The 68% yield sits under the arrow, inside the conditions block, not after the product label.
- Colours are not applied: dark-red substrate and product cores, dark-blue TMS-N3 and product N3, green 18O in the reagent, and the blue-grey italic "optimized conditions".
- The new C-N3 bond is bold in the paper and thin here. The C-NH bond is red in the paper and black here.
- The isotope is drawn on the carbonyl O as a superscript "18O". The paper keeps the O plain and gives the label only in the compound caption "[18O]-3a".
- Line weight is thinner than the paper's (0.042 vs about 0.051 of the bond length), and the arrow is longer (7.2 bonds vs 5.9; the card's evidence records 230 px over a 39 px bond).
- Labels are about 15% larger relative to the bonds (cap height over bond 0.50 here against 0.44 in the paper).

## Tool gaps

Each item was checked against the toolkit code. Items marked "card" are card-data choices, not missing tool capabilities.

- `draw_figure` cannot place two independent reactions in one figure. A brief with two steps that share the substrate species but give different products was refused: "The steps are not a linear route, a convergent route (arms that merge) or a set of reactions from one starting material, so they cannot be laid out" (`render/route_graph.py`). The stacked-row layout exists in `render_scheme` under the name `stacked-rows` (`render/parser.py`; the earlier name `stacked` was wrong), but `render_scheme` takes no house-style argument (`mcp_runtime/official_overrides.py`), so the two-row house layout is not available.
- Section headers are partly available. A section of a `stacked-rows` scheme takes a `label`, drawn as plain text at the left margin (`render/renderer.py`, section label block). What is missing is the italic blue styling, the horizontal rules, and house-style application to the header.
- No note text attached to a product (the "without TEMPO" line). Species and step keys in the brief have no note field.
- No per-run text colour or italic in the above or below lines. They are lists of plain strings, and no markup was found.
- Substrate colouring: the code colours substrate fragments when the card gives `substrate_colors` (`mcp_runtime/figure_house.py`). The card leaves the field null, although its own evidence records #800000 and #004080 for this family. That is a card gap. The real tool gap is that product fragments are never coloured (the loop skips products), and a colour applies to a whole fragment, so a dark-red core with a dark-blue N3 on the product cannot be drawn.
- No abbreviation labels for isocyanide NC or azide N3. The table's `CN` entry matches only nitrile (`[CX2]#[NX1]`), and there is no azide entry. TMS has an entry (`publication/house_styles.py`), but the card lists only OMe. The last part is a card gap.
- Yield placement: `after_product_label` and `yield_separator` are implemented (`mcp_runtime/figure_house.py`). The card leaves both unset, so the under-arrow default is used. A separate tool gap: the under-arrow yield is written into the same text object as the below-arrow conditions (the CDXML text object holds "optimized conditions" and "68%"), so it cannot be placed apart from them.
- Line width is not taken from the card's measured block, and nothing else reads that block either: bond over cap height, line width, label font and arrow length all come from the base preset. The brief has no line-width key.
- Arrow length follows the bond length (104 pt on a 14.4 pt bond), and the brief has no arrow-length key.
- The isotope label is drawn as a superscript on the atom (CDXML face 64 "18" before "O"). There is no option to show the isotope only in the compound caption.
- Isotope source given as condition text: the step reports "does not balance as drawn: the reactants lack [18O]" (confirmed in validation.json). The earlier claim "no way to represent it" is wrong. A probe in a temporary folder gave water-18 as a species (SMILES `[18OH2]`, label "H2 18O") among the step-1 substrates. The 18O balance then passes, and the only remaining report is the by-product C3H10Si, which is not drawn. The cost is that water appears as a structure, not as condition text.
- No bond-weight option for a single bond. The only weights in the house code are arrow weights (thin, bond, bold; `mcp_runtime/figure_house.py`), so the paper's bold new C-N3 bond cannot be drawn.
- No per-bond split colour: `new_bond_color` gives one colour per new bond, so the half-red, half-black C-NH bond cannot be reproduced.
- ChemDraw rendering shares a resource lock with other runs. `mcp_runtime/figure_validation.py` takes the `chemdraw_com` lock with a 120 s timeout, and the default worker timeout in `mcp_runtime/tool_worker.py` is 570 s. The 300 s draw timeout and the exit-143 failure were not found in the code read here. This is operational, not a drawing capability.

## Audit

Checked on this run: reference.png, rendered.png (enlarged crops), the drawn figure.cdxml (regenerated offline into a temporary folder, not the case folder), validation.json, and the toolkit code paths named above. Overclaims in the earlier version of this file:

- The new-bond row was marked yes. The paper's new bonds are not uniformly black (C-N3 is bold, C-NH is red), and the card's `new_bond_color` is null. Changed to no. The matched count is now 11 of 19, not 12.
- The "no section headers" gap overstated the tool. Section labels exist in the `stacked-rows` path; what is missing is styling, rules and house-style support.
- The "no per-fragment colouring" gap was attributed to the tool. The tool colours substrates when the card gives colours; the card left them null, and the real tool gap is that products cannot be coloured.
- The yield-placement gap was attributed to the tool. `after_product_label` is implemented, so this is a card choice; the card-driven path was not tested.
- The "no way to represent" isotope gap is wrong. Water-18 as a species balances the 18O, at the cost of drawing water as a structure.
- The layout name is `stacked-rows`, not `stacked`.
- The arrow value in the Differences list and the table was 227 px (5.8 bonds). The card's evidence records 230 px (5.9 bonds).
- The label-font match holds only through the base preset; the card's measured block is not read by any code.
- The 300 s draw timeout and exit 143 could not be found in the code read here; the 120 s lock is confirmed.

Tool gaps missed earlier: the card's `measured` block is inert; products cannot be coloured; there is no bold single-bond option; the under-arrow yield is merged into the conditions text.

Observations not measured: the rendered isocyanide triple bond looks dashed at 1200 px, and the N-H hydrogen sits close to the "[18O]-3a" caption. Not verified: that rendered.png came from the `--render` run described above. The yield-in-label variant and the TEMPO row were not re-run.
