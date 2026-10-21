#!/usr/bin/env python3
"""
ChemScript 32-bit subprocess server.

This script runs under the 32-bit chemscript32 conda environment and provides
JSON-based RPC access to the ChemScript .NET DLL. It reads JSON commands from
stdin (one per line) and writes JSON responses to stdout.

NOT intended for direct use — called by chemscript_bridge.py.
"""

import json
import os
import sys
import traceback

# ---------------------------------------------------------------------------
# Bootstrap: load .NET runtime and ChemScript DLL
# ---------------------------------------------------------------------------

# Accept --dll-dir and --assembly from chemscript_bridge.py to support
# different ChemDraw versions (e.g. ChemOffice2015 vs ChemOffice2016).
_dll_dir_arg = None
_assembly_arg = None
_remaining = []
_args = sys.argv[1:]
_i = 0
while _i < len(_args):
    if _args[_i] == "--dll-dir" and _i + 1 < len(_args):
        _dll_dir_arg = _args[_i + 1]
        _i += 2
    elif _args[_i] == "--assembly" and _i + 1 < len(_args):
        _assembly_arg = _args[_i + 1]
        _i += 2
    else:
        _remaining.append(_args[_i])
        _i += 1
sys.argv = [sys.argv[0]] + _remaining

DLL_DIR = _dll_dir_arg or os.environ.get("CHEMSCRIPT_DLL_DIR") or os.path.join(
    os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)"),
    "PerkinElmerInformatics", "ChemOffice2016", "ChemScript", "Lib", "Net",
)

ASSEMBLY = _assembly_arg or os.environ.get("CHEMSCRIPT_ASSEMBLY") or "CambridgeSoft.ChemScript16"

# Suppress the ChemScript welcome banner (goes to stderr)
_real_stderr = sys.stderr
sys.stderr = open(os.devnull, "w")

# Add DLL_DIR to Python path for the managed assembly (.NET DLL)
sys.path.insert(0, DLL_DIR)

# Also add DLL_DIR (and its parent) to the Windows PATH so the native
# ChemScript engine DLL (e.g. ChemScript160.dll) can be found at runtime.
# When DLLs are bundled in a flat directory (portable deployment), both the
# managed and native DLLs live in the same folder.
_dll_parent = os.path.dirname(DLL_DIR.rstrip(os.sep))
_extra_paths = os.pathsep.join(p for p in [DLL_DIR, _dll_parent] if os.path.isdir(p))
os.environ["PATH"] = _extra_paths + os.pathsep + os.environ.get("PATH", "")

from pythonnet import load as _load_runtime

_load_runtime("netfx")
import clr

clr.AddReference(ASSEMBLY)
_cs_module = __import__(ASSEMBLY, fromlist=["StructureData", "ReactionData"])
StructureData = _cs_module.StructureData
ReactionData = _cs_module.ReactionData

# Restore stderr
sys.stderr = _real_stderr

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Extension-to-mimetype mapping for WriteFile when format isn't obvious
EXT_MIME = {
    ".cdxml": "text/xml",
    ".cdx": "chemical/x-cdx",
    ".mol": "chemical/x-mdl-molfile",
    ".sdf": "chemical/x-mdl-molfile",
    ".rxn": "chemical/x-mdl-rxn",
    ".smi": "chemical/x-smiles",
    ".smiles": "chemical/x-smiles",
    ".inchi": "chemical/x-inchi",
}

# Short alias → full mimetype
MIME_ALIASES = {
    "cdxml": "text/xml",
    "cdx": "chemical/x-cdx",
    "smiles": "chemical/x-smiles",
    "smi": "chemical/x-smiles",
    "inchi": "chemical/x-inchi",
    "name": "chemical/x-name",
    "mol": "chemical/x-mdl-molfile",
    "molv3": "chemical/x-mdl-molfile-v3000",
    "rxn": "chemical/x-mdl-rxn",
    "rxnv3": "chemical/x-mdl-rxn-v3000",
    "cml": "chemical/x-cml",
}


def resolve_mime(fmt: str) -> str:
    """Resolve a short alias or extension to a full mimetype."""
    if "/" in fmt:
        return fmt
    return MIME_ALIASES.get(fmt.lower().lstrip("."), fmt)


def _load_structure(source: str, fmt: str = None) -> StructureData:
    """Load a StructureData from file path or data string."""
    if os.path.isfile(source):
        if fmt:
            m = StructureData()
            m.ReadFile(source)
            return m
        return StructureData.LoadFile(source)
    else:
        mime = resolve_mime(fmt) if fmt else None
        if mime:
            return StructureData.LoadData(source, mime)
        return StructureData.LoadData(source)


