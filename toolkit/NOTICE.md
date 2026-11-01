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

## OPSIN (optional name-to-structure tool)

`scripts/install.py --opsin` downloads the OPSIN command-line JAR from the
[OPSIN releases](https://github.com/dan2097/opsin/releases) page, and the
`opsin` extra installs the `py2opsin` wrapper. Neither is redistributed in this
repository. OPSIN is developed by Daniel Lowe and licensed under the
MIT License ([source](https://github.com/dan2097/opsin)).

## PubChem (online lookup service)

Name and identifier lookups query the
[PUG REST](https://pubchem.ncbi.nlm.nih.gov/docs/pug-rest) service of
PubChem, run by the US National Center for Biotechnology Information. No
PubChem data is bundled. Use of the service follows the
[NCBI policies](https://www.ncbi.nlm.nih.gov/home/about/policies/) and
PubChem's request-volume limits; `CHEMDRAW_OFFLINE=1` turns these requests off.

## DECIMER (structure recognition)

Image recognition uploads the image to the DECIMER endpoint of the
[Cheminformatics Microservice](https://api.naturalproducts.net/) maintained by
the Steinbeck group, or, with the `decimer` extra, runs the
[DECIMER](https://github.com/Kohulan/DECIMER-Image_Transformer) models locally.
DECIMER is licensed under the MIT License; its model weights are downloaded by
the `decimer` package and are not redistributed here. Uploads follow the terms
of the service operator and are refused when `CHEMDRAW_OFFLINE=1` is set.

## Optional prediction engines

Nothing below is bundled. `cdx.py install-engines` downloads each engine and its model files from the
project's own distribution into a separate environment on the user's machine, checks them against pinned
SHA-256 hashes, and runs them locally; only the remote DECIMER engine contacts a service. Each engine's
licence is that of its project; model files carry their own terms.

## MolScribe (structure recognition)

[MolScribe](https://github.com/thomas0809/MolScribe) by Yujie Qian and colleagues, MIT License; the
`swin_base_char_aux_1m` checkpoint is downloaded from the project's Hugging Face repository.

## MolNexTR (structure recognition)

[MolNexTR](https://github.com/CYF2000127/MolNexTR) by Yufan Chen and colleagues, Apache License 2.0, installed
from a pinned commit; its checkpoint is downloaded from the project's Hugging Face dataset repository
(Apache-2.0) and loaded with PyTorch's `weights_only` mode.

## MolParser (structure recognition)

[MolParser](https://github.com/dptech-corp/MolParser) by the UniParser team (DP Technology), Apache License 2.0,
installed from a pinned commit and checked against a pinned hash. The `MolParser-Mobile-V2` weights are downloaded
from Hugging Face at a pinned revision and are licensed **CC BY-NC-SA 4.0: non-commercial use only**. The model
repository includes Python files that transformers runs when the model loads; they are pinned by hash. The YOLO
detector (ultralytics, AGPL-3.0) is not installed or used.

## MolVec (structure recognition)

[MolVec](https://github.com/ncats/molvec) by the NCATS informatics group, Apache License 2.0. The release jar
with dependencies is downloaded from Maven Central and checked against a pinned hash.

## DECIMER Segmentation (structure detection)

[DECIMER Segmentation](https://github.com/Kohulan/DECIMER-Image-Segmentation) by the Steinbeck group, MIT
License. Its Mask R-CNN model is downloaded from Zenodo at install time.

## AiZynthFinder (retrosynthesis)

[AiZynthFinder](https://github.com/MolecularAI/aizynthfinder) by AstraZeneca's Molecular AI group, MIT
License, with the public USPTO policy models and ZINC stock it publishes.

## SynPlanner (retrosynthesis)

[SynPlanner](https://github.com/Laboratoire-de-Chemoinformatique/SynPlanner) by the Laboratoire de
Chemoinformatique (University of Strasbourg), MIT License, with its published USPTO-based reaction rules and
MCULE/Molport building-block list. Its checkpoints are PyTorch files from the project.

## ReactionT5 (reaction prediction)

[ReactionT5v2](https://github.com/sagawatatsuya/ReactionT5v2) by Tatsuya Sagawa and Ryosuke Kojima, MIT
License; the forward and retrosynthesis models are downloaded from Hugging Face as safetensors.

## MagNET (NMR shift prediction)

[MagNET](https://huggingface.co/ekwan16/MagNET) by the Kwan group, MIT License, with PyTorch Geometric
extension wheels from the PyG project.
