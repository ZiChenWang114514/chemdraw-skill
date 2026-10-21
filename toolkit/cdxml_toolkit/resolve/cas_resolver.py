#!/usr/bin/env python3
"""
CAS Number Resolver via PubChem PUG REST API
Resolves CAS numbers to compound name, MW, molecular formula, SMILES,
and optionally 2D coordinates.

Usage:
    python cas_resolver.py 534-17-8
    python cas_resolver.py 534-17-8 51364-51-3 98327-87-8 123-91-1
    python cas_resolver.py 534-17-8 --coords --output result.json
    python cas_resolver.py --batch cas_list.txt --pretty

PubChem API docs:
    https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{CAS}/...
"""

import argparse
import json
import sys
import time
import urllib.request
import urllib.error
from typing import Dict, Any, List, Optional

# ---------------------------------------------------------------------------
# PubChem API base
# ---------------------------------------------------------------------------

PUBCHEM_BASE = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"

# Properties to request in a single call
PROPERTIES = "IUPACName,MolecularWeight,MolecularFormula,CanonicalSMILES,IsomericSMILES"

# Rate limiting: PubChem asks for max 5 requests/second
REQUEST_DELAY = 0.25  # seconds between requests


# ---------------------------------------------------------------------------
# Core resolution function (importable by other tools)
# ---------------------------------------------------------------------------

def resolve_cas(cas: str, include_coords: bool = False) -> Optional[Dict[str, Any]]:
    """
    Resolve a single CAS number via PubChem PUG REST.

    Args:
        cas: CAS registry number (e.g. "534-17-8").
        include_coords: If True, also fetch 2D atom coordinates.

    Returns:
        Dict with keys: cas, name, mw, formula, smiles, isomeric_smiles,
        and optionally coords_2d. Returns None if the lookup fails.
    """
    if not cas or not _validate_cas(cas):
        return None

    # Step 1: Get compound properties
    props = _fetch_properties(cas)
    if props is None:
        return None

    result = {
        "cas": cas,
        "name": props.get("IUPACName", ""),
        "mw": props.get("MolecularWeight"),
        "formula": props.get("MolecularFormula", ""),
        "smiles": (props.get("IsomericSMILES")
                   or props.get("CanonicalSMILES")
                   or props.get("SMILES")
                   or props.get("ConnectivitySMILES", "")),
        "isomeric_smiles": (props.get("IsomericSMILES")
                            or props.get("SMILES", "")),
        "cid": props.get("CID"),
    }

    # Convert MW to float
    if result["mw"] is not None:
        try:
            result["mw"] = float(result["mw"])
        except (ValueError, TypeError):
            pass

    # Step 2: Optionally get 2D coordinates
    if include_coords and result.get("cid"):
        coords = _fetch_2d_coords(result["cid"])
        if coords:
            result["coords_2d"] = coords

    return result


# ---------------------------------------------------------------------------
# PubChem API helpers
# ---------------------------------------------------------------------------

def _validate_cas(cas: str) -> bool:
    """
    Validate CAS number format (digits-digits-digit with check digit).

    CAS format: up to 10 digits as XXX...X-YY-Z where Z is a check digit.
    """
    import re
    if not re.match(r'^\d{2,7}-\d{2}-\d$', cas):
        return False

    # Verify check digit
    digits_only = cas.replace("-", "")
    check = int(digits_only[-1])
    body = digits_only[:-1]
    total = sum(int(d) * (i + 1) for i, d in enumerate(reversed(body)))
    return total % 10 == check


def _fetch_properties(cas: str) -> Optional[Dict[str, Any]]:
    """Fetch compound properties from PubChem by CAS number."""
    url = f"{PUBCHEM_BASE}/compound/name/{cas}/property/{PROPERTIES}/JSON"

    try:
        req = urllib.request.Request(url)
        req.add_header("User-Agent", "chem-tools/1.0 (cas_resolver.py)")
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            props_list = data.get("PropertyTable", {}).get("Properties", [])
            if props_list:
                return props_list[0]
    except urllib.error.HTTPError as e:
        if e.code == 404:
            print(f"  CAS {cas}: not found in PubChem", file=sys.stderr)
        else:
            print(f"  CAS {cas}: HTTP error {e.code}", file=sys.stderr)
    except urllib.error.URLError as e:
        print(f"  CAS {cas}: connection error — {e.reason}", file=sys.stderr)
    except Exception as e:
        print(f"  CAS {cas}: unexpected error — {e}", file=sys.stderr)

    return None


