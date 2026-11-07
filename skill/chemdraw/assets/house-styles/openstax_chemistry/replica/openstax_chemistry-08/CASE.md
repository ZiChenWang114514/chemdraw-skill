# openstax_chemistry, crop 08 (Figure 20.10, butene isomers)

Source: Flowers, Theopold, Langley, Robinson et al., *OpenStax Chemistry* 2015, section 20.1 Hydrocarbons, Figure 20.10. DOI: none on the card. Licence: CC BY 4.0 (from the house-style card).

Figure type: `stereo_model` and `structure_panel` (the crop is listed under both sections of the card). Style: `openstax_chemistry` (base preset `chemdraw_slide`). Scope panels apply only the base preset; the house conventions are skipped (see Audit).

Result: partial replica. Not rendered: the native ChemDraw render did not run (resource busy), so no PNG was checked by eye.

## What is reproduced

The skeletal drawings of 1-butene and cis-2-butene, captioned `1-butene` and `cis isomer` in plain Arial, drawn with `kind: "scope"` (the only panel kind that places structures side by side with captions). The structures were read from the crop by eye and checked with RDKit (`C=CCC`, `C/C=C\C`, both C4H8).

Not reproduced: trans-2-butene (`C/C=C/C`, RDKit canonical form), the ball-and-stick and space-filling rows, the expanded line formulas, the red-brown methyl groups, the italic cis and trans captions, and the brace with the shared `2-butene` caption. OCSR (`cdx.py ocsr`) was not run; the three isomers are unambiguous C4H8 structures.

## Tool result

`cdx.py draw brief.json <out> --render` on the final brief returned `ok: true`, `checks_passed: true`, `readback: matched` (2 structures, 0 missing, 0 unexpected), `data_binding: passed`, and `native: not_run` (`resource_busy`, `chemdraw_com` busy for 175 s). The layout run in the first render attempt timed out at 300 s. The output is a draft: `figure-v3b/page-001.cdxml` in the scratch folder, not copied here. The offline replay reproduces the same checks (see Replay).

Checked in the CDXML text: `BondLength` 30.0 pt, `LineWidth` 1.6, `LabelSize` 8.0, font Arial (font id 1001), labels plain (`face="0"`). Text colour is index 3 of the colour table. The table has two entries, so index 3 is the second one, (0,0,0), if ChemDraw indexes colours from 2. Not confirmed without a render.

