# NOTE: This module is not imported by any other tool as of v0.3.
#        It is a standalone CLI utility.
#!/usr/bin/env python3
"""
coord_normalizer.py — Normalize atom coordinates to ACS Document 1996 standard.

Takes atom coordinates from any source (RDKit, PubChem SDF, SciFinder RDF V3000 MOL
blocks) and normalizes them so they are ready for cdxml_builder.py:

  - Scale so that the average bond length == 14.40 pt (ACS 1996 target)
  - Flip y-axis (MOL/SDF format is y-up; CDXML is y-down)
  - Center molecule at a caller-supplied (cx, cy) position
  - Strip explicit hydrogens: remove H atoms and update NumHydrogens on the
    heavy atom they were bonded to

The module can also be used as a CLI tool to normalise a JSON atom/bond file.

Usage (CLI):
    python coord_normalizer.py molecule.json [options]
    python coord_normalizer.py molecule.json --center 200 300 --output normalised.json

Input JSON format (same as cdxml_builder.py expects):
    {
      "atoms": [
        {"index": 1, "symbol": "C", "x": 0.0, "y": 0.0},
        ...
      ],
      "bonds": [
        {"index": 1, "order": 1, "atom1": 1, "atom2": 2},
        ...
      ]
    }

Output: same JSON structure with normalised x/y and added "num_hydrogens" fields.
"""

import argparse
import json
import math
import sys
from copy import deepcopy
from typing import List, Dict, Tuple, Optional

from .constants import ACS_BOND_LENGTH


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ACS_BOND_LENGTH_PT = ACS_BOND_LENGTH   # target average bond length in points (1 pt = 1/72 in)

# Periodic table: element symbol -> (atomic number, default valence)
# Only the elements we are likely to encounter in medicinal chemistry
ELEMENT_DATA: Dict[str, Tuple[int, int]] = {
    "H":  (1,  1),
    "C":  (6,  4),
    "N":  (7,  3),
    "O":  (8,  2),
    "F":  (9,  1),
    "P":  (15, 3),
    "S":  (16, 2),
    "Cl": (17, 1),
    "Br": (35, 1),
    "I":  (53, 1),
    "B":  (5,  3),
    "Si": (14, 4),
    "Se": (34, 2),
}

ELEMENT_NUMBERS: Dict[str, int] = {sym: data[0] for sym, data in ELEMENT_DATA.items()}
DEFAULT_VALENCE: Dict[str, int] = {sym: data[1] for sym, data in ELEMENT_DATA.items()}


# ---------------------------------------------------------------------------
# Core normalisation logic
# ---------------------------------------------------------------------------

def _average_bond_length(atoms: List[Dict], bonds: List[Dict]) -> float:
    """Return the average Euclidean bond length, or 1.0 if no bonds."""
    if not bonds:
        return 1.0
    atom_xy = {a["index"]: (a["x"], a["y"]) for a in atoms}
    lengths = []
    for b in bonds:
        x1, y1 = atom_xy.get(b["atom1"], (0, 0))
        x2, y2 = atom_xy.get(b["atom2"], (0, 0))
        d = math.hypot(x2 - x1, y2 - y1)
        if d > 1e-6:
            lengths.append(d)
    return sum(lengths) / len(lengths) if lengths else 1.0


def _bounding_box(atoms: List[Dict]) -> Tuple[float, float, float, float]:
    """Return (min_x, min_y, max_x, max_y) of atom positions."""
    xs = [a["x"] for a in atoms]
    ys = [a["y"] for a in atoms]
    return min(xs), min(ys), max(xs), max(ys)


def strip_explicit_hydrogens(
    atoms: List[Dict],
    bonds: List[Dict],
) -> Tuple[List[Dict], List[Dict]]:
    """
    Remove explicit hydrogen atoms from the atom/bond lists.

    For each heavy atom that had an explicit H neighbour, increment
    num_hydrogens by 1 (or initialise it to 1).  Returns new lists;
    input is not modified.
    """
    atoms = deepcopy(atoms)
    bonds = deepcopy(bonds)

    # Identify explicit H atom indices
    h_indices = {a["index"] for a in atoms if a.get("symbol", "C") == "H"}
    if not h_indices:
        return atoms, bonds

    # For each H, find the heavy-atom neighbour and bump its H count
    h_count_delta: Dict[int, int] = {}
    bonds_to_remove = set()
    for b in bonds:
        a1, a2 = b["atom1"], b["atom2"]
        if a1 in h_indices or a2 in h_indices:
            bonds_to_remove.add(b["index"])
            heavy = a2 if a1 in h_indices else a1
            h_count_delta[heavy] = h_count_delta.get(heavy, 0) + 1

    # Update num_hydrogens on heavy atoms
    for a in atoms:
        if a["index"] in h_count_delta:
            a["num_hydrogens"] = a.get("num_hydrogens", 0) + h_count_delta[a["index"]]

    # Remove H atoms and their bonds
    atoms = [a for a in atoms if a["index"] not in h_indices]
    bonds = [b for b in bonds if b["index"] not in bonds_to_remove]

    return atoms, bonds


