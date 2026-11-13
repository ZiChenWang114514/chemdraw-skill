# Drawing a new reaction scheme

Use this when the structures are known and the figure does not exist yet: a reaction, a multi-step route, conditions and yields. For a figure to copy from an image, see [image reconstruction](image-visual-review.md).

## Which tool

| Need | Use |
| --- | --- |
| A molecule, structure grid, reaction, route, substrate-scope panel or mechanism from a request, drawn and checked in one call | `draw_figure` / `cdx.py draw` (next sections) |
| Reactants, reagents, products, conditions and yields laid out by hand-written compact text | `render_scheme` (below) |
| Exam or lecture drawing with abbreviations (C10H21), Chinese notes, boxed compound codes, hand-placed objects | [ACS 1996 drawings](acs1996-drawings.md), `cdx.py build` |
| Exact coordinates, hand-placed curved arrows, grids | [Figure manifest](publication-figures.md), `compose_chemical_figure` |
| Many compounds already in a CSV/XLSX table (scope, SAR), or an edit of such a figure | [Data-driven figures](data-driven-figures.md) |

## One call: draw_figure

For simple reactions or multi-step schemes without writing a JSON file, pass `--reaction` directly (repeatable for multi-step linear/convergent/divergent routes):

```bash
cdx.py draw --reaction "CC(=O)O.CCO>O=S(=O)(O)O>CCOC(C)=O" --below "rt, 2 h" --yield "85%" rxn.cdxml --render
cdx.py draw --compact scheme.dsl scheme.cdxml --render   # Compact Scheme DSL via render_scheme
```

For full styling (runs, highlights, boxes, atom colours, scope panels, mechanisms), turn the request into a brief, then run `cdx.py draw brief.json out.cdxml --render` (or `draw_figure(brief=..., output_path=..., render=true)`). You decide what the user asked for; the tool grounds the structures, checks the chemistry and the geometry, and reports what it verified. It draws one reaction, a linear route, a convergent route (arms that merge into one step) or one starting material with several products. A substrate-scope panel, a mechanism, and a standalone molecule or structure grid (kind: "molecule" / "structure_panel") each have their own brief, described after the report table below.

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
  - **Coordination/dative bonds (`Order="dative"`):** transition-metal complexes, borane-amine adducts, and Lewis acid-base pairs support native dative bonds (`Order="dative"` in CDXML) via RDKit dative SMILES (`->`, for example `[NH3]->[BH3]`) or explicit `dative_bonds: [[donor_atom_idx, acceptor_atom_idx], ...]` on a species record.
  - **Radicals:** open-shell radical species in SMILES (for example `[CH2]c1ccccc1`, `[O]C(C)(C)C`, or carbenes) preserve their radical state (`Radical="Doublet"`, `"Singlet"`, or `"Triplet"` on the CDXML `<n>` node) and pair with visible radical dot symbols and 1-electron fishhook arrows (`electrons: 1`).
- `steps` take `substrates`, `products`, `above` / `below` (text lines), `yield` and `arrow` (`solid`, `dashed`, `failed`, `reversible` for an equilibrium, `resonance` for a double-headed arrow). A product of one step may be the substrate of the next; list the steps in any order and the tool works out the route:
  - **Convergent branch-merge arrows (`layout: "convergent"`):** two synthesis arms that meet in one step can either be drawn with true Y-junction / T-junction convergent branch-merge arrows (upper and lower branch sequences merging into a vertical connector that feeds the shared coupling arrow) or as stacked rows with the merge row repeating the joined intermediates.
  - **Divergent routes (`layout: "divergent"`):** one substrate with several products is drawn once on the left, each product on its own row with a horizontal arrow, the arrows joined by a vertical line so every product reads as made from that substrate.
  - **Catalytic cycles (`layout: "catalytic-cycle"`):** when `"layout": "catalytic-cycle"` is set (or when the steps form a closed catalytic loop), intermediates are arranged around a circle of radius `cycle_radius` (default `120.0` pt) with curved arrows along the circumference and entering reactants / departing products placed on radial in/out arrows around each step.
  - Put in `above` / `below` only what the user gave: a step without conditions is drawn without them and the report says so.
