# Stereo-sensitive reconstruction and native-save diagnosis

Use when perspective bonds, collapsed labels or bridged cages give different stereo in different readers. It supplements [saved-file validation](figure-validation.md); it is not an automatic fixer.

## First decide the target

Decide what the source shows before repairing how it is drawn. Reader agreement cannot resolve an ambiguous source. Keep the source-oriented drawing; if an explicit-wedge variant is needed for interoperability, deliver both and name the changed compounds.

On a large figure, test the hard fragments early: a bridged stereocenter next to a collapsed group, an N-H or acid O-H abbreviation, a charged stereogenic nitrogen. Render and native-save them before reusing a template.

## Diagnose in this order

1. Reproduce one failing saved fragment before any batch change. Note ChemDraw, ChemScript and RDKit versions; `Chem.HasChemDrawCDXSupport()` tells which RDKit reader is used.
2. Check graph, bond orders, charges, isotopes, hydrogens and radicals first. Expand collapsed groups for analysis. `LabelDisplay` controls abbreviation direction; moving text alone may not. Turning off chemical label interpretation can drop inferred N-H/O-H on native save. Set an explicit hydrogen only on the atom the source supports.
3. Map atoms by the full graph, not by index or record order. Where symmetry gives several mappings, continue only if the stereo target is the same in all.
4. Classify each mapped center: same, missing, opposite, unspecified or unresolved. A changed CIP letter after a connectivity change is not by itself an inversion.
5. Check the depiction: uniform `Bold`, uniform `Hash`, `WedgeBegin` and `WedgedHashBegin` mean different things. Check the narrow end, explicit H, bridge depth and neighbouring centers. Native `CrossingBonds` handle occlusion; `Dash` is not a substitute.
6. Correct through `modify_molecule` / `rdkit_workbench` and read the diff. CDXML `AS` is a cached CIP label, not evidence. Workarounds found for one reader version are version-specific; do not hard-code them.
7. Save CDXML → CDX → CDXML and read the saved file with both readers (`cdx.py chemscript-info` for ChemScript). Native save may rewrite `BondOrdering` or geometry. Compare both readers with the target, not only with each other. Never erase stereo or flip wedges to get agreement.
8. Render the final file and look at the whole figure and the changed details. Report what stays unresolved.

## Drawing pitfalls

Shared topology does not mean shared coordinates; trace a local outlier instead of re-tuning a wrong template. Double-bond placement and Kekulé choice can differ visually with no change in identity. Charge symbols and electron-arrow heads render larger than their stored bounds; check them in the PNG. An X-ray panel requested as an image is cropped and embedded, never redrawn.

## The two reference cases

- **Twenty-structure development case (not shipped).** After this procedure, all 20 structures reached RDKit/ChemScript agreement with ChemDraw 22.2.0.3300, ChemScript 22.0.0.0 and RDKit 2026.03.3.
- **Bundled example ([assets/paper-reconstructions](../assets/paper-reconstructions/README.md)).** Its 18 components were assembled for layout only and were not taken through this procedure. 12 of them (105–109 and 115–121) still have opposing RDKit/ChemScript assignments (`stereochemistry-check.json`). It is useful practice material for this guide.

References: [CDXML cached CIP](https://iupac.github.io/IUPAC-FAIRSpec/cdx_sdk/properties/Atom_CIPStereochemistry.htm), [node label direction](https://iupac.github.io/IUPAC-FAIRSpec/cdx_sdk/properties/Node_LabelDisplay.htm), [bond display](https://iupac.github.io/IUPAC-FAIRSpec/cdx_sdk/properties/Bond_Display.htm), [RDKit ChemDraw reader](https://github.com/rdkit/rdkit/blob/master/External/ChemDraw/utils.cpp).
