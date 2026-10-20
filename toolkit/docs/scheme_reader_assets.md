# Scheme Reader Assets — Reference for Downstream Consumers

This document describes the `scheme_reader` ecosystem in `cdxml-toolkit` and what assets
are available for reuse by other tools (e.g. IUPAC name alignment, molecule matching).

---

## 1. Quick Start — Parse Any CDXML Scheme

```python
from cdxml_toolkit.scheme_reader import read_scheme

desc = read_scheme("path/to/scheme.cdxml", use_chemscript=True)

# desc.species  → Dict[str, SpeciesRecord]  (every chemical entity)
# desc.steps    → List[StepRecord]          (every reaction arrow)
# desc.topology → "linear" | "divergent" | "convergent" | "parallel" | "mixed"
# desc.narrative → human-readable text summary
```

**Signature:**
```python
def read_scheme(
    cdxml_path: str,
    use_network: bool = True,       # PubChem lookups for text labels
    use_chemscript: bool = False,   # ChemScript IUPAC names + abbreviation resolution
    verbose: bool = False,
) -> SchemeDescription
```

Handles single-step and multi-step schemes, sequential/divergent/parallel layouts,
above/below-arrow reagents, condition blocks, yield annotations, and failed arrows.

---

## 2. Data Model

### `SpeciesRecord` — one chemical entity

```python
@dataclass
class SpeciesRecord:
    id: str                             # "species_0", "species_1", ...
    cdxml_element_id: str               # original CDXML element id
    element_type: str                   # "fragment" (drawn structure) or "text"
    smiles: Optional[str]               # canonical SMILES (abbreviations resolved)
    smiles_raw: Optional[str]           # SMILES without abbreviation expansion
    name: Optional[str]                 # display name / text label content
    formula: Optional[str]              # molecular formula (e.g. "C12H15NO2")
    mw: Optional[float]                 # molecular weight
    label: Optional[str]               # compound number ("1", "2a", "(iv)")
    iupac_name: Optional[str]          # IUPAC name (ChemScript or lookup)
    text_category: Optional[str]       # for text species: "chemical",
                                        #   "condition_ref", "citation",
                                        #   "bioactivity", "conditions_block"
```

**Key fields for molecule alignment:**
- `smiles` — canonical, abbreviation-resolved SMILES (best for structural matching)
- `smiles_raw` — SMILES before abbreviation expansion (may contain `*` groups)
- `iupac_name` — systematic IUPAC name (populated when `use_chemscript=True`)
- `name` — display name from the CDXML (common name, abbreviation, or text block)
- `formula` — molecular formula from RDKit
- `label` — compound number as drawn (e.g. "1", "2a")

### `StepRecord` — one reaction arrow

```python
@dataclass
class StepRecord:
    step_index: int                     # 0-based
    reactant_ids: List[str]            # SpeciesRecord.id refs
    product_ids: List[str]             # SpeciesRecord.id refs
    reagent_ids: List[str]             # above/below arrow species
    conditions: List[str]              # parsed conditions (temp, time, atm)
    condition_text_raw: List[str]      # full text blocks as-is
    yield_text: Optional[str]          # "72%", "quant."
    arrow_style: str                   # "solid" | "dashed" | "failed"
    arrow_cdxml_id: Optional[str]
```

### `SchemeDescription` — complete scheme output

```python
@dataclass
class SchemeDescription:
    version: str = "1.0"
    source_file: str
    topology: str                      # "linear", "divergent", etc.
    content_type: str                  # "synthesis", "sar_design", etc.
    num_steps: int
    species: Dict[str, SpeciesRecord]
    steps: List[StepRecord]
    narrative: str
    warnings: List[str]
```

**Serialization:**
```python
desc.to_dict()                         # → dict
desc.to_json("output.json")           # → JSON file
SchemeDescription.from_json("f.json") # → SchemeDescription
SchemeDescription.from_dict(d)        # → SchemeDescription
```

---

## 3. IUPAC Name Generation

### Via ChemScript (best quality, requires ChemDraw 16 on Windows)

```python
from cdxml_toolkit.chemscript_bridge import ChemScriptBridge

cs = ChemScriptBridge()
iupac = cs.get_name("c1ccc2nc(N3CCOCC3)ccc2c1")
# → "2-(morpholin-4-yl)quinoline"
```

