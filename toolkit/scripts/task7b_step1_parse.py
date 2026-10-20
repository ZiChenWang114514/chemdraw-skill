"""Step 1: Parse all 6 experiments to JSON reaction descriptors."""
import sys
import os
import json

base_dir = r"C:\Users\mic23\chem-test-data\lab-books\KL-7001"
out_dir = r"C:\Users\mic23\cdxml-toolkit-mcp-testing-temp\phase2\task7b"
os.makedirs(out_dir, exist_ok=True)

sys.path.insert(0, r"C:\Users\mic23\cdxml-toolkit")

from cdxml_toolkit.perception.reaction_parser import parse_reaction

experiments = ["KL-7001-009", "KL-7001-010", "KL-7001-011",
               "KL-7001-012", "KL-7001-013", "KL-7001-014"]

for exp in experiments:
    exp_dir = os.path.join(base_dir, exp)
    cdxml_path = os.path.join(exp_dir, f"{exp}.cdxml")
    csv_path = os.path.join(exp_dir, f"{exp}.csv")
    rxn_path = os.path.join(exp_dir, f"{exp}.rxn")
    out_path = os.path.join(out_dir, f"{exp}.json")

    print(f"\n{'='*50}")
    print(f"Parsing {exp}...")

    try:
        result = parse_reaction(
            cdxml=cdxml_path,
            csv=csv_path,
            rxn=rxn_path,
            use_network=True,
        )
        # Save JSON
        result.to_json(out_path)
        print(f"  Reaction class: {result.reaction_class}")
        print(f"  Reaction name:  {result.reaction_name}")
        print(f"  SMILES: {result.reaction_smiles[:100] if result.reaction_smiles else 'None'}...")
        sm = result.get_sm()
        dp = result.get_dp()
        yield_info = result.eln_data.get("product_yield", "?") if result.eln_data else "?"
        print(f"  SM:  {[s.name + ' (MW=' + str(s.mw) + ')' for s in sm]}")
        print(f"  DP:  {[s.name + ' (MW=' + str(s.mw) + ')' for s in dp]}")
        print(f"  Yield: {yield_info}")
        print(f"  -> saved to {out_path}")
    except Exception as e:
        print(f"  ERROR: {e}")
        import traceback
        traceback.print_exc()

print("\nDone.")