def _load_reaction(source: str, fmt: str = None):
    """Load a ReactionData from file path or data string."""
    if os.path.isfile(source):
        return ReactionData.LoadFile(source)
    else:
        mime = resolve_mime(fmt) if fmt else "chemical/x-smiles"
        return ReactionData.LoadData(source, mime)


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------


def cmd_convert(args: dict) -> dict:
    """Convert a file from one format to another."""
    input_path = args["input"]
    output_path = args["output"]

    # Try loading as structure first, then as reaction
    m = StructureData.LoadFile(input_path)
    if m is not None:
        m.WriteFile(output_path)
        return {"ok": True, "type": "structure", "formula": m.Formula()}

    r = ReactionData.LoadFile(input_path)
    if r is not None:
        r.WriteFile(output_path)
        return {"ok": True, "type": "reaction", "formula": r.Formula()}

    return {"ok": False, "error": f"Could not load: {input_path}"}


def cmd_name_to_cdxml(args: dict) -> dict:
    """Convert a chemical name to CDXML string."""
    name = args["name"]
    m = StructureData.LoadData(name, "chemical/x-name")
    if m is None:
        return {"ok": False, "error": f"Could not resolve name: {name}"}
    m.CleanupStructure()
    cdxml = m.WriteData("text/xml")
    smiles = m.WriteData("chemical/x-smiles")
    formula = m.Formula()
    output = args.get("output")
    if output:
        m.WriteFile(output)
    return {"ok": True, "cdxml": cdxml, "smiles": smiles, "formula": formula}


def cmd_smiles_to_cdxml(args: dict) -> dict:
    """Convert a SMILES string to CDXML."""
    smi = args["smiles"]
    m = StructureData.LoadData(smi, "chemical/x-smiles")
    if m is None:
        return {"ok": False, "error": f"Could not parse SMILES: {smi}"}
    m.CleanupStructure()
    cdxml = m.WriteData("text/xml")
    formula = m.Formula()
    output = args.get("output")
    if output:
        m.WriteFile(output)
    return {"ok": True, "cdxml": cdxml, "smiles": smi, "formula": formula}


def cmd_cleanup(args: dict) -> dict:
    """Clean up a structure file (normalize coordinates, bond lengths)."""
    input_path = args["input"]
    output_path = args.get("output", input_path)
    m = StructureData.LoadFile(input_path)
    if m is None:
        return {"ok": False, "error": f"Could not load: {input_path}"}
    m.CleanupStructure()
    m.WriteFile(output_path)
    return {"ok": True, "formula": m.Formula()}


def cmd_get_info(args: dict) -> dict:
    """Get chemical information about a structure file or string."""
    source = args["source"]
    fmt = args.get("format")

    # Try as structure
    m = _load_structure(source, fmt)
    if m is not None:
        result = {
            "ok": True,
            "type": "structure",
            "formula": m.Formula(),
            "smiles": m.WriteData("chemical/x-smiles"),
        }
        try:
            result["name"] = m.ChemicalName()
        except Exception:
            result["name"] = None
        try:
            result["inchi"] = m.WriteData("chemical/x-inchi")
        except Exception:
            result["inchi"] = None

        # Count atoms and bonds
        atom_count = 0
        bond_count = 0
        for _ in m.Atoms:
            atom_count += 1
        for _ in m.Bonds:
            bond_count += 1
        result["atom_count"] = atom_count
        result["bond_count"] = bond_count
        return result

    # Try as reaction
    r = _load_reaction(source, fmt)
    if r is not None:
        reactants = []
        for rct in r.Reactants:
            info = {"smiles": rct.WriteData("chemical/x-smiles"), "formula": rct.Formula()}
            try:
                info["name"] = rct.ChemicalName()
            except Exception:
                info["name"] = None
            reactants.append(info)
        products = []
        for prod in r.Products:
            info = {"smiles": prod.WriteData("chemical/x-smiles"), "formula": prod.Formula()}
            try:
                info["name"] = prod.ChemicalName()
            except Exception:
                info["name"] = None
            products.append(info)
        return {
            "ok": True,
            "type": "reaction",
            "formula": r.Formula(),
            "reactants": reactants,
            "products": products,
        }

    return {"ok": False, "error": f"Could not load: {source}"}


