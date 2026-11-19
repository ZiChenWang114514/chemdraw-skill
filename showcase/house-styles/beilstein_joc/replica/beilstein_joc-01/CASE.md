# Beilstein JOC 2025: Pd-catalysed azobenzene synthesis (Scheme 1, crop 01)

Source: Beller et al., "Pd-catalyzed dehydrogenative arylation of arylhydrazines to access non-symmetric azobenzenes", *Beilstein J. Org. Chem.* **2025**, *21*, 170. DOI: [10.3762/bjoc.21.170](https://doi.org/10.3762/bjoc.21.170).

Licence: CC BY 4.0 (Beilstein-Institut), as recorded on the house-style card. `reference.png` is the evidence crop, reproduced under that licence.

Drawing style: house style `beilstein_joc` (base preset `nature`), card `toolkit/cdxml_toolkit/publication/house_styles/beilstein_joc.json`. Figure types: `reaction_scheme` (general reaction on top) and `substrate_scope` (product grid).

## What is reproduced

1. The general reaction at the top of the crop, `1a` + `2b` to `3b`, with the catalyst and ligand above the arrow and base, water, solvent, temperature, time and O2 below, as printed. The 2b to 2q family is generic (R); the replica draws 4-bromotoluene (`2b`) and its product `3b` as the representative member. The paper scheme prints no yield, so none is drawn.
2. A six-entry part of the substrate grid: `3b`, `3h`, `3j` (para series) and `3c`, `3d`, `3f` (ortho series), with their yields from the crop (`brief-scope.json`). Not drawn: `3e`, `3g`, `3i`, `3k`, `3l`, `3m` to `3q`, the grey rule and the `R = ...` row labels.

Files: `brief.json` (scheme, `rendered.png`, 1200 x 240 px) and `brief-scope.json` (scope, `rendered-scope.png`, 1200 x 755 px). `replay.py` replays `brief.json` only; it was run offline and exited 0. The scope brief was drawn without `--render` (layout checks passed, zero warnings) and rendered from its `page-001.cdxml` with `cdx.py render`, because `draw ... --render` hit the 300 s tool limit twice for the scope brief.

Structures: read from the crop without OCSR. Every product SMILES was checked with RDKit (formulas: `3b` C13H12N2, `3c` C13H9F3N2O, `3h` C14H12N2O2, `3j` C12H9N3O2, `3d` C13H12N2O, `3f` C12H9FN2). The azo bond is written with E stereo, for example `Cc1ccc(/N=N/c2ccccc2)cc1`. The paper draws no E/Z; the E form is the usual azobenzene geometry and is an assumption here. Without the stereo the scheme was refused (see Tool gaps).

## Convention table

Claimed = the conventions the card gives for `reaction_scheme` and `substrate_scope`, plus the top-level conventions visible in this crop. Match compares the replica with the paper.

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| reaction_scheme: catalyst above arrow, base/solvent/temperature/time below | `[PdCl(allyl)]2 (1 mol %)`, `t-BuXPhos (4 mol %)` above; `Cs2CO3 (2 equiv)`, `H2O (2 equiv)`, `DME, 90 °C, 15 h`, `O2 (1 atm)` below | same lines above and below | yes |
| reaction_scheme: one item per line below the arrow (card, crops 01 and 02) | `DME, 90 °C, 15 h` on one line | `DME, 90 °C, 15 h` on one line, as the paper | yes to the paper; the card's "one item per line" is contradicted by crop 01 and needs correcting in the card |
| reaction_scheme: colours chosen by authors | purple Ph, dark red aryl C-Br bond | all black | no |
| top: compound_label_face bold | `1a`, `2b`, `3b` bold | bold | yes |
| top: compound_label_color #000000 | black | black | yes |
| top: reagent_text_color #000000 | black | black | yes |
| top: arrow_style plain | plain arrow | plain arrow | yes |
| top: show_plus_sign, substrate_layout inline_plus | `1a + 2b` inline | `1a + 2b` inline | yes |
| top: aromatic_rings kekule | Kekule rings | Kekule rings | yes |
| top: abbreviate_groups Ph | `Ph` | `Ph` | yes |
| top: t-Bu written with italic t | `t-BuXPhos`, italic t | italic t in the scheme conditions | yes |
| top: conditions_split reagents_above_solvent_below | catalyst above, base and solvent below | same split | yes |
| top: sans-serif (Arial-like) text | sans-serif | sans-serif | yes |
| top: new_bond_color and substrate_colors null | author colouring on the aryl-Br bond and Ph | no colour applied | no |
| substrate_scope: grid layout | ortho and para series in columns, with `R = ...` rows; meta and other compounds in a third column | three columns, but 3b, 3h, 3j share row 1 with ortho 3c, 3d, 3f; no series grouping and no `R = ...` rows | no |
| substrate_scope: general reaction on top (conditions_position scheme_on_top) | general reaction above the grid | conditions as one plain text line above the grid, no structures | no |
| substrate_scope: full-width thin grey rule under the general reaction | present | absent | no |
| substrate_scope: label and yield on one line (bold label, then yield) | `3c R = OCF3, 69%` | label and yield on separate lines | no |
| substrate_scope: compound_label_face bold in scope panels | bold labels | plain labels | no |
| substrate_scope: yield_format `{value}%` | `69%` | `50%` | yes |
| substrate_scope: shared core as `R = ...` rows under one drawing | ortho and para series, one drawing each | every compound drawn separately | no |
| substrate_scope: abbreviate OMe and CO2Me | `R = OMe`, `R = CO2Me` | OMe, CO2Me and OCF3 drawn expanded | no |
| substrate_scope: footnote as superscript a after the yield | `3q 66%^a` | not drawn (3q outside the subset) | no |
| substrate_scope: variation_color and highlight_fill null | no fills, but author colouring in the scope panel: purple Ph, blue N=N and blue bonds | no fills, no colour | no (the no-fill part matches; the author colouring does not) |

Matched 15 of 23 claimed conventions (replicator's count). The table has 24 rows; after the audit 13 of 24 rows match (see Audit).

## Differences from the paper

- Top scheme: no thin grey rule under the general reaction (the paper has a full-width rule).
- Top scheme: the `(1 equiv)` lines under `1a` and `2b` to `2q` are not drawn.
- Top scheme: generic R is replaced by 4-methyl (`2b`) and product `3b`.
- Top scheme: the paper colours the Ph of `1a` and `3b` purple and the aryl-Br bond dark red; the replica is black. The card leaves these colours null.
- Scope: a default title "Substrate scope" is added (the paper has none).
- Scope: conditions are one plain line, not a general scheme with structures on top.
- Scope: labels are plain (the paper uses bold), and the yield sits on its own line below the label instead of after the label on one line.
- Scope: `t-BuXPhos` in the conditions line is plain (italic t applied only in the scheme).
- Scope: each compound is drawn separately; the paper draws the ortho and para series once with `R = ...` rows.
- Scope: OMe, CO2Me and OCF3 drawn as expanded atoms; the paper abbreviates them. The nitro group of `3j` is drawn as N+/O- (the paper writes NO2 in the row label).
- Scope: 6 of the 16 compounds in the crop; footnote a on `3q` not shown.
- Proportions: the scheme arrow is 380 px long in a 1200 px wide render (0.32 of the width). In the crop the arrow is 211 px in a 775 px image (0.27). No bond-length or label-height measurement was taken, so the bond/cap-height ratio on the card (2.25) is not verified.

## Tool gaps

- No thin full-width grey rule between a general reaction and a product grid, in either scheme or scope output.
- Scope panels apply only the base preset. The house conventions (bold labels, `after_product_label` yield, `abbreviate_groups`, `t-Bu` italic, label/yield layout) are not drawn, so the card's scope conventions cannot be reproduced in a scope panel.
- Scope panels have no scheme-on-top: `conditions` is a single plain text line, not a reaction drawing above the grid.
- Scope panels always add the title "Substrate scope". Source check: `figure_scope.py` sets `"title": brief.get("title") or "Substrate scope"`, so an empty string, null or a missing title all fall back to the default. No empty title can suppress it. A single space is truthy and was not tested.
- Scope panels cannot place a value on the label line (`3b  50%`). A field with an empty label puts the value on its own line below the label.
- Scope panels cannot draw a shared core as `R = X` rows under one structure; every compound gets its own drawing.
- Footnote superscripts (for example `66%^a`) cannot be drawn in a scope panel: its text is plain (see the text gap below). The `3q` entry is outside the subset.
- Per-fragment colour is not available: `substrate_colors` colours whole substrates by step, so the purple Ph group and the dark red aryl-Br bond cannot be coloured separately. The species options `ring_fills` and `atom_halos` exist but draw fills and halos, not coloured bonds or atom text, so they do not give the author colouring.
- No species-level note line for plain text under a bold substrate label, so the `(1 equiv)` lines are not drawn.
- No generic R placeholder was used for the 2b to 2q family; the replica substitutes 4-methyl. Whether the markush brief covers this was not tested.
- Undefined azo (N=N) stereo is refused: a stereo-free `N=N` is round-tripped by ChemDraw as E (`/N=N/`), and `draw_figure` stopped with `chemical_semantics_changed`. The brief must carry explicit E stereo for azobenzenes, which the paper does not show.
- Balance: the paper omits by-products (H2O, HBr, H2 with O2 as oxidant). `draw_figure` warns that the step does not balance ("products lack BrH3") and cannot express "by-products not drawn" as a house convention. The warning is advisory; `checks_passed` was true.
- Render reliability: the first scheme `--render` attempt returned worker_crashed (exit 143) at 277 s under a 280 s wrapper, so the cause is not established; a later attempt on a fresh output name succeeded. The scope `--render` run hit the 300 s tool limit twice. Layout without render followed by `cdx.py render` on the CDXML worked.
- Scope text is plain, with no subscript or superscript runs. `publication/layout.py` writes labels, values, conditions and footnotes as plain text; subscripts come only from the scheme path. In `rendered-scope.png` the conditions line shows `Cs2CO3`, `H2O`, `O2` and `[PdCl(allyl)]2` with the digits on the baseline.
- Scope panels take only `width_mm` and `height_mm` from the brief. Bond length, line width and bold width come from the base preset, and text size stays at the 8 pt default (`figure_scope.py` pops the preset's font size). The card's proportions (bond/cap 2.25, line/bond 0.068) therefore cannot be set for a scope panel.
- Scope panels have no line object: the layout writes only `text` and `molecule` objects, so no grey rule of any kind can be drawn.
- Render time: `publication_figure.py` renders PNG and then SVG, each with a 180 s timeout, so one scope render can run up to 360 s, past the 300 s tool limit. This is a source fact; the scheme `worker_crashed` cause was not investigated.

## Audit

Checked against reference.png, rendered.png, rendered-scope.png, brief.json, brief-scope.json, the house card and the toolkit source (`figure_scope.py`, `publication/layout.py`, `publication_figure.py`, `figure_draw.py`).

- Two overclaims corrected: the scope grid row (the paper groups ortho and para series with `R = ...` rows) and the variation colour row (the paper's scope panel has purple Ph and blue N=N and bonds; the replica has none).
- Count: the table has 24 rows, not 23. After the corrections, 13 of 24 rows match.
- Confirmed in the crops: bold `1a` and `3b`, italic `t` in `t-BuXPhos`, plain arrow, inline plus, `Ph` abbreviation, catalyst above and conditions below, `{value}%` format.
- Card error: crop 01 shows `DME, 90 °C, 15 h` on one line, so the card's "one item per line" claim is wrong for that crop. The table previously cited a `card_errors` field, which the card does not have.
- Arrow ratio: replica 380 of 1200 px (0.32), reference 211 of 775 px (0.27); the earlier 1213 px width was wrong.
- Not measured: proportions and line weight. No row claims a match on either, so they stay unverified.
- Formulas: the hand counts for 3b, 3c, 3h, 3j, 3d and 3f agree with the table. The RDKit check was not rerun.
