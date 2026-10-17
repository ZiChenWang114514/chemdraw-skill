# Editable paper-figure reconstructions

Run `cdx.py py <skill>/assets/paper-reconstructions/rebuild.py NEW_DIR` (the skill runtime already contains `cdxml-toolkit` and `lxml`). This offline example assembles native molecular fragments, abbreviations, text, brackets and electron arrows. It does not repeat image recognition or require network access. Render the resulting CDXML through installed ChemDraw for a native preview.

Both complete layouts are provided, including the shared OR representation for compounds 113/114. Component molecular inventories must remain unchanged during assembly. Coordinates belong to these examples and are not general drawing rules.

Stereochemistry in these examples is still open (see below), and they are not pixel-identical reproductions. Source artwork is not relicensed.

## Stereochemistry review

[Reader comparison](stereochemistry-check.json) covers the 18 components with connectivity-matched atom indices. Twelve compounds — 105–109 and 115–121 — contain opposing assignments between RDKit and direct ChemScript output. These components were not taken through the [stereo repair procedure](../../references/stereo-reconstruction.md); the 20/20 agreement mentioned there belongs to a different, unshipped development case. Other differences are specified versus unspecified centers. Atom indices refer to the recorded RDKit readback, not paper atom numbering.

An isolated RDKit 2026.03.6 check of compound 120 retained the same assignment as 2026.03.3 and still disagreed with ChemScript. Upgrading the reader alone did not resolve this case. Do not flip wedges to make readers agree: first establish the source configuration, then validate both the resulting chemistry and native rendering.
