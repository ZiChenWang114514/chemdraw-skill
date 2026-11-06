# Scientific workflows

These commands need the `cdxml_toolkit.scientific` module and the `scientific` extra (`cdx.py doctor` lists missing extras). If the module is missing, the runtime is older than this Skill; report the rebuild step from `cdx.py doctor` and change the runtime only when the user asks for installation. Do not confuse this processed-spectrum interface with the older NMR-report extraction interfaces. Start from the supplied data or grounded molecule; inspect actual outputs before making scientific claims.

| Request | Execute | Deliver |
| --- | --- | --- |
| TLC or laboratory apparatus | `tlc`, `apparatus` ([Native laboratory drawings](native-laboratory-drawings.md)) | Native editable TLC/template objects (`auto_cospot`, stain palettes, `mode="2d"` 2D TLC) and ChemDraw preview |
| Processed 1D NMR analysis | `nmr` | Input hash, processing record, peak/integral tables and plots (`inset_region`) |
| Stacked multi-spectrum NMR | `stack_nmr` | Stacked time-course / step-by-step NMR comparison (`build_stacked_nmr_cdxml`) |
| LCMS 24/96-well purity plate | `lcms_plate` | High-throughput screening 24/96-well purity heatmap (`build_lcms_plate_cdxml`) |
| Numerical scientific plot | `plot` | SVG, PNG, full data CSV and editable CDXML |
| Explicit mechanism | `mechanism` | Grounded molecule graphs and atom/bond-anchored electron arrows |

Each operation runs either via the CLI subcommand `cdx.py scientific <nmr|plot|tlc|apparatus|mechanism|stack_nmr|lcms_plate> SPEC.json OUTPUT` or as the MCP tool `scientific_workflow(operation, spec_path, output_path)` (profiles `full` and `analysis`) with the same spec files: `tlc`, `apparatus`, `mechanism`, `stack_nmr`, and `lcms_plate` write one new `.cdxml` (plus SVG/PNG sidecars where configured), while `nmr` and `plot` write a new directory. Output is staged and published only on success, and an existing path is never replaced. The commands below remain the way to run it without an MCP client.

## Fast examples

The example runner and JSON specifications are in [assets/scientific](../assets/scientific/run_examples.py). Requires the `scientific` extra (`cdx.py doctor` lists missing extras):

```console
cdx.py py <skill>/assets/scientific/run_examples.py --output NEW_DIR
```

This produces TLC, substitution-mechanism and simulated kinetic-plot examples. The TLC values are illustrative and the kinetic data are explicitly simulated. Add `--nmr-input PATH` for a real processed spectrum; add both `--glassware PATH --condensers PATH` for converted, inspected native template libraries. The apparatus page indexes are example-specific and must be checked against the installed library. Use a new output directory.

## NMR: inspect data before analysis

1. Identify the input type, nucleus, units and processing state. Native 1D NMR loading via `nmrglue` supports:
   - **NMRPipe** processed `.ft`, `.ft1`, `.ft2` files and two-column `ppm,intensity` CSVs;
   - **Bruker** TopSpin processed `pdata/1/1r` directories (`1r` + `procs`/`acqus`) and raw Bruker `fid`/`ser` directories (automatically zero-filled, apodized, Fourier-transformed, and zero-order phased);
   - **JCAMP-DX** `.jdx` and `.dx` spectra (`##XYDATA`, `##PEAK TABLE`, or `##NTUPLES`, automatically converting Hz axes to ppm using `.OBSERVEFREQUENCY`);
   - **JEOL Delta** `.jdf` files (processed frequency-domain or time-domain FID);
   - **Varian / Agilent VNMRJ** `.fid` directories (`fid` + `procpar`).
