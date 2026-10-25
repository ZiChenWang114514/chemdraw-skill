# Efficient reconstruction

For figures with many structures, or when work is split across subagents. Read this guide and the needed signatures only. For candidate caching and repeated local repairs, see [incremental reconstruction](incremental-reconstruction.md).

## Procedure

1. The main agent reads the whole source. Keep complete structures, salts and shared fragments together. Arrows, conditions, numbering and shared definitions stay with the main agent.
2. Crop: `cdx.py py <skill>/scripts/image_review_workspace.py prepare IMAGE REGIONS_JSON NEW_DIR`. Look at each crop against the full image; automatic cropping is not segmentation.
3. Optional packets: `cdx.py py <skill>/scripts/reconstruction_packets.py CROPS/manifest.json NEW_PACKETS_DIR [--config CONFIG_JSON]`. Each structure gets its crop, coordinate map, the context it needs and its own output folder. Check `dispatch.json` before running.
4. Per crop: recognize, correct connectivity and charges, check stereobonds and crossings locally. A broken line at a crossing may be an occluded single bond.
5. Render the result natively and look at it. Return the output path to the main agent, not long SMILES, XML or logs. Anything ambiguous goes back to the main agent.
6. The main agent checks all components and the complete figure and assembles them with the existing figure operations. If native object relationships cannot be kept, deliver separate components and say so.

## Large results

```text
cdx.py call modify_molecule --args arguments.json --out result.json
```

Works for every tool. The full result goes to the file and only a short summary is printed (about 6 KB at most). Read the errors and warnings it points to before continuing.

## Dispatch configuration

```json
{
  "parallel": false,
  "max_subagents": 4,
  "structures_per_task": 1,
  "max_ocsr_requests": 2,
  "max_native_workers": 1,
  "max_structure_retries": 1,
  "host_capacity": 1,
  "supports_subagents": false,
  "context": {}
}
```

`context` maps a region ID to only the definitions and style it needs. Set `parallel` true only when the user asked for parallel work. The helper proposes batches; it launches nothing.

When authorized, the main agent runs a bounded queue and tracks each structure as pending, working, submitted, needs_review, failed or accepted. A subagent writes only into its own folder. A late or duplicate result never replaces an accepted one. After an interruption, rerun only missing or changed regions.

Limit OCSR requests separately from agent count and follow the [DECIMER retry rule](decimer-api.md#diagnosing-failed-requests). Native work is serialized by the ChemDraw mutex no matter how many agents run.

## Acceptance

Keep native, chemical and visual acceptance separate. An agent without vision cannot judge image agreement. Do not upgrade a model after a failure. Reuse a cached recognition only if the crop, scale and parameters are unchanged; a changed shared definition invalidates the structures that use it.