def cmd_contains_substructure(args: dict) -> dict:
    """Check if target contains query substructure."""
    target = _load_structure(args["target"], args.get("target_format"))
    query = _load_structure(args["query"], args.get("query_format"))
    if target is None:
        return {"ok": False, "error": f"Could not load target: {args['target']}"}
    if query is None:
        return {"ok": False, "error": f"Could not load query: {args['query']}"}
    result = target.ContainsSubstructure(query)
    return {"ok": True, "contains": bool(result)}


def cmd_substructure_search(args: dict) -> dict:
    """Perform atom-by-atom substructure search."""
    target = _load_structure(args["target"], args.get("target_format"))
    query = _load_structure(args["query"], args.get("query_format"))
    if target is None:
        return {"ok": False, "error": f"Could not load target: {args['target']}"}
    if query is None:
        return {"ok": False, "error": f"Could not load query: {args['query']}"}

    maps = query.AtomByAtomSearch(target)
    all_maps = []
    for atom_map in maps:
        mapping = {}
        for atom in atom_map.Keys:
            mapping[atom.Name] = atom_map[atom].Name
        all_maps.append(mapping)
    return {"ok": True, "contains": len(all_maps) > 0, "maps": all_maps}


def cmd_get_name(args: dict) -> dict:
    """Get IUPAC name for a structure."""
    m = _load_structure(args["source"], args.get("format"))
    if m is None:
        return {"ok": False, "error": f"Could not load: {args['source']}"}
    try:
        name = m.ChemicalName()
        return {"ok": True, "name": name}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def cmd_get_formula(args: dict) -> dict:
    """Get molecular formula for a structure."""
    m = _load_structure(args["source"], args.get("format"))
    if m is None:
        return {"ok": False, "error": f"Could not load: {args['source']}"}
    return {"ok": True, "formula": m.Formula()}


def cmd_write_data(args: dict) -> dict:
    """Convert a structure to a specific format string."""
    m = _load_structure(args["source"], args.get("source_format"))
    if m is None:
        return {"ok": False, "error": f"Could not load: {args['source']}"}
    mime = resolve_mime(args["target_format"])
    data = m.WriteData(mime)
    return {"ok": True, "data": data}


def cmd_load_reaction(args: dict) -> dict:
    """Load a reaction and return component information."""
    r = _load_reaction(args["source"], args.get("format"))
    if r is None:
        return {"ok": False, "error": f"Could not load reaction: {args['source']}"}

    reactants = []
    for rct in r.Reactants:
        info = {
            "smiles": rct.WriteData("chemical/x-smiles"),
            "formula": rct.Formula(),
        }
        try:
            info["name"] = rct.ChemicalName()
        except Exception:
            info["name"] = None
        if args.get("include_cdxml"):
            rct.CleanupStructure()
            info["cdxml"] = rct.WriteData("text/xml")
        reactants.append(info)

    products = []
    for prod in r.Products:
        info = {
            "smiles": prod.WriteData("chemical/x-smiles"),
            "formula": prod.Formula(),
        }
        try:
            info["name"] = prod.ChemicalName()
        except Exception:
            info["name"] = None
        if args.get("include_cdxml"):
            prod.CleanupStructure()
            info["cdxml"] = prod.WriteData("text/xml")
        products.append(info)

    result = {
        "ok": True,
        "formula": r.Formula(),
        "reactants": reactants,
        "products": products,
    }

    output = args.get("output")
    if output:
        r.WriteFile(output)

    return result


def cmd_largest_common_substructure(args: dict) -> dict:
    """Find the largest common substructure between two molecules."""
    from CambridgeSoft.ChemScript16 import LargestCommonSubstructure

    m1 = _load_structure(args["mol1"], args.get("mol1_format"))
    m2 = _load_structure(args["mol2"], args.get("mol2_format"))
    if m1 is None:
        return {"ok": False, "error": f"Could not load mol1: {args['mol1']}"}
    if m2 is None:
        return {"ok": False, "error": f"Could not load mol2: {args['mol2']}"}

    common = LargestCommonSubstructure.Compute(m1, m2)
    if common is None:
        return {"ok": True, "atom_map": []}

    atom_map1 = common.AtomMapM1()
    atom_map2 = common.AtomMapM2()
    mapping = []
    for atom in atom_map1.Keys:
        mapping.append({
            "common": atom.Name,
            "mol1": atom_map1[atom].Name,
            "mol2": atom_map2[atom].Name,
        })
    return {"ok": True, "atom_map": mapping, "common_atom_count": len(mapping)}