2. Select integration intervals from the actual spectrum. Optional baseline windows must be signal-free and within its ppm range. Do not reuse the bundled intervals for a different sample.
3. Use `baseline_windows`, integer `baseline_degree` from 0 to 3, positive `prominence`, `integration_regions`, and optional zero-based `normalization_region` plus `normalization_value`. Normalization needs a known reference; do not manufacture proton counts.
4. Configure optional peak analysis and plotting fields in `nmr.json`:
   - **Deuterated residual solvent peak flagging (`1H` and `13C`):** set `solvent` (for example `"CDCl3"`, `"DMSO-d6"`, `"CD3OD"`, `"D2O"`, `"CD2Cl2"`, `"acetone-d6"`, `"CD3CN"`, `"THF-d8"`, `"C6D6"`, `"toluene-d8"`) to flag residual solvent and dissolved H2O/HDO peaks in both `1H` and `13C` peak tables (`is_solvent: true`, `solvent_assignment`) and exclude them from compound peak counts.
   - **Multiplet splitting ($J$-coupling extraction):** when `spectrometer_frequency_mhz` is supplied (or read automatically from vendor metadata), adjacent sub-peaks are grouped into multiplets (`s`, `d`, `t`, `q`, `dd`, `dt`, `td`, `m`) with `center_ppm` and extracted `j_couplings_hz` in Hz.
   - **NMR zoom insets (`inset_region`):** pass `inset_region: [high_ppm, low_ppm]` (for example `[7.8, 7.1]`) to render an expanded zoom inset box above the main spectrum in the SVG, PNG, and editable CDXML outputs.
