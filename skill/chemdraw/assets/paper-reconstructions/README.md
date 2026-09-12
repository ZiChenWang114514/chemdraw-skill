# Editable paper-figure reconstructions

Run `python rebuild.py <new-output-directory>` in an environment containing `cdxml-toolkit` and `lxml`. This offline example assembles native molecular fragments, abbreviations, text, brackets and electron arrows. It does not repeat image recognition or require network access. Render the resulting CDXML through installed ChemDraw for a native preview.

Both complete layouts are provided, including the shared OR representation for compounds 113/114. Component molecular inventories must remain unchanged during assembly. Coordinates belong to these examples and are not general drawing rules.

Connectivity, charge, isotope and alkene checks do not establish full source stereochemistry. Native saving can add bridgehead assignments, and ChemScript and RDKit can disagree. These examples remain provisional for stereochemistry and are not pixel-identical reproductions. Source artwork supplied by the user is not relicensed under the software license.

## Stereochemistry review

[Reader comparison](stereochemistry-check.json) records 18 included components, their source hashes and connectivity-matched atom indices. Compounds 105–109, 115–120 and 121 contain opposing assignments between RDKit and direct ChemScript output. Other differences concern specified versus unspecified centers; absence of a disagreement does not establish agreement with the source image. Atom indices refer to the recorded RDKit readback, not paper atom numbering.

An isolated RDKit 2026.03.6 check of compound 120 retained the same assignment as 2026.03.3 and still disagreed with ChemScript. Upgrading the reader alone did not resolve this case. Do not flip wedges to make readers agree: first establish the source configuration, then validate both the resulting chemistry and native rendering.
