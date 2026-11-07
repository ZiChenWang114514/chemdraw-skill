# oprd_process-01: Scheme 1 panel b (this work), first three steps

## Source

Guthrie, Gupton et al., "A Concise Process to Lenacapavir Sodium: Demonstration of One-Pot Sequential Heck/Suzuki-Miyaura Couplings in Lenacapavir API Synthesis", *Org. Process Res. Dev.* **2026**, *30*, 692-706. DOI: [10.1021/acs.oprd.5c00443](https://doi.org/10.1021/acs.oprd.5c00443). Licence: CC BY 4.0. Reference crop: `evidence/oprd_process-01.png` (Scheme 1, panels a and b), cut from the full-resolution figure.

Card: `toolkit/cdxml_toolkit/publication/house_styles/oprd_process.json`, figure type `process_route`.

## What is reproduced

Only the first three steps of panel b ("This work: our new streamlined process"):

1. Frag A (the (S)-amine, `N[C@@H](Cc1cc(F)cc(F)c1)c1nc(Br)ccc1Br`) with Frag D (`C#CC(C)(C)S(C)(=O)=O`), Boc2O, Pd(PPh3)2Cl2 and TEA gives 5 (Boc-protected, one Br replaced by the alkyne). In the paper 5 is a bracketed, non-isolated intermediate.
2. 5 with Frag B-DiMs (boronate ester) under PdCl2 / CataCXium A gives 6 (R = Ms).
3. 6 with H2SO4 gives 8 (Boc removed, one Ms removed, `> 95 % yield`).

Not reproduced: the KOH / SiliaMetS branch to 6 and 7-K, the Frag C amide coupling and salt formation to Len-API-Na, the CataCXium A inset box, the "70 % overall yield from Frag A" line, and all of panel a (the previous Gilead route with step 1 to step 4 labels).

SMILES were checked with RDKit (`cdx.py py`). Both stereocentres are (S) by CIP. No structure came from OCSR; the drawings were read by eye from the full-resolution figure.

## Replay

```
python skill/chemdraw/scripts/cdx.py py skill/chemdraw/assets/house-styles/oprd_process/replica/oprd_process-01/replay.py NEW_DIR
python skill/chemdraw/scripts/cdx.py render NEW_DIR/figure.cdxml
```

`brief.json` is the final brief (`style` `oprd_process`, `max_width` 1100; the route still wraps to two rows, see the Audit note). `rendered.png` is the desktop ChemDraw render of that brief, downscaled to 1200 px wide.

## Attempts

- Try 1 and try 2 used the default `max_width` 504. The route wrapped to three rows, one step per row, with a "+" between Frag A and Frag D and between 5 and Frag B-DiMs. The `Boc` label overlapped the indazole ring in 6. The draw log reported 8 warnings, including two balance notes: step 1 "reactants lack Cl" and step 2 "reactants lack C7H7N". The tool named these as unexplained mismatches and drew nothing for them.
- Try 3 (final) set `max_width` to 1100. The route still wraps: rendered.png shows steps 1 and 2 on the first row and step 3 on a second row, with product 6 drawn at the end of row one and again at the start of row two. The reference has steps 1 to 3 on one row. The `Boc` overlap in 6 remains. The draw log reported 6 warnings (the log is not in this folder); the step 1 and step 2 balance notes were not drawn as by-products.

## Convention table

Rows marked "card" are claims the card makes for `process_route` or the top-level conventions. Rows marked "panel b" are visible features of this figure that the card does not claim.

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| compound labels bold (card) | bold 5, 6, 8, Frag names | bold | yes |
| compound labels black (card) | black | black | yes |
| yield under the arrow (card) | yield after the conditions, under the arrow | yield under the arrow | yes |
| yield text form, "Yield x% Purity y%" (process_route card) | "> 95 % yield" (no purity) | "> 95 % yield" | no (card format is wrong for this crop) |
| reagents above, solvent and temperature below (card) | reagents above, 2-MeTHF and 68 °C, 3 h below | same split | yes |
| Boc abbreviated (card) | Boc | Boc (text only; in 6 the Boc label is crossed by ring bonds) | yes (abbreviation only) |
| plain arrow (card) | solid, plain | solid, plain | yes |
| Kekule aromatic rings (card) | Kekule | Kekule | yes |
| reagent text black (card) | black | black | yes |
| step labels "step n" numbered (process_route card) | none in panel b (numbers only in panel a) | none | no (card claim not visible in this panel) |
| "+" between substrates (top-level show_plus_sign) | no "+" between Frag A and Frag D, nor between 5 and Frag B-DiMs; Frag D sits above the arrow | "+" drawn in both places | no |
| route endpoint carries yield text (process_route card) | "> 75 % yield" and "> 95 % yield" and "70 % overall yield from Frag A" | only "> 95 % yield" on step 3 | partial |
| telescoped intermediate in square brackets, not numbered (process_route card) | 5 in brackets, numbered "5" | not drawn | no |
| scale on drawing (process_route card) | none in this crop | none | no (card claims scale_shown; not visible here) |
| step count in the summary (process_route card) | none in this crop | none | no (card claims step_count_shown; not visible here) |
| stacked panels a) and b) with dashed rule (process_route card) | two panels | one panel | no |
| highlight_fill null (card) | none | none | yes |
| stereo at the amine: bold wedge | bold wedge | hashed bond | no |
| arrow length about 8 bond lengths (top-level) | long arrows, several lines of conditions | long arrows, lines of conditions | not measured (the crop is too low resolution for a bond-length measurement) |
| steps 1 to 3 on one row (panel b) | one row: 5, 6 and 8 on one line | two rows; 6 drawn at the end of row one and again at the start of row two | no |
| reagent equivalents on the structure reagents (panel b) | Frag D (1.05 eq) above step 1; Frag B-DiMs (1.2 eq) above step 2 | no equivalents drawn | no |
| (S) descriptor beside the Frag A stereocentre (panel b) | italic (S) | none | no |

