# Editable publication figures and reference replication

For a paper screenshot, start with the [fast replication guide](image-visual-review.md). This page is the optional field reference for fixed layout and drawing objects; do not load it in full before image segmentation or recognition.

Use `compose_chemical_figure(manifest_path, output_path)` for exact placement, mechanism graphics, compound grids, and preservation of a native template. Use `render_scheme` for ordinary automatic reaction layout. Use `compare_figure_images` after native rendering to quantify reference differences.

## Reference-first workflow

1. Inspect the reference and identify the required chemical content, font, bond length, line width, wedge style, labels and arrow types. Prefer original CDX/CDXML/Office OLE over raster reconstruction. PDF/SVG line art can guide geometry, but is not automatically an editable chemical graph.
2. Ground all molecules with source structures, resolver or validated OCSR results. Image recognition and layout extraction are separate; unresolved chemistry stays unresolved. Remote image upload still requires authorization.
3. Choose native-template mode when the source CDXML exists. It preserves objects, including uncommon native symbols. Choose fixed-coordinate mode when reconstructing from a figure, with one coordinate per source atom. Use MCS/template alignment for related compounds, not when it would overwrite the reference conformation.
4. Native-render the result, inspect every panel and compare at the same canvas, scale, DPI and font environment. Fix substantive differences and repeat. Do not stretch or warp an image to disguise errors.
5. Deliver editable CDXML, native PNG/SVG, source/roundtrip chemistry evidence and reference-comparison JSON. A byte-identical native-template copy can preserve all source objects; arbitrary journal screenshots have no universal automatic 1:1 guarantee.

## Manifest v1

Top-level keys: `version: 1`, `objects`, optional `steps`, `style`, `grid`, `template_path`, `edits`. File paths are relative to the manifest unless absolute. All positions are **points, x right, y down**. Output path is a separate tool argument. Existing output files are rejected.

`style` accepts `font`, `font_size`, `bond_length`, `line_width`, `bold_width`, `hash_spacing`, `margin_width`. The base is Arial 10 pt, 14.4 pt bonds. Explicitly set measurements from the target figure rather than assigning a supposed universal journal style. Template style overrides affect document defaults and newly added objects; existing explicit text/bond styles remain intact.

Every object may have a unique string `id`, which `steps` can reference.

### Molecule

```json
{
  "type": "molecule", "id": "A",
  "file": "verified_structure.mol",
  "position": [110, 100], "rotation": 0,
  "label": "1", "cip_labels": true
}
```

Sources: tool-produced `smiles`/CXSMILES, `molblock`, or `file` ending CDXML/MOL/SDF. `fragment_index` is zero-based for multi-structure files. Additional controls:

- `coordinates`: exactly one `[x,y]` per input atom, in final CDXML points. This overrides automatic position/rotation; final-coordinate wedging preserves specified configuration. Use `rdkit_workbench inspect` to obtain input indices.
- `preserve_coordinates: true`: use source MOL/CDXML coordinates, normalized to the requested bond length and position. For exact preservation of all native objects/styles, use `template_path` instead.
- `align_to`: a source record for a reference molecule; `alignment_mode: substructure` (default) or `mcs`. Failures do not silently fall back to an unrelated orientation.
- `bond_length`: per-molecule point override; `rotation`: degrees in the mathematical y-up frame before conversion to CDXML.
- `atom_numbers: true`: display zero-based input indices; `cip_labels: true`: labels computed with RDKit CIPLabeler. These labels supplement, never replace, wedge bonds.
- `annotation_offsets`: object keyed by atom index string, e.g. `{"1":[12,-8]}`, to place crowded index/CIP labels precisely.
- `highlight_atoms`, `highlight_bonds`: zero-based index lists; `highlight_color` RGB hex. Atoms receive a visible halo, including unlabeled carbon atoms. `color` colors a whole molecule.
- `bond_displays`: zero-based bond index to `None`, `WedgeBegin`, `WedgeEnd`, `WedgedHashBegin`, `WedgedHashEnd`, `Wavy`, `Bold`, or `Dash`. Used to match a reference's specific bond depiction; final semantic readback rejects changes that remove/invert specified chirality. These are presentation attributes, not a way to invent missing chemistry.

Stereo AND/OR/ABS attributes are retained and round-trip checked. Native ChemDraw may place stereo-group labels close together; inspect and use longer bonds or a native template when the target requires different label placement.

### Text, arrows and graphics

