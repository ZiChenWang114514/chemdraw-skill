# Analytical And Lab-Book Workflows

## When To Load

Load for LCMS/NMR PDFs, multi-timepoint LCMS, experiment file discovery, expected masses, procedure writing, or complete lab-book assembly.

## Preferred Entry Points

- One analytical PDF: tool `parse_analysis_file`.
- Discover an experiment: tool `discover_experiment_files`.
- Multi-LCMS tracking: tool `analyze_lcms_series`.
- Format structured entries: tool `format_lab_entry`.
- Complete experiment entry: tool `assemble_lab_book`.
- Python series engine: `analysis.deterministic.multi_lcms_analyzer.analyze`.
- Python expected species: `mass_resolver.extract_expected_masses`.

## Inputs And Outputs

Single-file parsing supports recognized Waters/manual LCMS and MestReNova NMR reports. Series analysis requires at least two standard LCMS PDFs and emits one validated JSON object or list of result groups with warnings. Discovery returns classified CSV/CDX/RXN/LCMS/NMR paths. Lab-book assembly writes source-grounded text.

## Failure Modes

Reject unsupported PDFs, missing experiment identity, nonpositive tolerances, ambiguous acquisition order presented as certain, and inferred peaks or integrations. Expected-mass matches are not confirmed identities. Byproducts from FlowER (a reaction-outcome prediction model, enabled with `predict_byproducts=True`) are predictions: label them so and never enable them silently.

## Supporting APIs

- `analysis.lcms_analyzer`: report detection, parsing, tables, annotations, and peak matching.
- `lcms_file_categorizer`: batch classification and order calibration.
- `lcms_identifier`: match tracked ions to expected adducts.
- `procedure_writer`: file discovery and NMR extraction.
- `lab_book_formatter`: procedure, characterization, notes, and final assembly sections.

## Do Not Use Directly

Do not expose per-peak matching, ion clustering, or trend internals as standalone MCP tools. Do not infer absent analytical values or suppress source and exclusion warnings.
