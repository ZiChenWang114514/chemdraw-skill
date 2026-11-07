# Org. Lett. graphical abstract: photocatalytic enantioselective alpha-amination of an aldehyde (evidence crop 05)

Source: Dell'Amico et al., *Org. Lett.* 2025 (Enantioselective organophotocatalytic alpha-functionalization of aldehydes with N-lactam radicals). DOI: [10.1021/acs.orglett.5c02365](https://doi.org/10.1021/acs.orglett.5c02365).

Licence: CC BY 4.0. The reference crop (`reference.png`) is the graphical abstract (TOC) of that article, reproduced under that licence.

Figure type: `graphical_abstract` (the free-form TOC, crop 05). Style: the `org_lett` house style in `brief.json` (base preset ACS Document 1996, bond length 14.4 pt).

## What is reproduced

Only the reaction scheme at the top of the TOC: an aldehyde and an N-centred lactam radical, under light and photocatalyst with an amine catalyst, give the alpha-N-lactam aldehyde, with the lactam ring filled lilac.

The aldehyde substituent is not a generic R in this replica. The crop shows R, so the replica uses R = ethyl (butanal, `CCCC=O`) as one concrete instance. The lactam is the unsubstituted 2-pyrrolidinone radical (`O=C1CCC[N]1`, one unpaired electron on N). The product is `CC[C@@H](C=O)N1CCCC1=O`, the (S) configuration taken from the (S)-levetiracetam target in the crop; the stereocentre is (S) by CIP in both the paper and the replica, but the paper draws a hashed bond to R and the replica a bold wedge to the ethyl group, in different orientations (see the table).

| Structures (SMILES in brief.json) | Role |
| --- | --- |
| `CCCC=O` | aldehyde (R = Et instance) |
| `O=C1CCC[N]1` | N-lactam radical |
| `CC[C@@H](C=O)N1CCCC1=O` | alpha-amino aldehyde product, lactam ring filled |

The product lactam ring is filled with `#DFB3FE` through a species-level `ring_fills` entry in the brief (see "Tool gaps"). The paper also fills the reactant lactam ring; the replica does not (see the table).

Replay: `replay.py` runs `draw_figure` on `brief.json` offline and writes `figure.cdxml` and `validation.json` to a new folder. `rendered.png` is the desktop ChemDraw render of the same brief (max width 440 pt).

## Card conventions for this figure type and the visible scheme conventions

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| light source as a blue ring with lamp icon on the reaction arrow | blue `#0B0DFE` ring with lamp glyph on the arrow | not drawn; `hv` as text above the arrow | no |
| two interlocking arc arrows (mint `#55FFA9`, dark green `#066A34`) around a bold PC | present | not drawn; `PC` appears only as text below the arrow | no |
| key ring filled lilac `#DFB3FE` (`highlight_fill`) | lactam ring of the product and of the reactant lactam (both filled; lilac pixels at x≈640–760 and x≈200–240 in reference.png) | product lactam ring filled `#DFB3FE` via brief `ring_fills` (colour matches to 1 unit); reactant lactam unfilled | partial |
| check-mark bullets with bold dark green `#066A34` claims | three claims beside the scheme | not drawn (no bullet or text-block element) | no |
| target drug in a rounded black frame | (S)-levetiracetam with name | not drawn | no |
| `substrate_layout` inline_plus (A + B) | aldehyde + lactam side by side with "+"; aldehyde O at top left, lactam C=O on top | same inline layout; aldehyde O at the bottom, lactam C=O at the bottom | yes (layout only; orientations differ) |
| `show_plus_sign` | "+" between substrates | "+" drawn; the lint flags it as crowded (within 3 pt of a species) | yes (presence only; size not compared) |
| `arrow_style` plain | plain arrow | plain solid arrow | yes |
| `reagent_text_color` #000000 | no black reagent text: PC is bold dark green, the light source is a blue glyph | black regular text `PC, amine catalyst` | no |
| `conditions_split` reagents above, solvent/catalyst below | light as a blue glyph on the arrow, amine catalyst drawn as a structure above the arrow, PC below | `hv` as text above, `PC, amine catalyst` as text below (amine catalyst on the wrong side, no structure) | no |
| `abbreviate_groups` (Me) | crop shows R and no Me | the render shows `Me` on the aldehyde and the product, where the paper shows R | not tested (the render differs from the paper; no test was run) |
| `compound_label_face` bold | no compound labels in the scheme | none drawn | n/a |
| atom label weight (N, O, R) | bold N, O and R labels | regular-weight `Me` label; N and O not measured | no (visual, not measured) |
| `yield_placement` under_product_label | no yield in the scheme | none drawn | n/a |
| `new_bond_color` null | no bond colour in the crop | black | n/a |
| bond length and line width (`bond_length_over_cap_height` 2.2) | not measured | not measured; "visually close" is not supported | no (unmeasured) |
| radical dot on the lactam N | `·N` in the paper's lactam | the radical is stored (`Radical="Doublet"` on N), but the rendered PNG shows no dot | no |
| stereo bond at the alpha carbon | hashed (dashed) bond to R; (S) by CIP; N down, CHO up-left, R up-right | bold wedge to the ethyl group; (S) by CIP; N left, CHO down-right, Et up-right | no (bond style and orientation differ; the descriptor agrees) |

