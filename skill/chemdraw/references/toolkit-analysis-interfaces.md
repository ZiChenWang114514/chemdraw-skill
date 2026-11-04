# Analytical And Lab-Book Workflows

## When To Load

Load for LCMS reports (Waters MassLynx PDF or OpenLynx .rpt), NMR PDFs, multi-timepoint LCMS, experiment file discovery, expected masses, procedure writing, or complete lab-book assembly.

## Preferred Entry Points

- One analytical file (LCMS PDF, OpenLynx `.rpt`, NMR PDF): tool `parse_analysis_file`.
- Discover an experiment: tool `discover_experiment_files`.
- Multi-LCMS tracking: tool `analyze_lcms_series`.
- Format structured entries: tool `format_lab_entry`.
- Complete experiment entry: tool `assemble_lab_book`.
- Python series engine: `analysis.deterministic.multi_lcms_analyzer.analyze`.
- Python expected species: `mass_resolver.extract_expected_masses`.

## Inputs And Outputs

Single-file parsing supports recognized Waters/manual LCMS PDFs, OpenLynx `.rpt` exports and MestReNova NMR reports. An `.rpt` is a text batch export with one `[SAMPLE]` per injection: `parse_analysis_file` returns the same report dict as for a PDF when it holds one sample, otherwise `{source_format, sample_count, samples: [...]}`. Each sample carries `sample_name`, `sample_id`, `well`, peaks with RT, area and area %, ESI+/ESI- ions (up to five, at least 20 % of the base peak, with `intensities`) and UV maxima; when the file has no DAD total-absorbance trace the MS TIC areas are used and `detector` says `MS TIC`. Series analysis requires at least two standard LCMS PDFs, or one `.rpt` with at least two samples (each sample is a timepoint), and emits one validated JSON object or list of result groups with warnings. Discovery returns classified CSV/CDX/RXN/LCMS/NMR paths. Lab-book assembly writes source-grounded text.

## Failure Modes

Reject unsupported PDFs and text that is not an OpenLynx export, missing experiment identity, nonpositive tolerances, ambiguous acquisition order presented as certain, and inferred peaks or integrations. Expected-mass matches are not confirmed identities. Byproducts from FlowER (a reaction-outcome prediction model, enabled with `predict_byproducts=True`) are predictions: label them so and never enable them silently.

## Supporting APIs

- `analysis.lcms_analyzer`: report detection, parsing (`parse_report` for one sample, `parse_reports` for every sample of a PDF or `.rpt`), tables, annotations, and peak matching.
- `analysis.openlynx_rpt`: the OpenLynx `.rpt` parser. Experiment discovery takes single-sample `.rpt` files and skips batch exports with a warning; `format_lab_entry` LCMS entries take `sample` to pick one sample of a batch `.rpt`. Shimadzu `.daml` and Agilent `report.txt` are not read.
- `lcms_file_categorizer`: batch classification and order calibration.
- `lcms_identifier`: match tracked ions to expected adducts.
- `procedure_writer`: file discovery and NMR extraction.
- `lab_book_formatter`: procedure, characterization, notes, and final assembly sections.

## Do Not Use Directly

Do not expose per-peak matching, ion clustering, or trend internals as standalone MCP tools. Do not infer absent analytical values or suppress source and exclusion warnings.
