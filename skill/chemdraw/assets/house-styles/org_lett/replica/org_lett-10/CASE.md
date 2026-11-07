# Organic Letters: telescoped flow route to levetiracetam (Figure 5, chemistry steps only)

Source: Dell'Amico et al., *Org. Lett.* **2025** (Enantioselective organophotocatalytic alpha-functionalization of aldehydes with N-lactam radicals). DOI: [10.1021/acs.orglett.5c02365](https://doi.org/10.1021/acs.orglett.5c02365).

Licence: CC BY 4.0. Reference crop `reference.png` is reproduced from Figure 5 (telescoped flow synthesis) under that licence.

Drawing style: the `org_lett` house style (`brief.json` `"style": "org_lett"`; base preset ACS Document 1996); see `cdx.py styles org_lett`.

Figure type: `setup_diagram` (the card's crop 10 entry, a bonus type with no drawer).

## What is reproduced

Only the chemistry of the flow route, as a single scheme: 1a and 2a give 3aa (photocatalytic step, conditions above and below the arrow), 3aa gives the nitrile (I2 / NH3 oxidation), and the nitrile gives levetiracetam 5 (H2O2 hydration), with the yield of 5 under its label.

The flow hardware is not drawn: the three colour bands and their bold titles, the coil reactors as stacked rings, the Zaiput separators and phase outlets, the f-reactor mixer, the T-pieces, the dashed hexane and water feed boxes and the DMA:H2O solvent switch. draw_figure has no drawer for these.

## Structures

| ID | SMILES in brief.json | Note |
| --- | --- | --- |
| 1a | `CCCC=O` | butanal, as drawn in the crop. |
| 2a | `Cc1cc(C)[n+](N2CCCC2=O)c(C)c1` with the triflate written as a second fragment (`O=S(=O)([O-])C(F)(F)F`) | N-lactam pyridinium salt. The three methyls (2, 4, 6) are read from the crop. |
| 3aa | `CC[C@@H](C=O)N1CCCC1=O` | (S) by RDKit CIP labelling. |
| nitrile | `CC[C@@H](C#N)N1CCCC1=O` | intermediate, no label (as in the crop). (S) by RDKit. |
| 5 | `CC[C@@H](C(N)=O)N1CCCC1=O` | levetiracetam, labelled (S) in the crop; (S) by RDKit. |

Configuration: the crop names 5 as (S)-levetiracetam. The aldehyde and nitrile are given the same spatial arrangement, which RDKit labels (S) as well because the CIP priorities are the same in the three compounds. The stereocentre of 3aa is inferred, not measured from the source.

Each SMILES was read from the crop by eye. No OCSR run was made.

## Render history

Three briefs were tried. Only the row budget changed between them; the content was the same.

| try | max_width | result |
| --- | --- | --- |
| 1 | 504 | three rows (sequential layout), readback matched, lint crowded plus |
| 2 | 900 | two rows, the third step wrapped |
| 3 (kept) | 1200 | one row, all three steps; readback matched, lint crowded plus |

Try 3 first failed on a ChemDraw lock (`resource_busy` after 295 s); the single retry succeeded. The kept brief is `brief.json` (max_width 1200). `rendered.png` is the try-3 render, downscaled to 1200 px wide.

## Replay

```
python skill/chemdraw/scripts/cdx.py py skill/chemdraw/assets/house-styles/org_lett/replica/org_lett-10/replay.py NEW_DIR
python skill/chemdraw/scripts/cdx.py render NEW_DIR/figure.cdxml
```

`replay.py` runs `draw_figure` on `brief.json` offline and writes `figure.cdxml` and `validation.json`. Compare the PNG with `reference.png`; `rendered.png` is the ChemDraw rendering of the kept brief.

## Convention checks

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| compound_label_face bold | 1a, 2a, 3aa, 5 bold | bold | yes |
| compound_label_color #000000 | black | black | yes |
| compound_label_italic_suffix false | no suffix | no suffix | yes |
| yield_placement under_product_label | yield under the bold label of 5 | `24%` under `5` | yes (placement only; the face differs, see Audit) |
| yield_format `{value}%` (top-level) | `24 % Yield` (word Yield, spaced percent sign) | `24%` | no. The template comes from the card and draw_figure has no per-figure override |
| yield and ee on the line under the label | `24 % Yield` and `82 % ee` on two lines | only the yield; ee cannot be given | no |
| conditions_split reagents_above_solvent_below | step 1: reagents above, dry DMA and LED/temperature below | the split is the one in the brief; draw_figure does not apply the rule | partial |
| substrate_layout inline_plus | 1a + 2a inline | inline with plus | yes |
| abbreviate_groups (Me, CF3) | skeletal methyls and ethyl, no Me or CF3 text; the triflate is written TfO⁻ | eight groups contracted (seven Me, one CF3); the triflate is drawn in full | no |
| aromatic_rings kekule | kekule pyridinium | not confirmed at the reference resolution; no code applies kekule (the rule only skips circle) | no |
| reagent_text_color #000000 | black | black | yes |
| arrow_style plain | plain arrows | plain arrows | yes |
| show_plus_sign true | plus between 1a and 2a | plus present (lint: crowded) | yes |
| new_bond_color null | black | black | yes |
| highlight_fill null | none | none | yes |
| substrate_colors null | black structures | black structures | yes |
| setup: three horizontal pastel bands (mint, light blue, lilac) | three bands | one row, no bands | no |
| setup: band background #D7FFF6 | mint band | no background (background_fill not applied to schemes) | no |
| setup: bold coloured band titles | Photocatalytic reaction, In-line separation, Oxidation | no titles | no |
| setup: coil reactors as stacked rings, time and temperature bold italic | rings with `20 °C 30 min` in bold italic | conditions as plain text on the arrow | no |
| setup: reagent feeds in dashed boxes at T-pieces | dashed boxes for hexane, water, I2, NH3, H2O2 | reagents as plain text | no |

Matched: 11 of 21 checked rows after audit (the first pass said 13; see Audit).

## Differences from the paper

- Scope: only the three reaction steps are drawn. The separation band (Zaiput separators, non-polar phase outlets, the f-reactor mixer, hexane and water feeds, the DMA:H2O 9:1 (0.18 M) switch) is not drawn.
- Layout: one scheme row, not three colour bands. The bands and their titles are absent.
- Intermediates: 3aa is drawn as a plain structure. The paper places it in square brackets, and the nitrile is drawn in brackets too; a plain bracket needs a species-level ts_bracket with an empty superscript, which the replica does not use (see Audit).
- Equivalents: `1a 4 equiv.` and `2a 1 equiv.` under the substrates are not drawn.
- Yield: only `24%` appears under 5. The paper gives `24 % Yield` and `82 % ee`; the ee is missing. The paper sets the yield line in bold italic; the replica's is plain.
- Product name: the paper writes `(S)-levetiracetam` above the label `5`; the replica has only the label.
- Reagent and condition lines: the paper's reagent lines appear to be bold and its `rt` and `15 min` lines bold italic; the replica's are plain.
- Conditions: "coil reactor" is written into the conditions text of each step to keep the equipment visible; in the paper it is an equipment label on the band, not a reagent. "rt" and "20 °C" follow the crop; draw_figure does not change them.
- Stereo: the wedge at the stereocentre is drawn for 3aa, the nitrile and 5 (S); the 3aa and nitrile assignments are inferred from 5 (see Structures).
- Reagent formulas: `I2 (1.1 M in THF) 1.5 equiv.` and `NH3 30% aq. excess` are kept as text; the paper's separation between the two is not drawn.

## Tool gaps

- No flow-setup drawer: coil reactors (stacked rings with residence time and temperature), Zaiput-type separators with phase outlets, f-reactor mixer, T-pieces and dashed reagent feed boxes.
- No band layout for a scheme: no horizontal pastel bands, no per-band background fill (background_fill is not applied to schemes) and no bold coloured band titles.
- No per-substrate equivalents: the `4 equiv.` and `1 equiv.` under the substrates cannot be attached to a species; they can only go in the conditions text.
- A single yield field: yield and ee cannot be given on separate lines beneath a product label.
- Plain brackets: draw_figure adds a double dagger by default. An empty superscript gives a bracket without one, but the empty text box is then reported as overlapping (see Audit).
- Layout: the three steps need max_width 1200 to stay on one row; at 504 and 900 they wrap (sequential layout).
- Crowded plus: a salt written as a second fragment next to 1a gives a crowded_plus lint; the plus spacing cannot be set.
- Balance: step 1 reports a missing by-product (C9H12F3NO3S, 2,4,6-collidinium triflate) and step 2 reports the missing N and step 3 the missing H2O (NH3 and water are this reading of the reagent text). These are real by-products or reagents, but the tool can only name them, not draw them as a reagent; `checks_passed` is false on all three tries.
- conditions_split reagents_above_solvent_below is listed under skipped in the style report.
- Render stability: the ChemDraw render waited on a lock on one try and failed with `resource_busy` after 295 s; the retry passed.
- No per-figure override of the card: abbreviate_groups applies to every species, and the style name is the only style input in the brief.
- No free text: the brief takes a title, above and below lines and a yield, so product names, band titles and equipment labels cannot be placed.
- No face control for reagent or condition text: only compound labels are set bold, and yield text is forced to plain under a product label.
- No shapes: dashed boxes, rectangles and reactor rings cannot be drawn. ring_fills and atom_halos only colour atoms of a species.
- No counterion abbreviation: a salt such as TfO⁻ is drawn as a full second fragment.

## Audit

Checked on 2026-11-07 against `reference.png`, `rendered.png`, `brief.json`, the card `org_lett.json` and the toolkit source (`figure_draw.py`, `figure_house.py`). `replay.py` was run offline into a temporary folder, not this folder. Its validation report matches the figures above: step 1 misses C9H12F3NO3S, step 2 misses N, step 3 misses H2O; the lint reports crowded_plus on the plus 1023; readback matched; `checks_passed` is false. Balance does not depend on `max_width`, so `checks_passed` false on the other two tries follows from the code; those tries are not in this folder and were not replayed.

Corrections to the table and text:

- abbreviate_groups was marked matched. The paper has no Me or CF3 text: the methyls and the ethyl are skeletal, and the triflate is written TfO⁻. The replica contracts eight groups (report: `abbreviate_groups (8 contracted)`) and draws the triflate in full. Not matched.
- aromatic_rings: kekule cannot be confirmed at the reference resolution, and no code applies it (`figure_house` only skips circle). Not matched until checked at higher resolution.
- yield_format: "see card_errors" pointed to no section. The cause is that the template comes from the card and draw_figure cannot override it per figure.
- yield_placement matches in placement only. The paper sets `24 % Yield` and `82 % ee` in bold italic; `figure_house` forces yield text to face 0 (plain) under a product label, and the replica's `24%` is plain.
- Matched count is 11 of 21, not 13. Still matched: compound_label_face, compound_label_color, compound_label_italic_suffix, yield_placement (placement only), substrate_layout, reagent_text_color, arrow_style, show_plus_sign, new_bond_color, highlight_fill, substrate_colors.
- Plain brackets were overstated as impossible. A probe with a species-level ts_bracket whose superscript is an empty string produced bracket groups with no dagger, but left an empty text box that the lint reports as overlapping after relayout. Not checked in ChemDraw, and the kept brief does not use it.
- The product name `(S)-levetiracetam` is in the reference and absent from the replica; it was not listed as a difference before.
- The balance report names N (step 2) and H2O (step 3); NH3 and water are the replicator's reading of the reagent text.
