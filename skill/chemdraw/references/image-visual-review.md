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

`<corrected>` is the recognized SMILES with only the change you can point to in the image (here one methyl replaced by OH); do not write a new SMILES from memory. Prefer an operation that states the change (`name_surgery`, `smarts`) when one fits. When the compound has a name or number in the source text, `resolve_name` gives an independent structure to compare with. Read the returned diff status: the diff must show exactly the intended change, and a null MCS or `partial`/`not_completed` does not mean "no change".

### Atom-index & stereochemical surgery with `rdkit_workbench`

When OCSR returns a structure that needs targeted atom/bond edits, wedge/dash inspection, or 2D orientation alignment to match the source crop, use `rdkit_workbench`:

- **`edit_structure`:** apply deterministic graph edits by zero-based atom index (`set_atom`, `set_bond`, `add_group`, `remove_atoms`, `set_ez` for $E/Z$ alkene geometry) with full valence and sanitisation checks.
- **`read_wedges`:** read back 2D wedge/dash/wavy bond directions (`BEGINWEDGE`, `BEGINDASH`, `UNKNOWN`), CIP ($R$/$S$, $E$/$Z$) labels, and narrow-end / wide-end atom indices from a CDXML or MOL file.
- **`depict_like`:** align a molecule onto a reference template (or search 16 candidate rotation/flip orientations) to match the source drawing's ring and substituent orientation while recomputing stereo wedges consistently.
- **`enumerate_markush`:** expand R-group tables and variable attachment points into concrete member structures.
- **`visual_checkpoints` & `diagnose_smiles_error`:** generate structured visual inspection checklists (ring sizes, hetero-labels, wedge narrow ends, charges) and pinpoint syntax/valence errors in broken OCSR SMILES strings.

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

## Many structures, subagents and small contexts

The main agent reads the whole source and keeps arrows, conditions, numbering and shared definitions; complete structures, salts and shared fragments stay together in one crop.

1. Crop with `image_review_workspace.py prepare` (step 2). Look at each crop against the full image: automatic cropping is not segmentation.
2. Optional packets: `cdx.py py <skill>/scripts/reconstruction_packets.py CROPS/manifest.json NEW_PACKETS_DIR [--config CONFIG_JSON]` gives each structure its crop, coordinate map, the context it needs and its own output folder, and proposes batches in `dispatch.json` (it launches nothing). Config keys: `parallel` (true only when the user asked for parallel work), `max_subagents`, `structures_per_task`, `max_ocsr_requests`, `max_native_workers`, `max_structure_retries`, `host_capacity`, `supports_subagents`, and `context` (region ID to only the definitions and style that structure needs).
3. Per crop: recognize, correct connectivity and charges, check stereobonds and crossings locally (a broken line at a crossing may be an occluded single bond), render natively and look. Return the output path to the main agent, not long SMILES, XML or logs; anything ambiguous goes back to the main agent.
4. The main agent checks every component and the whole figure and assembles them with the figure operations. If native object relationships cannot be kept, deliver separate components and say so.