5. Run the command and inspect the plotted spectrum for a distorted baseline, missing peaks or inappropriate integration limits. Report assignments as unperformed unless separately supported by evidence. To match measured peaks to a model prediction, give `predict_nmr` the measured ppm lists (`experimental_1h`, `experimental_13c`): it returns a model-assisted candidate assignment per peak with errors and outliers ([engines.md](engines.md#predictions)).

```console
cdx.py scientific nmr nmr.json nmr-results
```

### Stacked multi-spectrum NMR (`stack_nmr` / `build_stacked_nmr_cdxml`)

To compare reaction timepoints, purification fractions, or multistep synthetic intermediates on a shared chemical-shift axis (with vertical offset, optional `match_shifts` dashed tracking lines, and `normalize: "each" | "max" | "none"`):

```console
cdx.py scientific stack_nmr stack_nmr.json stacked.cdxml
```

### TLC (`auto_cospot`, stain palettes, `mode="2d"`) & LCMS well plates (`lcms_plate`)

- **TLC (`tlc`):** `draw_tlc` supports automatic co-spot lane generation (`"auto_cospot": true`), chemical stain palettes (`"stain": "uv254" | "kmno4" | "cam" | "ninhydrin" | "anisaldehyde" | "iodine" | "pma"`), and 2D stability TLC (`"mode": "2d"` with diagonal decomposition reference line and first/second-dimension spots).
- **LCMS 24/96-well purity plates (`lcms_plate` / `build_lcms_plate_cdxml`):** render high-throughput screening plates (`rows: 4, cols: 6` or `rows: 8, cols: 12`) colored by target product purity % or internal-standard ratio (`"wells": {"A1": {"purity": 94.2, "label": "94%"}}`):

```console
cdx.py scientific lcms_plate plate.json plate.cdxml
```

The [NMR JSON example](../assets/scientific/nmr.json) uses integration ranges from the real [nmrglue integration example](https://nmrglue.readthedocs.io/en/latest/examples/integrate_1d.html). Its spectrum is not bundled: download `1d_data.ft` from that page (network access; skip this example for offline work) and set the input path to it. For another spectrum, replace the ranges or use the example runner, which omits those preset intervals.

## Scientific plots

```console
cdx.py py -m cdxml_toolkit.scientific plot --spec plot.json --output plot-results
```

The JSON requires `x_label` and `y_label` plus either a single-series `input`, `x_column`, `y_column` or a multi-series `series` list (`[{"label": "Cat. A", "input": "a.csv", "x_column": "time_s", "y_column": "conv", "color": "#1b4f72", "style": "both"}, ...]`) for multi-series plot overlays (`style` may be `"line"`, `"scatter"`, or `"both"` with legend and distinct palette colors across SVG, PNG, and editable CDXML). `title` and `reverse_x` are optional. Input paths are relative to the JSON. Label units and distinguish simulated from experimental data. Native CDXML and SVG/PNG share axis limits and ticks. The CDXML display may use a peak-preserving envelope, while the exported CSV keeps all samples. Do not analyze reduced display coordinates as if they were the original data.

## Mechanisms

```console
cdx.py py -m cdxml_toolkit.scientific mechanism --spec mechanism.json --output mechanism.cdxml
```

Use the [complete substitution example](../assets/scientific/mechanism.json). Each molecule supplies a grounded SMILES or structure `file`, `id` and explicit `coordinates` in atom order. Each electron arrow has `source` and `target` anchors with a molecule ID and either `atom` or `bond: [i,j]`; optional offsets shift endpoints. Two Bezier `controls` shape the curve; `electrons` is 1 or 2. Endpoint anchors follow atom positions; absolute control points must be reviewed after moving a structure.

Use native `symbol` objects for lone pairs and circled charges as described in [publication figures](publication-figures.md). Set formal charges in the molecular graph. ChemDraw can associate a nearby charge symbol with an atom when opening a file: a detached circle is not a safe replacement for a charged atom label. Do not assign a mechanism solely because the drawing is plausible.

For a paper mechanism with circled charges, verify an actual **CDXML → CDX → CDXML** native save cycle with `convert_cdx_cdxml`, then compare the molecular inventories before and after: `cdx.py py -c "import sys; from cdxml_toolkit.chemistry_semantics import validate_document_preserved as v; print(v(sys.argv[1], sys.argv[2]))" before.cdxml after.cdxml` prints `'status': 'preserved'` or fails with `chemical_semantics_changed`; then find the changed species by comparing the two files. A valid input CDXML alone misses charge reassignment during native editing. The CDXML `<represent attribute="Charge" object="ATOM_ID"/>` records a charge-symbol association, but placement must still be checked after saving; keep the symbol closest to its intended charged atom. If this prevents an exact visual match, state the difference. Preserve undefined R groups with native `NodeType="GenericNickname" GenericNickname="R"` nodes; `Element="0"` can prevent ChemDraw from opening the document.

When the reference shows a separate proton, create a separate chemical `[H+]` species with an `Element="1"`, `Charge="1"` node. Put its H label on that node and associate any circled plus with that node. Plain H text beside a free charge symbol can cause ChemDraw to charge a nearby heteroatom instead. Verify both species separately after native saving: the proton must remain a proton and the neighbouring molecule must retain its intended charge.

For bridged or perspective ring drawings, inspect native-save stereochemistry even when no new wedges were added. ChemDraw can write `Geometry="Tetrahedral"` and `BondOrdering` from the drawing geometry. Neither removing `CrossingBonds` nor setting `AS="u"` and `Geometry="Unknown"` reliably prevents that inference. Resolve the depicted configuration against the reference before accepting the native result; do not delete stereo from the comparison merely to make validation pass.

When a bridgehead assignment is missing or disputed, compare RDKit's readback with `cdx.py chemscript-info <saved.cdxml>` on the **same saved file**, matching atoms by connectivity rather than by index. A MOL export read by RDKit can lose centers and is only a secondary check. Setting `Geometry` and `BondOrdering` alone does not make readers recover the intended stereo; leave real disagreements open.

Set `complete: true` on a step only when both sides include every atom-contributing species. Element, isotope and charge counts, including hydrogen, must balance. Repeat species IDs for stoichiometric coefficients. Partial paper illustrations remain explicitly unchecked. A balanced equation does not establish mechanistic correctness.

## Acceptance

Before comparing save cycles, list every species the reference shows, including separate protons and counterions, and check each one is in the saved inventory — a species drawn only as text will be missing on both sides.

Read molecular identity from the saved CDXML and look at the native previews for labels, stereo bonds, electron-arrow endpoints and symbol sizes. Render plot files with identical basenames into separate folders. Deliver the figures and editable files first, with a short note on data source and limitations.
