# Editable paper-figure reconstructions

Run `cdx.py py <skill>/assets/paper-reconstructions/rebuild.py NEW_DIR` (the skill runtime already contains `cdxml-toolkit` and `lxml`). This offline example assembles native molecular fragments, abbreviations, text, brackets and electron arrows. It does not repeat image recognition or require network access. Render the resulting CDXML through installed ChemDraw for a native preview.

Both complete layouts are provided, including the shared OR representation for compounds 113/114. Component molecular inventories must remain unchanged during assembly. Coordinates belong to these examples and are not general drawing rules.

The reader comparison below records the stereochemistry of every component. Source artwork belongs to the original paper and is not covered by the MIT license.

## Stereochemistry review

[Reader comparison](stereochemistry-check.json) covers the 18 components with connectivity-matched atom indices. Twelve compounds — 105–109 and 115–121 — contain opposing assignments between RDKit and direct ChemScript output. The [stereo repair procedure](../../references/stereo-reconstruction.md) describes how to bring such components to agreement. Other differences are specified versus unspecified centers. Atom indices refer to the recorded RDKit readback, not paper atom numbering.

Upgrading RDKit (2026.03.3 to 2026.03.6) does not change compound 120. Do not flip wedges to make readers agree: first establish the source configuration, then validate both the resulting chemistry and native rendering.
