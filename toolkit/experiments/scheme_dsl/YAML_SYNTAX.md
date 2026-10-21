# Scheme YAML Syntax Reference

The YAML format is the primary input for `cdxml-render`. It describes a reaction scheme declaratively: you specify structures (as SMILES), reaction steps, conditions, and layout — the renderer handles all spatial positioning.

## Minimal Example

```yaml
structures:
  ArBr:
    smiles: "Brc1ncnc2sccc12"
  Morph:
    smiles: "C1COCCN1"
  Product:
    smiles: "c1nc(N2CCOCC2)c2ccsc2n1"

steps:
  - substrates: [ArBr]
    products: [Product]
    above_arrow:
      structures: [Morph]
    below_arrow:
      text:
        - "Pd2(dba)3 (0.05 eq.)"
        - "rac-BINAP (0.1 eq.)"
        - "Cs2CO3 (2 eq.)"
        - "Dioxane, 105 °C, 24 h"
```

This produces a single-step Buchwald coupling with morpholine drawn above the arrow and catalyst/conditions text below.

## Top-Level Keys

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `structures` | dict | `{}` | Structure definitions (keyed by ID) |
| `steps` | list | `[]` | Reaction steps (required unless using `sections`) |
| `layout` | string | `"linear"` | Layout pattern (see below) |
| `wrap` | string | `"repeat"` | Wrapping mode for multi-row schemes |
| `steps_per_row` | integer | auto | Steps per row before wrapping |
| `run_arrows` | list | `[]` | Scale arrows (mass in → mass out) |
| `condition_key` | dict | `null` | Letter → condition text mapping |
| `sections` | list | `[]` | Independent row sections (for `stacked-rows` layout) |
| `source` | string | `null` | Path to `reaction_parser` JSON for structure resolution |

## Structure Definitions

Each entry in `structures` maps an ID to a structure reference.

**Full form:**
```yaml
structures:
  ArBr:
    smiles: "Brc1ncnc2sccc12"
    label: "1"                    # compound number below structure
    name: "4-bromothienopyrimidine"  # for name resolution (optional)
    file: "structures/ArBr.cdxml"    # load from file (optional)
```

**Shorthand** (SMILES only):
```yaml
structures:
  ArBr: "Brc1ncnc2sccc12"
```

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `smiles` | string | SMILES string for the structure |
| `name` | string | Compound name (resolved via reagent database or PubChem) |
| `file` | string | Path to a CDXML file containing the structure |
| `label` | string | Compound number displayed below the structure (e.g. `"1"`, `"2a"`) |
| `cdxml_id` | integer | Fragment ID in an existing CDXML (internal use) |

Resolution priority: `smiles` > `name` > `file`. If none are provided, the renderer tries to look up the ID in the reagent database.

## Steps

Each step represents one reaction transformation.

```yaml
steps:
  - substrates: [ArBr, Morph]
    products: [Product]
    above_arrow:
      structures: [catalyst]
      text: ["0.5 mol%"]
    below_arrow:
      text:
        - "Cs2CO3 (2 eq.)"
        - "Dioxane, 110 °C, 24 h"
    yield_: "72%"
    arrow_style: "solid"
```

### Step Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `substrates` | list or string | (required) | Structure ID(s) left of arrow |
| `products` | list or string | (required) | Structure ID(s) right of arrow |
| `above_arrow` | dict | `null` | Content above the arrow |
| `below_arrow` | dict | `null` | Content below the arrow |
| `yield_` | string | `null` | Yield annotation (e.g. `"72%"`) |
| `arrow_style` | string | `"solid"` | Arrow style: `"solid"`, `"dashed"`, or `"failed"` |

### Arrow Content (`above_arrow` / `below_arrow`)

| Field | Type | Description |
|-------|------|-------------|
| `structures` | list or string | Structure IDs to draw as structures above/below the arrow |
| `text` | list or string | Condition text lines (reagents, temperature, time) |

## Arrow Styles

| Style | Description |
|-------|-------------|
| `solid` | Normal reaction arrow (default) |
| `dashed` | Dashed arrow (equilibrium, reversible, or tentative) |
| `failed` | Arrow with X overlay (reaction did not work) |

```yaml
steps:
  - substrates: [SM]
    products: [Product]
    arrow_style: "failed"
    below_arrow:
      text: ["conditions that didn't work"]
```

## Layout Patterns

Set with `layout:` at the top level.

| Layout | Description |
|--------|-------------|
| `linear` | Single-step reaction (default) |
| `sequential` | Multi-step chain — shared intermediates drawn once |
| `divergent` | One substrate → multiple products (fan-out) |
| `stacked-rows` | Independent rows stacked vertically |
| `serpentine` | Zigzag rows (use `wrap: serpentine` with `sequential`) |

### Sequential (Multi-Step)

