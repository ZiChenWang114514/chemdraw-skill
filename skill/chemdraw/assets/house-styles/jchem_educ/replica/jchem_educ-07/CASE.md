# J. Chem. Educ.: deuterium-labelled structure 1-d (Figure 4, structure box)

Source: Deufel, van Gemmeren et al., "Deuteration of arenes via Pd-catalyzed C-H activation: a lesson in nondirected C-H activation", *J. Chem. Educ.* **2024**. DOI: [10.1021/acs.jchemed.4c00270](https://doi.org/10.1021/acs.jchemed.4c00270). Licence: CC BY 4.0 (from the house-style card). Reference crop: `reference.png` (copy of `evidence/jchem_educ-07.png`, 290 x 330 px).

Drawing style: the `jchem_educ` house style in `brief.json` (base preset acs1996). Figure type: `assignment_panel`.

## What is reproduced

Only the structure of compound 1-d, with its compound label. The crop shows one structure on a light grey box, with the deuterium content of each ring position (13%D, 30%D, 50%D) in bold teal next to the ring H, and a teal X and A marking the substituent position on carbon A. The brief draws the skeleton and the label "1-d" as a `kind: "scope"` panel with one compound and no values.

Structure reading (from the crop; checked with RDKit):

- 2,4-dihydro-1,5-benzodioxepin-3-one core: a benzene ring fused to a seven-membered O-CH2-C(=O)-CH2-O ring.
- Three aromatic CH positions (the 13%D, 30%D and 50%D positions) and one ring carbon (A) bearing the substituent X.
- X is not identified in the crop. The brief uses a dummy atom `*` as a placeholder, so the SMILES `O=C1COc2cc(*)ccc2OC1` is a generic placeholder for "X on ring carbon A", not a defined compound. RDKit reads it as C9H7O3* with three aromatic CH.

Not reproduced: the three %D values, the teal X and A labels and the teal dot on carbon A, the grey #EBEBEB box, the bold teal colour, and the yield (the card's 72% is not in this crop; the crop shows no yield and no DTot values, so the card note for crop 07 is wrong).

## Render status

Not rendered. `rendered.png` was not produced. The `draw` runs did not complete in this session: the `scope` brief and a plain `scheme` probe brief did not finish, and `cdx.py doctor` hung after printing. Two `--render` runs ended with `tool_timeout` (draw_figure exceeded 300 seconds), and the non-render scope run and scheme probe ended with `worker_crashed` (exit 143) after the 100-second shell timeout. The replicating agent reported many other ChemDraw and Python processes active at the same time and named the shared ChemDraw native resource lock as the likely cause. No log of these runs is kept in this folder, so the cause is not confirmed; the toolkit's ChemDraw lock is a named mutex with 120 to 300 second timeouts, which fits the 300 second timeout but has not been tested. This is an environment blocker, not a drawing result. Nothing in the table below has been checked against a render.

## Replay

```
python skill/chemdraw/scripts/cdx.py py skill/chemdraw/assets/house-styles/jchem_educ/replica/jchem_educ-07/replay.py NEW_DIR
```

`replay.py` is the `jacs-au-pd-amination` script with a new docstring. For a `scope` brief the output path is a folder, so the file it writes is a folder named `figure.cdxml` holding `page-001.cdxml`. Not run in this session.

## Conventions

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| assignment_panel: deuterium % per position in bold teal #006C88, placed beside the ring H (13%D, 30%D, 50%D) | bold teal text beside each ring H | not drawn: a scope panel puts values in table columns below the structure, not beside an atom | no |
| assignment_panel: structure on a light grey #EBEBEB box | grey box behind the structure (measured fill about #ECECEC) | no box: scope panels have no background fill, and highlight_fill applies only to schemes | no |
| assignment_panel: compound label bold, italic d suffix (card: 1-dx, crop: 1-d) | bold "1-d", italic d | label "1-d" set; scope panels take the base preset only, so the italic suffix is not applied and the bold face is not verified | not verified |
| assignment_panel: yield 72% in bold under the structure (card note) | not in this crop | not drawn | n/a (card error: the card note says crop 07 shows it; it does not) |
| assignment_panel: DTot values (card observation) | not in this crop | not drawn | n/a (card error: the card observation says crop 07 shows them; it does not) |
| teal X and A position labels with a teal dot on carbon A (not in the card) | teal X and A | X is a dummy atom `*` with no label text and no colour | no |
| top-level compound_label_color #000000 | black | label colour follows the base preset; not verified | not verified |
| top-level aromatic_rings kekule | benzene ring drawn Kekule (confirmed at crop resolution only roughly) | aromatic SMILES; ChemDraw's default Kekule form not checked | not verified |
| structure: benzodioxepinone core with three ring CH and one substituted carbon | same | SMILES reads as the same core (RDKit in the toolkit runtime: C9H7O3*, 3 aromatic CH, rings of 6 and 7 atoms) | not verified (no render) |

## Differences from the paper

- The %D labels (13%D, 30%D, 50%D) are not drawn. They are positional text beside each ring H in the paper; the tool has no way to place text at an atom of a structure in a scope panel.
- The grey #EBEBEB box is not drawn.
- The teal X and A position labels and the teal dot are not drawn. X is a placeholder `*` atom, not a defined substituent.
- The label is plain text "1-d" from the scope panel, so the italic d is not applied.
- The 72% yield and the DTot values in the card are not shown in this crop and are not drawn.
- The figure is a scope panel with one compound, so it has the panel's page size (60 x 60 mm set in the brief) rather than the paper's crop size.

## Tool gaps

- No single-structure or structure-panel kind in `draw_figure`: the scheme needs at least one step, and the scope kind is a table of compounds with label and value columns. Other tools draw single structures: `draw_molecule`, `build_acs_figure` and `compose_chemical_figure` (see Audit).
- No per-atom text annotation in `draw_figure`: values or labels cannot be placed beside a given ring position of a structure. `build_acs_figure` text objects can be placed at atom coordinates (see Audit).
- No background box or fill behind a single structure (highlight_fill applies to the largest ring of a scheme product only).
- Scope panels apply only the base preset, so house label conventions (italic isotopologue suffix, bold face, colour) are not applied.
- No atom label such as "X" in `draw_figure`; only a dummy `*` atom. `build_acs_figure` labels a dummy atom from its atom-map number (see Audit), but that path has not been rendered.
- Rendering blocked in this session (see Render status): a shared-lock wait or hang in the draw worker, not a drawing defect.

## Audit

Re-checked from the reference crop, the card and the toolkit source (the toolkit's `figure_draw.py`, `figure_scope.py`, `figure_house.py`, `acs_builder.py`, `resource_lock.py` and `docs/mcp-tools.md`). Nothing was rendered.

- Reference crop: `reference.png` is 290 x 330 px and is byte-identical to `evidence/jchem_educ-07.png` (same MD5). The grey box fill is #ECECEC (about 58,000 pixels; the card says #EBEBEB). The box runs to the crop's right and bottom edges, so its full size is not visible. The teal labels sample near #006C88.
- Proportions: the brief is square (60 x 60 mm) and the reference is portrait (290 x 330 px). Proportion, line weight, bond length and label size are not matched, and cannot be measured from a 290 px crop.
- Card errors: the card's crop-07 note and evidence observation say the crop shows a bold 72% yield and DTot values. It shows neither, so the yield and DTot rows are card errors, not convention matches.
- RDKit: re-run in the toolkit runtime, the SMILES gives formula C9H7O3*, 3 aromatic CH, and rings of 6 and 7 atoms. The structure graph agrees with the crop; the drawing does not.
- Replay: `replay.py` differs from `jacs-au-pd-amination/replay.py` only in its docstring. The scope output-folder behaviour matches the `draw_figure` docstring. Not run.
- Overclaims corrected above: `cdx.py doctor` is now "hung after printing", as the replicating agent reported; "see card errors in the result" pointed to a result that is not in this folder; the ChemDraw lock as the cause is marked as unconfirmed; the atom-label and per-atom-text tool gaps were stated as absolute.

Corrected match count: 0 of 7. No row is a match, and none can be upgraded without a render.

Tool gaps the replicating agent missed (from the toolkit source and docs, none rendered):

- Single structures: `draw_molecule` draws one molecule to CDXML. `build_acs_figure` builds a figure from molecule, text, box and arrow objects with explicit coordinates. `compose_chemical_figure` places molecules at exact atom coordinates, with labels and rich text.
- Free text with colour: `build_acs_figure` text objects take position, size, bold and colour, so the %D labels and the X and A labels can sit at atom positions. The positions come from the molecule's `coords` input or from reading a saved CDXML with `chemdraw_object`.
- Atom labels: `build_acs_figure` sets a dummy atom's label from its atom-map number, so `[*:1]` with labels {1: "X"} gives an X label. An unmapped dummy is labelled R by default, not left blank, so the brief's `*` would show R on that path.
- Italic suffix: `figure_house.py` skips `compound_label_italic_suffix` on the scheme path too ("not applied yet"), so this gap is not limited to scope panels.
- Background box: `build_acs_figure` box objects have no fill attribute. A grey fill may be possible through `chemdraw_object` add, but the catalog's only observed `FillType` value is None, so this is unverified.
- `chemdraw_object` writes a new CDXML and checks it without ChemDraw; only rendering the result needs ChemDraw, which is where the lock applies.
