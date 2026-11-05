# Tool Decisions And Failure Rules

All tools run through `cdx.py call` (see [agent integration](agent-integration.md)); the rules are the same whichever route invokes the worker.

Exact signatures are generated in [mcp-signatures.md](mcp-signatures.md). This file is the authority for behavior and selection only.

## Selection

- Prefer official molecule/reaction tools for ordinary drawing and parsing.
- Prefer extended tools for complete layout, merge, polish, batch render, Office, RDF, and experiment workflows.
- Use the comparison tools for ChemScript-grounded identity plus RDKit similarity. Use the SDK tools only after inspecting the relevant public member.
- Use `chemdraw_object` to read or edit CDXML elements the drawing tools do not cover, and `chemdraw_inventory` to ask which ChemDraw interfaces (ChemScript members, COM objects, CDXML elements, menu commands) exist and which tier covers them. Neither starts ChemDraw. Use `chemdraw_com_call` (Windows) to run a checked program over ChemDraw's own COM objects when no dedicated tool covers the operation; see the workflow router.
- Use the remote DECIMER tool (`cdx.py decimer`) by default for task images under the upload rule in SKILL.md.
- New extended tools return `{ok, outputs, warnings, metadata}`. Existing official tools retain their upstream fields and add `metadata.artifacts`, listing the written files, after a successful write.

## Overlapping tools: prefer

When two tools can do the job, take the first:

- Reading a structure image: `recognize_structure` (`cdx.py ocsr`, or `cdx.py decimer` for the remote engine) over `extract_structures_via_decimer_api` (the raw upload call) and `extract_structures_from_image` (upstream DECIMER segmentation and OCR; use it only to look for structures in an uncropped image). A PDF or a whole page: `extract_structures_from_document`.
- Rendering CDXML to PNG: `render_cdxml_files` (`cdx.py render`; one ChemDraw session for many files, SVG too) over `render_to_png` (one file).
- Drawing a figure: `draw_figure` for a reaction, route, scope panel or mechanism from a brief; `publication_figure` for a substrate-scope or SAR project kept in a folder; `compose_chemical_figure` only for exact coordinates you supply; `render_scheme` for a compact text scheme or a row-width setting.
- Comparing molecules: `compare_molecules` for one pair, `batch_compare_molecules` for many pairs.
- Putting drawings into Office: `embed_cdxml_in_office` for one new file with one object, `batch_embed_cdxml_in_office` for several objects or pages.
- Reading a reaction drawing: `parse_scheme` for a CDXML scheme as ordered steps, `parse_reaction` for species, roles and SMILES (also from ELN files), `summarize_reaction` for a short view of an existing reaction JSON, `route_summary` for the overall yield and PMI of a route.

## Failures

- `tool_timeout`: the isolated worker exceeded `CHEMDRAW_MCP_WORKER_TIMEOUT_SECONDS`; inspect input size and runtime health before retrying.
- `worker_launch_failed`: Python or the worker script could not start; run `cdx.py doctor`.
- `tool_cancelled`: the request was cancelled and the worker process tree was terminated.
- `resource_busy`: another worker held the ChemDraw lock for the request's timeout. Retry after the active native operation finishes; do not start parallel GUI automation.
- `worker_output_limit`: stdout or stderr exceeded `CHEMDRAW_MCP_WORKER_OUTPUT_BYTES`; inspect the local diagnostic log rather than raising the limit blindly.
- `worker_protocol_error`: the isolated worker did not return a valid JSON envelope. Treat this as a runtime defect, not a chemistry result.
- `worker_out_of_memory`: the worker died while allocating memory, usually because other programs hold it. Retry once memory is free; do not change the input.
- `worker_crashed`: the worker exited before answering; the message carries the end of its error output. Run `cdx.py doctor` before retrying.
- `tool_execution_failed`: a tool raised an input, chemistry, COM, parser, or write error. The result carries a stable error id; details remain in the worker log (`cdx.py doctor --paths`).
- ChemScript SDK request failure: reduce the program to the failing step and inspect the exact member first. File access, existing-file replacement, and native interop are independent explicit options.
- Existing output: a writing tool refuses an existing output unless it has an explicit replace option (`cdx.py render --replace`, `chemdraw_com_call` with `allow_overwrite`, `execute_chemscript_sdk` with `allow_overwrite`); nothing replaces a file by default. Default destinations use semantic suffixes and increment on conflict. Outputs are staged, validated, and published without clobbering; multi-file failures roll back the whole result. The official `embed_cdxml_in_office` name is retained, but its safety override rejects existing Office targets because the upstream builder cannot preserve their content.
- Native render failure: keep the CDXML for diagnosis but do not claim final validation.
- Multiple OCSR candidates: return all candidates and warnings; do not assume the first item is correct.

## Compatibility

The 15 upstream tool names and `extract_structures_via_decimer_api` remain registered. Official parameters and return types are preserved; the overridden Office tool publishes its stricter creation-only contract in its tool metadata. The low-level API keeps a no-upload default for direct callers; `cdx.py decimer` passes `confirm_upload=true` unless `--preflight` is given. Extended, comparison, and ChemScript SDK tools are additive. `reaction_image_to_cdxml` is documented but not registered because candidate ordering and reaction-role mapping are not reliably supported.
