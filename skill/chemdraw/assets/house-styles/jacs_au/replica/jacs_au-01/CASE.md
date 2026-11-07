# JACS Au: radical propagation chain of the Kharasch ATRA process (Figure 1 A)

Source: Gilmour et al., *JACS Au* **2025**, DOI [10.1021/jacsau.5c01211](https://doi.org/10.1021/jacsau.5c01211) (Chloroalkylation of unactivated alkenes via a cobalt-mediated radical ligand transfer). Licence: CC BY 4.0, from the `jacs_au` card. Reference crop: `reference.png` (copy of `evidence/jacs_au-01.png`, panels A to C).

Figure type: `concept_panel` (card section `figure_types.concept_panel`), style `jacs_au` (base preset `acs1996`).

## What is reproduced

The radical propagation steps of panel (A), "Kharasch ATRA Process", as a two-step convergent route drawn by `draw_figure` (`brief.json`, `style: "jacs_au"`):

1. `COC(=O)[CH2]` (electrophilic radical, EWG = CO2Me) and `C=CCCCC` (1-hexene) give `COC(=O)CC[CH]CCCC` (nucleophilic radical, R = n-Bu), labelled "Int-II" with "radical propagation chain" above the arrow.
2. `COC(=O)CC[CH]CCCC` and `COC(=O)CCl` give `COC(=O)CCC(Cl)CCCC` ("stable adduct") with the Cl drawn as a blue disc, as in panel (A).

Choices made for the replica, all of them differences from the paper: EWG is CO2Me (the paper's EWG is generic; CO2Me is on the card's abbreviation list), R is n-Bu, the alkene is 1-hexene. The "Int-II" label is borrowed from panel (C); panel (A) has no compound labels. Structures are schematic, read from the crop's generic labels, so no OCSR was run. Each SMILES was checked with RDKit: formulas C3H5ClO2, C3H5O2, C6H12, C9H17O2, C9H17ClO2. Step 1 and the adduct balance.

Brief history: a first brief with the radical-initiation step (`COC(=O)CCl` to `COC(=O)[CH2]`) and the chain closed through a reused chloride was refused by the layout ("not a linear route, a convergent route or a set of reactions from one starting material"). The second brief dropped the initiation step and was drawn; the regenerated radical of the chain is not drawn (see below). The `--render` call inside `draw` timed out at 300 s, but the CDXML was saved; `cdx.py render` on that file then produced `figure-try3.png`, which is the one shown in `rendered.png` (downscaled from 1832 px to 1200 px wide).

## Card conventions against the replica

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| compound_label_face bold (Int-II) | bold Int-I, Int-II in panels B and C | bold "Int-II" | yes |
| compound_label_color #000000 | black | black | yes |
| arrow_style plain | plain arrows, filled head | plain arrows, filled head | yes |
| reagent_text_color #000000 | "radical propagation chain" dark slate (darkest pixels about RGB 27,45,46); "radical initiation" in the same panel is pure black | black | no |
| show_plus_sign true | no + between the radical and the alkene in panel (A) | + drawn between substrates (from the card value true, not from the paper) | no |
| bond_length_over_cap_height 2.06 | bond about 2.0 cap heights | bond about 2.1 cap heights (61 px against 29 px on the 1832 px render, by pixel measure; figure-try3.png is not in this folder, so this cannot be rechecked; rendered.png gives a bond of about 39 px against a cap of about 19 px, about 2.0 to 2.1) | yes (approximate; not refuted) |
| line_width_over_bond_length 0.09 | about 0.095 (arrow shaft about 1.46 px on a 15 px bond, reference.png) | about 0.04 (arrow shaft about 1.45 px on a 39 px bond, rendered.png; the acs1996 preset gives LineWidth 0.6 over BondLength 14.4) | no |
| arrow_length_over_bond_length 3.2 | panel (A) arrows about 43 px on a 15 px bond in reference.png, about 2.9 bond lengths; the card's 200 px arrow is not in panel (A) | row 1 arrow 531 px on the 1832 px render, about 8.7 bond lengths (347 px against about 39 px in rendered.png); no code path reads the card's 3.2 | no |
| halogens as filled discs, Cl blue #4F8EDB | Cl on the substrate and on the adduct as blue discs | blue #4F8EDB discs on both Cl (`atom_halos`, radius 9) | yes for style and colour only (disc about 49 px across against a 39 px bond, about 1.2 bond lengths, against about 1.05 in the reference, so it is larger than the paper) |
| comparison_layout stacked_rows, panels A to C | three stacked panels with titles | one scheme of two rows, no panels | no |
| panel titles bold, set into a #B1BDBD frame line | "(A) Kharasch ATRA Process" in a frame | none | no |
| background_fill #DEE2E3 | white background in crop 01 | white | no for the card's #DEE2E3 (white in both, as in crop 01; the grey comes from crop 02, which is not replicated) |
| radicals as blue orbital lobes (crop 01 observation) | blue lobes on every radical | radical centres drawn with no unpaired-electron mark at all | no |
| "radical initiation" text above the first arrow | present | step not drawn | no |
| step captions under structures ("electrophilic radical", "stable adduct") | present | not drawn | no |
| "radical propagation chain" bracket over two steps | one bracket over the chain | text over one step only, no bracket | no |
| abbreviate_groups CO2Me | paper uses EWG, not CO2Me | CO2Me abbreviation applied (report lists 9 contracted) | not comparable |
| substrate_layout inline_plus | no bimolecular step visible as a pair in crop 01 | inline | not comparable |

Matched 5 of the 16 comparable rows (rows 1 to 16; rows 17 and 18 are not comparable). The earlier "6 of 12" does not match the table, which has 18 rows, and one of its six matches (reagent_text_color) is refuted by the crop. Matches: label face, label colour, arrow style, bond/cap ratio (approximate), halogen disc style and colour. See the Audit note.

## Differences from the paper

- Generic EWG and R become CO2Me and n-Bu, and the alkene becomes 1-hexene.
- The radical-initiation step and its Cl by-product are omitted. The chain's regenerated radical `COC(=O)[CH2]` is not drawn; `draw_figure` names it as a missing by-product (C3H5O2) in step 2, which is the tool's intended behaviour and is flagged in the report.
- Panels (B) and (C) are not drawn, and neither are the frames, the panel titles and letters, the teal substrate boxes, the dotted blue rule and the "(C) Our Platform" heading.
- Plus signs are drawn between the substrates; the paper has none in this panel.
- The radicals look like closed-shell species (see tool gaps).
- Row 1's arrow is about 8.7 bond lengths long; the paper's arrows are much shorter.
- "crowded_plus" lint: the + in row 2 touches the "Me" label, and the layout did not re-layout to fix it.

## Tool gaps

- Radical centres given as SMILES `[CH2]` and `[CH]` are drawn with no unpaired-electron mark (checked in `figure-try3.png`): the radical reads as a plain CH2 or CH attached to a methyl ester or alkyl chain. Nothing in the brief can ask for the dot or the lobe.
- No radical orbital lobe notation for schemes. The `orbital` object exists in the toolkit but is not exposed in the `draw_figure` brief.
- No concept-panel composition in `draw_figure`: no panel frame, no panel letter or title, no boxes around substrates, no separator rule, no background fill. Panel layouts need `cdx.py build` or `compose_chemical_figure`.
- No free-text caption under a single structure. Text is only `above` or `below` a step.
- A chain whose intermediate is regenerated (a radical that closes the loop) cannot be drawn as a closed route. A species reused as a starting material for two steps (the chloride as the chain-start and as the chain-transfer reagent) is refused by the layout.
- No bracket or grouping that spans several steps for one shared condition.
- Arrow length inside a row is set by the layout; the brief has no arrow-length control.
- The `crowded_plus` lint finds a plus within 3 pt of a label and leaves it; the re-layout did not run (`relayout: null`). The plus in row 2 is visibly touching the "Me" label of Int-II in rendered.png.
- No per-step control of the plus sign. `show_plus_sign` is applied from the style to every step (`figure_house.py`); the step keys (`substrates`, `products`, `above`, `below`, `arrow`, `ts_bracket`) have none to turn it off for one reaction.
- No reagent structure above or below an arrow. Step keys take text only, so the alkene drawn above the arrow in panel (A) cannot be placed.
- One text colour for all above and below texts (`reagent_text_color`), so two captions of different colour cannot be drawn in one scheme.
- The card's measured geometry values (`line_width_over_bond_length`, `bond_length_over_cap_height`, `arrow_length_over_bond_length`) are not read by any code path in `cdxml_toolkit` (searched 2026-11-07). Line weight therefore comes from the base preset (acs1996: LineWidth 0.6 over BondLength 14.4, a ratio of 0.04), not from the card's 0.09. Fixing this needs a change in the style path, not in the brief.
- `cdx.py draw ... --render` returned `tool_timeout` after 300 s although the CDXML was saved; rendering the saved file separately worked (about 1 min 50 s). The draw itself took about 4 min without render.

## Audit

Checked on 2026-11-07 against reference.png (900 x 383 px) and rendered.png (1200 x 354 px), using enlarged crops and pixel sampling. Figure-try3.png is not in this folder, so the 1832 px measurements could not be rechecked. Colour values are medians of the darkest pixels of text in downscaled PNGs, which is reliable for hue but not exact.

Overclaims corrected:
- reagent_text_color: the "radical propagation chain" caption is dark slate (darkest pixels about RGB 27,45,46), while "radical initiation" in the same panel is black. Changed to no. The card's #000000 is not supported by this caption.
- line_width_over_bond_length was "not measured". Arrow shafts give about 0.095 in the paper and about 0.04 in the replica. Changed to no. The arrow shaft stands in for bond width; bonds were not measured separately.
- arrow length: no stands, now with numbers (about 8.9 bond lengths against about 2.9 in the paper).
- halogen discs: style and colour match, but the disc is about 1.2 bond lengths against about 1.05 in the paper.
- radical propagation chain: text over one step with no bracket, so partial becomes no.
- Count: the "6 of 12" did not match the table. Corrected to 5 of 16 comparable rows.

Not refuted: label face, label colour, arrow style, bond/cap ratio (about 2.0 to 2.1 against about 2.1 to 2.2 in the paper).

Tool gaps the replicator missed are listed above: per-step plus control, reagent structures above arrows, per-text colour, and the card's measured geometry values, which no code reads.