Claimed by the card and checked here: 16 rows. Matched: 9 (the table's own "yes" rows; the earlier count of 8 was a miscount). See the Audit note.

## Differences from the paper

- Scope: three steps of panel b, not the whole panel; no branch to 7-K, no Frag C amide, no Len-API-Na, no CataCXium A box, no panel a.
- Intermediate 5 is drawn as a plain structure, not in square brackets with its number.
- Stereocentres: the paper uses bold wedges at the amine; the replica draws hashed bonds. The brief has no wedge control.
- Boc label collides with the indazole ring in 6 (both in try 1 and in try 3).
- A "+" is drawn between Frag A and Frag D, and between 5 and Frag B-DiMs. The paper shows Frag D above the arrow and Frag B-DiMs above the second arrow, with no "+".
- Frag D is drawn as a substrate with the name "Frag D" beneath it, not as a reagent above the arrow with its equivalents.
- Reagent lines are in the paper's order and wording (Boc2O (1.1 eq), Pd(PPh3)2Cl2 (1 mol %), TEA (5 eq) above; 2-MeTHF (8 V), 68 °C, 3 h below). Solvent amounts in V match the paper.
- Balance warnings from the draw (step 1 and step 2) are not drawn as by-products, as the tool specifies.

## Tool gaps

- No telescoped or non-isolated intermediate bracket: the tool cannot draw square brackets around a numbered intermediate with a "not isolated" caption (the paper uses this on 5 and on 4 in panel a).
- No stereo wedge control: the brief has no way to request a bold wedge on the stereocentre, and the draw used hashed bonds.
- No reagent structures above the arrow: Frag D and Frag B-DiMs appear as substrates on the row, not as labelled reagents above or below the arrow.
- No stacked two-panel layout with a dashed rule and "a)" and "b)" headings in `draw_figure`; one scheme per brief.
- No boxed insert for a catalyst ligand (CataCXium A).
- No step labels ("step 1", "step 2") under the arrows; the process_route card calls for them in panel a.
- The process_route yield template "Yield {value}% Purity {purity}%" is not applied by `draw_figure`; the paper's "> 95 % yield" needed the literal yield text.
- No divergent branch to a salt (7-K) from an intermediate (6) with the second arrow.
- `max_width` defaults to 504, so a three-step route wraps to three rows. The reference uses one row; the row budget had to be raised by hand in the brief.

## Audit

Checked by the auditor against reference.png and rendered.png (zoomed crops of the labels, the stereocentres, the 6 region and the wrap), against the card entry in `toolkit/cdxml_toolkit/publication/house_styles/oprd_process.json`, and against the toolkit source (`toolkit/cdxml_toolkit/mcp_runtime/figure_draw.py` and `figure_house.py`). The draw log and validation.json are not in this folder, so the warning counts are not verified.

Overclaims corrected in this file:

- Layout. rendered.png has two rows, not one. The Try 3 sentence, the Replay note and the table rows now say so. Raising max_width from 504 to 1100 reduced the wrap from three rows to two; it did not reach one row.
- Count. The table has nine rows marked yes among the 16 card rows. The stated 8 was a miscount. On inspection none of the nine is overturned. The Boc row is matched for the abbreviation only, because the label is crossed by ring bonds in 6.
- Tool gap "no telescoped or non-isolated bracket". Not accurate as written. draw_figure draws square brackets around a species through ts_bracket (superscript defaults to a double dagger). What is missing is the number under the bracket and a "not isolated" caption. Neither the 5 bracket nor the 4 bracket in the supplied panel a and b crop carries a "not isolated" caption.
- Tool gap "yield template not applied". The cause is incomplete. draw_figure takes no figure_type key, and figure_house.apply_figure_type_conventions is called only for catalytic_cycle, so the process_route conventions never apply. "Purity" is not implemented anywhere in mcp_runtime. The literal "> 95 % yield" passes through because format_yield templates only bare numbers.
- Tool gap "no divergent branch to 7-K". Not tested. The draw_figure docstring lists one starting material with several products (divergent) as a supported layout. The branch was out of scope, so the accurate statement is "not tested".
- Tool gap "max_width ... row budget had to be raised". True as far as it goes, but raising it did not give one row (see Layout).
- Stereo gap. Confirmed for draw_figure. The toolkit has a native bond-display helper (figure_editing.edit_bond_display, accepting WedgeBegin and Hash) that the brief does not reach; whether an MCP tool exposes it was not checked.
- Confirmed as stated: no reagent structures above the arrow (step above and below entries accept text lines only), no step labels (step_label_style, scale_shown and step_count_shown appear in the card schema but are not read by mcp_runtime), no boxed insert, no stacked panels (the replica covers panel b by choice, so this did not block anything).
- The Frag A SMILES was checked by hand and gives (S), as stated.

Tool gaps the replicator did not list:

- No wrap control: when a route wraps, the intermediate 6 is drawn twice.
- No equivalents on structure reagents: Frag D (1.05 eq) and Frag B-DiMs (1.2 eq) are dropped.
- No stereo descriptor such as the italic (S) beside the Frag A stereocentre.
- No repair of label collisions: the Boc label in 6 is crossed by ring bonds, and the draw did not fix it.
