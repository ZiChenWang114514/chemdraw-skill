# Tool Decisions And Failure Rules

All tools run through `cdx.py call` (see [agent integration](agent-integration.md)); the rules are the same whichever route invokes the worker.

Exact signatures are generated in [mcp-signatures.md](mcp-signatures.md). This file is the authority for behavior and selection only.

## Selection

- Prefer official molecule/reaction tools for ordinary drawing and parsing.
- Prefer extended tools for complete layout, merge, polish, batch render, Office, RDF, and experiment workflows.
- Use the comparison tools for ChemScript-grounded identity plus RDKit similarity. Use the SDK tools only after inspecting the relevant public member.
- Use `chemdraw_object` to read or edit CDXML elements the drawing tools do not cover, and `chemdraw_inventory` to ask which ChemDraw interfaces (ChemScript members, COM objects, CDXML elements, menu commands) exist and which tier covers them. Neither starts ChemDraw.
- Use the remote DECIMER tool (`cdx.py decimer`) by default for task images under the upload rule in SKILL.md.
- New extended tools return `{ok, outputs, warnings, metadata}`. Existing official tools retain their upstream fields and add `metadata.artifacts`, listing the written files, after a successful write.

## Failures

- `tool_timeout`: the isolated worker exceeded `CHEMDRAW_MCP_WORKER_TIMEOUT_SECONDS`; inspect input size and runtime health before retrying.
- `worker_launch_failed`: Python or the worker script could not start; run `cdx.py doctor`.
- `tool_cancelled`: the request was cancelled and the worker process tree was terminated.
- `resource_busy`: another worker held the ChemDraw COM mutex for the request's timeout. Retry after the active native operation finishes; do not start parallel GUI automation.
- `worker_output_limit`: stdout or stderr exceeded `CHEMDRAW_MCP_WORKER_OUTPUT_BYTES`; inspect the local diagnostic log rather than raising the limit blindly.
- `worker_protocol_error`: the isolated worker did not return a valid JSON envelope. Treat this as a runtime defect, not a chemistry result.
- `tool_execution_failed`: a tool raised an input, chemistry, COM, parser, or write error. The result carries a stable error id; details remain in the worker log (`cdx.py doctor --paths`).
- ChemScript SDK request failure: reduce the program to the failing step and inspect the exact member first. File access, existing-file replacement, and native interop are independent explicit options.
- Existing output: every writing tool refuses explicit overwrite. Default destinations use semantic suffixes and increment on conflict. Outputs are staged, validated, and published without clobbering; multi-file failures roll back the whole result. The official `embed_cdxml_in_office` name is retained, but its safety override rejects existing Office targets because the upstream builder cannot preserve their content.
- Native render failure: keep the CDXML for diagnosis but do not claim final validation.
- Multiple OCSR candidates: return all candidates and warnings; do not assume the first item is correct.

## Compatibility

The 15 upstream tool names and `extract_structures_via_decimer_api` remain registered. Official parameters and return types are preserved; the overridden Office tool publishes its stricter creation-only contract in its tool metadata. The low-level API keeps a no-upload default for direct callers; `cdx.py decimer` passes `confirm_upload=true` unless `--preflight` is given. Extended, comparison, and ChemScript SDK tools are additive. `reaction_image_to_cdxml` is documented but not registered because candidate ordering and reaction-role mapping are not reliably supported.
