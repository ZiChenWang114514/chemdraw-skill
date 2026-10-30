# Rendering And Layout

## When To Load

Load for new reaction rendering, existing CDXML cleanup, alignment, multi-scheme merge, or deterministic composition beyond the MCP decision layer.

## Preferred Entry Points

- New grounded scheme: tool `render_scheme`.
- Existing layout cleanup: tool `clean_scheme_layout`; Python `layout.reaction_cleanup.run_cleanup`. Every step is laid out, with "+" signs and compound numbers kept with their structures; a scheme drawn one step per row gets a common left edge and even row gaps. A step that reuses a species of an earlier step (A -> B -> C on one row) is left as drawn and listed in `skipped_steps`.
- Multi-file merge: tool `merge_reaction_schemes`; Python `layout.scheme_merger` parse, detect, execute workflow.
- Full normalization/polish: tool `polish_reaction_scheme`; Python `scheme_polisher_v2.run_pipeline`. Conditions are tidied and merged for every step.
- Parsed reaction JSON: `render.auto_layout.auto_layout_to_cdxml` or `render.scheme_maker.build_scheme`.
- YAML/compact input: `render.parser.parse_yaml` or `render.compact_parser.parse_compact`, then `render.renderer.render_to_file`.

## Inputs And Outputs

Use grounded structures or parser-produced reaction JSON. Cleanup and merge accept CDXML and write new CDXML. Always native-render final output. Merge modes are auto, parallel, sequential, and adjacent. Sequential mode verifies every adjacent canonical product/reactant link; auto mode also rejects a non-linear, branching, convergent, or gap-containing sequential plan. `force_sequential=true` is a reviewed override. Equivalent labels apply to auto/parallel modes.

## Failure Modes

Reject missing inputs, unsupported modes, accidental overwrite, unlinked sequential steps, disconnected schemes when adjacency is disallowed, and native-render failures. Cleanup, merge, polish, and preview files are staged together so a failed preview leaves no final CDXML. Alignment may fail when products share no usable MCS; preserve the unaligned output only as diagnostic evidence.

## Supporting APIs

- `layout.alignment`: product-reference, RDKit/MCS, Kabsch, and optional RXNMapper alignment.
- `render.scheme_yaml_writer`: inspectable intermediate YAML and merged-plan construction.
- `cdxml_utils`: safe parse/write, bounding boxes, centroids, arrows, IDs, and text bounds.
- `coord_normalizer`: ACS bond length and trusted parsed coordinate normalization.
- `text_formatting`: subscript and stereochemical text runs.

## Do Not Use Directly

Do not expose raw atom/bond builders as chemistry truth. Do not call individual geometry mutation functions for routine cleanup. Do not use text formatting to reinterpret unknown chemical abbreviations.