```yaml
layout: sequential

structures:
  SM: { smiles: "Fc1ccnc2cc(NC(=O)OC(C)(C)C)ccc12" }
  Int: { smiles: "C1CCN(c2ccnc3cc(NC(=O)OC(C)(C)C)ccc23)CC1" }
  Product: { smiles: "C1CCN(c2ccnc3cc(N)ccc23)CC1" }

steps:
  - substrates: [SM]
    products: [Int]
    below_arrow:
      text: ["piperidine (3.0 eq)", "DIPEA (3.0 eq)", "NMP, 120 °C, 16 h"]
    yield_: "82%"

  - substrates: [Int]
    products: [Product]
    below_arrow:
      text: ["TFA/DCM (1:1)", "RT, 1 h"]
    yield_: "quant."
```

The intermediate is drawn once between the two arrows.

### Wrapping

For long sequences (3+ steps), control row wrapping:

```yaml
layout: sequential
wrap: repeat          # "repeat", "serpentine", or "none"
steps_per_row: 3      # auto-computed if omitted
```

| Wrap | Description |
|------|-------------|
| `repeat` | All rows go left → right. Structures at row boundaries are repeated. |
| `serpentine` | Rows alternate direction (L→R, R→L, L→R...) with vertical connecting arrows. |
| `none` | All steps in a single row (no wrapping). |

### Divergent (SAR / Multiple Products)

```yaml
layout: divergent

structures:
  SM: { smiles: "Brc1ccc2ccccc2n1", label: "1" }
  ProdA: { smiles: "c1ccc2nc(N3CCOCC3)ccc2c1", label: "2a" }
  ProdB: { smiles: "c1ccc2nc(N3CCCCC3)ccc2c1", label: "2b" }
  ProdC: { smiles: "c1ccc(Nc2ccc3ccccc3n2)cc1", label: "2c" }

steps:
  - substrates: [SM]
    products: [ProdA]
    below_arrow:
      text: ["morpholine (1.2 eq)", "Pd2(dba)3, BINAP", "Cs2CO3, dioxane", "reflux, 24 h, 72%"]

  - substrates: [SM]
    products: [ProdB]
    below_arrow:
      text: ["piperidine (1.2 eq)", "Pd2(dba)3, BINAP", "Cs2CO3, dioxane", "reflux, 24 h, 65%"]

  - substrates: [SM]
    products: [ProdC]
    arrow_style: failed
    below_arrow:
      text: ["aniline (1.2 eq)", "Pd2(dba)3, BINAP", "Cs2CO3, dioxane", "reflux, 24 h"]
```

The starting material is drawn once; arrows fan out to each product.

### Stacked Rows

```yaml
layout: stacked-rows

sections:
  - label: "(i)"
    steps:
      - substrates: [A]
        products: [B]
        below_arrow:
          text: ["conditions 1"]

  - label: "(ii)"
    steps:
      - substrates: [C]
        products: [D]
        below_arrow:
          text: ["conditions 2"]
```

Each section is an independent row. `label` appears to the left of the row.

## Run Arrows (Reaction Scale)

Show starting material mass → product yield below each step:

```yaml
run_arrows:
  - step: 1
    runs:
      - input: "2.15 g"
        output: "1.60 g, 72% yield"

  - step: 2
    runs:
      - input: "1.25 g"
        output: "600 mg, 44% yield"
```

`step` is 1-indexed. A step can have multiple runs (e.g. different scales).

## Condition Key (Letter Conditions)

Map single letters to condition text, then reference them per step:

```yaml
condition_key:
  a: "Pd2(dba)3, BINAP, Cs2CO3, toluene, 110 °C, 16 h"
  b: "NBS, DMF, 0 °C, 2 h"
  c: "PhB(OH)2, Pd(dppf)Cl2, K2CO3, dioxane/H2O, 80 °C"
```

This is most useful with the compact text syntax (where arrows can reference letters with `-->|a|`). In YAML, you'd typically write the conditions directly in `below_arrow.text`.

## JSON Source Resolution

When working with the JSON-first pipeline, you can reference a `reaction_parser` JSON file:

```yaml
source: "reaction.json"

steps:
  - substrates: [sp_0]
    products: [sp_3]
    above_arrow:
      structures: [sp_2]
    below_arrow:
      text:
        - "n-BuLi (1.05 eq)"
        - "THF, -78 °C, 1 h"

layout: linear
```

Structure IDs (like `sp_0`) are resolved from the JSON at render time — their SMILES and geometry come from the parsed reaction data.

## Text Formatting

Condition text is automatically formatted:
- **Subscript digits** in chemical formulas: `Cs2CO3` → Cs₂CO₃
- **Italic prefixes** in IUPAC nomenclature: `n-BuLi` → *n*-BuLi, `tert-BuOH` → *tert*-BuOH

No special markup needed — just write plain text.

## More Examples

See `experiments/scheme_dsl/showcase/` for 30 working examples covering all layout patterns, arrow styles, run arrows, compound labels, and wrapping modes.
