# Goldup et al., Chem 2020: substrate scope of the cyclopropanation (Figure 3, first row)

Source: Goldup et al., "Synthesis of a mechanically planar chiral rotaxane ligand for enantioselective catalysis", *Chem* **2020**. DOI: [10.1016/j.chempr.2020.02.006](https://doi.org/10.1016/j.chempr.2020.02.006).

Licence: CC BY 4.0, © the authors 2020; reference crop reproduced under that licence.

Drawing style: the `cell_press_chem` house style card, applied through `brief.json` (`"style": "cell_press_chem"`, figure type `substrate_scope`). A scope panel takes only the base preset (wiley), so the card's conventions are not applied by the tool.

## What is reproduced

The first row of the three-row product grid in Figure 3: cis-9, cis-10, cis-11 and cis-12. Each is a PhC(=O)O enol ester on a cyclopropane bearing an aryl (Ph, 4-tolyl, 2-tolyl) or benzyl group, with the yield and selectivity under the label, for example `86% (88% de, 57% ee)`. Rows 2 and 3 (cis-13 to cis-18) are not drawn. The conditions are in the paper's caption and not in the crop, so none are drawn.

| ID | Structure (SMILES in brief.json) | Stereo source |
| --- | --- | --- |
| cis-9 | `CC(C)=C(OC(=O)c1ccccc1)[C@H]1C[C@H]1c1ccccc1` | Read from the crop: the enol-ester C–Ca bond and the Cb–aryl bond are both hashed, so the pair is cis. The hashed-bond geometry was set from 2D positions read off the crop, and RDKit assigned the stereo tags. A 3D embedding confirms the two substituents are on the same face. |
| cis-10 | `CC(C)=C(OC(=O)c1ccccc1)[C@H]1C[C@H]1c1ccc(C)cc1` | Same drawing, 4-tolyl. cis confirmed in 3D. |
| cis-11 | `CC(C)=C(OC(=O)c1ccccc1)[C@H]1C[C@H]1c1ccccc1C` | Same drawing, 2-tolyl. cis confirmed in 3D. |
| cis-12 | `CC(C)=C(OC(=O)c1ccccc1)[C@H]1C[C@H]1Cc1ccccc1` | Same drawing, benzyl (hashed CH2 then Ph). cis confirmed in 3D. The CIP label at the aryl-bearing carbon reads S here and R in cis-9 only because the priority order changes with CH2Ph; the drawn geometry is the same. |

OCSR was not run. The structures were read by eye from the zoomed crop, and the SMILES were checked by RDKit parsing and the 3D cis test.

## Replay

```
python skill/chemdraw/scripts/cdx.py py skill/chemdraw/assets/house-styles/cell_press_chem/replica/cell_press_chem-04/replay.py NEW_DIR
```

`replay.py` runs `draw_figure` on `brief.json` offline and writes `validation.json` and a folder of pages (`pages/page-001.cdxml`). The scope kind writes a folder, so the output path differs from the jacs-au example, which writes one `figure.cdxml`. The replay was not run to completion (see Render status).

## Render status

Not rendered. `rendered.png` is absent.

- Attempt 1: `cdx.py draw ... --render` produced no output for several minutes while about 100 other `cdx.py draw` processes from parallel replicas queued on the same desktop ChemDraw COM resource (`chemdraw_com`). The run exited with no output folder and no log.
- Attempt 2 (the one permitted retry, with `--render`): `draw_figure` returned `tool_timeout` after 300 s (`draw_figure exceeded 300 seconds`, exit 1).
- Attempt 3 (without `--render`, to at least get the layout and the readback): also `tool_timeout` after 300 s. The scope path waited on the same ChemDraw resource even without rendering.

Because nothing was drawn, every visual comparison below is "no" or "not verified" from the brief and the card, not from a rendered PNG. The rows marked "yes" are true by construction (null conventions on both sides, nothing drawn in either figure), not observed in a drawing. The attempt logs are not in the repository, so the timeout account is the replicator's report and is not confirmed here. The code path that replay.py takes with `native_render` false (`figure_scope.draw_scope` into `publication_figure`) reads SMILES from the brief and does not call `chemdraw_com`, so the cause of the wait is unexplained, not established.

## Convention check

The card's `substrate_scope` section and the top-level conventions visible in this crop. "Match" is yes only where the card value is null and nothing is drawn on either side. Anything not observed in a drawing is "no" (not verified).

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| scope_layout: grid | one row of four products in the crop (the paper has rows of 4, 3 and 3) | scope flow packs compounds by width on pages; `scope_layout` is accepted by house_styles but never read by `publication/layout.py`; no column count or core alignment reachable from the scope brief | no |
| yield_format: `{value}%` | `86%` as the first token of the yield line | value string `86% (88% de, 57% ee)` passed verbatim (`figure_scope._write_inputs`); template not applied | no |
| selectivity_format: null | `(88% de, 57% ee)` after the yield, with italic `de` and `ee` | plain text, no italics | no |
| conditions_position: null | no conditions in the crop | no conditions drawn | yes (vacuous: null and nothing drawn on both sides) |
| variation_color: null | no variation colour | none drawn | n/a |
| highlight_fill: null | no fill | none drawn | yes (vacuous: null and nothing drawn on both sides) |
| signature: bold label with italic `cis` prefix | bold `9`, italic `cis-` | plain `cis-9` (the label is written as plain text by `layout.py`) | no |
| signature: green ester part, blue aryl part | green: benzoate, C=C(CH3)2 alkene, enol-ester hashed bond; blue: aryl or benzyl and the hashed bond to it, and the cyclopropane bond from the aryl-bearing carbon to CH2; the rest of the cyclopropane is black (zoom of crop 04, cis-9) | black everywhere; no per-fragment colour in scope panels | no |
| compound_label_face: bold | bold number, plain italic `cis` | plain text | no |
| compound_label_color: #000000 | black | default colour, not set in the brief | no (not verified) |
| yield_placement: under the label | label, then yield, both centred under the structure | label and yield start at x+6 in each cell (left-aligned, `layout.py` create_pages), not centred under the structure | no |
| abbreviate_groups: Ph | `Ph` text on all four benzoates, on the aryl of cis-9 and on the benzyl phenyl of cis-12; tolyl groups drawn as rings | all aryl and benzoyl groups drawn as rings; abbreviate_groups not applied to scope | no |
| aromatic_rings: kekule | Kekulé rings (inner double bonds visible in the benzoate and tolyl rings) | not checked; the scope brief has no ring-display option | no (not verified) |
| substrate_colors (top-level null) | green and blue origin colours | none | no |
| sans-serif text | Arial-like labels | wiley preset font, not checked | no (not verified) |

Counts: 14 claims apply to this crop (the teal-dot signature belongs to crop 03 and is excluded). 2 are yes, both vacuous (null on both sides, nothing drawn). The other 12 are no or not verified; none is confirmed against a drawing.

Not in the table and not claimed: proportions (bond length against cap height), line weight and label size. These need a rendered PNG and are unchecked.

## Differences from the paper

- The rendered comparison could not be made (see Render status), so proportions, line weight and label size are unchecked.
- Compound labels are plain text. The paper uses a bold number and an italic `cis` prefix.
- Yield and selectivity are one plain string. The paper writes `de` and `ee` in italics.
- The paper abbreviates `Ph` on all four benzoates and on the aryl of cis-9 and the benzyl phenyl of cis-12. The replica draws all of these as rings.
- The paper centres the label and yield under each structure. The scope flow left-aligns them at x+6.
- The paper colours the benzoate and enol-ester part green and the aryl part blue, with the cyclopropane black except for the bond from the aryl-bearing carbon to CH2, which is blue. The scope panel has no per-fragment colour, so everything is black.
- The grid order, column count and spacing of the paper are not reproduced, because the scope layout was not checked and the scope flow has no column option.
- Rows 2 and 3 (cis-13 to cis-18) are not drawn.

## Tool gaps

Checked against the toolkit source (`toolkit/cdxml_toolkit/mcp_runtime/figure_scope.py`, `publication/layout.py`, `publication/house_styles.py`, `mcp_runtime/figure_tools.py`).

- Scope panels take only the base preset. `figure_scope._write_inputs` passes the preset geometry and the width and height; the house conventions are never read for scope. The `style.applied` and `style.skipped` values in the scope report are hard-coded strings in `draw_scope`, not the result of a convention check.
- No rich text in the scope route. `layout.py` writes each label and value as a plain text string, and the scope brief has no bold, italic or subscript fields. The lower-level manifest composer `compose_chemical_figure` does support text runs (bold, italic, subscript, superscript), so this is a gap of the scope route, not of the toolkit as a whole.
- No per-fragment colour in scope panels. The scope route has no colour option. The manifest composer's molecule object takes one `color` and a `highlight_color` for atoms or bonds listed in `highlight_atoms` and `highlight_bonds`; the schema has no per-atom or per-bond colour, so the green, blue and black split needs post-editing of the CDXML in either route.
- No value-format template for scope fields. `yield_format` from the card is not applied to `values`.
- No abbreviation labels (`Ph`) for scope structures. The composer schema has no atom-label override field; the only route is a text object placed over computed atom coordinates.
- Not reachable from the scope brief, although the code has the hook: `publication/layout.py` `prepare` accepts `core_by_group` to align structures to a shared core, but `SCOPE_KEYS` in `figure_scope.py` does not include it. Structure orientation otherwise comes from RDKit `Compute2DCoords`, so the paper's orientation is not reproduced.
- No column count for `scope_layout: grid`. The value is accepted by `house_styles.py` and never read by `layout.py`.
- No control of caption alignment. Labels and values are left-aligned at x+6; the paper centres them under the structure.
- Operational blocker, not a drawing gap, and not confirmed: the replicator reports scope `draw_figure` waiting on the shared `chemdraw_com` resource with and without `--render`. The code path with `native_render` false reads SMILES and does not take that lock. The cited log (`draw_figure-20261107-051810-83620.json`) is not in the repository.

## Card errors and inconsistencies (reported, not fixed)

- `substrate_scope` signature "alkene-derived part blue #4068AD": in the crop the blue part is the aryl or benzyl group on the cyclopropane. The C=C(CH3)2 enol alkene is green, the same as the benzoate. The card's wording names the wrong part.
- Top-level `conventions.substrate_colors` is null, yet crop 04 colours the ester part green and the aryl part blue.
- `substrate_scope.conventions.selectivity_format` is null, yet crop 04 writes the selectivity after the yield in parentheses with italic `de` and `ee`.

## Audit

Audited against reference.png (zoomed), the toolkit source and RDKit. No rendered.png exists, so no row is verified against a drawing.

- Stereo: all four SMILES are cis (same face in a 3D embedding), and the CIP label at the aryl-bearing carbon is S in cis-12 and R in cis-9, as stated above. These claims hold.
- Corrected in this audit: the cyclopropane is not all black in the paper; the Ph abbreviation applies to all four benzoates, not only cis-9 and cis-12; the yield and label placement is known to differ (left-aligned, not centred); the chemdraw_com blocker and the cited log are unconfirmed; the rich-text and colour gaps belong to the scope route, since the manifest composer supports runs and text colour.
- Corrected matched count: 2 of 14, both vacuous (null convention, nothing drawn). None of the 12 drawn-content rows matches.
