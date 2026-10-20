"""
test_parser_normalization.py

Tests for the LLM-friendly YAML normalization pass in parser.py.
Run with:
    /c/Users/mic23/miniconda3/Scripts/conda.exe run -n LLMChem python test_parser_normalization.py
"""

import sys
import traceback
from cdxml_toolkit.render.parser import parse_yaml, _normalize_scheme_data

PASS = "[PASS]"
FAIL = "[FAIL]"

results = []


def check(name, fn):
    try:
        fn()
        print(f"{PASS} {name}")
        results.append((name, True, None))
    except Exception as e:
        tb = traceback.format_exc()
        print(f"{FAIL} {name}: {e}")
        print(tb)
        results.append((name, False, str(e)))


# ---------------------------------------------------------------------------
# Test 1: Inline structures in steps (no top-level structures block)
# ---------------------------------------------------------------------------
TEST1_YAML = """
steps:
  - substrates:
      - smiles: "CCO"
    products:
      - smiles: "CC=O"
    above_arrow:
      text: "PCC"
"""

def test1():
    sd = parse_yaml(TEST1_YAML)
    assert sd.steps, "no steps"
    step = sd.steps[0]
    assert len(step.substrates) == 1, f"expected 1 substrate, got {step.substrates}"
    assert len(step.products) == 1, f"expected 1 product, got {step.products}"
    sub_id = step.substrates[0]
    prod_id = step.products[0]
    assert sub_id in sd.structures, f"substrate id '{sub_id}' not in structures"
    assert prod_id in sd.structures, f"product id '{prod_id}' not in structures"
    assert sd.structures[sub_id].smiles == "CCO", f"wrong substrate SMILES: {sd.structures[sub_id].smiles}"
    assert sd.structures[prod_id].smiles == "CC=O", f"wrong product SMILES: {sd.structures[prod_id].smiles}"
    # text "PCC" should be wrapped in a list
    assert step.above_arrow is not None, "no above_arrow"
    assert step.above_arrow.text == ["PCC"], f"expected ['PCC'], got {step.above_arrow.text}"

check("Test 1: Inline structures in steps + text as string", test1)


# ---------------------------------------------------------------------------
# Test 2: reagents key + text as string
# ---------------------------------------------------------------------------
TEST2_YAML = """
steps:
  - substrates:
      - smiles: "CCO"
    reagents:
      - smiles: "Nc1ccccc1N"
        above_arrow: true
    products:
      - smiles: "CC=O"
    above_arrow:
      text: "Conditions"
"""

def test2():
    sd = parse_yaml(TEST2_YAML)
    step = sd.steps[0]
    # The reagent with above_arrow: true should appear in above_arrow.structures
    assert step.above_arrow is not None, "no above_arrow"
    assert len(step.above_arrow.structures) == 1, (
        f"expected 1 above_arrow structure, got {step.above_arrow.structures}"
    )
    reagent_id = step.above_arrow.structures[0]
    assert reagent_id in sd.structures, f"reagent id '{reagent_id}' not registered"
    assert sd.structures[reagent_id].smiles == "Nc1ccccc1N", (
        f"wrong reagent SMILES: {sd.structures[reagent_id].smiles}"
    )
    # Original text "Conditions" should still be there
    assert "Conditions" in step.above_arrow.text, (
        f"expected 'Conditions' in above_arrow.text, got {step.above_arrow.text}"
    )

check("Test 2: reagents with above_arrow flag + text as string", test2)


# ---------------------------------------------------------------------------
# Test 2b: reagent without above_arrow flag goes to below_arrow text
# ---------------------------------------------------------------------------
TEST2B_YAML = """
steps:
  - substrates:
      - smiles: "CCO"
    reagents:
      - smiles: "O"
        name: "Water"
    products:
      - smiles: "CC=O"
"""

def test2b():
    sd = parse_yaml(TEST2B_YAML)
    step = sd.steps[0]
    assert step.below_arrow is not None, "no below_arrow"
    # Reagent without above_arrow: true → rendered as text in below_arrow
    assert len(step.below_arrow.text) >= 1, "expected text in below_arrow"
    # Display name "Water" should appear (name takes priority over SMILES id)
    assert any("Water" in t or "s_" in t for t in step.below_arrow.text), (
        f"expected Water in below_arrow.text, got {step.below_arrow.text}"
    )

check("Test 2b: reagent without above_arrow flag → below_arrow text", test2b)


# ---------------------------------------------------------------------------
# Test 3: species alias + bare SMILES in substrates/products
# ---------------------------------------------------------------------------
TEST3_YAML = """
species:
  - smiles: "CCO"
    name: "Ethanol"
  - smiles: "CC=O"
    name: "Acetaldehyde"
steps:
  - substrates:
      - smiles: "CCO"
    products:
      - smiles: "CC=O"
"""

def test3():
    sd = parse_yaml(TEST3_YAML)
    # species should have been renamed to structures
    assert len(sd.structures) >= 2, f"expected >=2 structures, got {len(sd.structures)}"
    # Verify both smiles appear in structures
    smiles_set = {ref.smiles for ref in sd.structures.values()}
    assert "CCO" in smiles_set, f"CCO not in {smiles_set}"
    assert "CC=O" in smiles_set, f"CC=O not in {smiles_set}"
    # Steps should resolve correctly
    step = sd.steps[0]
    assert len(step.substrates) == 1
    assert len(step.products) == 1
    sub_id = step.substrates[0]
    prod_id = step.products[0]
    assert sd.structures[sub_id].smiles == "CCO"
    assert sd.structures[prod_id].smiles == "CC=O"