def _fetch_2d_coords(cid: int) -> Optional[Dict[str, Any]]:
    """
    Fetch 2D atom coordinates from PubChem SDF and parse into a dict.

    Returns:
        Dict with 'atoms' list of {symbol, x, y} and 'bonds' list of
        {atom1, atom2, order}.
    """
    url = f"{PUBCHEM_BASE}/compound/cid/{cid}/record/SDF/?record_type=2d"

    try:
        req = urllib.request.Request(url)
        req.add_header("User-Agent", "chem-tools/1.0 (cas_resolver.py)")
        with urllib.request.urlopen(req, timeout=15) as resp:
            sdf_text = resp.read().decode("utf-8")
            return _parse_sdf_coords(sdf_text)
    except Exception as e:
        print(f"  CID {cid}: could not fetch 2D coords — {e}", file=sys.stderr)
        return None


def _parse_sdf_coords(sdf_text: str) -> Optional[Dict[str, Any]]:
    """
    Parse atom coordinates and bonds from an SDF/MOL block.
    Handles both V2000 and V3000 formats.
    """
    lines = sdf_text.strip().split("\n")

    atoms = []
    bonds = []

    # Find counts line (line 4 in V2000, or look for V3000 marker)
    if any("V3000" in line for line in lines[:10]):
        return _parse_v3000_sdf(lines)

    # V2000 parsing
    counts_line = None
    counts_idx = None
    for i, line in enumerate(lines):
        if "V2000" in line:
            counts_line = line
            counts_idx = i
            break

    if counts_line is None or counts_idx is None:
        return None

    # Parse counts
    num_atoms = int(counts_line[:3].strip())
    num_bonds = int(counts_line[3:6].strip())

    # Atom block starts right after counts line
    for i in range(counts_idx + 1, counts_idx + 1 + num_atoms):
        if i >= len(lines):
            break
        parts = lines[i].split()
        if len(parts) >= 4:
            x = float(parts[0])
            y = float(parts[1])
            symbol = parts[3]
            atoms.append({"symbol": symbol, "x": round(x, 4), "y": round(y, 4)})

    # Bond block
    bond_start = counts_idx + 1 + num_atoms
    for i in range(bond_start, bond_start + num_bonds):
        if i >= len(lines):
            break
        parts = lines[i].split()
        if len(parts) >= 3:
            a1 = int(parts[0])
            a2 = int(parts[1])
            order = int(parts[2])
            bonds.append({"atom1": a1, "atom2": a2, "order": order})

    if not atoms:
        return None

    return {"atoms": atoms, "bonds": bonds}


def _parse_v3000_sdf(lines: List[str]) -> Optional[Dict[str, Any]]:
    """Parse V3000 format SDF for 2D coords."""
    atoms = []
    bonds = []
    in_atom = False
    in_bond = False

    for line in lines:
        stripped = line.strip()
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

        if in_atom and stripped.startswith("M  V30"):
            parts = stripped[6:].split()
            if len(parts) >= 5:
                symbol = parts[1]
                x = float(parts[2])
                y = float(parts[3])
                atoms.append({"symbol": symbol, "x": round(x, 4), "y": round(y, 4)})

        elif in_bond and stripped.startswith("M  V30"):
            parts = stripped[6:].split()
            if len(parts) >= 4:
                order = int(parts[1])
                a1 = int(parts[2])
                a2 = int(parts[3])
                bonds.append({"atom1": a1, "atom2": a2, "order": order})

    if not atoms:
        return None
    return {"atoms": atoms, "bonds": bonds}


# ---------------------------------------------------------------------------
# Batch resolution
# ---------------------------------------------------------------------------

