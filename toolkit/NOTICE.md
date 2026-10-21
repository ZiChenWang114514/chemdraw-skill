# Third-Party Notices

## Community maintenance

This repository is maintained by ZiChenWang114514 as an independent community
continuation of Hiu Fung Kevin Lee's original `cdxml-toolkit` project. The
original Git history, copyright notice, MIT license, and attribution are
preserved. Community modifications are copyright 2026 ZiChenWang114514 and
contributors under the same MIT license.

This project includes data and code derived from the following sources.

## ChemScanner (data source)

The files `chemscanner_abbreviations.json` and `superatom_data.json` contain
chemical abbreviation-to-SMILES mappings derived from data files in the
[ChemScanner](https://github.com/ComPlat/chem_scanner) project, which is
licensed under AGPL-3.0.

The original data was extracted from ChemScanner's `abbreviations.yaml`,
`solvents.yaml`, and `superatom.txt` configuration files. The extraction
process involved:
- Parsing the original YAML/TXT files
- Validating all SMILES strings with RDKit
- Canonicalizing SMILES to a standard form
- Deduplicating entries by canonical SMILES
- Reorganizing into a different JSON schema with alias support

The resulting JSON files contain factual chemical information (abbreviation
labels mapped to their corresponding SMILES representations). Chemical
abbreviation-to-structure mappings are scientific facts — "OTs" represents
a tosylate group regardless of the source from which it is documented.

## RDKit Built-in Abbreviations (runtime data source)

At runtime, `superatom_table.py` supplements its JSON-backed lookup table
with abbreviation data from RDKit's `rdAbbreviations.GetDefaultAbbreviations()`
(approximately 40 entries). RDKit is licensed under the
[BSD 3-Clause License](https://github.com/rdkit/rdkit/blob/master/license.txt).

## Reagent Database

The file `reagent_abbreviations.json` is an original curated database of
approximately 172 reagent entries commonly used in medicinal chemistry,
compiled by the project author. It is licensed under MIT as part of this project.
