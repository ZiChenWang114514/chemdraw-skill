# jchem_educ-09 replica (concept_panel)

## Source

- Paper: Elliott et al., J. Chem. Educ. 2026, Figure 16 (concept panel, bond polarization).
- DOI: 10.1021/acs.jchemed.6c00141
- Licence (from the card): CC BY 4.0
- Style slug: `jchem_educ`. Card: `toolkit/cdxml_toolkit/publication/house_styles/jchem_educ.json`, section `figure_types.concept_panel`, crop `evidence/jchem_educ-09.png`.

## Figure type and what is reproduced

Figure type: concept_panel. The card has no drawer for this type, so the nearest expressible layout was used: `kind: "scope"` with the base preset acs1996 (scope panels take only the base preset, so house conventions are not applied).

Reproduced:

- Two small structures, `ClCCC` (A) and `ClCCCC(=O)[O-]` (B), with the caption text under each.
- Two footnote lines at the bottom.

Not reproduced: the red partial-charge labels (delta minus, delta plus, delta delta plus, delta delta delta plus) on the left structure, and the blue double-headed bond-dipole arrows with crossing ticks on the right structure. No tool primitive exists for either.

Brief used: `brief.json` in this folder (copy of the scratch brief1). Only one brief was tried. The native draw with `--render` failed twice (see Tool gaps); the render below is a render-only run of the same page, produced after the brief was final.

## Match table

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| concept_panel: panel_label_style none (no panel letters) | no panel letters | letters A and B drawn under the structures (from species ids) | no |
| concept_panel signature: take-home statements in blue #0000FC plain text | the two footnote lines at the bottom are blue, plain | footnotes are black, plain | no |
| concept_panel signature: take-home statements under small structures | black italic captions under each structure, two lines; the card's signature for this row is blue plain take-home text | plain (not italic) single-line captions under each structure, left aligned; no blue take-home text | no (placement only; see Audit) |
| top-level label_font Arial or Helvetica | sans text, Arial-like | sans text, Arial-like | yes (typeface only; text size not compared) |

Counts: claimed 4, matched 2 (the replicator's count). Audit count: 1 of 4 (see Audit).

Rows not counted (not claimed by the card, but visible in the crop):

- Captions are italic in the paper, plain in the replica.
- Left structure: the paper has Cl at the left end of the chain; the replica has Cl at the right end (mirrored).
- Right structure: the paper has Cl at the left and the carboxylate at the right; the replica has the reverse (mirrored).
- Paper has the red delta labels and blue dipole arrows; the replica has neither.
- Replica adds a default title "Substrate scope"; the paper has no title.
- Footnotes sit close below the captions in the paper; in the replica they are pushed to the bottom of a very tall page.

## Differences from the paper

- Panel letters A and B are drawn; the paper has none. The letters come from the species ids, which the scope kind needs.
- Footnotes are black; the paper's footnotes are blue #0000FC.
- Captions are plain; the paper's captions are italic.
- Both structures are mirrored left to right compared with the paper.
- No partial-charge labels (red delta marks) and no bond-dipole arrows.
- A default title "Substrate scope" appears that the paper does not have.
- The page is much taller than the figure. The render is 1617 x 2688 px before trimming; the footnotes sit at the bottom of the page with a large empty gap above them.
- Bond proportions were not measured against the paper; the replica looks similar by eye but no ratio was checked.

`rendered.png` is trimmed of the outer white margin and downscaled to 1200 px wide. It is the render of the non-render draft page (`cdx.py render` on the draft `page-001.cdxml`), not the output of `draw --render`.

## Tool gaps

- The scope kind adds a default title ("Substrate scope") when the brief title is empty, with no way to omit it.
- The scope kind ignores the concept_panel conventions in the card (only acs1996 applies), so italic captions and blue take-home text cannot be requested.
- Species ids are always drawn as panel letters; there is no option to hide them.
- Field and footnote text has no italic, centred or colour option.
- Footnotes are placed at the bottom of the page, not directly under the captions, which makes the page very tall.
- No primitive for partial-charge annotations (delta symbols, coloured).
- No primitive for straight double-headed arrows with crossing ticks along bonds (bond-dipole arrows).
- No control over structure orientation (Cl at left or right).
- Native `draw --render` did not complete: attempt1 ended with exit 143 after 293 s (worker_crashed, ChemDraw lock contention), attempt2 hit tool_timeout at 302 s. A render-only run of the existing page then completed (exit 0) after about 5 minutes; several other ChemDraw processes were running at the time.

## Audit

Checked against reference.png, rendered.png, brief.json, this file and the concept_panel section of `toolkit/cdxml_toolkit/publication/house_styles/jchem_educ.json`. Changes made in this audit: the take-home row is now "no", the label-font row is marked as typeface only, and the count is corrected. No other file was edited.

Overclaims:

- The take-home row was marked as matched on placement alone. The card's signature for this row is blue plain take-home text. The replica has black text, captions that are not wrapped to two lines, not italic and left aligned rather than centred, and no blue text.
- The label-font row matches the typeface only. Text size was not compared, and the scope kind cannot set it (gap 2 below).
- The "Reproduced" section counts both structures as reproduced. Both are mirrored left to right: in A the Cl is at the right end (reference: left end), and in B the carboxylate is at the left (reference: right).
- "Bond proportions ... look similar by eye" does not hold for the page. The reference is 666 x 222 px (about 3:1). rendered.png is 1200 x 1995 px (about 0.6:1) with the footnotes on its bottom edge. Line weight and bond-to-caption ratio were not measured, so they are not matched.
- The render timings (293 s, 302 s, about 5 minutes for the render-only run), the 1617 x 2688 px size and the statement about other ChemDraw processes have no log or record in this folder, so they could not be checked. replay.py does not render and does not write rendered.png.

Other differences found on re-reading (not in the table):

- Colours: no blue take-home text, no red partial-charge labels and no blue bond-dipole arrows.
- Layout: a "Substrate scope" title and panel letters A and B are added; the footnotes sit at the page bottom, far from the captions.
- Carboxylate charge: drawn as a plain superscript hyphen (O-). The reference symbol may be circled; this could not be settled at reference size.

Corrected count: 1 of 4 conventions matched (label typeface only).

Tool gaps the replicator did not list (checked in toolkit source):

1. Caption wrap width. `publication/layout.py` `prepare()` sets each column to the widest caption, capped at the page width, so captions never wrap to the structure width. Two-line captions cannot be requested.
2. Text size. `style_settings()` defaults `font_size` to 8 pt. `figure_scope.py` `_write_inputs()` passes only width_mm and height_mm from the brief, and the preset call removes font_size. Field, footnote and title text is therefore fixed at 8 pt.
3. Page size. width_mm and height_mm are accepted by kind scope (defaults 180 x 240 mm), but brief.json sets neither. Part of the "very tall page" is that default and could be reduced. The footnotes still sit at the bottom of the page box, not under the captions.
4. Card conventions do not reach scope panels. `figure_scope.py` does not import `figure_house`, so no house convention applies to a scope panel at all, including circled charges. This extends the replicator's own gap about concept_panel conventions.

Confirmed from source: the default title (`figure_scope.py` `_write_inputs`), panel letters taken from the species id when the label is empty (`publication/data.py` line 138, `label or cid`), footnotes at the page bottom (`layout.py` `create_pages`), no italic or colour option for field or footnote text, and no partial-charge or bond-dipole primitive (no dipole or partial-charge code in the toolkit).

Not a drawing capability: the two native `draw --render` failures are ChemDraw lock or worker problems. They belong in an operations note, not in the tool gap list.
