# Markush Public Symbols

> Generated from cdxml-toolkit 0.7.0a3. Curated guidance: [../markush.md](../markush.md).

## `markush.cdxml_writer`

- **function**, line 89: `auto_layout(graph: Graph, style = None) -> dict` - RDKit CoordGen coordinates for atoms the layout does not place.
- **function**, line 83: `default_style(style = None)` - No public docstring in the audited version.
- **function**, line 222: `to_points(layout: dict | None) -> dict` - Convert a ``"units": "px"`` layout (image pixels) to points with ``scale``/``offset``.
- **function**, line 238: `write_cdxml(graph: Graph, layout: dict | None = None) -> str` - No public docstring in the audited version.

## `markush.compile`

- **function**, line 50: `build_graph(spec) -> Graph` - No public docstring in the audited version.
- **function**, line 172: `check_cxsmiles(graph: Graph, cxsmiles: str) -> list[str]` - Parse the written CXSMILES back and compare labels and attachment sets.
- **function**, line 309: `compile_spec(spec) -> dict` - Spec -> {'cxsmiles', 'molblock', 'labels', 'checks'} plus the graph for writers.
- **function**, line 35: `cx_label(info: dict) -> str` - No public docstring in the audited version.
- **function**, line 203: `enumerate_members(spec, n: int = 5, seed: int = 0) -> dict` - Sample concrete molecules using definition ``values`` (``[*:1]`` fragments).
- **class**, line 25: `Graph` - No public docstring in the audited version.
- **class**, line 18: `SpecError` - No public docstring in the audited version.
- **function**, line 147: `to_cxsmiles(graph: Graph) -> str` - No public docstring in the audited version.
- **function**, line 193: `to_molblock(cxsmiles: str, coords: dict[int, tuple[float, float]] | None = None) -> str` - No public docstring in the audited version.

## `markush.draft_spec`

- **function**, line 33: `classify(text: str)` - ('element', symbol, h) | ('group', inner, count) | ('generic', label).
- **function**, line 70: `draft(graph: dict, texts: dict[str, str], bond_length_pt: float = 14.4) -> dict` - Return ``{"spec": ..., "layout": ..., "notes": [...], "missing": [...]}``.

## `markush.fidelity`

- **function**, line 31: `compare(reference, candidate, overlay_path = None, tolerance: int = 3, search: int = 12) -> dict` - No public docstring in the audited version.

## `markush.layout_detect`

- **function**, line 388: `detect(image_path, upscale: int | None = None) -> dict` - No public docstring in the audited version.
- **function**, line 572: `label_sheet(image_path, graph: dict, out_path, ids = None, pad: int = 6) -> str` - One enlarged crop per label box, captioned with its id, stacked vertically.
- **function**, line 545: `overlay(image_path, graph: dict, out_path, labels_only: bool = False) -> str` - Numbered marks for label boxes (T#) and vertices (v#) on the upscaled image.

## `markush.spec`

- **function**, line 20: `label_runs(label: str) -> list[tuple[str, str]]` - ``R^{A}`` -> [('R','normal'), ('A','sup')]; ``(R^{B})_{q}`` keeps parentheses.
- **function**, line 41: `load_spec(spec) -> dict` - No public docstring in the audited version.
- **function**, line 35: `plain_label(label: str) -> str` - Label text safe for CXSMILES ``$...$`` fields.
- **function**, line 56: `references(spec: dict) -> dict[str, str]` - Every addressable atom reference -> kind ('template', 'atom', 'ring').
- **function**, line 68: `validate_spec(spec) -> list[str]` - Return a list of actionable problems; empty means the spec compiles.

## `markush.templates`

- **function**, line 65: `locants(name: str) -> tuple[str, ...]` - No public docstring in the audited version.
- **function**, line 50: `template_mol(name: str) -> Chem.Mol` - Kekulized template with 2D coordinates; atom i has locant ``locants[i]``.
- **function**, line 45: `template_names() -> list[str]` - No public docstring in the audited version.

## `markush.text_defs`

- **function**, line 17: `load_text(path) -> str` - No public docstring in the audited version.
- **function**, line 47: `locate(text: str, names, counts = None, rings = ()) -> dict[str, str]` - ``{name: passage}`` for every variable whose definition appears in the text.

## `markush.workflow`

- **function**, line 73: `init(workdir, image, text = None, crop = None, reuse = None) -> dict` - No public docstring in the audited version.
- **function**, line 125: `next_task(workdir, renderer: Renderer | None = None) -> dict` - No public docstring in the audited version.
- **function**, line 57: `parse_answer(text: str)` - Answers may arrive wrapped in a ```json fence or with prose around them.
- **function**, line 103: `status(workdir) -> dict` - No public docstring in the audited version.
- **function**, line 262: `submit(workdir, task, answer, renderer: Renderer | None = None, _state = None) -> dict` - No public docstring in the audited version.
