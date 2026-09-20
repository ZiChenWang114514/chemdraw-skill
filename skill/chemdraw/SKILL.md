---
name: chemdraw
description: Use ChemDraw and cdxml-toolkit for editable chemical structures, reaction figures, image reconstruction, scientific drawings, chemical analysis, and ChemDraw objects in Office; also install or diagnose their runtime.
---

# ChemDraw

Use `cdxml-toolkit-community` for editable chemistry. Preserve sources and distinguish chemical identity, reader consistency, native compatibility, and visual fidelity. This Skill supports any agent with MCP or the documented Python/CLI runtime; native rendering requires the licensed Windows host.

## Core Rules

1. Ground connectivity in trusted user structures, a resolver, parser, or reviewed OCSR candidate. Never treat valid SMILES syntax as recognition accuracy. Route intentional structural corrections through `modify_molecule`; inspect its comparison status, not just empty change lists. Use `rdkit_workbench` for explicit atom-index stereo edits.
2. Preserve input files. Write new staged outputs, inspect their actual readback, and retain source hashes and unresolved issues. Byte-identical copying proves unchanged bytes only.
3. For image recognition, use DECIMER API for task images and relevant crops with `confirm_upload=true`, without a separate upload question. Honor explicit offline/no-upload requests. Do not silently switch models or endpoints after failure.
4. A crossing does not create an atom. Distinguish an occluded solid bond, a repeated dash, and a stereochemical hashed wedge. Review narrow ends and foreground/background relationships against the image.
5. Layout edits must preserve the molecular inventory, including stereo, charge and isotope information. If a bond-display edit changes semantic readback, do not accept it as layout-only.
6. Use isolated workers and the shared resource lock for native operations. Never substitute RDKit rendering for required native acceptance, or flatten editable chemistry into a bitmap.

## Route By Intent

Read only the matching workflow and the needed tool signature, not the complete catalog.

| Task | Start here |
| --- | --- |
| Publication image or reaction screenshot | [Quick reconstruction](references/image-visual-review.md) |
| Small-context models, result files, local task packets | [Efficient reconstruction](references/efficient-reconstruction.md) |
| Molecule drawing, modification, comparison, reaction editing | Matching section in [workflow router](references/workflow-router.md) |
| Exact coordinates, native template edits, arrows, crossings | [Figure manifest](references/publication-figures.md) |
| Reader stereo disagreement, native-save H loss | [Stereo diagnosis](references/stereo-reconstruction.md) |
| Saved-file and cross-reader validation | [Figure validation](references/figure-validation.md) |
| Substrate scope, SAR, table-driven updates | [Data-driven figures](references/data-driven-figures.md) |
| Office extraction, inspection, replacement or embedding | Office section in [workflow router](references/workflow-router.md) |
| LCMS/NMR reports, RDF, experiment discovery and lab books | Analysis section in [workflow router](references/workflow-router.md) |
| Processed spectra, plots and mechanisms | [Scientific workflows](references/scientific-workflows.md) |
| TLC, apparatus and instruments | [Native laboratory drawings](references/native-laboratory-drawings.md) |
| Atom indices, CIP, MCS or stereo enumeration | [RDKit workbench](references/rdkit-workbench.md) |
| Installation, upgrade, missing tools or runtime failure | [Operations](references/operations.md), then [agent integration](references/agent-integration.md) if needed |

For recurring errors, consult [lessons](references/lessons.md). Exact MCP signatures are generated in [mcp-signatures.md](references/mcp-signatures.md); search the requested tool section. Use [interface catalog](references/interface-catalog.md) only when routing does not identify an entry point.

## Publication Figure Reconstruction

Inspect the whole image, crop structures, recognize, correct connectivity and charges, verify stereobonds and occlusion, then restore coordinates and text. Native-render and inspect local details plus the complete figure. Reprocess only affected regions, preserving candidate/correction provenance. Follow the quick reconstruction guide for commands and the task record.

Execute serially unless the user explicitly requests parallel agents or sets `parallel=true`. A request to edit parallel-workflow instructions does not itself authorize delegation. Use short local packets for an authorized worker; retain global conditions, final review and unresolved chemistry with the main agent. Never upgrade models automatically.

## Acceptance

Deliver editable files and native previews first. State the outcome separately for source review; connectivity, bond order and charge; stereochemistry and reader agreement; native opening/saving/rendering; and visual comparison. Use not-run, unresolved and failed distinctly. Do not inflate a short response with checks irrelevant to the task.

For bridges, charge symbols or stereo-sensitive edits, run the saved-file workflow. Native saving may add configurations. Cross-reader disagreement keeps stereo acceptance unresolved; never flip wedges to force agreement. Compare mapped atoms, not raw indices from different files.

Inspect native pixels for clipped labels, arrows, charges and crossings. Use same-scale alignment for numerical image comparison; independently resized panels are for visual review only. Pixel metrics never establish chemistry. Claim strict 1:1 only when demonstrated.

Use runtime capability queries only for missing interfaces, unknown versions or diagnosis; `detail="summary"` avoids loading every signature. Do not infer capabilities from fixed tool counts. If native validation cannot run, deliver a clearly identified draft with the outstanding checks.
