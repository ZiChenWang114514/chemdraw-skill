# J. Med. Chem.: core of Table 1 (LIMK inhibitor series, sar_table)

Source: Baldwin, Ward et al., "Discovery of MDI-114215: a potent and selective LIMK inhibitor to treat fragile X syndrome", *J. Med. Chem.* **2025**. DOI: [10.1021/acs.jmedchem.4c02694](https://doi.org/10.1021/acs.jmedchem.4c02694).

Licence: CC BY 4.0. The reference crop (`reference.png`, evidence crop `jmed_chem-07`) is reproduced under that licence.

Drawing style: the `jmed_chem` house style card (`cdx.py styles jmed_chem`). Figure type: `sar_table`.

## What is reproduced

Only the core structure drawn above Table 1: a 4-(N-phenylsulfamoyl)benzamide whose amide nitrogen carries a cyclopropylmethyl group and a benzyl group. The paper's benzyl ring carries a generic A position (ortho to the benzylic carbon) and a generic R position (para to it). The paper core, with the variables as dummy atoms, is `O=C(c1ccc(cc1)S(=O)(=O)Nc1ccccc1)N(CC1CC1)Cc1c(*)cc(*)cc1`. The replica does not reproduce it exactly (see below).

The replica (`brief.json`) draws the N-benzyl analogue with no A and no R. The draw_figure scope path used here cannot write R or A labels (see Tool gaps for other paths that can). Scope panels take only the base preset (`acs1996`), so the card's sar_table conventions are not applied (the report says: "house conventions apply to schemes only").

The table below the core (grid, headers, compound numbers, pIC50 values) is not drawn. No tool used here produces a grid; the publication `sar` mode lays out structure cards, not a table.

Brief: `brief.json` (kind `scope`, one species, no label, no footnotes). Replay: `replay.py` writes a `figure.cdxml` folder containing `page-001.cdxml`; re-run during the audit, `ok: true` (see Audit).

## Convention check

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| `table_style`: grid (full black rule on every cell) | full grid under the core | no table drawn | no |
| `activity_format`: pIC50 mean ± SD, two decimals | values in the table (e.g. 7.48 ± 0.18) | no values drawn | no |
| `variation_color`: null | no colour | no colour (colour table holds only black and white) | yes |
| `highlight_fill`: null | no fill | no fill | yes |
| core structure with R and A drawn above the table | core with plain R and A labels above the table | core drawn, no R or A labels, no table | no |
| bold header with merged group headers | bold header, Enzymatic pIC50 over LIMK1 and LIMK2 | not drawn | no |
| bold compound numbers in the first column | bold numbers | not drawn | no |
| R groups as small fragments with a dashed attachment bond | R fragments in the table | not drawn; R position is a plain ring carbon | no |
| text values such as Rapid and nd | in the table | not drawn | no |
| top level: Kekule aromatic rings | Kekule | Kekule (12 double bonds in the CDXML: 9 ring, 3 exocyclic; no 1.5 orders) | yes |
| top level: black only, no colour or boxes | black | black | yes |
| top level: label font Arial or Helvetica | Arial-like labels (N, O, S) | Arial (fonttable `Arial`, atom labels in font 1001) | yes |
| `line_width_over_bond_length`: 0.07 | line 3 px / bond 50 px = 0.06 in the evidence crop | CDXML LineWidth 0.6 pt over bond 14.4 pt (0.042); the card implies 1.0 pt | no |
| `bond_length_over_cap_height`: 2.25 | bond 50 px / cap 22 px = 2.27 in the evidence crop | CDXML bond 14.4 pt over 8.0 pt labels; Arial cap height about 0.716 em gives 5.7 pt, ratio about 2.5 against 2.25; the rendered N is 24 px tall beside a 60 px bond | no |
| `compound_label_face`: bold | bold compound numbers | the caption `core` is plain (face 0) | no |

Matched 5 of 15 rows. The five matches were checked against the CDXML: label font, Kekule bonds, black colour, and the two absence rows (no colour, no fill). The three rows marked no for line width, proportion and caption face were added in this audit from the replay CDXML; the other rows were already marked no.

## Differences from the paper

- The core is an N-benzyl analogue. The paper's benzyl ring has an A position ortho to the benzylic carbon and an R position para to it; the replica ring is an unsubstituted benzene, so the drawn molecule is not the paper's core.
- No table: the grid, bold header, merged headers, bold compound numbers, R-group fragments and value cells are absent.
- The replica has a title and a caption that the paper does not have. The default title "Substrate scope" appears when no title is given (test brief v3), and a species without a label is captioned with its id, so the replica shows `core` under the structure. Setting the label to an empty string did not remove it; the publication code falls back to the id when the label is empty. The rendered replica (`rendered.png`) carries the title "Table 1 core", which I set in brief v2.
- Orientation: the paper draws the amide carbonyl at the top and the sulfonamide phenyl at the left. The tool laid the replica out with the benzyl group at upper left and the sulfonamide phenyl at upper right; the bonds are the same kind but the arrangement differs.
- Line weight and proportions are measured and do not match (see the last three rows of the table). The replica's CDXML has a 0.6 pt line where the card implies 1.0 pt, and 8.0 pt labels that put the bond-to-cap ratio near 2.5 instead of 2.25.

## Tool gaps

- No grid or rule primitive: the draw_figure scope path, the publication `sar` mode and the `build_acs_figure` object set (molecule, text, arrow, box, label_box and others) have no table or line object. Cells and headers can be placed as text objects. Rules could only be approximated with boxes, which was not tried. The card's sar_table grid conventions are therefore not reproducible natively as a grid.
- Generic variable labels are available on other paths. `build_acs_figure` (`cdx.py build`) takes a molecule with `[*:n]` dummy atoms and a `labels` map such as `{1: "A"}`; an unmapped dummy atom is labelled `R` by default (`skill/chemdraw/scripts/acs_builder.py`, line 340). `markush_compile` writes generic labels at variable positions from a `markush.json` spec. The earlier `*` attempt went through the draw_figure scope path, which does not map dummy atoms to labels, so its timeout says nothing about label support. Not tried for this figure.
- Scope panels ignore house styles: the report lists house conventions as skipped and applies the base preset only (confirmed: `style.applied` is empty in the replay output), so the `jmed_chem` label and colour conventions are not applied to a scope or structure panel.
- Scope panels add text the caller did not ask for. In code, the draw_figure scope path uses `brief.get("title") or "Substrate scope"` (`figure_scope.py`, line 140), so an empty title is replaced, and the caption falls back to the species id (`publication/data.py`, line 138). The publication_figure layer reads `spec.get('title', default)`, so an explicit empty title may remove the title there. A non-empty whitespace label should avoid the caption fallback. Neither was run.
- Orientation is not controlled on the draw_figure scope path. Other paths can set it: `build_acs_figure` molecule takes `rotate` (degrees), `flip` and per-atom `coords`; the publication molecule takes `rotation`, `coordinates` and `align_to`; `rdkit_workbench` `depict_like` searches 16 candidate orientations or aligns to a reference image. None was tried, so the paper's orientation has not been shown to be reachable.
- Runtime: not reproduced for the draw step. The unrendered replay (render off) finished in about 4 s (`validation.json` was written about 4 s after the log started). The slow step is native rendering: the publication native preview allows 180 s per worker, and the draw_figure tool timeout is 300 s. The `resource_busy` result (`chemdraw_com` busy for 175 s) is consistent with that step, but the native logs are not in this folder, so they could not be checked.

## Rendering

`rendered.png` is the standalone `cdx.py render` of the brief-v2 output (title "Table 1 core", caption "core"). It is 671 x 554 px, under the 1200 px and 250 KB limits. Its scale is consistent with 300 dpi (about 4.2 px per pt).

## Audit

Checked on 2026-11-07 against `reference.png`, `rendered.png`, the house card (`toolkit/cdxml_toolkit/publication/house_styles/jmed_chem.json`), the toolkit source, and a fresh run of `replay.py`. The replay wrote into a temporary folder, not into this folder: `replay-out/figure.cdxml/page-001.cdxml` (`ok: true`, readback matched, native not run).

- Overclaims corrected. "Could not be compared" for line weight and proportions: both were measured and do not match. "draw_figure cannot write R or A" and "the only option is a dummy atom": `build_acs_figure` and `markush_compile` write generic labels. "No orientation control for single structures": other paths have rotate, flip, coordinates, align_to and depict_like. "Cannot be produced by any draw path": only grid rules are absent. "About four to five minutes per draw_figure call": the draw step took about 4 s without render. "No option removes either" the title or the caption: true for draw_figure, untested for the publication layer.
- Confirmed. Arial labels, Kekule bonds (12 double bonds: 9 ring, 3 exocyclic), black-only colour table, no house conventions applied, the default title and the id caption fallback in code.
- Corrected count: 5 of 15 rows. The five "no" rows in the original table were correct as written.
- Not verified: the native render and the `resource_busy` message. The N glyph in `reference.png` is about 30 px tall, against the 22 px cap in the evidence record, so the card's 2.27 ratio cannot be reproduced from `reference.png` at this scale. The card's own line ratio, 0.07, disagrees with its evidence record (3 px / 50 px = 0.06).
- Tool gaps not tried for this figure: `build_acs_figure` labels, rotate and coords; a `publication_figure` title of `""`; `rdkit_workbench` `depict_like`; `markush_compile`. Nothing here shows that any of them would reproduce the paper's core; they are listed as paths the replicator did not test.
