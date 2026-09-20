# Stereo-sensitive reconstruction and native-save diagnosis

Use this guide when perspective bonds, collapsed labels, or bridged cages disagree between readers. It supplements [saved-file validation](figure-validation.md); it is not an automatic stereochemistry fixer.

## Establish the target before repairing representation

Separate source fidelity, molecular identity, reader agreement, native compatibility, and visual review. A high image score cannot accept chemical changes, and agreement between readers cannot identify an ambiguous source. Preserve the source-oriented document before making an interoperability variant. If an explicit wedge depiction is necessary, disclose the changed compound and retain both variants. Do not silently prioritize either objective.

For an expensive figure, test representative difficult fragments early: a bridged stereocenter adjacent to a collapsed group, an N-H or acid O-H abbreviation, and any charged stereogenic nitrogen. Render and run a native save/readback before propagating a shared template. Reuse recognition candidates and unchanged crops. After each local correction check affected fragments; run the complete final inventory and native render once the candidate is stable. A later semantic edit invalidates the earlier acceptance.

## Diagnose in this order

1. Freeze the exact candidate, source hash, reader versions and parser capability. Check `Chem.HasChemDrawCDXSupport()` where available: the ChemDraw-backed and legacy RDKit readers need not use the same implementation. Reproduce one failing saved fragment before a batch change.
2. Confirm graph, bond orders, charges, isotopes, hydrogens and radicals first. Expand collapsed groups for analysis. `LabelDisplay` controls abbreviation direction; moving text alone may not. Disabling chemical label interpretation can remove inferred N-H/O-H on native save. Set an explicit hydrogen only on the source-supported inner atom; never add H to every N/O or use appearance as proof. Inspect both initial and saved inventories.
3. Map corresponding atoms by the complete graph. Original indices and CDXML record order are not identity. Enumerate symmetry-equivalent mappings; proceed only where the stereo target is unambiguous across them. MCS partial/ambiguous results do not establish no change. Coordinates help locate a node but require a fitted and verified transform, not an assumed parser scale.
4. Classify each mapped center as same, missing, opposite, unspecified, or unresolved. Keep compound labels and source locations. A changed CIP descriptor after a connectivity change is not by itself spatial inversion.
5. Check the actual depiction: uniform `Bold`, uniform `Hash`, `WedgeBegin`, and `WedgedHashBegin` have different semantics. Review the narrow end, explicit H, bridge depth and neighboring centers. Crossings do not create atoms. Native `CrossingBonds` and depth preserve occlusion; `Dash` is not a substitute.
6. Apply a source-grounded correction through the workbench/structural-edit workflow and inspect its diff. CDXML `AS` is cached CIP annotation, not independent evidence. Metadata and XML node-order workarounds observed in one reader combination must be treated as version-specific; do not hardcode this case's IDs, R/S assignments, or ordering into a general repair. Do not patch vendor libraries to conceal disagreement.
7. Repeat CDXML -> CDX -> CDXML and read the saved CDXML directly with both readers. A MOL intermediate can lose the feature under test. Native save may rewrite `BondOrdering` or geometry; an initial XML-only pass is insufficient. Match both results against the predeclared target, not only against each other. If perspective and explicit bonds conflict, test a consistent explicit depiction locally and disclose the visual tradeoff. Do not erase stereo to obtain agreement.
8. Render the exact accepted bytes, inspect the entire figure and changed details, and record the receipt/hash. Report unresolved differences as unresolved, not as a complete reproduction.

## Rendering pitfalls worth checking locally

Shared molecular topology does not imply shared coordinates. Trace a local outlier instead of repeatedly tuning a wrong template. Double-bond placement and the chosen alternating aromatic depiction can differ visually without changing canonical identity. Charge symbol bounds and electron-arrow head geometry may not equal their rendered extents; inspect the native result and the charge-bearing atom separately. For an X-ray panel requested as an image, crop and embed the source pixels; do not infer or redraw a molecular model.

Use same-scale translation/padding for pixel comparisons. Independently resized review panels are only visual aids. Report whole-figure and relevant local metrics; white background can hide large structural errors. Neither IoU nor a matching render receipt establishes chemistry correctness.

## Evidence and efficiency

Keep an acceptance table with separate statuses for source interpretation, graph/charge/H/radicals, stereo target, native persistence, direct reader agreement, and visual fidelity. Top-level `ok` only means a report was produced. The figure validator exposes `hydrogen_count`, `radical_electrons`, and `composition_preserved` on toolkit versions containing these diagnostics; absence on an older runtime means unavailable, not zero. Composition equality is weaker than semantic identity and does not replace it. Radicals may be intentional; report them rather than rejecting every nonzero count.

Read only relevant signatures and compact result summaries; keep large SDK catalogs and raw diagnostic arrays in files. Stop unsuccessful source-download guessing after an access failure and record the limitation. If usage is requested, subtract cumulative token snapshots at explicit start/end cutoffs rather than summing snapshots. Cached input is already part of input; reasoning is already part of output. Report unavailable third-party usage separately. Do not call a workflow efficient merely because its final checks pass.

The observed case used ChemDraw 22.2.0.3300, ChemScript 22.0.0.0 and RDKit 2026.03.3. Its 20/20 reader agreement is an interoperability result for those versions, not experimental confirmation of absolute configuration or a guarantee for other parsers.

References: [CDXML cached CIP annotation](https://iupac.github.io/IUPAC-FAIRSpec/cdx_sdk/properties/Atom_CIPStereochemistry.htm), [node label direction](https://iupac.github.io/IUPAC-FAIRSpec/cdx_sdk/properties/Node_LabelDisplay.htm), [bond display](https://iupac.github.io/IUPAC-FAIRSpec/cdx_sdk/properties/Bond_Display.htm), [RDKit ChemDraw reader](https://github.com/rdkit/rdkit/blob/master/External/ChemDraw/utils.cpp). Check the installed build before attributing behavior to upstream source.
