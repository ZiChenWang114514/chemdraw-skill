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

<!-- example: commands -->
```bash
cdx.py draw --reaction "CC(=O)O.CCO>O=S(=O)(O)O>CCOC(C)=O" --below "rt, 2 h" --yield "85%" rxn.cdxml --render
cdx.py draw --compact scheme.dsl scheme.cdxml --render   # Compact Scheme DSL via render_scheme
```

For full styling (runs, highlights, boxes, atom colours, scope panels, mechanisms), turn the request into a brief, then run `cdx.py draw brief.json out.cdxml --render` (or `draw_figure(brief=..., output_path=..., render=true)`). You decide what the user asked for; the tool grounds the structures, checks the chemistry and the geometry, and reports what it verified. It draws one reaction, a linear route, a convergent route (arms that merge into one step) or one starting material with several products. A substrate-scope panel, a mechanism, and a standalone molecule or structure grid (kind: "molecule" / "structure_panel") each have their own brief, described after the report table below.

<!-- example: call draw_figure arg=brief output_path=scheme.cdxml -->
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
  - **Catalytic cycles (`layout: "catalytic-cycle"`):** when `"layout": "catalytic-cycle"` is set (or when the steps form a closed catalytic loop), intermediates are arranged around a circle whose radius grows with the number of steps until the structures no longer overlap (there is no radius option), each step is a straight arrow along the chord between consecutive intermediates, and its `above` / `below` text is placed radially outside / inside that arrow.
  - Put in `above` / `below` only what the user gave: a step without conditions is drawn without them and the report says so.
- `max_width` is the row budget in points (default 504). A longer route wraps onto more rows.
- `style` names a journal preset (default `acs1996`) or a house style, and a species can carry its own colour, abbreviations, orientation, caption and box: see [figure styles](figure-styles.md).


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

### Other kinds of figure

`"kind": "scope"` (substrate-scope panel), `"kind": "mechanism"` (curved arrows for the electron moves you list) and `"kind": "molecule"` (one structure or a grid, no arrows) take the same call: see [scope panels, mechanisms and structure grids](scope-mechanism-figures.md).

## render_scheme

Pass exactly one of `compact_text`, `yaml_text` or `json_path` (a `parse_reaction` result). Ground every structure first: give a SMILES from the user, a resolver or a parser. A structure given only as `name "..."` is looked up in the curated reagent table (common reagents, solvents and abbreviations); there is no PubChem or IUPAC lookup on this path, and an unknown name stops with an error asking for a SMILES.

Compact text, one scheme in a few lines:

<!-- example: call render_scheme arg=compact_text output_path=compact.cdxml -->
```
"1"{OC(=O)c1ccccc1O} + Ac2O{CC(=O)OC(C)=O} --> "2"{CC(=O)Oc1ccccc1C(=O)O} (85%)
  above: "H2SO4 (cat.)"
  below: "rt, 2 h"
```

- `ID{SMILES}` defines a structure inline; a quoted ID such as `"1"` also becomes its compound label below the structure.
- `-->` is a solid arrow, `..>` a dashed one, `<=>` an equilibrium arrow, `<->` a resonance arrow, `X>` a failed one. `A --> B --> C` makes two steps and draws the shared intermediate once.
- `(85%)` after the last product is the yield, printed under the arrow.
- `above:` and `below:` take quoted text lines or bare structure IDs (drawn as structures). For several steps use `step 1:`, `step 2:` blocks, or `-->|a|` with an `@conditions` block of lettered conditions.
- `run: "2.15 g" -> "1.60 g, 72% yield"` (or `run[1]: ...` for step 1) adds per-run scale and yield annotations; each run line needs exactly one `->`.
- Directives start with `@`: `@layout linear|sequential|divergent|convergent|stacked-rows|numbered-parallel`, `@wrap repeat|serpentine|none`, `@steps_per_row N`, `@max_row_width PT`, `@title "..."`.

### Compact Scheme DSL (`compact_text` — "Mermaid for reaction schemes")