Claimed for this figure type: 5 items. Corrected: 0 matched in full, 1 partial (the lilac key ring). The replicator counted `highlight_fill` and the key ring as two items, but they are one feature. Three of the six original "yes" rows (reagent colour, stereo bond, key ring) do not hold for the TOC, and the two layout rows hold only in part; see the Audit below.

## Differences from the paper

- The aldehyde and the lactam are drawn as the simplest instances: R is ethyl, and the lactam carries no substituent. The paper keeps a generic R and an (CH2)n ring bracket (the ring is drawn as a five-membered ring with `n` subscript).
- The amine catalyst is not drawn. Only the text "amine catalyst" is written below the arrow.
- The blue light ring and the lamp glyph are absent; the light source is the text `hv` above the arrow.
- The PC and amine cycle arcs are absent, so the catalytic cycle of the TOC is not shown.
- The three green check-mark claims and the levetiracetam frame are absent. They are text and box elements of a free-form TOC, which `draw_figure` does not produce.
- The radical dot on the lactam N is missing in the render.
- The step does not balance as drawn: the product has one H fewer than the sum of the two reactants (the step loses H, as an oxidative C-H amination does). The tool names the missing H and draws no by-product, because the paper shows none. The drawing is the paper's, with that imbalance left in place.
- No yield, ee or compound numbers are in the source crop, so none are drawn.

## Tool gaps

- No free-form TOC layout: no coloured headings, no check-mark bullet list and no framed target box. A graphical abstract with text claims cannot be drawn by `draw_figure`; it needs a hand-made layout in ChemDraw.
- No light-source glyph on an arrow (the blue ring with lamp icon). Conditions are text only.
- No coloured catalytic arcs around a single label (PC). The `catalytic-cycle` layout is for a closed loop of intermediates and cannot draw a photocatalyst ring beside an amine cycle.
- Catalysts that are drawn as structures above or below the arrow cannot be placed: `draw_figure` takes species only as substrates or products, and text-only conditions above and below the arrow.
- A generic substituent R and a repeat bracket (CH2)n on a ring cannot be expressed in the brief; SMILES must be concrete.
- The radical electron is preserved in the saved file (`Radical="Doublet"` on the N node) but the desktop render shows no radical dot on the lactam N.
- A card-level figure-type colour (`graphical_abstract.highlight_fill`) is not read by `draw_figure` for a scheme brief. `draw_figure` reads only the top-level house conventions, so the style report says "highlight_fill: not specified by the card". The lilac ring was reproduced through species-level `ring_fills` in the brief, which is a brief decoration, not a card convention.
- The atom-balance check flags the H lost in an oxidative step and names it, but the tool gives no way to show the oxidant or the released H as a by-product in an intentional way. The warning stands.
- The layout lint reports the "+" between the substrates as crowded at both widths (504 and 440 pt).
- No stereo bond style. `draw_figure` picks the wedge from the SMILES, and a species entry (keys: id, smiles or name, label, ring_fills, atom_halos, ts_bracket) has no bond-style field, so the hashed bond to R in the paper cannot be drawn.
- No 2D orientation control. Species are SMILES only, with no rotation or mirror option, so the paper's aldehyde and lactam orientations cannot be matched.
- No per-label colour or weight for conditions. The step `above` and `below` entries are plain strings, so the dark green bold `PC` cannot be drawn. Species entries have no label-weight field, so bold atom labels cannot be set.

## Audit

Checked by viewing `reference.png` and `rendered.png`, zooming on the product and the reactant lactam, sampling pixel colours, and reading `figure_house.py` (`add_highlight_fills`, which reads only the top-level `highlight_fill`) and the `draw_figure` docstring in `figure_draw.py`. `figure.cdxml` and `validation.json` are not in this folder, so the `Radical="Doublet"` attribute and the lint result are taken as stated, not checked.

- Key ring lilac: partial. The colour matches (paper `#DFB3FE`, render `#DEB3FE`), but the paper also fills the reactant lactam ring and the replica does not. This is fixable in the brief by adding `ring_fills` to the `lac` species; it is a replicator miss, not a tool gap.
- Reagent text colour: not matched. The paper's `PC` is bold dark green; the replica's conditions are black regular text.
- Conditions split: not matched. The paper puts the amine catalyst above the arrow as a structure; the replica puts it below as text.
- Bold wedge: not matched. The paper's bond to R is hashed; the replica's is bold. Both centres are (S) by CIP (checked by hand), so the descriptor agrees.
- Inline layout: matched for the layout only. The substrate orientations differ.
- Atom label weight, bond length and line width: not matched. The first is visual; the second was not measured.
- Radical dot: correctly marked no. The paper's `·N` is on the reactant lactam, and the render shows no dot on it.
- The six gaps in the replicator's report are accurate. The reactant lactam fill and the orientation and stereo-bond items are additional, and the first is not a tool gap.
- Corrected count: 0 matched in full, 1 partial (lilac key ring).