def normalize_coords(
    atoms: List[Dict],
    bonds: List[Dict],
    center_x: float = 200.0,
    center_y: float = 300.0,
    flip_y: bool = True,
    target_bond_length: float = ACS_BOND_LENGTH_PT,
    strip_hydrogens: bool = True,
) -> Tuple[List[Dict], List[Dict]]:
    """
    Normalize atom coordinates and return (atoms, bonds) ready for cdxml_builder.

    Parameters
    ----------
    atoms : list of dicts with keys: index, symbol, x, y (and optionally z,
            num_hydrogens, cfg, etc.)
    bonds : list of dicts with keys: index, order, atom1, atom2 (and optionally cfg)
    center_x, center_y : target centre in CDXML points
    flip_y : True to negate y (converts MOL y-up → CDXML y-down)
    target_bond_length : desired average bond length in points (default 14.40)
    strip_hydrogens : remove explicit H atoms and count them on heavy atoms

    Returns
    -------
    (atoms, bonds) — new lists, input unchanged
    """
    atoms = deepcopy(atoms)
    bonds = deepcopy(bonds)

    # Step 1 — strip explicit hydrogens before calculating scale
    if strip_hydrogens:
        atoms, bonds = strip_explicit_hydrogens(atoms, bonds)

    if not atoms:
        return atoms, bonds

    # Step 2 — flip y-axis (MOL y-up → CDXML y-down)
    if flip_y:
        for a in atoms:
            a["y"] = -a["y"]

    # Step 3 — scale to ACS bond length
    avg_bl = _average_bond_length(atoms, bonds)
    if avg_bl > 1e-6 and abs(avg_bl - target_bond_length) > 0.01:
        scale = target_bond_length / avg_bl
        for a in atoms:
            a["x"] *= scale
            a["y"] *= scale

    # Step 4 — translate so centroid lands at (center_x, center_y)
    xmin, ymin, xmax, ymax = _bounding_box(atoms)
    cx = (xmin + xmax) / 2.0
    cy = (ymin + ymax) / 2.0
    dx = center_x - cx
    dy = center_y - cy
    for a in atoms:
        a["x"] += dx
        a["y"] += dy

    return atoms, bonds


def normalize_molecule(
    molecule: Dict,
    center_x: float = 200.0,
    center_y: float = 300.0,
    flip_y: bool = True,
    target_bond_length: float = ACS_BOND_LENGTH_PT,
    strip_hydrogens: bool = True,
) -> Dict:
    """
    Convenience wrapper: take a molecule dict {"atoms": [...], "bonds": [...]}
    and return a new dict with normalised coordinates.

    Extra top-level keys (name, role, etc.) are preserved.
    """
    mol = deepcopy(molecule)
    atoms, bonds = normalize_coords(
        mol.get("atoms", []),
        mol.get("bonds", []),
        center_x=center_x,
        center_y=center_y,
        flip_y=flip_y,
        target_bond_length=target_bond_length,
        strip_hydrogens=strip_hydrogens,
    )
    mol["atoms"] = atoms
    mol["bonds"] = bonds
    return mol


def normalize_reaction(
    reactants: List[Dict],
    products: List[Dict],
    reactant_y: float = 300.0,
    product_y: float = 300.0,
    reactant_start_x: float = 50.0,
    product_start_x: float = 350.0,
    molecule_gap: float = 80.0,
    flip_y: bool = True,
    target_bond_length: float = ACS_BOND_LENGTH_PT,
    strip_hydrogens: bool = True,
) -> Tuple[List[Dict], List[Dict]]:
    """
    Normalize a set of reactant and product molecules for a reaction scheme.

    Molecules are laid out horizontally with `molecule_gap` points between
    bounding boxes.

    Returns (reactants_normalised, products_normalised).
    """
    def layout_molecules(
        mols: List[Dict],
        start_x: float,
        row_y: float,
    ) -> List[Dict]:
        result = []
        cursor_x = start_x
        for mol in mols:
            # First normalise at origin to measure the bounding box
            tmp_atoms, tmp_bonds = normalize_coords(
                mol.get("atoms", []),
                mol.get("bonds", []),
                center_x=0.0,
                center_y=0.0,
                flip_y=flip_y,
                target_bond_length=target_bond_length,
                strip_hydrogens=strip_hydrogens,
            )
            if not tmp_atoms:
                result.append(mol)
                continue
            xmin, _, xmax, _ = _bounding_box(tmp_atoms)
            half_w = (xmax - xmin) / 2.0
            cx = cursor_x + half_w
            # Now normalise for real at the correct position
            norm_atoms, norm_bonds = normalize_coords(
                mol.get("atoms", []),
                mol.get("bonds", []),
                center_x=cx,
                center_y=row_y,
                flip_y=flip_y,
                target_bond_length=target_bond_length,
                strip_hydrogens=strip_hydrogens,
            )
            new_mol = deepcopy(mol)
            new_mol["atoms"] = norm_atoms
            new_mol["bonds"] = norm_bonds
            result.append(new_mol)
            # Move cursor past this molecule's bounding box
            cursor_x = cx + half_w + molecule_gap
        return result

    norm_reactants = layout_molecules(reactants, reactant_start_x, reactant_y)
    norm_products  = layout_molecules(products,  product_start_x,  product_y)
    return norm_reactants, norm_products


