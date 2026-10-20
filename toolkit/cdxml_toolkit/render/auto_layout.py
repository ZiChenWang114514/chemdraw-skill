"""
auto_layout.py — Generate a default SchemeDescriptor from reaction_parser JSON.

The "zero-effort" path: reads the JSON, puts SM on left, DP on right,
atom-contributing species above arrow, conditions and non-contributing
species as text below arrow.

Usage:
    from scheme_dsl.auto_layout import auto_layout
    scheme = auto_layout("reaction.json")

    # Or from CLI:
    python -m scheme_dsl.auto_layout reaction.json -o scheme.cdxml
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any, Dict, List, Optional

from .schema import (
    ArrowContent,
    SchemeDescriptor,
    StepDescriptor,
    StructureRef,
)


def auto_layout(
    reaction_json_path: str,
    include_equiv: bool = True,
) -> SchemeDescriptor:
    """
    Generate a default SchemeDescriptor from reaction_parser output.

    Reads the JSON, classifies species into layout positions:
      - SM → substrate (left of arrow)
      - atom-contributing non-SM species → above arrow as structures
      - non-contributing species with SMILES → text below arrow (with equiv)
      - conditions from JSON → text below arrow
      - DP → product (right of arrow)

    Parameters
    ----------
    reaction_json_path : str
        Path to reaction_parser JSON file.
    include_equiv : bool
        Whether to include equivalents in text labels (default True).

    Returns
    -------
    SchemeDescriptor
        Ready to render with renderer.render().
    """
    with open(reaction_json_path, encoding="utf-8") as f:
        data = json.load(f)

    species_list = data.get("species", [])
    conditions = data.get("conditions", [])

    # Classify species by role and position
    sm = None
    dp = None
    above_structures: List[Dict] = []      # drawn above arrow
    below_text_species: List[Dict] = []    # reagents shown as text below

    for sp in species_list:
        if sp.get("is_sm"):
            sm = sp
        elif sp.get("is_dp"):
            dp = sp
        elif sp.get("role") == "atom_contributing":
            # Non-SM atom-contributing species go above arrow as structures
            above_structures.append(sp)
        elif sp.get("role") in ("non_contributing", "reagent"):
            below_text_species.append(sp)
        elif sp.get("role") == "product":
            # Additional products (not DP) — skip for now
            pass
        else:
            # Unknown role — put as text below
            below_text_species.append(sp)

    if sm is None:
        raise ValueError("No starting material (is_sm=true) found in JSON")
    if dp is None:
        raise ValueError("No desired product (is_dp=true) found in JSON")

    # Build step
    substrates = [sm["id"]]
    products = [dp["id"]]

    # Above arrow: structures + equiv text
    above_arrow = None
    if above_structures:
        above_struct_ids = [sp["id"] for sp in above_structures]
        above_text = []
        if include_equiv:
            for sp in above_structures:
                equiv = sp.get("csv_equiv")
                if equiv and equiv != "1.0":
                    above_text.append(f"({equiv} eq)")
        above_arrow = ArrowContent(
            structures=above_struct_ids,
            text=above_text,
        )

    # Below arrow: reagent text + conditions
    below_lines: List[str] = []

    for sp in below_text_species:
        name = sp.get("name", sp.get("csv_name", ""))
        if not name:
            continue
        # Format: "Name (X eq.)" or just "Name"
        equiv = sp.get("csv_equiv")
        if include_equiv and equiv and equiv != "1.0":
            below_lines.append(f"{name} ({equiv} eq.)")
        else:
            below_lines.append(name)

    # Append conditions from JSON
    below_lines.extend(conditions)

    below_arrow = None
    if below_lines:
        below_arrow = ArrowContent(text=below_lines)

    step = StepDescriptor(
        substrates=substrates,
        products=products,
        above_arrow=above_arrow,
        below_arrow=below_arrow,
    )

    # Store just the basename — the renderer resolves relative to yaml_dir
    return SchemeDescriptor(
        source=os.path.basename(reaction_json_path),
        steps=[step],
        layout="linear",
    )


def auto_layout_to_cdxml(
    reaction_json_path: str,
    output_path: Optional[str] = None,
    include_equiv: bool = True,
) -> str:
    """
    Generate and render a scheme from reaction_parser JSON.

    Parameters
    ----------
    reaction_json_path : str
        Path to reaction_parser JSON file.
    output_path : str, optional
        Output CDXML path. If None, derives from JSON filename.
    include_equiv : bool
        Whether to include equivalents in text labels.

    Returns
    -------
    str
        Path to the written CDXML file.
    """
    from .renderer import render_to_file

    scheme = auto_layout(reaction_json_path, include_equiv=include_equiv)

    if output_path is None:
        stem = os.path.splitext(os.path.basename(reaction_json_path))[0]
        output_path = os.path.join(
            os.path.dirname(reaction_json_path),
            f"{stem}-scheme.cdxml",
        )

    yaml_dir = os.path.dirname(os.path.abspath(reaction_json_path))
    render_to_file(scheme, output_path, yaml_dir=yaml_dir)
    return output_path


def main():
    """CLI entry point for auto_layout."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Auto-generate a CDXML reaction scheme from reaction_parser JSON.",
    )
    parser.add_argument(
        "input",
        help="reaction_parser JSON file",
    )
    parser.add_argument(
        "-o", "--output",
        default=None,
        help="Output CDXML file (default: {input_stem}-scheme.cdxml)",
    )
    parser.add_argument(
        "--no-equiv",
        action="store_true",
        help="Don't include equivalents in reagent text",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Print progress to stderr",
    )
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"Error: file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    if args.verbose:
        print(f"Loading {args.input}...", file=sys.stderr)

    output_path = auto_layout_to_cdxml(
        args.input,
        output_path=args.output,
        include_equiv=not args.no_equiv,
    )

    print(f"Written: {output_path}")


if __name__ == "__main__":
    main()
