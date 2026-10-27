# Drawing a new reaction scheme

Use this when the structures are known and the figure does not exist yet: a reaction, a multi-step route, conditions and yields. For a figure to copy from an image, see [image reconstruction](image-visual-review.md).

## Which tool

| Need | Use |
| --- | --- |
| A reaction, route or substrate-scope panel from a request, drawn and checked in one call | `draw_figure` / `cdx.py draw` (next sections) |
| Reactants, reagents, products, conditions and yields laid out by hand-written compact text | `render_scheme` (below) |
| Exam or lecture drawing with abbreviations (C10H21), Chinese notes, boxed compound codes, hand-placed objects | [ACS 1996 drawings](acs1996-drawings.md), `cdx.py build` |
| Exact coordinates, curved arrows, grids, equilibrium arrows | [Figure manifest](publication-figures.md), `compose_chemical_figure` |
| Many compounds already in a CSV/XLSX table (scope, SAR), or an edit of such a figure | [Data-driven figures](data-driven-figures.md) |

## One call: draw_figure

Turn the request into a brief, then run `cdx.py draw brief.json out.cdxml --render` (or `draw_figure(brief=..., output_path=..., render=true)`). You decide what the user asked for; the tool grounds the structures, checks the chemistry and the geometry, and reports what it verified. It draws one reaction, a linear route, a convergent route (arms that merge into one step) or one starting material with several products. Mechanisms are not available yet and are refused, not approximated. A substrate-scope panel has its own brief, described after the report table below.

```json
{
  "species": [
    {"id": "SA", "smiles": "OC(=O)c1ccccc1O", "label": "1"},
    {"id": "Ac2O", "name": "Ac2O"},
    {"id": "ASP", "smiles": "CC(=O)Oc1ccccc1C(=O)O", "label": "2"}
  ],
  "steps": [
    {"substrates": ["SA", "Ac2O"], "products": ["ASP"],
     "above": ["H2SO4 (cat.)"], "below": ["rt, 2 h"], "yield": "85%"}
  ],
  "max_width": 504
}
```

- `species` lists every structure with an `id` and either `smiles` (used as given) or `name` (curated reagent table, then PubChem unless `CHEMDRAW_OFFLINE=1`). A name that cannot be resolved stops the run and nothing is written; give a SMILES instead. Do not guess a SMILES to get past this.
- `steps` take `substrates`, `products`, `above` / `below` (text lines), `yield` and `arrow` (`solid`, `dashed`, `failed`, `reversible` for an equilibrium, `resonance` for a double-headed arrow). A product of one step may be the substrate of the next; list the steps in any order and the tool works out the route. Two arms that meet in one step are drawn as stacked rows, the merge row repeating the intermediates it joins; one substrate with several products branches down from the first reaction. Steps that are none of these (a species made twice, a cycle, unrelated reactions) are refused. Put in `above` / `below` only what the user gave: a step without conditions is drawn without them and the report says so.
- `max_width` is the row budget in points (default 504). A longer route wraps onto more rows.

Read the report before you answer:

| Field | Meaning |
| --- | --- |
| `species[].source` | `user` for a SMILES you were given, otherwise the table that resolved the name |
| `steps[].balanced`, `missing` | atom and charge balance of each step; a missing by-product (for example acetic acid) is named, not drawn |
| `layout` | `linear`, `sequential`, `convergent` or `divergent`: how the steps were arranged |
| `lint` | overlaps, text under 6 pt, drawing wider than `max_width`; `lint.relayout` appears when a failed check triggered the one automatic re-layout, with what changed and the original problems |
| `readback` | the saved file's structures compared with the brief (`matched` or `mismatch`) |
| `native` | `rendered` with `png_path`, or `not_run` with the reason; `not_run` means unrendered draft |
| `notes`, `warnings` | steps without conditions, unused species, balance and layout problems that remain |

`ok` means a file was written; `checks_passed` means the layout and readback checks both passed. Open the PNG and look at it even then. The output is never written over an existing file: without an output path a fresh name is made in the temp folder.

### Substrate-scope panel

`"kind": "scope"` draws many compounds with their labels and the numbers the user gave, packed onto as many editable pages as needed:

```json
{
  "kind": "scope",
  "title": "Substrate scope",
  "conditions": "As supplied by the user",
  "footnotes": ["a Isolated yield."],
  "fields": [{"key": "yield", "label": "Yield"}, {"key": "ee", "label": "ee"}],
  "species": [
    {"id": "3a", "smiles": "Cc1ccc(cc1)C(=O)N", "label": "3a", "group": "para", "values": {"yield": "88%", "ee": "95%"}},
    {"id": "3b", "name": "benzamide", "label": "3b", "values": {"yield": "91%"}}
  ]
}
```

- `fields` is optional; without it the keys used in `values` become the columns, in first-seen order. A `unit` is added after the value, so do not repeat it in the text.
- `group` makes a heading; groups and compounds keep first-seen order. A value you were not given is left out: the panel shows a dash, never zero, and the report names the compound.
- `width_mm` and `height_mm` set the page (default 180 x 240 mm); more compounds continue on further pages, labels and values staying with their structure.
- `output` is a new folder: `page-001.cdxml`, ... and, with `--render`, `png/page-001.png`, ... The report lists `pages`, `native.png_paths`, and the same `species`, `lint`, `readback`, `checks_passed`, `notes` and `warnings` as above, plus `checks.data_binding` (each label and value found next to its structure). Pages are packed from measured sizes, so there is no automatic re-layout.
- To change a panel after the user edits it in ChemDraw, use `publication_figure update` ([data-driven figures](data-driven-figures.md)).

## render_scheme

Pass exactly one of `compact_text`, `yaml_text` or `json_path` (a `parse_reaction` result). Ground every structure first: give a SMILES from the user, a resolver or a parser. A structure given only as `name "..."` is looked up in the curated reagent table (common reagents, solvents and abbreviations); there is no PubChem or IUPAC lookup on this path, and an unknown name stops with an error asking for a SMILES.

Compact text, one scheme in a few lines:

```
"1"{OC(=O)c1ccccc1O} + Ac2O{CC(=O)OC(C)=O} --> "2"{CC(=O)Oc1ccccc1C(=O)O} (85%)
  above: "H2SO4 (cat.)"
  below: "rt, 2 h"
```

- `ID{SMILES}` defines a structure inline; a quoted ID such as `"1"` also becomes its compound label below the structure.
- `-->` is a solid arrow, `..>` a dashed one, `<=>` an equilibrium arrow, `<->` a resonance arrow, `X>` a failed one. `A --> B --> C` makes two steps and draws the shared intermediate once.
- `(85%)` after the last product is the yield, printed under the arrow.
- `above:` and `below:` take quoted text lines or bare structure IDs (drawn as structures). For several steps use `step 1:`, `step 2:` blocks, or `-->|a|` with an `@conditions` block of lettered conditions.
- `run: "2.15 g" -> "1.60 g, 72% yield"` adds a mass-in to mass-out arrow.
- Directives start with `@`: `@layout sequential|divergent|convergent|stacked-rows`, `@wrap repeat|serpentine|none`, `@steps_per_row N`, `@max_row_width PT`, `@title "..."`.

A route stays on one row unless told otherwise. Set `@max_row_width 504` (points, the width of a two-column journal page) and the renderer picks the largest number of steps per row that fits; an explicit `@steps_per_row` always wins. In YAML the keys are `max_row_width` and `steps_per_row`.

Condition lines are tidied on every path: `80 C` becomes `80 °C`, `RT` and `room temperature` become `rt`, `12 hrs` becomes `12 h`, formula digits become subscripts and prefixes such as `n-` and `tert-` are italic. Text that is already correct is left alone.

## Checks

1. Read the per-fragment `chemistry_validation` in the result; anything other than `preserved` means a structure changed while drawing.
2. For a balanced-reaction check run `check_reaction_balance` on the same species; it names a missing by-product but never draws one.
3. Render with `cdx.py render FILE.cdxml` and look at the PNG for clipped labels, arrows running into structures and plus signs touching atoms.

Not available in `render_scheme` or `draw_figure`: curved arrows and conditions chosen for you. State only the conditions the user gave; a missing one stays missing.
