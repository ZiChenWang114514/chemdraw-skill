"""Step 3: Merge reactions into schemes using write_merged_scheme_yaml."""
import sys
import os

sys.path.insert(0, r"C:\Users\mic23\cdxml-toolkit")
from cdxml_toolkit.render.scheme_yaml_writer import write_merged_scheme_yaml
from cdxml_toolkit.render.renderer import render_to_file
from cdxml_toolkit.render.parser import parse_yaml

out_dir = r"C:\Users\mic23\cdxml-toolkit-mcp-testing-temp\phase2\task7b"

# --- Route A: 5-carbon linker ---
# 009 = Mitsunobu (SM: thalidomide-OH + Boc-aminopentanol -> Boc-product)
# 011, 013 = Boc deprotections of 009 product (repeat runs -> range yields)
# Expected topology: sequential chain: 009 -> (011+013)

route_a_jsons = [
    os.path.join(out_dir, "KL-7001-009.json"),
    os.path.join(out_dir, "KL-7001-011.json"),
    os.path.join(out_dir, "KL-7001-013.json"),
]
route_a_yaml = os.path.join(out_dir, "route_A_5C_scheme.yaml")
route_a_cdxml = os.path.join(out_dir, "route_A_5C_scheme.cdxml")

print("Building Route A (5-carbon linker) scheme...")
try:
    yaml_path = write_merged_scheme_yaml(
        route_a_jsons,
        route_a_yaml,
        layout="auto",
        include_run_arrows=True,
        use_eln_labels=True,
    )
    print(f"  YAML saved: {yaml_path}")

    # Render to CDXML
    scheme = parse_yaml(yaml_path)
    render_to_file(scheme, route_a_cdxml)
    print(f"  CDXML saved: {route_a_cdxml}")
except Exception as e:
    print(f"  ERROR: {e}")
    import traceback
    traceback.print_exc()

# --- Route B: 4-carbon linker ---
# 010 = Boc deprotection of KL-7003-008 (4C Boc SM)
# 012, 014 = Boc deprotections of 4C Boc SM (parallel repeat runs)
# Expected topology: parallel (all same reaction, different runs)

route_b_jsons = [
    os.path.join(out_dir, "KL-7001-010.json"),
    os.path.join(out_dir, "KL-7001-012.json"),
    os.path.join(out_dir, "KL-7001-014.json"),
]
route_b_yaml = os.path.join(out_dir, "route_B_4C_scheme.yaml")
route_b_cdxml = os.path.join(out_dir, "route_B_4C_scheme.cdxml")

print("\nBuilding Route B (4-carbon linker) scheme...")
try:
    yaml_path = write_merged_scheme_yaml(
        route_b_jsons,
        route_b_yaml,
        layout="auto",
        include_run_arrows=True,
        use_eln_labels=True,
    )
    print(f"  YAML saved: {yaml_path}")

    # Render to CDXML
    scheme = parse_yaml(yaml_path)
    render_to_file(scheme, route_b_cdxml)
    print(f"  CDXML saved: {route_b_cdxml}")
except Exception as e:
    print(f"  ERROR: {e}")
    import traceback
    traceback.print_exc()

print("\nDone.")
