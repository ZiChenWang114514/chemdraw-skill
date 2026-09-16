# Perception, Images, And RDF

## When To Load

Load for local/remote OCSR, reaction screenshots, ELN/SciFinder RDF, existing scheme reading, segmentation, or reagent-role classification.

## Preferred Entry Points

- Default image recognition: MCP `extract_structures_via_decimer_api` with upload authorization and `confirm_upload=true`.
- Explicitly requested local/offline recognition only: MCP `extract_structures_from_image`. Do not automatically fall back to local models on API failure.
- Existing CDXML: MCP `parse_scheme`; Python `perception.scheme_reader.read_scheme` for deeper reading.
- SciFinder export: MCP `parse_scifinder_rdf`.
- Large/disconnected scheme: MCP `segment_large_scheme`.
- ELN/CDX/RXN/CSV: MCP `parse_reaction` and `summarize_reaction`.

## Inputs And Outputs

OCSR returns candidate SMILES plus validation metadata; segmentation and candidate order do not establish chemical role. RDF parsing rejects empty reaction sets. CAS enrichment is networked and requires `resolve_cas=true` together with `confirm_pubchem=true`; metadata reports candidate and resolved counts. Scheme reading returns serializable species, steps, topology, and narrative.

## Failure Modes

Local OCSR fails without model weights. Remote OCSR rejects undecodable images, oversized data, unconfirmed upload, invalid endpoint/limits, timeout, and unusable responses. Treat multiple candidates as unresolved. `reaction_image_to_cdxml` remains unregistered because candidate-to-role mapping is not reliably supported.

## Supporting APIs

- `image.structure_from_image`: image loading, segmentation, labels, and mass enrichment.
- `image.reaction_from_image`: descriptor-driven assembly when local recognition is verified.
- `perception.rdf_parser`: V3000 parsing, reaction serialization, optional CAS resolution.
- `perception.spatial_assignment`: arrow vectors, layout classification, and element assignment.
- `perception.reactant_heuristic`: curated/MCS role classification for grounded SMILES.

## Do Not Use Directly

Do not infer atom connectivity with general vision. Do not use LLM refinement as chemical truth. Do not publish developer audit/report generators as ordinary tools.
