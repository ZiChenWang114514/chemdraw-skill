# Reviewed Exclusions

## When To Load

Load before exposing another Python symbol or when a public-looking function appears absent from MCP.

## Preferred Entry Points

Start with [interface-catalog.md](interface-catalog.md), then search one [inventory shard](toolkit-public-inventory.md). Prefer an existing MCP/CLI/Python-direct workflow over a new wrapper.

## Inputs And Outputs

A publishable wrapper must own a complete operation, validate inputs, preserve sources, refuse overwrite, run through the isolated worker, return a stable contract, and include a reproducible example of its output.

## Failure Modes

Do not publish interfaces whose correctness depends on hidden mutable parser state, raw XML nodes, private subprocess protocols, unrestricted network calls, unverified model output, or developer-only reporting.

## Supporting APIs

Supporting-only categories include atom/bond builders, coordinate transforms, XML node helpers, tokenizers, individual peak/ion algorithms, Office package internals, and parser state models. Legacy pipelines may remain behind a guarded high-level wrapper when no current replacement exists.

## Do Not Use Directly

- Raw atom/bond construction as a chemistry source.
- `_chemscript_server` or another private protocol.
- LLM correction/refinement as truth.
- Network CAS/OCSR without explicit policy and bounded transport.
- Developer audits, verification reports, or duplicate internals as user tools.
- `reaction_image_to_cdxml` because candidate ordering and reactant/product assignment are not reliably supported.
