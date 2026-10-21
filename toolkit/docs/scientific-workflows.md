# Scientific drawings and spectrum analysis

Generate editable TLC plates, assemble native ChemDraw apparatus templates, analyze processed 1D NMR spectra, draw plots from numerical data, and annotate mechanisms with atom- or bond-anchored electron arrows.

Install the optional numerical dependencies:

```console
python -m pip install -e ".[scientific]"
python docs/examples/scientific/run_examples.py --output generated-examples
```

The runner creates a native TLC plate, a substitution mechanism and a clearly labeled simulated kinetic plot. It preserves data and writes receipts. The output directory must be new. Native ChemDraw rendering requires an activated Windows installation and is a separate step.

## Native TLC

```console
python -m cdxml_toolkit.scientific tlc --spec docs/examples/scientific/tlc.json --output plate.cdxml
```

The output contains native `tlcplate`, `tlclane` and `tlcspot` objects. Each spot accepts an Rf between 0 and 1, dimensions in points and optional tail length. The example values are illustrative.

For calibrated image measurements:

```python
from cdxml_toolkit.scientific.tlc import measure_rf
rf = measure_rf(origin=[40, 200], solvent_front=[40, 40], spot=[43, 120])
assert rf == 0.5
```

The projection follows the origin-to-front direction. Spot area or darkness is not converted into purity.

## Native apparatus and instruments

Use the installed ChemDraw Clipware templates. Preserve the CTP files, copy them to working CDX files, and convert the copies through the toolkit's isolated native converter. Inspect the template pages before selecting components. The example assembles a round-bottom flask, Allihn condenser, stand, clamp and magnetic stirrer from editable template objects.

```console
python docs/examples/scientific/run_examples.py --output laboratory-examples --glassware templates/clipware-1.cdxml --condensers templates/clipware-2.cdxml
```

Page indexes in `apparatus.json` belong to the inspected Clipware libraries; verify them against your installation. `template_catalog(path)` in `cdxml_toolkit.scientific.apparatus` reports page indexes, bounds and source hashes. Component positions use CDXML points, with uniform scale and normalized attachment ports. Inspect the resulting joints, clamps and connections in native ChemDraw. If an instrument is absent from the installed library, supply an appropriate native template rather than silently substituting an approximation.

The toolkit does not distribute the proprietary template libraries. A port describes a drawing connection, not physical joint compatibility or laboratory operating instructions.

## Real NMR data

```console
python -m cdxml_toolkit.scientific nmr --spec docs/examples/scientific/nmr.json --output nmr-results
```

Set the JSON input path to a processed real 1D NMRPipe `.ft`, `.ft1` or `.ft2` file, or a CSV with `ppm,intensity` columns. Paths are relative to the JSON file. Raw FID processing, phase correction, 2D assignment and structure identification are not implemented by this command.

Processing supports optional polynomial baseline correction over explicit signal-free windows, prominence-based peak picking, integration over specified ppm intervals, and normalization to an explicit reference integral. Invalid windows, duplicate/non-monotonic axes, non-finite samples and unknown options are rejected. Results preserve the input hash, processing choices, peak table and integral table; normalized results record the reference region and denominator.

A real NMRPipe integration example is available from the [nmrglue documentation](https://nmrglue.readthedocs.io/en/latest/examples/integrate_1d.html). Its `1d_data.ft` was used to validate this workflow. The example integration ranges in `nmr.json` apply to that dataset only. For a different spectrum, choose appropriate ranges, or use the demo runner's `--nmr-input` option to perform peak picking without those preset ranges. Peaks are not automatic atom assignments, and integration alone does not establish purity.

## Scientific plots

The `plot` command reads named CSV columns and explicit axis labels. It writes SVG, PNG, editable CDXML, full-resolution CSV and metadata. CDXML display curves use a peak-preserving min/max envelope when necessary; the exported CSV retains all points. The included first-order-decay data are simulated with `fraction = exp(-0.06 × time_min)` and are labeled accordingly.

## Mechanisms

```console
python -m cdxml_toolkit.scientific mechanism --spec docs/examples/scientific/mechanism.json --output mechanism.cdxml
```

Each molecule uses grounded SMILES or a structure file and one explicit coordinate per atom. An electron arrow names a source and target atom or bond, optional endpoint offsets, two Bezier control points and an electron count of 1 or 2. Invalid anchors and nonexistent bonds are rejected. Native lone-pair and charge symbols can be included as `symbol` objects; formal molecular charges must also exist in the molecule graph.

For a fully specified equation, set `complete: true` on its step and include all atom-contributing species on both sides. The compiler checks element counts, isotope counts and formal charge, including implicit hydrogen. Repeat a species ID when its stoichiometric coefficient is greater than one. A step with omitted species stays unchecked by default. Conservation checks do not prove that the proposed mechanism is chemically valid.

Inspect the saved CDXML chemistry and native preview independently. Check electron-arrow endpoints, line clearance, charge symbols, abbreviations and stereochemical bonds. Successful rendering is not proof of correct chemistry or pixel identity with a paper figure.

For circled charges, also save through ChemDraw as CDX and convert back to CDXML. Compare `document_inventory` before and after: ChemDraw may associate a floating charge symbol with a nearby atom during opening or saving. Keep the symbol closest to its intended atom and validate the native result even when a `<represent attribute="Charge" object="ATOM_ID"/>` association is present. Inline charged atom labels are the default for new drawings. Variable R substituents use native generic nickname nodes; an atomic `Element="0"` is not a portable ChemDraw representation.

The [eight-structure mechanism example](../assets/readme/mechanism/mechanism.cdxml) includes a [native save-cycle check and source limitations](../assets/readme/mechanism/provenance.json). It reproduces a published proposal; the validation establishes preservation of the reviewed graph, not independent evidence for the mechanism.
