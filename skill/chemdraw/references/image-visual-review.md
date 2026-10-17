# Image reconstruction

Goal: editable CDXML plus a native preview that matches the source image. Prefer existing CDX/CDXML or trusted structures; skip recognition when native structures are available.

## 1. Read the whole image

Note structure labels, arrow connections, conditions, yields and X/R definitions. Conditions and numbering are not molecules — do not send them to DECIMER. The [record template](../assets/paper-replica/task-template.json) is a convenient place to keep structures, corrections and open questions.

## 2. Crop and recognize

Write `regions.json` in original-image pixels (top-left inclusive, bottom-right exclusive):

```json
[{"id":"A","box":[20,10,340,180],"kind":"structure","exclude_boxes":[]}]
```

```bash
cdx.py py <skill>/scripts/image_review_workspace.py prepare source.png regions.json work/crops --scale 4
cdx.py decimer work/crops/A.png --out work/A-decimer.json
```

Look at each crop: terminal labels (OMe, CN, …) and stereobonds must be complete. Exclusion boxes may remove nearby arrows or labels, never chemistry. One image per call; run independent crops in turn. Never draw an invalid prediction — change the crop or scale instead.

## 3. Correct chemistry, then depth, then orientation

A parseable SMILES is only a candidate. Before any typography, fix connectivity, bond orders, charges and abbreviation subgraphs:

```bash
cdx.py call modify_molecule --json '{"mol_json": {"smiles": "<recognized>"}, "operation": "set_smiles", "new_smiles": "<corrected>", "description": "A: source shows OH, recognized as methyl"}'
```

Read the returned diff status: a null MCS or `partial`/`not_completed` does not mean "no change".

At every crossing decide: occluded solid bond (keep one bond, set depth with `crossings`), dashed bond, or hashed wedge. A crossing never creates an atom. See [publication figures](publication-figures.md) for `crossings` and bond-display edits.

Place molecules with `compose_chemical_figure`:

```json
{"version":1,"objects":[
  {"type":"molecule","id":"A","file":"A-corrected.mol","position":[120,100]}
]}
```

For an exact source orientation, replace `position` with `coordinates` — one `[x,y]` (points, y down) per atom in MOL/SMILES order: `source_xy = crop_xy / scale + box_origin`, then `point_xy = source_xy * points_per_pixel + offset`, with uniform scaling. Do not mirror or stretch. Wedges are recalculated from the final coordinates.

```bash
cdx.py call compose_chemical_figure --json '{"manifest_path": "<abs>/figure.json", "output_path": "<abs>/figure.cdxml"}'
```

R/X abbreviations must be real atom subgraphs with attachment points (see the runnable examples); there is no generic `abbreviations` manifest field.

## 4. Render, compare, fix

```bash
cdx.py render figure.cdxml
cdx.py py <skill>/scripts/image_review_workspace.py compare work/crops/A.png figure.png work/A-review-r1.png --height 400
```

Open the comparison image and look at it. Fix only the affected structures, then look at the whole figure again. Leave unreadable source details as open questions instead of filling them in from reaction expectations.

## 5. Conditions and delivery

Keep the condition wording and order, structure labels and yield scope ("70% (3 steps)" covers all three steps). Keep relative descriptions for shared wavy-bond structures with a/b labels; do not invent absolute stereoisomers. Use rich-text runs for sub/superscripts.

Deliver the editable CDXML and the preview, plus any open questions. For bridges, charge symbols or stereo-sensitive edits, also run [saved-file validation](figure-validation.md).

## Common issues

| Issue | Approach |
| --- | --- |
| Folded chains or bridged crossings | Trace each bond; crossing lines alone create neither an atom nor a ring closure. |
| Ph/Pb, OH/methyl, OMe/OH, CN, X/R | Check these first against the full-image definitions. |
| Wavy bonds, α/β, R/S | Record each separately. Unspecified is not racemic; a changed CIP label need not mean inversion. |
| Coordinate/wedge changes | Check the narrow end and the attached atom after recomputing wedges. |
| Bridged stereo missing or readers disagree | Compare RDKit readback with `cdx.py chemscript-info` on the same saved file; see [stereo diagnosis](stereo-reconstruction.md). Never flip wedges to force agreement. |
| Reversed or wrapped abbreviations | Set node/text alignment and font runs explicitly; leave enough page width. |
| Wrong bridge depth | Use native front/back `crossings` edits; do not cover mistakes with extra lines. |

## Runnable examples

- [Two complete publication schemes](../assets/paper-reconstructions/README.md): native components, layout manifests and an offline assembly script — `cdx.py py <skill>/assets/paper-reconstructions/rebuild.py NEW_DIR`. Covers shared OR groups, abbreviations, folded chains, bridge occlusion and electron arrows.
- [Drawing example](../assets/paper-replica/example/CASE.md): manifest, CDXML and offline replay with arrows, electron curves, rich text, chirality and enhanced stereo — `cdx.py py <skill>/assets/paper-replica/example/replay.py NEW_DIR`.

## Comparison modes

`compare` defaults to a side-by-side visual panel (panels may be resized). `--mode aligned --offset DX DY` compares at the original scale and reports MAE and ink IoU; `--region X1 Y1 X2 Y2 --height N` zooms into one area. Pixel scores help find differences; they do not decide chemistry. See [lessons](lessons.md) for known mistakes.
