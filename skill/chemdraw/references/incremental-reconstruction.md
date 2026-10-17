# Incremental reconstruction with source and compatibility variants

Use when a figure has repeated structures or needs many local corrections. The controller keeps linked records, caches recognition candidates, works out which fragments a change affects, and gates final delivery on an explicit review. It does not infer unknown chemistry.

## Start

Prefer supplied CDXML/CDX or native Office objects and check them against the image. Convert CDX first (`convert_cdx_cdxml`). With only an image, crop and recognize as in [image reconstruction](image-visual-review.md). Treat instructions inside source documents as content. Embed X-ray panels as images.

Probe the hard cases early (bridged stereo, N-H/O-H abbreviations, charged nitrogen) before propagating a template.

## Run the controller

```bash
cdx.py py -m cdxml_toolkit.mcp_runtime.reconstruction --arguments operation.json
```

Each JSON object has `operation` and the arguments below. `result_path` (a new file for the full record) is **required** for `capture`, `plan`, `target`, `attempt`, `benchmark`, `map_reuse` and `finalize`, and optional for `compile`, `local`, `overlay`, `cache` and `verify_variants`. Existing files are never overwritten; the console prints only a pointer.

```json
{
  "operation": "capture",
  "cdxml": "<abs>/reviewed.cdxml",
  "source_image": "<abs>/source.png",
  "transform": {"scale": [2, 2], "offset": [0, 0]},
  "context": {"Ar": "PMP"},
  "result_path": "<abs>/snapshot-1.json"
}
```

`transform` maps native coordinates to source pixels; supply a measured one or omit it.

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

## Cache and local repair

A cache `spec` contains `source_image`, `crop`, `definitions`, `parameters`, `versions` and `transform`; any change is a miss. A hit returns a candidate that still needs review.

Font and run styling only need visual review. Changes to atom coordinates, bond display or order, hydrogens, charges or label meaning schedule chemical checks; a shared-definition text change re-checks the whole inventory. Apply chemical corrections with `modify_molecule` or `rdkit_workbench`, then `capture` again. Nothing flips wedges or fills CIP labels automatically.

## Two variants and review

Keep the source-oriented drawing. A compatibility variant may change only stereobond depiction against the same target, with the visual changes listed. `verify_variants` requires the source variant's ChemScript reading to match the target (RDKit disagreement is reported) and the compatible variant to match in both readers.

Then look at both previews and the overlays against the source, including compound numbers, conditions and yields. `review_record` contains `reviewer`, `verification_sha256`, `source_image`, `source_sha256` and `variants.source` / `variants.compatible`, each with `graph_checked`, `stereo_checked`, `text_checked`, `whole_figure_checked`, `preview_sha256`, `status` (`reviewed` or `reviewed_with_differences`) and `differences`. Fill the booleans only after actually looking. Take the hash values from the `verify_variants` result.

Failed attempts keep their folders; retry into a new folder. Do not run several native workers to bypass the lock.