def resolve_batch(cas_list: List[str], include_coords: bool = False,
                  delay: float = REQUEST_DELAY) -> List[Dict[str, Any]]:
    """
    Resolve a list of CAS numbers with rate limiting.

    Args:
        cas_list: List of CAS numbers.
        include_coords: Whether to fetch 2D coordinates.
        delay: Seconds between API requests.

    Returns:
        List of result dicts (None entries for failed lookups are excluded).
    """
    results = []
    for i, cas in enumerate(cas_list):
        cas = cas.strip()
        if not cas:
            continue
        print(f"Resolving {cas} ({i+1}/{len(cas_list)})...", file=sys.stderr)
        result = resolve_cas(cas, include_coords=include_coords)
        if result:
            results.append(result)
        else:
            results.append({"cas": cas, "error": "not found or lookup failed"})
        if i < len(cas_list) - 1:
            time.sleep(delay)
    return results


# ---------------------------------------------------------------------------
# Name → SMILES lookup (common name, abbreviation, or IUPAC)
# ---------------------------------------------------------------------------

_last_request_time: float = 0.0


def _rate_limit() -> None:
    """Enforce PubChem rate limit (max 5 req/sec) across all calls."""
    global _last_request_time
    elapsed = time.time() - _last_request_time
    if elapsed < REQUEST_DELAY:
        time.sleep(REQUEST_DELAY - elapsed)
    _last_request_time = time.time()


def resolve_name_to_smiles(name: str) -> Optional[str]:
    """
    Resolve a chemical name to a canonical SMILES via PubChem PUG REST.

    Works with common names, trade names, and abbreviations
    (e.g. "BINAP", "Cs2CO3", "dioxane", "triethylamine").

    Returns a SMILES string, or None on failure.
    """
    import urllib.parse

    _rate_limit()
    encoded = urllib.parse.quote(name, safe="")
    # Request IsomericSMILES (preserves isotopes, stereochemistry) with
    # CanonicalSMILES as fallback.
    url = (f"{PUBCHEM_BASE}/compound/name/{encoded}"
           f"/property/IsomericSMILES,CanonicalSMILES/JSON")

    try:
        req = urllib.request.Request(url)
        req.add_header("User-Agent", "chem-tools/1.0 (cas_resolver.py)")
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            props = data.get("PropertyTable", {}).get("Properties", [])
            if props:
                p = props[0]
                # Prefer IsomericSMILES — preserves isotope labels (e.g.
                # deuterium in deucravacitinib) and stereochemistry.
                smiles = (p.get("IsomericSMILES")
                          or p.get("CanonicalSMILES")
                          or p.get("SMILES")
                          or p.get("ConnectivitySMILES"))
                if smiles:
                    return smiles
    except urllib.error.HTTPError as e:
        if e.code != 404:
            print(f"  PubChem name lookup '{name}': HTTP {e.code}",
                  file=sys.stderr)
    except urllib.error.URLError as e:
        print(f"  PubChem name lookup '{name}': connection error — {e.reason}",
              file=sys.stderr)
    except Exception as e:
        print(f"  PubChem name lookup '{name}': error — {e}", file=sys.stderr)

    return None


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Resolve CAS numbers to compound info via PubChem API."
    )
    parser.add_argument(
        "cas_numbers",
        nargs="*",
        help="One or more CAS numbers to resolve (e.g. 534-17-8 123-91-1)",
    )
    parser.add_argument(
        "--batch", "-b",
        help="Text file with one CAS number per line",
    )
    parser.add_argument(
        "--coords",
        action="store_true",
        help="Also fetch 2D atom coordinates from PubChem",
    )
    parser.add_argument(
        "--output", "-o",
        help="Output JSON file (default: print to stdout)",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output",
    )
    args = parser.parse_args(argv)

    # Collect CAS numbers from args and/or batch file
    cas_list = list(args.cas_numbers) if args.cas_numbers else []

    if args.batch:
        with open(args.batch, "r") as f:
            for line in f:
                cas = line.strip()
                if cas and not cas.startswith("#"):
                    cas_list.append(cas)

    if not cas_list:
        parser.error("No CAS numbers provided. Use positional args or --batch.")

    # Resolve
    if len(cas_list) == 1:
        result = resolve_cas(cas_list[0], include_coords=args.coords)
        if result is None:
            print(f"Could not resolve CAS {cas_list[0]}", file=sys.stderr)
            return 1
        output = result
    else:
        output = resolve_batch(cas_list, include_coords=args.coords)

    # Output
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