**In scheme_reader flow:** When `use_chemscript=True`, `read_scheme()` calls
`ChemScriptBridge.get_name(smiles)` for every fragment species and stores the
result in `SpeciesRecord.iupac_name`.

**Graceful degradation:** If ChemScript is unavailable (Linux, no ChemDraw),
`iupac_name` stays `None`. No error raised.

**Known limitations:**
- Fails on some charged structures and unusual valences
- Fails on abbreviation groups that weren't expanded
- 32-bit .NET library — runs via subprocess bridge to `chemscript32` env

### Via PubChem (network lookup, cross-platform)

The `reaction_parser` module's `_resolve_text_label()` can resolve common names
to SMILES via PubChem API. This is used when `use_network=True`.

---

## 4. Reagent Database — Name/SMILES Resolution + Role Classification

```python
from cdxml_toolkit.reagent_db import get_reagent_db

db = get_reagent_db()

# Name → role
db.role_for_name("pd2(dba)3")         # → "catalyst"
db.role_for_name("rac-binap")         # → "ligand"
db.role_for_name("cs2co3")            # → "base"
db.role_for_name("thf")               # → "solvent"

# Name → display name
db.display_for_name("pd2dba3")        # → "Pd₂(dba)₃"
db.resolve_display("dppf")            # → "dppf" (or display if known)

# SMILES → role
db.role_for_smiles("[Cs+].[Cs+].[O-]C(=O)[O-]")  # → "base"

# Full entry lookup
db.entry_for_name("cs2co3")
# → {"display": "Cs₂CO₃", "smiles": "...", "role": "base", "aliases": [...]}

db.entry_for_smiles("C1CCOC1")
# → {"display": "THF", "smiles": "C1CCOC1", "role": "solvent", ...}

# Combined lookup
db.smiles_role_display("C1CCOC1")     # → ("solvent", "THF")
```

**Two-tier architecture:**
- **Tier 1** (`reagent_abbreviations.json`, ~172 entries): Curated, has roles
- **Tier 2** (`chemscanner_abbreviations.json`, ~5,800 entries): ChemScanner-derived, no roles

**Available roles:** `catalyst`, `ligand`, `base`, `lewis_acid`, `solvent`,
`coupling_reagent`, `reducing_agent`, `reductant`, `oxidant`,
`halogenating_agent`, `fluorinating_agent`, `borylating_agent`,
`activating_agent`, `deprotecting_agent`, `protecting_group`,
`drying_agent`, `acid`, `additive`, `reagent`

---

## 5. Structured Reagent Parsing

The `scheme_refine` module provides `_parse_step_reagents()` which decomposes
all above/below-arrow information into categorised bins:

```python
from cdxml_toolkit.scheme_refine import _parse_step_reagents

cats = _parse_step_reagents(step, desc.species)
# cats = {
#     "catalysts":  [("Pd₂(dba)₃", "5 mol%"), ...],
#     "ligands":    [("rac-BINAP", "10 mol%"), ...],
#     "bases":      [("Cs₂CO₃", "2.0 eq"), ...],
#     "reagents":   [("morpholine", ""), ...],
#     "solvents":   ["Dioxane"],
#     "conditions": ["reflux", "24 h"],
#     "workup":     ["then filter through Celite"],
# }
```

Handles both fragment species (drawn structures) and text species (multi-line
text blocks with reagent names, solvents, conditions mixed together).

---

## 6. RDKit Utilities for SMILES/Structure Work

```python
from cdxml_toolkit.rdkit_utils import (
    frag_to_smiles,            # <fragment> → canonical SMILES
    frag_to_smiles_resolved,   # with abbreviation expansion
    frag_to_smiles_chemscript, # via ChemScript (best quality)
    frag_to_mw,                # → molecular weight
)
```

---

## 7. CDXML Utilities

```python
from cdxml_toolkit.cdxml_utils import (
    parse_cdxml,        # path → ElementTree root
    build_id_map,       # root → {id_str: Element}
    fragment_bbox,      # <fragment> → (x0, y0, x1, y1)
    fragment_centroid,  # <fragment> → (cx, cy)
    arrow_endpoints,    # <arrow> → ((tail_x, tail_y), (head_x, head_y))
)
```

