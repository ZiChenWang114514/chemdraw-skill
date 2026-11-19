# Scope Panels, Mechanisms and Structure Grids

The other kinds of `draw_figure` brief. They share the species, styling, checks and report of a reaction brief, described in [scheme drawing](scheme-drawing.md) and [figure styles](figure-styles.md).

## Substrate-scope panel

`"kind": "scope"` draws many compounds with their labels and the numbers the user gave, packed onto as many editable pages as needed:

<!-- example: call draw_figure arg=brief output_path=scope.cdxml -->
```json
{
  "kind": "scope",
  "title": "Substrate scope",
  "conditions": "As supplied by the user",
  "footnotes": ["a Isolated yield."],
  "fields": [{"key": "yield", "label": "Yield"}, {"key": "ee", "label": "ee"}],
  "species": [
    {"id": "3a", "smiles": "Cc1ccc(cc1)C(=O)N", "label": "3a", "group": "para", "values": {"yield": "88%", "ee": "95%"}},
    {"id": "3b", "name": "benzamide", "smiles": "NC(=O)c1ccccc1", "label": "3b", "values": {"yield": "91%"}}
  ]
}
```

- A species may give a `name`, a `smiles` or both; when both are given and the name resolves, they must describe the same structure.

- `fields` is optional; without it the keys used in `values` become the columns, in first-seen order. A `unit` is added after the value, so do not repeat it in the text.
- `group` makes a heading; groups and compounds keep first-seen order. A value you were not given is left out: the panel shows a dash, never zero, and the report names the compound.
- `width_mm` and `height_mm` set the page (default 180 x 240 mm); more compounds continue on further pages, labels and values staying with their structure.
- `output` is a new folder: `page-001.cdxml`, ... and, with `--render`, `png/page-001.png`, ... The report lists `pages`, `native.png_paths`, and the same `species`, `lint`, `readback`, `checks_passed`, `notes` and `warnings` as above, plus `checks.data_binding` (each label and value found next to its structure). Pages are packed from measured sizes, so there is no automatic re-layout.
- To change a panel after the user edits it in ChemDraw, use `publication_figure update` ([data-driven figures](data-driven-figures.md)).

## Mechanism

`"kind": "mechanism"` draws the structures of a mechanism and one curved arrow for every electron move you list. You decide which electrons move; the tool places the structures, turns each move into an arrow from the drawn coordinates and checks the result. It never works out a mechanism: a step without `moves` is refused.

<!-- example: call draw_figure arg=brief output_path=mechanism.cdxml -->
```json
{
  "kind": "mechanism",
  "species": [
    {"id": "ald", "smiles": "CC=O", "label": "1"},
    {"id": "hyd", "smiles": "[OH-]"},
    {"id": "alk", "smiles": "CC([O-])O", "label": "2"}
  ],
  "steps": [
    {"substrates": ["ald", "hyd"], "products": ["alk"], "above": ["H2O"],
     "moves": [
       {"from": {"species": "hyd", "atom": 0}, "to": {"species": "ald", "atom": 1}},
       {"from": {"species": "ald", "bond": [1, 2]}, "to": {"species": "ald", "atom": 2}}
     ]}
  ]
}
```

- Steps are drawn in the order given. A step with one substrate and one product continues the same row, the intermediate drawn once; any other step starts a new row and draws its substrates again (the report notes it). A row that would pass `max_width` wraps the same way.
- A move goes `from` / `to` an `atom` (a lone pair, a charge, a radical) or a `bond` `[i, j]` (a pi or sigma bond), in species that are substrates of that step. `electrons` is 2 (full head, the default) or 1 (half head). The step `arrow` may be `solid`, `reversible` or `resonance`; `above`, `below` and `yield` work as in schemes.
- Atoms are numbered from 0 in the order of the SMILES you gave, hydrogens not counted. The report lists them per species (`species[].atoms`, for example `0 C, 1 C, 2 O`). Set `show_atom_numbers: true` to print them on a draft and check the moves by eye, then draw again without it.
- The report adds `moves` (what each arrow connects and its `checks`) and `arrows` (`crossings`, the atoms an arrow runs through, and `relayout` when one automatic retry changed the gaps and loop height). A two-electron arrow that starts on an atom with no lone pair or negative charge is drawn and flagged in `moves[].checks` and `warnings`; atom and charge balance is checked per step as for schemes.
- Limits: arrows are drawn as given; the tool does not judge whether the mechanism is chemically right. A long arrow can still run close to a label, so open the PNG.

## Standalone molecules and structure grids

`"kind": "molecule"` (also `"structures"` or `"structure_panel"`) draws one molecule or a multi-row grid of structures without reaction arrows, using the same grounding, styling, abbreviations, boxes, captions, decorations, lint checks, read-back and optional native PNG rendering as schemes:

- From the CLI without writing a brief file: `cdx.py draw --name aspirin aspirin.cdxml --render`, or multiple entries such as `cdx.py draw --smiles "CCO" --name caffeine --number roman --properties --columns 2 --style sarpong_group panel.cdxml --render`.
- In a brief JSON: pass `"kind": "molecule"` (or `"structure_panel"`), `species` (`id` is optional and defaults to `s1`, `s2`, ... when omitted), optional `columns` (structures per row), `numbering` (`"arabic"`, `"roman"`, `"letter"`, `"plain_roman"`, `"int_number"`, etc., filling missing `label` values), `properties` (`true` for `"formula"` and `"mw"`, or a list from `["formula", "mw", "exact_mass"]` for species lacking a custom `caption`), `max_width`, `title`, `panel_label` and `style` (preset or house style). When the house style defines `structure_panel` conventions (`variation_color`, `highlight_fill`, `intermediate_label_style`), multi-structure panels highlight varied substituents against the shared core, tint ring interiors and auto-number unlabelled entries automatically.