`compact_text` lets you write complete multi-step schemes and divergent routes in a concise declarative syntax. A label is written `label "..."` after the SMILES, and a scheme has one reaction chain line. Catalytic cycles are not a `render_scheme` layout; draw them with `draw_figure` and `"layout": "catalytic-cycle"` (see above).

<!-- example: call render_scheme arg=compact_text output_path=route.cdxml -->
```text
@layout sequential
SA: {OC(=O)c1ccccc1O} label "1"
ASP: {CC(=O)Oc1ccccc1C(=O)O} label "2"
AMD: {CC(=O)Oc1ccccc1C(=O)N} label "3"
SA -->|a| ASP -->|b| AMD
  run[1]: "2.15 g" -> "1.60 g, 85%"
@conditions
(a) "Ac2O, H2SO4 (cat.), rt, 2 h"
(b) "SOCl2, then NH3"
```

### JACS / Angew publication styling & 3D conformers

When a scheme or figure requires top-journal visual highlights, transition states, organometallic hapticity, orbitals, or 3D conformer projections (via `draw_figure`, `build_acs_figure`, or `acs_builder.py`):

- **`ring_fills` & `atom_halos`:** pastel JACS/Angew ring-interior polygon shading (`ring_fills`) and circular pharmacophore atom highlights (`atom_halos`) placed on a background layer behind bonds and labels.
- **`multi_attachments` ($\eta^5$-Cp ferrocene & organometallics):** native CDXML `NodeType="MultiAttachment"` centroid nodes with `Attachments="..."` atom ID lists and coordination bonds (`Display="Dash"` or `"WedgeBegin"`).
- **`ts_bracket` (`[...]‡`):** square transition-state brackets (`BracketType="SquarePair"`) with a superscript double-dagger `‡` (`\u2021`) annotation. In a `draw_figure` brief, set `ts_bracket: true` (or `{superscript, bracket_type, lip_size}`) on the species, or `ts_bracket: "<species id>"` on a step; a step's `ts_bracket: true` is refused because it does not say which species is the transition state.
- **`orbital` & `interaction`:** native `<orbital>` lobes (`s`, `p`, `sp3`, `dz2`, `lobe`, shaded/filled/unfilled) and non-covalent H-bond / $\pi$-stacking dashed interaction lines with distance labels (`"2.8 Å"`).
- **Conformer templates (`chair`, `newman`, `haworth`, `fischer`, `norbornane`):** deterministic 2D coordinate generators for cyclohexane chairs (`substituents` keyed by ring position 1-6, each `{"ax": label, "eq": label}`, for example `{"1": {"eq": "OH"}, "4": {"ax": "Me"}}`; optional `flip`), Newman projections (`front`, `back`, `dihedral_deg`), Haworth pyranose/furanose rings, Fischer projections, and bridged bicyclic `[2.2.1]` norbornane skeletons.

A route stays on one row unless told otherwise. Set `@max_row_width 504` (points, the width of a two-column journal page) and the renderer picks the largest number of steps per row that fits; an explicit `@steps_per_row` always wins. In YAML the keys are `max_row_width` and `steps_per_row`.

Condition lines are tidied on every path: `80 C` becomes `80 °C`, `RT` and `room temperature` become `rt`, `12 hrs` becomes `12 h`, formula digits become subscripts and prefixes such as `n-` and `tert-` are italic. Text that is already correct is left alone.

## Checks

1. Read the per-fragment `chemistry_validation` in the result; anything other than `preserved` means a structure changed while drawing.
2. For a balanced-reaction check run `check_reaction_balance` on the same species; it names a missing by-product but never draws one.
3. Render with `cdx.py render FILE.cdxml` and look at the PNG for clipped labels, arrows running into structures and plus signs touching atoms.

Not available in `render_scheme`: curved arrows (use `draw_figure` with `kind: mechanism`). Neither tool chooses conditions for you. State only the conditions the user gave; a missing one stays missing.