check("Test 3: species alias + structures as list", test3)


# ---------------------------------------------------------------------------
# Test 4: structures as dict with id field (change 7 — id is redundant)
# ---------------------------------------------------------------------------
TEST4_YAML = """
structures:
  SM:
    id: "SM"
    smiles: "CCO"
  Product:
    id: "Product"
    smiles: "CC=O"
steps:
  - substrates: [SM]
    products: [Product]
"""

def test4():
    sd = parse_yaml(TEST4_YAML)
    assert "SM" in sd.structures
    assert "Product" in sd.structures
    assert sd.structures["SM"].smiles == "CCO"
    assert sd.structures["Product"].smiles == "CC=O"

check("Test 4: redundant id field inside structure defs", test4)


# ---------------------------------------------------------------------------
# Test 5: reactants alias for substrates
# ---------------------------------------------------------------------------
TEST5_YAML = """
structures:
  SM:
    smiles: "CCO"
  Product:
    smiles: "CC=O"
steps:
  - reactants: [SM]
    products: [Product]
"""

def test5():
    sd = parse_yaml(TEST5_YAML)
    step = sd.steps[0]
    assert step.substrates == ["SM"], f"expected ['SM'], got {step.substrates}"

check("Test 5: reactants alias for substrates", test5)


# ---------------------------------------------------------------------------
# Test 6: bare SMILES strings in substrates/products list
# ---------------------------------------------------------------------------
TEST6_YAML = """
steps:
  - substrates:
      - "CCO"
    products:
      - "CC=O"
"""

def test6():
    sd = parse_yaml(TEST6_YAML)
    step = sd.steps[0]
    sub_id = step.substrates[0]
    prod_id = step.products[0]
    assert sub_id in sd.structures, f"bare SMILES substrate not registered; id={sub_id}"
    assert prod_id in sd.structures, f"bare SMILES product not registered; id={prod_id}"
    assert sd.structures[sub_id].smiles == "CCO"
    assert sd.structures[prod_id].smiles == "CC=O"

check("Test 6: bare SMILES strings in substrates/products", test6)


# ---------------------------------------------------------------------------
# Regression: existing canonical YAML must still work unchanged
# ---------------------------------------------------------------------------
REGRESSION_YAML = """
structures:
  SM:
    smiles: "CCO"
  Product:
    smiles: "CC=O"
steps:
  - substrates: [SM]
    products: [Product]
    above_arrow:
      text: ["PCC"]
"""

def test_regression():
    sd = parse_yaml(REGRESSION_YAML)
    assert "SM" in sd.structures
    assert "Product" in sd.structures
    assert sd.structures["SM"].smiles == "CCO"
    assert sd.structures["Product"].smiles == "CC=O"
    step = sd.steps[0]
    assert step.substrates == ["SM"]
    assert step.products == ["Product"]
    assert step.above_arrow is not None
    assert step.above_arrow.text == ["PCC"]
    assert step.above_arrow.structures == []

check("Regression: canonical YAML still parses correctly", test_regression)


# ---------------------------------------------------------------------------
# Regression: structures as dict shorthand (SMILES string value)
# ---------------------------------------------------------------------------
REGRESSION2_YAML = """
structures:
  ArBr: "Brc1ncnc2sccc12"
  Product: "c1nc(N2CCOCC2)c2ccsc2n1"
steps:
  - substrates: [ArBr]
    products: [Product]
    below_arrow:
      text:
        - "Pd2(dba)3"
        - "Cs2CO3"
"""

def test_regression2():
    sd = parse_yaml(REGRESSION2_YAML)
    assert sd.structures["ArBr"].smiles == "Brc1ncnc2sccc12"
    step = sd.steps[0]
    assert step.substrates == ["ArBr"]
    assert step.below_arrow.text == ["Pd2(dba)3", "Cs2CO3"]

check("Regression: shorthand SMILES value in structures dict", test_regression2)


# ---------------------------------------------------------------------------
# Idempotency: normalizing already-canonical data twice gives same result
# ---------------------------------------------------------------------------
def test_idempotent():
    import yaml as _yaml
    data = _yaml.safe_load(REGRESSION_YAML)
    once = _normalize_scheme_data(data)
    twice = _normalize_scheme_data(once)
    # structures keys and SMILES should be identical
    assert set(once["structures"].keys()) == set(twice["structures"].keys()), (
        f"keys differ: {set(once['structures'].keys())} vs {set(twice['structures'].keys())}"
    )
    once_steps = once["steps"]
    twice_steps = twice["steps"]
    assert len(once_steps) == len(twice_steps)
    for s1, s2 in zip(once_steps, twice_steps):
        assert s1["substrates"] == s2["substrates"], f"{s1['substrates']} != {s2['substrates']}"
        assert s1["products"] == s2["products"]

check("Idempotency: normalizing twice gives same result", test_idempotent)


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
total = len(results)
passed = sum(1 for _, ok, _ in results if ok)
failed = total - passed

print()
print(f"Results: {passed}/{total} passed", end="")
if failed:
    print(f", {failed} FAILED")
    sys.exit(1)
else:
    print(" — all OK")
    sys.exit(0)
