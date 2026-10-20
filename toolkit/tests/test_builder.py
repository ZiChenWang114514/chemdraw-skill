#!/usr/bin/env python3
"""
End-to-end test: RDF → normalised coords → CDXML reaction scheme.

Usage:
    python test_builder.py [rdf_file] [output.cdxml]

Defaults to the test_data RDF file and writes to test_data/test_output.cdxml
"""
import json
import sys
import os

# Allow running from any directory
HERE = os.path.dirname(os.path.abspath(__file__))

from cdxml_toolkit.perception.rdf_parser import parse_rdf as parse_rdf_file
from cdxml_toolkit.coord_normalizer import normalize_reaction
from cdxml_toolkit.cdxml_builder import build_reaction_cdxml


def main():
    rdf_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        HERE, "test_data", "Reaction_20260217_1738.rdf"
    )
    out_path = sys.argv[2] if len(sys.argv) > 2 else os.path.join(
        HERE, "test_data", "test_output.cdxml"
    )

    print(f"Parsing {rdf_path} ...")
    reactions = parse_rdf_file(rdf_path)
    if not reactions:
        print("ERROR: no reactions parsed")
        return 1

    rxn = reactions[0]
    print(
        f"Reaction: {rxn.num_reactants} reactant(s), {rxn.num_products} product(s), "
        f"scheme={rxn.scheme_id}"
    )

    # Convert dataclass atoms/bonds to plain dicts for our tools
    def mol_to_dict(mol):
        return {
            "name": mol.name,
            "atoms": [
                {
                    "index": a.index,
                    "symbol": a.symbol,
                    "x": a.x,
                    "y": a.y,
                    **({"cfg": a.cfg} if a.cfg else {}),
                }
                for a in mol.atoms
            ],
            "bonds": [
                {
                    "index": b.index,
                    "order": b.order,
                    "atom1": b.atom1,
                    "atom2": b.atom2,
                    **({"cfg": b.cfg} if b.cfg else {}),
                }
                for b in mol.bonds
            ],
        }

    reactants = [mol_to_dict(m) for m in rxn.reactants]
    products  = [mol_to_dict(m) for m in rxn.products]

    print("Normalising coordinates ...")
    # Layout: reactants on left (~x=120), products on right (~x=400), y=300
    norm_reactants, norm_products = normalize_reaction(
        reactants, products,
        reactant_y=300.0,
        product_y=300.0,
        reactant_start_x=30.0,
        product_start_x=330.0,
        molecule_gap=60.0,
        flip_y=True,       # V3000 MOL is y-up
        strip_hydrogens=True,
    )

    # Report normalised bond lengths
    from cdxml_toolkit.coord_normalizer import _average_bond_length
    for mol in norm_reactants + norm_products:
        avg = _average_bond_length(mol["atoms"], mol["bonds"])
        print(f"  {mol.get('name', '?')}: avg bond length = {avg:.2f} pt")

    # Conditions (pulled from first variation if available)
    conditions = {}
    if rxn.variations:
        v = rxn.variations[0]
        above = [r.name or r.cas for r in v.reagents if r.name or r.cas]
        below = [r.name or r.cas for r in v.catalysts + v.solvents if r.name or r.cas]
        if above:
            conditions["above"] = above
        if below:
            conditions["below"] = below

    # Fallback conditions for display if CAS not resolved
    if not conditions:
        conditions = {
            "above": ["reagent"],
            "below": ["solvent, conditions"],
        }

    print(f"Conditions above: {conditions.get('above', [])}")
    print(f"Conditions below: {conditions.get('below', [])}")

    print("Building CDXML ...")
    cdxml = build_reaction_cdxml(norm_reactants, norm_products, conditions)

    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(cdxml)
    print(f"Written to {out_path}")
    print("Open in ChemDraw to verify.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
