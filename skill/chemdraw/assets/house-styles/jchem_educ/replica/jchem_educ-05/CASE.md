# jchem_educ, Figure 15 (structure only): pentyl-X chain with wedge and hash H pairs

Source: Elliott et al., "Exploring the interface of hyperconjugation and polarizability", *J. Chem. Educ.* **2026**, DOI [10.1021/acs.jchemed.6c00708](https://doi.org/10.1021/acs.jchemed.6c00708). Licence: CC BY 4.0 (from the `jchem_educ` card). The crop `evidence/jchem_educ-05.png` is Figure 15 (structure only) of that article, as recorded in the card.

Figure type: `stereo_model` (card section `figure_types.stereo_model`, which cites crop 05 for the wedge/hash H pairs and the a/b bond labels).

Drawing style: the `jchem_educ` house style in `brief.json`. Only its base preset applies, because `kind: "scope"` takes only the base preset, so none of the house conventions are drawn.

## What is reproduced

Nothing has been drawn yet. This section records what the specification covers.

The crop shows a five-carbon zigzag. C1 is a CH3 carbon with all three hydrogens drawn: one plain bond to the lower left, and one bold wedge H and one hashed H above it. C2 to C5 are CH2 carbons, each drawn with one bold wedge H and one hashed H; C5 carries a generic X. Bond a (on C1, beside its hashed bond) and bond b (on C2, beside its wedged bond) are labelled in orange-red.

Only the skeleton is specified, as `CCCCC[*]` (pentyl with a dummy atom for X). RDKit reads it as `*CCCCC`, 6 heavy atoms, implicit H counts 3, 2, 2, 2, 2, 0 (rechecked in the audit). The SMILES was written from the crop. OCSR (decimer-api) returned an invalid SMILES with deuterium and stereo-marked hydrogens and was not used. The SMILES has no hydrogen atoms, so none of the drawn H can be specified from it.

The `draw_figure` brief could not express the wedge/hash H pairs or the a and b labels. The replica would show a plain skeleton with implicit hydrogens, but it was never rendered (see Runtime status). The manifest route (`compose_chemical_figure`) was not tried (see Tool gaps).

## Replay

`replay.py` is the jacs-au script with only the docstring changed. It runs `draw_figure` on `brief.json` offline. For `kind: "scope"` the output argument is a folder, so the script writes `figure.cdxml/` (a folder holding `page-001.cdxml`) and `validation.json` into the new directory.

```
python skill/chemdraw/scripts/cdx.py py skill/chemdraw/assets/house-styles/jchem_educ/replica/jchem_educ-05/replay.py NEW_DIR
```

## Runtime status

No rendered PNG exists. Four `draw_figure` attempts were reported, and none returned a result:

1. `kind: "scope"` with `--render` (background): the wrapper stopped it after 300 s with `tool_timeout: draw_figure exceeded 300 seconds`.
2. Same brief, `CHEMDRAW_OFFLINE=1`, no render, 150 s cap: `worker_crashed`, exit code 143, no output.
3. A two-species scheme probe (`jchem_educ` style, offline), 100 s cap: `worker_crashed`, exit code 143. This shows the scheme path is blocked too, not only the scope path.
4. Same brief as 1, offline, `--render`, 280 s cap: `worker_crashed`, exit code 124 after 276 s.

The attempt logs are not in this folder, so these counts and exit codes are the replicator's report and were not re-checked. All four used `draw_figure`. The manifest route (`compose_chemical_figure`) was not tried. Its CDXML writing makes no ChemDraw call (`figure_tools.py` has no ChemDraw or COM reference, and its report marks native render as `not_run`), so the block applies to `draw_figure` and to any ChemDraw render, not to writing the CDXML.

The likely cause is the native ChemDraw automation mutex (`Local\CodexChemDrawComAutomation`, taken through `native_resource_lock('chemdraw_com', ...)` in the runtime's `figure_validation.py`). This is not verified. Eleven ChemDraw.exe processes were running when the audit ran. They belong to other sessions and were not stopped. The brief allows one retry, so this is reported as blocked, not as a result.

## Comparison (structure reasoning from the crop; no render)

| convention or signature feature | paper | replica | match |
| --- | --- | --- | --- |
| stereo_model `model_style: perspective_3d` (wedge/hash H pairs on each carbon) | paired bold wedge and hashed H on C2 to C5 and on C1 (CH3), plus one plain H on C1 | skeleton with implicit H, no wedge or hash | no |
| every hydrogen shown with a bold wedge or hashed bond (signature feature) | every H on C1 to C5 is a wedge or hash H, except the one plain H on C1 | none shown | no |
| bonds of interest labelled a and b in orange-red (signature feature) | a beside the hashed C1 bond, b beside the wedged C2 bond, orange-red (core pixels of reference.png about #E74B21; the card gives no hex for a/b, and #E43800 is the crop 06 shift colour) | not drawn | no |
| explanations as plain text with thin leader lines (signature feature) | not in crop 05 (it is in crop 04) | not drawn | not counted |
| `ts_marker`, `highlight_fill`, `variation_color` null | none in crop 05 | none | consistent, not counted |
| top-level bond length to cap height 2.2 | in reference.png (409 x 140 px): C1 to C2 bond about 47 px, H cap height 22 px, ratio about 2.1 to 2.15 (measured on the pixels) | not rendered | not checked (the reference ratio is confirmed) |
| top-level compound label, aromatic and arrow conventions | no compound label, ring or arrow in crop 05 | n/a | not applicable |

Claimed for this figure type: 3 (the model style, the every-hydrogen wedge/hash feature and the orange-red a/b labels). Matched: 0. The leader-line feature is not counted because crop 05 does not show it.

## Differences from the paper

- The wedge and hashed H pairs on C1 to C5 and the plain H on C1 are not drawn; implicit hydrogens are used.
- The three H on C1 (one plain, one wedge, one hash) are implicit in the replica.
- The a and b labels in orange-red are not drawn.
- X is a dummy atom, not a labelled group.
- Output would be a scope-panel structure, not a perspective model.
- Nothing was rendered, so no visual comparison of proportions, line weight or label size is available.

## Tool gaps

The replicator's list, checked against the toolkit source and `skill/chemdraw/references/publication-figures.md`:

1. Stereo or perspective model. Confirmed for `draw_figure`, which accepts `scheme`, `scope` and `mechanism` only. Missed: `compose_chemical_figure` (manifest v1) places molecules at explicit 2D coordinates, so a perspective layout can be specified by hand. It has no automatic projection, so the coordinates must be set by the drawer.
2. Species input and wedge/hash H. Confirmed for `draw_figure`, where species take `smiles` or `name` only. Missed: a manifest molecule accepts `molblock` (read with explicit hydrogens kept) and `bond_displays`, keyed by bond index, with `WedgeBegin`, `WedgedHashBegin` and the other stock displays. Plain `Hash` is refused in fresh generation, so use `WedgedHashBegin` or `WedgeBegin`. Not tested: whether the stereo readback accepts wedges on these non-stereogenic CH2 carbons.
3. Coloured annotation. Overstated. A manifest `text` object takes `position`, `text` or `runs`, `size`, `align` and `color` (six-digit hex), and each run takes its own `color`, so the a and b labels can be placed as coloured text at measured coordinates. What is missing is an annotation bound to a bond: the label is positioned by coordinates, not attached to the bond.
4. Single structure as a scheme. Confirmed for `draw_figure`. Missed: `draw_molecule` (one molecule to CDXML, no ChemDraw needed, per `mcp-signatures.md`) and a manifest holding one molecule.
5. Draw runtime blocked. Confirmed only for `draw_figure`; the manifest route was not tried. Missed: `chemdraw_object` lists, gets, sets, adds and deletes any CDXML element, text included, and writes a new file (the input is never changed); `edit_bond_display` accepts `Hash` for template edits.

Remaining real gaps: no automatic perspective projection; no annotation bound to a bond; plain `Hash` refused for fresh generation; no native render was possible in this run, so no visual check exists; the H pairs and the a/b colour have not been tested in ChemDraw.

## Audit

Audit on 2026-11-07. The audit read `reference.png`, this file, `brief.json`, `replay.py` and the `jchem_educ` card, then checked the toolkit source. No replica image exists in this folder, so no row can be matched.

Overclaims and errors, corrected above:
- C1 was described as a CH3 with a plain H only, and its H as implicit. The reference draws all three H on C1: one plain bond, one wedge H and one hash H. Corrected in the description, the table and Differences.
- The wedge/hash pairs were said to be on "each CH2". C1 (CH3) carries them too.
- "What is reproduced" read as a reproduction. Nothing was drawn. Corrected.
- Tool gaps 2, 3 and 4 and the blanket runtime block were stated as absolute. The toolkit has a manifest route (`compose_chemical_figure`) and `draw_molecule`, neither tried. Corrected in Tool gaps and Runtime status.

Confirmed: five carbons with X on C5; a sits beside the hashed bond on C1 and b beside the wedged bond on C2; the H pattern otherwise as described; the RDKit H counts; the bond (about 47 px) to cap height (about 22 px) ratio of about 2.1 to 2.15.

Corrected matched count: 0 of 3. Nothing was rendered, so no row can be matched.

Not verified here: the four attempt logs and exit codes, the OCSR result, and the mutex cause.