- `text`: `position`, `text` or `runs`, optional `size`, `align` (`Left`, `Center`, `Right`), `color`. Runs accept `text`, `bold`, `italic`, `underline`, `subscript`, `superscript`, `color`. Subscript and superscript are mutually exclusive per run. Unicode text is preserved, but local font glyph availability requires native inspection.
- `arrow`: `start`, `end`, `style`: `forward`, `dashed`, `failed`, `resonance`, `equilibrium`, `retro`. Arbitrary direction is allowed. `line` is also an object type.
- `electron_arrow`: four cubic Bezier `points` in start/control/control/end order; `electrons: 1` gives a fishhook, `2` a full head. These are editable graphic arrows, not inferred mechanistic correctness.
- `curve`: the same four Bezier points without an arrowhead.
- `symbol`: native ChemDraw electron/charge symbol, with native bounding coordinates `start` and `end`, optional `color`, and `symbol` chosen from `LonePair`, `Electron`, `RadicalCation`, `RadicalAnion`, `CirclePlus`, `CircleMinus`, `Dagger`, `DoubleDagger`, `Plus`, or `Minus`. Prefer these native objects to text dots or a drawn circle. They annotate the figure; a molecular formal charge must also be present in the grounded molecule graph. Symbol anchors vary with native type; inspect the native preview for placement, size and arrow clearance. For circled charges, follow the native save-cycle verification in [scientific workflows](scientific-workflows.md).
- `rectangle`, `ellipse`, `bracket`: upper-left `start`, lower-right `end`, optional `color`; bracket may include a `label` such as `n`. This is a **visual bracket**, not a machine-readable polymer SRU graph. Preserve a native polymer template when SRU semantics matter.

Place rich chemical conditions with explicit runs when typography matters:

```json
{"type":"text","position":[180,75],"runs":[
  {"text":"H"},{"text":"2","subscript":true},{"text":"O"}
]}
```

For a grid of compound structures, add `grid: {"columns":3,"cell_width":160,"row_height":140,"origin":[90,90]}`. Molecules without explicit positions are placed in cells. Choose larger cells for large structures/long labels and inspect reported overlap candidates.

### Reaction graph

`steps` is a list of objects with ID lists `reactants`, `products`, `arrows`, optional `above`, `below`. These write native `<scheme>/<step>` object references. Position and role are separate: preserve atom-contributing reactants even when the figure draws one above an arrow. Do not include unrelated annotations as reagents merely because they are nearby.

### Native template preservation

```json
{"version":1,"template_path":"original.cdxml"}
```

With no other changes this copies the exact original bytes to a new output. To move an existing object or change a nonchemical label:

```json
{"template_path":"original.cdxml","edits":[
  {"id":"123","translate":[10,0]},
  {"id":"456","text":"New caption"}
]}
```

IDs are actual native IDs. Edits support translation of whole fragments/groups/text/arrows/curves/graphics/brackets and replacement of non-atom annotation runs. Individual atom-label replacement is rejected because it could change chemistry. Editing currently requires a single-page template. No-op copying preserves multiple pages. Source molecules must remain present with their original semantics after edits. Opaque objects are preserved; unsupported source chemistry may prevent semantic verification of edited templates.

## Comparison and acceptance

`compare_figure_images(reference_path, candidate_path, output_path)` writes dimensions, exact pixel equality, normalized MAE and ink IoU. Different dimensions explicitly fail comparability; no implicit resampling occurs. Images must already be aligned. Transparent backgrounds are composited over white. These metrics do not establish chemical identity, text correctness or vector editability. No automatic threshold is a universal publication standard.

`component_overlap_candidates` is a conservative geometry warning, not full font-aware collision detection. Mechanistic arrows intentionally touching atoms should be reviewed in context. Native rendering and manual inspection remain mandatory for final acceptance.

## Immediate CLI fallback

If the host has not rediscovered the new tools, write a JSON keyword-arguments file and invoke:

```powershell
& <MCP-Python> -m cdxml_toolkit.mcp_runtime.figure_tools compose_chemical_figure --arguments <arguments.json>
```

The same entrypoint supports `rdkit_workbench` and `compare_figure_images`. This runs portable operations only; native rendering continues through the isolated, locked native MCP tools.

## Sources and limits

- [RDKit depiction](https://www.rdkit.org/docs/source/rdkit.Chem.rdDepictor.html): constrained depictions and wedging after coordinate changes.
- [RDKit CDXML support](https://www.rdkit.org/docs/cppapi/namespaceRDKit_1_1v2_1_1CDXMLParser.html): CDXML coverage is partial, not a full native-format implementation.
- [CDX SDK archive maintained by IUPAC FAIRSpec](https://iupac.github.io/IUPAC-FAIRSpec/cdx_sdk/TableOfProperties.htm): native curve, arrow, color and graphic properties.

Fresh generation currently rejects unvalidated radical, axial and non-tetrahedral stereochemical encodings. Native-template copies preserve such source bytes, but that is not new chemical validation. Fischer/Newman/Haworth/chair layouts can use verified coordinates/native templates; automatic general projection conversion is not implemented. No claim is made to implement every ChemDraw feature or reconstruct every raster figure automatically.

## Document validation receipt

`metadata.document_chemistry_validation` supplements per-fragment receipts. Composed output uses `status`, `method`, `scope`, `molecules` (including duplicate species), and `sha256` of the final file. `scope=rdkit_readback_consistency` compares the complete serialized inventory against template molecules plus grounded inputs before publication. An unchanged native-template copy instead reports `scope=unchanged_bytes` and `method=byte_identical_copy`; it does not claim reader validation. Native rendering and cross-reader stereochemical acceptance remain separate.
