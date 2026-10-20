"""Step 2: Inspect reaction summaries to confirm routes and plan merging."""
import sys
import os
import json

sys.path.insert(0, r"C:\Users\mic23\cdxml-toolkit")
from cdxml_toolkit.perception import reaction_summary

out_dir = r"C:\Users\mic23\cdxml-toolkit-mcp-testing-temp\phase2\task7b"

experiments = ["KL-7001-009", "KL-7001-010", "KL-7001-011",
               "KL-7001-012", "KL-7001-013", "KL-7001-014"]

for exp in experiments:
    json_path = os.path.join(out_dir, f"{exp}.json")
    print(f"\n{'='*60}")
    print(f"  {exp}")
    print(f"{'='*60}")
    summary = reaction_summary(
        json_path,
        species_fields=["id", "name", "role", "smiles", "mw", "formula", "is_sm", "is_dp"],
        top_fields=["experiment", "reaction_class", "reaction_name", "reaction_smiles", "conditions"],
        eln_fields=["product_yield", "reaction_type", "sm_mass", "product_obtained"],
    )
    # Print key parts concisely
    print(f"  Reaction type: {summary.get('eln_data', {}).get('reaction_type', '?')}")
    print(f"  Yield:         {summary.get('eln_data', {}).get('product_yield', '?')}")
    species = summary.get("species", [])
    if isinstance(species, dict):
        items = species.items()
    else:
        # It's a list
        items = [(sp.get("id", i), sp) for i, sp in enumerate(species)]
    for sp_id, sp in items:
        role_flag = ""
        if sp.get("is_sm"):
            role_flag = " [SM]"
        elif sp.get("is_dp"):
            role_flag = " [DP]"
        print(f"    {sp_id}: {str(sp.get('name', '?'))[:50]}{role_flag}")
        print(f"       role={sp.get('role','?')}, MW={sp.get('mw','?')}, formula={sp.get('formula','?')}")
        smiles = sp.get("smiles", "")
        if smiles:
            print(f"       smiles={smiles[:80]}")
print()