# ---------------------------------------------------------------------------
# Utility: infer missing num_hydrogens from valence
# ---------------------------------------------------------------------------

def infer_hydrogens(atoms: List[Dict], bonds: List[Dict]) -> List[Dict]:
    """
    For any atom that has no explicit num_hydrogens set, calculate it from
    the default valence minus the sum of bond orders from bonds.

    This is only called for atoms that don't already have num_hydrogens.
    Returns a new list.
    """
    atoms = deepcopy(atoms)

    # Count bond-order sum per atom
    bond_order_sum: Dict[int, int] = {}
    for b in bonds:
        o = b.get("order", 1)
        for idx in (b["atom1"], b["atom2"]):
            bond_order_sum[idx] = bond_order_sum.get(idx, 0) + o

    for a in atoms:
        if "num_hydrogens" in a:
            continue  # already explicit
        sym = a.get("symbol", "C")
        if sym == "C":
            continue  # carbons get implicit Hs in ChemDraw automatically
        valence = DEFAULT_VALENCE.get(sym)
        if valence is None:
            continue
        used = bond_order_sum.get(a["index"], 0)
        nh = max(0, valence - used)
        a["num_hydrogens"] = nh

    return atoms


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Normalize atom/bond coordinates to ACS Document 1996 style.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("input", help="JSON file with {atoms, bonds} (use - for stdin)")
    p.add_argument(
        "--output", "-o",
        default="-",
        help="Output JSON file (default: stdout)",
    )
    p.add_argument(
        "--center",
        nargs=2,
        type=float,
        metavar=("X", "Y"),
        default=[200.0, 300.0],
        help="Target centre in CDXML points (default: 200 300)",
    )
    p.add_argument(
        "--no-flip-y",
        action="store_true",
        help="Do NOT flip the y-axis (use if coords are already CDXML y-down)",
    )
    p.add_argument(
        "--no-strip-h",
        action="store_true",
        help="Keep explicit hydrogen atoms",
    )
    p.add_argument(
        "--bond-length",
        type=float,
        default=ACS_BOND_LENGTH_PT,
        help=f"Target average bond length in points (default: {ACS_BOND_LENGTH_PT})",
    )
    p.add_argument(
        "--infer-h",
        action="store_true",
        help="Infer missing num_hydrogens from valence after normalisation",
    )
    p.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print output JSON",
    )
    return p


def main(argv: Optional[List[str]] = None) -> int:
    parser = _build_arg_parser()
    args = parser.parse_args(argv)

    # Read input
    if args.input == "-":
        data = json.load(sys.stdin)
    else:
        with open(args.input, encoding="utf-8") as fh:
            data = json.load(fh)

    atoms = data.get("atoms", [])
    bonds = data.get("bonds", [])

    if not atoms:
        print("WARNING: no atoms found in input", file=sys.stderr)

    atoms, bonds = normalize_coords(
        atoms,
        bonds,
        center_x=args.center[0],
        center_y=args.center[1],
        flip_y=not args.no_flip_y,
        target_bond_length=args.bond_length,
        strip_hydrogens=not args.no_strip_h,
    )

    if args.infer_h:
        atoms = infer_hydrogens(atoms, bonds)

    # Preserve any extra top-level keys
    out = {k: v for k, v in data.items() if k not in ("atoms", "bonds")}
    out["atoms"] = atoms
    out["bonds"] = bonds

    indent = 2 if args.pretty else None
    output_text = json.dumps(out, indent=indent)

    if args.output == "-":
        print(output_text)
    else:
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(output_text)
        print(f"Written to {args.output}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
