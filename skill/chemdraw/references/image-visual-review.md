# Reconstructing publication reaction figures

Deliver editable CDXML and a native preview by default. Provide a longer report only when requested. Prefer existing CDX/CDXML or trusted structures and skip OCSR when native structures are available.

## 1. Inspect the complete image

Read structure labels, arrow connections, conditions, yields, and X/R definitions. Do not submit conditions or numbering to DECIMER as molecules. Adapt the [record template](../assets/paper-replica/task-template.json) to the actual structures; it is not a drawing API schema. Start with the existing tools without scanning the full catalog or reinstalling the environment.

## 2. Crop and recognize structures

Write `regions.json` using original-image display pixels, with inclusive top-left and exclusive bottom-right boundaries:

```json
[{"id":"A","box":[20,10,340,180],"kind":"structure","exclude_boxes":[]}]
```

Use the existing MCP Python environment. `<skill>` denotes the installed skill directory:

```powershell
& <MCP-Python> <skill>/scripts/image_review_workspace.py prepare source.png regions.json work/crops --scale 4
```

Use a new output directory. Inspect crops for complete terminal labels, OMe, CN, and stereobonds. Exclusion boxes use original-image coordinates and may remove nearby labels or arrows, never chemical information. Preserve the source. The helper records crop hashes and coordinate transforms; upscaling cannot recover missing detail.

Default to DECIMER API. Use local models only for an explicit local/offline request; never switch automatically after API failure. For task images and relevant crops, call the API with `confirm_upload=true` directly; do not ask a separate upload-authorization question. Respect explicit local/offline or no-upload requests.

```python
extract_structures_via_decimer_api(
    image_path="<absolute>/work/crops/A.png",
    output_path="<absolute>/work/A-decimer.json",
    confirm_upload=True, timeout_seconds=120)
```

This is a single-image interface. Process independent crops concurrently only when supported; do not invent batch parameters. Save raw responses including invalid SMILES. Reuse cached predictions when crop hashes match. Change cropping or scale to address specific recognition errors, and never draw invalid predictions.

## 3. Correct chemistry, depth, then source orientation

Before typography, review connectivity, bond orders, charges and abbreviation subgraphs. A valid OCSR SMILES is only a candidate. Record correction reasons and unresolved details in the same task record as crop hashes, predictions and coordinate mappings.

Inspect local crops of every ambiguous crossing. A solid bond interrupted only at an intersection is occluded, not a repeated dash. A hashed wedge can encode stereo. Do not create an atom or split the chemical bond at a visual crossing. Use the explicit native `crossings` and bond-display template edits in [publication figures](publication-figures.md), then inspect both local and whole native previews. Resolve structure and depth before font/layout iteration.


Check obvious recognition errors and X/R definitions first. Use constrained alignment for ordinary structures and trace atom coordinates for folded chains or bridged rings. Try a few rotations only when direct alignment fails; do not mirror or stretch structures.

Use `compose_chemical_figure(manifest_path, output_path)` with a drawing manifest:

```json
{"version":1,"objects":[
  {"type":"molecule","id":"A","file":"A-corrected.mol","position":[120,100]}
]}
```

For precise orientation, replace `position` with `coordinates`: one `[x,y]` per input atom in points, positive rightward and downward. Use actual MOL/SMILES atom order; indices cannot be reused after canonical reordering. Convert coordinates with `source_xy = crop_xy / scale + box_origin`, then `point_xy = source_xy * points_per_pixel + offset`. Use uniform scaling. The renderer recalculates wedges from final coordinates and checks readback.

If the MCP tool is not visible, use the existing CLI:

```powershell
& <MCP-Python> -m cdxml_toolkit.mcp_runtime.figure_tools compose_chemical_figure --arguments draw-args.json
```

`draw-args.json` contains `{"manifest_path":"<absolute>/figure.json","output_path":"<absolute>/figure.cdxml"}`. See [drawing fields](publication-figures.md) when needed. Runnable examples demonstrate grounded R/X abbreviations and bridged rings; do not invent a generic `abbreviations` manifest field.

## 4. Render, compare, and correct

```python
render_cdxml_files(input_paths=["<absolute>/A.cdxml", "<absolute>/B.cdxml"],
                   output_dir="<absolute>/work/native-r1", format="png", dpi=144)
```

Use the isolated native worker and shared lock, not an additional unlocked COM session. Create a comparison from the returned native output:

```powershell
& <MCP-Python> <skill>/scripts/image_review_workspace.py compare work/crops/A.png work/native-r1/A.png work/A-review-r1.png --height 400
```

Open and inspect the comparison. Successful generation, hashes, and display scales do not establish visual correctness or prove native-renderer provenance.

Route grounded structural corrections through:

```python
modify_molecule(mol_json={"smiles":"<recognized SMILES>"},
    operation="set_smiles", new_smiles="<visually grounded corrected SMILES>",
    description="A: source shows OH, recognized as methyl; preserve other connectivity")
```

