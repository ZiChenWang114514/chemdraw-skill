# Native laboratory drawings

Use ChemDraw's native representations for TLC, laboratory apparatus and instruments. TLC uses `tlcplate`, `tlclane` and `tlcspot`; equipment uses editable objects copied from installed ChemDraw templates. Retain template curves, groups, colors and object references. Do not silently replace equipment with generated bitmap images or approximate outlines.

These commands require the toolkit's `cdxml_toolkit.scientific` module. Native conversion and preview also require an activated ChemDraw installation. If the module is unavailable, update the toolkit before attempting the workflow.

## Apparatus and instruments

1. Inspect the requested arrangement and list the components and joints.
2. Locate the installed ChemDraw Items directory. Depending on the installation, it may be under the vendor's ProgramData directory. Locate Clipware `.ctp` files or a user-provided native template; preserve the original files. Do not assume a template's page numbers are identical across installations.
3. Copy each required binary CTP to a new working `.cdx` file and convert that copy to CDXML using the existing native conversion tool. Use the generated signatures reference for the exact MCP call. Do not start a separate, unlocked COM process.
4. Inspect the converted template pages and their native previews. Use `template_catalog` below to obtain zero-based page indexes and source hashes. Select the actual equipment artwork, including flask, condenser, funnel, stand, clamp or other available instrument. If the requested component is absent, report that gap or use a user-supplied native template; do not claim a generic replacement is a built-in instrument.
5. Assemble a JSON specification, preserving aspect ratio. Attach components through normalized ports. Place supporting components behind the glassware by listing them first. Port attachment describes drawing geometry, not an engineering compatibility assessment.
6. Render the saved CDXML in native ChemDraw and actually inspect joints, overlap, hoses, clamp positions, missing lines and labels. Deliver the editable CDXML and preview together.

Catalog a converted library:

```python
from cdxml_toolkit.scientific.apparatus import template_catalog
catalog = template_catalog("templates/glassware.cdxml")
print(catalog)
```

Minimal assembly specification (page indexes must come from the inspected library):

```json
{
  "title": "Laboratory apparatus",
  "width": 600,
  "height": 600,
  "template_files": {"glassware": "templates/glassware.cdxml"},
  "components": [
    {"id": "flask", "template": "glassware", "page": 14,
     "position": [220, 270], "scale": 1.0,
     "ports": {"neck": [0.49, 0.025]},
     "label": "Round-bottom flask"}
  ]
}
```

`position` places the upper-left of the template bounds in CDXML points. Ports are fractions of those bounds. To attach a later component, give it a local port and `"attach": {"port": "bottom", "to": "flask.neck"}`. Inspect both port positions in the source artwork before using them. Optional connections have `from`, `to` and intermediate `via` points.

```console
python -m cdxml_toolkit.scientific apparatus --spec apparatus.json --output apparatus.cdxml
```

Template paths are relative to the specification. Use a new output path. The returned receipt records source hashes, selected pages and copied object counts. Keep proprietary template libraries on the licensed host; do not bundle the complete libraries with a public demo. Share the assembly recipe and the resulting drawing as appropriate.

## TLC

```console
python -m cdxml_toolkit.scientific tlc --spec tlc.json --output tlc.cdxml
```

Use measured or explicitly illustrative Rf values. Do not infer purity from spot intensity. For image measurement, calibrate the origin and solvent front along the same development axis, then project each spot onto that axis. Preserve lane order and distinguish co-spots from separate samples.

Verify the saved XML contains native plate, lane and spot objects, and inspect the native preview. TLC spot dimensions use raw 16.16 coordinate values in CDXML; the helper converts point dimensions to this representation. Do not replace native spots with generic ellipses to work around serialization errors.