---

## 8. Test Data Locations

### Showcase CDXML (30 synthetic schemes, rendered from DSL)

```
C:\Users\mic23\cdxml-toolkit\experiments\scheme_dsl\showcase\
├── 01_buchwald_linear.cdxml        # Single-step Buchwald-Hartwig
├── 02_suzuki_linear.cdxml          # Suzuki coupling
├── 03_snar_linear.cdxml            # SNAr
├── 04_amide_coupling_linear.cdxml  # Amide coupling
├── 05_boc_deprotection_linear.cdxml
├── 06_two_step_sequential.cdxml    # 2-step chain
├── 07_three_step_sequential.cdxml  # 3-step chain
├── 08_wrap_repeat_4step.cdxml      # Wrap layout
├── ...
├── 17_divergent_buchwald_sar.cdxml # Divergent SAR
├── 19_stacked_rows_comparison.cdxml
├── 26_divergent_success_vs_failure.cdxml
└── 30_compact_syntax_multistep.cdxml
```

Each has a matching `.yaml` DSL source and a pre-rendered `.cdxml` output.

### Real-world CDXML (extracted from DOCX/PPTX)

```
C:\Users\mic23\chem-test-data\
├── docx\*.docx                    # Source Word documents with embedded ChemDraw
├── pptx\*.pptx                    # Source PowerPoint slides
├── extracted_docx\*.cdxml         # Extracted ChemDraw objects from DOCX
└── extracted_pptx\*.cdxml         # Extracted from PPTX
```

Extraction tool: `cdxml_toolkit.ole_extractor.extract_from_office()`

### Verification report

```
C:\Users\mic23\chem-test-data\scheme_reader_report_full_rendered.html
```

HTML report with ChemDraw-rendered images, parsed species tables,
structured narratives, ML enrichment, and bond-change analysis for all 62 schemes.

---

## 9. ML Enrichment (Optional)

### Atom Mapping (RXNMapper)

```python
# Via subprocess to rxn-experiments conda env (GPU-accelerated)
from cdxml_toolkit.scheme_reader_verify import enrich_scheme, batch_enrich_schemes

enrichment = enrich_scheme(desc)
# enrichment[step_index] = {
#     "mapped_rxn": "...",        # atom-mapped SMILES
#     "confidence": 0.95,         # mapping confidence
#     "reaction_class": "...",    # from RXN Insight
#     "reaction_name": "...",
#     "bond_changes": {...},      # bonds formed/broken
# }
```

### Batch processing (single model load)

```python
results = batch_enrich_schemes([(0, desc1), (1, desc2), ...])
```

---

## 10. Condition Token Classification

```python
from cdxml_toolkit.reaction_parser import _is_condition_token

_is_condition_token("reflux")    # True
_is_condition_token("24 h")     # True
_is_condition_token("-78 °C")   # True
_is_condition_token("N₂")       # True
_is_condition_token("Cs2CO3")   # False (it's a reagent)
```

---

## 11. Common Patterns

### Iterate all fragment species with SMILES

```python
desc = read_scheme("scheme.cdxml", use_chemscript=True)
for sp_id, sp in desc.species.items():
    if sp.element_type == "fragment" and sp.smiles:
        print(f"{sp.id}: {sp.smiles}  IUPAC={sp.iupac_name}  label={sp.label}")
```

### Get all reactant/product SMILES for a step

```python
step = desc.steps[0]
reactant_smiles = [desc.species[rid].smiles for rid in step.reactant_ids
                   if desc.species[rid].smiles]
product_smiles  = [desc.species[pid].smiles for pid in step.product_ids
                   if desc.species[pid].smiles]
```

### Resolve a common name to SMILES

```python
db = get_reagent_db()
entry = db.entry_for_name("pd(dppf)cl2")
if entry:
    print(entry["smiles"], entry["display"])  # → SMILES, "Pd(dppf)Cl₂"
```

### Parse a scheme from DOCX/PPTX

```python
from cdxml_toolkit.ole_extractor import extract_from_office

cdxml_paths = extract_from_office("report.pptx", "output_dir/",
                                   output_format="cdxml", convert_method="auto")
for path in cdxml_paths:
    desc = read_scheme(path, use_chemscript=True)
    # ... process each embedded scheme
```
