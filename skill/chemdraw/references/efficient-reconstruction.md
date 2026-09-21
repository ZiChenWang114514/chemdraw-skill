# Efficient reconstruction

Use the existing toolkit environment. Read this guide and the needed tool signature; do not load the entire catalog. These packet helpers save evidence and propose batches; they do not implement worker scheduling or a task lease database. For implemented candidate caching, change-based fragment checks, native-tree replay and dual delivery, use [incremental reconstruction](incremental-reconstruction.md). It does not add a general native component importer or launch agents.

## Short procedure

1. Main agent inspects the whole source. Keep complete structures, salts and shared fragments together. Own reaction arrows, conditions, numbering and common definitions centrally.
2. Use `image_review_workspace.py prepare IMAGE REGIONS_JSON NEW_DIRECTORY` from the visual-review guide. Inspect each crop against the full image. Overlapping regions require review; automatic cropping is not correct segmentation by definition.
3. Generate packets with `reconstruction_packets.py CROPS/manifest.json NEW_PACKETS_DIRECTORY [--config CONFIG_JSON]`. Each structure receives its crop hash, source hash, coordinate map, relevant context and isolated output directory. Check `dispatch.json` before execution.
4. For each crop, recognize a candidate, correct connectivity and charges, and compare stereobonds and crossings locally. A broken line at a crossing may be an occluded single bond. A parsed SMILES is not acceptance.
5. Native-render the editable result; inspect labels and pixels. Record issues and evidence in that structure's attempt directory. Submit a path and hash, not long SMILES, XML or logs. Any ambiguity returns to the main agent.
6. Main agent checks all components and the complete figure. Use supported existing figure/template operations. Existing molecule-file drawing may reconstruct through RDKit; it is not a lossless native import. If native object relationships cannot be preserved, retain separate components and report assembly unresolved.

## Compact tool output

Write the arguments for one existing tool to a JSON object file, using its generated signature. Then run:

```text
python scripts/compact_tool.py modify_molecule --arguments arguments.json --output new-evidence.json
```

The allowlist also includes `extract_structures_via_decimer_api`, `compose_chemical_figure`, `render_cdxml_files` and `get_toolkit_capabilities`. This calls the existing isolated worker without changing its interface or native lock. Full output is saved before a short summary is printed. Inspect referenced errors and warnings before further work; `produced` never means chemically accepted. Existing evidence files are refused. If publication fails after a tool ran, inspect that tool's artifacts before retrying.

DECIMER upload/offline rules are unchanged. No response is silently truncated on disk. Normally the summary is below 4 KiB; path length contributes to its size. This helper does not reduce schemas already exposed by an MCP host. Do not equate characters with tokens.

## Optional dispatch proposal

Configuration fields and defaults:

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

Set `context` to a map from region ID to only its necessary definitions and style requirements. Obtain host capacity from the actual host. Only set parallel true after the user requests it. No subagent support means serial fallback; zero capacity on an enabled host means blocked. The helper generates proposed batches but launches nothing and enforces no remote concurrency limit.

When authorized, the main agent dispatches a bounded queue, replenishing only after completion. Use a fresh short packet per task, without full conversation history. Keep each structure's result independent even in a grouped batch. The main agent alone maintains status: pending, working, submitted, needs_review, failed, accepted. A worker writes only its attempt directory. Check attempt ID, input hashes and artifact hashes before accepting a returned path. Late or duplicate results cannot replace an accepted attempt; preserve them separately. After interruption inspect records and rerun only missing or changed regions. These are caller responsibilities, not automatic recovery guarantees.

The caller limits OCSR requests separately from agent count, retries a transient network failure at most once while honoring server delay, and returns persistent or semantic failures to the main agent. Native work always uses the existing shared lock with one native worker. Preserve the existing HTTP host/port configuration (normally `127.0.0.1:8029`); different ports do not bypass that lock. Do not start a service per worker.

## Acceptance and measurement

Keep native, chemical and visual acceptance separate. A model without vision can run deterministic steps but cannot certify image agreement. Do not auto-upgrade a model on failure. Cache reuse is manual: verify source/crop hashes, transform, parameters, tool version and correction rules; never reuse a final correctness verdict. Changed shared definitions invalidate affected results even when pixels match.

When requested, record wall time, recognition time, native queue time and host token counters with their cutoff. Separate cached input, uncached input and output; unavailable counters are unknown. Compare the same model and fixture before claiming savings or speedups. Packet generation and tests establish engineering behavior only, not low-cost model accuracy or parallel performance. The incremental controller can enforce cache dependencies and a two-failure repair bound; final correctness verdicts are never cache hits.