Review the MCS status, formula, and stereo changes before redrawing. Null MCS or empty change lists with partial/not-completed status do not establish no change. Record minimal normalization of invalid R tokens separately from raw OCSR output. Redo affected structures only, but inspect the complete preview after layout changes. Keep unreadable source details unresolved instead of filling them from reaction expectations.

## 5. Assemble conditions and deliver

Preserve condition wording and order, structure/state labels, and yield scope. For example, "70% (3 steps)" covers all three steps. Preserve relative descriptions for shared wavy-bond structures with a/b labels; do not invent absolute stereoisomers. Use native rich text for subscripts and superscripts and follow source positions for structures, arrows, and labels.

Inspect the whole native figure for conditions, yields, labels, arrows, abbreviations, crossings, and clipping. Deliver **editable CDXML, preview, then necessary comparisons or unresolved issues**. Retain raw responses, corrections, and hashes in the working directory.

Check corrected structures against final CDXML readback, inspect visual fidelity, and disclose layout differences. For bridges, charge symbols or stereo-sensitive edits, use [saved-file validation](figure-validation.md). Claim strict 1:1 reproduction only when demonstrated. Pixel similarity and white-background area do not establish chemical correctness.

## Common issues

| Issue | Approach |
|---|---|
| Folded chains or bridged crossings | Trace each bond; crossing lines alone create neither an atom nor a ring closure. |
| Ph/Pb, OH/methyl, OMe/OH, CN, X/R | Check these first using full-image definitions, then inspect formula differences. |
| R/X abbreviations | Preserve displayed text with real atom subgraphs and attachment points; text cannot replace connectivity. |
| Wavy bonds, alpha/beta, R/S | Record each separately. Unspecified does not mean racemic; a changed CIP label need not mean spatial inversion. |
| Coordinate/wedge changes | Recompute wedges and read back final coordinates; verify the narrow end and attached atom. |
| Missing bridged stereo or reader disagreement | Compare RDKit CDXML readback and direct ChemScript SMILES from the same native file. MOL intermediates can lose stereo and are not the sole judge. Map atoms explicitly. After upgrades, retest one disputed structure before batch processing. Never flip wedges merely to force agreement; unresolved differences prevent full acceptance. |
| Reversed or wrapped abbreviations | Set node/text alignment and font runs explicitly; allow sufficient page width. |
| Incorrect bridge depth | Verify front/back bonds before changing bold bonds or occlusion. Use native front/back crossing edits first; inspect every intersection rather than covering mistakes with extra lines. |
| Individual exports wrap | Check page width and coordinates instead of editing correct SMILES. |

## Runnable examples

[Two complete publication schemes](../assets/paper-reconstructions/README.md) include native components, layout manifests, and an offline assembly script. Run `python <skill>/assets/paper-reconstructions/rebuild.py <new-output-directory>` and inspect native previews. Examples cover shared OR groups, abbreviations, folded chains, bridge occlusion, and electron arrows. Complete layouts do not establish stereo acceptance; reader disagreements remain. Preserve and report inconsistencies between source expanded chains and abbreviation definitions instead of making adjacent steps artificially consistent.

The [drawing example](../assets/paper-replica/example/CASE.md) includes a manifest, actual CDXML/native preview, and offline replay covering arrows, electron curves, rich text, chirality, and enhanced stereo groups:

```powershell
& <MCP-Python> <skill>/assets/paper-replica/example/replay.py <absolute-new-output-directory>
```

Render `figure.cdxml` natively and inspect a comparison. This example does not call DECIMER. For recognition, use images the user is authorized to provide and follow the workflow above. See the [drawing reference](publication-figures.md) for supported fields.

## Validation scope

`document_chemistry_validation` checks the complete final molecular inventory, including multiplicity, and records SHA-256. `scope=rdkit_readback_consistency` establishes RDKit consistency only. Cross-reader stereo disagreement prevents full stereochemical acceptance. When native ChemDraw is unavailable, deliver editable files marked as pending native preview; other renderers cannot replace native acceptance.

## Comparison modes and provenance

The `compare` helper defaults to a visual display: panels may be independently resized and are not a strict pixel comparison. Candidates are not called native without `--native-receipt` pointing to the saved `render_cdxml_files` result with matching path/hash and renderer metadata. The helper publishes image and receipt together.

Use `--mode aligned --offset DX DY` for explicit integer translation and padding at the original scale. Candidate pixels must fit the reference canvas; clipping is rejected. This mode records exact equality, normalized MAE and ink IoU. `--region X1 Y1 X2 Y2 --height N` produces an explicitly marked local display, not full-image pixel acceptance. Keep the complete comparison as well as details. See [lessons](lessons.md) for known mistakes.

For perspective-bond disagreement, abbreviation hydrogen loss, and version-specific stereo handling, use [stereo reconstruction diagnosis](stereo-reconstruction.md). Test a difficult fragment before propagating templates; revalidate the exact final saved file.
