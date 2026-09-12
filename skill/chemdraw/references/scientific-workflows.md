# Scientific workflows

Use the toolkit source version containing `cdxml_toolkit.scientific`, with the `scientific` optional dependencies installed. Do not confuse this processed-spectrum interface with the older NMR-report extraction interfaces. Start from the supplied data or grounded molecule; inspect actual outputs before making scientific claims.

| Request | Execute | Deliver |
| --- | --- | --- |
| TLC or laboratory apparatus | [Native laboratory drawings](native-laboratory-drawings.md) | Native editable TLC/template objects and ChemDraw preview |
| Processed 1D NMR analysis | `nmr` | Input hash, processing record, peak/integral tables and plots |
| Numerical scientific plot | `plot` | SVG, PNG, full data CSV and editable CDXML |
| Explicit mechanism | `mechanism` | Grounded molecule graphs and atom/bond-anchored electron arrows |

## Fast examples

The example runner and JSON specifications are in [assets/scientific](../assets/scientific/run_examples.py). From the Skill directory:

```console
python assets/scientific/run_examples.py --output generated-examples
```

This produces TLC, substitution-mechanism and simulated kinetic-plot examples. The TLC values are illustrative and the kinetic data are explicitly simulated. Add `--nmr-input PATH` for a real processed spectrum; add both `--glassware PATH --condensers PATH` for converted, inspected native template libraries. The apparatus page indexes are example-specific and must be checked against the installed library. Use a new output directory.

## NMR: inspect data before analysis

1. Identify the input type, nucleus, units and processing state. Supported inputs are real 1D NMRPipe `.ft`, `.ft1`, `.ft2` and CSV with `ppm,intensity`. Raw FID processing, phase correction, 2D correlations and atom assignment are not implemented by this command.
2. Select integration intervals from the actual spectrum. Optional baseline windows must be signal-free and within its ppm range. Do not reuse the bundled intervals for a different sample.
3. Use `baseline_windows`, integer `baseline_degree` from 0 to 3, positive `prominence`, `integration_regions`, and optional zero-based `normalization_region` plus `normalization_value`. Normalization needs a known reference; do not manufacture proton counts.
4. Run the command and inspect the plotted spectrum for a distorted baseline, missing peaks or inappropriate integration limits. Report assignments as unperformed unless separately supported by evidence.

```console
python -m cdxml_toolkit.scientific nmr --spec nmr.json --output nmr-results
```

The [NMR JSON example](../assets/scientific/nmr.json) uses integration ranges from the real [nmrglue integration example](https://nmrglue.readthedocs.io/en/latest/examples/integrate_1d.html). Set its input path to the downloaded `1d_data.ft`. For another spectrum, replace the ranges or use the example runner, which omits those preset intervals.

## Scientific plots

```console
python -m cdxml_toolkit.scientific plot --spec plot.json --output plot-results
```

The JSON requires `input`, `x_column`, `y_column`, `x_label` and `y_label`; `title` and `reverse_x` are optional. Input paths are relative to the JSON. Label units and distinguish simulated from experimental data. Native CDXML and SVG/PNG share axis limits and ticks. The CDXML display may use a peak-preserving envelope, while the exported CSV keeps all samples. Do not analyze reduced display coordinates as if they were the original data.

## Mechanisms

```console
python -m cdxml_toolkit.scientific mechanism --spec mechanism.json --output mechanism.cdxml
```

Use the [complete substitution example](../assets/scientific/mechanism.json). Each molecule supplies a grounded SMILES or structure `file`, `id` and explicit `coordinates` in atom order. Each electron arrow has `source` and `target` anchors with a molecule ID and either `atom` or `bond: [i,j]`; optional offsets shift endpoints. Two Bezier `controls` shape the curve; `electrons` is 1 or 2. Endpoint anchors follow atom positions; absolute control points must be reviewed after moving a structure.

Use native `symbol` objects for lone pairs and circled charges as described in [publication figures](publication-figures.md). Set formal charges in the molecular graph. ChemDraw can associate a nearby charge symbol with an atom when opening a file: a detached circle is not a safe replacement for a charged atom label. Do not assign a mechanism solely because the drawing is plausible.

For a paper mechanism with circled charges, verify an actual **CDXML → CDX → CDXML** native save cycle with `convert_cdx_cdxml`, then compare `document_inventory` from `cdxml_toolkit.chemistry_semantics` before and after. A valid input CDXML alone misses charge reassignment during native editing. The CDXML `<represent attribute="Charge" object="ATOM_ID"/>` records a charge-symbol association, but placement must still be checked after saving; keep the symbol closest to its intended charged atom. If this prevents an exact visual match, state the difference. Preserve undefined R groups with native `NodeType="GenericNickname" GenericNickname="R"` nodes; `Element="0"` can prevent ChemDraw from opening the document.

When the reference shows a separate proton, create a separate chemical `[H+]` species with an `Element="1"`, `Charge="1"` node. Put its H label on that node and associate any circled plus with that node. Plain H text beside a free charge symbol can cause ChemDraw to charge a nearby heteroatom instead. Verify both species separately after native saving: the proton must remain a proton and the neighbouring molecule must retain its intended charge.

For bridged or perspective ring drawings, inspect native-save stereochemistry even when no new wedges were added. ChemDraw can write `Geometry="Tetrahedral"` and `BondOrdering` from the drawing geometry. Neither removing `CrossingBonds` nor setting `AS="u"` and `Geometry="Unknown"` reliably prevents that inference. Resolve the depicted configuration against the reference before accepting the native result; do not delete stereo from the comparison merely to make validation pass.

Set `complete: true` on a step only when both sides include every atom-contributing species. Element, isotope and charge counts, including hydrogen, must balance. Repeat species IDs for stoichiometric coefficients. Partial paper illustrations remain explicitly unchecked. A balanced equation does not establish mechanistic correctness.

## Acceptance

Before comparing save cycles, inventory the chemical species actually shown in the reference, including separate protons and counterions. Check that each appears in the saved molecular inventory. Identical before/after inventories can still omit a species that was only drawn as text.

Preserve inputs and save command receipts. Read molecular identity from saved CDXML, and inspect native previews for labels, stereo bonds, electron endpoints and symbol sizes. Render plot files with identical basenames into separate directories. Deliver figures and editable documents first, with concise data provenance and known limitations. Never claim pixel-level paper identity from a successful export.