## Convention check

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| stereo_model: perspective_3d models (ball-and-stick, space-filling rows under the formulas) | ball-and-stick and space-filling rows | not drawn; draw_figure has no 3D model kind | no |
| stereo_model: variation_color #983820 on the groups that differ | CH3 labels in the top row are red-brown | not drawn; scope panels have no per-atom colour | no |
| stereo_model: cis and trans isomers side by side | 1-butene, cis, trans in three columns | cis drawn; trans refused by draw_figure in the two-species scope panel | no |
| stereo_model: cis and trans in italic in the captions | `cis` and `trans` italic | captions are plain strings; no italic run | no |
| stereo_model: line formula stacked over ball-and-stick and space-filling models | three stacked rows per isomer | one skeletal row per isomer | no |
| structure_panel: one molecule in several notations, each captioned underneath in plain Arial | three notations per isomer, caption under the bottom row | one notation per isomer; one depiction per species, so several notations cannot share one caption; the label is bound next to its structure (data_binding passed), position not checked by eye | no |
| structure_panel: expanded formulas with every C and H written and bonds at 90 degrees | top row is an expanded formula, but 1-butene condenses CH2 and CH3 and bonds are not all at 90 degrees | skeletal only; scope panels cannot write atom labels | no |
| top level: compound labels in black (#000000) | black captions | captions use colour index 3 (second table entry, 0,0,0, if indexing starts at 2); not confirmed by render | no |
| top level: label font Arial or Helvetica | Arial | CDXML font 1001 is Arial, face 0; file level only, nothing rendered | yes (file only) |
| top level: bond length / cap height 3.35 | not measured on this crop (card has no crop 08 measurement) | bond 30 pt, label 8 pt; Arial cap height about 5.7 pt, so the ratio is about 5.2, not 3.35; a scope panel cannot set the label size | no |
| top level: line width / bond length 0.042 | card value (no crop 08 measurement) | LineWidth 1.6 / BondLength 30.0 = 0.053 | no |
| top level: species named in plain Arial words, never numbered | `1-butene`, `cis isomer` (italic `cis`), `trans isomer` (italic `trans`) | `1-butene` and `cis isomer` in plain type; no trans caption; no 2-butene caption | no |

Claimed: 11 rows. Matched: 2 as claimed; 1 after audit (label font, file level only). The audit added the line-width row, so the table has 12 rows.

## Differences from the paper

- trans-2-butene is missing. The paper shows three isomers; the replica shows two.
- The panel has no ball-and-stick or space-filling rows, and no line formulas with every atom written.
- The methyl groups that differ are not red-brown.
- The captions are not italic for cis and trans.
- There is no brace with the `2-butene` caption.
- The scope panel adds a `Substrate scope` heading (not in the paper) because no title was given in the brief. A title of `""` does not remove it (see Audit).

## Tool gaps

- No 3D perspective model kind in `draw_figure` (ball-and-stick and space-filling, CPK colours). The kinds are `scheme`, `scope` and `mechanism`.
- Scope panels cannot write every atom (expanded formula); they draw skeletal structures from SMILES only.
- Scope panels have no per-atom colour. `ring_fills` and `atom_halos` are not accepted in scope species at all (validation rejects them), so the red-brown methyl groups cannot be drawn.
- Scope labels are one plain string: no italic run for `cis` and `trans`.
- No brace or bracket that spans columns with a shared caption.
- E-configured double bonds fail the readback in the scope and scheme kinds, but not in every layout. Observed: `C/C=C/C` in a two-species scope panel raises `chemical_semantics_changed: source=C/C=C/C; roundtrip=C/C=C\C`. In a scheme (one step, with or without conditions), the cis isomer `C/C=C\C` also fails, with the roundtrip inverted to `C/C=C/C`, and trans fails the same way. The mechanism kind reads back matched for both isomers, but it needs a move and draws an arrow.
- Scope panels cannot set the label size or bond length from the brief. The panel removes `font_size` from the preset, so the house bond-to-cap-height ratio of 3.35 cannot be reached.
- House conventions are skipped for scope panels altogether (colours, arrows, label text). The report says "house conventions apply to schemes only".
- One depiction per species: there is no way to group several notations of one compound under one caption.
- The default `Substrate scope` title cannot be removed: `title: ""` falls back to the default (see Audit).
- Native render: the first render attempt timed out at 300 s and the retry returned `resource_busy` after 175 s, so no PNG was made.

## Replay

```
python skill/chemdraw/scripts/cdx.py py skill/chemdraw/assets/house-styles/openstax_chemistry/replica/openstax_chemistry-08/replay.py NEW_DIR
```

`replay.py` calls `draw_figure` on `brief.json`. The brief is a scope panel, so `figure.cdxml` in `NEW_DIR` is a folder of page files, not one file. The replay was run offline in the audit (no native render) and returned `ok: true`, `checks_passed: true`, `readback: matched` (2 structures, 0 missing, 0 unexpected), `native: not_run`. The folder holds `page-001.cdxml` with the values listed above.

## Audit

Checked against the reference image, `brief.json`, the house-style card and the toolkit source, with an offline run of `replay.py` and a few probe briefs in a scratch folder. No native render was available, so visual claims stay unconfirmed.

Overclaims corrected:

- The species row was marked matched. The card's crop 08 caption sets `cis` and `trans` in italic, and the reference names three species. The replica has a plain `cis isomer` and no trans caption. Now marked no.
- The label font row is kept only at file level: the CDXML font is Arial, but nothing was rendered. Corrected matched count: 1 of the 12 rows.
- The E-bond gap was overstated. It is not "every draw_figure layout", and the cis isomer does not pass in scheme. Mechanism passed readback for both isomers; scope passed for cis, and for trans only as a single species.
- The title was listed as untested. `figure_scope.py` sets `title = brief.get("title") or "Substrate scope"`, so `""` gives the default back, and the replay output contains the text "Substrate scope". A brief cannot remove this heading.
- The Style line implied the house style applied. The replay report shows `style.applied: []`, with the house conventions skipped for scope panels. Only the `chemdraw_slide` base preset applies (30 pt bond, 1.6 pt line, 8 pt Arial).
- The line weight is heavier than the card's ratio (0.053 against 0.042); the table did not list this.

Gaps the replicator did not list: scope panels cannot set label size or bond length; scope species reject `ring_fills` and `atom_halos` outright; house conventions do not reach scope panels; one depiction per species, so the three notations cannot share a caption.
