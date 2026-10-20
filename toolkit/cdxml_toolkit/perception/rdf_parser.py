#!/usr/bin/env python3
"""
SciFinder RDF Reaction Parser
Parses SciFinder .rdf reaction export files (V3000 MOL blocks) into structured JSON.

Usage:
    python rdf_parser.py reaction.rdf
    python rdf_parser.py reaction.rdf --output parsed.json
    python rdf_parser.py reaction.rdf --resolve-cas   # also resolve CAS via PubChem
    python rdf_parser.py reaction.rdf --pretty

Output: JSON with reactants, products, reagents/catalysts/solvents, conditions,
        literature references, and yield data.
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class Atom:
    """A single atom from a V3000 MOL block."""
    index: int
    symbol: str
    x: float
    y: float
    z: float
    cfg: int = 0  # stereochemistry flag (1=wedge, 2=dash, 3=either)


@dataclass
class Bond:
    """A single bond from a V3000 MOL block."""
    index: int
    order: int  # 1=single, 2=double, 3=triple
    atom1: int
    atom2: int
    cfg: int = 0  # stereo bond config


@dataclass
class StereoCollection:
    """Stereo collection from V3000 (ABS, REL, RAC)."""
    stereo_type: str  # "ABS", "REL", "RAC"
    atom_indices: List[int] = field(default_factory=list)


@dataclass
class Molecule:
    """A molecule parsed from a $MOL block."""
    name: str = ""
    formula: str = ""
    cas: str = ""
    role: str = ""  # "reactant" or "product"
    atoms: List[Atom] = field(default_factory=list)
    bonds: List[Bond] = field(default_factory=list)
    stereo: List[StereoCollection] = field(default_factory=list)


@dataclass
class ReagentEntry:
    """A reagent, catalyst, or solvent identified by CAS in $DTYPE/$DATUM."""
    cas: str = ""
    role: str = ""  # "reagent", "catalyst", "solvent"
    name: str = ""  # populated if --resolve-cas is used
    mw: Optional[float] = None
    formula: str = ""
    smiles: str = ""


@dataclass
class Reference:
    """A literature reference from the reaction record."""
    title: str = ""
    authors: str = ""
    citation: str = ""


@dataclass
class ReactionVariation:
    """One experimental variation of a reaction (SciFinder VAR block)."""
    cas_reaction_number: str = ""
    steps: int = 1
    stages: int = 1
    yield_pct: Optional[float] = None
    reagents: List[ReagentEntry] = field(default_factory=list)
    catalysts: List[ReagentEntry] = field(default_factory=list)
    solvents: List[ReagentEntry] = field(default_factory=list)
    references: List[Reference] = field(default_factory=list)
    conditions: Dict[str, str] = field(default_factory=dict)


@dataclass
class Reaction:
    """A complete parsed reaction record from an RDF file."""
    file_date: str = ""
    scheme_id: str = ""
    num_reactants: int = 0
    num_products: int = 0
    reactants: List[Molecule] = field(default_factory=list)
    products: List[Molecule] = field(default_factory=list)
    variations: List[ReactionVariation] = field(default_factory=list)


# ---------------------------------------------------------------------------
# V3000 MOL block parsing
# ---------------------------------------------------------------------------

def parse_v3000_mol(lines: List[str]) -> tuple:
    """
    Parse a V3000 MOL block into atoms, bonds, and stereo collections.

    Args:
        lines: Lines of the MOL block starting from the counts line
               (after name/formula/CAS header lines).

    Returns:
        (atoms, bonds, stereo_collections)
    """
    atoms = []
    bonds = []
    stereo = []

    in_atom = False
    in_bond = False
    in_collection = False

    for line in lines:
        stripped = line.strip()

        # Detect section boundaries
        if "BEGIN ATOM" in stripped:
            in_atom = True
            continue
        elif "END ATOM" in stripped:
            in_atom = False
            continue
        elif "BEGIN BOND" in stripped:
            in_bond = True
            continue
        elif "END BOND" in stripped:
            in_bond = False
            continue
        elif "BEGIN COLLECTION" in stripped:
            in_collection = True
            continue
        elif "END COLLECTION" in stripped:
            in_collection = False
            continue
        elif "END CTAB" in stripped or stripped == "M  END":
            break

        # Parse atoms: M  V30 index symbol x y z charge [CFG=n]
        if in_atom and stripped.startswith("M  V30"):
            parts = stripped[6:].split()
            if len(parts) >= 6:
                idx = int(parts[0])
                symbol = parts[1]
                x = float(parts[2])
                y = float(parts[3])
                z = float(parts[4])
                cfg = 0
                for p in parts[5:]:
                    if p.startswith("CFG="):
                        cfg = int(p.split("=")[1])
                atoms.append(Atom(index=idx, symbol=symbol, x=x, y=y, z=z, cfg=cfg))

        # Parse bonds: M  V30 index order atom1 atom2 [CFG=n]
        elif in_bond and stripped.startswith("M  V30"):
            parts = stripped[6:].split()
            if len(parts) >= 4:
                idx = int(parts[0])
                order = int(parts[1])
                a1 = int(parts[2])
                a2 = int(parts[3])
                cfg = 0
                for p in parts[4:]:
                    if p.startswith("CFG="):
                        cfg = int(p.split("=")[1])
                bonds.append(Bond(index=idx, order=order, atom1=a1, atom2=a2, cfg=cfg))

        # Parse stereo collections: M  V30 MDLV30/STEABS ATOMS=(1 9)
        elif in_collection and stripped.startswith("M  V30"):
            content = stripped[6:].strip()
            # Match patterns like MDLV30/STEABS ATOMS=(1 9)
            m = re.match(r'MDLV30/STE(\w+)\s+ATOMS=\((.+?)\)', content)
            if m:
                stype = m.group(1)  # ABS, REL, RAC
                atom_ids = [int(x) for x in m.group(2).split()]
                stereo.append(StereoCollection(stereo_type=stype, atom_indices=atom_ids))

    return atoms, bonds, stereo


# ---------------------------------------------------------------------------
# RDF file parsing
# ---------------------------------------------------------------------------

def parse_rdf(filepath: str) -> List[Reaction]:
    """
    Parse a SciFinder .rdf file and return a list of Reaction objects.

    The RDF format consists of:
    - $RDFILE header
    - $DATM timestamp
    - One or more reaction records starting with $RFMT
    - Each record has $RXN header, $MOL blocks, and $DTYPE/$DATUM metadata

    Args:
        filepath: Path to the .rdf file.

    Returns:
        List of Reaction objects.
    """
    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()

    reactions = []

    # Parse file header
    file_date = ""
    datm_match = re.search(r'\$DATM\s+(.+)', content)
    if datm_match:
        file_date = datm_match.group(1).strip()

    # Split into reaction records at $RFMT
    # The first chunk before any $RFMT is the file header
    rfmt_parts = re.split(r'^\$RFMT\b', content, flags=re.MULTILINE)

    for part_idx, part in enumerate(rfmt_parts):
        if part_idx == 0:
            # File header — skip
            continue

        rxn = Reaction(file_date=file_date)

        # Parse scheme ID from the $RFMT line remainder
        first_line = part.split("\n")[0].strip()
        scheme_match = re.search(r'\$RIREG\s+(\S+)', first_line)
        if scheme_match:
            rxn.scheme_id = scheme_match.group(1)

        # Find the $RXN block and count line
        rxn_match = re.search(r'\$RXN\s*\n', part)
        if not rxn_match:
            continue

        # Lines after $RXN: two blank lines, then counts line
        post_rxn = part[rxn_match.end():]
        post_lines = post_rxn.split("\n")

        # Find the counts line (first non-blank line after $RXN header lines)
        counts_line = None
        counts_line_idx = 0
        for i, line in enumerate(post_lines):
            stripped = line.strip()
            if stripped and re.match(r'^\d+\s+\d+', stripped):
                counts_line = stripped
                counts_line_idx = i
                break

        if counts_line:
            count_parts = counts_line.split()
            rxn.num_reactants = int(count_parts[0])
            rxn.num_products = int(count_parts[1])

        # Split out $MOL blocks
        mol_splits = re.split(r'^\$MOL\s*$', part, flags=re.MULTILINE)
        # mol_splits[0] = everything before first $MOL (RXN header)
        # mol_splits[1..n] = individual MOL blocks

        total_mols = rxn.num_reactants + rxn.num_products
        for mol_idx in range(1, len(mol_splits)):
            if mol_idx > total_mols:
                break

            mol_text = mol_splits[mol_idx]
            mol_lines = mol_text.strip().split("\n")

            mol = Molecule()

            # First three lines: name, formula, CAS/copyright
            if len(mol_lines) >= 1:
                mol.name = mol_lines[0].strip()
            if len(mol_lines) >= 2:
                mol.formula = mol_lines[1].strip()
            if len(mol_lines) >= 3:
                cas_line = mol_lines[2].strip()
                cas_match = re.match(r'([\d-]+)', cas_line)
                if cas_match:
                    mol.cas = cas_match.group(1)

            # Determine role
            if mol_idx <= rxn.num_reactants:
                mol.role = "reactant"
            else:
                mol.role = "product"

            # Parse V3000 CTAB — starts after the header line containing "V3000"
            ctab_start = None
            for i, line in enumerate(mol_lines):
                if "V3000" in line:
                    ctab_start = i
                    break

            if ctab_start is not None:
                atoms, bonds, stereo = parse_v3000_mol(mol_lines[ctab_start + 1:])
                mol.atoms = atoms
                mol.bonds = bonds
                mol.stereo = stereo

            if mol.role == "reactant":
                rxn.reactants.append(mol)
            else:
                rxn.products.append(mol)

        # Parse $DTYPE / $DATUM metadata
        _parse_dtype_datum(part, rxn)

        reactions.append(rxn)

    return reactions


def _parse_dtype_datum(text: str, rxn: Reaction):
    """
    Parse all $DTYPE/$DATUM pairs from a reaction record and populate
    the reaction's variation data (reagents, catalysts, solvents,
    yield, references, conditions).

    Handles multiline $DATUM values (continuation lines without $DTYPE prefix).
    """
    # Extract all DTYPE/DATUM pairs, handling multiline DATUM values
    dtype_datum_pairs = []
    lines = text.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("$DTYPE"):
            dtype = line[6:].strip()
            datum_lines = []
            i += 1
            # Collect the $DATUM line and any continuation lines
            while i < len(lines):
                dline = lines[i]
                if dline.strip().startswith("$DATUM"):
                    datum_lines.append(dline.strip()[6:].strip())
                    i += 1
                    # Continuation: lines that don't start with $ are part of this datum
                    while i < len(lines):
                        cont = lines[i]
                        if cont.strip().startswith("$"):
                            break
                        if cont.strip():
                            datum_lines.append(cont.strip())
                        i += 1
                    break
                else:
                    i += 1
            datum = " ".join(datum_lines)
            dtype_datum_pairs.append((dtype, datum))
        else:
            i += 1

    # Ensure we have at least one variation to populate
    variations = {}  # var_num -> ReactionVariation

    for dtype, datum in dtype_datum_pairs:
        # Direct reactant/product CAS: RXN:RCT(n):CAS_RN, RXN:PRO(n):CAS_RN
        # These are already captured in the MOL blocks, but we verify here

        # Variation-level data: RXN:VAR(n):...
        var_match = re.match(r'RXN:VAR\((\d+)\):(.+)', dtype)
        if var_match:
            var_num = int(var_match.group(1))
            var_key = var_match.group(2)

            if var_num not in variations:
                variations[var_num] = ReactionVariation()
            var = variations[var_num]

            # Yield: PRO(n):YIELD
            yield_match = re.match(r'PRO\(\d+\):YIELD', var_key)
            if yield_match:
                try:
                    var.yield_pct = float(datum)
                except ValueError:
                    var.yield_pct = None
                continue

            # CAS Reaction Number
            if var_key == "CAS_Reaction_Number":
                var.cas_reaction_number = datum
                continue

            # Steps / Stages
            if var_key == "STEPS":
                try:
                    var.steps = int(datum)
                except ValueError:
                    pass
                continue
            if var_key == "STAGES":
                try:
                    var.stages = int(datum)
                except ValueError:
                    pass
                continue

            # Reagents: RGT(n):CAS_RN
            rgt_match = re.match(r'RGT\((\d+)\):CAS_RN', var_key)
            if rgt_match:
                var.reagents.append(ReagentEntry(cas=datum, role="reagent"))
                continue

            # Catalysts: CAT(n):CAS_RN
            cat_match = re.match(r'CAT\((\d+)\):CAS_RN', var_key)
            if cat_match:
                var.catalysts.append(ReagentEntry(cas=datum, role="catalyst"))
                continue

            # Solvents: SOL(n):CAS_RN
            sol_match = re.match(r'SOL\((\d+)\):CAS_RN', var_key)
            if sol_match:
                var.solvents.append(ReagentEntry(cas=datum, role="solvent"))
                continue

            # References: REFERENCE(n):TITLE / AUTHOR / CITATION
            ref_match = re.match(r'REFERENCE\((\d+)\):(\w+)', var_key)
            if ref_match:
                ref_num = int(ref_match.group(1))
                ref_field = ref_match.group(2).upper()
                # Ensure we have enough reference objects
                while len(var.references) < ref_num:
                    var.references.append(Reference())
                ref = var.references[ref_num - 1]
                if ref_field == "TITLE":
                    ref.title = datum
                elif ref_field == "AUTHOR":
                    ref.authors = datum
                elif ref_field == "CITATION":
                    ref.citation = datum
                continue

            # Temperature, time, pressure, pH, etc.
            cond_match = re.match(r'COND\((\d+)\):(.+)', var_key)
            if cond_match:
                cond_key = cond_match.group(2)
                var.conditions[cond_key] = datum
                continue

            # Anything else — store as generic condition
            # e.g. TEMP, TIME, PRESSURE from some exports
            if var_key in ("TEMP", "TIME", "PRESSURE", "PH", "ATMOSPHERE"):
                var.conditions[var_key] = datum
                continue

    # Add all variations sorted by var number
    for var_num in sorted(variations.keys()):
        rxn.variations.append(variations[var_num])


# ---------------------------------------------------------------------------
# CAS resolution (optional, delegates to cas_resolver.py)
# ---------------------------------------------------------------------------

def resolve_cas_numbers(reaction: Reaction) -> None:
    """
    Resolve all CAS numbers in the reaction using cas_resolver.
    Populates name, MW, formula, SMILES for reagents/catalysts/solvents.
    """
    try:
        from ..resolve.cas_resolver import resolve_cas
    except ImportError:
        print("Warning: cas_resolver.py not found. Skipping CAS resolution.",
              file=sys.stderr)
        return

    # Resolve reagents, catalysts, solvents in all variations
    for var in reaction.variations:
        for entry_list in [var.reagents, var.catalysts, var.solvents]:
            for entry in entry_list:
                if entry.cas:
                    result = resolve_cas(entry.cas)
                    if result:
                        entry.name = result.get("name", "")
                        entry.mw = result.get("mw")
                        entry.formula = result.get("formula", "")
                        entry.smiles = result.get("smiles", "")


# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------

def reaction_to_dict(rxn: Reaction) -> Dict[str, Any]:
    """Convert a Reaction dataclass to a clean dictionary for JSON output."""

    def mol_to_dict(mol: Molecule) -> Dict[str, Any]:
        d = {
            "name": mol.name,
            "formula": mol.formula,
            "cas": mol.cas,
            "role": mol.role,
            "atom_count": len(mol.atoms),
            "bond_count": len(mol.bonds),
            "atoms": [
                {
                    "index": a.index,
                    "symbol": a.symbol,
                    "x": a.x,
                    "y": a.y,
                    "z": a.z,
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
        if mol.stereo:
            d["stereo"] = [
                {"type": s.stereo_type, "atoms": s.atom_indices}
                for s in mol.stereo
            ]
        return d

    def entry_to_dict(e: ReagentEntry) -> Dict[str, Any]:
        d = {"cas": e.cas, "role": e.role}
        if e.name:
            d["name"] = e.name
        if e.mw is not None:
            d["mw"] = e.mw
        if e.formula:
            d["formula"] = e.formula
        if e.smiles:
            d["smiles"] = e.smiles
        return d

    def ref_to_dict(r: Reference) -> Dict[str, Any]:
        d = {}
        if r.title:
            d["title"] = r.title
        if r.authors:
            d["authors"] = r.authors
        if r.citation:
            d["citation"] = r.citation
        return d

    result = {
        "file_date": rxn.file_date,
        "scheme_id": rxn.scheme_id,
        "num_reactants": rxn.num_reactants,
        "num_products": rxn.num_products,
        "reactants": [mol_to_dict(m) for m in rxn.reactants],
        "products": [mol_to_dict(m) for m in rxn.products],
        "variations": [],
    }

    for var in rxn.variations:
        v = {}
        if var.cas_reaction_number:
            v["cas_reaction_number"] = var.cas_reaction_number
        v["steps"] = var.steps
        v["stages"] = var.stages
        if var.yield_pct is not None:
            v["yield_pct"] = var.yield_pct
        if var.reagents:
            v["reagents"] = [entry_to_dict(e) for e in var.reagents]
        if var.catalysts:
            v["catalysts"] = [entry_to_dict(e) for e in var.catalysts]
        if var.solvents:
            v["solvents"] = [entry_to_dict(e) for e in var.solvents]
        if var.references:
            v["references"] = [ref_to_dict(r) for r in var.references]
        if var.conditions:
            v["conditions"] = var.conditions
        result["variations"].append(v)

    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Parse SciFinder .rdf reaction exports into structured JSON."
    )
    parser.add_argument(
        "rdf_file",
        help="Path to the SciFinder .rdf file",
    )
    parser.add_argument(
        "--output", "-o",
        help="Output JSON file (default: print to stdout)",
    )
    parser.add_argument(
        "--resolve-cas",
        action="store_true",
        help="Resolve reagent/catalyst/solvent CAS numbers via PubChem "
             "(requires cas_resolver.py)",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output",
    )
    args = parser.parse_args(argv)

    # Parse
    reactions = parse_rdf(args.rdf_file)

    if not reactions:
        print(f"No reactions found in {args.rdf_file}", file=sys.stderr)
        return 1

    print(f"Parsed {len(reactions)} reaction(s) from {args.rdf_file}",
          file=sys.stderr)

    # Optionally resolve CAS numbers
    if args.resolve_cas:
        for rxn in reactions:
            resolve_cas_numbers(rxn)

    # Convert to JSON
    if len(reactions) == 1:
        output = reaction_to_dict(reactions[0])
    else:
        output = [reaction_to_dict(r) for r in reactions]

    indent = 2 if args.pretty else None
    json_str = json.dumps(output, indent=indent, ensure_ascii=False)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(json_str)
            f.write("\n")
        print(f"Written to {args.output}", file=sys.stderr)
    else:
        print(json_str)

    return 0


if __name__ == "__main__":
    sys.exit(main())
