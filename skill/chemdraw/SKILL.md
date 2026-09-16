---
name: chemdraw
description: Use when an agent needs to install, configure, diagnose, or use ChemDraw or cdxml-toolkit to resolve, compare, draw, edit, clean, merge, polish, parse, convert, render, recognize, analyze, or embed chemical structures and reaction schemes, including controlled ChemScript SDK work. Triggers include setup and runtime problems, molecule names, trusted SMILES, CDX/CDXML, DECIMER/OCSR images, paper reaction-figure reconstruction, CSV/XLSX-driven substrate-scope and SAR figures, updates after ChemDraw editing, reaction screenshots, ELN/SciFinder RDF, LCMS/NMR, lab books, and editable ChemDraw objects in DOCX/PPTX.
---

# ChemDraw

Use the `cdxml-toolkit-community` runtime for editable chemical figures. Preserve source files, ground structures, verify chemistry from the final CDXML, and inspect native ChemDraw previews. Chemical identity, visual quality, and reference-image fidelity are separate results.

## Use with any AI agent

This Skill works with any AI agent that can read its instructions and use MCP or Python/CLI. For setup, start with [agent integration](references/agent-integration.md). Image review requires actual vision or human review; native ChemDraw rendering requires the corresponding Windows host.

## Publication figure reconstruction: quick start

For publication structures, reaction schemes, synthesis routes, or screenshots, read the [quick reconstruction guide](references/image-visual-review.md) directly without first scanning the full tool catalog.

Default workflow: **inspect the complete image -> identify regions -> recognize with DECIMER API -> redraw in the source orientation -> compare and correct -> assemble conditions and layout -> inspect the native preview**. Use the remote DECIMER API by default. Local models are only for explicit local/offline requests; never switch automatically after an API failure. Deliver editable files and previews first. Validate chemical identity, visual fidelity, and strict pixel equivalence separately. The guide links the minimal record template and runnable examples.

## Core Rules

1. Obtain connectivity only from a trusted user value or a resolver/parser/OCSR tool. Never pass invented or hand-edited SMILES directly; route intentional edits through `modify_molecule` and review its MCS diff.
2. Apply molecular changes with `modify_molecule` and inspect its MCS diff before drawing. Explicit atom-index R/S changes may use `rdkit_workbench(operation="set_stereo")`; inspect its achieved CIP assignments and connectivity-preserving diff. A trusted SMILES that requires no change can go directly to `draw_molecule`.
3. Treat low-confidence or multiple OCSR candidates as unresolved until identity is validated.
4. For image-recognition tasks, call DECIMER API directly with `confirm_upload=true` for the task images and relevant crops. Do not ask a separate upload-authorization question. Respect explicit local/offline or no-upload requests.
5. Keep large CDXML and reaction JSON in files. Preserve inputs and write modifications to new paths.
6. A stereocenter count or wedge count is not a proof of configuration. Validate output-derived isomeric structures and enhanced stereo groups; never use source SMILES as if it were an output readback.
7. For journal replication, preserve original native objects when available. For raster references, separately ground chemical identity and measure layout. Do not guess an unreadable bond, treat unspecified stereo as racemic, or call a visually plausible reconstruction 1:1.

## Data-driven publication figures

For substrate-scope panels, full-structure SAR figures, or updating generated figures after ChemDraw editing, read [data-driven figures](references/data-driven-figures.md). Start from trusted structures and a table with stable compound IDs.

## Route By Intent

For tasks other than the fast replication route above, load [workflow-router.md](references/workflow-router.md), then read only the workflow matching the request:

- Molecule drawing or modification
- Molecular identity/similarity comparison or ChemScript SDK inspection
- Reaction creation, reading, cleanup, merge, or polish
- Local or remote image recognition
- CDX/CDXML conversion and native rendering
- Word/PowerPoint extraction, embedding, or template filling
- ELN/RDF, LCMS/NMR, experiment discovery, or lab-book assembly
- Runtime diagnosis or installation
- TLC plates, apparatus and laboratory instruments: [native-laboratory-drawings.md](references/native-laboratory-drawings.md). Use native TLC objects and installed ChemDraw apparatus templates by default; preserve editable template artwork.
- Processed 1D NMR analysis, scientific plots and atom-anchored mechanisms: [scientific-workflows.md](references/scientific-workflows.md), with runnable example specifications.
- Fixed-layout publication figures, mechanisms, template replication, and image comparison: [publication-figures.md](references/publication-figures.md)
- RDKit atom/CIP inspection, explicit R/S edits, stereo/tautomer enumeration, MCS, R-group decomposition, and aligned grids: [rdkit-workbench.md](references/rdkit-workbench.md)
- Multi-structure image segmentation, DECIMER API recognition, agent visual correction loops, and structured reaction-condition transcription: [image-visual-review.md](references/image-visual-review.md)

For first-time installation or upgrade work, load [operations.md](references/operations.md) before changing files or MCP configuration. Run the read-only prerequisite checker, distinguish core, native ChemDraw, ChemScript, Office, and DECIMER requirements, and verify only the capabilities the user selected.

For an exact callable signature, read [mcp-signatures.md](references/mcp-signatures.md). For selection, policy, and errors, read [toolkit-tools.md](references/toolkit-tools.md). Do not guess arguments from prose.

Start diagnosis with `get_toolkit_capabilities()`. The default full runtime profile
contains 39 tools; `core`, `office`, `analysis`, and `chemscript` profiles can
reduce tool selection noise for focused work.
If a documented tool is missing, verify the installed runtime version and refresh the client tool list. Use the documented figure CLI when the client cannot discover MCP tools.

## Domain References

- Chemistry resolution and molecular diffs: [toolkit-chemistry-resolution-interfaces.md](references/toolkit-chemistry-resolution-interfaces.md)
- Rendering, layout, cleanup, and merge: [toolkit-render-layout-interfaces.md](references/toolkit-render-layout-interfaces.md)
- OCSR, reaction images, RDF, and scheme reading: [toolkit-perception-image-interfaces.md](references/toolkit-perception-image-interfaces.md)
- LCMS/NMR and lab books: [toolkit-analysis-interfaces.md](references/toolkit-analysis-interfaces.md)
- ChemDraw COM and Office OLE: [toolkit-office-chemdraw-interfaces.md](references/toolkit-office-chemdraw-interfaces.md)
- CLI-only workflows: [toolkit-cli-interfaces.md](references/toolkit-cli-interfaces.md)
- Runtime, configuration, and DECIMER status: [operations.md](references/operations.md)
- Reviewed exclusions: [toolkit-reviewed-exclusions.md](references/toolkit-reviewed-exclusions.md)
- Exhaustive audit index: [toolkit-public-inventory.md](references/toolkit-public-inventory.md)

## Acceptance

Return absolute output paths and check output existence. For molecules, inspect `chemistry_validation` source/roundtrip signatures, stereo groups, E/Z, isotopes and charges. Generated reaction fragments use the same final-coordinate validation; retain source-to-species roles and verify the complete reaction graph when parsing/merging. Layout-only edits must preserve the source molecular inventory.

When native ChemDraw is available, render final CDXML through it and inspect actual pixels for missing arrow shafts, overlapping labels, stereo annotations, clipping, and missing plus signs. Dimensions alone are insufficient. Inspect the revised figure again after cleanup, template edits, or font changes. Confirm editable OLE objects for Office outputs.

For reference replication, compare aligned images at the same scale/DPI, record dimensions and pixel/ink metrics, then inspect meaningful differences. Pixel equality does not establish chemical correctness; chemical equivalence does not establish visual equality. Report unverified/unsupported features and distinguish a native-template copy from a reconstructed raster figure.

RDKit round-trip preservation establishes consistency under that reader, not independent stereochemical truth. Any known cross-reader disagreement keeps full stereochemical acceptance unresolved. If native rendering is unavailable, deliver editable CDXML with an explicit pending-native-validation status.