- `max_width` is the row budget in points (default 504). A longer route wraps onto more rows.
- `style` is a journal preset from ChemDraw's stock style sheets (default `acs1996`; also `wiley`, `adv_synth_catal`, `rsc`, `rsc_1col`, `nature`, `synthesis` and others; `cdx.py styles` lists them, `cdx.py draw --style PRESET` sets it). The figure is laid out at ACS geometry and rescaled to the preset's bond length, fonts and line widths; `max_width` still applies to the styled figure, and the report's `style` field names the preset and bond length. Scope and mechanism briefs take the same key; `cdx.py build` specs take a top-level `style` too.
- `style` can also name a **house style**: how a journal, publisher or research group actually draws schemes, measured from openly licensed published figures. A measurement preset fixes only bond length, line widths and fonts; a house style names one of those presets as its base and adds drawing conventions. `cdx.py styles` lists both kinds (house styles in a second section with their kind, base preset and number of evidence figures), `cdx.py styles NAME` prints a card with its evidence, and `chemdraw://style-guide/{name}` returns it. The conventions a scheme takes:
  - `compound_label_face` (`bold` or `plain`) and `compound_label_color` for the compound numbers;
  - `yield_placement`: `under_arrow` (the default), `under_product_label` (a separate line under the product's number), `after_product_label` (`3, 85%` on the number's line, joined by `yield_separator`, default `", "`) or `after_product_label_parenthesised` (`3 (85%)`); `yield_format` is a template such as `"{value}% yield"`;
  - `substrate_layout`: `inline_plus` (A + B) or `stacked_plus` (A above B with the "+" between, centred on the arrow);
  - `abbreviate_groups`: groups drawn as abbreviation labels (CO2Me, CO2Et, OMe, OCF3, OAc, NO2, CN, Boc, NHBoc, Cbz, Ph, Bn, OBn, Bz, OBz, Piv, Ts, OTs, Ms, OMs, Tf, OTf, OTBS, OTMS, TMS, TIPS, OTIPS, Bpin, N3, NMe2, CF3, tBu, nBu, iPr, Et, Me, Ac, PhthN); they stay chemically complete, so the saved file reads back as the same molecule. A group on the left of its parent is placed correctly but desktop ChemDraw spells it right-flowing (CO2Me rather than MeO2C) until Clean Up Structure is run on the file; see the [style gallery](../assets/house-styles/gallery/README.md) and the per-style evidence folders beside it;
  - `new_bond_color`: bonds formed in the step, found by atom mapping; when the mapping is incomplete or ambiguous the bonds stay black and the report says so;
  - `substrate_colors`: the i-th substrate of a step drawn in the i-th colour; `highlight_fill`: a pastel fill behind the largest ring of the final product; `reagent_text_color`; `arrow_style` `bold`; `show_plus_sign`; `conditions_split` `all_above` or `all_below`.

  The card's `measured` ratios set the rest of the geometry after the base preset: bond line width and wedge width as fractions of the bond length, the atom-label size from the bond length over the capital-letter height, and the shortest reaction arrow in bond lengths (labels kept between 6 and 14 pt, arrows between 3 and 16 bonds). The report lists them as `measured.*` under `applied`.

  A null convention leaves today's drawing. The report's `style` gives `house`, `preset`, `applied` and `skipped` (with the reason); `compound_label_italic_suffix`, `aromatic_rings: "circle"` and `conditions_split: "reagents_above_solvent_below"` (the brief's own above/below split is kept) are not applied yet.

  A card may also carry `figure_types`: one section per kind of figure the journal or group draws (`reaction_scheme`, `substrate_scope`, `mechanism`, `catalytic_cycle`, `energy_profile`, `total_synthesis`, `retrosynthesis`, `structure_panel`, `sar_table`, `optimization_table`, `concept_panel`, `graphical_abstract`, `stereo_model`, `derivatization`, `biosynthesis`, `biomolecule`, `coordination_complex`, `polymer`, `markush`, `process_route`, `photophysical_diagram`, `assignment_panel`, `setup_diagram`), each with its own conventions, signature features and the evidence crops it was read from (`cdx.py styles NAME` prints them). The tools apply `mechanism.curved_arrow_color` and `mechanism.curved_arrow_weight` (`thin`, `bond` or `bold`, relative to the preset's bond width) to the curved arrows of a `kind: "mechanism"` brief, `catalytic_cycle.cycle_arrow_color` to the arrows of a catalytic-cycle layout, and `structure_panel.variation_color`, `structure_panel.highlight_fill` and `structure_panel.intermediate_label_style` to `kind: "molecule"` / `"structure_panel"` panels. The other figure-type conventions (lone pairs, circled charges, intermediate numbering, energy units, disconnection marks, SAR table rules and so on) are listed under `skipped` as guidance: follow them when finishing the figure by hand or with `cdx.py build`. A `kind: "scope"` panel takes the base preset, `compound_label_face`, `compound_label_color`, `abbreviate_groups` and the measured geometry; its species accept `color`, `atom_colors`, `bond_colors` and `abbreviate` as in a scheme, and the `substrate_scope` conventions are listed under `skipped` as guidance.

- The brief itself can style what a figure needs beyond the house style, with or without one:
  - a species' `color` paints the whole structure; `atom_colors` `[{"atoms": [0, 1], "color": "#0072B2"}]` paints atoms (a bond between two listed atoms too) and `bond_colors` `[{"bonds": [[7, 8]], "color": "#D55E00"}]` paints bonds, with atoms numbered from 0 in SMILES order;
  - a species' `abbreviate` lists the groups to contract in that structure; it replaces the house style's `abbreviate_groups` for it, and `[]` keeps it fully drawn;
  - a species' `orientation` (`flip_horizontal`, `flip_vertical` or `rotate_180`) mirrors or turns the structure about its centre; wedges and hashes are swapped on a mirror image, so the drawn compound keeps its configuration;
  - `title` and `panel_label` (`"a"`, `"(b)"`) are drawn above the figure at its left edge, the label in bold;
  - a species' `caption` is a line under its compound number (`"gram scale"`, `"98:2 er"`);
  - a species' `box` frames the structure and its number: `true` for a thin black frame, or `{"color": "#1F4E9E", "fill": "#EAF2FB", "style": "dashed", "rounded": true}`; the fill is drawn behind the structure;
  - a condition line in `above` or `below` may be a run `{"text": "Pd(OAc)2", "color": "#DC3220", "bold": true, "italic": false}` or a list of runs that make one line (`[{"text": "cat.", "italic": true}, {"text": " Pd(OAc)2"}]`); `title` and `caption` take the same forms.

  These are applied after the house style, so a colour the brief asks for wins over the card's; the report's `style.applied` lists them and `warnings` names any atom, bond or run that could not be found.

Read the report before you answer:

| Field | Meaning |
| --- | --- |
| `species[].source` | `user` for a SMILES you were given, otherwise the table that resolved the name |
| `steps[].balanced`, `missing` | atom and charge balance of each step; a missing by-product (for example acetic acid) is named, not drawn |
| `layout` | `linear`, `sequential`, `convergent`, `divergent` or `catalytic-cycle`: how the steps were arranged |
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

### Mechanism

`"kind": "mechanism"` draws the structures of a mechanism and one curved arrow for every electron move you list. You decide which electrons move; the tool places the structures, turns each move into an arrow from the drawn coordinates and checks the result. It never works out a mechanism: a step without `moves` is refused.

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

### Standalone molecules and structure grids

`"kind": "molecule"` (also `"structures"` or `"structure_panel"`) draws one molecule or a multi-row grid of structures without reaction arrows, using the same grounding, styling, abbreviations, boxes, captions, decorations, lint checks, read-back and optional native PNG rendering as schemes:

- From the CLI without writing a brief file: `cdx.py draw --name aspirin aspirin.cdxml --render`, or multiple entries such as `cdx.py draw --smiles "CCO" --name caffeine --number roman --properties --columns 2 --style sarpong_group panel.cdxml --render`.
- In a brief JSON: pass `"kind": "molecule"` (or `"structure_panel"`), `species` (`id` is optional and defaults to `s1`, `s2`, ... when omitted), optional `columns` (structures per row), `numbering` (`"arabic"`, `"roman"`, `"letter"`, `"plain_roman"`, `"int_number"`, etc., filling missing `label` values), `properties` (`true` for `"formula"` and `"mw"`, or a list from `["formula", "mw", "exact_mass"]` for species lacking a custom `caption`), `max_width`, `title`, `panel_label` and `style` (preset or house style). When the house style defines `structure_panel` conventions (`variation_color`, `highlight_fill`, `intermediate_label_style`), multi-structure panels highlight varied substituents against the shared core, tint ring interiors and auto-number unlabelled entries automatically.

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
- `run: "2.15 g" -> "1.60 g, 72% yield"` or `run[1]: 85%` adds per-run scale and yield annotations.
- Directives start with `@`: `@layout linear|sequential|stacked|divergent|convergent|stacked-rows|catalytic-cycle`, `@wrap repeat|serpentine|none`, `@steps_per_row N`, `@max_row_width PT`, `@title "..."`.

### Compact Scheme DSL (`compact_text` — "Mermaid for reaction schemes")

`compact_text` lets you write complete multi-step schemes, divergent routes, and catalytic cycles in a concise declarative syntax:

```text
@layout catalytic-cycle
Cat: {[Pd]} "Pd(0)"
Int1: {c1ccccc1[Pd]Br} "Ar-Pd-Br"
Int2: {c1ccccc1[Pd]c2ccccc2} "Ar-Pd-Ar'"
Cat -->|a| Int1
  above: "ArBr, oxidative addition"
Int1 -->|b| Int2
  above: "Ar'B(OH)2, base"
Int2 -->|c| Cat
  above: "reductive elimination"
  run[1]: 85%
```

### JACS / Angew publication styling & 3D conformers

When a scheme or figure requires top-journal visual highlights, transition states, organometallic hapticity, orbitals, or 3D conformer projections (via `draw_figure`, `build_acs_figure`, or `acs_builder.py`):

- **`ring_fills` & `atom_halos`:** pastel JACS/Angew ring-interior polygon shading (`ring_fills`) and circular pharmacophore atom highlights (`atom_halos`) placed on a background layer behind bonds and labels.
- **`multi_attachments` ($\eta^5$-Cp ferrocene & organometallics):** native CDXML `NodeType="MultiAttachment"` centroid nodes with `Attachments="..."` atom ID lists and coordination bonds (`Display="Dash"` or `"WedgeBegin"`).
- **`ts_bracket` (`[...]‡`):** square transition-state brackets (`BracketType="SquarePair"`) with a superscript double-dagger `‡` (`\u2021`) annotation. In a `draw_figure` brief, set `ts_bracket: true` (or `{superscript, bracket_type, lip_size}`) on the species, or `ts_bracket: "<species id>"` on a step; a step's `ts_bracket: true` is refused because it does not say which species is the transition state.
- **`orbital` & `interaction`:** native `<orbital>` lobes (`s`, `p`, `sp3`, `dz2`, `lobe`, shaded/filled/unfilled) and non-covalent H-bond / $\pi$-stacking dashed interaction lines with distance labels (`"2.8 Å"`).
- **Conformer templates (`chair`, `newman`, `haworth`, `fischer`, `norbornane`):** deterministic 2D coordinate generators for cyclohexane chairs (`1_ax`/`1_eq` through `6_ax`/`6_eq`, optional `flip`), Newman projections (`front`, `back`, `dihedral_deg`), Haworth pyranose/furanose rings, Fischer projections, and bridged bicyclic `[2.2.1]` norbornane skeletons.

A route stays on one row unless told otherwise. Set `@max_row_width 504` (points, the width of a two-column journal page) and the renderer picks the largest number of steps per row that fits; an explicit `@steps_per_row` always wins. In YAML the keys are `max_row_width` and `steps_per_row`.

Condition lines are tidied on every path: `80 C` becomes `80 °C`, `RT` and `room temperature` become `rt`, `12 hrs` becomes `12 h`, formula digits become subscripts and prefixes such as `n-` and `tert-` are italic. Text that is already correct is left alone.

## Checks

1. Read the per-fragment `chemistry_validation` in the result; anything other than `preserved` means a structure changed while drawing.
2. For a balanced-reaction check run `check_reaction_balance` on the same species; it names a missing by-product but never draws one.
3. Render with `cdx.py render FILE.cdxml` and look at the PNG for clipped labels, arrows running into structures and plus signs touching atoms.

Not available in `render_scheme`: curved arrows (use `draw_figure` with `kind: mechanism`). Neither tool chooses conditions for you. State only the conditions the user gave; a missing one stays missing.