def cmd_overlay(args: dict) -> dict:
    """Overlay (2D-align) a molecule onto a reference molecule.

    Args:
        source: CDXML string or file path of the molecule to align.
        target: CDXML string or file path of the reference molecule.
        source_format: optional format hint for source (default: auto).
        target_format: optional format hint for target (default: auto).

    Returns:
        aligned_cdxml: CDXML string of the aligned molecule.
        success: whether the overlay succeeded.
    """
    source = args["source"]
    target = args["target"]
    src_fmt = args.get("source_format")
    tgt_fmt = args.get("target_format")

    m = _load_structure(source, src_fmt)
    if m is None:
        return {"ok": False, "error": "Could not load source structure"}
    t = _load_structure(target, tgt_fmt)
    if t is None:
        return {"ok": False, "error": "Could not load target structure"}

    success = bool(m.Overlay(t))
    aligned_cdxml = m.WriteData("text/xml")
    return {"ok": True, "aligned_cdxml": aligned_cdxml, "success": success}


def cmd_substructure_align(args: dict) -> dict:
    """Align a query (small molecule) to its substructure match in a target.

    Uses ChemScript to convert both structures to SMILES, then returns
    the SMILES + target CDXML so the caller can do substructure matching
    (e.g. via RDKit) to find the atom mapping.

    This avoids the ChemScript atom-name-mismatch problem entirely.

    Args:
        query: CDXML string or file path of the small molecule (reagent).
        target: CDXML string or file path of the large molecule (product).

    Returns:
        ok, contains, query_smiles, target_smiles, target_cdxml
    """
    target = _load_structure(args["target"], args.get("target_format"))
    query = _load_structure(args["query"], args.get("query_format"))
    if target is None:
        return {"ok": False, "error": "Could not load target"}
    if query is None:
        return {"ok": False, "error": "Could not load query"}

    # Check if query is a substructure of target
    maps = query.AtomByAtomSearch(target)
    contains = bool(maps and len(maps) > 0)

    # Always return MOL blocks + CDXML (caller may need them for MCS fallback)
    query_mol = query.WriteData("chemical/x-mdl-molfile")
    target_mol = target.WriteData("chemical/x-mdl-molfile")
    target_cdxml = target.WriteData("text/xml")
    query_cdxml = query.WriteData("text/xml")

    return {
        "ok": True,
        "contains": contains,
        "query_mol": query_mol,
        "target_mol": target_mol,
        "target_cdxml": target_cdxml,
        "query_cdxml": query_cdxml,
    }


def cmd_mimetypes(args: dict) -> dict:
    """List all supported mimetypes."""
    types = list(StructureData.MimeTypes())
    return {"ok": True, "mimetypes": types}


def cmd_ping(args: dict) -> dict:
    """Health check."""
    return {"ok": True, "message": "ChemScript server ready"}


# ---------------------------------------------------------------------------
# Dispatch table
# ---------------------------------------------------------------------------

COMMANDS = {
    "ping": cmd_ping,
    "convert": cmd_convert,
    "name_to_cdxml": cmd_name_to_cdxml,
    "smiles_to_cdxml": cmd_smiles_to_cdxml,
    "cleanup": cmd_cleanup,
    "get_info": cmd_get_info,
    "get_name": cmd_get_name,
    "get_formula": cmd_get_formula,
    "contains_substructure": cmd_contains_substructure,
    "substructure_search": cmd_substructure_search,
    "write_data": cmd_write_data,
    "load_reaction": cmd_load_reaction,
    "largest_common_substructure": cmd_largest_common_substructure,
    "overlay": cmd_overlay,
    "substructure_align": cmd_substructure_align,
    "mimetypes": cmd_mimetypes,
}

# ---------------------------------------------------------------------------
# Main loop — reads JSON lines from stdin, writes JSON lines to stdout
# ---------------------------------------------------------------------------


def main():
    # Signal readiness
    sys.stdout.write(json.dumps({"ready": True}) + "\n")
    sys.stdout.flush()

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
        except json.JSONDecodeError as e:
            response = {"ok": False, "error": f"Invalid JSON: {e}"}
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()
            continue

        cmd = request.get("cmd")
        args = request.get("args", {})

        if cmd == "quit":
            sys.stdout.write(json.dumps({"ok": True, "message": "bye"}) + "\n")
            sys.stdout.flush()
            break

        handler = COMMANDS.get(cmd)
        if handler is None:
            response = {"ok": False, "error": f"Unknown command: {cmd}"}
        else:
            try:
                response = handler(args)
            except Exception as e:
                response = {
                    "ok": False,
                    "error": str(e),
                    "traceback": traceback.format_exc(),
                }

        sys.stdout.write(json.dumps(response) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
