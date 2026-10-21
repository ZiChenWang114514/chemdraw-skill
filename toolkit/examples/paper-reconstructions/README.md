# Editable paper-figure reconstructions

Run `python rebuild.py <new-output-directory>` in an environment containing `cdxml-toolkit` and `lxml`. This offline example assembles native molecular fragments, abbreviations, text, brackets and electron arrows. It does not repeat image recognition or require network access. Render the resulting CDXML through installed ChemDraw for a native preview.

Both complete layouts are provided, including the shared OR representation for compounds 113/114. Component molecular inventories must remain unchanged during assembly. Coordinates belong to these examples and are not general drawing rules.

Native saving keeps connectivity, charges, isotopes and alkene geometry; the reader comparison below records the stereochemistry of every component. Source artwork belongs to the original paper and is not covered by the software license.

## Stereochemistry review

[Reader comparison](stereochemistry-check.json) records 18 included components, their source hashes and connectivity-matched atom indices. Compounds 105–109, 115–120 and 121 contain opposing assignments between RDKit and direct ChemScript output. Other differences concern specified versus unspecified centers. Atom indices refer to the recorded RDKit readback, not paper atom numbering.

Upgrading RDKit (2026.03.3 to 2026.03.6) does not change compound 120. Do not flip wedges to make readers agree: first establish the source configuration, then validate both the resulting chemistry and native rendering.