When authorized to run a queue, track each structure as pending, working, submitted, needs_review, failed or accepted. A subagent writes only into its own folder, and a late or duplicate result never replaces an accepted one. After an interruption rerun only missing or changed regions. Limit OCSR requests separately from agent count and follow the [DECIMER retry rule](decimer-api.md#diagnosing-failed-requests); native work is serialized by the ChemDraw lock however many agents run. An agent without vision cannot judge image agreement, and a model is not upgraded after a failure. Reuse a cached recognition only when the crop, scale and parameters are unchanged; a changed shared definition invalidates the structures that use it.

## Repeated structures and local repairs

For a figure with repeated structures or many local corrections, a controller keeps linked records, caches recognition candidates, works out which fragments a change affects and gates delivery on an explicit review. It does not infer unknown chemistry. Prefer supplied CDXML/CDX or native Office objects (convert CDX first with `convert_cdx_cdxml`) and probe the hard cases early (bridged stereo, N-H/O-H abbreviations, charged nitrogen) before propagating a template. Embed X-ray panels as images.

```bash
cdx.py py -m cdxml_toolkit.mcp_runtime.reconstruction --arguments operation.json
```

Each JSON object has `operation` and the arguments below. `result_path` (a new file for the full record) is **required** for `capture`, `plan`, `target`, `attempt`, `benchmark`, `map_reuse` and `finalize`, optional for the rest; existing files are never overwritten. Example: `{"operation": "capture", "cdxml": "<abs>/reviewed.cdxml", "source_image": "<abs>/source.png", "transform": {"scale": [2, 2], "offset": [0, 0]}, "context": {"Ar": "PMP"}, "result_path": "<abs>/snapshot-1.json"}`; `transform` maps native coordinates to source pixels (measured, or omitted).

| Operation | Arguments | Behavior |
| --- | --- | --- |
| `capture` | `cdxml`, `source_image`, optional `transform`, `context`, `versions` | Snapshot of native objects, coordinates and molecule inventory. |
| `compile` | `template`, `output_path`, `edits` | Replay a native tree through the figure composer; empty edits copy the bytes. |
| `plan` | `before`, `after` snapshots | List the objects and fragments a change affects. Source, context or transform changes affect everything. |
| `local` | `snapshot`, `plan`, `output_dir`; optional `native`, `cross_reader` (default true) | Check only the scheduled fragments. |
| `map_reuse` | `reference`, `candidate` CDXML | Require a unique full graph mapping and show stereo differences. Does not copy stereo or coordinates. |
| `cache` | `action` store/load, `root`, `spec`, optional `artifact`, `kind` | Store or load recognition/intermediate files keyed by their inputs. |
| `attempt` | `previous` (or null), `issue_id`, `passed`, `difference`, `artifact_sha256` | Repair history; after two failures the issue becomes needs_review. |
| `overlay` | `source`, `candidate`, `output_dir`, integer `offset` | Same-scale ink overlay with MAE and IoU. Never resizes. |
| `target` | `molecules` (label/smiles), `provenance`, `reviewed: true` | Freeze the reviewed target structures. |
| `verify_variants` | `source_cdxml`, `compatible_cdxml`, `target_record`, `output_dir` | Native save, readback and preview of both variants against the target. |
| `finalize` | `package_dir`, `review_record` | Emit the delivery manifest after review. |
| `benchmark` | `baseline`, `candidate` | Compare timings for the same fixture and versions. |

A cache `spec` contains `source_image`, `crop`, `definitions`, `parameters`, `versions` and `transform`; any change is a miss, and a hit is still a candidate that needs review. Font and run styling need only visual review; changes to atom coordinates, bond display or order, hydrogens, charges or label meaning schedule chemical checks, and a shared-definition text change re-checks the whole inventory. Apply chemical corrections with `modify_molecule` or `rdkit_workbench`, then `capture` again. Nothing flips wedges or fills CIP labels automatically.

**Two variants.** Keep the source-oriented drawing. A compatibility variant may change only stereobond depiction against the same target, with the visual changes listed. `verify_variants` requires the source variant's ChemScript reading to match the target (RDKit disagreement is reported) and the compatible variant to match in both readers. Then look at both previews and the overlays against the source, including compound numbers, conditions and yields. `review_record` holds `reviewer`, `verification_sha256`, `source_image`, `source_sha256` and `variants.source` / `variants.compatible`, each with `graph_checked`, `stereo_checked`, `text_checked`, `whole_figure_checked`, `preview_sha256`, `status` (`reviewed` or `reviewed_with_differences`) and `differences`; fill the booleans only after actually looking, and take the hashes from the `verify_variants` result. Failed attempts keep their folders; retry into a new folder, and never run several native workers to get past the lock.

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
- Open-access paper replicas, each a `brief.json` for `cdx.py draw` with the journal's house style, the reference crop (CC BY) and the ChemDraw render, replayed offline with `cdx.py py <skill>/assets/paper-replica/<case>/replay.py NEW_DIR`: [JACS Au, Pd-catalysed amination](../assets/paper-replica/jacs-au-pd-amination/CASE.md) (`lipshutz_group`), [Chem. Sci., DPDTC formation](../assets/paper-replica/chem-sci-amide-coupling/CASE.md) (`rsc_journals`), [Nat. Commun., electroreductive arylation](../assets/paper-replica/nat-commun-ni-ereductive/CASE.md) (`nature_portfolio`). Each CASE.md lists the OCSR agreement per structure and what still differs from the paper's artwork.

## Comparison modes

`compare` defaults to a side-by-side visual panel (panels may be resized). `--mode aligned --offset DX DY` compares at the original scale and reports MAE and ink IoU; `--region X1 Y1 X2 Y2 --height N` zooms into one area. Pixel scores help find differences; they do not decide chemistry. See [lessons](lessons.md) for known mistakes.
