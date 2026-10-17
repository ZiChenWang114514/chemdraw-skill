# Chemistry Resolution And Molecular Changes

## When To Load

Load for chemical-name resolution, CAS lookup, formula/MW validation, reagent abbreviations, structural modification, MCS diffs, or aligned names.

## Preferred Entry Points

- Resolve a molecule: tool `resolve_name`.
- Modify a validated molecule: tool `modify_molecule`.
- Draw grounded SMILES: tool `draw_molecule`.
- Search collections: tool `search_compound`.
- Compare molecular identity and similarity: tool `compare_molecules` or `batch_compare_molecules`.
- Python CAS resolution: `resolve.cas_resolver` high-level resolvers.
- Python naming support: curated reagent database and name decomposition modules.

## Inputs And Outputs

Accept a user-provided trusted SMILES or a resolver result. Verify canonical identity, formula, molecular weight, and source before drawing. Molecular modification must include an MCS-based before/after diff. `draw_molecule` repairs missing RDKit wedge annotations, validates connectivity, Kekule bond orders, isotopes, charges, specified tetrahedral centers, and E/Z geometry, then returns the result in `metadata.chemistry_validation`.

Comparison first resolves each representation or supported structure file through `ChemScriptBridge.get_info`. Exact identity uses ChemScript InChI when both values are present. RDKit calculates a chirality-aware fingerprint similarity and a connectivity-only value; a connectivity value of 1.0 with unequal identity is a prompt to inspect stereo, isotopes, charge, or tautomer state. Batch results omit the original representations and continue after a per-pair parsing failure.

## Failure Modes

Names may be ambiguous, network resolvers may disagree, and abbreviations may be context dependent. Return alternatives and provenance rather than selecting silently. Reject direct string edits that bypass molecular graph validation. Treat `stereochemistry_not_preserved` and `structure_fidelity_mismatch` as hard failures; do not publish or render the rejected CDXML.

## Supporting APIs

- `rdkit_utils`: canonicalization, formula/MW, molecule validation, and graph helpers.
- `naming.reagent_database`: known labels and display names.
- `naming.name_decomposer`: R-group decomposition and aligned naming support.
- `resolve.cas_resolver`: optional network-backed CAS/name lookups.

## Do Not Use Directly

Do not construct chemistry from raw atom/bond JSON, invent SMILES from memory, or treat a generated systematic name as stronger evidence than the validated molecular graph and source record.
