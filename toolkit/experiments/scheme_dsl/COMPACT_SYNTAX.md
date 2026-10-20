# Compact Text Syntax Reference

The compact text syntax is a concise alternative to YAML for describing reaction schemes. Think "Mermaid for reaction schemes" — you can describe a complete scheme in a few lines of plain text.

```
ArBr: {Brc1ncnc2sccc12}
Morph: {C1COCCN1}

ArBr + Morph --> Product{c1nc(N2CCOCC2)c2ccsc2n1} (72%)
  above: Morph
  below: "Pd2(dba)3", "BINAP", "Cs2CO3", "toluene, 110 °C, 16 h"
```

Files use `.txt`, `.scheme`, or `.rxn` extension and are rendered the same way as YAML:

```bash
cdxml-render scheme.txt -o scheme.cdxml
```

## Structure Definitions

Define structures by ID with a SMILES in curly braces:

```
ArBr: {Brc1ncnc2sccc12}
Morph: {C1COCCN1}
Product: {c1nc(N2CCOCC2)c2ccsc2n1}
```

**Name resolution** (looked up via reagent database or PubChem):
```
catalyst: name "Pd2(dba)3"
```

**File reference:**
```
reference: file "path/to/structure.cdxml"
```

**Compound labels** (displayed below the structure):
```
ArBr: {Brc1ncnc2sccc12} label "1"
```

Or use quoted IDs — they automatically become labels:
```
"1"{Brc1ncnc2sccc12}
```

## Reaction Chain

The core of every scheme is the reaction chain — a line containing at least one arrow:

```
ArBr + Morph --> Product
```

### Arrow Types

| Arrow | Style | Description |
|-------|-------|-------------|
| `-->` | Solid | Normal reaction arrow |
| `..>` | Dashed | Equilibrium or reversible |
| `X>` | Failed | Reaction did not work (X overlay) |

### Multi-Step Chains

Chain multiple steps on one line:

```
A --> B --> C --> Product (80%)
```

This creates 3 separate steps. The renderer draws shared intermediates once.

### Inline Structure Definitions

Define structures directly in the chain:

```
"1"{Brc1ccc2ccccc2n1} --> "2"{c1ccc2nc(N3CCOCC3)ccc2c1}
```

Each `ID{SMILES}` pair defines the structure inline. Quoted IDs like `"1"` also set the compound label.

### Yield

Add yield in parentheses at the end of the last product:

```
A + B --> Product (72%)
A + B --> Product (1.60 g, 72% yield)
```

## Condition Blocks

Indented lines after the reaction chain specify conditions for each step.

### Below-Arrow Text

```
A + B --> Product
  below: "Cs2CO3 (2 eq.)", "Dioxane, 110 °C, 24 h"
```

Multiple items are comma-separated. Each becomes a separate line of text below the arrow.

### Above-Arrow Structures and Text

```
A --> Product
  above: Morph, "1.2 eq."
  below: "Pd2(dba)3", "BINAP", "Cs2CO3"
```

Bare IDs (like `Morph`) are drawn as structures. Quoted strings are rendered as text.

You can define structures inline in the above block:

```
  above: catalyst{c1ccc(P(c2ccccc2)c2ccccc2)cc1}
```

### Step-Indexed Conditions

For multi-step chains, target conditions to specific steps:

```
A --> B --> C --> Product

step 1:
  below: "NBS (1.1 eq)", "DMF, 0 °C, 2 h"

step 2:
  below: "PhB(OH)2, Pd(dppf)Cl2", "K2CO3, dioxane/H2O, 80 °C"

step 3:
  below: "H2, Pd/C", "MeOH, RT, 4 h"
```

Or use bracket notation:

```
  [1] below: "conditions for step 1"
  [2] below: "conditions for step 2"
```

## Run Arrows

Show starting material mass and product yield:

```
A --> Product
  run: "2.15 g" -> "1.60 g, 72% yield"
```

Step-indexed for multi-step:

```
  run[1]: "2.15 g" -> "1.60 g, 72% yield"
  run[2]: "1.25 g" -> "600 mg, 44% yield"
```

## Directives

Lines starting with `@` set scheme-level options:

| Directive | Example | Description |
|-----------|---------|-------------|
| `@layout` | `@layout sequential` | Layout pattern |
| `@wrap` | `@wrap serpentine` | Wrapping mode |
| `@steps_per_row` | `@steps_per_row 3` | Steps per row |
| `@title` | `@title "My Synthesis"` | Scheme title |
| `@conditions` | (block) | Letter condition definitions |

### Layout Values

| Value | Description |
|-------|-------------|
| `linear` | Single-step (default) |
| `sequential` | Multi-step chain (auto-detected if >1 step) |
| `divergent` | One SM → multiple products |
| `stacked-rows` | Independent rows |
| `serpentine` | Zigzag rows |

Layout is auto-detected if not specified: multi-step chains default to `sequential`, single-step to `linear`.

## Letter Conditions

Define conditions once and reference them by letter on each arrow:

```
@conditions
(a) "Pd2(dba)3, BINAP, Cs2CO3, toluene, 110 °C, 16 h"
(b) "NBS, DMF, 0 °C, 2 h"
(c) "PhB(OH)2, Pd(dppf)Cl2, K2CO3, dioxane/H2O, 80 °C"

A -->|a| B -->|b| C -->|c| Product
```

The letter in `|...|` after the arrow inserts the corresponding condition text below that arrow. This keeps the reaction chain concise when conditions are long.

## Complete Examples

### Single-Step Buchwald Coupling

```
@layout linear

"1"{Brc1ccc2ccccc2n1} --> "2"{c1ccc2nc(N3CCOCC3)ccc2c1}

step 1:
  below: "morpholine (1.2 eq)", "Pd2(dba)3 (5 mol%)", "rac-BINAP (10 mol%)", "Cs2CO3 (2.0 eq)", "1,4-dioxane", "reflux, 24 h"
```

### Three-Step Sequential Synthesis

```
@layout sequential

"1"{Brc1ccc2ccccc2n1} --> "2"{c1ccc2nc(N3CCOCC3)ccc2c1} --> "3"{Brc1cc2ccccc2nc1N1CCOCC1} --> "4"{c1ccc(-c2cc3ccccc3nc2N2CCOCC2)cc1}

step 1:
  below: "morpholine (1.2 eq)", "Pd2(dba)3, BINAP", "Cs2CO3, dioxane, reflux"

step 2:
  below: "NBS (1.1 eq)", "DMF, 0 °C, 2 h"

step 3:
  below: "PhB(OH)2, Pd(dppf)Cl2", "K2CO3, dioxane/H2O, 80 °C"
```

### With Run Arrows

```
ArBr: {Brc1ncnc2sccc12}
Product: {c1nc(N2CCOCC2)c2ccsc2n1}

ArBr --> Product (72%)
  above: Morph{C1COCCN1}
  below: "Pd2(dba)3 (0.05 eq.)", "rac-BINAP (0.1 eq.)", "Cs2CO3 (2 eq.)", "Dioxane, 105 °C, 24 h"
  run: "2.15 g" -> "1.60 g, 72% yield"
```

## Text Formatting

Same automatic formatting as YAML — subscripts in chemical formulas and italic IUPAC prefixes are handled automatically from plain text input.

## More Examples

See `experiments/scheme_dsl/showcase/` for 30 working examples. Files 29 and 30 use compact syntax; the rest use YAML (both produce equivalent output).
